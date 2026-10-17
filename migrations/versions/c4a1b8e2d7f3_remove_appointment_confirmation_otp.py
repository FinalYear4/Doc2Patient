"""remove appointment confirmation otp

Revision ID: c4a1b8e2d7f3
Revises: 7f2c1d4e8a90
"""

from alembic import op
import sqlalchemy as sa


revision = 'c4a1b8e2d7f3'
down_revision = '7f2c1d4e8a90'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('appointment', schema=None) as batch_op:
        batch_op.drop_column('confirmation_otp_verified_at')
        batch_op.drop_column('confirmation_otp_attempts')
        batch_op.drop_column('confirmation_otp_expires_at')
        batch_op.drop_column('confirmation_otp_hash')


def downgrade():
    with op.batch_alter_table('appointment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('confirmation_otp_hash', sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column('confirmation_otp_expires_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('confirmation_otp_attempts', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('confirmation_otp_verified_at', sa.DateTime(), nullable=True))
