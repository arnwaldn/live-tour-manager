"""Add planning_slots table for daily concert planning grid

Revision ID: v3w5y7z9a1b3
Revises: u2v4w6x8y0z2
Create Date: 2026-01-31 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'v3w5y7z9a1b3'
down_revision = 'u2v4w6x8y0z2'
branch_labels = None
depends_on = None


def upgrade():
    # Create planning_slots table for the daily planning grid
    op.create_table('planning_slots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tour_stop_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('profession_id', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('task_description', sa.String(200), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tour_stop_id'], ['tour_stops.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['profession_id'], ['professions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_planning_slots_tour_stop', 'planning_slots', ['tour_stop_id'])
    op.create_index('ix_planning_slots_user', 'planning_slots', ['user_id'])


def downgrade():
    op.drop_index('ix_planning_slots_user', table_name='planning_slots')
    op.drop_index('ix_planning_slots_tour_stop', table_name='planning_slots')
    op.drop_table('planning_slots')
