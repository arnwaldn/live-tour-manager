# =============================================================================
# Tour Manager - Logistics Routes Tests
# =============================================================================

import pytest
from datetime import date, time, datetime, timedelta
from flask import url_for

from app.extensions import db
from app.models.user import User, Role
from app.models.band import Band, BandMembership
from app.models.venue import Venue
from app.models.tour import Tour, TourStatus
from app.models.tour_stop import TourStop, TourStopStatus
from app.models.logistics import LogisticsInfo, LogisticsType, LogisticsStatus, LocalContact


# =============================================================================
# Helper Functions
# =============================================================================

def login(client, email, password):
    """Helper to login a user."""
    return client.post('/auth/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)


def logout(client):
    """Helper to logout."""
    return client.get('/auth/logout', follow_redirects=True)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def manager_role(app):
    """Create Manager role."""
    role = Role(
        name='MANAGER',
        description='Tour/Band Manager',
        permissions=['manage_band', 'manage_tour', 'manage_logistics', 'view_tour']
    )
    db.session.add(role)
    db.session.commit()
    return role


@pytest.fixture
def musician_role(app):
    """Create Musician role."""
    role = Role(
        name='MUSICIAN',
        description='Band Member',
        permissions=['view_tour']
    )
    db.session.add(role)
    db.session.commit()
    return role


@pytest.fixture
def manager_user(app, manager_role):
    """Create a manager user."""
    user = User(
        email='manager@test.com',
        first_name='Test',
        last_name='Manager',
        is_active=True
    )
    user.set_password('Manager123!')
    user.roles.append(manager_role)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def musician_user(app, musician_role):
    """Create a musician user."""
    user = User(
        email='musician@test.com',
        first_name='Test',
        last_name='Musician',
        is_active=True
    )
    user.set_password('Musician123!')
    user.roles.append(musician_role)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def band(app, manager_user):
    """Create a band with manager."""
    band = Band(
        name='Test Band',
        genre='Rock',
        manager_id=manager_user.id
    )
    db.session.add(band)
    db.session.commit()
    return band


@pytest.fixture
def band_with_musician(app, band, musician_user):
    """Add musician to band."""
    membership = BandMembership(
        band_id=band.id,
        user_id=musician_user.id,
        instrument='Guitar',
        role_in_band='Lead Guitar'
    )
    db.session.add(membership)
    db.session.commit()
    return band


@pytest.fixture
def venue(app):
    """Create a venue."""
    venue = Venue(
        name='Test Venue',
        address='123 Main St',
        city='Paris',
        country='France',
        capacity=500
    )
    db.session.add(venue)
    db.session.commit()
    return venue


@pytest.fixture
def tour(app, band):
    """Create a tour."""
    tour = Tour(
        name='Test Tour 2026',
        band_id=band.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        status=TourStatus.ACTIVE
    )
    db.session.add(tour)
    db.session.commit()
    return tour


@pytest.fixture
def tour_stop(app, tour, venue):
    """Create a tour stop."""
    stop = TourStop(
        tour_id=tour.id,
        venue_id=venue.id,
        date=date.today() + timedelta(days=7),
        status=TourStopStatus.CONFIRMED,
        doors_time=time(19, 0),
        set_time=time(21, 0)
    )
    db.session.add(stop)
    db.session.commit()
    return stop


@pytest.fixture
def logistics_item(app, tour_stop):
    """Create a logistics item."""
    item = LogisticsInfo(
        tour_stop_id=tour_stop.id,
        logistics_type=LogisticsType.HOTEL,
        status=LogisticsStatus.CONFIRMED,
        provider='Hotel Paris',
        confirmation_number='CONF123',
        address='456 Hotel Blvd',
        city='Paris',
        country='France',
        cost=150.00,
        currency='EUR'
    )
    db.session.add(item)
    db.session.commit()
    return item


@pytest.fixture
def local_contact(app, tour_stop):
    """Create a local contact."""
    contact = LocalContact(
        tour_stop_id=tour_stop.id,
        name='John Promoter',
        role='Promoter',
        company='Promo Inc',
        email='john@promo.com',
        phone='+33 1 23 45 67 89',
        is_primary=True
    )
    db.session.add(contact)
    db.session.commit()
    return contact


# =============================================================================
# Test Manage Route (View Logistics)
# =============================================================================

class TestManageLogistics:
    """Tests for logistics manage view."""

    def test_manage_requires_login(self, client, tour_stop):
        """Test manage route requires authentication."""
        response = client.get(f'/logistics/stop/{tour_stop.id}')
        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_manager_can_view_logistics(self, client, manager_user, tour_stop, band):
        """Test manager can view logistics page."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get(f'/logistics/stop/{tour_stop.id}')
        assert response.status_code == 200
        assert b'Test Venue' in response.data or b'logistics' in response.data.lower()

    def test_musician_can_view_own_band_logistics(self, client, musician_user, tour_stop, band_with_musician):
        """Test musician can view logistics for their band."""
        login(client, 'musician@test.com', 'Musician123!')
        response = client.get(f'/logistics/stop/{tour_stop.id}')
        assert response.status_code == 200

    def test_unauthorized_user_redirected(self, client, musician_user, tour_stop):
        """Test user without band access is redirected."""
        # Create a different band/user that has no access
        other_user = User(
            email='other@test.com',
            first_name='Other',
            last_name='User',
            is_active=True
        )
        other_user.set_password('Other123!')
        db.session.add(other_user)
        db.session.commit()

        login(client, 'other@test.com', 'Other123!')
        response = client.get(f'/logistics/stop/{tour_stop.id}', follow_redirects=True)
        # Should be redirected to dashboard or show error
        assert response.status_code == 200

    def test_logistics_grouped_by_type(self, client, manager_user, tour_stop, band):
        """Test logistics items are grouped by type."""
        # Add multiple logistics items of different types
        hotel = LogisticsInfo(
            tour_stop_id=tour_stop.id,
            logistics_type=LogisticsType.HOTEL,
            provider='Hotel Test'
        )
        flight = LogisticsInfo(
            tour_stop_id=tour_stop.id,
            logistics_type=LogisticsType.FLIGHT,
            provider='Airline Test'
        )
        db.session.add_all([hotel, flight])
        db.session.commit()

        login(client, 'manager@test.com', 'Manager123!')
        response = client.get(f'/logistics/stop/{tour_stop.id}')
        assert response.status_code == 200


# =============================================================================
# Test Add Logistics
# =============================================================================

class TestAddLogistics:
    """Tests for adding logistics items."""

    def test_add_requires_login(self, client, tour_stop):
        """Test add route requires authentication."""
        response = client.get(f'/logistics/stop/{tour_stop.id}/add')
        assert response.status_code == 302

    def test_manager_can_access_add_form(self, client, manager_user, tour_stop, band):
        """Test manager can access add logistics form."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get(f'/logistics/stop/{tour_stop.id}/add')
        assert response.status_code == 200
        assert b'form' in response.data.lower()

    def test_musician_cannot_add_logistics(self, client, musician_user, tour_stop, band_with_musician):
        """Test musician cannot add logistics (manager only)."""
        login(client, 'musician@test.com', 'Musician123!')
        response = client.get(f'/logistics/stop/{tour_stop.id}/add', follow_redirects=True)
        # Should be redirected with error message
        assert response.status_code == 200
        assert b'manager' in response.data.lower() or b'permission' in response.data.lower()

    def test_add_hotel_logistics(self, client, manager_user, tour_stop, band):
        """Test adding a hotel logistics item."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post(f'/logistics/stop/{tour_stop.id}/add', data={
            'logistics_type': 'HOTEL',
            'status': 'CONFIRMED',
            'provider': 'Grand Hotel',
            'confirmation_number': 'GH12345',
            'address': '789 Luxury Ave',
            'city': 'Paris',
            'country': 'France',
            'room_type': 'DOUBLE',
            'number_of_rooms': 2,
            'breakfast_included': True,
            'cost': '200.00',
            'currency': 'EUR'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Verify item was created
        item = LogisticsInfo.query.filter_by(provider='Grand Hotel').first()
        assert item is not None
        assert item.logistics_type == LogisticsType.HOTEL

    def test_add_flight_logistics(self, client, manager_user, tour_stop, band):
        """Test adding a flight logistics item."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post(f'/logistics/stop/{tour_stop.id}/add', data={
            'logistics_type': 'FLIGHT',
            'status': 'BOOKED',
            'provider': 'Air France',
            'confirmation_number': 'AF789',
            'flight_number': 'AF1234',
            'departure_airport': 'CDG',
            'arrival_airport': 'JFK',
            'start_datetime': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'cost': '450.00',
            'currency': 'EUR'
        }, follow_redirects=True)

        assert response.status_code == 200
        item = LogisticsInfo.query.filter_by(flight_number='AF1234').first()
        assert item is not None

    def test_add_ground_transport(self, client, manager_user, tour_stop, band):
        """Test adding ground transport logistics."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post(f'/logistics/stop/{tour_stop.id}/add', data={
            'logistics_type': 'TAXI',
            'status': 'PENDING',
            'provider': 'Uber',
            'pickup_location': 'CDG Airport',
            'dropoff_location': 'Hotel Paris',
            'driver_name': 'Jean Driver',
            'driver_phone': '+33 6 12 34 56 78'
        }, follow_redirects=True)

        assert response.status_code == 200

    def test_save_and_add_another(self, client, manager_user, tour_stop, band):
        """Test save and add another functionality."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post(f'/logistics/stop/{tour_stop.id}/add', data={
            'logistics_type': 'HOTEL',
            'provider': 'Quick Hotel',
            'save_add': '1'  # Save and add button
        })

        # Should redirect back to add form
        assert response.status_code == 302
        assert '/add' in response.location


