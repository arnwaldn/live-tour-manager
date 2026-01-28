"""Fix critical inconsistencies - CHECK constraint and NOT NULL

Cette migration corrige les incohérences critiques identifiées dans l'analyse:
- C3: Ajoute CHECK constraint sur tour_stops (tour_id OR band_id required)
- C4: Rend guest_email NOT NULL dans guestlist_entries
- C6: Ajoute index FK manquants pour performance

Revision ID: g7i9k1m3o5p7
Revises: f6h8j0l2n4p6
Create Date: 2026-01-06 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g7i9k1m3o5p7'
down_revision = 'f6h8j0l2n4p6'
branch_labels = None
depends_on = None


def upgrade():
    # C3: Add CHECK constraint - TourStop doit avoir soit tour_id soit band_id
    op.execute(sa.text("""
        ALTER TABLE tour_stops
        ADD CONSTRAINT check_tour_or_band_required
        CHECK (tour_id IS NOT NULL OR band_id IS NOT NULL)
    """))

    # C4: Make guest_email NOT NULL
    # First, update any NULL emails to a placeholder
    op.execute(sa.text("""
        UPDATE guestlist_entries
        SET guest_email = 'unknown@placeholder.temp'
        WHERE guest_email IS NULL
    """))
    # Then make the column NOT NULL
    op.alter_column('guestlist_entries', 'guest_email',
                    existing_type=sa.String(120),
                    nullable=False)

    # C6: Add missing foreign key indexes for performance (IF NOT EXISTS pour éviter erreur si déjà présent)
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_tour_stops_tour_id ON tour_stops (tour_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_tour_stops_band_id ON tour_stops (band_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_tour_stops_venue_id ON tour_stops (venue_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_logistics_info_tour_stop_id ON logistics_info (tour_stop_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_guestlist_entries_guestlist_id ON guestlist_entries (tour_stop_id)"))


def downgrade():
    # Remove indexes
    op.drop_index('ix_guestlist_entries_guestlist_id', table_name='guestlist_entries')
    op.drop_index('ix_logistics_info_tour_stop_id', table_name='logistics_info')
    op.drop_index('ix_tour_stops_venue_id', table_name='tour_stops')
    op.drop_index('ix_tour_stops_band_id', table_name='tour_stops')
    op.drop_index('ix_tour_stops_tour_id', table_name='tour_stops')

    # Make guest_email nullable again
    op.alter_column('guestlist_entries', 'guest_email',
                    existing_type=sa.String(120),
                    nullable=True)

    # Remove CHECK constraint
    op.execute(sa.text("""
        ALTER TABLE tour_stops
        DROP CONSTRAINT check_tour_or_band_required
    """))
