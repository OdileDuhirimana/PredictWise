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
    # Explicit instance_path, anchored to this file's own directory (one
    # level up, mirroring the repo layout's existing top-level `instance/`
    # folder) rather than Flask's default auto-detection from `__name__`.
    #
    # Real, reproducible bug this fixes: Flask's default instance-path
    # resolution depends on *how this module was invoked*, not just where
    # it lives on disk. `Flask(__name__)` computes it from the string
    # `__name__` at the call site — normally `'backend.app'` when this
    # module is imported as part of the `backend` package (gunicorn's
    # `wsgi:application`, `flask run`/`flask db upgrade`, pytest's
    # `create_app()` calls, and `python -m backend.seed`, which all import
    # this module rather than execute it), resolving one level *above* the
    # `backend/` package directory — i.e. this repo's top-level
    # `instance/`. But `python -m backend.app` — project.md's own "Local
    # Setup" step 5, listed as the primary way to run the dev server —
    # executes this exact file with `__name__` forced to `'__main__'`
    # instead, which resolves to `backend/instance/` one level down.
    # Confirmed via a real run: seeding demo data with `python -m
    # backend.seed` (writes to top-level `instance/predictwise.db`) and
    # then starting the server with `python -m backend.app` (reads from
    # `backend/instance/predictwise.db`, silently empty) meant every
    # seeded demo account — admin/teacher/parent alike — got a clean but
    # incorrect 401 "Invalid email or password" on login, because the
    # dev server was never looking at the database that had just been
    # seeded. Pinning instance_path here makes it identical across every
    # entry point regardless of how this module happens to be invoked.
    _instance_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance'
    )
    app = Flask(__name__, instance_path=_instance_path)

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
    CORS(app, origins=_parse_origins(os.getenv('CORS_ALLOWED_ORIGINS', '*')))
    JWTManager(app)
    limiter = Limiter(get_remote_address, app=app, default_limits=[os.getenv('RATE_LIMIT', '200/hour')])
    Swagger(app)
    PrometheusMetrics(app)

    db.init_app(app)
    # Explicit directory (rather than Flask-Migrate's default, cwd-relative
    # 'migrations'): start.sh and Docker/Render both run `flask db upgrade`
    # from the repository root, not from backend/, so the cwd-relative
    # default silently resolved to a nonexistent './migrations' and failed
    # every time — masked in practice by start.sh's `|| echo "...continuing"`
    # fallback, meaning migrations were never actually being applied in any
    # deployed environment despite DB-05 migrations "existing" in the repo.
    # Anchoring to this file's own directory makes migration discovery
    # independent of the caller's working directory.
    migrate.init_app(app, db, directory=os.path.join(os.path.dirname(__file__), 'migrations'))

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


# This must be the last thing in the file: `if __name__ == '__main__':`
# runs immediately as the module executes top-to-bottom, so every name it
# references (_setup_signals, _configure_logging via create_app()) must
# already be defined above it. Previously `_configure_logging`/
# `_setup_signals` were defined *after* this block, meaning `python -m
# backend.app` — the exact command project.md's own "Local Setup"
# instructions recommend — raised `NameError: name '_configure_logging'
# is not defined` immediately on startup. This went undetected because
# every other entry point (the pytest suite's `create_app()` calls via
# the factory pattern, `flask run`/`flask db upgrade` via the Flask CLI,
# and `gunicorn wsgi:application` in start.sh) imports the module without
# ever executing this `__main__` block, so none of them exercised it.
if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    _setup_signals()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
