#!/usr/bin/env python3
"""Create a new Markdown internship submission draft in pending/.

Standard-library only. Does NOT install or require any third-party package.

Interactive CLI: prompts for a handful of core fields, pre-fills the rest with
"Unclear" / empty values / placeholder review notes, and writes a draft named
`YYYY-MM-DD_company_role.md` into the project's pending/ folder.

This script NEVER writes to data/internships.json. It only creates a draft for
later manual review.

Refuses to create the draft if:
  - application_url is blank, or
  - last_verified_date is blank.

Exit code:
    0  -> draft created
    1  -> aborted (missing required input) or error
"""

import datetime
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PENDING_DIR = os.path.join(PROJECT_ROOT, "pending")

# Allowed enum values (kept in sync with data/schema.json) shown as hints.
ENUM_HINTS = {
    "category": "Software Engineering | AI/ML | Data Science | Product | Hardware | Other",
    "location_type": "Remote | Hybrid | Onsite | Multiple | Unclear",
    "source_type": ("Company Career Page | Greenhouse | Lever | Ashby | Workday | "
                    "Simplify | Handshake | LinkedIn | Other"),
    "status": "Open | Closed | Unclear",
}


def prompt(label, hint=None, default=""):
    """Prompt for a single line of input. Returns the stripped string."""
    if hint:
        text = "%s [%s]: " % (label, hint)
    elif default:
        text = "%s (default: %s): " % (label, default)
    else:
        text = "%s: " % label
    try:
        value = input(text)
    except EOFError:
        return default
    value = value.strip()
    return value if value else default


def sanitize_filename_part(text):
    """Make a string safe for use in a filename across platforms."""
    if not text:
        return "unknown"
    # Lowercase, replace any non-alphanumeric run with a single underscore.
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    if not cleaned:
        return "unknown"
    # Keep filenames reasonably short.
    return cleaned[:40]


def main():
    print("=" * 60)
    print("InternRadar AI - new submission draft")
    print("=" * 60)
    print("Fill in the core fields. Leave blank to keep defaults where allowed.")
    print("Required: application_url and last_verified_date (draft refused if blank).")
    print("-" * 60)

    today = datetime.date.today().isoformat()

    company = prompt("Company")
    role = prompt("Role title")
    category = prompt("Category", hint=ENUM_HINTS["category"], default="Other")
    location = prompt("Location")
    location_type = prompt("Location type", hint=ENUM_HINTS["location_type"], default="Unclear")
    internship_term = prompt("Internship term (e.g. Summer 2026)")
    application_url = prompt("Official application URL (REQUIRED)")
    source_url = prompt("Source URL")
    source_type = prompt("Source type", hint=ENUM_HINTS["source_type"], default="Other")
    status = prompt("Status", hint=ENUM_HINTS["status"], default="Unclear")
    last_verified_date = prompt("Last verified date YYYY-MM-DD (REQUIRED)")
    discovered_date = prompt("Discovered date YYYY-MM-DD", default=today)

    print("-" * 60)
    print("Compensation (OFFICIAL PAGE ONLY — never guess or use estimate sites).")
    print("Leave blank if the official page does not list pay.")
    comp_min = prompt("Compensation min (number, blank if not listed)")
    comp_max = prompt("Compensation max (number, blank if not listed)")
    comp_currency = prompt("Compensation currency",
                           hint="USD | Other | Unclear", default="Unclear")
    comp_period = prompt("Compensation period",
                         hint="Hour | Month | Year | Stipend | Unpaid | Other | Unclear",
                         default="Unclear")
    comp_note = prompt("Compensation note (e.g. $25/hr)", default="Unclear")
    comp_evidence = prompt(
        "Compensation evidence",
        default="No compensation information found on the official application page.")

    # Hard refusals.
    if not application_url:
        print("\nERROR: application_url is blank. Refusing to create a draft.", file=sys.stderr)
        print("Every entry must have a concrete official application link.", file=sys.stderr)
        return 1
    if not last_verified_date:
        print("\nERROR: last_verified_date is blank. Refusing to create a draft.", file=sys.stderr)
        print("You must record the date you verified the official page.", file=sys.stderr)
        return 1

    # Fallbacks for display-only fields.
    company_display = company if company else "Unknown Company"
    role_display = role if role else "Unknown Role"

    draft = build_draft(
        company=company_display,
        role=role_display,
        category=category or "Other",
        location=location,
        location_type=location_type or "Unclear",
        internship_term=internship_term,
        application_url=application_url,
        source_url=source_url,
        source_type=source_type or "Other",
        status=status or "Unclear",
        last_verified_date=last_verified_date,
        discovered_date=discovered_date or today,
        compensation_min=comp_min,
        compensation_max=comp_max,
        compensation_currency=comp_currency or "Unclear",
        compensation_period=comp_period or "Unclear",
        compensation_note=comp_note or "Unclear",
        compensation_evidence=(comp_evidence or
                               "No compensation information found on the official application page."),
    )

    # Build a safe filename: YYYY-MM-DD_company_role.md
    date_part = discovered_date if re.match(r"^\d{4}-\d{2}-\d{2}$", discovered_date or "") else today
    filename = "%s_%s_%s.md" % (
        date_part,
        sanitize_filename_part(company),
        sanitize_filename_part(role),
    )
    out_path = os.path.join(PENDING_DIR, filename)

    if not os.path.isdir(PENDING_DIR):
        os.makedirs(PENDING_DIR)

    if os.path.exists(out_path):
        print("\nERROR: a draft already exists at:\n  %s" % out_path, file=sys.stderr)
        print("Refusing to overwrite it. Rename or remove it first.", file=sys.stderr)
        return 1

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(draft)

    print("-" * 60)
    print("Draft created:")
    print("  %s" % out_path)
    print("\nNext steps:")
    print("  1. Manually review the official application page.")
    print("  2. Fill in the remaining fields in the draft (do NOT paste full JDs).")
    print("  3. Convert: python scripts/submission_to_json.py %s"
          % os.path.join("pending", filename))
    print("  4. Append:  python scripts/append_entry.py <json-file>")
    print("  5. Validate: python scripts/validate_data.py")
    return 0


