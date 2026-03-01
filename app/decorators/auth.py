"""
Authentication and authorization decorators.
Includes both legacy role-based and new access-level-based decorators.
"""
from functools import wraps
from flask import abort, flash, redirect, url_for, request
from flask_login import current_user, login_required

from app.models.user import AccessLevel
from app.utils.org_context import get_current_org_id


def _verify_org_owns_band(band):
    """Verify a band belongs to the user's current org. Abort 404 if not.

    Superadmins bypass this check.
    """
    current_org = get_current_org_id()
    if current_org and band and band.org_id and band.org_id != current_org:
        if not getattr(current_user, 'is_superadmin', False):
            abort(404)


# ============================================================
# ACCESS LEVEL DECORATORS (v2.0)
# ============================================================

def requires_access(required_level):
    """
    Decorator to require minimum access level for a view.
    Uses hierarchy: ADMIN > MANAGER > STAFF > VIEWER > EXTERNAL

    Usage:
        @requires_access(AccessLevel.MANAGER)
        def manager_view():
            ...
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.has_access(required_level):
                flash('Vous n\'avez pas les permissions nécessaires pour accéder à cette page.', 'error')
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def requires_admin(f):
    """
    Decorator to require ADMIN access level.

    Usage:
        @requires_admin
        def admin_only_view():
            ...
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash('Accès réservé aux administrateurs.', 'error')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def requires_manager(f):
    """
    Decorator to require MANAGER or higher access level.

    Usage:
        @requires_manager
        def manager_view():
            ...
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_manager_or_above():
            flash('Accès réservé aux managers.', 'error')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def requires_staff(f):
    """
    Decorator to require STAFF or higher access level.

    Usage:
        @requires_staff
        def staff_view():
            ...
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_staff_or_above():
            flash('Accès réservé au staff.', 'error')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# LEGACY ROLE DECORATORS (deprecated, kept for compatibility)
# ============================================================

def role_required(*role_names):
    """
    Decorator to require specific role(s) for a view.

    Usage:
        @role_required('MANAGER')
        def admin_view():
            ...

        @role_required('MANAGER', 'GUESTLIST_MANAGER')
        def guestlist_view():
            ...
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.has_any_role(role_names):
                flash('Vous n\'avez pas les permissions nécessaires pour accéder à cette page.', 'error')
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def permission_required(permission):
    """
    Decorator to require a specific permission for a view.

    Usage:
        @permission_required('manage_guestlist')
        def guestlist_management():
            ...
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.has_permission(permission):
                flash('Vous n\'avez pas les permissions nécessaires pour effectuer cette action.', 'error')
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def band_access_required(f):
    """
    Decorator to verify user has access to the band.
    Expects 'band_id' or 'id' in route parameters.
    Also verifies the band belongs to the user's current organization.

    Usage:
        @band_access_required
        def band_detail(band_id):
            ...
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        from app.models.band import Band
        from app.utils.org_context import get_current_org_id

        band_id = kwargs.get('band_id') or kwargs.get('id')
        if not band_id:
            abort(400)

        band = Band.query.get_or_404(band_id)

        # Verify band belongs to user's current org (tenant isolation)
        current_org = get_current_org_id()
        if current_org and band.org_id and band.org_id != current_org:
            # Superadmins can bypass org check
            if not getattr(current_user, 'is_superadmin', False):
                abort(404)  # 404 not 403 — don't leak existence

        # Allow access if user is admin, manager, member, or has manage_band permission
        if not (band.has_access(current_user) or
                current_user.has_permission('manage_band') or
                current_user.is_admin()):
            flash('Vous n\'avez pas accès à ce groupe.', 'error')
            abort(403)

        # Add band to kwargs for convenience
        kwargs['band'] = band
        return f(*args, **kwargs)
    return decorated_function


def tour_access_required(f):
    """
    Decorator to verify user has access to the tour.
    Expects 'tour_id' or 'id' in route parameters.
    Also verifies the tour's band belongs to the user's current organization.

    Usage:
        @tour_access_required
        def tour_detail(tour_id):
            ...
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        from app.models.tour import Tour

        tour_id = kwargs.get('tour_id') or kwargs.get('id')
        if not tour_id:
            abort(400)

        tour = Tour.query.get_or_404(tour_id)

        # Verify tour's band belongs to user's current org (tenant isolation)
        _verify_org_owns_band(tour.band)

        # Check if user can view this tour
        if not tour.can_view(current_user):
            flash('Vous n\'avez pas accès à cette tournée.', 'error')
            abort(403)

        # Add tour to kwargs for convenience
        kwargs['tour'] = tour
        return f(*args, **kwargs)
    return decorated_function


