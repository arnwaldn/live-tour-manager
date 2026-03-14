"""add device_tokens table for FCM

Revision ID: 54cf47fde258
Revises: b2c3d4e5f6g8
Create Date: 2026-03-14 17:19:50.139486

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '54cf47fde258'
down_revision = 'b2c3d4e5f6g8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'device_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=500), nullable=False),
        sa.Column('platform', sa.String(length=20), server_default='android'),
        sa.Column('device_name', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )
    with op.batch_alter_table('device_tokens', schema=None) as batch_op:
        batch_op.create_index('ix_device_tokens_user', ['user_id'])


def downgrade():
    with op.batch_alter_table('device_tokens', schema=None) as batch_op:
        batch_op.drop_index('ix_device_tokens_user')

    op.drop_table('device_tokens')
