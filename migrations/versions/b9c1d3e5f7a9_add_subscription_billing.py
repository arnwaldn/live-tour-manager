"""Add subscription table and stripe_customer_id on users

Revision ID: b9c1d3e5f7a9
Revises: a8b0c2d4e6f8
Create Date: 2026-02-26 23:00:00.000000

Phase 7c: Stripe SaaS billing — subscription model for Free/Pro plans.
"""
from alembic import op
import sqlalchemy as sa


revision = 'b9c1d3e5f7a9'
down_revision = 'a8b0c2d4e6f8'
branch_labels = None
depends_on = None


def upgrade():
    # --- Subscription table ---
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan', sa.String(20), nullable=False, server_default='free'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('current_period_start', sa.DateTime(), nullable=True),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'], unique=True)
    op.create_index('ix_subscriptions_stripe_subscription_id', 'subscriptions', ['stripe_subscription_id'], unique=True)

    # --- Add stripe_customer_id to users ---
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('stripe_customer_id', sa.String(255), nullable=True))
        batch_op.create_index('ix_users_stripe_customer_id', ['stripe_customer_id'], unique=True)


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_index('ix_users_stripe_customer_id')
        batch_op.drop_column('stripe_customer_id')

    op.drop_table('subscriptions')
