"""
Tests for the REST API v1 — JWT auth, tours, stops, guestlist, notifications.
"""
import json
import pytest
from datetime import date, datetime, timedelta, time, timezone

import jwt as pyjwt

from app import create_app
from app.extensions import db
from app.models.user import User, AccessLevel, ACCESS_HIERARCHY
from app.models.tour import Tour, TourStatus
from app.models.band import Band
from app.models.venue import Venue
from app.models.tour_stop import TourStop, TourStopStatus, TourStopMember, EventType
from app.models.guestlist import GuestlistEntry, GuestlistStatus, EntryType
from app.models.notification import Notification, NotificationType
from app.models.payments import (
    TeamMemberPayment, PaymentStatus, PaymentType, PaymentFrequency,
    StaffCategory, StaffRole,
)


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


# ── Additional Fixtures ────────────────────────────────────

@pytest.fixture
def staff_user(app):
    """Create a staff-level user (lower than manager)."""
    with app.app_context():
        user = User(
            email='staff@example.com',
            first_name='Staff',
            last_name='Member',
            access_level=AccessLevel.STAFF,
            is_active=True,
            email_verified=True,
        )
        user.set_password('StaffPass123!')
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def sample_venue(app):
    """Create a sample venue."""
    with app.app_context():
        venue = Venue(
            name='Le Bataclan',
            address='50 Boulevard Voltaire',
            city='Paris',
            country='France',
            capacity=1500,
            venue_type='Concert Hall',
        )
        db.session.add(venue)
        db.session.commit()
        return venue.id


@pytest.fixture
def second_venue(app):
    """Create a second venue in a different city/country for filter tests."""
    with app.app_context():
        venue = Venue(
            name='O2 Arena',
            address='Peninsula Square',
            city='London',
            country='United Kingdom',
            capacity=20000,
            venue_type='Arena',
        )
        db.session.add(venue)
        db.session.commit()
        return venue.id


@pytest.fixture
def sample_tour_stop(app, sample_tour, sample_venue):
    """Create a tour stop linked to sample_tour and sample_venue."""
    with app.app_context():
        stop = TourStop(
            tour_id=sample_tour,
            venue_id=sample_venue,
            band_id=None,
            date=date(2026, 7, 15),
            doors_time=time(19, 0),
            soundcheck_time=time(16, 0),
            set_time=time(21, 0),
            status=TourStopStatus.CONFIRMED,
            event_type=EventType.SHOW,
            guarantee=5000.00,
            ticket_price=35.00,
            sold_tickets=300,
            currency='EUR',
        )
        db.session.add(stop)
        db.session.commit()
        return stop.id


@pytest.fixture
def second_tour_stop(app, sample_tour, sample_venue):
    """Create a second tour stop for pagination / list tests."""
    with app.app_context():
        stop = TourStop(
            tour_id=sample_tour,
            venue_id=sample_venue,
            band_id=None,
            date=date(2026, 7, 20),
            status=TourStopStatus.DRAFT,
            event_type=EventType.SHOW,
        )
        db.session.add(stop)
        db.session.commit()
        return stop.id


@pytest.fixture
def approved_guestlist_entry(app, sample_tour_stop, sample_user):
    """Create an APPROVED guestlist entry ready for check-in."""
    with app.app_context():
        entry = GuestlistEntry(
            tour_stop_id=sample_tour_stop,
            guest_name='Alice VIP',
            guest_email='alice@example.com',
            entry_type=EntryType.VIP,
            plus_ones=2,
            status=GuestlistStatus.APPROVED,
            requested_by_id=sample_user,
        )
        db.session.add(entry)
        db.session.commit()
        return entry.id


@pytest.fixture
def pending_guestlist_entry(app, sample_tour_stop, sample_user):
    """Create a PENDING guestlist entry (cannot be checked in)."""
    with app.app_context():
        entry = GuestlistEntry(
            tour_stop_id=sample_tour_stop,
            guest_name='Bob Pending',
            guest_email='bob@example.com',
            entry_type=EntryType.GUEST,
            plus_ones=0,
            status=GuestlistStatus.PENDING,
            requested_by_id=sample_user,
        )
        db.session.add(entry)
        db.session.commit()
        return entry.id


