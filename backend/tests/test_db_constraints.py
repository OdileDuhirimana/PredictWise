"""Tests proving domain rules are enforced at the database layer itself,
not only by pydantic at the API boundary.

The audit's DOM-04/DB-03 findings were specific: pydantic schemas validate
mood/stress/score bounds on the HTTP request path, but a direct ORM write
(e.g. from seed.py, a future admin script, or a bug that bypasses the
route layer) had no database-level backstop. These tests write directly
through SQLAlchemy — bypassing schemas.py and the route layer entirely —
to prove the CheckConstraints added to models.py actually reject bad data
at the database, not just at the API.
"""
import pytest
from sqlalchemy.exc import IntegrityError

from backend.database import db
from backend.models import Assessment, Student, SurveyResponse


def _make_student(app):
    student = Student(name="Constraint Test Student", grade="S3")
    db.session.add(student)
    db.session.commit()
    return student.id


class TestAssessmentConstraints:
    def test_negative_score_rejected_at_db_layer(self, app):
        with app.app_context():
            student_id = _make_student(app)
            db.session.add(
                Assessment(student_id=student_id, subject="Math", score=-1, max_score=100, term="T1")
            )
            with pytest.raises(IntegrityError):
                db.session.commit()

    def test_zero_max_score_rejected_at_db_layer(self, app):
        with app.app_context():
            student_id = _make_student(app)
            db.session.add(
                Assessment(student_id=student_id, subject="Math", score=10, max_score=0, term="T1")
            )
            with pytest.raises(IntegrityError):
                db.session.commit()

    def test_valid_assessment_is_accepted(self, app):
        with app.app_context():
            student_id = _make_student(app)
            db.session.add(
                Assessment(student_id=student_id, subject="Math", score=70, max_score=100, term="T1")
            )
            db.session.commit()  # must not raise


class TestSurveyResponseConstraints:
    def test_out_of_range_mood_rejected_at_db_layer(self, app):
        with app.app_context():
            student_id = _make_student(app)
            db.session.add(SurveyResponse(student_id=student_id, mood=15, stress=5, sleep_hours=7))
            with pytest.raises(IntegrityError):
                db.session.commit()

    def test_out_of_range_stress_rejected_at_db_layer(self, app):
        with app.app_context():
            student_id = _make_student(app)
            db.session.add(SurveyResponse(student_id=student_id, mood=5, stress=0, sleep_hours=7))
            with pytest.raises(IntegrityError):
                db.session.commit()

    def test_valid_survey_response_is_accepted(self, app):
        with app.app_context():
            student_id = _make_student(app)
            db.session.add(SurveyResponse(student_id=student_id, mood=5, stress=5, sleep_hours=7))
            db.session.commit()  # must not raise
