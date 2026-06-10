#!/usr/bin/env python3
"""Re-verify existing active internship entries against their official pages.

Standard-library only (urllib, json, re, datetime, pathlib). No browser
automation, no third-party salary sources, no guessing.

For every entry in data/internships.json this script fetches the stored
`application_url` over plain HTTP and classifies the result as one of:

  * keep   - the official page is reachable (HTTP 200), still shows the role and
             an apply flow. The posting stays. With --refresh-verified (apply
             mode only) its last_verified_date/date_updated are bumped to today.
  * warn   - could NOT be confirmed for a NON-deterministic reason (timeout, DNS
             failure, 429, 5xx, an ambiguous parse, a JS-heavy page, or any other
             transient/uncertain signal). The posting STAYS. Never removed.
  * remove - the page deterministically failed re-verification: HTTP 404/410, an
             explicit closed/filled/expired banner, the final URL is now a
             private/login-gated board / generic careers homepage / search page /
             raw API endpoint, or the role title is gone AND there is no apply
             flow. Only these cause removal.

CONSERVATIVE REMOVAL IS THE WHOLE POINT: a posting is removed only on a
deterministic failure, never on a transient error or ambiguity. Every removed
entry is archived to archive/removed_internships.json (full previous entry +
evidence) BEFORE it leaves the dataset.

Default mode is DRY-RUN: nothing in data/ or archive/ is mutated; the script only
reports what it *would* do. Pass --apply to actually remove (and archive) the
deterministically-failed postings.

Outputs (always, even in dry-run):
  tmp/reverification_results.json   machine-readable per-entry results
  docs/reverification_report.md     human-readable report

Usage:
    python scripts/reverify_existing.py                       # dry-run
    python scripts/reverify_existing.py --apply --max-remove 5
    python scripts/reverify_existing.py --apply --refresh-verified

Exit code:
    0  -> ran successfully (0 removals is success)
    1  -> a step failed / over the removal limit with --fail-on-remove-over-limit
    2  -> usage error / dataset unreadable
"""

import argparse
import html as html_mod
import json
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"
DATA_PATH = PROJECT_ROOT / "data" / "internships.json"
WEB_DATA = PROJECT_ROOT / "web" / "src" / "data" / "internships.json"
ARCHIVE_PATH = PROJECT_ROOT / "archive" / "removed_internships.json"
TMP_DIR = PROJECT_ROOT / "tmp"
RESULTS_PATH = TMP_DIR / "reverification_results.json"
DEFAULT_REPORT = PROJECT_ROOT / "docs" / "reverification_report.md"

TODAY = date.today().isoformat()
FETCH_TIMEOUT = 25
MAX_BYTES = 800_000

# --------------------------------------------------------------------------- #
# Deterministic "this posting is closed" page-text signals.
# Kept TIGHT on purpose: a false positive here would delete a live posting, so
# only unambiguous job-closure phrasing counts. Generic words ("closed",
# "expired") alone are NOT enough; they must be in a job-closure phrase.
# --------------------------------------------------------------------------- #
CLOSED_PAGE_RE = re.compile(
    r"no longer (?:available|accepting applications|active|open|being accepted)|"
    r"this (?:job|position|posting|role|opening|requisition) (?:is |has been )?"
    r"(?:closed|filled|expired|no longer)|"
    r"(?:position|role|opening) (?:has been |is )?filled|"
    r"applications? (?:for this (?:role|job|position) )?(?:are |is )?(?:now )?closed|"
    r"we are no longer accepting applications|"
    r"this (?:job|posting|position) (?:has )?expired|"
    r"job (?:posting )?(?:has )?(?:been )?(?:closed|removed|expired)|"
    r"posting (?:has )?(?:been )?(?:closed|removed|expired)|"
    r"this opening (?:has been|is) (?:filled|closed)",
    re.I,
)

# Final-URL hosts that are private / login-gated / aggregator and never allowed
# as a real, specific official posting. (Mirrors verify_candidates.py.)
_BANNED_HOST = ("linkedin.com", "indeed.com", "joinhandshake", "handshake",
                "glassdoor", "ziprecruiter", "simplify.jobs")
