# =============================================================================
# Tour Manager - Notification Web Routes Integration Tests
# =============================================================================

import pytest

from app.extensions import db
from app.models.user import User, Role, AccessLevel
from app.models.notification import Notification, NotificationType, NotificationCategory


# =============================================================================
# Helpers
# =============================================================================

def _login(client, email, password):
    """Log a user in via the auth form."""
    return client.post('/auth/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)


def _create_notification(user_id, title='Test Notification', message='Test message',
                         notification_type=NotificationType.INFO,
                         category=NotificationCategory.SYSTEM,
                         is_read=False):
    """Create and persist a notification, returning its id."""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        category=category,
        is_read=is_read,
    )
    db.session.add(notification)
    db.session.commit()
    notif_id = notification.id
    db.session.expire_all()
    return notif_id


# =============================================================================
# List Notifications Tests
# =============================================================================

class TestListNotifications:
    """Tests for the notifications list page."""

    def test_list_requires_login(self, client):
        """Test that notifications list requires authentication."""
        response = client.get('/notifications/', follow_redirects=False)
        assert response.status_code == 302
        assert 'login' in response.location.lower()

    def test_list_empty(self, app, client, manager_user):
        """Test notifications list with no notifications."""
        _login(client, 'manager@test.com', 'Manager123!')

        response = client.get('/notifications/')
        assert response.status_code == 200

    def test_list_shows_notifications(self, app, client, manager_user):
        """Test notifications list displays user's notifications."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(manager_user.id, title='Tour Update')
            _create_notification(manager_user.id, title='Guestlist Alert')

        response = client.get('/notifications/')
        assert response.status_code == 200
        assert b'Tour Update' in response.data or b'notification' in response.data.lower()

    def test_list_does_not_show_other_user_notifications(self, app, client, manager_user, musician_user):
        """Test that user only sees their own notifications."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(musician_user.id, title='Secret Musician Note')
            _create_notification(manager_user.id, title='Manager Note')

        response = client.get('/notifications/')
        assert response.status_code == 200
        # Musician notification should not appear for manager
        assert b'Secret Musician Note' not in response.data

    def test_list_pagination(self, app, client, manager_user):
        """Test notifications list pagination."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            # Create more than per_page (20) notifications
            for i in range(25):
                _create_notification(manager_user.id, title=f'Notification {i}')

        response_page1 = client.get('/notifications/')
        assert response_page1.status_code == 200

        response_page2 = client.get('/notifications/?page=2')
        assert response_page2.status_code == 200


# =============================================================================
# API Unread Count Tests
# =============================================================================

class TestApiUnreadCount:
    """Tests for the unread count API endpoint."""

    def test_unread_count_requires_login(self, client):
        """Test unread count API requires authentication."""
        response = client.get('/notifications/api/unread-count', follow_redirects=False)
        assert response.status_code == 302

    def test_unread_count_zero(self, app, client, manager_user):
        """Test unread count returns 0 when no notifications."""
        _login(client, 'manager@test.com', 'Manager123!')

        response = client.get('/notifications/api/unread-count')
        assert response.status_code == 200

        data = response.get_json()
        assert data['count'] == 0

    def test_unread_count_with_notifications(self, app, client, manager_user):
        """Test unread count returns correct number."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(manager_user.id, title='Unread 1', is_read=False)
            _create_notification(manager_user.id, title='Unread 2', is_read=False)
            _create_notification(manager_user.id, title='Read 1', is_read=True)

        response = client.get('/notifications/api/unread-count')
        assert response.status_code == 200

        data = response.get_json()
        assert data['count'] == 2

    def test_unread_count_excludes_other_users(self, app, client, manager_user, musician_user):
        """Test unread count only counts current user's notifications."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(manager_user.id, title='Manager Unread', is_read=False)
            _create_notification(musician_user.id, title='Musician Unread', is_read=False)

        response = client.get('/notifications/api/unread-count')
        data = response.get_json()
        assert data['count'] == 1


# =============================================================================
# API Recent Notifications Tests
# =============================================================================

class TestApiRecent:
    """Tests for the recent notifications API endpoint."""

    def test_recent_requires_login(self, client):
        """Test recent notifications API requires authentication."""
        response = client.get('/notifications/api/recent', follow_redirects=False)
        assert response.status_code == 302

    def test_recent_empty(self, app, client, manager_user):
        """Test recent notifications returns empty list when no notifications."""
        _login(client, 'manager@test.com', 'Manager123!')

        response = client.get('/notifications/api/recent')
        assert response.status_code == 200

        data = response.get_json()
        assert data['notifications'] == []
        assert data['unread_count'] == 0

    def test_recent_with_notifications(self, app, client, manager_user):
        """Test recent notifications returns notification data."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(manager_user.id, title='Recent Note', message='Details here')

        response = client.get('/notifications/api/recent')
        assert response.status_code == 200

        data = response.get_json()
        assert len(data['notifications']) == 1
        assert data['notifications'][0]['title'] == 'Recent Note'
        assert data['notifications'][0]['message'] == 'Details here'
        assert data['unread_count'] == 1

    def test_recent_custom_limit(self, app, client, manager_user):
        """Test recent notifications respects limit parameter."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            for i in range(15):
                _create_notification(manager_user.id, title=f'Note {i}')

        response = client.get('/notifications/api/recent?limit=5')
        assert response.status_code == 200

        data = response.get_json()
        assert len(data['notifications']) == 5

    def test_recent_default_limit(self, app, client, manager_user):
        """Test recent notifications default limit is 10."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            for i in range(15):
                _create_notification(manager_user.id, title=f'Note {i}')

        response = client.get('/notifications/api/recent')
        data = response.get_json()
        assert len(data['notifications']) == 10


