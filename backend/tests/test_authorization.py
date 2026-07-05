"""Integration tests proving RBAC is actually enforced end-to-end.

The audit found several sensitive routes with no role gate (or no auth at
all, via `jwt_required(optional=True)`). These tests prove, through real
HTTP requests against the real routes (not by calling `roles_required`
directly), that:
  - a teacher-role token is rejected (403) on admin-only routes,
  - an admin-role token succeeds on those same routes,
  - a request with no token at all is rejected (401) on a route that used
    to be `optional=True` but is now `jwt_required()`.
"""

API = "/api/v1"


class TestTrainRequiresAdmin:
    def test_teacher_gets_403(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("teacher.train@example.com", role="teacher")

        resp = client.post(f"{API}/ml/train", headers=headers)

        assert resp.status_code == 403
        assert resp.get_json()["error"]["code"] == "forbidden"

    def test_admin_is_allowed(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("admin.train@example.com", role="admin")

        resp = client.post(f"{API}/ml/train", headers=headers)

        # 400 is acceptable here: no assessment data exists yet in this
        # test's empty database, but that's a *domain* rejection, not an
        # authorization one — the RBAC gate itself must let admins through.
        assert resp.status_code in (200, 400)


class TestSendAlertRequiresAdmin:
    def test_teacher_gets_403(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("teacher.alert@example.com", role="teacher")

        resp = client.post(
            f"{API}/alerts/send",
            json={"channel": "sms", "to": "+250700000000", "message": "hi"},
            headers=headers,
        )

        assert resp.status_code == 403
        assert resp.get_json()["error"]["code"] == "forbidden"

    def test_admin_is_allowed(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("admin.alert@example.com", role="admin")

        resp = client.post(
            f"{API}/alerts/send",
            json={"channel": "sms", "to": "+250700000000", "message": "hi"},
            headers=headers,
        )

        assert resp.status_code == 200


class TestAwardAllowsTeacherAndAdmin:
    def test_parent_gets_403(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("parent.award@example.com", role="parent")
        student_resp = client.post(
            f"{API}/students/",
            json={"name": "Test Student", "grade": "S3"},
            headers=headers,
        )
        student_id = student_resp.get_json()["id"]

        resp = client.post(
            f"{API}/gamify/award",
            json={"student_id": student_id, "xp": 10},
            headers=headers,
        )

        assert resp.status_code == 403
        assert resp.get_json()["error"]["code"] == "forbidden"

    def test_teacher_is_allowed(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("teacher.award@example.com", role="teacher")
        student_resp = client.post(
            f"{API}/students/",
            json={"name": "Test Student", "grade": "S3"},
            headers=headers,
        )
        student_id = student_resp.get_json()["id"]

        resp = client.post(
            f"{API}/gamify/award",
            json={"student_id": student_id, "xp": 10},
            headers=headers,
        )

        assert resp.status_code == 200

    def test_admin_is_allowed(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("admin.award@example.com", role="admin")
        student_resp = client.post(
            f"{API}/students/",
            json={"name": "Test Student", "grade": "S3"},
            headers=headers,
        )
        student_id = student_resp.get_json()["id"]

        resp = client.post(
            f"{API}/gamify/award",
            json={"student_id": student_id, "xp": 10},
            headers=headers,
        )

        assert resp.status_code == 200


class TestPreviouslyOptionalRoutesNowRequireAuth:
    """These routes used @jwt_required(optional=True) before this pass;
    an unauthenticated request must now be rejected with 401 rather than
    silently succeeding with an anonymous identity."""

    def test_list_students_requires_token(self, client):
        resp = client.get(f"{API}/students/")
        assert resp.status_code == 401

    def test_analytics_dashboard_requires_token(self, client):
        resp = client.get(f"{API}/analytics/dashboard")
        assert resp.status_code == 401

    def test_leaderboard_requires_token(self, client):
        resp = client.get(f"{API}/gamify/leaderboard")
        assert resp.status_code == 401

    def test_wellness_indicator_requires_token(self, client):
        resp = client.get(f"{API}/wellness/indicator?student_id=1")
        assert resp.status_code == 401

    def test_digital_twin_requires_token(self, client):
        resp = client.post(f"{API}/digital-twin/project", json={})
        assert resp.status_code == 401

    def test_voice_analyze_requires_token(self, client):
        resp = client.post(f"{API}/voice/analyze", json={"transcript": "hello"})
        assert resp.status_code == 401

    def test_predict_requires_token(self, client):
        resp = client.post(f"{API}/ml/predict", json={"avg_score": 70})
        assert resp.status_code == 401
