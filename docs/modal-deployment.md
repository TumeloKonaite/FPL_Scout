# Modal deployment

Modal runs a replaceable FastAPI container and detached pipeline workers.
Supabase PostgreSQL is their only durable store; no Modal Volume is mounted.

## Connections and secrets

The `fpl-scout-secrets` Modal secret must contain:

- `DATABASE_URL`: Supabase transaction pooler, normally port 6543;
- `DIRECT_DATABASE_URL`: direct endpoint or session pooler, port 5432;
- application/provider credentials such as `OPENAI_API_KEY` and
  `ADMIN_API_TOKEN`.

Never expose either URL through `NEXT_PUBLIC_*`. Production enables TLS,
disables prepared statements for transaction pooling, and uses bounded
SQLAlchemy pools.

## Schema gate

Run migrations and verification before deploying application code:

```bash
make modal-migrate
make modal-verify
make modal-deploy
```

Verification checks transcript, revision, pipeline-run, and completed-report
tables and indexes, then reports row counts without printing credentials.
`/health` returns 503 whenever PostgreSQL is unavailable.

## Legacy Volume cutover

Do not detach or delete the old `fpl-scout-data` Volume until this procedure is
complete:

1. Stop new pipeline writes on the old deployment.
2. Download `reports/` and `runs/` into encrypted recovery storage. Record the
   backup location, timestamp, checksum, owner, and retention expiry.
3. Apply the new Alembic migration.
4. Run `scripts.migrate_legacy_storage` with `--dry-run`, review all malformed
   rows, then run it without `--dry-run`.
5. Compare legacy counts with `pipeline_runs_imported`,
   `reports_imported`, `skipped_existing`, and `malformed`.
6. Compare the reported `(run_id, season, gameweek)` identities with the
   legacy inventory.
7. Read representative and latest reports through `/api/admin/reports/{run_id}`,
   `/api/recommendations`, and `/api/recommendations/latest`.
8. Restart/redeploy both API and worker and repeat those reads.
9. Keep the Volume read-only and retain the backup for the agreed retention
   window. Delete the Volume only after owner sign-off.

The importer is idempotent: rows already present by run ID are skipped.
Malformed JSON, missing required artifacts, invalid report schemas, and
aggregate/final identity conflicts are listed in `malformed` and are not
inserted. Repair them in a copy of the recovery backup and rerun, or document
an explicit decision not to retain them.

Remove the importer after the retention window unless operations formally
choose to keep it.

## Runtime verification

Start a bounded pipeline run, poll it to completion, and record its report run
ID. Redeploy the API and worker, then confirm:

- the pipeline status is still readable;
- the report and rendered recommendations are unchanged;
- a second active run is rejected while one is queued/running;
- database unavailability returns an error and does not create local files.

## Recovery and rollback

Application rollback is a normal code redeploy only when the old code supports
the current schema. Do not automatically downgrade Alembic.

For data recovery, stop writes and restore Supabase from its backup/PITR
mechanism. Run `modal-migrate`, `modal-verify`, and representative API reads
before resuming workers. The retired Modal Volume and container files are not
backend recovery mechanisms.

Rotate both database URLs together, rerun the schema gate, and redeploy. Never
place connection URLs in CLI arguments, issues, CI logs, or frontend settings.
