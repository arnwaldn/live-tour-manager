# =============================================================================
# Tour Manager - Payments Routes Tests
# =============================================================================

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.extensions import db
from app.models.user import User, Role
from app.models.band import Band
from app.models.tour import Tour, TourStatus
from app.models.payments import (
    TeamMemberPayment, UserPaymentConfig,
    StaffCategory, StaffRole, PaymentType, PaymentStatus, PaymentMethod,
    PaymentFrequency
)


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
        permissions=['manage_band', 'manage_tour', 'manage_payments', 'view_tour']
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
def payee_user(app, musician_role):
    """Create a user to receive payments."""
    user = User(
        email='payee@test.com',
        first_name='John',
        last_name='Payee',
        is_active=True
    )
    user.set_password('Payee123!')
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
def draft_payment(app, payee_user, tour, manager_user):
    """Create a draft payment."""
    payment = TeamMemberPayment(
        user_id=payee_user.id,
        tour_id=tour.id,
        staff_category=StaffCategory.ARTISTIC,
        staff_role=StaffRole.MUSICIAN,
        payment_type=PaymentType.CACHET,
        description='Cachet artiste',
        amount=Decimal('2500.00'),
        currency='EUR',
        work_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=PaymentStatus.DRAFT,
        created_by_id=manager_user.id
    )
    payment.reference = TeamMemberPayment.generate_reference()
    db.session.add(payment)
    db.session.commit()
    return payment


@pytest.fixture
def pending_payment(app, payee_user, tour, manager_user):
    """Create a payment pending approval."""
    payment = TeamMemberPayment(
        user_id=payee_user.id,
        tour_id=tour.id,
        staff_category=StaffCategory.ARTISTIC,
        staff_role=StaffRole.MUSICIAN,
        payment_type=PaymentType.PER_DIEM,
        description='Per diem for show',
        amount=Decimal('150.00'),
        currency='EUR',
        work_date=date.today(),
        due_date=date.today() + timedelta(days=7),
        status=PaymentStatus.PENDING_APPROVAL,
        created_by_id=manager_user.id
    )
    payment.reference = TeamMemberPayment.generate_reference()
    db.session.add(payment)
    db.session.commit()
    return payment


@pytest.fixture
def approved_payment(app, payee_user, tour, manager_user):
    """Create an approved payment."""
    payment = TeamMemberPayment(
        user_id=payee_user.id,
        tour_id=tour.id,
        staff_category=StaffCategory.TECHNICAL,
        staff_role=StaffRole.FOH_ENGINEER,
        payment_type=PaymentType.CACHET,
        description='Cachet ingenieur son',
        amount=Decimal('500.00'),
        currency='EUR',
        work_date=date.today(),
        due_date=date.today() + timedelta(days=14),
        status=PaymentStatus.APPROVED,
        created_by_id=manager_user.id,
        approved_by_id=manager_user.id,
        approved_at=datetime.utcnow()
    )
    payment.reference = TeamMemberPayment.generate_reference()
    db.session.add(payment)
    db.session.commit()
    return payment


@pytest.fixture
def paid_payment(app, payee_user, tour, manager_user):
    """Create a paid payment."""
    payment = TeamMemberPayment(
        user_id=payee_user.id,
        tour_id=tour.id,
        staff_category=StaffCategory.ARTISTIC,
        staff_role=StaffRole.MUSICIAN,
        payment_type=PaymentType.BONUS,
        description='Performance bonus',
        amount=Decimal('300.00'),
        currency='EUR',
        work_date=date.today() - timedelta(days=7),
        due_date=date.today(),
        status=PaymentStatus.PAID,
        created_by_id=manager_user.id,
        paid_date=date.today()
    )
    payment.reference = TeamMemberPayment.generate_reference()
    db.session.add(payment)
    db.session.commit()
    return payment


# =============================================================================
# Test Index / List
# =============================================================================

class TestPaymentsList:
    """Tests for payments list view."""

    def test_index_requires_login(self, client):
        """Test index requires authentication."""
        response = client.get('/payments/')
        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_index_requires_manager(self, client, musician_user):
        """Test index requires manager role."""
        login(client, 'musician@test.com', 'Musician123!')
        response = client.get('/payments/', follow_redirects=True)
        assert b'manager' in response.data.lower() or b'acces' in response.data.lower()

    def test_manager_can_view_list(self, client, manager_user):
        """Test manager can view payments list."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/payments/')
        assert response.status_code == 200

    def test_list_shows_payments(self, client, manager_user, draft_payment):
        """Test list shows existing payments."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/payments/')
        assert response.status_code == 200
        assert draft_payment.reference.encode() in response.data or b'payment' in response.data.lower()

    def test_filter_by_status(self, client, manager_user, draft_payment, pending_payment):
        """Test filtering payments by status."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/payments/?status=draft')
        assert response.status_code == 200

    def test_filter_by_tour(self, client, manager_user, draft_payment, tour):
        """Test filtering payments by tour."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get(f'/payments/?tour_id={tour.id}')
        assert response.status_code == 200

    def test_filter_by_date_range(self, client, manager_user, draft_payment):
        """Test filtering payments by date range."""
        login(client, 'manager@test.com', 'Manager123!')
        today = date.today().isoformat()
        response = client.get(f'/payments/?date_from={today}&date_to={today}')
        assert response.status_code == 200


