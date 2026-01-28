# =============================================================================
# Tour Manager - Routes Integration Tests
# =============================================================================

import pytest
from datetime import date, timedelta

from app.extensions import db
from app.models.band import Band
from app.models.tour import Tour, TourStatus
from app.models.venue import Venue


# =============================================================================
# Band Routes Tests
# =============================================================================

class TestBandRoutes:
    """Tests for band routes."""

    def test_bands_list(self, app, client, manager_user, sample_band):
        """Test bands list page."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get('/bands/')
        assert response.status_code == 200
        assert b'Test Band' in response.data

    def test_band_detail(self, app, client, manager_user, sample_band):
        """Test band detail page."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get(f'/bands/{sample_band.id}')
        assert response.status_code == 200
        assert b'Test Band' in response.data

    def test_create_band_form(self, app, client, manager_user):
        """Test create band form page."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get('/bands/create')
        assert response.status_code == 200

    def test_create_band_submit(self, app, client, manager_user):
        """Test creating a new band."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.post('/bands/create', data={
            'name': 'New Test Band',
            'genre': 'Electronic',
            'bio': 'A new electronic band'
        }, follow_redirects=True)

        assert response.status_code == 200

        with app.app_context():
            band = Band.query.filter_by(name='New Test Band').first()
            assert band is not None
            assert band.genre == 'Electronic'


# =============================================================================
# Tour Routes Tests
# =============================================================================

class TestTourRoutes:
    """Tests for tour routes."""

    def test_tours_list(self, app, client, manager_user, sample_tour):
        """Test tours list page."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get('/tours/')
        assert response.status_code == 200

    def test_tour_detail(self, app, client, manager_user, sample_tour):
        """Test tour detail page."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get(f'/tours/{sample_tour.id}')
        assert response.status_code == 200
        assert b'Test Tour 2025' in response.data

    def test_tour_calendar(self, app, client, manager_user, sample_tour):
        """Test tour calendar page."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get(f'/tours/{sample_tour.id}/calendar')
        assert response.status_code == 200


# =============================================================================
# Venue Routes Tests
# =============================================================================

class TestVenueRoutes:
    """Tests for venue routes."""

    def test_venues_list(self, app, client, manager_user, sample_venue):
        """Test venues list page."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get('/venues/')
        assert response.status_code == 200
        assert b'Test Venue' in response.data

    def test_venue_detail(self, app, client, manager_user, sample_venue):
        """Test venue detail page."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get(f'/venues/{sample_venue.id}')
        assert response.status_code == 200

    def test_create_venue(self, app, client, manager_user):
        """Test creating a new venue."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.post('/venues/create', data={
            'name': 'New Venue',
            'city': 'Paris',
            'country': 'France',
            'address': '123 Rue Test',
            'capacity': 1000,
            'venue_type': 'Theater'
        }, follow_redirects=True)

        assert response.status_code == 200

        with app.app_context():
            venue = Venue.query.filter_by(name='New Venue').first()
            assert venue is not None


# =============================================================================
# Guestlist Routes Tests
# =============================================================================

class TestGuestlistRoutes:
    """Tests for guestlist routes."""

    def test_guestlist_manage(self, app, client, manager_user, sample_tour_stop):
        """Test guestlist management page."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get(f'/guestlist/stop/{sample_tour_stop.id}')
        assert response.status_code == 200

    def test_guestlist_add(self, app, client, manager_user, sample_tour_stop):
        """Test adding guest to guestlist."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.post(f'/guestlist/stop/{sample_tour_stop.id}/add', data={
            'guest_name': 'New Guest',
            'guest_email': 'newguest@test.com',
            'entry_type': 'GUEST',
            'plus_ones': 1,
            'notes': 'Test guest'
        }, follow_redirects=True)

        assert response.status_code == 200

    def test_guestlist_check_in_page(self, app, client, manager_user, sample_tour_stop):
        """Test check-in interface page."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get(f'/guestlist/stop/{sample_tour_stop.id}/check-in')
        assert response.status_code == 200

    def test_guestlist_approve(self, app, client, manager_user, sample_guestlist_entry):
        """Test approving a guestlist entry."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.post(
            f'/guestlist/entry/{sample_guestlist_entry.id}/approve',
            follow_redirects=True
        )

        assert response.status_code == 200


# =============================================================================
# Search Route Tests
# =============================================================================

class TestSearchRoutes:
    """Tests for search functionality."""

    def test_search_empty(self, app, client, manager_user):
        """Test search with empty query."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get('/search')
        assert response.status_code == 200

    def test_search_with_query(self, app, client, manager_user, sample_band):
        """Test search with query."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get('/search?q=Test')
        assert response.status_code == 200

    def test_search_short_query(self, app, client, manager_user):
        """Test search with too short query."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!'
        })

        response = client.get('/search?q=T')
        assert response.status_code == 200
        # Should show message about query being too short


# =============================================================================
# Error Page Tests
# =============================================================================

class TestErrorPages:
    """Tests for error pages."""

    def test_404_page(self, client):
        """Test 404 page."""
        response = client.get('/nonexistent-page-xyz')
        assert response.status_code == 404

    def test_404_content(self, client):
        """Test 404 page has proper content."""
        response = client.get('/nonexistent-page-xyz')
        assert b'404' in response.data or b'Page non' in response.data or b'Not Found' in response.data
