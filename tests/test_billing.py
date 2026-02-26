# =============================================================================
# Tour Manager - Billing Module Tests (Phase 7c lite)
# =============================================================================
#
# Tests for Stripe SaaS billing: Subscription model, SubscriptionService,
# billing decorators, billing routes, webhook handling.
#
# NOTE: The `app` fixture already pushes an app context (via `with app.app_context():`
# in conftest.py). Do NOT wrap test bodies with `with app.app_context():`.
# =============================================================================

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.extensions import db
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.tour import Tour, TourStatus
from app.models.tour_stop import TourStop, TourStopStatus
from app.blueprints.billing.plans import PlanLimits, get_plan_limits, PLAN_LIMITS
from app.services.subscription_service import SubscriptionService, PlanLimitExceeded


# =============================================================================
# Plan Config Tests
# =============================================================================

class TestPlanConfig:
    """Tests for plan limits configuration."""

    def test_plan_limits_frozen(self):
        """PlanLimits dataclass is frozen (immutable)."""
        limits = PlanLimits(max_tours=1, max_stops_per_tour=5, features=['a'])
        with pytest.raises(AttributeError):
            limits.max_tours = 10

    def test_free_plan_limits(self):
        """Free plan has correct limits."""
        limits = PLAN_LIMITS['free']
        assert limits.max_tours == 1
        assert limits.max_stops_per_tour == 5
        assert 'advancing' in limits.features
        assert 'invoices' not in limits.features

    def test_pro_plan_limits(self):
        """Pro plan has unlimited (None) limits."""
        limits = PLAN_LIMITS['pro']
        assert limits.max_tours is None
        assert limits.max_stops_per_tour is None
        assert 'invoices' in limits.features
        assert 'api' in limits.features
        assert 'export_pdf' in limits.features

    def test_get_plan_limits_known(self):
        """get_plan_limits returns correct limits for known plan."""
        limits = get_plan_limits('pro')
        assert limits.max_tours is None

    def test_get_plan_limits_unknown_defaults_to_free(self):
        """get_plan_limits returns free limits for unknown plan."""
        limits = get_plan_limits('nonexistent')
        assert limits.max_tours == 1


# =============================================================================
# Subscription Model Tests
# =============================================================================

