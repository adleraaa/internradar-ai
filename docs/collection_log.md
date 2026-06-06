# Collection Log

A running record of verification batches for InternRadar AI. Each batch notes the
date, sources checked, roles accepted/skipped (with reasons), and the high-level
method used.

> **Reminder:** Postings change without notice. Users must verify every detail —
> status, deadlines, eligibility, citizenship/sponsorship/work-authorization — on
> the company's **official application page** before applying.

---

## Batch 1 — 2026-06-05

**Collected by:** maintainer (assisted), verification-first smoke test.
**Target:** 3–5 verified, currently-open CS/AI/full-stack internships.

### Sources checked

- Public discovery source: **SimplifyJobs / Summer2026-Internships** GitHub repo
  (`.github/scripts/listings.json`, ~17,121 records) — used only to *discover*
  candidate roles, never as the final application link.
- **Official application pages** for each accepted role (Greenhouse and Ashby),
  fetched and verified directly over HTTPS from the terminal.

### Method (high level)

1. Downloaded the repo's `listings.json` to `tmp/` and filtered for `active` +
   `is_visible` internship roles in Software / AI/ML / Data categories whose
   `url` pointed at a **direct ATS** (Greenhouse / Lever / Ashby), not a Simplify
   redirect.
2. For each candidate, verified the **official** posting via the ATS's public API
   (`boards-api.greenhouse.io`, `api.ashbyhq.com/posting-api`) and by fetching the
   **human-facing application page** with PowerShell `Invoke-WebRequest`:
   confirmed HTTP 200, that the page still shows the exact role title, and that an
   Apply flow is present.
3. Scanned each posting for short evidence only — internship term, location,
   class-year/degree language, and any citizenship/sponsorship/work-authorization
   wording. No full job descriptions were copied.
4. Wrote a reviewed Markdown draft per role in `pending/`, converted it with
   `scripts/submission_to_json.py`, saved the JSON under `tmp/`, appended with
   `scripts/append_entry.py`, and ran `scripts/validate_data.py`.
5. Moved the reviewed drafts to `reviewed/` as an audit trail.

### Roles accepted (5)

| Company | Role | Location | Source type | Application URL |
|---------|------|----------|-------------|-----------------|
| BillionToOne | Software Engineering Intern | Menlo Park, CA | Greenhouse | https://job-boards.greenhouse.io/billiontoone/jobs/4702398005 |
| Attentive | AI Intern | New York, NY | Greenhouse | https://job-boards.greenhouse.io/attentive/jobs/4209296009 |
| Podium | Software Engineering Intern | Lehi, UT | Greenhouse | https://job-boards.greenhouse.io/podium81/jobs/7939921 |
| Dryft | Full-Stack Engineering Intern | San Francisco, CA | Ashby | https://jobs.ashbyhq.com/dryft/3f1c261d-9b65-412b-9f17-34b8968bdd78/application |
| Astranis | Software Engineer Intern - Data Platform | San Francisco, CA | Greenhouse | https://job-boards.greenhouse.io/astranis/jobs/4667477006 |

Notes:
- **Astranis** is flagged as **ITAR / U.S.-person restricted** (citizenship, LPR,
  refugee, or asylee status required); most F-1/OPT/CPT international students are
  not eligible. Captured in `work_authorization_note` and `risk_flags`.
- **Dryft** posting states the team "supports visa," so the role is recorded as
  not citizenship-restricted (`requires_us_citizenship: No`).
- Where class year was not stated, `student_level` and/or
  `freshman_sophomore_friendly` were left **Unclear** rather than guessed.

### Roles skipped (with reasons)

- **Octaura — Intern, Data Engineering (NYC):** verifiable and active, but the
  official title differs from the listing and the page was last updated
  2026-02-19 (older); deprioritized to keep the batch focused on five fresher
  roles.
- **Labelbox — Forward Deployed Engineer Intern (SF):** customer-facing
  "forward deployed" role; weaker fit for the core SWE/AI/full-stack focus.
- **Workday- and iCIMS-hosted roles (e.g. RTX and ~40+ others):** skipped as a
  class because those pages are JavaScript-rendered and could not be reliably
  verified as open via raw terminal HTTP without browser automation (prohibited).
- **Mariana Minerals non-software interns** (Mechanical / Chemical / Geology /
  Field / Process / Project Engineering): not CS / AI / full-stack / technical
  data roles.
- **Inactive listings** (`active: false`, e.g. RTX "Software Fellow Engineer
  Intern"): marked inactive in the source and not re-verified as open.
- **Any role reachable only through a Simplify redirect row** with no confirmable
  official page: not used as a final application link.

### Result

- Appended: **5** entries. Validation: **PASSED** (0 errors, 0 warnings).
- Dataset: `data/internships.json` now contains 5 verified, currently-open roles.
