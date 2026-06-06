# Search & Verification Rules

These rules govern how internships are discovered, verified, and recorded in
InternRadar AI. They exist to keep the dataset **trustworthy and
evidence-based**. When a rule and convenience conflict, follow the rule.

> **Core policy**
> - A job is **never** marked `Open` unless its official application page is
>   reachable and still appears to accept applications.
> - A job is **never** marked "no citizenship required" / "Green Card OK" unless
>   there is explicit or strongly inferable evidence that the role does not
>   require U.S. citizenship.
> - When anything is unclear, mark it **`Unclear`** instead of guessing.

---

## 1. Acceptable Sources

- Company **official career pages**.
- Official applicant tracking systems (ATS) linked from the company:
  **Greenhouse, Lever, Ashby, Workday**.
- University / official partner portals where the link resolves to an official
  posting (e.g. **Handshake** pointing to a company ATS).
- Reputable aggregators (**Simplify, LinkedIn**) **only as a discovery starting
  point** — the entry must then be verified and linked against the official
  posting.

## 2. Unacceptable Sources

- Re-hosted or scraped copies of job descriptions on unknown sites.
- Screenshots, social-media posts, or forum hearsay as the sole source.
- Expired-link caches, content farms, or SEO mirror pages.
- Any source that cannot be traced back to an official posting or ATS.
- Paywalled or login-walled pages that cannot be independently confirmed.

## 3. Official Link Rules

- `application_url` **must** point to the official posting or official ATS apply
  page whenever one exists.
- If only an aggregator link exists and no official link can be found, you may
  record the aggregator link **only if** `source_type` reflects it and
  `evidence_notes` explains why no official link was available.
- Prefer the **direct apply URL** over a generic careers landing page when the
  specific posting is identifiable.
- Never fabricate or "reconstruct" a URL. If you cannot find a working link, do
  not add the entry.

## 4. Posting Date Rules

- Record `discovered_date` as the date you first added the posting to the
  dataset (`YYYY-MM-DD`).
- If the official posting shows a publication or update date, you may note it in
  `evidence_notes`; do not invent one.
- `age_days` is derived (days since `discovered_date`) and must not be guessed.

## 5. Last Verified Rules

- `last_verified_date` is the date a human (or supervised process) **actually
  loaded the official page** and confirmed reachability and status.
- It must be `YYYY-MM-DD` and must not be set to a future date.
- Re-verify periodically. An entry whose `last_verified_date` is old should be
  treated with suspicion and re-checked before being relied upon.

## 6. Status Rules

- `Open` — the official application page is reachable **and** still appears to
  accept applications.
- `Closed` — the posting is gone, explicitly closed, or no longer accepting
  applications.
- `Unclear` — the page is unreachable, ambiguous, login-walled, or you cannot
  confirm whether it is accepting applications.
- Default to `Unclear` when uncertain. Never mark `Open` optimistically.

## 7. Sponsorship / Citizenship Interpretation Rules

- `requires_us_citizenship`:
  - `Yes` — posting explicitly requires U.S. citizenship (e.g. "must be a U.S.
    citizen", clearance requiring citizenship).
  - `No` — explicit or strongly inferable evidence the role does **not** require
    citizenship (e.g. "open to all work-authorized candidates", "we sponsor").
  - `Unclear` — not stated or genuinely ambiguous.
- `sponsorship_note` — capture exact stance when stated: sponsors / does not
  sponsor / CPT or OPT mentioned / silent. Record ambiguity as ambiguity.
- Do **not** infer immigration outcomes. Phrases like "must be authorized to
  work in the U.S." do **not** by themselves prove citizenship is required or
  that sponsorship is offered — record what is written and mark `Unclear` where
  appropriate.

## 8. AI Classification Rules

- `ai_relevance` and `full_stack_relevance` (`High` / `Medium` / `Low` / `None`
  / `Unclear`) must be based on **text in the posting** — named technologies,
  responsibilities, or team description.
- Do not infer relevance from the company's general reputation.
- If the posting gives no signal, use `Unclear` (or `None` only when the posting
  clearly describes unrelated work).
- `tech_keywords` should list technologies **explicitly named** in the posting.

## 9. Evidence Rules

- Any non-obvious classification — citizenship, sponsorship, work authorization,
  freshman/sophomore friendliness, AI/full-stack relevance — should be supported
  by a short note in `evidence_notes`.
- Evidence may quote at most ~1 sentence from the posting; do not paste the full
  description.
- If you cannot point to evidence, downgrade the claim to `Unclear`.

## 10. No Hallucination Rules

- **Never invent** companies, roles, links, dates, or eligibility details.
- **Never fill** unknown fields with plausible-sounding values — use `Unclear`,
  empty strings, or empty arrays as the schema allows.
- **Never copy** full job descriptions into the dataset.
- If a posting cannot be verified against an acceptable source, **do not add
  it.** Omission is always preferable to a fabricated or unverified entry.
