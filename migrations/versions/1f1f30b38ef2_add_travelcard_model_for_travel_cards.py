"""Add TravelCard model for travel cards

Revision ID: 1f1f30b38ef2
Revises: 00e9f0bad5f8
Create Date: 2026-01-21 22:13:21.139482

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1f1f30b38ef2'
down_revision = '00e9f0bad5f8'
branch_labels = None
depends_on = None


def upgrade():
    # Create travel_cards table
    op.create_table('travel_cards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('card_number', sa.String(length=50), nullable=False),
        sa.Column('card_type', sa.String(length=50), nullable=False),
        sa.Column('card_name', sa.String(length=100), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_travel_cards_user_id'), 'travel_cards', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_travel_cards_user_id'), table_name='travel_cards')
    op.drop_table('travel_cards')
