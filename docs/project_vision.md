# Project Vision — InternRadar AI

## Mission

Help undergraduate CS students find internships **faster** and with **less
wasted effort**, by guaranteeing that every listing is real, official, and
freshly verified.

## Why This Exists

Most internship lists optimize for size. That produces dead links, stale
postings, and roles that quietly exclude freshmen, sophomores, or international
students. Students burn hours discovering this themselves. InternRadar AI
inverts the priority: **trust first, volume second.**

## Guiding Principles

1. **Quality and verification over quantity.** A short list of verified,
   official postings beats a long list of unverified ones.
2. **Evidence over inference.** Eligibility and fit claims are grounded in the
   posting's own text, never guessed.
3. **Honesty about uncertainty.** When something can't be confirmed, it is
   marked `Unclear` — not hidden, not guessed.
4. **Respect for sources.** We store official links and short factual notes, not
   copied job descriptions.
5. **Undergraduate-first.** Special attention to whether early undergraduates
   (freshmen/sophomores) are actually eligible.

## Roadmap

### Phase 1 — GitHub repository first (current)
- Public, transparent repo with schema, rules, and documentation.
- Standard-library validation script.
- Empty, valid data file — **no postings yet**.

### Phase 2 — Verified data collection
- Add real internships from official sources, each with a `last_verified_date`.
- Periodic re-verification to keep `status` and freshness honest.

### Phase 3 — Searchable Next.js dashboard
- Turn the JSON dataset into a searchable, filterable web UI.
- Filter by category, location type, student level, citizenship/sponsorship,
  freshman/sophomore friendliness, and freshness.

### Phase 4 — AI matching based on student background
- Given a student's background (year, skills, work-authorization status),
  surface the best-fit verified roles.
- AI fit tags remain **evidence-based** — derived from posting text, never
  fabricated.

## Non-Goals

- Becoming a generic, high-volume scraper of every posting on the internet.
- Copying or re-hosting full job descriptions.
- Offering legal or immigration advice.
- Guessing eligibility to make the list look more complete.

## Definition of Success

A student can open InternRadar AI, trust that a listing marked `Open` is
genuinely open, click an **official** application link, and clearly understand
the citizenship/sponsorship situation and whether their year is eligible —
without being misled.
