"""Add system_settings table

Revision ID: 5fc84d517d83
Revises: 7fc0aa7603ce
Create Date: 2026-01-22 04:05:56.899314

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5fc84d517d83'
down_revision = '7fc0aa7603ce'
branch_labels = None
depends_on = None


def upgrade():
    # Create system_settings table
    op.create_table('system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('is_encrypted', sa.Boolean(), default=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('updated_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('system_settings', schema=None) as batch_op:
        batch_op.create_index('ix_system_settings_key', ['key'], unique=True)


def downgrade():
    with op.batch_alter_table('system_settings', schema=None) as batch_op:
        batch_op.drop_index('ix_system_settings_key')

    op.drop_table('system_settings')
