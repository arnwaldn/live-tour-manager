"""
API v1 Routes — REST endpoints for tours, stops, guestlist, schedule, payments, notifications.
"""
from datetime import datetime, date

from flask import request, jsonify
from sqlalchemy import desc, func
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
from app.models.tour import Tour, TourStatus
from app.models.tour_stop import TourStop, TourStopMember
from app.models.guestlist import GuestlistEntry, GuestlistStatus
from app.models.notification import Notification
from app.models.payments import TeamMemberPayment
from app.models.band import Band, BandMembership
from app.models.venue import Venue
from app.models.guestlist import GuestlistEntry, GuestlistStatus, EntryType


# ── Dashboard ────────────────────────────────────────────────

@api_bp.route('/dashboard/stats', methods=['GET'])
@jwt_required
def api_dashboard_stats():
    """Dashboard KPIs for the current user.

    Returns:
        active_tours: number of tours with status active or confirmed
        next_show_date: ISO date of the nearest upcoming tour stop (or null)
        next_show_venue: venue name of the nearest upcoming tour stop (or null)
        unread_notifications: count of unread notifications
        shows_this_month: count of tour stops in the current calendar month
    """
    user = request.api_user
    org_id = get_current_org_id()
    today = date.today()

    # Base tour query scoped to user's org
    tour_query = Tour.query
    if org_id:
        tour_query = tour_query.join(Band).filter(Band.org_id == org_id)

    # Active tours (confirmed or active)
    active_tours = tour_query.filter(
        Tour.status.in_([TourStatus.CONFIRMED, TourStatus.ACTIVE])
    ).count()

    # Next upcoming show
    next_stop_query = TourStop.query.options(
        joinedload(TourStop.venue)
    ).join(Tour).filter(
        TourStop.date >= today,
    )
    if org_id:
        next_stop_query = next_stop_query.join(Band, Tour.band_id == Band.id).filter(
            Band.org_id == org_id
        )
    next_stop = next_stop_query.order_by(TourStop.date).first()

    next_show_date = next_stop.date.isoformat() if next_stop else None
    next_show_venue = None
    if next_stop and next_stop.venue:
        next_show_venue = next_stop.venue.name

    # Unread notifications
    unread_notifications = Notification.query.filter_by(
        user_id=user.id,
        is_read=False,
    ).count()

    # Shows this month
    first_of_month = today.replace(day=1)
    if today.month == 12:
        first_of_next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        first_of_next_month = today.replace(month=today.month + 1, day=1)

    shows_month_query = TourStop.query.join(Tour).filter(
        TourStop.date >= first_of_month,
        TourStop.date < first_of_next_month,
    )
    if org_id:
        shows_month_query = shows_month_query.join(
            Band, Tour.band_id == Band.id
        ).filter(Band.org_id == org_id)
    shows_this_month = shows_month_query.count()

    return api_success({
        'active_tours': active_tours,
        'next_show_date': next_show_date,
        'next_show_venue': next_show_venue,
        'unread_notifications': unread_notifications,
        'shows_this_month': shows_this_month,
    })


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


@api_bp.route('/tours', methods=['POST'])
@jwt_required
def api_create_tour():
    """Create a new tour.

    Required fields: name, start_date, end_date, band_id
    Optional fields: description, budget, currency, notes
    """
    data = request.get_json(silent=True) or {}
    user = request.api_user

    # Validate required fields
    errors = {}
    for field in ('name', 'start_date', 'end_date', 'band_id'):
        if not data.get(field):
            errors[field] = f'{field} is required.'
    if errors:
        return api_error('validation_error', 'Missing required fields.', 422, errors)

    # Validate band exists and user has access
    band = Band.query.get(data['band_id'])
    if not band:
        return api_error('not_found', 'Band not found.', 404)
    if not band.has_access(user) and not user.is_manager_or_above():
        return api_error('forbidden', 'No access to this band.', 403)

    # Parse dates
    try:
        start_date = date.fromisoformat(data['start_date'])
        end_date = date.fromisoformat(data['end_date'])
    except (ValueError, TypeError):
        return api_error('validation_error', 'Dates must be YYYY-MM-DD format.', 422)

    if end_date < start_date:
        return api_error('validation_error', 'end_date must be after start_date.', 422)

    tour = Tour(
        name=data['name'].strip(),
        description=data.get('description', '').strip() or None,
        start_date=start_date,
        end_date=end_date,
        band_id=band.id,
        budget=data.get('budget'),
        currency=data.get('currency', 'EUR'),
        notes=data.get('notes', '').strip() or None,
        status=TourStatus.DRAFT,
    )
    db.session.add(tour)
    db.session.commit()

    tour_id = tour.id
    db.session.expire_all()
    tour = Tour.query.options(joinedload(Tour.band)).get(tour_id)
    return api_success(TourSchema().dump(tour)), 201


