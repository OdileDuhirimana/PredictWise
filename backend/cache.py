"""Flask-Caching wiring, mirroring the module-level singleton pattern
already used for `db`/`migrate` in database.py.

Why response-level caching here specifically: routes/analytics.py's
dashboard/subjects/classes/heatmap/benchmarks endpoints each re-run
full-table aggregate queries (AVG/COUNT/GROUP BY over every Assessment
row) on every single request, even though the underlying data changes
relatively infrequently compared to how often a dashboard page might be
viewed or auto-refreshed. A short TTL cache trades a small amount of
staleness for avoiding repeated full-table scans under read-heavy
dashboard traffic.

Backend selection mirrors the Redis-vs-in-memory choice already made for
rate limiting (see backend/app.py and ADR 0002): Redis-backed when
REDIS_URL is configured (correct and shared across multiple gunicorn
workers), otherwise Flask-Caching's SimpleCache (adequate for local
dev/demo, but per-process and not shared across workers).
"""
from __future__ import annotations

from flask_caching import Cache

cache = Cache()

# Kept short deliberately: this is staleness-tolerant caching for
# dashboard-style aggregate reads, not a correctness-critical cache. A
# school admin looking at the dashboard tolerates numbers being up to this
# many seconds old far better than the API tolerates every page view
# re-scanning the full assessments table.
ANALYTICS_CACHE_TIMEOUT_SECONDS = 30


def cache_config(redis_url: str | None) -> dict:
    """Pure function (like `_limiter_storage_kwargs` in app.py) so the
    backend-selection logic is unit-testable without needing a real or
    fake Redis connection — Flask-Caching's RedisCache also connects
    lazily.
    """
    if redis_url:
        return {'CACHE_TYPE': 'RedisCache', 'CACHE_REDIS_URL': redis_url, 'CACHE_DEFAULT_TIMEOUT': ANALYTICS_CACHE_TIMEOUT_SECONDS}
    return {'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': ANALYTICS_CACHE_TIMEOUT_SECONDS}
