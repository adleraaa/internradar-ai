#!/usr/bin/env python3
"""Fully automated, conservative verified-internship update pipeline.

Standard-library only. Orchestrates discovery -> verification -> gated
auto-promotion -> regeneration -> validation/audit/build -> optional commit/push.

This is NOT a blind scraper. It auto-promotes ONLY candidates whose official,
human-facing application page is verified reachable, specific, open, technical,
and parseable (verification_confidence >= threshold AND no hard blocker). If no
candidate clears the bar, it promotes 0 entries. It never guesses compensation,
citizenship, sponsorship, or student level (Unclear is recorded when silent), and
never uses private/login-gated boards or third-party salary sources.

Usage (dry-run by default):
    python scripts/auto_update_verified.py --limit 20
Full auto:
    python scripts/auto_update_verified.py --limit 50 --max-promote 5 \
        --min-confidence 90 --apply --commit --push

Exit code:
    0  -> ran successfully (0 promotions is success)
    1  -> a step failed / an invariant was violated (no commit performed)
    2  -> usage error
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
TMP = ROOT / "tmp"
DATA = ROOT / "data" / "internships.json"
SCHEMA = ROOT / "data" / "schema.json"
WEB_DATA = ROOT / "web" / "src" / "data" / "internships.json"
README = ROOT / "README.md"
VERIFIED_JSON = TMP / "candidates_verified.json"
REVERIFY_RESULTS = TMP / "reverification_results.json"

START = "<!-- INTERNSHIPS_TABLE_START -->"
END = "<!-- INTERNSHIPS_TABLE_END -->"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def run_py(script, *args, capture=False):
    cmd = [sys.executable, str(SCRIPTS / script), *args]
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=capture, text=True)


def run_npm_build():
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        return None  # npm unavailable -> treated as skipped
    return subprocess.run([npm, "run", "build", "--prefix", str(ROOT / "web")],
                          cwd=str(ROOT))


def git(*args, capture=True):
    return subprocess.run(["git", *args], cwd=str(ROOT), capture_output=capture, text=True)


def url_key(url):
    import re
    u = (url or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.split("#", 1)[0].split("?", 1)[0].rstrip("/")


def load_dataset():
    return json.loads(DATA.read_text(encoding="utf-8-sig"))


def count_removed(applied, max_remove):
    """How many postings the prune step actually removed this run.

    In apply mode the reverify step removes up to --max-remove deterministic
    failures; in dry-run it removes none. Reads tmp/reverification_results.json.
    """
    try:
        results = json.loads(REVERIFY_RESULTS.read_text(encoding="utf-8"))
    except Exception:
        return 0
    deterministic = sum(1 for r in results if r.get("action") == "remove")
    if not applied:
        return 0
    return min(deterministic, max_remove)


def snapshot():
    data = load_dataset()
    return {
        "count": len(data),
        "url_keys": {url_key(e.get("application_url", "")) for e in data},
        "by_id": {e.get("id"): json.dumps(e, sort_keys=True, ensure_ascii=False)
                  for e in data},
        "hash": hashlib.sha256(DATA.read_bytes()).hexdigest(),
    }


# --------------------------------------------------------------------------- #
# promotion
# --------------------------------------------------------------------------- #
def promote_one(draft_path):
    """Convert one draft to JSON and append it. Returns (ok, entry_or_None)."""
    conv = run_py("submission_to_json.py", draft_path, capture=True)
    if conv.returncode != 0:
        sys.stderr.write(conv.stderr)
        return False, None
    try:
        entry = json.loads(conv.stdout)
    except ValueError:
        return False, None
    TMP.mkdir(exist_ok=True)
    tmp_json = TMP / ("promote_%s.json" % entry.get("id", "entry"))
    tmp_json.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    app = run_py("append_entry.py", str(tmp_json), capture=True)
    sys.stdout.write(app.stdout)
    if app.returncode != 0:
        sys.stderr.write(app.stderr)
        return False, None
    return True, entry


# --------------------------------------------------------------------------- #
# invariants
# --------------------------------------------------------------------------- #
def check_invariants(before, promoted_entries):
    problems = []
    after = load_dataset()
    after_keys = [url_key(e.get("application_url", "")) for e in after]

    if len(after) != before["count"] + len(promoted_entries):
        problems.append("entry count changed unexpectedly (%d -> %d, +%d promoted)"
                        % (before["count"], len(after), len(promoted_entries)))
    # no existing entry removed or modified
    after_by_id = {e.get("id"): json.dumps(e, sort_keys=True, ensure_ascii=False)
                   for e in after}
    for eid, blob in before["by_id"].items():
        if eid not in after_by_id:
            problems.append("existing entry removed: %s" % eid)
        elif after_by_id[eid] != blob:
            problems.append("existing entry modified: %s" % eid)
    # no duplicate application_url
    if len(after_keys) != len(set(after_keys)):
        problems.append("duplicate application_url present after promotion")
    # web data sync matches root
    try:
        if json.loads(WEB_DATA.read_text(encoding="utf-8-sig")) != after:
            problems.append("web/src/data/internships.json does not match root data")
    except Exception as exc:
        problems.append("could not compare web data copy: %s" % exc)
    # README markers intact
    readme = README.read_text(encoding="utf-8-sig")
    if START not in readme or END not in readme:
        problems.append("README internship-table markers missing")
    return problems


# --------------------------------------------------------------------------- #
# commit / push
# --------------------------------------------------------------------------- #
SAFE_PATHS = [
    "data/schema.json", "data/internships.json", "web/src/data/internships.json",
    "docs/internships_table.md", "docs/status_report.md",
    "docs/candidate_review_report.md", "docs/reverification_report.md",
    "README.md", "pending/auto", "reviewed",
    "scripts/auto_update_verified.py", "scripts/auto_update_policy_test.py",
    "scripts/verify_candidates.py", "scripts/check_all.py",
    "scripts/reverify_existing.py", "scripts/reverify_existing_test.py",
    "archive/removed_internships.json", "archive/README.md",
    "docs/automation_policy.md", "docs/maintenance_workflow.md",
]
COMMIT_TITLE = "Auto-update verified internship listings"
COMMIT_BODY = ("- Discover and verify public internship postings\n"
               "- Auto-promote high-confidence official application pages\n"
               "- Regenerate dataset artifacts and dashboard data")


def do_commit():
    existing = [p for p in SAFE_PATHS if (ROOT / p).exists()]
    git("add", *existing, capture=True)
    # Safety: ensure nothing forbidden is staged.
    staged = git("diff", "--cached", "--name-only").stdout.splitlines()
    bad = [s for s in staged if s.startswith("tmp/") or "node_modules" in s
           or s.startswith(".next") or "/.next/" in s or s.endswith(".log")
           or s.endswith(".env") or ".env." in s]
    if bad:
        print("ERROR: refusing to commit forbidden staged paths: %s" % bad, file=sys.stderr)
        return None
    if not staged:
        print("Nothing staged to commit.")
        return None
    res = git("commit", "-m", COMMIT_TITLE, "-m", COMMIT_BODY)
    sys.stdout.write(res.stdout)
    sys.stderr.write(res.stderr)
    if res.returncode != 0:
        return None
    return git("rev-parse", "--short", "HEAD").stdout.strip()


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(argv):
    p = argparse.ArgumentParser(description="Automated verified internship update.")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--max-promote", type=int, default=5)
    p.add_argument("--min-confidence", type=int, default=90)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--commit", action="store_true")
    p.add_argument("--push", action="store_true")
    p.add_argument("--no-build", action="store_true")
    p.add_argument("--keep-tmp", action="store_true")
    p.add_argument("--source", default="simplify", choices=["simplify"])
    p.add_argument("--prune-closed", action="store_true",
                   help="re-verify existing postings first and remove (archive) "
                        "the ones that deterministically fail")
    p.add_argument("--max-remove", type=int, default=5,
                   help="safety cap on removals during --prune-closed (default 5)")
    p.add_argument("--skip-reverify", action="store_true",
                   help="skip the re-verification/prune step even if --prune-closed")
    args = p.parse_args(argv[1:])

    if args.push and not args.commit:
        print("ERROR: --push requires --commit.", file=sys.stderr)
        return 2
    if args.commit and not args.apply:
        print("ERROR: --commit requires --apply.", file=sys.stderr)
        return 2
    if args.max_remove < 0:
        print("ERROR: --max-remove must be >= 0.", file=sys.stderr)
        return 2

    mode = "APPLY" if args.apply else "DRY-RUN"
    print("=" * 64)
    print("Auto-update verified internships  [%s]" % mode)
    print("limit=%d max_promote=%d min_confidence=%d source=%s prune_closed=%s"
          % (args.limit, args.max_promote, args.min_confidence, args.source,
             args.prune_closed))
    print("=" * 64)

    # 0) Re-verify existing postings first (conservative prune of closed roles).
    #    Runs BEFORE discovery. In apply mode it removes (and archives) only
    #    deterministically-failed postings, capped by --max-remove; if it fails
    #    we stop before adding anything new.
    removed_count = 0
    if args.prune_closed and not args.skip_reverify:
        print("\n[0] Re-verify existing postings (prune deterministically-closed)...")
        rv_args = ["--max-remove", str(args.max_remove)]
        if args.apply:
            rv_args.append("--apply")
        if run_py("reverify_existing.py", *rv_args).returncode != 0:
            print("ERROR: re-verification/prune step failed — stopping before "
                  "adding new postings.", file=sys.stderr)
            return 1
        removed_count = count_removed(args.apply, args.max_remove)
        print("   Re-verification done (removed this run: %d)." % removed_count)
    elif args.prune_closed and args.skip_reverify:
        print("\n[0] --prune-closed given but --skip-reverify set; skipping prune.")

    # 1) Discover.
    print("\n[1] Discover candidates...")
    disc_args = ["--keep-tmp"] if args.keep_tmp else []
    if run_py("discover_candidates.py", *disc_args).returncode != 0:
        print("ERROR: discovery failed.", file=sys.stderr)
        return 1

    # 2) Verify.
    print("\n[2] Verify candidates (limit %d)..." % args.limit)
    if run_py("verify_candidates.py", "--limit", str(args.limit)).returncode != 0:
        print("ERROR: verification failed.", file=sys.stderr)
        return 1

    # 3) Select auto-promote-eligible candidates.
    try:
        verified = json.loads(VERIFIED_JSON.read_text(encoding="utf-8"))
    except Exception as exc:
        print("ERROR: could not read %s: %s" % (VERIFIED_JSON, exc), file=sys.stderr)
        return 1

    eligible = [r for r in verified
                if r.get("auto_promote_eligible")
                and r.get("verification_confidence", 0) >= args.min_confidence
                and r.get("draft_file")]
    eligible.sort(key=lambda r: -r.get("verification_confidence", 0))
    chosen = eligible[:args.max_promote]

    raw_n = len(verified)
    skipped = [r for r in verified if not r.get("drafted")]

    print("\n[3] Eligible for auto-promotion: %d (taking up to %d)"
          % (len(eligible), args.max_promote))
    for r in chosen:
        print("   - conf=%3d %s — %s" % (r["verification_confidence"],
                                         r["company"], r["role"]))

    before = snapshot()

    # Dry-run stops here (no dataset changes).
    if not args.apply:
        print("\n[DRY-RUN] No dataset changes. Re-run with --apply to promote.")
        print_report(before, [], eligible, skipped, None, None, None, None, None,
                     removed_count=removed_count)
        return 0

    # 4) Promote (gated).
    print("\n[4] Promoting up to %d candidate(s)..." % args.max_promote)
    promoted = []
    for r in chosen:
        draft = ROOT / r["draft_file"]
        if not draft.is_file():
            print("   skip (draft missing): %s" % r["draft_file"])
            continue
        ok, entry = promote_one(str(draft))
        if not ok:
            print("   STOP: append failed for %s — halting promotions." % r["company"])
            break
        promoted.append({"company": r["company"], "role": r["role"],
                         "compensation_note": entry.get("compensation_note", ""),
                         "id": entry.get("id")})
        print("   promoted: %s — %s" % (r["company"], r["role"]))
        if len(promoted) >= args.max_promote:
            break

    # 5) Regenerate derived artifacts.
    print("\n[5] Regenerating artifacts...")
    for s in ("generate_readme_table.py", "generate_status_report.py", "sync_web_data.py"):
        run_py(s)

    # 6) Validate + audit.
    rc_validate = run_py("validate_data.py", capture=True)
    rc_audit = run_py("audit_data_quality.py", capture=True)
    validate_ok = rc_validate.returncode == 0
    audit_ok = rc_audit.returncode == 0

    # 7) Invariants.
    print("\n[6] Checking invariants...")
    problems = check_invariants(before, promoted)
    if problems:
        print("INVARIANT VIOLATIONS:", file=sys.stderr)
        for pr in problems:
            print("  - %s" % pr, file=sys.stderr)

    # 8) Final gate (check_all incl. build, unless --no-build).
    build_result = "skipped"
    gate_ok = validate_ok and audit_ok
    if args.no_build:
        rc_pol = run_py("auto_update_policy_test.py", capture=True)
        gate_ok = gate_ok and rc_pol.returncode == 0
    else:
        print("\n[7] Running full quality gate (check_all.py)...")
        rc_gate = run_py("check_all.py")
        gate_ok = gate_ok and rc_gate.returncode == 0
        build_result = "passed" if rc_gate.returncode == 0 else "FAILED"

    ok = validate_ok and audit_ok and gate_ok and not problems

    commit_hash = None
    push_result = "not requested"
    if ok and args.commit:
        print("\n[8] Committing...")
        commit_hash = do_commit()
        if commit_hash and args.push:
            print("\n[9] Pushing...")
            res = git("push", capture=True)
            sys.stdout.write(res.stdout)
            sys.stderr.write(res.stderr)
            push_result = "ok" if res.returncode == 0 else "FAILED: %s" % res.stderr.strip()
    elif args.commit and not ok:
        print("\nNOT committing: a check failed or an invariant was violated.",
              file=sys.stderr)

    print_report(before, promoted, eligible, skipped, validate_ok, audit_ok,
                 build_result, commit_hash, push_result if args.push else None,
                 removed_count=removed_count)

    return 0 if ok else 1


def print_report(before, promoted, eligible, skipped, validate_ok, audit_ok,
                 build_result, commit_hash, push_result, removed_count=0):
    after = load_dataset()
    known = sum(1 for e in promoted
                if (e.get("compensation_note") or "").strip().lower() not in ("", "unclear"))
    unclear = len(promoted) - known
    # skip reasons tally
    reasons = {}
    for r in skipped:
        reasons[r.get("skip_reason", "?")] = reasons.get(r.get("skip_reason", "?"), 0) + 1

    try:
        verified_total = len(json.loads(VERIFIED_JSON.read_text(encoding="utf-8")))
    except Exception:
        verified_total = len(skipped) + len(eligible)

    print("\n" + "=" * 64)
    print("AUTO-UPDATE REPORT")
    print("=" * 64)
    print("Candidates verified:        %d" % verified_total)
    print("Eligible for auto-promote:  %d" % len(eligible))
    print("Promoted this run:          %d" % len(promoted))
    for e in promoted:
        print("   - %s — %s (%s)" % (e["company"], e["role"],
                                     e.get("compensation_note", "")))
    print("Skipped (not drafted):      %d" % len(skipped))
    for reason, n in sorted(reasons.items(), key=lambda kv: -kv[1])[:8]:
        print("   - %dx %s" % (n, reason))
    print("Promoted compensation:      %d known / %d unclear" % (known, unclear))
    print("Removed (prune, this run):  %d" % removed_count)
    print("Dataset entries before:     %d (after any prune, before promotion)"
          % before["count"])
    print("Dataset entries after:      %d" % len(after))
    if validate_ok is not None:
        print("Validation:                 %s" % ("PASSED" if validate_ok else "FAILED"))
        print("Audit:                      %s" % ("PASSED" if audit_ok else "FAILED"))
        print("Build / check_all:          %s" % build_result)
    if commit_hash:
        print("Commit:                     %s" % commit_hash)
    if push_result is not None:
        print("Push:                       %s" % push_result)
    gs = git("status", "--short").stdout.strip()
    print("Final git status:           %s" % ("clean" if not gs else "\n" + gs))
    print("=" * 64)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
