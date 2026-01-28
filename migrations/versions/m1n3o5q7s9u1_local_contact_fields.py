"""Add company and phone_secondary to local_contacts.

Revision ID: m1n3o5q7s9u1
Revises: k0l2m4n6p8r0
Create Date: 2026-01-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'm1n3o5q7s9u1'
down_revision = 'k0l2m4n6p8r0'
branch_labels = None
depends_on = None


def upgrade():
    """Add company and phone_secondary fields to local_contacts table."""
    op.add_column('local_contacts', sa.Column('company', sa.String(100), nullable=True))
    op.add_column('local_contacts', sa.Column('phone_secondary', sa.String(30), nullable=True))


def downgrade():
    """Remove the new fields."""
    op.drop_column('local_contacts', 'phone_secondary')
    op.drop_column('local_contacts', 'company')
