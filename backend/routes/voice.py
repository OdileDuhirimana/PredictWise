from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from pydantic import ValidationError
from ..schemas import VoiceAnalyzeRequest
from ..utils.errors import error_response
from ..utils.nlp import analyze_sentiment

voice_bp = Blueprint('voice', __name__)


@voice_bp.post('/analyze')
@jwt_required()
def analyze():
    try:
        payload = VoiceAnalyzeRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return error_response('validation_error', 'Invalid voice analysis request', 400, details=exc.errors())

    text = payload.transcript
    result = analyze_sentiment(text)
    # Extract simple behavior flags
    behaviors = []
    lowered = text.lower()
    for kw, label in [
        ('late', 'lateness'),
        ('absent', 'absence'),
        ('fight', 'conflict'),
        ('bully', 'bullying'),
        ('anxious', 'anxiety'),
        ('sad', 'sadness'),
        ('stressed', 'stress'),
    ]:
        if kw in lowered:
            behaviors.append(label)
    return {'sentiment': result, 'behaviors': behaviors}
