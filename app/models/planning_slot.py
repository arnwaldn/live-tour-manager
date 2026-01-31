"""
PlanningSlot model for daily concert planning.
Manages time slots for staff on a specific tour stop.
"""
from datetime import datetime
from app.extensions import db


class PlanningSlot(db.Model):
    """A time slot in the daily concert planning."""

    __tablename__ = 'planning_slots'

    id = db.Column(db.Integer, primary_key=True)

    # Tour stop reference
    tour_stop_id = db.Column(
        db.Integer,
        db.ForeignKey('tour_stops.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # User assigned to this slot
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Profession for categorization (optional, uses user's primary if not set)
    profession_id = db.Column(
        db.Integer,
        db.ForeignKey('professions.id', ondelete='SET NULL'),
        nullable=True
    )

    # Time slot (01:00 - 00:00)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    # Task description
    task_description = db.Column(db.String(200), nullable=False)

    # Audit
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tour_stop = db.relationship('TourStop', backref=db.backref('planning_slots', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('planning_slots', lazy='dynamic'))
    profession = db.relationship('Profession', foreign_keys=[profession_id])
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def __repr__(self):
        return f'<PlanningSlot {self.user_id} {self.start_time}-{self.end_time} @ TourStop {self.tour_stop_id}>'

    @property
    def effective_profession(self):
        """Get the profession for this slot (explicit or user's primary)."""
        if self.profession:
            return self.profession
        if self.user and self.user.professions:
            return self.user.professions[0]
        return None

    @property
    def category(self):
        """Get the category of this slot's profession."""
        prof = self.effective_profession
        return prof.category if prof else None

    @property
    def category_value(self):
        """Get the category value string."""
        cat = self.category
        return cat.value if cat else None

    @property
    def time_range(self):
        """Get formatted time range."""
        return f"{self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"

    @property
    def grid_start(self):
        """Calculate CSS grid column start (1-based, starting at 01:00)."""
        hour = self.start_time.hour
        # Adjust for grid starting at 01:00
        if hour == 0:
            return 24  # Midnight maps to column 24
        return hour

    @property
    def grid_end(self):
        """Calculate CSS grid column end."""
        hour = self.end_time.hour
        if hour == 0:
            return 25  # Midnight end maps to column 25
        return hour + 1

    @property
    def grid_span(self):
        """Calculate number of hours this slot spans."""
        start_h = self.start_time.hour if self.start_time.hour != 0 else 24
        end_h = self.end_time.hour if self.end_time.hour != 0 else 24
        if end_h <= start_h:
            end_h += 24
        return end_h - start_h

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'tour_stop_id': self.tour_stop_id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else None,
            'profession_id': self.profession_id,
            'profession_name': self.effective_profession.name_fr if self.effective_profession else None,
            'category': self.category_value,
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M'),
            'time_range': self.time_range,
            'task_description': self.task_description,
            'grid_start': self.grid_start,
            'grid_end': self.grid_end,
        }
