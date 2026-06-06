# InternRadar AI — Dashboard (web/)

A local **Next.js** dashboard that provides a clean, searchable, filterable view
of InternRadar AI's verified internship listings. It is a **read-only frontend
layer** — it never applies to jobs, sends emails, or modifies the dataset.

**Live demo:** https://internradar-ai.vercel.app/

## What it shows

- Summary cards: total verified postings, open postings, AI/ML-relevant,
  full-stack-relevant, citizenship-restricted, and unclear sponsorship/work-auth.
- A card per internship with company, role, location & type, category, status,
  last-verified date, student level, AI/full-stack relevance, citizenship
  requirement, sponsorship & work-authorization notes, risk flags, fit summary,
  and an **Apply** button to the official `application_url`.
- Client-side filters (search, category, location type, status, AI relevance,
  full-stack relevance, citizenship, freshman/sophomore-friendly) and sorting
  (last verified newest, company A–Z, role A–Z).

## How it reads data

The **source of truth is `../data/internships.json`** in the repository root.

The app imports a local, generated copy at `src/data/internships.json` so that
Next.js only needs to read files inside `web/`. That copy is **not** authoritative
and must not be hand-edited — regenerate it from the root dataset:

```
python ../scripts/sync_web_data.py
```

This copies `../data/internships.json` → `src/data/internships.json` without
modifying the source. Re-run it whenever the root dataset changes.

The TypeScript type in `src/lib/types.ts` mirrors `../data/schema.json` exactly.

## Run locally

From inside `web/`:

```
npm install
npm run dev
```

Then open http://localhost:3000.

## Build

`src/data/internships.json` is a **generated copy** — re-sync from the root source
of truth **before building or deploying** so the dashboard does not ship stale
data:

```
python ../scripts/sync_web_data.py   # run from web/, refreshes src/data/internships.json
npm run build
```

(Optionally `npm run start` to serve the production build.) The MVP uses **no
backend database** — the build reads only the local JSON copy.

## Vercel Deployment

Deploy this dashboard from the GitHub repo by importing it into Vercel and using
these settings (no `vercel.json` is needed — set the Root Directory instead):

- **Root Directory:** `web`
- **Framework Preset:** Next.js
- **Build Command:** `npm run build`
- **Install Command:** `npm install`
- **Environment variables:** none required for the current MVP

The dashboard's data is the generated copy `src/data/internships.json`, produced
from the root source of truth `../data/internships.json`. If the root data
changes, run `python ../scripts/sync_web_data.py` and commit the refreshed copy
**before** building or deploying — Vercel builds the committed tree and does not
run the Python sync step. See [`../docs/deployment_notes.md`](../docs/deployment_notes.md).

## Notes

- Dependencies are local to `web/` (`web/node_modules`); nothing is installed
  globally.
- Tech: Next.js (App Router) + TypeScript + Tailwind CSS. No backend, no database.
- **Reminder:** postings change without notice. Always verify status, deadlines,
  eligibility, and citizenship/sponsorship requirements on the company's official
  application page before applying. Nothing here is legal or immigration advice.
