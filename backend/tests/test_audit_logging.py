"""Tests proving `roles_required` actually emits audit events, and that a
request ID is generated and echoed back — the audit's SEC-08 finding was
that a 403 from RBAC produced no observable trail at all.

These use pytest's `caplog` against the `predictwise.audit` logger rather
than parsing JSON stdout, since the JSON formatting itself is
`app.py`-level plumbing already covered indirectly by every other test
exercising a logged request without crashing.
"""
import logging

API = "/api/v1"


class TestRbacAuditLogging:
    def test_denial_is_logged(self, make_authenticated_client, caplog):
        client, headers, _ = make_authenticated_client("audit.denied@example.com", role="teacher")

        with caplog.at_level(logging.INFO, logger="predictwise.audit"):
            resp = client.post(f"{API}/ml/train", headers=headers)

        assert resp.status_code == 403
        audit_records = [r for r in caplog.records if r.name == "predictwise.audit"]
        assert len(audit_records) == 1
        event = audit_records[0].msg
        assert event["event"] == "rbac_denied"
        assert event["role"] == "teacher"
        assert event["allowed_roles"] == ["admin"]
        assert event["endpoint"] == "/api/v1/ml/train"

    def test_success_is_logged(self, make_authenticated_client, caplog):
        client, headers, _ = make_authenticated_client("audit.allowed@example.com", role="admin")

        with caplog.at_level(logging.INFO, logger="predictwise.audit"):
            resp = client.post(
                f"{API}/alerts/send",
                json={"channel": "sms", "to": "+250700000000", "message": "hi"},
                headers=headers,
            )

        assert resp.status_code == 200
        audit_records = [r for r in caplog.records if r.name == "predictwise.audit"]
        assert len(audit_records) == 1
        event = audit_records[0].msg
        assert event["event"] == "admin_action_success"
        assert event["role"] == "admin"
        assert event["endpoint"] == "/api/v1/alerts/send"

    def test_domain_rejection_is_not_logged_as_success(self, make_authenticated_client, caplog):
        """A 400 from a *domain* rejection (e.g. no assessment data to
        train on) is not the same as a successful admin action — it must
        not be logged as admin_action_success."""
        client, headers, _ = make_authenticated_client("audit.domainfail@example.com", role="admin")

        with caplog.at_level(logging.INFO, logger="predictwise.audit"):
            resp = client.post(f"{API}/ml/train", headers=headers)

        assert resp.status_code == 400
        audit_records = [r for r in caplog.records if r.name == "predictwise.audit"]
        assert audit_records == []


class TestRequestIdPropagation:
    def test_response_echoes_a_request_id_header(self, client):
        resp = client.get("/health")

        assert resp.status_code == 200
        assert resp.headers.get("X-Request-ID")

    def test_inbound_request_id_is_reused(self, client):
        resp = client.get("/health", headers={"X-Request-ID": "fixed-test-id"})

        assert resp.headers.get("X-Request-ID") == "fixed-test-id"
