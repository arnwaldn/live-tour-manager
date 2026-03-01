"""
API v1 Routes — REST endpoints for tours, stops, guestlist, schedule, payments, notifications.
"""
from datetime import datetime, date

from flask import request, jsonify
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from app.blueprints.api import api_bp
from app.blueprints.api.decorators import jwt_required, requires_api_access
from app.blueprints.api.schemas import (
    TourSchema, TourStopSchema, GuestlistEntrySchema,
    NotificationSchema, PaymentSchema, BandSchema, VenueSchema,
    TourStopMinimalSchema,
)
from app.blueprints.api.helpers import paginate_query, api_error, api_success
from app.extensions import db, limiter
from app.utils.org_context import get_current_org_id
from app.models.user import AccessLevel
from app.models.tour import Tour
from app.models.tour_stop import TourStop, TourStopMember
from app.models.guestlist import GuestlistEntry, GuestlistStatus
from app.models.notification import Notification
from app.models.payments import TeamMemberPayment
from app.models.band import Band, BandMembership
from app.models.venue import Venue


# ── Tours ───────────────────────────────────────────────────

@api_bp.route('/tours', methods=['GET'])
@jwt_required
def api_list_tours():
    """List tours accessible to the current user.

    Query params:
        status (str): Filter by tour status (draft, planning, confirmed, active, completed, cancelled)
        band_id (int): Filter by band
        page, per_page: Pagination
    """
    user = request.api_user
    query = Tour.query.options(joinedload(Tour.band))

    # Org-scoped: only tours from bands in user's org
    org_id = get_current_org_id()
    if org_id:
        query = query.join(Band).filter(Band.org_id == org_id)

    # Object-level authorization: non-staff see only their bands' tours
    if not user.is_staff_or_above():
        accessible_band_ids = db.session.query(BandMembership.band_id).filter(
            BandMembership.user_id == user.id
        ).union(
            db.session.query(Band.id).filter(Band.manager_id == user.id)
        )
        query = query.filter(Tour.band_id.in_(accessible_band_ids))

    # Filters
    status = request.args.get('status')
    if status:
        from app.models.tour import TourStatus
        try:
            query = query.filter(Tour.status == TourStatus(status))
        except ValueError:
            return api_error('invalid_filter', f'Invalid status: {status}', 422)

    band_id = request.args.get('band_id', type=int)
    if band_id:
        query = query.filter(Tour.band_id == band_id)

    # Sort by start_date descending (most recent first)
    query = query.order_by(desc(Tour.start_date))

    return jsonify(paginate_query(query, TourSchema())), 200


@api_bp.route('/tours/<int:tour_id>', methods=['GET'])
@jwt_required
def api_get_tour(tour_id):
    """Get a single tour by ID."""
    tour = Tour.query.options(joinedload(Tour.band)).get(tour_id)
    if not tour or not tour.can_view(request.api_user):
        return api_error('not_found', 'Tour not found.', 404)

    return api_success(TourSchema().dump(tour))


# ── Tour Stops ──────────────────────────────────────────────

@api_bp.route('/tours/<int:tour_id>/stops', methods=['GET'])
@jwt_required
def api_list_tour_stops(tour_id):
    """List all stops for a given tour.

    Query params:
        status (str): Filter by stop status
        page, per_page: Pagination
    """
    tour = Tour.query.get(tour_id)
    if not tour or not tour.can_view(request.api_user):
        return api_error('not_found', 'Tour not found.', 404)

    query = TourStop.query.options(
        joinedload(TourStop.venue),
        joinedload(TourStop.band),
        joinedload(TourStop.tour),
    ).filter(TourStop.tour_id == tour_id)

    status = request.args.get('status')
    if status:
        from app.models.tour_stop import TourStopStatus
        try:
            query = query.filter(TourStop.status == TourStopStatus(status))
        except ValueError:
            return api_error('invalid_filter', f'Invalid status: {status}', 422)

    query = query.order_by(TourStop.date)

    return jsonify(paginate_query(query, TourStopSchema())), 200


