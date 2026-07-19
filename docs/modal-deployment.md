# Modal deployment

The Modal app deploys two functions: the FastAPI ASGI service and a detached pipeline worker. Reports, transcripts, and JSON run-state records share the `fpl-scout-data` Volume mounted at `/data`. The Next.js frontend is intentionally outside this deployment and can be deployed separately to Vercel.

## Account and secrets

Install the locked environment and authenticate the CLI:

```bash
uv sync --frozen --group dev
uv run modal setup
```

Create a strong pipeline token, then create the server-side secret. Do not put real values in `.env`, shell history, source control, or a `NEXT_PUBLIC_*` variable. If your shell records commands, use Modal's interactive secret creation flow or temporarily disable history.

```bash
uv run modal secret create fpl-scout-secrets \
  OPENAI_API_KEY="..." \
  OPENAI_MODEL="gpt-4.1-mini" \
  OPENAI_BASE_URL="" \
  ENABLE_WEBSHARE_PROXY="true" \
  WEBSHARE_PROXY_USERNAME="..." \
  WEBSHARE_PROXY_PASSWORD="..." \
  PIPELINE_API_TOKEN="..."
```

An empty `OPENAI_BASE_URL` safely selects `https://api.openai.com/v1`. Rotate secrets by running the same command with the replacement values, then redeploy. The token is read by FastAPI. A separately deployed frontend should keep the same token in a server-only environment variable and inject it from its `/backend/*` route; never use a `NEXT_PUBLIC_*` variable for it.

## Volume and deployment

`modal_app.py` creates `fpl-scout-data` on first deployment. To create it explicitly:

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

## Vercel frontend handoff

The existing Next.js server route already proxies `/backend/*`, injects `PIPELINE_API_TOKEN` for pipeline mutations, and keeps browser requests same-origin. In the future Vercel project, configure these server-side environment variables:

```text
API_PROXY_TARGET=https://<modal-api-host>.modal.run
PIPELINE_API_TOKEN=<same value stored in fpl-scout-secrets>
```

Neither variable should be prefixed with `NEXT_PUBLIC_`. The Modal API's CORS settings do not need the Vercel origin when the frontend uses this server-side proxy.

## Operations

- View app/function logs in the Modal dashboard or with `uv run modal app logs fpl-technocrat`.
- Inspect stored artifacts with `uv run modal volume ls fpl-scout-data /` and download recovery copies with `uv run modal volume get`.
- A failed run remains in `/data/runs/<run-id>.json`. Read its structured `error`, correct credentials/provider/proxy configuration, and start a new run from the UI; failed runs are not resumed in place.
- Redeploy with `make modal-deploy`. Existing Volume data survives container shutdown and redeployment.
- Configure an API custom domain from the Modal endpoint settings, then update DNS exactly as Modal displays. Set the resulting URL as the frontend's `API_PROXY_TARGET`.
- Stop compute with `uv run modal app stop fpl-technocrat`. Delete the deployed app from the dashboard or CLI when retiring it. Delete `fpl-scout-data` separately only after downloading anything required; Volume deletion permanently removes reports and status history.

## Cost considerations

Modal billing is driven mainly by API and worker CPU/memory duration plus outbound traffic; each analysis worker can run for up to one hour. Vercel and OpenAI are billed separately. The largest analysis cost controls are `expert_count`, `per_expert_limit`, transcript length, and synthesis. Use one expert/video for smoke tests, set provider budget alerts, review current Modal/OpenAI pricing before production, and keep the bearer token private to prevent unapproved runs.
