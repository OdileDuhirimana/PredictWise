# ADR 0001: SQLite by default, Postgres via DATABASE_URL in production

## Status

Accepted

## Context

PredictWise needs a database that works with zero setup for local
development and grading/demo purposes, but that can also run in a real
production deployment with concurrent write traffic (a school's admin,
teachers, and parents all hitting the API simultaneously). Requiring a
Postgres install just to run `python -m backend.app` locally would raise
the barrier to trying the project; requiring SQLite in production would
mean data loss risk under concurrent writes (SQLite serializes writers at
the file level) and would make `docker-compose.yml`'s multi-container
setup (`db` + `backend`) pointless.

## Decision

SQLAlchemy is used as the persistence layer specifically because it makes
the database engine a configuration choice rather than a code choice:

- `DATABASE_URL` unset (or absent) → falls back to `sqlite:///predictwise.db`
  in non-production environments (`backend/app.py::create_app`).
- `DATABASE_URL` set → used as-is, with `postgres://`/`postgresql://`
  schemes normalized to `postgresql+psycopg://` for the `psycopg` v3
  driver already pinned in `requirements.txt`.
- Production (`FLASK_ENV=production`) requires `DATABASE_URL` to be set
  explicitly — there is no silent SQLite fallback in production, matching
  the same fail-closed pattern used for `JWT_SECRET_KEY` and
  `CORS_ALLOWED_ORIGINS`.
- `docker-compose.yml` provisions a real Postgres 16 container for any
  environment that wants to exercise the production-shaped path locally.

## Consequences

**Positive:**
- Zero-config local development and grading (`git clone` → `pip install`
  → `flask db upgrade` → running app, no external services required).
- The exact same application code runs against either engine; only the
  connection string changes.

**Negative / accepted tradeoffs:**
- SQLite's single-writer model is a real limitation if local development
  ever needs to simulate concurrent-write load — it doesn't, today, but a
  contributor debugging a "why did my write silently serialize" question
  should know this is expected SQLite behavior, not an application bug.
- Two database engines means two things that could theoretically diverge
  in behavior (e.g. `CheckConstraint` SQL syntax differences, which is why
  `backend/migrations/env.py` conditionally enables Alembic's batch mode
  only for the sqlite dialect — see the migration that added indexes and
  check constraints).
- `render.yaml`'s default deployment configuration currently uses SQLite
  in production for demo simplicity, which is itself a deliberate,
  disclosed tradeoff (documented in `project.md`'s "Challenges &
  Tradeoffs") rather than the recommended production configuration.
