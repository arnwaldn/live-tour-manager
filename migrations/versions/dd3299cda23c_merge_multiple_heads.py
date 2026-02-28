"""merge multiple heads

Revision ID: dd3299cda23c
Revises: 6ea92203edbe, a1b2c3d4e5f6, b9c1d3e5f7a9
Create Date: 2026-02-27 17:01:30.640326

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dd3299cda23c'
down_revision = ('6ea92203edbe', 'a1b2c3d4e5f6', 'b9c1d3e5f7a9')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
