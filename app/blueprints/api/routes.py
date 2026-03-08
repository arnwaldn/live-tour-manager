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
    NotificationSchema, PaymentSchema, BandSchema, BandDetailSchema,
    VenueSchema, VenueDetailSchema, TourStopMinimalSchema,
    UserSchema, LogisticsInfoSchema,
    AdvancingChecklistItemSchema, RiderRequirementSchema,
    AdvancingContactSchema, LineupSlotSchema,
    CrewScheduleSlotSchema, CrewAssignmentSchema,
    DocumentSchema, InvoiceSchema, InvoiceLineSchema, InvoiceMinimalSchema,
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
from app.models.venue import Venue, VenueContact
from app.models.guestlist import GuestlistEntry, GuestlistStatus, EntryType
from app.models.advancing import (
    AdvancingChecklistItem, ChecklistCategory, RiderRequirement, RiderCategory,
    AdvancingContact, DEFAULT_CHECKLIST_ITEMS,
)
from app.models.logistics import LogisticsInfo, LogisticsType, LogisticsStatus
from app.models.lineup import LineupSlot, PerformerType
from app.models.crew_schedule import CrewScheduleSlot, CrewAssignment, AssignmentStatus
from app.models.document import Document, DocumentType, DocumentShare, ShareType
from app.models.invoices import Invoice, InvoiceStatus, InvoiceType, InvoiceLine, InvoicePayment


# ── Version check (deploy verification) ─────────────────────

@api_bp.route('/version', methods=['GET'])
def api_version():
    """Return API version to verify deployment."""
    return jsonify({'version': '2026-03-08-v5', 'routes': 116})


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
    import traceback
    try:
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
    except Exception as e:
        db.session.rollback()
        tb = traceback.format_exc()
        return jsonify({'error': {'code': 'debug', 'message': str(e), 'trace': tb[-500:]}}), 500


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


@api_bp.route('/bands/<int:band_id>', methods=['GET'])
@jwt_required
def api_get_band(band_id):
    """Get a single band with members."""
    band = Band.query.options(
        joinedload(Band.manager),
        joinedload(Band.memberships).joinedload(BandMembership.user),
    ).get(band_id)

    if not band:
        return api_error('not_found', 'Band not found.', 404)
    user = request.api_user
    if not band.has_access(user) and not user.is_manager_or_above():
        return api_error('forbidden', 'No access to this band.', 403)

    return api_success(BandDetailSchema().dump(band))


@api_bp.route('/bands/<int:band_id>', methods=['PUT'])
@jwt_required
def api_update_band(band_id):
    """Update an existing band.

    Updatable fields: name, genre, bio, website, social_links
    """
    band = Band.query.options(joinedload(Band.manager)).get(band_id)
    if not band:
        return api_error('not_found', 'Band not found.', 404)
    user = request.api_user
    if not band.is_manager(user) and not user.is_manager_or_above():
        return api_error('forbidden', 'No permission to edit this band.', 403)

    data = request.get_json(silent=True) or {}

    UPDATABLE = {'name', 'genre', 'bio', 'website'}
    for field in UPDATABLE:
        if field in data:
            value = data[field]
            if isinstance(value, str):
                value = value.strip() or None
            setattr(band, field, value)

    if 'social_links' in data:
        if isinstance(data['social_links'], dict):
            band.social_links = data['social_links']
        else:
            return api_error('validation_error', 'social_links must be a JSON object.', 422)

    # Validate name not empty
    if band.name is None or (isinstance(band.name, str) and not band.name.strip()):
        return api_error('validation_error', 'name cannot be empty.', 422)

    db.session.commit()

    band_id = band.id
    db.session.expire_all()
    band = Band.query.options(
        joinedload(Band.manager),
        joinedload(Band.memberships).joinedload(BandMembership.user),
    ).get(band_id)
    return api_success(BandDetailSchema().dump(band))


@api_bp.route('/bands/<int:band_id>', methods=['DELETE'])
@jwt_required
def api_delete_band(band_id):
    """Delete a band. Checks for deletion blockers (active tours, pending payments)."""
    band = Band.query.get(band_id)
    if not band:
        return api_error('not_found', 'Band not found.', 404)
    user = request.api_user
    if not band.is_manager(user) and not user.is_admin():
        return api_error('forbidden', 'No permission to delete this band.', 403)

    blockers = band.get_deletion_blockers()
    if blockers:
        return api_error(
            'deletion_blocked',
            f'Cannot delete band: {", ".join(blockers)}.',
            409,
            {'blockers': blockers},
        )

    db.session.delete(band)
    db.session.commit()
    return api_success({'deleted': True})


@api_bp.route('/venues', methods=['POST'])
@jwt_required
def api_create_venue():
    """Create a new venue."""
    import traceback
    try:
        data = request.get_json(silent=True) or {}
        user = request.api_user

        errors = {}
        for field in ('name', 'city', 'country'):
            if not data.get(field, '').strip():
                errors[field] = f'{field} is required.'
        if errors:
            return api_error('validation_error', 'Missing required fields.', 422, errors)

        from app.models.organization import OrganizationMembership
        membership = OrganizationMembership.query.filter_by(user_id=user.id).first()
        if not membership:
            return api_error('forbidden', 'User has no organization.', 403)

        venue = Venue(
            name=data['name'].strip(),
            city=data['city'].strip(),
            country=data['country'].strip(),
            address=data.get('address', '').strip() or None,
            state=data.get('state', '').strip() or None,
            postal_code=data.get('postal_code', '').strip() or None,
            capacity=data.get('capacity'),
            venue_type=data.get('venue_type', '').strip() or None,
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            timezone=data.get('timezone', 'Europe/Paris'),
            website=data.get('website', '').strip() or None,
            phone=data.get('phone', '').strip() or None,
            email=data.get('email', '').strip() or None,
            notes=data.get('notes', '').strip() or None,
            technical_specs=data.get('technical_specs', '').strip() or None,
            stage_dimensions=data.get('stage_dimensions', '').strip() or None,
            load_in_info=data.get('load_in_info', '').strip() or None,
            parking_info=data.get('parking_info', '').strip() or None,
            backline_available=data.get('backline_available', False),
            backline_details=data.get('backline_details', '').strip() or None,
            org_id=membership.org_id,
        )
        db.session.add(venue)
        db.session.commit()

        venue_id = venue.id
        db.session.expire_all()
        venue = Venue.query.options(joinedload(Venue.contacts)).get(venue_id)
        return api_success(VenueDetailSchema().dump(venue)), 201
    except Exception as e:
        db.session.rollback()
        tb = traceback.format_exc()
        return jsonify({'error': {'code': 'debug', 'message': str(e), 'trace': tb[-500:]}}), 500


@api_bp.route('/venues/<int:venue_id>', methods=['GET'])
@jwt_required
def api_get_venue(venue_id):
    """Get a single venue with contacts and technical specs."""
    venue = Venue.query.options(joinedload(Venue.contacts)).get(venue_id)
    if not venue:
        return api_error('not_found', 'Venue not found.', 404)

    return api_success(VenueDetailSchema().dump(venue))


@api_bp.route('/venues/<int:venue_id>', methods=['PUT'])
@jwt_required
def api_update_venue(venue_id):
    """Update an existing venue.

    Updatable fields: name, address, city, state, country, postal_code,
        capacity, venue_type, latitude, longitude, timezone, website,
        phone, email, notes, technical_specs, stage_dimensions,
        load_in_info, parking_info, backline_available, backline_details
    """
    venue = Venue.query.options(joinedload(Venue.contacts)).get(venue_id)
    if not venue:
        return api_error('not_found', 'Venue not found.', 404)

    data = request.get_json(silent=True) or {}

    STRING_FIELDS = [
        'name', 'address', 'city', 'state', 'country', 'postal_code',
        'venue_type', 'timezone', 'website', 'phone', 'email', 'notes',
        'technical_specs', 'stage_dimensions', 'load_in_info', 'parking_info',
        'backline_details',
    ]
    for field in STRING_FIELDS:
        if field in data:
            value = data[field]
            if isinstance(value, str):
                value = value.strip() or None
            setattr(venue, field, value)

    NUMERIC_FIELDS = ['capacity', 'latitude', 'longitude']
    for field in NUMERIC_FIELDS:
        if field in data:
            setattr(venue, field, data[field])

    if 'backline_available' in data:
        venue.backline_available = bool(data['backline_available'])

    # Validate required fields not empty
    if venue.name is None or (isinstance(venue.name, str) and not venue.name.strip()):
        return api_error('validation_error', 'name cannot be empty.', 422)
    if venue.city is None or (isinstance(venue.city, str) and not venue.city.strip()):
        return api_error('validation_error', 'city cannot be empty.', 422)
    if venue.country is None or (isinstance(venue.country, str) and not venue.country.strip()):
        return api_error('validation_error', 'country cannot be empty.', 422)

    db.session.commit()
    return api_success(VenueDetailSchema().dump(venue))


@api_bp.route('/venues/<int:venue_id>', methods=['DELETE'])
@jwt_required
def api_delete_venue(venue_id):
    """Delete a venue. Fails if any tour stops reference it."""
    venue = Venue.query.get(venue_id)
    if not venue:
        return api_error('not_found', 'Venue not found.', 404)

    # Check for referencing tour stops
    stop_count = TourStop.query.filter_by(venue_id=venue.id).count()
    if stop_count > 0:
        return api_error(
            'deletion_blocked',
            f'Cannot delete venue: {stop_count} tour stop(s) reference it.',
            409,
            {'blockers': [f'{stop_count} tour stop(s) reference this venue']},
        )

    db.session.delete(venue)
    db.session.commit()
    return api_success({'deleted': True})


# ── Profile ────────────────────────────────────────────────

@api_bp.route('/auth/me', methods=['PUT'])
@jwt_required
def api_update_profile():
    """Update current user's profile.

    Updatable fields: first_name, last_name, phone
    """
    user = request.api_user
    data = request.get_json(silent=True) or {}

    UPDATABLE = {'first_name', 'last_name', 'phone'}
    for field in UPDATABLE:
        if field in data:
            value = data[field]
            if isinstance(value, str):
                value = value.strip() or None
            setattr(user, field, value)

    # Validate required fields
    if not user.first_name or not user.first_name.strip():
        return api_error('validation_error', 'first_name cannot be empty.', 422)
    if not user.last_name or not user.last_name.strip():
        return api_error('validation_error', 'last_name cannot be empty.', 422)

    db.session.commit()
    return api_success(UserSchema().dump(user))


# ── Advancing ──────────────────────────────────────────────

@api_bp.route('/stops/<int:stop_id>/advancing', methods=['GET'])
@jwt_required
def api_get_advancing(stop_id):
    """Get full advancing data for a tour stop.

    Returns checklist items, rider requirements, contacts, and completion %.
    """
    stop = TourStop.query.options(
        joinedload(TourStop.tour),
        joinedload(TourStop.checklist_items),
        joinedload(TourStop.rider_requirements),
        joinedload(TourStop.advancing_contacts),
    ).get(stop_id)

    if not stop or not stop.tour.can_view(request.api_user):
        return api_error('not_found', 'Tour stop not found.', 404)

    checklist = AdvancingChecklistItemSchema(many=True).dump(stop.checklist_items)
    rider = RiderRequirementSchema(many=True).dump(stop.rider_requirements)
    contacts = AdvancingContactSchema(many=True).dump(stop.advancing_contacts)

    total = len(stop.checklist_items)
    completed = sum(1 for item in stop.checklist_items if item.is_completed)
    completion_pct = round((completed / total * 100) if total > 0 else 0)

    return api_success({
        'checklist': checklist,
        'rider': rider,
        'contacts': contacts,
        'completion': {
            'total': total,
            'completed': completed,
            'percentage': completion_pct,
        },
    })


