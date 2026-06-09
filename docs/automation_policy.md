# Automation Policy

InternRadar AI uses **assisted automation, not blind auto-append**. Scripts can
*discover* and *verify* internship candidates, but a human must review each one
and explicitly promote it before it enters `data/internships.json`. This protects
the project's verification-first positioning.

## Why assisted, not automatic

The dataset's value is **trust**: every entry links to an official application
page and carries a `last_verified_date`. Fully automatic scraping would
reintroduce exactly the problems the project exists to solve — dead links, stale
or closed roles, mis-read eligibility, and hallucinated fit. So automation stops
at **reviewable candidates**; promotion stays human and explicit.

## Pipeline

```
discover_candidates.py  →  tmp/candidates_filtered.json
verify_candidates.py    →  pending/auto/*.md  +  docs/candidate_review_report.md
   (human review of each draft against the official page)
promote_candidate.py    →  data/internships.json   (explicit, one draft at a time)
```

- **Discovery** pulls public listings, normalizes them, and filters for relevant,
  active, well-linked internship candidates.
- **Verification** fetches each candidate's official page over plain HTTP, checks
  the role and apply flow, scores confidence, and writes review drafts to
  `pending/auto/`. It never writes to the dataset.
- **Promotion** is a separate, explicit command that takes one reviewed draft and
  appends it after status/duplicate checks, then regenerates derived artifacts.

## Allowed sources

- Public, official career pages and public ATS pages:
  **Greenhouse, Lever, Ashby, Workday, iCIMS**.
- Public aggregator **data files** used only for *discovery* (e.g. the
  SimplifyJobs / Summer2026-Internships public listings JSON) — never used as the
  final application link.

## Disallowed sources

- **LinkedIn, Handshake, Indeed, Glassdoor, ZipRecruiter** or any login-gated /
  private job board.
- **Simplify redirect links** as the final `application_url` (discovery only).
- Generic careers **homepages**, **search/query** pages, and **raw API** endpoints
  as the final application link.
- Anything requiring **browser automation** or a logged-in session.

## Verification rules

- Fetch the **human-facing application URL** over plain HTTP (no browser).
- Confirm the page is reachable (HTTP 200), the **role title** (or a close
  variant) appears, and an **apply indicator** is present.
- Prefer **Greenhouse / Lever / Ashby** (reliably verifiable from raw HTML).
- **Skip JS-heavy pages** (often Workday/iCIMS) that can't be confirmed from
  terminal HTTP — they are listed as skipped in the report, not drafted.
- **Never guess** work authorization, citizenship, sponsorship, or student level.
  If not explicit, mark `Unclear`. Never mark "Green Card OK" without evidence.
- **Never copy full job descriptions** — evidence notes are short, factual, and
  derived from page metadata, not pasted JD text.
- `status` may be `Open` only if the official page appears active.
- **Compensation** is detected only from **explicit** pay text on the official
  page (e.g. "$25 per hour", a posted range, "unpaid"). If none is found, the
  draft's `compensation_*` fields default to `Unclear` / `null`. The pipeline
  never uses Glassdoor, Levels.fyi, Reddit, or salary estimates, and treats
  funding/revenue figures as **not** pay. Generated `pending/auto` drafts always
  include the six compensation fields for the maintainer to verify.

## Confidence scoring (local only — not a schema field)

Each verified candidate gets a local score; it is recorded in the report, not in
the dataset:

| Signal | Points |
|---|---|
| Reachable official ATS page | +30 |
| Role title appears on page | +20 |
| Apply indicator found | +20 |
| Internship wording on page | +10 |
| Location found | +10 |
| Clearly CS / SWE / AI / data technical | +10 |
| Work authorization unclear | −20 |
| Student level unclear | −20 |
| JS-heavy / hard to verify | −30 |
| Generic / non-official link | −50 |

- A draft is created only at **confidence ≥ 70**.
- **≥ 90** → "High confidence"; **70–89** → "Needs manual review".
- Neither group is auto-appended. Both require human promotion.

## Why `pending/auto/` exists

It separates machine-proposed candidates from human-verified data. A file there
means "worth a look," not "trusted." The dataset stays the single source of
truth; `pending/auto/` is a staging area, never authoritative.

### Generated drafts are local-only

The generated `pending/auto/auto_*.md` drafts are **local review artifacts and are
gitignored** — they are regenerated on demand and not committed, which keeps the
public repository from accumulating stale candidate drafts. What stays tracked:

