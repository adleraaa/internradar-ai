# Verification Policy

This document tells maintainers **how** to verify each claim before it enters
the dataset. It complements [`../search_rules.md`](../search_rules.md) and
[`../CONTRIBUTING.md`](../CONTRIBUTING.md). The overriding principle:
**verify, don't guess. If you can't confirm it, mark it `Unclear`.**

---

## 1. Is the job open?

Goal: set `status` honestly.

1. Open the official application page (`application_url`).
2. Confirm the page **loads** and shows the specific role.
3. Confirm it still **accepts applications** (an Apply button / form, no
   "this position is closed" notice).
4. Set:
   - `Open` — reachable **and** accepting applications.
   - `Closed` — gone, expired, or explicitly closed.
   - `Unclear` — unreachable, login-walled, ambiguous, or you can't tell.
5. Record today's date in `last_verified_date` (`YYYY-MM-DD`).

Never mark `Open` from an aggregator alone or from memory.

## 2. Is the link official?

Goal: ensure `application_url` is trustworthy.

1. Prefer the company's own career page or its official ATS
   (Greenhouse, Lever, Ashby, Workday).
2. Confirm the domain matches the company or a recognized ATS the company uses.
3. Set `source_type` to match the actual source.
4. If only an aggregator link exists and no official link can be found, you may
   record it **only** with `source_type` reflecting that and an `evidence_notes`
   explanation. Add `unverified-link` to `risk_flags` if appropriate.
5. Never fabricate or reconstruct a URL.

## 3. Is citizenship required?

Goal: set `requires_us_citizenship` with evidence.

1. Read the eligibility / requirements section of the posting.
2. Set:
   - `Yes` — explicit requirement (e.g. "must be a U.S. citizen", or a clearance
     that requires citizenship).
   - `No` — explicit or strongly inferable evidence it is **not** required
     (e.g. "open to all candidates authorized to work in the U.S.", "we
     sponsor").
   - `Unclear` — not stated or genuinely ambiguous.
3. Put the supporting phrase in `evidence_notes` (≤ ~1 sentence).
4. Do **not** treat "must be authorized to work in the U.S." as proof of a
   citizenship requirement — that phrase alone is `Unclear` for citizenship.

## 4. Is sponsorship mentioned?

Goal: fill `sponsorship_note` factually.

1. Look for explicit statements about visa sponsorship, CPT, or OPT.
2. Record the company's stated stance: sponsors / does not sponsor / CPT or OPT
   mentioned / silent.
3. If ambiguous, record the ambiguity rather than resolving it.
4. Support any definite stance with `evidence_notes`.
5. Do not infer immigration outcomes that the posting does not state.

## 5. Is the role freshman/sophomore friendly?

Goal: set `freshman_sophomore_friendly` and `student_level`.

1. Look for class-year language ("rising sophomore", "all undergraduates",
   "graduating in 2027", "junior/senior standing required").
2. Set `freshman_sophomore_friendly`:
   - `Yes` — early undergraduates are clearly eligible.
   - `No` — clearly restricted to juniors/seniors/grads.
   - `Unclear` — not stated.
3. Set `student_level` to the closest matching enum value, or `Unclear`.
4. Cite the relevant phrase in `evidence_notes` for a definite `Yes`/`No`.

## 6. Is AI / full-stack relevance evidence-based?

Goal: set `ai_relevance` and `full_stack_relevance` honestly.

1. Base the rating only on **text in the posting**: named technologies,
   responsibilities, team description.
2. Use `High` / `Medium` / `Low` according to how central the work is.
3. Use `None` only when the posting clearly describes unrelated work.
4. Use `Unclear` when the posting gives no usable signal.
5. List explicitly named technologies in `tech_keywords`.
6. Do **not** infer relevance from the company's general reputation.

---

## Re-verification

Postings expire. Periodically re-open official pages and update
`last_verified_date`, `status`, and `date_updated`. Consider adding a `stale`
entry to `risk_flags` for postings that have not been re-verified recently, and
move clearly closed/outdated postings to `archive/` when that workflow is added.

## Final Check

Before committing any entry, run:

```
python scripts/validate_data.py
```

Resolve all errors and review all warnings (especially evidence warnings on
citizenship/sponsorship/authorization claims).