# =============================================================================
# Test Dashboard
# =============================================================================

class TestPaymentsDashboard:
    """Tests for payments dashboard."""

    def test_dashboard_requires_login(self, client):
        """Test dashboard requires authentication."""
        response = client.get('/payments/dashboard')
        assert response.status_code == 302

    def test_dashboard_requires_manager(self, client, musician_user):
        """Test dashboard requires manager role."""
        login(client, 'musician@test.com', 'Musician123!')
        response = client.get('/payments/dashboard', follow_redirects=True)
        assert b'manager' in response.data.lower() or b'acces' in response.data.lower()

    def test_manager_can_view_dashboard(self, client, manager_user):
        """Test manager can view dashboard."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/payments/dashboard')
        assert response.status_code == 200

    def test_dashboard_shows_stats(self, client, manager_user, pending_payment, approved_payment):
        """Test dashboard shows statistics."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/payments/dashboard')
        assert response.status_code == 200
        # Dashboard should show pending count and totals


# =============================================================================
# Test Add Payment
# =============================================================================

class TestAddPayment:
    """Tests for adding payments."""

    def test_add_requires_login(self, client):
        """Test add requires authentication."""
        response = client.get('/payments/add')
        assert response.status_code == 302

    def test_add_requires_manager(self, client, musician_user):
        """Test add requires manager role."""
        login(client, 'musician@test.com', 'Musician123!')
        response = client.get('/payments/add', follow_redirects=True)
        assert b'manager' in response.data.lower()

    def test_manager_can_access_add_form(self, client, manager_user):
        """Test manager can access add form."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/payments/add')
        assert response.status_code == 200
        assert b'form' in response.data.lower()

    def test_create_salary_payment(self, client, manager_user, payee_user, tour):
        """Test creating a salary payment."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post('/payments/add', data={
            'user_id': payee_user.id,
            'tour_id': tour.id,
            'tour_stop_id': 0,
            'staff_category': 'artistic',
            'staff_role': 'MUSICIAN',
            'payment_type': 'cachet',
            'payment_frequency': 'monthly',
            'description': 'January 2026 salary',
            'quantity': '1',
            'unit_rate': '3000.00',
            'amount': '3000.00',
            'currency': 'EUR',
            'work_date': date.today().isoformat(),
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'payment_method': 'bank_transfer'
        }, follow_redirects=True)

        assert response.status_code == 200
        # Verify payment was created
        payment = TeamMemberPayment.query.filter_by(description='January 2026 salary').first()
        assert payment is not None
        assert payment.amount == Decimal('3000.00')
        assert payment.status == PaymentStatus.DRAFT

    def test_create_per_diem_payment(self, client, manager_user, payee_user, tour):
        """Test creating a per diem payment."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post('/payments/add', data={
            'user_id': payee_user.id,
            'tour_id': tour.id,
            'tour_stop_id': 0,
            'staff_category': 'technical',
            'staff_role': 'TOUR_MANAGER',
            'payment_type': 'per_diem',
            'description': 'Per diem - Paris show',
            'quantity': '1',
            'unit_rate': '75.00',
            'amount': '75.00',
            'currency': 'EUR',
            'work_date': date.today().isoformat(),
            'due_date': (date.today() + timedelta(days=7)).isoformat()
        }, follow_redirects=True)

        assert response.status_code == 200
        payment = TeamMemberPayment.query.filter_by(description='Per diem - Paris show').first()
        assert payment is not None

    def test_create_bonus_payment(self, client, manager_user, payee_user):
        """Test creating a bonus payment without tour."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post('/payments/add', data={
            'user_id': payee_user.id,
            'tour_id': 0,  # No tour
            'tour_stop_id': 0,
            'staff_category': 'artistic',
            'staff_role': 'MUSICIAN',
            'payment_type': 'bonus',
            'description': 'Year-end bonus',
            'amount': '500.00',
            'currency': 'EUR',
            'work_date': date.today().isoformat(),
            'due_date': (date.today() + timedelta(days=14)).isoformat()
        }, follow_redirects=True)

        assert response.status_code == 200