- the **verified dataset**, `data/internships.json` (the single source of truth);
- the **concise review summary**, `docs/candidate_review_report.md`;
- `pending/auto/README.md` (this folder's documentation).

Full-auto can promote high-confidence candidates into the dataset without
committing every draft.

## How to promote a candidate

```
python scripts/promote_candidate.py pending/auto/<candidate-file>.md
```

- Drafts marked **"Needs manual review"** require `--allow-needs-review`, after a
  maintainer has personally checked the official page.
- Promotion refuses entries whose `status` is not `Open` or whose
  `application_url` already exists in the dataset.
- After promoting, run `python scripts/check_all.py`, review `git diff`, then
  commit and push.

## Why human review is still required

Automated checks can confirm a page loads and shows an apply button, but they
cannot reliably judge eligibility nuance (ITAR/citizenship phrasing, class-year
limits, sponsorship intent) or whether a role truly fits an undergraduate. A
human keeps the bar high — which is the entire point of InternRadar AI.

## Full Auto-Promotion Mode

`scripts/auto_update_verified.py` adds an optional **full-auto** mode that can
discover, verify, and promote in one command. It is deliberately **conservative**:

- It **only promotes high-confidence official application pages** —
  `verification_confidence >= 90` **and** no hard blocker. Verification confidence
  measures whether a posting is real, open, official, specific, and parseable; it
  is **not** lowered just because sponsorship, student level, or compensation is
  `Unclear`.
- **Hard blockers** (any one prevents promotion): duplicate `application_url`,
  generic careers/search page, Simplify redirect, raw API URL, LinkedIn /
  Handshake / Indeed / other private board, JS-heavy / unverifiable page,
  non-internship role, **a title that does not clearly name an internship/co-op**
  (e.g. a full-time/launch/rotational "program"), nontechnical role, hardware-only
  role, **hardware-adjacent role** (silicon/ASIC/RTL/FPGA/SoC/firmware/embedded/
  design-verification/SDR work), full-time / new-grad / senior / staff /
  manager-only role, **graduate-only / advanced-degree-only role**, status not
  `Open`, or any missing required field.
- It **never uses private / login-gated boards** and **never uses third-party
  salary sources** (Glassdoor, Levels.fyi, Reddit, estimates, averages). It does
  **not guess** compensation or work authorization.
- It **allows `Unclear`** when the official page is silent — accurately recording
  ambiguity is acceptable and does not block promotion.
- **Lower-confidence candidates stay in `pending/auto/`** for human review; they
  are never auto-promoted.
- After any promotion it regenerates the README table, status report, and web
  data, then runs validation, audit, and the build, and verifies invariants
  (no existing entry removed/changed, no duplicate URLs, web copy matches root).
  If anything fails, it does **not** commit.

**Dry-run (default — no dataset changes, no commit, no push):**

```
python scripts/auto_update_verified.py --limit 20
```

**Recommended full-auto run:**

```
python scripts/auto_update_verified.py --limit 50 --max-promote 5 --min-confidence 90 --apply --commit --push
```

Safety interlocks: `--push` requires `--commit`, and `--commit` requires
`--apply`. Without `--apply` the run is a dry-run only.

### Graduate-only role blocker

InternRadar AI targets **undergraduate CS students**, so the pipeline does **not**
auto-promote roles that clearly target graduate students only:

- **Blocked:** PhD / Ph.D. / Doctoral interns, MBA interns, master's-only or
  graduate-only roles, and postings that explicitly require an advanced degree
  (e.g. "currently pursuing a PhD", "master's degree required", "MS/PhD required").
- **Not blocked (mixed eligibility):** roles open to a range of degrees, such as
  "Bachelor's or Master's", "B.S. or M.S.", "undergraduate or graduate students",
  or "pursuing a Bachelor's, Master's, or PhD". These remain eligible.
- A graduate-only role that is otherwise verified may still produce a draft in
  `pending/auto/` (flagged "Graduate/advanced-degree-only (not
  undergraduate-focused)"), but it is **never auto-appended** to the dataset; a
  maintainer can promote it manually if they choose.

The machine-readable verification output records `graduate_only_detected` and a
short `graduate_only_evidence`, and the blocker reason
`"graduate-only or advanced-degree-only role"` appears in `auto_promote_blockers`.

### Title-level and hardware-adjacent blockers

Auto-promotion is limited to clearly undergraduate-appropriate software / AI /
data internships. Two additional gates keep ambiguous roles out of the dataset:

- **Title-level internship required.** Auto-promotion requires the **title** to
  clearly name an internship/co-op role. A title that is really a full-time,
  launch, rotational, or "high-potential" **program** (even if it contains the
  word "intern") is blocked with `"title does not clearly identify an internship
  or co-op role"`. (`title_level_internship_detected` / `_evidence`.)
- **Hardware-adjacent roles are manual review by default.** Software-titled roles
  whose title or page points to silicon/ASIC/RTL/FPGA/SoC, design verification,
  firmware, embedded, board bring-up, or SDR/RF work are blocked with
  `"hardware-adjacent role requires manual review"`.
  (`hardware_adjacent_detected` / `_evidence`.)
- **Graduate-intern titles** (e.g. "Software Graduate Intern") are blocked unless
  the page makes undergraduate eligibility explicit.

As with the other fit gates, **these do not lower verification confidence** — the
posting is still real and parseable, so it can still appear as a flagged draft in
`pending/auto/` for optional manual review; it is simply not auto-promoted.

## GitHub Actions manual run

The same full-auto pipeline can be triggered from GitHub Actions via the
**"Auto Update Verified Internships"** workflow
(`.github/workflows/auto-update-internships.yml`).

- **Manual only.** It uses `workflow_dispatch` with no schedule/cron — it never
  runs on its own.
- **Dry-run is the default.** The `apply` and `push_changes` inputs default to
  `false`, so a plain run discovers and verifies candidates **without** changing
  `data/internships.json`.
- **`apply=false` does not change the dataset** — it only reports what *would* be
  promoted.
- **`push_changes=true` requires `apply=true`.** The workflow has a shell guard
  that fails fast on the unsafe combination, mirroring the script's own
  `--push` ⇒ `--commit` ⇒ `--apply` interlocks.
- **When a push happens, Vercel redeploys automatically** from `main`. The
  workflow uses the repository's auto-provided token for a normal `git push`
  (never `--force`); no Vercel token or other secret is used.
- **Keep `max_promote` conservative** (e.g. 3–5) so each run adds only a small,
  reviewable batch of high-confidence postings.
