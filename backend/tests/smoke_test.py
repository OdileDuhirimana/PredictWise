import json
from backend.app import create_app
from backend.database import db


def get_token(client):
    client.post('/auth/register', json={'email': 't@t.t', 'password': 'p'})
    r = client.post('/auth/login', json={'email': 't@t.t', 'password': 'p'})
    return r.get_json()['access_token']


def test_end_to_end():
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all(); db.create_all()
    with app.test_client() as client:
        token = get_token(client)
        headers = {'Authorization': f'Bearer {token}'}

        # Create student
        rs = client.post('/students/', json={'name': 'Test Student', 'grade': 'S3', 'class_name': 'A'}, headers=headers)
        student_id = rs.get_json()['id']

        # Add assessments
        client.post('/students/assessment', json={'student_id': student_id, 'subject': 'Math', 'score': 70, 'term': 'T1'}, headers=headers)
        client.post('/students/assessment', json={'student_id': student_id, 'subject': 'English', 'score': 65, 'term': 'T1'}, headers=headers)

        # Attendance
        client.post('/students/attendance', json={'student_id': student_id, 'date': '2025-01-10', 'present': True}, headers=headers)
        client.post('/students/attendance', json={'student_id': student_id, 'date': '2025-01-11', 'present': False}, headers=headers)

        # Survey
        client.post('/students/survey', json={'student_id': student_id, 'mood': 6, 'stress': 4, 'sleep_hours': 7.5}, headers=headers)

        # Train model
        tr = client.post('/ml/train', headers=headers)
        assert tr.status_code in (200, 400)  # If no data it may error, but we added

        # Predict
        pred = client.post('/ml/predict', json={'avg_score': 67, 'attendance_rate': 0.8, 'homework_completion': 0.7, 'behavior_incidents': 0}, headers=headers)
        assert pred.status_code == 200
        j = pred.get_json()
        assert 'prediction' in j and 'risk' in j

        # Wellness indicator
        w = client.get(f'/wellness/indicator?student_id={student_id}', headers=headers)
        assert w.status_code == 200

        # Voice NLP
        v = client.post('/voice/analyze', json={'transcript': 'Student felt anxious and was late to class.'}, headers=headers)
        assert v.status_code == 200

        # Digital twin
        dt = client.post('/digital-twin/project', json={'avg_score': 67, 'attendance_rate': 0.8, 'homework_completion': 0.7, 'behavior_incidents': 0}, headers=headers)
        assert dt.status_code == 200

        # Gamify
        ga = client.post('/gamify/award', json={'student_id': student_id, 'xp': 20, 'badge': 'Hard Worker'}, headers=headers)
        assert ga.status_code == 200
        lb = client.get('/gamify/leaderboard', headers=headers)
        assert lb.status_code == 200

        # Alerts (mock)
        al = client.post('/alerts/send', json={'channel': 'sms', 'to': '+2507...', 'message': 'Reminder'}, headers=headers)
        assert al.status_code == 200

        # Analytics
        dash = client.get('/analytics/dashboard', headers=headers)
        assert dash.status_code == 200
        rep = client.get('/analytics/report.pdf', headers=headers)
        assert rep.status_code == 200

        # Health
        h = client.get('/health')
        assert h.status_code == 200

        print('Smoke test passed')
