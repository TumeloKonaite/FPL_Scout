# Modal deployment

The Modal app deploys two functions: the FastAPI ASGI service and a detached pipeline worker. Reports, transcripts, and JSON run-state records share the `fpl-scout-data` Volume mounted at `/data`. The Next.js frontend is intentionally outside this deployment and can be deployed separately to Vercel.

## Account and secrets

Install the locked environment and authenticate the CLI:

```bash
uv sync --frozen --group dev
uv run modal setup
```

Create a strong pipeline token, then create the server-side secret. The same
secret must contain `DATABASE_URL` (and `DIRECT_DATABASE_URL` when migrations
use a different direct connection). Do not put real values in `.env`, shell
history, source control, or a `NEXT_PUBLIC_*` variable. If your shell records
commands, use Modal's interactive secret creation flow or temporarily disable history.

```bash
uv run modal secret create fpl-scout-secrets \
  OPENAI_API_KEY="..." \
  OPENAI_MODEL="gpt-4.1-mini" \
  OPENAI_BASE_URL="" \
  ENABLE_WEBSHARE_PROXY="true" \
  WEBSHARE_PROXY_USERNAME="..." \
  WEBSHARE_PROXY_PASSWORD="..." \
  ADMIN_API_TOKEN="..." \
  PIPELINE_API_TOKEN="..." \
  DATABASE_URL="postgresql+psycopg://..." \
  DIRECT_DATABASE_URL="postgresql+psycopg://..."
```

An empty `OPENAI_BASE_URL` safely selects `https://api.openai.com/v1`. Rotate secrets by running the same command with the replacement values, then redeploy. `ADMIN_API_TOKEN` protects admin pages and APIs; `PIPELINE_API_TOKEN` remains available for compatible automation.

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

Application runtime values such as `OPENAI_API_KEY`, Webshare proxy credentials, and `PIPELINE_API_TOKEN` remain in the Modal secret named `fpl-scout-secrets`. Do not duplicate them in GitHub Actions. The deployment workflow needs only the Modal service-user credentials; its post-deployment check calls the public, non-chargeable `/health` endpoint.

After a backend-related commit reaches `main`, GitHub Actions deploys `modal_app.py` only if linting and tests pass. Pull requests never deploy. Production deployments share one concurrency group and cannot overlap.

To deploy the current branch manually:

1. Open **Actions** in GitHub and select **Backend CI/CD**.
2. Choose **Run workflow**, select the branch to deploy, and start the run.
3. If the `production` environment requires review, have an authorized reviewer approve the deployment after CI passes.

Manual runs use the same lint, test, deployment, concurrency, and health-check gates as deployments from `main`. The full `scripts/modal_smoke_test.sh` remains a separate manual operation because it starts a real, potentially chargeable pipeline run.

If a deployment fails, open its run under **Actions**, expand the failed step, and inspect the Modal deploy output or the bounded `/health` retry output. Confirm that the production environment contains both Modal secrets and that `MODAL_API_URL` points to the deployed API. Modal application logs are also available in the dashboard or with `uv run modal app logs fpl-technocrat`.

To roll back, revert the relevant commit on `main` and merge the revert. The resulting backend workflow validates and redeploys the previous code. If an immediate manual redeployment is needed, run the workflow against the revert commit after it is available on an authorized branch. The named `fpl-scout-data` Modal Volume is independent of an app deployment and survives redeployment and rollback; do not delete the Volume as part of recovery.

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