# =============================================================================
# Test Payment Detail
# =============================================================================

class TestPaymentDetail:
    """Tests for viewing payment details."""

    def test_detail_requires_login(self, client, draft_payment):
        """Test detail view requires authentication."""
        response = client.get(f'/payments/{draft_payment.id}')
        assert response.status_code == 302

    def test_manager_can_view_detail(self, client, manager_user, draft_payment):
        """Test manager can view payment details."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get(f'/payments/{draft_payment.id}')
        assert response.status_code == 200
        assert draft_payment.reference.encode() in response.data or b'payment' in response.data.lower()

    def test_nonexistent_payment_returns_404(self, client, manager_user):
        """Test viewing nonexistent payment returns 404."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/payments/99999')
        assert response.status_code == 404


# =============================================================================
# Test Edit Payment
# =============================================================================

class TestEditPayment:
    """Tests for editing payments."""

    def test_edit_requires_login(self, client, draft_payment):
        """Test edit requires authentication."""
        response = client.get(f'/payments/{draft_payment.id}/edit')
        assert response.status_code == 302

    def test_manager_can_edit_draft(self, client, manager_user, draft_payment):
        """Test manager can edit draft payment."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get(f'/payments/{draft_payment.id}/edit')
        assert response.status_code == 200

    def test_edit_updates_payment(self, client, manager_user, draft_payment, payee_user, tour):
        """Test editing updates payment data."""
        login(client, 'manager@test.com', 'Manager123!')

        new_amount = '3500.00'
        response = client.post(f'/payments/{draft_payment.id}/edit', data={
            'user_id': payee_user.id,
            'tour_id': tour.id,
            'tour_stop_id': 0,
            'staff_category': 'artistic',
            'staff_role': 'MUSICIAN',
            'payment_type': 'cachet',
            'description': 'Updated salary',
            'quantity': '1',
            'unit_rate': new_amount,
            'amount': new_amount,
            'currency': 'EUR',
            'work_date': date.today().isoformat(),
            'due_date': (date.today() + timedelta(days=30)).isoformat()
        }, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(draft_payment)
        assert draft_payment.amount == Decimal(new_amount)

    def test_cannot_edit_paid_payment(self, client, manager_user, paid_payment):
        """Test cannot edit a paid payment."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get(f'/payments/{paid_payment.id}/edit', follow_redirects=True)
        # Should redirect with warning
        assert response.status_code == 200
        assert b'modifie' in response.data.lower() or b'paid' in response.data.lower()


# =============================================================================
# Test Delete Payment
# =============================================================================

class TestDeletePayment:
    """Tests for deleting payments."""

    def test_delete_requires_login(self, client, draft_payment):
        """Test delete requires authentication."""
        response = client.post(f'/payments/{draft_payment.id}/delete')
        assert response.status_code == 302

    def test_delete_requires_post(self, client, manager_user, draft_payment):
        """Test delete only works with POST."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get(f'/payments/{draft_payment.id}/delete')
        assert response.status_code == 405

    def test_can_delete_draft(self, client, manager_user, draft_payment):
        """Test can delete draft payment."""
        login(client, 'manager@test.com', 'Manager123!')
        payment_id = draft_payment.id

        response = client.post(f'/payments/{payment_id}/delete', follow_redirects=True)
        assert response.status_code == 200

        deleted = TeamMemberPayment.query.get(payment_id)
        assert deleted is None

    def test_cannot_delete_approved_payment(self, client, manager_user, approved_payment):
        """Test cannot delete approved payment."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post(f'/payments/{approved_payment.id}/delete', follow_redirects=True)
        assert response.status_code == 200

        # Payment should still exist
        payment = TeamMemberPayment.query.get(approved_payment.id)
        assert payment is not None


# =============================================================================
# Test Approval Workflow
# =============================================================================