@api_bp.route('/tours/<int:tour_id>', methods=['PUT'])
@jwt_required
def api_update_tour(tour_id):
    """Update an existing tour.

    Updatable fields: name, description, start_date, end_date, budget, currency, notes
    """
    tour = Tour.query.options(joinedload(Tour.band)).get(tour_id)
    if not tour:
        return api_error('not_found', 'Tour not found.', 404)
    if not tour.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to edit this tour.', 403)
    if not tour.is_editable:
        return api_error('invalid_state', f'Cannot edit tour in {tour.status.value} status.', 409)

    data = request.get_json(silent=True) or {}

    UPDATABLE = {'name', 'description', 'budget', 'currency', 'notes'}
    for field in UPDATABLE:
        if field in data:
            value = data[field]
            if isinstance(value, str):
                value = value.strip() or None
            setattr(tour, field, value)

    # Handle date updates
    if 'start_date' in data:
        try:
            tour.start_date = date.fromisoformat(data['start_date'])
        except (ValueError, TypeError):
            return api_error('validation_error', 'start_date must be YYYY-MM-DD.', 422)

    if 'end_date' in data:
        try:
            tour.end_date = date.fromisoformat(data['end_date'])
        except (ValueError, TypeError):
            return api_error('validation_error', 'end_date must be YYYY-MM-DD.', 422)

    if tour.end_date < tour.start_date:
        return api_error('validation_error', 'end_date must be after start_date.', 422)

    # Validate name is not empty
    if tour.name is None or (isinstance(tour.name, str) and not tour.name.strip()):
        return api_error('validation_error', 'name cannot be empty.', 422)

    db.session.commit()
    return api_success(TourSchema().dump(tour))


@api_bp.route('/tours/<int:tour_id>', methods=['DELETE'])
@jwt_required
def api_delete_tour(tour_id):
    """Delete a tour. Checks for deletion blockers (pending payments, active status)."""
    tour = Tour.query.options(joinedload(Tour.band)).get(tour_id)
    if not tour:
        return api_error('not_found', 'Tour not found.', 404)
    if not tour.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to delete this tour.', 403)

    blockers = tour.get_deletion_blockers()
    if blockers:
        return api_error(
            'deletion_blocked',
            f'Cannot delete tour: {", ".join(blockers)}.',
            409,
            {'blockers': blockers},
        )

    db.session.delete(tour)
    db.session.commit()
    return api_success({'deleted': True})


@api_bp.route('/tours/<int:tour_id>/status', methods=['POST'])
@jwt_required
def api_transition_tour_status(tour_id):
    """Transition tour status via state machine.

    Body: {"status": "planning"|"confirmed"|"active"|"completed"|"cancelled"}
    """
    tour = Tour.query.options(joinedload(Tour.band)).get(tour_id)
    if not tour:
        return api_error('not_found', 'Tour not found.', 404)
    if not tour.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to change tour status.', 403)

    data = request.get_json(silent=True) or {}
    target = data.get('status')
    if not target:
        return api_error('validation_error', 'status is required.', 422)

    try:
        target_status = TourStatus(target)
    except ValueError:
        return api_error('validation_error', f'Invalid status: {target}.', 422)

    try:
        tour.transition_to(target_status)
    except ValueError as e:
        return api_error('invalid_transition', str(e), 409)

    db.session.commit()
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


