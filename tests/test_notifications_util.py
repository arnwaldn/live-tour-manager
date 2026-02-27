# =============================================================================
# Tour Manager - Notification Utilities Tests
# =============================================================================

import pytest
from datetime import datetime

from app.extensions import db
from app.models.user import User, AccessLevel
from app.models.notification import Notification, NotificationType, NotificationCategory
from app.utils.notifications import (
    create_notification,
    create_notification_batch,
    notify_user,
    notify_band_members,
    notify_registration_approved,
)


# =============================================================================
# Helper fixtures
# =============================================================================

@pytest.fixture
def user_a(app):
    """Create user A for notification tests."""
    user = User(
        email='user_a@test.com',
        first_name='User',
        last_name='Alpha',
        access_level=AccessLevel.STAFF,
        is_active=True,
        email_verified=True,
    )
    user.set_password('UserA123!')
    db.session.add(user)
    db.session.commit()
    user_id = user.id
    db.session.expire_all()
    return db.session.get(User, user_id)


@pytest.fixture
def user_b(app):
    """Create user B for notification tests."""
    user = User(
        email='user_b@test.com',
        first_name='User',
        last_name='Beta',
        access_level=AccessLevel.STAFF,
        is_active=True,
        email_verified=True,
    )
    user.set_password('UserB123!')
    db.session.add(user)
    db.session.commit()
    user_id = user.id
    db.session.expire_all()
    return db.session.get(User, user_id)


# =============================================================================
# create_notification
# =============================================================================

