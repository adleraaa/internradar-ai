#!/usr/bin/env python3
"""Verify discovered candidates and produce reviewable pending drafts.

Standard-library only (urllib, json, re, datetime, html, pathlib). No browser
automation. This script fetches PUBLIC application pages over HTTP to check that a
role still exists and appears to accept applications, then writes review drafts.

It does NOT modify data/internships.json and does NOT promote anything.

Input:
  tmp/candidates_filtered.json   (from scripts/discover_candidates.py)

Outputs:
  pending/auto/auto_*.md             one draft per high-enough-confidence candidate
  docs/candidate_review_report.md    human-readable report (incl. skipped + scores)
  tmp/candidates_verified.json       machine-readable verification results

Confidence (local-only; NOT a schema field) gates draft creation:
  draft created only if confidence >= 70
  >= 90 -> "High confidence";  70-89 -> "Needs manual review"

Usage:
    python scripts/verify_candidates.py [--limit N]   (default N = 10)

Exit code:
    0  -> ran (even if 0 drafts created)
    1  -> input missing / unreadable
"""

import argparse
import html as html_mod
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = PROJECT_ROOT / "tmp"
PENDING_AUTO = PROJECT_ROOT / "pending" / "auto"
REPORT_PATH = PROJECT_ROOT / "docs" / "candidate_review_report.md"
INPUT_PATH = TMP_DIR / "candidates_filtered.json"
SOURCE_REPO = "https://github.com/SimplifyJobs/Summer2026-Internships"

TODAY = date.today().isoformat()

PREFERRED_ATS = ("greenhouse", "lever", "ashby")
DRAFT_THRESHOLD = 70        # write a pending/auto draft at/above this confidence
AUTO_PROMOTE_THRESHOLD = 90  # eligible for auto-promotion at/above this confidence

# Populated in main() with normalized application_urls already in the dataset.
EXISTING_URL_KEYS = set()

TECH_PATTERNS = {
    "Python": r"\bpython\b", "JavaScript": r"\bjavascript\b", "TypeScript": r"\btypescript\b",
    "React": r"\breact\b", "Node.js": r"\bnode(?:\.js)?\b", "Java": r"\bjava\b(?!script)",
    "Go": r"\bgolang\b", "Rust": r"\brust\b", "C++": r"c\+\+", "Go ": r"\bgo\b",
    "SQL": r"\bsql\b", "PyTorch": r"\bpytorch\b", "TensorFlow": r"\btensorflow\b",
    "Kubernetes": r"\bkubernetes\b", "Docker": r"\bdocker\b", "AWS": r"\baws\b",
    "GCP": r"\bgcp\b", "Django": r"\bdjango\b", "Flask": r"\bflask\b",
    "GraphQL": r"\bgraphql\b", "Next.js": r"\bnext\.js\b", "Ruby": r"\bruby\b",
    "Kotlin": r"\bkotlin\b", "Swift": r"\bswift\b", "Scala": r"\bscala\b",
}

RELEVANT_TITLE_RE = re.compile(
    r"software|engineer|developer|full[\s-]?stack|front[\s-]?end|back[\s-]?end|"
    r"machine learning|deep learning|artificial intelligence|\bai\b|\bml\b|"
    r"data scien|data engineer|platform|infrastructure|\bsde\b|\bswe\b|web develop",
    re.I,
)
# Titles that disqualify a role (unless clearly software).
REJECT_TITLE_RE = re.compile(
    r"new grad|new graduate|\bsenior\b|\bstaff\b|\bprincipal\b|manager|director|"
    r"\bsales\b|recruit|mechanical|chemical|geolog|civil eng|biolog|accounting|"
    r"marketing|full[\s-]?time only", re.I)
SOFTWARE_OVERRIDE_RE = re.compile(r"software|\bswe\b|\bsde\b|developer", re.I)
INTERN_TITLE_RE = re.compile(r"\bintern|internship|co-?op\b", re.I)

# Hardware / electrical / silicon roles — NOT the CS/software/AI/data focus.
HARDWARE_DOMAIN_RE = re.compile(
    r"\bic design\b|physical design|\brtl\b|\basic\b|\bfpga\b|\bvlsi\b|"
    r"mixed[- ]signal|semiconductor|\bsilicon\b|tapeout|place and route|"
    r"\bdft\b|\bserdes\b|\bpcb\b|circuit design|\bfirmware\b|embedded systems|"
    r"\bhardware\b|chip design|board design|analog design|digital design", re.I)
