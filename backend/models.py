from datetime import datetime
from .database import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(32), default='teacher')  # admin, teacher, parent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    grade = db.Column(db.String(16), nullable=False)
    class_name = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Assessment(db.Model):
    __table_args__ = (
        db.CheckConstraint('score >= 0', name='ck_assessment_score_non_negative'),
        db.CheckConstraint('max_score > 0', name='ck_assessment_max_score_positive'),
    )

    id = db.Column(db.Integer, primary_key=True)
    # index=True: student_id is the join/filter key for every leaderboard,
    # analytics, and per-student query in the codebase — without an index
    # every one of those becomes a full table scan as data grows.
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), index=True)
    subject = db.Column(db.String(64), nullable=False)
    score = db.Column(db.Float, nullable=False)
    max_score = db.Column(db.Float, default=100)
    term = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), index=True)
    date = db.Column(db.Date, nullable=False)
    present = db.Column(db.Boolean, default=True)


class Gamification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), index=True)
    xp = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0)
    badges = db.Column(db.String(512), default='')  # comma-separated


class SurveyResponse(db.Model):
    __table_args__ = (
        db.CheckConstraint('mood >= 1 AND mood <= 10', name='ck_survey_response_mood_range'),
        db.CheckConstraint('stress >= 1 AND stress <= 10', name='ck_survey_response_stress_range'),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), index=True)
    mood = db.Column(db.Integer, default=5)  # 1-10
    stress = db.Column(db.Integer, default=5)  # 1-10
    sleep_hours = db.Column(db.Float, default=7.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
