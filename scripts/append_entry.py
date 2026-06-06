#!/usr/bin/env python3
"""Append one internship JSON object to data/internships.json after checks.

Standard-library only. Does NOT install or require any third-party package.

Usage:
    python scripts/append_entry.py <path-to-entry.json>

The input file must contain a single JSON object (one internship entry), e.g.
the output of scripts/submission_to_json.py saved to a temporary local file.

Checks before appending:
  - Refuses entries without a non-empty application_url.
  - Refuses entries without a non-empty last_verified_date.
  - Refuses duplicate ids (id already present in data/internships.json).
  - Validates required enum fields against data/schema.json.

On success:
  - Appends the entry.
  - Sorts entries by last_verified_date (descending), then company (ascending).
  - Writes data/internships.json with pretty (indent=2) formatting.
  - Recommends running scripts/validate_data.py afterward.

Exit code:
    0  -> appended successfully
    1  -> usage / file error
    2  -> validation failure (nothing written)
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "internships.json")
SCHEMA_PATH = os.path.join(PROJECT_ROOT, "data", "schema.json")

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


def load_json(path):
    # utf-8-sig tolerates a leading BOM that Windows editors may add.
    with open(path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def load_enums():
    try:
        schema = load_json(SCHEMA_PATH)
        props = schema.get("items", {}).get("properties", {})
        enums = {}
        for field, spec in props.items():
            if isinstance(spec, dict) and "enum" in spec:
                enums[field] = list(spec["enum"])
        merged = dict(FALLBACK_ENUMS)
        merged.update(enums)
        return merged
    except Exception:
        return dict(FALLBACK_ENUMS)


def main(argv):
    if len(argv) != 2:
        print("Usage: python scripts/append_entry.py <path-to-entry.json>",
              file=sys.stderr)
        print("Append one internship JSON object to data/internships.json after checks.",
              file=sys.stderr)
        return 1

    entry_path = argv[1]
    if not os.path.isfile(entry_path):
        print("ERROR: file not found: %s" % entry_path, file=sys.stderr)
        return 1

    # Load the candidate entry.
    try:
        entry = load_json(entry_path)
    except ValueError as exc:
        print("ERROR: input file is not valid JSON: %s" % exc, file=sys.stderr)
        return 1

    if isinstance(entry, list):
        print("ERROR: input must be a single JSON object, not an array.", file=sys.stderr)
        return 2
    if not isinstance(entry, dict):
        print("ERROR: input must be a single JSON object.", file=sys.stderr)
        return 2

    errors = []

    # Required link / date checks.
    app_url = entry.get("application_url")
    if not (isinstance(app_url, str) and app_url.strip()):
        errors.append("entry is missing a non-empty 'application_url'.")

    lvd = entry.get("last_verified_date")
    if not (isinstance(lvd, str) and lvd.strip()):
        errors.append("entry is missing a non-empty 'last_verified_date'.")

    entry_id = entry.get("id")
    if not (isinstance(entry_id, str) and entry_id.strip()):
        errors.append("entry is missing a non-empty 'id'.")

    # Compensation fields must all be present.
    for field in ("compensation_min", "compensation_max", "compensation_currency",
                  "compensation_period", "compensation_note", "compensation_evidence"):
        if field not in entry:
            errors.append("entry is missing compensation field '%s'." % field)
    for field in ("compensation_note", "compensation_evidence"):
        val = entry.get(field)
        if field in entry and not (isinstance(val, str) and val.strip()):
            errors.append("entry has empty '%s' (use 'Unclear' / an evidence note)." % field)
    for field in ("compensation_min", "compensation_max"):
        val = entry.get(field, None)
        if field in entry and not (val is None or
                                   (isinstance(val, (int, float)) and not isinstance(val, bool))):
            errors.append("entry '%s' must be a number or null (got %r)." % (field, val))
    cmin, cmax = entry.get("compensation_min"), entry.get("compensation_max")
    if isinstance(cmin, (int, float)) and not isinstance(cmin, bool) \
            and isinstance(cmax, (int, float)) and not isinstance(cmax, bool) and cmin > cmax:
        errors.append("compensation_min (%s) > compensation_max (%s)." % (cmin, cmax))

    # Enum validation.
    enums = load_enums()
    for field, allowed in enums.items():
        val = entry.get(field)
        if val is not None and val not in allowed:
            errors.append("field '%s' has invalid value %r (allowed: %s)."
                          % (field, val, ", ".join(allowed)))

    # Load existing dataset.
    if not os.path.exists(DATA_PATH):
        print("ERROR: dataset not found: %s" % DATA_PATH, file=sys.stderr)
        return 1
    try:
        data = load_json(DATA_PATH)
    except ValueError as exc:
        print("ERROR: dataset is not valid JSON: %s" % exc, file=sys.stderr)
        return 1
    if not isinstance(data, list):
        print("ERROR: dataset top-level must be a JSON array.", file=sys.stderr)
        return 1

    # Duplicate id check.
    if isinstance(entry_id, str) and entry_id.strip():
        existing_ids = {e.get("id") for e in data if isinstance(e, dict)}
        if entry_id in existing_ids:
            errors.append("duplicate id '%s' already exists in the dataset." % entry_id)

    if errors:
        print("Refusing to append. Problems found:", file=sys.stderr)
        for e in errors:
            print("  - %s" % e, file=sys.stderr)
        return 2

    # Append and sort.
    data.append(entry)
    data.sort(key=lambda e: (
        _neg_date_key(e.get("last_verified_date", "")),
        (e.get("company", "") or "").lower(),
    ))

    # Write back with pretty formatting + trailing newline.
    with open(DATA_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("Appended entry id '%s'." % entry_id)
    print("Dataset now contains %d entr%s."
          % (len(data), "y" if len(data) == 1 else "ies"))
    print("Sorted by last_verified_date (desc), then company (asc).")
    print("\nNext: run the validator to confirm integrity:")
    print("  python scripts/validate_data.py")
    return 0


def _neg_date_key(date_str):
    """Sort key that puts later dates first (descending) using a string trick.

    For YYYY-MM-DD strings, mapping each character to its inverse keeps lexical
    order reversed without parsing. Non-conforming values sort last.
    """
    if not isinstance(date_str, str) or not date_str:
        return (1, "")  # empty/invalid -> after valid dates
    # Tuple: valid dates (0) before invalid (1); within valid, reverse-sorted.
    inverted = "".join(chr(255 - ord(c)) for c in date_str)
    return (0, inverted)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
