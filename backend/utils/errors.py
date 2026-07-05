"""Centralized error-response helpers.

Why: every route was hand-rolling its own error JSON shape ({'error': 'msg'},
plain strings, etc.), which makes frontend error handling brittle and makes
it impossible to distinguish a validation failure from an auth failure from
a not-found case programmatically. This module defines ONE envelope shape
used everywhere (validation, auth, authorization, not-found, and unhandled
5xx via the global Flask error handlers registered in app.py):

    {"error": {"code": "...", "message": "...", "details": [...] | None}}

`code` is a short machine-readable slug (e.g. "validation_error",
"unauthorized", "forbidden", "not_found", "internal_error") that the
frontend or API consumers can branch on without parsing the message text.
`details` is optional and carries structured extra context, such as the
list of per-field pydantic validation errors.
"""
from __future__ import annotations

from typing import Any

from flask import jsonify


def error_response(code: str, message: str, status: int, details: Any = None):
    """Build a Flask JSON response using the standard error envelope.

    Args:
        code: Short machine-readable error identifier, e.g. "validation_error".
        message: Human-readable summary safe to show to API consumers.
        status: HTTP status code to return.
        details: Optional structured detail (e.g. list of field errors).
            Omitted from the payload entirely when None, keeping responses
            compact for simple error cases.

    Returns:
        A (Response, status) tuple, ready to be returned directly from a
        Flask view function.
    """
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return jsonify(body), status
