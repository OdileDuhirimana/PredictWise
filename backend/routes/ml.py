from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from pydantic import ValidationError
from ..models import Assessment, Attendance

from ..ml.engine import predict, is_trained, compute_psi, explain_shap, train_regressor
from ..schemas import StudentFeaturesRequest
from ..services.ml_feature_service import build_feature_dataframe
from ..services.risk_service import classify_risk
from ..utils.errors import error_response
from ..utils.recommend import recommend_study_plan

ml_bp = Blueprint('ml', __name__)


def _fetch_feature_dataframe():
    """Shared DB-read step for both the synchronous train() and drift()
    below — both need the exact same per-student feature frame (see
    services/ml_feature_service.py's module docstring for why this used to
    be duplicated). Returns None if there is no assessment data at all.
    """
    assessments = Assessment.query.all()
    if not assessments:
        return None
    attendance = Attendance.query.all()
    return build_feature_dataframe(
        [{'student_id': a.student_id, 'score': a.score} for a in assessments],
        [{'student_id': x.student_id, 'present': 1 if x.present else 0} for x in attendance],
    )


@ml_bp.post('/train')
@jwt_required()
def train():
    df = _fetch_feature_dataframe()
    if df is None:
        return {'error': 'no assessment data'}, 400
    y = df['avg_score']
    X = df[['avg_score', 'attendance_rate', 'homework_completion', 'behavior_incidents']]
    score = train_regressor(X, y)
    return {'cv_score': score}


@ml_bp.post('/predict')
@jwt_required()
def do_predict():
    try:
        payload = StudentFeaturesRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return error_response('validation_error', 'Invalid prediction features', 400, details=exc.errors())

    data = payload.model_dump()
    res = predict(data)
    risk = classify_risk(res['pass_prob'], res['predicted_score'])
    # SHAP explain (real if available, otherwise fallback)
    shap_vals = explain_shap(data)
    recs = recommend_study_plan(data, res, risk)
    return {'prediction': res, 'risk': risk, 'shap': shap_vals, 'recommendations': recs, 'model_trained': is_trained()}


@ml_bp.get('/drift')
@jwt_required()
def drift():
    df = _fetch_feature_dataframe()
    if df is None:
        return {'error': 'no assessment data'}, 400
    cur = df[['avg_score', 'attendance_rate', 'homework_completion', 'behavior_incidents']]
    psi = compute_psi(cur)
    return {'psi': psi}