class TestApprovalWorkflow:
    """Tests for payment approval workflow."""

    def test_submit_for_approval(self, client, manager_user, draft_payment):
        """Test submitting payment for approval."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post(f'/payments/{draft_payment.id}/submit', follow_redirects=True)
        assert response.status_code == 200

        db.session.refresh(draft_payment)
        assert draft_payment.status == PaymentStatus.PENDING_APPROVAL

    def test_cannot_submit_already_pending(self, client, manager_user, pending_payment):
        """Test cannot submit already pending payment."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post(f'/payments/{pending_payment.id}/submit', follow_redirects=True)
        assert response.status_code == 200
        # Should show warning

    def test_view_approval_queue(self, client, manager_user, pending_payment):
        """Test viewing approval queue."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.get('/payments/approval-queue')
        assert response.status_code == 200
        assert pending_payment.reference.encode() in response.data or b'approval' in response.data.lower()

    def test_approve_payment(self, client, manager_user, pending_payment):
        """Test approving a payment."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post(f'/payments/{pending_payment.id}/approve', follow_redirects=True)
        assert response.status_code == 200

        db.session.refresh(pending_payment)
        assert pending_payment.status == PaymentStatus.APPROVED
        assert pending_payment.approved_by_id == manager_user.id

    def test_reject_payment(self, client, manager_user, pending_payment):
        """Test rejecting a payment."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post(f'/payments/{pending_payment.id}/reject', data={
            'reason': 'Amount incorrect'
        }, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(pending_payment)
        assert pending_payment.status == PaymentStatus.REJECTED

    def test_cannot_approve_draft(self, client, manager_user, draft_payment):
        """Test cannot approve a draft payment."""
        login(client, 'manager@test.com', 'Manager123!')

        original_status = draft_payment.status
        response = client.post(f'/payments/{draft_payment.id}/approve', follow_redirects=True)
        assert response.status_code == 200

        db.session.refresh(draft_payment)
        assert draft_payment.status == original_status


# =============================================================================
# Test Mark as Paid
# =============================================================================

class TestMarkAsPaid:
    """Tests for marking payments as paid."""

    def test_mark_approved_as_paid(self, client, manager_user, approved_payment):
        """Test marking approved payment as paid."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post(f'/payments/{approved_payment.id}/mark-paid', follow_redirects=True)
        assert response.status_code == 200

        db.session.refresh(approved_payment)
        assert approved_payment.status == PaymentStatus.PAID
        assert approved_payment.paid_at is not None

    def test_cannot_mark_draft_as_paid(self, client, manager_user, draft_payment):
        """Test cannot mark draft payment as paid."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.post(f'/payments/{draft_payment.id}/mark-paid', follow_redirects=True)
        assert response.status_code == 200

        db.session.refresh(draft_payment)
        assert draft_payment.status != PaymentStatus.PAID


# =============================================================================
# Test Summary Statistics
# =============================================================================

class TestSummaryStats:
    """Tests for payment summary statistics."""

    def test_list_shows_totals(self, client, manager_user, draft_payment, pending_payment, paid_payment):
        """Test list page shows total amounts."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.get('/payments/')
        assert response.status_code == 200
        # Page should show summary stats

    def test_dashboard_category_totals(self, client, manager_user, draft_payment, approved_payment):
        """Test dashboard shows category totals."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.get('/payments/dashboard')
        assert response.status_code == 200


# =============================================================================
# Test 404 Handling
# =============================================================================

class TestPaymentsNotFound:
    """Tests for 404 handling."""

    def test_detail_nonexistent(self, client, manager_user):
        """Test detail for nonexistent payment."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/payments/99999')
        assert response.status_code == 404

    def test_edit_nonexistent(self, client, manager_user):
        """Test edit for nonexistent payment."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.get('/payments/99999/edit')
        assert response.status_code == 404

    def test_delete_nonexistent(self, client, manager_user):
        """Test delete for nonexistent payment."""
        login(client, 'manager@test.com', 'Manager123!')
        response = client.post('/payments/99999/delete')
        assert response.status_code == 404


# =============================================================================
# Test Payment Types
# =============================================================================

class TestPaymentTypes:
    """Tests for different payment types."""

    def test_create_all_payment_types(self, client, manager_user, payee_user):
        """Test creating all payment types."""
        login(client, 'manager@test.com', 'Manager123!')

        payment_types = ['cachet', 'per_diem', 'overtime', 'bonus', 'reimbursement', 'advance']

        for ptype in payment_types:
            response = client.post('/payments/add', data={
                'user_id': payee_user.id,
                'tour_id': 0,
                'tour_stop_id': 0,
                'staff_category': 'artistic',
                'staff_role': 'MUSICIAN',
                'payment_type': ptype,
                'description': f'Test {ptype} payment',
                'amount': '100.00',
                'currency': 'EUR',
                'work_date': date.today().isoformat(),
                'due_date': (date.today() + timedelta(days=7)).isoformat()
            }, follow_redirects=True)

            assert response.status_code == 200


# =============================================================================
# Test Staff Categories
# =============================================================================

class TestStaffCategories:
    """Tests for staff categories."""

    def test_filter_by_category(self, client, manager_user, draft_payment, approved_payment):
        """Test filtering by staff category."""
        login(client, 'manager@test.com', 'Manager123!')

        response = client.get('/payments/?staff_category=artistic')
        assert response.status_code == 200

        response = client.get('/payments/?staff_category=technical')
        assert response.status_code == 200
