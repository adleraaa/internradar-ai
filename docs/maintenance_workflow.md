# Maintenance Workflow

How to keep InternRadar AI's dataset accurate, fresh, and trustworthy over time.
This complements [`../CONTRIBUTING.md`](../CONTRIBUTING.md),
[`../search_rules.md`](../search_rules.md), and
[`verification_policy.md`](verification_policy.md).

Guiding principle: **verify, don't guess.** A small, fresh, evidence-backed list
beats a large, stale one.

---

## End-to-end workflow

1. **Find a candidate role.** Use an acceptable discovery source (official career
   page, an official ATS, or a reputable aggregator used only as a starting
   point).
2. **Verify the official, human-facing application page.** Open the company's own
   posting or its official ATS page (Greenhouse, Lever, Ashby, Workday, iCIMS).
   Confirm the page loads, still shows the **specific role**, and has a live
   **Apply** flow. Never rely on a job-board row alone. **Also check for an
   explicit pay figure** on that page — record it in the `compensation_*` fields,
   or mark `Unclear` if none is listed. Never use estimate sites.
3. **Create a pending Markdown draft.** Run `python scripts/new_submission.py`
   (or copy [`../templates/internship_submission_template.md`](../templates/internship_submission_template.md))
   to produce a draft in `pending/`. Record only short evidence snippets.
4. **Convert to JSON.** Run
   `python scripts/submission_to_json.py pending/<file>.md` and save the JSON to a
   temporary file under `tmp/`.
5. **Append to the dataset.** Run `python scripts/append_entry.py tmp/<file>.json`.
   It refuses duplicate `id`s and entries missing `application_url` or
   `last_verified_date`.
6. **Validate.** Run `python scripts/validate_data.py` and fix every error.
7. **Audit data quality.** Run `python scripts/audit_data_quality.py` and resolve
   errors; review warnings.
8. **Generate the README table.** Run `python scripts/generate_readme_table.py`
   to refresh `docs/internships_table.md` and the README table section.
9. **Generate the status report.** Run `python scripts/generate_status_report.py`
   to refresh `docs/status_report.md`.
10. **Re-check old postings periodically.** Use the status report's
    "Needs re-verification soon" list to find entries to re-verify.

After a successful append, move the reviewed Markdown draft from `pending/` to
`reviewed/` as an audit trail.

## Quick command sequence

```
python scripts/validate_data.py
python scripts/audit_data_quality.py
python scripts/generate_readme_table.py
python scripts/generate_status_report.py
python scripts/validate_data.py
```

---

## Automated (assisted) workflow

Discovery and verification are automated, but promotion stays human and explicit.
See [`automation_policy.md`](automation_policy.md) for the rules.

1. **Run discovery** — `python scripts/discover_candidates.py` pulls public
   listings, filters them, and writes `tmp/candidates_filtered.json`.
2. **Run verification** — `python scripts/verify_candidates.py --limit 10` fetches
   each candidate's official page, scores confidence, and writes review drafts to
   `pending/auto/` plus `docs/candidate_review_report.md`. Nothing touches the
   dataset.
3. **Review `pending/auto/` drafts** — open each one's official application page,
   confirm the role/status/eligibility, and correct any `Unclear` fields. Drafts
   are labeled "High confidence" or "Needs manual review".
4. **Promote selected candidates** —
   `python scripts/promote_candidate.py pending/auto/<file>.md` (add
   `--allow-needs-review` for the latter group). It refuses non-`Open` or
   duplicate entries, appends, and regenerates artifacts.
5. **Run the quality gate** — `python scripts/check_all.py`.
6. **Commit & push** — `git add -A && git commit && git push`.
7. **Vercel redeploys automatically** from the pushed `main` branch.

---

## When to mark a job `Closed`

Mark `status: Closed` when, on the official page, any of these is true:

- The posting no longer exists (404 / removed).
- The page explicitly says the role is closed or no longer accepting applications.
- The Apply flow is gone or disabled.

If you simply **cannot tell** (page unreachable, login-walled, ambiguous), mark
`Unclear` — not `Closed` and not `Open`. Closed entries may later be moved to
`archive/`.

## When to update `last_verified_date`

- Set it to **today** (`YYYY-MM-DD`) **only** when you have just loaded the
  official page and confirmed the role and its status yourself.
- Update it on every re-verification, even if nothing else changed — it records
  *freshness*, not *last edit*.
- Never set it to a future date, and never copy an old date forward without
  actually re-checking. Also update `date_updated` when you change an entry.

## Why official links matter

The whole project's value is trust. An official, human-facing application page is
the only source that reliably reflects the role's real existence, status, and
eligibility. Generic careers homepages, search pages, raw API endpoints,
community-tracker rows, and aggregator redirects can all be stale, ambiguous, or
misleading — so they are **not** acceptable as the final `application_url`.
`scripts/audit_data_quality.py` flags links that look like these.

## Why `Unclear` is better than guessing

`Unclear` is an honest, useful signal. Guessing — especially about
**citizenship, sponsorship, or work authorization** — can send a student to apply
for something they're ineligible for, or scare them away from something open to
them. If the posting doesn't state it explicitly (or strongly imply it), record
`Unclear` and capture what you *did* see in `evidence_notes`.

## Do not copy full job descriptions

Store the **link** plus **short factual notes** and at most ~1-sentence evidence
snippets. Never paste full JD text into drafts, the dataset, or the docs. This
keeps the repo clean, respectful of sources, and focused on verification rather
than re-hosting content.
