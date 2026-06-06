#!/usr/bin/env python3
"""Convert ONE reviewed Markdown submission into a JSON internship object.

Standard-library only. Does NOT install or require any third-party package.

Usage:
    python scripts/submission_to_json.py <path-to-submission.md>

Behavior:
  - Parses `- **field:** value` lines from the Markdown template.
  - Validates enum fields against the enum values in data/schema.json
    (falls back to built-in enums if the schema cannot be read).
  - Warns (stderr) if required fields are missing.
  - Generates a stable `id` from company + role + internship_term + discovered_date.
  - Computes `age_days` from discovered_date to today when possible.
  - Converts comma-separated `tech_keywords` and `risk_flags` into arrays.
  - Keeps `evidence_notes` and `fit_summary` as strings.
  - Prints the resulting JSON object to stdout.
  - Does NOT modify data/internships.json.

Exit code:
    0  -> conversion succeeded (object printed to stdout)
    1  -> usage error / file error
    2  -> required fields missing or enum values invalid
"""

import datetime
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SCHEMA_PATH = os.path.join(PROJECT_ROOT, "data", "schema.json")

# Built-in enum fallback (kept in sync with data/schema.json).
FALLBACK_ENUMS = {
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

# Fields the parser reads directly from the Markdown.
STRING_FIELDS = [
    "company", "role", "category", "location", "location_type", "internship_term",
    "application_url", "source_url", "source_type", "status",
    "last_verified_date", "discovered_date",
    "ai_relevance", "full_stack_relevance", "student_level",
    "freshman_sophomore_friendly", "requires_us_citizenship",
    "sponsorship_note", "work_authorization_note", "evidence_notes", "fit_summary",
]
LIST_FIELDS = ["tech_keywords", "risk_flags"]

# Minimum fields required to build a usable entry.
REQUIRED_FIELDS = [
    "company", "role", "category", "location_type", "internship_term",
    "application_url", "source_type", "status", "last_verified_date",
    "discovered_date",
]

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Matches:  - **field:** value   (also tolerates leading spaces / extra spaces)
FIELD_RE = re.compile(r"^\s*[-*]?\s*\*\*\s*([A-Za-z_]+)\s*:\*\*\s*(.*?)\s*$")


def load_enums():
    """Load enum allowed-values from schema.json; fall back to built-ins."""
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8-sig") as fh:
            schema = json.load(fh)
        props = schema.get("items", {}).get("properties", {})
        enums = {}
        for field, spec in props.items():
            if isinstance(spec, dict) and "enum" in spec:
                enums[field] = list(spec["enum"])
        # Merge: schema wins, fallback fills any gaps.
        merged = dict(FALLBACK_ENUMS)
        merged.update(enums)
        return merged
    except Exception:
        return dict(FALLBACK_ENUMS)


def strip_comment(value):
    """Remove a trailing inline HTML comment, if present."""
    idx = value.find("<!--")
    if idx != -1:
        value = value[:idx]
    return value.strip()


def parse_markdown(text):
    """Return a dict of {field: raw_value} parsed from the submission."""
    fields = {}
    for line in text.splitlines():
        m = FIELD_RE.match(line)
        if not m:
            continue
        key = m.group(1).strip()
        val = strip_comment(m.group(2))
        # Only keep the first occurrence of a field.
        if key not in fields:
            fields[key] = val
    return fields


def to_list(raw):
    """Split a comma-separated string into a clean list of strings."""
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def slugify(text):
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", text or "").strip("-").lower()
    return cleaned if cleaned else "unknown"


def make_id(company, role, term, discovered_date):
    parts = [slugify(company), slugify(role), slugify(term), slugify(discovered_date)]
    return "-".join(parts)


def compute_age_days(discovered_date):
    """Days from discovered_date to today, or None if not computable."""
    if not DATE_RE.match(discovered_date or ""):
        return None
    try:
        d = datetime.date(*[int(x) for x in discovered_date.split("-")])
    except ValueError:
        return None
    delta = (datetime.date.today() - d).days
    return delta if delta >= 0 else 0


def main(argv):
    if len(argv) != 2:
        print("Usage: python scripts/submission_to_json.py <path-to-submission.md>",
              file=sys.stderr)
        print("Convert one reviewed Markdown submission into a JSON object (stdout).",
              file=sys.stderr)
        return 1

    path = argv[1]
    if not os.path.isfile(path):
        print("ERROR: file not found: %s" % path, file=sys.stderr)
        return 1

    try:
        # utf-8-sig tolerates a leading BOM that Windows editors may add.
        with open(path, "r", encoding="utf-8-sig") as fh:
            text = fh.read()
    except OSError as exc:
        print("ERROR: could not read file: %s" % exc, file=sys.stderr)
        return 1

    enums = load_enums()
    parsed = parse_markdown(text)

    errors = []
    warnings = []

    # Warn on missing required fields.
    for field in REQUIRED_FIELDS:
        if not parsed.get(field, "").strip():
            warnings.append("missing required field '%s'" % field)
            errors.append("required field '%s' is missing or empty" % field)

    # Build the entry.
    entry = {}
    for field in STRING_FIELDS:
        entry[field] = parsed.get(field, "").strip()
    for field in LIST_FIELDS:
        entry[field] = to_list(parsed.get(field, ""))

    # Validate enum fields.
    for field, allowed in enums.items():
        val = entry.get(field, "")
        if val and val not in allowed:
            errors.append("field '%s' has invalid value %r (allowed: %s)"
                          % (field, val, ", ".join(allowed)))

    # Derived fields.
    discovered_date = entry.get("discovered_date", "")
    entry["id"] = make_id(
        entry.get("company", ""),
        entry.get("role", ""),
        entry.get("internship_term", ""),
        discovered_date,
    )
    age = compute_age_days(discovered_date)
    if age is None:
        warnings.append("could not compute age_days (discovered_date missing/invalid); set to 0")
        entry["age_days"] = 0
    else:
        entry["age_days"] = age

    today = datetime.date.today().isoformat()
    entry["date_added"] = today
    entry["date_updated"] = today

    # Order the object to match the schema for readability.
    ordered_keys = [
        "id", "company", "role", "category", "location", "location_type",
        "internship_term", "application_url", "source_url", "source_type",
        "status", "last_verified_date", "discovered_date", "age_days",
        "tech_keywords", "ai_relevance", "full_stack_relevance", "student_level",
        "freshman_sophomore_friendly", "requires_us_citizenship", "sponsorship_note",
        "work_authorization_note", "evidence_notes", "fit_summary", "risk_flags",
        "date_added", "date_updated",
    ]
    ordered = {k: entry.get(k) for k in ordered_keys}

    # Emit warnings/errors to stderr so stdout stays clean JSON.
    for w in warnings:
        print("WARNING: %s" % w, file=sys.stderr)
    for e in errors:
        print("ERROR: %s" % e, file=sys.stderr)

    if errors:
        print("Conversion failed: fix the issues above before appending.", file=sys.stderr)
        return 2

    print(json.dumps(ordered, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
