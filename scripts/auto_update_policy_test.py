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
    print("Result: %d passed, %d failed" % (passed, failed if failed else 0))
    if failed:
        print("RESULT: FAILED")
        return 1
    print("RESULT: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
