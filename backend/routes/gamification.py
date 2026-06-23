from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from ..models import Gamification, Student
from ..database import db


gamify_bp = Blueprint('gamify', __name__)


@gamify_bp.post('/award')
@jwt_required()
def award():
    data = request.get_json() or {}
    student_id = int(data['student_id'])
    xp = int(data.get('xp', 10))
    badge = data.get('badge')
    g = Gamification.query.filter_by(student_id=student_id).first()
    if not g:
        g = Gamification(student_id=student_id, xp=0, streak=0, badges='')
        db.session.add(g)
    g.xp += xp
    g.streak = min(g.streak + 1, 365)
    if badge:
        badges = [b for b in g.badges.split(',') if b]
        if badge not in badges:
            badges.append(badge)
        g.badges = ','.join(badges)
    db.session.commit()
    return {'student_id': student_id, 'xp': g.xp, 'streak': g.streak, 'badges': g.badges.split(',') if g.badges else []}


@gamify_bp.get('/leaderboard')
@jwt_required(optional=True)
def leaderboard():
    rows = Gamification.query.order_by(Gamification.xp.desc()).limit(20).all()
    result = []
    for r in rows:
        s = Student.query.get(r.student_id)
        result.append({'student_id': r.student_id, 'name': s.name if s else 'Unknown', 'xp': r.xp, 'streak': r.streak})
    return {'leaderboard': result}
