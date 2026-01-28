# =============================================================================
# Tour Manager - Model Unit Tests
# =============================================================================

import pytest
from datetime import date, time, timedelta

from app.extensions import db
from app.models.user import User, Role
from app.models.band import Band, BandMembership
from app.models.venue import Venue
from app.models.tour import Tour, TourStatus
from app.models.tour_stop import TourStop, TourStopStatus
from app.models.guestlist import GuestlistEntry, GuestlistStatus, EntryType
from app.models.logistics import LogisticsInfo, LogisticsType


# =============================================================================
# User Model Tests
# =============================================================================

class TestUserModel:
    """Tests for User model."""

    def test_create_user(self, app):
        """Test user creation."""
        with app.app_context():
            user = User(
                email='test@example.com',
                first_name='Test',
                last_name='User'
            )
            user.set_password('Password123!')
            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.email == 'test@example.com'
            assert user.first_name == 'Test'
            assert user.last_name == 'User'

    def test_password_hashing(self, app):
        """Test password is hashed correctly."""
        with app.app_context():
            user = User(email='hash@test.com', first_name='Hash', last_name='Test')
            user.set_password('MySecretPassword!')

            assert user.password_hash is not None
            assert user.password_hash != 'MySecretPassword!'
            assert user.check_password('MySecretPassword!') is True
            assert user.check_password('WrongPassword') is False

    def test_user_full_name(self, app):
        """Test full_name property."""
        with app.app_context():
            user = User(
                email='name@test.com',
                first_name='John',
                last_name='Doe'
            )
            assert user.full_name == 'John Doe'

    def test_user_roles(self, app, manager_role, manager_user):
        """Test user role assignment."""
        with app.app_context():
            user = db.session.get(User, manager_user.id)
            assert len(user.roles) == 1
            assert user.roles[0].name == 'MANAGER'

    def test_user_has_role(self, app, manager_user):
        """Test has_role method."""
        with app.app_context():
            user = db.session.get(User, manager_user.id)
            assert user.has_role('MANAGER') is True
            assert user.has_role('MUSICIAN') is False

    def test_user_has_permission(self, app, manager_user):
        """Test has_permission method."""
        with app.app_context():
            user = db.session.get(User, manager_user.id)
            assert user.has_permission('manage_band') is True
            assert user.has_permission('nonexistent_permission') is False


# =============================================================================
# Role Model Tests
# =============================================================================

class TestRoleModel:
    """Tests for Role model."""

    def test_create_role(self, app):
        """Test role creation."""
        with app.app_context():
            role = Role(
                name='TEST_ROLE',
                description='A test role',
                permissions=['permission1', 'permission2']
            )
            db.session.add(role)
            db.session.commit()

            assert role.id is not None
            assert role.name == 'TEST_ROLE'
            assert 'permission1' in role.permissions

    def test_role_permissions_json(self, app):
        """Test permissions are stored as JSON."""
        with app.app_context():
            role = Role(
                name='JSON_TEST',
                description='Test JSON storage',
                permissions=['view', 'edit', 'delete']
            )
            db.session.add(role)
            db.session.commit()

            retrieved = db.session.get(Role, role.id)
            assert retrieved.permissions == ['view', 'edit', 'delete']


# =============================================================================
# Band Model Tests
# =============================================================================

class TestBandModel:
    """Tests for Band model."""

    def test_create_band(self, app, manager_user):
        """Test band creation."""
        with app.app_context():
            manager = db.session.get(User, manager_user.id)
            band = Band(
                name='New Band',
                genre='Jazz',
                bio='A new jazz band',
                manager=manager
            )
            db.session.add(band)
            db.session.commit()

            assert band.id is not None
            assert band.name == 'New Band'
            assert band.manager_id == manager.id

    def test_band_members(self, app, sample_band, musician_user):
        """Test band membership."""
        with app.app_context():
            band = db.session.get(Band, sample_band.id)
            musician = db.session.get(User, musician_user.id)

            membership = BandMembership(
                band=band,
                user=musician,
                role_in_band='Lead Guitar',
                is_active=True
            )
            db.session.add(membership)
            db.session.commit()

            assert len(band.memberships) == 1
            assert band.memberships[0].user_id == musician.id
            assert band.memberships[0].role_in_band == 'Lead Guitar'

    def test_band_social_links(self, app, manager_user):
        """Test band social links JSON field."""
        with app.app_context():
            manager = db.session.get(User, manager_user.id)
            band = Band(
                name='Social Band',
                genre='Pop',
                manager=manager,
                social_links={
                    'instagram': '@socialband',
                    'twitter': '@socialband',
                    'facebook': 'socialband'
                }
            )
            db.session.add(band)
            db.session.commit()

            retrieved = db.session.get(Band, band.id)
            assert retrieved.social_links['instagram'] == '@socialband'


