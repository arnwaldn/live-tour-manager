"""Add planning columns to tour_stop_members_v2

Revision ID: a1b2c3d4e5f6
Revises: z7a9b1c3d5e7
Create Date: 2026-01-31 23:30:00.000000

Adds work_start, work_end, break_start, break_end, meal_time columns
for proper planning functionality.
"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = 'z7a9b1c3d5e7'
branch_labels = None
depends_on = None


def upgrade():
    # Add planning columns to tour_stop_members_v2
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'tour_stop_members_v2' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('tour_stop_members_v2')]

        if 'work_start' not in columns:
            op.add_column('tour_stop_members_v2', sa.Column('work_start', sa.Time(), nullable=True))
        if 'work_end' not in columns:
            op.add_column('tour_stop_members_v2', sa.Column('work_end', sa.Time(), nullable=True))
        if 'break_start' not in columns:
            op.add_column('tour_stop_members_v2', sa.Column('break_start', sa.Time(), nullable=True))
        if 'break_end' not in columns:
            op.add_column('tour_stop_members_v2', sa.Column('break_end', sa.Time(), nullable=True))
        if 'meal_time' not in columns:
            op.add_column('tour_stop_members_v2', sa.Column('meal_time', sa.Time(), nullable=True))

        print("Added planning columns to tour_stop_members_v2")


def downgrade():
    op.drop_column('tour_stop_members_v2', 'meal_time')
    op.drop_column('tour_stop_members_v2', 'break_end')
    op.drop_column('tour_stop_members_v2', 'break_start')
    op.drop_column('tour_stop_members_v2', 'work_end')
    op.drop_column('tour_stop_members_v2', 'work_start')
