# Deployment Notes

How to run and (later) deploy the InternRadar AI dashboard. **Nothing here has
been deployed** — these are instructions for when the user chooses to.

The dashboard lives in `web/` and is a static-friendly **Next.js (App Router) +
TypeScript + Tailwind CSS** app with **no backend and no database**.

## Run locally

From inside `web/`:

```
npm install      # first time only; installs into web/node_modules (local)
npm run dev      # http://localhost:3000
```

## Build

```
python scripts/sync_web_data.py   # run from the repo root, BEFORE building
cd web
npm run build
npm run start                     # optional: serve the production build locally
```

### Always sync data before building or deploying

`scripts/sync_web_data.py` copies `data/internships.json` →
`web/src/data/internships.json`. The app reads the copy, so an un-synced build can
ship stale data. The **source of truth remains `data/internships.json`**; the copy
is a generated build input and must never be hand-edited. (The one-command
`scripts/check_all.py` performs this sync as part of the gate.)

## Vercel deployment considerations

- **Project root / base directory:** set the Vercel project's root directory to
  `web/` (the Next.js app is not at the repo root).
- **Framework preset:** Next.js (auto-detected).
- **Install / build commands:** defaults (`npm install`, `npm run build`) work.
- **Committed data copy:** because Vercel builds from the committed tree, make
  sure `web/src/data/internships.json` is **synced and committed** before
  deploying — Vercel will not run the Python sync step. Re-run
  `python scripts/sync_web_data.py` locally, then commit, then deploy.
- **Node version:** the app targets the Next.js 14 / React 18 line; a current LTS
  Node on Vercel is fine.

> Alternative hosts (Netlify, static export, a container) work too; the same
> "sync data → build → deploy the committed copy" rule applies.

## Secrets and environment variables

- **No environment variables are required** for the current MVP.
- There are **no secrets, API keys, or tokens** in this project — do not add any
  to the dataset, the dashboard, or committed `.env*` files. `.env` and
  `.env.local` are gitignored at the repo root.
- If a future feature needs a secret, use the host's encrypted environment-variable
  settings — never commit it.

## Before sharing publicly — checklist

- [ ] `python scripts/check_all.py` passes (validation, audit, generation, sync,
      web build).
- [ ] `data/internships.json` and `web/src/data/internships.json` match (the sync
      step ensures this).
- [ ] README internship-table markers are intact and the table is current.
- [ ] No secrets or personal data committed; `.gitignore` excludes
      `node_modules/`, `.next/`, `tmp/`, `.env*`, logs, and caches.
- [ ] Every entry still links to an official application page and has a
      `last_verified_date`; consider re-verifying old entries first (see
      [`status_report.md`](status_report.md)).
- [ ] The disclaimer is present: users must verify details on the official company
      page before applying.
