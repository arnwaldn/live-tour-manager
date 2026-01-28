"""Add timezone field to User and Venue models.

Revision ID: t1z2n3e4w5b6
Revises: r1s2c3h4e5d6
Create Date: 2026-01-26

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 't1z2n3e4w5b6'
down_revision = 'p8q0r2t4v6x8'
branch_labels = None
depends_on = None


def upgrade():
    """Add timezone column to users and venues tables."""
    # Add timezone to users table
    op.add_column('users', sa.Column('timezone', sa.String(50), nullable=True, server_default='Europe/Paris'))

    # Add timezone to venues table
    op.add_column('venues', sa.Column('timezone', sa.String(50), nullable=True, server_default='Europe/Paris'))


def downgrade():
    """Remove timezone columns."""
    op.drop_column('users', 'timezone')
    op.drop_column('venues', 'timezone')
