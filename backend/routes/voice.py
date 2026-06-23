from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from ..utils.nlp import analyze_sentiment

voice_bp = Blueprint('voice', __name__)


@voice_bp.post('/analyze')
@jwt_required(optional=True)
def analyze():
    data = request.get_json() or {}
    text = data.get('transcript', '')
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
