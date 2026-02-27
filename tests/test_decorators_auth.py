# =============================================================================
# Tour Manager - Auth Decorators Tests
# =============================================================================

import pytest
from flask import Flask, g
from flask_login import login_user, logout_user

from app.extensions import db
from app.models.user import User, Role, AccessLevel
from app.decorators.auth import (
    requires_admin,
    requires_manager,
    requires_staff,
    requires_access,
    role_required,
    permission_required,
    ajax_login_required,
)
from tests.conftest import login


# =============================================================================
# Helper fixtures
# =============================================================================

@pytest.fixture
def admin_user(app):
    """Create an admin user."""
    user = User(
        email='admin@test.com',
        first_name='Test',
        last_name='Admin',
        access_level=AccessLevel.ADMIN,
        is_active=True,
        email_verified=True,
    )
    user.set_password('Admin123!')
    db.session.add(user)
    db.session.commit()
    user_id = user.id
    db.session.expire_all()
    return db.session.get(User, user_id)


@pytest.fixture
def viewer_user(app):
    """Create a viewer-level user."""
    user = User(
        email='viewer@test.com',
        first_name='Test',
        last_name='Viewer',
        access_level=AccessLevel.VIEWER,
        is_active=True,
        email_verified=True,
    )
    user.set_password('Viewer123!')
    db.session.add(user)
    db.session.commit()
    user_id = user.id
    db.session.expire_all()
    return db.session.get(User, user_id)


# =============================================================================
# requires_admin decorator
# =============================================================================

