"""add appointment confirmation otp

Revision ID: 7f2c1d4e8a90
Revises: 9a45cc84e44a
"""

from alembic import op
import sqlalchemy as sa


revision = '7f2c1d4e8a90'
down_revision = '9a45cc84e44a'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('appointment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('confirmation_otp_hash', sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column('confirmation_otp_expires_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('confirmation_otp_attempts', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('confirmation_otp_verified_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('appointment', schema=None) as batch_op:
        batch_op.drop_column('confirmation_otp_verified_at')
        batch_op.drop_column('confirmation_otp_attempts')
        batch_op.drop_column('confirmation_otp_expires_at')
        batch_op.drop_column('confirmation_otp_hash')
