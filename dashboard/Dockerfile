# ─── Stage 1: Node.js — Build React SPA ──────────────────────────────────────
FROM node:20-alpine AS node-builder

WORKDIR /build

# Install dependencies first (layer cache)
COPY react/package.json react/package-lock.json* ./
RUN npm ci --prefer-offline

# Copy source and build
COPY react/ .
RUN npm run build
# Output: /build/dist


# ─── Stage 2: Python — Build venv ────────────────────────────────────────────
FROM python:3.12-slim AS py-builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt .

RUN python -m venv /venv \
    && /venv/bin/pip install --upgrade pip \
    && /venv/bin/pip install --no-cache-dir -r requirements.txt


# ─── Stage 3: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Python venv from builder
COPY --from=py-builder /venv /venv

# Application source (Python backend)
COPY app/ ./app/

# Built React SPA → served as static files by FastAPI
COPY --from=node-builder /build/dist /app/static/spa

# Permissions
RUN mkdir -p /app/logs /app/static/avatars \
    && chown -R appuser:appgroup /app

# Activate venv
ENV PATH="/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD /venv/bin/python -c "import httpx; httpx.get('http://localhost:8003/health').raise_for_status()"

CMD ["/venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
