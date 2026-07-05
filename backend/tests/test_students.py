"""Integration tests for backend/routes/students.py.

Covers pydantic validation (the audit's specific "malformed add_assessment
returns 400 with structured envelope, not a raw 500" requirement) and the
new pagination/filtering/sorting behavior of list_students, including the
sort-column allow-list that guards against arbitrary attribute injection.
"""

API = "/api/v1/students"


def _create_student(client, headers, **overrides):
    payload = {"name": "Test Student", "grade": "S3", "class_name": "A"}
    payload.update(overrides)
    resp = client.post(f"{API}/", json=payload, headers=headers)
    assert resp.status_code == 200
    return resp.get_json()["id"]


class TestAddAssessmentValidation:
    def test_missing_score_returns_400_not_500(self, make_authenticated_client):
        """This is the exact regression case called out by the audit: a
        malformed body (missing 'score') must never reach a raw
        `float(data['score'])` KeyError that surfaces as an unhandled 500."""
        client, headers, _ = make_authenticated_client("assess.missing@example.com")
        student_id = _create_student(client, headers)

        resp = client.post(
            f"{API}/assessment",
            json={"student_id": student_id, "subject": "Math", "term": "T1"},
            headers=headers,
        )

        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"]["code"] == "validation_error"
        assert any(err["loc"] == ["score"] for err in body["error"]["details"])

    def test_negative_score_rejected(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("assess.negative@example.com")
        student_id = _create_student(client, headers)

        resp = client.post(
            f"{API}/assessment",
            json={"student_id": student_id, "subject": "Math", "score": -5, "term": "T1"},
            headers=headers,
        )

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"

    def test_unknown_student_id_returns_404(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("assess.unknown@example.com")

        resp = client.post(
            f"{API}/assessment",
            json={"student_id": 999999, "subject": "Math", "score": 70, "term": "T1"},
            headers=headers,
        )

        assert resp.status_code == 404
        assert resp.get_json()["error"]["code"] == "not_found"

    def test_valid_assessment_succeeds(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("assess.valid@example.com")
        student_id = _create_student(client, headers)

        resp = client.post(
            f"{API}/assessment",
            json={"student_id": student_id, "subject": "Math", "score": 70, "term": "T1"},
            headers=headers,
        )

        assert resp.status_code == 200
        assert "id" in resp.get_json()


class TestAddAttendanceValidation:
    def test_invalid_date_format_returns_400(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("attend.invalid@example.com")
        student_id = _create_student(client, headers)

        resp = client.post(
            f"{API}/attendance",
            json={"student_id": student_id, "date": "not-a-date"},
            headers=headers,
        )

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"


class TestAddSurveyValidation:
    def test_out_of_range_mood_returns_400(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("survey.invalid@example.com")
        student_id = _create_student(client, headers)

        resp = client.post(
            f"{API}/survey",
            json={"student_id": student_id, "mood": 15},
            headers=headers,
        )

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"


class TestListStudentsPagination:
    def test_default_pagination_shape(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("list.default@example.com")
        for i in range(3):
            _create_student(client, headers, name=f"Student {i}")

        resp = client.get(f"{API}/", headers=headers)

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["page"] == 1
        assert body["per_page"] == 20
        assert body["total"] == 3
        assert len(body["students"]) == 3

    def test_per_page_is_capped_at_100(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("list.cap@example.com")
        _create_student(client, headers)

        resp = client.get(f"{API}/?per_page=500", headers=headers)

        assert resp.status_code == 200
        assert resp.get_json()["per_page"] == 100

    def test_filter_by_grade(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("list.filter@example.com")
        _create_student(client, headers, name="S3 Student", grade="S3")
        _create_student(client, headers, name="S6 Student", grade="S6")

        resp = client.get(f"{API}/?grade=S6", headers=headers)

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total"] == 1
        assert body["students"][0]["name"] == "S6 Student"

    def test_sort_by_name_descending(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("list.sort@example.com")
        _create_student(client, headers, name="Alice")
        _create_student(client, headers, name="Bob")

        resp = client.get(f"{API}/?sort=-name", headers=headers)

        assert resp.status_code == 200
        names = [s["name"] for s in resp.get_json()["students"]]
        assert names == ["Bob", "Alice"]

    def test_sort_by_disallowed_column_returns_400(self, make_authenticated_client):
        """Guards the sortable-columns allow-list: an attempt to sort by a
        column outside {name, grade, class_name, created_at} must be
        rejected rather than raising AttributeError deep in SQLAlchemy."""
        client, headers, _ = make_authenticated_client("list.badsort@example.com")

        resp = client.get(f"{API}/?sort=password_hash", headers=headers)

        assert resp.status_code == 400
        assert resp.get_json()["error"]["code"] == "validation_error"

    def test_page_beyond_range_returns_empty_list_not_error(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("list.outofrange@example.com")
        _create_student(client, headers)

        resp = client.get(f"{API}/?page=99", headers=headers)

        assert resp.status_code == 200
        assert resp.get_json()["students"] == []
