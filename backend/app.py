import os
import secrets
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger
from prometheus_flask_exporter import PrometheusMetrics
import logging
from pythonjsonlogger import jsonlogger
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sqlalchemy import text
import signal
import threading

from .database import db, migrate
from .routes.auth import auth_bp
from .routes.students import students_bp
from .routes.ml import ml_bp
from .routes.analytics import analytics_bp
from .routes.gamification import gamify_bp
from .routes.alerts import alerts_bp
from .routes.wellness import wellness_bp
from .routes.voice import voice_bp
from .routes.digital_twin import dt_bp


def _parse_origins(raw_origins: str):
    origins = [origin.strip() for origin in raw_origins.split(',') if origin.strip()]
    return origins or ['*']


def _normalize_database_url(raw_url: str) -> str:
    if raw_url.startswith('postgres://'):
        return raw_url.replace('postgres://', 'postgresql+psycopg://', 1)
    if raw_url.startswith('postgresql://'):
        return raw_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    return raw_url


def create_app():
    load_dotenv()
    app = Flask(__name__)

    _is_prod = (os.getenv('FLASK_ENV') or os.getenv('NODE_ENV') or 'development').lower() == 'production'

    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        if _is_prod:
            raise RuntimeError('DATABASE_URL must be set in production')
        db_url = 'sqlite:///predictwise.db'
    else:
        db_url = _normalize_database_url(db_url)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    _jwt_secret = os.getenv('JWT_SECRET_KEY')
    if not _jwt_secret:
        if _is_prod:
            raise RuntimeError('JWT_SECRET_KEY must be set in production')
        _jwt_secret = secrets.token_hex(32)
    app.config['JWT_SECRET_KEY'] = _jwt_secret
    app.config['SWAGGER'] = {
        'title': 'PredictWise API',
        'uiversion': 3,
        'version': '1.0.0',
        'openapi': '3.0.3'
    }

    # Observability & security
    _configure_logging()
    sentry_dsn = os.getenv('SENTRY_DSN')
    if sentry_dsn:
        sentry_sdk.init(dsn=sentry_dsn, integrations=[FlaskIntegration()])
    CORS(app, origins=_parse_origins(os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://localhost:3000')))
    JWTManager(app)
    limiter = Limiter(get_remote_address, app=app, default_limits=[os.getenv('RATE_LIMIT', '200/hour')])
    Swagger(app)
    PrometheusMetrics(app)

    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    api_prefix = '/api/v1'
    app.register_blueprint(auth_bp, url_prefix=f'{api_prefix}/auth')
    app.register_blueprint(students_bp, url_prefix=f'{api_prefix}/students')
    app.register_blueprint(ml_bp, url_prefix=f'{api_prefix}/ml')
    app.register_blueprint(analytics_bp, url_prefix=f'{api_prefix}/analytics')
    app.register_blueprint(gamify_bp, url_prefix=f'{api_prefix}/gamify')
    app.register_blueprint(alerts_bp, url_prefix=f'{api_prefix}/alerts')
    app.register_blueprint(wellness_bp, url_prefix=f'{api_prefix}/wellness')
    app.register_blueprint(voice_bp, url_prefix=f'{api_prefix}/voice')
    app.register_blueprint(dt_bp, url_prefix=f'{api_prefix}/digital-twin')

    @app.get('/health')
    def health():
        return {'status': 'ok'}

    @app.get('/ready')
    def ready():
        try:
            db.session.execute(text('SELECT 1'))
            db_ok = True
        except Exception:
            db_ok = False
        status = 200 if db_ok else 503
        return jsonify({'db': db_ok}), status

    return app


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    _setup_signals()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))


# Logging configuration
def _configure_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

_shutdown_event = threading.Event()

def _setup_signals():
    def _graceful(signum, frame):
        logging.info({'event': 'shutdown', 'signal': signum})
        _shutdown_event.set()
    signal.signal(signal.SIGTERM, _graceful)
    signal.signal(signal.SIGINT, _graceful)
