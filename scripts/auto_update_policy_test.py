#!/usr/bin/env python3
"""Local tests for the auto-promotion policy logic.

Standard-library only. Exercises scripts/verify_candidates.py's pure
verification-confidence + eligibility decision (no network, no I/O).

Exit code:
    0  -> all tests passed
    1  -> one or more tests failed
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_candidates as v  # noqa: E402


# A fully-verified, clean official internship posting (the "happy path").
CLEAN = dict(
    reachable=True, title_match=True, apply_found=True, internship_wording=True,
    location_found=True, technical=True, comp_classified=True,
    forbidden_reason=None, js_heavy=False, non_internship=False,
    nontechnical=False, senior_fulltime=False, duplicate=False, status_open=True,
)


def decide(**overrides):
    kwargs = dict(CLEAN)
    kwargs.update(overrides)
    conf, eligible, reasons, blockers = v.score_and_eligibility(**kwargs)
    return conf, eligible, blockers


CASES = []


def case(name, expect_eligible, **overrides):
    CASES.append((name, expect_eligible, overrides))


# --- Test cases (task 4) ---
case("high-confidence official ATS page -> eligible", True)
case("duplicate URL -> blocked", False, duplicate=True)
case("generic careers URL -> blocked", False,
     forbidden_reason="generic careers/jobs homepage")
case("raw API final URL -> blocked", False, forbidden_reason="raw API URL")
case("Simplify redirect final URL -> blocked", False,
     forbidden_reason="Simplify redirect as final URL")
case("private board final URL -> blocked", False,
     forbidden_reason="private/login-gated job board")
case("non-internship title -> blocked", False, non_internship=True, internship_wording=False)
case("nontechnical title -> blocked", False, nontechnical=True, technical=False)
case("JS-heavy page -> blocked", False, js_heavy=True)
case("senior/full-time role -> blocked", False, senior_fulltime=True)
case("status not Open -> blocked", False, status_open=False)
case("graduate-only role -> blocked", False, graduate_only=True)
case("title not a clean internship -> blocked", False, title_level_intern=False)
case("hardware-adjacent role -> blocked", False, hardware_adjacent=True)
# Unclear sponsorship / compensation must NOT block (they aren't inputs to the
# verification score at all — verification != user-fit).
case("unclear sponsorship but otherwise verified -> eligible", True)
case("unclear compensation but otherwise verified -> eligible", True)
# Below-threshold confidence (drop a couple of positive signals) -> blocked.
case("confidence below threshold -> blocked", False,
     location_found=False, internship_wording=False, non_internship=True)


def url_forbidden_checks():
    """Sanity-check classify_forbidden on representative URLs."""
    checks = [
        ("https://simplify.jobs/p/abc", True),
        ("https://www.linkedin.com/jobs/view/123", True),
        ("https://api.greenhouse.io/v1/boards/acme/jobs/1", True),
        ("https://acme.com/careers", True),
        ("https://acme.com/jobs/search?q=intern", True),
        ("https://job-boards.greenhouse.io/acme/jobs/123", False),
        ("https://jobs.ashbyhq.com/acme/uuid/application", False),
    ]
    ok = True
    for url, should_be_forbidden in checks:
        reason = v.classify_forbidden(url)
        got = reason is not None
        status = "ok" if got == should_be_forbidden else "FAIL"
        if status == "FAIL":
            ok = False
        print("  [%s] classify_forbidden(%s) -> %r" % (status, url, reason))
    return ok


def hardware_checks():
    """is_hardware_only must flag hardware/electrical roles, not pure software."""
    checks = [
        ("Digital IC Design Engineer Intern", True),
        ("Physical Design for Machine Learning Intern", True),
        ("Firmware Engineer - Internship", True),
        ("FPGA / RTL Design Intern", True),
        ("Software Engineer Intern", False),
        ("Full-Stack Engineering Intern", False),
        ("Software Intern - AI Compilers", False),
        ("Data Science Intern", False),
    ]
    ok = True
    for title, expect in checks:
        got = v.is_hardware_only(title)
        status = "ok" if got == expect else "FAIL"
        if status == "FAIL":
            ok = False
        print("  [%s] is_hardware_only(%r) -> %s" % (status, title, got))
    return ok


def graduate_checks():
    """is_graduate_only must flag graduate/PhD/MBA-only roles, not mixed eligibility."""
    checks = [
        ("PhD Intern, Machine Learning", "", True),
        ("Research Scientist PhD Intern", "", True),
        ("MBA Product Intern", "", True),
        ("Software Engineering Intern - Bachelor's or Master's", "", False),
        ("Software Engineer Intern - B.S. or M.S. in Computer Science", "", False),
        ("Software Engineer Intern", "Undergraduate or graduate students welcome.", False),
    ]
    ok = True
    for title, text, expect in checks:
        got, _ = v.is_graduate_only(title, text)
        status = "ok" if got == expect else "FAIL"
        if status == "FAIL":
            ok = False
        print("  [%s] is_graduate_only(%r) -> %s" % (status, title, got))
    return ok


def tightened_gate_checks():
    """End-to-end auto-promote eligibility for real titles, assuming the candidate
    is otherwise high-confidence (reachable/title/apply/location/technical)."""
    # (title, body, expect_eligible)
    cases = [
        ("Engineering High-Potential Launch Program Intern to Full-Time Program", "", False),
        ("Software Graduate Intern - Autonomous Lab", "", False),
        ("Software Graduate Intern - Autonomous Lab",
         "Undergraduate or graduate students welcome.", True),
        ("Design Verification Engineer - Intern 2026",
         "We design ASIC / RTL semiconductor silicon.", False),
        ("Platform Applications Engineer Internship",
         "Astera Labs is a semiconductor company building silicon for PCIe.", False),
        ("Embedded Software Developer Intern", "satellite payload device firmware", False),
        ("Software Intern - AI Compilers", "We build compilers and ML tooling.", True),
        ("Software Developer Intern", "build backend web services", True),
        ("Software Quality Engineer Intern", "test and automate software", True),
    ]
    ok = True
    for title, body, expect in cases:
        title_ok, _ = v.title_level_internship(title)
        hw, _ = v.is_hardware_adjacent(title, body)
        grad, _ = v.is_graduate_only(title, body)
        _, eligible, _, _ = v.score_and_eligibility(
            reachable=True, title_match=True, apply_found=True, internship_wording=True,
            location_found=True, technical=True, comp_classified=True,
            forbidden_reason=None, js_heavy=False, non_internship=False,
            nontechnical=False, senior_fulltime=False, duplicate=False, status_open=True,
            graduate_only=grad, title_level_intern=title_ok, hardware_adjacent=hw)
        status = "ok" if eligible == expect else "FAIL"
        if status == "FAIL":
            ok = False
        print("  [%s] eligible=%s (expect %s) | %r" % (status, eligible, expect, title))
    return ok


def compensation_detection_checks():
    """detect_compensation must parse explicit pay (incl. hourly ranges) and only
    that — no guessing, official-page text only."""
    # (page_text, min, max, period)
    cases = [
        ("Compensation ranges from $50/hr - $70/hr including base.", 50, 70, "Hour"),
        ("$50 / hr - $70 / hr", 50, 70, "Hour"),
        ("$50 to $70 per hour", 50, 70, "Hour"),
        ("$25/hr", 25, 25, "Hour"),
        ("the base pay rate is $25 per hour", 25, 25, "Hour"),
        ("$7,000/month", 7000, 7000, "Month"),
        ("$80,000/year", 80000, 80000, "Year"),
        ("this is an unpaid internship", None, None, "Unpaid"),
        ("no compensation is listed on this page", None, None, "Unclear"),
        ("We crossed $100M in ARR last year", None, None, "Unclear"),
    ]
    ok = True
    for text, exp_min, exp_max, exp_period in cases:
        r = v.detect_compensation(text, "Greenhouse")
        got = (r["compensation_min"], r["compensation_max"], r["compensation_period"])
        exp = (exp_min, exp_max, exp_period)
        status = "ok" if got == exp else "FAIL"
        if status == "FAIL":
            ok = False
        print("  [%s] %r -> %s%s" % (status, text[:38], got,
                                     "" if status == "ok" else " (expected %s)" % (exp,)))
    return ok


class _FakeResponse:
    """Minimal stand-in for the object urllib.request.urlopen returns."""

    def __init__(self, status, final_url, body):
        self._status, self._final_url, self._body = status, final_url, body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, _n=-1):
        return self._body.encode("utf-8")

    def getcode(self):
        return self._status

    def geturl(self):
        return self._final_url


def closed_candidate_checks():
    """verify_one must refuse a candidate whose ATS reports it closed, even when
    the page it lands on (a Greenhouse board index) lists a similar title and
    has apply links. Offline: urlopen is replaced with canned responses."""
    board = ("<title>Jobs at Acme</title> Current openings at Acme. "
             + "Software Engineer Intern - Summer 2027 New York, NY Apply. " * 20)
    ashby_shell = ('<title>Jobs</title><script>window.__appData = {"organization":null,'
                   '"posting":null,"jobBoard":null};</script> You need to enable JavaScript.')
    cases = [
        ("Greenhouse job redirected to board index",
         "https://job-boards.greenhouse.io/acme/jobs/4703343005",
         _FakeResponse(200, "https://job-boards.greenhouse.io/acme?error=true", board)),
        ("Ashby shell with posting null",
         "https://jobs.ashbyhq.com/acme/e458b046-aa7f-4022-bca5-63cdfd495456/application",
         _FakeResponse(200, "https://jobs.ashbyhq.com/acme/e458b046-aa7f-4022-bca5-63cdfd495456"
                            "/application", ashby_shell)),
    ]
    real_urlopen = v.urllib.request.urlopen
    ok = True
    try:
        for label, url, resp in cases:
            v.urllib.request.urlopen = lambda *_a, _r=resp, **_k: _r
            cand = {"url": url, "title": "Software Engineer Intern", "company": "Acme",
                    "locations": ["New York, NY"], "terms": ["Summer 2027"],
                    "source_category": "Software"}
            fields, result = v.verify_one(cand)
            refused = fields is None and "closed" in result.get("skip_reason", "")
            status = "ok" if refused else "FAIL"
            if not refused:
                ok = False
            print("  [%s] %s -> skip_reason=%r" % (status, label, result.get("skip_reason")))
    finally:
        v.urllib.request.urlopen = real_urlopen
    return ok


def redirected_candidate_checks():
    """A link that now lands on a generic careers page is pruned by re-verification
    (which judges the FINAL url), so promotion must judge the final url too —
    otherwise the same posting is removed and re-added day after day."""
    page = ("<title>Careers at Acme</title> Software Engineer Intern. Apply today. "
            + "Join our team of engineers building the future of the internet. " * 12)
    # (label, url, final_url, skip_reason or blocker that must explain the refusal)
    cases = [
        ("Greenhouse link -> acme.com/careers",
         "https://boards.greenhouse.io/acme/jobs/7774167",
         "https://www.acme.com/careers", "posting closed"),
        ("company job link -> generic /jobs page",
         "https://careers.acme.com/jobs/12345",
         "https://careers.acme.com/jobs", "forbidden source"),
    ]
    real_urlopen = v.urllib.request.urlopen
    ok = True
    try:
        for label, url, final_url, why in cases:
            v.urllib.request.urlopen = lambda *_a, _f=final_url, **_k: _FakeResponse(
                200, _f, page)
            _fields, result = v.verify_one({
                "url": url, "title": "Software Engineer Intern", "company": "Acme",
                "locations": ["Austin, TX"], "terms": ["Summer 2027"],
                "source_category": "Software"})
            reasons = [result.get("skip_reason", "")] + result.get("auto_promote_blockers", [])
            refused = not result.get("auto_promote_eligible") and any(why in r for r in reasons)
            if not refused:
                ok = False
            print("  [%s] %s -> eligible=%s reasons=%s"
                  % ("ok" if refused else "FAIL", label, result.get("auto_promote_eligible"),
                     [r for r in reasons if r]))
    finally:
        v.urllib.request.urlopen = real_urlopen
    return ok


def fit_summary_checks():
    """fit_summary is shown on the public dashboard, so the text generated for a
    verified posting must not carry maintainer-only instructions."""
    url = "https://job-boards.greenhouse.io/acme/jobs/4703343005"
    page = ("<title>Job Application for Software Engineer Intern at Acme</title> "
            "Software Engineer Intern New York, NY Apply for this job. "
            + "You will build backend services in Python for undergraduate interns. " * 12)
    real_urlopen = v.urllib.request.urlopen
    try:
        v.urllib.request.urlopen = lambda *_a, **_k: _FakeResponse(200, url, page)
        fields, result = v.verify_one({
            "url": url, "title": "Software Engineer Intern", "company": "Acme",
            "locations": ["New York, NY"], "terms": ["Summer 2027"],
            "source_category": "Software"})
    finally:
        v.urllib.request.urlopen = real_urlopen
    if fields is None:
        print("  [FAIL] open posting was not drafted: %r" % result.get("skip_reason"))
        return False
    summary = fields["fit_summary"]
    leaked = [p for p in ("promot", "verify the official page", "maintainer")
              if p in summary.lower()]
    status = "ok" if not leaked else "FAIL"
    print("  [%s] fit_summary=%r" % (status, summary))
    return not leaked


def main():
    print("Auto-promotion policy tests")
    print("-" * 60)
    passed = 0
    failed = 0
    for name, expect_eligible, overrides in CASES:
        conf, eligible, blockers = decide(**overrides)
        ok = (eligible == expect_eligible)
        if ok:
            passed += 1
        else:
            failed += 1
        print("  [%s] %-55s conf=%3d eligible=%s"
              % ("PASS" if ok else "FAIL", name, conf, eligible))
        if not ok:
            print("        expected eligible=%s; blockers=%s" % (expect_eligible, blockers))

    print("-" * 60)
    print("URL classification checks:")
    url_ok = url_forbidden_checks()
    if not url_ok:
        failed += 1

    print("-" * 60)
    print("Hardware-only detection checks:")
    hw_ok = hardware_checks()
    if not hw_ok:
        failed += 1

    print("-" * 60)
    print("Graduate-only detection checks:")
    grad_ok = graduate_checks()
    if not grad_ok:
        failed += 1

    print("-" * 60)
    print("Tightened eligibility gate checks (real titles):")
    gate_ok = tightened_gate_checks()
    if not gate_ok:
        failed += 1

    print("-" * 60)
    print("Compensation detection checks:")
    comp_ok = compensation_detection_checks()
    if not comp_ok:
        failed += 1

    print("-" * 60)
    print("Closed-candidate checks (offline):")
    if not closed_candidate_checks():
        failed += 1

    print("-" * 60)
    print("Redirected-candidate checks (offline):")
    if not redirected_candidate_checks():
        failed += 1

    print("-" * 60)
    print("Public fit_summary checks (offline):")
    if not fit_summary_checks():
        failed += 1

    print("-" * 60)
    print("Result: %d passed, %d failed" % (passed, failed if failed else 0))
    if failed:
        print("RESULT: FAILED")
        return 1
    print("RESULT: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
