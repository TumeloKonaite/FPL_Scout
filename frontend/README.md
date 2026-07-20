# FPL Technocrat Frontend

Next.js is the only frontend for the FPL Technocrat report dashboard and pipeline runner.

## Pages

- Dashboard: loads the latest generated report
- Reports: lists historical reports and renders the selected run
- Suggested Team
- Captaincy
- Transfers
- Expert Consensus
- Pipeline Runner: triggers a backend pipeline run and shows the result or error

## Setup

Install dependencies:

```bash
npm install
```

Run the development server:

```bash
npm run dev
```

Open `http://localhost:3000`.

## Backend Configuration

The frontend proxies `/backend/*` to `http://127.0.0.1:8000` by default. This keeps
browser requests same-origin and works when the UI is opened through a WSL or LAN IP.

To point the server-side proxy at another FastAPI URL, create `frontend/.env.local`:

```bash
API_PROXY_TARGET=http://127.0.0.1:8000
```

For a Vercel deployment backed by Modal, set `API_PROXY_TARGET` to the public Modal
API URL and set `PIPELINE_API_TOKEN` to the same value stored in the Modal secret.
Both are server-only variables and must not use a `NEXT_PUBLIC_*` prefix.

Browser requests always use the same-origin `/backend/*` proxy; no backend URL or
pipeline credential is included in the client bundle.

Start the FastAPI backend from the repository root:

```bash
make run-api
```

Generated report artifacts are loaded from the backend's configured `data/reports/` directory.

## Verification

Run the frontend parity tests:

```bash
npm run test
```

Build the app:

```bash
npm run build
```

Lint the app:

```bash
npm run lint
```

Check the main routes:

- `/`
- `/dashboard`
- `/reports`
- `/suggested-team`
- `/captaincy`
- `/transfers`
- `/expert-consensus`
- `/pipeline-runner`
