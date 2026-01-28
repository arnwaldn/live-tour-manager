"""Add logistics_assignments table for nominative assignments.

Revision ID: n2o4p6r8t0v2
Revises: m1n3o5q7s9u1
Create Date: 2026-01-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'n2o4p6r8t0v2'
down_revision = 'm1n3o5q7s9u1'
branch_labels = None
depends_on = None


def upgrade():
    """Create logistics_assignments table."""
    op.create_table(
        'logistics_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('logistics_info_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('seat_number', sa.String(20), nullable=True),
        sa.Column('room_number', sa.String(20), nullable=True),
        sa.Column('room_sharing_with', sa.String(100), nullable=True),
        sa.Column('special_requests', sa.Text(), nullable=True),
        sa.Column('confirmation_sent', sa.Boolean(), default=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.Column('assigned_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['logistics_info_id'], ['logistics_info.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('logistics_info_id', 'user_id', name='unique_logistics_user_assignment')
    )
    # Create indexes for faster queries
    op.create_index('ix_logistics_assignments_logistics_info_id', 'logistics_assignments', ['logistics_info_id'])
    op.create_index('ix_logistics_assignments_user_id', 'logistics_assignments', ['user_id'])


def downgrade():
    """Drop logistics_assignments table."""
    op.drop_index('ix_logistics_assignments_user_id', table_name='logistics_assignments')
    op.drop_index('ix_logistics_assignments_logistics_info_id', table_name='logistics_assignments')
    op.drop_table('logistics_assignments')