@api_bp.route('/stops/<int:stop_id>/advancing/checklist', methods=['POST'])
@jwt_required
def api_create_checklist_item(stop_id):
    """Add a checklist item to a tour stop's advancing.

    Required fields: label, category
    Optional fields: notes, due_date, sort_order
    """
    stop = TourStop.query.options(joinedload(TourStop.tour)).get(stop_id)
    if not stop:
        return api_error('not_found', 'Tour stop not found.', 404)
    if not stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to edit this stop.', 403)

    data = request.get_json(silent=True) or {}

    if not data.get('label', '').strip():
        return api_error('validation_error', 'label is required.', 422)
    if not data.get('category'):
        return api_error('validation_error', 'category is required.', 422)

    try:
        category = ChecklistCategory(data['category'])
    except ValueError:
        return api_error('validation_error', f"Invalid category: {data['category']}.", 422)

    due_date = None
    if data.get('due_date'):
        try:
            due_date = date.fromisoformat(data['due_date'])
        except (ValueError, TypeError):
            return api_error('validation_error', 'due_date must be YYYY-MM-DD.', 422)

    item = AdvancingChecklistItem(
        tour_stop_id=stop.id,
        category=category,
        label=data['label'].strip(),
        notes=data.get('notes', '').strip() or None,
        due_date=due_date,
        sort_order=data.get('sort_order', 0),
    )
    db.session.add(item)
    db.session.commit()

    return api_success(AdvancingChecklistItemSchema().dump(item)), 201


@api_bp.route('/advancing/checklist/<int:item_id>', methods=['PUT'])
@jwt_required
def api_update_checklist_item(item_id):
    """Update or toggle a checklist item.

    Updatable fields: label, category, is_completed, notes, due_date, sort_order
    """
    item = AdvancingChecklistItem.query.options(
        joinedload(AdvancingChecklistItem.tour_stop).joinedload(TourStop.tour),
    ).get(item_id)
    if not item:
        return api_error('not_found', 'Checklist item not found.', 404)
    if not item.tour_stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to edit this item.', 403)

    data = request.get_json(silent=True) or {}

    if 'label' in data:
        value = data['label'].strip() if isinstance(data['label'], str) else data['label']
        if not value:
            return api_error('validation_error', 'label cannot be empty.', 422)
        item.label = value

    if 'category' in data:
        try:
            item.category = ChecklistCategory(data['category'])
        except ValueError:
            return api_error('validation_error', f"Invalid category: {data['category']}.", 422)

    if 'is_completed' in data:
        item.toggle(request.api_user.id)

    if 'notes' in data:
        item.notes = data['notes'].strip() if isinstance(data['notes'], str) else data['notes']

    if 'due_date' in data:
        if data['due_date']:
            try:
                item.due_date = date.fromisoformat(data['due_date'])
            except (ValueError, TypeError):
                return api_error('validation_error', 'due_date must be YYYY-MM-DD.', 422)
        else:
            item.due_date = None

    if 'sort_order' in data:
        item.sort_order = data['sort_order']

    db.session.commit()
    return api_success(AdvancingChecklistItemSchema().dump(item))


@api_bp.route('/advancing/checklist/<int:item_id>', methods=['DELETE'])
@jwt_required
def api_delete_checklist_item(item_id):
    """Delete a checklist item."""
    item = AdvancingChecklistItem.query.options(
        joinedload(AdvancingChecklistItem.tour_stop).joinedload(TourStop.tour),
    ).get(item_id)
    if not item:
        return api_error('not_found', 'Checklist item not found.', 404)
    if not item.tour_stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to delete this item.', 403)

    db.session.delete(item)
    db.session.commit()
    return api_success({'deleted': True})


@api_bp.route('/stops/<int:stop_id>/advancing/init', methods=['POST'])
@jwt_required
def api_init_advancing_checklist(stop_id):
    """Initialize advancing checklist from default template (26 items).

    Only works if checklist is empty (no existing items).
    """
    stop = TourStop.query.options(
        joinedload(TourStop.tour),
        joinedload(TourStop.checklist_items),
    ).get(stop_id)
    if not stop:
        return api_error('not_found', 'Tour stop not found.', 404)
    if not stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to edit this stop.', 403)

    if len(stop.checklist_items) > 0:
        return api_error('invalid_state', 'Checklist already initialized.', 409)

    for item_data in DEFAULT_CHECKLIST_ITEMS:
        item = AdvancingChecklistItem(
            tour_stop_id=stop.id,
            category=ChecklistCategory(item_data['category']),
            label=item_data['label'],
            sort_order=item_data['sort_order'],
        )
        db.session.add(item)

    db.session.commit()

    # Re-fetch with items
    db.session.expire_all()
    stop = TourStop.query.options(joinedload(TourStop.checklist_items)).get(stop_id)
    items = AdvancingChecklistItemSchema(many=True).dump(stop.checklist_items)
    return api_success({'items': items, 'count': len(items)}), 201


@api_bp.route('/stops/<int:stop_id>/advancing/rider', methods=['POST'])
@jwt_required
def api_create_rider_requirement(stop_id):
    """Add a rider requirement.

    Required fields: requirement, category
    Optional fields: quantity, is_mandatory, notes, sort_order
    """
    stop = TourStop.query.options(joinedload(TourStop.tour)).get(stop_id)
    if not stop:
        return api_error('not_found', 'Tour stop not found.', 404)
    if not stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to edit this stop.', 403)

    data = request.get_json(silent=True) or {}

    if not data.get('requirement', '').strip():
        return api_error('validation_error', 'requirement is required.', 422)
    if not data.get('category'):
        return api_error('validation_error', 'category is required.', 422)

    try:
        category = RiderCategory(data['category'])
    except ValueError:
        return api_error('validation_error', f"Invalid category: {data['category']}.", 422)

    rider = RiderRequirement(
        tour_stop_id=stop.id,
        category=category,
        requirement=data['requirement'].strip(),
        quantity=data.get('quantity', 1),
        is_mandatory=data.get('is_mandatory', True),
        notes=data.get('notes', '').strip() or None,
        sort_order=data.get('sort_order', 0),
    )
    db.session.add(rider)
    db.session.commit()

    return api_success(RiderRequirementSchema().dump(rider)), 201


@api_bp.route('/advancing/rider/<int:rider_id>', methods=['PUT'])
@jwt_required
def api_update_rider_requirement(rider_id):
    """Update a rider requirement.

    Updatable fields: requirement, category, quantity, is_mandatory,
        is_confirmed, venue_response, notes, sort_order
    """
    rider = RiderRequirement.query.options(
        joinedload(RiderRequirement.tour_stop).joinedload(TourStop.tour),
    ).get(rider_id)
    if not rider:
        return api_error('not_found', 'Rider requirement not found.', 404)
    if not rider.tour_stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to edit this item.', 403)

    data = request.get_json(silent=True) or {}

    if 'requirement' in data:
        value = data['requirement'].strip() if isinstance(data['requirement'], str) else data['requirement']
        if not value:
            return api_error('validation_error', 'requirement cannot be empty.', 422)
        rider.requirement = value

    if 'category' in data:
        try:
            rider.category = RiderCategory(data['category'])
        except ValueError:
            return api_error('validation_error', f"Invalid category: {data['category']}.", 422)

    SIMPLE_FIELDS = {'quantity', 'is_mandatory', 'is_confirmed', 'sort_order'}
    for field in SIMPLE_FIELDS:
        if field in data:
            setattr(rider, field, data[field])

    STRING_FIELDS = {'venue_response', 'notes'}
    for field in STRING_FIELDS:
        if field in data:
            value = data[field]
            if isinstance(value, str):
                value = value.strip() or None
            setattr(rider, field, value)

    db.session.commit()
    return api_success(RiderRequirementSchema().dump(rider))


@api_bp.route('/advancing/rider/<int:rider_id>', methods=['DELETE'])
@jwt_required
def api_delete_rider_requirement(rider_id):
    """Delete a rider requirement."""
    rider = RiderRequirement.query.options(
        joinedload(RiderRequirement.tour_stop).joinedload(TourStop.tour),
    ).get(rider_id)
    if not rider:
        return api_error('not_found', 'Rider requirement not found.', 404)
    if not rider.tour_stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to delete this item.', 403)

    db.session.delete(rider)
    db.session.commit()
    return api_success({'deleted': True})


@api_bp.route('/stops/<int:stop_id>/advancing/contacts', methods=['POST'])
@jwt_required
def api_create_advancing_contact(stop_id):
    """Add an advancing contact.

    Required fields: name
    Optional fields: role, email, phone, is_primary, notes
    """
    stop = TourStop.query.options(joinedload(TourStop.tour)).get(stop_id)
    if not stop:
        return api_error('not_found', 'Tour stop not found.', 404)
    if not stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to edit this stop.', 403)

    data = request.get_json(silent=True) or {}

    if not data.get('name', '').strip():
        return api_error('validation_error', 'name is required.', 422)

    contact = AdvancingContact(
        tour_stop_id=stop.id,
        name=data['name'].strip(),
        role=data.get('role', '').strip() or None,
        email=data.get('email', '').strip() or None,
        phone=data.get('phone', '').strip() or None,
        is_primary=data.get('is_primary', False),
        notes=data.get('notes', '').strip() or None,
    )
    db.session.add(contact)
    db.session.commit()

    return api_success(AdvancingContactSchema().dump(contact)), 201


@api_bp.route('/advancing/contacts/<int:contact_id>', methods=['PUT'])
@jwt_required
def api_update_advancing_contact(contact_id):
    """Update an advancing contact.

    Updatable fields: name, role, email, phone, is_primary, notes
    """
    contact = AdvancingContact.query.options(
        joinedload(AdvancingContact.tour_stop).joinedload(TourStop.tour),
    ).get(contact_id)
    if not contact:
        return api_error('not_found', 'Advancing contact not found.', 404)
    if not contact.tour_stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to edit this contact.', 403)

    data = request.get_json(silent=True) or {}

    STRING_FIELDS = {'name', 'role', 'email', 'phone', 'notes'}
    for field in STRING_FIELDS:
        if field in data:
            value = data[field]
            if isinstance(value, str):
                value = value.strip() or None
            setattr(contact, field, value)

    if 'is_primary' in data:
        contact.is_primary = bool(data['is_primary'])

    if contact.name is None or (isinstance(contact.name, str) and not contact.name.strip()):
        return api_error('validation_error', 'name cannot be empty.', 422)

    db.session.commit()
    return api_success(AdvancingContactSchema().dump(contact))


@api_bp.route('/advancing/contacts/<int:contact_id>', methods=['DELETE'])
@jwt_required
def api_delete_advancing_contact(contact_id):
    """Delete an advancing contact."""
    contact = AdvancingContact.query.options(
        joinedload(AdvancingContact.tour_stop).joinedload(TourStop.tour),
    ).get(contact_id)
    if not contact:
        return api_error('not_found', 'Advancing contact not found.', 404)
    if not contact.tour_stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to delete this contact.', 403)

    db.session.delete(contact)
    db.session.commit()
    return api_success({'deleted': True})


# ── Logistics ──────────────────────────────────────────────

@api_bp.route('/stops/<int:stop_id>/logistics', methods=['GET'])
@jwt_required
def api_list_logistics(stop_id):
    """List logistics items for a tour stop."""
    stop = TourStop.query.options(joinedload(TourStop.tour)).get(stop_id)
    if not stop or not stop.tour.can_view(request.api_user):
        return api_error('not_found', 'Tour stop not found.', 404)

    query = LogisticsInfo.query.filter_by(
        tour_stop_id=stop_id
    ).order_by(LogisticsInfo.start_datetime)

    logistics_type = request.args.get('type')
    if logistics_type:
        try:
            query = query.filter(LogisticsInfo.logistics_type == LogisticsType(logistics_type))
        except ValueError:
            return api_error('invalid_filter', f'Invalid type: {logistics_type}', 422)

    items = query.all()
    return api_success(LogisticsInfoSchema(many=True).dump(items))