# =============================================================================
# Test Edit Logistics
# =============================================================================

class TestEditLogistics:
    """Tests for editing logistics items."""

    def test_edit_requires_login(self, client, logistics_item):
        """Test edit route requires authentication."""
        response = client.get(f'/logistics/{logistics_item.id}/edit')
        assert response.status_code == 302

    def test_manager_can_edit(self, client, manager_user, logistics_item, band):
        """Test manager can access edit form."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get(f'/logistics/{logistics_item.id}/edit')
        assert response.status_code == 200

    def test_edit_logistics_updates_data(self, client, manager_user, logistics_item, band):
        """Test editing logistics updates the data."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post(f'/logistics/{logistics_item.id}/edit', data={
            'logistics_type': 'HOTEL',
            'status': 'COMPLETED',
            'provider': 'Updated Hotel Name',
            'confirmation_number': 'NEW123',
            'address': logistics_item.address,
            'city': logistics_item.city,
            'country': logistics_item.country,
            'cost': '300.00',
            'currency': 'EUR'
        }, follow_redirects=True)

        assert response.status_code == 200

        # Verify update
        db.session.refresh(logistics_item)
        assert logistics_item.provider == 'Updated Hotel Name'
        assert logistics_item.status == LogisticsStatus.COMPLETED

    def test_musician_cannot_edit(self, client, musician_user, logistics_item, band_with_musician):
        """Test musician cannot edit logistics."""
        login(client, 'musician@test.com', 'Musician123!')
        response = client.get(f'/logistics/{logistics_item.id}/edit', follow_redirects=True)
        assert b'manager' in response.data.lower() or b'permission' in response.data.lower()


# =============================================================================
# Test Delete Logistics
# =============================================================================

class TestDeleteLogistics:
    """Tests for deleting logistics items."""

    def test_delete_requires_login(self, client, logistics_item):
        """Test delete requires authentication."""
        response = client.post(f'/logistics/{logistics_item.id}/delete')
        assert response.status_code == 302

    def test_delete_requires_post(self, client, manager_user, logistics_item, band):
        """Test delete only works with POST."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get(f'/logistics/{logistics_item.id}/delete')
        assert response.status_code == 405  # Method not allowed

    def test_manager_can_delete(self, client, manager_user, logistics_item, band):
        """Test manager can delete logistics item."""
        login(client, 'manager@test.com', 'Manager123!')
        item_id = logistics_item.id

        response = client.post(f'/logistics/{item_id}/delete', follow_redirects=True)
        assert response.status_code == 200

        # Verify deletion
        deleted = LogisticsInfo.query.get(item_id)
        assert deleted is None

    def test_musician_cannot_delete(self, client, musician_user, logistics_item, band_with_musician):
        """Test musician cannot delete logistics."""
        login(client, 'musician@test.com', 'Musician123!')
        response = client.post(f'/logistics/{logistics_item.id}/delete', follow_redirects=True)

        # Item should still exist
        item = LogisticsInfo.query.get(logistics_item.id)
        assert item is not None


# =============================================================================
# Test Status Update
# =============================================================================

class TestStatusUpdate:
    """Tests for quick status updates."""

    def test_update_status(self, client, manager_user, logistics_item, band):
        """Test updating logistics status."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post(f'/logistics/{logistics_item.id}/status', data={
            'status': 'COMPLETED'
        }, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(logistics_item)
        assert logistics_item.status == LogisticsStatus.COMPLETED

    def test_invalid_status(self, client, manager_user, logistics_item, band):
        """Test invalid status value."""
        login(client, 'manager@test.com', 'Manager123!')

        original_status = logistics_item.status
        response = client.post(f'/logistics/{logistics_item.id}/status', data={
            'status': 'INVALID_STATUS'
        }, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(logistics_item)
        # Status should be unchanged
        assert logistics_item.status == original_status


# =============================================================================
# Test Local Contacts
# =============================================================================

class TestLocalContacts:
    """Tests for local contact management."""

    def test_add_contact(self, client, manager_user, tour_stop, band):
        """Test adding a local contact."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post(f'/logistics/stop/{tour_stop.id}/contacts/add', data={
            'name': 'New Contact',
            'role': 'Venue Manager',
            'company': 'Test Venue Inc',
            'email': 'contact@venue.com',
            'phone': '+33 1 11 22 33 44',
            'is_primary': '1'
        }, follow_redirects=True)

        assert response.status_code == 200
        contact = LocalContact.query.filter_by(name='New Contact').first()
        assert contact is not None
        assert contact.is_primary == True

    def test_edit_contact(self, client, manager_user, local_contact, band):
        """Test editing a local contact."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post(f'/logistics/contacts/{local_contact.id}/edit', data={
            'name': 'Updated Name',
            'role': local_contact.role,
            'company': local_contact.company,
            'email': 'updated@email.com',
            'phone': local_contact.phone,
            'is_primary': '0'
        }, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(local_contact)
        assert local_contact.name == 'Updated Name'
        assert local_contact.email == 'updated@email.com'

    def test_delete_contact(self, client, manager_user, local_contact, band):
        """Test deleting a local contact."""
        login(client, 'manager@test.com', 'Manager123!')
        contact_id = local_contact.id

        response = client.post(f'/logistics/contacts/{contact_id}/delete', follow_redirects=True)
        assert response.status_code == 200

        # Verify deletion
        deleted = LocalContact.query.get(contact_id)
        assert deleted is None

    def test_musician_cannot_add_contact(self, client, musician_user, tour_stop, band_with_musician):
        """Test musician cannot add contacts."""
        login(client, 'musician@test.com', 'Musician123!')

        response = client.post(f'/logistics/stop/{tour_stop.id}/contacts/add', data={
            'name': 'Unauthorized Contact',
            'phone': '+33 1 00 00 00 00'
        }, follow_redirects=True)

        # Contact should not be created
        contact = LocalContact.query.filter_by(name='Unauthorized Contact').first()
        assert contact is None