_SEARCH_RE = re.compile(r"/search|[?&](q|query|keyword|search)=", re.I)
_HOMEPAGE_RE = re.compile(r"^/?(careers?|jobs|join-?us|opportunities)/?$", re.I)


def url_key(url):
    u = (url or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.split("#", 1)[0].split("?", 1)[0].rstrip("/")


def _host(url):
    m = re.match(r"^https?://([^/]+)", (url or "").strip(), re.I)
    return (m.group(1).lower() if m else "")


def _path(url):
    m = re.match(r"^https?://[^/]+(/[^?#]*)", (url or "").strip(), re.I)
    return (m.group(1) if m else "")


def classify_forbidden(url):
    """Return a short reason if the FINAL URL is a forbidden source, else None.

    Identical policy to verify_candidates.classify_forbidden so the same links
    that could never be promoted are also treated as no-longer-valid here.
    """
    if not url or not url.strip():
        return "missing/broken link"
    low = url.strip().lower()
    host = _host(url)
    if "simplify.jobs" in low:
        return "Simplify redirect as final URL"
    if any(b in host or b in low for b in _BANNED_HOST):
        return "private/login-gated job board"
    if host.startswith("api.") or "-api." in host or "/api/" in low or "boards-api" in host:
        return "raw API URL"
    if _SEARCH_RE.search(url):
        return "job-search/query page"
    path = _path(url)
    if _HOMEPAGE_RE.match(path) or path in ("", "/"):
        return "generic careers/jobs homepage"
    return None


def source_type_of(url):
    u = (url or "").lower()
    if "greenhouse.io" in u:
        return "Greenhouse"
    if "lever.co" in u:
        return "Lever"
    if "ashbyhq.com" in u:
        return "Ashby"
    if "myworkdayjobs.com" in u or "workday" in u:
        return "Workday"
    if "icims.com" in u:
        return "iCIMS"
    return "Company Career Page"


def page_text_of(html_text):
    stripped = re.sub(r"<script[^>]*>.*?</script>", " ", html_text, flags=re.S | re.I)
    stripped = re.sub(r"<style[^>]*>.*?</style>", " ", stripped, flags=re.S | re.I)
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    return re.sub(r"\s+", " ", html_mod.unescape(stripped)).strip()


def title_on_page(role, html_text, text):
    simp = re.sub(r"\(.*?\)", "", role or "")
    simp = re.sub(r"[^a-z0-9 ]", " ", simp.lower())
    words = [w for w in simp.split() if len(w) > 2]
    if not words:
        return False
    low_text = text.lower()
    low_html = html_text.lower()
    phrase = " ".join(words)
    if phrase in low_text or phrase in low_html:
        return True
    uniq = set(words)
    hits = sum(1 for w in uniq if w in low_text or w in low_html)
    return hits >= max(2, int(0.6 * len(uniq)))


def apply_on_page(text, html_text, source_type, url):
    t = text.lower()
    for kw in ("apply for this job", "apply now", "submit application",
               "start application", "apply"):
        if kw in t:
            return True
    if "application" in t:
        return True
    if source_type == "Ashby" and url.lower().endswith("/application"):
        return True
    if "apply" in html_text.lower():
        return True
    return False


# --------------------------------------------------------------------------- #
# fetch
# --------------------------------------------------------------------------- #
def reverify_fetch(url):
    """Fetch a URL. Return a dict with keys:

      status        int HTTP status, or None on a network-level error
      final_url     URL after redirects (or the original on error)
      html          response body (possibly an error page), '' if none
      network_error short error type string for transient failures, else None
    """
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            raw = resp.read(MAX_BYTES)
            status = resp.getcode()
            final_url = resp.geturl()
        return {"status": status, "final_url": final_url,
                "html": raw.decode("utf-8", "replace"), "network_error": None}
    except urllib.error.HTTPError as exc:
        # A real HTTP status (404/410/403/5xx/...). Try to read the error body so
        # closed-banner detection can run, but never fail on a missing body.
        body = ""
        try:
            body = exc.read(MAX_BYTES).decode("utf-8", "replace")
        except Exception:
            body = ""
        return {"status": exc.code, "final_url": getattr(exc, "url", url) or url,
                "html": body, "network_error": None}
    except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, socket.timeout) or isinstance(exc, (socket.timeout, TimeoutError)):
            etype = "timeout"
        elif isinstance(reason, socket.gaierror):
            etype = "dns"
        else:
            etype = type(reason).__name__ if reason else type(exc).__name__
        return {"status": None, "final_url": url, "html": "", "network_error": etype}
    except Exception as exc:  # noqa: BLE001 - any other network oddity is transient
        return {"status": None, "final_url": url, "html": "",
                "network_error": type(exc).__name__}


