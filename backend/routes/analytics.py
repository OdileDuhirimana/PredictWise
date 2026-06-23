from flask import Blueprint, send_file
from flask_jwt_extended import jwt_required
from io import BytesIO
from reportlab.pdfgen import canvas
from ..database import db
from ..models import Assessment, Student

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.get('/dashboard')
@jwt_required(optional=True)
def dashboard():
    # Minimal metrics
    total_students = Student.query.count()
    assessments = Assessment.query.all()
    avg_score = round(sum(a.score for a in assessments)/len(assessments), 2) if assessments else 0
    return {'total_students': total_students, 'avg_score': avg_score}


@analytics_bp.get('/report.pdf')
@jwt_required()
def report_pdf():
    buf = BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 800, 'PredictWise Annual Report')
    c.drawString(100, 780, f'Total Students: {Student.query.count()}')
    assessments = Assessment.query.all()
    avg_score = round(sum(a.score for a in assessments)/len(assessments), 2) if assessments else 0
    c.drawString(100, 760, f'Average Score: {avg_score}')
    c.showPage(); c.save()
    buf.seek(0)
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name='annual_report.pdf')


@analytics_bp.get('/subjects')
@jwt_required(optional=True)
def subjects():
    # Average score per subject
    rows = db.session.query(Assessment.subject, db.func.avg(Assessment.score), db.func.count(Assessment.id))\
        .group_by(Assessment.subject).all()
    data = [{'subject': r[0], 'avg_score': float(r[1] or 0), 'count': int(r[2] or 0)} for r in rows]
    return {'subjects': data}


@analytics_bp.get('/classes')
@jwt_required(optional=True)
def classes():
    # Average score per class_name by joining Student
    rows = db.session.query(Student.class_name, db.func.avg(Assessment.score), db.func.count(Assessment.id))\
        .join(Assessment, Assessment.student_id == Student.id)\
        .group_by(Student.class_name).all()
    data = [{'class_name': (r[0] or 'Unknown'), 'avg_score': float(r[1] or 0), 'count': int(r[2] or 0)} for r in rows]
    return {'classes': data}


@analytics_bp.get('/heatmap')
@jwt_required(optional=True)
def heatmap():
    # Build subject x class_name matrix of average scores
    rows = db.session.query(Assessment.subject, Student.class_name, db.func.avg(Assessment.score))\
        .join(Student, Student.id == Assessment.student_id)\
        .group_by(Assessment.subject, Student.class_name).all()
    subjects = sorted({r[0] for r in rows})
    classes = sorted({(r[1] or 'Unknown') for r in rows})
    # Initialize matrix with None
    matrix = [[None for _ in classes] for _ in subjects]
    index_s = {s:i for i,s in enumerate(subjects)}
    index_c = {c:i for i,c in enumerate(classes)}
    for s, c, avg in rows:
        i = index_s[s]
        j = index_c[(c or 'Unknown')]
        matrix[i][j] = float(avg or 0)
    return {'subjects': subjects, 'classes': classes, 'matrix': matrix}


@analytics_bp.get('/benchmarks')
@jwt_required(optional=True)
def benchmarks():
    # Simple static national benchmark; could be stored/configured elsewhere
    # Also include overall current average for comparison
    assessments = Assessment.query.all()
    current_avg = round(sum(a.score for a in assessments)/len(assessments), 2) if assessments else 0
    return {'national_avg': 65.0, 'current_avg': current_avg}

