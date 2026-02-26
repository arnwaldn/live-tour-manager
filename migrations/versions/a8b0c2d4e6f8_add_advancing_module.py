"""Add advancing module tables and TourStop columns

Revision ID: a8b0c2d4e6f8
Revises: z7a9b1c3d5e7
Create Date: 2026-02-26 21:50:00.000000

Phase 7a: Advancing module — checklist, templates, rider requirements,
contacts, and production specs for event preparation workflow.
"""
from alembic import op
import sqlalchemy as sa


revision = 'a8b0c2d4e6f8'
down_revision = 'z7a9b1c3d5e7'
branch_labels = None
depends_on = None


def upgrade():
    # --- AdvancingTemplate ---
    op.create_table(
        'advancing_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('items', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- AdvancingChecklistItem ---
    op.create_table(
        'advancing_checklist_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tour_stop_id', sa.Integer(), sa.ForeignKey('tour_stops.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(30), nullable=False),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('completed_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_advancing_checklist_items_tour_stop_id', 'advancing_checklist_items', ['tour_stop_id'])
    op.create_index('ix_advancing_checklist_items_category', 'advancing_checklist_items', ['category'])

    # --- RiderRequirement ---
    op.create_table(
        'rider_requirements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tour_stop_id', sa.Integer(), sa.ForeignKey('tour_stops.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category', sa.String(30), nullable=False),
        sa.Column('requirement', sa.String(255), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_mandatory', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_confirmed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('venue_response', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_rider_requirements_tour_stop_id', 'rider_requirements', ['tour_stop_id'])
    op.create_index('ix_rider_requirements_category', 'rider_requirements', ['category'])

    # --- AdvancingContact ---
    op.create_table(
        'advancing_contacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tour_stop_id', sa.Integer(), sa.ForeignKey('tour_stops.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('role', sa.String(100), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_advancing_contacts_tour_stop_id', 'advancing_contacts', ['tour_stop_id'])

    # --- TourStop new columns ---
    with op.batch_alter_table('tour_stops') as batch_op:
        batch_op.add_column(sa.Column('advancing_status', sa.String(20), nullable=False, server_default='not_started'))
        batch_op.add_column(sa.Column('advancing_deadline', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('stage_width', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('stage_depth', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('stage_height', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('power_available', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('rigging_points', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('venue_contact_name', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('venue_contact_email', sa.String(120), nullable=True))
        batch_op.add_column(sa.Column('venue_contact_phone', sa.String(30), nullable=True))
        batch_op.create_index('ix_tour_stops_advancing_status', ['advancing_status'])


def downgrade():
    with op.batch_alter_table('tour_stops') as batch_op:
        batch_op.drop_index('ix_tour_stops_advancing_status')
        batch_op.drop_column('venue_contact_phone')
        batch_op.drop_column('venue_contact_email')
        batch_op.drop_column('venue_contact_name')
        batch_op.drop_column('rigging_points')
        batch_op.drop_column('power_available')
        batch_op.drop_column('stage_height')
        batch_op.drop_column('stage_depth')
        batch_op.drop_column('stage_width')
        batch_op.drop_column('advancing_deadline')
        batch_op.drop_column('advancing_status')

    op.drop_table('advancing_contacts')
    op.drop_table('rider_requirements')
    op.drop_table('advancing_checklist_items')
    op.drop_table('advancing_templates')