# Clear software/data signals that override a hardware keyword.
_HW_SOFTWARE_OVERRIDE_RE = re.compile(
    r"software (?:engineer|developer)|full[\s-]?stack|web develop|\bswe\b|"
    r"backend|frontend|\bcompiler", re.I)


def is_hardware_only(title):
    """True for hardware/electrical roles outside the CS/software/AI/data focus."""
    t = title or ""
    if not HARDWARE_DOMAIN_RE.search(t):
        return False
    return not _HW_SOFTWARE_OVERRIDE_RE.search(t)


# Graduate-only / advanced-degree-only signals (the tracker targets undergrads).
# Title-level: a clearly graduate/PhD/MBA-targeted role.
_GRAD_TITLE_RE = re.compile(
    r"\bph\.?\s?d\.?\b|\bdoctoral\b|\bdoctorate\b|\bmba\b|\bm\.?b\.?a\.?\b|"
    r"graduate (?:student )?intern|grad intern", re.I)
# Body-level: a requirement that clearly excludes undergraduates.
_GRAD_BODY_RE = re.compile(
    r"ph\.?\s?d\.?\s*(?:student|candidate|required|preferred)|"
    r"currently pursuing a ph\.?\s?d|pursuing ph\.?\s?d|enrolled in a ph\.?\s?d|"
    r"doctoral (?:student|candidate)|graduate student required|"
    r"master'?s degree required|master'?s students? only|"
    r"advanced degree required|ms\s*/\s*ph\.?\s?d\s*required|"
    r"m\.?s\.?\s*/\s*ph\.?\s?d\.?|mba (?:student|candidate|required|program)",
    re.I)
# Mixed/inclusive phrasing that must NOT trigger a graduate-only block.
_GRAD_INCLUSIVE_RE = re.compile(
    r"bachelor'?s or master|b\.?s\.?\s*(?:,|or|/)\s*m\.?s\.?|"
    r"undergraduate or graduate|undergraduate (?:and|or|/) graduate|"
    r"bachelor'?s,?\s*master'?s,?\s*(?:or|and)\s*ph\.?\s?d|"
    r"pursuing a bachelor'?s|undergraduate students? (?:are )?(?:welcome|encouraged)|"
    r"rising (?:junior|senior)|all undergraduates", re.I)


def is_graduate_only(title, text=""):
    """Return (bool, evidence). True only when the role is CLEARLY graduate/PhD/
    MBA/advanced-degree-only. Mixed eligibility (e.g. "Bachelor's or Master's")
    never triggers a block.
    """
    t = title or ""
    body = text or ""
    # Inclusive phrasing anywhere → not graduate-only (undergrads are welcome).
    if _GRAD_INCLUSIVE_RE.search(t) or _GRAD_INCLUSIVE_RE.search(body):
        return False, ""
    m = _GRAD_TITLE_RE.search(t)
    if m:
        return True, "role title indicates graduate/advanced degree: '%s'" % m.group(0).strip()
    m = _GRAD_BODY_RE.search(body)
    if m:
        return True, "posting requires graduate/advanced degree: '%s'" % m.group(0).strip()
    return False, ""

DATA_PATH = PROJECT_ROOT / "data" / "internships.json"
# Final-URL hosts that are private / login-gated / aggregator and never allowed.
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
    """Return a short reason if the FINAL URL is a forbidden source, else None."""
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


def load_existing_url_keys():
    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8-sig"))
        return {url_key(e.get("application_url", "")) for e in data}
    except Exception:
        return set()


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


def ats_rank(cand):
    u = (cand.get("url") or "").lower()
    for i, name in enumerate(PREFERRED_ATS):
        if name in u:
            return i
    return len(PREFERRED_ATS)


