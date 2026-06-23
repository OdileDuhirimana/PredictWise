from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from ..models import SurveyResponse, Attendance
from statistics import mean

wellness_bp = Blueprint('wellness', __name__)


@wellness_bp.get('/indicator')
@jwt_required(optional=True)
def indicator():
    student_id = request.args.get('student_id', type=int)
    if not student_id:
        return {'error': 'student_id required'}, 400
    surveys = SurveyResponse.query.filter_by(student_id=student_id).order_by(SurveyResponse.created_at.desc()).limit(5).all()
    if not surveys:
        return {'risk': 'unknown', 'score': None}
    mood_avg = mean([s.mood for s in surveys])
    stress_avg = mean([s.stress for s in surveys])
    sleep_avg = mean([s.sleep_hours for s in surveys])
    # Attendance in last 30 entries
    attends = Attendance.query.filter_by(student_id=student_id).order_by(Attendance.id.desc()).limit(30).all()
    attendance_rate = mean([1 if a.present else 0 for a in attends]) if attends else 0.9

    score = (mood_avg/10.0)*0.3 + (1 - (stress_avg/10.0))*0.3 + (min(sleep_avg, 8)/8.0)*0.2 + attendance_rate*0.2
    if score < 0.5:
        risk = 'High Risk'
    elif score < 0.7:
        risk = 'Needs Attention'
    else:
        risk = 'On-Track'
    return {'risk': risk, 'score': round(score, 3), 'inputs': {'mood_avg': mood_avg, 'stress_avg': stress_avg, 'sleep_avg': sleep_avg, 'attendance_rate': attendance_rate}}
