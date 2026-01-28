"""add rate columns to professions table

Revision ID: 3a289981bde5
Revises: q9r1s3t5u7v9
Create Date: 2026-01-28 22:10:17.738064

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3a289981bde5'
down_revision = 'q9r1s3t5u7v9'
branch_labels = None
depends_on = None


def upgrade():
    # Add rate columns to professions table
    with op.batch_alter_table('professions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('show_rate', sa.Numeric(precision=10, scale=2), nullable=True))
        batch_op.add_column(sa.Column('daily_rate', sa.Numeric(precision=10, scale=2), nullable=True))
        batch_op.add_column(sa.Column('weekly_rate', sa.Numeric(precision=10, scale=2), nullable=True))
        batch_op.add_column(sa.Column('per_diem', sa.Numeric(precision=10, scale=2), nullable=True))
        batch_op.add_column(sa.Column('default_frequency', sa.String(length=20), nullable=True))


def downgrade():
    with op.batch_alter_table('professions', schema=None) as batch_op:
        batch_op.drop_column('default_frequency')
        batch_op.drop_column('per_diem')
        batch_op.drop_column('weekly_rate')
        batch_op.drop_column('daily_rate')
        batch_op.drop_column('show_rate')
