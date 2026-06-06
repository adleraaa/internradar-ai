# Contributing to InternRadar AI

Thank you for helping build a **verification-first** internship tracker. The
single most important rule: **never add data you have not verified.** A small,
trustworthy list is more valuable than a large, stale one.

Please read [`search_rules.md`](search_rules.md) and
[`docs/verification_policy.md`](docs/verification_policy.md) before submitting.

## What You May Submit

Real internship roles for undergraduate CS students (Software Engineering,
AI/ML, Data Science, Full-Stack, and adjacent) that you have personally
verified against an **official source**.

## Required Information for Every Submission

Every internship entry **must** include:

- **Company name** — the actual hiring company.
- **Role title** — as written on the official posting.
- **Official application link** — the company's own posting or its official ATS
  (Greenhouse, Lever, Ashby, Workday). See "Link Rules" below.
- **Location** — city/state/country, or "Remote".
- **Internship term** — e.g. "Summer 2026".
- **Last verified date** — the date you personally confirmed the posting was
  reachable and its status. Use `YYYY-MM-DD`.
- **Evidence** — for any claim about **citizenship requirements**, **sponsorship
  / CPT / OPT**, or **work authorization**, you must include a short
  `evidence_notes` entry quoting or paraphrasing the relevant line from the
  posting. No evidence → mark the field `Unclear`.

## Hard Rules

1. **No full JD copying.** Do not paste full job descriptions. Store the link
   plus short, factual notes only. Quote at most a sentence when needed as
   evidence.
2. **No unofficial third-party links** unless an official link genuinely does
   not exist. If you must use one, mark `source_type` accordingly and explain in
   `evidence_notes` why no official link was available.
3. **No fake, guessed, or hallucinated data.** Do not invent postings, fill in
   plausible-looking values, or "guess" eligibility. Unknown → `Unclear`.
4. **No optimistic status.** Mark `Open` only if the official application page is
   reachable and still appears to accept applications.
5. **No citizenship/sponsorship claims without evidence.** "Green card OK" / "No
   citizenship required" requires explicit or strongly inferable evidence from
   the posting.

## Submission Workflow

Use the local tooling rather than hand-editing `data/internships.json`:

1. **Draft** — start from
   [`templates/internship_submission_template.md`](templates/internship_submission_template.md),
   or generate a draft with `python scripts/new_submission.py`. Drafts live in
   [`pending/`](pending/) and are named `YYYY-MM-DD_company_role.md`.
2. **Review** — open the **official** application page, confirm status and
   eligibility, and fill in the draft. Quote only short evidence snippets; never
   paste full job descriptions.
3. **Convert** — `python scripts/submission_to_json.py pending/<file>.md` prints a
   validated JSON object to stdout. Save it to a temporary local file.
4. **Append** — `python scripts/append_entry.py <json-file>` checks for duplicate
   `id`s, a present `application_url`, a present `last_verified_date`, and valid
   enums, then appends and re-sorts the dataset.
5. **Validate** — run `python scripts/validate_data.py` and fix all errors and
   warnings before submitting your change.
6. **Archive the draft** — optionally move the reviewed Markdown from `pending/`
   to [`reviewed/`](reviewed/) as an audit trail.

### Maintainer acceptance rules

Maintainers must **not** accept an entry that lacks any of:

- A **concrete, human-facing official application link** (`application_url`).
- A **last verified date** (`last_verified_date`), confirmed against the official
  page and in `YYYY-MM-DD` format.
- **Evidence notes** (`evidence_notes`) for any definite **work authorization**,
  **citizenship**, or **sponsorship** claim. No evidence → the relevant field
  must be `Unclear`.

Entries failing `python scripts/validate_data.py` must not be merged.

## Field Conventions

- Dates use `YYYY-MM-DD`.
- Enum fields must use one of the allowed values in `data/schema.json` exactly.
- When in doubt about any enum (status, citizenship, relevance), choose
  `Unclear` rather than guessing.
- Keep `evidence_notes`, `fit_summary`, and `work_authorization_note` short and
  factual.

## Review Checklist (before you submit)

- [ ] Official application link included and reachable.
- [ ] `last_verified_date` is today and in `YYYY-MM-DD` format.
- [ ] `status` reflects what you actually observed.
- [ ] Every citizenship / sponsorship / work-authorization claim has matching
      `evidence_notes`.
- [ ] No full job description text was pasted.
- [ ] `python scripts/validate_data.py` passes with no errors.
