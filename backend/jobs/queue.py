"""Redis/RQ connection wiring for background jobs.

Why this module exists as a thin, isolated seam: `routes/ml.py::train()`
needs to decide, per request, whether to enqueue a background job or fall
back to running training inline — and tests need to be able to substitute
a fake Redis connection (via `fakeredis`) without a real Redis server
running anywhere in this environment. Putting connection construction
behind `get_redis_connection()` gives tests exactly one function to
monkeypatch instead of needing to intercept `redis.from_url` calls
scattered across multiple modules.

Config contract: REDIS_URL unset -> get_redis_connection() returns None ->
every caller falls back to synchronous behavior. This means the app has
zero required new configuration: a fresh clone with no REDIS_URL still
runs exactly as before this change (see routes/ml.py::train()).
"""
from __future__ import annotations

import os

TRAINING_QUEUE_NAME = "ml-training"


def get_redis_connection():
    """Returns a redis-py connection built from REDIS_URL, or None if
    REDIS_URL isn't set (the "background jobs disabled" state).

    Not cached: a fresh connection per call is cheap with redis-py's
    connection pooling and avoids holding a stale connection object across
    app-factory calls in tests, where a new Flask app (and potentially a
    monkeypatched connection) is created per test.
    """
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    import redis

    return redis.from_url(redis_url)


def get_training_queue():
    """Returns an rq.Queue for ML training jobs, or None if Redis isn't
    configured (REDIS_URL unset) — the caller must treat None as "run
    synchronously instead."
    """
    connection = get_redis_connection()
    if connection is None:
        return None
    from rq import Queue

    return Queue(TRAINING_QUEUE_NAME, connection=connection)
