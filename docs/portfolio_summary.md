# Portfolio Summary — InternRadar AI

A ready-to-adapt summary for a resume, GitHub README, LinkedIn post, or
application. Edit freely. **Please keep it honest:** this is an early MVP with a
small, manually verified dataset — do not claim users, traffic, revenue, or
production adoption it does not have.

## Two-sentence description

InternRadar AI is a verification-first internship tracker for undergraduate CS
students that prioritizes official application links, freshness checks, and
evidence-based fit tags over raw volume. It pairs a validated JSON dataset and
standard-library Python tooling with a read-only Next.js dashboard for searching
and filtering verified roles.

## Problem solved

Internship lists and aggregators fill up with dead links, stale postings, and
roles that quietly require U.S. citizenship or won't sponsor international
students — so students waste time on listings that were never open to them.
InternRadar AI fixes the trust problem first: every entry points to an official
application page, carries a last-verified date, and marks anything uncertain as
`Unclear` instead of guessing.

## Technical stack

- **Data:** JSON dataset with a JSON Schema contract (`data/schema.json`).
- **Tooling:** Python 3 (standard library only) — validation, quality audit,
  Markdown/table generation, status reporting, and a web-data sync step.
- **Frontend:** Next.js (App Router) + TypeScript + Tailwind CSS; no backend,
  no database.
- **Quality gate:** a single `scripts/check_all.py` command runs validation,
  audit, doc generation, sync, and the web build in sequence.

## Key features

- Verified internship entries with official `application_url` and
  `last_verified_date`.
- Honest `Open` / `Closed` / `Unclear` status — never an optimistic guess.
- Work-authorization signals: U.S.-citizenship requirement detection and
  sponsorship / CPT / OPT notes, captured only when evidenced.
- Evidence-based AI and full-stack relevance tags (derived from posting text).
- Auto-generated README table and a data status/freshness report.
- Searchable, filterable, sortable dashboard (search; filters for category,
  location type, status, AI/full-stack relevance, citizenship, and
  freshman/sophomore-friendliness; sorting by recency or name).

## Data quality strategy

- **No hallucinated jobs** — entries correspond to real, official postings.
- **No copied job descriptions** — store links plus short evidence snippets only.
- **Verify, don't guess** — unknown facts are recorded as `Unclear`.
- **Evidence over inference** — citizenship/sponsorship/fit claims must be backed
  by `evidence_notes`.
- **Automated guardrails** — `validate_data.py` and `audit_data_quality.py`
  enforce schema conformance and flag risky links, missing dates, and unbacked
  claims before anything is published.

## What makes it different from generic job boards

Generic boards optimize for quantity. InternRadar AI optimizes for **trust and
verifiability**: official links only, freshness dates on every entry, explicit
work-authorization handling, undergraduate-friendliness signals, and a transparent
verification policy. It is an **AI-assisted, verification-first tracker — not an
auto-apply bot**; it never applies to jobs on a user's behalf.

## Possible resume bullet points

- Built a verification-first internship tracker (Next.js + TypeScript +
  Tailwind; Python standard-library tooling) that enforces official application
  links and last-verified dates over raw listing volume.
- Designed a JSON Schema data contract and standard-library validation + audit
  scripts that block malformed entries, suspicious links, and unevidenced
  eligibility claims.
- Implemented a one-command quality gate (`check_all.py`) chaining validation,
  data-quality audit, doc generation, web-data sync, and a production build.
- Created a searchable/filterable dashboard rendering evidence-based fit tags and
  work-authorization signals, with a single JSON source of truth.

## Possible LinkedIn project post (draft)

> I built **InternRadar AI**, a verification-first internship tracker for
> undergraduate CS students. Instead of chasing volume, it focuses on what
> students actually need to trust a listing: an official application link, a
> last-verified date, and honest "Open / Closed / Unclear" status — with U.S.
> citizenship and sponsorship signals captured only when the posting states them.
>
> Stack: a JSON dataset with a schema contract, standard-library Python tooling
> for validation/auditing/report generation, and a Next.js + TypeScript + Tailwind
> dashboard for searching and filtering. Everything regenerates from one source of
> truth, gated by a single `check_all` command.
>
> It's an AI-assisted, verification-first tracker — not an auto-apply bot. Early
> MVP with a small, hand-verified dataset; feedback welcome.

## Possible GitHub repository description

> Verification-first internship tracker for undergraduate CS students — official
> application links, last-verified dates, evidence-based AI/full-stack tags, and a
> Next.js dashboard. Python tooling, JSON source of truth, no auto-apply.

## Honesty note

This project is an early MVP. The dataset is small and manually verified. Do not
present it as having users, scale, or production deployment unless and until that
is actually true.
