#!/bin/sh
set -e

# Prefer real Alembic migrations (backend/migrations) so schema changes are
# tracked and reversible in production, mirroring entrypoint.sh. Only fall
# back to db.create_all() (no migration history, just "make tables match
# models.py") when no migrations directory has been generated yet — this
# keeps `start.sh` usable in environments (e.g. a fresh clone before anyone
# has run `flask db init`) where migrations/ doesn't exist.
export FLASK_APP=${FLASK_APP:-backend.app:create_app}

if [ -d "backend/migrations" ]; then
  echo "[start] Running DB migrations"
  flask db upgrade || echo "[start] Migration failed; continuing"
else
  echo "[start] No migrations folder; creating tables via SQLAlchemy create_all()"
  python - <<'PY'
from backend.app import create_app
from backend.database import db
app = create_app()
with app.app_context():
    db.create_all()
print("[start] Tables ready")
PY
fi

exec gunicorn -w 2 -k gthread --threads 4 -b 0.0.0.0:${PORT:-5000} wsgi:application