class TestSubscriptionModel:
    """Tests for Subscription SQLAlchemy model."""

    def test_create_subscription(self, app, manager_user):
        """Create a basic subscription record."""
        sub = Subscription(
            user_id=manager_user.id,
            plan=SubscriptionPlan.FREE,
            status=SubscriptionStatus.ACTIVE,
        )
        db.session.add(sub)
        db.session.commit()

        assert sub.id is not None
        assert sub.plan == SubscriptionPlan.FREE
        assert sub.status == SubscriptionStatus.ACTIVE

    def test_is_active_property(self, app, manager_user):
        """is_active returns True for active subscription."""
        sub = Subscription(
            user_id=manager_user.id,
            plan=SubscriptionPlan.PRO,
            status=SubscriptionStatus.ACTIVE,
        )
        db.session.add(sub)
        db.session.commit()

        assert sub.is_active is True

    def test_is_active_false_for_canceled(self, app, manager_user):
        """is_active returns False for canceled subscription."""
        sub = Subscription(
            user_id=manager_user.id,
            plan=SubscriptionPlan.PRO,
            status=SubscriptionStatus.CANCELED,
        )
        db.session.add(sub)
        db.session.commit()

        assert sub.is_active is False

    def test_is_pro_property(self, app, manager_user):
        """is_pro returns True for active Pro subscription."""
        sub = Subscription(
            user_id=manager_user.id,
            plan=SubscriptionPlan.PRO,
            status=SubscriptionStatus.ACTIVE,
        )
        db.session.add(sub)
        db.session.commit()

        assert sub.is_pro is True

    def test_is_pro_false_for_free(self, app, manager_user):
        """is_pro returns False for Free plan."""
        sub = Subscription(
            user_id=manager_user.id,
            plan=SubscriptionPlan.FREE,
            status=SubscriptionStatus.ACTIVE,
        )
        db.session.add(sub)
        db.session.commit()

        assert sub.is_pro is False

    def test_days_remaining_with_future_end(self, app, manager_user):
        """days_remaining returns positive value for future period end."""
        sub = Subscription(
            user_id=manager_user.id,
            plan=SubscriptionPlan.PRO,
            status=SubscriptionStatus.ACTIVE,
            current_period_end=datetime.utcnow() + timedelta(days=15),
        )
        db.session.add(sub)
        db.session.commit()

        assert sub.days_remaining >= 14  # At least 14 due to timing

    def test_days_remaining_none_without_period_end(self, app, manager_user):
        """days_remaining returns None when no period end set."""
        sub = Subscription(
            user_id=manager_user.id,
            plan=SubscriptionPlan.FREE,
            status=SubscriptionStatus.ACTIVE,
        )
        db.session.add(sub)
        db.session.commit()

        assert sub.days_remaining is None

    def test_user_current_plan_default_free(self, app, manager_user):
        """User without subscription has current_plan == 'free'."""
        assert manager_user.current_plan == 'free'

    def test_user_is_pro_default_false(self, app, manager_user):
        """User without subscription has is_pro == False."""
        assert manager_user.is_pro is False

    def test_user_current_plan_pro(self, app, manager_user):
        """User with Pro subscription has current_plan == 'pro'."""
        sub = Subscription(
            user_id=manager_user.id,
            plan=SubscriptionPlan.PRO,
            status=SubscriptionStatus.ACTIVE,
        )
        db.session.add(sub)
        db.session.commit()
        # Refresh user to pick up subscription
        db.session.expire(manager_user)

        assert manager_user.current_plan == 'pro'
        assert manager_user.is_pro is True

    def test_subscription_plan_enum_values(self):
        """SubscriptionPlan enum has expected values."""
        assert SubscriptionPlan.FREE.value == 'free'
        assert SubscriptionPlan.PRO.value == 'pro'

    def test_subscription_status_enum_values(self):
        """SubscriptionStatus enum has all expected values."""
        expected = {'active', 'past_due', 'canceled', 'trialing', 'incomplete'}
        actual = {s.value for s in SubscriptionStatus}
        assert actual == expected


# =============================================================================
# SubscriptionService Tests
# =============================================================================

