#!/bin/sh
# Container entrypoint: verify the database is configured and reachable, migrate,
# then hand off to uvicorn.
set -e

# --- Fail fast with an actionable message instead of a SQLAlchemy stack trace ---
RESOLVED_HOST=$(python - <<'PY'
import os
from urllib.parse import urlparse

url = os.environ.get("DATABASE_URL", "")
# Strip a dialect modifier so urlparse sees the real scheme.
print(urlparse(url.replace("postgresql+", "postgresql", 1)).hostname or "")
PY
)

if [ -z "$RESOLVED_HOST" ]; then
    echo "=============================================================="
    echo " FATAL: DATABASE_URL is not set on this service."
    echo ""
    echo " Add it on the Railway service Variables tab:"
    echo "   key   DATABASE_URL"
    echo "   value \${{Postgres.DATABASE_URL}}"
    echo ""
    echo " Use the value-field autocomplete dropdown, then DEPLOY the"
    echo " staged change. Variables do not apply until you redeploy."
    echo "=============================================================="
    exit 1
fi

if [ "$RESOLVED_HOST" = "localhost" ] || [ "$RESOLVED_HOST" = "127.0.0.1" ]; then
    echo "=============================================================="
    echo " FATAL: DATABASE_URL still points at ${RESOLVED_HOST}."
    echo ""
    echo " That is the development default from backend/app/config.py,"
    echo " so the environment variable is missing or empty. Set"
    echo " DATABASE_URL=\${{Postgres.DATABASE_URL}} on the service and"
    echo " deploy the staged change."
    echo "=============================================================="
    exit 1
fi

# --- Wait for Postgres -------------------------------------------------------
# On a fresh Railway deploy the app container can start before the database
# accepts connections. Retry briefly instead of crash-looping.
echo "Waiting for postgres at ${RESOLVED_HOST} ..."
attempt=0
while [ "$attempt" -lt 30 ]; do
    attempt=$((attempt + 1))
    if python -c "
from app.config import settings
from sqlalchemy import create_engine
create_engine(settings.database_url).connect().close()
" >/dev/null 2>&1; then
        echo "Postgres reachable after ${attempt} attempt(s)."
        break
    fi
    if [ "$attempt" -eq 30 ]; then
        echo "FATAL: postgres at ${RESOLVED_HOST} never became reachable."
        echo "Check that the Postgres service is running and that"
        echo "DATABASE_URL points at its DATABASE_URL, not DATABASE_PUBLIC_URL."
        exit 1
    fi
    sleep 2
done

# --- Migrate, then serve -----------------------------------------------------
# Alembic is idempotent, so this is safe on every deploy.
alembic upgrade head

# Listen on 8080 unconditionally. Railway's public HTTP proxy is pointed at this
# port in the service's Public Networking settings, so deriving it from Railway's
# injected PORT would only work as long as the two stayed in sync. Override with
# APP_PORT if the port ever needs to change.
echo "Starting uvicorn on 0.0.0.0:${APP_PORT:-8080}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT:-8080}"