@api_bp.route('/stops/<int:stop_id>/logistics', methods=['POST'])
@jwt_required
def api_create_logistics(stop_id):
    """Create a logistics item.

    Required fields: logistics_type
    Optional fields: provider, confirmation_number, start_datetime, end_datetime,
        status, address, city, country, cost, currency, notes, and type-specific fields
    """
    stop = TourStop.query.options(joinedload(TourStop.tour)).get(stop_id)
    if not stop:
        return api_error('not_found', 'Tour stop not found.', 404)
    if not stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to edit this stop.', 403)

    data = request.get_json(silent=True) or {}

    if not data.get('logistics_type'):
        return api_error('validation_error', 'logistics_type is required.', 422)

    try:
        ltype = LogisticsType(data['logistics_type'])
    except ValueError:
        return api_error('validation_error', f"Invalid logistics_type: {data['logistics_type']}.", 422)

    # Parse status
    lstatus = LogisticsStatus.PENDING
    if data.get('status'):
        try:
            lstatus = LogisticsStatus(data['status'])
        except ValueError:
            return api_error('validation_error', f"Invalid status: {data['status']}.", 422)

    # Parse datetimes
    start_dt = None
    end_dt = None
    if data.get('start_datetime'):
        try:
            start_dt = datetime.fromisoformat(data['start_datetime'])
        except (ValueError, TypeError):
            return api_error('validation_error', 'start_datetime must be ISO format.', 422)
    if data.get('end_datetime'):
        try:
            end_dt = datetime.fromisoformat(data['end_datetime'])
        except (ValueError, TypeError):
            return api_error('validation_error', 'end_datetime must be ISO format.', 422)

    # Parse time fields for hotels
    def parse_time(value):
        if not value:
            return None
        from datetime import time as dt_time
        try:
            parts = value.split(':')
            return dt_time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return None

    item = LogisticsInfo(
        tour_stop_id=stop.id,
        logistics_type=ltype,
        status=lstatus,
        provider=data.get('provider', '').strip() or None,
        confirmation_number=data.get('confirmation_number', '').strip() or None,
        start_datetime=start_dt,
        end_datetime=end_dt,
        address=data.get('address', '').strip() or None,
        city=data.get('city', '').strip() or None,
        country=data.get('country', '').strip() or None,
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        cost=data.get('cost'),
        currency=data.get('currency', 'EUR'),
        is_paid=data.get('is_paid', False),
        paid_by=data.get('paid_by', '').strip() or None,
        # Flight
        flight_number=data.get('flight_number', '').strip() or None,
        departure_airport=data.get('departure_airport', '').strip() or None,
        arrival_airport=data.get('arrival_airport', '').strip() or None,
        departure_terminal=data.get('departure_terminal', '').strip() or None,
        arrival_terminal=data.get('arrival_terminal', '').strip() or None,
        # Hotel
        room_type=data.get('room_type', '').strip() or None,
        number_of_rooms=data.get('number_of_rooms', 1),
        breakfast_included=data.get('breakfast_included', False),
        check_in_time=parse_time(data.get('check_in_time')),
        check_out_time=parse_time(data.get('check_out_time')),
        # Ground transport
        pickup_location=data.get('pickup_location', '').strip() or None,
        dropoff_location=data.get('dropoff_location', '').strip() or None,
        vehicle_type=data.get('vehicle_type', '').strip() or None,
        driver_name=data.get('driver_name', '').strip() or None,
        driver_phone=data.get('driver_phone', '').strip() or None,
        # Contact
        contact_name=data.get('contact_name', '').strip() or None,
        contact_phone=data.get('contact_phone', '').strip() or None,
        contact_email=data.get('contact_email', '').strip() or None,
        notes=data.get('notes', '').strip() or None,
    )
    db.session.add(item)
    db.session.commit()

    return api_success(LogisticsInfoSchema().dump(item)), 201


@api_bp.route('/logistics/<int:item_id>', methods=['PUT'])
@jwt_required
def api_update_logistics(item_id):
    """Update a logistics item."""
    item = LogisticsInfo.query.options(
        joinedload(LogisticsInfo.tour_stop).joinedload(TourStop.tour),
    ).get(item_id)
    if not item:
        return api_error('not_found', 'Logistics item not found.', 404)
    if not item.tour_stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to edit this item.', 403)

    data = request.get_json(silent=True) or {}

    if 'logistics_type' in data:
        try:
            item.logistics_type = LogisticsType(data['logistics_type'])
        except ValueError:
            return api_error('validation_error', f"Invalid logistics_type.", 422)

    if 'status' in data:
        try:
            item.status = LogisticsStatus(data['status'])
        except ValueError:
            return api_error('validation_error', f"Invalid status.", 422)

    # Datetime fields
    for dt_field in ('start_datetime', 'end_datetime'):
        if dt_field in data:
            if data[dt_field]:
                try:
                    setattr(item, dt_field, datetime.fromisoformat(data[dt_field]))
                except (ValueError, TypeError):
                    return api_error('validation_error', f'{dt_field} must be ISO format.', 422)
            else:
                setattr(item, dt_field, None)

    # Time fields
    def parse_time(value):
        if not value:
            return None
        from datetime import time as dt_time
        try:
            parts = value.split(':')
            return dt_time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError, AttributeError):
            return None

    for time_field in ('check_in_time', 'check_out_time'):
        if time_field in data:
            setattr(item, time_field, parse_time(data[time_field]))

    # String fields
    STRING_FIELDS = [
        'provider', 'confirmation_number', 'address', 'city', 'country',
        'paid_by', 'flight_number', 'departure_airport', 'arrival_airport',
        'departure_terminal', 'arrival_terminal', 'room_type',
        'pickup_location', 'dropoff_location', 'vehicle_type',
        'driver_name', 'driver_phone', 'contact_name', 'contact_phone',
        'contact_email', 'notes',
    ]
    for field in STRING_FIELDS:
        if field in data:
            value = data[field]
            if isinstance(value, str):
                value = value.strip() or None
            setattr(item, field, value)

    # Numeric/boolean fields
    SIMPLE_FIELDS = [
        'latitude', 'longitude', 'cost', 'currency', 'is_paid',
        'number_of_rooms', 'breakfast_included',
    ]
    for field in SIMPLE_FIELDS:
        if field in data:
            setattr(item, field, data[field])

    db.session.commit()
    return api_success(LogisticsInfoSchema().dump(item))


@api_bp.route('/logistics/<int:item_id>', methods=['DELETE'])
@jwt_required
def api_delete_logistics(item_id):
    """Delete a logistics item."""
    item = LogisticsInfo.query.options(
        joinedload(LogisticsInfo.tour_stop).joinedload(TourStop.tour),
    ).get(item_id)
    if not item:
        return api_error('not_found', 'Logistics item not found.', 404)
    if not item.tour_stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to delete this item.', 403)

    db.session.delete(item)
    db.session.commit()
    return api_success({'deleted': True})


# ── Lineup ─────────────────────────────────────────────────

@api_bp.route('/stops/<int:stop_id>/lineup', methods=['GET'])
@jwt_required
def api_list_lineup(stop_id):
    """List lineup slots for a tour stop."""
    stop = TourStop.query.options(joinedload(TourStop.tour)).get(stop_id)
    if not stop or not stop.tour.can_view(request.api_user):
        return api_error('not_found', 'Tour stop not found.', 404)

    slots = LineupSlot.query.filter_by(
        tour_stop_id=stop_id
    ).order_by(LineupSlot.order, LineupSlot.start_time).all()

    return api_success(LineupSlotSchema(many=True).dump(slots))


@api_bp.route('/stops/<int:stop_id>/lineup', methods=['POST'])
@jwt_required
def api_create_lineup_slot(stop_id):
    """Create a lineup slot.

    Required fields: performer_name, start_time
    Optional fields: performer_type, end_time, set_length_minutes, order, notes, is_confirmed
    """
    stop = TourStop.query.options(joinedload(TourStop.tour)).get(stop_id)
    if not stop:
        return api_error('not_found', 'Tour stop not found.', 404)
    if not stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to edit this stop.', 403)

    data = request.get_json(silent=True) or {}

    if not data.get('performer_name', '').strip():
        return api_error('validation_error', 'performer_name is required.', 422)
    if not data.get('start_time'):
        return api_error('validation_error', 'start_time is required.', 422)

    # Parse performer_type
    ptype = PerformerType.SUPPORT
    if data.get('performer_type'):
        try:
            ptype = PerformerType(data['performer_type'])
        except ValueError:
            return api_error('validation_error', f"Invalid performer_type: {data['performer_type']}.", 422)

    # Parse times
    def parse_time(value):
        if not value:
            return None
        from datetime import time as dt_time
        try:
            parts = value.split(':')
            return dt_time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return None

    start_time = parse_time(data['start_time'])
    if not start_time:
        return api_error('validation_error', 'start_time must be HH:MM format.', 422)

    slot = LineupSlot(
        tour_stop_id=stop.id,
        performer_name=data['performer_name'].strip(),
        performer_type=ptype,
        start_time=start_time,
        end_time=parse_time(data.get('end_time')),
        set_length_minutes=data.get('set_length_minutes'),
        order=data.get('order', 1),
        notes=data.get('notes', '').strip() or None,
        is_confirmed=data.get('is_confirmed', False),
    )
    db.session.add(slot)
    db.session.commit()

    return api_success(LineupSlotSchema().dump(slot)), 201


@api_bp.route('/lineup/<int:slot_id>', methods=['PUT'])
@jwt_required
def api_update_lineup_slot(slot_id):
    """Update a lineup slot.

    Updatable fields: performer_name, performer_type, start_time, end_time,
        set_length_minutes, order, notes, is_confirmed
    """
    slot = LineupSlot.query.options(
        joinedload(LineupSlot.tour_stop).joinedload(TourStop.tour),
    ).get(slot_id)
    if not slot:
        return api_error('not_found', 'Lineup slot not found.', 404)
    if not slot.tour_stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to edit this slot.', 403)

    data = request.get_json(silent=True) or {}

    if 'performer_name' in data:
        value = data['performer_name'].strip() if isinstance(data['performer_name'], str) else data['performer_name']
        if not value:
            return api_error('validation_error', 'performer_name cannot be empty.', 422)
        slot.performer_name = value

    if 'performer_type' in data:
        try:
            slot.performer_type = PerformerType(data['performer_type'])
        except ValueError:
            return api_error('validation_error', f"Invalid performer_type.", 422)

    # Parse times
    def parse_time(value):
        if not value:
            return None
        from datetime import time as dt_time
        try:
            parts = value.split(':')
            return dt_time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError, AttributeError):
            return None

    for time_field in ('start_time', 'end_time'):
        if time_field in data:
            setattr(slot, time_field, parse_time(data[time_field]))

    SIMPLE_FIELDS = {'set_length_minutes', 'order', 'is_confirmed'}
    for field in SIMPLE_FIELDS:
        if field in data:
            setattr(slot, field, data[field])

    if 'notes' in data:
        slot.notes = data['notes'].strip() if isinstance(data['notes'], str) else data['notes']

    db.session.commit()
    return api_success(LineupSlotSchema().dump(slot))


@api_bp.route('/lineup/<int:slot_id>', methods=['DELETE'])
@jwt_required
def api_delete_lineup_slot(slot_id):
    """Delete a lineup slot."""
    slot = LineupSlot.query.options(
        joinedload(LineupSlot.tour_stop).joinedload(TourStop.tour),
    ).get(slot_id)
    if not slot:
        return api_error('not_found', 'Lineup slot not found.', 404)
    if not slot.tour_stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to delete this slot.', 403)

    db.session.delete(slot)
    db.session.commit()
    return api_success({'deleted': True})


# ── Crew ───────────────────────────────────────────────────

@api_bp.route('/stops/<int:stop_id>/crew', methods=['GET'])
@jwt_required
def api_list_crew(stop_id):
    """List crew schedule slots and assignments for a tour stop."""
    stop = TourStop.query.options(joinedload(TourStop.tour)).get(stop_id)
    if not stop or not stop.tour.can_view(request.api_user):
        return api_error('not_found', 'Tour stop not found.', 404)

    slots = CrewScheduleSlot.query.options(
        joinedload(CrewScheduleSlot.assignments),
    ).filter_by(
        tour_stop_id=stop_id
    ).order_by(CrewScheduleSlot.order, CrewScheduleSlot.start_time).all()

    return api_success(CrewScheduleSlotSchema(many=True).dump(slots))


