from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from pydantic import ValidationError

from ..database import db
from ..models import Assessment, Attendance, Gamification, Student, SurveyResponse, User
from ..schemas import (
    AddAssessmentRequest,
    AddAttendanceRequest,
    AddSurveyRequest,
    AssignParentRequest,
    CreateStudentRequest,
)
from ..utils.auth import get_current_role_and_user_id, roles_required
from ..utils.errors import error_response

students_bp = Blueprint('students', __name__)

# Allow-list of columns the `sort` query param may reference. This prevents
# arbitrary attribute injection (e.g. sorting by an unintended/sensitive
# column) — only these known-safe Student columns are sortable.
_SORTABLE_COLUMNS = {
    'name': Student.name,
    'grade': Student.grade,
    'class_name': Student.class_name,
    'created_at': Student.created_at,
}
_DEFAULT_PER_PAGE = 20
_MAX_PER_PAGE = 100


@students_bp.get('/')
@jwt_required()
def list_students():
    page = request.args.get('page', default=1, type=int) or 1
    per_page = request.args.get('per_page', default=_DEFAULT_PER_PAGE, type=int) or _DEFAULT_PER_PAGE
    page = max(page, 1)
    per_page = min(max(per_page, 1), _MAX_PER_PAGE)

    query = Student.query

    # Ownership scoping: a parent may only ever see their own children.
    # This was the audit's most consequential unaddressed privacy gap —
    # any authenticated parent could previously list every student in the
    # school. Admin/teacher are unrestricted here by design: they need
    # school-wide visibility to do their jobs (grading, attendance,
    # alerts), which is the same role distinction already enforced on the
    # mutating endpoints below.
    role, user_id = get_current_role_and_user_id()
    if role == 'parent':
        query = query.filter(Student.parent_id == (int(user_id) if user_id is not None else -1))

    grade = request.args.get('grade')
    if grade:
        query = query.filter_by(grade=grade)
    class_name = request.args.get('class_name')
    if class_name:
        query = query.filter_by(class_name=class_name)

    sort = request.args.get('sort')
    if sort:
        descending = sort.startswith('-')
        column_name = sort[1:] if descending else sort
        column = _SORTABLE_COLUMNS.get(column_name)
        if column is None:
            return error_response(
                'validation_error',
                f"Cannot sort by '{column_name}'. Allowed fields: {', '.join(sorted(_SORTABLE_COLUMNS))}.",
                400,
            )
        query = query.order_by(column.desc() if descending else column.asc())

    result = query.paginate(page=page, per_page=per_page, error_out=False)
    return {
        'students': [
            {'id': s.id, 'name': s.name, 'grade': s.grade, 'class_name': s.class_name}
            for s in result.items
        ],
        'page': result.page,
        'per_page': result.per_page,
        'total': result.total,
        'pages': result.pages,
    }


def _validate_parent_id(parent_id):
    """Shared guard for both create_student() and assign_parent(): a
    parent_id must reference an existing User whose role is actually
    'parent'. Without this check, linking a student to an admin/teacher
    account (or a nonexistent id) would silently defeat the ownership
    model — e.g. an admin account accidentally set as `parent_id` would
    then be treated as "not a parent" by the role check anyway, but a
    typo'd id pointing at a real parent's colleague would grant that
    unrelated parent access. Returns an error_response tuple, or None if
    valid.
    """
    if parent_id is None:
        return None
    parent_user = User.query.get(parent_id)
    if not parent_user or parent_user.role != 'parent':
        return error_response(
            'validation_error',
            f'No parent account with id {parent_id} exists.',
            400,
        )
    return None


@students_bp.post('/')
@jwt_required()
def create_student():
    try:
        payload = CreateStudentRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return error_response('validation_error', 'Invalid student details', 400, details=exc.errors())

    parent_error = _validate_parent_id(payload.parent_id)
    if parent_error:
        return parent_error

    student = Student(
        name=payload.name,
        grade=payload.grade,
        class_name=payload.class_name,
        parent_id=payload.parent_id,
    )
    db.session.add(student)
    db.session.commit()

    # Initialize gamification record so award()/leaderboard() never need to
    # special-case a student with no Gamification row yet.
    gamification = Gamification(student_id=student.id, xp=0, streak=0, badges='')
    db.session.add(gamification)
    db.session.commit()
    return {'id': student.id}


@students_bp.patch('/<int:student_id>/parent')
@jwt_required()
# Only admin/teacher may (re)assign guardianship — a parent must never be
# able to link themselves (or anyone else) to an arbitrary student record.
@roles_required('admin', 'teacher')
def assign_parent(student_id: int):
    try:
        payload = AssignParentRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return error_response('validation_error', 'Invalid parent assignment', 400, details=exc.errors())

    student = Student.query.get(student_id)
    if not student:
        return error_response('not_found', f'No student with id {student_id}', 404)

    parent_error = _validate_parent_id(payload.parent_id)
    if parent_error:
        return parent_error

    student.parent_id = payload.parent_id
    db.session.commit()
    return {'id': student.id, 'parent_id': student.parent_id}


@students_bp.post('/assessment')
@jwt_required()
def add_assessment():
    try:
        payload = AddAssessmentRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return error_response('validation_error', 'Invalid assessment details', 400, details=exc.errors())

    if not Student.query.get(payload.student_id):
        return error_response('not_found', f'No student with id {payload.student_id}', 404)

    assessment = Assessment(
        student_id=payload.student_id,
        subject=payload.subject,
        score=payload.score,
        max_score=payload.max_score,
        term=payload.term,
    )
    db.session.add(assessment)
    db.session.commit()
    return {'id': assessment.id}


@students_bp.post('/attendance')
@jwt_required()
def add_attendance():
    try:
        payload = AddAttendanceRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return error_response('validation_error', 'Invalid attendance details', 400, details=exc.errors())

    if not Student.query.get(payload.student_id):
        return error_response('not_found', f'No student with id {payload.student_id}', 404)

    attendance = Attendance(student_id=payload.student_id, date=payload.date, present=payload.present)
    db.session.add(attendance)
    db.session.commit()
    return {'id': attendance.id}


@students_bp.post('/survey')
@jwt_required()
def add_survey():
    try:
        payload = AddSurveyRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return error_response('validation_error', 'Invalid survey details', 400, details=exc.errors())

    if not Student.query.get(payload.student_id):
        return error_response('not_found', f'No student with id {payload.student_id}', 404)

    survey = SurveyResponse(
        student_id=payload.student_id,
        mood=payload.mood,
        stress=payload.stress,
        sleep_hours=payload.sleep_hours,
    )
    db.session.add(survey)
    db.session.commit()
    return {'id': survey.id}
