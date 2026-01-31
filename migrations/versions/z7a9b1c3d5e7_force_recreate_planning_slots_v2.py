"""Force recreate planning_slots table v2

Revision ID: z7a9b1c3d5e7
Revises: y6z8a0b2c4d6
Create Date: 2026-01-31 22:00:00.000000

This migration UNCONDITIONALLY drops and recreates planning_slots
to ensure the correct schema with role_name and category columns.
"""
from alembic import op
import sqlalchemy as sa


revision = 'z7a9b1c3d5e7'
down_revision = 'y6z8a0b2c4d6'
branch_labels = None
depends_on = None


def upgrade():
    # FORCE drop the table unconditionally using raw SQL
    # This ensures the table is recreated with correct schema
    print("=== FORCE RECREATING planning_slots TABLE ===")

    conn = op.get_bind()

    # Drop table if exists (PostgreSQL syntax)
    conn.execute(sa.text('DROP TABLE IF EXISTS planning_slots CASCADE'))
    print("Dropped existing planning_slots table")

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
    print("Created planning_slots with correct schema")

    # Create indexes
    op.create_index('ix_planning_slots_tour_stop', 'planning_slots', ['tour_stop_id'])
    op.create_index('ix_planning_slots_category', 'planning_slots', ['category'])
    op.create_index('ix_planning_slots_role', 'planning_slots', ['role_name'])
    print("Created indexes")

    # Verify the schema
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('planning_slots')]
    print(f"Final columns: {columns}")

    if 'role_name' in columns and 'category' in columns:
        print("=== SUCCESS: planning_slots has correct schema ===")
    else:
        print("=== ERROR: Schema still incorrect! ===")


def downgrade():
    op.drop_index('ix_planning_slots_role', table_name='planning_slots')
    op.drop_index('ix_planning_slots_category', table_name='planning_slots')
    op.drop_index('ix_planning_slots_tour_stop', table_name='planning_slots')
    op.drop_table('planning_slots')
