import os
import random
from datetime import date, timedelta

from backend.app import create_app
from backend.database import db
from backend.models import User, Student, Assessment, Attendance, Gamification, SurveyResponse

DEFAULT_STUDENTS = int(os.getenv('SEED_STUDENTS', '300'))
DEFAULT_TEACHERS = int(os.getenv('SEED_TEACHERS', '10'))
DEFAULT_PARENTS = int(os.getenv('SEED_PARENTS', '20'))
ASSESS_SUBJECTS = ['Math', 'English', 'Kinyarwanda', 'Biology', 'Chemistry', 'Physics', 'History', 'Geography', 'ICT']
TERMS = ['T1', 'T2', 'T3']
GRADES = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6']
CLASSES = ['A', 'B', 'C', 'D']

FIRST_NAMES = [
    'Alice', 'Emmanuel', 'Grace', 'Eric', 'Diane', 'Jean', 'Patrick', 'Aline', 'Samuel', 'Marie',
    'Didier', 'Josiane', 'David', 'Sandrine', 'Joseph', 'Ange', 'Innocent', 'Esther', 'Claude', 'Yvette'
]
LAST_NAMES = [
    'Uwase', 'Ndayisenga', 'Iradukunda', 'Uwimana', 'Munyaneza', 'Uwamahoro', 'Nkurunziza', 'Habyarimana', 'Twagirayezu', 'Mukamana'
]

def rand_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

# Real bug this fixes: '.test' is an IANA/RFC 2606 reserved special-use
# TLD (alongside '.example', '.invalid', '.localhost'). pydantic's
# EmailStr (via the email-validator package, used by schemas.py's
# LoginRequest/RegisterRequest) rejects addresses on any of these
# reserved TLDs as a syntax-level validation failure — meaning every demo
# account this script created with an '@predictwise.test' address could
# never actually log in through the real API, only be inserted directly
# via the ORM. '.rw' is a real ccTLD (Rwanda), fitting this project's own
# "designed with the Rwandan education system in mind" framing, and
# passes EmailStr validation.
DEMO_EMAIL_DOMAIN = 'predictwise.rw'


def ensure_admin():
    admin_email = f'admin@{DEMO_EMAIL_DOMAIN}'
    if not User.query.filter_by(email=admin_email).first():
        u = User(email=admin_email, role='admin')
        u.set_password('admin123')
        db.session.add(u)

def ensure_users(role: str, count: int, email_prefix: str):
    existing = User.query.filter_by(role=role).count()
    to_make = max(0, count - existing)
    for i in range(to_make):
        email = f"{email_prefix}{existing + i + 1}@{DEMO_EMAIL_DOMAIN}"
        u = User(email=email, role=role)
        u.set_password('password')
        db.session.add(u)

def seed_students(target: int):
    current = Student.query.count()
    to_make = max(0, target - current)
    students = []
    for _ in range(to_make):
        s = Student(
            name=rand_name(),
            grade=random.choice(GRADES),
            class_name=random.choice(CLASSES)
        )
        students.append(s)
    if students:
        db.session.add_all(students)
        db.session.commit()
    return Student.query.all()

def seed_gamification(students):
    existing = {g.student_id for g in Gamification.query.all()}
    todo = []
    for s in students:
        if s.id in existing:
            continue
        todo.append(Gamification(
            student_id=s.id,
            xp=random.randint(0, 1500),
            streak=random.randint(0, 60),
            badges=','.join(random.sample(['Starter','Helper','Achiever','Mentor','Leader'], k=random.randint(0,3)))
        ))
    if todo:
        db.session.bulk_save_objects(todo)

def seed_assessments(students):
    if Assessment.query.count() > len(students) * 3:
        return
    rows = []
    for s in students:
        for term in TERMS:
            for subj in random.sample(ASSESS_SUBJECTS, k=min(6, len(ASSESS_SUBJECTS))):
                base = random.randint(40, 85)
                variance = random.randint(-10, 10)
                score = max(0, min(100, base + variance))
                rows.append(Assessment(student_id=s.id, subject=subj, score=score, term=term, max_score=100))
    if rows:
        db.session.bulk_save_objects(rows)

def seed_attendance(students):
    start = date.today() - timedelta(days=80)
    dates = [start + timedelta(days=i) for i in range(80) if (start + timedelta(days=i)).weekday() < 5]
    if Attendance.query.count() > len(students) * len(dates) * 0.5:
        return
    rows = []
    for s in students:
        attend_prob = random.uniform(0.85, 0.98)
        for d in dates:
            present = random.random() < attend_prob
            rows.append(Attendance(student_id=s.id, date=d, present=present))
    if rows:
        db.session.bulk_save_objects(rows)

def seed_surveys(students):
    if SurveyResponse.query.count() > len(students) * 2:
        return
    rows = []
    for s in students:
        for _ in range(random.randint(2, 6)):
            rows.append(SurveyResponse(
                student_id=s.id,
                mood=random.randint(3, 9),
                stress=random.randint(2, 8),
                sleep_hours=round(random.uniform(5.0, 9.0), 1)
            ))
    if rows:
        db.session.bulk_save_objects(rows)

def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        ensure_admin()
        ensure_users('teacher', DEFAULT_TEACHERS, 'teacher')
        ensure_users('parent', DEFAULT_PARENTS, 'parent')
        db.session.commit()

        students = seed_students(DEFAULT_STUDENTS)
        seed_gamification(students)
        seed_assessments(students)
        seed_attendance(students)
        seed_surveys(students)
        db.session.commit()
        print(f"Seeded users: {User.query.count()}, students: {Student.query.count()}, assessments: {Assessment.query.count()}, attendance: {Attendance.query.count()}")

if __name__ == '__main__':
    main()
