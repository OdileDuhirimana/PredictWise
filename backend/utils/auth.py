"""Role-based access control (RBAC) helpers.

Why a decorator instead of inline checks in each route: the audit found
several routes performing pedagogically/administratively sensitive actions
(training the ML model, sending parent alerts, awarding gamification XP)
with no role gate at all — any authenticated user, or in some cases anyone
unauthenticated at all, could call them. `roles_required` centralizes the
"is this JWT's role allowed here" check into one tested code path, applied
declaratively with `@roles_required('admin')` etc., rather than repeating
`if claims['role'] not in (...)` in every view function.

Design notes:
- This decorator does NOT call `verify_jwt_in_request()` itself — it expects
  to be stacked underneath `@jwt_required()` (Flask-JWT-Extended convention:
  decorators nearest the function run first). This keeps the 401-vs-403
  distinction crisp: `@jwt_required()` alone answers "is there a valid
  token", `@roles_required(...)` answers "is this token's role allowed".
- A malformed/missing 'role' claim degrades to 403 (forbidden), not 500.
  This can legitimately happen for tokens issued before a role claim was
  added to the schema, or from a buggy client sending a hand-crafted JWT;
  either way a client input problem should never surface as a server error.
"""
from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import request
from flask_jwt_extended import get_jwt, get_jwt_identity

from .audit import log_audit_event
from .errors import error_response


def get_current_role_and_user_id() -> tuple[str | None, str | None]:
    """Best-effort (role, user_id) extraction from the current JWT.

    Why this exists separately from `roles_required`: several routes are
    open to *any* authenticated role via plain `@jwt_required()` (list
    students, view the leaderboard, view a wellness indicator) but still
    need to know *which* role is calling in order to scope results — e.g.
    a parent must only see their own children, while admin/teacher see
    everyone. That's an ownership filter, not a role gate, so it doesn't
    belong in `roles_required`.

    Returns:
        (None, None) if no JWT context is available (should not normally
        happen behind @jwt_required(), but callers must not crash if it
        does — the caller decides how to fail).
    """
    try:
        claims = get_jwt()
        return claims.get("role"), get_jwt_identity()
    except Exception:
        return None, None


def roles_required(*allowed_roles: str) -> Callable:
    """Require the current JWT's `role` claim to be one of `allowed_roles`.

    Must be used beneath `@jwt_required()` so a valid JWT is already
    guaranteed to be present on the request:

        @some_bp.post('/train')
        @jwt_required()
        @roles_required('admin')
        def train():
            ...

    Returns:
        403 with the standard error envelope if the role claim is missing
        or not in `allowed_roles`; otherwise calls through to the view.

    Audit trail: every denial and every successful call through this gate
    is logged as a structured audit event (utils/audit.py) — this decorator
    is applied exactly to the routes the audit identified as sensitive
    (training the shared ML model, sending parent alerts, awarding XP), so
    it is the single natural place to answer "who did this / who was
    denied" without repeating logging calls in every route body.
    """

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            try:
                claims = get_jwt()
                role = claims.get("role")
                user_id = get_jwt_identity()
            except Exception:
                # No JWT context available (e.g. decorator misordered, or
                # verify_jwt_in_request never ran). Fail closed as 403
                # rather than letting an AttributeError/RuntimeError bubble
                # up as an unhandled 500.
                role = None
                user_id = None

            if role not in allowed_roles:
                log_audit_event(
                    "rbac_denied",
                    user_id=user_id,
                    role=role,
                    allowed_roles=list(allowed_roles),
                    endpoint=request.path,
                    method=request.method,
                )
                return error_response(
                    "forbidden",
                    "You do not have permission to perform this action.",
                    403,
                )

            result = view_func(*args, **kwargs)

            status = result[1] if isinstance(result, tuple) and len(result) > 1 else 200
            if status < 400:
                log_audit_event(
                    "admin_action_success",
                    user_id=user_id,
                    role=role,
                    endpoint=request.path,
                    method=request.method,
                    status=status,
                )
            return result

        return wrapper

    return decorator