# --------------------------------------------------------------------------- #
# classifier (pure — no I/O; this is what the tests exercise)
# --------------------------------------------------------------------------- #
def classify_reverify(*, http_status, network_error, final_url,
                      title_match, apply_found, closed_signal, js_heavy=False):
    """Decide keep / warn / remove for one posting from deterministic signals.

    Returns (action, reason, evidence) where action is 'keep', 'warn', or
    'remove'. REMOVE is returned ONLY for deterministic failures; every
    transient or ambiguous signal returns 'warn' (which keeps the posting).
    """
    # --- Transient / network: NEVER remove. ---
    if network_error:
        return ("warn", "transient network error (%s)" % network_error,
                "could not reach the page (%s); kept pending re-check" % network_error)
    if http_status is None:
        return ("warn", "no HTTP status obtained",
                "no HTTP status returned; kept pending re-check")
    if http_status == 429:
        return ("warn", "rate limited (HTTP 429)",
                "HTTP 429 is transient; kept pending re-check")
    if 500 <= http_status <= 599:
        return ("warn", "server error (HTTP %d)" % http_status,
                "HTTP %d is a transient server error; kept pending re-check" % http_status)

    # --- Deterministic gone. ---
    if http_status in (404, 410):
        return ("remove", "page gone (HTTP %d)" % http_status,
                "official page returned HTTP %d" % http_status)

    # --- Any other non-200 (403/401/3xx leftover/...) is ambiguous → keep. ---
    if http_status != 200:
        return ("warn", "ambiguous HTTP status (%d)" % http_status,
                "HTTP %d is ambiguous (could be bot-blocking); kept pending re-check"
                % http_status)

    # --- HTTP 200 from here on. ---
    if closed_signal:
        return ("remove", "page indicates the role is closed/filled/expired",
                "official page text states the posting is closed/filled/expired")

    forbidden = classify_forbidden(final_url)
    if forbidden:
        return ("remove", "final URL is no longer a specific official posting",
                "the link now resolves to: %s" % forbidden)

    if js_heavy:
        return ("warn", "page not verifiable from terminal HTTP (JS-heavy)",
                "page is JS-heavy / too sparse to confirm from raw HTML; kept")

    if title_match and apply_found:
        return ("keep", "role title and apply flow confirmed on official page",
                "HTTP 200; role title present; apply flow present")

    if not title_match and not apply_found:
        return ("remove", "role no longer present and no apply flow",
                "HTTP 200 but the role title is gone and no apply flow was found")

    # Mixed signals (title XOR apply) → ambiguous → keep.
    if title_match and not apply_found:
        return ("warn", "title present but apply flow not detected",
                "HTTP 200; role title present but apply flow not detected; kept")
    return ("warn", "apply flow present but title not confirmed",
            "HTTP 200; apply flow present but role title not confirmed; kept")


