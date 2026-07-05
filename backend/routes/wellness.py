from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from ..models import Student, SurveyResponse, Attendance
from ..utils.auth import get_current_role_and_user_id
from ..utils.errors import error_response
from statistics import mean

wellness_bp = Blueprint('wellness', __name__)


@wellness_bp.get('/indicator')
@jwt_required()
def indicator():
    student_id = request.args.get('student_id', type=int)
    if not student_id:
        return error_response('validation_error', 'student_id query parameter is required', 400)

    # Ownership scoping: a parent may only view their own child's wellness
    # indicator (mood/stress/sleep survey data is exactly the kind of
    # sensitive information the audit's privacy finding was about). A
    # nonexistent student and a real-but-not-owned student both return the
    # same 404 rather than 403, so a parent probing student IDs cannot use
    # the response to learn which IDs exist in the system.
    role, user_id = get_current_role_and_user_id()
    if role == 'parent':
        student = Student.query.get(student_id)
        if not student or student.parent_id != (int(user_id) if user_id is not None else -1):
            return error_response('not_found', f'No student with id {student_id}', 404)

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
