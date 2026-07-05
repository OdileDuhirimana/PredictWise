"""The ML training job body, runnable either inline (synchronous fallback)
or inside an RQ worker process (background job).

Why a standalone function rather than reusing routes/ml.py::train()
directly: when RQ executes this in a worker process, there is no active
Flask request/app context (a worker process never received an HTTP
request) — it has to build its own. `run_training_job()` is therefore
self-contained: it creates its own Flask app + app context, does the DB
reads, and returns a plain JSON-serializable dict (RQ persists the return
value as the job's `.result`). The synchronous path in routes/ml.py calls
the same underlying `services.ml_feature_service` transform directly
inside the *existing* request's app context instead of going through this
function, to avoid the overhead/complexity of spinning up a second Flask
app on every synchronous training request — see routes/ml.py::train() for
that path.

Production note: the RQ worker process and the web process must point at
the same DATABASE_URL (a real shared Postgres, or a shared file — never
each process's own `:memory:` SQLite) for this to see the same data the
web process does. This is standard practice for any multi-process
deployment and is not something this module can verify at runtime; the
accompanying test suite verifies the queueing/status-polling plumbing
using a shared temp-file SQLite database rather than a live multi-process
deployment.
"""
from __future__ import annotations


def run_training_job() -> dict:
    """Entry point invoked by the RQ worker. Must remain importable and
    callable with no arguments and no ambient Flask/app context, since
    that's exactly the environment an RQ worker calls it in.
    """
    # Deferred imports: this module must be importable (for RQ to look up
    # `backend.jobs.training_job.run_training_job` by dotted path) without
    # requiring an app context to already exist.
    from ..app import create_app
    from ..database import db
    from ..models import Assessment, Attendance
    from ..ml.engine import train_regressor
    from ..services.ml_feature_service import build_feature_dataframe

    app = create_app()
    with app.app_context():
        # Defensive, idempotent schema guard — mirrors the same fallback
        # already used in start.sh/backend/app.py's __main__ block. A real
        # deployment's worker process points DATABASE_URL at the same
        # already-migrated database the web process uses, so this is
        # normally a no-op. But this function builds its own independent
        # engine/connection (see module docstring), and against a SQLite
        # `:memory:` DATABASE_URL specifically, that connection starts with
        # *no* schema at all — `Assessment.query.all()` would raise
        # `OperationalError: no such table: assessment` instead of cleanly
        # returning `[]`. Confirmed via the accompanying test suite: once
        # tests/conftest.py's `app` fixture was fixed to give each test a
        # genuinely isolated `:memory:` database (see that fixture's own
        # docstring), this job's separate `:memory:` connection had no
        # tables, and the "no assessment data" result this test asserts on
        # requires an existing-but-empty table, not a missing one.
        db.create_all()
        assessments = Assessment.query.all()
        if not assessments:
            return {"error": "no assessment data"}

        attendance = Attendance.query.all()
        df = build_feature_dataframe(
            [{"student_id": a.student_id, "score": a.score} for a in assessments],
            [{"student_id": x.student_id, "present": 1 if x.present else 0} for x in attendance],
        )
        y = df["avg_score"]
        X = df[["avg_score", "attendance_rate", "homework_completion", "behavior_incidents"]]
        cv_score = train_regressor(X, y)
        db.session.remove()
        return {"cv_score": cv_score}
