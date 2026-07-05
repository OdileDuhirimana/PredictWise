"""Shared pytest fixtures for the backend test suite.

Why fixtures live here instead of being duplicated per test file: every
integration test needs (1) an isolated Flask app + database and (2) an
authenticated client for one of three roles (admin/teacher/parent). Before
this change there was no reusable way to get either, so each test file
would have had to hand-roll app setup and register/login boilerplate,
which is exactly the kind of duplication that makes test suites expensive
to maintain. `app`/`client` give a fresh in-memory SQLite database per test
function (fast, and guarantees no cross-test pollution), and
`make_authenticated_client` is a factory fixture parametrizable by role so
test_authorization.py, test_auth.py, and the smoke test can all share it.
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path so `import backend` works when running from repo root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from backend.app import create_app
from backend.database import db as _db
from backend.models import User


@pytest.fixture()
def app(monkeypatch):
    """A fresh Flask app + in-memory SQLite schema, torn down after each test.

    Function-scoped (not session-scoped) so tests never leak state into
    each other via shared rows — each test gets `db.create_all()` on an
    empty in-memory database and `db.drop_all()` afterwards.

    Real, reproducible bug this fixes: the in-memory URI used to be applied
    by mutating `flask_app.config["SQLALCHEMY_DATABASE_URI"]` *after*
    `create_app()` had already returned. But `create_app()` calls
    `db.init_app(app)`, and Flask-SQLAlchemy 3.x binds its actual Engine at
    that call using whatever `SQLALCHEMY_DATABASE_URI` is in `app.config`
    at that moment — mutating the config afterward doesn't rebind the
    already-created engine. So every test using this fixture was silently
    running `db.create_all()` / `db.drop_all()` against the *real* database
    (`DATABASE_URL`, or the `sqlite:///predictwise.db` default) instead of
    an isolated in-memory one. Confirmed via a real reproduction: seeding
    demo data with `python -m backend.seed` and then running `pytest`
    (project.md's own documented commands, in that order) silently dropped
    every table in the just-seeded database via this fixture's teardown.
    Setting the env var *before* `create_app()` runs — the same pattern
    `test_app_config.py` already uses correctly via `monkeypatch.setenv`
    — ensures Flask-SQLAlchemy binds its engine to the in-memory database
    from the start.
    """
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    """A Flask test client bound to the per-test `app` fixture."""
    return app.test_client()


@pytest.fixture()
def make_authenticated_client(app, client):
    """Factory fixture: registers+logs in a user with a given role and
    returns (client, headers, user_id) for immediate use in a test.

    Parametrizable by role because RBAC tests need admin/teacher/parent
    tokens interchangeably, and auth tests need plain default-role tokens.
    Registration always creates a 'teacher' role (the model default), so
    for admin/parent roles we register then directly flip the role in the
    database — mirroring how seed.py creates non-default-role users.
    """

    def _make(email: str, password: str = "password123", role: str = "teacher"):
        register_resp = client.post(
            "/api/v1/auth/register", json={"email": email, "password": password}
        )
        assert register_resp.status_code == 200, register_resp.get_json()

        if role != "teacher":
            with app.app_context():
                user = User.query.filter_by(email=email).first()
                user.role = role
                _db.session.commit()

        login_resp = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert login_resp.status_code == 200, login_resp.get_json()
        token = login_resp.get_json()["access_token"]

        with app.app_context():
            user_id = User.query.filter_by(email=email).first().id

        return client, {"Authorization": f"Bearer {token}"}, user_id

    return _make
