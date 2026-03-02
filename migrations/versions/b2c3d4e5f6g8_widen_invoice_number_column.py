"""Widen invoice number column from 20 to 30 chars.

Draft numbers like BROUILLON-20260302184900 need 24+ chars.
The old String(20) caused 500 errors on invoice creation.

Revision ID: b2c3d4e5f6g8
Revises: a1b2c3d4e5f7
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'b2c3d4e5f6g8'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.alter_column('number',
                              existing_type=sa.String(20),
                              type_=sa.String(30),
                              existing_nullable=False)


def downgrade():
    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.alter_column('number',
                              existing_type=sa.String(30),
                              type_=sa.String(20),
                              existing_nullable=False)