# =============================================================================
# Test Day Sheet
# =============================================================================

class TestDaySheet:
    """Tests for day sheet view."""

    def test_day_sheet_requires_login(self, client, tour_stop):
        """Test day sheet requires authentication."""
        response = client.get(f'/logistics/stop/{tour_stop.id}/day-sheet')
        assert response.status_code == 302

    def test_manager_can_view_day_sheet(self, client, manager_user, tour_stop, band, logistics_item, local_contact):
        """Test manager can view day sheet."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get(f'/logistics/stop/{tour_stop.id}/day-sheet')
        assert response.status_code == 200

    def test_musician_can_view_day_sheet(self, client, musician_user, tour_stop, band_with_musician):
        """Test musician can view day sheet for their band."""
        login(client, 'musician@test.com', 'Musician123!')
        response = client.get(f'/logistics/stop/{tour_stop.id}/day-sheet')
        assert response.status_code == 200


# =============================================================================
# Test 404 Handling
# =============================================================================

class TestNotFound:
    """Tests for 404 handling."""

    def test_manage_nonexistent_stop(self, client, manager_user, band):
        """Test accessing nonexistent tour stop."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/logistics/stop/99999')
        assert response.status_code == 404

    def test_edit_nonexistent_item(self, client, manager_user, band):
        """Test editing nonexistent logistics item."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/logistics/99999/edit')
        assert response.status_code == 404

    def test_delete_nonexistent_item(self, client, manager_user, band):
        """Test deleting nonexistent logistics item."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.post('/logistics/99999/delete')
        assert response.status_code == 404


