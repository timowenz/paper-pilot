# Paper Pilot — Client

Web UI for **Paper Pilot**: upload an academic PDF, run the analysis pipeline on the backend, and download an annotated PDF with grammar highlights, coherence notes, and a summary.

## Prerequisites

- Node.js 20+
- [pnpm](https://pnpm.io/)
- The [server](../server) running locally (or a reachable deployment)

## Install

```bash
cd client
pnpm install
```

## Development

```bash
pnpm dev
```

The app is served at [http://localhost:3000](http://localhost:3000). By default it talks to the API at `http://localhost:8000`. Start the server first (see the server README).

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | No | If set, the app calls this origin for `POST /analyze-pdf`. If unset, requests go to `/api/...` and Next.js rewrites them (see `next.config.ts` — use `BACKEND_URL` at build time in Docker). |
| `BACKEND_URL` | No | **Build-time** only: where the Next.js server proxies `/api/*` (default `http://127.0.0.1:8000`). In Docker Compose this is set to `http://server:8000`. |

Only variables prefixed with `NEXT_PUBLIC_` are exposed to the browser; do not put API keys there.

## Production

```bash
pnpm build
pnpm start
```

## Scripts

| Command | Description |
|---------|-------------|
| `pnpm dev` | Next.js dev server with hot reload |
| `pnpm build` | Production build |
| `pnpm start` | Run production server |
| `pnpm lint` | ESLint |

## Stack

- Next.js 16 (App Router), React 19, TypeScript
- Tailwind CSS v4, shadcn/ui (Base UI primitives)
- Bricolage Grotesque (Google Fonts)
