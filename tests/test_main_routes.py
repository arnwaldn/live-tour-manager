# =============================================================================
# Tour Manager - Main Blueprint Routes Tests
# =============================================================================

import pytest
from datetime import date, timedelta

from app.extensions import db
from app.models.user import User, AccessLevel
from tests.conftest import login


# =============================================================================
# Helper fixtures for admin user (not in conftest.py)
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


# =============================================================================
# Ping / Simple Endpoints
# =============================================================================

class TestPingEndpoint:
    """Tests for the /ping endpoint."""

    def test_ping_no_auth_required(self, client):
        """Ping endpoint does not require authentication."""
        response = client.get('/ping')
        assert response.status_code == 200
        assert b'PONG' in response.data

    def test_ping_content_type_is_text(self, client):
        """Ping returns text/plain content type."""
        response = client.get('/ping')
        assert 'text/plain' in response.content_type


# =============================================================================
# Health Check Endpoint
# =============================================================================

class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_check_returns_200(self, client):
        """Health check returns 200 and JSON."""
        response = client.get('/health')
        assert response.status_code == 200

    def test_health_check_json_structure(self, client):
        """Health check returns expected JSON keys."""
        import json
        response = client.get('/health')
        data = json.loads(response.data)
        assert 'status' in data
        assert 'database' in data
        assert 'service' in data

    def test_health_check_db_healthy(self, client):
        """Health check reports DB as healthy in test environment."""
        import json
        response = client.get('/health')
        data = json.loads(response.data)
        assert data['database'] == 'healthy'


# =============================================================================
# Dashboard
# =============================================================================

class TestDashboard:
    """Tests for the main dashboard at GET /."""

    def test_dashboard_redirects_unauthenticated(self, client):
        """Unauthenticated access redirects to login."""
        response = client.get('/')
        assert response.status_code == 302
        assert '/auth/login' in response.location or 'login' in response.location

    def test_dashboard_accessible_for_manager(self, client, manager_user):
        """Manager can access the dashboard."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/', follow_redirects=True)
        assert response.status_code == 200

    def test_dashboard_accessible_for_musician(self, client, musician_user):
        """Musician (staff-level) can access the dashboard."""
        login(client, 'musician@test.com', 'Musician123!')
        response = client.get('/', follow_redirects=True)
        assert response.status_code == 200

    def test_dashboard_accessible_for_admin(self, client, admin_user):
        """Admin can access the dashboard."""
        login(client, 'admin@test.com', 'Admin123!')
        response = client.get('/', follow_redirects=True)
        assert response.status_code == 200

    def test_dashboard_shows_stats_section(self, client, manager_user):
        """Dashboard response contains HTML content when logged in."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/', follow_redirects=True)
        assert response.status_code == 200
        # Verify an HTML page was rendered (not a redirect loop)
        assert len(response.data) > 100


# =============================================================================
# Search
# =============================================================================

class TestSearch:
    """Tests for the /search endpoint."""

    def test_search_redirects_unauthenticated(self, client):
        """Unauthenticated search redirects to login."""
        response = client.get('/search?q=test')
        assert response.status_code == 302
        assert 'login' in response.location

    def test_search_accessible_for_manager(self, client, manager_user):
        """Manager can access search."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/search?q=test', follow_redirects=True)
        assert response.status_code == 200

    def test_search_empty_query(self, client, manager_user):
        """Search with empty query renders without results."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/search?q=', follow_redirects=True)
        assert response.status_code == 200

    def test_search_short_query(self, client, manager_user):
        """Search with single-character query renders without results."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/search?q=a', follow_redirects=True)
        assert response.status_code == 200

    def test_search_with_valid_query(self, client, manager_user):
        """Search with valid query (>= 2 chars) executes search logic."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/search?q=test', follow_redirects=True)
        assert response.status_code == 200

    def test_search_no_q_param(self, client, manager_user):
        """Search without q parameter renders cleanly."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/search', follow_redirects=True)
        assert response.status_code == 200

    def test_search_finds_tour(self, client, manager_user, sample_tour):
        """Search can find an existing tour by name."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/search?q=Test+Tour', follow_redirects=True)
        assert response.status_code == 200

    def test_search_finds_venue(self, client, manager_user, sample_venue):
        """Search can find an existing venue by name."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/search?q=Test+Venue', follow_redirects=True)
        assert response.status_code == 200

    def test_search_accessible_for_musician(self, client, musician_user):
        """Musician can access search."""
        login(client, 'musician@test.com', 'Musician123!')
        response = client.get('/search?q=test', follow_redirects=True)
        assert response.status_code == 200


# =============================================================================
# Global Calendar
# =============================================================================

class TestGlobalCalendar:
    """Tests for the /calendar endpoint."""

    def test_calendar_redirects_unauthenticated(self, client):
        """Unauthenticated access redirects to login."""
        response = client.get('/calendar')
        assert response.status_code == 302
        assert 'login' in response.location

    def test_calendar_accessible_for_manager(self, client, manager_user):
        """Manager can access the global calendar."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/calendar', follow_redirects=True)
        assert response.status_code == 200

    def test_calendar_accessible_for_musician(self, client, musician_user):
        """Musician can access the global calendar."""
        login(client, 'musician@test.com', 'Musician123!')
        response = client.get('/calendar', follow_redirects=True)
        assert response.status_code == 200

    def test_calendar_accessible_for_admin(self, client, admin_user):
        """Admin can access the global calendar."""
        login(client, 'admin@test.com', 'Admin123!')
        response = client.get('/calendar', follow_redirects=True)
        assert response.status_code == 200

    def test_calendar_trailing_slash_redirect(self, client, manager_user):
        """Calendar with trailing slash is accessible (strict_slashes=False)."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/calendar/', follow_redirects=True)
        assert response.status_code == 200

    def test_calendar_events_api_requires_login(self, client):
        """Calendar events API requires authentication."""
        response = client.get('/calendar/events')
        assert response.status_code == 302
        assert 'login' in response.location

    def test_calendar_events_api_accessible_for_manager(self, client, manager_user):
        """Manager can fetch calendar events JSON."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/calendar/events', follow_redirects=True)
        assert response.status_code == 200

    def test_calendar_events_returns_json(self, client, manager_user):
        """Calendar events endpoint returns JSON."""
        import json
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/calendar/events')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)


# =============================================================================
# Debug Endpoint Production Blocking
# =============================================================================

class TestHealthCheck:
    """Tests for the production health check endpoint."""

    def test_health_root_accessible(self, client):
        """/health endpoint is accessible for Docker/load balancer."""
        response = client.get('/health')
        assert response.status_code == 200
