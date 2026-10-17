"""add structured consultation findings

Revision ID: d8e4f1a2b7c6
Revises: c4a1b8e2d7f3
"""

from alembic import op
import sqlalchemy as sa


revision = 'd8e4f1a2b7c6'
down_revision = 'c4a1b8e2d7f3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('appointment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('clinical_findings', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('care_plan', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('completed_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('appointment', schema=None) as batch_op:
        batch_op.drop_column('completed_at')
        batch_op.drop_column('care_plan')
        batch_op.drop_column('clinical_findings')