@api_bp.route('/stops/<int:stop_id>', methods=['GET'])
@jwt_required
def api_get_stop(stop_id):
    """Get a single tour stop with full details."""
    stop = TourStop.query.options(
        joinedload(TourStop.venue),
        joinedload(TourStop.band),
        joinedload(TourStop.tour),
    ).get(stop_id)

    if not stop or not stop.tour.can_view(request.api_user):
        return api_error('not_found', 'Tour stop not found.', 404)

    return api_success(TourStopSchema().dump(stop))


# ── Guestlist ───────────────────────────────────────────────

@api_bp.route('/stops/<int:stop_id>/guestlist', methods=['GET'])
@jwt_required
def api_list_guestlist(stop_id):
    """List guestlist entries for a tour stop.

    Query params:
        status (str): Filter by entry status (pending, approved, denied, checked_in, no_show)
        q (str): Search by guest name
        page, per_page: Pagination
    """
    stop = TourStop.query.options(joinedload(TourStop.tour)).get(stop_id)
    if not stop or not stop.tour.can_view(request.api_user):
        return api_error('not_found', 'Tour stop not found.', 404)

    query = GuestlistEntry.query.filter(
        GuestlistEntry.tour_stop_id == stop_id
    )

    status = request.args.get('status')
    if status:
        try:
            query = query.filter(GuestlistEntry.status == GuestlistStatus(status))
        except ValueError:
            return api_error('invalid_filter', f'Invalid status: {status}', 422)

    search = request.args.get('q', '').strip()
    if search:
        query = query.filter(GuestlistEntry.guest_name.ilike(f'%{search}%'))

    query = query.order_by(desc(GuestlistEntry.created_at))

    return jsonify(paginate_query(query, GuestlistEntrySchema())), 200


@api_bp.route('/guestlist/<int:entry_id>/checkin', methods=['POST'])
@jwt_required
def api_checkin_guest(entry_id):
    """Check in a guestlist entry.

    Only approved entries can be checked in.
    """
    entry = GuestlistEntry.query.options(
        joinedload(GuestlistEntry.tour_stop).joinedload(TourStop.tour)
    ).get(entry_id)
    if not entry or not entry.tour_stop.tour.can_view(request.api_user):
        return api_error('not_found', 'Guestlist entry not found.', 404)

    if entry.status != GuestlistStatus.APPROVED:
        return api_error(
            'invalid_state',
            f'Cannot check in entry with status "{entry.status.value}". Must be "approved".',
            409,
        )

    entry.status = GuestlistStatus.CHECKED_IN
    entry.checked_in_at = datetime.utcnow()
    entry.checked_in_by_id = request.api_user.id
    db.session.commit()

    return api_success(GuestlistEntrySchema().dump(entry))


# ── My Schedule ─────────────────────────────────────────────

@api_bp.route('/me/schedule', methods=['GET'])
@jwt_required
def api_my_schedule():
    """Get current user's upcoming schedule (assigned tour stops).

    Query params:
        from_date (str): Start date filter (YYYY-MM-DD, default: today)
        to_date (str): End date filter (YYYY-MM-DD)
        page, per_page: Pagination
    """
    user = request.api_user

    query = TourStop.query.join(
        TourStopMember, TourStopMember.tour_stop_id == TourStop.id
    ).filter(
        TourStopMember.user_id == user.id,
    ).options(
        joinedload(TourStop.venue),
        joinedload(TourStop.band),
        joinedload(TourStop.tour),
    )

    # Date filters
    from_date_str = request.args.get('from_date')
    if from_date_str:
        try:
            from_date = date.fromisoformat(from_date_str)
        except ValueError:
            return api_error('invalid_filter', 'from_date must be YYYY-MM-DD.', 422)
    else:
        from_date = date.today()

    query = query.filter(TourStop.date >= from_date)

    to_date_str = request.args.get('to_date')
    if to_date_str:
        try:
            to_date = date.fromisoformat(to_date_str)
            query = query.filter(TourStop.date <= to_date)
        except ValueError:
            return api_error('invalid_filter', 'to_date must be YYYY-MM-DD.', 422)

    query = query.order_by(TourStop.date)

    return jsonify(paginate_query(query, TourStopSchema())), 200


# ── My Payments ─────────────────────────────────────────────

