#!/usr/bin/env python3
"""Sync the root dataset into the web dashboard's local data folder.

Standard-library only. Does NOT install or require any third-party package.

Source of truth (never modified):
    data/internships.json
Destination (generated copy, safe to overwrite):
    web/src/data/internships.json

The copy lets the Next.js app import the dataset from inside web/ without
reaching outside its own tree. The root dataset remains the single source of
truth; re-run this script whenever the root data changes.

Exit code:
    0  -> synced successfully
    1  -> source missing / invalid JSON / write error
"""

import json
import os
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SOURCE = os.path.join(PROJECT_ROOT, "data", "internships.json")
DEST = os.path.join(PROJECT_ROOT, "web", "src", "data", "internships.json")


def main():
    print("InternRadar AI - sync web data")
    print("Source: %s" % SOURCE)
    print("Dest:   %s" % DEST)

    if not os.path.exists(SOURCE):
        print("ERROR: source dataset not found.", file=sys.stderr)
        return 1

    # Validate the source is well-formed JSON (a list) before copying.
    try:
        with open(SOURCE, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except ValueError as exc:
        print("ERROR: source is not valid JSON: %s" % exc, file=sys.stderr)
        return 1
    if not isinstance(data, list):
        print("ERROR: source JSON must be an array of entries.", file=sys.stderr)
        return 1

    # Ensure destination directory exists.
    dest_dir = os.path.dirname(DEST)
    try:
        os.makedirs(dest_dir, exist_ok=True)
    except OSError as exc:
        print("ERROR: could not create destination directory: %s" % exc, file=sys.stderr)
        return 1

    # Copy (overwrite) the destination. Source is never modified.
    try:
        shutil.copyfile(SOURCE, DEST)
    except OSError as exc:
        print("ERROR: copy failed: %s" % exc, file=sys.stderr)
        return 1

    print("Synced %d entr%s." % (len(data), "y" if len(data) == 1 else "ies"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