@api_bp.route('/tours/<int:tour_id>/stops', methods=['POST'])
@jwt_required
def api_create_stop(tour_id):
    """Create a new tour stop.

    Required fields: date
    Optional fields: venue_id, event_type, status, doors_time, soundcheck_time,
        set_time, load_in_time, curfew_time, guarantee, ticket_price, currency,
        notes, set_length_minutes, age_restriction, location_address, location_city,
        location_country
    """
    tour = Tour.query.options(joinedload(Tour.band)).get(tour_id)
    if not tour:
        return api_error('not_found', 'Tour not found.', 404)
    if not tour.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to add stops to this tour.', 403)

    data = request.get_json(silent=True) or {}

    if not data.get('date'):
        return api_error('validation_error', 'date is required.', 422)

    try:
        stop_date = date.fromisoformat(data['date'])
    except (ValueError, TypeError):
        return api_error('validation_error', 'date must be YYYY-MM-DD format.', 422)

    # Validate venue if provided
    venue_id = data.get('venue_id')
    if venue_id:
        venue = Venue.query.get(venue_id)
        if not venue:
            return api_error('not_found', 'Venue not found.', 404)

    # Parse event_type
    from app.models.tour_stop import EventType, TourStopStatus
    event_type = EventType.SHOW
    if data.get('event_type'):
        try:
            event_type = EventType(data['event_type'])
        except ValueError:
            return api_error('validation_error', f"Invalid event_type: {data['event_type']}.", 422)

    # Parse status
    stop_status = TourStopStatus.DRAFT
    if data.get('status'):
        try:
            stop_status = TourStopStatus(data['status'])
        except ValueError:
            return api_error('validation_error', f"Invalid status: {data['status']}.", 422)

    # Parse time fields
    def parse_time(value):
        if not value:
            return None
        from datetime import time as dt_time
        try:
            parts = value.split(':')
            return dt_time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return None

    stop = TourStop(
        tour_id=tour.id,
        band_id=tour.band_id,
        venue_id=venue_id,
        date=stop_date,
        event_type=event_type,
        status=stop_status,
        doors_time=parse_time(data.get('doors_time')),
        soundcheck_time=parse_time(data.get('soundcheck_time')),
        set_time=parse_time(data.get('set_time')),
        load_in_time=parse_time(data.get('load_in_time')),
        curfew_time=parse_time(data.get('curfew_time')),
        guarantee=data.get('guarantee'),
        ticket_price=data.get('ticket_price'),
        currency=data.get('currency', 'EUR'),
        notes=data.get('notes', '').strip() or None,
        set_length_minutes=data.get('set_length_minutes'),
        age_restriction=data.get('age_restriction'),
        location_address=data.get('location_address'),
        location_city=data.get('location_city'),
        location_country=data.get('location_country'),
    )
    db.session.add(stop)
    db.session.commit()

    stop_id = stop.id
    db.session.expire_all()
    stop = TourStop.query.options(
        joinedload(TourStop.venue),
        joinedload(TourStop.band),
        joinedload(TourStop.tour),
    ).get(stop_id)
    return api_success(TourStopSchema().dump(stop)), 201


@api_bp.route('/stops/<int:stop_id>', methods=['PUT'])
@jwt_required
def api_update_stop(stop_id):
    """Update an existing tour stop.

    Updatable fields: date, venue_id, event_type, status, doors_time,
        soundcheck_time, set_time, load_in_time, curfew_time, guarantee,
        ticket_price, currency, notes, set_length_minutes, age_restriction,
        location_address, location_city, location_country
    """
    stop = TourStop.query.options(
        joinedload(TourStop.venue),
        joinedload(TourStop.band),
        joinedload(TourStop.tour),
    ).get(stop_id)

    if not stop:
        return api_error('not_found', 'Tour stop not found.', 404)
    if not stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to edit this stop.', 403)

    data = request.get_json(silent=True) or {}

    # Date update
    if 'date' in data:
        try:
            stop.date = date.fromisoformat(data['date'])
        except (ValueError, TypeError):
            return api_error('validation_error', 'date must be YYYY-MM-DD.', 422)

    # Venue update
    if 'venue_id' in data:
        if data['venue_id'] is not None:
            venue = Venue.query.get(data['venue_id'])
            if not venue:
                return api_error('not_found', 'Venue not found.', 404)
        stop.venue_id = data['venue_id']

    # Event type update
    if 'event_type' in data:
        from app.models.tour_stop import EventType
        try:
            stop.event_type = EventType(data['event_type'])
        except ValueError:
            return api_error('validation_error', f"Invalid event_type: {data['event_type']}.", 422)

    # Status update
    if 'status' in data:
        from app.models.tour_stop import TourStopStatus
        try:
            target = TourStopStatus(data['status'])
        except ValueError:
            return api_error('validation_error', f"Invalid status: {data['status']}.", 422)
        if not stop.can_transition_to(target):
            return api_error(
                'invalid_transition',
                f"Cannot transition from {stop.status.value} to {target.value}.",
                409,
            )
        stop.status = target

    # Time fields
    def parse_time(value):
        if value is None:
            return None
        from datetime import time as dt_time
        try:
            parts = value.split(':')
            return dt_time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError, AttributeError):
            return None

    time_fields = ['doors_time', 'soundcheck_time', 'set_time', 'load_in_time', 'curfew_time']
    for field in time_fields:
        if field in data:
            setattr(stop, field, parse_time(data[field]))

    # Simple fields
    simple_fields = [
        'guarantee', 'ticket_price', 'currency', 'notes',
        'set_length_minutes', 'age_restriction',
        'location_address', 'location_city', 'location_country',
    ]
    for field in simple_fields:
        if field in data:
            value = data[field]
            if isinstance(value, str):
                value = value.strip() or None
            setattr(stop, field, value)

    db.session.commit()
    return api_success(TourStopSchema().dump(stop))


