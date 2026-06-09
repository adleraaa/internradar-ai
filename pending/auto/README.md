# Auto-Discovered Candidates (`pending/auto/`)

This folder holds **auto-discovered internship candidate drafts** produced by the
discovery + verification pipeline:

```
python scripts/discover_candidates.py
python scripts/verify_candidates.py --limit 10
```

## Local-only by default

The generated `auto_*.md` drafts are **local review artifacts** and are
intentionally **gitignored** (`pending/auto/auto_*.md`) so the public repo does
not accumulate stale candidate drafts. Only this `README.md` is tracked here.

- The tracked, concise **review summary** is
  [`../../docs/candidate_review_report.md`](../../docs/candidate_review_report.md).
- The tracked **verified dataset** is `data/internships.json`.
- Regenerate drafts any time (they stay local):
  ```
  python scripts/auto_update_verified.py --limit 20
  ```
- Full-auto can still **promote high-confidence candidates** into the dataset
  without committing every draft — only the dataset and the summary report are
  tracked.

## Important

- These are **candidates, not verified final entries.** Discovery and automated
  verification are best-effort signals — they are **not** a substitute for a human
  checking the official application page.
- **Nothing here is in the dataset.** A draft existing in this folder does **not**
  mean the role is in `data/internships.json`. The dataset is the single source of
  truth and is only changed by an explicit promotion step.
- **Maintainers must review each draft** against its official application page
  before promoting it. Confirm the role still exists, the page is accepting
  applications, and that any citizenship/sponsorship/work-authorization wording is
  read correctly.
- **Promotion is explicit and manual:**
  ```
  python scripts/promote_candidate.py pending/auto/<candidate-file>.md
  ```
  Drafts marked **"Needs manual review"** require `--allow-needs-review` to
  promote, after you have verified them yourself.

## Do not

- Do **not** treat this folder as the source of truth.
- Do **not** bulk-append these into the dataset without review.
- Do **not** edit a draft to inflate its confidence — re-verify instead.

See [`../../docs/automation_policy.md`](../../docs/automation_policy.md) for the
full policy.
