"""
Planning slot model for daily concert staff scheduling.
"""
from datetime import datetime, time
from app.extensions import db


class PlanningSlot(db.Model):
    """A time slot in the daily concert planning grid."""
    __tablename__ = 'planning_slots'

    id = db.Column(db.Integer, primary_key=True)
    tour_stop_id = db.Column(db.Integer, db.ForeignKey('tour_stops.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    profession_id = db.Column(db.Integer, db.ForeignKey('professions.id', ondelete='SET NULL'), nullable=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    task_description = db.Column(db.String(200), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tour_stop = db.relationship('TourStop', backref=db.backref('planning_slots', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('planning_slots', lazy='dynamic'))
    profession = db.relationship('Profession', backref=db.backref('planning_slots', lazy='dynamic'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    @property
    def effective_profession(self):
        """Get the profession - from slot or from user's primary profession."""
        if self.profession:
            return self.profession
        if self.user and self.user.primary_profession:
            return self.user.primary_profession
        return None

    @property
    def category(self):
        """Get the profession category for styling."""
        prof = self.effective_profession
        if prof and prof.category:
            return prof.category.value
        return 'production'  # Default category

    @property
    def category_color(self):
        """Get color based on category."""
        colors = {
            'musicien': '#8b5cf6',
            'technicien': '#3b82f6',
            'securite': '#ef4444',
            'management': '#22c55e',
            'style': '#ec4899',
            'production': '#f97316'
        }
        return colors.get(self.category, '#6b7280')

    @property
    def time_range(self):
        """Format time range as HH:MM-HH:MM."""
        return f"{self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"

    @property
    def grid_start(self):
        """Calculate CSS grid column start (1-based, starting from 01:00)."""
        # Grid starts at 01:00 (column 1)
        # 00:00 is column 24
        hour = self.start_time.hour
        if hour == 0:
            return 24
        return hour

    @property
    def grid_end(self):
        """Calculate CSS grid column end."""
        hour = self.end_time.hour
        if hour == 0:
            return 25  # Spans to end
        return hour + 1

    @property
    def grid_span(self):
        """Calculate number of hours the slot spans."""
        start_h = self.start_time.hour if self.start_time.hour > 0 else 24
        end_h = self.end_time.hour if self.end_time.hour > 0 else 24
        if end_h <= start_h:
            end_h += 24
        return end_h - start_h

    def to_dict(self):
        """Convert to dictionary for JSON API."""
        return {
            'id': self.id,
            'tour_stop_id': self.tour_stop_id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else 'Unknown',
            'profession_id': self.profession_id,
            'profession_name': self.effective_profession.name_fr if self.effective_profession else None,
            'category': self.category,
            'category_color': self.category_color,
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M'),
            'time_range': self.time_range,
            'task_description': self.task_description,
            'grid_start': self.grid_start,
            'grid_end': self.grid_end
        }

    def __repr__(self):
        return f'<PlanningSlot {self.id}: {self.time_range} - {self.task_description[:30]}>'
