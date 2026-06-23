from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from ..models import Assessment, Attendance, Student
from ..database import db
import pandas as pd

from ..ml.engine import train_regressor, predict, is_trained, compute_psi, explain_shap
from ..utils.recommend import recommend_study_plan

ml_bp = Blueprint('ml', __name__)


@ml_bp.post('/train')
@jwt_required()
def train():
    # Simple dataset: aggregate per-student features from assessments and attendance
    assessments = Assessment.query.all()
    if not assessments:
        return {'error': 'no assessment data'}, 400
    df = pd.DataFrame([{'student_id': a.student_id, 'score': a.score} for a in assessments])
    agg = df.groupby('student_id').score.mean().reset_index().rename(columns={'score': 'avg_score'})

    # Attendance rate mock: count of attendance rows
    att = Attendance.query.all()
    if att:
        att_df = pd.DataFrame([{'student_id': x.student_id, 'present': 1 if x.present else 0} for x in att])
        att_agg = att_df.groupby('student_id').present.mean().reset_index().rename(columns={'present': 'attendance_rate'})
    else:
        att_agg = pd.DataFrame(columns=['student_id', 'attendance_rate'])

    X = agg.merge(att_agg, on='student_id', how='left').fillna({'attendance_rate': 0.9})
    X['homework_completion'] = 0.8
    X['behavior_incidents'] = 0
    y = X.pop('avg_score')
    features = X.assign(avg_score=y)[['avg_score','attendance_rate','homework_completion','behavior_incidents']]
    score = train_regressor(features, y)
    return {'cv_score': score}


@ml_bp.post('/predict')
@jwt_required(optional=True)
def do_predict():
    data = request.get_json() or {}
    res = predict(data)
    # Risk classification
    risk = 'On-Track'
    if res['pass_prob'] < 0.5 or res['predicted_score'] < 50:
        risk = 'High Risk'
    elif res['pass_prob'] < 0.7 or res['predicted_score'] < 65:
        risk = 'Needs Attention'
    # SHAP explain (real if available, otherwise fallback)
    shap_vals = explain_shap(data)
    recs = recommend_study_plan(data, res, risk)
    return {'prediction': res, 'risk': risk, 'shap': shap_vals, 'recommendations': recs, 'model_trained': is_trained()}


@ml_bp.get('/drift')
@jwt_required()
def drift():
    # Build current feature frame similar to training
    assessments = Assessment.query.all()
    if not assessments:
        return {'error': 'no assessment data'}, 400
    df = pd.DataFrame([{'student_id': a.student_id, 'score': a.score} for a in assessments])
    agg = df.groupby('student_id').score.mean().reset_index().rename(columns={'score': 'avg_score'})

    att = Attendance.query.all()
    if att:
        att_df = pd.DataFrame([{'student_id': x.student_id, 'present': 1 if x.present else 0} for x in att])
        att_agg = att_df.groupby('student_id').present.mean().reset_index().rename(columns={'present': 'attendance_rate'})
    else:
        att_agg = pd.DataFrame(columns=['student_id', 'attendance_rate'])

    X = agg.merge(att_agg, on='student_id', how='left').fillna({'attendance_rate': 0.9})
    X['homework_completion'] = 0.8
    X['behavior_incidents'] = 0
    cur = X[['avg_score','attendance_rate','homework_completion','behavior_incidents']]
    psi = compute_psi(cur)
    return {'psi': psi}
