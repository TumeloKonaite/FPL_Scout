# FPL Technocrat Frontend

Next.js application shell for the FPL Technocrat product UI.

## Pages

- Dashboard
- Reports
- Suggested Team
- Captaincy
- Transfers
- Expert Consensus
- Pipeline Runner

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

No backend integration is wired into the placeholder pages yet.

## Verification

Build the app:

```bash
npm run build
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
