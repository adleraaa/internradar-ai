# Reviewed Submissions

This folder stores Markdown submissions that have been **reviewed** and
converted into JSON entries in `../data/internships.json`.

## What goes here

- Markdown drafts (originally from `../pending/`) that a maintainer has reviewed
  against the official application page and then converted to JSON using
  [`../scripts/submission_to_json.py`](../scripts/submission_to_json.py) and
  appended via [`../scripts/append_entry.py`](../scripts/append_entry.py).

## Why keep them

- They provide a human-readable audit trail of how each JSON entry was reviewed,
  including the evidence notes the maintainer recorded.
- They make it easier to re-verify an entry later and to see what was checked.

## Conventions

- Keep the same filename as in `pending/` (`YYYY-MM-DD_company_role.md`) so the
  Markdown and its JSON entry are easy to correlate.
- These files are a record, not active data. The authoritative dataset is always
  `../data/internships.json`.
- Do not paste full job descriptions here either — the same evidence-snippet rule
  applies.
