"""
LineupSlot model for managing concert lineup/programming.
Allows managing opening acts, headliners, DJ sets, etc.
"""
from datetime import datetime
import enum

from app.extensions import db


class PerformerType(enum.Enum):
    """Type of performer in the lineup."""
    MAIN_ARTIST = 'main_artist'      # Artiste principal/headliner
    OPENING_ACT = 'opening_act'      # Première partie
    SUPPORT = 'support'              # Artiste de soutien
    DJ_SET = 'dj_set'                # DJ set
    SPECIAL_GUEST = 'special_guest'  # Artiste invité
    OTHER = 'other'                  # Autre


# Labels français pour l'affichage
PERFORMER_TYPE_LABELS = {
    PerformerType.MAIN_ARTIST: 'Artiste Principal',
    PerformerType.OPENING_ACT: 'Première Partie',
    PerformerType.SUPPORT: 'Support',
    PerformerType.DJ_SET: 'DJ Set',
    PerformerType.SPECIAL_GUEST: 'Invité Spécial',
    PerformerType.OTHER: 'Autre',
}


class LineupSlot(db.Model):
    """A slot in the concert lineup/programming."""

    __tablename__ = 'lineup_slots'

    id = db.Column(db.Integer, primary_key=True)

    # Tour stop reference
    tour_stop_id = db.Column(
        db.Integer,
        db.ForeignKey('tour_stops.id'),
        nullable=False,
        index=True
    )

    # Performer information
    performer_name = db.Column(db.String(100), nullable=False)
    performer_type = db.Column(
        db.Enum(PerformerType),
        default=PerformerType.SUPPORT,
        nullable=False
    )

    # Timing
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=True)
    set_length_minutes = db.Column(db.Integer, nullable=True)

    # Order in the lineup (1 = first, 2 = second, etc.)
    order = db.Column(db.Integer, nullable=False, default=1)

    # Additional info
    notes = db.Column(db.Text, nullable=True)
    is_confirmed = db.Column(db.Boolean, default=False, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)

    # Relationships
    tour_stop = db.relationship('TourStop', back_populates='lineup_slots')

    def __repr__(self):
        return f'<LineupSlot {self.performer_name} @ {self.start_time}>'

    @property
    def performer_type_label(self):
        """Get the French label for performer type."""
        return PERFORMER_TYPE_LABELS.get(self.performer_type, 'Autre')

    @property
    def duration_formatted(self):
        """Get formatted duration string."""
        if self.set_length_minutes:
            hours = self.set_length_minutes // 60
            minutes = self.set_length_minutes % 60
            if hours > 0:
                return f"{hours}h{minutes:02d}" if minutes else f"{hours}h"
            return f"{minutes} min"
        elif self.start_time and self.end_time:
            # Calculate from times
            start_minutes = self.start_time.hour * 60 + self.start_time.minute
            end_minutes = self.end_time.hour * 60 + self.end_time.minute
            if end_minutes < start_minutes:  # Passes midnight
                end_minutes += 24 * 60
            duration = end_minutes - start_minutes
            hours = duration // 60
            minutes = duration % 60
            if hours > 0:
                return f"{hours}h{minutes:02d}" if minutes else f"{hours}h"
            return f"{minutes} min"
        return None

    @property
    def time_range_formatted(self):
        """Get formatted time range string."""
        if self.start_time:
            start = self.start_time.strftime('%H:%M')
            if self.end_time:
                end = self.end_time.strftime('%H:%M')
                return f"{start} - {end}"
            return start
        return None

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'tour_stop_id': self.tour_stop_id,
            'performer_name': self.performer_name,
            'performer_type': self.performer_type.value,
            'performer_type_label': self.performer_type_label,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'set_length_minutes': self.set_length_minutes,
            'duration_formatted': self.duration_formatted,
            'time_range_formatted': self.time_range_formatted,
            'order': self.order,
            'notes': self.notes,
            'is_confirmed': self.is_confirmed,
        }