def build_draft(company, role, category, location, location_type, internship_term,
                application_url, source_url, source_type, status,
                last_verified_date, discovered_date,
                compensation_min="", compensation_max="",
                compensation_currency="Unclear", compensation_period="Unclear",
                compensation_note="Unclear",
                compensation_evidence="No compensation information found on the official application page."):
    """Return the Markdown draft text. Fields not prompted are pre-filled."""
    return """# Internship Submission

Draft created by scripts/new_submission.py. Review against the official
application page before converting to JSON. Do NOT paste full job descriptions;
quote only short evidence snippets. If uncertain, mark fields "Unclear".

## Core fields

- **company:** {company}
- **role:** {role}
- **category:** {category}
- **location:** {location}
- **location_type:** {location_type}
- **internship_term:** {internship_term}

## Links & source

- **application_url:** {application_url}
- **source_url:** {source_url}
- **source_type:** {source_type}

## Status & freshness

- **status:** {status}
- **last_verified_date:** {last_verified_date}
- **discovered_date:** {discovered_date}

## Classification (evidence-based only)

- **tech_keywords:**
- **ai_relevance:** Unclear
- **full_stack_relevance:** Unclear
- **student_level:** Unclear
- **freshman_sophomore_friendly:** Unclear

## Work authorization (cite evidence for any definite claim)

- **requires_us_citizenship:** Unclear
- **sponsorship_note:**
- **work_authorization_note:**

## Compensation (OFFICIAL PAGE ONLY — never guess or use estimate sites)

- **compensation_min:** {compensation_min}
- **compensation_max:** {compensation_max}
- **compensation_currency:** {compensation_currency}
- **compensation_period:** {compensation_period}
- **compensation_note:** {compensation_note}
- **compensation_evidence:** {compensation_evidence}

## Notes & summary (your own words - never copied JD text)

- **evidence_notes:**
- **fit_summary:**
- **risk_flags:**

---

## Reviewer checklist

- [ ] application_url is a concrete, human-facing official application link.
- [ ] last_verified_date is filled, in YYYY-MM-DD, and not in the future.
- [ ] status reflects what was actually observed on the official page.
- [ ] status: Open only set because the page is reachable and accepting applications.
- [ ] Every citizenship / sponsorship / work-authorization claim has matching evidence_notes.
- [ ] requires_us_citizenship: No is backed by real evidence (not optimism).
- [ ] No full job description text was pasted; only short evidence snippets.
- [ ] All enum fields use exact allowed values (or Unclear).
- [ ] After converting to JSON, python scripts/validate_data.py passes.

<!-- REVIEW NOTE: This is an UNREVIEWED draft. Fill remaining fields and verify
     every claim against the official posting before converting to JSON. -->
""".format(
        company=company,
        role=role,
        category=category,
        location=location,
        location_type=location_type,
        internship_term=internship_term,
        application_url=application_url,
        source_url=source_url,
        source_type=source_type,
        status=status,
        last_verified_date=last_verified_date,
        discovered_date=discovered_date,
        compensation_min=compensation_min,
        compensation_max=compensation_max,
        compensation_currency=compensation_currency,
        compensation_period=compensation_period,
        compensation_note=compensation_note,
        compensation_evidence=compensation_evidence,
    )


if __name__ == "__main__":
    sys.exit(main())