# =============================================================================
# Tour Model Tests
# =============================================================================

class TestTourModel:
    """Tests for Tour model."""

    def test_create_tour(self, app, sample_band):
        """Test tour creation."""
        with app.app_context():
            band = db.session.get(Band, sample_band.id)
            tour = Tour(
                name='World Tour',
                description='A world tour',
                start_date=date(2025, 6, 1),
                end_date=date(2025, 8, 31),
                status=TourStatus.PLANNING,
                band=band
            )
            db.session.add(tour)
            db.session.commit()

            assert tour.id is not None
            assert tour.name == 'World Tour'
            assert tour.status == TourStatus.PLANNING

    def test_tour_status_enum(self, app, sample_tour):
        """Test tour status enum values."""
        with app.app_context():
            tour = db.session.get(Tour, sample_tour.id)
            tour.status = TourStatus.ACTIVE
            db.session.commit()

            retrieved = db.session.get(Tour, tour.id)
            assert retrieved.status == TourStatus.ACTIVE

    def test_tour_stops_relationship(self, app, sample_tour, sample_tour_stop):
        """Test tour to stops relationship."""
        with app.app_context():
            tour = db.session.get(Tour, sample_tour.id)
            assert len(tour.stops) == 1
            assert tour.stops[0].id == sample_tour_stop.id


# =============================================================================
# Venue Model Tests
# =============================================================================

class TestVenueModel:
    """Tests for Venue model."""

    def test_create_venue(self, app):
        """Test venue creation."""
        with app.app_context():
            venue = Venue(
                name='Grand Theater',
                address='456 Main Street',
                city='Paris',
                country='France',
                capacity=2000,
                venue_type='Theater'
            )
            db.session.add(venue)
            db.session.commit()

            assert venue.id is not None
            assert venue.name == 'Grand Theater'
            assert venue.capacity == 2000

    def test_venue_optional_fields(self, app):
        """Test venue with optional fields."""
        with app.app_context():
            venue = Venue(
                name='Small Club',
                city='Lyon',
                country='France'
            )
            db.session.add(venue)
            db.session.commit()

            assert venue.id is not None
            assert venue.address is None
            assert venue.capacity is None


# =============================================================================
# TourStop Model Tests
# =============================================================================

class TestTourStopModel:
    """Tests for TourStop model."""

    def test_create_tour_stop(self, app, sample_tour, sample_venue):
        """Test tour stop creation."""
        with app.app_context():
            tour = db.session.get(Tour, sample_tour.id)
            venue = db.session.get(Venue, sample_venue.id)

            stop = TourStop(
                tour=tour,
                venue=venue,
                date=date(2025, 7, 15),
                doors_time=time(18, 0),
                set_time=time(20, 0),
                status=TourStopStatus.DRAFT
            )
            db.session.add(stop)
            db.session.commit()

            assert stop.id is not None
            assert stop.date == date(2025, 7, 15)
            assert stop.status == TourStopStatus.DRAFT

    def test_tour_stop_status_transitions(self, app, sample_tour_stop):
        """Test tour stop status workflow (Pattern Dolibarr)."""
        with app.app_context():
            stop = db.session.get(TourStop, sample_tour_stop.id)

            # Test workflow: DRAFT → CONFIRMED → PERFORMED → SETTLED
            stop.status = TourStopStatus.DRAFT
            db.session.commit()

            # DRAFT → CONFIRMED
            assert stop.confirm() == True
            db.session.commit()
            assert stop.status == TourStopStatus.CONFIRMED
            assert stop.confirmed_at is not None

            # CONFIRMED → PERFORMED
            assert stop.perform() == True
            db.session.commit()
            assert stop.status == TourStopStatus.PERFORMED
            assert stop.performed_at is not None

            # PERFORMED → SETTLED
            assert stop.settle() == True
            db.session.commit()
            retrieved = db.session.get(TourStop, stop.id)
            assert retrieved.status == TourStopStatus.SETTLED
            assert retrieved.settled_at is not None


# =============================================================================
# GuestlistEntry Model Tests
# =============================================================================

