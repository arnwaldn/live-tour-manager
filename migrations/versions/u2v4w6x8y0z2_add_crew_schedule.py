"""Add crew schedule tables

Revision ID: u2v4w6x8y0z2
Revises: t1z2n3e4w5b6
Create Date: 2026-01-30 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'u2v4w6x8y0z2'
down_revision = 't1z2n3e4w5b6'
branch_labels = None
depends_on = None


def upgrade():
    # Create external_contacts table
    op.create_table('external_contacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(50), nullable=False),
        sa.Column('last_name', sa.String(50), nullable=False),
        sa.Column('email', sa.String(120), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('profession_id', sa.Integer(), nullable=True),
        sa.Column('company', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['profession_id'], ['professions.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create crew_schedule_slots table
    op.create_table('crew_schedule_slots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tour_stop_id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('task_name', sa.String(100), nullable=False),
        sa.Column('task_description', sa.Text(), nullable=True),
        sa.Column('profession_category', sa.Enum('MUSICIEN', 'TECHNICIEN', 'PRODUCTION', 'STYLE', 'SECURITE', 'MANAGEMENT', name='professioncategory'), nullable=True),
        sa.Column('color', sa.String(7), nullable=True, default='#3B82F6'),
        sa.Column('order', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['tour_stop_id'], ['tour_stops.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_crew_slots_tour_stop', 'crew_schedule_slots', ['tour_stop_id'])

    # Create crew_assignments table
    op.create_table('crew_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slot_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('external_contact_id', sa.Integer(), nullable=True),
        sa.Column('profession_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('ASSIGNED', 'CONFIRMED', 'DECLINED', 'UNAVAILABLE', 'COMPLETED', name='assignmentstatus'), nullable=True, default='ASSIGNED'),
        sa.Column('call_time', sa.Time(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('assigned_by_id', sa.Integer(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['slot_id'], ['crew_schedule_slots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['external_contact_id'], ['external_contacts.id'], ),
        sa.ForeignKeyConstraint(['profession_id'], ['professions.id'], ),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('user_id IS NOT NULL OR external_contact_id IS NOT NULL', name='ck_assignment_person'),
        sa.UniqueConstraint('slot_id', 'user_id', name='uq_slot_user'),
        sa.UniqueConstraint('slot_id', 'external_contact_id', name='uq_slot_external')
    )
    op.create_index('ix_crew_assignments_user', 'crew_assignments', ['user_id'])


def downgrade():
    op.drop_index('ix_crew_assignments_user', table_name='crew_assignments')
    op.drop_table('crew_assignments')
    op.drop_index('ix_crew_slots_tour_stop', table_name='crew_schedule_slots')
    op.drop_table('crew_schedule_slots')
    op.drop_table('external_contacts')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS assignmentstatus')