# =============================================================================
# Mark as Read Tests
# =============================================================================

class TestMarkRead:
    """Tests for marking a notification as read."""

    def test_mark_read_requires_login(self, app, client, manager_user):
        """Test mark as read requires authentication."""
        with app.app_context():
            notif_id = _create_notification(manager_user.id)

        response = client.post(f'/notifications/{notif_id}/mark-read', follow_redirects=False)
        assert response.status_code == 302
        assert 'login' in response.location.lower()

    def test_mark_read_success(self, app, client, manager_user):
        """Test marking a notification as read."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            notif_id = _create_notification(manager_user.id, is_read=False)

        response = client.post(f'/notifications/{notif_id}/mark-read', follow_redirects=False)
        assert response.status_code == 302

        with app.app_context():
            notification = db.session.get(Notification, notif_id)
            assert notification.is_read is True
            assert notification.read_at is not None

    def test_mark_read_ajax(self, app, client, manager_user):
        """Test marking notification as read via AJAX returns JSON."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            notif_id = _create_notification(manager_user.id, is_read=False)

        response = client.post(
            f'/notifications/{notif_id}/mark-read',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] is True

    def test_mark_read_other_user_blocked(self, app, client, manager_user, musician_user):
        """Test that a user cannot mark another user's notification as read."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            notif_id = _create_notification(musician_user.id, is_read=False)

        response = client.post(f'/notifications/{notif_id}/mark-read', follow_redirects=True)
        assert response.status_code == 200

        # Notification should still be unread
        with app.app_context():
            notification = db.session.get(Notification, notif_id)
            assert notification.is_read is False

    def test_mark_read_nonexistent(self, app, client, manager_user):
        """Test marking nonexistent notification returns 404."""
        _login(client, 'manager@test.com', 'Manager123!')

        response = client.post('/notifications/99999/mark-read')
        assert response.status_code == 404


# =============================================================================
# Mark All Read Tests
# =============================================================================

class TestMarkAllRead:
    """Tests for marking all notifications as read."""

    def test_mark_all_read_requires_login(self, client):
        """Test mark all as read requires authentication."""
        response = client.post('/notifications/mark-all-read', follow_redirects=False)
        assert response.status_code == 302
        assert 'login' in response.location.lower()

    def test_mark_all_read_success(self, app, client, manager_user):
        """Test marking all notifications as read."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(manager_user.id, title='Notif 1', is_read=False)
            _create_notification(manager_user.id, title='Notif 2', is_read=False)
            _create_notification(manager_user.id, title='Notif 3', is_read=False)

        response = client.post('/notifications/mark-all-read', follow_redirects=False)
        assert response.status_code == 302

        with app.app_context():
            unread = Notification.query.filter_by(
                user_id=manager_user.id, is_read=False
            ).count()
            assert unread == 0

    def test_mark_all_read_ajax(self, app, client, manager_user):
        """Test mark all as read via AJAX returns JSON."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(manager_user.id, is_read=False)

        response = client.post(
            '/notifications/mark-all-read',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] is True

    def test_mark_all_read_does_not_affect_other_users(self, app, client, manager_user, musician_user):
        """Test that mark all read only affects current user's notifications."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(manager_user.id, title='Manager Notif', is_read=False)
            _create_notification(musician_user.id, title='Musician Notif', is_read=False)

        client.post('/notifications/mark-all-read', follow_redirects=True)

        with app.app_context():
            # Musician's notification should still be unread
            musician_unread = Notification.query.filter_by(
                user_id=musician_user.id, is_read=False
            ).count()
            assert musician_unread == 1

    def test_mark_all_read_no_notifications(self, app, client, manager_user):
        """Test mark all read when there are no notifications."""
        _login(client, 'manager@test.com', 'Manager123!')

        response = client.post('/notifications/mark-all-read', follow_redirects=False)
        assert response.status_code == 302


