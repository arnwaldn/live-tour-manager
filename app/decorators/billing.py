"""
Billing decorators for plan enforcement.
Apply to routes that need subscription plan checks.
"""
from functools import wraps

from flask import flash, redirect, url_for, request
from flask_login import current_user

from app.services.subscription_service import SubscriptionService, PlanLimitExceeded


def plan_required(plan_name):
    """Decorator: require a specific plan (e.g., 'pro') at the org level.

    Redirects to pricing page with flash message if org doesn't have the plan.
    Falls back to user plan for backward compatibility.

    Usage:
        @plan_required('pro')
        def export_pdf():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))

            SubscriptionService.ensure_subscription_exists(current_user)

            # current_plan already delegates to org subscription (see User model)
            if current_user.current_plan != plan_name:
                flash(
                    'Cette fonctionnalité nécessite le plan Pro. '
                    'Mettez à niveau pour y accéder.',
                    'warning'
                )
                return redirect(url_for('billing.pricing'))

            return f(*args, **kwargs)
        return decorated
    return decorator


def check_tour_limit(f):
    """Decorator: check if user can create another tour.

    Redirects back with flash message if limit exceeded.

    Usage:
        @check_tour_limit
        def create_tour():
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        SubscriptionService.ensure_subscription_exists(current_user)

        try:
            SubscriptionService.check_tour_limit(current_user)
        except PlanLimitExceeded as e:
            flash(
                f'Limite atteinte : {e.current}/{e.maximum} {e.limit_name}. '
                f'Passez au plan Pro pour creer des tournees illimitees.',
                'warning'
            )
            return redirect(url_for('billing.pricing'))

        return f(*args, **kwargs)
    return decorated


def check_stop_limit(f):
    """Decorator: check if user can add another stop to a tour.

    Expects 'id' (tour_id) in route kwargs.

    Usage:
        @check_stop_limit
        def add_stop(id):
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        SubscriptionService.ensure_subscription_exists(current_user)

        # Extract tour_id from route kwargs (commonly 'id' in tours blueprint)
        tour_id = kwargs.get('id') or kwargs.get('tour_id')
        if tour_id:
            try:
                SubscriptionService.check_stop_limit(current_user, tour_id)
            except PlanLimitExceeded as e:
                flash(
                    f'Limite atteinte : {e.current}/{e.maximum} {e.limit_name}. '
                    f'Passez au plan Pro pour ajouter des dates illimitees.',
                    'warning'
                )
                return redirect(url_for('billing.pricing'))

        return f(*args, **kwargs)
    return decorated
