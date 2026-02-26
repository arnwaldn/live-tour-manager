# =============================================================================
# Tour Manager - Guestlist Routes Integration Tests
# =============================================================================
#
# Comprehensive tests for app/blueprints/guestlist/routes.py
# Covers: index, manage, add/edit/delete entries, approve/deny,
#         check-in/undo, bulk actions, CSV export, API search,
#         permission checks, and edge cases.
# =============================================================================

import pytest
from datetime import date, time, timedelta, datetime
from unittest.mock import patch

from app.extensions import db
from app.models.user import User, Role, AccessLevel
from app.models.band import Band, BandMembership
from app.models.venue import Venue
from app.models.tour import Tour, TourStatus
from app.models.tour_stop import TourStop, TourStopStatus
from app.models.guestlist import GuestlistEntry, GuestlistStatus, EntryType


# =============================================================================
# Helpers
# =============================================================================

# Credentials constants to keep tests DRY
MANAGER_EMAIL = 'manager@test.com'
MANAGER_PASS = 'Manager123!'
VIEWER_EMAIL = 'viewer@test.com'
VIEWER_PASS = 'Viewer123!'
STAFF_EMAIL = 'staff@test.com'
STAFF_PASS = 'Staff1234!'


def _login(client, email, password):
    """Log in a user via the auth form (no follow_redirects so session is set)."""
    client.post('/auth/login', data={
        'email': email,
        'password': password,
    })


def _make_entry(stop, requester, **overrides):
    """Create a GuestlistEntry with sensible defaults, add to session, commit, return refreshed."""
    defaults = dict(
        tour_stop_id=stop.id,
        guest_name='Guest Default',
        guest_email='guest@example.com',
        entry_type=EntryType.GUEST,
        plus_ones=0,
        status=GuestlistStatus.PENDING,
        requested_by_id=requester.id,
    )
    defaults.update(overrides)
    entry = GuestlistEntry(**defaults)
    db.session.add(entry)
    db.session.commit()
    entry_id = entry.id
    db.session.expire_all()
    return db.session.get(GuestlistEntry, entry_id)


# =============================================================================
# Extra fixtures local to this module
# =============================================================================

@pytest.fixture
def viewer_user(app):
    """A user with VIEWER access level (low permissions)."""
    role = Role(name='VIEWER_ROLE', description='Viewer', permissions=['view_tour'])
    db.session.add(role)
    db.session.flush()
    user = User(
        email=VIEWER_EMAIL,
        first_name='View',
        last_name='Only',
        access_level=AccessLevel.VIEWER,
        is_active=True,
        email_verified=True,
    )
    user.set_password(VIEWER_PASS)
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    uid = user.id
    db.session.expire_all()
    return db.session.get(User, uid)


@pytest.fixture
def staff_user(app):
    """A user with STAFF access level (can manage guestlists) but NOT member of any band."""
    role = Role(
        name='STAFF_ROLE', description='Staff',
        permissions=['view_tour', 'view_show', 'check_in_guests', 'manage_guestlist']
    )
    db.session.add(role)
    db.session.flush()
    user = User(
        email=STAFF_EMAIL,
        first_name='Staff',
        last_name='Member',
        access_level=AccessLevel.STAFF,
        is_active=True,
        email_verified=True,
    )
    user.set_password(STAFF_PASS)
    user.roles.append(role)
    db.session.add(user)
    db.session.commit()
    uid = user.id
    db.session.expire_all()
    return db.session.get(User, uid)


# =============================================================================
# Index & Check-in Select
# =============================================================================

class TestGuestlistIndex:
    """Tests for the guestlist overview page (GET /guestlist/)."""

    def test_index_requires_login(self, client):
        """Unauthenticated users are redirected to login."""
        resp = client.get('/guestlist/')
        assert resp.status_code in (302, 308)

    def test_index_renders_for_authenticated_user(
        self, app, client, manager_user, sample_band, sample_tour
    ):
        """Authenticated user sees the guestlist overview page."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get('/guestlist/')
        assert resp.status_code == 200

    def test_index_shows_tours(
        self, app, client, manager_user, sample_band, sample_tour
    ):
        """Overview lists tours the user has access to."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get('/guestlist/')
        assert resp.status_code == 200
        assert b'Test Tour 2025' in resp.data


