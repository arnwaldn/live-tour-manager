"""
TicketTier model for multi-tier ticket pricing.
Allows multiple price categories per concert (Fosse, Assis, VIP, etc.).
"""
from datetime import datetime

from app.extensions import db


class TicketTier(db.Model):
    """A ticket pricing tier for a tour stop."""

    __tablename__ = 'ticket_tiers'

    id = db.Column(db.Integer, primary_key=True)

    # Tour stop reference
    tour_stop_id = db.Column(
        db.Integer,
        db.ForeignKey('tour_stops.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Tier definition
    name = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Numeric(8, 2), nullable=False)
    quantity_available = db.Column(db.Integer, nullable=True)  # None = illimite
    sold = db.Column(db.Integer, nullable=False, default=0)

    # Display order (0 = first)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)

    # Relationships
    tour_stop = db.relationship('TourStop', back_populates='ticket_tiers')

    def __repr__(self):
        return f'<TicketTier {self.name} @ {self.price}>'

    @property
    def revenue(self):
        """Gross revenue for this tier (price * sold)."""
        return float(self.price or 0) * (self.sold or 0)

    @property
    def is_sold_out(self):
        """Check if this tier is sold out."""
        if self.quantity_available is None:
            return False
        return self.sold >= self.quantity_available

    @property
    def remaining(self):
        """Remaining tickets for this tier (None if unlimited)."""
        if self.quantity_available is None:
            return None
        return max(0, self.quantity_available - (self.sold or 0))

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'tour_stop_id': self.tour_stop_id,
            'name': self.name,
            'price': float(self.price),
            'quantity_available': self.quantity_available,
            'sold': self.sold,
            'revenue': self.revenue,
            'is_sold_out': self.is_sold_out,
            'remaining': self.remaining,
            'sort_order': self.sort_order,
        }
