"""Add user_id to guestlist_entries for artist linking

Cette migration ajoute la possibilité de lier une entrée guestlist de type ARTIST
à un utilisateur réel (membre du groupe). Cela permet:
- Auto-remplissage des infos depuis le profil utilisateur
- Traçabilité des entrées artistes
- Lien vers le profil depuis la liste d'invités

Revision ID: h8j0l2n4p6r8
Revises: g7i9k1m3o5p7
Create Date: 2026-01-06 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'h8j0l2n4p6r8'
down_revision = 'g7i9k1m3o5p7'
branch_labels = None
depends_on = None


def upgrade():
    # Add user_id column to guestlist_entries (nullable - only used for ARTIST type)
    op.add_column('guestlist_entries',
        sa.Column('user_id', sa.Integer(), nullable=True))

    # Add index for performance on user_id lookups
    op.create_index('ix_guestlist_entries_user_id',
        'guestlist_entries', ['user_id'])

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_guestlist_entries_user_id',
        'guestlist_entries', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL'  # Si l'utilisateur est supprimé, garder l'entrée guestlist
    )


def downgrade():
    # Remove foreign key constraint
    op.drop_constraint('fk_guestlist_entries_user_id', 'guestlist_entries', type_='foreignkey')

    # Remove index
    op.drop_index('ix_guestlist_entries_user_id', table_name='guestlist_entries')

    # Remove column
    op.drop_column('guestlist_entries', 'user_id')
