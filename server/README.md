# Paper Pilot — Server

FastAPI backend that analyzes academic PDFs for grammar, spelling, and coherence, then returns an **annotated PDF** (highlights, sticky notes, summary pages). Uploads are processed in memory only—nothing is written to disk for GDPR-friendly operation.

## Pipeline

1. **Parse** — Text extraction with `pymupdf4llm`, cleanup of OCR noise, section-aware chunking.
2. **Spellcheck** — LanguageTool per chunk, with heuristics to reduce false positives (whitelist, list detection, skippable sections).
3. **Coherence** — Full-document pass via OpenRouter (LLM) for flow, logic, and style.
4. **Annotate** — Errors located in the PDF, notes attached, summary appended.
5. **Return** — PDF bytes in the HTTP response.

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- **LanguageTool** (Java) — `language-tool-python` downloads and runs LanguageTool; a JRE/JDK 17+ is required on the machine.

## Install

```bash
cd server
uv sync
```

## Environment variables

Create `server/.env` (gitignored). Values are loaded at startup with `python-dotenv`; shell exports still work and override the file.

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key (coherence step) |
| `COHERENCE_MODEL` | No | Model id (default: `openai/gpt-oss-20b:free`) |
| `HOST` / `PORT` | No | Bind address (default `127.0.0.1:8000`; use `HOST=0.0.0.0` in containers). |
| `CORS_ORIGINS` | No | Comma-separated origins (default includes `http://localhost:3000`). |

## Docker

From the repo root, `docker compose` builds `server/Dockerfile` (Debian slim, Java + Tesseract, `uv sync`). The API listens on `0.0.0.0:8000`. See the [root README](../README.md#docker) for Compose and GHCR.

## Run

```bash
cd server/src
uv run python main.py
```

API base: [http://127.0.0.1:8000](http://127.0.0.1:8000). CORS defaults allow the Next.js dev origin; override with `CORS_ORIGINS` if needed.

### `GET /health`

Returns `{"status":"ok"}` for load balancers and Compose health checks.

## API

### `POST /analyze-pdf`

Upload a PDF; response is the annotated PDF.

**Request:** `multipart/form-data` with field `file` (PDF).

**Response:** `application/pdf` with `Content-Disposition` attachment.

```bash
curl -X POST http://localhost:8000/analyze-pdf \
  -F "file=@thesis.pdf" \
  --output thesis_annotated.pdf
```

## Stack

- FastAPI, Uvicorn
- pymupdf4llm, PyMuPDF (via annotator)
- language-tool-python, LanguageTool
- OpenAI-compatible client → OpenRouter (coherence)