@api_bp.route('/me/payments', methods=['GET'])
@jwt_required
def api_my_payments():
    """Get current user's payments.

    Query params:
        status (str): Filter by payment status
        page, per_page: Pagination
    """
    user = request.api_user

    query = TeamMemberPayment.query.filter(
        TeamMemberPayment.user_id == user.id
    ).order_by(desc(TeamMemberPayment.created_at))

    status = request.args.get('status')
    if status:
        try:
            from app.models.payments import PaymentStatus
            query = query.filter(TeamMemberPayment.status == PaymentStatus(status))
        except (ValueError, AttributeError):
            return api_error('invalid_filter', f'Invalid status: {status}', 422)

    return jsonify(paginate_query(query, PaymentSchema())), 200


# ── Notifications ───────────────────────────────────────────

@api_bp.route('/notifications', methods=['GET'])
@jwt_required
def api_list_notifications():
    """Get current user's notifications.

    Query params:
        unread (bool): Filter unread only (unread=true)
        page, per_page: Pagination
    """
    user = request.api_user

    query = Notification.query.filter(
        Notification.user_id == user.id
    ).order_by(desc(Notification.created_at))

    unread = request.args.get('unread', '').lower()
    if unread == 'true':
        query = query.filter(Notification.is_read == False)

    return jsonify(paginate_query(query, NotificationSchema())), 200


@api_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@jwt_required
def api_mark_notification_read(notif_id):
    """Mark a notification as read."""
    notif = Notification.query.filter_by(
        id=notif_id,
        user_id=request.api_user.id,
    ).first()

    if not notif:
        return api_error('not_found', 'Notification not found.', 404)

    notif.is_read = True
    db.session.commit()

    return api_success(NotificationSchema().dump(notif))


@api_bp.route('/notifications/read-all', methods=['POST'])
@jwt_required
def api_mark_all_notifications_read():
    """Mark all notifications as read for current user."""
    count = Notification.query.filter_by(
        user_id=request.api_user.id,
        is_read=False,
    ).update({'is_read': True})
    db.session.commit()

    return api_success({'marked_read': count})


# ── Bands ───────────────────────────────────────────────────

@api_bp.route('/bands', methods=['GET'])
@jwt_required
def api_list_bands():
    """List bands.

    Query params:
        q (str): Search by band name
        page, per_page: Pagination
    """
    user = request.api_user
    query = Band.query.options(joinedload(Band.manager))

    # Org-scoped: only bands in user's org
    org_id = get_current_org_id()
    if org_id:
        query = query.filter(Band.org_id == org_id)

    # Object-level authorization: non-staff see only their bands
    if not user.is_staff_or_above():
        managed = db.session.query(Band.id).filter(Band.manager_id == user.id)
        member_of = db.session.query(BandMembership.band_id).filter(
            BandMembership.user_id == user.id
        )
        query = query.filter(Band.id.in_(managed.union(member_of)))

    search = request.args.get('q', '').strip()
    if search:
        query = query.filter(Band.name.ilike(f'%{search}%'))

    query = query.order_by(Band.name)

    return jsonify(paginate_query(query, BandSchema())), 200


# ── Venues ──────────────────────────────────────────────────

@api_bp.route('/venues', methods=['GET'])
@jwt_required
def api_list_venues():
    """List venues.

    Query params:
        q (str): Search by venue name or city
        city (str): Filter by city
        country (str): Filter by country
        page, per_page: Pagination
    """
    # Org-scoped venue list (get_current_org_id may return None for API/JWT auth — Phase 2)
    org_id = get_current_org_id()
    query = Venue.query.filter_by(org_id=org_id) if org_id else Venue.query

    search = request.args.get('q', '').strip()
    if search:
        query = query.filter(
            db.or_(
                Venue.name.ilike(f'%{search}%'),
                Venue.city.ilike(f'%{search}%'),
            )
        )

    city = request.args.get('city', '').strip()
    if city:
        query = query.filter(Venue.city.ilike(f'%{city}%'))

    country = request.args.get('country', '').strip()
    if country:
        query = query.filter(Venue.country.ilike(f'%{country}%'))

    query = query.order_by(Venue.name)

    return jsonify(paginate_query(query, VenueSchema())), 200