# --------------------------------------------------------------------------- #
# per-entry re-verification (I/O wrapper around the pure classifier)
# --------------------------------------------------------------------------- #
def reverify_entry(entry):
    """Fetch + classify one dataset entry. Returns a result dict."""
    url = entry.get("application_url", "")
    role = entry.get("role", "")
    source_type = source_type_of(url)

    fetched = reverify_fetch(url)
    status = fetched["status"]
    final_url = fetched["final_url"]
    html_text = fetched["html"]
    network_error = fetched["network_error"]

    title_match = False
    apply_found = False
    closed_signal = False
    js_heavy = False
    if status == 200 and html_text:
        text = page_text_of(html_text)
        title_match = title_on_page(role, html_text, text)
        apply_found = apply_on_page(text, html_text, source_type, url)
        closed_signal = bool(CLOSED_PAGE_RE.search(text))
        # JS-heavy: known SPA ATS that didn't render a confirmable title, or a
        # page too sparse to judge. Mirrors verify_candidates' heuristic.
        js_heavy = (source_type in ("Workday", "iCIMS") and not title_match) or \
            (len(text) < 600 and not title_match)
    elif status is not None and status != 200 and html_text:
        # Even on an HTTP error page we may see an explicit closed banner.
        text = page_text_of(html_text)
        closed_signal = bool(CLOSED_PAGE_RE.search(text))

    action, reason, evidence = classify_reverify(
        http_status=status, network_error=network_error, final_url=final_url,
        title_match=title_match, apply_found=apply_found,
        closed_signal=closed_signal, js_heavy=js_heavy)

    return {
        "id": entry.get("id"),
        "company": entry.get("company"),
        "role": role,
        "application_url": url,
        "final_url": final_url,
        "source_type": source_type,
        "http_status": status,
        "network_error": network_error,
        "title_match": title_match,
        "apply_found": apply_found,
        "closed_signal": closed_signal,
        "js_heavy": js_heavy,
        "action": action,
        "reason": reason,
        "evidence": evidence,
        "last_verified_date": entry.get("last_verified_date", ""),
    }


# --------------------------------------------------------------------------- #
# data / archive helpers
# --------------------------------------------------------------------------- #
def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return default
    except ValueError as exc:
        raise SystemExit("ERROR: %s is not valid JSON: %s" % (path, exc))


