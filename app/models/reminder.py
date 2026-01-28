"""
Model for tracking sent tour stop reminders.
Prevents duplicate reminder emails being sent.
"""
from datetime import datetime
from app.extensions import db


class TourStopReminder(db.Model):
    """Track sent reminders to avoid duplicates."""

    __tablename__ = 'tour_stop_reminders'

    id = db.Column(db.Integer, primary_key=True)
    tour_stop_id = db.Column(
        db.Integer,
        db.ForeignKey('tour_stops.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    reminder_type = db.Column(db.String(10), nullable=False)  # 'j7' or 'j1'
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            'tour_stop_id', 'user_id', 'reminder_type',
            name='uq_reminder_once'
        ),
    )

    # Relationships
    tour_stop = db.relationship(
        'TourStop',
        backref=db.backref('reminders_sent', lazy='dynamic', cascade='all, delete-orphan')
    )
    user = db.relationship(
        'User',
        backref=db.backref('tour_stop_reminders', lazy='dynamic', cascade='all, delete-orphan')
    )

    @classmethod
    def already_sent(cls, tour_stop_id, user_id, reminder_type):
        """Check if a reminder has already been sent."""
        return cls.query.filter_by(
            tour_stop_id=tour_stop_id,
            user_id=user_id,
            reminder_type=reminder_type
        ).first() is not None

    @classmethod
    def mark_sent(cls, tour_stop_id, user_id, reminder_type):
        """Mark a reminder as sent."""
        reminder = cls(
            tour_stop_id=tour_stop_id,
            user_id=user_id,
            reminder_type=reminder_type
        )
        db.session.add(reminder)
        return reminder

    def __repr__(self):
        return f'<TourStopReminder {self.reminder_type} for stop={self.tour_stop_id} user={self.user_id}>'
