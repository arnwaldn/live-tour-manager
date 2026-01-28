"""Add oauth_tokens table for calendar integrations

Revision ID: j9k1m3o5q7s9
Revises: 49d627652263
Create Date: 2026-01-08 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'j9k1m3o5q7s9'
down_revision = '49d627652263'
branch_labels = None
depends_on = None


def upgrade():
    # Create oauth_tokens table
    op.create_table(
        'oauth_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(20), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_type', sa.String(50), nullable=True, server_default='Bearer'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('scopes', sa.JSON(), nullable=True),
        sa.Column('sync_token', sa.Text(), nullable=True),
        sa.Column('delta_link', sa.Text(), nullable=True),
        sa.Column('calendar_id', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('last_sync', sa.DateTime(), nullable=True),
        sa.Column('sync_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'provider', name='uq_user_provider')
    )

    # Create indexes
    op.create_index(op.f('ix_oauth_tokens_user_id'), 'oauth_tokens', ['user_id'], unique=False)
    op.create_index(op.f('ix_oauth_tokens_provider'), 'oauth_tokens', ['provider'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_oauth_tokens_provider'), table_name='oauth_tokens')
    op.drop_index(op.f('ix_oauth_tokens_user_id'), table_name='oauth_tokens')

    # Drop table
    op.drop_table('oauth_tokens')
