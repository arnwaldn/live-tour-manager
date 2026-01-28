"""Add logistics GPS, status, and enhanced fields.

Revision ID: k0l2m4n6p8r0
Revises: 64bf63b18108
Create Date: 2026-01-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'k0l2m4n6p8r0'
down_revision = '64bf63b18108'
branch_labels = None
depends_on = None


def upgrade():
    """Add new fields to logistics_info table."""
    # Status field
    op.add_column('logistics_info', sa.Column('status', sa.String(20), nullable=True, server_default='pending'))

    # Location - country
    op.add_column('logistics_info', sa.Column('country', sa.String(100), nullable=True))

    # GPS Coordinates for hotels/locations
    op.add_column('logistics_info', sa.Column('latitude', sa.Numeric(10, 7), nullable=True))
    op.add_column('logistics_info', sa.Column('longitude', sa.Numeric(10, 7), nullable=True))

    # Flight specific - terminals and GPS
    op.add_column('logistics_info', sa.Column('departure_terminal', sa.String(20), nullable=True))
    op.add_column('logistics_info', sa.Column('arrival_terminal', sa.String(20), nullable=True))
    op.add_column('logistics_info', sa.Column('departure_lat', sa.Numeric(10, 7), nullable=True))
    op.add_column('logistics_info', sa.Column('departure_lng', sa.Numeric(10, 7), nullable=True))
    op.add_column('logistics_info', sa.Column('arrival_lat', sa.Numeric(10, 7), nullable=True))
    op.add_column('logistics_info', sa.Column('arrival_lng', sa.Numeric(10, 7), nullable=True))

    # Hotel specific - check-in/out times
    op.add_column('logistics_info', sa.Column('check_in_time', sa.Time(), nullable=True))
    op.add_column('logistics_info', sa.Column('check_out_time', sa.Time(), nullable=True))

    # Ground transport specific
    op.add_column('logistics_info', sa.Column('pickup_location', sa.String(255), nullable=True))
    op.add_column('logistics_info', sa.Column('dropoff_location', sa.String(255), nullable=True))
    op.add_column('logistics_info', sa.Column('vehicle_type', sa.String(50), nullable=True))
    op.add_column('logistics_info', sa.Column('driver_name', sa.String(100), nullable=True))
    op.add_column('logistics_info', sa.Column('driver_phone', sa.String(30), nullable=True))


def downgrade():
    """Remove the new fields."""
    op.drop_column('logistics_info', 'driver_phone')
    op.drop_column('logistics_info', 'driver_name')
    op.drop_column('logistics_info', 'vehicle_type')
    op.drop_column('logistics_info', 'dropoff_location')
    op.drop_column('logistics_info', 'pickup_location')
    op.drop_column('logistics_info', 'check_out_time')
    op.drop_column('logistics_info', 'check_in_time')
    op.drop_column('logistics_info', 'arrival_lng')
    op.drop_column('logistics_info', 'arrival_lat')
    op.drop_column('logistics_info', 'departure_lng')
    op.drop_column('logistics_info', 'departure_lat')
    op.drop_column('logistics_info', 'arrival_terminal')
    op.drop_column('logistics_info', 'departure_terminal')
    op.drop_column('logistics_info', 'longitude')
    op.drop_column('logistics_info', 'latitude')
    op.drop_column('logistics_info', 'country')
    op.drop_column('logistics_info', 'status')
