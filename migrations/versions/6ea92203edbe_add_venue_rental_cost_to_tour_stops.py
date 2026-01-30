"""add venue_rental_cost to tour_stops

Revision ID: 6ea92203edbe
Revises: r0s2t4v6x8z0
Create Date: 2026-01-30 12:03:54.643796

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6ea92203edbe'
down_revision = 'r0s2t4v6x8z0'
branch_labels = None
depends_on = None


def upgrade():
    # Add venue_rental_cost column to tour_stops table
    op.add_column('tour_stops', sa.Column('venue_rental_cost', sa.Numeric(precision=10, scale=2), nullable=True))


def downgrade():
    # Remove venue_rental_cost column
    op.drop_column('tour_stops', 'venue_rental_cost')
