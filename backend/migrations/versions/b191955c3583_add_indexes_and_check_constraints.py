"""Add indexes and check constraints

Revision ID: b191955c3583
Revises: 1077e9ff1d62
Create Date: 2026-07-04 00:00:00.000000

Why hand-written rather than `flask db migrate --autogenerate`: Alembic's
autogenerate does not reliably diff CheckConstraint additions across all
supported backends, so this migration is written directly against the
models.py changes it corresponds to (index=True on every student_id
foreign key, plus CheckConstraints on Assessment.score/max_score and
SurveyResponse.mood/stress). `op.batch_alter_table` is used throughout
(rather than direct `op.create_index`/`op.create_check_constraint`) so the
same migration file works unmodified on both SQLite (which cannot ALTER a
table in place to add a CHECK constraint and requires Alembic's
"recreate the table" batch strategy) and Postgres in production, where
batch mode transparently degrades to plain ALTER statements. See
backend/migrations/env.py for the render_as_batch wiring this depends on.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b191955c3583'
down_revision = '1077e9ff1d62'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('assessment', schema=None) as batch_op:
        batch_op.create_index('ix_assessment_student_id', ['student_id'])
        batch_op.create_check_constraint('ck_assessment_score_non_negative', 'score >= 0')
        batch_op.create_check_constraint('ck_assessment_max_score_positive', 'max_score > 0')

    with op.batch_alter_table('attendance', schema=None) as batch_op:
        batch_op.create_index('ix_attendance_student_id', ['student_id'])

    with op.batch_alter_table('gamification', schema=None) as batch_op:
        batch_op.create_index('ix_gamification_student_id', ['student_id'])

    with op.batch_alter_table('survey_response', schema=None) as batch_op:
        batch_op.create_index('ix_survey_response_student_id', ['student_id'])
        batch_op.create_check_constraint('ck_survey_response_mood_range', 'mood >= 1 AND mood <= 10')
        batch_op.create_check_constraint('ck_survey_response_stress_range', 'stress >= 1 AND stress <= 10')


def downgrade():
    with op.batch_alter_table('survey_response', schema=None) as batch_op:
        batch_op.drop_constraint('ck_survey_response_stress_range', type_='check')
        batch_op.drop_constraint('ck_survey_response_mood_range', type_='check')
        batch_op.drop_index('ix_survey_response_student_id')

    with op.batch_alter_table('gamification', schema=None) as batch_op:
        batch_op.drop_index('ix_gamification_student_id')

    with op.batch_alter_table('attendance', schema=None) as batch_op:
        batch_op.drop_index('ix_attendance_student_id')

    with op.batch_alter_table('assessment', schema=None) as batch_op:
        batch_op.drop_constraint('ck_assessment_max_score_positive', type_='check')
        batch_op.drop_constraint('ck_assessment_score_non_negative', type_='check')
        batch_op.drop_index('ix_assessment_student_id')
