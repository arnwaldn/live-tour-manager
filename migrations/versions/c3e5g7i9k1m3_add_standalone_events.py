"""Add standalone events support - tour_id nullable + band_id on tour_stops

Revision ID: c3e5g7i9k1m3
Revises: b2d4f6a8c0e2
Create Date: 2026-01-06 12:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3e5g7i9k1m3'
down_revision = 'b2d4f6a8c0e2'
branch_labels = None
depends_on = None


def upgrade():
    # Make tour_id nullable to support standalone events
    op.alter_column('tour_stops', 'tour_id',
               existing_type=sa.INTEGER(),
               nullable=True)

    # Add band_id column for standalone events (not linked to a tour)
    op.add_column('tour_stops', sa.Column('band_id', sa.Integer(), nullable=True))

    # Add foreign key constraint for band_id
    op.create_foreign_key(
        'fk_tour_stops_band_id',
        'tour_stops', 'bands',
        ['band_id'], ['id']
    )

    # Add index on band_id for faster queries
    op.create_index('ix_tour_stops_band_id', 'tour_stops', ['band_id'], unique=False)


def downgrade():
    # Remove index
    op.drop_index('ix_tour_stops_band_id', table_name='tour_stops')

    # Remove foreign key constraint
    op.drop_constraint('fk_tour_stops_band_id', 'tour_stops', type_='foreignkey')

    # Remove band_id column
    op.drop_column('tour_stops', 'band_id')

    # Make tour_id not nullable again (this might fail if there are NULL values)
    op.alter_column('tour_stops', 'tour_id',
               existing_type=sa.INTEGER(),
               nullable=False)
