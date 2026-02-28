"""
Security Breach model for RGPD Art. 33-34 breach notification compliance.
"""
import enum
from datetime import datetime

from app.extensions import db


class BreachSeverity(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BreachStatus(enum.Enum):
    DECLARED = "declared"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    NOTIFIED = "notified"        # CNIL notified (Art. 33)
    USERS_NOTIFIED = "users_notified"  # Users notified (Art. 34)
    CLOSED = "closed"


class SecurityBreach(db.Model):
    """
    Tracks security breaches for RGPD Art. 33-34 compliance.

    Art. 33: Notify CNIL within 72 hours of becoming aware.
    Art. 34: Notify affected users without undue delay if high risk.
    """
    __tablename__ = 'security_breaches'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.Enum(BreachSeverity), nullable=False)
    status = db.Column(db.Enum(BreachStatus), default=BreachStatus.DECLARED, nullable=False)

    # What data was affected
    affected_data_types = db.Column(db.Text)  # e.g. "emails, passwords, IBAN"
    estimated_affected_users = db.Column(db.Integer, default=0)

    # Timeline (RGPD Art. 33 requires 72h notification)
    discovered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    contained_at = db.Column(db.DateTime)
    cnil_notified_at = db.Column(db.DateTime)      # Art. 33
    users_notified_at = db.Column(db.DateTime)      # Art. 34

    # Remediation
    remediation_actions = db.Column(db.Text)

    # Audit
    declared_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    declared_by = db.relationship('User', foreign_keys=[declared_by_id])

    def __repr__(self):
        return f'<SecurityBreach {self.id}: {self.title}>'

    @property
    def hours_since_discovery(self):
        """Hours elapsed since breach discovery (72h CNIL deadline)."""
        delta = datetime.utcnow() - self.discovered_at
        return delta.total_seconds() / 3600

    @property
    def cnil_deadline_exceeded(self):
        """Whether the 72-hour CNIL notification deadline has passed."""
        return (
            self.hours_since_discovery > 72
            and self.cnil_notified_at is None
        )
