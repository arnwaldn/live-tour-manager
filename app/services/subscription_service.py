"""
Subscription service for GigRoute SaaS billing.
Handles Stripe integration, plan limits, and subscription lifecycle.
"""
from datetime import datetime
from typing import Optional

import stripe
from flask import current_app

from app.extensions import db
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.user import User
from app.models.tour import Tour
from app.models.tour_stop import TourStop
from app.models.band import Band


class PlanLimitExceeded(Exception):
    """Raised when a user exceeds their plan limits."""

    def __init__(self, limit_name: str, current: int, maximum: int):
        self.limit_name = limit_name
        self.current = current
        self.maximum = maximum
        super().__init__(
            f"Limite du plan atteinte : {limit_name} ({current}/{maximum})"
        )


class SubscriptionService:
    """Service for managing user subscriptions and Stripe billing."""

    @staticmethod
    def ensure_subscription_exists(user: User) -> Subscription:
        """Ensure user has a Subscription record. Creates FREE if none exists.

        Args:
            user: User to check

        Returns:
            Existing or newly created Subscription
        """
        if user.subscription:
            return user.subscription

        subscription = Subscription(
            user_id=user.id,
            plan=SubscriptionPlan.FREE,
            status=SubscriptionStatus.ACTIVE,
        )
        db.session.add(subscription)
        db.session.commit()
        return subscription

    @staticmethod
    def get_or_create_stripe_customer(user: User) -> str:
        """Get or create a Stripe customer for the user.

        Args:
            user: User to get/create customer for

        Returns:
            Stripe customer ID
        """
        if user.stripe_customer_id:
            return user.stripe_customer_id

        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name,
            metadata={'user_id': str(user.id)},
        )

        user.stripe_customer_id = customer.id
        # Also store on subscription if it exists
        if user.subscription:
            user.subscription.stripe_customer_id = customer.id
        db.session.commit()

        return customer.id

    @staticmethod
    def create_checkout_session(user: User) -> str:
        """Create a Stripe Checkout Session for upgrading to Pro.

        Args:
            user: User requesting upgrade

        Returns:
            Checkout session URL to redirect to
        """
        customer_id = SubscriptionService.get_or_create_stripe_customer(user)
        app_url = current_app.config['APP_URL']

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': current_app.config['STRIPE_PRO_PRICE_ID'],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f'{app_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{app_url}/billing/pricing',
            metadata={'user_id': str(user.id)},
        )

        return session.url

    @staticmethod
    def create_portal_session(user: User) -> str:
        """Create a Stripe Billing Portal session.

        Args:
            user: User requesting portal access

        Returns:
            Portal session URL to redirect to
        """
        customer_id = SubscriptionService.get_or_create_stripe_customer(user)
        app_url = current_app.config['APP_URL']

        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f'{app_url}/billing/dashboard',
        )

        return session.url

    @staticmethod
    def activate_pro(
        user: User,
        stripe_subscription_id: str,
        stripe_customer_id: str,
        current_period_end: Optional[datetime] = None,
    ) -> Subscription:
        """Activate Pro plan for a user after successful checkout.

        Args:
            user: User to upgrade
            stripe_subscription_id: Stripe subscription ID
            stripe_customer_id: Stripe customer ID
            current_period_end: Subscription period end datetime

        Returns:
            Updated Subscription
        """
        subscription = SubscriptionService.ensure_subscription_exists(user)
        subscription.plan = SubscriptionPlan.PRO
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.stripe_subscription_id = stripe_subscription_id
        subscription.stripe_customer_id = stripe_customer_id
        subscription.cancel_at_period_end = False

        if current_period_end:
            subscription.current_period_end = current_period_end

        # Also update user's stripe_customer_id
        user.stripe_customer_id = stripe_customer_id

        db.session.commit()
        return subscription

    @staticmethod
    def cancel_subscription(user: User) -> Subscription:
        """Mark subscription as canceled (at period end).

        Args:
            user: User canceling

        Returns:
            Updated Subscription
        """
        subscription = SubscriptionService.ensure_subscription_exists(user)
        subscription.cancel_at_period_end = True
        db.session.commit()
        return subscription

    @staticmethod
    def deactivate_subscription(user: User) -> Subscription:
        """Fully deactivate subscription (revert to Free).

        Called by webhook when subscription actually ends.

        Args:
            user: User whose subscription ended

        Returns:
            Updated Subscription
        """
        subscription = SubscriptionService.ensure_subscription_exists(user)
        subscription.plan = SubscriptionPlan.FREE
        subscription.status = SubscriptionStatus.CANCELED
        subscription.stripe_subscription_id = None
        subscription.current_period_end = None
        subscription.cancel_at_period_end = False
        db.session.commit()
        return subscription

    @staticmethod
    def handle_webhook_event(payload: bytes, sig_header: str) -> dict:
        """Handle incoming Stripe webhook event.

        Args:
            payload: Raw request body
            sig_header: Stripe-Signature header value

        Returns:
            Dict with event type and processing result

        Raises:
            ValueError: If signature verification fails
        """
        webhook_secret = current_app.config['STRIPE_WEBHOOK_SECRET']

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except stripe.error.SignatureVerificationError:
            raise ValueError("Invalid webhook signature")

        event_type = event['type']
        data = event['data']['object']
        result = {'event_type': event_type, 'handled': False}

        if event_type == 'checkout.session.completed':
            SubscriptionService._handle_checkout_completed(data)
            result['handled'] = True

        elif event_type == 'customer.subscription.updated':
            SubscriptionService._handle_subscription_updated(data)
            result['handled'] = True

        elif event_type == 'customer.subscription.deleted':
            SubscriptionService._handle_subscription_deleted(data)
            result['handled'] = True

        elif event_type == 'invoice.payment_failed':
            SubscriptionService._handle_payment_failed(data)
            result['handled'] = True

        return result

    @staticmethod
    def _handle_checkout_completed(session_data: dict) -> None:
        """Process checkout.session.completed event."""
        user_id = session_data.get('metadata', {}).get('user_id')
        if not user_id:
            current_app.logger.warning('Checkout completed without user_id metadata')
            return

        user = User.query.get(int(user_id))
        if not user:
            current_app.logger.warning(f'Checkout completed for unknown user_id={user_id}')
            return

        subscription_id = session_data.get('subscription')
        customer_id = session_data.get('customer')

        if subscription_id and customer_id:
            SubscriptionService.activate_pro(
                user=user,
                stripe_subscription_id=subscription_id,
                stripe_customer_id=customer_id,
            )
            current_app.logger.info(f'Pro activated for user {user.email}')

    @staticmethod
    def _handle_subscription_updated(sub_data: dict) -> None:
        """Process customer.subscription.updated event."""
        stripe_sub_id = sub_data.get('id')
        subscription = Subscription.query.filter_by(
            stripe_subscription_id=stripe_sub_id
        ).first()

        if not subscription:
            return

        # Update period end
        period_end = sub_data.get('current_period_end')
        if period_end:
            subscription.current_period_end = datetime.utcfromtimestamp(period_end)

        # Update cancel_at_period_end
        subscription.cancel_at_period_end = sub_data.get('cancel_at_period_end', False)

        # Update status
        status_map = {
            'active': SubscriptionStatus.ACTIVE,
            'past_due': SubscriptionStatus.PAST_DUE,
            'canceled': SubscriptionStatus.CANCELED,
            'trialing': SubscriptionStatus.TRIALING,
            'incomplete': SubscriptionStatus.INCOMPLETE,
        }
        stripe_status = sub_data.get('status')
        if stripe_status in status_map:
            subscription.status = status_map[stripe_status]

        db.session.commit()

    @staticmethod
    def _handle_subscription_deleted(sub_data: dict) -> None:
        """Process customer.subscription.deleted event."""
        stripe_sub_id = sub_data.get('id')
        subscription = Subscription.query.filter_by(
            stripe_subscription_id=stripe_sub_id
        ).first()

        if not subscription:
            return

        user = subscription.user
        SubscriptionService.deactivate_subscription(user)
        current_app.logger.info(f'Subscription deactivated for user {user.email}')

    @staticmethod
    def _handle_payment_failed(invoice_data: dict) -> None:
        """Process invoice.payment_failed event."""
        stripe_sub_id = invoice_data.get('subscription')
        if not stripe_sub_id:
            return

        subscription = Subscription.query.filter_by(
            stripe_subscription_id=stripe_sub_id
        ).first()

        if subscription:
            subscription.status = SubscriptionStatus.PAST_DUE
            db.session.commit()
            current_app.logger.warning(
                f'Payment failed for user {subscription.user.email}'
            )

    @staticmethod
    def check_tour_limit(user: User) -> None:
        """Check if user can create another tour.

        Args:
            user: User attempting to create a tour

        Raises:
            PlanLimitExceeded: If limit reached
        """
        from app.blueprints.billing.plans import get_plan_limits

        plan = user.current_plan
        limits = get_plan_limits(plan)

        if limits.max_tours is None:
            return  # Unlimited

        current_count = Tour.query.join(Band).filter(Band.manager_id == user.id).count()
        if current_count >= limits.max_tours:
            raise PlanLimitExceeded('tournees', current_count, limits.max_tours)

    @staticmethod
    def check_stop_limit(user: User, tour_id: int) -> None:
        """Check if user can add another stop to a tour.

        Args:
            user: User attempting to add a stop
            tour_id: Tour to add stop to

        Raises:
            PlanLimitExceeded: If limit reached
        """
        from app.blueprints.billing.plans import get_plan_limits

        plan = user.current_plan
        limits = get_plan_limits(plan)

        if limits.max_stops_per_tour is None:
            return  # Unlimited

        current_count = TourStop.query.filter_by(tour_id=tour_id).count()
        if current_count >= limits.max_stops_per_tour:
            raise PlanLimitExceeded('dates par tournee', current_count, limits.max_stops_per_tour)
