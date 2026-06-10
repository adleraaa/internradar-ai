# Archive

This folder preserves a record of internship postings that were **removed** from
the active dataset (`../data/internships.json`) because they deterministically
failed official-page re-verification. Nothing is ever silently deleted.

## `removed_internships.json`

`removed_internships.json` is a JSON array of removal records, appended to by
`../scripts/reverify_existing.py` (directly or via
`../scripts/auto_update_verified.py --prune-closed`). Each record captures:

| Field | Meaning |
|---|---|
| `removed_at` | Date the entry was removed (`YYYY-MM-DD`). |
| `removal_reason` | Short reason (e.g. "page gone (HTTP 404)"). |
| `removal_evidence` | Short evidence; **never** full job-description text. |
| `previous_entry` | The full entry as it last appeared in the dataset. |
| `previous_application_url` | The entry's `application_url` at removal time. |
| `previous_last_verified_date` | When the entry was last confirmed before removal. |
| `reverify_status` | The classifier action that triggered removal (`remove`). |
| `reverify_http_status` | The HTTP status observed (or `null` for a network error). |

The file starts as an empty array (`[]`). It is committed so removals are part of
the project's transparent history.

## When (and only when) a posting is removed

Removal is **conservative and deterministic**. A posting leaves the active
dataset only when its official application page fails in an unambiguous way:

- HTTP **404 / 410** (the posting is gone);
- the page explicitly says the role is **closed / filled / expired / no longer
  accepting applications**;
- the final URL now resolves to a **private/login-gated board, a generic careers
  homepage, a search/query page, or a raw API endpoint** (no longer a specific
  official posting);
- the **role title is gone AND there is no apply flow**.

A removal is **never** triggered by a transient or ambiguous signal — timeouts,
DNS errors, HTTP **429**, HTTP **5xx**, JS-heavy pages, or a single ambiguous
parse all **keep** the posting (reported as warnings). A per-run `--max-remove`
cap (default 5) bounds how many postings can be removed at once.

## Daily maintenance

The daily scheduled workflow (`.github/workflows/auto-update-internships.yml`)
runs re-verification before adding new postings, so closed roles are pruned and
archived here automatically. See
[`../docs/automation_policy.md`](../docs/automation_policy.md) and
[`../docs/maintenance_workflow.md`](../docs/maintenance_workflow.md).

Archived entries are kept for transparency and history. They should **not** be
presented to students as active opportunities.
