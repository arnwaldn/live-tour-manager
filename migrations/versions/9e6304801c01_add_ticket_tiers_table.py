"""add_ticket_tiers_table

Revision ID: 9e6304801c01
Revises: 09eda1c0fb44
Create Date: 2026-02-28 17:06:18.158710

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9e6304801c01'
down_revision = '09eda1c0fb44'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ticket_tiers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tour_stop_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('price', sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column('quantity_available', sa.Integer(), nullable=True),
        sa.Column('sold', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tour_stop_id'], ['tour_stops.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ticket_tiers_tour_stop_id', 'ticket_tiers', ['tour_stop_id'])


def downgrade():
    op.drop_index('ix_ticket_tiers_tour_stop_id', table_name='ticket_tiers')
    op.drop_table('ticket_tiers')