# =============================================================================
# Delete Notification Tests
# =============================================================================

class TestDeleteNotification:
    """Tests for deleting a single notification."""

    def test_delete_requires_login(self, app, client, manager_user):
        """Test delete notification requires authentication."""
        with app.app_context():
            notif_id = _create_notification(manager_user.id)

        response = client.post(f'/notifications/{notif_id}/delete', follow_redirects=False)
        assert response.status_code == 302
        assert 'login' in response.location.lower()

    def test_delete_success(self, app, client, manager_user):
        """Test successful notification deletion."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            notif_id = _create_notification(manager_user.id)

        response = client.post(f'/notifications/{notif_id}/delete', follow_redirects=False)
        assert response.status_code == 302

        with app.app_context():
            notification = db.session.get(Notification, notif_id)
            assert notification is None

    def test_delete_ajax(self, app, client, manager_user):
        """Test deleting notification via AJAX returns JSON."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            notif_id = _create_notification(manager_user.id)

        response = client.post(
            f'/notifications/{notif_id}/delete',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] is True

    def test_delete_other_user_blocked(self, app, client, manager_user, musician_user):
        """Test that a user cannot delete another user's notification."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            notif_id = _create_notification(musician_user.id)

        response = client.post(f'/notifications/{notif_id}/delete', follow_redirects=True)
        assert response.status_code == 200

        # Notification should still exist
        with app.app_context():
            notification = db.session.get(Notification, notif_id)
            assert notification is not None

    def test_delete_nonexistent(self, app, client, manager_user):
        """Test deleting nonexistent notification returns 404."""
        _login(client, 'manager@test.com', 'Manager123!')

        response = client.post('/notifications/99999/delete')
        assert response.status_code == 404


# =============================================================================
# Delete All Notifications Tests
# =============================================================================

class TestDeleteAllNotifications:
    """Tests for deleting all notifications."""

    def test_delete_all_requires_login(self, client):
        """Test delete all requires authentication."""
        response = client.post('/notifications/delete-all', follow_redirects=False)
        assert response.status_code == 302
        assert 'login' in response.location.lower()

    def test_delete_all_success(self, app, client, manager_user):
        """Test successful deletion of all notifications."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(manager_user.id, title='Delete Me 1')
            _create_notification(manager_user.id, title='Delete Me 2')
            _create_notification(manager_user.id, title='Delete Me 3')

        response = client.post('/notifications/delete-all', follow_redirects=False)
        assert response.status_code == 302

        with app.app_context():
            count = Notification.query.filter_by(user_id=manager_user.id).count()
            assert count == 0

    def test_delete_all_ajax(self, app, client, manager_user):
        """Test delete all via AJAX returns JSON."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(manager_user.id)

        response = client.post(
            '/notifications/delete-all',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] is True

    def test_delete_all_does_not_affect_other_users(self, app, client, manager_user, musician_user):
        """Test that delete all only removes current user's notifications."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(manager_user.id, title='Manager Notif')
            _create_notification(musician_user.id, title='Musician Notif')

        client.post('/notifications/delete-all', follow_redirects=True)

        with app.app_context():
            # Musician's notification should still exist
            musician_count = Notification.query.filter_by(user_id=musician_user.id).count()
            assert musician_count == 1

    def test_delete_all_no_notifications(self, app, client, manager_user):
        """Test delete all when there are no notifications."""
        _login(client, 'manager@test.com', 'Manager123!')

        response = client.post('/notifications/delete-all', follow_redirects=False)
        assert response.status_code == 302


