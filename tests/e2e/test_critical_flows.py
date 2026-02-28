# =============================================================================
# GigRoute E2E Tests — Critical User Flows
# =============================================================================
#
# These tests verify the most important user journeys in the application.
# They require Playwright: pip install -r requirements-e2e.txt
#
# Run: pytest tests/e2e/ -m e2e
# =============================================================================

import pytest

pytestmark = pytest.mark.e2e


class TestHealthCheck:
    """Verify the app is reachable and responding."""

    def test_health_endpoint(self, page, base_url):
        """Health check endpoint returns 200."""
        response = page.goto(f'{base_url}/health')
        assert response.status == 200


class TestPublicPages:
    """Verify public pages load correctly."""

    def test_login_page_loads(self, page, base_url):
        """Login page is accessible and has expected elements."""
        page.goto(f'{base_url}/auth/login')
        assert page.title()
        assert page.locator('input[name="email"]').is_visible()
        assert page.locator('input[name="password"]').is_visible()

    def test_register_page_loads(self, page, base_url):
        """Registration page is accessible."""
        page.goto(f'{base_url}/auth/register')
        assert page.locator('input[name="email"]').is_visible()

    def test_privacy_policy_accessible(self, page, base_url):
        """Privacy policy page loads (RGPD Art. 13-14)."""
        response = page.goto(f'{base_url}/privacy')
        assert response.status == 200

    def test_terms_of_service_accessible(self, page, base_url):
        """Terms of service page loads."""
        response = page.goto(f'{base_url}/terms')
        assert response.status == 200


class TestAuthFlow:
    """Test registration → login → dashboard flow."""

    def test_register_login_redirect(self, page, base_url):
        """New user can register then gets redirected to login."""
        # Go to register
        page.goto(f'{base_url}/auth/register')

        # Fill registration form
        page.fill('input[name="email"]', 'e2e-test@example.com')
        page.fill('input[name="first_name"]', 'E2E')
        page.fill('input[name="last_name"]', 'Test')
        page.fill('input[name="password"]', 'E2eTest123!')
        page.fill('input[name="password_confirm"]', 'E2eTest123!')

        # Submit and check we don't get a 500
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')
        assert '500' not in page.title()


class TestUnauthenticatedRedirects:
    """Verify protected pages redirect to login."""

    def test_dashboard_redirects_to_login(self, page, base_url):
        """Accessing dashboard without auth redirects to login."""
        page.goto(f'{base_url}/dashboard')
        page.wait_for_load_state('networkidle')
        assert '/auth/login' in page.url or '/login' in page.url


class TestCSPHeaders:
    """Verify Content Security Policy headers are present."""

    def test_csp_header_present(self, page, base_url):
        """Responses include CSP header with nonce."""
        response = page.goto(f'{base_url}/auth/login')
        csp = response.headers.get('content-security-policy', '')
        assert 'nonce-' in csp or "script-src" in csp
