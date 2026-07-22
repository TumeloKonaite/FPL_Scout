# ⚽ FPL Technocrat

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![OpenAI Agents](https://img.shields.io/badge/OpenAI-Agents-412991?logo=openai&logoColor=white)](https://openai.github.io/openai-agents-python/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![uv](https://img.shields.io/badge/uv-managed-DE5FE9)](https://docs.astral.sh/uv/)

AI-powered Fantasy Premier League workflow that converts expert YouTube videos into structured gameweek intelligence, reviewable artifacts, and a Next.js dashboard-ready report.

## Dashboard Preview
![FPL Technocrat dashboard preview](data/FPL_Example.png)

## 🚀 Features
- 📺 Auto-fetch recent FPL YouTube videos from configured expert channels
- 🧠 Run LLM-based transcript analysis into typed, structured outputs
- 📊 Detect consensus, disagreement, captaincy, transfers, and team-reveal patterns
- 📝 Generate markdown and JSON gameweek reports under `data/reports/`
- 📈 Explore results in the Next.js dashboard and launch runs from the UI
- 🐳 Run locally with `uv` or in Docker
- ☁️ Deploy the API, detached worker, and persistent storage on Modal

## 🧠 Why This Matters
FPL content is high-volume and repetitive. Useful signals are buried across multiple creators, long videos, and slightly different phrasing.

FPL Technocrat turns that into a repeatable weekly workflow:
- ingest expert content automatically
- normalize it into structured analysis
- compare experts at scale
- surface agreement, disagreement, and team-reveal signals
- produce outputs you can inspect, reuse, or visualize

## What This Repository Actually Does
This repository is not just a dashboard and not just an LLM wrapper.

It is an end-to-end gameweek reporting pipeline that:
- discovers recent YouTube videos from configured FPL experts
- fetches transcripts and persists their revisions in PostgreSQL
- builds `VideoAnalysisJob` inputs per relevant video
- runs expert-analysis agents over each transcript
- aggregates the results into consensus and disagreement views
- writes a complete run folder with JSON artifacts and `report.md`
- serves generated reports through FastAPI for inspection in the Next.js frontend

## Architecture At A Glance
```text
Configured expert channels
    ↓
Discover latest videos
    ↓
Filter relevant videos
    ↓
Fetch transcripts
    ↓
Build VideoAnalysisJobs
    ↓
Run expert analysis agents
    ↓
Aggregate consensus + disagreements
    ↓
Persist artifacts under data/reports/
    ↓
Review in Next.js dashboard
```

## Outputs
Each run produces reviewable artifacts under `data/reports/<gameweek-or-run-name>/`.

Core outputs:
- `discovered_videos.json`: normalized metadata for candidate videos discovered from expert channels
- `input_jobs.json`: validated transcript-backed jobs sent into analysis
- `expert_outputs.json`: structured per-expert analysis output
- `aggregate_report.json`: deterministic consensus and disagreement data
- `final_report.json`: final report consumed by the UI
- `report.md`: human-readable gameweek report
- `manifest.json`: run metadata, counts, duplicate handling, and failures

This makes the project useful both as an automation tool and as an inspectable data pipeline.

## Runtime Data
Mutable and generated files live under `data/`:
- `data/reports/`: generated run reports and review artifacts
- `data/raw/`: raw imported datasets before processing
- `data/processed/`: cleaned or transformed datasets
- `data/transcripts/`: legacy transcript cache used only during staged file fallback/import

PostgreSQL is the transcript source of truth. `input_jobs.json` remains as a
transitional immutable run snapshot for debugging and backward compatibility;
each job includes `transcript_id` and `transcript_revision_id`, identifying the
exact persisted content used by that report. New transcript results are not
written to the Modal Volume when PostgreSQL is configured.

These directories are created automatically when the API starts. Their generated contents are ignored by Git, while `.gitkeep` placeholders preserve the folder structure.

## Quick Start
```bash
cp .env.example .env
make install
make install-frontend
make test
make run-api
```

In another terminal, start the frontend:

```bash
make run-frontend
```

Open the Next.js app at `http://localhost:3000`. Next.js is the app's only frontend; the FastAPI backend serves report and pipeline APIs.

## Prerequisites
- Python `3.12`
- [`uv`](https://docs.astral.sh/uv/)
- Node.js and npm for the Next.js frontend
- Docker Desktop or Docker Engine if you want the container workflow

## Environment Variables
Copy `.env.example` to `.env` and fill in the values you need.

| Variable | Required | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | Usually yes | Credentials for the `openai-agents` runtime used during expert analysis and final synthesis |
| `OPENAI_BASE_URL` | Optional | Base URL for an OpenAI-compatible provider |
| `OPENAI_DEFAULT_MODEL` | Optional | Default model used when creating provider-aware agent models |
| `ENABLE_WEBSHARE_PROXY` | Optional | Set to `true` to route transcript fetches through Webshare |
| `WEBSHARE_PROXY_USERNAME` | If proxy enabled | Webshare username |
| `WEBSHARE_PROXY_PASSWORD` | If proxy enabled | Webshare password |
| `DATABASE_URL` | For PostgreSQL transcript storage | Pooled application connection URL |
| `DIRECT_DATABASE_URL` | For migrations | Optional direct/unpooled Alembic connection URL |
| `TRANSCRIPT_FAILURE_RETRY_HOURS` | Optional | Hours before a failed or unavailable transcript is retried |
| `TRANSCRIPT_FILE_FALLBACK_ENABLED` | Optional | Read legacy JSON only when PostgreSQL is unavailable during rollout |

### Local PostgreSQL setup

Create a dedicated login and database rather than running the application as
the PostgreSQL superuser. From pgAdmin's Query Tool, connected as `postgres`:

```sql
CREATE ROLE fpl_scout_app WITH LOGIN PASSWORD 'choose-a-url-safe-password';
CREATE DATABASE fpl_scout OWNER TO fpl_scout_app;
```

If `fpl_scout` already exists, assign it to the application role instead:

```sql
ALTER DATABASE fpl_scout OWNER TO fpl_scout_app;
ALTER SCHEMA public OWNER TO fpl_scout_app;
GRANT ALL PRIVILEGES ON DATABASE fpl_scout TO fpl_scout_app;
GRANT ALL ON SCHEMA public TO fpl_scout_app;
```

For PostgreSQL installed on the same Linux host, configure `.env` with its
actual port (normally `5432`):

```dotenv
DATABASE_URL=postgresql+psycopg://fpl_scout_app:password@127.0.0.1:5432/fpl_scout
DIRECT_DATABASE_URL=postgresql+psycopg://fpl_scout_app:password@127.0.0.1:5432/fpl_scout
TRANSCRIPT_STORE=postgres
TRANSCRIPT_FILE_FALLBACK_ENABLED=true
TRANSCRIPT_FAILURE_RETRY_HOURS=24
```

When PostgreSQL runs on Windows and the application runs inside WSL 2,
`127.0.0.1` might not reach the Windows service. Find the current Windows host
address with:

```bash
ip route show default
```

Use the address after `via` as the database hostname and PostgreSQL's configured
port. For example, a PostgreSQL server on port `5433` might use:

```dotenv
DATABASE_URL=postgresql+psycopg://fpl_scout_app:password@172.28.208.1:5433/fpl_scout
DIRECT_DATABASE_URL=postgresql+psycopg://fpl_scout_app:password@172.28.208.1:5433/fpl_scout
```

The WSL host address can change after a Windows or WSL restart. If connectivity
stops working, rerun `ip route show default` and update `.env`. PostgreSQL must
also listen on an interface reachable from WSL, and Windows Firewall should
allow its port only from the local/WSL network.

Test authentication without printing credentials:

```bash
uv run python -c "
from sqlalchemy import text
from src.app.infrastructure.database import get_engine
with get_engine().connect() as connection:
    print(connection.execute(text('select current_user, current_database()')).one())
"
```

Then apply the schema and optionally import legacy files:

```bash
uv run alembic upgrade head
uv run alembic current
uv run alembic check
uv run python -m src.scripts.import_transcripts --source data/transcripts --dry-run
uv run python -m src.scripts.import_transcripts --source data/transcripts
```

`--no-synthesis` only skips the final LLM synthesis step. The pipeline still uses `openai-agents` earlier to analyze video transcripts, so full pipeline runs still need provider credentials.

The analysis and synthesis agents use a shared OpenAI-compatible model factory. To target providers such as Ollama Cloud, set `OPENAI_BASE_URL` and `OPENAI_DEFAULT_MODEL` to the values from your provider.

## Local Development
Install dependencies:

```bash
make install
```

Run the full test suite:

```bash
make test
```

Run lint checks:

```bash
make lint
```

Install frontend dependencies:

```bash
make install-frontend
```

## Main Execution Paths
### CLI Pipeline
Source of truth command:

```bash
uv run python -m src.app.cli.run_gameweek_report --gameweek 32 --output-dir data/reports/gw32-example --per-expert-limit 2 --no-synthesis
```

Equivalent Make target:

```bash
make run-cli GAMEWEEK=32 OUTPUT_DIR=data/reports/gw32-example
```

Useful overrides:
- `PER_EXPERT_LIMIT=3`
- `EXPERT_NAME="FPL Focal"`
- `EXPERT_COUNT=5`
- `SYNTHESIS=1`

What the CLI does:
- loads environment and proxy settings
- ingests recent expert videos
- orchestrates transcript analysis jobs
- writes run artifacts to the output directory
- prints a human-readable report location when complete

### Backend API
Source of truth command:

```bash
uv run uvicorn src.app.main:app --host 0.0.0.0 --port 8000
```

Equivalent Make target:

```bash
make run-api
```

The API exposes:
- `GET /api/gameweek/current`: load public gameweek timing and availability
- `GET /api/recommendations/latest`: load the latest public recommendations without run metadata
- `GET /api/admin/pipeline/status`: inspect the latest internal run
- `POST /api/admin/pipeline/run`: trigger a protected pipeline run
- `POST /api/admin/reports/generate`: generate and publish a protected report
- `GET /api/admin/runs/{run_id}`: poll durable queued/running/completed/failed state

All `/api/admin` endpoints require an administrator bearer token. Set `ADMIN_API_TOKEN`; `PIPELINE_API_TOKEN` remains an accepted compatibility credential. Pipeline POSTs return `202 Accepted`; work continues in a background thread locally and a detached worker on Modal.

### Next.js Frontend
Production: [https://fpl-scout-kappa.vercel.app](https://fpl-scout-kappa.vercel.app)

Install dependencies once:

```bash
npm --prefix frontend install
```

Run the frontend:

```bash
npm --prefix frontend run dev
make run-frontend
```

Open `http://localhost:3000`. The frontend's same-origin `/backend/*` route proxies to `http://localhost:8000` by default. To use another API URL, set the server-only `API_PROXY_TARGET` in `frontend/.env.local`.

Visitors can load only the latest published recommendations and see neutral unavailable states. Operational controls and internal run metadata are restricted to `/admin`; sign in there with the configured `ADMIN_API_TOKEN`.

Administrators can trigger a pipeline or report generation from `/admin`. Duplicate runs are rejected while another run is queued or running.

### Test Suite
Source of truth command:

```bash
uv run pytest
```

Equivalent Make target:

```bash
make test
```

Frontend verification:

```bash
npm --prefix frontend run test
npm --prefix frontend run lint
npm --prefix frontend run build
```

## Docker Workflow
Build the image:

```bash
make docker-build
```

Run the backend API in Docker:

```bash
make docker-run
```

Then open `http://localhost:8000/docs` for the API docs. Run the Next.js frontend locally with `make run-frontend`.

Notes:
- `docker-compose.yml` is included because it makes local API startup, `.env` loading, and a persistent `data/` directory much easier for contributors.
- The container mounts `./data` into `/app/data`, so generated artifacts stay on your host machine.
- If you prefer plain Docker for the CLI, you can override the container command:

```bash
docker run --rm -it --env-file .env \
  -v "$(pwd)/data:/app/data" \
  fpl-agent:latest \
  uv run python -m src.app.cli.run_gameweek_report --gameweek 32 --output-dir data/reports/gw32-docker --per-expert-limit 2 --no-synthesis
```

Stop the Compose service with:

```bash
make docker-down
```

## Modal deployment

The production backend deployment uses FastAPI, a detached worker, and a persistent Modal Volume. The Next.js frontend is intentionally deployed separately (for example, on Vercel). See [docs/modal-deployment.md](docs/modal-deployment.md) for secret setup, deployment, frontend handoff, smoke testing, logs, recovery, cost controls, custom domains, and teardown.

## Weekly Workflow
1. Update `.env` if provider credentials or proxy settings changed.
2. Run the weekly pipeline with `make run-cli GAMEWEEK=<n> OUTPUT_DIR=data/reports/gw<n>`.
3. Review `data/reports/gw<n>/report.md` and the corresponding JSON artifacts.
4. Start the API with `make run-api` and the frontend with `make run-frontend` for visual review.
5. Re-run with different filters if you want to limit experts or compare outputs.

## Troubleshooting
- `Pipeline could not create any usable video analysis jobs from YouTube sources`: discovery returned no relevant videos, or no usable transcript could be fetched.
- `Pipeline did not produce any expert analyses`: every job failed or had an unusable transcript.
- Webshare errors: if `ENABLE_WEBSHARE_PROXY=true`, both proxy credentials must be set.
- Transcript fetch errors are retried with bounded backoff before being recorded in `manifest.json`.
- Successful transcripts and their revisions are persisted in PostgreSQL.
- When PostgreSQL on Windows times out from WSL, confirm the current host with `ip route show default`, verify the PostgreSQL port, and check that the server listens on a WSL-reachable interface.

## Key Code Paths
- CLI entry: [src/app/cli/run_gameweek_report.py](/home/l/projects/fpl_agent/src/app/cli/run_gameweek_report.py)
- FastAPI app: [src/app/main.py](/home/l/projects/fpl_agent/src/app/main.py)
- Next.js frontend: [frontend/app/dashboard/page.tsx](/home/l/projects/fpl_agent/frontend/app/dashboard/page.tsx)
- Pipeline orchestration: [src/services/pipeline_service.py](/home/l/projects/fpl_agent/src/services/pipeline_service.py)
- Expert transcript analysis: [src/services/expert_analysis_service.py](/home/l/projects/fpl_agent/src/services/expert_analysis_service.py)
- YouTube ingestion: [src/services/transcript_ingestion_service.py](/home/l/projects/fpl_agent/src/services/transcript_ingestion_service.py)
- Aggregation and consensus: [src/services/aggregation_service.py](/home/l/projects/fpl_agent/src/services/aggregation_service.py)
- Final synthesis and fallback report generation: [src/services/synthesis_service.py](/home/l/projects/fpl_agent/src/services/synthesis_service.py)
