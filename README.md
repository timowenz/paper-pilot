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

Images are built for **linux/amd64** and **linux/arm64** (server and client). On Apple Silicon you get a **native ARM** server for speed. If German (or other Hunspell-backed) spellcheck still fails inside the container with native ARM, LanguageTool may be loading the wrong architecture’s natives ([LanguageTool#4543](https://github.com/languagetool-org/languagetool/issues/4543)); then add **`platform: linux/amd64`** under the **`server`** service in Compose (or `docker build --platform linux/amd64 ./server`) to use emulation only for the API.

**One-time:** create a [GitHub personal access token](https://github.com/settings/tokens) with `read:packages` (pull) or use `GITHUB_TOKEN` when logged in via GitHub CLI. For a private repo, the image may be private; set package visibility under **Packages** in your profile or org.

**Log in on any machine:**

```bash
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

**Run published images** (replace owner and use your key):

The compose file needs **`GHCR_OWNER`** for image names. If it is missing, you get `ghcr.io//paper-pilot-server:latest` and **`invalid reference format`**.

**Recommended:** copy [docker.env.example](docker.env.example) to **`.env`** in the same directory as `docker-compose.ghcr.yml`. Docker Compose loads **`.env` automatically** for `${GHCR_OWNER}` substitution (no `--env-file` needed):

```bash
cp docker.env.example .env
# edit .env: set GHCR_OWNER and OPENROUTER_API_KEY (no "export", no spaces around "=")
docker compose -f docker-compose.ghcr.yml up
```

**Alternative:** `docker compose --env-file docker.env ...` — if you use **`sudo`**, pass an **absolute** path: `--env-file /home/rpi/Desktop/docker.env`, because `sudo` can change how relative paths resolve.

If substitution still fails, run `docker compose -f docker-compose.ghcr.yml config` and check that `image:` lines show `ghcr.io/yourname/...` with no double slash.

## Documentation

- **[Client](client/README.md)** — environment variables, scripts, stack  
- **[Server](server/README.md)** — pipeline, API (`POST /analyze-pdf`), prerequisites  

Secrets belong in `server/.env` only; never put API keys in `NEXT_PUBLIC_*` or commit `.env` files.
