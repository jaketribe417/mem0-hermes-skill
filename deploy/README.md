# Mem0 Deployment — Hardened v2.0.4

## Architecture

This deployment replaces the fragile inline base64 runtime patch with a proper Dockerfile-based build.

- **Mem0 API**: `mem0-app:patched-v2.0.4` — pinned to upstream v2.0.4, build-time patching
- **Dashboard**: `mem0-dashboard:built` — pre-built in CI, no source rebuild on startup
- **Postgres**: `ankane/pgvector:v0.5.1` — with healthcheck

## Changes from Previous Deployment

1. **Pinned upstream**: `v2.0.4` instead of `main` branch
2. **Build-time patching**: `mem0_apply_patches.py` runs at Docker build, not container startup
3. **No inline base64**: Removed 1200-char base64 patch from compose command
4. **Healthchecks**: All 3 containers now have HEALTHCHECK stanzas
5. **Pre-built dashboard**: Multi-stage Dockerfile, `next build` happens in CI not on VPS

## Embedding Dimensions

**Actual: 1536** (OpenAI text-embedding-3-small)
- pgvector brute-force cosine (no ANN — HNSW caps at 2000 dims)
- Score range: 0.1–0.5 (cosine distance inverted to similarity in patch)

## Patches Applied

| Patch | Target | Purpose |
|-------|--------|---------|
| Ollama LLM | `/app/main.py` | Configure Ollama Cloud `gpt-oss:20b-cloud` |
| 1536-dim embedder | `DEFAULT_CONFIG` | Set `embedding_model_dims: 1536` |
| Score inversion | `mem0/memory/main.py` | Flip `mem.score` to `(1.0 - mem.score)` |
| `__build__` endpoint | `main.py` | Health/telemetry endpoint |

## Backup

- **Local**: Postgres data volume persists across restarts
- **S3 placeholder**: `s3://my-mem0-backup/` — add credentials when ready

## Deployment

```bash
cd deploy
docker-compose up --build -d
```

## Health Verification

```bash
curl -sf https://mem0api.jhostly.com/__build__
curl -sf https://mem0.jhostly.com/login
```

## Known Issues (v2.0.4)

- **DELETE /memories/{id}**: Returns 502 — use `DELETE /memories?user_id=xxx&agent_id=yyy` for bulk deletion
- **Score range**: Non-intuitive (0.1–0.5) — filter client-side with threshold 0.3+
