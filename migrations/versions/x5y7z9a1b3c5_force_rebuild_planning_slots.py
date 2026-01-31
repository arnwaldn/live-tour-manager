"""Force rebuild planning_slots table with correct schema

Revision ID: x5y7z9a1b3c5
Revises: w4x6z8a0b2c4
Create Date: 2026-01-31 18:00:00.000000

This migration DROPS and RECREATES planning_slots to ensure the correct schema.
"""
from alembic import op
import sqlalchemy as sa


revision = 'x5y7z9a1b3c5'
down_revision = 'w4x6z8a0b2c4'
branch_labels = None
depends_on = None


def upgrade():
    # FORCE drop the table if it exists with wrong schema
    op.execute('DROP TABLE IF EXISTS planning_slots CASCADE')

    # Create with correct schema
    op.create_table('planning_slots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tour_stop_id', sa.Integer(), nullable=False),
        sa.Column('role_name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('task_description', sa.String(200), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tour_stop_id'], ['tour_stops.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_planning_slots_tour_stop', 'planning_slots', ['tour_stop_id'])
    op.create_index('ix_planning_slots_category', 'planning_slots', ['category'])
    op.create_index('ix_planning_slots_role', 'planning_slots', ['role_name'])


def downgrade():
    op.drop_index('ix_planning_slots_role', table_name='planning_slots')
    op.drop_index('ix_planning_slots_category', table_name='planning_slots')
    op.drop_index('ix_planning_slots_tour_stop', table_name='planning_slots')
    op.drop_table('planning_slots')
