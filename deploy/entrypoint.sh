#!/bin/bash
set -e

echo "========================================"
echo "Mem0 Server Starting"
echo "Version: v2.0.4 (pinned)"
echo "Build: BUILD-20260606-HARDENED"
echo "Patch set: ollama-llm, 1536-dim, score-inversion"
echo "========================================"

# Verify env vars are set
: "${OPENAI_API_KEY:?OPENAI_API_KEY is not set}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is not set}"

echo "Environment check: OK"
echo "Postgres host: ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}"
echo "Embedder model: ${MEM0_DEFAULT_EMBEDDER_MODEL:-text-embedding-3-small}"
echo "LLM model: ${MEM0_DEFAULT_LLM_MODEL:-gpt-oss:20b-cloud}"

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Verify build endpoint is accessible
echo "Starting uvicorn on 0.0.0.0:8000..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers
