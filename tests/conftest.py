# =============================================================================
# Tour Manager - Pytest Fixtures Configuration
# =============================================================================

import pytest
from datetime import date, time, timedelta

from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.band import Band, BandMembership
from app.models.venue import Venue
from app.models.tour import Tour, TourStatus
from app.models.tour_stop import TourStop, TourStopStatus
from app.models.guestlist import GuestlistEntry, GuestlistStatus, EntryType


# =============================================================================
# Application Fixtures
# =============================================================================

@pytest.fixture(scope='function')
def app():
    """Create and configure test application with SQLite in-memory database."""
    # Create app with 'testing' config (uses SQLite in-memory)
    application = create_app('testing')

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Test client for HTTP requests."""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """CLI test runner."""
    return app.test_cli_runner()


# =============================================================================
# Database Session Fixture
# =============================================================================

@pytest.fixture(scope='function')
def session(app):
    """Database session for tests."""
    yield db.session


# =============================================================================
# Role Fixtures
# =============================================================================

@pytest.fixture
def manager_role(app):
    """Create Manager role and return its ID."""
    role = Role(
        name='MANAGER',
        description='Tour/Band Manager',
        permissions=[
            'manage_band', 'manage_tour', 'manage_guestlist',
            'view_tour', 'view_show', 'check_in_guests'
        ]
    )
    db.session.add(role)
    db.session.commit()
    role_id = role.id
    db.session.expire_all()
    return db.session.get(Role, role_id)


@pytest.fixture
def musician_role(app):
    """Create Musician role and return its ID."""
    role = Role(
        name='MUSICIAN',
        description='Band Member',
        permissions=['view_tour', 'view_show', 'request_guestlist']
    )
    db.session.add(role)
    db.session.commit()
    role_id = role.id
    db.session.expire_all()
    return db.session.get(Role, role_id)


@pytest.fixture
def guestlist_manager_role(app):
    """Create Guestlist Manager role and return its ID."""
    role = Role(
        name='GUESTLIST_MANAGER',
        description='Guestlist Manager',
        permissions=[
            'manage_guestlist', 'view_show', 'check_in_guests', 'export_guestlist'
        ]
    )
    db.session.add(role)
    db.session.commit()
    role_id = role.id
    db.session.expire_all()
    return db.session.get(Role, role_id)


# =============================================================================
# User Fixtures
# =============================================================================

@pytest.fixture
def manager_user(app, manager_role):
    """Create a manager user."""
    user = User(
        email='manager@test.com',
        first_name='Test',
        last_name='Manager',
        phone='+33 1 23 45 67 89'
    )
    user.set_password('Manager123!')
    user.roles.append(manager_role)
    db.session.add(user)
    db.session.commit()
    user_id = user.id
    db.session.expire_all()
    return db.session.get(User, user_id)


@pytest.fixture
def musician_user(app, musician_role):
    """Create a musician user."""
    user = User(
        email='musician@test.com',
        first_name='Test',
        last_name='Musician',
        phone='+33 1 98 76 54 32'
    )
    user.set_password('Musician123!')
    user.roles.append(musician_role)
    db.session.add(user)
    db.session.commit()
    user_id = user.id
    db.session.expire_all()
    return db.session.get(User, user_id)


# =============================================================================
# Band Fixtures
# =============================================================================

@pytest.fixture
def sample_band(app, manager_user):
    """Create a sample band."""
    band = Band(
        name='Test Band',
        genre='Rock',
        bio='A test band for testing purposes.',
        manager=manager_user
    )
    db.session.add(band)
    db.session.commit()
    band_id = band.id
    db.session.expire_all()
    return db.session.get(Band, band_id)


# =============================================================================
# Venue Fixtures
# =============================================================================

@pytest.fixture
def sample_venue(app):
    """Create a sample venue."""
    venue = Venue(
        name='Test Venue',
        address='123 Test Street',
        city='Test City',
        country='France',
        capacity=500,
        venue_type='Concert Hall',
        website='https://test-venue.com'
    )
    db.session.add(venue)
    db.session.commit()
    venue_id = venue.id
    db.session.expire_all()
    return db.session.get(Venue, venue_id)


# =============================================================================
# Tour Fixtures
# =============================================================================

@pytest.fixture
def sample_tour(app, sample_band):
    """Create a sample tour."""
    tour = Tour(
        name='Test Tour 2025',
        description='A test tour for testing.',
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        status=TourStatus.CONFIRMED,
        band=sample_band
    )
    db.session.add(tour)
    db.session.commit()
    tour_id = tour.id
    db.session.expire_all()
    return db.session.get(Tour, tour_id)


# =============================================================================
# Tour Stop Fixtures
# =============================================================================

@pytest.fixture
def sample_tour_stop(app, sample_tour, sample_venue):
    """Create a sample tour stop."""
    stop = TourStop(
        tour=sample_tour,
        venue=sample_venue,
        date=date.today() + timedelta(days=7),
        doors_time=time(19, 0),
        soundcheck_time=time(16, 0),
        set_time=time(21, 0),
        status=TourStopStatus.CONFIRMED
    )
    db.session.add(stop)
    db.session.commit()
    stop_id = stop.id
    db.session.expire_all()
    return db.session.get(TourStop, stop_id)


# =============================================================================
# Guestlist Fixtures
# =============================================================================

@pytest.fixture
def sample_guestlist_entry(app, sample_tour_stop, manager_user):
    """Create a sample guestlist entry."""
    entry = GuestlistEntry(
        guest_name='John Doe',
        guest_email='john@example.com',
        entry_type=EntryType.VIP,
        plus_ones=1,
        notes='VIP guest',
        status=GuestlistStatus.PENDING,
        tour_stop=sample_tour_stop,
        requested_by=manager_user
    )
    db.session.add(entry)
    db.session.commit()
    entry_id = entry.id
    db.session.expire_all()
    return db.session.get(GuestlistEntry, entry_id)


# =============================================================================
# Authentication Helpers
# =============================================================================

@pytest.fixture
def authenticated_client(client, app, manager_user):
    """Client with logged-in manager user."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(manager_user.id)
        sess['_fresh'] = True
    return client


# =============================================================================
# Financial Tour Stop Fixtures
# =============================================================================

@pytest.fixture
def tour_stop_with_guarantee(app, sample_tour, sample_venue):
    """Create a tour stop with guarantee only (no door deal)."""
    stop = TourStop(
        tour=sample_tour,
        venue=sample_venue,
        date=date.today() + timedelta(days=14),
        doors_time=time(19, 0),
        soundcheck_time=time(16, 0),
        set_time=time(21, 0),
        status=TourStopStatus.CONFIRMED,
        guarantee=5000.00,
        ticket_price=35.00,
        sold_tickets=350,
        currency='EUR'
    )
    db.session.add(stop)
    db.session.commit()
    stop_id = stop.id
    db.session.expire_all()
    return db.session.get(TourStop, stop_id)


@pytest.fixture
def tour_stop_with_door_deal(app, sample_tour, sample_venue):
    """Create a tour stop with guarantee + door deal."""
    stop = TourStop(
        tour=sample_tour,
        venue=sample_venue,
        date=date.today() + timedelta(days=21),
        doors_time=time(20, 0),
        soundcheck_time=time(17, 0),
        set_time=time(22, 0),
        status=TourStopStatus.CONFIRMED,
        guarantee=3000.00,
        ticket_price=40.00,
        sold_tickets=400,
        door_deal_percentage=15.0,
        ticketing_fee_percentage=6.0,
        currency='EUR'
    )
    db.session.add(stop)
    db.session.commit()
    stop_id = stop.id
    db.session.expire_all()
    return db.session.get(TourStop, stop_id)


@pytest.fixture
def tour_stop_sold_out(app, sample_tour, sample_venue):
    """Create a sold-out tour stop for fill rate testing."""
    stop = TourStop(
        tour=sample_tour,
        venue=sample_venue,
        date=date.today() + timedelta(days=28),
        doors_time=time(19, 30),
        set_time=time(21, 30),
        status=TourStopStatus.CONFIRMED,
        guarantee=8000.00,
        ticket_price=50.00,
        sold_tickets=500,  # Same as venue capacity
        ticketing_fee_percentage=5.0,
        currency='EUR'
    )
    db.session.add(stop)
    db.session.commit()
    stop_id = stop.id
    db.session.expire_all()
    return db.session.get(TourStop, stop_id)


@pytest.fixture
def venue_no_capacity(app):
    """Create a venue without capacity (for Bug #3 testing)."""
    venue = Venue(
        name='Mystery Club',
        address='Unknown Address',
        city='Paris',
        country='France',
        capacity=None,  # No capacity
        venue_type='Club'
    )
    db.session.add(venue)
    db.session.commit()
    venue_id = venue.id
    db.session.expire_all()
    return db.session.get(Venue, venue_id)


@pytest.fixture
def tour_stop_no_capacity(app, sample_tour, venue_no_capacity):
    """Create a tour stop with venue without capacity (Bug #3 & #4)."""
    stop = TourStop(
        tour=sample_tour,
        venue=venue_no_capacity,
        date=date.today() + timedelta(days=35),
        doors_time=time(20, 0),
        set_time=time(22, 0),
        status=TourStopStatus.CONFIRMED,
        guarantee=2000.00,
        ticket_price=25.00,
        sold_tickets=150,
        currency='EUR'
    )
    db.session.add(stop)
    db.session.commit()
    stop_id = stop.id
    db.session.expire_all()
    return db.session.get(TourStop, stop_id)


@pytest.fixture
def tour_with_multiple_stops(app, sample_band, sample_venue):
    """Create a tour with multiple stops for aggregation testing."""
    tour = Tour(
        name='Multi-Stop Tour',
        description='Tour with multiple stops for testing',
        start_date=date.today(),
        end_date=date.today() + timedelta(days=60),
        status=TourStatus.CONFIRMED,
        band=sample_band
    )
    db.session.add(tour)
    db.session.flush()

    # Add 3 stops
    stops = [
        TourStop(
            tour=tour,
            venue=sample_venue,
            date=date.today() + timedelta(days=10),
            status=TourStopStatus.CONFIRMED,
            guarantee=5000.00,
            ticket_price=30.00,
            sold_tickets=300,
            currency='EUR'
        ),
        TourStop(
            tour=tour,
            venue=sample_venue,
            date=date.today() + timedelta(days=20),
            status=TourStopStatus.CONFIRMED,
            guarantee=6000.00,
            ticket_price=35.00,
            sold_tickets=400,
            door_deal_percentage=10.0,
            currency='EUR'
        ),
        TourStop(
            tour=tour,
            venue=sample_venue,
            date=date.today() + timedelta(days=30),
            status=TourStopStatus.CONFIRMED,
            guarantee=7000.00,
            ticket_price=40.00,
            sold_tickets=450,
            currency='EUR'
        ),
    ]
    for stop in stops:
        db.session.add(stop)

    db.session.commit()
    tour_id = tour.id
    db.session.expire_all()
    return db.session.get(Tour, tour_id)


# =============================================================================
# Utility Functions
# =============================================================================

def login(client, email, password):
    """Helper function to login a user."""
    return client.post('/auth/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)


def logout(client):
    """Helper function to logout."""
    return client.get('/auth/logout', follow_redirects=True)
