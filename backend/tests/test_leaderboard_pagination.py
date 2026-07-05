"""Tests for the pagination/filtering/sorting added to
routes/gamification.py::leaderboard(), matching the pattern already
established in routes/students.py::list_students. Parent-ownership scoping
on this same endpoint is covered separately in test_parent_ownership.py.
"""

API = "/api/v1"


def _create_student_with_xp(client, headers, name, xp):
    student_id = client.post(f"{API}/students/", json={"name": name, "grade": "S3"}, headers=headers).get_json()["id"]
    client.post(f"{API}/gamify/award", json={"student_id": student_id, "xp": xp}, headers=headers)
    return student_id


class TestLeaderboardPaginationFilterSort:
    def test_pagination_metadata_present(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("lb.page@example.com")
        _create_student_with_xp(client, headers, "A", 10)
        _create_student_with_xp(client, headers, "B", 20)

        resp = client.get(f"{API}/gamify/leaderboard", headers=headers)

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["page"] == 1
        assert body["per_page"] == 20
        assert body["total"] == 2

    def test_per_page_limits_page_size(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("lb.perpage@example.com")
        for i in range(5):
            _create_student_with_xp(client, headers, f"Student {i}", i)

        resp = client.get(f"{API}/gamify/leaderboard?per_page=2", headers=headers)

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total"] == 5
        assert len(body["leaderboard"]) == 2

    def test_min_xp_filter(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("lb.minxp@example.com")
        _create_student_with_xp(client, headers, "Low", 5)
        _create_student_with_xp(client, headers, "High", 50)

        resp = client.get(f"{API}/gamify/leaderboard?min_xp=10", headers=headers)

        assert resp.status_code == 200
        rows = resp.get_json()["leaderboard"]
        assert len(rows) == 1
        assert rows[0]["name"] == "High"

    def test_sort_by_streak_ascending(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("lb.sortstreak@example.com")
        # Two awards raises streak to 2 for one student, one award for the other.
        low_id = _create_student_with_xp(client, headers, "OneAward", 10)
        high_id = _create_student_with_xp(client, headers, "TwoAwards", 5)
        client.post(f"{API}/gamify/award", json={"student_id": high_id, "xp": 5}, headers=headers)

        resp = client.get(f"{API}/gamify/leaderboard?sort=streak", headers=headers)

        assert resp.status_code == 200
        ids = [r["student_id"] for r in resp.get_json()["leaderboard"]]
        assert ids == [low_id, high_id]

    def test_disallowed_sort_column_returns_400(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("lb.badsort@example.com")

        resp = client.get(f"{API}/gamify/leaderboard?sort=name", headers=headers)

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"

    def test_default_order_is_unchanged_highest_xp_first(self, make_authenticated_client):
        """Backward compatibility: the pre-pagination default behavior
        (top XP first, implicit top-20) must be unchanged for any existing
        consumer that doesn't pass query params at all."""
        client, headers, _ = make_authenticated_client("lb.default@example.com")
        low_id = _create_student_with_xp(client, headers, "Low", 5)
        high_id = _create_student_with_xp(client, headers, "High", 50)

        resp = client.get(f"{API}/gamify/leaderboard", headers=headers)

        ids = [r["student_id"] for r in resp.get_json()["leaderboard"]]
        assert ids == [high_id, low_id]
