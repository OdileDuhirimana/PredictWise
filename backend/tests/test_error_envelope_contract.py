"""Contract test: every error response across the API surface uses the
same envelope shape, `{"error": {"code": str, "message": str}}`, with an
optional "details" list.

Why this matters as its own test file rather than being implicitly
covered by each route's own test file: individual route tests each assert
their *own* error responses, but nothing previously proved the envelope
is *consistent* across the whole API — a route that quietly reverted to
an ad hoc `{'error': 'message'}` string (the exact pre-audit pattern) would
still pass its own file's tests if that file only checked
`resp.get_json()['error']` without checking it was a dict with a `code`
key. This test exercises a deliberately broad sample of endpoints across
every blueprint and every error class (401 unauthenticated, 403 RBAC
denial, 404 not-found, 400 validation) and asserts the exact same
structural contract on all of them.
"""
import pytest

API = "/api/v1"


def _assert_error_envelope(response, expected_status: int):
    assert response.status_code == expected_status, response.get_json()
    body = response.get_json()
    assert "error" in body, f"missing 'error' key: {body}"
    error = body["error"]
    assert isinstance(error, dict), f"'error' must be an object, got {type(error)}: {body}"
    assert isinstance(error.get("code"), str) and error["code"], f"missing/invalid 'code': {body}"
    assert isinstance(error.get("message"), str) and error["message"], f"missing/invalid 'message': {body}"
    if "details" in error:
        assert isinstance(error["details"], list)


class Test401UnauthenticatedContract:
    """Every one of these previously required no token at all
    (`jwt_required(optional=True)`) before the audit response — now every
    one must 401 with the standard envelope, not just *a* 401."""

    @pytest.mark.parametrize(
        "method,path",
        [
            ("get", f"{API}/students/"),
            ("get", f"{API}/analytics/dashboard"),
            ("get", f"{API}/gamify/leaderboard"),
            ("get", f"{API}/wellness/indicator?student_id=1"),
            ("post", f"{API}/digital-twin/project"),
            ("post", f"{API}/voice/analyze"),
            ("post", f"{API}/ml/predict"),
            ("post", f"{API}/ml/train"),
            ("post", f"{API}/gamify/award"),
            ("post", f"{API}/alerts/send"),
        ],
    )
    def test_unauthenticated_request_returns_standard_401(self, client, method, path):
        response = getattr(client, method)(path, json={} if method == "post" else None)
        _assert_error_envelope(response, 401)


class Test403RbacDenialContract:
    @pytest.mark.parametrize(
        "path,body",
        [
            (f"{API}/ml/train", {}),
            (f"{API}/alerts/send", {"channel": "sms", "to": "+1", "message": "hi"}),
            (f"{API}/gamify/award", {"student_id": 1, "xp": 5}),
        ],
    )
    def test_wrong_role_returns_standard_403(self, make_authenticated_client, path, body):
        client, headers, _ = make_authenticated_client(f"contract403{hash(path) % 10_000}@example.com", role="parent")

        response = client.post(path, json=body, headers=headers)

        _assert_error_envelope(response, 403)


class Test404NotFoundContract:
    def test_unknown_route_returns_standard_404(self, client):
        response = client.get(f"{API}/this-route-does-not-exist")
        _assert_error_envelope(response, 404)

    def test_assessment_for_unknown_student_returns_standard_404(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("contract404.assessment@example.com")

        response = client.post(
            f"{API}/students/assessment",
            json={"student_id": 999999, "subject": "Math", "score": 70, "term": "T1"},
            headers=headers,
        )

        _assert_error_envelope(response, 404)

    def test_award_for_unknown_student_returns_standard_404(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("contract404.award@example.com", role="teacher")

        response = client.post(f"{API}/gamify/award", json={"student_id": 999999, "xp": 5}, headers=headers)

        _assert_error_envelope(response, 404)


class Test400ValidationContract:
    @pytest.mark.parametrize(
        "path,body",
        [
            (f"{API}/auth/register", {"email": "not-an-email"}),
            (f"{API}/students/", {"name": ""}),
            (f"{API}/students/assessment", {"student_id": 1}),
            (f"{API}/ml/predict", {"avg_score": "not-a-number"}),
            (f"{API}/digital-twin/project", {"attendance_rate": 5}),
            (f"{API}/voice/analyze", {"transcript": "x" * 20_000}),
            (f"{API}/alerts/send", {"channel": "carrier-pigeon", "to": "x", "message": "hi"}),
        ],
    )
    def test_invalid_body_returns_standard_400(self, client, make_authenticated_client, path, body):
        # /auth/register is unauthenticated by design; everything else
        # needs a token first.
        headers = {}
        if path != f"{API}/auth/register":
            _, headers, _ = make_authenticated_client(
                f"contract400{hash(path) % 10_000}@example.com", role="admin"
            )

        response = client.post(path, json=body, headers=headers)

        _assert_error_envelope(response, 400)
