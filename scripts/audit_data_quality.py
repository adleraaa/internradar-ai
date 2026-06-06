#!/usr/bin/env python3
"""Local-only data quality audit for data/internships.json.

Standard-library only. Does NOT install or require any third-party package.
This audit is LOCAL ONLY -- it never fetches web pages or checks live status.

Errors are integrity problems that should block publishing.
Warnings are quality concerns worth a human look.

Exit code:
    0  -> no errors (warnings allowed)
    1  -> one or more errors (or the data file could not be read)
"""

import json
import os
import re
import sys
from urllib.parse import urlparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "internships.json")

STATUS_ENUM = ["Open", "Closed", "Unclear"]

# Heuristics for application_url shapes that are NOT acceptable final links.
HOMEPAGE_PATH_RE = re.compile(r"^/?(careers?|jobs|join-?us|opportunities)/?$", re.I)
SEARCH_HINT_RE = re.compile(r"(/search|/jobs/search|[?&](q|query|keyword|search)=)", re.I)


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def classify_url(url):
    """Return a short reason string if the URL looks unacceptable, else None."""
    if not url or not url.strip():
        return None  # missing handled separately
    u = url.strip()
    low = u.lower()

    if "simplify.jobs" in low:
        return "looks like a Simplify redirect, not a final official link"

    parsed = urlparse(u)
    host = (parsed.netloc or "").lower()
    path = parsed.path or ""

    # Raw API endpoints.
    if host.startswith("api.") or "-api." in host or "/api/" in low or "boards-api" in host:
        return "looks like a raw API endpoint, not a human-facing page"

    # Generic search pages.
    if SEARCH_HINT_RE.search(u):
        return "looks like a job-search/query page, not a specific role page"

    # Generic careers/jobs homepage with no specific posting path.
    if HOMEPAGE_PATH_RE.match(path) or path in ("", "/"):
        return "looks like a generic careers/jobs homepage, not a specific role page"

    return None


def is_unclear_enum(value):
    return (value or "").strip().lower() == "unclear"


def is_unclear_text(value):
    text = (value or "").strip().lower()
    if not text:
        return True
    return text == "unclear" or "not stated" in text or "not explicitly" in text \
        or text.startswith("unclear")


def audit(entries, report):
    seen_ids = {}
    seen_urls = {}

    for i, e in enumerate(entries):
        label = "entry[%d] (id=%s)" % (i, e.get("id", "<no id>"))

        if not isinstance(e, dict):
            report.error("%s is not a JSON object." % label)
            continue

        # Duplicate id.
        eid = e.get("id")
        if isinstance(eid, str) and eid.strip():
            if eid in seen_ids:
                report.error("Duplicate id '%s' (entries %d and %d)."
                             % (eid, seen_ids[eid], i))
            else:
                seen_ids[eid] = i

        # application_url present + duplicate + shape.
        url = e.get("application_url")
        if not (isinstance(url, str) and url.strip()):
            report.error("%s missing application_url." % label)
        else:
            key = url.strip()
            if key in seen_urls:
                report.error("Duplicate application_url (entries %d and %d): %s"
                             % (seen_urls[key], i, key))
            else:
                seen_urls[key] = i
            reason = classify_url(key)
            if reason:
                report.warn("%s application_url %s: %s" % (label, reason, key))

        # last_verified_date present.
        lvd = e.get("last_verified_date")
        if not (isinstance(lvd, str) and lvd.strip()):
            report.error("%s missing last_verified_date." % label)

        # status enum.
        if e.get("status") not in STATUS_ENUM:
            report.error("%s status %r is not in %s." % (label, e.get("status"), STATUS_ENUM))

        # Closed roles still show up in the generated README table -> warning.
        if e.get("status") == "Closed":
            report.warn("%s status is Closed; it still appears in the generated "
                        "README table until archived." % label)

        # Evidence / fit completeness.
        if not (e.get("evidence_notes") or "").strip():
            report.warn("%s has empty evidence_notes." % label)
        if not (e.get("fit_summary") or "").strip():
            report.warn("%s has empty fit_summary." % label)

        # risk_flags empty while something is Unclear.
        risk = e.get("risk_flags")
        risk_empty = not (isinstance(risk, list) and len(risk) > 0)
        unclear_dims = []
        if is_unclear_enum(e.get("requires_us_citizenship")):
            unclear_dims.append("citizenship")
        if is_unclear_text(e.get("sponsorship_note")):
            unclear_dims.append("sponsorship")
        if is_unclear_text(e.get("work_authorization_note")):
            unclear_dims.append("work authorization")
        if is_unclear_enum(e.get("student_level")):
            unclear_dims.append("student level")
        if is_unclear_enum(e.get("location_type")):
            unclear_dims.append("location")
        if risk_empty and unclear_dims:
            report.warn("%s has empty risk_flags but these are Unclear: %s."
                        % (label, ", ".join(unclear_dims)))


def main():
    print("=" * 60)
    print("InternRadar AI - data quality audit (local only)")
    print("=" * 60)

    if not os.path.exists(DATA_PATH):
        print("ERROR: data file not found: %s" % DATA_PATH, file=sys.stderr)
        return 1
    try:
        data = load_data()
    except ValueError as exc:
        print("ERROR: data file is not valid JSON: %s" % exc, file=sys.stderr)
        return 1
    if not isinstance(data, list):
        print("ERROR: top-level JSON must be an array.", file=sys.stderr)
        return 1

    report = Report()
    audit(data, report)

    print("Entries audited: %d" % len(data))
    print("Errors:   %d" % len(report.errors))
    print("Warnings: %d" % len(report.warnings))

    if report.warnings:
        print("\nWARNINGS:")
        for w in report.warnings:
            print("  - %s" % w)
    if report.errors:
        print("\nERRORS:")
        for e in report.errors:
            print("  - %s" % e)

    print("-" * 60)
    if report.errors:
        print("RESULT: FAILED")
        return 1
    print("RESULT: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
