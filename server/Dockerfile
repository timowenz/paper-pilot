# syntax=docker/dockerfile:1
# Hunspell: use -dev so /usr/lib/.../libhunspell.so symlink exists (JNA often loads that
# name; runtime-only libhunspell-*-0 was not enough on arm64 — see LanguageTool#4543 / RPi reports).
# If it still fails on arm64, pin server to platform: linux/amd64 in Compose.
FROM python:3.14-slim-trixie

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libhunspell-dev \
    openjdk-25-jre-headless \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV PYTHONPATH=/app/src
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev

EXPOSE 8000
ENV HOST=0.0.0.0
ENV PORT=8000
CMD ["uv", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
