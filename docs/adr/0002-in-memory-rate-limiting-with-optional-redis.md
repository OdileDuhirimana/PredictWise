# ADR 0002: In-memory rate limiting by default, Redis-backed when configured

## Status

Accepted

## Context

Flask-Limiter needs a storage backend to track request counts per client.
The two realistic options for this project are its built-in in-memory
store (zero configuration, but per-process and lost on restart) and a
Redis-backed store (correct across multiple gunicorn workers and process
restarts, but requires a Redis deployment).

An earlier pass left this as in-memory only, explicitly disclosed as a
known gap in `project.md`. Requiring Redis unconditionally would break the
project's own zero-config local-dev story (ADR 0001's same motivation)
and would make grading/demo environments depend on a service this
codebase has no other reason to need.

## Decision

`backend/app.py::create_app()` selects the storage backend based on
`REDIS_URL`:

- Unset → Flask-Limiter's default in-memory storage (Flask-Limiter itself
  emits a startup warning in this case, which is expected and left
  visible rather than suppressed).
- Set → `Limiter(..., storage_uri=REDIS_URL)`, giving correct rate-limit
  enforcement across every gunicorn worker (`.env.example`'s
  `GUNICORN_WORKERS=2`) and surviving process restarts.

The selection logic is isolated in `_limiter_storage_kwargs()` specifically
so it can be unit-tested (`test_app_config.py::TestLimiterStorageSelection`)
without needing a real or fake Redis connection — Flask-Limiter/`limits`
only connects lazily on first rate-limited request, so app *creation*
with an unreachable `REDIS_URL` must not (and does not) raise.

The same `REDIS_URL` also gates whether `POST /ml/train` runs as a
background RQ job or falls back to synchronous training in the request
thread (`backend/jobs/queue.py`) — one environment variable enables both
production-shaped behaviors together.

## Consequences

**Positive:**
- Zero required configuration for local dev/demo use, exactly like ADR
  0001's database choice.
- A real, tested path to production-correct rate limiting exists and is
  exercised by tests (`test_app_config.py`), not just documented as a
  future improvement.

**Negative / accepted tradeoffs:**
- Without `REDIS_URL` configured, rate limits are only correct within a
  single worker process — a client could effectively get
  `RATE_LIMIT * GUNICORN_WORKERS` requests before any single worker
  enforces its limit. This is the same gap the prior pass disclosed; it
  is now optional rather than mandatory to accept, but still the default.
- This repository's test suite validates the *selection logic* and that
  `create_app()` doesn't crash with an unreachable Redis URL, but does not
  validate actual rate-limit enforcement against a live Redis server — no
  Redis server is available in this development/CI environment. The
  RQ background-job path is validated more thoroughly using `fakeredis`
  (see `test_ml_train_background.py`), since RQ's job execution can be
  fully exercised in-process; Flask-Limiter's Redis storage backend
  connects through `redis-py` directly and was not similarly swapped for
  a fake in this pass.
