# kasifpl

[![Backend CI/CD](https://github.com/TumeloKonaite/FPL_Scout/actions/workflows/backend-ci-cd.yml/badge.svg)](https://github.com/TumeloKonaite/FPL_Scout/actions/workflows/backend-ci-cd.yml)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-000000?logo=next.js&logoColor=white)](frontend/package.json)
[![MIT License](https://img.shields.io/badge/License-MIT-2ea44f.svg)](LICENSE)

kasifpl turns Fantasy Premier League expert analysis into structured,
gameweek-specific recommendations. The pipeline selects timely expert videos,
collects and validates their evidence, extracts individual recommendations,
builds a consensus report, and publishes that report through a FastAPI API and
a Next.js web application.

The public experience provides:

- a weekly briefing with key decisions, risks, and news to monitor;
- a suggested starting XI and bench when the report has a valid squad;
- prioritised transfer recommendations;
- captaincy recommendations and comparisons;
- expert consensus, team reveals, agreements, and disagreements;
- a historical archive of published season/gameweek reports; and
- protected administration for starting pipelines, generating reports, and
  monitoring run status.

![kasifpl Suggested Team page showing the gameweek squad and its consensus provenance](docs/assets/kasifpl-suggested-team.png)

## Architecture

- **Backend:** FastAPI on Python 3.12+, with the analysis and report pipeline
  dispatched to a background worker in production.
- **Frontend:** Next.js 15 and React 19. Browser requests use the same-origin
  Next.js `/backend/*` proxy to reach FastAPI.
- **Durable storage:** PostgreSQL is authoritative for transcripts, revisions,
  pipeline runs, report artifacts, rendered Markdown, publication state, and
  completed report snapshots.
- **Caching:** Redis is optional, never authoritative, and is not required or
  configured by the current checkout. The application works directly with
  PostgreSQL and uses only small process-local caches where implemented.
- **Production:** Vercel hosts the Next.js frontend, Modal runs the replaceable
  FastAPI and pipeline-worker containers, and Supabase provides PostgreSQL.

Completed reports are immutable point-in-time snapshots. Public queries return
only the published, completed snapshot for a season and gameweek. Publication,
supersession, and pipeline completion are protected by PostgreSQL constraints
and transactions. Neither local files nor Modal Volumes are a fallback or
recovery source for application data.

## Repository names

**kasifpl** is the product and user-facing brand. Some internal identifiers
remain from earlier versions and are kept for compatibility:

| Identifier | Current use |
| --- | --- |
| `FPL_Scout` | Repository/directory name in some clones |
| `fpl-agent` | Python project metadata and default Docker image name |
| `fpl_scout` | Default local PostgreSQL database name |
| `fpl-technocrat` | Legacy Modal application identifier |

These names do not refer to separate products.

## Prerequisites

- Python 3.12 or newer;
- [`uv`](https://docs.astral.sh/uv/) for locked Python environments and
  commands;
- Node.js with npm (Node.js 20 LTS or newer is recommended); and
- Docker with the Compose v2 plugin for local PostgreSQL and container
  workflows.

## Local setup

Run the following from the repository root after a fresh clone:

```bash
cp .env.example .env
make install
make install-frontend
docker compose up -d postgres
uv run alembic upgrade head
```

The checked-in development URLs connect both the application and Alembic to
the local PostgreSQL container at
`postgresql+psycopg://postgres:postgres@localhost:5432/fpl_scout`.

Start the backend in one terminal:

```bash
make run-api
```

Start the frontend in another:

```bash
make run-frontend
```

Open:

- kasifpl: <http://localhost:3000>
- FastAPI interactive documentation: <http://localhost:8000/docs>
- backend health check: <http://localhost:8000/health>

The frontend proxy targets `http://127.0.0.1:8000` by default, so no frontend
environment file is needed for this local layout. See
[the frontend README](frontend/README.md) when the frontend must target a
different backend.

To stop the local services, stop both development processes and run:

```bash
make docker-down
```

### Containerized backend alternative

`make docker-run` builds the backend image, starts PostgreSQL, applies Alembic
migrations, and starts FastAPI. A backend container must use the Compose service
hostname rather than `localhost`:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/fpl_scout \
DIRECT_DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/fpl_scout \
make docker-run
```

Start the frontend separately with `make run-frontend`.

## Configuration

`.env.example` is the source of truth for backend configuration. Copy it to
`.env`, keep real credentials out of Git, and change only the settings needed
for the workflow being run.

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Required for expert-analysis and synthesis pipeline runs |
| `OPENAI_BASE_URL`, `OPENAI_MODEL` | Optional OpenAI-compatible endpoint and model selection |
| `DATABASE_URL` | PostgreSQL URL used by application traffic |
| `DIRECT_DATABASE_URL` | PostgreSQL URL used by Alembic; in production this must be a direct or session-pooled connection, not the transaction pooler |
| `DATABASE_POOL_MODE` | Connection mode: `auto`, `direct`, `session`, or `transaction` |
| `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW` | SQLAlchemy pool bounds |
| `DATABASE_POOL_TIMEOUT_SECONDS`, `DATABASE_POOL_RECYCLE_SECONDS`, `DATABASE_CONNECT_TIMEOUT_SECONDS` | Database timeout and connection-lifecycle settings |
| `TRANSCRIPT_FAILURE_RETRY_HOURS` | Delay before retrying a failed transcript |
| `VIDEO_SELECTION_WINDOW_DAYS_BEFORE`, `VIDEO_SELECTION_WINDOW_DAYS_AFTER` | Allowed publication window around the supplied gameweek deadline |
| `CORS_ORIGINS` | JSON list of browser origins accepted by FastAPI |
| `ENVIRONMENT` | Runtime environment; production mode enables stricter database validation |
| `CLERK_ISSUER` | Clerk application issuer used to locate its JWKS and validate session tokens |
| `CLERK_AUTHORIZED_PARTIES` | Comma-separated frontend origins accepted in Clerk's `azp` claim |
| `CLERK_ADMIN_USER_IDS` | Comma-separated Clerk user IDs authorized as administrators |
| `PIPELINE_API_TOKEN` | Machine-only bearer token for trusted scripts, cron jobs, and CI/CD |
| `ENABLE_WEBSHARE_PROXY` | Enables the optional Webshare route for transcript requests |
| `WEBSHARE_PROXY_USERNAME`, `WEBSHARE_PROXY_PASSWORD` | Webshare credentials when its proxy is enabled |

Keep database URLs, `CLERK_SECRET_KEY`, and provider credentials server-side.
Only Clerk's publishable key may use a `NEXT_PUBLIC_*` variable. Clerk owns the
browser session; the Next.js proxy forwards a short-lived Clerk token only to
the protected backend API. The machine pipeline token is never sent to the browser.

## Commands

The commands below map directly to the current `Makefile`, `pyproject.toml`,
and `frontend/package.json` scripts.

| Task | Command |
| --- | --- |
| Install backend and development dependencies | `make install` |
| Install frontend dependencies | `make install-frontend` |
| Apply database migrations | `uv run alembic upgrade head` |
| Run backend tests | `make test` |
| Lint backend Python | `make lint` |
| Run frontend tests | `npm --prefix frontend run test` |
| Lint frontend TypeScript/React | `npm --prefix frontend run lint` |
| Build the production frontend | `npm --prefix frontend run build` |
| Start the backend development server | `make run-api` |
| Start the frontend development server | `make run-frontend` |
| Build the backend Docker image | `make docker-build` |
| Start the containerized backend and PostgreSQL | `make docker-run` |

PostgreSQL integration tests are enabled only when `TEST_DATABASE_URL` points
to a dedicated database whose name ends in `_test`; without it, pytest skips
those tests. The regular `make test` command still runs the rest of the backend
suite.

To run the weekly pipeline from the CLI, supply a season; the Make target
defaults to gameweek 32, two videos per expert, and synthesis disabled:

```bash
make run-cli SEASON=2025-26 GAMEWEEK=32
```

Set `SYNTHESIS=1` to enable synthesis. `RUN_ID`, `PER_EXPERT_LIMIT`,
`EXPERT_NAME`, and `EXPERT_COUNT` are optional Make variables.

## Frontend routes

The public pages are:

| Route | Purpose |
| --- | --- |
| `/` and `/dashboard` | Weekly or selected historical briefing |
| `/suggested-team` | Suggested XI, bench, and player support |
| `/transfers` | Transfer recommendations |
| `/captaincy` | Captaincy comparison |
| `/expert-consensus` | Expert reveals, agreements, and disagreements |
| `/reports` | Historical report archive |

Recommendation pages support bookmarkable
`?season=YYYY-YY&gameweek=N` selections. Administrative routes are:

| Route | Purpose |
| --- | --- |
| `/admin/login` | Administrator sign-in |
| `/admin` | Protected pipeline execution and status dashboard |

`/pipeline-runner` is a compatibility redirect to `/admin`.
`/backend/[...path]` is the server-side backend proxy, not a user-facing page.

## FastAPI routes

Public application routes and their in-repository consumers:

| Route | Consumer |
| --- | --- |
| `GET /health` | Deployment readiness checks, Modal smoke test, and API tests |
| `GET /api/recommendations/latest` | Public API clients and API tests |
| `GET /api/recommendations/gameweeks` | Frontend report selector/archive and API tests |
| `GET /api/recommendations?season=YYYY-YY&gameweek=N` | Frontend report pages, regeneration verification, and API tests |
| `GET /api/gameweek/current` | Frontend report selection and API tests |

The API also exposes `GET /` for a basic service message, `GET /openapi.json`
for its schema, and FastAPI's generated UIs at `GET /docs` and `GET /redoc`.

Protected administrative routes require either an authorized Clerk session JWT
for a human administrator or the machine-only `PIPELINE_API_TOKEN`:

| Route | Consumer |
| --- | --- |
| `POST /api/admin/pipeline/run` | Frontend admin dashboard, Modal smoke test, and API tests |
| `GET /api/admin/pipeline/status` | Frontend admin session guard/dashboard and API tests |
| `GET /api/admin/runs/{run_id}` | Frontend polling, Modal smoke test, and API tests |
| `GET /api/admin/reports` | Administrative API clients and API tests |
| `GET /api/admin/reports/{run_id}` | Deployment verification, administrative API clients, and API tests |

These are the canonical protected routes; the API does not register parallel
compatibility aliases. The pipeline start performs the complete analysis and
report-generation workflow. Public pages use only the recommendation endpoints
above and never expose internal run identifiers.

The Python CLI invokes application services directly; it does not consume the
HTTP API. `GET /`, FastAPI's schema/UI routes, and the Next.js proxy/session
handlers are infrastructure surfaces rather than report or pipeline operations.

## Deployment and operations

Production uses Supabase's transaction pooler for `DATABASE_URL` and a direct
or session-pooled URL for `DIRECT_DATABASE_URL`. Modal deploys the API and
worker without a persistent Volume; Vercel deploys the frontend and points its
server-side proxy at the Modal API.

Run the production schema gate before deploying backend code:

```bash
make modal-migrate
make modal-verify
make modal-deploy
```

Operational details live in dedicated documentation:

- [Modal deployment, schema verification, legacy cutover, and recovery](docs/modal-deployment.md)
- [Completed-report publication semantics](docs/report-publication.md)
- [Consensus XI deployment and historical regeneration](docs/consensus-xi-regeneration.md)
- [Completed-report lookup-index validation](docs/completed-report-public-index-validation.md)

Historical regeneration and legacy storage import are controlled, auditable
operations. Use the dry-run and verification procedures in those documents
rather than treating generated files as durable state. Recovery is performed
from PostgreSQL backups/PITR, followed by migration and database verification;
container files and retired Modal Volumes are not recovery sources.
