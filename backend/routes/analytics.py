from math import ceil

from flask import Blueprint, request, send_file
from flask_jwt_extended import jwt_required
from io import BytesIO
from reportlab.pdfgen import canvas
from ..cache import ANALYTICS_CACHE_TIMEOUT_SECONDS, cache
from ..database import db
from ..models import Assessment, Student
from ..utils.errors import error_response

analytics_bp = Blueprint('analytics', __name__)

_DEFAULT_PER_PAGE = 20
_MAX_PER_PAGE = 100


def _parse_pagination(args):
    page = args.get('page', default=1, type=int) or 1
    per_page = args.get('per_page', default=_DEFAULT_PER_PAGE, type=int) or _DEFAULT_PER_PAGE
    return max(page, 1), min(max(per_page, 1), _MAX_PER_PAGE)


def _paginate_rows(rows, page, per_page):
    total = len(rows)
    start = (page - 1) * per_page
    page_rows = rows[start:start + per_page]
    return page_rows, total, (ceil(total / per_page) if per_page else 0)


# IMPORTANT — cache-key safety: `@cache.cached(...)` keys purely on the
# request path + query string, NOT on the caller's identity or role. That
# is only safe because every cached endpoint below returns the same
# school-wide aggregate data to every authenticated caller regardless of
# role (unlike routes/students.py or routes/gamification.py::leaderboard,
# which are parent-ownership-scoped and must never be cached this way
# without also namespacing the cache key by user id). `@cache.cached()`
# is placed *below* `@jwt_required()` on every route specifically so an
# unauthenticated request is rejected by JWT verification before it can
# ever reach (or poison) the cache.
@analytics_bp.get('/dashboard')
@jwt_required()
@cache.cached(timeout=ANALYTICS_CACHE_TIMEOUT_SECONDS)
def dashboard():
    # Not paginated: this returns two scalar summary metrics, not a list —
    # pagination has no meaning here. Same reasoning applies to
    # report_pdf()/heatmap()/benchmarks() below (a single PDF, a bounded
    # matrix, and two scalars respectively). subjects()/classes() below
    # *are* row-shaped and paginated/filtered/sorted, matching the pattern
    # in routes/students.py::list_students.
    total_students = Student.query.count()
    assessments = Assessment.query.all()
    avg_score = round(sum(a.score for a in assessments)/len(assessments), 2) if assessments else 0
    return {'total_students': total_students, 'avg_score': avg_score}


@analytics_bp.get('/report.pdf')
@jwt_required()
def report_pdf():
    buf = BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 800, 'PredictWise Annual Report')
    c.drawString(100, 780, f'Total Students: {Student.query.count()}')
    assessments = Assessment.query.all()
    avg_score = round(sum(a.score for a in assessments)/len(assessments), 2) if assessments else 0
    c.drawString(100, 760, f'Average Score: {avg_score}')
    c.showPage(); c.save()
    buf.seek(0)
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name='annual_report.pdf')


_SUBJECT_SORTABLE = {'subject', 'avg_score', 'count'}
_CLASS_SORTABLE = {'class_name', 'avg_score', 'count'}


def _apply_sort(data, sort_param, sortable_keys):
    """Sorts an already-materialized list of row dicts in place-equivalent
    fashion. Sorting in Python (rather than in SQL via `order_by` on the
    aggregate expression) after the GROUP BY is deliberate: aggregate
    columns here are computed (AVG/COUNT), and re-deriving a `order_by`-
    compatible labeled column reference across both SQLite and Postgres
    added real complexity for a result set whose cardinality is bounded by
    "number of distinct subjects/classes" (a handful, for any real school),
    not by row count in the underlying assessment table.

    Returns None on success (sorts `data` in place via Python's stable
    sort), or an error_response tuple if `sort_param` names a disallowed
    column.
    """
    if not sort_param:
        return None
    descending = sort_param.startswith('-')
    key = sort_param[1:] if descending else sort_param
    if key not in sortable_keys:
        return error_response(
            'validation_error',
            f"Cannot sort by '{key}'. Allowed fields: {', '.join(sorted(sortable_keys))}.",
            400,
        )
    data.sort(key=lambda row: (row[key] is None, row[key]), reverse=descending)
    return None


