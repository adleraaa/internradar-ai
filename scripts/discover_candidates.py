#!/usr/bin/env python3
"""Discover internship CANDIDATES from allowed public sources.

Standard-library only (urllib, json, re, datetime, pathlib). No third-party
packages, no browser automation, no login-gated scraping.

This script ONLY produces normalized candidate records for later verification.
It does NOT verify pages and does NOT touch data/internships.json.

Allowed source (initial):
  - SimplifyJobs / Summer2026-Internships public listings JSON.

Outputs (under tmp/):
  - tmp/candidates_raw.json       normalized intern-titled records considered
  - tmp/candidates_filtered.json  records that passed all discovery filters

The large downloaded source file is removed after the run unless --keep-tmp.

Usage:
    python scripts/discover_candidates.py [--keep-tmp]

Exit code:
    0  -> ran successfully
    1  -> could not fetch / parse the source
"""

import argparse
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "internships.json"
TMP_DIR = PROJECT_ROOT / "tmp"

SOURCE_URL = ("https://raw.githubusercontent.com/SimplifyJobs/"
              "Summer2026-Internships/dev/.github/scripts/listings.json")
SOURCE_REPO = "https://github.com/SimplifyJobs/Summer2026-Internships"
SOURCE_DOWNLOAD = "candidates_source.json"  # large; removed unless --keep-tmp

INTERN_RE = re.compile(r"\b(intern|internship|co-?op)\b", re.I)

# Title/category signals that the role is CS / software / AI / data technical.
RELEVANT_TITLE_RE = re.compile(
    r"software|engineer|developer|full[\s-]?stack|front[\s-]?end|back[\s-]?end|"
    r"machine learning|deep learning|artificial intelligence|\bai\b|\bml\b|"
    r"data scien|data engineer|platform|infrastructure|\bsde\b|\bswe\b|"
    r"applied scien|web develop",
    re.I,
)
RELEVANT_CATEGORIES = {"software", "data science", "ai/ml", "data", "data engineering"}

# Title signals that disqualify (unless clearly software).
REJECT_TITLE_RE = re.compile(
    r"new grad|new graduate|\bsenior\b|\bstaff\b|\bprincipal\b|manager|director|"
    r"\bsales\b|recruit|mechanical|chemical|geolog|civil eng|biolog|accounting|"
    r"marketing|finance",
    re.I,
)
SOFTWARE_OVERRIDE_RE = re.compile(r"software|\bswe\b|\bsde\b|developer", re.I)

# Hosts that are public ATS / official-application pages we accept for discovery.
ATS_HOST_HINTS = (
    "greenhouse.io", "lever.co", "ashbyhq.com", "myworkdayjobs.com",
    "workday", "icims.com",
)
# Login-gated / private boards and aggregators we reject outright.
BANNED_HOST_HINTS = (
    "linkedin.com", "indeed.com", "joinhandshake", "handshake", "glassdoor",
    "ziprecruiter", "simplify.jobs",
)
SEARCH_HINT_RE = re.compile(r"(/search|[?&](q|query|keyword|search)=)", re.I)
HOMEPAGE_PATH_RE = re.compile(r"^/?(careers?|jobs|join-?us|opportunities)/?$", re.I)


