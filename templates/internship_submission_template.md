# Internship Submission

A human-fillable form for **one** internship entry. Fill in the values after each
`**field:**` marker on the same line. Keep the `- **field:**` markers intact —
the tooling (`scripts/submission_to_json.py`) parses those exact lines.

> **Before you fill this in, read the rules**
> - **Do not paste full job descriptions.** Quote only short evidence snippets
>   (≤ ~1 sentence) when needed.
> - **If uncertain, mark a field `Unclear`** (for enum fields) or leave it empty
>   (for free-text/list fields). Never guess.
> - **Do not mark `status: Open`** unless the official application page is
>   reachable and still appears to be accepting applications.
> - **Do not mark `requires_us_citizenship: No` ("Green Card OK")** unless the
>   posting gives explicit or strongly inferable evidence. Otherwise `Unclear`.
> - **Every entry must have a concrete, human-facing official application link**
>   in `application_url`.

---

## Core fields

- **company:**
- **role:**
- **category:** Other
  <!-- one of: Software Engineering | AI/ML | Data Science | Product | Hardware | Other.
       (No 'Unclear' for this field — use 'Other' until you can classify it.) -->
- **location:**
- **location_type:** Unclear
  <!-- one of: Remote | Hybrid | Onsite | Multiple | Unclear -->
- **internship_term:**
  <!-- e.g. Summer 2026 -->

## Links & source

- **application_url:**
  <!-- REQUIRED. Official apply page (company career page or official ATS). -->
- **source_url:**
  <!-- Where you discovered/verified it. May equal application_url. -->
- **source_type:** Other
  <!-- one of: Company Career Page | Greenhouse | Lever | Ashby | Workday | Simplify | Handshake | LinkedIn | Other.
       (No 'Unclear' for this field — use 'Other' until you can classify the source.) -->

## Status & freshness

- **status:** Unclear
  <!-- one of: Open | Closed | Unclear. Open ONLY if the page is reachable and accepting applications. -->
- **last_verified_date:**
  <!-- REQUIRED. YYYY-MM-DD. The date YOU loaded the official page. -->
- **discovered_date:**
  <!-- YYYY-MM-DD. The date this posting was first added. -->

## Classification (evidence-based only)

- **tech_keywords:**
  <!-- Comma-separated, e.g. Python, React, PyTorch. Only technologies named in the posting. -->
- **ai_relevance:** Unclear
  <!-- one of: High | Medium | Low | None | Unclear -->
- **full_stack_relevance:** Unclear
  <!-- one of: High | Medium | Low | None | Unclear -->
- **student_level:** Unclear
  <!-- one of: Freshman | Sophomore | Junior | Senior | Undergraduate | Graduate | Unclear -->
- **freshman_sophomore_friendly:** Unclear
  <!-- one of: Yes | No | Unclear -->

## Work authorization (cite evidence for any definite claim)

- **requires_us_citizenship:** Unclear
  <!-- one of: Yes | No | Unclear. 'No' requires evidence. -->
- **sponsorship_note:**
  <!-- Short factual note: sponsors / does not sponsor / CPT or OPT mentioned / silent. -->
- **work_authorization_note:**
  <!-- Short factual note on any stated work-authorization requirement. -->

## Notes & summary (your own words — never copied JD text)

- **evidence_notes:**
  <!-- Short evidence (≤ ~1 sentence quotes) backing citizenship/sponsorship/authorization/relevance claims. -->
- **fit_summary:**
  <!-- Your own short summary of why this may fit an undergrad CS student. Not copied from the JD. -->
- **risk_flags:**
  <!-- Comma-separated, e.g. unverified-link, citizenship-required, stale. -->

---

## Reviewer checklist

- [ ] `application_url` is a concrete, human-facing **official** application link.
- [ ] `last_verified_date` is filled, in `YYYY-MM-DD`, and not in the future.
- [ ] `status` reflects what was actually observed on the official page.
- [ ] `status: Open` only set because the page is reachable and accepting applications.
- [ ] Every `requires_us_citizenship` / `sponsorship_note` / `work_authorization_note`
      claim has matching `evidence_notes`.
- [ ] `requires_us_citizenship: No` is backed by real evidence (not optimism).
- [ ] No full job description text was pasted; only short evidence snippets.
- [ ] All enum fields use exact allowed values (or `Unclear`).
- [ ] After converting to JSON, `python scripts/validate_data.py` passes.
