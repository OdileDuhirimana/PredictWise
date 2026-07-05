"""Add student.parent_id guardian relationship

Revision ID: 960de6e73166
Revises: b191955c3583
Create Date: 2026-07-04 00:10:00.000000

Why: the audit's most reputationally consequential finding was that any
authenticated parent could read every student's data — there was no
concept of "this student belongs to this guardian" anywhere in the schema.
This migration adds a nullable, indexed foreign key from student to the
owning parent's user row. Nullable because a student may be enrolled
before any guardian account exists; NULL is treated as "no parent may read
this record yet" by the application-layer ownership checks (fail-secure),
not "any parent may."
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '960de6e73166'
down_revision = 'b191955c3583'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('student', schema=None) as batch_op:
        batch_op.add_column(sa.Column('parent_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_student_parent_id', ['parent_id'])
        batch_op.create_foreign_key('fk_student_parent_id_user', 'user', ['parent_id'], ['id'])


def downgrade():
    with op.batch_alter_table('student', schema=None) as batch_op:
        batch_op.drop_constraint('fk_student_parent_id_user', type_='foreignkey')
        batch_op.drop_index('ix_student_parent_id')
        batch_op.drop_column('parent_id')
