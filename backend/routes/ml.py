from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from pydantic import ValidationError
from ..models import Assessment, Attendance

from ..jobs.queue import get_training_queue
from ..jobs.training_job import run_training_job
from ..ml.engine import predict, is_trained, compute_psi, explain_shap, train_regressor
from ..schemas import StudentFeaturesRequest
from ..services.ml_feature_service import build_feature_dataframe
from ..services.risk_service import classify_risk
from ..utils.auth import roles_required
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
# Retraining the shared model affects predictions for the whole school, so
# it's restricted to admins rather than any teacher/parent.
@roles_required('admin')
def train():
    # Background job path: if REDIS_URL is configured, hand training off
    # to an RQ worker and return immediately with a pollable job id rather
    # than blocking the request thread for the duration of GridSearchCV —
    # this was explicitly flagged as unaddressed technical debt ("Future
    # Work") for any dataset larger than a demo-scale school. Falls back
    # to the original synchronous behavior with zero configuration
    # required, so existing deployments/tests are unaffected.
    queue = get_training_queue()
    if queue is not None:
        job = queue.enqueue(run_training_job)
        return {'job_id': job.id, 'status': 'queued'}, 202

    df = _fetch_feature_dataframe()
    if df is None:
        return {'error': 'no assessment data'}, 400
    y = df['avg_score']
    X = df[['avg_score', 'attendance_rate', 'homework_completion', 'behavior_incidents']]
    score = train_regressor(X, y)
    return {'cv_score': score}


@ml_bp.get('/train/status/<job_id>')
@jwt_required()
@roles_required('admin')
def train_status(job_id: str):
    queue = get_training_queue()
    if queue is None:
        return error_response(
            'not_found',
            'Background training is not enabled (REDIS_URL is not configured).',
            404,
        )

    from rq.job import Job
    from rq.exceptions import NoSuchJobError

    try:
        job = Job.fetch(job_id, connection=queue.connection)
    except NoSuchJobError:
        return error_response('not_found', f'No training job with id {job_id}', 404)

    return {
        'job_id': job.id,
        'status': job.get_status(refresh=True),
        'result': job.return_value(),
    }


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