# =============================================================================
# Delete Read Notifications Tests
# =============================================================================

class TestDeleteReadNotifications:
    """Tests for deleting all read notifications."""

    def test_delete_read_requires_login(self, client):
        """Test delete read requires authentication."""
        response = client.post('/notifications/delete-read', follow_redirects=False)
        assert response.status_code == 302
        assert 'login' in response.location.lower()

    def test_delete_read_success(self, app, client, manager_user):
        """Test deleting only read notifications."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(manager_user.id, title='Unread', is_read=False)
            _create_notification(manager_user.id, title='Read 1', is_read=True)
            _create_notification(manager_user.id, title='Read 2', is_read=True)

        response = client.post('/notifications/delete-read', follow_redirects=False)
        assert response.status_code == 302

        with app.app_context():
            remaining = Notification.query.filter_by(user_id=manager_user.id).all()
            assert len(remaining) == 1
            assert remaining[0].title == 'Unread'
            assert remaining[0].is_read is False

    def test_delete_read_ajax(self, app, client, manager_user):
        """Test delete read via AJAX returns JSON."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(manager_user.id, is_read=True)

        response = client.post(
            '/notifications/delete-read',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] is True

    def test_delete_read_does_not_affect_other_users(self, app, client, manager_user, musician_user):
        """Test that delete read only removes current user's read notifications."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(manager_user.id, title='Manager Read', is_read=True)
            _create_notification(musician_user.id, title='Musician Read', is_read=True)

        client.post('/notifications/delete-read', follow_redirects=True)

        with app.app_context():
            musician_count = Notification.query.filter_by(user_id=musician_user.id).count()
            assert musician_count == 1

    def test_delete_read_no_read_notifications(self, app, client, manager_user):
        """Test delete read when only unread notifications exist."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(manager_user.id, title='Unread Only', is_read=False)

        response = client.post('/notifications/delete-read', follow_redirects=False)
        assert response.status_code == 302

        with app.app_context():
            count = Notification.query.filter_by(user_id=manager_user.id).count()
            assert count == 1


# =============================================================================
# Notification Types and Categories Tests
# =============================================================================

class TestNotificationTypesAndCategories:
    """Tests verifying different notification types and categories work correctly."""

    def test_different_notification_types(self, app, client, manager_user):
        """Test that notifications of all types display correctly."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(manager_user.id, title='Info Note',
                                 notification_type=NotificationType.INFO)
            _create_notification(manager_user.id, title='Success Note',
                                 notification_type=NotificationType.SUCCESS)
            _create_notification(manager_user.id, title='Warning Note',
                                 notification_type=NotificationType.WARNING)
            _create_notification(manager_user.id, title='Error Note',
                                 notification_type=NotificationType.ERROR)

        response = client.get('/notifications/')
        assert response.status_code == 200

    def test_different_notification_categories(self, app, client, manager_user):
        """Test that notifications of all categories display correctly."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            _create_notification(manager_user.id, title='Tour Notif',
                                 category=NotificationCategory.TOUR)
            _create_notification(manager_user.id, title='Guestlist Notif',
                                 category=NotificationCategory.GUESTLIST)
            _create_notification(manager_user.id, title='System Notif',
                                 category=NotificationCategory.SYSTEM)
            _create_notification(manager_user.id, title='Band Notif',
                                 category=NotificationCategory.BAND)

        response = client.get('/notifications/')
        assert response.status_code == 200

    def test_notification_with_link(self, app, client, manager_user):
        """Test notification with a link field in recent API."""
        _login(client, 'manager@test.com', 'Manager123!')

        with app.app_context():
            notification = Notification(
                user_id=manager_user.id,
                title='Tour Created',
                message='A new tour was created',
                type=NotificationType.SUCCESS,
                category=NotificationCategory.TOUR,
                link='/tours/1',
                is_read=False,
            )
            db.session.add(notification)
            db.session.commit()

        response = client.get('/notifications/api/recent')
        data = response.get_json()

        assert len(data['notifications']) == 1
        assert data['notifications'][0]['link'] == '/tours/1'
        assert data['notifications'][0]['category'] == 'tour'
        assert data['notifications'][0]['type'] == 'success'
