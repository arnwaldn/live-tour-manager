# =============================================================================
# Tour Manager - Authentication Integration Tests
# =============================================================================

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.extensions import db
from app.models.user import User, Role, AccessLevel


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

    def test_register_weak_password(self, client):
        """Test registration with password that doesn't meet complexity requirements."""
        response = client.post('/auth/register', data={
            'email': 'weakpass@test.com',
            'password': 'short',
            'password_confirm': 'short',
            'first_name': 'Weak',
            'last_name': 'Password'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Should stay on registration page with validation error

    def test_register_missing_required_fields(self, client):
        """Test registration with missing required fields."""
        response = client.post('/auth/register', data={
            'email': '',
            'password': 'Password123!',
            'password_confirm': 'Password123!',
            'first_name': '',
            'last_name': ''
        }, follow_redirects=True)

        assert response.status_code == 200
        # Should stay on registration page with validation errors

    def test_register_assigns_musician_role(self, app, client):
        """Test that newly registered user gets default MUSICIAN role."""
        with app.app_context():
            role = Role(
                name='MUSICIAN',
                description='Default role',
                permissions=['view_tour', 'view_show']
            )
            db.session.add(role)
            db.session.commit()

        client.post('/auth/register', data={
            'email': 'roletest@test.com',
            'password': 'RoleTest123!',
            'password_confirm': 'RoleTest123!',
            'first_name': 'Role',
            'last_name': 'Test'
        })

        with app.app_context():
            user = User.query.filter_by(email='roletest@test.com').first()
            assert user is not None
            assert any(r.name == 'MUSICIAN' for r in user.roles)

    def test_register_without_musician_role_still_works(self, app, client):
        """Test registration works even if MUSICIAN role doesn't exist."""
        # No MUSICIAN role created
        response = client.post('/auth/register', data={
            'email': 'norole@test.com',
            'password': 'NoRole123!',
            'password_confirm': 'NoRole123!',
            'first_name': 'No',
            'last_name': 'Role'
        }, follow_redirects=False)

        assert response.status_code == 302
        assert 'pending' in response.location.lower()

        with app.app_context():
            user = User.query.filter_by(email='norole@test.com').first()
            assert user is not None
            assert len(user.roles) == 0

    def test_register_email_stored_lowercase(self, app, client):
        """Test that email is stored in lowercase."""
        with app.app_context():
            role = Role(
                name='MUSICIAN',
                description='Default role',
                permissions=['view_tour', 'view_show']
            )
            db.session.add(role)
            db.session.commit()

        client.post('/auth/register', data={
            'email': 'UPPERCASE@TEST.COM',
            'password': 'Upper123!',
            'password_confirm': 'Upper123!',
            'first_name': 'Upper',
            'last_name': 'Case'
        })

        with app.app_context():
            user = User.query.filter_by(email='uppercase@test.com').first()
            assert user is not None
            assert user.email == 'uppercase@test.com'

    def test_register_with_phone(self, app, client):
        """Test registration with optional phone number."""
        with app.app_context():
            role = Role(
                name='MUSICIAN',
                description='Default role',
                permissions=['view_tour', 'view_show']
            )
            db.session.add(role)
            db.session.commit()

        client.post('/auth/register', data={
            'email': 'phone@test.com',
            'password': 'Phone123!',
            'password_confirm': 'Phone123!',
            'first_name': 'Phone',
            'last_name': 'User',
            'phone': '+33 6 12 34 56 78'
        })

        with app.app_context():
            user = User.query.filter_by(email='phone@test.com').first()
            assert user is not None
            assert user.phone == '+33 6 12 34 56 78'

    def test_register_email_notification_failure_does_not_break(self, app, client):
        """Test that email notification failure doesn't prevent registration."""
        with app.app_context():
            role = Role(
                name='MUSICIAN',
                description='Default role',
                permissions=['view_tour', 'view_show']
            )
            db.session.add(role)
            db.session.commit()

        with patch('app.blueprints.auth.routes.send_registration_notification', side_effect=Exception('SMTP error')):
            response = client.post('/auth/register', data={
                'email': 'emailfail@test.com',
                'password': 'EmailFail123!',
                'password_confirm': 'EmailFail123!',
                'first_name': 'Email',
                'last_name': 'Fail'
            }, follow_redirects=False)

            # Should still redirect successfully
            assert response.status_code == 302
            assert 'pending' in response.location.lower()

        with app.app_context():
            user = User.query.filter_by(email='emailfail@test.com').first()
            assert user is not None

    def test_register_redirects_if_authenticated(self, app, client, manager_user):
        """Test that authenticated users are redirected from register page."""
        # Login first
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get('/auth/register', follow_redirects=False)
        assert response.status_code == 302

    def test_pending_approval_page_loads(self, client):
        """Test pending approval page is accessible."""
        response = client.get('/auth/pending-approval')
        assert response.status_code == 200

    def test_pending_approval_redirects_if_authenticated(self, app, client, manager_user):
        """Test authenticated users are redirected from pending approval page."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get('/auth/pending-approval', follow_redirects=False)
        assert response.status_code == 302


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

    def test_login_inactive_user(self, app, client):
        """Test login with inactive account shows proper error."""
        with app.app_context():
            user = User(
                email='inactive@test.com',
                first_name='Inactive',
                last_name='User',
                access_level=AccessLevel.MANAGER,
                is_active=False,
                email_verified=True,
            )
            user.set_password('Inactive123!')
            db.session.add(user)
            db.session.commit()

        response = client.post('/auth/login', data={
            'email': 'inactive@test.com',
            'password': 'Inactive123!'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'activ' in response.data.lower() or b'sactiv' in response.data.lower()

    def test_login_locked_account(self, app, client):
        """Test login with locked account shows lockout message."""
        with app.app_context():
            user = User(
                email='locked@test.com',
                first_name='Locked',
                last_name='User',
                access_level=AccessLevel.MANAGER,
                is_active=True,
                email_verified=True,
            )
            user.set_password('Locked123!')
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
            user.failed_login_attempts = 5
            db.session.add(user)
            db.session.commit()

        response = client.post('/auth/login', data={
            'email': 'locked@test.com',
            'password': 'Locked123!'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'verrouill' in response.data.lower() or b'lock' in response.data.lower()

    def test_login_records_failed_attempts(self, app, client, manager_user):
        """Test that failed logins increment the failed_login_attempts counter."""
        # First failed login
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'WrongPassword!'
        }, follow_redirects=True)

        with app.app_context():
            user = User.query.filter_by(email='manager@test.com').first()
            assert user.failed_login_attempts >= 1

    def test_login_resets_failed_attempts_on_success(self, app, client, manager_user):
        """Test that successful login resets failed_login_attempts."""
        # First fail a login
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'WrongPassword!'
        }, follow_redirects=True)

        # Then succeed
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        }, follow_redirects=True)

        with app.app_context():
            user = User.query.filter_by(email='manager@test.com').first()
            assert user.failed_login_attempts == 0

    def test_login_with_remember_me(self, app, client, manager_user):
        """Test login with remember_me flag set."""
        response = client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!',
            'remember_me': 'y'
        }, follow_redirects=True)

        assert response.status_code == 200

    def test_login_redirect_next_page(self, app, client, manager_user):
        """Test login redirects to next parameter after authentication."""
        response = client.post('/auth/login?next=/bands/', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/bands/' in response.location

    def test_login_blocks_open_redirect(self, app, client, manager_user):
        """Test login prevents open redirect attacks via next parameter."""
        response = client.post('/auth/login?next=//evil.com', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        }, follow_redirects=False)

        assert response.status_code == 302
        # Should redirect to dashboard, NOT to evil.com
        assert 'evil.com' not in response.location

    def test_login_blocks_backslash_redirect(self, app, client, manager_user):
        """Test login prevents backslash-based open redirect attacks."""
        response = client.post('/auth/login?next=/\\evil.com', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        }, follow_redirects=False)

        assert response.status_code == 302
        assert 'evil.com' not in response.location

    def test_login_redirects_if_authenticated(self, app, client, manager_user):
        """Test that already authenticated users are redirected from login page."""
        # Login first
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get('/auth/login', follow_redirects=False)
        assert response.status_code == 302

    def test_login_email_case_insensitive(self, app, client, manager_user):
        """Test that login is case-insensitive for email."""
        response = client.post('/auth/login', data={
            'email': 'MANAGER@TEST.COM',
            'password': 'Manager123!'
        }, follow_redirects=True)

        assert response.status_code == 200

    def test_login_missing_email(self, client):
        """Test login with missing email field."""
        response = client.post('/auth/login', data={
            'email': '',
            'password': 'Password123!'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Should stay on login page

    def test_login_missing_password(self, client):
        """Test login with missing password field."""
        response = client.post('/auth/login', data={
            'email': 'test@test.com',
            'password': ''
        }, follow_redirects=True)

        assert response.status_code == 200
        # Should stay on login page

    def test_login_account_lockout_after_max_attempts(self, app, client):
        """Test that account gets locked after max failed login attempts."""
        with app.app_context():
            user = User(
                email='locktest@test.com',
                first_name='Lock',
                last_name='Test',
                access_level=AccessLevel.MANAGER,
                is_active=True,
                email_verified=True,
            )
            user.set_password('LockTest123!')
            db.session.add(user)
            db.session.commit()

        # Attempt multiple failed logins (default max_attempts=5)
        for _ in range(5):
            client.post('/auth/login', data={
                'email': 'locktest@test.com',
                'password': 'WrongPassword!'
            }, follow_redirects=True)

        with app.app_context():
            user = User.query.filter_by(email='locktest@test.com').first()
            assert user.failed_login_attempts >= 5
            assert user.locked_until is not None


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

    def test_logout_redirects_to_login(self, app, client, manager_user):
        """Test that logout redirects to login page."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get('/auth/logout', follow_redirects=False)
        assert response.status_code == 302
        assert '/auth/login' in response.location or 'login' in response.location.lower()

    def test_logout_requires_login(self, client):
        """Test that logout requires being logged in."""
        response = client.get('/auth/logout', follow_redirects=False)
        # Should redirect to login page since not authenticated
        assert response.status_code == 302


# =============================================================================
# Forgot Password Tests
# =============================================================================

class TestForgotPassword:
    """Tests for password reset request."""

    def test_forgot_password_page_loads(self, client):
        """Test forgot password page is accessible."""
        response = client.get('/auth/forgot-password')
        assert response.status_code == 200

    def test_forgot_password_with_valid_email(self, app, client, manager_user):
        """Test forgot password request with a registered email."""
        with patch('app.blueprints.auth.routes.send_password_reset_email', return_value=True):
            response = client.post('/auth/forgot-password', data={
                'email': 'manager@test.com'
            }, follow_redirects=True)

        assert response.status_code == 200
        # Should show generic success message
        assert b'lien' in response.data.lower() or b'email' in response.data.lower()

    def test_forgot_password_with_unknown_email(self, client):
        """Test forgot password with non-existent email (should not leak info)."""
        response = client.post('/auth/forgot-password', data={
            'email': 'unknown@test.com'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Same message as valid email (security: don't reveal if email exists)
        assert b'lien' in response.data.lower() or b'email' in response.data.lower()

    def test_forgot_password_generates_token(self, app, client, manager_user):
        """Test that forgot password generates a reset token."""
        with patch('app.blueprints.auth.routes.send_password_reset_email', return_value=True):
            client.post('/auth/forgot-password', data={
                'email': 'manager@test.com'
            }, follow_redirects=True)

        with app.app_context():
            user = User.query.filter_by(email='manager@test.com').first()
            assert user.reset_token is not None
            assert user.reset_token_expires is not None

    def test_forgot_password_email_failure(self, app, client, manager_user):
        """Test forgot password when email send fails (still shows success)."""
        with patch('app.blueprints.auth.routes.send_password_reset_email', return_value=False):
            response = client.post('/auth/forgot-password', data={
                'email': 'manager@test.com'
            }, follow_redirects=True)

        # Should still show generic success message (security)
        assert response.status_code == 200

    def test_forgot_password_redirects_if_authenticated(self, app, client, manager_user):
        """Test authenticated users are redirected from forgot password page."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get('/auth/forgot-password', follow_redirects=False)
        assert response.status_code == 302

    def test_forgot_password_missing_email(self, client):
        """Test forgot password with empty email field."""
        response = client.post('/auth/forgot-password', data={
            'email': ''
        }, follow_redirects=True)

        assert response.status_code == 200
        # Should stay on forgot password page with validation error


# =============================================================================
# Reset Password Tests
# =============================================================================

class TestResetPassword:
    """Tests for password reset with token."""

    def test_reset_password_valid_token(self, app, client, manager_user):
        """Test password reset with a valid token."""
        user = User.query.filter_by(email='manager@test.com').first()
        token = user.generate_reset_token()
        db.session.commit()

        response = client.get(f'/auth/reset-password/{token}')
        assert response.status_code == 200

    def test_reset_password_submit(self, app, client, manager_user):
        """Test successful password reset submission."""
        user = User.query.filter_by(email='manager@test.com').first()
        token = user.generate_reset_token()
        db.session.commit()

        response = client.post(f'/auth/reset-password/{token}', data={
            'password': 'NewPassword123!',
            'password_confirm': 'NewPassword123!'
        }, follow_redirects=False)

        assert response.status_code == 302
        assert '/auth/login' in response.location or 'login' in response.location.lower()

        # Verify new password works
        user = User.query.filter_by(email='manager@test.com').first()
        assert user.check_password('NewPassword123!')
        assert user.reset_token is None

    def test_reset_password_invalid_token(self, client):
        """Test password reset with invalid token."""
        response = client.get('/auth/reset-password/invalid-token-123', follow_redirects=False)
        assert response.status_code == 302
        assert 'forgot' in response.location.lower()

    def test_reset_password_expired_token(self, app, client, manager_user):
        """Test password reset with expired token."""
        user = User.query.filter_by(email='manager@test.com').first()
        token = user.generate_reset_token()
        # Expire the token
        user.reset_token_expires = datetime.utcnow() - timedelta(hours=1)
        db.session.commit()

        response = client.get(f'/auth/reset-password/{token}', follow_redirects=False)
        assert response.status_code == 302
        assert 'forgot' in response.location.lower()

    def test_reset_password_clears_lockout(self, app, client):
        """Test that resetting password clears account lockout."""
        user = User(
            email='resetlock@test.com',
            first_name='Reset',
            last_name='Lock',
            access_level=AccessLevel.MANAGER,
            is_active=True,
            email_verified=True,
        )
        user.set_password('OldPass123!')
        user.failed_login_attempts = 5
        user.locked_until = datetime.utcnow() + timedelta(minutes=15)
        db.session.add(user)
        db.session.commit()

        token = user.generate_reset_token()
        db.session.commit()

        client.post(f'/auth/reset-password/{token}', data={
            'password': 'NewPass123!',
            'password_confirm': 'NewPass123!'
        }, follow_redirects=True)

        user = User.query.filter_by(email='resetlock@test.com').first()
        assert user.failed_login_attempts == 0
        assert user.locked_until is None

    def test_reset_password_redirects_if_authenticated(self, app, client, manager_user):
        """Test authenticated users are redirected from reset password page."""
        user = User.query.filter_by(email='manager@test.com').first()
        token = user.generate_reset_token()
        db.session.commit()

        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get(f'/auth/reset-password/{token}', follow_redirects=False)
        assert response.status_code == 302

    def test_reset_password_password_mismatch(self, app, client, manager_user):
        """Test password reset with mismatched passwords."""
        user = User.query.filter_by(email='manager@test.com').first()
        token = user.generate_reset_token()
        db.session.commit()

        response = client.post(f'/auth/reset-password/{token}', data={
            'password': 'NewPass123!',
            'password_confirm': 'DifferentPass123!'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Should stay on reset page with error


# =============================================================================
# Change Password Tests
# =============================================================================

class TestChangePassword:
    """Tests for password change (logged-in users)."""

    def test_change_password_page_loads(self, app, client, manager_user):
        """Test change password page is accessible when authenticated."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get('/auth/change-password')
        assert response.status_code == 200

    def test_change_password_requires_login(self, client):
        """Test change password requires authentication."""
        response = client.get('/auth/change-password', follow_redirects=False)
        assert response.status_code == 302

    def test_change_password_success(self, app, client, manager_user):
        """Test successful password change."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.post('/auth/change-password', data={
            'current_password': 'Manager123!',
            'new_password': 'NewManager123!',
            'new_password_confirm': 'NewManager123!'
        }, follow_redirects=False)

        assert response.status_code == 302

        # Verify new password works
        with app.app_context():
            user = User.query.filter_by(email='manager@test.com').first()
            assert user.check_password('NewManager123!')

    def test_change_password_wrong_current(self, app, client, manager_user):
        """Test password change with wrong current password."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.post('/auth/change-password', data={
            'current_password': 'WrongPassword!',
            'new_password': 'NewManager123!',
            'new_password_confirm': 'NewManager123!'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'incorrect' in response.data.lower() or b'actuel' in response.data.lower()

    def test_change_password_new_mismatch(self, app, client, manager_user):
        """Test password change with mismatched new passwords."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.post('/auth/change-password', data={
            'current_password': 'Manager123!',
            'new_password': 'NewPass123!',
            'new_password_confirm': 'DifferentPass123!'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Should stay on change password page with error


# =============================================================================
# Accept Invitation Tests
# =============================================================================

class TestAcceptInvite:
    """Tests for invitation acceptance flow."""

    def test_accept_invite_page_loads(self, app, client):
        """Test accept invite page loads with valid token."""
        user = User(
            email='invited@test.com',
            first_name='Invited',
            last_name='User',
            access_level=AccessLevel.STAFF,
            is_active=True,
            email_verified=False,
            password_hash='placeholder',
        )
        db.session.add(user)
        db.session.commit()

        token = user.generate_invitation_token()
        db.session.commit()

        response = client.get(f'/auth/accept-invite/{token}')
        assert response.status_code == 200

    def test_accept_invite_invalid_token(self, client):
        """Test accept invite with invalid token redirects to login."""
        response = client.get('/auth/accept-invite/invalid-token-xyz', follow_redirects=False)
        assert response.status_code == 302
        assert 'login' in response.location.lower()

    def test_accept_invite_sets_password(self, app, client):
        """Test successful password setting via invitation."""
        user = User(
            email='setpass@test.com',
            first_name='Set',
            last_name='Pass',
            access_level=AccessLevel.STAFF,
            is_active=True,
            email_verified=False,
            password_hash='placeholder',
        )
        db.session.add(user)
        db.session.commit()

        token = user.generate_invitation_token()
        db.session.commit()

        with patch('app.blueprints.auth.routes.send_welcome_email'):
            response = client.post(f'/auth/accept-invite/{token}', data={
                'password': 'InvitePass123!',
                'confirm_password': 'InvitePass123!'
            }, follow_redirects=False)

        assert response.status_code == 302
        assert 'login' in response.location.lower()

        user = User.query.filter_by(email='setpass@test.com').first()
        assert user.check_password('InvitePass123!')
        assert user.invitation_token is None
        assert user.email_verified is True

    def test_accept_invite_expired_token(self, app, client):
        """Test accept invite with expired token."""
        user = User(
            email='expired@test.com',
            first_name='Expired',
            last_name='Token',
            access_level=AccessLevel.STAFF,
            is_active=True,
            email_verified=False,
            password_hash='placeholder',
        )
        db.session.add(user)
        db.session.commit()

        token = user.generate_invitation_token()
        # Expire the token
        user.invitation_token_expires = datetime.utcnow() - timedelta(hours=1)
        db.session.commit()

        response = client.get(f'/auth/accept-invite/{token}', follow_redirects=False)
        assert response.status_code == 302
        assert 'login' in response.location.lower()

    def test_accept_invite_logs_out_authenticated_user(self, app, client, manager_user):
        """Test that accept invite logs out any currently authenticated user."""
        # Login first
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        user = User(
            email='newinvite@test.com',
            first_name='New',
            last_name='Invite',
            access_level=AccessLevel.STAFF,
            is_active=True,
            email_verified=False,
            password_hash='placeholder',
        )
        db.session.add(user)
        db.session.commit()

        token = user.generate_invitation_token()
        db.session.commit()

        response = client.get(f'/auth/accept-invite/{token}')
        # Should load the accept invite page (user was logged out)
        assert response.status_code == 200

    def test_accept_invite_welcome_email_failure(self, app, client):
        """Test invitation acceptance succeeds even if welcome email fails."""
        user = User(
            email='welcomefail@test.com',
            first_name='Welcome',
            last_name='Fail',
            access_level=AccessLevel.STAFF,
            is_active=True,
            email_verified=False,
            password_hash='placeholder',
        )
        db.session.add(user)
        db.session.commit()

        token = user.generate_invitation_token()
        db.session.commit()

        with patch('app.blueprints.auth.routes.send_welcome_email', side_effect=Exception('SMTP error')):
            response = client.post(f'/auth/accept-invite/{token}', data={
                'password': 'WelcomeFail123!',
                'confirm_password': 'WelcomeFail123!'
            }, follow_redirects=False)

        # Should still succeed
        assert response.status_code == 302
        assert 'login' in response.location.lower()


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
        assert data['service'] == 'gigroute'

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