def fetch(url):
    """Return (status, html_text). Raises on network error."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read(800_000)  # cap to avoid huge pages
        status = resp.getcode()
    text = raw.decode("utf-8", "replace")
    return status, text


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


def category_of(title, source_category):
    t = (title or "").lower()
    c = (source_category or "").lower()
    if "data scien" in t or "data scien" in c:
        return "Data Science"
    if re.search(r"\bai\b|\bml\b|machine learning|artificial intelligence|deep learning", t) \
            or "ai/ml" in c:
        return "AI/ML"
    if RELEVANT_TITLE_RE.search(t) or "software" in c or "data" in c:
        return "Software Engineering"
    return "Other"


def extract_techs(text):
    found = []
    for name, pat in TECH_PATTERNS.items():
        if re.search(pat, text, re.I):
            label = name.strip()
            if label not in found:
                found.append(label)
    return found[:8]


def detect_student_level(text):
    t = text.lower()
    if re.search(r"bachelor|undergraduate|\bb\.?s\.?\b|pursuing a degree|"
                 r"currently enrolled|rising (?:sophomore|junior|senior)|undergrad", t):
        return "Undergraduate"
    return "Unclear"


def detect_fresh_soph(text):
    t = text.lower()
    if re.search(r"freshman|sophomore|first[\s-]year|all undergraduates|rising sophomore", t):
        return "Yes"
    if re.search(r"junior or senior|rising senior only|seniors only", t):
        return "No"
    return "Unclear"


def detect_citizenship(text):
    """Return (requires_us_citizenship, sponsorship_note, work_auth_note, evidence_extra)."""
    t = text.lower()
    if re.search(r"u\.?\s?s\.?\s?citizen|citizenship (?:is )?required|"
                 r"must be a u\.?s\.? citizen|citizenship,? lawful permanent", t):
        return ("Yes",
                "Posting indicates a U.S. citizenship / U.S.-person requirement.",
                "Posting indicates U.S. citizenship or U.S.-person status is required "
                "(verify exact wording on the official page).",
                "page text mentions U.S. citizenship requirement")
    if re.search(r"we sponsor|offer sponsorship|provide sponsorship|support.{0,6}visa|"
                 r"visa sponsorship|open to all.{0,20}work authorization", t):
        return ("No",
                "Posting appears to mention visa sponsorship / openness to work-authorized "
                "candidates (verify wording).",
                "Posting appears to indicate sponsorship or openness to work-authorized "
                "candidates (verify wording).",
                "page text mentions sponsorship / work-authorization openness")
    return ("Unclear",
            "Not explicitly stated on the official posting.",
            "Not explicitly stated on the official posting.",
            "")


def location_fields(locations):
    locs = [l for l in (locations or []) if str(l).strip()]
    loc_str = "; ".join(locs)
    if not loc_str:
        return "Unclear", "Unclear", False
    low = loc_str.lower()
    if "remote" in low:
        return loc_str, "Remote", True
    if "multiple" in low or len(locs) > 1:
        return loc_str, "Multiple", True
    return loc_str, "Onsite", True


def sanitize(part):
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", part or "").strip("_").lower()
    return (cleaned or "unknown")[:40]


# Period word -> (enum, suffix).
_PERIOD_MAP = [
    (r"hour|hourly|/\s*hr\b|per hour", ("Hour", "/hr")),
    (r"year|annual|annually|/\s*yr\b|per year", ("Year", "/year")),
    (r"month|/\s*mo\b|per month", ("Month", "/month")),
]
# Context that means a dollar figure is NOT pay (funding/revenue/valuation).
_NOT_PAY_CTX = re.compile(r"arr|raised|funding|valuation|revenue|million|billion|"
                          r"series\s+[a-e]\b|in funding|market", re.I)
_AMT = r"\$\s?([\d,]+(?:\.\d{1,2})?)"
_PERIOD = r"(?:/|\s*per\s*|\s+an?\s+)\s*(hour|hourly|hr|year|yr|annual|annually|month|mo)\b"


def _to_num(s):
    try:
        n = float(s.replace(",", ""))
        return int(n) if n.is_integer() else n
    except ValueError:
        return None


def _period_enum(word):
    w = word.lower()
    for pat, (enum, suffix) in _PERIOD_MAP:
        if re.search(pat, w):
            return enum, suffix
    return "Other", ""


def detect_compensation(text, source_type):
    """Detect EXPLICIT pay on the page. Never guesses; no third-party sources.

    Returns dict: compensation_min/max/currency/period/note/evidence.
    """
    unclear = {
        "compensation_min": None, "compensation_max": None,
        "compensation_currency": "Unclear", "compensation_period": "Unclear",
        "compensation_note": "Unclear",
        "compensation_evidence":
            "No compensation information found on the official application page.",
    }
    flat = re.sub(r"\s+", " ", text)

    # Range: $A - $B per <period>
    rng = re.search(_AMT + r"\s*(?:-|–|to)\s*" + _AMT + r"\s*" + _PERIOD, flat, re.I)
    if rng and not _NOT_PAY_CTX.search(flat[max(0, rng.start() - 30):rng.start()]):
        lo, hi = _to_num(rng.group(1)), _to_num(rng.group(2))
        enum, suffix = _period_enum(rng.group(3))
        if lo is not None and hi is not None:
            return {
                "compensation_min": lo, "compensation_max": hi,
                "compensation_currency": "USD", "compensation_period": enum,
                "compensation_note": "$%s - $%s%s" % (rng.group(1), rng.group(2), suffix),
                "compensation_evidence":
                    "Official %s page explicitly lists pay of $%s-$%s%s."
                    % (source_type, rng.group(1), rng.group(2), suffix),
            }

    # Single: $A per <period>
    for m in re.finditer(_AMT + r"\s*" + _PERIOD, flat, re.I):
        ctx = flat[max(0, m.start() - 30):m.start()]
        if _NOT_PAY_CTX.search(ctx):
            continue
        amt = _to_num(m.group(1))
        enum, suffix = _period_enum(m.group(2))
        if amt is not None:
            return {
                "compensation_min": amt, "compensation_max": amt,
                "compensation_currency": "USD", "compensation_period": enum,
                "compensation_note": "$%s%s" % (m.group(1), suffix),
                "compensation_evidence":
                    "Official %s page explicitly lists pay of $%s%s."
                    % (source_type, m.group(1), suffix),
            }

    # Unpaid.
    if re.search(r"\bunpaid\b", flat, re.I):
        return {
            "compensation_min": None, "compensation_max": None,
            "compensation_currency": "Unclear", "compensation_period": "Unpaid",
            "compensation_note": "Unpaid",
            "compensation_evidence": "Official %s page indicates the role is unpaid." % source_type,
        }
    # Stipend mentioned without a parseable figure.
    if re.search(r"\bstipend\b", flat, re.I):
        return {
            "compensation_min": None, "compensation_max": None,
            "compensation_currency": "Unclear", "compensation_period": "Stipend",
            "compensation_note": "Stipend (amount not parsed)",
            "compensation_evidence": "Official %s page mentions a stipend; verify the amount." % source_type,
        }
    return unclear


def build_draft(f, confidence, classification):
    """Return Markdown text in the project's submission format."""
    techs = ", ".join(f["tech_keywords"])
    risks = ", ".join(f["risk_flags"])
    return """# Internship Submission (auto-discovered candidate)

<!-- auto-generated by scripts/verify_candidates.py -->
<!-- auto-confidence: {confidence} -->
<!-- auto-classification: {classification} -->

> **Review status: {classification}** (local confidence {confidence}/100).
> This is an UNVERIFIED auto-discovered candidate. A maintainer must check the
> official application page before promoting it. Do not copy full JD text.

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

- **tech_keywords:** {techs}
- **ai_relevance:** {ai_relevance}
- **full_stack_relevance:** {full_stack_relevance}
- **student_level:** {student_level}
- **freshman_sophomore_friendly:** {freshman_sophomore_friendly}

## Work authorization (cite evidence for any definite claim)

- **requires_us_citizenship:** {requires_us_citizenship}
- **sponsorship_note:** {sponsorship_note}
- **work_authorization_note:** {work_authorization_note}

## Compensation (OFFICIAL PAGE ONLY — auto-detected; verify before promoting)

- **compensation_min:** {compensation_min}
- **compensation_max:** {compensation_max}
- **compensation_currency:** {compensation_currency}
- **compensation_period:** {compensation_period}
- **compensation_note:** {compensation_note}
- **compensation_evidence:** {compensation_evidence}

## Notes & summary (maintainer must verify; never copied JD text)

- **evidence_notes:** {evidence_notes}
- **fit_summary:** {fit_summary}
- **risk_flags:** {risks}
""".format(confidence=confidence, classification=classification, techs=techs, risks=risks, **f)


