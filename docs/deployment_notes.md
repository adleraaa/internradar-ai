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

## Deploy from GitHub with Vercel

The repo is live at <https://github.com/adleraaa/internradar-ai>. The Next.js app
is in the `web/` subdirectory, so deploy it by pointing Vercel's **Root Directory**
at `web`. No `vercel.json` is needed (see "Why no vercel.json" below).

### Step by step

1. In Vercel, **Add New… → Project → Import Git Repository** and choose
   **`adleraaa/internradar-ai`**.
2. Set the project settings exactly as below, then **Deploy**.

| Setting | Value |
|---|---|
| **Framework Preset** | Next.js |
| **Root Directory** | `web` |
| **Build Command** | `npm run build` |
| **Install Command** | `npm install` |
| **Output Directory** | leave default (Vercel manages `.next` for Next.js) |
| **Environment Variables** | none required for the current MVP |
| **Node version** | a current LTS (the app targets the Next.js 14 / React 18 line) |

### Before every deployment — sync and commit the data copy

Vercel builds from the **committed** tree and does **not** run the Python sync
step. The dashboard reads the generated static copy `web/src/data/internships.json`,
so if `data/internships.json` changed you must regenerate and commit the copy
first:

```
python scripts/sync_web_data.py   # refresh web/src/data/internships.json from the root source of truth
python scripts/check_all.py       # validate, audit, regenerate docs, re-sync, build
git add web/src/data/internships.json   # (plus any regenerated docs)
git commit -m "Refresh web data before deploy"
git push
```

The **source of truth remains `data/internships.json`**; the copy is a generated
build input and must never be hand-edited.

### Why no `vercel.json`

Setting **Root Directory = `web`** in the dashboard is the supported, reliable way
to deploy a Next.js app that lives in a subdirectory. `vercel.json` has no
"root directory" field (it is a project setting, not a config key), and when the
Root Directory is `web`, Vercel reads `vercel.json` from inside `web/`, not the
repo root — so a root-level file would be ignored. Hard-coding `cd web && …` build
commands at the root is fragile and unnecessary. We therefore document the
dashboard settings instead of committing a config file.

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