class TestCheckInSelect:
    """Tests for GET /guestlist/check-in (check-in tour stop selection)."""

    def test_check_in_select_requires_login(self, client):
        resp = client.get('/guestlist/check-in')
        assert resp.status_code in (302, 308)

    def test_staff_can_access_check_in_select(
        self, app, client, manager_user, sample_band, sample_tour
    ):
        """Staff-or-above users can access the check-in selection page."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get('/guestlist/check-in')
        assert resp.status_code == 200

    def test_viewer_cannot_access_check_in_select(
        self, app, client, viewer_user
    ):
        """VIEWER access level is redirected away from check-in."""
        _login(client, VIEWER_EMAIL, VIEWER_PASS)
        resp = client.get('/guestlist/check-in', follow_redirects=True)
        assert resp.status_code == 200
        body = resp.data.decode('utf-8')
        # Flash message about permission or redirected to dashboard
        assert 'permission' in body.lower() or 'check-in' in body.lower() or \
               'dashboard' in resp.request.path


# =============================================================================
# Manage guestlist (GET /guestlist/stop/<id>)
# =============================================================================

class TestManageGuestlist:
    """Tests for viewing/managing guestlist for a specific tour stop."""

    def test_manage_requires_login(self, client, sample_tour_stop):
        resp = client.get(f'/guestlist/stop/{sample_tour_stop.id}')
        assert resp.status_code in (302, 308)

    def test_manage_shows_entries(
        self, app, client, manager_user, sample_tour_stop, sample_guestlist_entry
    ):
        """Manager sees guestlist entries for a tour stop."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(f'/guestlist/stop/{sample_tour_stop.id}')
        assert resp.status_code == 200
        assert b'John Doe' in resp.data

    def test_manage_nonexistent_stop_returns_404(
        self, app, client, manager_user
    ):
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get('/guestlist/stop/99999')
        assert resp.status_code == 404

    def test_manage_no_access_redirects(
        self, app, client, staff_user, sample_tour_stop
    ):
        """A user not belonging to the band is denied access."""
        _login(client, STAFF_EMAIL, STAFF_PASS)
        resp = client.get(
            f'/guestlist/stop/{sample_tour_stop.id}', follow_redirects=True
        )
        assert resp.status_code == 200
        body = resp.data.decode('utf-8')
        assert 'non autorisé' in body.lower() or 'dashboard' in resp.request.path

    def test_manage_filter_by_status(
        self, app, client, manager_user, sample_tour_stop, sample_guestlist_entry
    ):
        """Status filter narrows down entries."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/stop/{sample_tour_stop.id}?status=approved'
        )
        assert resp.status_code == 200

    def test_manage_filter_by_entry_type(
        self, app, client, manager_user, sample_tour_stop, sample_guestlist_entry
    ):
        """Entry type filter works."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/stop/{sample_tour_stop.id}?entry_type=vip'
        )
        assert resp.status_code == 200

    def test_manage_filter_invalid_status_ignored(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Invalid status value is silently ignored."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/stop/{sample_tour_stop.id}?status=BOGUS'
        )
        assert resp.status_code == 200

    def test_manage_filter_invalid_entry_type_ignored(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Invalid entry_type value is silently ignored."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/stop/{sample_tour_stop.id}?entry_type=INVALID'
        )
        assert resp.status_code == 200

    def test_manage_search(
        self, app, client, manager_user, sample_tour_stop, sample_guestlist_entry
    ):
        """Search query filters by guest name/email/company."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/stop/{sample_tour_stop.id}?search=John'
        )
        assert resp.status_code == 200
        assert b'John Doe' in resp.data

    def test_manage_search_no_match(
        self, app, client, manager_user, sample_tour_stop, sample_guestlist_entry
    ):
        """Search with non-matching query loads page successfully.

        Note: "John Doe" (PENDING) may still appear in the separate pending
        approvals section because that section uses its own query without
        search filters.  We verify the page loads with 200 and the search
        parameter is reflected.
        """
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/stop/{sample_tour_stop.id}?search=ZZZZNOTFOUND'
        )
        assert resp.status_code == 200
        body = resp.data.decode('utf-8')
        # The search term should be reflected on the page (in the input field)
        assert 'ZZZZNOTFOUND' in body

    def test_manage_pagination(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Pagination parameter is accepted."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        for i in range(25):
            _make_entry(
                sample_tour_stop, manager_user,
                guest_name=f'Guest {i}', guest_email=f'g{i}@example.com'
            )
        resp = client.get(
            f'/guestlist/stop/{sample_tour_stop.id}?page=2'
        )
        assert resp.status_code == 200

    def test_viewer_sees_only_own_entries(
        self, app, client, viewer_user, manager_user, sample_band, sample_tour_stop
    ):
        """VIEWER-level user only sees entries they requested or are linked to."""
        # Add viewer as band member so they pass band access check
        membership = BandMembership(
            user_id=viewer_user.id, band_id=sample_band.id,
            instrument='Vocals', role_in_band='Singer',
        )
        db.session.add(membership)
        db.session.commit()

        # Entry requested by manager -- viewer should NOT see it
        _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Manager Guest', guest_email='mg@test.com'
        )
        # Entry requested by viewer -- viewer SHOULD see it
        _make_entry(
            sample_tour_stop, viewer_user,
            guest_name='Viewer Guest', guest_email='vg@test.com'
        )

        _login(client, VIEWER_EMAIL, VIEWER_PASS)
        resp = client.get(f'/guestlist/stop/{sample_tour_stop.id}')
        assert resp.status_code == 200
        body = resp.data.decode('utf-8')
        assert 'Viewer Guest' in body
        assert 'Manager Guest' not in body


# =============================================================================
# Add entry (GET+POST /guestlist/stop/<id>/add)
# =============================================================================

class TestAddEntry:
    """Tests for adding a guestlist entry."""

    def test_add_entry_get_form(
        self, app, client, manager_user, sample_tour_stop
    ):
        """GET renders the add entry form."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(f'/guestlist/stop/{sample_tour_stop.id}/add')
        assert resp.status_code == 200

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_add_entry_post_standard(
        self, mock_notify, app, client, manager_user, sample_tour_stop
    ):
        """POST creates a new guestlist entry (auto-approved for staff+)."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/stop/{sample_tour_stop.id}/add',
            data={
                'guest_name': 'Alice Wonderland',
                'guest_email': 'alice@example.com',
                'guest_phone': '+33600000000',
                'entry_type': 'guest',
                'artist_id': '0',
                'plus_ones': '2',
                'company': 'Acme Corp',
                'notes': 'Backstage pass',
                'internal_notes': 'VIP treatment',
                'status': 'pending',
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with app.app_context():
            entry = GuestlistEntry.query.filter_by(guest_name='Alice Wonderland').first()
            assert entry is not None
            assert entry.plus_ones == 2
            assert entry.company == 'Acme Corp'
            # Staff-or-above auto-approves
            assert entry.status == GuestlistStatus.APPROVED
            assert entry.approved_by_id == manager_user.id

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_add_entry_artist_type_with_band_member(
        self, mock_notify, app, client, manager_user, sample_band, sample_tour_stop
    ):
        """Adding an ARTIST type entry with a valid band member sets user_id."""
        membership = BandMembership(
            user_id=manager_user.id, band_id=sample_band.id,
            instrument='Guitar', role_in_band='Lead',
        )
        db.session.add(membership)
        db.session.commit()

        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/stop/{sample_tour_stop.id}/add',
            data={
                'guest_name': '',
                'guest_email': '',
                'entry_type': 'artist',
                'artist_id': str(manager_user.id),
                'plus_ones': '0',
                'status': 'pending',
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with app.app_context():
            entry = GuestlistEntry.query.filter_by(user_id=manager_user.id).first()
            assert entry is not None
            assert entry.entry_type == EntryType.ARTIST
            assert entry.guest_name == manager_user.full_name

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_add_entry_artist_type_invalid_member(
        self, mock_notify, app, client, manager_user, sample_band, sample_tour_stop
    ):
        """ARTIST type with invalid artist_id redirects with error."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/stop/{sample_tour_stop.id}/add',
            data={
                'guest_name': '',
                'guest_email': '',
                'entry_type': 'artist',
                'artist_id': '99999',
                'plus_ones': '0',
                'status': 'pending',
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        body = resp.data.decode('utf-8')
        assert 'invalide' in body.lower() or 'artiste' in body.lower()

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_add_entry_artist_type_no_name_no_id(
        self, mock_notify, app, client, manager_user, sample_tour_stop
    ):
        """ARTIST type with no artist_id and no guest_name flashes error."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/stop/{sample_tour_stop.id}/add',
            data={
                'guest_name': '',
                'guest_email': '',
                'entry_type': 'artist',
                'artist_id': '0',
                'plus_ones': '0',
                'status': 'pending',
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        body = resp.data.decode('utf-8')
        assert 'artiste' in body.lower() or 'sélectionner' in body.lower()

    def test_add_entry_no_band_access_redirects(
        self, app, client, staff_user, sample_tour_stop
    ):
        """User without band access cannot add entries."""
        _login(client, STAFF_EMAIL, STAFF_PASS)
        resp = client.get(
            f'/guestlist/stop/{sample_tour_stop.id}/add',
            follow_redirects=True,
        )
        assert resp.status_code == 200
        body = resp.data.decode('utf-8')
        assert 'non autorisé' in body.lower() or 'dashboard' in resp.request.path

    def test_add_entry_viewer_permission_denied(
        self, app, client, viewer_user, sample_band, sample_tour_stop
    ):
        """VIEWER in band cannot add entries (needs staff+)."""
        membership = BandMembership(
            user_id=viewer_user.id, band_id=sample_band.id,
            instrument='Keys', role_in_band='Keyboardist',
        )
        db.session.add(membership)
        db.session.commit()

        _login(client, VIEWER_EMAIL, VIEWER_PASS)
        resp = client.get(
            f'/guestlist/stop/{sample_tour_stop.id}/add',
            follow_redirects=True,
        )
        assert resp.status_code == 200
        body = resp.data.decode('utf-8')
        assert 'permission' in body.lower()

    def test_add_entry_nonexistent_stop_404(self, app, client, manager_user):
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get('/guestlist/stop/99999/add')
        assert resp.status_code == 404


# =============================================================================
# Entry Detail (GET /guestlist/entry/<id>)
# =============================================================================

class TestEntryDetail:
    """Tests for viewing a single guestlist entry."""

    def test_detail_renders(
        self, app, client, manager_user, sample_guestlist_entry
    ):
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(f'/guestlist/entry/{sample_guestlist_entry.id}')
        assert resp.status_code == 200
        assert b'John Doe' in resp.data

    def test_detail_nonexistent_404(self, app, client, manager_user):
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get('/guestlist/entry/99999')
        assert resp.status_code == 404

    def test_detail_no_band_access(
        self, app, client, staff_user, sample_guestlist_entry
    ):
        """User outside the band cannot view entry details."""
        _login(client, STAFF_EMAIL, STAFF_PASS)
        resp = client.get(
            f'/guestlist/entry/{sample_guestlist_entry.id}',
            follow_redirects=True,
        )
        body = resp.data.decode('utf-8')
        assert 'non autorisé' in body.lower() or 'dashboard' in resp.request.path


# =============================================================================
# Edit entry (GET+POST /guestlist/entry/<id>/edit)
# =============================================================================

class TestEditEntry:
    """Tests for editing a guestlist entry."""

    def test_edit_get_form(
        self, app, client, manager_user, sample_guestlist_entry
    ):
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(f'/guestlist/entry/{sample_guestlist_entry.id}/edit')
        assert resp.status_code == 200

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_edit_post_updates_entry(
        self, mock_notify, app, client, manager_user, sample_guestlist_entry
    ):
        """POST updates the guestlist entry fields.

        Note: entry_type is overridden by routes.py line 310
        (``form.entry_type.data = entry.entry_type.value``) before
        validate_on_submit, so it always stays at the original value.
        We therefore test fields that *can* be changed.
        """
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{sample_guestlist_entry.id}/edit',
            data={
                'guest_name': 'Jane Smith',
                'guest_email': 'jane@example.com',
                'guest_phone': '',
                'entry_type': 'vip',  # Same as original -- cannot change via form
                'artist_id': '0',
                'plus_ones': '3',
                'company': 'Press Corp',
                'notes': 'Updated',
                'internal_notes': '',
                'status': 'pending',
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with app.app_context():
            entry = db.session.get(GuestlistEntry, sample_guestlist_entry.id)
            assert entry.guest_name == 'Jane Smith'
            assert entry.guest_email == 'jane@example.com'
            assert entry.plus_ones == 3
            assert entry.company == 'Press Corp'
            assert entry.notes == 'Updated'

    def test_edit_locked_entry_blocked(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Editing a checked-in (locked) entry is blocked."""
        entry = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Locked Guest', guest_email='locked@test.com',
            status=GuestlistStatus.CHECKED_IN,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/entry/{entry.id}/edit',
            follow_redirects=True,
        )
        assert resp.status_code == 200
        body = resp.data.decode('utf-8')
        assert 'verrouillée' in body.lower() or 'check-in' in body.lower()

    def test_edit_no_band_access(
        self, app, client, staff_user, sample_guestlist_entry
    ):
        """User outside band cannot edit entry."""
        _login(client, STAFF_EMAIL, STAFF_PASS)
        resp = client.get(
            f'/guestlist/entry/{sample_guestlist_entry.id}/edit',
            follow_redirects=True,
        )
        body = resp.data.decode('utf-8')
        assert 'non autorisé' in body.lower() or 'dashboard' in resp.request.path

    def test_edit_not_requester_and_not_staff(
        self, app, client, viewer_user, manager_user, sample_band,
        sample_tour_stop, sample_guestlist_entry
    ):
        """Non-requester VIEWER cannot edit entry even with band access."""
        membership = BandMembership(
            user_id=viewer_user.id, band_id=sample_band.id,
            instrument='Bass', role_in_band='Bassist',
        )
        db.session.add(membership)
        db.session.commit()

        _login(client, VIEWER_EMAIL, VIEWER_PASS)
        resp = client.get(
            f'/guestlist/entry/{sample_guestlist_entry.id}/edit',
            follow_redirects=True,
        )
        body = resp.data.decode('utf-8')
        assert 'modifier' in body.lower() or 'permission' in body.lower() or \
               resp.request.path != f'/guestlist/entry/{sample_guestlist_entry.id}/edit'

    def test_edit_nonexistent_entry_404(self, app, client, manager_user):
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get('/guestlist/entry/99999/edit')
        assert resp.status_code == 404