def score_and_eligibility(*, reachable, title_match, apply_found, internship_wording,
                          location_found, technical, comp_classified,
                          forbidden_reason, js_heavy, non_internship, nontechnical,
                          senior_fulltime, duplicate, status_open,
                          graduate_only=False,
                          min_confidence=AUTO_PROMOTE_THRESHOLD):
    """Pure verification-confidence + auto-promote decision (no I/O).

    Verification confidence measures whether the posting is real, open, official,
    specific, and parseable — NOT user-fit. Unclear sponsorship / student level /
    compensation does NOT reduce it.
    """
    conf, reasons = 0, []
    if reachable:
        conf += 25; reasons.append("reachable official application page (+25)")
    if title_match:
        conf += 20; reasons.append("role title (or close variant) on page (+20)")
    if apply_found:
        conf += 20; reasons.append("apply indicator found (+20)")
    if internship_wording:
        conf += 15; reasons.append("internship/co-op wording (+15)")
    if location_found:
        conf += 10; reasons.append("location found (+10)")
    if technical:
        conf += 10; reasons.append("clearly CS/software/AI/data technical (+10)")
    if comp_classified:
        conf += 5; reasons.append("compensation classified from official page (+5)")

    if forbidden_reason in ("generic careers/jobs homepage", "job-search/query page"):
        conf -= 50
    if forbidden_reason == "Simplify redirect as final URL":
        conf -= 50
    if forbidden_reason == "raw API URL":
        conf -= 50
    if forbidden_reason == "private/login-gated job board":
        conf -= 50
    if js_heavy:
        conf -= 40
    if non_internship:
        conf -= 40
    if nontechnical:
        conf -= 40
    if senior_fulltime:
        conf -= 40
    # NOTE: graduate-only is a FIT/eligibility issue, not a posting-quality issue.
    # It is a hard blocker for auto-promotion but does NOT lower verification
    # confidence, so an otherwise-verified grad-only role still gets a (flagged)
    # pending/auto draft for optional manual review.
    if duplicate:
        conf -= 100
    conf = max(0, min(100, conf))

    blockers = []
    if not reachable:
        blockers.append("page not reachable")
    if not title_match:
        blockers.append("role title not confirmed on page")
    if not apply_found:
        blockers.append("no apply indicator found")
    if non_internship:
        blockers.append("not clearly an internship/co-op")
    if nontechnical:
        blockers.append("not clearly CS/software/AI/data technical")
    if senior_fulltime:
        blockers.append("appears full-time/new-grad/senior/staff/manager")
    if graduate_only:
        blockers.append("graduate-only or advanced-degree-only role")
    if forbidden_reason:
        blockers.append("forbidden source: %s" % forbidden_reason)
    if js_heavy:
        blockers.append("JS-heavy / not verifiable from terminal HTTP")
    if duplicate:
        blockers.append("duplicate application_url")
    if not status_open:
        blockers.append("status is not Open")
    if conf < min_confidence:
        blockers.append("verification_confidence %d below %d" % (conf, min_confidence))

    eligible = not blockers
    return conf, eligible, reasons, blockers


