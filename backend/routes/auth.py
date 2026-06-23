from flask import Blueprint, request
from flask_jwt_extended import create_access_token
from ..models import User
from ..database import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.post('/register')
def register():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return {'error': 'email and password required'}, 400
    if User.query.filter_by(email=email).first():
        return {'error': 'email exists'}, 400
    u = User(email=email)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return {'message': 'registered'}


@auth_bp.post('/login')
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    u = User.query.filter_by(email=email).first()
    if not u or not u.check_password(password):
        return {'error': 'invalid credentials'}, 401
    token = create_access_token(identity=str(u.id), additional_claims={'role': u.role})
    return {'access_token': token}
