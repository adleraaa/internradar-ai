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

## Full-auto workflow

`scripts/auto_update_verified.py` runs discovery → verification → conservative
auto-promotion → regeneration → checks → optional commit/push in one command. See
[`automation_policy.md`](automation_policy.md) for the gates.

1. **Run a dry-run first** — `python scripts/auto_update_verified.py --limit 20`.
   It changes nothing in `data/internships.json`; it only reports which
   high-confidence candidates *would* be promoted.
2. **Review the summary** — check the eligible candidates, skip reasons, and
   confidence scores. Lower-confidence candidates stay in `pending/auto/`.
3. **Run full-auto apply mode** —
   `python scripts/auto_update_verified.py --limit 50 --max-promote 5 --min-confidence 90 --apply --commit --push`.
   (Drop `--commit --push` to apply locally without publishing.)
4. **Confirm `check_all` passes** — the pipeline runs it automatically and refuses
   to commit if validation, audit, build, or any invariant fails.
5. **Confirm Vercel redeploys** from the pushed `main` branch.
6. **Spot-check the live site** at <https://internradar-ai.vercel.app/> — verify a
   newly promoted role appears with the correct Pay and official Apply link.

---

## Re-verify and prune existing postings

Freshness cuts both ways: as well as adding postings, maintenance re-checks the
ones already listed and removes those that have genuinely closed. This is what
`scripts/reverify_existing.py` does (conservatively — see
[`automation_policy.md`](automation_policy.md) for the full rules).

1. **Dry-run first** — `python scripts/reverify_existing.py`. It fetches every
   active entry's official page, classifies each **keep / warn / remove**, and
   writes `docs/reverification_report.md` and `tmp/reverification_results.json`.
   It changes **nothing**.
2. **Review the report** — confirm that anything marked **remove** really is a
   deterministic failure (404/410, an explicit closed/filled/expired banner, a
   final URL that is now generic/private/api/search, or title-gone-and-no-apply).
   Transient errors (timeout, DNS, 429, 5xx) and ambiguity are always **warn**
   (kept), never removed.
3. **Apply** — `python scripts/reverify_existing.py --apply --max-remove 5`. Each
   removed entry is archived to `archive/removed_internships.json` **before**
   deletion, capped by `--max-remove`. Add `--fail-on-remove-over-limit` to abort
   (mutating nothing) if more than the cap would be removed. Add
   `--refresh-verified` to bump `last_verified_date` on re-confirmed-open roles.
4. **Run the quality gate** — `python scripts/check_all.py`, then review
   `git diff`, commit, and push.

To do both at once (prune closed, then add new) use the full-auto pipeline with
`--prune-closed`:

```
# Dry-run: see what would be pruned and promoted, change nothing.
python scripts/auto_update_verified.py --limit 20 --max-promote 3 --min-confidence 90 --prune-closed

# Apply: prune deterministic failures (cap 5), then add high-confidence postings.
python scripts/auto_update_verified.py --limit 50 --max-promote 5 --min-confidence 90 --apply --prune-closed --max-remove 5
```

Re-verification runs **before** discovery; if it fails, the pipeline stops before
adding anything. `--skip-reverify` disables the prune step even when
`--prune-closed` is given.

---

## Run the pipeline from GitHub Actions

The full-auto pipeline runs **daily on a schedule** and can also be run manually
from the browser via the **"Auto Update Verified Internships"** workflow (see
[`automation_policy.md`](automation_policy.md)).

- **Daily schedule.** A cron (`0 15 * * *` UTC ≈ 08:00 America/Los_Angeles, ±1h
  across DST) adds new high-confidence postings and prunes
  deterministically-closed ones, then commits and pushes. No action needed.
- **Manual dry-run.** Go to the **Actions** tab → **Auto Update Verified
  Internships** → **Run workflow**, leaving `apply`, `push_changes`, and
  `prune_closed` unchecked (the defaults). This changes nothing.
- **Manual apply.** Run again with `apply=true` (and `push_changes=true`, and
  `prune_closed=true` if you want to prune) only when comfortable with what it
  would change; keep `max_promote`/`max_remove` small. The guard refuses
  `push_changes=true` unless `apply=true`.
- **Check the Vercel redeploy** and the live site after a push completes.

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