@analytics_bp.get('/subjects')
@jwt_required()
@cache.cached(timeout=ANALYTICS_CACHE_TIMEOUT_SECONDS, query_string=True)
def subjects():
    # Average score per subject. Cardinality here is bounded by the number
    # of distinct subjects taught (a handful for any real school), so
    # pagination is applied in Python after fetching the full grouped
    # result rather than via SQL OFFSET/LIMIT — see _apply_sort's docstring
    # for why the same reasoning extends to sorting.
    query = db.session.query(Assessment.subject, db.func.avg(Assessment.score), db.func.count(Assessment.id))

    subject_filter = request.args.get('subject')
    if subject_filter:
        query = query.filter(Assessment.subject.ilike(f'%{subject_filter}%'))

    rows = query.group_by(Assessment.subject).all()
    data = [{'subject': r[0], 'avg_score': float(r[1] or 0), 'count': int(r[2] or 0)} for r in rows]

    sort_error = _apply_sort(data, request.args.get('sort'), _SUBJECT_SORTABLE)
    if sort_error:
        return sort_error

    page, per_page = _parse_pagination(request.args)
    page_data, total, pages = _paginate_rows(data, page, per_page)
    return {'subjects': page_data, 'page': page, 'per_page': per_page, 'total': total, 'pages': pages}


@analytics_bp.get('/classes')
@jwt_required()
@cache.cached(timeout=ANALYTICS_CACHE_TIMEOUT_SECONDS, query_string=True)
def classes():
    # Average score per class_name by joining Student. Same bounded-
    # cardinality reasoning as subjects() above applies to pagination/sort.
    query = (
        db.session.query(Student.class_name, db.func.avg(Assessment.score), db.func.count(Assessment.id))
        .join(Assessment, Assessment.student_id == Student.id)
    )

    class_filter = request.args.get('class_name')
    if class_filter:
        query = query.filter(Student.class_name.ilike(f'%{class_filter}%'))

    rows = query.group_by(Student.class_name).all()
    data = [{'class_name': (r[0] or 'Unknown'), 'avg_score': float(r[1] or 0), 'count': int(r[2] or 0)} for r in rows]

    sort_error = _apply_sort(data, request.args.get('sort'), _CLASS_SORTABLE)
    if sort_error:
        return sort_error

    page, per_page = _parse_pagination(request.args)
    page_data, total, pages = _paginate_rows(data, page, per_page)
    return {'classes': page_data, 'page': page, 'per_page': per_page, 'total': total, 'pages': pages}


@analytics_bp.get('/heatmap')
@jwt_required()
@cache.cached(timeout=ANALYTICS_CACHE_TIMEOUT_SECONDS)
def heatmap():
    # Build subject x class_name matrix of average scores
    rows = db.session.query(Assessment.subject, Student.class_name, db.func.avg(Assessment.score))\
        .join(Student, Student.id == Assessment.student_id)\
        .group_by(Assessment.subject, Student.class_name).all()
    subjects = sorted({r[0] for r in rows})
    classes = sorted({(r[1] or 'Unknown') for r in rows})
    # Initialize matrix with None
    matrix = [[None for _ in classes] for _ in subjects]
    index_s = {s:i for i,s in enumerate(subjects)}
    index_c = {c:i for i,c in enumerate(classes)}
    for s, c, avg in rows:
        i = index_s[s]
        j = index_c[(c or 'Unknown')]
        matrix[i][j] = float(avg or 0)
    return {'subjects': subjects, 'classes': classes, 'matrix': matrix}


@analytics_bp.get('/benchmarks')
@jwt_required()
@cache.cached(timeout=ANALYTICS_CACHE_TIMEOUT_SECONDS)
def benchmarks():
    # Simple static national benchmark; could be stored/configured elsewhere
    # Also include overall current average for comparison
    assessments = Assessment.query.all()
    current_avg = round(sum(a.score for a in assessments)/len(assessments), 2) if assessments else 0
    return {'national_avg': 65.0, 'current_avg': current_avg}

