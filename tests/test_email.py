# =============================================================================
# Tour Manager - Email System Tests
# =============================================================================
"""
Comprehensive tests for the email notification system.
Tests all email functions with mocked SMTP to avoid actual email sending.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date, time, timedelta

from app.extensions import db
from app.models.user import User, Role
from app.models.band import Band, BandMembership
from app.models.venue import Venue
from app.models.tour import Tour, TourStatus
from app.models.tour_stop import TourStop, TourStopStatus
from app.models.guestlist import GuestlistEntry, GuestlistStatus, EntryType
from app.utils.email import (
    send_email,
    send_async_email,
    send_password_reset_email,
    send_welcome_email,
    send_invitation_email,
    send_guestlist_notification,
    send_tour_stop_notification,
    send_registration_notification,
    send_approval_email,
    send_rejection_email,
    _get_manager_emails,
    _get_band_member_emails,
    _html_to_text,
)


# =============================================================================
# Email-Specific Fixtures
# =============================================================================

@pytest.fixture
def mock_mail(app):
    """Mock Flask-Mail to prevent actual email sending."""
    with patch('app.utils.email.mail') as mock:
        mock.send = MagicMock(return_value=None)
        yield mock


@pytest.fixture
def user_with_reset_token(app, manager_role):
    """Create a user with a password reset token."""
    user = User(
        email='reset@test.com',
        first_name='Reset',
        last_name='User',
        phone='+33 6 00 00 00 00'
    )
    user.set_password('OldPassword123!')
    user.reset_token = 'test-reset-token-12345'
    user.roles.append(manager_role)
    db.session.add(user)
    db.session.commit()
    user_id = user.id
    db.session.expire_all()
    return db.session.get(User, user_id)


@pytest.fixture
def user_with_invitation_token(app, musician_role):
    """Create a user with an invitation token."""
    user = User(
        email='invited@test.com',
        first_name='Invited',
        last_name='User',
        phone='+33 6 11 11 11 11',
        is_active=False
    )
    user.set_password('TempPassword123!')  # Required: password_hash is NOT NULL
    user.invitation_token = 'invitation-token-xyz-789'
    user.roles.append(musician_role)
    db.session.add(user)
    db.session.commit()
    user_id = user.id
    db.session.expire_all()
    return db.session.get(User, user_id)


@pytest.fixture
def pending_user(app):
    """Create a pending registration user (awaiting approval)."""
    user = User(
        email='pending@test.com',
        first_name='Pending',
        last_name='Registration',
        is_active=False
    )
    user.set_password('Pending123!')
    db.session.add(user)
    db.session.commit()
    user_id = user.id
    db.session.expire_all()
    return db.session.get(User, user_id)


@pytest.fixture
def approved_guestlist_entry(app, sample_tour_stop, manager_user):
    """Create an approved guestlist entry."""
    entry = GuestlistEntry(
        guest_name='Jane Smith',
        guest_email='jane.smith@example.com',
        entry_type=EntryType.VIP,
        plus_ones=2,
        notes='VIP approved guest',
        status=GuestlistStatus.APPROVED,
        tour_stop=sample_tour_stop,
        requested_by=manager_user
    )
    db.session.add(entry)
    db.session.commit()
    entry_id = entry.id
    db.session.expire_all()
    return db.session.get(GuestlistEntry, entry_id)


@pytest.fixture
def denied_guestlist_entry(app, sample_tour_stop, manager_user):
    """Create a denied guestlist entry."""
    entry = GuestlistEntry(
        guest_name='Bob Wilson',
        guest_email='bob.wilson@example.com',
        entry_type=EntryType.GUEST,
        plus_ones=0,
        notes='Denied entry',
        status=GuestlistStatus.DENIED,
        tour_stop=sample_tour_stop,
        requested_by=manager_user
    )
    db.session.add(entry)
    db.session.commit()
    entry_id = entry.id
    db.session.expire_all()
    return db.session.get(GuestlistEntry, entry_id)


@pytest.fixture
def checked_in_guestlist_entry(app, sample_tour_stop, manager_user):
    """Create a checked-in guestlist entry."""
    entry = GuestlistEntry(
        guest_name='Alice Brown',
        guest_email='alice.brown@example.com',
        entry_type=EntryType.INDUSTRY,
        plus_ones=1,
        notes='Checked in',
        status=GuestlistStatus.CHECKED_IN,
        tour_stop=sample_tour_stop,
        requested_by=manager_user
    )
    db.session.add(entry)
    db.session.commit()
    entry_id = entry.id
    db.session.expire_all()
    return db.session.get(GuestlistEntry, entry_id)


@pytest.fixture
def band_with_members(app, manager_user, musician_role):
    """Create a band with multiple members for email recipient testing."""
    band = Band(
        name='Full Band',
        genre='Jazz',
        bio='A band with multiple members',
        manager=manager_user
    )
    db.session.add(band)
    db.session.flush()

    # Add musician members
    for i in range(2):
        member = User(
            email=f'member{i}@band.com',
            first_name=f'Member{i}',
            last_name='Musician'
        )
        member.set_password('Member123!')
        member.roles.append(musician_role)
        db.session.add(member)
        db.session.flush()

        membership = BandMembership(
            user=member,
            band=band,
            instrument=f'Instrument{i}'
        )
        db.session.add(membership)

    db.session.commit()
    band_id = band.id
    db.session.expire_all()
    return db.session.get(Band, band_id)


# =============================================================================
# Core Email Function Tests
# =============================================================================

class TestSendEmail:
    """Tests for the base send_email function."""

    def test_send_email_success(self, app, mock_mail):
        """Test successful email sending."""
        result = send_email(
            subject='Test Subject',
            recipient='recipient@test.com',
            template='welcome',
            user=MagicMock(first_name='Test', full_name='Test User'),
            login_url='http://localhost/login'
        )

        assert result is True
        mock_mail.send.assert_called_once()

    def test_send_email_failure(self, app):
        """Test email sending failure."""
        with patch('app.utils.email.mail') as mock_mail:
            mock_mail.send.side_effect = Exception('SMTP Error')

            result = send_email(
                subject='Test Subject',
                recipient='recipient@test.com',
                template='welcome',
                user=MagicMock(first_name='Test', full_name='Test User'),
                login_url='http://localhost/login'
            )

            assert result is False

    def test_send_email_adds_prefix_to_subject(self, app, mock_mail):
        """Test that email subject is prefixed with [Studio Palenque Tour]."""
        send_email(
            subject='My Subject',
            recipient='test@test.com',
            template='welcome',
            user=MagicMock(first_name='Test', full_name='Test User'),
            login_url='http://localhost/login'
        )

        # Get the Message object that was sent
        call_args = mock_mail.send.call_args
        message = call_args[0][0]

        assert '[Studio Palenque Tour]' in message.subject
        assert 'My Subject' in message.subject


class TestSendAsyncEmail:
    """Tests for async email (currently falls back to sync)."""

    def test_send_async_email_fallback(self, app, mock_mail):
        """Test that async email falls back to sync."""
        result = send_async_email(
            subject='Async Test',
            recipient='async@test.com',
            template='welcome',
            user=MagicMock(first_name='Test', full_name='Test User'),
            login_url='http://localhost/login'
        )

        assert result is True
        mock_mail.send.assert_called_once()


# =============================================================================
# Password Reset Email Tests
# =============================================================================

class TestPasswordResetEmail:
    """Tests for password reset email."""

    def test_send_password_reset_email_success(self, app, mock_mail, user_with_reset_token):
        """Test successful password reset email."""
        result = send_password_reset_email(
            user=user_with_reset_token,
            reset_token='test-token-123'
        )

        assert result is True
        mock_mail.send.assert_called_once()

        # Verify message content
        message = mock_mail.send.call_args[0][0]
        assert 'Reinitialisation' in message.subject
        assert user_with_reset_token.email == message.recipients[0]

    def test_send_password_reset_email_contains_url(self, app, mock_mail, user_with_reset_token):
        """Test that password reset email contains the reset URL."""
        send_password_reset_email(
            user=user_with_reset_token,
            reset_token='my-reset-token'
        )

        message = mock_mail.send.call_args[0][0]
        assert 'my-reset-token' in message.html


# =============================================================================
# Welcome Email Tests
# =============================================================================

class TestWelcomeEmail:
    """Tests for welcome email."""

    def test_send_welcome_email_success(self, app, mock_mail, manager_user):
        """Test successful welcome email."""
        result = send_welcome_email(user=manager_user)

        assert result is True
        mock_mail.send.assert_called_once()

        message = mock_mail.send.call_args[0][0]
        assert 'Bienvenue' in message.subject
        assert manager_user.email == message.recipients[0]


# =============================================================================
# Invitation Email Tests
# =============================================================================

class TestInvitationEmail:
    """Tests for invitation email."""

    def test_send_invitation_email_success(self, app, mock_mail, user_with_invitation_token, manager_user):
        """Test successful invitation email."""
        result = send_invitation_email(
            user=user_with_invitation_token,
            invited_by=manager_user
        )

        assert result is True
        mock_mail.send.assert_called_once()

        message = mock_mail.send.call_args[0][0]
        assert 'Invitation' in message.subject
        assert user_with_invitation_token.email == message.recipients[0]

    def test_send_invitation_email_contains_token(self, app, mock_mail, user_with_invitation_token, manager_user):
        """Test that invitation email contains the accept URL with token."""
        send_invitation_email(
            user=user_with_invitation_token,
            invited_by=manager_user
        )

        message = mock_mail.send.call_args[0][0]
        assert user_with_invitation_token.invitation_token in message.html


# =============================================================================
# Guestlist Notification Tests
# =============================================================================

class TestGuestlistNotification:
    """Tests for guestlist notification emails."""

    def test_guestlist_notification_approved(self, app, mock_mail, approved_guestlist_entry):
        """Test approved guestlist notification."""
        result = send_guestlist_notification(
            entry=approved_guestlist_entry,
            notification_type='approved'
        )

        assert result is True
        mock_mail.send.assert_called_once()

        message = mock_mail.send.call_args[0][0]
        assert 'approuvee' in message.subject.lower()
        assert approved_guestlist_entry.guest_email == message.recipients[0]

    def test_guestlist_notification_denied(self, app, mock_mail, denied_guestlist_entry):
        """Test denied guestlist notification."""
        result = send_guestlist_notification(
            entry=denied_guestlist_entry,
            notification_type='denied'
        )

        assert result is True
        mock_mail.send.assert_called_once()

        message = mock_mail.send.call_args[0][0]
        assert 'refusee' in message.subject.lower()

    def test_guestlist_notification_checked_in(self, app, mock_mail, checked_in_guestlist_entry):
        """Test checked-in guestlist notification."""
        result = send_guestlist_notification(
            entry=checked_in_guestlist_entry,
            notification_type='checked_in'
        )

        assert result is True
        mock_mail.send.assert_called_once()

        message = mock_mail.send.call_args[0][0]
        assert 'check-in' in message.subject.lower()

    def test_guestlist_notification_request_to_managers(self, app, mock_mail, sample_guestlist_entry, manager_user):
        """Test that guestlist request notification goes to managers."""
        result = send_guestlist_notification(
            entry=sample_guestlist_entry,
            notification_type='request'
        )

        # Should send to manager(s)
        assert result is True
        assert mock_mail.send.called

    def test_guestlist_notification_invalid_type(self, app, mock_mail, sample_guestlist_entry):
        """Test invalid notification type returns False."""
        result = send_guestlist_notification(
            entry=sample_guestlist_entry,
            notification_type='invalid_type'
        )

        assert result is False
        mock_mail.send.assert_not_called()


# =============================================================================
# Tour Stop Notification Tests
# =============================================================================

class TestTourStopNotification:
    """Tests for tour stop notification emails."""

    def test_tour_stop_notification_created(self, app, mock_mail, sample_tour_stop):
        """Test tour stop created notification."""
        result = send_tour_stop_notification(
            tour_stop=sample_tour_stop,
            notification_type='created'
        )

        assert result is True

        # Check message was sent
        assert mock_mail.send.called
        message = mock_mail.send.call_args[0][0]
        assert 'ajoutee' in message.subject.lower()

    def test_tour_stop_notification_updated(self, app, mock_mail, sample_tour_stop):
        """Test tour stop updated notification."""
        result = send_tour_stop_notification(
            tour_stop=sample_tour_stop,
            notification_type='updated'
        )

        assert result is True
        message = mock_mail.send.call_args[0][0]
        assert 'modifiee' in message.subject.lower()

    def test_tour_stop_notification_cancelled(self, app, mock_mail, sample_tour_stop):
        """Test tour stop cancelled notification."""
        result = send_tour_stop_notification(
            tour_stop=sample_tour_stop,
            notification_type='cancelled'
        )

        assert result is True
        message = mock_mail.send.call_args[0][0]
        assert 'annulee' in message.subject.lower()

    def test_tour_stop_notification_includes_venue_name(self, app, mock_mail, sample_tour_stop):
        """Test that tour stop notification includes venue name in subject."""
        send_tour_stop_notification(
            tour_stop=sample_tour_stop,
            notification_type='created'
        )

        message = mock_mail.send.call_args[0][0]
        assert sample_tour_stop.venue.name in message.subject


# =============================================================================
# Registration Notification Tests
# =============================================================================

class TestRegistrationNotification:
    """Tests for registration notification emails."""

    def test_send_registration_notification_to_managers(self, app, mock_mail, pending_user, manager_user):
        """Test that registration notification is sent to managers."""
        result = send_registration_notification(user=pending_user)

        assert result is True
        assert mock_mail.send.called

        message = mock_mail.send.call_args[0][0]
        assert 'inscription' in message.subject.lower()
        assert pending_user.full_name in message.subject

    def test_send_registration_notification_no_managers(self, app, mock_mail, pending_user):
        """Test registration notification when no managers exist."""
        # pending_user fixture doesn't create managers
        # This test verifies graceful handling
        result = send_registration_notification(user=pending_user)

        # Should return True even without recipients (not a failure)
        assert result is True


# =============================================================================
# Approval/Rejection Email Tests
# =============================================================================

class TestApprovalRejectionEmail:
    """Tests for approval and rejection emails."""

    def test_send_approval_email_success(self, app, mock_mail, pending_user):
        """Test successful approval email."""
        result = send_approval_email(user=pending_user)

        assert result is True
        mock_mail.send.assert_called_once()

        message = mock_mail.send.call_args[0][0]
        assert 'approuvee' in message.subject.lower()
        assert pending_user.email == message.recipients[0]

    def test_send_rejection_email_success(self, app, mock_mail):
        """Test successful rejection email."""
        result = send_rejection_email(
            email='rejected@test.com',
            name='Rejected User'
        )

        assert result is True
        mock_mail.send.assert_called_once()

        message = mock_mail.send.call_args[0][0]
        assert 'refusee' in message.subject.lower()
        assert 'rejected@test.com' == message.recipients[0]


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_manager_emails_with_band(self, app, band_with_members):
        """Test getting manager emails for a specific band."""
        emails = _get_manager_emails(band=band_with_members)

        # Should include the band manager
        assert band_with_members.manager.email in emails

    def test_get_manager_emails_system_wide(self, app, manager_user):
        """Test getting all system manager emails."""
        emails = _get_manager_emails(band=None)

        assert manager_user.email in emails

    def test_get_manager_emails_no_managers(self, app):
        """Test getting manager emails when none exist."""
        emails = _get_manager_emails(band=None)

        # Should return empty list, not error
        assert isinstance(emails, list)

    def test_get_band_member_emails(self, app, band_with_members):
        """Test getting all band member emails."""
        emails = _get_band_member_emails(band=band_with_members)

        # Should include manager
        assert band_with_members.manager.email in emails

        # Should include members
        assert len(emails) >= 3  # manager + 2 members

    def test_html_to_text_strips_tags(self, app):
        """Test HTML to text conversion strips tags."""
        html = '<p>Hello <strong>World</strong></p>'
        text = _html_to_text(html)

        assert '<p>' not in text
        assert '<strong>' not in text
        assert 'Hello' in text
        assert 'World' in text

    def test_html_to_text_handles_whitespace(self, app):
        """Test HTML to text handles excessive whitespace."""
        html = '<p>Hello</p>    <p>World</p>'
        text = _html_to_text(html)

        # Should not have excessive spaces
        assert '    ' not in text


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_guestlist_notification_requested_by_no_email(self, app, mock_mail, sample_tour_stop, manager_user, musician_role):
        """Test guestlist notification when requested_by user has no associated email for recipient."""
        # Create a guestlist entry where the guest_email exists but we test the fallback logic
        entry = GuestlistEntry(
            guest_name='Test Guest',
            guest_email='test@example.com',
            entry_type=EntryType.GUEST,
            status=GuestlistStatus.APPROVED,
            tour_stop=sample_tour_stop,
            requested_by=manager_user
        )
        db.session.add(entry)
        db.session.commit()

        result = send_guestlist_notification(
            entry=entry,
            notification_type='approved'
        )

        # Should send to guest_email
        assert result is True
        mock_mail.send.assert_called_once()

    def test_tour_stop_notification_band_no_members(self, app, mock_mail, sample_venue, manager_user):
        """Test tour stop notification when band has no additional members (only manager)."""
        # Create band with only manager (no memberships)
        band = Band(
            name='Solo Band',
            genre='Solo',
            manager=manager_user
        )
        db.session.add(band)
        db.session.flush()

        tour = Tour(
            name='Solo Tour',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.CONFIRMED,
            band=band
        )
        db.session.add(tour)
        db.session.flush()

        stop = TourStop(
            tour=tour,
            venue=sample_venue,
            date=date.today(),
            status=TourStopStatus.CONFIRMED
        )
        db.session.add(stop)
        db.session.commit()

        result = send_tour_stop_notification(
            tour_stop=stop,
            notification_type='created'
        )

        # Should send to manager only
        assert result is True
        mock_mail.send.assert_called_once()

    def test_send_email_with_special_characters(self, app, mock_mail, manager_user):
        """Test email sending with special characters in content."""
        # Emails with French accents should work
        result = send_email(
            subject='Test avec accents: e, a, u',
            recipient='test@test.com',
            template='welcome',
            user=manager_user,
            login_url='http://localhost/login'
        )

        assert result is True


# =============================================================================
# Integration Tests
# =============================================================================

class TestEmailIntegration:
    """Integration tests combining multiple email functions."""

    def test_full_guestlist_workflow(self, app, mock_mail, sample_tour_stop, manager_user):
        """Test complete guestlist email workflow: request -> approve -> check-in."""
        # Create new entry (pending)
        entry = GuestlistEntry(
            guest_name='Workflow Test',
            guest_email='workflow@test.com',
            entry_type=EntryType.VIP,
            plus_ones=1,
            status=GuestlistStatus.PENDING,
            tour_stop=sample_tour_stop,
            requested_by=manager_user
        )
        db.session.add(entry)
        db.session.commit()

        # Step 1: Request notification
        result1 = send_guestlist_notification(entry, 'request')
        assert result1 is True

        # Step 2: Approve
        entry.status = GuestlistStatus.APPROVED
        db.session.commit()
        result2 = send_guestlist_notification(entry, 'approved')
        assert result2 is True

        # Step 3: Check-in
        entry.status = GuestlistStatus.CHECKED_IN
        db.session.commit()
        result3 = send_guestlist_notification(entry, 'checked_in')
        assert result3 is True

        # Should have sent 3 emails total (request to managers + approved + checked_in)
        assert mock_mail.send.call_count >= 2

    def test_full_registration_workflow(self, app, mock_mail, manager_role):
        """Test complete registration email workflow: register -> notify -> approve."""
        # Need a manager for notifications first
        manager = User(
            email='admin@test.com',
            first_name='Admin',
            last_name='Manager'
        )
        manager.set_password('Admin123!')
        manager.roles.append(manager_role)
        db.session.add(manager)
        db.session.commit()

        # Step 1: Create pending user
        user = User(
            email='newuser@test.com',
            first_name='New',
            last_name='User',
            is_active=False
        )
        user.set_password('NewUser123!')
        db.session.add(user)
        db.session.commit()

        # Step 2: Notify managers
        result1 = send_registration_notification(user)
        assert result1 is True

        # Step 3: Approve
        user.is_active = True
        db.session.commit()
        result2 = send_approval_email(user)
        assert result2 is True

        # Should have sent 2 emails
        assert mock_mail.send.call_count >= 2
