"""Fix eventtype data - convert UPPERCASE to lowercase

Les données event_type dans la BD contiennent des valeurs UPPERCASE (SHOW, DAY_OFF...)
mais l'enum PostgreSQL eventtype a des valeurs lowercase (show, day_off...).

Cette migration convertit toutes les données existantes en lowercase.

Revision ID: f6h8j0l2n4p6
Revises: e5g7i9k1m3o5
Create Date: 2026-01-06 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f6h8j0l2n4p6'
down_revision = 'e5g7i9k1m3o5'
branch_labels = None
depends_on = None


def upgrade():
    # L'enum PostgreSQL 'eventtype' a des valeurs UPPERCASE (SHOW, DAY_OFF...)
    # Mais SQLAlchemy avec values_callable envoie lowercase (show, day_off...)
    # Solution: Recréer l'enum avec des valeurs lowercase

    # 1. Supprimer la valeur par défaut
    op.execute(sa.text("ALTER TABLE tour_stops ALTER COLUMN event_type DROP DEFAULT"))

    # 2. Convertir la colonne en VARCHAR
    op.execute(sa.text("ALTER TABLE tour_stops ALTER COLUMN event_type TYPE VARCHAR(50) USING event_type::text"))

    # 3. Convertir toutes les valeurs en lowercase
    op.execute(sa.text("UPDATE tour_stops SET event_type = LOWER(event_type)"))

    # 4. Supprimer l'ancien enum type
    op.execute(sa.text("DROP TYPE eventtype"))

    # 5. Créer le nouvel enum avec valeurs lowercase
    op.execute(sa.text("""
        CREATE TYPE eventtype AS ENUM (
            'show', 'day_off', 'travel', 'studio', 'promo',
            'rehearsal', 'press', 'meet_greet', 'photo_video', 'other'
        )
    """))

    # 6. Reconvertir la colonne au type enum
    op.execute(sa.text("ALTER TABLE tour_stops ALTER COLUMN event_type TYPE eventtype USING event_type::eventtype"))

    # 7. Remettre la valeur par défaut
    op.execute(sa.text("ALTER TABLE tour_stops ALTER COLUMN event_type SET DEFAULT 'show'"))


def downgrade():
    # Reconvertir en uppercase (pour rollback)
    # 1. Supprimer la valeur par défaut
    op.execute(sa.text("ALTER TABLE tour_stops ALTER COLUMN event_type DROP DEFAULT"))

    # 2. Convertir en VARCHAR
    op.execute(sa.text("ALTER TABLE tour_stops ALTER COLUMN event_type TYPE VARCHAR(50) USING event_type::text"))

    # 3. Convertir en uppercase
    op.execute(sa.text("UPDATE tour_stops SET event_type = UPPER(event_type)"))

    # 4. Supprimer l'enum lowercase
    op.execute(sa.text("DROP TYPE eventtype"))

    # 5. Recréer l'enum avec valeurs uppercase
    op.execute(sa.text("""
        CREATE TYPE eventtype AS ENUM (
            'SHOW', 'DAY_OFF', 'TRAVEL', 'STUDIO', 'PROMO',
            'REHEARSAL', 'PRESS', 'MEET_GREET', 'PHOTO_VIDEO', 'OTHER'
        )
    """))

    # 6. Reconvertir la colonne
    op.execute(sa.text("ALTER TABLE tour_stops ALTER COLUMN event_type TYPE eventtype USING event_type::eventtype"))

    # 7. Remettre la valeur par défaut
    op.execute(sa.text("ALTER TABLE tour_stops ALTER COLUMN event_type SET DEFAULT 'SHOW'"))