@pytest.fixture
def denied_guestlist_entry(app, sample_tour_stop, sample_user):
    """Create a DENIED guestlist entry."""
    with app.app_context():
        entry = GuestlistEntry(
            tour_stop_id=sample_tour_stop,
            guest_name='Charlie Denied',
            guest_email='charlie@example.com',
            entry_type=EntryType.PRESS,
            plus_ones=1,
            status=GuestlistStatus.DENIED,
            requested_by_id=sample_user,
        )
        db.session.add(entry)
        db.session.commit()
        return entry.id


@pytest.fixture
def sample_notification(app, sample_user):
    """Create a sample unread notification for sample_user."""
    with app.app_context():
        notif = Notification(
            user_id=sample_user,
            title='Tour Update',
            message='Your tour has been updated.',
            type=NotificationType.INFO,
            is_read=False,
        )
        db.session.add(notif)
        db.session.commit()
        return notif.id


@pytest.fixture
def read_notification(app, sample_user):
    """Create a read notification for sample_user."""
    with app.app_context():
        notif = Notification(
            user_id=sample_user,
            title='Old Notification',
            message='This was already read.',
            type=NotificationType.SUCCESS,
            is_read=True,
        )
        db.session.add(notif)
        db.session.commit()
        return notif.id


@pytest.fixture
def other_user_notification(app, admin_user):
    """Create a notification belonging to admin_user (not sample_user)."""
    with app.app_context():
        notif = Notification(
            user_id=admin_user,
            title='Admin Notification',
            message='Only for admin.',
            type=NotificationType.WARNING,
            is_read=False,
        )
        db.session.add(notif)
        db.session.commit()
        return notif.id


@pytest.fixture
def tour_stop_member_assignment(app, sample_tour_stop, sample_user):
    """Assign sample_user to sample_tour_stop via TourStopMember."""
    with app.app_context():
        assignment = TourStopMember(
            tour_stop_id=sample_tour_stop,
            user_id=sample_user,
        )
        db.session.add(assignment)
        db.session.commit()
        return assignment.id


@pytest.fixture
def sample_payment(app, sample_user, sample_tour, sample_tour_stop):
    """Create a sample payment for sample_user."""
    with app.app_context():
        payment = TeamMemberPayment(
            reference='PAY-2026-00001',
            user_id=sample_user,
            tour_id=sample_tour,
            tour_stop_id=sample_tour_stop,
            staff_category=StaffCategory.MANAGEMENT,
            staff_role=StaffRole.TOUR_MANAGER,
            payment_type=PaymentType.CACHET,
            payment_frequency=PaymentFrequency.PER_SHOW,
            amount=500.00,
            currency='EUR',
            status=PaymentStatus.PAID,
        )
        db.session.add(payment)
        db.session.commit()
        return payment.id


@pytest.fixture
def pending_payment(app, sample_user, sample_tour):
    """Create a pending payment for sample_user."""
    with app.app_context():
        payment = TeamMemberPayment(
            reference='PAY-2026-00002',
            user_id=sample_user,
            tour_id=sample_tour,
            staff_category=StaffCategory.ARTISTIC,
            staff_role=StaffRole.MUSICIAN,
            payment_type=PaymentType.CACHET,
            amount=300.00,
            currency='EUR',
            status=PaymentStatus.PENDING_APPROVAL,
        )
        db.session.add(payment)
        db.session.commit()
        return payment.id


# ── Tour Stops Tests ───────────────────────────────────────

