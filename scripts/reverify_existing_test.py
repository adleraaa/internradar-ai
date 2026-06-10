#!/usr/bin/env python3
"""Local tests for the re-verification classifier.

Standard-library only. Exercises scripts/reverify_existing.py's pure
keep/warn/remove decision (no network, no I/O). Removal must happen ONLY on
deterministic failures; every transient/ambiguous signal must keep the posting.

Exit code:
    0  -> all tests passed
    1  -> one or more tests failed
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reverify_existing as rv  # noqa: E402


# A clean, reachable, still-open official posting (the keep "happy path").
OPEN = dict(
    http_status=200, network_error=None,
    final_url="https://job-boards.greenhouse.io/acme/jobs/123",
    title_match=True, apply_found=True, closed_signal=False, js_heavy=False,
)


def decide(**overrides):
    kwargs = dict(OPEN)
    kwargs.update(overrides)
    action, reason, _evidence = rv.classify_reverify(**kwargs)
    return action, reason


CASES = []


def case(name, expect_action, **overrides):
    CASES.append((name, expect_action, overrides))


# --- keep ---
case("200 + title + apply -> keep", "keep")

# --- deterministic removals ---
case("404 -> remove", "remove", http_status=404, title_match=False, apply_found=False)
case("410 -> remove", "remove", http_status=410, title_match=False, apply_found=False)
case("'job no longer available' banner -> remove", "remove", closed_signal=True)
case("'position filled' banner -> remove", "remove", closed_signal=True)
case("generic careers URL -> remove", "remove",
     final_url="https://acme.com/careers", title_match=False, apply_found=False)
case("private/login-gated final URL -> remove", "remove",
     final_url="https://www.linkedin.com/jobs/view/123")
case("raw API final URL -> remove", "remove",
     final_url="https://boards-api.greenhouse.io/v1/boards/acme/jobs/1")
case("search/query final URL -> remove", "remove",
     final_url="https://acme.com/jobs/search?q=intern")
case("title gone AND no apply flow -> remove", "remove",
     title_match=False, apply_found=False)

# --- transient: ALWAYS warn (kept), NEVER remove ---
case("429 -> warn", "warn", http_status=429)
case("503 -> warn", "warn", http_status=503)
case("500 -> warn", "warn", http_status=500)
case("timeout -> warn", "warn", http_status=None, network_error="timeout")
case("DNS failure -> warn", "warn", http_status=None, network_error="dns")
case("403 (ambiguous) -> warn", "warn", http_status=403)
case("no status, no error -> warn", "warn", http_status=None, network_error=None)

# --- ambiguous at 200: warn/keep, NOT remove ---
case("title mismatch but apply present (ambiguous) -> warn", "warn",
     title_match=False, apply_found=True)
case("title present but apply not detected (ambiguous) -> warn", "warn",
     title_match=True, apply_found=False)
case("JS-heavy page -> warn", "warn", js_heavy=True, title_match=False, apply_found=False)

# --- safety: a transient error must win even if the URL looks forbidden ---
case("timeout on a careers-looking URL -> warn (never remove)", "warn",
     http_status=None, network_error="timeout", final_url="https://acme.com/careers")
# --- safety: 5xx must not remove even with title/apply gone ---
case("503 with title/apply gone -> warn (never remove)", "warn",
     http_status=503, title_match=False, apply_found=False)


def closed_regex_checks():
    """The closed-page regex must catch real closure phrasing and reject
    ordinary open-posting text (tight, to avoid deleting live postings)."""
    should_match = [
        "This job is no longer available.",
        "We are no longer accepting applications for this role.",
        "This position has been filled.",
        "The position is filled.",
        "This posting has expired.",
        "Applications for this job are now closed.",
        "This requisition is closed.",
        "This job posting has been removed.",
    ]
    should_not_match = [
        "Apply now for this Software Engineer Internship.",
        "We build closed-loop control systems for robotics.",  # 'closed' unrelated
        "Open positions are filled by our hiring team year-round.",  # no closure phrase
        "Submit your application to join our team.",
    ]
    ok = True
    for txt in should_match:
        got = bool(rv.CLOSED_PAGE_RE.search(txt))
        status = "ok" if got else "FAIL"
        if not got:
            ok = False
        print("  [%s] closed match: %r" % (status, txt[:48]))
    for txt in should_not_match:
        got = bool(rv.CLOSED_PAGE_RE.search(txt))
        status = "ok" if not got else "FAIL"
        if got:
            ok = False
        print("  [%s] open (no match): %r" % (status, txt[:48]))
    return ok


def forbidden_url_checks():
    """classify_forbidden must flag generic/private/api/search final URLs and
    pass clean specific ATS posting URLs."""
    checks = [
        ("https://acme.com/careers", True),
        ("https://www.linkedin.com/jobs/view/1", True),
        ("https://boards-api.greenhouse.io/v1/boards/acme/jobs/1", True),
        ("https://acme.com/jobs/search?q=intern", True),
        ("https://simplify.jobs/p/abc", True),
        ("https://job-boards.greenhouse.io/acme/jobs/123", False),
        ("https://jobs.lever.co/acme/uuid", False),
        ("https://jobs.ashbyhq.com/acme/uuid/application", False),
    ]
    ok = True
    for url, expect_forbidden in checks:
        got = rv.classify_forbidden(url) is not None
        status = "ok" if got == expect_forbidden else "FAIL"
        if got != expect_forbidden:
            ok = False
        print("  [%s] classify_forbidden(%s) forbidden=%s" % (status, url, got))
    return ok


def main():
    print("Re-verification classifier tests")
    print("-" * 60)
    passed = 0
    failed = 0
    for name, expect_action, overrides in CASES:
        action, reason = decide(**overrides)
        ok = (action == expect_action)
        if ok:
            passed += 1
        else:
            failed += 1
        print("  [%s] %-52s -> %s" % ("PASS" if ok else "FAIL", name, action))
        if not ok:
            print("        expected %s, got %s (%s)" % (expect_action, action, reason))

    print("-" * 60)
    print("Closed-page regex checks:")
    if not closed_regex_checks():
        failed += 1

    print("-" * 60)
    print("Forbidden final-URL checks:")
    if not forbidden_url_checks():
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
