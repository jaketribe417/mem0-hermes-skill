# Mem0 Dashboard — Pre-built, no source rebuild on startup
# Multi-stage build: build once, serve static output

FROM node:22-alpine AS builder

WORKDIR /app

# Install build deps
RUN apk add --no-cache libc6-compat git

# Clone dashboard source at pinned version
ARG MEM0_VERSION=v2.0.4
RUN git clone --depth 1 --branch ${MEM0_VERSION} https://github.com/mem0ai/mem0.git /src \
    && cp -r /src/server/dashboard/* /app/

# Enable pnpm and install deps
RUN corepack enable pnpm \
    && pnpm install --frozen-lockfile \
    && pnpm rebuild sharp unrs-resolver

# Build the dashboard
ENV NEXT_PUBLIC_API_URL=https://mem0api.jhostly.com
ENV API_INTERNAL_URL=http://mem0:8000
ENV NEXT_PUBLIC_INSTANCE_NAME=Mem0
RUN node_modules/.bin/next build

# Runtime stage — lightweight server
FROM node:22-alpine

WORKDIR /app

# Copy built artifacts
COPY --from=builder /app/.next /app/.next
COPY --from=builder /app/node_modules /app/node_modules
COPY --from=builder /app/package.json /app/package.json

# Serve with next start (no build)
EXPOSE 3000
CMD ["sh", "-c", "node_modules/.bin/next start -H 0.0.0.0 -p 3000"]
