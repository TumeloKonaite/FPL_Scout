# kasifpl Frontend

Next.js provides a public recommendations experience and a protected operations area.

## Suggested-team API contract

The selected report may include `report.suggested_team` with an optional `formation`, an
exactly 11-player `startingXi`, and an optional complete `players` array (starters and
substitutes) for the detail table. Each player requires `playerId`, `name`, `number`, and
a normalized `position` (`GK`, `DEF`, `MID`, or `FWD`). Optional detail fields include
`club`, `price`, `predictedPoints`, `ownership`, `expectedMinutes`,
`fixtureDifficulty`, `captain`, `viceCaptain`, and `isStarter`.

The pitch rejects a supplied formation when it differs from the formation derived from
the XI. This strict behavior prevents an incorrect tactical shape from being shown;
the detail table remains available for diagnosis and legacy reports remain supported.

## Pages

- Dashboard: loads the URL-selected season/gameweek report
- Reports: renders the selected canonical public report without internal run metadata
- Public report pages share `?season=YYYY-YY&gameweek=N`; the header selector and
  report navigation preserve that selection for bookmarkable historical views
- Suggested Team
- Captaincy
- Transfers
- Expert Consensus
- Admin (`/admin`): authenticated report-pipeline execution and internal status

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
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
API_PROXY_TARGET=http://127.0.0.1:8000
```

For a Vercel deployment backed by Modal, set `API_PROXY_TARGET` to the public Modal
API URL. Clerk owns the browser session. For `/api/admin/*` requests, the server-side
proxy retrieves the Clerk session token and forwards it to FastAPI as a bearer token.

Browser requests always use the same-origin `/backend/*` proxy; no backend URL,
Clerk secret key, or pipeline credential is included in the client bundle.

Public pages call only `/api/recommendations`,
`/api/recommendations/gameweeks`, and `/api/gameweek/current`. The protected
admin UI calls only `/api/admin/pipeline/run`, `/api/admin/pipeline/status`, and
`/api/admin/runs/{run_id}`. Parallel compatibility route families are not used.

Start the FastAPI backend from the repository root:

```bash
make run-api
```

Generated report snapshots are loaded through the backend API from PostgreSQL.

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