def verify_one(cand):
    """Return (fields_or_None, result_dict). fields is None if no draft."""
    url = cand.get("url", "")
    role = cand.get("title", "")
    company = cand.get("company", "")
    source_type = source_type_of(url)
    result = {
        "company": company, "role": role, "url": url,
        "source_type": source_type, "confidence": 0, "verification_confidence": 0,
        "classification": "Skipped", "drafted": False, "skip_reason": "",
        "draft_file": "", "auto_promote_eligible": False,
        "auto_promote_reasons": [], "auto_promote_blockers": [],
        "title_match": False, "apply_indicator_found": False,
        "internship_wording_found": bool(INTERN_TITLE_RE.search(role)),
        "location_found": False, "technical_role_detected": False,
        "graduate_only_detected": False, "graduate_only_evidence": "",
        "compensation_known": False, "compensation_note": "",
        "requires_us_citizenship": "", "sponsorship_note": "",
        "work_authorization_note": "",
        "locations": cand.get("locations", []), "terms": cand.get("terms", []),
    }

    # Fetch.
    try:
        status, html_text = fetch(url)
    except urllib.error.HTTPError as exc:
        result["skip_reason"] = "HTTP error %s" % exc.code
        return None, result
    except Exception as exc:
        result["skip_reason"] = "fetch failed (%s)" % type(exc).__name__
        return None, result
    if status != 200:
        result["skip_reason"] = "non-200 status (%s)" % status
        return None, result

    text = page_text_of(html_text)
    title_found = title_on_page(role, html_text, text)
    apply_found = apply_on_page(text, html_text, source_type, url)
    intern_found = bool(re.search(r"intern|co-?op", text, re.I)) or \
        bool(re.search(r"intern|co-?op", role, re.I))
    cs_relevant = bool(RELEVANT_TITLE_RE.search(role)) or \
        (cand.get("source_category", "").lower() in
         ("software", "data science", "ai/ml", "data"))
    # Hardware/electrical roles are not the CS/software/AI/data focus, so they are
    # not counted as "technical" for auto-promotion (rule: no hardware-only roles).
    technical = cs_relevant and not is_hardware_only(role)

    location, location_type, loc_found = location_fields(cand.get("locations"))
    student_level = detect_student_level(text)
    fresh_soph = detect_fresh_soph(text)
    citizen, sponsor_note, workauth_note, cit_evidence = detect_citizenship(text)

    js_heavy = (source_type in ("Workday", "iCIMS") and not title_found) or \
        (len(text) < 600 and not title_found)
    non_official = source_type == "Company Career Page" and not title_found

    # --- Role / source / dedup flags ---
    internship_title = bool(INTERN_TITLE_RE.search(role))
    non_internship = not internship_title
    nontechnical = not technical
    senior_fulltime = bool(REJECT_TITLE_RE.search(role)) and not SOFTWARE_OVERRIDE_RE.search(role)
    grad_only, grad_evidence = is_graduate_only(role, text)
    forbidden_reason = classify_forbidden(url)
    duplicate = url_key(url) in EXISTING_URL_KEYS

    comp = detect_compensation(text, source_type)
    comp_known = comp["compensation_note"].strip().lower() not in ("", "unclear")

    # --- Verification confidence + auto-promote decision ---
    conf, eligible, reasons, blockers = score_and_eligibility(
        reachable=True, title_match=title_found, apply_found=apply_found,
        internship_wording=internship_title, location_found=loc_found,
        technical=technical, comp_classified=True, forbidden_reason=forbidden_reason,
        js_heavy=js_heavy, non_internship=non_internship, nontechnical=nontechnical,
        senior_fulltime=senior_fulltime, graduate_only=grad_only,
        duplicate=duplicate, status_open=True)

    result.update({
        "verification_confidence": conf,
        "confidence": conf,
        "auto_promote_eligible": False,
        "auto_promote_reasons": reasons,
        "auto_promote_blockers": blockers,
        "title_match": title_found,
        "apply_indicator_found": apply_found,
        "internship_wording_found": internship_title,
        "location_found": loc_found,
        "technical_role_detected": technical,
        "graduate_only_detected": grad_only,
        "graduate_only_evidence": grad_evidence,
        "compensation_known": comp_known,
        "compensation_note": comp["compensation_note"],
        "requires_us_citizenship": citizen,
        "sponsorship_note": sponsor_note,
        "work_authorization_note": workauth_note,
        "locations": cand.get("locations", []),
        "terms": cand.get("terms", []),
    })

    # A draft is created only for postings that are real, specific, and applyable.
    if not (title_found and apply_found):
        result["skip_reason"] = "could not confirm title/apply flow on page"
        return None, result
    if conf < DRAFT_THRESHOLD:
        result["skip_reason"] = "verification_confidence %d below draft threshold %d" % (
            conf, DRAFT_THRESHOLD)
        return None, result

    if eligible:
        classification = "Auto-promote eligible"
    elif conf >= AUTO_PROMOTE_THRESHOLD:
        classification = "High confidence"
    else:
        classification = "Needs manual review"
    result["classification"] = classification
    result["drafted"] = True
    result["auto_promote_eligible"] = eligible

    # AI / full-stack relevance from title + page.
    rl = role.lower()
    if re.search(r"\bai\b|\bml\b|machine learning|artificial intelligence", rl) or \
            category_of(role, cand.get("source_category")) == "AI/ML":
        ai_rel = "High"
    elif re.search(r"machine learning|\bml\b|neural|model training", text, re.I):
        ai_rel = "Medium"
    else:
        ai_rel = "Unclear"
    if re.search(r"full[\s-]?stack", rl):
        fs_rel = "High"
    elif re.search(r"front[\s-]?end|react|vue|angular", text, re.I) and \
            re.search(r"back[\s-]?end|api|django|node|server", text, re.I):
        fs_rel = "Medium"
    else:
        fs_rel = "Unclear"

    techs = extract_techs(text)

    risk_flags = ["Auto-promoted (verification-gated)" if eligible
                  else "Auto-discovered (needs manual review)"]
    if citizen == "Unclear":
        risk_flags.append("Citizenship unclear")
    if "not explicitly stated" in sponsor_note.lower():
        risk_flags.append("Sponsorship unclear")
    if student_level == "Unclear":
        risk_flags.append("Student level unclear")
    if location_type == "Unclear":
        risk_flags.append("Location unclear")
    if js_heavy:
        risk_flags.append("Application page difficult to verify")
    if comp["compensation_note"] == "Unclear":
        risk_flags.append("Compensation unclear")
    if grad_only:
        risk_flags.append("Graduate/advanced-degree-only (not undergraduate-focused)")

    term = "Summer 2026"
    terms = cand.get("terms") or []
    if terms and "Summer 2026" not in terms:
        term = str(terms[0])

    evidence = ("Auto-verified: official %s page returned HTTP 200 on %s; "
                "title '%s' detected; apply flow detected; location '%s'."
                % (source_type, TODAY, role, location))
    if cit_evidence:
        evidence += " Note: %s." % cit_evidence

    fields = {
        "company": company,
        "role": role,
        "category": category_of(role, cand.get("source_category")),
        "location": location,
        "location_type": location_type,
        "internship_term": term,
        "application_url": url,
        "source_url": SOURCE_REPO,
        "source_type": source_type,
        "status": "Open",
        "last_verified_date": TODAY,
        "discovered_date": TODAY,
        "tech_keywords": techs,
        "ai_relevance": ai_rel,
        "full_stack_relevance": fs_rel,
        "student_level": student_level,
        "freshman_sophomore_friendly": fresh_soph,
        "requires_us_citizenship": citizen,
        "sponsorship_note": sponsor_note,
        "work_authorization_note": workauth_note,
        "evidence_notes": evidence,
        "fit_summary": ("%s internship at %s; auto-discovered candidate for "
                        "undergraduate CS students. Verify the official page before "
                        "promoting." % (category_of(role, cand.get('source_category')), company)),
        "risk_flags": risk_flags,
        "compensation_min": comp["compensation_min"],
        "compensation_max": comp["compensation_max"],
        "compensation_currency": comp["compensation_currency"],
        "compensation_period": comp["compensation_period"],
        "compensation_note": comp["compensation_note"],
        "compensation_evidence": comp["compensation_evidence"],
    }
    return fields, result


