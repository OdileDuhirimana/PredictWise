"""Integration tests for /api/v1/auth/register and /api/v1/auth/login.

Covers the pydantic-validated happy path plus every failure mode the audit
called out explicitly: duplicate email, missing fields (structured 400
instead of a raw KeyError-triggered 500), wrong password, and a
nonexistent user — each asserted against the shared error envelope shape
from backend/utils/errors.py so a regression in the envelope format fails
loudly here rather than being discovered by a frontend consumer later.
"""

API = "/api/v1/auth"


class TestRegister:
    def test_register_success(self, client):
        resp = client.post(f"{API}/register", json={"email": "new.user@example.com", "password": "password123"})

        assert resp.status_code == 200
        assert resp.get_json() == {"message": "registered"}

    def test_register_then_login_succeeds(self, client):
        client.post(f"{API}/register", json={"email": "roundtrip@example.com", "password": "password123"})

        resp = client.post(f"{API}/login", json={"email": "roundtrip@example.com", "password": "password123"})

        assert resp.status_code == 200
        assert "access_token" in resp.get_json()

    def test_duplicate_email_returns_400_with_envelope(self, client):
        client.post(f"{API}/register", json={"email": "dupe@example.com", "password": "password123"})

        resp = client.post(f"{API}/register", json={"email": "dupe@example.com", "password": "password123"})

        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"]["code"] == "validation_error"
        assert "message" in body["error"]

    def test_missing_password_returns_400_structured_envelope(self, client):
        resp = client.post(f"{API}/register", json={"email": "missing.pw@example.com"})

        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"]["code"] == "validation_error"
        assert any(err["loc"] == ["password"] for err in body["error"]["details"])

    def test_missing_email_returns_400_structured_envelope(self, client):
        resp = client.post(f"{API}/register", json={"password": "password123"})

        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"]["code"] == "validation_error"
        assert any(err["loc"] == ["email"] for err in body["error"]["details"])

    def test_short_password_rejected(self, client):
        resp = client.post(f"{API}/register", json={"email": "short.pw@example.com", "password": "short"})

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"

    def test_malformed_json_body_returns_400_not_500(self, client):
        """request.get_json(silent=True) returns None on a non-JSON body,
        which the route treats as {} — this must validate as a structured
        400 (missing required fields), never an unhandled 500."""
        resp = client.post(f"{API}/register", data="not json", content_type="text/plain")

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"


class TestLogin:
    def test_wrong_password_returns_401(self, client):
        client.post(f"{API}/register", json={"email": "wrongpw@example.com", "password": "correct-password"})

        resp = client.post(f"{API}/login", json={"email": "wrongpw@example.com", "password": "incorrect-password"})

        assert resp.status_code == 401
        body = resp.get_json()
        assert body["error"]["code"] == "unauthorized"

    def test_nonexistent_user_returns_401(self, client):
        resp = client.post(f"{API}/login", json={"email": "nobody@example.com", "password": "password123"})

        assert resp.status_code == 401
        assert resp.get_json()["error"]["code"] == "unauthorized"

    def test_missing_credentials_returns_400(self, client):
        resp = client.post(f"{API}/login", json={})

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"