@api_bp.route('/stops/<int:stop_id>/crew/slots', methods=['POST'])
@jwt_required
def api_create_crew_slot(stop_id):
    """Create a crew schedule slot.

    Required fields: task_name, start_time, end_time
    Optional fields: task_description, profession_category, color, order
    """
    stop = TourStop.query.options(joinedload(TourStop.tour)).get(stop_id)
    if not stop:
        return api_error('not_found', 'Tour stop not found.', 404)
    if not stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to edit this stop.', 403)

    data = request.get_json(silent=True) or {}

    if not data.get('task_name', '').strip():
        return api_error('validation_error', 'task_name is required.', 422)
    if not data.get('start_time') or not data.get('end_time'):
        return api_error('validation_error', 'start_time and end_time are required.', 422)

    def parse_time(value):
        if not value:
            return None
        from datetime import time as dt_time
        try:
            parts = value.split(':')
            return dt_time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return None

    start_time = parse_time(data['start_time'])
    end_time = parse_time(data['end_time'])
    if not start_time or not end_time:
        return api_error('validation_error', 'Times must be HH:MM format.', 422)

    # Parse profession_category
    prof_cat = None
    if data.get('profession_category'):
        from app.models.profession import ProfessionCategory
        try:
            prof_cat = ProfessionCategory(data['profession_category'])
        except ValueError:
            return api_error('validation_error', f"Invalid profession_category.", 422)

    slot = CrewScheduleSlot(
        tour_stop_id=stop.id,
        task_name=data['task_name'].strip(),
        task_description=data.get('task_description', '').strip() or None,
        start_time=start_time,
        end_time=end_time,
        profession_category=prof_cat,
        color=data.get('color', '#3B82F6'),
        order=data.get('order', 0),
        created_by_id=request.api_user.id,
    )
    db.session.add(slot)
    db.session.commit()

    return api_success(CrewScheduleSlotSchema().dump(slot)), 201


@api_bp.route('/crew/slots/<int:slot_id>', methods=['PUT'])
@jwt_required
def api_update_crew_slot(slot_id):
    """Update a crew schedule slot.

    Updatable fields: task_name, task_description, start_time, end_time,
        profession_category, color, order
    """
    slot = CrewScheduleSlot.query.options(
        joinedload(CrewScheduleSlot.assignments),
    ).get(slot_id)
    if not slot:
        return api_error('not_found', 'Crew slot not found.', 404)

    stop = TourStop.query.options(joinedload(TourStop.tour)).get(slot.tour_stop_id)
    if not stop or not stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to edit this slot.', 403)

    data = request.get_json(silent=True) or {}

    if 'task_name' in data:
        value = data['task_name'].strip() if isinstance(data['task_name'], str) else data['task_name']
        if not value:
            return api_error('validation_error', 'task_name cannot be empty.', 422)
        slot.task_name = value

    if 'task_description' in data:
        slot.task_description = data['task_description'].strip() if isinstance(data['task_description'], str) else data['task_description']

    def parse_time(value):
        if not value:
            return None
        from datetime import time as dt_time
        try:
            parts = value.split(':')
            return dt_time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError, AttributeError):
            return None

    for time_field in ('start_time', 'end_time'):
        if time_field in data:
            parsed = parse_time(data[time_field])
            if not parsed:
                return api_error('validation_error', f'{time_field} must be HH:MM.', 422)
            setattr(slot, time_field, parsed)

    if 'profession_category' in data:
        if data['profession_category']:
            from app.models.profession import ProfessionCategory
            try:
                slot.profession_category = ProfessionCategory(data['profession_category'])
            except ValueError:
                return api_error('validation_error', f"Invalid profession_category.", 422)
        else:
            slot.profession_category = None

    if 'color' in data:
        slot.color = data['color']
    if 'order' in data:
        slot.order = data['order']

    db.session.commit()
    return api_success(CrewScheduleSlotSchema().dump(slot))


@api_bp.route('/crew/slots/<int:slot_id>', methods=['DELETE'])
@jwt_required
def api_delete_crew_slot(slot_id):
    """Delete a crew schedule slot (and all its assignments)."""
    slot = CrewScheduleSlot.query.get(slot_id)
    if not slot:
        return api_error('not_found', 'Crew slot not found.', 404)

    stop = TourStop.query.options(joinedload(TourStop.tour)).get(slot.tour_stop_id)
    if not stop or not stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to delete this slot.', 403)

    db.session.delete(slot)
    db.session.commit()
    return api_success({'deleted': True})


@api_bp.route('/crew/slots/<int:slot_id>/assign', methods=['POST'])
@jwt_required
def api_assign_crew(slot_id):
    """Assign a person to a crew slot.

    Required: user_id OR external_contact_id (at least one)
    Optional: profession_id, call_time, notes
    """
    slot = CrewScheduleSlot.query.get(slot_id)
    if not slot:
        return api_error('not_found', 'Crew slot not found.', 404)

    stop = TourStop.query.options(joinedload(TourStop.tour)).get(slot.tour_stop_id)
    if not stop or not stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to assign crew.', 403)

    data = request.get_json(silent=True) or {}

    user_id = data.get('user_id')
    external_id = data.get('external_contact_id')
    if not user_id and not external_id:
        return api_error('validation_error', 'user_id or external_contact_id is required.', 422)

    # Check for duplicate assignment
    existing = CrewAssignment.query.filter_by(slot_id=slot.id)
    if user_id:
        existing = existing.filter_by(user_id=user_id).first()
    elif external_id:
        existing = existing.filter_by(external_contact_id=external_id).first()
    if existing:
        return api_error('conflict', 'Person already assigned to this slot.', 409)

    def parse_time(value):
        if not value:
            return None
        from datetime import time as dt_time
        try:
            parts = value.split(':')
            return dt_time(int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            return None

    assignment = CrewAssignment(
        slot_id=slot.id,
        user_id=user_id,
        external_contact_id=external_id,
        profession_id=data.get('profession_id'),
        call_time=parse_time(data.get('call_time')),
        notes=data.get('notes', '').strip() or None,
        assigned_by_id=request.api_user.id,
        status=AssignmentStatus.ASSIGNED,
    )
    db.session.add(assignment)
    db.session.commit()

    return api_success(CrewAssignmentSchema().dump(assignment)), 201


@api_bp.route('/crew/assignments/<int:assignment_id>', methods=['PUT'])
@jwt_required
def api_update_crew_assignment(assignment_id):
    """Update a crew assignment (status, notes, call_time).

    Updatable fields: status, call_time, notes
    """
    assignment = CrewAssignment.query.options(
        joinedload(CrewAssignment.slot),
    ).get(assignment_id)
    if not assignment:
        return api_error('not_found', 'Crew assignment not found.', 404)

    stop = TourStop.query.options(joinedload(TourStop.tour)).get(assignment.slot.tour_stop_id)
    if not stop or not stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to edit this assignment.', 403)

    data = request.get_json(silent=True) or {}

    if 'status' in data:
        try:
            new_status = AssignmentStatus(data['status'])
            assignment.status = new_status
            if new_status == AssignmentStatus.CONFIRMED:
                assignment.confirmed_at = datetime.utcnow()
        except ValueError:
            return api_error('validation_error', f"Invalid status: {data['status']}.", 422)

    if 'call_time' in data:
        def parse_time(value):
            if not value:
                return None
            from datetime import time as dt_time
            try:
                parts = value.split(':')
                return dt_time(int(parts[0]), int(parts[1]))
            except (ValueError, IndexError, AttributeError):
                return None
        assignment.call_time = parse_time(data['call_time'])

    if 'notes' in data:
        assignment.notes = data['notes'].strip() if isinstance(data['notes'], str) else data['notes']

    db.session.commit()
    return api_success(CrewAssignmentSchema().dump(assignment))


@api_bp.route('/crew/assignments/<int:assignment_id>', methods=['DELETE'])
@jwt_required
def api_delete_crew_assignment(assignment_id):
    """Remove a crew assignment."""
    assignment = CrewAssignment.query.options(
        joinedload(CrewAssignment.slot),
    ).get(assignment_id)
    if not assignment:
        return api_error('not_found', 'Crew assignment not found.', 404)

    stop = TourStop.query.options(joinedload(TourStop.tour)).get(assignment.slot.tour_stop_id)
    if not stop or not stop.can_edit(request.api_user):
        return api_error('forbidden', 'No permission to delete this assignment.', 403)

    db.session.delete(assignment)
    db.session.commit()
    return api_success({'deleted': True})


# ── Documents ─────────────────────────────────────────────

@api_bp.route('/documents', methods=['GET'])
@jwt_required
def api_list_documents():
    """List documents accessible to the current user.

    Filters: type, owner_type (user/band/tour), expiring (true = expiring_soon + expired)
    """
    user = request.api_user
    org_id = get_current_org_id()

    # Base query: documents owned by user OR shared with user OR belonging to user's tours/bands
    query = Document.query.filter(
        db.or_(
            Document.user_id == user.id,
            Document.uploaded_by_id == user.id,
            Document.id.in_(
                db.session.query(DocumentShare.document_id).filter(
                    DocumentShare.shared_to_user_id == user.id
                )
            ),
        )
    )

    # Filter by type
    doc_type = request.args.get('type')
    if doc_type:
        try:
            query = query.filter(Document.document_type == DocumentType(doc_type))
        except ValueError:
            return api_error('invalid_filter', f'Invalid type: {doc_type}', 422)

    # Filter by owner type
    owner_type = request.args.get('owner_type')
    if owner_type == 'user':
        query = query.filter(Document.user_id.isnot(None))
    elif owner_type == 'band':
        query = query.filter(Document.band_id.isnot(None))
    elif owner_type == 'tour':
        query = query.filter(Document.tour_id.isnot(None))

    # Filter expiring documents
    if request.args.get('expiring') == 'true':
        from datetime import timedelta
        threshold = date.today() + timedelta(days=90)
        query = query.filter(
            Document.expiry_date.isnot(None),
            Document.expiry_date <= threshold,
        )

    query = query.order_by(desc(Document.created_at))
    return paginate_query(query, DocumentSchema())


@api_bp.route('/documents', methods=['POST'])
@jwt_required
def api_create_document():
    """Upload a new document (multipart/form-data).

    Required: file, name, document_type
    Optional: description, user_id, band_id, tour_id, expiry_date, issue_date,
        document_number, issuing_country
    """
    import uuid
    from werkzeug.utils import secure_filename

    user = request.api_user

    if 'file' not in request.files:
        return api_error('validation_error', 'No file provided.', 422)

    file = request.files['file']
    if not file or not file.filename:
        return api_error('validation_error', 'Empty file.', 422)

    if not Document.is_allowed_file(file.filename):
        return api_error('validation_error',
                         f'File type not allowed. Allowed: {", ".join(Document.allowed_extensions())}', 422)

    # Validate file content (magic bytes)
    is_valid, error_msg = Document.validate_file_content(file, file.filename)
    if not is_valid:
        return api_error('validation_error', error_msg, 422)

    # Check file size
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if file_size > Document.max_file_size():
        return api_error('validation_error', 'File too large (max 16 MB).', 422)

    name = request.form.get('name', '').strip()
    if not name:
        return api_error('validation_error', 'name is required.', 422)

    doc_type_str = request.form.get('document_type', 'other')
    try:
        doc_type = DocumentType(doc_type_str)
    except ValueError:
        return api_error('validation_error', f'Invalid document_type: {doc_type_str}', 422)

    # Generate stored filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    stored_filename = f'{uuid.uuid4().hex}.{ext}'
    original_filename = secure_filename(file.filename)

    # Save file
    import os
    from flask import current_app
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, stored_filename)
    file.save(file_path)

    # Parse optional dates
    expiry_date = None
    if request.form.get('expiry_date'):
        try:
            expiry_date = date.fromisoformat(request.form['expiry_date'])
        except ValueError:
            pass

    issue_date = None
    if request.form.get('issue_date'):
        try:
            issue_date = date.fromisoformat(request.form['issue_date'])
        except ValueError:
            pass

    doc = Document(
        name=name,
        document_type=doc_type,
        description=request.form.get('description', '').strip() or None,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type,
        user_id=request.form.get('user_id', type=int) or user.id,
        band_id=request.form.get('band_id', type=int),
        tour_id=request.form.get('tour_id', type=int),
        expiry_date=expiry_date,
        issue_date=issue_date,
        document_number=request.form.get('document_number', '').strip() or None,
        issuing_country=request.form.get('issuing_country', '').strip() or None,
        uploaded_by_id=user.id,
    )
    db.session.add(doc)
    db.session.commit()

    return api_success(DocumentSchema().dump(doc)), 201


@api_bp.route('/documents/<int:doc_id>', methods=['GET'])
@jwt_required
def api_get_document(doc_id):
    """Get document detail."""
    doc = Document.query.options(
        joinedload(Document.uploaded_by),
    ).get(doc_id)
    if not doc:
        return api_error('not_found', 'Document not found.', 404)

    # Access check: owner, uploader, or shared with
    user = request.api_user
    if (doc.user_id != user.id
            and doc.uploaded_by_id != user.id
            and not DocumentShare.is_shared_with(doc.id, user.id)):
        return api_error('forbidden', 'No access to this document.', 403)

    return api_success(DocumentSchema().dump(doc))


@api_bp.route('/documents/<int:doc_id>', methods=['PUT'])
@jwt_required
def api_update_document(doc_id):
    """Update document metadata.

    Updatable: name, description, document_type, expiry_date, issue_date,
        document_number, issuing_country
    """
    doc = Document.query.get(doc_id)
    if not doc:
        return api_error('not_found', 'Document not found.', 404)

    user = request.api_user
    if doc.uploaded_by_id != user.id and doc.user_id != user.id:
        return api_error('forbidden', 'No permission to edit this document.', 403)

    data = request.get_json(silent=True) or {}

    if 'name' in data:
        value = data['name'].strip() if isinstance(data['name'], str) else data['name']
        if not value:
            return api_error('validation_error', 'name cannot be empty.', 422)
        doc.name = value

    if 'description' in data:
        doc.description = data['description'].strip() if isinstance(data['description'], str) else data['description']

    if 'document_type' in data:
        try:
            doc.document_type = DocumentType(data['document_type'])
        except ValueError:
            return api_error('validation_error', f"Invalid document_type.", 422)

    for date_field in ('expiry_date', 'issue_date'):
        if date_field in data:
            if data[date_field]:
                try:
                    setattr(doc, date_field, date.fromisoformat(data[date_field]))
                except (ValueError, TypeError):
                    return api_error('validation_error', f'{date_field} must be YYYY-MM-DD.', 422)
            else:
                setattr(doc, date_field, None)

    STRING_FIELDS = {'document_number', 'issuing_country'}
    for field in STRING_FIELDS:
        if field in data:
            value = data[field]
            if isinstance(value, str):
                value = value.strip() or None
            setattr(doc, field, value)

    db.session.commit()
    return api_success(DocumentSchema().dump(doc))


@api_bp.route('/documents/<int:doc_id>', methods=['DELETE'])
@jwt_required
def api_delete_document(doc_id):
    """Delete a document and its file."""
    doc = Document.query.get(doc_id)
    if not doc:
        return api_error('not_found', 'Document not found.', 404)

    user = request.api_user
    if doc.uploaded_by_id != user.id and doc.user_id != user.id:
        return api_error('forbidden', 'No permission to delete this document.', 403)

    # Delete physical file
    from flask import current_app
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    doc.delete_file(upload_folder)

    db.session.delete(doc)
    db.session.commit()
    return api_success({'deleted': True})


@api_bp.route('/documents/<int:doc_id>/share', methods=['POST'])
@jwt_required
def api_share_document(doc_id):
    """Share a document with another user.

    Required: user_id
    Optional: share_type ('view' or 'edit', defaults to 'view')
    """
    doc = Document.query.get(doc_id)
    if not doc:
        return api_error('not_found', 'Document not found.', 404)

    user = request.api_user
    if doc.uploaded_by_id != user.id and doc.user_id != user.id:
        return api_error('forbidden', 'No permission to share this document.', 403)

    data = request.get_json(silent=True) or {}
    target_user_id = data.get('user_id')
    if not target_user_id:
        return api_error('validation_error', 'user_id is required.', 422)

    if target_user_id == user.id:
        return api_error('validation_error', 'Cannot share with yourself.', 422)

    # Check if already shared
    existing = DocumentShare.get_share(doc.id, target_user_id)
    if existing:
        return api_error('conflict', 'Document already shared with this user.', 409)

    share_type = ShareType.VIEW
    if data.get('share_type') == 'edit':
        share_type = ShareType.EDIT

    share = DocumentShare(
        document_id=doc.id,
        shared_by_id=user.id,
        shared_to_user_id=target_user_id,
        share_type=share_type,
    )
    db.session.add(share)
    db.session.commit()

    return api_success({'shared': True, 'share_type': share_type.value}), 201


# ── Invoices ──────────────────────────────────────────────

@api_bp.route('/invoices', methods=['GET'])
@jwt_required
def api_list_invoices():
    """List invoices.

    Filters: status, tour_id, from_date, to_date
    """
    user = request.api_user
    query = Invoice.query.filter(
        db.or_(
            Invoice.created_by_id == user.id,
            Invoice.recipient_id == user.id,
        )
    )

    status_filter = request.args.get('status')
    if status_filter:
        try:
            query = query.filter(Invoice.status == InvoiceStatus(status_filter))
        except ValueError:
            return api_error('invalid_filter', f'Invalid status: {status_filter}', 422)

    tour_id = request.args.get('tour_id', type=int)
    if tour_id:
        query = query.filter(Invoice.tour_id == tour_id)

    from_date = request.args.get('from_date')
    if from_date:
        try:
            query = query.filter(Invoice.issue_date >= date.fromisoformat(from_date))
        except ValueError:
            pass

    to_date = request.args.get('to_date')
    if to_date:
        try:
            query = query.filter(Invoice.issue_date <= date.fromisoformat(to_date))
        except ValueError:
            pass

    query = query.order_by(desc(Invoice.created_at))
    return paginate_query(query, InvoiceSchema())


@api_bp.route('/invoices', methods=['POST'])
@jwt_required
def api_create_invoice():
    """Create a draft invoice.

    Required: recipient_name, issuer_name
    Optional: type, tour_id, tour_stop_id, recipient_*, issuer_*, payment_terms, lines[]
    """
    user = request.api_user
    data = request.get_json(silent=True) or {}

    if not data.get('recipient_name', '').strip():
        return api_error('validation_error', 'recipient_name is required.', 422)
    if not data.get('issuer_name', '').strip():
        return api_error('validation_error', 'issuer_name is required.', 422)

    # Parse type
    inv_type = InvoiceType.INVOICE
    if data.get('type'):
        try:
            inv_type = InvoiceType(data['type'])
        except ValueError:
            return api_error('validation_error', f"Invalid type: {data['type']}.", 422)

    # Generate draft number
    import uuid
    draft_number = f'BROUILLON-{uuid.uuid4().hex[:8].upper()}'

    # Parse due_date
    due_date = date.today()
    if data.get('due_date'):
        try:
            due_date = date.fromisoformat(data['due_date'])
        except (ValueError, TypeError):
            return api_error('validation_error', 'due_date must be YYYY-MM-DD.', 422)
    else:
        from datetime import timedelta
        due_date = date.today() + timedelta(days=data.get('payment_terms_days', 30))

    # Parse issue_date
    issue_date = date.today()
    if data.get('issue_date'):
        try:
            issue_date = date.fromisoformat(data['issue_date'])
        except (ValueError, TypeError):
            pass

    invoice = Invoice(
        number=draft_number,
        type=inv_type,
        status=InvoiceStatus.DRAFT,
        issue_date=issue_date,
        due_date=due_date,
        created_by_id=user.id,
        currency=data.get('currency', 'EUR'),
        tour_id=data.get('tour_id'),
        tour_stop_id=data.get('tour_stop_id'),
        payment_terms=data.get('payment_terms', 'Paiement a 30 jours'),
        payment_terms_days=data.get('payment_terms_days', 30),
    )

    # Issuer fields
    for field in ['issuer_name', 'issuer_legal_form', 'issuer_address_line1',
                  'issuer_address_line2', 'issuer_city', 'issuer_postal_code',
                  'issuer_country', 'issuer_siren', 'issuer_siret', 'issuer_vat',
                  'issuer_rcs', 'issuer_capital', 'issuer_phone', 'issuer_email',
                  'issuer_website', 'issuer_iban', 'issuer_bic']:
        if field in data:
            setattr(invoice, field, data[field])

    # Recipient fields
    for field in ['recipient_name', 'recipient_legal_form', 'recipient_address_line1',
                  'recipient_address_line2', 'recipient_city', 'recipient_postal_code',
                  'recipient_country', 'recipient_siren', 'recipient_siret',
                  'recipient_vat', 'recipient_email', 'recipient_phone']:
        if field in data:
            setattr(invoice, field, data[field])

    if data.get('recipient_id'):
        invoice.recipient_id = data['recipient_id']

    # Notes fields
    for field in ['special_mentions', 'internal_notes', 'public_notes', 'vat_mention']:
        if field in data:
            setattr(invoice, field, data[field])

    db.session.add(invoice)

    # Add lines if provided
    lines = data.get('lines', [])
    for i, line_data in enumerate(lines, start=1):
        line = InvoiceLine(
            invoice=invoice,
            line_number=line_data.get('line_number', i),
            description=line_data.get('description', ''),
            detail=line_data.get('detail'),
            reference=line_data.get('reference'),
            quantity=line_data.get('quantity', 1),
            unit=line_data.get('unit', 'unite'),
            unit_price_ht=line_data.get('unit_price_ht', 0),
            discount_percent=line_data.get('discount_percent', 0),
            vat_rate=line_data.get('vat_rate', 20.00),
        )
        line.calculate_totals()
        db.session.add(line)

    db.session.flush()
    invoice.calculate_totals()
    db.session.commit()

    return api_success(InvoiceSchema().dump(invoice)), 201


@api_bp.route('/invoices/<int:invoice_id>', methods=['GET'])
@jwt_required
def api_get_invoice(invoice_id):
    """Get invoice detail with lines."""
    invoice = Invoice.query.options(
        joinedload(Invoice.lines),
        joinedload(Invoice.tour),
    ).get(invoice_id)
    if not invoice:
        return api_error('not_found', 'Invoice not found.', 404)

    user = request.api_user
    if invoice.created_by_id != user.id and invoice.recipient_id != user.id:
        return api_error('forbidden', 'No access to this invoice.', 403)

    return api_success(InvoiceSchema().dump(invoice))


