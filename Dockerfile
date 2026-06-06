# Mem0 Server — Hardened Build
# Pin to upstream v2.0.4, apply patches at build time, add healthcheck

FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-cache-dir \
    git curl gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python base deps
RUN pip install --no-cache-dir 'psycopg[binary]' pgvector alembic uvicorn fastapi slowapi sqlalchemy pydantic

# Pin to mem0 v2.0.4 — known good version
# This is a SHALLOW clone of just the server subdirectory
ARG MEM0_VERSION=v2.0.4
RUN pip install --no-cache-dir \
    "mem0ai[server,postgres] @ git+https://github.com/mem0ai/mem0.git@${MEM0_VERSION}"

# Copy build-time patcher
COPY mem0_apply_patches.py /app/mem0_apply_patches.py
RUN chmod +x /app/mem0_apply_patches.py

# Apply patches at build time (not runtime)
# Patches are applied to the installed package in site-packages
RUN python3 /app/mem0_apply_patches.py /usr/local/lib/python3.11/site-packages

# Validate patches were applied
RUN python3 -c "import mem0.memory.main as mm; src = open(mm.__file__).read(); assert '(1.0 - mem.score)' in src, 'SCORE PATCH FAILED'; print('PATCH VALIDATED: score inversion active')"

# Copy startup script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Healthcheck using the injected __build__ endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -sf http://localhost:8000/__build__ || exit 1

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
