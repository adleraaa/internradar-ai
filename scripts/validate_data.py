#!/usr/bin/env python3
"""Validate data/internships.json for InternRadar AI.

Standard-library only. Does NOT install or require any third-party package.
If the optional `jsonschema` package happens to be installed, it is used as an
extra check; otherwise validation falls back to manual, field-by-field checks.

Exit code:
    0  -> validation passed (warnings allowed)
    1  -> validation failed (one or more errors)
    2  -> could not run (e.g. data file missing / not valid JSON)
"""

import json
import os
import re
import sys

# --- Paths ------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "internships.json")
SCHEMA_PATH = os.path.join(PROJECT_ROOT, "data", "schema.json")

# --- Enums (kept in sync with data/schema.json) -----------------------------

ENUMS = {
    "category": ["Software Engineering", "AI/ML", "Data Science", "Product", "Hardware", "Other"],
    "location_type": ["Remote", "Hybrid", "Onsite", "Multiple", "Unclear"],
    "status": ["Open", "Closed", "Unclear"],
    "source_type": ["Company Career Page", "Greenhouse", "Lever", "Ashby", "Workday",
                    "Simplify", "Handshake", "LinkedIn", "Other"],
    "ai_relevance": ["High", "Medium", "Low", "None", "Unclear"],
    "full_stack_relevance": ["High", "Medium", "Low", "None", "Unclear"],
    "student_level": ["Freshman", "Sophomore", "Junior", "Senior", "Undergraduate", "Graduate", "Unclear"],
    "freshman_sophomore_friendly": ["Yes", "No", "Unclear"],
    "requires_us_citizenship": ["Yes", "No", "Unclear"],
}

REQUIRED_FIELDS = [
    "id", "company", "role", "category", "location", "location_type",
    "internship_term", "application_url", "source_url", "source_type",
    "status", "last_verified_date", "discovered_date", "age_days",
    "tech_keywords", "ai_relevance", "full_stack_relevance", "student_level",
    "freshman_sophomore_friendly", "requires_us_citizenship", "sponsorship_note",
    "work_authorization_note", "evidence_notes", "fit_summary", "risk_flags",
    "date_added", "date_updated",
]

DATE_FIELDS = ["last_verified_date", "discovered_date", "date_added", "date_updated"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ARRAY_FIELDS = ["tech_keywords", "risk_flags"]

# Fields whose claims require evidence when they assert something definite.
CLAIM_FIELDS = {
    "requires_us_citizenship": ["Yes", "No"],
    "freshman_sophomore_friendly": ["Yes", "No"],
}


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_entry(entry, index, report):
    label = "entry[%d]" % index
    if not isinstance(entry, dict):
        report.error("%s is not a JSON object." % label)
        return

    eid = entry.get("id", "<no id>")
    label = "entry[%d] (id=%s)" % (index, eid)

    # Required fields present.
    for field in REQUIRED_FIELDS:
        if field not in entry:
            report.error("%s missing required field '%s'." % (label, field))

    # application_url present and non-empty.
    app_url = entry.get("application_url")
    if not (isinstance(app_url, str) and app_url.strip()):
        report.error("%s has missing or empty 'application_url'." % label)

    # last_verified_date present.
    lvd = entry.get("last_verified_date")
    if not (isinstance(lvd, str) and lvd.strip()):
        report.error("%s has missing or empty 'last_verified_date'." % label)

    # Date format checks.
    for field in DATE_FIELDS:
        val = entry.get(field)
        if isinstance(val, str) and val.strip() and not DATE_RE.match(val):
            report.error("%s field '%s' must be YYYY-MM-DD (got '%s')." % (label, field, val))

    # status enum (explicit per spec).
    status = entry.get("status")
    if status not in ENUMS["status"]:
        report.error("%s 'status' must be one of %s (got %r)." % (label, ENUMS["status"], status))

    # All enum fields.
    for field, allowed in ENUMS.items():
        if field == "status":
            continue  # already reported above
        if field in entry and entry[field] not in allowed:
            report.error("%s '%s' must be one of %s (got %r)." % (label, field, allowed, entry[field]))

    # age_days non-negative integer.
    age = entry.get("age_days")
    if not isinstance(age, int) or isinstance(age, bool) or age < 0:
        report.error("%s 'age_days' must be a non-negative integer (got %r)." % (label, age))

    # Array fields.
    for field in ARRAY_FIELDS:
        if field in entry and not isinstance(entry[field], list):
            report.error("%s '%s' must be an array." % (label, field))

    # Evidence warnings for definite citizenship/sponsorship/authorization claims.
    evidence = entry.get("evidence_notes", "")
    has_evidence = isinstance(evidence, str) and evidence.strip() != ""

    for field, asserting_values in CLAIM_FIELDS.items():
        if entry.get(field) in asserting_values and not has_evidence:
            report.warn("%s asserts '%s'='%s' but 'evidence_notes' is empty."
                        % (label, field, entry.get(field)))

    sponsorship = entry.get("sponsorship_note", "")
    if isinstance(sponsorship, str) and sponsorship.strip() and not has_evidence:
        report.warn("%s has a 'sponsorship_note' but 'evidence_notes' is empty." % label)

    work_auth = entry.get("work_authorization_note", "")
    if isinstance(work_auth, str) and work_auth.strip() and not has_evidence:
        report.warn("%s has a 'work_authorization_note' but 'evidence_notes' is empty." % label)


def try_jsonschema(data, schema, report):
    """Optional extra validation if jsonschema is installed. Never required."""
    try:
        import jsonschema  # type: ignore
    except Exception:
        print("  (optional) jsonschema package not available - using manual checks only.")
        return
    try:
        jsonschema.validate(instance=data, schema=schema)
        print("  (optional) jsonschema validation passed.")
    except jsonschema.ValidationError as exc:  # type: ignore
        report.error("jsonschema validation error: %s" % exc.message)
    except Exception as exc:
        print("  (optional) jsonschema could not run: %s" % exc)


def main():
    print("=" * 60)
    print("InternRadar AI - data validation")
    print("=" * 60)
    print("Data file:   %s" % DATA_PATH)
    print("Schema file: %s" % SCHEMA_PATH)
    print("-" * 60)

    # Load data.
    if not os.path.exists(DATA_PATH):
        print("ERROR: data file not found: %s" % DATA_PATH)
        return 2
    try:
        data = load_json(DATA_PATH)
    except ValueError as exc:
        print("ERROR: data file is not valid JSON: %s" % exc)
        return 2

    if not isinstance(data, list):
        print("ERROR: top-level JSON must be an array of internship objects.")
        return 2

    # Load schema (optional).
    schema = None
    if os.path.exists(SCHEMA_PATH):
        try:
            schema = load_json(SCHEMA_PATH)
            print("Schema loaded OK.")
        except ValueError as exc:
            print("WARNING: schema file is not valid JSON, skipping schema load: %s" % exc)
    else:
        print("WARNING: schema file not found, skipping schema load.")

    report = Report()

    # Manual per-entry validation.
    for index, entry in enumerate(data):
        validate_entry(entry, index, report)

    # Optional jsonschema check.
    if schema is not None:
        try_jsonschema(data, schema, report)

    # Report.
    print("-" * 60)
    print("Entries checked: %d" % len(data))
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
