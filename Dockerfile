# syntax=docker/dockerfile:1
#
# Single-image deployment: builds the React SPA and serves it from FastAPI
# alongside the API, so the browser only ever talks to one origin.
#
# Build from the REPOSITORY ROOT so that both backend/ and frontend/ are in context:
#   docker build -t fieldnotes .

# ---------- Stage 1: build the React bundle ----------
FROM node:22-alpine AS frontend

WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build          # emits /web/dist


# ---------- Stage 2: Python runtime ----------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# curl is used by the container healthcheck below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend /web/dist ./static

RUN chmod +x ./entrypoint.sh

# Port the app listens on. Must match the target port configured under the
# service's Settings -> Networking -> Public Networking.
ENV APP_PORT=8080

# Drop privileges. The volume-free Railway filesystem does not require root.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# Entrypoint verifies DATABASE_URL, waits for Postgres, migrates, then serves.
CMD ["./entrypoint.sh"]
