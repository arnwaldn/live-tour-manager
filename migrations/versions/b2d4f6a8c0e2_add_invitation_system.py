"""Add invitation system to users

Revision ID: b2d4f6a8c0e2
Revises: a7c8d9e0f123
Create Date: 2026-01-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2d4f6a8c0e2'
down_revision = 'a7c8d9e0f123'
branch_labels = None
depends_on = None


def upgrade():
    # Add invitation_token column
    op.add_column('users', sa.Column('invitation_token', sa.String(100), nullable=True))

    # Add invitation_token_expires column
    op.add_column('users', sa.Column('invitation_token_expires', sa.DateTime(), nullable=True))

    # Add invited_by_id column (foreign key to users.id)
    op.add_column('users', sa.Column('invited_by_id', sa.Integer(), nullable=True))

    # Create foreign key constraint
    op.create_foreign_key(
        'fk_users_invited_by_id',
        'users', 'users',
        ['invited_by_id'], ['id']
    )

    # Create unique index on invitation_token
    op.create_index(
        'ix_users_invitation_token',
        'users',
        ['invitation_token'],
        unique=True
    )


def downgrade():
    # Drop index
    op.drop_index('ix_users_invitation_token', table_name='users')

    # Drop foreign key constraint
    op.drop_constraint('fk_users_invited_by_id', 'users', type_='foreignkey')

    # Drop columns
    op.drop_column('users', 'invited_by_id')
    op.drop_column('users', 'invitation_token_expires')
    op.drop_column('users', 'invitation_token')
