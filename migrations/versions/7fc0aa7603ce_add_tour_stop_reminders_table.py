"""add tour_stop_reminders table

Revision ID: 7fc0aa7603ce
Revises: 6eb9996592bd
Create Date: 2026-01-22 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7fc0aa7603ce'
down_revision = '6eb9996592bd'
branch_labels = None
depends_on = None


def upgrade():
    # Create tour_stop_reminders table
    op.create_table('tour_stop_reminders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tour_stop_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('reminder_type', sa.String(length=10), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tour_stop_id'], ['tour_stops.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tour_stop_id', 'user_id', 'reminder_type', name='uq_reminder_once')
    )
    with op.batch_alter_table('tour_stop_reminders', schema=None) as batch_op:
        batch_op.create_index('ix_tour_stop_reminders_tour_stop_id', ['tour_stop_id'], unique=False)
        batch_op.create_index('ix_tour_stop_reminders_user_id', ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('tour_stop_reminders', schema=None) as batch_op:
        batch_op.drop_index('ix_tour_stop_reminders_user_id')
        batch_op.drop_index('ix_tour_stop_reminders_tour_stop_id')

    op.drop_table('tour_stop_reminders')
