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

3. Open [http://localhost:3000](http://localhost:3000). The UI calls the API at [http://localhost:8000](http://localhost:8000) by default.

## Documentation

- **[Client](client/README.md)** — environment variables, scripts, stack  
- **[Server](server/README.md)** — pipeline, API (`POST /analyze-pdf`), prerequisites  

Secrets belong in `server/.env` only; never put API keys in `NEXT_PUBLIC_*` or commit `.env` files.