class TestGuestlistEntryModel:
    """Tests for GuestlistEntry model."""

    def test_create_guestlist_entry(self, app, sample_tour_stop, manager_user):
        """Test guestlist entry creation."""
        with app.app_context():
            stop = db.session.get(TourStop, sample_tour_stop.id)
            user = db.session.get(User, manager_user.id)

            entry = GuestlistEntry(
                guest_name='Jane Smith',
                guest_email='jane@example.com',
                entry_type=EntryType.GUEST,
                plus_ones=2,
                tour_stop=stop,
                requested_by=user
            )
            db.session.add(entry)
            db.session.commit()

            assert entry.id is not None
            assert entry.guest_name == 'Jane Smith'
            assert entry.plus_ones == 2
            assert entry.status == GuestlistStatus.PENDING

    def test_guestlist_approval_workflow(self, app, sample_guestlist_entry, manager_user):
        """Test guestlist approval workflow."""
        with app.app_context():
            entry = db.session.get(GuestlistEntry, sample_guestlist_entry.id)
            approver = db.session.get(User, manager_user.id)

            # Approve the entry
            entry.status = GuestlistStatus.APPROVED
            entry.approved_by = approver
            db.session.commit()

            retrieved = db.session.get(GuestlistEntry, entry.id)
            assert retrieved.status == GuestlistStatus.APPROVED
            assert retrieved.approved_by_id == approver.id

    def test_guestlist_check_in(self, app, sample_guestlist_entry):
        """Test guestlist check-in."""
        with app.app_context():
            entry = db.session.get(GuestlistEntry, sample_guestlist_entry.id)

            # First approve
            entry.status = GuestlistStatus.APPROVED
            db.session.commit()

            # Then check in
            entry.status = GuestlistStatus.CHECKED_IN
            db.session.commit()

            retrieved = db.session.get(GuestlistEntry, entry.id)
            assert retrieved.status == GuestlistStatus.CHECKED_IN

    def test_entry_type_enum(self, app, sample_tour_stop, manager_user):
        """Test entry type enum values."""
        with app.app_context():
            stop = db.session.get(TourStop, sample_tour_stop.id)
            user = db.session.get(User, manager_user.id)

            for entry_type in [EntryType.VIP, EntryType.GUEST, EntryType.INDUSTRY, EntryType.PRESS]:
                entry = GuestlistEntry(
                    guest_name=f'Guest {entry_type.value}',
                    guest_email=f'guest.{entry_type.value}@test.com',
                    entry_type=entry_type,
                    tour_stop=stop,
                    requested_by=user
                )
                db.session.add(entry)

            db.session.commit()

            # Verify all types were saved
            entries = GuestlistEntry.query.filter_by(tour_stop_id=stop.id).all()
            # +1 for the sample_guestlist_entry if it exists from fixture
            assert len(entries) >= 4


# =============================================================================
# LogisticsInfo Model Tests
# =============================================================================

class TestLogisticsInfoModel:
    """Tests for LogisticsInfo model."""

    def test_create_logistics_info(self, app, sample_tour_stop):
        """Test logistics info creation."""
        with app.app_context():
            stop = db.session.get(TourStop, sample_tour_stop.id)

            logistics = LogisticsInfo(
                tour_stop=stop,
                logistics_type=LogisticsType.HOTEL,
                provider='Grand Hotel',
                confirmation_number='HOTEL123',
                cost=150.00,
                details={
                    'room_type': 'Double',
                    'check_in': '14:00',
                    'check_out': '11:00'
                }
            )
            db.session.add(logistics)
            db.session.commit()

            assert logistics.id is not None
            assert logistics.logistics_type == LogisticsType.HOTEL
            assert logistics.details['room_type'] == 'Double'

    def test_logistics_types(self, app, sample_tour_stop):
        """Test all logistics types."""
        with app.app_context():
            stop = db.session.get(TourStop, sample_tour_stop.id)

            types_to_test = [
                LogisticsType.FLIGHT,
                LogisticsType.HOTEL,
                LogisticsType.TRAIN,
                LogisticsType.RENTAL_CAR
            ]

            for ltype in types_to_test:
                logistics = LogisticsInfo(
                    tour_stop=stop,
                    logistics_type=ltype,
                    provider=f'Provider {ltype.value}'
                )
                db.session.add(logistics)

            db.session.commit()

            all_logistics = LogisticsInfo.query.filter_by(tour_stop_id=stop.id).all()
            assert len(all_logistics) == len(types_to_test)