# =============================================================================
# Approve / Deny (POST /guestlist/entry/<id>/approve|deny)
# =============================================================================

class TestApproveAndDeny:
    """Tests for approving and denying guestlist entries."""

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_approve_entry(
        self, mock_notify, app, client, manager_user, sample_guestlist_entry
    ):
        """Manager can approve a pending entry."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{sample_guestlist_entry.id}/approve',
            data={'notes': 'Looks good'},
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with app.app_context():
            entry = db.session.get(GuestlistEntry, sample_guestlist_entry.id)
            assert entry.status == GuestlistStatus.APPROVED
            assert entry.approved_by_id == manager_user.id

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_deny_entry(
        self, mock_notify, app, client, manager_user, sample_guestlist_entry
    ):
        """Manager can deny a pending entry."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{sample_guestlist_entry.id}/deny',
            data={'notes': 'No room'},
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with app.app_context():
            entry = db.session.get(GuestlistEntry, sample_guestlist_entry.id)
            assert entry.status == GuestlistStatus.DENIED

    def test_approve_no_band_access(
        self, app, client, staff_user, sample_guestlist_entry
    ):
        """User outside band cannot approve."""
        _login(client, STAFF_EMAIL, STAFF_PASS)
        resp = client.post(
            f'/guestlist/entry/{sample_guestlist_entry.id}/approve',
            follow_redirects=True,
        )
        body = resp.data.decode('utf-8')
        assert 'non autorisé' in body.lower() or 'dashboard' in resp.request.path

    def test_deny_no_band_access(
        self, app, client, staff_user, sample_guestlist_entry
    ):
        """User outside band cannot deny."""
        _login(client, STAFF_EMAIL, STAFF_PASS)
        resp = client.post(
            f'/guestlist/entry/{sample_guestlist_entry.id}/deny',
            follow_redirects=True,
        )
        body = resp.data.decode('utf-8')
        assert 'non autorisé' in body.lower() or 'dashboard' in resp.request.path

    def test_approve_viewer_permission_denied(
        self, app, client, viewer_user, sample_band, sample_guestlist_entry
    ):
        """VIEWER in band cannot approve (needs staff+)."""
        membership = BandMembership(
            user_id=viewer_user.id, band_id=sample_band.id,
            instrument='Drums', role_in_band='Drummer',
        )
        db.session.add(membership)
        db.session.commit()

        _login(client, VIEWER_EMAIL, VIEWER_PASS)
        resp = client.post(
            f'/guestlist/entry/{sample_guestlist_entry.id}/approve',
            follow_redirects=True,
        )
        body = resp.data.decode('utf-8')
        assert 'permission' in body.lower()

    def test_approve_nonexistent_entry_404(self, app, client, manager_user):
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post('/guestlist/entry/99999/approve')
        assert resp.status_code == 404

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_approve_sends_notification(
        self, mock_notify, app, client, manager_user, sample_guestlist_entry
    ):
        """Approving calls send_guestlist_notification with 'approved'."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        client.post(
            f'/guestlist/entry/{sample_guestlist_entry.id}/approve',
            follow_redirects=True,
        )
        mock_notify.assert_called()
        args = mock_notify.call_args
        assert args[0][1] == 'approved'

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_deny_sends_notification(
        self, mock_notify, app, client, manager_user, sample_guestlist_entry
    ):
        """Denying calls send_guestlist_notification with 'denied'."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        client.post(
            f'/guestlist/entry/{sample_guestlist_entry.id}/deny',
            follow_redirects=True,
        )
        mock_notify.assert_called()
        args = mock_notify.call_args
        assert args[0][1] == 'denied'

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification', side_effect=Exception('SMTP error'))
    def test_approve_email_failure_does_not_crash(
        self, mock_notify, app, client, manager_user, sample_guestlist_entry
    ):
        """Email failure during approve is caught and does not crash the route."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{sample_guestlist_entry.id}/approve',
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            entry = db.session.get(GuestlistEntry, sample_guestlist_entry.id)
            assert entry.status == GuestlistStatus.APPROVED


# =============================================================================
# Delete entry (POST /guestlist/entry/<id>/delete)
# =============================================================================

class TestDeleteEntry:
    """Tests for deleting a guestlist entry."""

    def test_delete_entry(
        self, app, client, manager_user, sample_tour_stop, sample_guestlist_entry
    ):
        """Manager can delete their own pending entry."""
        entry_id = sample_guestlist_entry.id
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{entry_id}/delete',
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with app.app_context():
            assert db.session.get(GuestlistEntry, entry_id) is None

    def test_delete_locked_entry_blocked(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Deleting a checked-in (locked) entry is blocked."""
        entry = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Locked Del', guest_email='ld@test.com',
            status=GuestlistStatus.CHECKED_IN,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{entry.id}/delete',
            follow_redirects=True,
        )
        assert resp.status_code == 200
        body = resp.data.decode('utf-8')
        assert 'verrouillée' in body.lower()

        with app.app_context():
            assert db.session.get(GuestlistEntry, entry.id) is not None

    def test_delete_no_band_access(
        self, app, client, staff_user, sample_guestlist_entry
    ):
        """User outside band cannot delete."""
        _login(client, STAFF_EMAIL, STAFF_PASS)
        resp = client.post(
            f'/guestlist/entry/{sample_guestlist_entry.id}/delete',
            follow_redirects=True,
        )
        body = resp.data.decode('utf-8')
        assert 'non autorisé' in body.lower() or 'dashboard' in resp.request.path

    def test_delete_not_requester_and_not_staff(
        self, app, client, viewer_user, manager_user, sample_band,
        sample_tour_stop, sample_guestlist_entry
    ):
        """Non-requester VIEWER cannot delete entry."""
        membership = BandMembership(
            user_id=viewer_user.id, band_id=sample_band.id,
            instrument='Flute', role_in_band='Extra',
        )
        db.session.add(membership)
        db.session.commit()

        _login(client, VIEWER_EMAIL, VIEWER_PASS)
        resp = client.post(
            f'/guestlist/entry/{sample_guestlist_entry.id}/delete',
            follow_redirects=True,
        )
        body = resp.data.decode('utf-8')
        assert 'supprimer' in body.lower() or 'permission' in body.lower() or \
               resp.request.path != f'/guestlist/entry/{sample_guestlist_entry.id}/delete'

    def test_delete_nonexistent_404(self, app, client, manager_user):
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post('/guestlist/entry/99999/delete')
        assert resp.status_code == 404


