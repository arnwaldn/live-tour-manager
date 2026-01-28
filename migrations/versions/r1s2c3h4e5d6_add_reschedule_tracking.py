"""Add reschedule tracking fields to tour_stops

Revision ID: r1s2c3h4e5d6
Revises: 6bf86f0608f1
Create Date: 2026-01-21 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'r1s2c3h4e5d6'
down_revision = '6bf86f0608f1'
branch_labels = None
depends_on = None


def upgrade():
    # Add reschedule tracking columns to tour_stops
    with op.batch_alter_table('tour_stops', schema=None) as batch_op:
        batch_op.add_column(sa.Column('original_date', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('rescheduled_from_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('reschedule_reason', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('reschedule_count', sa.Integer(), server_default='0', nullable=True))
        batch_op.add_column(sa.Column('rescheduled_at', sa.DateTime(), nullable=True))
        batch_op.create_foreign_key(
            'fk_tour_stops_rescheduled_from',
            'tour_stops',
            ['rescheduled_from_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('tour_stops', schema=None) as batch_op:
        batch_op.drop_constraint('fk_tour_stops_rescheduled_from', type_='foreignkey')
        batch_op.drop_column('rescheduled_at')
        batch_op.drop_column('reschedule_count')
        batch_op.drop_column('reschedule_reason')
        batch_op.drop_column('rescheduled_from_id')
        batch_op.drop_column('original_date')
