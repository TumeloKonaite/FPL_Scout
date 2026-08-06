# Completed report publication

`completed_report_runs.status` describes generation lifecycle, while
`publication_status` describes public visibility. A snapshot is public only
when it is `completed`, `published`, and has a non-null `final_report`.

New snapshots default to `unpublished`. Publishing uses a transaction-level
PostgreSQL advisory lock keyed by season and gameweek, changes the existing
published snapshot to `superseded`, and changes the target to `published` in
the same transaction. The partial unique index
`uq_published_report_per_gameweek` is the final safeguard against concurrent
publishers. Republishing the current snapshot is idempotent.

Migration `20260806_06` backfills each season/gameweek deterministically. Valid
completed snapshots are ordered by `updated_at DESC`, `created_at DESC`, then
`run_id DESC`; the first is published and the remainder are superseded.
Processing, invalid, and payload-less snapshots remain unpublished. The
backfill runs before the partial unique index and aborts if invalid or duplicate
publication state remains.

Ordinary and historical pipeline workflows persist their completed snapshot
before invoking publication. A publication failure therefore leaves the new
snapshot stored but unpublished, and never changes which report public APIs
serve.
