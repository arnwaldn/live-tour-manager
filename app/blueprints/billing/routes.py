"""
Billing routes - Stripe SaaS subscription management.
6 routes: pricing (public), dashboard, checkout, portal, webhook, success.
"""
from flask import (
    render_template, redirect, url_for, flash, request,
    current_app, abort
)
from flask_login import login_required, current_user

from app.blueprints.billing import billing_bp
from app.extensions import csrf, limiter
from app.services.subscription_service import SubscriptionService


@billing_bp.route('/pricing')
def pricing():
    """Public pricing page — Free vs Pro comparison."""
    return render_template('billing/pricing.html')


@billing_bp.route('/dashboard')
@login_required
def dashboard():
    """Subscription dashboard — current plan, usage, management."""
    from app.models.tour import Tour
    from app.models.tour_stop import TourStop
    from app.models.band import Band
    from app.blueprints.billing.plans import get_plan_limits

    SubscriptionService.ensure_subscription_exists(current_user)

    plan = current_user.current_plan
    limits = get_plan_limits(plan)

    # Usage stats — tours managed by this user (via band.manager_id)
    tour_count = Tour.query.join(Band).filter(Band.manager_id == current_user.id).count()

    # For stop count, show the tour with the most stops
    max_stops = 0
    tours = Tour.query.join(Band).filter(Band.manager_id == current_user.id).all()
    for tour in tours:
        stop_count = TourStop.query.filter_by(tour_id=tour.id).count()
        if stop_count > max_stops:
            max_stops = stop_count

    return render_template(
        'billing/dashboard.html',
        plan=plan,
        limits=limits,
        tour_count=tour_count,
        max_stops=max_stops,
        subscription=current_user.subscription,
    )


@billing_bp.route('/checkout', methods=['POST'])
@login_required
@limiter.limit('5 per hour')
def checkout():
    """Create Stripe Checkout Session and redirect to Stripe."""
    try:
        checkout_url = SubscriptionService.create_checkout_session(current_user)
        return redirect(checkout_url)
    except Exception as e:
        current_app.logger.error(f'Checkout session creation failed: {e}')
        flash('Erreur lors de la creation de la session de paiement. Veuillez reessayer.', 'danger')
        return redirect(url_for('billing.pricing'))


@billing_bp.route('/portal', methods=['POST'])
@login_required
@limiter.limit('10 per hour')
def portal():
    """Create Stripe Billing Portal session and redirect."""
    try:
        portal_url = SubscriptionService.create_portal_session(current_user)
        return redirect(portal_url)
    except Exception as e:
        current_app.logger.error(f'Portal session creation failed: {e}')
        flash('Erreur lors de l\'acces au portail de facturation.', 'danger')
        return redirect(url_for('billing.dashboard'))


@billing_bp.route('/webhook', methods=['POST'])
@csrf.exempt
@limiter.limit('100 per minute')
def webhook():
    """Handle Stripe webhook events.

    CSRF exempt — verified via Stripe signature instead.
    Returns 200 quickly to avoid Stripe retries.
    """
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature', '')

    try:
        result = SubscriptionService.handle_webhook_event(payload, sig_header)
        current_app.logger.info(f'Webhook processed: {result["event_type"]} (handled={result["handled"]})')
        return '', 200
    except ValueError as e:
        current_app.logger.warning(f'Webhook signature verification failed: {e}')
        abort(400)
    except Exception as e:
        current_app.logger.error(f'Webhook processing error: {e}')
        return '', 200  # Return 200 to prevent Stripe retries on app errors


@billing_bp.route('/success')
@login_required
def success():
    """Post-checkout success page."""
    session_id = request.args.get('session_id')
    return render_template('billing/success.html', session_id=session_id)