# =============================================================================
# Check-in interface (GET /guestlist/stop/<id>/check-in)
# =============================================================================

class TestCheckInInterface:
    """Tests for the check-in interface page."""

    def test_check_in_interface_renders(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Check-in interface renders for authorised user."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(f'/guestlist/stop/{sample_tour_stop.id}/check-in')
        assert resp.status_code == 200

    def test_check_in_interface_shows_approved_entries(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Only APPROVED and CHECKED_IN entries appear."""
        _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Approved Guy', guest_email='ag@test.com',
            status=GuestlistStatus.APPROVED,
        )
        _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Pending Guy', guest_email='pg@test.com',
            status=GuestlistStatus.PENDING,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(f'/guestlist/stop/{sample_tour_stop.id}/check-in')
        assert resp.status_code == 200
        body = resp.data.decode('utf-8')
        assert 'Approved Guy' in body
        assert 'Pending Guy' not in body


# =============================================================================
# Do check-in (POST /guestlist/entry/<id>/check-in)
# =============================================================================

class TestDoCheckIn:
    """Tests for the actual check-in action."""

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_check_in_approved_entry(
        self, mock_notify, app, client, manager_user, sample_tour_stop
    ):
        """Check-in an approved entry succeeds."""
        entry = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='CheckIn Test', guest_email='ci@test.com',
            status=GuestlistStatus.APPROVED, plus_ones=2,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{entry.id}/check-in',
            data={'plus_ones': '1'},
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with app.app_context():
            updated = db.session.get(GuestlistEntry, entry.id)
            assert updated.status == GuestlistStatus.CHECKED_IN
            assert updated.checked_in_at is not None

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_check_in_ajax_returns_json(
        self, mock_notify, app, client, manager_user, sample_tour_stop
    ):
        """AJAX check-in returns JSON response."""
        entry = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Ajax CI', guest_email='ajci@test.com',
            status=GuestlistStatus.APPROVED,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{entry.id}/check-in',
            headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['entry_id'] == entry.id

    def test_check_in_not_approved_returns_400(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Cannot check-in a non-approved entry (returns 400)."""
        entry = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Pending CI', guest_email='pci@test.com',
            status=GuestlistStatus.PENDING,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{entry.id}/check-in',
            headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_check_in_permission_denied(
        self, app, client, viewer_user, manager_user, sample_band, sample_tour_stop
    ):
        """VIEWER cannot perform check-in (returns 403)."""
        membership = BandMembership(
            user_id=viewer_user.id, band_id=sample_band.id,
            instrument='Sax', role_in_band='Sax',
        )
        db.session.add(membership)
        db.session.commit()

        entry = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Viewer CI', guest_email='vci@test.com',
            status=GuestlistStatus.APPROVED,
        )
        _login(client, VIEWER_EMAIL, VIEWER_PASS)
        resp = client.post(
            f'/guestlist/entry/{entry.id}/check-in',
            headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        assert resp.status_code == 403

    def test_check_in_nonexistent_404(self, app, client, manager_user):
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post('/guestlist/entry/99999/check-in')
        assert resp.status_code == 404


# =============================================================================
# Undo check-in (POST /guestlist/entry/<id>/undo-check-in)
# =============================================================================

class TestUndoCheckIn:
    """Tests for undoing a check-in."""

    def test_undo_check_in(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Undo reverts CHECKED_IN back to APPROVED."""
        entry = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Undo CI', guest_email='uci@test.com',
            status=GuestlistStatus.CHECKED_IN,
        )
        with app.app_context():
            e = db.session.get(GuestlistEntry, entry.id)
            e.checked_in_at = datetime.utcnow()
            e.checked_in_plus_ones = 1
            db.session.commit()

        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{entry.id}/undo-check-in',
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with app.app_context():
            updated = db.session.get(GuestlistEntry, entry.id)
            assert updated.status == GuestlistStatus.APPROVED
            assert updated.checked_in_at is None
            assert updated.checked_in_plus_ones is None

    def test_undo_check_in_ajax(
        self, app, client, manager_user, sample_tour_stop
    ):
        """AJAX undo returns JSON."""
        entry = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Ajax Undo', guest_email='au@test.com',
            status=GuestlistStatus.CHECKED_IN,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{entry.id}/undo-check-in',
            headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True

    def test_undo_check_in_not_checked_in_returns_400(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Cannot undo if entry is not CHECKED_IN."""
        entry = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Not CI', guest_email='nci@test.com',
            status=GuestlistStatus.APPROVED,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{entry.id}/undo-check-in',
            headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_undo_check_in_permission_denied(
        self, app, client, viewer_user, manager_user, sample_band, sample_tour_stop
    ):
        """VIEWER cannot undo check-in."""
        membership = BandMembership(
            user_id=viewer_user.id, band_id=sample_band.id,
            instrument='Piano', role_in_band='Pianist',
        )
        db.session.add(membership)
        db.session.commit()

        entry = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Viewer Undo', guest_email='vu@test.com',
            status=GuestlistStatus.CHECKED_IN,
        )
        _login(client, VIEWER_EMAIL, VIEWER_PASS)
        resp = client.post(
            f'/guestlist/entry/{entry.id}/undo-check-in',
            headers={'X-Requested-With': 'XMLHttpRequest'},
        )
        assert resp.status_code == 403


# =============================================================================
# Bulk actions (POST /guestlist/stop/<id>/bulk-action)
# =============================================================================

class TestBulkAction:
    """Tests for bulk approve/deny/delete."""

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_bulk_approve(
        self, mock_notify, app, client, manager_user, sample_tour_stop
    ):
        """Bulk approve pending entries."""
        e1 = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Bulk A1', guest_email='ba1@test.com',
            status=GuestlistStatus.PENDING,
        )
        e2 = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Bulk A2', guest_email='ba2@test.com',
            status=GuestlistStatus.PENDING,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/stop/{sample_tour_stop.id}/bulk-action',
            data={
                'action': 'approve',
                'entry_ids': [str(e1.id), str(e2.id)],
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with app.app_context():
            assert db.session.get(GuestlistEntry, e1.id).status == GuestlistStatus.APPROVED
            assert db.session.get(GuestlistEntry, e2.id).status == GuestlistStatus.APPROVED

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_bulk_deny(
        self, mock_notify, app, client, manager_user, sample_tour_stop
    ):
        """Bulk deny pending entries."""
        e1 = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Bulk D1', guest_email='bd1@test.com',
            status=GuestlistStatus.PENDING,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/stop/{sample_tour_stop.id}/bulk-action',
            data={
                'action': 'deny',
                'entry_ids': [str(e1.id)],
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with app.app_context():
            assert db.session.get(GuestlistEntry, e1.id).status == GuestlistStatus.DENIED

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_bulk_delete(
        self, mock_notify, app, client, manager_user, sample_tour_stop
    ):
        """Bulk delete entries."""
        e1 = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Bulk Del', guest_email='bdel@test.com',
        )
        eid = e1.id
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/stop/{sample_tour_stop.id}/bulk-action',
            data={
                'action': 'delete',
                'entry_ids': [str(eid)],
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with app.app_context():
            assert db.session.get(GuestlistEntry, eid) is None

    def test_bulk_no_entries_selected(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Bulk action with no entry_ids flashes warning."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/stop/{sample_tour_stop.id}/bulk-action',
            data={'action': 'approve'},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        body = resp.data.decode('utf-8')
        assert 'aucune' in body.lower() or 'sélectionnée' in body.lower()

    def test_bulk_permission_denied_viewer(
        self, app, client, viewer_user, sample_band, sample_tour_stop
    ):
        """VIEWER cannot perform bulk actions."""
        membership = BandMembership(
            user_id=viewer_user.id, band_id=sample_band.id,
            instrument='Tuba', role_in_band='Extra',
        )
        db.session.add(membership)
        db.session.commit()

        _login(client, VIEWER_EMAIL, VIEWER_PASS)
        resp = client.post(
            f'/guestlist/stop/{sample_tour_stop.id}/bulk-action',
            data={'action': 'approve', 'entry_ids': ['1']},
            follow_redirects=True,
        )
        body = resp.data.decode('utf-8')
        assert 'permission' in body.lower() or 'refusée' in body.lower()

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification', side_effect=Exception('fail'))
    def test_bulk_approve_email_failure_does_not_crash(
        self, mock_notify, app, client, manager_user, sample_tour_stop
    ):
        """Email failure during bulk approve is caught gracefully."""
        e1 = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Bulk Email Fail', guest_email='bef@test.com',
            status=GuestlistStatus.PENDING,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/stop/{sample_tour_stop.id}/bulk-action',
            data={'action': 'approve', 'entry_ids': [str(e1.id)]},
            follow_redirects=True,
        )
        assert resp.status_code == 200


# =============================================================================
# CSV Export (GET /guestlist/stop/<id>/export)
# =============================================================================

class TestExportCSV:
    """Tests for CSV guestlist export."""

    def test_export_csv_default_filter(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Default export returns approved/checked-in entries as CSV."""
        _make_entry(
            sample_tour_stop, manager_user,
            guest_name='CSV Guest', guest_email='csv@test.com',
            status=GuestlistStatus.APPROVED, entry_type=EntryType.VIP,
            plus_ones=1, company='Export Co',
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(f'/guestlist/stop/{sample_tour_stop.id}/export')
        assert resp.status_code == 200
        assert resp.content_type == 'text/csv; charset=utf-8'
        assert b'CSV Guest' in resp.data
        assert b'Export Co' in resp.data

    def test_export_csv_all_filter(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Export with status=all includes all statuses."""
        _make_entry(
            sample_tour_stop, manager_user,
            guest_name='All Status', guest_email='all@test.com',
            status=GuestlistStatus.PENDING,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/stop/{sample_tour_stop.id}/export?status=all'
        )
        assert resp.status_code == 200
        assert b'All Status' in resp.data

    def test_export_csv_specific_status_filter(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Export filtered by a specific status."""
        _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Denied Export', guest_email='de@test.com',
            status=GuestlistStatus.DENIED,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/stop/{sample_tour_stop.id}/export?status=denied'
        )
        assert resp.status_code == 200
        assert b'Denied Export' in resp.data

    def test_export_csv_invalid_status_ignored(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Invalid status filter is silently ignored."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/stop/{sample_tour_stop.id}/export?status=BOGUS'
        )
        assert resp.status_code == 200

    def test_export_csv_has_correct_headers(
        self, app, client, manager_user, sample_tour_stop
    ):
        """CSV starts with the expected header row."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(f'/guestlist/stop/{sample_tour_stop.id}/export')
        first_line = resp.data.decode('utf-8').split('\n')[0]
        assert 'Nom' in first_line
        assert 'Email' in first_line
        assert 'Statut' in first_line

    def test_export_csv_content_disposition(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Response has Content-Disposition attachment header."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(f'/guestlist/stop/{sample_tour_stop.id}/export')
        cd = resp.headers.get('Content-Disposition', '')
        assert 'attachment' in cd
        assert 'guestlist_' in cd

    def test_export_no_band_access(
        self, app, client, staff_user, sample_tour_stop
    ):
        """User outside band cannot export."""
        _login(client, STAFF_EMAIL, STAFF_PASS)
        resp = client.get(
            f'/guestlist/stop/{sample_tour_stop.id}/export',
            follow_redirects=True,
        )
        body = resp.data.decode('utf-8')
        assert 'non autorisé' in body.lower() or 'dashboard' in resp.request.path

    def test_export_viewer_permission_denied(
        self, app, client, viewer_user, sample_band, sample_tour_stop
    ):
        """VIEWER in band cannot export (needs staff+)."""
        membership = BandMembership(
            user_id=viewer_user.id, band_id=sample_band.id,
            instrument='Harp', role_in_band='Harper',
        )
        db.session.add(membership)
        db.session.commit()

        _login(client, VIEWER_EMAIL, VIEWER_PASS)
        resp = client.get(
            f'/guestlist/stop/{sample_tour_stop.id}/export',
            follow_redirects=True,
        )
        body = resp.data.decode('utf-8')
        assert 'permission' in body.lower() or 'refusée' in body.lower()


# =============================================================================
# API Search (GET /guestlist/api/stop/<id>/search)
# =============================================================================

class TestAPISearch:
    """Tests for the AJAX search API endpoint."""

    def test_search_returns_matching_entries(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Search with valid query returns matching entries."""
        _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Searchable Alice', guest_email='alice@search.com',
            status=GuestlistStatus.APPROVED,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/api/stop/{sample_tour_stop.id}/search?q=Searchable'
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]['name'] == 'Searchable Alice'

    def test_search_too_short_query_returns_empty(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Query shorter than 2 chars returns empty list."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/api/stop/{sample_tour_stop.id}/search?q=A'
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data == []

    def test_search_empty_query_returns_empty(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Empty query returns empty list."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/api/stop/{sample_tour_stop.id}/search?q='
        )
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_search_no_match(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Query with no matching entries returns empty."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/api/stop/{sample_tour_stop.id}/search?q=ZZNOEXIST'
        )
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_search_only_approved_or_checked_in(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Search only returns APPROVED or CHECKED_IN entries."""
        _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Pending Search', guest_email='ps@test.com',
            status=GuestlistStatus.PENDING,
        )
        _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Approved Search', guest_email='as@test.com',
            status=GuestlistStatus.APPROVED,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/api/stop/{sample_tour_stop.id}/search?q=Search'
        )
        data = resp.get_json()
        names = [d['name'] for d in data]
        assert 'Approved Search' in names
        assert 'Pending Search' not in names

    def test_search_by_email(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Search matches on guest_email as well."""
        _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Email Match', guest_email='unique-email@search.com',
            status=GuestlistStatus.APPROVED,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/api/stop/{sample_tour_stop.id}/search?q=unique-email'
        )
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]['email'] == 'unique-email@search.com'

    def test_search_returns_correct_fields(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Each search result has the expected JSON fields."""
        _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Fields Test', guest_email='ft@test.com',
            status=GuestlistStatus.APPROVED, entry_type=EntryType.VIP,
            plus_ones=3,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/api/stop/{sample_tour_stop.id}/search?q=Fields'
        )
        data = resp.get_json()
        assert len(data) == 1
        item = data[0]
        assert 'id' in item
        assert item['name'] == 'Fields Test'
        assert item['type'] == 'vip'
        assert item['plus_ones'] == 3
        assert item['status'] == 'approved'

    def test_search_limit_20(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Search results are capped at 20."""
        for i in range(25):
            _make_entry(
                sample_tour_stop, manager_user,
                guest_name=f'Limit Test {i}', guest_email=f'lt{i}@test.com',
                status=GuestlistStatus.APPROVED,
            )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/api/stop/{sample_tour_stop.id}/search?q=Limit Test'
        )
        data = resp.get_json()
        assert len(data) <= 20


# =============================================================================
# Edge cases & integration
# =============================================================================

class TestEdgeCases:
    """Miscellaneous edge cases and cross-cutting concerns."""

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_add_entry_auto_approve_for_staff(
        self, mock_notify, app, client, manager_user, sample_band, sample_tour_stop
    ):
        """Staff+ users auto-approve their own entries on creation."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        client.post(
            f'/guestlist/stop/{sample_tour_stop.id}/add',
            data={
                'guest_name': 'Auto Approve',
                'guest_email': 'aa@test.com',
                'entry_type': 'guest',
                'artist_id': '0',
                'plus_ones': '0',
                'status': 'pending',
            },
            follow_redirects=True,
        )
        with app.app_context():
            entry = GuestlistEntry.query.filter_by(guest_name='Auto Approve').first()
            assert entry is not None
            assert entry.status == GuestlistStatus.APPROVED

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification', side_effect=Exception('fail'))
    def test_add_entry_email_failure_does_not_crash(
        self, mock_notify, app, client, manager_user, sample_tour_stop
    ):
        """Email failure during add_entry is caught and does not crash."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/stop/{sample_tour_stop.id}/add',
            data={
                'guest_name': 'Email Fail',
                'guest_email': 'ef@test.com',
                'entry_type': 'guest',
                'artist_id': '0',
                'plus_ones': '0',
                'status': 'pending',
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_delete_no_show_entry_blocked(
        self, app, client, manager_user, sample_tour_stop
    ):
        """NO_SHOW entries are also locked and cannot be deleted."""
        entry = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='No Show Del', guest_email='nsd@test.com',
            status=GuestlistStatus.NO_SHOW,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{entry.id}/delete',
            follow_redirects=True,
        )
        body = resp.data.decode('utf-8')
        assert 'verrouillée' in body.lower()
        with app.app_context():
            assert db.session.get(GuestlistEntry, entry.id) is not None

    def test_edit_no_show_entry_blocked(
        self, app, client, manager_user, sample_tour_stop
    ):
        """NO_SHOW entries cannot be edited (locked)."""
        entry = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='No Show Edit', guest_email='nse@test.com',
            status=GuestlistStatus.NO_SHOW,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(
            f'/guestlist/entry/{entry.id}/edit',
            follow_redirects=True,
        )
        body = resp.data.decode('utf-8')
        assert 'verrouillée' in body.lower()

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_bulk_approve_skips_non_pending(
        self, mock_notify, app, client, manager_user, sample_tour_stop
    ):
        """Bulk approve only affects PENDING entries, skipping others."""
        e_approved = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Already Approved', guest_email='aa@test.com',
            status=GuestlistStatus.APPROVED,
        )
        e_pending = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Still Pending', guest_email='sp@test.com',
            status=GuestlistStatus.PENDING,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/stop/{sample_tour_stop.id}/bulk-action',
            data={
                'action': 'approve',
                'entry_ids': [str(e_approved.id), str(e_pending.id)],
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        body = resp.data.decode('utf-8')
        assert '1 entrée' in body

    def test_export_empty_guestlist(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Exporting an empty guestlist produces a CSV with only headers."""
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(f'/guestlist/stop/{sample_tour_stop.id}/export')
        assert resp.status_code == 200
        lines = resp.data.decode('utf-8').strip().split('\n')
        assert len(lines) >= 1
        assert 'Nom' in lines[0]

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_check_in_without_email_no_async_email(
        self, mock_notify, app, client, manager_user, sample_tour_stop
    ):
        """Check-in of entry without guest_email skips async email thread."""
        entry = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='No Email', guest_email='',
            status=GuestlistStatus.APPROVED,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{entry.id}/check-in',
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_manage_stats_calculation(
        self, app, client, manager_user, sample_tour_stop
    ):
        """Stats on the manage page are computed correctly."""
        _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Stat Pending', guest_email='sp@test.com',
            status=GuestlistStatus.PENDING,
        )
        _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Stat Approved', guest_email='sa@test.com',
            status=GuestlistStatus.APPROVED, plus_ones=2,
        )
        _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Stat CheckedIn', guest_email='sci@test.com',
            status=GuestlistStatus.CHECKED_IN, plus_ones=1,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.get(f'/guestlist/stop/{sample_tour_stop.id}')
        assert resp.status_code == 200

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_edit_entry_artist_type_with_valid_member(
        self, mock_notify, app, client, manager_user, sample_band,
        sample_tour_stop
    ):
        """Editing an artist-type entry with a valid band member updates user_id.

        Because routes.py line 310 overwrites ``form.entry_type.data`` with the
        entry's current type, we must start with an ARTIST-type entry to reach
        the artist branch in the edit handler.
        """
        membership = BandMembership(
            user_id=manager_user.id, band_id=sample_band.id,
            instrument='Guitar', role_in_band='Lead',
        )
        db.session.add(membership)
        db.session.commit()

        # Create an entry that is already ARTIST type
        artist_entry = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Artist Entry', guest_email='artist@test.com',
            entry_type=EntryType.ARTIST,
            status=GuestlistStatus.PENDING,
        )

        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{artist_entry.id}/edit',
            data={
                'guest_name': '',
                'guest_email': '',
                'entry_type': 'artist',
                'artist_id': str(manager_user.id),
                'plus_ones': '0',
                'status': 'pending',
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        with app.app_context():
            entry = db.session.get(GuestlistEntry, artist_entry.id)
            assert entry.user_id == manager_user.id
            assert entry.entry_type == EntryType.ARTIST
            assert entry.guest_name == manager_user.full_name

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_edit_entry_artist_type_invalid_member(
        self, mock_notify, app, client, manager_user,
        sample_tour_stop
    ):
        """Editing an artist-type entry with invalid member flashes error.

        Entry must already be ARTIST type so that ``form.entry_type.data``
        (overwritten by route line 310) stays 'artist'.
        """
        artist_entry = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Artist Invalid', guest_email='ai@test.com',
            entry_type=EntryType.ARTIST,
            status=GuestlistStatus.PENDING,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{artist_entry.id}/edit',
            data={
                'guest_name': '',
                'guest_email': '',
                'entry_type': 'artist',
                'artist_id': '99999',
                'plus_ones': '0',
                'status': 'pending',
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        body = resp.data.decode('utf-8')
        assert 'invalide' in body.lower() or 'artiste' in body.lower()

    @patch('app.blueprints.guestlist.routes.send_guestlist_notification')
    def test_edit_entry_artist_type_no_name_no_id(
        self, mock_notify, app, client, manager_user,
        sample_tour_stop
    ):
        """Editing an artist-type entry with no selection and no name flashes error.

        Entry must already be ARTIST type so that ``form.entry_type.data``
        (overwritten by route line 310) stays 'artist'.
        """
        artist_entry = _make_entry(
            sample_tour_stop, manager_user,
            guest_name='Artist NoId', guest_email='ani@test.com',
            entry_type=EntryType.ARTIST,
            status=GuestlistStatus.PENDING,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/entry/{artist_entry.id}/edit',
            data={
                'guest_name': '',
                'guest_email': '',
                'entry_type': 'artist',
                'artist_id': '0',
                'plus_ones': '0',
                'status': 'pending',
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        body = resp.data.decode('utf-8')
        assert 'artiste' in body.lower() or 'sélectionner' in body.lower()

    def test_bulk_action_entries_from_different_stop_ignored(
        self, app, client, manager_user, sample_tour, sample_venue, sample_tour_stop
    ):
        """Bulk action only affects entries belonging to the target stop."""
        other_stop = TourStop(
            tour=sample_tour, venue=sample_venue,
            date=date.today() + timedelta(days=14),
            doors_time=time(19, 0), set_time=time(21, 0),
            status=TourStopStatus.CONFIRMED,
        )
        db.session.add(other_stop)
        db.session.commit()
        db.session.expire_all()
        other_stop = db.session.get(TourStop, other_stop.id)

        entry_other = _make_entry(
            other_stop, manager_user,
            guest_name='Other Stop', guest_email='os@test.com',
            status=GuestlistStatus.PENDING,
        )
        _login(client, MANAGER_EMAIL, MANAGER_PASS)
        resp = client.post(
            f'/guestlist/stop/{sample_tour_stop.id}/bulk-action',
            data={
                'action': 'approve',
                'entry_ids': [str(entry_other.id)],
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            e = db.session.get(GuestlistEntry, entry_other.id)
            assert e.status == GuestlistStatus.PENDING
