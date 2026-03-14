"""
Device token model for push notifications (FCM).
Stores FCM registration tokens per user/device.
"""
from datetime import datetime

from app.extensions import db


class DeviceToken(db.Model):
    """FCM device token linked to a user."""

    __tablename__ = 'device_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(500), nullable=False, unique=True)
    platform = db.Column(db.String(20), default='android')  # android, ios, web
    device_name = db.Column(db.String(100))  # optional label
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref(
        'device_tokens', lazy='dynamic', cascade='all, delete-orphan',
    ))

    __table_args__ = (
        db.Index('ix_device_tokens_user', 'user_id'),
    )

    def __repr__(self):
        return f'<DeviceToken {self.id} user={self.user_id} platform={self.platform}>'

    @classmethod
    def get_active_tokens(cls, user_id):
        """Get all active FCM tokens for a user."""
        return cls.query.filter_by(user_id=user_id, is_active=True).all()

    @classmethod
    def get_active_tokens_for_users(cls, user_ids):
        """Get all active FCM tokens for multiple users."""
        return cls.query.filter(
            cls.user_id.in_(user_ids),
            cls.is_active == True,  # noqa: E712
        ).all()

    @classmethod
    def register_token(cls, user_id, token, platform='android', device_name=None):
        """Register or update a device token for a user."""
        existing = cls.query.filter_by(token=token).first()
        if existing:
            # Token exists — reassign to current user if needed
            existing.user_id = user_id
            existing.platform = platform
            existing.device_name = device_name
            existing.is_active = True
            existing.updated_at = datetime.utcnow()
        else:
            existing = cls(
                user_id=user_id,
                token=token,
                platform=platform,
                device_name=device_name,
            )
            db.session.add(existing)
        db.session.commit()
        return existing

    @classmethod
    def unregister_token(cls, token):
        """Deactivate a device token."""
        existing = cls.query.filter_by(token=token).first()
        if existing:
            existing.is_active = False
            db.session.commit()
        return existing
