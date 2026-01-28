"""Add venue technical_specs column

Revision ID: a7c8d9e0f123
Revises: 13bf6b216395
Create Date: 2026-01-04 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7c8d9e0f123'
down_revision = '13bf6b216395'
branch_labels = None
depends_on = None


def upgrade():
    # Add technical_specs column to venues table (only missing column)
    with op.batch_alter_table('venues', schema=None) as batch_op:
        batch_op.add_column(sa.Column('technical_specs', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('venues', schema=None) as batch_op:
        batch_op.drop_column('technical_specs')
