# Modal deployment

The Modal app deploys two functions: the FastAPI ASGI service and a detached pipeline worker. Reports, transcripts, and JSON run-state records share the `fpl-scout-data` Volume mounted at `/data`. The Next.js frontend is intentionally outside this deployment and can be deployed separately to Vercel.

## Supabase project and connection modes

Create a dedicated production project in the Supabase dashboard, choose the
region closest to Modal's workload, generate a unique database password, and
record the connection strings from **Connect**. Do not reuse the local
development database or password.

Use these server-side connections:

- `DATABASE_URL`: shared or dedicated transaction pooler, normally port 6543.
  This suits Modal's temporary, autoscaling API containers and detached
  workers. `DATABASE_POOL_MODE=transaction` makes psycopg use
  `prepare_threshold=None`, because transaction pooling does not support
  prepared statements.
- `DIRECT_DATABASE_URL`: direct project connection on port 5432 for Alembic.
  The direct hostname requires IPv6 unless the Supabase IPv4 add-on is enabled.
  If the selected Modal migration runtime cannot reach it, use the shared
  session pooler on port 5432 instead. Never use transaction mode for Alembic.

Both `postgres://` and `postgresql://` dashboard URLs are accepted and
normalized to SQLAlchemy's psycopg 3 driver. Production connections add
`sslmode=require` in code, so credentials cannot accidentally opt out of TLS.
The application pool is deliberately small per Modal container: pool size 2,
overflow 1, timeout 10 seconds, recycle 300 seconds, pre-ping enabled, and a
5-second connection timeout. Adjust only after reviewing total connections
across all simultaneously scaled containers.

Supabase's current connection-mode and IPv4/IPv6 guidance is documented at
https://supabase.com/docs/guides/database/connecting-to-postgres.

## Account and secrets

Install the locked environment and authenticate the CLI:

```bash
uv sync --frozen --group dev
uv run modal setup
```

Create a strong pipeline token, then create the server-side secret. The existing
`fpl-scout-secrets` secret must contain both database URLs. Do not put real
values in the repository `.env`, shell history, logs, source control, Vercel,
frontend code, or any `NEXT_PUBLIC_*` variable. Prefer the Modal dashboard's
secret editor. When using the CLI, put the complete replacement secret in a
temporary, permission-0600 dotenv file and use `--from-dotenv ... --force`;
Modal replaces the named secret, so omitting an existing key removes it.

```bash
umask 077
editor /tmp/fpl-scout-production.env
uv run modal secret create fpl-scout-secrets \
  --from-dotenv /tmp/fpl-scout-production.env \
  --force
```

The temporary file must include all existing application keys plus:

```dotenv
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@<region>.pooler.supabase.com:6543/postgres
DIRECT_DATABASE_URL=postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

Delete the temporary file securely after the CLI succeeds. An empty
`OPENAI_BASE_URL` safely selects `https://api.openai.com/v1`.
`ADMIN_API_TOKEN` protects admin pages and APIs; `PIPELINE_API_TOKEN` remains
available for compatible automation.

## Migration and database verification

Test direct IPv6 connectivity by running the migration function on Modal. If it
cannot resolve or reach the direct endpoint, replace only
`DIRECT_DATABASE_URL` with the Supabase session-pooler URL on port 5432 and
retry.

Production schema changes are an explicit pre-deployment gate:

```bash
make modal-migrate
make modal-verify
make modal-deploy
```

The migration function runs, in order:

```text
alembic upgrade head
alembic current --check-heads
alembic check
```

The verification function fails unless `transcripts`,
`transcript_revisions`, and all migration-defined indexes exist. It returns
only row counts and an orphan-revision count; it never prints a connection URL.
The GitHub production job performs migration and verification before deploying
code, ensuring code that depends on the schema is not released first.

To validate runtime persistence, record the counts from `make modal-verify`,
run `scripts/modal_smoke_test.sh`, and run `make modal-verify` again. Confirm
that the run artifacts contain transcript and transcript-revision identifiers.
Stop/redeploy the Modal app, repeat a read or the same pipeline input, and
confirm the stored transcript is reused and counts/relationships remain valid.

## Volume and deployment

`modal_app.py` creates `fpl-scout-data` on first deployment. It remains the
report/run artifact store, but transcript persistence and cache hits do not
depend on Volume commits. To create it explicitly:

```bash
uv run modal volume create fpl-scout-data
```

For live development and production:

```bash
make modal-serve
make modal-migrate
make modal-verify
make modal-deploy
```

Modal prints one public URL for `api`; `pipeline_worker` has no public HTTP endpoint. Verify the backend deployment with:

```bash
MODAL_API_URL="https://...modal.run" \
PIPELINE_API_TOKEN="..." \
GAMEWEEK=1 \
scripts/modal_smoke_test.sh
```

The smoke test checks API health, starts a real, chargeable analysis run with one expert, and polls to a terminal state (set `SMOKE_TIMEOUT_SECONDS` to override the one-hour default). A POST returns 202 immediately. A separately deployed frontend can follow the same durable `/api/pipeline-runs/{run_id}` polling flow.

## GitHub Actions CI/CD

The `Backend CI/CD` workflow runs Ruff and the backend pytest suite for pull requests and pushes to `main` when backend-related code, tests, deployment files, scripts, or the workflow itself change. It also runs these checks before every manually requested deployment. CI installs Python 3.12 and the development dependency group exactly as locked in `uv.lock`; it does not receive Modal credentials or application runtime secrets.

Create a protected GitHub environment named `production`. Configure required reviewers or deployment branch rules there so only authorized users can approve a production deployment. Add these environment secrets:

- `MODAL_TOKEN_ID`
- `MODAL_TOKEN_SECRET`

Use a Modal service-user token when the workspace plan supports it. Give the service user Contributor access through Modal RBAC and scope the GitHub secrets to the `production` environment. Add `MODAL_API_URL` as a `production` environment variable (or repository variable) containing the public Modal API base URL, without requiring a trailing slash.

Application runtime values such as `OPENAI_API_KEY`, database URLs, Webshare
proxy credentials, and `PIPELINE_API_TOKEN` remain in the Modal secret named
`fpl-scout-secrets`. Do not duplicate them in GitHub Actions. The deployment
workflow needs only the Modal service-user credentials; it invokes the
secret-bound migration and verification functions and then calls the public,
non-chargeable `/health` endpoint. Production `/health` performs `SELECT 1` and
returns 503 if Supabase is unavailable.

After a backend-related commit reaches `main`, GitHub Actions deploys `modal_app.py` only if linting and tests pass. Pull requests never deploy. Production deployments share one concurrency group and cannot overlap.

To deploy the current branch manually:

1. Open **Actions** in GitHub and select **Backend CI/CD**.
2. Choose **Run workflow**, select the branch to deploy, and start the run.
3. If the `production` environment requires review, have an authorized reviewer approve the deployment after CI passes.

Manual runs use the same lint, test, deployment, concurrency, and health-check gates as deployments from `main`. The full `scripts/modal_smoke_test.sh` remains a separate manual operation because it starts a real, potentially chargeable pipeline run.

If a deployment fails, open its run under **Actions**, expand the failed step, and inspect the Modal deploy output or the bounded `/health` retry output. Confirm that the production environment contains both Modal secrets and that `MODAL_API_URL` points to the deployed API. Modal application logs are also available in the dashboard or with `uv run modal app logs fpl-technocrat`.

To roll back application code, revert the relevant commit on `main` and merge
the revert only when the old code is compatible with the migrated schema.
Alembic downgrades are not an automatic deployment action. For a destructive or
incompatible schema rollback, stop deployments/writes and restore from the
Supabase backup/PITR mechanism appropriate to the project plan, then verify the
revision, tables, indexes, counts, and relationships before redeploying. The
named `fpl-scout-data` Modal Volume is independent of database recovery and must
not be deleted.

## Secret rotation

1. Generate/reset the Supabase database password during a maintenance window.
2. Build a complete replacement `fpl-scout-secrets` value set in the Modal
   dashboard or a permission-0600 temporary file.
3. Replace both URLs together, using transaction mode for `DATABASE_URL` and
   direct/session mode for `DIRECT_DATABASE_URL`.
4. Run `make modal-migrate`, `make modal-verify`, and `make modal-deploy`.
5. Confirm `/health`, then perform the bounded pipeline persistence check.
6. Remove temporary credential files and revoke the old credential when the
   database/provider supports overlapping credentials.

If rotation fails, restore the previous complete Modal secret while it remains
valid and redeploy. Never paste either URL into an issue, CI log, or frontend
environment.

## Existing local transcript data decision

The current workspace contains seven ignored JSON transcript files (about
148 KB), including obvious development/fixture identifiers (`abc123` and
`run_001`). They are classified as local development data, not production
records, and are not uploaded automatically.

If a data owner later classifies specific files as production data, take a
backup and import deliberately:

```bash
uv run python -m src.scripts.import_transcripts \
  --source data/transcripts \
  --dry-run
uv run python -m src.scripts.import_transcripts \
  --source data/transcripts
make modal-verify
```

Perform the import from a controlled server-side environment configured with
the production URL; never put the URL on the command line. Compare the import
summary with the post-import `transcripts` count, verify
`transcript_revisions` increased as expected, and require
`orphan_revisions=0`.

## Vercel frontend handoff

The existing Next.js server route proxies `/backend/*` and forwards an authenticated admin's HttpOnly session credential only to `/api/admin/*`. Configure this server-side environment variable:

```text
API_PROXY_TARGET=https://<modal-api-host>.modal.run
```

The value should not be prefixed with `NEXT_PUBLIC_`. The Modal API's CORS settings do not need the Vercel origin when the frontend uses this server-side proxy.

## Operations

- View app/function logs in the Modal dashboard or with `uv run modal app logs fpl-technocrat`.
- Inspect stored artifacts with `uv run modal volume ls fpl-scout-data /` and download recovery copies with `uv run modal volume get`.
- A failed run remains in `/data/runs/<run-id>.json`. Read its structured `error`, correct credentials/provider/proxy configuration, and start a new run from the UI; failed runs are not resumed in place.
- Redeploy with `make modal-deploy`. Existing Volume data survives container shutdown and redeployment.
- Configure an API custom domain from the Modal endpoint settings, then update DNS exactly as Modal displays. Set the resulting URL as the frontend's `API_PROXY_TARGET`.
- Stop compute with `uv run modal app stop fpl-technocrat`. Delete the deployed app from the dashboard or CLI when retiring it. Delete `fpl-scout-data` separately only after downloading anything required; Volume deletion permanently removes reports and status history.

## Cost considerations

Modal billing is driven mainly by API and worker CPU/memory duration plus outbound traffic; each analysis worker can run for up to one hour. Vercel and OpenAI are billed separately. The largest analysis cost controls are `expert_count`, `per_expert_limit`, transcript length, and synthesis. Use one expert/video for smoke tests, set provider budget alerts, review current Modal/OpenAI pricing before production, and keep the bearer token private to prevent unapproved runs.