@api_bp.route('/invoices/<int:invoice_id>', methods=['PUT'])
@jwt_required
def api_update_invoice(invoice_id):
    """Update a draft invoice."""
    invoice = Invoice.query.options(joinedload(Invoice.lines)).get(invoice_id)
    if not invoice:
        return api_error('not_found', 'Invoice not found.', 404)
    if invoice.created_by_id != request.api_user.id:
        return api_error('forbidden', 'No permission to edit this invoice.', 403)
    if invoice.status != InvoiceStatus.DRAFT:
        return api_error('invalid_state', 'Only draft invoices can be edited.', 409)

    data = request.get_json(silent=True) or {}

    # Update all string fields
    ALL_FIELDS = [
        'issuer_name', 'issuer_legal_form', 'issuer_address_line1',
        'issuer_address_line2', 'issuer_city', 'issuer_postal_code',
        'issuer_country', 'issuer_siren', 'issuer_siret', 'issuer_vat',
        'issuer_rcs', 'issuer_capital', 'issuer_phone', 'issuer_email',
        'issuer_website', 'issuer_iban', 'issuer_bic',
        'recipient_name', 'recipient_legal_form', 'recipient_address_line1',
        'recipient_address_line2', 'recipient_city', 'recipient_postal_code',
        'recipient_country', 'recipient_siren', 'recipient_siret',
        'recipient_vat', 'recipient_email', 'recipient_phone',
        'payment_terms', 'special_mentions', 'internal_notes',
        'public_notes', 'vat_mention', 'currency',
    ]
    for field in ALL_FIELDS:
        if field in data:
            setattr(invoice, field, data[field])

    # Date fields
    for date_field in ('issue_date', 'due_date', 'delivery_date'):
        if date_field in data:
            if data[date_field]:
                try:
                    setattr(invoice, date_field, date.fromisoformat(data[date_field]))
                except (ValueError, TypeError):
                    return api_error('validation_error', f'{date_field} must be YYYY-MM-DD.', 422)
            else:
                setattr(invoice, date_field, None)

    # Update lines if provided
    if 'lines' in data:
        # Remove existing lines
        for line in invoice.lines:
            db.session.delete(line)

        for i, line_data in enumerate(data['lines'], start=1):
            line = InvoiceLine(
                invoice=invoice,
                line_number=line_data.get('line_number', i),
                description=line_data.get('description', ''),
                detail=line_data.get('detail'),
                reference=line_data.get('reference'),
                quantity=line_data.get('quantity', 1),
                unit=line_data.get('unit', 'unite'),
                unit_price_ht=line_data.get('unit_price_ht', 0),
                discount_percent=line_data.get('discount_percent', 0),
                vat_rate=line_data.get('vat_rate', 20.00),
            )
            line.calculate_totals()
            db.session.add(line)

        db.session.flush()
        invoice.calculate_totals()

    db.session.commit()
    return api_success(InvoiceSchema().dump(invoice))


@api_bp.route('/invoices/<int:invoice_id>', methods=['DELETE'])
@jwt_required
def api_delete_invoice(invoice_id):
    """Delete a draft invoice."""
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return api_error('not_found', 'Invoice not found.', 404)
    if invoice.created_by_id != request.api_user.id:
        return api_error('forbidden', 'No permission to delete this invoice.', 403)
    if invoice.status != InvoiceStatus.DRAFT:
        return api_error('invalid_state', 'Only draft invoices can be deleted.', 409)

    db.session.delete(invoice)
    db.session.commit()
    return api_success({'deleted': True})


@api_bp.route('/invoices/<int:invoice_id>/validate', methods=['POST'])
@jwt_required
def api_validate_invoice(invoice_id):
    """Validate an invoice (generates final number)."""
    invoice = Invoice.query.options(joinedload(Invoice.lines)).get(invoice_id)
    if not invoice:
        return api_error('not_found', 'Invoice not found.', 404)
    if invoice.created_by_id != request.api_user.id:
        return api_error('forbidden', 'No permission to validate this invoice.', 403)

    try:
        invoice.mark_as_validated(request.api_user.id)
    except ValueError as e:
        return api_error('validation_error', str(e), 422)

    db.session.commit()
    return api_success(InvoiceSchema().dump(invoice))


@api_bp.route('/invoices/<int:invoice_id>/send', methods=['POST'])
@jwt_required
def api_send_invoice(invoice_id):
    """Mark invoice as sent."""
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return api_error('not_found', 'Invoice not found.', 404)
    if invoice.created_by_id != request.api_user.id:
        return api_error('forbidden', 'No permission.', 403)

    try:
        invoice.mark_as_sent()
    except ValueError as e:
        return api_error('invalid_state', str(e), 409)

    db.session.commit()
    return api_success(InvoiceSchema().dump(invoice))


@api_bp.route('/invoices/<int:invoice_id>/payment', methods=['POST'])
@jwt_required
def api_record_invoice_payment(invoice_id):
    """Record a payment on an invoice.

    Required: amount
    Optional: payment_date, payment_method, reference, bank_reference, notes
    """
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return api_error('not_found', 'Invoice not found.', 404)
    if invoice.created_by_id != request.api_user.id:
        return api_error('forbidden', 'No permission.', 403)

    data = request.get_json(silent=True) or {}

    amount = data.get('amount')
    if not amount or float(amount) <= 0:
        return api_error('validation_error', 'amount must be positive.', 422)

    payment_date = None
    if data.get('payment_date'):
        try:
            payment_date = date.fromisoformat(data['payment_date'])
        except (ValueError, TypeError):
            return api_error('validation_error', 'payment_date must be YYYY-MM-DD.', 422)

    # Record payment on invoice
    invoice.record_payment(amount, payment_date)

    # Create payment record
    payment_record = InvoicePayment(
        invoice_id=invoice.id,
        amount=amount,
        payment_date=payment_date or date.today(),
        payment_method=data.get('payment_method'),
        reference=data.get('reference'),
        bank_reference=data.get('bank_reference'),
        notes=data.get('notes'),
        created_by_id=request.api_user.id,
    )
    db.session.add(payment_record)
    db.session.commit()

    return api_success(InvoiceSchema().dump(invoice))


# ── Calendar ──────────────────────────────────────────────

@api_bp.route('/calendar', methods=['GET'])
@jwt_required
def api_calendar():
    """Get all stops across all user's tours for calendar view.

    Params: from_date, to_date, band_id
    Returns: list of tour stops with tour and venue info.
    """
    import traceback
    try:
        user = request.api_user

        # Get all stops from org tours (via band org_id)
        org_id = get_current_org_id()
        query = TourStop.query.join(Tour).join(Band).filter(
            Band.org_id == org_id
        ).options(
            joinedload(TourStop.tour).joinedload(Tour.band),
            joinedload(TourStop.venue),
        )

        from_date_str = request.args.get('from_date')
        if from_date_str:
            try:
                query = query.filter(TourStop.date >= date.fromisoformat(from_date_str))
            except ValueError:
                pass

        to_date_str = request.args.get('to_date')
        if to_date_str:
            try:
                query = query.filter(TourStop.date <= date.fromisoformat(to_date_str))
            except ValueError:
                pass

        band_id = request.args.get('band_id', type=int)
        if band_id:
            query = query.filter(Tour.band_id == band_id)

        stops = query.order_by(TourStop.date).all()
        return api_success(TourStopSchema(many=True).dump(stops))
    except Exception as e:
        db.session.rollback()
        tb = traceback.format_exc()
        return jsonify({'error': {'code': 'debug', 'message': str(e), 'trace': tb[-500:]}}), 500


# ── Map ───────────────────────────────────────────────────

@api_bp.route('/tours/<int:tour_id>/map-data', methods=['GET'])
@jwt_required
def api_tour_map_data(tour_id):
    """Get tour stops with GPS coordinates for map display.

    Returns stops ordered chronologically with venue coordinates.
    """
    tour = Tour.query.get(tour_id)
    if not tour or not tour.can_view(request.api_user):
        return api_error('not_found', 'Tour not found.', 404)

    stops = TourStop.query.filter_by(tour_id=tour_id).options(
        joinedload(TourStop.venue),
    ).order_by(TourStop.date).all()

    markers = []
    for stop in stops:
        lat = None
        lng = None
        venue_name = None

        if stop.venue:
            lat = stop.venue.latitude
            lng = stop.venue.longitude
            venue_name = stop.venue.name

        # Skip stops without coordinates
        if lat is None or lng is None:
            continue

        markers.append({
            'stop_id': stop.id,
            'date': stop.date.isoformat() if stop.date else None,
            'city': stop.location_city or (stop.venue.city if stop.venue else None),
            'country': stop.location_country or (stop.venue.country if stop.venue else None),
            'venue_name': venue_name,
            'latitude': float(lat),
            'longitude': float(lng),
            'status': stop.status.value if stop.status else None,
            'event_type': stop.event_type.value if stop.event_type else None,
        })

    return api_success({
        'tour_id': tour.id,
        'tour_name': tour.name,
        'markers': markers,
        'total_stops': len(stops),
        'mapped_stops': len(markers),
    })


# ══════════════════════════════════════════════════════════════
# PAYMENTS — Full CRUD + Workflow
# ══════════════════════════════════════════════════════════════

@api_bp.route('/payments', methods=['GET'])
@jwt_required
def api_list_payments():
    """List payments with optional filters (status, tour_id, user_id)."""
    from app.models.payments import PaymentStatus as PS
    query = TeamMemberPayment.query.filter(
        TeamMemberPayment.user_id == request.api_user.id
    )

    status = request.args.get('status')
    if status:
        try:
            query = query.filter(TeamMemberPayment.status == PS(status))
        except ValueError:
            pass

    tour_id = request.args.get('tour_id', type=int)
    if tour_id:
        query = query.filter(TeamMemberPayment.tour_id == tour_id)

    query = query.options(
        joinedload(TeamMemberPayment.user),
        joinedload(TeamMemberPayment.tour_stop),
    ).order_by(desc(TeamMemberPayment.created_at))

    return api_success(paginate_query(query, PaymentSchema()))


@api_bp.route('/payments/<int:payment_id>', methods=['GET'])
@jwt_required
def api_get_payment(payment_id):
    """Get a single payment by ID."""
    payment = TeamMemberPayment.query.options(
        joinedload(TeamMemberPayment.user),
        joinedload(TeamMemberPayment.tour_stop),
    ).get(payment_id)
    if not payment:
        return api_error('not_found', 'Payment not found.', 404)
    if payment.user_id != request.api_user.id and not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Access denied.', 403)
    return api_success(PaymentSchema().dump(payment))


@api_bp.route('/payments', methods=['POST'])
@jwt_required
def api_create_payment():
    """Create a new payment (manager only)."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    data = request.get_json() or {}
    required = ['user_id', 'amount', 'payment_type', 'staff_category']
    missing = [f for f in required if f not in data]
    if missing:
        return api_error('validation', f'Missing fields: {", ".join(missing)}')

    from app.models.payments import PaymentType, StaffCategory, PaymentStatus as PS
    try:
        payment = TeamMemberPayment(
            user_id=data['user_id'],
            tour_id=data.get('tour_id'),
            tour_stop_id=data.get('tour_stop_id'),
            amount=data['amount'],
            currency=data.get('currency', 'EUR'),
            payment_type=PaymentType(data['payment_type']),
            staff_category=StaffCategory(data['staff_category']),
            description=data.get('description', ''),
            notes=data.get('notes', ''),
            status=PS.DRAFT,
            reference=_generate_payment_reference(),
        )
        db.session.add(payment)
        db.session.commit()
        return api_success(PaymentSchema().dump(payment), 201)
    except (ValueError, KeyError) as e:
        db.session.rollback()
        return api_error('validation', str(e))


@api_bp.route('/payments/<int:payment_id>', methods=['PUT'])
@jwt_required
def api_update_payment(payment_id):
    """Update a payment (manager only, draft/rejected only)."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    payment = TeamMemberPayment.query.get(payment_id)
    if not payment:
        return api_error('not_found', 'Payment not found.', 404)

    from app.models.payments import PaymentStatus as PS
    if payment.status not in (PS.DRAFT, PS.REJECTED):
        return api_error('conflict', 'Only draft or rejected payments can be edited.', 409)

    data = request.get_json() or {}
    for field in ['amount', 'currency', 'description', 'notes', 'tour_id', 'tour_stop_id', 'due_date']:
        if field in data:
            setattr(payment, field, data[field])

    db.session.commit()
    return api_success(PaymentSchema().dump(payment))


@api_bp.route('/payments/<int:payment_id>', methods=['DELETE'])
@jwt_required
def api_delete_payment(payment_id):
    """Delete a payment (manager only, draft only)."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    payment = TeamMemberPayment.query.get(payment_id)
    if not payment:
        return api_error('not_found', 'Payment not found.', 404)

    from app.models.payments import PaymentStatus as PS
    if payment.status != PS.DRAFT:
        return api_error('conflict', 'Only draft payments can be deleted.', 409)

    db.session.delete(payment)
    db.session.commit()
    return api_success({'deleted': True})


@api_bp.route('/payments/<int:payment_id>/submit', methods=['POST'])
@jwt_required
def api_submit_payment(payment_id):
    """Submit a payment for approval."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    payment = TeamMemberPayment.query.get(payment_id)
    if not payment:
        return api_error('not_found', 'Payment not found.', 404)

    from app.models.payments import PaymentStatus as PS
    if payment.status not in (PS.DRAFT, PS.REJECTED):
        return api_error('conflict', 'Payment cannot be submitted in current status.', 409)

    payment.status = PS.PENDING_APPROVAL
    payment.submitted_at = datetime.utcnow()
    payment.submitted_by_id = request.api_user.id
    db.session.commit()
    return api_success(PaymentSchema().dump(payment))


