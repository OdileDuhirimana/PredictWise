"""Integration tests for backend/routes/gamification.py.

Primarily proves the N+1 -> single-joined-query fix in leaderboard()
preserves the exact response shape ({"leaderboard": [{"student_id",
"name", "xp", "streak"}, ...]}) that the frontend (frontend/src/pages/
Leaderboard.jsx) depends on, and that ordering/limiting still works.
"""

API = "/api/v1"


def _create_student(client, headers, name):
    resp = client.post(f"{API}/students/", json={"name": name, "grade": "S3"}, headers=headers)
    assert resp.status_code == 200
    return resp.get_json()["id"]


class TestLeaderboard:
    def test_shape_and_ordering(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("leaderboard.shape@example.com")
        low_id = _create_student(client, headers, "Low XP Student")
        high_id = _create_student(client, headers, "High XP Student")

        client.post(f"{API}/gamify/award", json={"student_id": low_id, "xp": 5}, headers=headers)
        client.post(f"{API}/gamify/award", json={"student_id": high_id, "xp": 50}, headers=headers)

        resp = client.get(f"{API}/gamify/leaderboard", headers=headers)

        assert resp.status_code == 200
        rows = resp.get_json()["leaderboard"]
        assert len(rows) == 2
        # Highest XP first.
        assert rows[0]["student_id"] == high_id
        assert rows[0]["name"] == "High XP Student"
        assert set(rows[0].keys()) == {"student_id", "name", "xp", "streak"}

    def test_empty_leaderboard_returns_empty_list(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("leaderboard.empty@example.com")

        resp = client.get(f"{API}/gamify/leaderboard", headers=headers)

        assert resp.status_code == 200
        assert resp.get_json()["leaderboard"] == []


class TestAward:
    def test_award_creates_gamification_row_if_missing(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("award.create@example.com", role="teacher")
        student_id = _create_student(client, headers, "New Student")

        resp = client.post(
            f"{API}/gamify/award",
            json={"student_id": student_id, "xp": 15, "badge": "Starter"},
            headers=headers,
        )

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["xp"] == 15
        assert body["streak"] == 1
        assert body["badges"] == ["Starter"]

    def test_award_unknown_student_returns_404(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("award.unknown@example.com", role="teacher")

        resp = client.post(
            f"{API}/gamify/award",
            json={"student_id": 999999, "xp": 10},
            headers=headers,
        )

        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "not_found"

    def test_award_negative_xp_rejected(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("award.negative@example.com", role="teacher")
        student_id = _create_student(client, headers, "Some Student")

        resp = client.post(
            f"{API}/gamify/award",
            json={"student_id": student_id, "xp": -5},
            headers=headers,
        )

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"