class TestTourStops:
    """Test tour stop API endpoints."""

    def test_list_tour_stops(self, client, sample_user, sample_tour, sample_tour_stop):
        token = get_auth_token(client)
        resp = client.get(
            f'/api/v1/tours/{sample_tour}/stops',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'data' in data
        assert 'meta' in data
        assert data['meta']['total'] >= 1

    def test_list_tour_stops_tour_not_found(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.get('/api/v1/tours/99999/stops', headers=auth_header(token))
        assert resp.status_code == 404
        assert resp.get_json()['error']['code'] == 'not_found'

    def test_list_tour_stops_status_filter(
        self, client, sample_user, sample_tour, sample_tour_stop, second_tour_stop
    ):
        token = get_auth_token(client)
        # Filter confirmed only
        resp = client.get(
            f'/api/v1/tours/{sample_tour}/stops?status=confirmed',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['meta']['total'] == 1
        assert data['data'][0]['status'] == 'confirmed'

    def test_list_tour_stops_invalid_status(self, client, sample_user, sample_tour):
        token = get_auth_token(client)
        resp = client.get(
            f'/api/v1/tours/{sample_tour}/stops?status=bogus',
            headers=auth_header(token),
        )
        assert resp.status_code == 422
        assert resp.get_json()['error']['code'] == 'invalid_filter'

    def test_list_tour_stops_ordered_by_date(
        self, client, sample_user, sample_tour, sample_tour_stop, second_tour_stop
    ):
        token = get_auth_token(client)
        resp = client.get(
            f'/api/v1/tours/{sample_tour}/stops',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        items = resp.get_json()['data']
        assert len(items) == 2
        # First stop should be earlier date
        assert items[0]['date'] <= items[1]['date']

    def test_get_stop_detail(self, client, sample_user, sample_tour_stop):
        token = get_auth_token(client)
        resp = client.get(
            f'/api/v1/stops/{sample_tour_stop}',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['id'] == sample_tour_stop
        assert data['status'] == 'confirmed'
        assert data['venue'] is not None
        assert data['venue']['name'] == 'Le Bataclan'

    def test_get_stop_not_found(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.get('/api/v1/stops/99999', headers=auth_header(token))
        assert resp.status_code == 404
        assert resp.get_json()['error']['code'] == 'not_found'

    def test_stops_without_auth(self, client):
        resp = client.get('/api/v1/stops/1')
        assert resp.status_code == 401


# ── Guestlist Tests ────────────────────────────────────────

class TestGuestlist:
    """Test guestlist API endpoints."""

    def test_list_guestlist_for_stop(
        self, client, sample_user, sample_tour_stop, approved_guestlist_entry,
        pending_guestlist_entry,
    ):
        token = get_auth_token(client)
        resp = client.get(
            f'/api/v1/stops/{sample_tour_stop}/guestlist',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['meta']['total'] == 2

    def test_list_guestlist_stop_not_found(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.get('/api/v1/stops/99999/guestlist', headers=auth_header(token))
        assert resp.status_code == 404

    def test_list_guestlist_filter_by_status(
        self, client, sample_user, sample_tour_stop,
        approved_guestlist_entry, pending_guestlist_entry,
    ):
        token = get_auth_token(client)
        resp = client.get(
            f'/api/v1/stops/{sample_tour_stop}/guestlist?status=approved',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['meta']['total'] == 1
        assert data['data'][0]['status'] == 'approved'

    def test_list_guestlist_filter_invalid_status(
        self, client, sample_user, sample_tour_stop,
    ):
        token = get_auth_token(client)
        resp = client.get(
            f'/api/v1/stops/{sample_tour_stop}/guestlist?status=invalid',
            headers=auth_header(token),
        )
        assert resp.status_code == 422
        assert resp.get_json()['error']['code'] == 'invalid_filter'

    def test_list_guestlist_search_by_name(
        self, client, sample_user, sample_tour_stop,
        approved_guestlist_entry, pending_guestlist_entry,
    ):
        token = get_auth_token(client)
        resp = client.get(
            f'/api/v1/stops/{sample_tour_stop}/guestlist?q=Alice',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['meta']['total'] == 1
        assert data['data'][0]['guest_name'] == 'Alice VIP'

    def test_list_guestlist_search_no_match(
        self, client, sample_user, sample_tour_stop,
        approved_guestlist_entry,
    ):
        token = get_auth_token(client)
        resp = client.get(
            f'/api/v1/stops/{sample_tour_stop}/guestlist?q=Nonexistent',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()['meta']['total'] == 0

    def test_list_guestlist_combined_search_and_status(
        self, client, sample_user, sample_tour_stop,
        approved_guestlist_entry, pending_guestlist_entry,
    ):
        token = get_auth_token(client)
        # Search for "Bob" with status "approved" -- Bob is pending, so 0 results
        resp = client.get(
            f'/api/v1/stops/{sample_tour_stop}/guestlist?q=Bob&status=approved',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()['meta']['total'] == 0

    def test_checkin_approved_entry(
        self, client, sample_user, sample_tour_stop, approved_guestlist_entry,
    ):
        token = get_auth_token(client)
        resp = client.post(
            f'/api/v1/guestlist/{approved_guestlist_entry}/checkin',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['status'] == 'checked_in'
        assert data['checked_in_at'] is not None

    def test_checkin_pending_entry_fails(
        self, client, sample_user, sample_tour_stop, pending_guestlist_entry,
    ):
        token = get_auth_token(client)
        resp = client.post(
            f'/api/v1/guestlist/{pending_guestlist_entry}/checkin',
            headers=auth_header(token),
        )
        assert resp.status_code == 409
        assert resp.get_json()['error']['code'] == 'invalid_state'

    def test_checkin_denied_entry_fails(
        self, client, sample_user, sample_tour_stop, denied_guestlist_entry,
    ):
        token = get_auth_token(client)
        resp = client.post(
            f'/api/v1/guestlist/{denied_guestlist_entry}/checkin',
            headers=auth_header(token),
        )
        assert resp.status_code == 409
        assert resp.get_json()['error']['code'] == 'invalid_state'

    def test_checkin_entry_not_found(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.post(
            '/api/v1/guestlist/99999/checkin',
            headers=auth_header(token),
        )
        assert resp.status_code == 404

    def test_checkin_without_auth(self, client):
        resp = client.post('/api/v1/guestlist/1/checkin')
        assert resp.status_code == 401

    def test_checkin_already_checked_in(
        self, client, sample_user, sample_tour_stop, approved_guestlist_entry,
    ):
        token = get_auth_token(client)
        # First check-in should succeed
        resp = client.post(
            f'/api/v1/guestlist/{approved_guestlist_entry}/checkin',
            headers=auth_header(token),
        )
        assert resp.status_code == 200

        # Second check-in should fail (status is now checked_in, not approved)
        resp2 = client.post(
            f'/api/v1/guestlist/{approved_guestlist_entry}/checkin',
            headers=auth_header(token),
        )
        assert resp2.status_code == 409
        assert resp2.get_json()['error']['code'] == 'invalid_state'


# ── My Schedule Tests ──────────────────────────────────────

class TestMySchedule:
    """Test /me/schedule endpoint."""

    def test_schedule_empty(self, client, sample_user):
        """User with no assignments gets empty schedule."""
        token = get_auth_token(client)
        resp = client.get('/api/v1/me/schedule', headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()['meta']['total'] == 0

    def test_schedule_with_assignment(
        self, client, sample_user, sample_tour_stop, tour_stop_member_assignment,
    ):
        """User assigned to a future stop sees it in schedule."""
        token = get_auth_token(client)
        # Use from_date=2026-01-01 so the stop on 2026-07-15 is included
        resp = client.get(
            '/api/v1/me/schedule?from_date=2026-01-01',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['meta']['total'] >= 1

    def test_schedule_date_range_filter(
        self, client, sample_user, sample_tour_stop, tour_stop_member_assignment,
    ):
        """Date range that excludes the stop returns empty."""
        token = get_auth_token(client)
        # Stop is on 2026-07-15, filter only January
        resp = client.get(
            '/api/v1/me/schedule?from_date=2026-01-01&to_date=2026-01-31',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()['meta']['total'] == 0

    def test_schedule_invalid_from_date(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.get(
            '/api/v1/me/schedule?from_date=not-a-date',
            headers=auth_header(token),
        )
        assert resp.status_code == 422
        assert resp.get_json()['error']['code'] == 'invalid_filter'

    def test_schedule_invalid_to_date(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.get(
            '/api/v1/me/schedule?from_date=2026-01-01&to_date=bad',
            headers=auth_header(token),
        )
        assert resp.status_code == 422
        assert resp.get_json()['error']['code'] == 'invalid_filter'

    def test_schedule_default_from_date_is_today(
        self, client, sample_user, sample_tour_stop, tour_stop_member_assignment,
    ):
        """Without from_date, defaults to today -- future stop is included."""
        token = get_auth_token(client)
        resp = client.get('/api/v1/me/schedule', headers=auth_header(token))
        assert resp.status_code == 200
        # The stop is on 2026-07-15 which is in the future, so it should be included
        assert resp.get_json()['meta']['total'] >= 1

    def test_schedule_without_auth(self, client):
        resp = client.get('/api/v1/me/schedule')
        assert resp.status_code == 401


# ── My Payments Tests ──────────────────────────────────────

class TestMyPayments:
    """Test /me/payments endpoint."""

    def test_payments_empty(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.get('/api/v1/me/payments', headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()['meta']['total'] == 0

    def test_payments_with_data(
        self, client, sample_user, sample_payment, sample_tour_stop,
    ):
        token = get_auth_token(client)
        resp = client.get('/api/v1/me/payments', headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['meta']['total'] >= 1

    def test_payments_status_filter(
        self, client, sample_user, sample_payment, pending_payment,
        sample_tour_stop,
    ):
        token = get_auth_token(client)
        resp = client.get(
            '/api/v1/me/payments?status=paid',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['meta']['total'] == 1

    def test_payments_invalid_status_filter(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.get(
            '/api/v1/me/payments?status=nonexistent',
            headers=auth_header(token),
        )
        assert resp.status_code == 422
        assert resp.get_json()['error']['code'] == 'invalid_filter'

    def test_payments_without_auth(self, client):
        resp = client.get('/api/v1/me/payments')
        assert resp.status_code == 401


# ── Extended Notifications Tests ───────────────────────────

class TestNotificationsExtended:
    """Extended notification endpoint tests with actual data."""

    def test_list_notifications_with_data(
        self, client, sample_user, sample_notification, read_notification,
    ):
        token = get_auth_token(client)
        resp = client.get('/api/v1/notifications', headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['meta']['total'] == 2

    def test_list_notifications_unread_filter(
        self, client, sample_user, sample_notification, read_notification,
    ):
        token = get_auth_token(client)
        resp = client.get(
            '/api/v1/notifications?unread=true',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['meta']['total'] == 1
        assert data['data'][0]['is_read'] is False

    def test_list_notifications_unread_false_returns_all(
        self, client, sample_user, sample_notification, read_notification,
    ):
        """unread=false does not filter -- returns all notifications."""
        token = get_auth_token(client)
        resp = client.get(
            '/api/v1/notifications?unread=false',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()['meta']['total'] == 2

    def test_mark_single_notification_read(
        self, client, sample_user, sample_notification,
    ):
        token = get_auth_token(client)
        resp = client.post(
            f'/api/v1/notifications/{sample_notification}/read',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['is_read'] is True

    def test_mark_notification_read_not_found(self, client, sample_user):
        token = get_auth_token(client)
        resp = client.post(
            '/api/v1/notifications/99999/read',
            headers=auth_header(token),
        )
        assert resp.status_code == 404

    def test_mark_other_users_notification_returns_not_found(
        self, client, sample_user, admin_user, other_user_notification,
    ):
        """sample_user cannot mark admin_user's notification as read."""
        token = get_auth_token(client)
        resp = client.post(
            f'/api/v1/notifications/{other_user_notification}/read',
            headers=auth_header(token),
        )
        # Should be 404 because filter_by includes user_id check
        assert resp.status_code == 404

    def test_mark_all_read_with_data(
        self, client, sample_user, sample_notification, read_notification,
    ):
        token = get_auth_token(client)
        resp = client.post(
            '/api/v1/notifications/read-all',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        # Only 1 was unread (sample_notification)
        assert data['marked_read'] == 1

    def test_notifications_without_auth(self, client):
        resp = client.get('/api/v1/notifications')
        assert resp.status_code == 401

    def test_notifications_does_not_include_other_users(
        self, client, sample_user, admin_user, sample_notification,
        other_user_notification,
    ):
        """sample_user should not see admin_user's notifications."""
        token = get_auth_token(client)
        resp = client.get('/api/v1/notifications', headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        # Only sample_user's notification
        assert data['meta']['total'] == 1


# ── Extended Bands Tests ───────────────────────────────────

class TestBandsExtended:
    """Extended band search tests."""

    def test_search_bands_no_match(self, client, sample_user, sample_band):
        token = get_auth_token(client)
        resp = client.get('/api/v1/bands?q=Nonexistent', headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()['meta']['total'] == 0

    def test_search_bands_case_insensitive(self, client, sample_user, sample_band):
        token = get_auth_token(client)
        resp = client.get('/api/v1/bands?q=test', headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()['meta']['total'] >= 1

    def test_bands_without_auth(self, client):
        resp = client.get('/api/v1/bands')
        assert resp.status_code == 401


# ── Extended Venues Tests ──────────────────────────────────

class TestVenuesExtended:
    """Extended venue search and filter tests."""

    def test_list_venues_with_data(
        self, client, sample_user, sample_venue, second_venue,
    ):
        token = get_auth_token(client)
        resp = client.get('/api/v1/venues', headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()['meta']['total'] == 2

    def test_search_venues_by_name(
        self, client, sample_user, sample_venue, second_venue,
    ):
        token = get_auth_token(client)
        resp = client.get('/api/v1/venues?q=Bataclan', headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['meta']['total'] == 1
        assert data['data'][0]['name'] == 'Le Bataclan'

    def test_search_venues_by_city(
        self, client, sample_user, sample_venue, second_venue,
    ):
        """Search query also matches city name."""
        token = get_auth_token(client)
        resp = client.get('/api/v1/venues?q=London', headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['meta']['total'] == 1
        assert data['data'][0]['city'] == 'London'

    def test_filter_venues_by_city(
        self, client, sample_user, sample_venue, second_venue,
    ):
        token = get_auth_token(client)
        resp = client.get('/api/v1/venues?city=Paris', headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['meta']['total'] == 1
        assert data['data'][0]['city'] == 'Paris'

    def test_filter_venues_by_country(
        self, client, sample_user, sample_venue, second_venue,
    ):
        token = get_auth_token(client)
        resp = client.get(
            '/api/v1/venues?country=United Kingdom',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['meta']['total'] == 1
        assert data['data'][0]['country'] == 'United Kingdom'

    def test_filter_venues_city_and_country(
        self, client, sample_user, sample_venue, second_venue,
    ):
        """Combine city and country filters."""
        token = get_auth_token(client)
        resp = client.get(
            '/api/v1/venues?city=Paris&country=France',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()['meta']['total'] == 1

    def test_search_venues_no_match(self, client, sample_user, sample_venue):
        token = get_auth_token(client)
        resp = client.get(
            '/api/v1/venues?q=Nonexistent',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()['meta']['total'] == 0

    def test_venues_without_auth(self, client):
        resp = client.get('/api/v1/venues')
        assert resp.status_code == 401


# ── Decorators / RBAC Tests ───────────────────────────────

class TestDecorators:
    """Test JWT decorators and RBAC access control."""

    def test_expired_token_returns_401(self, app, client, sample_user):
        """An expired JWT access token should return 401."""
        with app.app_context():
            # Build an expired token manually using PyJWT
            payload = {
                'sub': str(sample_user),
                'type': 'access',
                'iat': datetime.now(timezone.utc) - timedelta(hours=2),
                'exp': datetime.now(timezone.utc) - timedelta(hours=1),
            }
            expired_token = pyjwt.encode(
                payload,
                app.config['SECRET_KEY'],
                algorithm='HS256',
            )

        resp = client.get(
            '/api/v1/tours',
            headers={'Authorization': f'Bearer {expired_token}'},
        )
        assert resp.status_code == 401

    def test_refresh_token_used_as_access_returns_401(self, client, sample_user):
        """Using a refresh token where an access token is expected should fail."""
        # Login to get refresh token
        login_resp = client.post('/api/v1/auth/login', json={
            'email': 'test@example.com',
            'password': 'TestPass123!',
        })
        refresh_token = login_resp.get_json()['data']['refresh_token']

        resp = client.get(
            '/api/v1/tours',
            headers={'Authorization': f'Bearer {refresh_token}'},
        )
        assert resp.status_code == 401
        assert resp.get_json()['error']['code'] == 'wrong_token_type'

    def test_missing_bearer_prefix_returns_401(self, client, sample_user):
        """Authorization header without Bearer prefix should fail."""
        token = get_auth_token(client)
        resp = client.get(
            '/api/v1/tours',
            headers={'Authorization': token},  # No "Bearer " prefix
        )
        assert resp.status_code == 401
        assert resp.get_json()['error']['code'] == 'missing_token'

    def test_deactivated_user_token_returns_401(self, app, client, sample_user):
        """Token for a deactivated user should return 401."""
        token = get_auth_token(client)
        # Now deactivate the user
        with app.app_context():
            user = db.session.get(User, sample_user)
            user.is_active = False
            db.session.commit()

        resp = client.get('/api/v1/tours', headers=auth_header(token))
        assert resp.status_code == 401
        assert resp.get_json()['error']['code'] == 'user_not_found'

    def test_token_with_invalid_user_id_returns_401(self, app, client):
        """Token referencing a non-existent user should return 401."""
        with app.app_context():
            payload = {
                'sub': '99999',
                'type': 'access',
                'iat': datetime.now(timezone.utc),
                'exp': datetime.now(timezone.utc) + timedelta(hours=1),
            }
            fake_token = pyjwt.encode(
                payload,
                app.config['SECRET_KEY'],
                algorithm='HS256',
            )

        resp = client.get(
            '/api/v1/tours',
            headers={'Authorization': f'Bearer {fake_token}'},
        )
        assert resp.status_code == 401
        assert resp.get_json()['error']['code'] == 'user_not_found'

    def test_requires_api_access_blocks_low_level_user(
        self, app, client, staff_user, sample_user,
    ):
        """Test that requires_api_access decorator denies a STAFF user
        when MANAGER level is required, by invoking the decorated function
        directly within a test request context.
        """
        from app.blueprints.api.decorators import requires_api_access

        @requires_api_access(AccessLevel.MANAGER)
        def protected_view():
            from flask import jsonify
            return jsonify({'data': 'ok'}), 200

        token_staff = get_auth_token(
            client, email='staff@example.com', password='StaffPass123!',
        )

        with app.test_request_context(
            headers={'Authorization': f'Bearer {token_staff}'},
        ):
            response = protected_view()
            # response is a tuple (Response, status_code) or Response
            if isinstance(response, tuple):
                resp_obj, status_code = response
            else:
                resp_obj = response
                status_code = resp_obj.status_code
            assert status_code == 403

    def test_requires_api_access_allows_sufficient_level(
        self, app, client, sample_user, staff_user,
    ):
        """Manager-level user should pass requires_api_access(MANAGER)."""
        from app.blueprints.api.decorators import requires_api_access

        @requires_api_access(AccessLevel.MANAGER)
        def protected_view():
            from flask import jsonify
            return jsonify({'data': 'ok'}), 200

        token = get_auth_token(client)

        with app.test_request_context(
            headers={'Authorization': f'Bearer {token}'},
        ):
            response = protected_view()
            if isinstance(response, tuple):
                _, status_code = response
            else:
                status_code = response.status_code
            assert status_code == 200

    def test_requires_api_access_allows_admin(
        self, app, client, admin_user, staff_user,
    ):
        """Admin-level user should pass requires_api_access(MANAGER)."""
        from app.blueprints.api.decorators import requires_api_access

        @requires_api_access(AccessLevel.MANAGER)
        def protected_view():
            from flask import jsonify
            return jsonify({'data': 'ok'}), 200

        token = get_auth_token(
            client, email='admin@example.com', password='AdminPass123!',
        )

        with app.test_request_context(
            headers={'Authorization': f'Bearer {token}'},
        ):
            response = protected_view()
            if isinstance(response, tuple):
                _, status_code = response
            else:
                status_code = response.status_code
            assert status_code == 200

    def test_requires_api_access_without_token(self, app, client, staff_user):
        """No token should still return 401 (not 403)."""
        from app.blueprints.api.decorators import requires_api_access

        @requires_api_access(AccessLevel.MANAGER)
        def protected_view():
            from flask import jsonify
            return jsonify({'data': 'ok'}), 200

        with app.test_request_context():
            response = protected_view()
            if isinstance(response, tuple):
                _, status_code = response
            else:
                status_code = response.status_code
            assert status_code == 401

    def test_token_with_non_integer_sub_returns_401(self, app, client):
        """Token with non-integer 'sub' field should return 401."""
        with app.app_context():
            payload = {
                'sub': 'not-a-number',
                'type': 'access',
                'iat': datetime.now(timezone.utc),
                'exp': datetime.now(timezone.utc) + timedelta(hours=1),
            }
            bad_token = pyjwt.encode(
                payload,
                app.config['SECRET_KEY'],
                algorithm='HS256',
            )

        resp = client.get(
            '/api/v1/tours',
            headers={'Authorization': f'Bearer {bad_token}'},
        )
        assert resp.status_code == 401
        assert resp.get_json()['error']['code'] == 'invalid_token'


# ── Tours Extended Tests ───────────────────────────────────

class TestToursExtended:
    """Extended tour tests — band_id filter, empty results."""

    def test_list_tours_filter_by_band_id(
        self, client, sample_user, sample_band, sample_tour,
    ):
        token = get_auth_token(client)
        resp = client.get(
            f'/api/v1/tours?band_id={sample_band}',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()['meta']['total'] >= 1

    def test_list_tours_filter_by_nonexistent_band(
        self, client, sample_user, sample_tour,
    ):
        token = get_auth_token(client)
        resp = client.get(
            '/api/v1/tours?band_id=99999',
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()['meta']['total'] == 0
