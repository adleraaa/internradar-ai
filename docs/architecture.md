# Architecture

InternRadar AI is a **verification-first internship tracker**. It is deliberately
simple: a single trusted JSON dataset, a layer of standard-library Python tools
that validate and derive artifacts from it, and a read-only Next.js dashboard on
top. There is no database and no backend service.

```
                      ┌─────────────────────────────┐
                      │   data/internships.json     │  ← SINGLE SOURCE OF TRUTH
                      │   (schema: data/schema.json)│
                      └──────────────┬──────────────┘
                                     │ (read-only)
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                             ▼
  Validation / Audit          Generators                     Web sync
  validate_data.py            generate_readme_table.py        sync_web_data.py
  audit_data_quality.py       generate_status_report.py             │
        │                            │                              ▼
        ▼                            ▼                  web/src/data/internships.json
   pass/fail gate         README table section,            (generated copy)
                          docs/internships_table.md                │
                          docs/status_report.md                    ▼
                                                       web/ Next.js dashboard (read-only)
```

## Source of truth: `data/internships.json`

Every internship entry lives here, conforming to `data/schema.json`. Nothing else
in the repository is authoritative. Each entry is appended only after a human has
verified it against an official application page (see
[`maintenance_workflow.md`](maintenance_workflow.md) and
[`verification_policy.md`](verification_policy.md)). The entry-authoring tools
(`new_submission.py`, `submission_to_json.py`, `append_entry.py`) write here; the
analysis and presentation tools below only ever **read** it.

## Validation / audit layer

- **`scripts/validate_data.py`** — checks the dataset against the schema: required
  fields, enum values, date formats, and evidence-warning rules. Exits nonzero on
  any error.
- **`scripts/audit_data_quality.py`** — local-only quality checks: duplicate ids /
  application URLs, missing links or dates, suspicious URL shapes (careers
  homepage, search page, raw API, Simplify redirect), empty evidence/fit, and
  missing risk flags when fields are `Unclear`. Errors fail the gate; warnings are
  advisory.

Neither fetches the web; both are deterministic and offline.

## Generated README table and status report

- **`scripts/generate_readme_table.py`** writes
  [`internships_table.md`](internships_table.md) and replaces the content between
  the `<!-- INTERNSHIPS_TABLE_START/END -->` markers in `README.md`. It never
  rewrites unrelated README content.
- **`scripts/generate_status_report.py`** writes
  [`status_report.md`](status_report.md): counts by status/category/location/
  source/citizenship/relevance, note-completeness stats, oldest/newest verified
  dates, and a "needs re-verification soon" list (entries older than 14 days).

These artifacts are **derived** — safe to regenerate at any time.

## Web dashboard layer

`web/` is a **Next.js (App Router) + TypeScript + Tailwind CSS** app with no
backend and no database. It renders summary cards, per-internship cards, and
client-side filters/sorting. `web/src/lib/types.ts` mirrors `data/schema.json`
exactly so the UI never invents fields. The **Apply** button links to the entry's
official `application_url`; the dashboard never applies on the user's behalf.

## Data sync flow

`scripts/sync_web_data.py` copies `data/internships.json` →
`web/src/data/internships.json`. The app imports this local copy so that Next.js
only needs to read files inside `web/`.

### Why the web copy is not the source of truth

The copy is a build input, regenerated from the root dataset on demand. Editing it
directly would silently diverge the dashboard from the verified data. The sync
script reads the root file and overwrites the copy; it never writes back to the
root. Always change `data/internships.json`, then re-sync.

## Why official URLs and `last_verified_date` are core

The project's entire value is **trust**:

- **Official `application_url`** — only the company's own posting (or its official
  ATS) reliably reflects whether a role really exists and is open. Generic careers
  pages, search results, raw API endpoints, and aggregator redirects are rejected.
- **`last_verified_date`** — records when a human last confirmed the role on its
  official page. Freshness is surfaced everywhere (table, status report, dashboard)
  so stale entries are obvious and users are reminded to re-check before applying.

When a fact (status, citizenship, sponsorship, student level) is not explicit, it
is recorded as `Unclear` rather than guessed.

## Possible future extensions

- **Scheduled re-verification** — periodically re-check official pages and update
  `last_verified_date`/`status` (e.g. a cron job or GitHub Action driving the
  existing scripts).
- **Larger verified dataset** — scale the batch collection while keeping the
  verification bar.
- **AI-assisted job classification** — evidence-based tagging of category, AI /
  full-stack relevance, and eligibility, derived strictly from posting text.
- **Resume-fit matching** — rank verified roles against a student's background.
- **Vercel deployment** — host the dashboard (see
  [`deployment_notes.md`](deployment_notes.md)).
- **GitHub Actions checks** — run `scripts/check_all.py` on every change to keep
  the dataset valid and the artifacts in sync.
