# =============================================================================
# Tour Manager - Extended Main Blueprint Route Tests
# =============================================================================
# Covers routes NOT already tested in test_main_routes.py:
#   - Admin full reset
#   - Health debug endpoints (tours-list, add-stop-debug, create-stop,
#     test-simple, create-guest, crew-debug, fix-enums, stop-debug,
#     db-test, db-raw, health/diagnose, bands-debug, admin-bands-check,
#     dashboard-debug, migration-status)
#   - Dashboard with tour/stop data
#   - Global calendar events with stops
#   - Standalone event creation
# =============================================================================

import json
import pytest
from datetime import date, timedelta

from app.extensions import db
from app.models.user import User, AccessLevel
from app.models.band import Band, BandMembership
from app.models.tour import Tour, TourStatus
from app.models.tour_stop import TourStop, TourStopStatus
from app.models.venue import Venue
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


# =============================================================================
# Health Debug Endpoints (no-auth, accessible in debug mode)
# =============================================================================

class TestHealthDebugEndpoints:
    """Tests for /health/* debug endpoints (blocked in production, open in test mode)."""

    def test_health_tours_list_returns_json(self, client):
        """/health/tours-list returns a JSON list."""
        response = client.get('/health/tours-list')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_health_tours_list_contains_tour(self, client, sample_tour):
        """/health/tours-list includes existing tours."""
        response = client.get('/health/tours-list')
        assert response.status_code == 200
        data = json.loads(response.data)
        ids = [t['id'] for t in data]
        assert sample_tour.id in ids

    def test_health_add_stop_debug_tour_not_found(self, client):
        """/health/add-stop-debug/9999 returns JSON with error for missing tour."""
        response = client.get('/health/add-stop-debug/9999')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'errors' in data
        assert any('not found' in e for e in data['errors'])

    def test_health_add_stop_debug_existing_tour(self, client, sample_tour):
        """/health/add-stop-debug/<id> returns JSON for existing tour."""
        response = client.get(f'/health/add-stop-debug/{sample_tour.id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['tour_id'] == sample_tour.id

    def test_health_create_stop_debug_tour_not_found(self, client):
        """/health/create-stop/9999 returns JSON with error."""
        response = client.get('/health/create-stop/9999')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'errors' in data

    def test_health_test_simple_returns_ok(self, client):
        """/health/test-simple returns status ok."""
        response = client.get('/health/test-simple')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'

    def test_health_create_guest_debug_stop_not_found(self, client):
        """/health/create-guest/9999 returns JSON with error."""
        response = client.get('/health/create-guest/9999')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'errors' in data

    def test_health_crew_debug_stop_not_found(self, client):
        """/health/crew-debug/9999 returns JSON with error."""
        response = client.get('/health/crew-debug/9999')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'errors' in data

    def test_health_crew_debug_existing_stop(self, client, sample_tour_stop):
        """/health/crew-debug/<id> inspects existing stop."""
        response = client.get(f'/health/crew-debug/{sample_tour_stop.id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['stop_id'] == sample_tour_stop.id

    def test_health_crew_full_debug_stop_not_found(self, client):
        """/health/crew-full-debug/9999 returns JSON with error."""
        response = client.get('/health/crew-full-debug/9999')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'errors' in data

    def test_health_fix_enums_returns_json(self, client):
        """/health/fix-enums returns a JSON result (may have DB-specific errors in SQLite)."""
        response = client.get('/health/fix-enums')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'success' in data

    def test_health_stop_debug_tour_not_found(self, client):
        """/health/stop-debug/9999/1 returns JSON with error."""
        response = client.get('/health/stop-debug/9999/1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'errors' in data

    def test_health_stop_debug_existing(self, client, sample_tour, sample_tour_stop):
        """/health/stop-debug/<tour_id>/<stop_id> returns debug data."""
        response = client.get(f'/health/stop-debug/{sample_tour.id}/{sample_tour_stop.id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['tour_id'] == sample_tour.id
        assert data['stop_id'] == sample_tour_stop.id

    def test_health_db_test_returns_json(self, client):
        """/health/db-test returns JSON with connection status."""
        response = client.get('/health/db-test')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'db_connection' in data

    def test_health_db_raw_returns_json(self, client):
        """/health/db-raw returns JSON."""
        response = client.get('/health/db-raw')
        # Status can be 200 or 500 depending on SQLite vs Postgres checks
        data = json.loads(response.data)
        assert 'checks' in data or 'db_connected' in data

    def test_health_diagnose_returns_json(self, client):
        """/health/diagnose returns diagnostics JSON."""
        response = client.get('/health/diagnose')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'tours' in data
        assert 'users' in data

    def test_health_bands_debug_returns_json(self, client, manager_user, sample_band):
        """/health/bands-debug returns JSON (uses user_id query param for existing user)."""
        response = client.get(f'/health/bands-debug?user_id={manager_user.id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'all_bands' in data

    def test_health_admin_bands_check_returns_json(self, client):
        """/health/admin-bands-check returns JSON."""
        response = client.get('/health/admin-bands-check')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'version' in data

    def test_health_migration_status_returns_json(self, client):
        """/health/migration-status returns JSON."""
        response = client.get('/health/migration-status')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'version' in data

    def test_health_run_migrations_returns_json(self, client):
        """/health/run-migrations returns JSON (may fail with SystemExit on SQLite in test env)."""
        import pytest
        try:
            response = client.get('/health/run-migrations')
            data = json.loads(response.data)
            assert 'status' in data
        except SystemExit:
            # flask_migrate may call sys.exit on SQLite in test mode — that's expected
            pytest.skip('flask_migrate raises SystemExit in test environment')

    def test_health_add_missing_columns_returns_json(self, client):
        """/health/add-missing-columns returns JSON."""
        response = client.get('/health/add-missing-columns')
        # 200 on success
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data

    def test_health_create_tables_returns_json(self, client):
        """/health/create-tables returns JSON (tables already exist → SKIPPED or SUCCESS)."""
        response = client.get('/health/create-tables')
        data = json.loads(response.data)
        assert 'status' in data

    def test_health_migration_check_returns_json(self, client):
        """/health/migration-check returns JSON."""
        response = client.get('/health/migration-check')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'table_count' in data

    def test_health_fix_professions_schema_returns_json(self, client):
        """/health/fix-professions-schema returns JSON."""
        response = client.get('/health/fix-professions-schema')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data


# =============================================================================
# Dashboard Debug Endpoint (requires auth)
# =============================================================================

class TestDashboardDebugEndpoint:
    """Tests for /health/dashboard-debug (requires login)."""

    def test_dashboard_debug_requires_auth(self, client):
        """Unauthenticated access to /health/dashboard-debug is redirected."""
        response = client.get('/health/dashboard-debug')
        assert response.status_code == 302
        assert 'login' in response.location

    def test_dashboard_debug_accessible_for_manager(self, client, manager_user):
        """Manager can access /health/dashboard-debug."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/health/dashboard-debug')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'current_user' in data
        assert 'user_bands' in data


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

    def test_dashboard_debug_html_param(self, client, manager_user):
        """Dashboard ?debug=html returns HTML debug page."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/?debug=html')
        assert response.status_code == 200
        assert b'Debug Dashboard' in response.data

    def test_dashboard_debug_json_for_admin(self, client, admin_user):
        """Admin dashboard with ?debug=1 returns JSON with admin branch."""
        login(client, 'admin@test.com', 'Admin123!')
        response = client.get('/?debug=1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['branch'] == 'admin'

    def test_dashboard_debug_json_for_manager(self, client, manager_user):
        """Manager dashboard with ?debug=1 returns JSON with non-admin branch."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/?debug=1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['branch'] == 'non-admin'


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


# =============================================================================
# Health Test-User-Edit Endpoint
# =============================================================================

class TestHealthTestUserEdit:
    """Tests for /health/test-user-edit/<user_id>."""

    def test_test_user_edit_not_found(self, client):
        """/health/test-user-edit/9999 returns 404 JSON."""
        response = client.get('/health/test-user-edit/9999')
        assert response.status_code == 404

    def test_test_user_edit_existing_user(self, client, manager_user):
        """/health/test-user-edit/<id> returns step results."""
        response = client.get(f'/health/test-user-edit/{manager_user.id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'steps' in data
