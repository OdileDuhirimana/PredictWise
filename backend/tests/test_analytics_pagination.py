"""Tests for the pagination/filtering/sorting added to
routes/analytics.py::subjects()/classes(), matching the pattern already
established in routes/students.py::list_students.
"""

API = "/api/v1"


def _seed(client, headers, name, class_name, subject, score):
    student_id = client.post(
        f"{API}/students/", json={"name": name, "grade": "S3", "class_name": class_name}, headers=headers
    ).get_json()["id"]
    client.post(
        f"{API}/students/assessment",
        json={"student_id": student_id, "subject": subject, "score": score, "term": "T1"},
        headers=headers,
    )


class TestSubjectsPaginationFilterSort:
    def test_pagination_shape(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("subj.page@example.com")
        _seed(client, headers, "S1", "A", "Math", 70)
        _seed(client, headers, "S2", "A", "English", 80)

        resp = client.get(f"{API}/analytics/subjects", headers=headers)

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["page"] == 1
        assert body["per_page"] == 20
        assert body["total"] == 2
        assert len(body["subjects"]) == 2

    def test_filter_by_subject_substring(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("subj.filter@example.com")
        _seed(client, headers, "S1", "A", "Mathematics", 70)
        _seed(client, headers, "S2", "A", "English", 80)

        resp = client.get(f"{API}/analytics/subjects?subject=math", headers=headers)

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total"] == 1
        assert body["subjects"][0]["subject"] == "Mathematics"

    def test_sort_by_avg_score_ascending(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("subj.sort@example.com")
        _seed(client, headers, "S1", "A", "Math", 90)
        _seed(client, headers, "S2", "A", "English", 60)

        resp = client.get(f"{API}/analytics/subjects?sort=avg_score", headers=headers)

        assert resp.status_code == 200
        subjects = [s["subject"] for s in resp.get_json()["subjects"]]
        assert subjects == ["English", "Math"]

    def test_disallowed_sort_column_returns_400(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("subj.badsort@example.com")

        resp = client.get(f"{API}/analytics/subjects?sort=nonexistent_column", headers=headers)

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"


class TestClassesPaginationFilterSort:
    def test_filter_by_class_name_substring(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("class.filter@example.com")
        _seed(client, headers, "S1", "Alpha", "Math", 70)
        _seed(client, headers, "S2", "Beta", "Math", 80)

        resp = client.get(f"{API}/analytics/classes?class_name=alpha", headers=headers)

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total"] == 1
        assert body["classes"][0]["class_name"] == "Alpha"

    def test_sort_by_avg_score_descending(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("class.sort@example.com")
        _seed(client, headers, "S1", "Alpha", "Math", 60)
        _seed(client, headers, "S2", "Beta", "Math", 90)

        resp = client.get(f"{API}/analytics/classes?sort=-avg_score", headers=headers)

        assert resp.status_code == 200
        names = [c["class_name"] for c in resp.get_json()["classes"]]
        assert names == ["Beta", "Alpha"]
