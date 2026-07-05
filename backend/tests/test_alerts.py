"""Integration tests for backend/routes/alerts.py.

Covers the mocked path (no Twilio credentials configured, the default in
any test/dev environment), the request validation, and the Twilio-failure
branch — which previously leaked `str(exception)` verbatim to the client
(a real information-disclosure finding) and now returns the standard error
envelope with a generic message instead.
"""
from unittest.mock import MagicMock, patch

API = "/api/v1/alerts"


class TestSendAlertValidation:
    def test_missing_message_returns_400(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("alert.missing@example.com", role="admin")

        resp = client.post(f"{API}/send", json={"channel": "sms", "to": "+250700000000"}, headers=headers)

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"

    def test_invalid_channel_returns_400(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("alert.badchannel@example.com", role="admin")

        resp = client.post(
            f"{API}/send",
            json={"channel": "carrier-pigeon", "to": "+250700000000", "message": "hi"},
            headers=headers,
        )

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"

    def test_defaults_channel_to_sms(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("alert.default@example.com", role="admin")

        resp = client.post(f"{API}/send", json={"to": "+250700000000", "message": "hi"}, headers=headers)

        assert resp.status_code == 200
        assert resp.get_json()["channel"] == "sms"

    def test_mocked_response_when_twilio_unconfigured(self, make_authenticated_client, monkeypatch):
        # Ensure a clean slate regardless of the host environment's env vars.
        for var in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER", "TWILIO_WHATSAPP_FROM"):
            monkeypatch.delenv(var, raising=False)
        client, headers, _ = make_authenticated_client("alert.mocked@example.com", role="admin")

        resp = client.post(
            f"{API}/send",
            json={"channel": "whatsapp", "to": "+250700000000", "message": "hi"},
            headers=headers,
        )

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "mocked"
        assert body["channel"] == "whatsapp"

    def test_twilio_failure_returns_standard_envelope_without_leaking_exception(
        self, make_authenticated_client, monkeypatch
    ):
        """Regression test: the Twilio-failure branch used to return
        `{'status': 'mocked', ..., 'error': str(e)}` with a 202 — leaking
        raw exception text (which can include account/config details) to
        the client. It must now return the standard error envelope with a
        generic message and a 5xx status."""
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "fake-sid")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "fake-token")
        monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15550000000")
        client, headers, _ = make_authenticated_client("alert.twiliofail@example.com", role="admin")

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("secret account config detail")

        with patch("backend.routes.alerts.Client", return_value=mock_client):
            resp = client.post(
                f"{API}/send",
                json={"channel": "sms", "to": "+250700000000", "message": "hi"},
                headers=headers,
            )

        assert resp.status_code == 502
        body = resp.get_json()
        assert body["error"]["code"] == "alert_delivery_failed"
        assert "secret account config detail" not in resp.get_data(as_text=True)
