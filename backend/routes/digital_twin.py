from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from ..ml.engine import predict


dt_bp = Blueprint('digital_twin', __name__)


@dt_bp.post('/project')
@jwt_required(optional=True)
def project():
    data = request.get_json() or {}
    # Create a simple projection curve across next 3 terms by varying attendance/homework slightly
    base = {
        'avg_score': float(data.get('avg_score', 60)),
        'attendance_rate': float(data.get('attendance_rate', 0.9)),
        'homework_completion': float(data.get('homework_completion', 0.8)),
        'behavior_incidents': float(data.get('behavior_incidents', 0)),
    }
    scenarios = [
        {'label': 'current', **base},
        {'label': 'improved_attendance', **{**base, 'attendance_rate': min(0.99, base['attendance_rate'] + 0.05)}},
        {'label': 'better_homework', **{**base, 'homework_completion': min(1.0, base['homework_completion'] + 0.1)}},
    ]
    points = []
    for sc in scenarios:
        res = predict(sc)
        points.append({'scenario': sc['label'], 'predicted_score': res['predicted_score'], 'pass_prob': res['pass_prob']})
    # Learning health is a composite index
    health = 0.4*(base['avg_score']/100.0) + 0.3*base['attendance_rate'] + 0.3*base['homework_completion']
    status = 'On-Track' if health >= 0.7 else ('Needs Attention' if health >= 0.5 else 'High Risk')
    return {'health_status': status, 'health_score': round(health,3), 'projections': points}
