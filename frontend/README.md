# EWA Dashboard — Frontend

React + TypeScript + Vite + Tailwind CSS frontend for the EWA (SAP EarlyWatch
Alert) analysis tool.

## Stack

- React 18, TypeScript 5, Vite 6
- Tailwind CSS 3.4
- react-router-dom 6
- recharts (charts)
- axios (API client)

## Prerequisites

- Node 22, npm 10
- The backend running on `http://localhost:8000`

## Getting started

```bash
npm install
npm run dev
```

The dev server runs on <http://localhost:5173>. Requests to `/api` and `/health`
are proxied to `http://localhost:8000` (see `vite.config.ts`), so no CORS setup
is required in development.

### Demo logins

| Email                | Password  | Role     |
| -------------------- | --------- | -------- |
| admin@example.com    | admin     | admin    |
| operator@example.com | operator  | operator |
| viewer@example.com   | viewer    | viewer   |

## Environment variables

| Variable        | Default | Description                                            |
| --------------- | ------- | ------------------------------------------------------ |
| `VITE_API_BASE` | `/api`  | Base URL for the backend API. The default works with the Vite dev proxy and a production reverse-proxy. |

Copy `.env.example` to `.env` to override.

## Scripts

- `npm run dev` — start the dev server (port 5173)
- `npm run build` — type-check (`tsc -b`) and produce a production build in `dist/`
- `npm run preview` — preview the production build
- `npm run lint` — type-check only (`tsc --noEmit`)

## Production

`npm run build` emits static assets to `dist/`. Serve them behind a reverse
proxy that forwards `/api` (and `/health`) to the backend, or set
`VITE_API_BASE` to the API's absolute URL at build time.
