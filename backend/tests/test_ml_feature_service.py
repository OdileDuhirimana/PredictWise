"""Pure unit tests for services/ml_feature_service.py — plain lists of
dicts in, a pandas DataFrame out. No Flask app, no database, no ORM
models. Proves ml.py::train() and ml.py::drift() now build their feature
frame identically (the audit's CODE-04 duplicate-logic finding).
"""
from backend.services.ml_feature_service import (
    DEFAULT_ATTENDANCE_RATE,
    DEFAULT_BEHAVIOR_INCIDENTS,
    DEFAULT_HOMEWORK_COMPLETION,
    build_feature_dataframe,
)


class TestBuildFeatureDataframe:
    def test_empty_assessments_returns_empty_frame_with_correct_columns(self):
        df = build_feature_dataframe([], [])

        assert df.empty
        assert list(df.columns) == ["student_id", "avg_score", "attendance_rate", "homework_completion", "behavior_incidents"]

    def test_averages_multiple_assessments_per_student(self):
        rows = [
            {"student_id": 1, "score": 60},
            {"student_id": 1, "score": 80},
        ]

        df = build_feature_dataframe(rows, [])

        assert len(df) == 1
        assert df.iloc[0]["avg_score"] == 70

    def test_missing_attendance_defaults_to_default_rate(self):
        df = build_feature_dataframe([{"student_id": 1, "score": 70}], [])

        assert df.iloc[0]["attendance_rate"] == DEFAULT_ATTENDANCE_RATE

    def test_attendance_rate_computed_from_present_flags(self):
        assessment_rows = [{"student_id": 1, "score": 70}]
        attendance_rows = [
            {"student_id": 1, "present": 1},
            {"student_id": 1, "present": 0},
        ]

        df = build_feature_dataframe(assessment_rows, attendance_rows)

        assert df.iloc[0]["attendance_rate"] == 0.5

    def test_homework_completion_and_behavior_incidents_use_fixed_defaults(self):
        df = build_feature_dataframe([{"student_id": 1, "score": 70}], [])

        assert df.iloc[0]["homework_completion"] == DEFAULT_HOMEWORK_COMPLETION
        assert df.iloc[0]["behavior_incidents"] == DEFAULT_BEHAVIOR_INCIDENTS

    def test_multiple_students_each_get_their_own_row(self):
        rows = [
            {"student_id": 1, "score": 60},
            {"student_id": 2, "score": 90},
        ]

        df = build_feature_dataframe(rows, [])

        assert sorted(df["student_id"].tolist()) == [1, 2]

    def test_student_with_assessments_but_no_attendance_rows_uses_default(self):
        assessment_rows = [
            {"student_id": 1, "score": 70},
            {"student_id": 2, "score": 80},
        ]
        attendance_rows = [{"student_id": 1, "present": 1}]

        df = build_feature_dataframe(assessment_rows, attendance_rows)

        student_2_row = df[df["student_id"] == 2].iloc[0]
        assert student_2_row["attendance_rate"] == DEFAULT_ATTENDANCE_RATE