def url_key(url):
    """Normalize a URL for duplicate comparison."""
    u = (url or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = u.split("#", 1)[0].split("?", 1)[0]
    return u.rstrip("/")


def host_of(url):
    m = re.match(r"^https?://([^/]+)", (url or "").strip(), re.I)
    return (m.group(1).lower() if m else "")


def path_of(url):
    m = re.match(r"^https?://[^/]+(/[^?#]*)", (url or "").strip(), re.I)
    return (m.group(1) if m else "")


def looks_like_ats(url):
    host = host_of(url)
    return any(h in host or h in url.lower() for h in ATS_HOST_HINTS)


def link_problem(url):
    """Return a reason string if the URL is not an acceptable candidate link."""
    if not url or not url.strip():
        return "missing application_url"
    low = url.strip().lower()
    host = host_of(url)
    if any(b in host or b in low for b in BANNED_HOST_HINTS):
        return "login-gated / aggregator / Simplify redirect link"
    if SEARCH_HINT_RE.search(url):
        return "job-search/query page, not a specific role"
    path = path_of(url)
    if HOMEPAGE_PATH_RE.match(path) or path in ("", "/"):
        return "generic careers/jobs homepage, not a specific role"
    # Accept known ATS hosts, or any other host that has a specific-looking path
    # (a job id segment of digits or a uuid). verify_candidates does the real check.
    if looks_like_ats(url):
        return None
    if re.search(r"/[0-9]{4,}", path) or re.search(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-", path, re.I):
        return None
    return "not a recognizable official/ATS application page"


def is_relevant(title, category):
    t = title or ""
    cat = (category or "").strip().lower()
    relevant = bool(RELEVANT_TITLE_RE.search(t)) or cat in RELEVANT_CATEGORIES
    if not relevant:
        return False
    if REJECT_TITLE_RE.search(t) and not SOFTWARE_OVERRIDE_RE.search(t):
        return False
    if re.search(r"hardware", t, re.I) and not SOFTWARE_OVERRIDE_RE.search(t):
        return False
    return True


def normalize(record):
    """Map a source record to our candidate shape."""
    return {
        "company": (record.get("company_name") or "").strip(),
        "title": (record.get("title") or "").strip(),
        "url": (record.get("url") or "").strip(),
        "source_repo": SOURCE_REPO,
        "source_category": (record.get("category") or "").strip(),
        "locations": record.get("locations") or [],
        "terms": record.get("terms") or [],
        "sponsorship": (record.get("sponsorship") or "").strip(),
        "degrees": record.get("degrees") or [],
        "active": bool(record.get("active")),
        "is_visible": bool(record.get("is_visible", True)),
    }


def fetch_source(dest_path):
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    dest_path.write_bytes(data)
    return json.loads(data.decode("utf-8"))


def load_existing_url_keys():
    try:
        with open(DATA_PATH, "r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
        return {url_key(e.get("application_url", "")) for e in data}
    except Exception:
        return set()


def main(argv):
    parser = argparse.ArgumentParser(description="Discover internship candidates.")
    parser.add_argument("--keep-tmp", action="store_true",
                        help="keep the large downloaded source file in tmp/")
    args = parser.parse_args(argv[1:])

    TMP_DIR.mkdir(exist_ok=True)
    source_file = TMP_DIR / SOURCE_DOWNLOAD

    print("Discovering candidates from: %s" % SOURCE_URL)
    try:
        records = fetch_source(source_file)
    except Exception as exc:
        print("ERROR: could not fetch/parse source: %s" % exc, file=sys.stderr)
        return 1
    if not isinstance(records, list):
        print("ERROR: source JSON is not a list.", file=sys.stderr)
        return 1

    existing = load_existing_url_keys()

    raw = []           # intern-titled, considered candidates (normalized)
    filtered = []      # passed all filters
    skipped_dup = 0
    skipped_irrelevant = 0
    skipped_badlink = 0

    for rec in records:
        title = (rec.get("title") or "")
        if not INTERN_RE.search(title):
            continue  # not an internship-style posting; not a "candidate" at all
        cand = normalize(rec)
        raw.append(cand)

        # Active / visible per source.
        if not (cand["active"] and cand["is_visible"]):
            skipped_irrelevant += 1
            continue
        # Relevance.
        if not is_relevant(cand["title"], cand["source_category"]):
            skipped_irrelevant += 1
            continue
        # Link quality.
        if link_problem(cand["url"]):
            skipped_badlink += 1
            continue
        # Duplicate vs the verified dataset.
        if url_key(cand["url"]) in existing:
            skipped_dup += 1
            continue
        filtered.append(cand)

    (TMP_DIR / "candidates_raw.json").write_text(
        json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    (TMP_DIR / "candidates_filtered.json").write_text(
        json.dumps(filtered, indent=2, ensure_ascii=False), encoding="utf-8")

    if not args.keep_tmp:
        try:
            source_file.unlink()
        except OSError:
            pass

    print("-" * 60)
    print("Raw candidates (intern-titled):  %d" % len(raw))
    print("Filtered candidates (kept):      %d" % len(filtered))
    print("Skipped duplicates:              %d" % skipped_dup)
    print("Skipped irrelevant/inactive:     %d" % skipped_irrelevant)
    print("Skipped bad links:               %d" % skipped_badlink)
    print("-" * 60)
    print("Wrote tmp/candidates_raw.json and tmp/candidates_filtered.json")
    print("Next: python scripts/verify_candidates.py --limit 10")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
