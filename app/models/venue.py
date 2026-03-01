"""
Venue and VenueContact models.
"""
from datetime import datetime

from app.extensions import db


class Venue(db.Model):
    """Venue model for concert locations."""

    __tablename__ = 'venues'

    id = db.Column(db.Integer, primary_key=True)

    # Organization (tenant isolation)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False, index=True)

    name = db.Column(db.String(100), nullable=False, index=True)
    address = db.Column(db.String(255))
    city = db.Column(db.String(100), nullable=False, index=True)
    state = db.Column(db.String(100))
    country = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20))

    # GPS Coordinates (pour cartes Leaflet/OpenStreetMap)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    # Timezone (IANA format, e.g., 'Europe/Paris', 'America/New_York')
    timezone = db.Column(db.String(50), default='Europe/Paris')

    capacity = db.Column(db.Integer)
    venue_type = db.Column(db.String(50))  # Club, Theater, Arena, Festival, etc.
    website = db.Column(db.String(255))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    notes = db.Column(db.Text)

    # Technical specifications
    technical_specs = db.Column(db.Text)  # General technical specs
    stage_dimensions = db.Column(db.String(100))
    load_in_info = db.Column(db.Text)
    parking_info = db.Column(db.Text)
    backline_available = db.Column(db.Boolean, default=False)
    backline_details = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = db.relationship('Organization', back_populates='venues')

    contacts = db.relationship(
        'VenueContact',
        back_populates='venue',
        cascade='all, delete-orphan'
    )

    tour_stops = db.relationship(
        'TourStop',
        back_populates='venue'
    )

    def __repr__(self):
        return f'<Venue {self.name}, {self.city}>'

    @property
    def full_address(self):
        """Return formatted full address."""
        parts = [self.address, self.city]
        if self.state:
            parts.append(self.state)
        parts.append(self.country)
        if self.postal_code:
            parts.append(self.postal_code)
        return ', '.join(filter(None, parts))

    @property
    def primary_contact(self):
        """Get the primary contact for this venue."""
        primary = [c for c in self.contacts if c.is_primary]
        return primary[0] if primary else (self.contacts[0] if self.contacts else None)

    @property
    def has_coordinates(self):
        """Check if GPS coordinates are available."""
        return self.latitude is not None and self.longitude is not None

    @property
    def map_url(self):
        """Get OpenStreetMap URL for this venue."""
        if self.has_coordinates:
            return f"https://www.openstreetmap.org/?mlat={self.latitude}&mlon={self.longitude}&zoom=16"
        return None

    @property
    def google_maps_url(self):
        """Get Google Maps URL for this venue."""
        if self.has_coordinates:
            return f"https://www.google.com/maps?q={self.latitude},{self.longitude}"
        # Fallback to address search
        import urllib.parse
        return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(self.full_address)}"

    def geocode(self):
        """
        Geocode this venue's address using Nominatim.
        Returns (lat, lon) tuple or (None, None) if geocoding fails.
        """
        from app.utils.geocoding import geocode_address
        if self.address and self.city and self.country:
            lat, lon = geocode_address(self.address, self.city, self.country)
            if lat and lon:
                self.latitude = lat
                self.longitude = lon
            return lat, lon
        return None, None


class VenueContact(db.Model):
    """Contact person at a venue."""

    __tablename__ = 'venue_contacts'

    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50))  # Booker, Production Manager, Sound Engineer, etc.
    email = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    is_primary = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    venue = db.relationship('Venue', back_populates='contacts')

    def __repr__(self):
        return f'<VenueContact {self.name} at {self.venue.name if self.venue else "?"}>'
