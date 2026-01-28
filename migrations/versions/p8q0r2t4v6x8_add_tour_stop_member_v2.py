"""Add TourStopMember v2 model with profession support.

Revision ID: p8q0r2t4v6x8
Revises: 5fc84d517d83
Create Date: 2026-01-25 12:00:00.000000

This migration:
1. Creates the new tour_stop_members_v2 table with profession support
2. Migrates existing data from tour_stop_members (legacy) to the new table
3. Keeps the legacy table for backwards compatibility during transition
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'p8q0r2t4v6x8'
down_revision = '5fc84d517d83'  # After system_settings
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create the new tour_stop_members_v2 table
    op.create_table(
        'tour_stop_members_v2',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tour_stop_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('profession_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('assigned', 'confirmed', 'declined', 'tentative', 'canceled',
                                    name='memberassignmentstatus'), nullable=False, default='assigned'),
        sa.Column('call_time', sa.Time(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('assigned_by_id', sa.Integer(), nullable=True),
        sa.Column('responded_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.ForeignKeyConstraint(['tour_stop_id'], ['tour_stops.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['profession_id'], ['professions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tour_stop_id', 'user_id', name='uq_tour_stop_user')
    )

    # Create indexes for performance
    op.create_index('ix_tour_stop_members_v2_tour_stop_id', 'tour_stop_members_v2', ['tour_stop_id'])
    op.create_index('ix_tour_stop_members_v2_user_id', 'tour_stop_members_v2', ['user_id'])
    op.create_index('ix_tour_stop_members_v2_status', 'tour_stop_members_v2', ['status'])

    # 2. Migrate existing data from legacy table
    # Get connection for raw SQL
    connection = op.get_bind()

    # Check if legacy table exists and has data
    result = connection.execute(sa.text("""
        SELECT COUNT(*) FROM tour_stop_members
    """))
    count = result.scalar()

    if count > 0:
        # Migrate data: For each legacy assignment, get user's primary profession if available
        connection.execute(sa.text("""
            INSERT INTO tour_stop_members_v2 (tour_stop_id, user_id, profession_id, status, assigned_at, created_at, updated_at)
            SELECT
                tsm.tour_stop_id,
                tsm.user_id,
                (SELECT up.profession_id FROM user_professions up WHERE up.user_id = tsm.user_id AND up.is_primary = 1 LIMIT 1),
                'assigned',
                COALESCE(tsm.assigned_at, CURRENT_TIMESTAMP),
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            FROM tour_stop_members tsm
            WHERE NOT EXISTS (
                SELECT 1 FROM tour_stop_members_v2 v2
                WHERE v2.tour_stop_id = tsm.tour_stop_id AND v2.user_id = tsm.user_id
            )
        """))

        print(f"Migrated {count} tour stop member assignments to v2 table.")


def downgrade():
    # Drop indexes
    op.drop_index('ix_tour_stop_members_v2_status', table_name='tour_stop_members_v2')
    op.drop_index('ix_tour_stop_members_v2_user_id', table_name='tour_stop_members_v2')
    op.drop_index('ix_tour_stop_members_v2_tour_stop_id', table_name='tour_stop_members_v2')

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS memberassignmentstatus")

    # Drop the table
    op.drop_table('tour_stop_members_v2')