def tour_edit_required(f):
    """
    Decorator to verify user can edit the tour.
    Expects 'tour_id' or 'id' in route parameters.
    Also verifies the tour's band belongs to the user's current organization.

    Usage:
        @tour_edit_required
        def tour_edit(tour_id):
            ...
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        from app.models.tour import Tour

        tour_id = kwargs.get('tour_id') or kwargs.get('id')
        if not tour_id:
            abort(400)

        tour = Tour.query.get_or_404(tour_id)

        # Verify tour's band belongs to user's current org (tenant isolation)
        _verify_org_owns_band(tour.band)

        # Check if user can edit this tour
        if not tour.can_edit(current_user):
            flash('Vous n\'avez pas la permission de modifier cette tournée.', 'error')
            abort(403)

        kwargs['tour'] = tour
        return f(*args, **kwargs)
    return decorated_function


def tour_stop_access_required(f):
    """
    Decorator to verify user has access to the tour stop.
    Expects 'stop_id' in route parameters.
    Also verifies the stop's band belongs to the user's current organization.

    Usage:
        @tour_stop_access_required
        def stop_detail(stop_id):
            ...
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        from app.models.tour_stop import TourStop

        stop_id = kwargs.get('stop_id')
        if not stop_id:
            abort(400)

        tour_stop = TourStop.query.get_or_404(stop_id)

        # Verify stop's band belongs to user's current org (tenant isolation)
        band = tour_stop.band if tour_stop.band else (tour_stop.tour.band if tour_stop.tour else None)
        _verify_org_owns_band(band)

        # Check if user can view this tour stop
        if not tour_stop.can_view(current_user):
            flash('Vous n\'avez pas accès à cette date de concert.', 'error')
            abort(403)

        kwargs['tour_stop'] = tour_stop
        return f(*args, **kwargs)
    return decorated_function


def guestlist_manage_required(f):
    """
    Decorator to verify user can manage guestlist for a tour stop.
    Expects 'stop_id' in route parameters.

    Usage:
        @guestlist_manage_required
        def guestlist_manage(stop_id):
            ...
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        from app.models.tour_stop import TourStop

        stop_id = kwargs.get('stop_id')
        if not stop_id:
            abort(400)

        tour_stop = TourStop.query.get_or_404(stop_id)

        # Verify stop's band belongs to user's current org (tenant isolation)
        band = tour_stop.band if tour_stop.band else (tour_stop.tour.band if tour_stop.tour else None)
        _verify_org_owns_band(band)

        # Check if user can manage guestlist
        if not tour_stop.can_manage_guestlist(current_user):
            flash('Vous n\'avez pas la permission de gérer la guestlist.', 'error')
            abort(403)

        kwargs['tour_stop'] = tour_stop
        return f(*args, **kwargs)
    return decorated_function


def check_in_required(f):
    """
    Decorator to verify user can check in guests at a tour stop.
    Expects 'stop_id' in route parameters.

    Usage:
        @check_in_required
        def check_in_guest(stop_id, entry_id):
            ...
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        from app.models.tour_stop import TourStop

        stop_id = kwargs.get('stop_id')
        if not stop_id:
            abort(400)

        tour_stop = TourStop.query.get_or_404(stop_id)

        # Verify stop's band belongs to user's current org (tenant isolation)
        band = tour_stop.band if tour_stop.band else (tour_stop.tour.band if tour_stop.tour else None)
        _verify_org_owns_band(band)

        # Check if user can check in guests
        if not tour_stop.can_check_in_guests(current_user):
            flash('Vous n\'avez pas la permission de faire le check-in.', 'error')
            abort(403)

        kwargs['tour_stop'] = tour_stop
        return f(*args, **kwargs)
    return decorated_function


def ajax_login_required(f):
    """
    Decorator for AJAX endpoints that returns JSON on auth failure.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return {'error': 'Authentication required'}, 401
        return f(*args, **kwargs)
    return decorated_function
