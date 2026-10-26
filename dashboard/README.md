# AI Workstation Dashboard

Local-only management UI for the AI workstation setup repo.

## Requirements

- Node.js 20+
- Repo root must support `python3 -m ai status --json`

## Development

Runs Vite on `127.0.0.1:5173` with `/api` proxied to the dashboard API server (`127.0.0.1:3847` by default):

```bash
cd dashboard
npm install
npm run dev
```

Open http://127.0.0.1:5173 — the API server injects an auth token into the dev page via the proxy; for API calls from the browser, use the production server or ensure the token header is set (production `npm start` injects `window.__DASHBOARD_TOKEN__`).

## Production

```bash
npm run build
npm start
```

Open http://127.0.0.1:3847

On first start, a token is written to `.run/token` (mode `600`). Requests to `/api/status` must include header `X-Dashboard-Token` or `?token=` (the served HTML injects the token for same-origin use).

## Scripts

| Script   | Description                          |
| -------- | ------------------------------------ |
| `dev`    | Vite + API server with watch         |
| `build`  | Typecheck, Vite build, compile server |
| `start`  | Serve `dist/` and API on loopback    |
| `lint`   | TypeScript check (client + server)   |
