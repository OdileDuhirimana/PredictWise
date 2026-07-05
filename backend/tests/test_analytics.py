"""Integration tests for backend/routes/analytics.py.

Covers the bounded aggregate endpoints (subjects/classes/heatmap/
benchmarks/dashboard) plus the PDF report endpoint, using real assessment
data created through the API rather than pagination (these endpoints
intentionally return small, bounded aggregate rows — see the comment in
students.py/analytics.py about why they are NOT paginated).
"""

API = "/api/v1"


def _seed_student_with_assessment(client, headers, name, class_name, subject, score):
    student_resp = client.post(
        f"{API}/students/", json={"name": name, "grade": "S3", "class_name": class_name}, headers=headers
    )
    student_id = student_resp.get_json()["id"]
    client.post(
        f"{API}/students/assessment",
        json={"student_id": student_id, "subject": subject, "score": score, "term": "T1"},
        headers=headers,
    )
    return student_id


class TestDashboard:
    def test_empty_dashboard_returns_zero_defaults(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("dash.empty@example.com")

        resp = client.get(f"{API}/analytics/dashboard", headers=headers)

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total_students"] == 0
        assert body["avg_score"] == 0

    def test_dashboard_reflects_seeded_data(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("dash.seeded@example.com")
        _seed_student_with_assessment(client, headers, "Student A", "A", "Math", 80)

        resp = client.get(f"{API}/analytics/dashboard", headers=headers)

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["total_students"] == 1
        assert body["avg_score"] == 80


class TestSubjectsClassesHeatmapBenchmarks:
    def test_subjects_aggregates_by_subject(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("analytics.subjects@example.com")
        _seed_student_with_assessment(client, headers, "S1", "A", "Math", 70)
        _seed_student_with_assessment(client, headers, "S2", "A", "Math", 90)

        resp = client.get(f"{API}/analytics/subjects", headers=headers)

        assert resp.status_code == 200
        subjects = resp.get_json()["subjects"]
        assert len(subjects) == 1
        assert subjects[0]["subject"] == "Math"
        assert subjects[0]["avg_score"] == 80
        assert subjects[0]["count"] == 2

    def test_classes_aggregates_by_class_name(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("analytics.classes@example.com")
        _seed_student_with_assessment(client, headers, "S1", "A", "Math", 70)
        _seed_student_with_assessment(client, headers, "S2", "B", "Math", 90)

        resp = client.get(f"{API}/analytics/classes", headers=headers)

        assert resp.status_code == 200
        classes = {c["class_name"]: c for c in resp.get_json()["classes"]}
        assert classes["A"]["avg_score"] == 70
        assert classes["B"]["avg_score"] == 90

    def test_heatmap_builds_subject_by_class_matrix(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("analytics.heatmap@example.com")
        _seed_student_with_assessment(client, headers, "S1", "A", "Math", 70)

        resp = client.get(f"{API}/analytics/heatmap", headers=headers)

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["subjects"] == ["Math"]
        assert body["classes"] == ["A"]
        assert body["matrix"] == [[70.0]]

    def test_benchmarks_returns_national_and_current_avg(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("analytics.benchmarks@example.com")
        _seed_student_with_assessment(client, headers, "S1", "A", "Math", 70)

        resp = client.get(f"{API}/analytics/benchmarks", headers=headers)

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["national_avg"] == 65.0
        assert body["current_avg"] == 70


class TestReportPdf:
    def test_report_pdf_returns_pdf_content_type(self, make_authenticated_client):
        client, headers, _ = make_authenticated_client("analytics.pdf@example.com")

        resp = client.get(f"{API}/analytics/report.pdf", headers=headers)

        assert resp.status_code == 200
        assert resp.mimetype == "application/pdf"
