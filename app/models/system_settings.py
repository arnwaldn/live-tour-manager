"""System settings model for storing app configuration."""
from datetime import datetime
from cryptography.fernet import Fernet
from flask import current_app
import base64
import hashlib
from app.extensions import db


class SystemSettings(db.Model):
    """Key-value store for system settings with optional encryption."""

    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    is_encrypted = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationship
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])

    @classmethod
    def _get_fernet(cls):
        """Get Fernet instance for encryption/decryption."""
        key = current_app.config['SECRET_KEY']
        # Derive a valid Fernet key from SECRET_KEY
        key_bytes = hashlib.sha256(key.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key_bytes))

    @classmethod
    def get(cls, key, default=None):
        """Get a setting value by key."""
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            return default
        if setting.is_encrypted and setting.value:
            try:
                fernet = cls._get_fernet()
                return fernet.decrypt(setting.value.encode()).decode()
            except Exception:
                return default
        return setting.value

    @classmethod
    def set(cls, key, value, encrypted=False, user_id=None):
        """Set a setting value."""
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            setting = cls(key=key)
            db.session.add(setting)

        if encrypted and value:
            fernet = cls._get_fernet()
            setting.value = fernet.encrypt(value.encode()).decode()
            setting.is_encrypted = True
        else:
            setting.value = value
            setting.is_encrypted = False

        setting.updated_by_id = user_id
        return setting

    @classmethod
    def delete(cls, key):
        """Delete a setting by key."""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            db.session.delete(setting)
            return True
        return False

    @classmethod
    def get_mail_config(cls):
        """Get all mail configuration as dict."""
        return {
            'MAIL_SERVER': cls.get('MAIL_SERVER'),
            'MAIL_PORT': cls.get('MAIL_PORT'),
            'MAIL_USE_TLS': cls.get('MAIL_USE_TLS'),
            'MAIL_USERNAME': cls.get('MAIL_USERNAME'),
            'MAIL_PASSWORD': cls.get('MAIL_PASSWORD'),  # Decrypted automatically
            'MAIL_DEFAULT_SENDER': cls.get('MAIL_DEFAULT_SENDER'),
        }

    @classmethod
    def get_mail_config_timestamp(cls):
        """Get the timestamp of the last mail config update.

        Used for multi-worker environments to detect when config has changed.
        """
        setting = cls.query.filter_by(key='MAIL_CONFIG_UPDATED_AT').first()
        if setting and setting.value:
            try:
                return float(setting.value)
            except (ValueError, TypeError):
                return 0
        return 0

    @classmethod
    def touch_mail_config(cls):
        """Update the mail config timestamp to trigger reload on all workers.

        Call this after saving any mail configuration change.
        """
        import time
        cls.set('MAIL_CONFIG_UPDATED_AT', str(time.time()))

    def __repr__(self):
        return f'<SystemSettings {self.key}>'
