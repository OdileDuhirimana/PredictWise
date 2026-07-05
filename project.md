PredictWise — AI-Powered Student Success Intelligence System

PredictWise is a futuristic educational analytics platform that empowers schools to predict academic outcomes, personalize learning, and intervene early to prevent student failure and dropout. Using a combination of machine learning, behavior analytics, and student wellness indicators, PredictWise turns raw school data into actionable insights that help every student thrive.

Designed with the Rwandan education system in mind — but built with global standards of innovation.

## Problem Validation

**The problem.** In Rwandan secondary schools, academic risk — a student sliding toward failing grades, chronic absenteeism, or dropout — is typically noticed only at the end of a term, once report cards or national exam results are already final. By then, the window for a low-cost intervention (a tutoring session, a parent conversation, a wellness check-in) has largely closed. Manual tracking across spreadsheets scales poorly once a school has hundreds of students across multiple grades and subjects.

**Target users**, matching the actual `role` field on every account (`admin | teacher | parent`):
- **Admins** — school leadership who need aggregate visibility (dashboards, benchmarks, drift-monitored models) and who own the highest-stakes actions (retraining the shared prediction model, sending bulk parent alerts).
- **Teachers** — the people closest to day-to-day student data entry (assessments, attendance, wellness surveys) and pedagogical actions (awarding recognition, reviewing risk flags).
- **Parents** — read access to their own children's outcomes and wellness indicators, so they can act on early signals rather than a term-end surprise. A `Student.parent_id` link (nullable, admin/teacher-assigned only) now scopes every parent-facing read endpoint — `list_students`, the wellness indicator, and the gamification leaderboard — to that parent's own linked children; see `docs/adr/0003-parent-ownership-via-nullable-foreign-key.md` for the data-model decision and its deliberately scoped-down limitations (one guardian per student, mutating endpoints not yet ownership-gated).

**Success metrics / KPIs this system is designed to move:**
- Earlier identification of at-risk students (weeks, not a full term, ahead of exam results) via the risk classifier and drift-monitored retraining.
- A measurable reduction in preventable dropout, by surfacing combined academic + attendance + wellness signals a single spreadsheet view would miss.
- Teacher time saved on manual tracking and report generation (PDF annual reports generated on demand instead of compiled by hand).

**Why this approach vs. existing alternatives.** Rwandan secondary schools largely choose between two extremes today: manual spreadsheets (free, but not predictive, not automatically flagged, and error-prone at scale) or expensive commercial Student Information System (SIS) platforms (predictive-ish, but priced and built for well-resourced international schools). PredictWise deliberately sits in between: a lightweight, SQLite-by-default, ML-driven system that a single school can self-host cheaply, while still providing the predictive risk-flagging and drift monitoring that spreadsheets can't.

🚀 Why PredictWise Is a Game-Changer

It doesn’t just analyze past performance — it predicts the future, recommends solutions, supports mental health, and enhances parental involvement.

It’s the ultimate proof that you understand:
✅ AI
✅ Real-world problem-solving
✅ Full-stack development
✅ Ethical & human-centered tech

🔥 Core Capabilities & WOW Features
🎯 1️⃣ Predictive Performance Engine

A Random Forest regressor (scikit-learn), tuned via GridSearchCV, forecasts:

Exam scores

Pass/fail likelihood

Expected academic growth

🚦 2️⃣ Academic Risk Radar

Auto-classifies students:

✅ On-Track

🟡 Needs Attention

🔴 High Risk

🔍 3️⃣ Transparent AI Insights

Real SHAP explainability (`backend/ml/engine.py::explain_shap`) when the `shap` library's TreeExplainer is available, with a feature-importance-based fallback when it isn't — so the "why is this student flagged" answer is never a black box.

🎯 4️⃣ Personalized Learning Paths

Rule-based study plan recommendations (`backend/utils/recommend.py`) driven off risk level, attendance, and average score — tutoring, revision focus areas, attendance follow-up, and daily-practice suggestions.

🎮 5️⃣ Gamified Motivation System

XP points & streak tracking

Achievement badges

