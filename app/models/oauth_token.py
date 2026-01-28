"""
OAuth Token model for external calendar integrations.
Supports Google Calendar and Microsoft Outlook.
"""
from datetime import datetime
from enum import Enum

from app.extensions import db


class OAuthProvider(Enum):
    """Supported OAuth providers."""
    GOOGLE = 'google'
    MICROSOFT = 'microsoft'


class OAuthToken(db.Model):
    """
    OAuth Token storage for external calendar integrations.

    Stores access and refresh tokens for Google Calendar and Outlook.
    Supports incremental sync with sync_token for efficiency.
    """

    __tablename__ = 'oauth_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    provider = db.Column(db.String(20), nullable=False, index=True)  # 'google' or 'microsoft'

    # Token data
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text)
    token_type = db.Column(db.String(50), default='Bearer')
    expires_at = db.Column(db.DateTime)

    # Scopes granted
    scopes = db.Column(db.JSON, default=list)

    # Sync data
    sync_token = db.Column(db.Text)  # For incremental sync (Google)
    delta_link = db.Column(db.Text)  # For incremental sync (Microsoft)
    calendar_id = db.Column(db.String(255))  # Selected calendar ID

    # Status
    is_active = db.Column(db.Boolean, default=True)
    last_sync = db.Column(db.DateTime)
    sync_error = db.Column(db.Text)  # Last sync error message

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('oauth_tokens', lazy='dynamic'))

    # Unique constraint: one token per provider per user
    __table_args__ = (
        db.UniqueConstraint('user_id', 'provider', name='uq_user_provider'),
    )

    def __repr__(self):
        return f'<OAuthToken {self.user_id}:{self.provider}>'

    @property
    def is_expired(self):
        """Check if the access token is expired."""
        if not self.expires_at:
            return True
        return datetime.utcnow() >= self.expires_at

    @property
    def is_google(self):
        """Check if this is a Google token."""
        return self.provider == OAuthProvider.GOOGLE.value

    @property
    def is_microsoft(self):
        """Check if this is a Microsoft token."""
        return self.provider == OAuthProvider.MICROSOFT.value

    def update_tokens(self, access_token, refresh_token=None, expires_at=None, scopes=None):
        """
        Update token data after refresh or re-authorization.

        Args:
            access_token: New access token
            refresh_token: New refresh token (optional, may not change)
            expires_at: Token expiration datetime
            scopes: List of granted scopes
        """
        self.access_token = access_token
        if refresh_token:
            self.refresh_token = refresh_token
        if expires_at:
            self.expires_at = expires_at
        if scopes:
            self.scopes = scopes
        self.sync_error = None
        self.updated_at = datetime.utcnow()

    def mark_sync_complete(self, sync_token=None, delta_link=None):
        """
        Mark sync as complete and store sync token for incremental sync.

        Args:
            sync_token: Google Calendar sync token
            delta_link: Microsoft Graph delta link
        """
        self.last_sync = datetime.utcnow()
        self.sync_error = None
        if sync_token:
            self.sync_token = sync_token
        if delta_link:
            self.delta_link = delta_link

    def mark_sync_error(self, error_message):
        """
        Record a sync error.

        Args:
            error_message: Error description
        """
        self.sync_error = str(error_message)[:1000]  # Limit error message length
        self.last_sync = datetime.utcnow()

    def deactivate(self):
        """Deactivate the token (user disconnected the integration)."""
        self.is_active = False
        self.access_token = 'revoked'
        self.refresh_token = None
        self.sync_token = None
        self.delta_link = None

    @classmethod
    def get_for_user(cls, user_id, provider):
        """
        Get active token for a user and provider.

        Args:
            user_id: User ID
            provider: 'google' or 'microsoft'

        Returns:
            OAuthToken or None
        """
        return cls.query.filter_by(
            user_id=user_id,
            provider=provider,
            is_active=True
        ).first()

    @classmethod
    def create_or_update(cls, user_id, provider, access_token, refresh_token=None,
                         expires_at=None, scopes=None, calendar_id=None):
        """
        Create or update OAuth token for a user.

        Args:
            user_id: User ID
            provider: 'google' or 'microsoft'
            access_token: Access token
            refresh_token: Refresh token
            expires_at: Expiration datetime
            scopes: List of granted scopes
            calendar_id: Selected calendar ID

        Returns:
            OAuthToken instance
        """
        token = cls.query.filter_by(user_id=user_id, provider=provider).first()

        if token:
            token.update_tokens(access_token, refresh_token, expires_at, scopes)
            token.is_active = True
            if calendar_id:
                token.calendar_id = calendar_id
        else:
            token = cls(
                user_id=user_id,
                provider=provider,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                scopes=scopes or [],
                calendar_id=calendar_id
            )
            db.session.add(token)

        return token
