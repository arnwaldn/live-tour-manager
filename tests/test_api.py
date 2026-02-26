"""
Tests for the REST API v1 — JWT auth, tours, stops, guestlist, notifications.
"""
import json
import pytest
from datetime import date, datetime

from app import create_app
from app.extensions import db
from app.models.user import User, AccessLevel
from app.models.tour import Tour, TourStatus
from app.models.band import Band


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def sample_user(app):
    """Create a sample active user."""
    with app.app_context():
        user = User(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            access_level=AccessLevel.MANAGER,
            is_active=True,
            email_verified=True,
        )
        user.set_password('TestPass123!')
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def admin_user(app):
    """Create an admin user."""
    with app.app_context():
        user = User(
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            access_level=AccessLevel.ADMIN,
            is_active=True,
            email_verified=True,
        )
        user.set_password('AdminPass123!')
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def sample_band(app, sample_user):
    """Create a sample band."""
    with app.app_context():
        band = Band(
            name='Test Band',
            genre='Rock',
            manager_id=sample_user,
        )
        db.session.add(band)
        db.session.commit()
        return band.id


@pytest.fixture
def sample_tour(app, sample_band):
    """Create a sample tour."""
    with app.app_context():
        tour = Tour(
            name='Test Tour 2026',
            start_date=date(2026, 6, 1),
            end_date=date(2026, 8, 31),
            status=TourStatus.ACTIVE,
            band_id=sample_band,
        )
        db.session.add(tour)
        db.session.commit()
        return tour.id


def get_auth_token(client, email='test@example.com', password='TestPass123!'):
    """Helper: login and return access token."""
    resp = client.post('/api/v1/auth/login', json={
        'email': email,
        'password': password,
    })
    data = resp.get_json()
    return data['data']['access_token']


def auth_header(token):
    """Helper: build Authorization header."""
    return {'Authorization': f'Bearer {token}'}


# ── Auth Tests ──────────────────────────────────────────────

