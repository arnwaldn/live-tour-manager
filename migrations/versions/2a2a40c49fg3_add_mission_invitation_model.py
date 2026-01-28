"""Add MissionInvitation model

Revision ID: 2a2a40c49fg3
Revises: 1f1f30b38ef2
Create Date: 2026-01-21 22:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2a2a40c49fg3'
down_revision = '1f1f30b38ef2'
branch_labels = None
depends_on = None


def upgrade():
    # Create mission_invitations table
    op.create_table('mission_invitations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tour_stop_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'accepted', 'declined', 'expired', name='missioninvitationstatus'), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('invited_at', sa.DateTime(), nullable=False),
        sa.Column('responded_at', sa.DateTime(), nullable=True),
        sa.Column('response_note', sa.Text(), nullable=True),
        sa.Column('reminder_sent_at', sa.DateTime(), nullable=True),
        sa.Column('reminder_count', sa.Integer(), nullable=True, default=0),
        sa.ForeignKeyConstraint(['tour_stop_id'], ['tour_stops.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tour_stop_id', 'user_id', name='uq_mission_invitation_stop_user')
    )
    op.create_index(op.f('ix_mission_invitations_status'), 'mission_invitations', ['status'], unique=False)
    op.create_index(op.f('ix_mission_invitations_token'), 'mission_invitations', ['token'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_mission_invitations_token'), table_name='mission_invitations')
    op.drop_index(op.f('ix_mission_invitations_status'), table_name='mission_invitations')
    op.drop_table('mission_invitations')
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS missioninvitationstatus')