@api_bp.route('/stops/<int:stop_id>', methods=['DELETE'])
@jwt_required
def api_delete_stop(stop_id):
    """Delete a tour stop."""
    stop = TourStop.query.options(joinedload(TourStop.tour)).get(stop_id)
    if not stop:
        return api_error('not_found', 'Tour stop not found.', 404)
    if not stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to delete this stop.', 403)

    db.session.delete(stop)
    db.session.commit()
    return api_success({'deleted': True})


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


@api_bp.route('/stops/<int:stop_id>/guestlist', methods=['POST'])
@jwt_required
def api_create_guestlist_entry(stop_id):
    """Add a guest to a tour stop's guestlist.

    Required fields: guest_name, guest_email
    Optional fields: guest_phone, company, entry_type, plus_ones,
        plus_one_names, request_reason, notes, status
    """
    stop = TourStop.query.options(joinedload(TourStop.tour)).get(stop_id)
    if not stop:
        return api_error('not_found', 'Tour stop not found.', 404)
    if not stop.can_manage_guestlist(request.api_user):
        return api_error('forbidden', 'No permission to manage guestlist.', 403)

    data = request.get_json(silent=True) or {}

    errors = {}
    if not data.get('guest_name', '').strip():
        errors['guest_name'] = 'guest_name is required.'
    if not data.get('guest_email', '').strip():
        errors['guest_email'] = 'guest_email is required.'
    if errors:
        return api_error('validation_error', 'Missing required fields.', 422, errors)

    # Parse entry_type
    entry_type = EntryType.GUEST
    if data.get('entry_type'):
        try:
            entry_type = EntryType(data['entry_type'])
        except ValueError:
            return api_error('validation_error', f"Invalid entry_type: {data['entry_type']}.", 422)

    # Parse status (default to APPROVED when manager adds directly)
    entry_status = GuestlistStatus.APPROVED
    if data.get('status'):
        try:
            entry_status = GuestlistStatus(data['status'])
        except ValueError:
            return api_error('validation_error', f"Invalid status: {data['status']}.", 422)

    plus_ones = data.get('plus_ones', 0)
    if not isinstance(plus_ones, int) or plus_ones < 0:
        return api_error('validation_error', 'plus_ones must be a non-negative integer.', 422)

    entry = GuestlistEntry(
        tour_stop_id=stop.id,
        guest_name=data['guest_name'].strip(),
        guest_email=data['guest_email'].strip().lower(),
        guest_phone=data.get('guest_phone', '').strip() or None,
        company=data.get('company', '').strip() or None,
        entry_type=entry_type,
        plus_ones=plus_ones,
        plus_one_names=data.get('plus_one_names', '').strip() or None,
        status=entry_status,
        requested_by_id=request.api_user.id,
        request_reason=data.get('request_reason', '').strip() or None,
        notes=data.get('notes', '').strip() or None,
    )

    if entry_status == GuestlistStatus.APPROVED:
        entry.approved_by_id = request.api_user.id
        entry.approved_at = datetime.utcnow()

    db.session.add(entry)
    db.session.commit()

    entry_id = entry.id
    db.session.expire_all()
    entry = GuestlistEntry.query.options(
        joinedload(GuestlistEntry.requested_by),
    ).get(entry_id)
    return api_success(GuestlistEntrySchema().dump(entry)), 201


@api_bp.route('/guestlist/<int:entry_id>', methods=['GET'])
@jwt_required
def api_get_guestlist_entry(entry_id):
    """Get a single guestlist entry."""
    entry = GuestlistEntry.query.options(
        joinedload(GuestlistEntry.tour_stop).joinedload(TourStop.tour),
        joinedload(GuestlistEntry.requested_by),
    ).get(entry_id)

    if not entry or not entry.tour_stop.tour.can_view(request.api_user):
        return api_error('not_found', 'Guestlist entry not found.', 404)

    return api_success(GuestlistEntrySchema().dump(entry))