class TestAuth:
    """Test JWT authentication endpoints."""

    def test_login_success(self, client, sample_user):
        resp = client.post('/api/v1/auth/login', json={
            'email': 'test@example.com',
            'password': 'TestPass123!',
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']
        assert data['data']['token_type'] == 'Bearer'
        assert data['data']['user']['email'] == 'test@example.com'

    def test_login_invalid_password(self, client, sample_user):
        resp = client.post('/api/v1/auth/login', json={
            'email': 'test@example.com',
            'password': 'WrongPassword!',
        })
        assert resp.status_code == 401
        assert resp.get_json()['error']['code'] == 'invalid_credentials'

    def test_login_unknown_email(self, client, sample_user):
        resp = client.post('/api/v1/auth/login', json={
            'email': 'nobody@example.com',
            'password': 'TestPass123!',
        })
        assert resp.status_code == 401

    def test_login_missing_fields(self, client, sample_user):
        resp = client.post('/api/v1/auth/login', json={'email': 'test@example.com'})
        assert resp.status_code == 422
        assert resp.get_json()['error']['code'] == 'validation_error'

    def test_login_invalid_json(self, client, sample_user):
        resp = client.post('/api/v1/auth/login', data='not json',
                          content_type='text/plain')
        assert resp.status_code == 400

    def test_refresh_token(self, client, sample_user):
        # Login first
        login_resp = client.post('/api/v1/auth/login', json={
            'email': 'test@example.com',
            'password': 'TestPass123!',
        })
        refresh_token = login_resp.get_json()['data']['refresh_token']

        # Refresh
        resp = client.post('/api/v1/auth/refresh', json={
            'refresh_token': refresh_token,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'access_token' in data['data']
        assert data['data']['expires_in'] == 3600

    def test_refresh_with_access_token_fails(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.post('/api/v1/auth/refresh', json={
            'refresh_token': token,  # Wrong — this is an access token
        })
        assert resp.status_code == 401

    def test_me_endpoint(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.get('/api/v1/auth/me', headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['data']['email'] == 'test@example.com'
        assert data['data']['full_name'] == 'Test User'

    def test_me_without_token(self, client):
        resp = client.get('/api/v1/auth/me')
        assert resp.status_code == 401

    def test_me_with_invalid_token(self, client):
        resp = client.get('/api/v1/auth/me',
                         headers={'Authorization': 'Bearer invalid.token.here'})
        assert resp.status_code == 401


# ── Tours Tests ─────────────────────────────────────────────

class TestTours:
    """Test tour API endpoints."""

    def test_list_tours(self, client, sample_user, sample_tour):
        token = get_auth_token(client)
        resp = client.get('/api/v1/tours', headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'data' in data
        assert 'meta' in data
        assert data['meta']['total'] >= 1
        assert data['data'][0]['name'] == 'Test Tour 2026'

    def test_list_tours_with_status_filter(self, client, sample_user, sample_tour):
        token = get_auth_token(client)
        resp = client.get('/api/v1/tours?status=active', headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()['meta']['total'] >= 1

    def test_list_tours_with_invalid_status(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.get('/api/v1/tours?status=invalid', headers=auth_header(token))
        assert resp.status_code == 422

    def test_get_tour(self, client, sample_user, sample_tour):
        token = get_auth_token(client)
        resp = client.get(f'/api/v1/tours/{sample_tour}', headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['data']['name'] == 'Test Tour 2026'
        assert data['data']['status'] == 'active'

    def test_get_tour_not_found(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.get('/api/v1/tours/99999', headers=auth_header(token))
        assert resp.status_code == 404

    def test_tours_without_auth(self, client):
        resp = client.get('/api/v1/tours')
        assert resp.status_code == 401


# ── Pagination Tests ────────────────────────────────────────

class TestPagination:
    """Test pagination behavior."""

    def test_pagination_defaults(self, client, sample_user, sample_tour):
        token = get_auth_token(client)
        resp = client.get('/api/v1/tours', headers=auth_header(token))
        meta = resp.get_json()['meta']
        assert meta['page'] == 1
        assert meta['per_page'] == 20

    def test_pagination_custom_page(self, client, sample_user, sample_tour):
        token = get_auth_token(client)
        resp = client.get('/api/v1/tours?page=1&per_page=5', headers=auth_header(token))
        meta = resp.get_json()['meta']
        assert meta['per_page'] == 5

    def test_pagination_links(self, client, sample_user, sample_tour):
        token = get_auth_token(client)
        resp = client.get('/api/v1/tours', headers=auth_header(token))
        links = resp.get_json()['links']
        assert 'self' in links
        assert 'first' in links
        assert 'last' in links


# ── Error Handling Tests ────────────────────────────────────

class TestErrorHandling:
    """Test API-specific error responses."""

    def test_404_returns_json(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.get('/api/v1/nonexistent', headers=auth_header(token))
        assert resp.status_code == 404
        data = resp.get_json()
        assert data['error']['code'] == 'not_found'

    def test_inactive_user_cannot_login(self, app, client):
        with app.app_context():
            user = User(
                email='inactive@example.com',
                first_name='Inactive',
                last_name='User',
                access_level=AccessLevel.STAFF,
                is_active=False,
                email_verified=True,
            )
            user.set_password('TestPass123!')
            db.session.add(user)
            db.session.commit()

        resp = client.post('/api/v1/auth/login', json={
            'email': 'inactive@example.com',
            'password': 'TestPass123!',
        })
        assert resp.status_code == 403
        assert resp.get_json()['error']['code'] == 'account_inactive'


# ── Bands & Venues Tests ───────────────────────────────────

class TestBandsAndVenues:
    """Test bands and venues endpoints."""

    def test_list_bands(self, client, sample_user, sample_band):
        token = get_auth_token(client)
        resp = client.get('/api/v1/bands', headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['meta']['total'] >= 1

    def test_search_bands(self, client, sample_user, sample_band):
        token = get_auth_token(client)
        resp = client.get('/api/v1/bands?q=Test', headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()['meta']['total'] >= 1

    def test_list_venues(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.get('/api/v1/venues', headers=auth_header(token))
        assert resp.status_code == 200


# ── Notifications Tests ─────────────────────────────────────

class TestNotifications:
    """Test notification endpoints."""

    def test_list_notifications_empty(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.get('/api/v1/notifications', headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()['meta']['total'] == 0

    def test_mark_all_read(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.post('/api/v1/notifications/read-all',
                          headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()['data']['marked_read'] == 0
