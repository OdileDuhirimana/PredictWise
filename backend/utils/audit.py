"""Structured audit logging for security-relevant events.

Why this exists: the audit found that `roles_required` produces a 403 on a
denied request but never records *who* was denied *what*, and that
sensitive admin-gated actions (training the shared ML model, sending a
parent alert, awarding XP) leave no trail of who performed them. For an
application handling student wellness data, "who trained the model" and
"who was denied access to /ml/train" are exactly the questions a security
review or incident investigation needs answered — and today there is no
way to answer them.

Design notes:
- Audit events are emitted through the same JSON-structured root logger
  already configured in app.py (`_configure_logging`), under the
  `predictwise.audit` logger name, so they show up in the same stdout log
  stream (and, in production, the same log aggregator) as everything else
  without requiring a new sink or a database table for a first pass. This
  is a deliberate scope decision: a dedicated `AuditLog` DB table with a
  query/reporting UI would be the natural next step, but it's a
  meaningfully larger feature (schema, retention policy, an admin-only
  read endpoint) that isn't required to close the "no audit trail exists
  at all" gap the audit identified.
- Every event includes `request_id` when available (see app.py's
  correlation-id middleware) so a single request's audit event, structured
  log lines, and Sentry report can all be tied together during an
  incident.
- This module never raises: a logging failure must never break the
  request it's trying to observe. `logging` itself is expected not to
  raise under normal operation, but the audit call sites intentionally
  don't wrap every call in try/except — if logging infrastructure itself
  is broken, that's a condition ops needs to see, not silently swallow.
"""
from __future__ import annotations

import logging
from typing import Any

from flask import g

_audit_logger = logging.getLogger('predictwise.audit')


def log_audit_event(event: str, **fields: Any) -> None:
    """Emit one structured audit log line.

    Args:
        event: A short, stable machine-readable event name, e.g.
            "rbac_denied" or "admin_action_success".
        **fields: Structured context (user_id, role, endpoint, etc.). Only
            JSON-serializable values should be passed — the configured
            `pythonjsonlogger` formatter serializes the log record as JSON.
    """
    request_id = getattr(g, 'request_id', None)
    payload = {'event': event, 'request_id': request_id, **fields}
    _audit_logger.info(payload)
