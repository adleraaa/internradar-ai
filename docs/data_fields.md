# Data Fields — Plain-English Reference

This document explains every field in `data/schema.json`. Each internship is one
JSON object inside the top-level array in `data/internships.json`.

Golden rule: **if a value is unknown, use `Unclear` (for enums) or an empty
string / empty array — never guess.**

| Field | Plain English |
|-------|---------------|
| `id` | A stable, unique identifier for the entry. Usually a slug like `company-role-term`. |
| `company` | The hiring company's name. |
| `role` | The role title, written exactly as on the official posting. |
| `category` | The high-level type of role. One of: `Software Engineering`, `AI/ML`, `Data Science`, `Product`, `Hardware`, `Other`. |
| `location` | Human-readable location, e.g. `San Francisco, CA` or `Remote (US)`. |
| `location_type` | The work arrangement. One of: `Remote`, `Hybrid`, `Onsite`, `Multiple`, `Unclear`. |
| `internship_term` | The internship period, e.g. `Summer 2026`. |
| `application_url` | The **official** apply link (company page or official ATS). Must always be present and non-empty. |
| `source_url` | Where the posting was discovered or verified (may equal `application_url`). |
| `source_type` | The kind of source. One of: `Company Career Page`, `Greenhouse`, `Lever`, `Ashby`, `Workday`, `Simplify`, `Handshake`, `LinkedIn`, `Other`. |
| `status` | Application status. `Open` only if the official page is reachable and still accepting applications; otherwise `Closed` or `Unclear`. |
| `last_verified_date` | The date (`YYYY-MM-DD`) a human last loaded the official page and confirmed reachability/status. Must be present. |
| `discovered_date` | The date (`YYYY-MM-DD`) the posting was first added to the dataset. |
| `age_days` | A derived integer: days since `discovered_date`. Not guessed. |
| `tech_keywords` | An array of technologies **explicitly named** in the posting (e.g. `["Python", "React"]`). |
| `ai_relevance` | How AI/ML-relevant the role is, based only on posting text. One of: `High`, `Medium`, `Low`, `None`, `Unclear`. |
| `full_stack_relevance` | How full-stack-relevant the role is, based only on posting text. One of: `High`, `Medium`, `Low`, `None`, `Unclear`. |
| `student_level` | The target student level per the posting. One of: `Freshman`, `Sophomore`, `Junior`, `Senior`, `Undergraduate`, `Graduate`, `Unclear`. |
| `freshman_sophomore_friendly` | Whether early undergraduates are eligible, per evidence. One of: `Yes`, `No`, `Unclear`. |
| `requires_us_citizenship` | Whether U.S. citizenship is required, per evidence. One of: `Yes`, `No`, `Unclear`. |
| `sponsorship_note` | A short factual note on sponsorship / CPT / OPT stance, or the ambiguity, as stated by the posting. |
| `work_authorization_note` | A short factual note on any work-authorization requirement the posting states. |
| `evidence_notes` | Short evidence supporting citizenship / sponsorship / authorization / relevance claims. May quote at most ~1 sentence from the posting. Required (in spirit) whenever such a claim is definite. |
| `fit_summary` | A short, evidence-based summary of why this role may fit an undergraduate CS student. |
| `risk_flags` | An array of risk indicators, e.g. `["unverified-link", "citizenship-required", "stale"]`. |
| `date_added` | The date (`YYYY-MM-DD`) the record was created. |
| `date_updated` | The date (`YYYY-MM-DD`) the record was last updated. |

## Notes on Dates

All dates use the `YYYY-MM-DD` format. `last_verified_date` should never be in
the future, and an old `last_verified_date` is a signal to re-check the posting.

## Notes on Enums

Enum values must match `data/schema.json` exactly (including capitalization).
When uncertain, prefer the `Unclear` value rather than picking an optimistic or
plausible-sounding option.

## Notes on Evidence

Any definite claim about citizenship, sponsorship, work authorization, or
freshman/sophomore friendliness should be accompanied by a short note in
`evidence_notes`. The validator (`scripts/validate_data.py`) warns when such a
claim is made without evidence.

## Field Format Examples

These examples reflect how the helper scripts (`scripts/submission_to_json.py`
and `scripts/append_entry.py`) expect values to look.

- **`tech_keywords` (array of strings).** In the Markdown submission you write a
  comma-separated list; the converter turns it into a JSON array:

  ```
  - **tech_keywords:** Python, React, PyTorch
  ```
  becomes
  ```json
  "tech_keywords": ["Python", "React", "PyTorch"]
  ```
  Only include technologies **explicitly named** in the posting. No signal →
  empty array `[]`.

- **`risk_flags` (array of strings).** Same comma-separated → array conversion:

  ```
  - **risk_flags:** unverified-link, stale
  ```
  becomes
  ```json
  "risk_flags": ["unverified-link", "stale"]
  ```
  Common values: `unverified-link`, `citizenship-required`, `stale`. None → `[]`.

- **`evidence_notes` (short string).** A brief evidence summary, optionally
  quoting ≤ ~1 sentence from the posting. **Not** a pasted job description:

  ```json
  "evidence_notes": "Posting says 'open to all candidates authorized to work in the US' — no citizenship requirement stated."
  ```

- **`fit_summary` (short string).** The maintainer's **own** summary of why the
  role may fit an undergraduate CS student — written in your words, never copied
  from the JD:

  ```json
  "fit_summary": "Full-stack SWE intern role naming React and Node; open to undergraduates, good fit for a sophomore with web experience."
  ```
