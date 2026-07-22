# FPL Technocrat Frontend

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
- Admin (`/admin`): authenticated pipeline execution, report generation, and internal status

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
API URL. Administrators enter the backend's `ADMIN_API_TOKEN` on `/admin/login`; it is
stored in an HttpOnly, same-site session cookie and forwarded only to `/api/admin/*`.

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