@api_bp.route('/payments/<int:payment_id>/approve', methods=['POST'])
@jwt_required
def api_approve_payment(payment_id):
    """Approve a pending payment."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    payment = TeamMemberPayment.query.get(payment_id)
    if not payment:
        return api_error('not_found', 'Payment not found.', 404)

    from app.models.payments import PaymentStatus as PS
    if payment.status != PS.PENDING_APPROVAL:
        return api_error('conflict', 'Payment is not pending approval.', 409)

    payment.status = PS.APPROVED
    payment.approved_by_id = request.api_user.id
    payment.approved_at = datetime.utcnow()
    db.session.commit()
    return api_success(PaymentSchema().dump(payment))


@api_bp.route('/payments/<int:payment_id>/reject', methods=['POST'])
@jwt_required
def api_reject_payment(payment_id):
    """Reject a pending payment."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    payment = TeamMemberPayment.query.get(payment_id)
    if not payment:
        return api_error('not_found', 'Payment not found.', 404)

    from app.models.payments import PaymentStatus as PS
    if payment.status != PS.PENDING_APPROVAL:
        return api_error('conflict', 'Payment is not pending approval.', 409)

    data = request.get_json() or {}
    payment.status = PS.REJECTED
    payment.rejection_reason = data.get('reason', '')
    db.session.commit()
    return api_success(PaymentSchema().dump(payment))


@api_bp.route('/payments/<int:payment_id>/mark-paid', methods=['POST'])
@jwt_required
def api_mark_payment_paid(payment_id):
    """Mark an approved payment as paid."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    payment = TeamMemberPayment.query.get(payment_id)
    if not payment:
        return api_error('not_found', 'Payment not found.', 404)

    from app.models.payments import PaymentStatus as PS
    if payment.status not in (PS.APPROVED, PS.SCHEDULED, PS.PROCESSING):
        return api_error('conflict', 'Payment must be approved first.', 409)

    data = request.get_json() or {}
    payment.status = PS.PAID
    payment.paid_date = date.today()
    payment.bank_reference = data.get('bank_reference', '')
    db.session.commit()
    return api_success(PaymentSchema().dump(payment))


@api_bp.route('/payments/<int:payment_id>/cancel', methods=['POST'])
@jwt_required
def api_cancel_payment(payment_id):
    """Cancel a payment."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    payment = TeamMemberPayment.query.get(payment_id)
    if not payment:
        return api_error('not_found', 'Payment not found.', 404)

    from app.models.payments import PaymentStatus as PS
    if payment.status == PS.PAID:
        return api_error('conflict', 'Cannot cancel a paid payment.', 409)

    payment.status = PS.CANCELLED
    db.session.commit()
    return api_success(PaymentSchema().dump(payment))


@api_bp.route('/payments/approval-queue', methods=['GET'])
@jwt_required
def api_payment_approval_queue():
    """List payments pending approval (manager only)."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    from app.models.payments import PaymentStatus as PS
    query = TeamMemberPayment.query.filter(
        TeamMemberPayment.status == PS.PENDING_APPROVAL
    ).options(
        joinedload(TeamMemberPayment.user),
        joinedload(TeamMemberPayment.tour_stop),
    ).order_by(TeamMemberPayment.submitted_at)

    return api_success(PaymentSchema().dump(query.all(), many=True))


def _generate_payment_reference():
    """Generate unique payment reference like PAY-2026-00042."""
    from app.models.payments import TeamMemberPayment as TMP
    year = datetime.utcnow().year
    last = db.session.query(func.max(TMP.id)).scalar() or 0
    return f'PAY-{year}-{last + 1:05d}'


# ══════════════════════════════════════════════════════════════
# REPORTS — Financial, Guestlist, Dashboard analytics
# ══════════════════════════════════════════════════════════════

@api_bp.route('/reports/summary', methods=['GET'])
@jwt_required
def api_reports_summary():
    """Global KPIs: tours, stops, revenue, guestlist stats."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    user = request.api_user
    user_bands = user.bands + user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    tours = Tour.query.filter(Tour.band_id.in_(user_band_ids)).all()
    stops = TourStop.query.join(Tour).filter(Tour.band_id.in_(user_band_ids)).all()

    total_revenue = sum(float(s.guarantee or 0) for s in stops)
    total_guestlist = sum(len(s.guestlist_entries) for s in stops)
    total_checked_in = sum(
        1 for s in stops for e in s.guestlist_entries
        if e.status == GuestlistStatus.CHECKED_IN
    )

    return api_success({
        'total_tours': len(tours),
        'total_stops': len(stops),
        'total_revenue': total_revenue,
        'total_guestlist': total_guestlist,
        'total_checked_in': total_checked_in,
        'fill_rate': round(total_checked_in / total_guestlist * 100, 1) if total_guestlist > 0 else 0,
    })


@api_bp.route('/reports/financial/<int:tour_id>', methods=['GET'])
@jwt_required
def api_report_financial_tour(tour_id):
    """Detailed financial report for a tour."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    tour = Tour.query.options(
        joinedload(Tour.stops),
    ).get(tour_id)
    if not tour:
        return api_error('not_found', 'Tour not found.', 404)

    stops_data = []
    total_revenue = 0
    total_tickets_sold = 0
    total_capacity = 0

    for stop in sorted(tour.stops, key=lambda s: s.date or date.min):
        fee = float(stop.guarantee or 0)
        bonus = float(stop.bonus_pct or 0) if hasattr(stop, 'bonus_pct') else 0
        sold = stop.tickets_sold or 0 if hasattr(stop, 'tickets_sold') else 0
        cap = stop.venue.capacity if stop.venue and stop.venue.capacity else 0

        total_revenue += fee
        total_tickets_sold += sold
        total_capacity += cap

        stops_data.append({
            'stop_id': stop.id,
            'date': stop.date.isoformat() if stop.date else None,
            'city': stop.location_city,
            'venue': stop.venue.name if stop.venue else None,
            'guaranteed_fee': fee,
            'bonus_percentage': bonus,
            'tickets_sold': sold,
            'capacity': cap,
            'fill_rate': round(sold / cap * 100, 1) if cap > 0 else 0,
        })

    return api_success({
        'tour_id': tour.id,
        'tour_name': tour.name,
        'total_revenue': total_revenue,
        'total_tickets_sold': total_tickets_sold,
        'total_capacity': total_capacity,
        'avg_fill_rate': round(total_tickets_sold / total_capacity * 100, 1) if total_capacity > 0 else 0,
        'stops': stops_data,
    })


@api_bp.route('/reports/guestlist', methods=['GET'])
@jwt_required
def api_report_guestlist():
    """Guestlist analytics across all tours."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    user = request.api_user
    user_bands = user.bands + user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    tours = Tour.query.filter(Tour.band_id.in_(user_band_ids)).all()
    tour_stats = []

    for tour in tours:
        stops = TourStop.query.filter_by(tour_id=tour.id).all()
        total = 0
        checked_in = 0
        pending = 0
        approved = 0
        denied = 0
        plus_ones = 0

        for stop in stops:
            for entry in stop.guestlist_entries:
                total += 1
                plus_ones += entry.plus_ones or 0
                if entry.status == GuestlistStatus.CHECKED_IN:
                    checked_in += 1
                elif entry.status == GuestlistStatus.PENDING:
                    pending += 1
                elif entry.status == GuestlistStatus.APPROVED:
                    approved += 1
                elif entry.status == GuestlistStatus.DENIED:
                    denied += 1

        if total > 0:
            tour_stats.append({
                'tour_id': tour.id,
                'tour_name': tour.name,
                'total_entries': total,
                'checked_in': checked_in,
                'pending': pending,
                'approved': approved,
                'denied': denied,
                'plus_ones': plus_ones,
            })

    return api_success(tour_stats)


# ══════════════════════════════════════════════════════════════
# SETTINGS — Password, Notifications, Professions, Users
# ══════════════════════════════════════════════════════════════

@api_bp.route('/auth/change-password', methods=['POST'])
@jwt_required
def api_change_password():
    """Change the current user's password."""
    data = request.get_json() or {}
    current_pw = data.get('current_password', '')
    new_pw = data.get('new_password', '')

    if not current_pw or not new_pw:
        return api_error('validation', 'Both current_password and new_password are required.')

    if len(new_pw) < 8:
        return api_error('validation', 'New password must be at least 8 characters.')

    user = request.api_user
    if not user.check_password(current_pw):
        return api_error('auth', 'Current password is incorrect.', 401)

    user.set_password(new_pw)
    db.session.commit()
    return api_success({'changed': True})


@api_bp.route('/auth/forgot-password', methods=['POST'])
def api_forgot_password():
    """Request a password reset email (no auth required)."""
    from app.models.user import User as UserModel
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return api_error('validation', 'Email is required.')

    user = UserModel.query.filter_by(email=email).first()
    if user:
        token = user.generate_reset_token()
        db.session.commit()
        # In production, send email with token
        # For now, just confirm the request was accepted
    # Always return success to prevent email enumeration
    return api_success({'message': 'If that email exists, a reset link has been sent.'})


@api_bp.route('/auth/reset-password', methods=['POST'])
def api_reset_password():
    """Reset password using a token."""
    from app.models.user import User as UserModel
    data = request.get_json() or {}
    token = data.get('token', '')
    new_pw = data.get('new_password', '')

    if not token or not new_pw:
        return api_error('validation', 'Token and new_password are required.')

    if len(new_pw) < 8:
        return api_error('validation', 'Password must be at least 8 characters.')

    user = UserModel.verify_reset_token(token)
    if not user:
        return api_error('auth', 'Invalid or expired token.', 401)

    user.set_password(new_pw)
    db.session.commit()
    return api_success({'reset': True})


@api_bp.route('/settings/notifications', methods=['GET'])
@jwt_required
def api_get_notification_prefs():
    """Get notification preferences for the current user."""
    user = request.api_user
    prefs = {
        'email_notifications': getattr(user, 'email_notifications', True),
        'push_notifications': getattr(user, 'push_notifications', True),
        'mission_alerts': getattr(user, 'mission_alerts', True),
        'payment_alerts': getattr(user, 'payment_alerts', True),
        'guestlist_alerts': getattr(user, 'guestlist_alerts', True),
    }
    return api_success(prefs)


@api_bp.route('/settings/notifications', methods=['PUT'])
@jwt_required
def api_update_notification_prefs():
    """Update notification preferences."""
    data = request.get_json() or {}
    user = request.api_user

    for field in ['email_notifications', 'push_notifications', 'mission_alerts',
                  'payment_alerts', 'guestlist_alerts']:
        if field in data and hasattr(user, field):
            setattr(user, field, bool(data[field]))

    db.session.commit()
    return api_success({'updated': True})


@api_bp.route('/users', methods=['GET'])
@jwt_required
def api_list_users():
    """List users (manager only)."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    from app.models.user import User as UserModel
    query = UserModel.query.order_by(UserModel.last_name)

    role = request.args.get('role')
    if role:
        try:
            query = query.filter(UserModel.access_level == AccessLevel(role))
        except ValueError:
            pass

    active = request.args.get('active')
    if active is not None:
        query = query.filter(UserModel.is_active == (active.lower() == 'true'))

    return api_success(UserSchema().dump(query.all(), many=True))


@api_bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required
def api_get_user(user_id):
    """Get a single user (manager only)."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    from app.models.user import User as UserModel
    user = UserModel.query.get(user_id)
    if not user:
        return api_error('not_found', 'User not found.', 404)
    return api_success(UserSchema().dump(user))


