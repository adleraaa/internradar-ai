#!/usr/bin/env python3
"""One-command local quality gate for InternRadar AI.

Standard-library only. Does NOT install or require any third-party package.

Runs, in order, stopping on the first failure:
  1. scripts/validate_data.py        (schema/field validation)
  2. scripts/audit_data_quality.py   (local-only quality audit)
  3. scripts/auto_update_policy_test.py (auto-promotion policy logic tests)
  4. scripts/generate_readme_table.py(refresh README table + table doc)
  5. scripts/generate_status_report.py (refresh status report)
  6. scripts/sync_web_data.py        (copy root data -> web/src/data)
  7. npm run build --prefix web      (only if web/package.json exists and npm
                                      is available; otherwise SKIPPED)

This script never edits data/internships.json directly. Steps 4-6 only write
GENERATED artifacts (README table section, docs, and the web data copy) from the
root dataset, which remains the single source of truth.

Exit code:
    0  -> all (non-skipped) checks passed
    1  -> a check failed (stops at the first failure)
"""

import os
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
WEB_PACKAGE_JSON = os.path.join(WEB_DIR, "package.json")


def header(title):
    line = "=" * 70
    print("\n" + line)
    print(title)
    print(line, flush=True)


def run_python(script_name):
    """Run a project Python script with the current interpreter."""
    path = os.path.join(SCRIPT_DIR, script_name)
    return subprocess.run([sys.executable, path], cwd=PROJECT_ROOT).returncode


def find_npm():
    """Locate npm (npm / npm.cmd) on PATH; return the executable or None."""
    for name in ("npm", "npm.cmd"):
        found = shutil.which(name)
        if found:
            return found
    return None


def main():
    steps = [
        ("1/7  Validate data", lambda: run_python("validate_data.py")),
        ("2/7  Audit data quality", lambda: run_python("audit_data_quality.py")),
        ("3/7  Auto-promotion policy tests", lambda: run_python("auto_update_policy_test.py")),
        ("4/7  Generate README table", lambda: run_python("generate_readme_table.py")),
        ("5/7  Generate status report", lambda: run_python("generate_status_report.py")),
        ("6/7  Sync web data", lambda: run_python("sync_web_data.py")),
    ]

    completed = []
    for title, fn in steps:
        header(title)
        code = fn()
        if code != 0:
            print("\nFAILED at: %s (exit %d). Stopping." % (title, code), file=sys.stderr)
            return 1
        completed.append(title)

    # Step 7: web build (conditional).
    header("7/7  Build web dashboard")
    build_status = "skipped"
    if not os.path.exists(WEB_PACKAGE_JSON):
        print("SKIPPED: web/package.json not found.")
    else:
        npm = find_npm()
        if not npm:
            print("SKIPPED: npm not found on PATH.")
        else:
            print("Running: %s run build --prefix web" % npm, flush=True)
            code = subprocess.run(
                [npm, "run", "build", "--prefix", WEB_DIR], cwd=PROJECT_ROOT
            ).returncode
            if code != 0:
                print("\nFAILED at: web build (exit %d). Stopping." % code, file=sys.stderr)
                return 1
            build_status = "passed"

    header("ALL CHECKS PASSED")
    for title in completed:
        print("  [OK] %s" % title)
    print("  [%s] 7/7  Build web dashboard" %
          ("OK" if build_status == "passed" else "--"))
    if build_status != "passed":
        print("\nNote: the web build was %s; run it manually if needed." % build_status)
    print("\nReminder: data/internships.json is the single source of truth; "
          "generated docs and the web data copy are derived from it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
