"""Add financial improvements R1-R5: ticketing_fee_percentage and promotor_expenses

R1: Add ticketing_fee_percentage to tour_stops (default 5% industry standard)
R4: Create promotor_expenses table for Split Point calculation

Revision ID: d4f6h8j0l2n4
Revises: c3e5g7i9k1m3
Create Date: 2026-01-06 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'd4f6h8j0l2n4'
down_revision = 'c3e5g7i9k1m3'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(table_name):
    """Check if a table exists."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade():
    # R1: Add ticketing_fee_percentage to tour_stops (industry standard: 2-10%, default 5%)
    if not column_exists('tour_stops', 'ticketing_fee_percentage'):
        op.add_column('tour_stops', sa.Column(
            'ticketing_fee_percentage',
            sa.Numeric(precision=5, scale=2),
            nullable=True,
            server_default='5.0'
        ))

    # R4: Create promotor_expenses table for Split Point calculation
    if not table_exists('promotor_expenses'):
        op.create_table(
            'promotor_expenses',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tour_stop_id', sa.Integer(), nullable=False),
            # Expense categories (industry standard - Pollstar, Billboard)
            sa.Column('venue_fee', sa.Numeric(precision=10, scale=2), server_default='0'),
            sa.Column('production_cost', sa.Numeric(precision=10, scale=2), server_default='0'),
            sa.Column('marketing_cost', sa.Numeric(precision=10, scale=2), server_default='0'),
            sa.Column('insurance', sa.Numeric(precision=10, scale=2), server_default='0'),
            sa.Column('security', sa.Numeric(precision=10, scale=2), server_default='0'),
            sa.Column('catering', sa.Numeric(precision=10, scale=2), server_default='0'),
            sa.Column('other', sa.Numeric(precision=10, scale=2), server_default='0'),
            sa.Column('other_description', sa.String(length=255), nullable=True),
            # Currency (inherited from TourStop)
            sa.Column('currency', sa.String(length=3), server_default='EUR'),
            # Notes
            sa.Column('notes', sa.Text(), nullable=True),
            # Timestamps
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            # Primary key
            sa.PrimaryKeyConstraint('id'),
            # Foreign key
            sa.ForeignKeyConstraint(['tour_stop_id'], ['tour_stops.id'], name='fk_promotor_expenses_tour_stop_id'),
        )

        # Create index on tour_stop_id for faster lookups
        op.create_index('ix_promotor_expenses_tour_stop_id', 'promotor_expenses', ['tour_stop_id'], unique=False)


def downgrade():
    # Drop promotor_expenses table
    op.drop_index('ix_promotor_expenses_tour_stop_id', table_name='promotor_expenses')
    op.drop_table('promotor_expenses')

    # Remove ticketing_fee_percentage from tour_stops
    op.drop_column('tour_stops', 'ticketing_fee_percentage')
