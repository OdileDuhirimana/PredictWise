"""End-to-end happy-path smoke test.

This exercises the full API surface through the real `/api/v1/...` prefix
(previously this test called unprefixed paths like `/auth/register`, which
is why it failed with a TypeError — login never got a token because the
route didn't exist under that path). It also now accounts for the RBAC
changes: `/ml/train` and `/alerts/send` require an admin token, so this
test seeds an admin user directly via the app context rather than the
default 'teacher' role a plain register() call would produce.
"""
from backend.app import create_app
from backend.database import db
from backend.models import User

API = '/api/v1'

# Real, reproducible bug this fixes: this test used to call `create_app()`
# with no DATABASE_URL override, so it fell back to the same default
# (`sqlite:///predictwise.db`) a real local dev run uses, then called
# `db.drop_all()` + `db.create_all()` directly against it — wiping any
# real seeded demo data on disk every time `pytest` ran, then leaving
# behind exactly this test's own two users / one student. Confirmed via a
# real reproduction: seeding demo data with `python -m backend.seed` and
# then running `pytest` (project.md's own documented commands, in that
# order) silently destroyed the just-seeded database. Isolating to an
# in-memory database mirrors the fix already applied to
# tests/conftest.py's `app` fixture and the pattern already used correctly
# in test_app_config.py.
_TEST_DATABASE_URL = 'sqlite:///:memory:'


def _register_and_login(client, email, password):
    client.post(f'{API}/auth/register', json={'email': email, 'password': password})
    r = client.post(f'{API}/auth/login', json={'email': email, 'password': password})
    return r.get_json()['access_token']


def _seed_admin(app, email, password):
    with app.app_context():
        if not User.query.filter_by(email=email).first():
            user = User(email=email, role='admin')
            user.set_password(password)
            db.session.add(user)
            db.session.commit()


def test_end_to_end(monkeypatch):
    # Must be set *before* create_app() runs: Flask-SQLAlchemy binds its
    # engine using whatever SQLALCHEMY_DATABASE_URI is active at
    # `db.init_app()` time, so setting `app.config[...]` afterward would
    # have no effect on the already-bound engine (see this file's module
    # docstring for the real-world consequence of getting this wrong).
    monkeypatch.setenv('DATABASE_URL', _TEST_DATABASE_URL)
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()

    admin_email, admin_password = 'admin@example.com', 'adminpass123'
    _seed_admin(app, admin_email, admin_password)

    with app.test_client() as client:
        # Teacher-role token (default role from register()) for
        # pedagogical/read actions.
        teacher_token = _register_and_login(client, 'teacher@example.com', 'teacherpass123')
        teacher_headers = {'Authorization': f'Bearer {teacher_token}'}

        # Admin-role token for admin-gated actions (train/alerts).
        admin_token = _register_and_login(client, admin_email, admin_password)
        admin_headers = {'Authorization': f'Bearer {admin_token}'}

        # Create student
        rs = client.post(
            f'{API}/students/',
            json={'name': 'Test Student', 'grade': 'S3', 'class_name': 'A'},
            headers=teacher_headers,
        )
        assert rs.status_code == 200
        student_id = rs.get_json()['id']

        # Add assessments
        a1 = client.post(
            f'{API}/students/assessment',
            json={'student_id': student_id, 'subject': 'Math', 'score': 70, 'term': 'T1'},
            headers=teacher_headers,
        )
        assert a1.status_code == 200
        a2 = client.post(
            f'{API}/students/assessment',
            json={'student_id': student_id, 'subject': 'English', 'score': 65, 'term': 'T1'},
            headers=teacher_headers,
        )
        assert a2.status_code == 200

        # Attendance
        at1 = client.post(
            f'{API}/students/attendance',
            json={'student_id': student_id, 'date': '2025-01-10', 'present': True},
            headers=teacher_headers,
        )
        assert at1.status_code == 200
        at2 = client.post(
            f'{API}/students/attendance',
            json={'student_id': student_id, 'date': '2025-01-11', 'present': False},
            headers=teacher_headers,
        )
        assert at2.status_code == 200

        # Survey
        sv = client.post(
            f'{API}/students/survey',
            json={'student_id': student_id, 'mood': 6, 'stress': 4, 'sleep_hours': 7.5},
            headers=teacher_headers,
        )
        assert sv.status_code == 200

        # List students (now paginated; teacher token required since
        # optional=True was removed)
        ls = client.get(f'{API}/students/', headers=teacher_headers)
        assert ls.status_code == 200
        list_body = ls.get_json()
        assert 'students' in list_body and 'page' in list_body and 'total' in list_body

        # Train model — admin only
        tr = client.post(f'{API}/ml/train', headers=admin_headers)
        assert tr.status_code in (200, 400)  # 400 if no assessment data, but we added some

        # Train as teacher should be forbidden (RBAC)
        tr_forbidden = client.post(f'{API}/ml/train', headers=teacher_headers)
        assert tr_forbidden.status_code == 403

        # Predict
        pred = client.post(
            f'{API}/ml/predict',
            json={'avg_score': 67, 'attendance_rate': 0.8, 'homework_completion': 0.7, 'behavior_incidents': 0},
            headers=teacher_headers,
        )
        assert pred.status_code == 200
        pred_body = pred.get_json()
        assert 'prediction' in pred_body and 'risk' in pred_body

        # Wellness indicator
        w = client.get(f'{API}/wellness/indicator?student_id={student_id}', headers=teacher_headers)
        assert w.status_code == 200

        # Voice NLP
        v = client.post(
            f'{API}/voice/analyze',
            json={'transcript': 'Student felt anxious and was late to class.'},
            headers=teacher_headers,
        )
        assert v.status_code == 200

        # Digital twin
        dt = client.post(
            f'{API}/digital-twin/project',
            json={'avg_score': 67, 'attendance_rate': 0.8, 'homework_completion': 0.7, 'behavior_incidents': 0},
            headers=teacher_headers,
        )
        assert dt.status_code == 200

        # Gamify — teacher is allowed to award
        ga = client.post(
            f'{API}/gamify/award',
            json={'student_id': student_id, 'xp': 20, 'badge': 'Hard Worker'},
            headers=teacher_headers,
        )
        assert ga.status_code == 200
        lb = client.get(f'{API}/gamify/leaderboard', headers=teacher_headers)
        assert lb.status_code == 200

        # Alerts — admin only
        al = client.post(
            f'{API}/alerts/send',
            json={'channel': 'sms', 'to': '+250700000000', 'message': 'Reminder'},
            headers=admin_headers,
        )
        assert al.status_code == 200

        # Alerts as teacher should be forbidden (RBAC)
        al_forbidden = client.post(
            f'{API}/alerts/send',
            json={'channel': 'sms', 'to': '+250700000000', 'message': 'Reminder'},
            headers=teacher_headers,
        )
        assert al_forbidden.status_code == 403

        # Analytics
        dash = client.get(f'{API}/analytics/dashboard', headers=teacher_headers)
        assert dash.status_code == 200
        rep = client.get(f'{API}/analytics/report.pdf', headers=teacher_headers)
        assert rep.status_code == 200

        # Previously-optional routes now require a token (401 without one)
        unauthenticated = client.get(f'{API}/analytics/dashboard')
        assert unauthenticated.status_code == 401

        # Health (unprefixed, no auth required)
        h = client.get('/health')
        assert h.status_code == 200
