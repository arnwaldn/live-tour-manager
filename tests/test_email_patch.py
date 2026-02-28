# =============================================================================
# Tour Manager - Email Patch Tests
# =============================================================================

import pytest
from app.utils.email_patch import _user_accepts_notification
from app.extensions import db
from app.models.user import User


class TestUserAcceptsNotification:
    """Tests for _user_accepts_notification()."""

    def test_unknown_email_returns_true(self, app):
        """External users (not in DB) should receive notifications by default."""
        result = _user_accepts_notification('external@example.com', 'notify_guestlist_request')
        assert result is True

    def test_user_with_preference_true(self, app, manager_user):
        """User with preference set to True should accept."""
        manager_user.notify_guestlist_request = True
        db.session.commit()
        result = _user_accepts_notification(manager_user.email, 'notify_guestlist_request')
        assert result is True

    def test_user_without_preference_attr_returns_true(self, app, manager_user):
        """User without the specific preference attribute defaults to True."""
        result = _user_accepts_notification(manager_user.email, 'nonexistent_preference')
        assert result is True
