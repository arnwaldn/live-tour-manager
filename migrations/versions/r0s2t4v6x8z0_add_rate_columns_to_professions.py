"""Add rate columns to professions table

Revision ID: r0s2t4v6x8z0
Revises: q9r1s3t5u7v9
Create Date: 2026-01-28 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'r0s2t4v6x8z0'
down_revision = 'q9r1s3t5u7v9'
branch_labels = None
depends_on = None


def upgrade():
    # Add rate columns to professions table
    op.add_column('professions', sa.Column('show_rate', sa.Numeric(10, 2), nullable=True))
    op.add_column('professions', sa.Column('daily_rate', sa.Numeric(10, 2), nullable=True))
    op.add_column('professions', sa.Column('weekly_rate', sa.Numeric(10, 2), nullable=True))
    op.add_column('professions', sa.Column('per_diem', sa.Numeric(10, 2), nullable=True))
    op.add_column('professions', sa.Column('default_frequency', sa.String(20), nullable=True))


def downgrade():
    op.drop_column('professions', 'default_frequency')
    op.drop_column('professions', 'per_diem')
    op.drop_column('professions', 'weekly_rate')
    op.drop_column('professions', 'daily_rate')
    op.drop_column('professions', 'show_rate')
