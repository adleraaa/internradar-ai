#!/usr/bin/env python3
"""Promote ONE reviewed pending/auto draft into the verified dataset.

Standard-library only. This is the ONLY automation step that may change
data/internships.json, and it requires an explicit draft path argument plus a
human who has reviewed the official application page.

Pipeline:
  1. Read the draft; refuse if classified "Needs manual review" unless
     --allow-needs-review is passed.
  2. Convert the draft to JSON via scripts/submission_to_json.py.
  3. Refuse if status is not Open.
  4. Refuse if application_url already exists in data/internships.json.
  5. Append via scripts/append_entry.py.
  6. Run validate -> audit -> generate table -> generate status report -> sync.
  7. Print next steps (review diff, run check_all.py, commit/push).

Usage:
    python scripts/promote_candidate.py pending/auto/<file>.md [--allow-needs-review]

Exit code:
    0  -> promoted successfully
    1  -> usage/file error
    2  -> refused (review gate / status / duplicate / validation)
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"
DATA_PATH = PROJECT_ROOT / "data" / "internships.json"
TMP_DIR = PROJECT_ROOT / "tmp"

CLASS_RE = re.compile(r"<!--\s*auto-classification:\s*(.*?)\s*-->", re.I)


def url_key(url):
    u = (url or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = u.split("#", 1)[0].split("?", 1)[0]
    return u.rstrip("/")


def run_script(script_name, *args, capture=False):
    cmd = [sys.executable, str(SCRIPTS / script_name), *args]
    return subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=capture, text=True)


def existing_url_keys():
    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
        return {url_key(e.get("application_url", "")) for e in data}
    except Exception:
        return set()


def main(argv):
    parser = argparse.ArgumentParser(description="Promote one reviewed draft.")
    parser.add_argument("draft", help="path to a pending/auto Markdown draft")
    parser.add_argument("--allow-needs-review", action="store_true",
                        help="allow promoting a 'Needs manual review' draft")
    args = parser.parse_args(argv[1:])

    draft = Path(args.draft)
    if not draft.is_file():
        print("ERROR: draft not found: %s" % draft, file=sys.stderr)
        return 1

    text = draft.read_text(encoding="utf-8-sig")

    # Review gate.
    m = CLASS_RE.search(text)
    classification = m.group(1).strip() if m else "Unknown"
    if classification.lower().startswith("needs manual review") and not args.allow_needs_review:
        print("REFUSED: draft is classified 'Needs manual review'.", file=sys.stderr)
        print("Review the official application page, then re-run with "
              "--allow-needs-review.", file=sys.stderr)
        return 2

    # Convert to JSON.
    conv = run_script("submission_to_json.py", str(draft), capture=True)
    if conv.returncode != 0:
        sys.stderr.write(conv.stderr)
        print("REFUSED: draft could not be converted to JSON.", file=sys.stderr)
        return 2
    try:
        entry = json.loads(conv.stdout)
    except ValueError as exc:
        print("ERROR: converter output was not valid JSON: %s" % exc, file=sys.stderr)
        return 2

    # Status gate.
    if entry.get("status") != "Open":
        print("REFUSED: status is %r (must be 'Open' to promote)."
              % entry.get("status"), file=sys.stderr)
        return 2

    # Compensation completeness gate.
    comp_fields = ("compensation_min", "compensation_max", "compensation_currency",
                   "compensation_period", "compensation_note", "compensation_evidence")
    if any(fld not in entry for fld in comp_fields):
        print("REFUSED: draft is missing compensation fields (%s)."
              % ", ".join(f for f in comp_fields if f not in entry), file=sys.stderr)
        return 2
    if not (entry.get("compensation_note") or "").strip() or \
            not (entry.get("compensation_evidence") or "").strip():
        print("REFUSED: compensation_note / compensation_evidence must be non-empty "
              "(use 'Unclear' and an evidence note).", file=sys.stderr)
        return 2

    # Duplicate gate.
    if url_key(entry.get("application_url", "")) in existing_url_keys():
        print("REFUSED: application_url already exists in data/internships.json.",
              file=sys.stderr)
        return 2

    # Save JSON to tmp and append.
    TMP_DIR.mkdir(exist_ok=True)
    tmp_json = TMP_DIR / ("promote_%s.json" % re.sub(r"[^A-Za-z0-9]+", "_", entry.get("id", "entry")))
    tmp_json.write_text(json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Promoting draft: %s" % draft)
    print("  classification: %s" % classification)
    print("  id: %s" % entry.get("id"))

    append = run_script("append_entry.py", str(tmp_json))
    if append.returncode != 0:
        print("REFUSED: append_entry.py failed (see output above).", file=sys.stderr)
        return 2

    # Refresh derived artifacts.
    print("\nRefreshing validation and generated artifacts...")
    for name in ("validate_data.py", "audit_data_quality.py",
                 "generate_readme_table.py", "generate_status_report.py",
                 "sync_web_data.py"):
        res = run_script(name)
        if res.returncode != 0 and name in ("validate_data.py", "audit_data_quality.py"):
            print("WARNING: %s reported a non-zero exit; review before committing."
                  % name, file=sys.stderr)

    print("\n" + "=" * 60)
    print("Promoted. Next steps (manual):")
    print("  1. Review the change:   git diff")
    print("  2. Run the quality gate: python scripts/check_all.py")
    print("  3. Commit & push:        git add -A && git commit && git push")
    print("  (Optionally move the reviewed draft into reviewed/ as an audit trail.)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