@api_bp.route('/guestlist/<int:entry_id>', methods=['PUT'])
@jwt_required
def api_update_guestlist_entry(entry_id):
    """Update a guestlist entry.

    Updatable fields: guest_name, guest_email, guest_phone, company,
        entry_type, plus_ones, plus_one_names, notes, status
    """
    entry = GuestlistEntry.query.options(
        joinedload(GuestlistEntry.tour_stop).joinedload(TourStop.tour),
        joinedload(GuestlistEntry.requested_by),
    ).get(entry_id)

    if not entry:
        return api_error('not_found', 'Guestlist entry not found.', 404)
    if not entry.tour_stop.can_manage_guestlist(request.api_user):
        return api_error('forbidden', 'No permission to edit this entry.', 403)
    if entry.is_locked:
        return api_error('invalid_state', 'Cannot edit a checked-in or no-show entry.', 409)

    data = request.get_json(silent=True) or {}

    # Simple string fields
    string_fields = ['guest_name', 'guest_email', 'guest_phone', 'company',
                     'plus_one_names', 'notes', 'request_reason']
    for field in string_fields:
        if field in data:
            value = data[field]
            if isinstance(value, str):
                value = value.strip() or None
            setattr(entry, field, value)

    # Validate name/email not empty
    if entry.guest_name is None or (isinstance(entry.guest_name, str) and not entry.guest_name.strip()):
        return api_error('validation_error', 'guest_name cannot be empty.', 422)
    if entry.guest_email is None or (isinstance(entry.guest_email, str) and not entry.guest_email.strip()):
        return api_error('validation_error', 'guest_email cannot be empty.', 422)

    # Entry type
    if 'entry_type' in data:
        try:
            entry.entry_type = EntryType(data['entry_type'])
        except ValueError:
            return api_error('validation_error', f"Invalid entry_type: {data['entry_type']}.", 422)

    # Plus ones
    if 'plus_ones' in data:
        if not isinstance(data['plus_ones'], int) or data['plus_ones'] < 0:
            return api_error('validation_error', 'plus_ones must be a non-negative integer.', 422)
        entry.plus_ones = data['plus_ones']

    # Status transition
    if 'status' in data:
        try:
            target = GuestlistStatus(data['status'])
        except ValueError:
            return api_error('validation_error', f"Invalid status: {data['status']}.", 422)
        if not entry.can_transition_to(target):
            return api_error(
                'invalid_transition',
                f"Cannot transition from {entry.status.value} to {target.value}.",
                409,
            )
        entry.status = target
        if target == GuestlistStatus.APPROVED:
            entry.approved_by_id = request.api_user.id
            entry.approved_at = datetime.utcnow()

    db.session.commit()
    return api_success(GuestlistEntrySchema().dump(entry))


@api_bp.route('/guestlist/<int:entry_id>', methods=['DELETE'])
@jwt_required
def api_delete_guestlist_entry(entry_id):
    """Delete a guestlist entry."""
    entry = GuestlistEntry.query.options(
        joinedload(GuestlistEntry.tour_stop).joinedload(TourStop.tour),
    ).get(entry_id)

    if not entry:
        return api_error('not_found', 'Guestlist entry not found.', 404)
    if not entry.tour_stop.can_manage_guestlist(request.api_user):
        return api_error('forbidden', 'No permission to delete this entry.', 403)
    if entry.is_locked:
        return api_error('invalid_state', 'Cannot delete a checked-in or no-show entry.', 409)

    db.session.delete(entry)
    db.session.commit()
    return api_success({'deleted': True})


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


@api_bp.route('/bands', methods=['POST'])
@jwt_required
def api_create_band():
    """Create a new band.

    Required fields: name
    Optional fields: genre, bio, website
    """
    data = request.get_json(silent=True) or {}
    user = request.api_user

    if not data.get('name', '').strip():
        return api_error('validation_error', 'Missing required fields.', 422,
                         {'name': 'name is required.'})

    from app.models.organization import OrganizationMembership
    membership = OrganizationMembership.query.filter_by(user_id=user.id).first()
    if not membership:
        return api_error('forbidden', 'User has no organization.', 403)

    band = Band(
        name=data['name'].strip(),
        genre=data.get('genre', '').strip() or None,
        bio=data.get('bio', '').strip() or None,
        website=data.get('website', '').strip() or None,
        org_id=membership.org_id,
        manager_id=user.id,
    )
    db.session.add(band)
    db.session.commit()

    band_id = band.id
    db.session.expire_all()
    band = Band.query.options(joinedload(Band.manager)).get(band_id)
    return api_success(BandSchema().dump(band)), 201


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