class TestSubscriptionService:
    """Tests for SubscriptionService methods."""

    def test_ensure_subscription_exists_creates_free(self, app, manager_user):
        """ensure_subscription_exists creates FREE subscription when none exists."""
        assert manager_user.subscription is None

        sub = SubscriptionService.ensure_subscription_exists(manager_user)

        assert sub is not None
        assert sub.plan == SubscriptionPlan.FREE
        assert sub.status == SubscriptionStatus.ACTIVE
        assert sub.user_id == manager_user.id

    def test_ensure_subscription_exists_returns_existing(self, app, manager_user):
        """ensure_subscription_exists returns existing subscription."""
        sub1 = SubscriptionService.ensure_subscription_exists(manager_user)
        sub2 = SubscriptionService.ensure_subscription_exists(manager_user)

        assert sub1.id == sub2.id

    def test_activate_pro(self, app, manager_user):
        """activate_pro upgrades user to Pro plan."""
        SubscriptionService.ensure_subscription_exists(manager_user)

        sub = SubscriptionService.activate_pro(
            user=manager_user,
            stripe_subscription_id='sub_test_123',
            stripe_customer_id='cus_test_456',
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )

        assert sub.plan == SubscriptionPlan.PRO
        assert sub.status == SubscriptionStatus.ACTIVE
        assert sub.stripe_subscription_id == 'sub_test_123'
        assert manager_user.stripe_customer_id == 'cus_test_456'

    def test_cancel_subscription(self, app, manager_user):
        """cancel_subscription sets cancel_at_period_end."""
        SubscriptionService.ensure_subscription_exists(manager_user)

        sub = SubscriptionService.cancel_subscription(manager_user)

        assert sub.cancel_at_period_end is True

    def test_deactivate_subscription(self, app, manager_user):
        """deactivate_subscription reverts to Free."""
        SubscriptionService.activate_pro(
            user=manager_user,
            stripe_subscription_id='sub_test_789',
            stripe_customer_id='cus_test_012',
        )

        sub = SubscriptionService.deactivate_subscription(manager_user)

        assert sub.plan == SubscriptionPlan.FREE
        assert sub.status == SubscriptionStatus.CANCELED
        assert sub.stripe_subscription_id is None

    def test_check_tour_limit_free_allows_first(self, app, manager_user):
        """Free plan allows creating the first tour."""
        SubscriptionService.ensure_subscription_exists(manager_user)

        # Should not raise
        SubscriptionService.check_tour_limit(manager_user)

    def test_check_tour_limit_free_blocks_second(self, app, manager_user, sample_band):
        """Free plan blocks creating a second tour."""
        SubscriptionService.ensure_subscription_exists(manager_user)

        # Create first tour (allowed)
        tour = Tour(
            name='Tour 1',
            start_date=datetime.utcnow().date(),
            end_date=datetime.utcnow().date() + timedelta(days=10),
            band=sample_band,
        )
        db.session.add(tour)
        db.session.commit()

        with pytest.raises(PlanLimitExceeded) as exc_info:
            SubscriptionService.check_tour_limit(manager_user)

        assert exc_info.value.limit_name == 'tournees'
        assert exc_info.value.current == 1
        assert exc_info.value.maximum == 1

    def test_check_tour_limit_pro_unlimited(self, app, manager_user, sample_band):
        """Pro plan allows unlimited tours."""
        SubscriptionService.activate_pro(
            user=manager_user,
            stripe_subscription_id='sub_test',
            stripe_customer_id='cus_test',
        )
        db.session.expire(manager_user)

        # Create multiple tours
        for i in range(5):
            tour = Tour(
                name=f'Tour {i}',
                start_date=datetime.utcnow().date(),
                end_date=datetime.utcnow().date() + timedelta(days=10),
                band=sample_band,
            )
            db.session.add(tour)
        db.session.commit()

        # Should not raise
        SubscriptionService.check_tour_limit(manager_user)

    def test_check_stop_limit_free_allows_up_to_5(self, app, manager_user, sample_tour, sample_venue):
        """Free plan allows up to 5 stops per tour."""
        SubscriptionService.ensure_subscription_exists(manager_user)

        # Should not raise when under limit
        SubscriptionService.check_stop_limit(manager_user, sample_tour.id)

    def test_check_stop_limit_free_blocks_6th(self, app, manager_user, sample_tour, sample_venue):
        """Free plan blocks the 6th stop."""
        SubscriptionService.ensure_subscription_exists(manager_user)

        # Create 5 stops
        for i in range(5):
            stop = TourStop(
                tour_id=sample_tour.id,
                venue_id=sample_venue.id,
                date=datetime.utcnow().date() + timedelta(days=i),
                status=TourStopStatus.CONFIRMED,
            )
            db.session.add(stop)
        db.session.commit()

        with pytest.raises(PlanLimitExceeded) as exc_info:
            SubscriptionService.check_stop_limit(manager_user, sample_tour.id)

        assert exc_info.value.limit_name == 'dates par tournee'
        assert exc_info.value.current == 5
        assert exc_info.value.maximum == 5

    @patch('stripe.Customer.create')
    def test_get_or_create_stripe_customer_new(self, mock_create, app, manager_user):
        """get_or_create_stripe_customer creates new Stripe customer."""
        mock_create.return_value = MagicMock(id='cus_new_123')

        customer_id = SubscriptionService.get_or_create_stripe_customer(manager_user)

        assert customer_id == 'cus_new_123'
        assert manager_user.stripe_customer_id == 'cus_new_123'
        mock_create.assert_called_once()

    def test_get_or_create_stripe_customer_existing(self, app, manager_user):
        """get_or_create_stripe_customer returns existing ID."""
        manager_user.stripe_customer_id = 'cus_existing_456'
        db.session.commit()

        customer_id = SubscriptionService.get_or_create_stripe_customer(manager_user)

        assert customer_id == 'cus_existing_456'

    @patch('stripe.checkout.Session.create')
    @patch('stripe.Customer.create')
    def test_create_checkout_session(self, mock_customer, mock_checkout, app, manager_user):
        """create_checkout_session returns Stripe checkout URL."""
        mock_customer.return_value = MagicMock(id='cus_test')
        mock_checkout.return_value = MagicMock(url='https://checkout.stripe.com/test')

        url = SubscriptionService.create_checkout_session(manager_user)

        assert url == 'https://checkout.stripe.com/test'
        mock_checkout.assert_called_once()

    @patch('stripe.billing_portal.Session.create')
    @patch('stripe.Customer.create')
    def test_create_portal_session(self, mock_customer, mock_portal, app, manager_user):
        """create_portal_session returns Stripe portal URL."""
        mock_customer.return_value = MagicMock(id='cus_test')
        mock_portal.return_value = MagicMock(url='https://billing.stripe.com/test')

        url = SubscriptionService.create_portal_session(manager_user)

        assert url == 'https://billing.stripe.com/test'
        mock_portal.assert_called_once()