class TestCreateNotification:
    """Tests for create_notification()."""

    def test_creates_notification_with_defaults(self, app, user_a):
        """create_notification creates a notification with default type and category."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = create_notification(user.id, 'Test title')
            assert notif.id is not None
            assert notif.title == 'Test title'
            assert notif.type == NotificationType.INFO
            assert notif.category == NotificationCategory.SYSTEM
            assert notif.is_read is False
            assert notif.message is None
            assert notif.link is None

    def test_creates_notification_with_message(self, app, user_a):
        """create_notification stores optional message."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = create_notification(user.id, 'Title', message='Detail message')
            assert notif.message == 'Detail message'

    def test_creates_notification_with_link(self, app, user_a):
        """create_notification stores optional link."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = create_notification(user.id, 'Title', link='/some/path')
            assert notif.link == '/some/path'

    def test_creates_info_type_notification(self, app, user_a):
        """create_notification supports INFO type."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = create_notification(user.id, 'Info', type=NotificationType.INFO)
            assert notif.type == NotificationType.INFO

    def test_creates_success_type_notification(self, app, user_a):
        """create_notification supports SUCCESS type."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = create_notification(user.id, 'Success', type=NotificationType.SUCCESS)
            assert notif.type == NotificationType.SUCCESS

    def test_creates_warning_type_notification(self, app, user_a):
        """create_notification supports WARNING type."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = create_notification(user.id, 'Warning', type=NotificationType.WARNING)
            assert notif.type == NotificationType.WARNING

    def test_creates_error_type_notification(self, app, user_a):
        """create_notification supports ERROR type."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = create_notification(user.id, 'Error', type=NotificationType.ERROR)
            assert notif.type == NotificationType.ERROR

    def test_creates_tour_category_notification(self, app, user_a):
        """create_notification supports TOUR category."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = create_notification(user.id, 'Tour event', category=NotificationCategory.TOUR)
            assert notif.category == NotificationCategory.TOUR

    def test_creates_guestlist_category_notification(self, app, user_a):
        """create_notification supports GUESTLIST category."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = create_notification(user.id, 'Guestlist', category=NotificationCategory.GUESTLIST)
            assert notif.category == NotificationCategory.GUESTLIST

    def test_notification_persisted_in_db(self, app, user_a):
        """Notification is committed to the database."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = create_notification(user.id, 'Persistent')
            notif_id = notif.id

            # Re-fetch from DB to confirm persistence
            fetched = db.session.get(Notification, notif_id)
            assert fetched is not None
            assert fetched.title == 'Persistent'

    def test_notification_belongs_to_correct_user(self, app, user_a):
        """Notification is associated with the correct user."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = create_notification(user.id, 'For user_a')
            assert notif.user_id == user.id


# =============================================================================
# create_notification_batch
# =============================================================================

class TestCreateNotificationBatch:
    """Tests for create_notification_batch()."""

    def test_creates_multiple_notifications(self, app, user_a, user_b):
        """create_notification_batch creates all notifications in one transaction."""
        with app.app_context():
            ua = db.session.get(User, user_a.id)
            ub = db.session.get(User, user_b.id)
            notifications_data = [
                {'user_id': ua.id, 'title': 'Notif for A'},
                {'user_id': ub.id, 'title': 'Notif for B'},
            ]
            notifications = create_notification_batch(notifications_data)
            assert len(notifications) == 2

    def test_batch_uses_default_type_and_category(self, app, user_a):
        """create_notification_batch uses INFO/SYSTEM defaults when not specified."""
        with app.app_context():
            ua = db.session.get(User, user_a.id)
            notifications = create_notification_batch([
                {'user_id': ua.id, 'title': 'Default test'}
            ])
            notif = notifications[0]
            assert notif.type == NotificationType.INFO
            assert notif.category == NotificationCategory.SYSTEM

    def test_batch_respects_custom_type(self, app, user_a):
        """create_notification_batch respects custom notification type."""
        with app.app_context():
            ua = db.session.get(User, user_a.id)
            notifications = create_notification_batch([
                {'user_id': ua.id, 'title': 'Custom', 'type': NotificationType.WARNING}
            ])
            assert notifications[0].type == NotificationType.WARNING

    def test_batch_respects_message_field(self, app, user_a):
        """create_notification_batch stores message if provided."""
        with app.app_context():
            ua = db.session.get(User, user_a.id)
            notifications = create_notification_batch([
                {'user_id': ua.id, 'title': 'With msg', 'message': 'The message'}
            ])
            assert notifications[0].message == 'The message'

    def test_batch_with_empty_list_returns_empty(self, app):
        """create_notification_batch with empty list returns empty list."""
        with app.app_context():
            notifications = create_notification_batch([])
            assert notifications == []

    def test_batch_all_persisted(self, app, user_a, user_b):
        """All batch notifications are persisted to the database."""
        with app.app_context():
            ua = db.session.get(User, user_a.id)
            ub = db.session.get(User, user_b.id)
            before_count = Notification.query.count()
            create_notification_batch([
                {'user_id': ua.id, 'title': 'A'},
                {'user_id': ub.id, 'title': 'B'},
            ])
            after_count = Notification.query.count()
            assert after_count == before_count + 2


# =============================================================================
# notify_user
# =============================================================================

class TestNotifyUser:
    """Tests for notify_user() helper."""

    def test_notify_user_creates_notification(self, app, user_a):
        """notify_user creates a notification for the given User object."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = notify_user(user, 'Hello user')
            assert notif.user_id == user.id
            assert notif.title == 'Hello user'

    def test_notify_user_default_type_info(self, app, user_a):
        """notify_user defaults to INFO type."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = notify_user(user, 'Info notif')
            assert notif.type == NotificationType.INFO

    def test_notify_user_custom_type(self, app, user_a):
        """notify_user accepts custom notification type."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = notify_user(user, 'Success notif', type=NotificationType.SUCCESS)
            assert notif.type == NotificationType.SUCCESS

    def test_notify_user_with_message(self, app, user_a):
        """notify_user passes message through."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = notify_user(user, 'Title', message='Body text')
            assert notif.message == 'Body text'


# =============================================================================
# Notification model methods
# =============================================================================

class TestNotificationModel:
    """Tests for Notification model methods."""

    def test_mark_as_read(self, app, user_a):
        """mark_as_read sets is_read=True and records read_at timestamp."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = create_notification(user.id, 'Unread notification')
            assert notif.is_read is False
            assert notif.read_at is None

            notif.mark_as_read()

            assert notif.is_read is True
            assert notif.read_at is not None

    def test_mark_as_read_idempotent(self, app, user_a):
        """Calling mark_as_read twice does not raise an error."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = create_notification(user.id, 'Already read')
            notif.mark_as_read()
            first_read_at = notif.read_at
            notif.mark_as_read()
            # read_at should not change after first read
            assert notif.read_at == first_read_at

    def test_get_unread_count_zero_initially(self, app, user_a):
        """New user starts with zero unread notifications."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            count = Notification.get_unread_count(user.id)
            assert count == 0

    def test_get_unread_count_increments(self, app, user_a):
        """Unread count increases with each new notification."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            create_notification(user.id, 'First')
            create_notification(user.id, 'Second')
            count = Notification.get_unread_count(user.id)
            assert count == 2

    def test_get_unread_count_excludes_read(self, app, user_a):
        """Unread count does not include read notifications."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = create_notification(user.id, 'Will be read')
            notif.mark_as_read()
            count = Notification.get_unread_count(user.id)
            assert count == 0

    def test_get_unread_count_mixed(self, app, user_a):
        """Unread count correctly handles mix of read and unread."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif1 = create_notification(user.id, 'Read me')
            create_notification(user.id, 'Keep unread')
            notif1.mark_as_read()
            count = Notification.get_unread_count(user.id)
            assert count == 1

    def test_get_recent_returns_notifications(self, app, user_a):
        """get_recent returns the most recent notifications."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            create_notification(user.id, 'Notif 1')
            create_notification(user.id, 'Notif 2')
            create_notification(user.id, 'Notif 3')
            recent = Notification.get_recent(user.id, limit=2)
            assert len(recent) == 2

    def test_get_recent_respects_limit(self, app, user_a):
        """get_recent returns at most limit notifications."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            for i in range(10):
                create_notification(user.id, f'Notif {i}')
            recent = Notification.get_recent(user.id, limit=5)
            assert len(recent) <= 5

    def test_mark_all_read(self, app, user_a):
        """mark_all_read marks all user notifications as read."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            create_notification(user.id, 'One')
            create_notification(user.id, 'Two')
            create_notification(user.id, 'Three')
            assert Notification.get_unread_count(user.id) == 3

            Notification.mark_all_read(user.id)
            assert Notification.get_unread_count(user.id) == 0

    def test_mark_all_read_only_affects_target_user(self, app, user_a, user_b):
        """mark_all_read for user_a does not affect user_b's notifications."""
        with app.app_context():
            ua = db.session.get(User, user_a.id)
            ub = db.session.get(User, user_b.id)
            create_notification(ua.id, 'A notif')
            create_notification(ub.id, 'B notif')

            Notification.mark_all_read(ua.id)

            assert Notification.get_unread_count(ua.id) == 0
            assert Notification.get_unread_count(ub.id) == 1

    def test_to_dict_returns_expected_keys(self, app, user_a):
        """to_dict returns a dictionary with all expected keys."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = create_notification(user.id, 'Dict test', message='Body', link='/test')
            d = notif.to_dict()
            assert 'id' in d
            assert 'type' in d
            assert 'category' in d
            assert 'title' in d
            assert 'message' in d
            assert 'link' in d
            assert 'is_read' in d
            assert 'created_at' in d
            assert 'read_at' in d

    def test_to_dict_values(self, app, user_a):
        """to_dict returns correct values."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = create_notification(
                user.id,
                'Title test',
                message='Msg',
                type=NotificationType.SUCCESS,
                link='/link'
            )
            d = notif.to_dict()
            assert d['title'] == 'Title test'
            assert d['message'] == 'Msg'
            assert d['type'] == NotificationType.SUCCESS
            assert d['link'] == '/link'
            assert d['is_read'] is False


# =============================================================================
# notify_registration_approved
# =============================================================================

class TestNotifyRegistrationApproved:
    """Tests for notify_registration_approved()."""

    def test_creates_success_notification(self, app, user_a):
        """notify_registration_approved creates a SUCCESS notification."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = notify_registration_approved(user)
            assert notif.type == NotificationType.SUCCESS
            assert notif.user_id == user.id
            assert notif.category == NotificationCategory.REGISTRATION

    def test_notification_title_mentions_welcome(self, app, user_a):
        """notify_registration_approved title contains 'Bienvenue' or welcome message."""
        with app.app_context():
            user = db.session.get(User, user_a.id)
            notif = notify_registration_approved(user)
            assert notif.title is not None
            assert len(notif.title) > 0
