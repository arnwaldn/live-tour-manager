"""Fix planning_slots schema - check and rebuild if needed

Revision ID: y6z8a0b2c4d6
Revises: x5y7z9a1b3c5
Create Date: 2026-01-31 20:00:00.000000

This migration checks if planning_slots has the correct schema.
If not (missing role_name/category), it drops and recreates the table.
"""
from alembic import op
import sqlalchemy as sa


revision = 'y6z8a0b2c4d6'
down_revision = 'x5y7z9a1b3c5'
branch_labels = None
depends_on = None


def upgrade():
    # Check if table exists and has wrong schema
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'planning_slots' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('planning_slots')]

        # If missing role_name or category, rebuild the table
        if 'role_name' not in columns or 'category' not in columns:
            print(f"planning_slots has wrong schema (columns: {columns}), rebuilding...")

            # Drop the old table
            op.drop_table('planning_slots')

    # Check if table was dropped or doesn't exist
    inspector = sa.inspect(conn)
    if 'planning_slots' not in inspector.get_table_names():
        print("Creating planning_slots with correct schema...")

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
        print("planning_slots table created successfully!")
    else:
        print("planning_slots table already has correct schema.")


def downgrade():
    # Only drop if it exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'planning_slots' in inspector.get_table_names():
        op.drop_index('ix_planning_slots_role', table_name='planning_slots')
        op.drop_index('ix_planning_slots_category', table_name='planning_slots')
        op.drop_index('ix_planning_slots_tour_stop', table_name='planning_slots')
        op.drop_table('planning_slots')