@api_bp.route('/users', methods=['POST'])
@jwt_required
def api_invite_user():
    """Invite a new user (manager only)."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    from app.models.user import User as UserModel
    data = request.get_json() or {}

    email = data.get('email', '').strip().lower()
    if not email:
        return api_error('validation', 'Email is required.')

    existing = UserModel.query.filter_by(email=email).first()
    if existing:
        return api_error('conflict', 'A user with this email already exists.', 409)

    user = UserModel(
        email=email,
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
        phone=data.get('phone', ''),
        is_active=False,
    )
    if data.get('role'):
        try:
            user.access_level = AccessLevel(data['role'])
        except ValueError:
            pass

    temp_pw = data.get('password', email)  # Temp password
    user.set_password(temp_pw)
    db.session.add(user)
    db.session.commit()
    return api_success(UserSchema().dump(user), 201)


@api_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required
def api_update_user(user_id):
    """Update a user (manager only)."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    from app.models.user import User as UserModel
    user = UserModel.query.get(user_id)
    if not user:
        return api_error('not_found', 'User not found.', 404)

    data = request.get_json() or {}
    for field in ['first_name', 'last_name', 'phone', 'is_active']:
        if field in data:
            setattr(user, field, data[field])

    if 'role' in data:
        try:
            user.access_level = AccessLevel(data['role'])
        except ValueError:
            pass

    db.session.commit()
    return api_success(UserSchema().dump(user))


@api_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required
def api_delete_user(user_id):
    """Delete a user (manager only)."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    from app.models.user import User as UserModel
    user = UserModel.query.get(user_id)
    if not user:
        return api_error('not_found', 'User not found.', 404)

    if user.id == request.api_user.id:
        return api_error('conflict', 'Cannot delete yourself.', 409)

    db.session.delete(user)
    db.session.commit()
    return api_success({'deleted': True})


@api_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@jwt_required
def api_approve_user(user_id):
    """Approve a pending user registration."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    from app.models.user import User as UserModel
    user = UserModel.query.get(user_id)
    if not user:
        return api_error('not_found', 'User not found.', 404)

    user.is_active = True
    user.email_verified = True
    db.session.commit()
    return api_success(UserSchema().dump(user))


@api_bp.route('/users/<int:user_id>/reject', methods=['POST'])
@jwt_required
def api_reject_user(user_id):
    """Reject a pending user registration."""
    if not request.api_user.is_manager_or_above():
        return api_error('forbidden', 'Manager access required.', 403)

    from app.models.user import User as UserModel
    user = UserModel.query.get(user_id)
    if not user:
        return api_error('not_found', 'User not found.', 404)

    user.is_active = False
    db.session.commit()
    return api_success({'rejected': True})


# ══════════════════════════════════════════════════════════════
# TOURS — Advanced (duplicate, reschedule, copy-crew, export)
# ══════════════════════════════════════════════════════════════

@api_bp.route('/tours/<int:tour_id>/duplicate', methods=['POST'])
@jwt_required
def api_duplicate_tour(tour_id):
    """Duplicate a tour with all its stops."""
    tour = Tour.query.options(joinedload(Tour.stops)).get(tour_id)
    if not tour or not tour.can_view(request.api_user):
        return api_error('not_found', 'Tour not found.', 404)

    new_tour = Tour(
        name=f'{tour.name} (copie)',
        band_id=tour.band_id,
        start_date=tour.start_date,
        end_date=tour.end_date,
        status=TourStatus.DRAFT,
        notes=tour.notes,
        created_by_id=request.api_user.id,
    )
    db.session.add(new_tour)
    db.session.flush()

    for stop in tour.stops:
        new_stop = TourStop(
            tour_id=new_tour.id,
            venue_id=stop.venue_id,
            date=stop.date,
            city=stop.city,
            country=stop.country,
            event_type=stop.event_type,
            status=stop.status,
            guaranteed_fee=stop.guaranteed_fee,
            capacity=stop.capacity,
            notes=stop.notes,
        )
        db.session.add(new_stop)

    db.session.commit()
    return api_success(TourSchema().dump(new_tour), 201)


@api_bp.route('/stops/<int:stop_id>/reschedule', methods=['POST'])
@jwt_required
def api_reschedule_stop(stop_id):
    """Reschedule a stop to a new date."""
    stop = TourStop.query.get(stop_id)
    if not stop:
        return api_error('not_found', 'Stop not found.', 404)

    data = request.get_json() or {}
    new_date = data.get('date')
    if not new_date:
        return api_error('validation', 'New date is required.')

    try:
        stop.date = date.fromisoformat(new_date)
    except ValueError:
        return api_error('validation', 'Invalid date format. Use YYYY-MM-DD.')

    db.session.commit()
    return api_success(TourStopSchema().dump(stop))


@api_bp.route('/stops/<int:stop_id>/copy-crew', methods=['POST'])
@jwt_required
def api_copy_crew(stop_id):
    """Copy crew slots from another stop."""
    stop = TourStop.query.get(stop_id)
    if not stop:
        return api_error('not_found', 'Destination stop not found.', 404)

    data = request.get_json() or {}
    source_id = data.get('source_stop_id')
    if not source_id:
        return api_error('validation', 'source_stop_id is required.')

    source = TourStop.query.get(source_id)
    if not source:
        return api_error('not_found', 'Source stop not found.', 404)

    source_slots = CrewScheduleSlot.query.filter_by(stop_id=source_id).all()
    created = 0
    for slot in source_slots:
        new_slot = CrewScheduleSlot(
            stop_id=stop_id,
            role_name=slot.role_name,
            department=slot.department,
            required_count=slot.required_count,
            start_time=slot.start_time,
            end_time=slot.end_time,
            notes=slot.notes,
        )
        db.session.add(new_slot)
        created += 1

    db.session.commit()
    return api_success({'copied_slots': created})


# ══════════════════════════════════════════════════════════════
# GUESTLIST — Advanced (approve, deny, undo, bulk, export)
# ══════════════════════════════════════════════════════════════

@api_bp.route('/guestlist/<int:entry_id>/approve', methods=['POST'])
@jwt_required
def api_approve_guestlist_entry(entry_id):
    """Approve a guestlist entry."""
    entry = GuestlistEntry.query.get(entry_id)
    if not entry:
        return api_error('not_found', 'Entry not found.', 404)

    entry.status = GuestlistStatus.APPROVED
    db.session.commit()
    return api_success(GuestlistEntrySchema().dump(entry))


@api_bp.route('/guestlist/<int:entry_id>/deny', methods=['POST'])
@jwt_required
def api_deny_guestlist_entry(entry_id):
    """Deny a guestlist entry."""
    entry = GuestlistEntry.query.get(entry_id)
    if not entry:
        return api_error('not_found', 'Entry not found.', 404)

    entry.status = GuestlistStatus.DENIED
    db.session.commit()
    return api_success(GuestlistEntrySchema().dump(entry))


@api_bp.route('/guestlist/<int:entry_id>/undo-checkin', methods=['POST'])
@jwt_required
def api_undo_checkin(entry_id):
    """Undo a check-in (revert to approved)."""
    entry = GuestlistEntry.query.get(entry_id)
    if not entry:
        return api_error('not_found', 'Entry not found.', 404)

    if entry.status != GuestlistStatus.CHECKED_IN:
        return api_error('conflict', 'Entry is not checked in.', 409)

    entry.status = GuestlistStatus.APPROVED
    entry.checked_in_at = None
    db.session.commit()
    return api_success(GuestlistEntrySchema().dump(entry))


@api_bp.route('/stops/<int:stop_id>/guestlist/bulk', methods=['POST'])
@jwt_required
def api_bulk_guestlist(stop_id):
    """Bulk action on guestlist entries (approve_all, deny_all, delete_all)."""
    data = request.get_json() or {}
    action = data.get('action')
    entry_ids = data.get('entry_ids', [])

    if action not in ('approve_all', 'deny_all', 'delete_all'):
        return api_error('validation', 'action must be approve_all, deny_all, or delete_all.')

    query = GuestlistEntry.query.filter(
        GuestlistEntry.stop_id == stop_id,
    )
    if entry_ids:
        query = query.filter(GuestlistEntry.id.in_(entry_ids))

    entries = query.all()
    count = len(entries)

    if action == 'approve_all':
        for e in entries:
            e.status = GuestlistStatus.APPROVED
    elif action == 'deny_all':
        for e in entries:
            e.status = GuestlistStatus.DENIED
    elif action == 'delete_all':
        for e in entries:
            db.session.delete(e)

    db.session.commit()
    return api_success({'action': action, 'affected': count})


# ══════════════════════════════════════════════════════════════
# NOTIFICATIONS — Advanced (delete, delete-all, delete-read)
# ══════════════════════════════════════════════════════════════

@api_bp.route('/notifications/<int:notif_id>', methods=['DELETE'])
@jwt_required
def api_delete_notification(notif_id):
    """Delete a single notification."""
    notif = Notification.query.get(notif_id)
    if not notif or notif.user_id != request.api_user.id:
        return api_error('not_found', 'Notification not found.', 404)

    db.session.delete(notif)
    db.session.commit()
    return api_success({'deleted': True})


@api_bp.route('/notifications/delete-all', methods=['POST'])
@jwt_required
def api_delete_all_notifications():
    """Delete all notifications for the current user."""
    count = Notification.query.filter_by(user_id=request.api_user.id).delete()
    db.session.commit()
    return api_success({'deleted': count})


@api_bp.route('/notifications/delete-read', methods=['POST'])
@jwt_required
def api_delete_read_notifications():
    """Delete all read notifications for the current user."""
    count = Notification.query.filter_by(
        user_id=request.api_user.id,
        is_read=True,
    ).delete()
    db.session.commit()
    return api_success({'deleted': count})


# ══════════════════════════════════════════════════════════════
# INVOICES — Advanced (lines, cancel, overdue, send-email)
# ══════════════════════════════════════════════════════════════

@api_bp.route('/invoices/<int:invoice_id>/lines', methods=['POST'])
@jwt_required
def api_add_invoice_line(invoice_id):
    """Add a line to an invoice."""
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return api_error('not_found', 'Invoice not found.', 404)

    if invoice.status != InvoiceStatus.DRAFT:
        return api_error('conflict', 'Cannot modify a non-draft invoice.', 409)

    data = request.get_json() or {}
    line = InvoiceLine(
        invoice_id=invoice_id,
        description=data.get('description', ''),
        quantity=data.get('quantity', 1),
        unit_price=data.get('unit_price', 0),
        tax_rate=data.get('tax_rate', 0),
    )
    db.session.add(line)

    # Recalculate invoice total
    invoice.recalculate_total()
    db.session.commit()
    return api_success(InvoiceLineSchema().dump(line), 201)


@api_bp.route('/invoices/<int:invoice_id>/lines/<int:line_id>', methods=['DELETE'])
@jwt_required
def api_delete_invoice_line(invoice_id, line_id):
    """Delete a line from an invoice."""
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return api_error('not_found', 'Invoice not found.', 404)

    if invoice.status != InvoiceStatus.DRAFT:
        return api_error('conflict', 'Cannot modify a non-draft invoice.', 409)

    line = InvoiceLine.query.filter_by(id=line_id, invoice_id=invoice_id).first()
    if not line:
        return api_error('not_found', 'Line not found.', 404)

    db.session.delete(line)
    invoice.recalculate_total()
    db.session.commit()
    return api_success({'deleted': True})


@api_bp.route('/invoices/<int:invoice_id>/cancel', methods=['POST'])
@jwt_required
def api_cancel_invoice(invoice_id):
    """Cancel an invoice."""
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return api_error('not_found', 'Invoice not found.', 404)

    if invoice.status in (InvoiceStatus.PAID,):
        return api_error('conflict', 'Cannot cancel a paid invoice.', 409)

    invoice.status = InvoiceStatus.CANCELLED
    db.session.commit()
    return api_success(InvoiceSchema().dump(invoice))


@api_bp.route('/invoices/<int:invoice_id>/mark-overdue', methods=['POST'])
@jwt_required
def api_mark_invoice_overdue(invoice_id):
    """Mark an invoice as overdue."""
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return api_error('not_found', 'Invoice not found.', 404)

    invoice.status = InvoiceStatus.OVERDUE
    db.session.commit()
    return api_success(InvoiceSchema().dump(invoice))
