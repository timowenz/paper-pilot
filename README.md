# Paper Pilot

**Paper Pilot** is a small full-stack app for reviewing academic PDFs: upload a thesis or paper, and get back an annotated PDF with grammar and spelling highlights, AI coherence feedback, and a short summary—without storing files on the server.

| | |
|---|---|
| **Web app** | Next.js UI — upload, progress, download |
| **API** | FastAPI — parse, spellcheck, coherence (OpenRouter), annotate PDF |

## Repository layout

```
paper-pilot/
├── client/     # Next.js frontend → [client/README.md](client/README.md)
└── server/     # FastAPI backend   → [server/README.md](server/README.md)
```

## Quick start

1. **Backend** — Python 3.14+, [uv](https://docs.astral.sh/uv/), Java (for LanguageTool). Configure `server/.env` with `OPENROUTER_API_KEY`, then:

   ```bash
   cd server && uv sync
   cd src && uv run python main.py
   ```

2. **Frontend** — Node 20+, [pnpm](https://pnpm.io/):

   ```bash
   cd client && pnpm install && pnpm dev
   ```

3. Open [http://localhost:3000](http://localhost:3000). In development the UI uses the Next.js rewrite `/api/*` → backend (see `client/next.config.ts`), or set `NEXT_PUBLIC_API_URL` to call the API directly.

## Docker

Build and run both services locally:

```bash
export OPENROUTER_API_KEY=sk-or-v1-...   # required for coherence
docker compose build
docker compose up
```

- UI: [http://localhost:3000](http://localhost:3000) (proxies API calls to the `server` container).
- API: [http://localhost:8000](http://localhost:8000) — `GET /health` for readiness.

### GitHub Container Registry (GHCR)

After you push to `main` (or tag `v*`), the workflow [.github/workflows/docker-ghcr.yml](.github/workflows/docker-ghcr.yml) builds and pushes:

- `ghcr.io/<your-github-user>/paper-pilot-server:latest`
- `ghcr.io/<your-github-user>/paper-pilot-client:latest`

**One-time:** create a [GitHub personal access token](https://github.com/settings/tokens) with `read:packages` (pull) or use `GITHUB_TOKEN` when logged in via GitHub CLI. For a private repo, the image may be private; set package visibility under **Packages** in your profile or org.

**Log in on any machine:**

```bash
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

**Run published images** (replace owner and use your key):

```bash
export GHCR_OWNER=your-github-username
export OPENROUTER_API_KEY=sk-or-v1-...
docker compose --env-file docker.env -f docker-compose.ghcr.yml up
```

Copy [docker.env.example](docker.env.example) to `docker.env` and edit `GHCR_OWNER` and `OPENROUTER_API_KEY`.

## Documentation

- **[Client](client/README.md)** — environment variables, scripts, stack  
- **[Server](server/README.md)** — pipeline, API (`POST /analyze-pdf`), prerequisites  

Secrets belong in `server/.env` only; never put API keys in `NEXT_PUBLIC_*` or commit `.env` files.
