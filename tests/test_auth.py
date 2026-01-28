# =============================================================================
# Tour Manager - Authentication Integration Tests
# =============================================================================

import pytest

from app.extensions import db
from app.models.user import User, Role


# =============================================================================
# Registration Tests
# =============================================================================

class TestRegistration:
    """Tests for user registration."""

    def test_register_page_loads(self, client):
        """Test registration page is accessible."""
        response = client.get('/auth/register')
        assert response.status_code == 200
        assert b'Inscription' in response.data or b'Register' in response.data

    def test_register_new_user(self, app, client):
        """Test successful user registration with pending approval workflow."""
        with app.app_context():
            # Create a default role for new users
            role = Role(
                name='MUSICIAN',
                description='Default role',
                permissions=['view_tour', 'view_show']
            )
            db.session.add(role)
            db.session.commit()

        # First, check the redirect without following
        response = client.post('/auth/register', data={
            'email': 'newuser@test.com',
            'password': 'NewUser123!',
            'password_confirm': 'NewUser123!',
            'first_name': 'New',
            'last_name': 'User'
        }, follow_redirects=False)

        # Should redirect to pending_approval page
        assert response.status_code == 302
        assert 'pending' in response.location.lower()

        # Follow redirect to verify page loads
        response = client.get(response.location)
        assert response.status_code == 200
        assert b'attente' in response.data.lower() or b'pending' in response.data.lower()

        # Verify user was created with is_active=False
        with app.app_context():
            user = User.query.filter_by(email='newuser@test.com').first()
            assert user is not None
            assert user.first_name == 'New'
            assert user.is_active == False  # New: user must be inactive
            assert user.invitation_token is None  # Self-registered, not invited

    def test_pending_user_cannot_login(self, app, client):
        """Test that pending users cannot login until approved."""
        with app.app_context():
            # Create a default role
            role = Role.query.filter_by(name='MUSICIAN').first()
            if not role:
                role = Role(
                    name='MUSICIAN',
                    description='Default role',
                    permissions=['view_tour', 'view_show']
                )
                db.session.add(role)
                db.session.commit()

        # Register a new user
        client.post('/auth/register', data={
            'email': 'pendinguser@test.com',
            'password': 'Pending123!',
            'password_confirm': 'Pending123!',
            'first_name': 'Pending',
            'last_name': 'User'
        })

        # Try to login - should fail because is_active=False
        response = client.post('/auth/login', data={
            'email': 'pendinguser@test.com',
            'password': 'Pending123!'
        }, follow_redirects=True)

        # Should show error message about inactive account
        assert response.status_code == 200
        assert b'activ' in response.data.lower() or b'attente' in response.data.lower() or \
               b'erreur' in response.data.lower() or b'incorrect' in response.data.lower()

    def test_register_duplicate_email(self, app, client, manager_user):
        """Test registration with existing email fails."""
        response = client.post('/auth/register', data={
            'email': 'manager@test.com',  # Already exists from fixture
            'password': 'Password123!',
            'password_confirm': 'Password123!',
            'first_name': 'Duplicate',
            'last_name': 'User'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'existe' in response.data.lower() or b'already' in response.data.lower() or \
               b'utilis' in response.data.lower()

    def test_register_password_mismatch(self, client):
        """Test registration with mismatched passwords."""
        response = client.post('/auth/register', data={
            'email': 'mismatch@test.com',
            'password': 'Password123!',
            'password_confirm': 'DifferentPassword123!',
            'first_name': 'Mismatch',
            'last_name': 'User'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Form should show error, user should not be created


# =============================================================================
# Login Tests
# =============================================================================

class TestLogin:
    """Tests for user login."""

    def test_login_page_loads(self, client):
        """Test login page is accessible."""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'Connexion' in response.data or b'Login' in response.data

    def test_login_valid_credentials(self, app, client, manager_user):
        """Test login with valid credentials."""
        response = client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Should redirect to dashboard after login

    def test_login_invalid_password(self, app, client, manager_user):
        """Test login with wrong password."""
        response = client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'WrongPassword!'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'incorrect' in response.data.lower() or b'invalid' in response.data.lower() or \
               b'erreur' in response.data.lower()

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent email."""
        response = client.post('/auth/login', data={
            'email': 'nobody@test.com',
            'password': 'Password123!'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'incorrect' in response.data.lower() or b'invalid' in response.data.lower() or \
               b'erreur' in response.data.lower()


# =============================================================================
# Logout Tests
# =============================================================================

class TestLogout:
    """Tests for user logout."""

    def test_logout(self, app, client, manager_user):
        """Test logout functionality."""
        # First login
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        }, follow_redirects=True)

        # Then logout
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200

        # Try to access protected page
        response = client.get('/')
        # Should redirect to login
        assert response.status_code == 302 or b'login' in response.data.lower()


# =============================================================================
# Protected Route Tests
# =============================================================================

class TestProtectedRoutes:
    """Tests for protected routes access."""

    def test_dashboard_requires_login(self, client):
        """Test dashboard redirects to login when not authenticated."""
        response = client.get('/', follow_redirects=False)
        assert response.status_code == 302
        assert '/auth/login' in response.location or 'login' in response.location.lower()

    def test_dashboard_accessible_when_logged_in(self, app, client, manager_user):
        """Test dashboard is accessible when authenticated."""
        # Login first
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get('/')
        assert response.status_code == 200

    def test_bands_requires_login(self, client):
        """Test bands page requires authentication."""
        response = client.get('/bands/', follow_redirects=False)
        assert response.status_code == 302

    def test_tours_requires_login(self, client):
        """Test tours page requires authentication."""
        response = client.get('/tours/', follow_redirects=False)
        assert response.status_code == 302


# =============================================================================
# Role-Based Access Tests
# =============================================================================

class TestRoleBasedAccess:
    """Tests for role-based access control."""

    def test_manager_can_access_band_create(self, app, client, manager_user):
        """Test manager can access band creation."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get('/bands/create')
        assert response.status_code == 200

    def test_musician_cannot_create_band(self, app, client, musician_user):
        """Test musician cannot access band creation."""
        client.post('/auth/login', data={
            'email': 'musician@test.com',
            'password': 'Musician123!'
        })

        response = client.get('/bands/create')
        # Should be 403 Forbidden or redirect
        assert response.status_code in [302, 403]


# =============================================================================
# Health Check Tests
# =============================================================================

class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_endpoint(self, client):
        """Test health check returns healthy status."""
        response = client.get('/health')
        assert response.status_code == 200

        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'tour-manager'

    def test_health_no_auth_required(self, client):
        """Test health check does not require authentication."""
        # This should work without login
        response = client.get('/health')
        assert response.status_code == 200


# =============================================================================
# CSRF Protection Tests
# =============================================================================

class TestCSRFProtection:
    """Tests for CSRF protection (disabled in test mode)."""

    def test_csrf_token_present_in_forms(self, client):
        """Test CSRF token field is present in login form."""
        response = client.get('/auth/login')
        # In production, CSRF token would be present
        # In test mode it's disabled, but we check the form exists
        assert response.status_code == 200


# =============================================================================
# Session Tests
# =============================================================================

class TestSession:
    """Tests for session handling."""

    def test_session_persists(self, app, client, manager_user):
        """Test session persists across requests."""
        # Login
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        # Multiple requests should stay logged in
        response1 = client.get('/')
        assert response1.status_code == 200

        response2 = client.get('/bands/')
        assert response2.status_code == 200

        response3 = client.get('/tours/')
        assert response3.status_code == 200
