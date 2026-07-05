from math import ceil

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from pydantic import ValidationError

from ..database import db
from ..models import Gamification, Student
from ..schemas import AwardRequest
from ..services.gamification_service import apply_award
from ..utils.auth import get_current_role_and_user_id, roles_required
from ..utils.errors import error_response

gamify_bp = Blueprint('gamify', __name__)

_SORTABLE_COLUMNS = {
    'xp': Gamification.xp,
    'streak': Gamification.streak,
}
_DEFAULT_PER_PAGE = 20
_MAX_PER_PAGE = 100


@gamify_bp.post('/award')
@jwt_required()
# Awarding XP/badges is a pedagogical action performed by whoever works
# directly with the student day-to-day — teachers and admins — but not
# parents, who should only view outcomes (see leaderboard below).
@roles_required('admin', 'teacher')
def award():
    try:
        payload = AwardRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return error_response('validation_error', 'Invalid award details', 400, details=exc.errors())

    if not Student.query.get(payload.student_id):
        return error_response('not_found', f'No student with id {payload.student_id}', 404)

    gamification = Gamification.query.filter_by(student_id=payload.student_id).first()
    if not gamification:
        gamification = Gamification(student_id=payload.student_id, xp=0, streak=0, badges='')
        db.session.add(gamification)

    apply_award(gamification, payload.xp, payload.badge)
    db.session.commit()

    return {
        'student_id': payload.student_id,
        'xp': gamification.xp,
        'streak': gamification.streak,
        'badges': gamification.badges.split(',') if gamification.badges else [],
    }


@gamify_bp.get('/leaderboard')
@jwt_required()
def leaderboard():
    # Single left-joined query instead of the previous N+1 (one
    # Student.query.get() per leaderboard row). LEFT OUTER JOIN preserves
    # the original behavior of still showing a row (name 'Unknown') for a
    # Gamification record whose Student was deleted, rather than silently
    # dropping it as an INNER JOIN would.
    query = db.session.query(Gamification, Student).outerjoin(Student, Student.id == Gamification.student_id)

    # Ownership scoping: a parent sees only their own children's standings,
    # never the whole school's — the leaderboard exposes names alongside
    # XP, which is exactly the per-student data the audit's privacy
    # finding was about. Admin/teacher remain unrestricted (school-wide
    # visibility is required for their role).
    role, user_id = get_current_role_and_user_id()
    if role == 'parent':
        query = query.filter(Student.parent_id == (int(user_id) if user_id is not None else -1))

    min_xp = request.args.get('min_xp', type=int)
    if min_xp is not None:
        query = query.filter(Gamification.xp >= min_xp)

    page = request.args.get('page', default=1, type=int) or 1
    per_page = request.args.get('per_page', default=_DEFAULT_PER_PAGE, type=int) or _DEFAULT_PER_PAGE
    page = max(page, 1)
    per_page = min(max(per_page, 1), _MAX_PER_PAGE)

    # Default sort preserves the pre-pagination behavior (highest XP
    # first); '-xp'/'streak'/'-streak' etc. are opt-in via an allow-list to
    # prevent arbitrary attribute-injection sorting, matching the pattern
    # already established in routes/students.py::list_students.
    sort = request.args.get('sort', default='-xp')
    descending = sort.startswith('-')
    sort_key = sort[1:] if descending else sort
    column = _SORTABLE_COLUMNS.get(sort_key)
    if column is None:
        return error_response(
            'validation_error',
            f"Cannot sort by '{sort_key}'. Allowed fields: {', '.join(sorted(_SORTABLE_COLUMNS))}.",
            400,
        )
    query = query.order_by(column.desc() if descending else column.asc())

    total = query.count()
    rows = query.offset((page - 1) * per_page).limit(per_page).all()

    leaderboard_rows = [
        {
            'student_id': gamification.student_id,
            'name': student.name if student else 'Unknown',
            'xp': gamification.xp,
            'streak': gamification.streak,
        }
        for gamification, student in rows
    ]
    return {
        'leaderboard': leaderboard_rows,
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': ceil(total / per_page) if per_page else 0,
    }