def write_report(results, drafted, limit, total_input):
    drafted_sorted = sorted(drafted, key=lambda r: -r["confidence"])
    skipped = [r for r in results if not r["drafted"]]
    lines = [
        "# Candidate Review Report",
        "",
        "_Generated by `scripts/verify_candidates.py`. Local, evidence-based "
        "verification of auto-discovered candidates. **Nothing here is in the "
        "dataset** — every draft must be reviewed against its official page and "
        "explicitly promoted._",
        "",
        "**Report date:** %s" % TODAY,
        "**Candidates available (filtered):** %d" % total_input,
        "**Verification attempts:** %d" % len(results),
        "**Drafts created:** %d (limit %d)" % (len(drafted), limit),
        "",
        "## Drafts created (need human review before promotion)",
        "",
    ]
    if drafted_sorted:
        lines.append("| Confidence | Classification | Company | Role | Source | Apply URL |")
        lines.append("|---|---|---|---|---|---|")
        for r in drafted_sorted:
            lines.append("| %d | %s | %s | %s | %s | %s |" % (
                r["confidence"], r["classification"],
                r["company"].replace("|", "\\|"), r["role"].replace("|", "\\|"),
                r["source_type"], r["url"]))
    else:
        lines.append("_No drafts met the confidence threshold this run._")
    lines += [
        "",
        "## Skipped candidates",
        "",
    ]
    if skipped:
        lines.append("| Company | Role | Source | Confidence | Reason |")
        lines.append("|---|---|---|---|---|")
        for r in skipped:
            lines.append("| %s | %s | %s | %d | %s |" % (
                r["company"].replace("|", "\\|"), r["role"].replace("|", "\\|"),
                r["source_type"], r["confidence"], r["skip_reason"]))
    else:
        lines.append("_None._")
    lines += [
        "",
        "## Verification confidence (local only — not a schema field)",
        "",
        "Measures whether the posting is **real, open, official, specific, and "
        "parseable** — not user-fit. Unclear sponsorship / student level / "
        "compensation does **not** lower it.",
        "",
        "+25 reachable official ATS page · +20 title on page · +20 apply flow · "
        "+15 internship/co-op wording · +10 location · +10 clearly technical · "
        "+5 compensation classified · -50 generic/search/Simplify/raw-API/private "
        "board · -40 JS-heavy / non-internship / nontechnical / senior-fulltime · "
        "-100 duplicate URL. Draft at **>= 70**; **Auto-promote eligible** requires "
        "**>= 90** AND no hard blocker (incl. graduate-only — a blocker that does "
        "not lower confidence, so flagged drafts are still produced).",
        "",
        "> Lower-confidence drafts stay here for human review: promote with "
        "`python scripts/promote_candidate.py pending/auto/<file>.md`. "
        "High-confidence eligible candidates can be auto-promoted by "
        "`scripts/auto_update_verified.py`.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main(argv):
    parser = argparse.ArgumentParser(description="Verify discovered candidates.")
    parser.add_argument("--limit", type=int, default=10,
                        help="max drafts to create this run (default 10)")
    args = parser.parse_args(argv[1:])
    limit = max(1, args.limit)

    if not INPUT_PATH.exists():
        print("ERROR: %s not found. Run discover_candidates.py first."
              % INPUT_PATH, file=sys.stderr)
        return 1
    try:
        candidates = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    except ValueError as exc:
        print("ERROR: could not parse %s: %s" % (INPUT_PATH, exc), file=sys.stderr)
        return 1

    PENDING_AUTO.mkdir(parents=True, exist_ok=True)
    candidates.sort(key=ats_rank)  # prefer Greenhouse/Lever/Ashby first

    global EXISTING_URL_KEYS
    EXISTING_URL_KEYS = load_existing_url_keys()

    attempts_cap = max(20, limit * 4)
    results = []
    drafted = []
    drafts_created = 0

    print("Verifying candidates (limit %d, attempt cap %d)..." % (limit, attempts_cap))
    for cand in candidates:
        if drafts_created >= limit or len(results) >= attempts_cap:
            break
        fields, result = verify_one(cand)
        results.append(result)
        if result["drafted"] and result["auto_promote_eligible"]:
            status_word = "PROMO"
        elif result["drafted"]:
            status_word = "DRAFT"
        else:
            status_word = "skip "
        print("  [%s] conf=%3d %-9s %s — %s"
              % (status_word, result["confidence"], result["source_type"],
                 result["company"][:24], result["role"][:40]))
        if fields:
            fname = "auto_%s_%s_%s.md" % (TODAY, sanitize(fields["company"]),
                                          sanitize(fields["role"]))
            (PENDING_AUTO / fname).write_text(
                build_draft(fields, result["confidence"], result["classification"]),
                encoding="utf-8")
            result["draft_file"] = "pending/auto/%s" % fname
            drafted.append(result)
            drafts_created += 1

    (TMP_DIR / "candidates_verified.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(results, drafted, limit, len(candidates))

    eligible = [r for r in drafted if r.get("auto_promote_eligible")]
    print("-" * 60)
    print("Attempts: %d | Drafts: %d | Auto-promote eligible: %d | Skipped: %d"
          % (len(results), len(drafted), len(eligible), len(results) - len(drafted)))
    print("Report: docs/candidate_review_report.md")
    print("Machine-readable: tmp/candidates_verified.json")
    print("NOTE: this script never writes to data/internships.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
