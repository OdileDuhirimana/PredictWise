"""Per-request correlation IDs threaded through logs, Sentry, and audit events.

Why: structured JSON logging, Sentry, and the audit log (utils/audit.py)
were each independently wired up, but nothing tied a single request's
events across all three together. During an incident ("why did this
parent get a 403 at 14:32?") an engineer would have had to correlate log
lines by timestamp/IP guesswork instead of a single ID. This module
generates one UUID per request (or reuses an inbound `X-Request-ID` header
so a request can be traced across service boundaries), exposes it via
`flask.g.request_id`, echoes it back on the response so a client/API
consumer can quote it when reporting an issue, and injects it into every
log record via `RequestIdLogFilter` so `grep request_id=<uuid>` finds every
log line — application, audit, and (if Sentry is configured) the matching
error report — for that request.
"""
from __future__ import annotations

import logging
import uuid

from flask import Flask, g, has_request_context, request

_REQUEST_ID_HEADER = 'X-Request-ID'


class RequestIdLogFilter(logging.Filter):
    """Injects `record.request_id` so the JSON log formatter can include it
    on every line, not just ones that explicitly pass it in."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = g.request_id if has_request_context() and hasattr(g, 'request_id') else None
        return True


def init_request_id(app: Flask) -> None:
    """Register before/after-request hooks that assign and propagate a
    per-request correlation ID. Call once per app, after Sentry (if
    configured) has been initialized so the sentry_sdk import below is a
    no-op cost either way — sentry_sdk is always installed as a dependency,
    it's `SENTRY_DSN` that's optional.
    """

    @app.before_request
    def _assign_request_id():
        g.request_id = request.headers.get(_REQUEST_ID_HEADER) or str(uuid.uuid4())
        try:
            import sentry_sdk

            sentry_sdk.set_tag('request_id', g.request_id)
        except Exception:
            # Sentry not configured (no SENTRY_DSN) or unavailable — a
            # correlation-id tag is a nice-to-have, never a request-blocker.
            pass

    @app.after_request
    def _echo_request_id(response):
        response.headers[_REQUEST_ID_HEADER] = getattr(g, 'request_id', '')
        return response
