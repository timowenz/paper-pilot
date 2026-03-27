# Paper Pilot - Client

Next.js frontend for uploading academic PDFs and downloading the annotated analysis results.

## Setup

Requires Node.js 20+ and [pnpm](https://pnpm.io/).

```bash
cd client
pnpm install
```

## Run

```bash
pnpm dev
```

Opens on `http://localhost:3000`. Make sure the server is running on `http://localhost:8000`.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | No | Backend URL (default: `http://localhost:8000`) |

## Stack

- Next.js 16 (App Router)
- TypeScript
- Tailwind CSS v4
- shadcn/ui components
- Bricolage Grotesque (Google Fonts)