class TestRequiresAdmin:
    """Tests for requires_admin decorator."""

    def test_admin_can_access(self, client, admin_user):
        """Admin user can access admin-protected routes."""
        login(client, 'admin@test.com', 'Admin123!')
        # Use admin full reset as a representative admin-protected route
        # We POST and check it doesn't return 403
        response = client.post('/admin/full-reset', follow_redirects=False)
        # Should redirect (302) after success, not 403
        assert response.status_code != 403

    def test_manager_blocked_from_admin_routes(self, client, manager_user):
        """Manager cannot access admin-only routes."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.post('/admin/full-reset', follow_redirects=False)
        assert response.status_code == 403

    def test_musician_blocked_from_admin_routes(self, client, musician_user):
        """Musician cannot access admin-only routes."""
        login(client, 'musician@test.com', 'Musician123!')
        response = client.post('/admin/full-reset', follow_redirects=False)
        assert response.status_code == 403

    def test_unauthenticated_redirected_from_admin_routes(self, client):
        """Unauthenticated user is redirected from admin-only routes."""
        response = client.post('/admin/full-reset', follow_redirects=False)
        assert response.status_code == 302
        assert 'login' in response.location


# =============================================================================
# requires_manager decorator
# =============================================================================

class TestRequiresManager:
    """Tests for requires_manager decorator — tests via User.is_manager_or_above()."""

    def test_admin_is_manager_or_above(self, app, admin_user):
        """Admin passes manager-or-above check."""
        with app.app_context():
            user = db.session.get(User, admin_user.id)
            assert user.is_manager_or_above() is True

    def test_manager_is_manager_or_above(self, app, manager_user):
        """Manager passes manager-or-above check."""
        with app.app_context():
            user = db.session.get(User, manager_user.id)
            assert user.is_manager_or_above() is True

    def test_musician_is_not_manager_or_above(self, app, musician_user):
        """Musician (STAFF level) fails manager-or-above check."""
        with app.app_context():
            user = db.session.get(User, musician_user.id)
            assert user.is_manager_or_above() is False

    def test_viewer_is_not_manager_or_above(self, app, viewer_user):
        """Viewer fails manager-or-above check."""
        with app.app_context():
            user = db.session.get(User, viewer_user.id)
            assert user.is_manager_or_above() is False


# =============================================================================
# requires_staff decorator
# =============================================================================

class TestRequiresStaff:
    """Tests for requires_staff decorator — tests via User.is_staff_or_above()."""

    def test_admin_is_staff_or_above(self, app, admin_user):
        """Admin passes staff-or-above check."""
        with app.app_context():
            user = db.session.get(User, admin_user.id)
            assert user.is_staff_or_above() is True

    def test_manager_is_staff_or_above(self, app, manager_user):
        """Manager passes staff-or-above check."""
        with app.app_context():
            user = db.session.get(User, manager_user.id)
            assert user.is_staff_or_above() is True

    def test_musician_is_staff_or_above(self, app, musician_user):
        """Musician (STAFF level) passes staff-or-above check."""
        with app.app_context():
            user = db.session.get(User, musician_user.id)
            assert user.is_staff_or_above() is True

    def test_viewer_is_not_staff_or_above(self, app, viewer_user):
        """Viewer fails staff-or-above check."""
        with app.app_context():
            user = db.session.get(User, viewer_user.id)
            assert user.is_staff_or_above() is False


# =============================================================================
# requires_access decorator (access level hierarchy)
# =============================================================================

class TestRequiresAccess:
    """Tests for the requires_access decorator via has_access()."""

    def test_admin_has_access_to_admin_level(self, app, admin_user):
        """Admin has access to ADMIN-required resources."""
        with app.app_context():
            user = db.session.get(User, admin_user.id)
            assert user.has_access(AccessLevel.ADMIN) is True

    def test_admin_has_access_to_manager_level(self, app, admin_user):
        """Admin has access to MANAGER-required resources."""
        with app.app_context():
            user = db.session.get(User, admin_user.id)
            assert user.has_access(AccessLevel.MANAGER) is True

    def test_admin_has_access_to_staff_level(self, app, admin_user):
        """Admin has access to STAFF-required resources."""
        with app.app_context():
            user = db.session.get(User, admin_user.id)
            assert user.has_access(AccessLevel.STAFF) is True

    def test_manager_has_access_to_manager_level(self, app, manager_user):
        """Manager has access to MANAGER-required resources."""
        with app.app_context():
            user = db.session.get(User, manager_user.id)
            assert user.has_access(AccessLevel.MANAGER) is True

    def test_manager_lacks_access_to_admin_level(self, app, manager_user):
        """Manager does not have access to ADMIN-required resources."""
        with app.app_context():
            user = db.session.get(User, manager_user.id)
            assert user.has_access(AccessLevel.ADMIN) is False

    def test_musician_has_access_to_staff_level(self, app, musician_user):
        """Musician (STAFF) has access to STAFF-required resources."""
        with app.app_context():
            user = db.session.get(User, musician_user.id)
            assert user.has_access(AccessLevel.STAFF) is True

    def test_musician_lacks_access_to_manager_level(self, app, musician_user):
        """Musician lacks access to MANAGER-required resources."""
        with app.app_context():
            user = db.session.get(User, musician_user.id)
            assert user.has_access(AccessLevel.MANAGER) is False

    def test_viewer_has_access_to_viewer_level(self, app, viewer_user):
        """Viewer has access to VIEWER-required resources."""
        with app.app_context():
            user = db.session.get(User, viewer_user.id)
            assert user.has_access(AccessLevel.VIEWER) is True

    def test_viewer_lacks_access_to_staff_level(self, app, viewer_user):
        """Viewer lacks access to STAFF-required resources."""
        with app.app_context():
            user = db.session.get(User, viewer_user.id)
            assert user.has_access(AccessLevel.STAFF) is False


# =============================================================================
# role_required decorator
# =============================================================================

class TestRoleRequired:
    """Tests for the role_required decorator via has_any_role()."""

    def test_user_with_role_passes(self, app, manager_user):
        """User with MANAGER role passes has_any_role check."""
        with app.app_context():
            user = db.session.get(User, manager_user.id)
            assert user.has_any_role(['MANAGER']) is True

    def test_user_without_role_fails(self, app, musician_user):
        """Musician without MANAGER role fails has_any_role check for MANAGER."""
        with app.app_context():
            user = db.session.get(User, musician_user.id)
            assert user.has_any_role(['MANAGER']) is False

    def test_user_with_one_of_multiple_roles_passes(self, app, manager_user):
        """User with MANAGER role passes check for MANAGER or GUESTLIST_MANAGER."""
        with app.app_context():
            user = db.session.get(User, manager_user.id)
            assert user.has_any_role(['MANAGER', 'GUESTLIST_MANAGER']) is True

    def test_user_with_musician_role_passes_musician_check(self, app, musician_user):
        """Musician passes has_any_role for MUSICIAN."""
        with app.app_context():
            user = db.session.get(User, musician_user.id)
            assert user.has_any_role(['MUSICIAN']) is True


# =============================================================================
# permission_required decorator
# =============================================================================

class TestPermissionRequired:
    """Tests for the permission_required decorator via has_permission()."""

    def test_manager_has_manage_tour_permission(self, app, manager_user):
        """Manager has manage_tour permission via their role."""
        with app.app_context():
            user = db.session.get(User, manager_user.id)
            assert user.has_permission('manage_tour') is True

    def test_manager_has_manage_band_permission(self, app, manager_user):
        """Manager has manage_band permission via their role."""
        with app.app_context():
            user = db.session.get(User, manager_user.id)
            assert user.has_permission('manage_band') is True

    def test_musician_lacks_manage_tour_permission(self, app, musician_user):
        """Musician does not have manage_tour permission."""
        with app.app_context():
            user = db.session.get(User, musician_user.id)
            assert user.has_permission('manage_tour') is False

    def test_musician_has_view_tour_permission(self, app, musician_user):
        """Musician has view_tour permission via their role."""
        with app.app_context():
            user = db.session.get(User, musician_user.id)
            assert user.has_permission('view_tour') is True

    def test_manager_has_view_tour_permission(self, app, manager_user):
        """Manager has view_tour permission via their role."""
        with app.app_context():
            user = db.session.get(User, manager_user.id)
            assert user.has_permission('view_tour') is True


# =============================================================================
# ajax_login_required decorator
# =============================================================================

class TestAjaxLoginRequired:
    """Tests for ajax_login_required decorator behavior."""

    def test_ajax_endpoint_returns_401_when_unauthenticated(self, client):
        """AJAX endpoints return 401 JSON instead of redirect when not logged in."""
        # The /api/v1/ endpoints use JWT auth and return 401 for unauthenticated requests
        response = client.get('/api/v1/notifications', follow_redirects=False)
        # API endpoints return 401 for unauthenticated requests (not a browser redirect)
        assert response.status_code == 401


# =============================================================================
# is_admin() method
# =============================================================================

class TestIsAdmin:
    """Tests for the User.is_admin() method used by requires_admin."""

    def test_admin_user_is_admin(self, app, admin_user):
        """Admin user returns True for is_admin()."""
        with app.app_context():
            user = db.session.get(User, admin_user.id)
            assert user.is_admin() is True

    def test_manager_is_not_admin(self, app, manager_user):
        """Manager returns False for is_admin()."""
        with app.app_context():
            user = db.session.get(User, manager_user.id)
            assert user.is_admin() is False

    def test_musician_is_not_admin(self, app, musician_user):
        """Musician returns False for is_admin()."""
        with app.app_context():
            user = db.session.get(User, musician_user.id)
            assert user.is_admin() is False
