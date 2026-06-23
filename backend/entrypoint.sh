#!/bin/sh
set -euo pipefail

echo "[entrypoint] Starting PredictWise backend entrypoint"

# Default to no waiting if not using Postgres
DB_HOST=${DB_HOST:-}
DB_PORT=${DB_PORT:-5432}

if [ -n "$DB_HOST" ]; then
  echo "[entrypoint] Waiting for DB at $DB_HOST:$DB_PORT ..."
  for i in $(seq 1 60); do
    if nc -z "$DB_HOST" "$DB_PORT"; then
      echo "[entrypoint] DB is up"
      break
    fi
    echo "[entrypoint] DB not ready yet ($i)"
    sleep 2
  done
fi

# Try to run migrations if migrations folder exists
export FLASK_APP=${FLASK_APP:-backend.app:create_app}
export FLASK_ENV=${FLASK_ENV:-production}

if [ -d "/app/backend/migrations" ]; then
  echo "[entrypoint] Running DB migrations"
  flask db upgrade || echo "[entrypoint] Migration failed or no migrations; continuing"
else
  echo "[entrypoint] No migrations folder; skipping flask db upgrade"
  echo "[entrypoint] Creating tables via SQLAlchemy create_all()"
  python - <<'PY'
from backend.app import create_app
from backend.database import db
app = create_app()
with app.app_context():
    db.create_all()
print('[entrypoint] create_all() completed')
PY
fi

# Start gunicorn
exec gunicorn -w ${GUNICORN_WORKERS:-2} -k gthread --threads ${GUNICORN_THREADS:-4} -b 0.0.0.0:${PORT:-5000} 'backend.app:create_app()'
