"""Integration tests for the pydantic validation added to ml.py::do_predict,
digital_twin.py::project, and voice.py::analyze.

The specific regression this closes: digital_twin.py previously did
`float(data.get('avg_score', 60))` with no validation, so a non-numeric
`avg_score` raised an unhandled ValueError that surfaced to the client as
a raw 500 (confirmed reproducible before this change). These tests prove
that exact case — and its equivalent on /ml/predict — now returns a
structured 400 instead.
"""

API = "/api/v1"


class TestPredictValidation:
    def test_non_numeric_avg_score_returns_400_not_500(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("predict.badinput@example.com")

        resp = client.post(
            f"{API}/ml/predict",
            json={"avg_score": "not-a-number"},
            headers=headers,
        )

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"

    def test_out_of_range_attendance_rate_returns_400(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("predict.outofrange@example.com")

        resp = client.post(
            f"{API}/ml/predict",
            json={"attendance_rate": 1.5},
            headers=headers,
        )

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"

    def test_defaults_applied_when_body_empty(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("predict.defaults@example.com")

        resp = client.post(f"{API}/ml/predict", json={}, headers=headers)

        assert resp.status_code == 200
        assert "prediction" in resp.get_json()


class TestDigitalTwinValidation:
    def test_non_numeric_avg_score_returns_400_not_500(self, make_authenticated_client):
        """This is the exact regression the audit flagged: digital_twin.py
        crashed with an unhandled 500 on non-numeric input before pydantic
        validation was added here."""
        client, headers, _ = make_authenticated_client("twin.badinput@example.com")

        resp = client.post(
            f"{API}/digital-twin/project",
            json={"avg_score": "not-a-number"},
            headers=headers,
        )

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"

    def test_negative_behavior_incidents_returns_400(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("twin.negative@example.com")

        resp = client.post(
            f"{API}/digital-twin/project",
            json={"behavior_incidents": -1},
            headers=headers,
        )

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"

    def test_valid_projection_succeeds(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("twin.valid@example.com")

        resp = client.post(
            f"{API}/digital-twin/project",
            json={"avg_score": 70, "attendance_rate": 0.9},
            headers=headers,
        )

        assert resp.status_code == 200
        assert "health_status" in resp.get_json()


class TestVoiceAnalyzeValidation:
    def test_transcript_too_long_returns_400(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("voice.toolong@example.com")

        resp = client.post(
            f"{API}/voice/analyze",
            json={"transcript": "x" * 10_001},
            headers=headers,
        )

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"

    def test_missing_transcript_defaults_to_empty_string(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("voice.empty@example.com")

        resp = client.post(f"{API}/voice/analyze", json={}, headers=headers)

        assert resp.status_code == 200
