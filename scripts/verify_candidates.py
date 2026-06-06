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

## Notes & summary (maintainer must verify; never copied JD text)

- **evidence_notes:** {evidence_notes}
- **fit_summary:** {fit_summary}
- **risk_flags:** {risks}
""".format(confidence=confidence, classification=classification, techs=techs, risks=risks, **f)


def verify_one(cand):
    """Return (fields_or_None, result_dict). fields is None if no draft."""
    url = cand.get("url", "")
    role = cand.get("title", "")
    company = cand.get("company", "")
    source_type = source_type_of(url)
    result = {
        "company": company, "role": role, "url": url,
        "source_type": source_type, "confidence": 0,
        "classification": "Skipped", "drafted": False, "skip_reason": "",
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
    technical = bool(RELEVANT_TITLE_RE.search(role)) or \
        (cand.get("source_category", "").lower() in
         ("software", "data science", "ai/ml", "data"))

    location, location_type, loc_found = location_fields(cand.get("locations"))
    student_level = detect_student_level(text)
    fresh_soph = detect_fresh_soph(text)
    citizen, sponsor_note, workauth_note, cit_evidence = detect_citizenship(text)

    js_heavy = (source_type in ("Workday", "iCIMS") and not title_found) or \
        (len(text) < 600 and not title_found)
    non_official = source_type == "Company Career Page" and not title_found

    # --- Confidence scoring (local-only) ---
    score = 0
    score += 30  # reachable page (status 200)
    if title_found:
        score += 20
    if apply_found:
        score += 20
    if intern_found:
        score += 10
    if loc_found:
        score += 10
    if technical:
        score += 10
    if citizen == "Unclear":
        score -= 20  # work authorization unclear
    if student_level == "Unclear":
        score -= 20
    if js_heavy:
        score -= 30
    if non_official:
        score -= 50
    score = max(0, min(100, score))
    result["confidence"] = score

    # Only create a draft for verified, active-looking pages.
    if not (title_found and apply_found):
        result["skip_reason"] = "could not confirm title/apply flow on page"
        return None, result
    if score < 70:
        result["skip_reason"] = "confidence %d below threshold 70" % score
        return None, result

    classification = "High confidence" if score >= 90 else "Needs manual review"
    result["classification"] = classification
    result["drafted"] = True

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

    risk_flags = ["Auto-discovered (needs manual review)"]
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
        "## Confidence scoring (local only — not a schema field)",
        "",
        "+30 reachable official ATS page · +20 title on page · +20 apply flow · "
        "+10 internship wording · +10 location · +10 clearly technical · "
        "-20 work-auth unclear · -20 student level unclear · -30 JS-heavy/hard to "
        "verify · -50 generic/non-official link. Draft created at **>= 70**; "
        "**>= 90** = High confidence, **70-89** = Needs manual review.",
        "",
        "> Promote with `python scripts/promote_candidate.py pending/auto/<file>.md` "
        "only after verifying the official page yourself.",
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
        status_word = "DRAFT" if result["drafted"] else "skip "
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

    print("-" * 60)
    print("Attempts: %d | Drafts created: %d | Skipped: %d"
          % (len(results), len(drafted), len(results) - len(drafted)))
    print("Report: docs/candidate_review_report.md")
    print("Drafts: pending/auto/")
    print("NOTE: nothing was added to data/internships.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
