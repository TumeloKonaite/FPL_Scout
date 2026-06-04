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

The API helper in `lib/api.ts` defaults to `http://localhost:8000`.

To point the frontend at another FastAPI URL, create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

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
