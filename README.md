# FPL Technocrat

FPL Technocrat turns expert YouTube videos into structured Fantasy Premier
League recommendations served by FastAPI and a Next.js dashboard.

## Storage architecture

PostgreSQL is the backend's only durable store:

- local development uses the PostgreSQL service in `docker-compose.yml`;
- deployed API and worker containers use Supabase PostgreSQL;
- transcripts and revisions, pipeline runs, completed report snapshots, all
  structured artifacts, manifests, and rendered Markdown are database rows.

The API and worker do not recover state from JSON, Markdown, SQLite, local
directories, process memory, or Modal Volumes. A container can be replaced at
any point without losing durable state. Completed reports are immutable
point-in-time snapshots; the newest valid completed row for a season/gameweek
is public without changing older snapshots.

Pipeline exclusivity is enforced by a PostgreSQL partial unique index, so
multiple API instances cannot accept overlapping queued/running jobs. A report
is published and its pipeline run is marked completed in one transaction.

## Quick start

```bash
cp .env.example .env
make install
docker compose up -d postgres
uv run alembic upgrade head
make test
make run-api
```

Start the frontend separately:

```bash
make install-frontend
make run-frontend
```

The defaults connect to `postgresql+psycopg://postgres:postgres@localhost:5432/fpl_scout`.
Both application and migration traffic use local PostgreSQL during development.

## Configuration

The important backend variables are:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Application traffic; use local PostgreSQL locally and Supabase's transaction pooler in production |
| `DIRECT_DATABASE_URL` | Alembic traffic; use a direct or session-pooler PostgreSQL URL |
| `DATABASE_POOL_MODE` | Set to `transaction` for Supabase transaction pooling |
| `OPENAI_API_KEY` | Expert analysis and synthesis |
| `ADMIN_API_TOKEN` | Protects admin APIs |
| `TRANSCRIPT_FAILURE_RETRY_HOURS` | Retry interval for unavailable transcripts |

Production configuration fails fast unless both database URLs are valid
PostgreSQL URLs. The direct migration URL may not use the transaction pooler on
port 6543. Database failures are surfaced; there is no file fallback.

## Running the pipeline

The admin API starts a durable background run:

```text
POST /api/admin/pipeline/run
GET  /api/admin/runs/{run_id}
```

The CLI writes the same PostgreSQL report snapshot:

```bash
uv run python -m src.app.cli.run_gameweek_report \
  --season 2025-26 --gameweek 32 --per-expert-limit 2 --no-synthesis
```

An optional `--run-id` assigns a database identifier. It is not a path.

Public and admin report endpoints resolve entirely from PostgreSQL:

- `GET /api/recommendations/latest`
- `GET /api/recommendations?season=2025-26&gameweek=32`
- `GET /api/recommendations/gameweeks`
- `GET /api/reports`
- `GET /api/admin/reports/{run_id}`

## Tests

```bash
uv run pytest
uv run ruff check .
npm --prefix frontend run test
```

Database integration tests require PostgreSQL. Unit tests may inject repository
mocks, but application code has no SQLite or filesystem store.

## Docker and deployment

`docker compose up --build api` starts PostgreSQL, applies Alembic migrations,
and runs the API. Only PostgreSQL's named data volume is persistent; the API
container has no host data bind mount.

Production uses Supabase's pooled URL for `DATABASE_URL` and its direct or
session URL for `DIRECT_DATABASE_URL`:

```bash
make modal-migrate
make modal-verify
make modal-deploy
```

Modal deploys replaceable API and worker containers without a Modal Volume.
See [docs/modal-deployment.md](docs/modal-deployment.md) for migration,
verification, backup, and recovery procedures.

## Legacy cutover

Before deleting the old Modal Volume, take a recovery copy and run the
idempotent importer from a controlled environment:

```bash
uv run python -m scripts.migrate_legacy_storage \
  --reports-dir /recovery/reports \
  --runs-dir /recovery/runs \
  --dry-run

uv run python -m scripts.migrate_legacy_storage \
  --reports-dir /recovery/reports \
  --runs-dir /recovery/runs
```

The summary includes imported/skipped counts, malformed records, database
counts, and every completed report identity. Existing run IDs are skipped, so
the command is safe to repeat. Malformed or identity-conflicting reports are
reported and left only in the recovery backup; they are never published.

Keep the backup and importer for the agreed retention window. After API reads,
counts, and identities have been verified and the window closes, delete the old
Volume and remove the importer in a follow-up change.

## Recovery

Recover PostgreSQL using Supabase backups/PITR in production or the local
PostgreSQL volume backup in development. After a restore:

```bash
uv run alembic current
uv run python -m src.scripts.verify_database
```

Then verify representative report IDs through the existing API. Local
application files are not a recovery source.
