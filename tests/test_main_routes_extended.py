# =============================================================================
# Tour Manager - Extended Main Blueprint Route Tests
# =============================================================================
# Covers routes NOT already tested in test_main_routes.py:
#   - Admin full reset
#   - Dashboard with tour/stop data
#   - Global calendar events with stops
#   - Standalone event creation
# =============================================================================

import json
import pytest
from datetime import date, timedelta

from app.extensions import db
from app.models.user import User, AccessLevel
from tests.conftest import login


# =============================================================================
# Shared admin fixture (not in conftest.py)
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


# Health debug endpoints have been removed from production code.
# The only remaining endpoint is /health (Docker healthcheck) tested in test_main_routes.py.


# =============================================================================
# Admin Full Reset
# =============================================================================

class TestAdminFullReset:
    """Tests for POST /admin/full-reset (admin only)."""

    def test_full_reset_requires_auth(self, client):
        """Unauthenticated POST is redirected."""
        response = client.post('/admin/full-reset')
        assert response.status_code == 302

    def test_full_reset_forbidden_for_manager(self, client, manager_user):
        """Manager (non-admin) gets 403."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.post('/admin/full-reset')
        assert response.status_code == 403

    def test_full_reset_accessible_for_admin(self, client, admin_user):
        """Admin can trigger full reset and is redirected."""
        login(client, 'admin@test.com', 'Admin123!')
        response = client.post('/admin/full-reset', follow_redirects=True)
        assert response.status_code == 200


# =============================================================================
# Dashboard with data
# =============================================================================

class TestDashboardWithData:
    """Dashboard rendering with tours and stops."""

    def test_dashboard_with_tour_shows_content(self, client, manager_user, sample_tour):
        """Dashboard renders successfully when a tour exists."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/', follow_redirects=True)
        assert response.status_code == 200

    def test_dashboard_with_upcoming_stop(self, client, manager_user, sample_tour_stop):
        """Dashboard renders when an upcoming tour stop exists."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/', follow_redirects=True)
        assert response.status_code == 200


# =============================================================================
# Global Calendar Events API (with stops)
# =============================================================================

class TestCalendarEventsWithStops:
    """Tests for /calendar/events with actual data."""

    def test_calendar_events_returns_events_for_stop(self, client, manager_user, sample_tour_stop):
        """Calendar events list includes the sample stop."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/calendar/events')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_calendar_events_with_tour_filter(self, client, manager_user, sample_tour, sample_tour_stop):
        """Calendar events can be filtered by tour_id."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get(f'/calendar/events?tour_id={sample_tour.id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_calendar_events_with_date_range(self, client, manager_user, sample_tour_stop):
        """Calendar events filtered by date range."""
        login(client, 'manager@test.com', 'Manager123!')
        start = date.today().isoformat()
        end = (date.today() + timedelta(days=30)).isoformat()
        response = client.get(f'/calendar/events?start={start}T00:00:00Z&end={end}T23:59:59Z')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_calendar_events_week_view(self, client, manager_user, sample_tour_stop):
        """Calendar events in week view returns schedule-type events."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/calendar/events?view=week')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_calendar_events_for_musician_only_sees_assigned(self, client, musician_user, sample_tour_stop):
        """Musician sees only assigned events (or empty if not assigned)."""
        login(client, 'musician@test.com', 'Musician123!')
        response = client.get('/calendar/events')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_calendar_events_with_invalid_date_range(self, client, manager_user):
        """Calendar events with invalid date strings handles gracefully."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/calendar/events?start=not-a-date&end=also-invalid')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)


# =============================================================================
# Standalone Event Creation
# =============================================================================

class TestStandaloneEvents:
    """Tests for /calendar/add and /calendar/events/<id>/edit."""

    def test_add_standalone_event_requires_auth(self, client):
        """GET /calendar/add requires authentication."""
        response = client.get('/calendar/add')
        assert response.status_code == 302
        assert 'login' in response.location

    def test_add_standalone_event_no_manageable_bands(self, client, musician_user):
        """Musician with no manageable bands is redirected with warning."""
        login(client, 'musician@test.com', 'Musician123!')
        response = client.get('/calendar/add', follow_redirects=True)
        assert response.status_code == 200

    def test_add_standalone_event_manager_with_band(self, client, manager_user, sample_band):
        """Manager who manages a band can access /calendar/add."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/calendar/add', follow_redirects=True)
        assert response.status_code == 200
