from flask import Blueprint, request
from flask_jwt_extended import create_access_token
from pydantic import ValidationError

from ..database import db
from ..models import User
from ..schemas import LoginRequest, RegisterRequest
from ..utils.errors import error_response

auth_bp = Blueprint('auth', __name__)


@auth_bp.post('/register')
def register():
    try:
        payload = RegisterRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return error_response('validation_error', 'Invalid registration details', 400, details=exc.errors())

    if User.query.filter_by(email=payload.email).first():
        return error_response('validation_error', 'An account with this email already exists', 400)

    user = User(email=payload.email)
    user.set_password(payload.password)
    db.session.add(user)
    db.session.commit()
    return {'message': 'registered'}


@auth_bp.post('/login')
def login():
    try:
        payload = LoginRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return error_response('validation_error', 'Invalid login details', 400, details=exc.errors())

    user = User.query.filter_by(email=payload.email).first()
    if not user or not user.check_password(payload.password):
        return error_response('unauthorized', 'Invalid email or password', 401)

    token = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
    return {'access_token': token}