Class leaderboard for healthy competition (single joined SQL query — no per-row N+1 lookups; paginated, filterable by minimum XP, sortable; scoped to a parent's own children when viewed by a parent account)

📡 6️⃣ Parent & Teacher Real-Time Alerts

SMS + WhatsApp reminders via Twilio (Twilio's own WhatsApp API, not a separate WhatsApp Business API integration) for:

Low attendance

Deadlines & exams

Behavior concerns

Restricted to admin accounts only — sending alerts to parents has real cost and disruption implications, so it isn't a self-service action for every teacher.

🧠 7️⃣ Mental Health Support Indicator

Uses survey (mood/stress/sleep) + attendance signals to compute a wellness risk indicator, flagging students who may need counselor involvement early — even when their grades still look fine on paper.

🎙 8️⃣ Voice-to-Insight Intelligence

Teachers submit a transcript of spoken notes

VADER sentiment analysis + keyword-based behavior-flag extraction (lateness, absence, conflict, bullying, anxiety, sadness, stress)

🧬 9️⃣ Student “Digital Twin”

A predictive academic projection across "what-if" scenarios (improved attendance, better homework completion), showing a learning-health status and score trajectory — not a full separate simulation engine, but a genuinely useful sensitivity analysis over the same trained model.

🌈 10️⃣ Inclusivity & Accessibility

Kinyarwanda language support (`frontend/src/i18n/rw.json`) alongside English

Accessibility settings context in the frontend (`frontend/src/a11y/SettingsContext.jsx`)

Automated accessibility checks (Lighthouse CI, `frontend/.lighthouserc.json`, wired into `.github/workflows/ci.yml`) — not just configured but actually run against a real headless Chromium during this pass, which found and led to fixing two real WCAG AA color-contrast failures (the primary button's orange-on-white text, in both the default and colorblind-friendly palettes) and a `<select>` missing an accessible label (the language switcher); both pages checked now score a verified 100% Lighthouse accessibility score

📊 11️⃣ School Performance Dashboard

Real aggregate queries, cached for 30 seconds to avoid re-scanning the full assessments table on every dashboard view (see "Challenges & Tradeoffs"), to compare:

Subjects (paginated, filterable by name, sortable by average score/count)

Classes (paginated, filterable by name, sortable by average score/count)

A static national benchmark vs. current school average

Subject × class heatmap

🧾 12️⃣ Intervention Tracking & Annual Reports

On-demand PDF report generation (ReportLab) for PTA and ministry-style reporting needs

🔐 13️⃣ Secure & Ethical AI

JWT authentication (Flask-JWT-Extended), with every authentication/authorization failure — including Flask-JWT-Extended's own 401s — returned in the same standard error envelope

Role-based access control: admin-only model retraining and alert-sending, teacher+admin gamification actions, authenticated-only access to every route that reads real student data, and parent accounts scoped to only their own linked children on every per-student read endpoint

Structured audit logging on every RBAC denial and every successful admin-gated action, tagged with a per-request correlation ID also threaded through application logs and Sentry

Pydantic-validated request bodies (extended to every mutating/prediction endpoint, including the ML feature-input routes) with a consistent structured error envelope across the API, and the same domain bounds (score/max_score/mood/stress ranges) also enforced as database-level CHECK constraints, not only at the API boundary

🔄 14️⃣ Continual Learning & Model Drift Detection

`backend/ml/engine.py::compute_psi` computes a genuine Population Stability Index per feature against a saved training-time baseline — this is real, working drift detection, not a placeholder. Retraining is a manual admin action either way; when `REDIS_URL` is configured it now runs as a background RQ job (`POST /ml/train` returns `202` with a `job_id` immediately, polled via `GET /ml/train/status/<job_id>`) instead of blocking the request thread, falling back to the original synchronous behavior with zero configuration required (see `backend/jobs/`).

🔍 15️⃣ Structured Audit Logging & Correlation IDs

Every `roles_required`-gated denial and every successful admin action (model training, sending an alert, awarding XP) emits a structured JSON audit event (`backend/utils/audit.py`) tagged with the caller's user id, role, and endpoint. A per-request correlation ID (`X-Request-ID`, generated or propagated from an inbound header) is threaded through every structured log line, every audit event, and Sentry (when configured) via `backend/utils/request_id.py`, so a single request's full trail — application logs, audit trail, and error report — can be reconstructed from one ID.

🧩 16️⃣ Service Layer for Core Business Rules

Risk-tier classification (`services/risk_service.py`), gamification XP/streak/badge math (`services/gamification_service.py`), and ML feature-engineering (`services/ml_feature_service.py`) are extracted into pure functions with zero Flask/database dependency, each with a dedicated unit-test file that runs without a Flask app, a database, or an HTTP client. This also fixed a real duplicate-logic bug: `ml.py::train()` and `ml.py::drift()` previously each independently rebuilt the same assessment/attendance feature transform.

🛠️ Tech Stack
Layer	Technology
ML	Scikit-learn (RandomForestRegressor + GridSearchCV), SHAP (with graceful fallback)
Backend	Flask REST API + Docker, Flask-JWT-Extended, Flask-Migrate/Alembic, pydantic
Database	SQLite (default/dev) or PostgreSQL via SQLAlchemy (`DATABASE_URL`, see `docker-compose.yml`)
Background jobs / caching / rate limiting	RQ + Redis (optional, via `REDIS_URL` — background ML training, Redis-backed rate limiting, response caching for analytics endpoints; all fall back to synchronous/in-memory behavior with zero configuration)
Frontend	React (Vite), Chart.js, Lighthouse CI (accessibility gate in CI)
Alerts	Twilio (SMS + WhatsApp via Twilio's WhatsApp API)
Observability	Sentry (optional, via `SENTRY_DSN`), Prometheus metrics, structured JSON logging with per-request correlation IDs, structured audit logging for RBAC/admin actions
Deployment	Render (`render.yaml`, deploys gated on CI success — see `.github/workflows/ci.yml`) or Docker Compose (Postgres + backend)

## Screenshots

Captured against a real `flask db upgrade` + seeded backend and a production frontend build, logged in as the seeded admin account (see `docs/ARCHITECTURE.md` for exactly how, and for four real bugs this surfaced and fixed):

| Login | Dashboard |
|---|---|
| `docs/screenshots/login.png` | `docs/screenshots/dashboard.png` |

| Students | Leaderboard |
|---|---|
| `docs/screenshots/students.png` | `docs/screenshots/leaderboard.png` |

No live hosted URL or demo video is linked here — no hosting account was available while making this pass's changes (see "Future Work").

## Architecture

An entity-relationship diagram, a request-flow diagram, and a layering diagram (with an honest marker of exactly where the current architecture stops short of a full service/domain split) live in `docs/ARCHITECTURE.md`. Specific architectural decisions — SQLite-vs-Postgres, the Redis-optional rate-limiting/caching/background-job design, and the parent-ownership data model — are documented as individual ADRs in `docs/adr/`.

## Local Setup

**Backend (Flask API):**
1. `cd backend && cp .env.example .env` — fill in `JWT_SECRET_KEY` at minimum for anything beyond local dev (a random one is auto-generated in non-production mode if omitted).
2. Create a virtualenv and `pip install -r requirements.txt`.
3. Apply the database schema with real migrations: `FLASK_APP=backend.app:create_app flask db upgrade` (run from the repo root — the migration history lives in `backend/migrations/`).
4. Optionally seed realistic demo data: `python -m backend.seed` (creates an admin account, teacher/parent accounts, and several hundred students with assessments, attendance, and survey history).
5. Run the dev server: `python -m backend.app` (or `flask run`), or use `start.sh` / `backend/entrypoint.sh` to mirror how the Docker/Render deployment boots (both now run `flask db upgrade` before falling back to `db.create_all()` if no migrations exist yet).

**Full stack via Docker Compose** (Postgres + backend): `docker compose up --build` from the repo root, using `docker-compose.yml`. Provide `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`, and `JWT_SECRET_KEY` via environment or an `.env` file at the repo root.

**Frontend:** `cd frontend && npm install && npm run dev` (Vite dev server; `VITE_API_BASE` defaults to `/api/v1`).

**Optional — Redis-backed background jobs / rate limiting / caching:** set `REDIS_URL` (e.g. `redis://localhost:6379/0`) to enable background ML training, Redis-backed rate limiting, and response caching for the analytics dashboard. Unset by default, so none of this is required to run the app — see `docs/adr/0002-in-memory-rate-limiting-with-optional-redis.md`. Run a worker with `rq worker ml-training` (pointed at the same `REDIS_URL`) to actually process enqueued training jobs.

**Environment variables reference** (all in `backend/.env.example`): `DATABASE_URL`, `JWT_SECRET_KEY`, and `CORS_ALLOWED_ORIGINS` are required in production (the app fails closed at startup if any is missing — see `backend/app.py::create_app`); `REDIS_URL`, `SENTRY_DSN`, and the `TWILIO_*` variables are all optional integrations that cleanly no-op when unset.

## Challenges & Tradeoffs

- **SQLite by default vs. Postgres in production.** Local dev and the default Render deployment (`render.yaml`) use SQLite for zero-setup simplicity; `docker-compose.yml` provisions a real Postgres instance for anything resembling a production load. SQLAlchemy abstracts the difference, but SQLite's single-writer model is a real limitation if this ever needed concurrent write-heavy usage. See `docs/adr/0001-sqlite-by-default-postgres-in-production.md`.
- **In-memory rate limiting/caching by default, Redis-backed when configured.** Flask-Limiter and Flask-Caching both default to in-memory backends (fine for a single-process demo, and Flask-Limiter itself warns about this at startup) but switch to Redis-backed storage automatically when `REDIS_URL` is set — correct behavior across multiple gunicorn workers, surviving restarts. Without `REDIS_URL`, this project's own `.env.example` (`GUNICORN_WORKERS=2`) is a known-inconsistent production configuration; this is now an operator choice rather than a hard-coded limitation. See `docs/adr/0002-in-memory-rate-limiting-with-optional-redis.md`. The Redis-backed *rate-limiting* path specifically was validated at the "app doesn't crash with an unreachable Redis URL" and "correct kwargs selected" level, not against a live Redis server (none is available in this environment) — the RQ background-job path below was validated more thoroughly using `fakeredis`.
- **Synchronous ML training by default, background RQ job when Redis is configured.** `/api/v1/ml/train` runs `GridSearchCV` inline in the request/response cycle unless `REDIS_URL` is set, in which case it enqueues onto an RQ queue and returns `202` immediately, pollable via `/ml/train/status/<job_id>`. The queueing/status-polling plumbing is tested end-to-end with `fakeredis` + `rq.SimpleWorker` (`test_ml_train_background.py`); what those tests deliberately do *not* claim to verify is a live multi-process deployment where the RQ worker and the web process share the same real database — that's a standard assumption for any such deployment, but not something a single-process test suite can exercise.
- **Response caching trades a small amount of staleness for fewer full-table scans.** `routes/analytics.py`'s dashboard/subjects/classes/heatmap/benchmarks endpoints are cached for 30 seconds (`backend/cache.py`). This is TTL-based, not exact invalidation — adding a new assessment won't be reflected in the dashboard for up to 30 seconds. Deliberately simple for the current read-heavy, write-light usage pattern; an exact-invalidation approach (e.g. tagging cache entries by the mutating routes that would invalidate them) is a reasonable follow-up if staleness ever becomes a real complaint rather than a documented tradeoff.
- **This pass (round 2), honestly.** A second internal-audit-response pass fixed: the CORS wildcard default that survived the first pass's remediation (now fails closed in production, exactly like `JWT_SECRET_KEY`/`DATABASE_URL`); the dead `utils/shap_utils.py`; missing DB-level indexes and check constraints (now enforced at the schema layer, not just by pydantic at the API boundary); unvalidated `digital_twin.py`/`voice.py`/`ml.py::do_predict` request bodies (`digital_twin.py` specifically 500'd on non-numeric input before this); the "any parent can read any student's data" privacy gap (`docs/adr/0003`); an open-redirect inconsistency between `Login.jsx` and `Register.jsx`; a Twilio-failure branch that leaked raw exception text to the client; and — found only by writing a broad contract test rather than being specifically flagged beforehand — Flask-JWT-Extended's own 401 responses had never been wired into the project's own standard error envelope, meaning the single most common error shape returned by the entire API (every route requires a JWT) was actually `{"msg": "..."}`, not `{"error": {"code", "message"}}`. That last one is called out specifically because it's a good example of why contract-level tests catch things route-level tests don't.

## Lessons Learned

- `jwt_required(optional=True)` is an easy way to accidentally ship an unauthenticated read endpoint for real user data — it "worked" in manual testing because the happy path was always tested with a token attached, and nothing failed loudly when the token was omitted.
- Manual `request.get_json().get(...)` field access silently produces `None` for missing fields (which corrupts stored data) or raises an unhandled `KeyError` (which becomes an opaque 500) — a schema-validation layer catching this at the boundary is worth the small amount of boilerplate per route.
- An N+1 query pattern (`Student.query.get(...)` inside a loop) is invisible in a demo with a handful of students and only becomes an obvious problem at a scale this project's own seed script (`SEED_STUDENTS=300` by default) was already large enough to expose.
- A "fix" that changes documentation but not the code path it describes is worse than no fix at all: the CORS wildcard default was flagged once, "fixed" in `.env.example` only, and shipped again — a second audit pass caught it specifically because it re-verified the actual code path (`app.py`) rather than trusting the diff's own narrative. The lesson generalized into this pass: prefer a *failing test* over a comment/doc claiming a fix, wherever a test is feasible (see `test_app_config.py::TestCorsProductionGuard`).
- Testing each route's error responses in isolation missed a cross-cutting gap: nothing asserted that *every* 401 across the API used the same envelope shape, so Flask-JWT-Extended's own default error handlers (never touched by any per-route error-envelope work) went unnoticed for two full audit passes. A small, deliberately broad contract test (`test_error_envelope_contract.py`) surfaced this in minutes once written.

## Future Work

Explicitly out of scope for this pass, listed here as a roadmap rather than as something already built:

- **Multi-guardian support.** `Student.parent_id` supports exactly one linked guardian per student today; a real school may have two parent accounts (or a parent + legal guardian) needing independent access to the same student. See `docs/adr/0003` for the many-to-many join-table alternative considered and deferred.
- **Ownership-gating on mutating endpoints.** Parent-role ownership scoping was applied to *read* endpoints only (`list_students`, the wellness indicator, the leaderboard) — a parent account can still technically create a student record or add an assessment/attendance/survey row for an arbitrary `student_id`, since that gap is about write permissions rather than the read-privacy gap this pass specifically targeted.
- **A full layered rewrite of `ml/engine.py`.** This pass extracted three real, unit-tested service modules (`services/risk_service.py`, `services/gamification_service.py`, `services/ml_feature_service.py`) but did not restructure `ml/engine.py` itself, which still mixes training, persistence, heuristic fallback, and drift computation in one module — see `docs/ARCHITECTURE.md`'s layering diagram for exactly where this stops today.
- **Exact cache invalidation** instead of the current 30-second TTL on analytics endpoints, if staleness ever becomes a real operational complaint.
- **AI teaching-assistant chatbot** and **automated bias-monitoring pipeline** — both were listed as capabilities in an earlier draft of this document but do not exist in the codebase today. They remain plausible future directions (a natural-language query layer over the existing analytics endpoints; a fairness-metric dashboard comparing prediction outcomes across demographic groups) but are not implemented, and are listed here instead of being described as current features.
- **Excel/CSV bulk import** and **biometric attendance device integration** — the current data-entry path is the REST API / frontend forms only; bulk import and hardware-integration were aspirational and are not implemented.
- **A live deployment and a demo video.** No hosting account or public network access was available while making this pass's changes, so there is no live URL or demo video to link here. Screenshots, however, *were* captured for real (`docs/screenshots/`) — see `docs/ARCHITECTURE.md` for exactly how, and for four genuine bugs that capturing them for real (rather than skipping the section) surfaced and fixed. The CI workflow's `deploy` job (`.github/workflows/ci.yml`) is wired to gate a Render deployment on tests passing, but has not itself been exercised against a real Render service/secret from within this pass.

🎯 Impact

PredictWise enables schools to:
✅ Prevent dropout early
✅ Improve pass rates and national exam performance
✅ Support both academic + emotional well-being
✅ Strengthen teacher-parent collaboration

It’s not just a system —
it’s a step toward more data-informed, human-centered education in Rwanda. 🇷🇼✨
