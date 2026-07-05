"""Tests for the response-level caching added to routes/analytics.py.

Two things matter here, for different reasons:

1. That caching actually happens (a second identical request within the
   TTL returns the first request's data even after the underlying data
   changed) — proving the cache is real, not just configured and unused.
2. That an unauthenticated request can never receive a cached response
   that an authenticated request populated — `@cache.cached()` keys only
   on path + query string, not caller identity, so this safety property
   depends entirely on `@jwt_required()` being the outer decorator and
   rejecting the request before the cache layer is ever consulted. This
   is the single most important thing to regression-test here: a future
   edit that reorders these two decorators would silently turn a
   performance optimization into an authentication bypass.
"""

API = "/api/v1"


def _seed_assessment(client, headers, score):
    student_id = client.post(f"{API}/students/", json={"name": "Cache Test", "grade": "S3"}, headers=headers).get_json()["id"]
    client.post(
        f"{API}/students/assessment",
        json={"student_id": student_id, "subject": "Math", "score": score, "term": "T1"},
        headers=headers,
    )


class TestDashboardCaching:
    def test_second_request_returns_cached_value_despite_new_data(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("cache.dashboard@example.com")
        _seed_assessment(client, headers, 50)

        first = client.get(f"{API}/analytics/dashboard", headers=headers)
        assert first.get_json()["avg_score"] == 50

        # New data is added, but within the cache TTL a second identical
        # request must still see the stale, cached value — this is the
        # deliberate tradeoff being tested, not a bug.
        _seed_assessment(client, headers, 100)
        second = client.get(f"{API}/analytics/dashboard", headers=headers)

        assert second.get_json()["avg_score"] == 50


class TestUnauthenticatedRequestsNeverReceiveCachedData:
    def test_unauthenticated_request_after_cached_authenticated_one_still_401s(self, make_authenticated_client):
        """Regression guard for decorator ordering: @jwt_required() must
        run (and reject) before @cache.cached() is ever consulted. If
        these were ever reordered, this test would start failing with a
        200 containing real school data instead of a 401."""
        client, headers, _ = make_authenticated_client("cache.unauth@example.com")
        _seed_assessment(client, headers, 77)

        authenticated_resp = client.get(f"{API}/analytics/dashboard", headers=headers)
        assert authenticated_resp.status_code == 200

        unauthenticated_resp = client.get(f"{API}/analytics/dashboard")

        assert unauthenticated_resp.status_code == 401


class TestSubjectsCachingKeyedByQueryString:
    def test_different_query_strings_are_cached_independently(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("cache.subjects@example.com")
        _seed_assessment(client, headers, 60)

        unfiltered = client.get(f"{API}/analytics/subjects", headers=headers)
        filtered = client.get(f"{API}/analytics/subjects?subject=Math", headers=headers)

        assert unfiltered.status_code == 200
        assert filtered.status_code == 200
        assert filtered.get_json()["subjects"][0]["subject"] == "Math"
