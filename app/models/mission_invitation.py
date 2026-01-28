"""
MissionInvitation model - tracks invitations sent to members for tour stops.
"""
from datetime import datetime
import enum
import secrets

from app.extensions import db


class MissionInvitationStatus(enum.Enum):
    """Mission invitation status enumeration."""
    PENDING = 'pending'      # En attente de réponse
    ACCEPTED = 'accepted'    # Accepté par le membre
    DECLINED = 'declined'    # Refusé par le membre
    EXPIRED = 'expired'      # Non répondu (délai dépassé)


class MissionInvitation(db.Model):
    """Mission invitation for a band member to a tour stop."""

    __tablename__ = 'mission_invitations'

    # Contrainte unique: un seul invitation par user/tour_stop
    __table_args__ = (
        db.UniqueConstraint('tour_stop_id', 'user_id', name='uq_mission_invitation_stop_user'),
    )

    id = db.Column(db.Integer, primary_key=True)
    tour_stop_id = db.Column(db.Integer, db.ForeignKey('tour_stops.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    status = db.Column(
        db.Enum(MissionInvitationStatus, values_callable=lambda x: [e.value for e in x]),
        default=MissionInvitationStatus.PENDING,
        nullable=False,
        index=True
    )

    # Token sécurisé pour réponse via email
    token = db.Column(db.String(64), unique=True, index=True, nullable=False)

    # Timestamps
    invited_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    responded_at = db.Column(db.DateTime, nullable=True)
    response_note = db.Column(db.Text, nullable=True)  # Raison du refus

    # Rappels
    reminder_sent_at = db.Column(db.DateTime, nullable=True)
    reminder_count = db.Column(db.Integer, default=0)

    # Relations
    tour_stop = db.relationship(
        'TourStop',
        backref=db.backref('mission_invitations', cascade='all, delete-orphan', lazy='dynamic')
    )
    user = db.relationship(
        'User',
        backref=db.backref('mission_invitations', lazy='dynamic')
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.token:
            self.token = self.generate_token()

    def __repr__(self):
        return f'<MissionInvitation {self.id} user={self.user_id} stop={self.tour_stop_id} status={self.status.value}>'

    @staticmethod
    def generate_token():
        """Generate a secure random token for email response links."""
        return secrets.token_urlsafe(32)

    def accept(self, note=None):
        """Accept the mission invitation."""
        self.status = MissionInvitationStatus.ACCEPTED
        self.responded_at = datetime.utcnow()
        if note:
            self.response_note = note
        return True

    def decline(self, note=None):
        """Decline the mission invitation."""
        self.status = MissionInvitationStatus.DECLINED
        self.responded_at = datetime.utcnow()
        self.response_note = note
        return True

    def mark_expired(self):
        """Mark the invitation as expired."""
        self.status = MissionInvitationStatus.EXPIRED
        return True

    def record_reminder(self):
        """Record that a reminder was sent."""
        self.reminder_sent_at = datetime.utcnow()
        self.reminder_count += 1

    def regenerate_token(self):
        """Regenerate the token (for resending invitation)."""
        self.token = self.generate_token()
        return self.token

    @property
    def is_pending(self):
        """Check if invitation is still pending."""
        return self.status == MissionInvitationStatus.PENDING

    @property
    def is_accepted(self):
        """Check if invitation was accepted."""
        return self.status == MissionInvitationStatus.ACCEPTED

    @property
    def is_declined(self):
        """Check if invitation was declined."""
        return self.status == MissionInvitationStatus.DECLINED

    @property
    def status_label(self):
        """Get French label for status."""
        labels = {
            MissionInvitationStatus.PENDING: 'En attente',
            MissionInvitationStatus.ACCEPTED: 'Accepté',
            MissionInvitationStatus.DECLINED: 'Refusé',
            MissionInvitationStatus.EXPIRED: 'Expiré',
        }
        return labels.get(self.status, self.status.value)

    @property
    def status_color(self):
        """Get Bootstrap color class for status."""
        colors = {
            MissionInvitationStatus.PENDING: 'warning',
            MissionInvitationStatus.ACCEPTED: 'success',
            MissionInvitationStatus.DECLINED: 'danger',
            MissionInvitationStatus.EXPIRED: 'secondary',
        }
        return colors.get(self.status, 'secondary')

    @property
    def status_icon(self):
        """Get Bootstrap icon for status."""
        icons = {
            MissionInvitationStatus.PENDING: 'bi-hourglass-split',
            MissionInvitationStatus.ACCEPTED: 'bi-check-circle-fill',
            MissionInvitationStatus.DECLINED: 'bi-x-circle-fill',
            MissionInvitationStatus.EXPIRED: 'bi-clock-history',
        }
        return icons.get(self.status, 'bi-question-circle')

    @classmethod
    def get_by_token(cls, token):
        """Find invitation by token."""
        return cls.query.filter_by(token=token).first()

    @classmethod
    def get_for_stop(cls, tour_stop_id):
        """Get all invitations for a tour stop."""
        return cls.query.filter_by(tour_stop_id=tour_stop_id).all()

    @classmethod
    def get_pending_for_user(cls, user_id):
        """Get all pending invitations for a user."""
        return cls.query.filter_by(
            user_id=user_id,
            status=MissionInvitationStatus.PENDING
        ).all()

    @classmethod
    def create_or_update(cls, tour_stop_id, user_id, send_email=True):
        """
        Create a new invitation or return existing one.

        Args:
            tour_stop_id: TourStop ID
            user_id: User ID
            send_email: Whether to send invitation email

        Returns:
            tuple: (MissionInvitation, created: bool)
        """
        existing = cls.query.filter_by(
            tour_stop_id=tour_stop_id,
            user_id=user_id
        ).first()

        if existing:
            return existing, False

        invitation = cls(
            tour_stop_id=tour_stop_id,
            user_id=user_id
        )
        db.session.add(invitation)
        return invitation, True
