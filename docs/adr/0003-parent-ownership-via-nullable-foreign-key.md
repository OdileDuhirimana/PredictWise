# ADR 0003: Parent/guardian ownership via a nullable Student.parent_id

## Status

Accepted

## Context

An internal audit found the most reputationally consequential gap in the
project: any authenticated `parent`-role account could read every
student's data (list, wellness indicators, leaderboard) — there was no
concept anywhere in the schema of "this student belongs to this
guardian." This needed a data-model change, not just a route-level fix,
since the ownership relationship has to be persisted somewhere to be
enforced consistently across multiple read endpoints.

Options considered:
1. **A many-to-many `student_guardian` join table**, allowing multiple
   guardians per student (common in reality — a student can have two
   parents, or a parent + a legal guardian, each wanting their own
   account).
2. **A single nullable `Student.parent_id` foreign key to `user.id`**, one
   guardian per student.
3. **A `Family`/`Household` grouping entity**, with students and parent
   users both belonging to a household.

## Decision

Option 2 — a single nullable `Student.parent_id` — was chosen for this
pass.

Rationale: the audit's finding and the available time both pointed at
closing the *binary* gap ("any parent reads any student" →
"a parent reads only students who are actually theirs") rather than
building out a fully general multi-guardian household model. A nullable
FK is the minimum schema change that makes ownership representable and
enforceable at all, and it does not foreclose migrating to option 1 later
— a follow-up migration could add a join table and backfill it from the
existing `parent_id` column without any data loss, since every existing
`parent_id` value maps to exactly one row in the future join table.

`parent_id` is nullable specifically because a student may be enrolled
before any guardian account exists in the system; `NULL` is treated as
"no parent may read this record yet" (fail-secure) rather than "any
parent may," enforced identically across `routes/students.py::list_students`,
`routes/wellness.py::indicator`, and `routes/gamification.py::leaderboard`.

Only `admin`/`teacher` roles may set or change `parent_id`
(`PATCH /students/<id>/parent`), and the assigned user must actually have
the `parent` role (`_validate_parent_id` in `routes/students.py`) — a
parent can never self-assign guardianship of an arbitrary student.

## Consequences

**Positive:**
- Closes the specific, named privacy gap with a minimal, reviewable schema
  change (one migration: `960de6e73166_add_student_parent_id.py`).
- Ownership enforcement is centralized in one helper
  (`utils/auth.py::get_current_role_and_user_id`) and applied consistently
  across every read endpoint that exposes per-student data.
- A parent probing an arbitrary `student_id` they don't own gets the same
  404 as a nonexistent ID (`routes/wellness.py::indicator`), preventing ID
  enumeration via a 403-vs-404 side channel.

**Negative / accepted tradeoffs:**
- Only one guardian per student is representable today. A school where a
  student has two separate parent accounts, each needing independent
  access, is not yet supported — this is the concrete case option 1 would
  have covered. Documented here as the natural next step rather than
  silently limiting the feature.
- Mutating endpoints (`add_assessment`/`add_attendance`/`add_survey`,
  `create_student`) were deliberately **not** gated by parent ownership in
  this pass — the audit's finding and this pass's scope were specifically
  about *reading* other students' data. A parent today can still create a
  student record or add an assessment for an arbitrary `student_id` if
  they have a `parent` JWT at all; restricting parents from these
  mutating actions entirely (or scoping mutations to owned students) is
  flagged as a follow-up in `project.md`'s "Future Work", not implemented
  here, to avoid conflating a privacy-of-reads fix with a broader
  write-permission redesign in the same change.
