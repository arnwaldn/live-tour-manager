"""System settings model for storing app configuration.

Supports per-organization settings with fallback to global defaults.
When org_id is provided, the lookup chain is: org-specific → global (org_id=NULL).
"""
from datetime import datetime
from cryptography.fernet import Fernet
from flask import current_app
import base64
import hashlib
from app.extensions import db


class SystemSettings(db.Model):
    """Key-value store for system settings with optional encryption.

    org_id=NULL means global/default setting.
    org_id=<int> means org-specific override.
    """

    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True, index=True)
    key = db.Column(db.String(100), nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    is_encrypted = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationships
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    organization = db.relationship('Organization', foreign_keys=[org_id])

    @classmethod
    def _get_fernet(cls):
        """Get Fernet instance for encryption/decryption.

        Uses dedicated FERNET_KEY if set, otherwise derives from SECRET_KEY.
        """
        fernet_key = current_app.config.get('FERNET_KEY')
        if fernet_key:
            return Fernet(fernet_key.encode() if isinstance(fernet_key, str) else fernet_key)
        key = current_app.config['SECRET_KEY']
        key_bytes = hashlib.sha256(key.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key_bytes))

    @classmethod
    def _decrypt_value(cls, setting, default=None):
        """Decrypt a setting's value if encrypted, otherwise return raw."""
        if setting.is_encrypted and setting.value:
            try:
                fernet = cls._get_fernet()
                return fernet.decrypt(setting.value.encode()).decode()
            except Exception:
                return default
        return setting.value

    @classmethod
    def get(cls, key, default=None, org_id=None):
        """Get a setting value by key with org fallback.

        Lookup order:
        1. Org-specific setting (if org_id provided)
        2. Global setting (org_id=NULL)
        3. default parameter
        """
        if org_id is not None:
            setting = cls.query.filter_by(key=key, org_id=org_id).first()
            if setting:
                return cls._decrypt_value(setting, default)

        # Fallback to global
        setting = cls.query.filter_by(key=key, org_id=None).first()
        if setting:
            return cls._decrypt_value(setting, default)

        return default

    @classmethod
    def set(cls, key, value, encrypted=False, user_id=None, org_id=None):
        """Set a setting value for a specific org (or global if org_id=None)."""
        setting = cls.query.filter_by(key=key, org_id=org_id).first()
        if not setting:
            setting = cls(key=key, org_id=org_id)
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
    def delete(cls, key, org_id=None):
        """Delete a setting by key for a specific org (or global)."""
        setting = cls.query.filter_by(key=key, org_id=org_id).first()
        if setting:
            db.session.delete(setting)
            return True
        return False

    @classmethod
    def get_mail_config(cls, org_id=None):
        """Get all mail configuration as dict with org fallback."""
        return {
            'MAIL_SERVER': cls.get('MAIL_SERVER', org_id=org_id),
            'MAIL_PORT': cls.get('MAIL_PORT', org_id=org_id),
            'MAIL_USE_TLS': cls.get('MAIL_USE_TLS', org_id=org_id),
            'MAIL_USERNAME': cls.get('MAIL_USERNAME', org_id=org_id),
            'MAIL_PASSWORD': cls.get('MAIL_PASSWORD', org_id=org_id),
            'MAIL_DEFAULT_SENDER': cls.get('MAIL_DEFAULT_SENDER', org_id=org_id),
        }

    @classmethod
    def get_mail_config_timestamp(cls, org_id=None):
        """Get the timestamp of the last mail config update."""
        if org_id is not None:
            setting = cls.query.filter_by(key='MAIL_CONFIG_UPDATED_AT', org_id=org_id).first()
            if setting and setting.value:
                try:
                    return float(setting.value)
                except (ValueError, TypeError):
                    pass

        setting = cls.query.filter_by(key='MAIL_CONFIG_UPDATED_AT', org_id=None).first()
        if setting and setting.value:
            try:
                return float(setting.value)
            except (ValueError, TypeError):
                return 0
        return 0

    @classmethod
    def touch_mail_config(cls, org_id=None):
        """Update the mail config timestamp to trigger reload on all workers."""
        import time
        cls.set('MAIL_CONFIG_UPDATED_AT', str(time.time()), org_id=org_id)

    def __repr__(self):
        org_label = f' org={self.org_id}' if self.org_id else ' global'
        return f'<SystemSettings {self.key}{org_label}>'