# =============================================================================
# PlanLimitExceeded Exception Tests
# =============================================================================

class TestPlanLimitExceeded:
    """Tests for PlanLimitExceeded exception."""

    def test_exception_attributes(self):
        """Exception stores limit_name, current, maximum."""
        exc = PlanLimitExceeded('tournees', 1, 1)
        assert exc.limit_name == 'tournees'
        assert exc.current == 1
        assert exc.maximum == 1

    def test_exception_message(self):
        """Exception has descriptive message."""
        exc = PlanLimitExceeded('dates par tournee', 5, 5)
        assert 'dates par tournee' in str(exc)
        assert '5/5' in str(exc)


# =============================================================================
# Billing Routes Tests
# =============================================================================

class TestBillingRoutes:
    """Tests for billing blueprint routes.

    Uses actual client.post('/auth/login') for authentication,
    matching the pattern from test_advancing.py. The session_transaction()
    approach in authenticated_client doesn't work with Flask-Login.
    """

    def _login(self, client):
        """Log in as the manager user."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!',
        })

    def test_pricing_page_public(self, client):
        """Pricing page is accessible without authentication."""
        response = client.get('/billing/pricing')
        assert response.status_code == 200
        assert b'Gratuit' in response.data
        assert b'Pro' in response.data

    def test_pricing_page_contains_plans(self, client):
        """Pricing page shows both Free and Pro plans."""
        response = client.get('/billing/pricing')
        assert b'0 &euro;' in response.data
        assert b'29 &euro;' in response.data

    def test_dashboard_requires_auth(self, client):
        """Dashboard redirects to login when not authenticated."""
        response = client.get('/billing/dashboard')
        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_dashboard_authenticated(self, client, app, manager_user):
        """Dashboard accessible when authenticated."""
        self._login(client)
        response = client.get('/billing/dashboard')
        assert response.status_code == 200
        assert b'abonnement' in response.data

    def test_checkout_requires_auth(self, client):
        """Checkout POST redirects to login when not authenticated."""
        response = client.post('/billing/checkout')
        assert response.status_code == 302
        assert '/auth/login' in response.location

    @patch('app.services.subscription_service.SubscriptionService.create_checkout_session')
    def test_checkout_redirects_to_stripe(self, mock_checkout, client, app, manager_user):
        """Checkout POST redirects to Stripe checkout URL."""
        mock_checkout.return_value = 'https://checkout.stripe.com/c/test_session'

        self._login(client)
        response = client.post('/billing/checkout')

        assert response.status_code == 302
        assert 'checkout.stripe.com' in response.location

    @patch('app.services.subscription_service.SubscriptionService.create_checkout_session')
    def test_checkout_error_redirects_to_pricing(self, mock_checkout, client, app, manager_user):
        """Checkout POST with error redirects to pricing with flash."""
        mock_checkout.side_effect = Exception('Stripe error')

        self._login(client)
        response = client.post('/billing/checkout', follow_redirects=True)

        assert response.status_code == 200

    def test_portal_requires_auth(self, client):
        """Portal POST redirects to login when not authenticated."""
        response = client.post('/billing/portal')
        assert response.status_code == 302
        assert '/auth/login' in response.location

    @patch('app.services.subscription_service.SubscriptionService.create_portal_session')
    def test_portal_redirects_to_stripe(self, mock_portal, client, app, manager_user):
        """Portal POST redirects to Stripe billing portal URL."""
        mock_portal.return_value = 'https://billing.stripe.com/p/test_portal'

        self._login(client)
        response = client.post('/billing/portal')

        assert response.status_code == 302
        assert 'billing.stripe.com' in response.location

    def test_success_page_requires_auth(self, client):
        """Success page redirects to login when not authenticated."""
        response = client.get('/billing/success')
        assert response.status_code == 302
        assert '/auth/login' in response.location

    def test_success_page_authenticated(self, client, app, manager_user):
        """Success page accessible when authenticated."""
        self._login(client)
        response = client.get('/billing/success?session_id=cs_test_123')
        assert response.status_code == 200
        assert b'Pro' in response.data


# =============================================================================
# Webhook Tests
# =============================================================================

class TestWebhookRoute:
    """Tests for Stripe webhook endpoint."""

    @patch('app.services.subscription_service.SubscriptionService.handle_webhook_event')
    def test_webhook_valid_signature(self, mock_handle, client, app):
        """Webhook returns 200 for valid event."""
        mock_handle.return_value = {'event_type': 'checkout.session.completed', 'handled': True}

        response = client.post(
            '/billing/webhook',
            data=b'{}',
            headers={'Stripe-Signature': 'test_sig'},
            content_type='application/json',
        )

        assert response.status_code == 200

    @patch('app.services.subscription_service.SubscriptionService.handle_webhook_event')
    def test_webhook_invalid_signature(self, mock_handle, client, app):
        """Webhook returns 400 for invalid signature."""
        mock_handle.side_effect = ValueError('Invalid webhook signature')

        response = client.post(
            '/billing/webhook',
            data=b'{}',
            headers={'Stripe-Signature': 'bad_sig'},
            content_type='application/json',
        )

        assert response.status_code == 400

    @patch('app.services.subscription_service.SubscriptionService.handle_webhook_event')
    def test_webhook_processing_error_returns_200(self, mock_handle, client, app):
        """Webhook returns 200 even on processing errors (prevent Stripe retries)."""
        mock_handle.side_effect = Exception('DB error')

        response = client.post(
            '/billing/webhook',
            data=b'{}',
            headers={'Stripe-Signature': 'test_sig'},
            content_type='application/json',
        )

        assert response.status_code == 200

    def test_webhook_no_csrf_required(self, client, app):
        """Webhook is CSRF-exempt (Stripe cannot send CSRF token)."""
        # If CSRF were required, this would return 400
        with patch('app.services.subscription_service.SubscriptionService.handle_webhook_event') as mock_handle:
            mock_handle.return_value = {'event_type': 'test', 'handled': False}

            response = client.post(
                '/billing/webhook',
                data=b'{}',
                headers={'Stripe-Signature': 'test_sig'},
                content_type='application/json',
            )

            # Should NOT get CSRF error (400)
            assert response.status_code == 200


# =============================================================================
# Webhook Handler Integration Tests
# =============================================================================

class TestWebhookHandlers:
    """Tests for webhook event handler methods."""

    @patch('stripe.Webhook.construct_event')
    def test_handle_checkout_completed(self, mock_construct, app, manager_user):
        """checkout.session.completed activates Pro plan."""
        SubscriptionService.ensure_subscription_exists(manager_user)

        mock_event = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'metadata': {'user_id': str(manager_user.id)},
                    'subscription': 'sub_webhook_test',
                    'customer': 'cus_webhook_test',
                }
            }
        }
        mock_construct.return_value = mock_event

        result = SubscriptionService.handle_webhook_event(b'payload', 'sig_header')

        assert result['handled'] is True
        db.session.expire(manager_user)
        assert manager_user.current_plan == 'pro'

    @patch('stripe.Webhook.construct_event')
    def test_handle_subscription_deleted(self, mock_construct, app, manager_user):
        """customer.subscription.deleted deactivates subscription."""
        SubscriptionService.activate_pro(
            user=manager_user,
            stripe_subscription_id='sub_to_delete',
            stripe_customer_id='cus_test',
        )

        mock_event = {
            'type': 'customer.subscription.deleted',
            'data': {
                'object': {
                    'id': 'sub_to_delete',
                }
            }
        }
        mock_construct.return_value = mock_event

        result = SubscriptionService.handle_webhook_event(b'payload', 'sig_header')

        assert result['handled'] is True
        db.session.expire(manager_user)
        assert manager_user.current_plan == 'free'

    @patch('stripe.Webhook.construct_event')
    def test_handle_payment_failed(self, mock_construct, app, manager_user):
        """invoice.payment_failed marks subscription as past_due."""
        SubscriptionService.activate_pro(
            user=manager_user,
            stripe_subscription_id='sub_payment_fail',
            stripe_customer_id='cus_test',
        )

        mock_event = {
            'type': 'invoice.payment_failed',
            'data': {
                'object': {
                    'subscription': 'sub_payment_fail',
                }
            }
        }
        mock_construct.return_value = mock_event

        result = SubscriptionService.handle_webhook_event(b'payload', 'sig_header')

        assert result['handled'] is True
        assert manager_user.subscription.status == SubscriptionStatus.PAST_DUE

    @patch('stripe.Webhook.construct_event')
    def test_handle_invalid_signature(self, mock_construct, app):
        """Invalid signature raises ValueError."""
        import stripe
        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            'Invalid', 'sig_header'
        )

        with pytest.raises(ValueError, match='Invalid webhook signature'):
            SubscriptionService.handle_webhook_event(b'payload', 'bad_sig')


# =============================================================================
# Decorator Integration Tests
# =============================================================================

class TestBillingDecorators:
    """Tests for billing decorator integration with routes.

    Uses actual client.post('/auth/login') for authentication.
    """

    def _login(self, client):
        """Log in as the manager user."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!',
        })

    def test_tour_creation_allowed_free_first(self, client, app, manager_user, sample_band):
        """Free user can access tour creation form (first tour)."""
        self._login(client)
        response = client.get('/tours/create')
        assert response.status_code == 200

    def test_tour_creation_blocked_free_second(self, client, app, manager_user, sample_band):
        """Free user is blocked from creating second tour."""
        SubscriptionService.ensure_subscription_exists(manager_user)

        # Create first tour
        tour = Tour(
            name='Existing Tour',
            start_date=datetime.utcnow().date(),
            end_date=datetime.utcnow().date() + timedelta(days=10),
            band=sample_band,
        )
        db.session.add(tour)
        db.session.commit()

        self._login(client)
        response = client.get('/tours/create')
        # Should redirect to pricing
        assert response.status_code == 302
        assert '/billing/pricing' in response.location
