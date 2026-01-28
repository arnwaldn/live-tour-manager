"""Update TourStopStatus enum (Pattern Dolibarr workflow)

Migration des statuts:
- HOLD → draft
- ADVANCED → confirmed (car is_advanced existe déjà)
- COMPLETED → performed
- CANCELLED → canceled (orthographe US)

Ajout des timestamps workflow:
- confirmed_at, performed_at, settled_at, canceled_at

Revision ID: e5g7i9k1m3o5
Revises: d4f6h8j0l2n4
Create Date: 2026-01-06 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'e5g7i9k1m3o5'
down_revision = 'd4f6h8j0l2n4'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade():
    # PostgreSQL approach: Convert column to VARCHAR, migrate data, then back to new ENUM
    # Note: Les valeurs existantes dans l'enum PostgreSQL sont en MAJUSCULES

    # 1. Ajouter les nouvelles colonnes timestamp
    if not column_exists('tour_stops', 'confirmed_at'):
        op.add_column('tour_stops', sa.Column('confirmed_at', sa.DateTime(), nullable=True))

    if not column_exists('tour_stops', 'performed_at'):
        op.add_column('tour_stops', sa.Column('performed_at', sa.DateTime(), nullable=True))

    if not column_exists('tour_stops', 'settled_at'):
        op.add_column('tour_stops', sa.Column('settled_at', sa.DateTime(), nullable=True))

    if not column_exists('tour_stops', 'canceled_at'):
        op.add_column('tour_stops', sa.Column('canceled_at', sa.DateTime(), nullable=True))

    # 2. Convertir la colonne status en VARCHAR temporairement (convertit MAJUSCULES en text)
    op.execute(sa.text("ALTER TABLE tour_stops ALTER COLUMN status TYPE VARCHAR(50) USING status::text"))

    # 3. Normaliser en minuscules et migrer les données
    # D'abord convertir tout en minuscules
    op.execute(sa.text("UPDATE tour_stops SET status = LOWER(status)"))

    # Ensuite faire le mapping des anciennes valeurs vers les nouvelles
    op.execute(sa.text("UPDATE tour_stops SET status='draft' WHERE status='hold'"))
    op.execute(sa.text("UPDATE tour_stops SET status='confirmed' WHERE status='advanced'"))
    op.execute(sa.text("UPDATE tour_stops SET status='performed' WHERE status='completed'"))
    op.execute(sa.text("UPDATE tour_stops SET status='canceled' WHERE status='cancelled'"))

    # 4. Supprimer l'ancien type enum
    op.execute(sa.text("DROP TYPE IF EXISTS tourstopstatus"))

    # 5. Créer le nouveau type enum (tout en minuscules)
    op.execute(sa.text("""
        CREATE TYPE tourstopstatus AS ENUM (
            'draft', 'pending', 'confirmed', 'performed', 'settled', 'canceled'
        )
    """))

    # 6. Reconvertir la colonne au nouveau type enum
    op.execute(sa.text("ALTER TABLE tour_stops ALTER COLUMN status TYPE tourstopstatus USING status::tourstopstatus"))

    # 7. Remettre la valeur par défaut
    op.execute(sa.text("ALTER TABLE tour_stops ALTER COLUMN status SET DEFAULT 'draft'"))

    # 8. Pour les stops confirmés, peupler confirmed_at avec created_at
    op.execute(sa.text("""
        UPDATE tour_stops
        SET confirmed_at = created_at
        WHERE status = 'confirmed' AND confirmed_at IS NULL
    """))

    # 9. Pour les stops performed, peupler performed_at
    op.execute(sa.text("""
        UPDATE tour_stops
        SET performed_at = COALESCE(updated_at, created_at)
        WHERE status = 'performed' AND performed_at IS NULL
    """))


def downgrade():
    # Convertir en VARCHAR
    op.execute(sa.text("ALTER TABLE tour_stops ALTER COLUMN status TYPE VARCHAR(50) USING status::text"))

    # Migrer vers anciennes valeurs (en MAJUSCULES pour compatibilité)
    op.execute(sa.text("UPDATE tour_stops SET status='HOLD' WHERE status='draft'"))
    op.execute(sa.text("UPDATE tour_stops SET status='CONFIRMED' WHERE status='settled'"))
    op.execute(sa.text("UPDATE tour_stops SET status='COMPLETED' WHERE status='performed'"))
    op.execute(sa.text("UPDATE tour_stops SET status='CANCELLED' WHERE status='canceled'"))
    # pending → PENDING, confirmed → CONFIRMED
    op.execute(sa.text("UPDATE tour_stops SET status = UPPER(status) WHERE status IN ('pending', 'confirmed')"))

    # Supprimer nouveau type, recréer ancien (en MAJUSCULES)
    op.execute(sa.text("DROP TYPE IF EXISTS tourstopstatus"))
    op.execute(sa.text("""
        CREATE TYPE tourstopstatus AS ENUM (
            'HOLD', 'PENDING', 'CONFIRMED', 'ADVANCED', 'COMPLETED', 'CANCELLED'
        )
    """))

    # Reconvertir
    op.execute(sa.text("ALTER TABLE tour_stops ALTER COLUMN status TYPE tourstopstatus USING status::tourstopstatus"))
    op.execute(sa.text("ALTER TABLE tour_stops ALTER COLUMN status SET DEFAULT 'HOLD'"))

    # Supprimer colonnes timestamp
    op.drop_column('tour_stops', 'canceled_at')
    op.drop_column('tour_stops', 'settled_at')
    op.drop_column('tour_stops', 'performed_at')
    op.drop_column('tour_stops', 'confirmed_at')
