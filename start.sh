#!/bin/sh
set -e

python - <<'PY'
from backend.app import create_app
from backend.database import db
app = create_app()
with app.app_context():
    db.create_all()
print("[start] Tables ready")
PY

exec gunicorn -w 2 -k gthread --threads 4 -b 0.0.0.0:${PORT:-5000} wsgi:application
