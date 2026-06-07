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
    print("Result: %d passed, %d failed" % (passed, failed if failed else 0))
    if failed:
        print("RESULT: FAILED")
        return 1
    print("RESULT: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
