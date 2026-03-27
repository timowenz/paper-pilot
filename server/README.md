# Paper Pilot - Server

FastAPI backend that analyzes academic PDF documents for grammar, spelling, and coherence.

## What it does

1. **Parse** - Extracts text from a PDF using `pymupdf4llm`, cleans OCR artifacts, and splits into section-based chunks.
2. **Spellcheck** - Runs each chunk through LanguageTool with smart false-positive filtering (dynamic whitelist, list-item detection, heuristic patterns).
3. **Coherence** - Sends the full document to an LLM (via OpenRouter) to evaluate narrative flow, logical breaks, and academic writing style.
4. **Annotate** - Highlights errors in the original PDF, attaches sticky notes with descriptions, and appends a summary report at the end.
5. **Return** - Streams the annotated PDF back. Nothing is stored on disk (GDPR compliant).

## Setup

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
cd server
uv sync
```

## Environment variables

Create `server/.env` or export in your shell:

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | API key for OpenRouter (coherence check) |
| `COHERENCE_MODEL` | No | Model to use (default: `openai/gpt-oss-20b:free`) |

On startup the app loads `server/.env` via `python-dotenv`, so you do not need to set these in the shell if they are in that file.

## Run

```bash
cd server/src
uv run python main.py
```

The server starts on `http://localhost:8000`.

## API

### `POST /analyze-pdf`

Upload a PDF file and receive the annotated version.

```bash
curl -X POST http://localhost:8000/analyze-pdf \
  -F "file=@thesis.pdf" \
  --output thesis_annotated.pdf
```

**Request:** `multipart/form-data` with a `file` field (PDF only).

**Response:** `application/pdf` - the annotated PDF with grammar highlights, coherence notes, and a summary report.
