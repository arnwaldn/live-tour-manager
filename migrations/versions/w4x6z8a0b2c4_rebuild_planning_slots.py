"""Rebuild planning_slots table with role-based structure

Revision ID: w4x6z8a0b2c4
Revises: v3w5y7z9a1b3
Create Date: 2026-01-31 14:00:00.000000

This migration drops and recreates planning_slots with the new
role-based structure (role_name, category) instead of user-based.
"""
from alembic import op
import sqlalchemy as sa


revision = 'w4x6z8a0b2c4'
down_revision = 'v3w5y7z9a1b3'
branch_labels = None
depends_on = None


def upgrade():
    # Drop old table if exists (may have wrong structure)
    op.execute('DROP TABLE IF EXISTS planning_slots CASCADE')

    # Create new table with role-based structure
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
