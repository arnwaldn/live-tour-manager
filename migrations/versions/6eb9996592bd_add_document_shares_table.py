"""add document_shares table

Revision ID: 6eb9996592bd
Revises: 2a2a40c49fg3
Create Date: 2026-01-21 23:15:57.972470

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6eb9996592bd'
down_revision = '2a2a40c49fg3'
branch_labels = None
depends_on = None


def upgrade():
    # Create document_shares table
    op.create_table('document_shares',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('shared_by_id', sa.Integer(), nullable=False),
        sa.Column('shared_to_user_id', sa.Integer(), nullable=False),
        sa.Column('share_type', sa.Enum('VIEW', 'EDIT', name='sharetype'), nullable=False),
        sa.Column('shared_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['shared_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['shared_to_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'shared_to_user_id', name='uq_document_share_recipient')
    )
    with op.batch_alter_table('document_shares', schema=None) as batch_op:
        batch_op.create_index('ix_document_shares_document_id', ['document_id'], unique=False)
        batch_op.create_index('ix_document_shares_shared_by_id', ['shared_by_id'], unique=False)
        batch_op.create_index('ix_document_shares_shared_to_user_id', ['shared_to_user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('document_shares', schema=None) as batch_op:
        batch_op.drop_index('ix_document_shares_shared_to_user_id')
        batch_op.drop_index('ix_document_shares_shared_by_id')
        batch_op.drop_index('ix_document_shares_document_id')

    op.drop_table('document_shares')