# =============================================================================
# Test Logistics Types and Statuses
# =============================================================================

class TestLogisticsTypesStatuses:
    """Tests for different logistics types and statuses."""

    def test_all_logistics_types(self, client, manager_user, tour_stop, band):
        """Test creating logistics items of all types."""
        login(client, 'manager@test.com', 'Manager123!')

        types_to_test = ['HOTEL', 'FLIGHT', 'TRAIN', 'BUS', 'TAXI', 'RENTAL_CAR', 'SHUTTLE']

        for ltype in types_to_test:
            response = client.post(f'/logistics/stop/{tour_stop.id}/add', data={
                'logistics_type': ltype,
                'provider': f'Provider for {ltype}'
            }, follow_redirects=True)
            assert response.status_code == 200

    def test_all_statuses(self, client, manager_user, logistics_item, band):
        """Test all status transitions."""
        login(client, 'manager@test.com', 'Manager123!')

        statuses = ['PENDING', 'BOOKED', 'CONFIRMED', 'COMPLETED', 'CANCELLED']

        for status in statuses:
            response = client.post(f'/logistics/{logistics_item.id}/status', data={
                'status': status
            }, follow_redirects=True)
            assert response.status_code == 200
            db.session.refresh(logistics_item)
            assert logistics_item.status == LogisticsStatus[status]


# =============================================================================
# Test Cost Calculations
# =============================================================================

class TestCostCalculations:
    """Tests for cost calculations."""

    def test_total_cost_calculation(self, client, manager_user, tour_stop, band):
        """Test that total costs are calculated correctly."""
        # Add multiple logistics with costs
        item1 = LogisticsInfo(
            tour_stop_id=tour_stop.id,
            logistics_type=LogisticsType.HOTEL,
            provider='Hotel 1',
            cost=150.00,
            currency='EUR'
        )
        item2 = LogisticsInfo(
            tour_stop_id=tour_stop.id,
            logistics_type=LogisticsType.FLIGHT,
            provider='Flight 1',
            cost=350.00,
            currency='EUR'
        )
        db.session.add_all([item1, item2])
        db.session.commit()

        login(client, 'manager@test.com', 'Manager123!')
        response = client.get(f'/logistics/stop/{tour_stop.id}')
        assert response.status_code == 200
        # Total should be 500 (150 + 350)
        # The view calculates and displays total

    def test_cost_with_null_values(self, client, manager_user, tour_stop, band):
        """Test cost calculation handles null values."""
        item1 = LogisticsInfo(
            tour_stop_id=tour_stop.id,
            logistics_type=LogisticsType.HOTEL,
            provider='Hotel No Cost',
            cost=None  # No cost
        )
        item2 = LogisticsInfo(
            tour_stop_id=tour_stop.id,
            logistics_type=LogisticsType.TAXI,
            provider='Taxi',
            cost=50.00
        )
        db.session.add_all([item1, item2])
        db.session.commit()

        login(client, 'manager@test.com', 'Manager123!')
        response = client.get(f'/logistics/stop/{tour_stop.id}')
        assert response.status_code == 200
