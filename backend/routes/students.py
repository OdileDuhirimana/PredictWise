from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from ..database import db
from ..models import Student, Assessment, Attendance, Gamification, SurveyResponse
from datetime import date, datetime

students_bp = Blueprint('students', __name__)


@students_bp.get('/')
@jwt_required(optional=True)
def list_students():
    items = Student.query.all()
    return {'students': [{'id': s.id, 'name': s.name, 'grade': s.grade, 'class_name': s.class_name} for s in items]}


@students_bp.post('/')
@jwt_required()
def create_student():
    data = request.get_json() or {}
    s = Student(name=data.get('name'), grade=data.get('grade', 'S3'), class_name=data.get('class_name'))
    db.session.add(s)
    db.session.commit()
    # Initialize gamification
    g = Gamification(student_id=s.id, xp=0, streak=0, badges='')
    db.session.add(g)
    db.session.commit()
    return {'id': s.id}


@students_bp.post('/assessment')
@jwt_required()
def add_assessment():
    data = request.get_json() or {}
    a = Assessment(student_id=data['student_id'], subject=data['subject'], score=float(data['score']), max_score=float(data.get('max_score', 100)), term=data.get('term', 'T1'))
    db.session.add(a)
    db.session.commit()
    return {'id': a.id}


@students_bp.post('/attendance')
@jwt_required()
def add_attendance():
    data = request.get_json() or {}
    d = data.get('date')
    if isinstance(d, str):
        try:
            d_parsed = date.fromisoformat(d)
        except ValueError:
            # try datetime full ISO
            d_parsed = datetime.fromisoformat(d).date()
    else:
        d_parsed = d
    at = Attendance(student_id=data['student_id'], date=d_parsed, present=bool(data.get('present', True)))
    db.session.add(at)
    db.session.commit()
    return {'id': at.id}


@students_bp.post('/survey')
@jwt_required()
def add_survey():
    data = request.get_json() or {}
    sr = SurveyResponse(student_id=data['student_id'], mood=int(data.get('mood', 5)), stress=int(data.get('stress', 5)), sleep_hours=float(data.get('sleep_hours', 7)))
    db.session.add(sr)
    db.session.commit()
    return {'id': sr.id}