def write_dataset(data):
    DATA_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_archive(records):
    archive = load_json(ARCHIVE_PATH, [])
    if not isinstance(archive, list):
        raise SystemExit("ERROR: archive/removed_internships.json is not a JSON array.")
    archive.extend(records)
    ARCHIVE_PATH.write_text(
        json.dumps(archive, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(archive)


def make_archive_record(entry, result):
    return {
        "removed_at": TODAY,
        "removal_reason": result["reason"],
        "removal_evidence": result["evidence"],
        "previous_entry": entry,
        "previous_application_url": entry.get("application_url", ""),
        "previous_last_verified_date": entry.get("last_verified_date", ""),
        "reverify_status": result["action"],
        "reverify_http_status": result["http_status"],
    }


def run_py(script):
    return subprocess.run([sys.executable, str(SCRIPTS / script)],
                          cwd=str(PROJECT_ROOT)).returncode


def regenerate():
    """Refresh derived artifacts after a dataset mutation. Returns True on OK."""
    ok = True
    for s in ("generate_readme_table.py", "generate_status_report.py", "sync_web_data.py"):
        if run_py(s) != 0:
            print("ERROR: regeneration step failed: %s" % s, file=sys.stderr)
            ok = False
    return ok


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def write_report(report_path, results, mode, removed_ids, refreshed_ids,
                 max_remove, over_limit):
    keeps = [r for r in results if r["action"] == "keep"]
    warns = [r for r in results if r["action"] == "warn"]
    removes = [r for r in results if r["action"] == "remove"]
    lines = [
        "# Re-verification Report",
        "",
        "_Generated by `scripts/reverify_existing.py`. Conservative re-check of "
        "existing active postings against their official application pages. "
        "Postings are removed **only** on a deterministic failure; transient "
        "errors (timeout, DNS, 429, 5xx) and ambiguity always keep the posting._",
        "",
        "**Report date:** %s" % TODAY,
        "**Mode:** %s" % mode,
        "**Entries checked:** %d" % len(results),
        "**Keep:** %d  ·  **Warn (kept):** %d  ·  **Remove (deterministic):** %d"
        % (len(keeps), len(warns), len(removes)),
        "**Max-remove guard:** %d%s" % (
            max_remove,
            "  ·  **OVER LIMIT — capped/halted**" if over_limit else ""),
    ]
    if mode == "APPLY":
        lines.append("**Removed this run:** %d  ·  **Re-confirmed dates refreshed:** %d"
                     % (len(removed_ids), len(refreshed_ids)))
    lines += ["", "## Removals (deterministic failures, archived)", ""]
    if removes:
        lines.append("| Company | Role | HTTP | Reason | Evidence | Apply URL |")
        lines.append("|---|---|---|---|---|---|")
        for r in removes:
            applied = " (removed)" if r["id"] in removed_ids else (
                " (would remove)" if mode != "APPLY" else " (deferred — over limit)")
            lines.append("| %s | %s | %s | %s%s | %s | %s |" % (
                _md(r["company"]), _md(r["role"]),
                r["http_status"] if r["http_status"] is not None else "-",
                _md(r["reason"]), applied, _md(r["evidence"]), _md(r["application_url"])))
    else:
        lines.append("_None. No posting deterministically failed re-verification._")
    lines += ["", "## Warnings (kept — transient or ambiguous)", ""]
    if warns:
        lines.append("| Company | Role | HTTP | Reason |")
        lines.append("|---|---|---|---|")
        for r in warns:
            lines.append("| %s | %s | %s | %s |" % (
                _md(r["company"]), _md(r["role"]),
                r["http_status"] if r["http_status"] is not None else
                (r["network_error"] or "-"), _md(r["reason"])))
    else:
        lines.append("_None._")
    lines += ["", "## Confirmed open (kept)", ""]
    if keeps:
        lines.append("| Company | Role | Source | Date refreshed? |")
        lines.append("|---|---|---|---|")
        for r in keeps:
            lines.append("| %s | %s | %s | %s |" % (
                _md(r["company"]), _md(r["role"]), r["source_type"],
                "yes" if r["id"] in refreshed_ids else "no"))
    else:
        lines.append("_None._")
    lines += [
        "",
        "## How removal is decided",
        "",
        "A posting is removed **only** when its official page deterministically "
        "fails: HTTP 404/410, an explicit closed/filled/expired banner, a final "
        "URL that is now a private/login-gated board, generic careers homepage, "
        "search page, or raw API endpoint, or the role title gone **and** no "
        "apply flow. Timeouts, DNS errors, HTTP 429, HTTP 5xx, JS-heavy pages, "
        "and single ambiguous parses **never** remove a posting — they warn and "
        "keep it. Every removed entry is archived to "
        "`archive/removed_internships.json` before deletion.",
        "",
        "> Users should still re-check the official application page themselves "
        "before applying.",
        "",
    ]
    Path(report_path).write_text("\n".join(lines), encoding="utf-8")


def _md(s):
    return str(s if s is not None else "").replace("|", "\\|")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(argv):
    p = argparse.ArgumentParser(
        description="Conservatively re-verify existing internship postings.")
    p.add_argument("--apply", action="store_true",
                   help="actually remove (and archive) deterministically-failed postings")
    p.add_argument("--max-remove", type=int, default=5,
                   help="safety cap on removals per run (default 5)")
    p.add_argument("--fail-on-remove-over-limit", action="store_true",
                   help="exit non-zero (mutating nothing) if removals exceed --max-remove")
    p.add_argument("--refresh-verified", action="store_true",
                   help="(apply only) bump last_verified_date/date_updated for "
                        "re-confirmed-open postings")
    p.add_argument("--report", default=str(DEFAULT_REPORT),
                   help="path for the human-readable report")
    p.add_argument("--limit", type=int, default=0,
                   help="re-verify at most N entries (0 = all; for quick local runs)")
    p.add_argument("--keep-tmp", action="store_true",
                   help="(accepted for parity; tmp results are always kept)")
    args = p.parse_args(argv[1:])

    if args.max_remove < 0:
        print("ERROR: --max-remove must be >= 0.", file=sys.stderr)
        return 2
    if args.refresh_verified and not args.apply:
        print("ERROR: --refresh-verified requires --apply.", file=sys.stderr)
        return 2

    mode = "APPLY" if args.apply else "DRY-RUN"
    data = load_json(DATA_PATH, None)
    if not isinstance(data, list):
        print("ERROR: %s is missing or not a JSON array." % DATA_PATH, file=sys.stderr)
        return 2

    entries = data if args.limit <= 0 else data[:args.limit]
    print("=" * 64)
    print("Re-verify existing postings  [%s]" % mode)
    print("entries=%d  max_remove=%d" % (len(entries), args.max_remove))
    print("=" * 64)

    results = []
    for e in entries:
        r = reverify_entry(e)
        results.append(r)
        tag = {"keep": "keep  ", "warn": "WARN  ", "remove": "REMOVE"}[r["action"]]
        http = r["http_status"] if r["http_status"] is not None else (r["network_error"] or "-")
        print("  [%s] %-5s %-9s %s — %s"
              % (tag, str(http), r["source_type"], (r["company"] or "")[:22],
                 (r["role"] or "")[:38]))

    TMP_DIR.mkdir(exist_ok=True)
    RESULTS_PATH.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    removes = [r for r in results if r["action"] == "remove"]
    over_limit = len(removes) > args.max_remove

    removed_ids = []
    refreshed_ids = []
    rc = 0

    if over_limit:
        msg = ("Removal candidates (%d) exceed --max-remove (%d)."
               % (len(removes), args.max_remove))
        if args.fail_on_remove_over_limit:
            print("\nERROR: %s Refusing to mutate (--fail-on-remove-over-limit)."
                  % msg, file=sys.stderr)
            write_report(args.report, results, mode, [], [], args.max_remove, True)
            return 1
        print("\nWARNING: %s Will remove only the first %d this run; the rest are "
              "deferred (kept)." % (msg, args.max_remove), file=sys.stderr)

    to_remove = removes[:args.max_remove] if over_limit else removes
    remove_ids_set = {r["id"] for r in to_remove}

    if args.apply and (to_remove or args.refresh_verified):
        # 1) Archive removed entries FIRST, then drop them from the dataset.
        if to_remove:
            id_to_result = {r["id"]: r for r in to_remove}
            archived = [make_archive_record(e, id_to_result[e.get("id")])
                        for e in data if e.get("id") in remove_ids_set]
            append_archive(archived)
            removed_ids = [a["previous_entry"].get("id") for a in archived]

        # 2) Build the new dataset: drop removed; optionally refresh confirmed-open.
        keep_open_ids = {r["id"] for r in results if r["action"] == "keep"}
        new_data = []
        for e in data:
            if e.get("id") in remove_ids_set:
                continue
            if args.refresh_verified and e.get("id") in keep_open_ids:
                if e.get("last_verified_date") != TODAY or e.get("date_updated") != TODAY:
                    e = dict(e)
                    e["last_verified_date"] = TODAY
                    e["date_updated"] = TODAY
                    refreshed_ids.append(e.get("id"))
            new_data.append(e)

        write_dataset(new_data)
        print("\nApplied: removed %d, refreshed %d. Regenerating artifacts..."
              % (len(removed_ids), len(refreshed_ids)))
        if not regenerate():
            rc = 1
    elif args.apply:
        print("\nApply mode: nothing to remove and no refresh requested. "
              "Dataset unchanged.")
    else:
        print("\n[DRY-RUN] No data/archive changes. Re-run with --apply to remove "
              "deterministically-failed postings.")

    write_report(args.report, results, mode, removed_ids, refreshed_ids,
                 args.max_remove, over_limit)

    keeps = sum(1 for r in results if r["action"] == "keep")
    warns = sum(1 for r in results if r["action"] == "warn")
    print("\n" + "=" * 64)
    print("RE-VERIFICATION SUMMARY")
    print("=" * 64)
    print("Checked:   %d" % len(results))
    print("Keep:      %d" % keeps)
    print("Warn:      %d (kept — transient/ambiguous)" % warns)
    print("Remove:    %d (deterministic)%s"
          % (len(removes), "  [OVER LIMIT]" if over_limit else ""))
    if args.apply:
        print("Removed:   %d (archived to archive/removed_internships.json)"
              % len(removed_ids))
        print("Refreshed: %d" % len(refreshed_ids))
    print("Results:   tmp/reverification_results.json")
    print("Report:    %s" % args.report)
    print("=" * 64)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
