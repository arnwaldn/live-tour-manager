"""
Logistics management routes.
"""
from datetime import datetime, time, timedelta
from flask import render_template, redirect, url_for, flash, request, make_response, Response
from flask_login import login_required, current_user

from sqlalchemy.orm import joinedload, selectinload

from app.blueprints.logistics import logistics_bp
from app.blueprints.logistics.forms import LogisticsInfoForm, LocalContactForm, LogisticsAssignmentForm
from app.models.tour import Tour
from app.models.tour_stop import TourStop
from app.models.logistics import LogisticsInfo, LogisticsType, LogisticsStatus, LocalContact, LogisticsAssignment
from app.models.user import User
from app.utils.geocoding import geocode_address
from app.extensions import db
from app.decorators import tour_access_required, tour_edit_required
from app.utils.audit import log_create, log_update, log_delete
from app.utils.org_context import get_org_users


def get_visible_logistics(stop, user):
    """Return logistics items visible to user.

    Manager sees all, others see only assigned items.

    Args:
        stop: TourStop object
        user: Current user

    Returns:
        List of LogisticsInfo items visible to user
    """
    # Manager du groupe voit tout
    if stop.tour and stop.tour.band_is_manager(user):
        return list(stop.logistics)

    # Manager ou admin voit tout
    if user.is_manager_or_above():
        return list(stop.logistics)

    # Autres: seulement les items ou ils sont assignes
    return [item for item in stop.logistics if item.is_user_assigned(user)]


@logistics_bp.route('/stop/<int:stop_id>')
@login_required
def manage(stop_id):
    """View logistics for a tour stop."""
    # Eager-load logistics and local_contacts to avoid N+1
    stop = TourStop.query.options(
        selectinload(TourStop.logistics),
        selectinload(TourStop.local_contacts),
        joinedload(TourStop.tour),
    ).get_or_404(stop_id)
    tour = stop.tour

    # Check access to tour
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('main.dashboard'))

    # Check if user is manager (for full visibility)
    is_manager = tour.band_is_manager(current_user) or current_user.is_manager_or_above()

    # Get visible logistics based on user role
    visible_logistics = get_visible_logistics(stop, current_user)

    # Group logistics by type
    logistics_by_type = {}
    for item in visible_logistics:
        type_name = item.logistics_type.value
        if type_name not in logistics_by_type:
            logistics_by_type[type_name] = []
        logistics_by_type[type_name].append(item)

    # Calculate costs by type (only for visible items)
    costs_by_type = {}
    total_cost = 0
    for item in visible_logistics:
        type_label = _get_logistics_title(item)
        cost = item.cost or 0
        if type_label not in costs_by_type:
            costs_by_type[type_label] = 0
        costs_by_type[type_label] += float(cost)
        total_cost += float(cost)

    # Sort contacts by primary status
    contacts = sorted(stop.local_contacts, key=lambda c: (not c.is_primary, c.name))

    return render_template(
        'logistics/manage.html',
        tour=tour,
        stop=stop,
        logistics_by_type=logistics_by_type,
        logistics_entries=visible_logistics,
        costs_by_type=costs_by_type,
        total_cost=total_cost,
        contacts=contacts,
        is_manager=is_manager
    )


@logistics_bp.route('/stop/<int:stop_id>/add', methods=['GET', 'POST'])
@login_required
def add_logistics(stop_id):
    """Add logistics info to a tour stop."""
    stop = TourStop.query.get_or_404(stop_id)
    tour = stop.tour

    # Check access and permission
    if not tour.band_is_manager(current_user):
        flash('Seul le manager peut ajouter des informations logistiques.', 'error')
        return redirect(url_for('logistics.manage', stop_id=stop_id))

    form = LogisticsInfoForm()

    # Load available users for assignment
    available_users = get_org_users().order_by(User.first_name, User.last_name).all()
    form.assigned_users.choices = [(u.id, f"{u.first_name} {u.last_name}") for u in available_users]

    if form.validate_on_submit():
        # Parse status from form
        status_value = form.status.data if form.status.data else 'PENDING'
        try:
            status = LogisticsStatus[status_value]
        except KeyError:
            status = LogisticsStatus.PENDING

        logistics = LogisticsInfo(
            tour_stop_id=stop_id,
            logistics_type=LogisticsType[form.logistics_type.data],
            status=status,
            provider=form.provider.data,
            confirmation_number=form.confirmation_number.data,
            start_datetime=form.start_datetime.data,
            end_datetime=form.end_datetime.data,
            # Location
            address=form.address.data,
            city=form.city.data,
            country=form.country.data,
            # Flight specific
            flight_number=form.flight_number.data,
            departure_airport=form.departure_airport.data,
            arrival_airport=form.arrival_airport.data,
            departure_terminal=form.departure_terminal.data,
            arrival_terminal=form.arrival_terminal.data,
            # Hotel specific
            room_type=form.room_type.data if form.room_type.data else None,
            number_of_rooms=form.number_of_rooms.data,
            breakfast_included=form.breakfast_included.data,
            check_in_time=form.check_in_time.data,
            check_out_time=form.check_out_time.data,
            # Ground transport specific
            pickup_location=form.pickup_location.data,
            dropoff_location=form.dropoff_location.data,
            vehicle_type=form.vehicle_type.data if form.vehicle_type.data else None,
            driver_name=form.driver_name.data,
            driver_phone=form.driver_phone.data,
            # Contact
            contact_name=form.contact_name.data,
            contact_phone=form.contact_phone.data,
            contact_email=form.contact_email.data,
            # Cost
            cost=form.cost.data,
            currency=form.currency.data,
            is_paid=form.is_paid.data,
            paid_by=form.paid_by.data if form.paid_by.data else None,
            # Notes
            notes=form.notes.data
        )

        # Use frontend coordinates IN PRIORITY (from autocomplete)
        frontend_lat = request.form.get('latitude')
        frontend_lng = request.form.get('longitude')

        if frontend_lat and frontend_lng:
            try:
                logistics.latitude = float(frontend_lat)
                logistics.longitude = float(frontend_lng)
            except (ValueError, TypeError):
                pass  # Fallback to geocoding

        # Fallback: Auto-geocoding if no frontend coordinates
        if logistics.latitude is None and logistics.address and logistics.city:
            coords = geocode_address(logistics.address, logistics.city, logistics.country or '')
            if coords:
                logistics.latitude = coords[0]
                logistics.longitude = coords[1]

        # Auto-fill airport coordinates from known airports
        if logistics.logistics_type == LogisticsType.FLIGHT:
            _fill_airport_coordinates(logistics)

        # For ground transports: save departure/arrival GPS from frontend autocomplete
        if logistics.is_transport and logistics.logistics_type != LogisticsType.FLIGHT:
            dep_lat = request.form.get('departure_lat')
            dep_lng = request.form.get('departure_lng')
            arr_lat = request.form.get('arrival_lat')
            arr_lng = request.form.get('arrival_lng')

            if dep_lat and dep_lng:
                try:
                    logistics.departure_lat = float(dep_lat)
                    logistics.departure_lng = float(dep_lng)
                except (ValueError, TypeError):
                    pass

            if arr_lat and arr_lng:
                try:
                    logistics.arrival_lat = float(arr_lat)
                    logistics.arrival_lng = float(arr_lng)
                except (ValueError, TypeError):
                    pass

        db.session.add(logistics)
        db.session.flush()  # Get the ID before committing

        # Handle user assignments
        assigned_user_ids = request.form.getlist('assigned_users', type=int)
        for user_id in assigned_user_ids:
            assignment = LogisticsAssignment(
                logistics_info_id=logistics.id,
                user_id=user_id,
                assigned_by_id=current_user.id
            )
            db.session.add(assignment)

        db.session.commit()

        log_create('LogisticsInfo', logistics.id, {
            'type': logistics.logistics_type.value,
            'tour_stop_id': stop_id,
            'assigned_users': assigned_user_ids
        })

        flash('Information logistique ajoutée.', 'success')

        # Handle "Save and Add" button
        if request.form.get('save_add'):
            return redirect(url_for('logistics.add_logistics', stop_id=stop_id))

        return redirect(url_for('logistics.manage', stop_id=stop_id))

    return render_template(
        'logistics/logistics_form.html',
        form=form,
        tour=tour,
        stop=stop,
        available_users=available_users,
        title='Ajouter une info logistique'
    )


@logistics_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_logistics(id):
    """Edit logistics info."""
    logistics = LogisticsInfo.query.get_or_404(id)
    stop = logistics.tour_stop
    tour = stop.tour

    # Check permission
    if not tour.band_is_manager(current_user):
        flash('Seul le manager peut modifier les informations logistiques.', 'error')
        return redirect(url_for('logistics.manage', stop_id=stop.id))

    form = LogisticsInfoForm(obj=logistics)

    # Load available users for assignment
    available_users = get_org_users().order_by(User.first_name, User.last_name).all()
    form.assigned_users.choices = [(u.id, f"{u.first_name} {u.last_name}") for u in available_users]

    # Pre-fill select fields with current values
    if request.method == 'GET':
        form.logistics_type.data = logistics.logistics_type.name
        form.status.data = logistics.status.name if logistics.status else 'PENDING'
        form.room_type.data = logistics.room_type or ''
        form.vehicle_type.data = logistics.vehicle_type or ''
        form.paid_by.data = logistics.paid_by or ''
        # Pre-fill assigned users
        form.assigned_users.data = [a.user_id for a in logistics.assignments]

    if form.validate_on_submit():
        # Parse status from form
        status_value = form.status.data if form.status.data else 'PENDING'
        try:
            logistics.status = LogisticsStatus[status_value]
        except KeyError:
            logistics.status = LogisticsStatus.PENDING

        logistics.logistics_type = LogisticsType[form.logistics_type.data]
        logistics.provider = form.provider.data
        logistics.confirmation_number = form.confirmation_number.data
        logistics.start_datetime = form.start_datetime.data
        logistics.end_datetime = form.end_datetime.data

        # Location
        old_address = logistics.address
        old_city = logistics.city
        logistics.address = form.address.data
        logistics.city = form.city.data
        logistics.country = form.country.data

        # Flight specific
        logistics.flight_number = form.flight_number.data
        logistics.departure_airport = form.departure_airport.data
        logistics.arrival_airport = form.arrival_airport.data
        logistics.departure_terminal = form.departure_terminal.data
        logistics.arrival_terminal = form.arrival_terminal.data

        # Hotel specific
        logistics.room_type = form.room_type.data if form.room_type.data else None
        logistics.number_of_rooms = form.number_of_rooms.data
        logistics.breakfast_included = form.breakfast_included.data
        logistics.check_in_time = form.check_in_time.data
        logistics.check_out_time = form.check_out_time.data

        # Ground transport specific
        logistics.pickup_location = form.pickup_location.data
        logistics.dropoff_location = form.dropoff_location.data
        logistics.vehicle_type = form.vehicle_type.data if form.vehicle_type.data else None
        logistics.driver_name = form.driver_name.data
        logistics.driver_phone = form.driver_phone.data

        # Contact
        logistics.contact_name = form.contact_name.data
        logistics.contact_phone = form.contact_phone.data
        logistics.contact_email = form.contact_email.data

        # Cost
        logistics.cost = form.cost.data
        logistics.currency = form.currency.data
        logistics.is_paid = form.is_paid.data
        logistics.paid_by = form.paid_by.data if form.paid_by.data else None

        # Notes
        logistics.notes = form.notes.data

        # Use frontend coordinates IN PRIORITY (from autocomplete)
        frontend_lat = request.form.get('latitude')
        frontend_lng = request.form.get('longitude')

        if frontend_lat and frontend_lng:
            try:
                logistics.latitude = float(frontend_lat)
                logistics.longitude = float(frontend_lng)
            except (ValueError, TypeError):
                pass  # Fallback to geocoding
        else:
            # Fallback: Re-geocode if address changed and no frontend coords
            address_changed = (logistics.address != old_address or logistics.city != old_city)
            if address_changed and logistics.address and logistics.city:
                coords = geocode_address(logistics.address, logistics.city, logistics.country or '')
                if coords:
                    logistics.latitude = coords[0]
                    logistics.longitude = coords[1]

        # Re-fill airport coordinates if flight
        if logistics.logistics_type == LogisticsType.FLIGHT:
            _fill_airport_coordinates(logistics)

        # For ground transports: save departure/arrival GPS from frontend autocomplete
        if logistics.is_transport and logistics.logistics_type != LogisticsType.FLIGHT:
            dep_lat = request.form.get('departure_lat')
            dep_lng = request.form.get('departure_lng')
            arr_lat = request.form.get('arrival_lat')
            arr_lng = request.form.get('arrival_lng')

            if dep_lat and dep_lng:
                try:
                    logistics.departure_lat = float(dep_lat)
                    logistics.departure_lng = float(dep_lng)
                except (ValueError, TypeError):
                    pass

            if arr_lat and arr_lng:
                try:
                    logistics.arrival_lat = float(arr_lat)
                    logistics.arrival_lng = float(arr_lng)
                except (ValueError, TypeError):
                    pass

        # Handle user assignments - sync with form data
        new_assigned_user_ids = set(request.form.getlist('assigned_users', type=int))
        existing_user_ids = {a.user_id for a in logistics.assignments}

        # Remove unassigned users
        for assignment in list(logistics.assignments):
            if assignment.user_id not in new_assigned_user_ids:
                db.session.delete(assignment)

        # Add new assignments
        for user_id in new_assigned_user_ids:
            if user_id not in existing_user_ids:
                assignment = LogisticsAssignment(
                    logistics_info_id=logistics.id,
                    user_id=user_id,
                    assigned_by_id=current_user.id
                )
                db.session.add(assignment)

        db.session.commit()

        log_update('LogisticsInfo', logistics.id)

        flash('Information logistique mise à jour.', 'success')
        return redirect(url_for('logistics.manage', stop_id=stop.id))

    return render_template(
        'logistics/logistics_form.html',
        form=form,
        logistics=logistics,
        tour=tour,
        stop=stop,
        available_users=available_users,
        title='Modifier l\'info logistique'
    )


@logistics_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_logistics(id):
    """Delete logistics info."""
    logistics = LogisticsInfo.query.get_or_404(id)
    stop = logistics.tour_stop
    tour = stop.tour

    # Check permission
    if not tour.band_is_manager(current_user):
        flash('Seul le manager peut supprimer les informations logistiques.', 'error')
        return redirect(url_for('logistics.manage', stop_id=stop.id))

    log_delete('LogisticsInfo', logistics.id, {'type': logistics.logistics_type.value})

    db.session.delete(logistics)
    db.session.commit()

    flash('Information logistique supprimée.', 'success')
    return redirect(url_for('logistics.manage', stop_id=stop.id))


@logistics_bp.route('/<int:id>/status', methods=['POST'])
@login_required
def update_status(id):
    """Quick status update for logistics item."""
    logistics = LogisticsInfo.query.get_or_404(id)
    stop = logistics.tour_stop
    tour = stop.tour

    # Check permission
    if not tour.band_is_manager(current_user):
        flash('Seul le manager peut modifier le statut.', 'error')
        return redirect(url_for('logistics.manage', stop_id=stop.id))

    # Get new status from form
    new_status = request.form.get('status', '').upper()

    try:
        logistics.status = LogisticsStatus[new_status]
        db.session.commit()

        status_labels = {
            'PENDING': 'En attente',
            'BOOKED': 'Réservé',
            'CONFIRMED': 'Confirmé',
            'COMPLETED': 'Terminé',
            'CANCELLED': 'Annulé'
        }
        label = status_labels.get(new_status, new_status)
        flash(f'Statut mis à jour: {label}', 'success')

    except KeyError:
        flash(f'Statut invalide: {new_status}', 'error')

    return redirect(url_for('logistics.manage', stop_id=stop.id))


# Local Contacts
@logistics_bp.route('/stop/<int:stop_id>/contacts/add', methods=['GET', 'POST'])
@login_required
def add_contact(stop_id):
    """Add a local contact to a tour stop."""
    stop = TourStop.query.get_or_404(stop_id)
    tour = stop.tour

    # Check permission
    if not tour.band_is_manager(current_user):
        flash('Seul le manager peut ajouter des contacts locaux.', 'error')
        return redirect(url_for('logistics.manage', stop_id=stop_id))

    form = LocalContactForm()

    if form.validate_on_submit():
        contact = LocalContact(
            tour_stop_id=stop_id,
            name=form.name.data,
            role=form.role.data or None,
            company=form.company.data,
            email=form.email.data,
            phone=form.phone.data,
            phone_secondary=form.phone_secondary.data,
            notes=form.notes.data,
            is_primary=form.is_primary.data == '1'
        )
        db.session.add(contact)
        db.session.commit()

        log_create('LocalContact', contact.id, {
            'name': contact.name,
            'tour_stop_id': stop_id
        })

        flash(f'Contact "{contact.name}" ajouté.', 'success')
        return redirect(url_for('logistics.manage', stop_id=stop_id))

    return render_template(
        'logistics/contact_form.html',
        form=form,
        tour=tour,
        stop=stop,
        title='Ajouter un contact local'
    )


@logistics_bp.route('/contacts/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_contact(id):
    """Edit a local contact."""
    contact = LocalContact.query.get_or_404(id)
    stop = contact.tour_stop
    tour = stop.tour

    # Check permission
    if not tour.band_is_manager(current_user):
        flash('Seul le manager peut modifier les contacts locaux.', 'error')
        return redirect(url_for('logistics.manage', stop_id=stop.id))

    form = LocalContactForm(obj=contact)
    form.is_primary.data = '1' if contact.is_primary else '0'

    if form.validate_on_submit():
        contact.name = form.name.data
        contact.role = form.role.data or None
        contact.company = form.company.data
        contact.email = form.email.data
        contact.phone = form.phone.data
        contact.phone_secondary = form.phone_secondary.data
        contact.notes = form.notes.data
        contact.is_primary = form.is_primary.data == '1'

        db.session.commit()

        flash('Contact mis à jour.', 'success')
        return redirect(url_for('logistics.manage', stop_id=stop.id))

    return render_template(
        'logistics/contact_form.html',
        form=form,
        contact=contact,
        tour=tour,
        stop=stop,
        title='Modifier le contact'
    )


@logistics_bp.route('/contacts/<int:id>/delete', methods=['POST'])
@login_required
def delete_contact(id):
    """Delete a local contact."""
    contact = LocalContact.query.get_or_404(id)
    stop = contact.tour_stop
    tour = stop.tour

    # Check permission
    if not tour.band_is_manager(current_user):
        flash('Seul le manager peut supprimer les contacts locaux.', 'error')
        return redirect(url_for('logistics.manage', stop_id=stop.id))

    contact_name = contact.name
    log_delete('LocalContact', contact.id, {'name': contact_name})

    db.session.delete(contact)
    db.session.commit()

    flash(f'Contact "{contact_name}" supprimé.', 'success')
    return redirect(url_for('logistics.manage', stop_id=stop.id))


# Day Sheet View
@logistics_bp.route('/stop/<int:stop_id>/day-sheet')
@login_required
def day_sheet(stop_id):
    """View day sheet for a tour stop."""
    # Eager-load logistics, contacts, members, venue, guestlist for day sheet
    stop = TourStop.query.options(
        joinedload(TourStop.venue),
        joinedload(TourStop.tour),
        selectinload(TourStop.logistics),
        selectinload(TourStop.local_contacts),
        selectinload(TourStop.assigned_members),
        selectinload(TourStop.guestlist_entries),
    ).get_or_404(stop_id)
    tour = stop.tour

    # Check access to tour
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('main.dashboard'))

    # Get visible logistics based on user role
    visible_logistics = get_visible_logistics(stop, current_user)

    # Organize logistics by type for display
    logistics_data = {
        'transport': [],
        'accommodation': [],
        'other': []
    }

    for item in visible_logistics:
        if item.logistics_type in [LogisticsType.FLIGHT, LogisticsType.TRAIN,
                                   LogisticsType.BUS, LogisticsType.RENTAL_CAR,
                                   LogisticsType.GROUND_TRANSPORT, LogisticsType.FERRY]:
            logistics_data['transport'].append(item)
        elif item.logistics_type == LogisticsType.HOTEL:
            logistics_data['accommodation'].append(item)
        else:
            logistics_data['other'].append(item)

    # Sort transport by start time
    logistics_data['transport'].sort(key=lambda x: x.start_datetime or x.created_at)

    # Primary contacts first
    contacts = sorted(stop.local_contacts, key=lambda c: (not c.is_primary, c.name))

    # Get crew members (assigned or all band members)
    crew_members = []
    if stop.assigned_members:
        crew_members = list(stop.assigned_members)
    elif tour.band:
        crew_members = tour.band.members
        # Also include manager if not already in members
        if tour.band.manager and tour.band.manager not in crew_members:
            crew_members = [tour.band.manager] + list(crew_members)

    # Aggregate meal preferences for catering
    meal_counts = {}
    seat_counts = {}
    dietary_notes = []
    allergy_notes = []

    for member in crew_members:
        # Meal preferences
        meal = member.meal_preference or 'standard'
        meal_counts[meal] = meal_counts.get(meal, 0) + 1

        # Seat preferences
        seat = member.seat_preference
        if seat:
            seat_counts[seat] = seat_counts.get(seat, 0) + 1

        # Dietary restrictions
        if member.dietary_restrictions:
            dietary_notes.append(f"{member.first_name}: {member.dietary_restrictions}")

        # Allergies
        if member.allergies:
            allergy_notes.append(f"{member.first_name}: {member.allergies}")

    # Guestlist statistics
    from app.models.guestlist import GuestlistStatus
    guestlist_entries = stop.guestlist_entries
    guestlist_approved = sum(1 for e in guestlist_entries if e.status == GuestlistStatus.APPROVED)
    guestlist_pending = sum(1 for e in guestlist_entries if e.status == GuestlistStatus.PENDING)
    guestlist_checked_in = sum(1 for e in guestlist_entries if e.status == GuestlistStatus.CHECKED_IN)
    guestlist_count = guestlist_approved + guestlist_checked_in

    return render_template(
        'logistics/day_sheet.html',
        tour=tour,
        stop=stop,
        logistics=logistics_data,
        logistics_entries=visible_logistics,  # Filtered by user role
        local_contacts=contacts,
        contacts=contacts,
        # Crew data (Phase 1)
        crew_members=crew_members,
        meal_counts=meal_counts,
        seat_counts=seat_counts,
        dietary_notes=dietary_notes,
        allergy_notes=allergy_notes,
        # Guestlist stats
        guestlist_count=guestlist_count,
        guestlist_approved=guestlist_approved,
        guestlist_pending=guestlist_pending,
        guestlist_checked_in=guestlist_checked_in,
        now=datetime.now()
    )


# Travel Itinerary View (Phase 2)
@logistics_bp.route('/stop/<int:stop_id>/itinerary')
@login_required
def travel_itinerary(stop_id):
    """Unified travel itinerary view - all transport, hotels, call times in one timeline."""
    # Eager-load logistics, venue, contacts for itinerary timeline
    stop = TourStop.query.options(
        joinedload(TourStop.venue),
        joinedload(TourStop.tour),
        selectinload(TourStop.logistics),
        selectinload(TourStop.local_contacts),
    ).get_or_404(stop_id)
    tour = stop.tour

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Acces non autorise.', 'error')
        return redirect(url_for('main.dashboard'))

    # Get visible logistics based on user role
    visible_logistics = get_visible_logistics(stop, current_user)

    # Build timeline events
    timeline = []

    # Add logistics events (transport, hotels)
    for item in visible_logistics:
        if item.start_datetime:
            event = {
                'time': item.start_datetime,
                'type': item.logistics_type.value,
                'title': _get_logistics_title(item),
                'subtitle': item.provider or '',
                'details': [],
                'icon': _get_logistics_icon(item.logistics_type),
                'color': _get_logistics_color(item.logistics_type),
                'maps_url': None,
                'is_transport': item.logistics_type in [
                    LogisticsType.FLIGHT, LogisticsType.TRAIN, LogisticsType.BUS,
                    LogisticsType.RENTAL_CAR, LogisticsType.GROUND_TRANSPORT, LogisticsType.FERRY
                ],
                'assignments': item.assignments  # Nominative assignments
            }
            # Add details
            if item.confirmation_number:
                event['details'].append(f"Ref: {item.confirmation_number}")
            if item.pickup_location:
                event['details'].append(f"Depart: {item.pickup_location}")
            if item.dropoff_location:
                event['details'].append(f"Arrivee: {item.dropoff_location}")
            if item.end_datetime:
                duration = (item.end_datetime - item.start_datetime).seconds // 60
                hours, mins = divmod(duration, 60)
                if hours:
                    event['details'].append(f"Duree: {hours}h{mins:02d}")
                else:
                    event['details'].append(f"Duree: {mins} min")
            if item.notes:
                event['details'].append(item.notes)

            timeline.append(event)

    # Add call times as events
    call_times = [
        ('load_in_time', 'Load-In', 'bi-truck', '#6c757d'),
        ('crew_call_time', 'Appel Equipe', 'bi-tools', '#0d6efd'),
        ('artist_call_time', 'Appel Artistes', 'bi-person-badge', '#6f42c1'),
        ('catering_time', 'Repas', 'bi-cup-hot', '#fd7e14'),
        ('soundcheck_time', 'Soundcheck', 'bi-soundwave', '#20c997'),
        ('press_time', 'Presse', 'bi-newspaper', '#d63384'),
        ('meet_greet_time', 'Meet & Greet', 'bi-people', '#e83e8c'),
        ('doors_time', 'Ouverture Portes', 'bi-door-open', '#0dcaf0'),
        ('set_time', 'SET TIME', 'bi-music-note-beamed', '#198754'),
        ('curfew_time', 'Curfew', 'bi-moon', '#dc3545'),
    ]

    for attr, label, icon, color in call_times:
        call_time = getattr(stop, attr, None)
        if call_time:
            event = {
                'time': datetime.combine(stop.date, call_time),
                'type': 'call_time',
                'title': label,
                'subtitle': stop.venue.name if stop.venue else '',
                'details': [],
                'icon': icon,
                'color': color,
                'maps_url': None,
                'is_transport': False,
                'is_highlight': attr == 'set_time'
            }
            timeline.append(event)

    # Sort timeline by time
    timeline.sort(key=lambda x: x['time'])

    # Get hotel info (filtered by visibility)
    hotels = [item for item in visible_logistics if item.logistics_type == LogisticsType.HOTEL]

    # Get primary contact
    primary_contact = None
    for contact in stop.local_contacts:
        if contact.is_primary:
            primary_contact = contact
            break
    if not primary_contact and stop.local_contacts:
        primary_contact = stop.local_contacts[0]

    return render_template(
        'logistics/travel_itinerary.html',
        tour=tour,
        stop=stop,
        timeline=timeline,
        hotels=hotels,
        primary_contact=primary_contact,
        now=datetime.now()
    )


# Mobile Quick Check View (Phase 3)
@logistics_bp.route('/stop/<int:stop_id>/mobile')
@login_required
def mobile_daysheet(stop_id):
    """Mobile-optimized day sheet for crew on the go."""
    # Eager-load venue, contacts, logistics for mobile view
    stop = TourStop.query.options(
        joinedload(TourStop.venue),
        joinedload(TourStop.tour),
        selectinload(TourStop.logistics),
        selectinload(TourStop.local_contacts),
    ).get_or_404(stop_id)
    tour = stop.tour

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Acces non autorise.', 'error')
        return redirect(url_for('main.dashboard'))

    # Get key call times
    call_times = []
    times_config = [
        ('crew_call_time', 'Crew Call'),
        ('artist_call_time', 'Artistes'),
        ('soundcheck_time', 'Soundcheck'),
        ('doors_time', 'Portes'),
        ('set_time', 'SET'),
        ('curfew_time', 'Curfew'),
    ]
    for attr, label in times_config:
        t = getattr(stop, attr, None)
        if t:
            call_times.append({
                'time': t.strftime('%H:%M'),
                'label': label,
                'is_highlight': attr == 'set_time'
            })

    # Primary contact
    primary_contact = None
    for contact in stop.local_contacts:
        if contact.is_primary:
            primary_contact = contact
            break
    if not primary_contact and stop.local_contacts:
        primary_contact = stop.local_contacts[0]

    # Next transport
    next_transport = None
    now = datetime.now()
    for item in sorted(stop.logistics, key=lambda x: x.start_datetime or datetime.max):
        if item.logistics_type in [LogisticsType.FLIGHT, LogisticsType.TRAIN, LogisticsType.BUS,
                                    LogisticsType.GROUND_TRANSPORT]:
            if item.start_datetime and item.start_datetime > now:
                next_transport = item
                break

    return render_template(
        'logistics/mobile_daysheet.html',
        tour=tour,
        stop=stop,
        call_times=call_times,
        primary_contact=primary_contact,
        next_transport=next_transport
    )


# Helper functions for itinerary
def _get_logistics_title(item):
    """Get display title for logistics item."""
    type_titles = {
        LogisticsType.FLIGHT: 'Vol',
        LogisticsType.TRAIN: 'Train',
        LogisticsType.BUS: 'Bus',
        LogisticsType.RENTAL_CAR: 'Location voiture',
        LogisticsType.GROUND_TRANSPORT: 'Navette',
        LogisticsType.FERRY: 'Ferry',
        LogisticsType.HOTEL: 'Hôtel',
        LogisticsType.MEAL: 'Repas',
        LogisticsType.PARKING: 'Parking',
        LogisticsType.VISA: 'Visa',
        LogisticsType.EQUIPMENT: 'Équipement',
        LogisticsType.OTHER: 'Autre',
    }
    return type_titles.get(item.logistics_type, 'Logistique')


def _get_logistics_icon(logistics_type):
    """Get Bootstrap icon for logistics type."""
    icons = {
        LogisticsType.FLIGHT: 'bi-airplane',
        LogisticsType.TRAIN: 'bi-train-front',
        LogisticsType.BUS: 'bi-bus-front',
        LogisticsType.RENTAL_CAR: 'bi-car-front',
        LogisticsType.GROUND_TRANSPORT: 'bi-truck',
        LogisticsType.FERRY: 'bi-water',
        LogisticsType.HOTEL: 'bi-building',
        LogisticsType.MEAL: 'bi-cup-hot',
        LogisticsType.PARKING: 'bi-p-circle',
        LogisticsType.VISA: 'bi-passport',
        LogisticsType.EQUIPMENT: 'bi-box-seam',
        LogisticsType.OTHER: 'bi-three-dots',
    }
    return icons.get(logistics_type, 'bi-geo-alt')


def _get_logistics_color(logistics_type):
    """Get color for logistics type."""
    colors = {
        LogisticsType.FLIGHT: '#0d6efd',
        LogisticsType.TRAIN: '#198754',
        LogisticsType.BUS: '#fd7e14',
        LogisticsType.RENTAL_CAR: '#6f42c1',
        LogisticsType.GROUND_TRANSPORT: '#6c757d',
        LogisticsType.FERRY: '#0dcaf0',
        LogisticsType.HOTEL: '#20c997',
        LogisticsType.MEAL: '#dc3545',
        LogisticsType.PARKING: '#adb5bd',
        LogisticsType.VISA: '#d63384',
        LogisticsType.EQUIPMENT: '#ffc107',
        LogisticsType.OTHER: '#6c757d',
    }
    return colors.get(logistics_type, '#6c757d')


# =============================================================================
# iCAL EXPORT
# =============================================================================

@logistics_bp.route('/stop/<int:stop_id>/ical')
@login_required
def export_ical(stop_id):
    """Export tour stop schedule as iCal file for calendar sync."""
    try:
        from icalendar import Calendar, Event
        import uuid
    except ImportError:
        flash('Module icalendar non installe. Executez: pip install icalendar', 'error')
        return redirect(url_for('logistics.manage', stop_id=stop_id))

    # Eager-load venue and logistics for iCal generation
    stop = TourStop.query.options(
        joinedload(TourStop.venue),
        joinedload(TourStop.tour),
        selectinload(TourStop.logistics),
    ).get_or_404(stop_id)
    tour = stop.tour

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Acces non autorise.', 'error')
        return redirect(url_for('main.dashboard'))

    # Create calendar
    cal = Calendar()
    cal.add('prodid', '-//GigRoute//GigRoute//FR')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('x-wr-calname', f'{tour.band_name} - {tour.name}')

    # Main event (the show)
    main_event = Event()
    main_event.add('uid', f'show-{stop.id}@gigroute.app')
    main_event.add('summary', f'{tour.band_name} @ {stop.venue.name if stop.venue else "TBA"}')

    # Set show time (prefer set_time, then doors_time, fallback to 20:30)
    show_time = stop.set_time or stop.doors_time or time(20, 30)
    event_start = datetime.combine(stop.date, show_time)
    main_event.add('dtstart', event_start)

    # Estimate 2 hours show duration (safe overflow past midnight)
    event_end = event_start + timedelta(hours=2)
    main_event.add('dtend', event_end)

    # Location
    if stop.venue:
        location = f"{stop.venue.name}, {stop.venue.address}, {stop.venue.postal_code} {stop.venue.city}"
        main_event.add('location', location)
        if stop.venue.has_coordinates:
            main_event.add('geo', (stop.venue.latitude, stop.venue.longitude))

    # Description with details
    description_lines = [
        f"Tournee: {tour.name}",
        f"Groupe: {tour.band_name}",
        "",
    ]

    if stop.venue:
        description_lines.extend([
            f"Venue: {stop.venue.name}",
            f"Capacite: {stop.venue.capacity or 'N/A'}",
            "",
        ])

    # Add call times to description
    call_times_info = []
    if stop.load_in_time:
        call_times_info.append(f"Load-in: {stop.load_in_time.strftime('%H:%M')}")
    if stop.crew_call_time:
        call_times_info.append(f"Crew Call: {stop.crew_call_time.strftime('%H:%M')}")
    if stop.artist_call_time:
        call_times_info.append(f"Artist Call: {stop.artist_call_time.strftime('%H:%M')}")
    if stop.soundcheck_time:
        call_times_info.append(f"Soundcheck: {stop.soundcheck_time.strftime('%H:%M')}")
    if stop.doors_time:
        call_times_info.append(f"Doors: {stop.doors_time.strftime('%H:%M')}")
    if stop.curfew_time:
        call_times_info.append(f"Curfew: {stop.curfew_time.strftime('%H:%M')}")

    if call_times_info:
        description_lines.append("HORAIRES:")
        description_lines.extend(call_times_info)

    main_event.add('description', '\n'.join(description_lines))
    main_event.add('dtstamp', datetime.utcnow())

    cal.add_component(main_event)

    # Add call times as separate reminder events
    call_times_events = [
        ('load_in_time', 'Load-in', 'bi-truck'),
        ('crew_call_time', 'Crew Call', 'bi-people'),
        ('artist_call_time', 'Artist Call', 'bi-person'),
        ('soundcheck_time', 'Soundcheck', 'bi-mic'),
        ('doors_time', 'Doors', 'bi-door-open'),
    ]

    for attr, label, icon in call_times_events:
        call_time = getattr(stop, attr, None)
        if call_time:
            call_event = Event()
            call_event.add('uid', f'{attr}-{stop.id}@gigroute.app')
            call_event.add('summary', f'{label} - {stop.venue.name if stop.venue else "TBA"}')
            call_start = datetime.combine(stop.date, call_time)
            call_event.add('dtstart', call_start)
            # 30 min duration for call times (safe overflow past midnight)
            call_event.add('dtend', call_start + timedelta(minutes=30))
            if stop.venue:
                call_event.add('location', f"{stop.venue.name}, {stop.venue.city}")
            call_event.add('dtstamp', datetime.utcnow())

            # Add alarm 15 minutes before
            from icalendar import Alarm
            alarm = Alarm()
            alarm.add('action', 'DISPLAY')
            alarm.add('trigger', timedelta(minutes=-15))
            alarm.add('description', f'{label} dans 15 minutes')
            call_event.add_component(alarm)

            cal.add_component(call_event)

    # Add transport events
    for logistics in stop.logistics:
        if logistics.logistics_type in [LogisticsType.FLIGHT, LogisticsType.TRAIN, LogisticsType.BUS]:
            if logistics.departure_time:
                transport_event = Event()
                transport_event.add('uid', f'transport-{logistics.id}@gigroute.app')

                type_name = _get_logistics_title(logistics)
                summary = f'{type_name}'
                if logistics.provider:
                    summary += f' - {logistics.provider}'
                if logistics.confirmation_number:
                    summary += f' ({logistics.confirmation_number})'

                transport_event.add('summary', summary)
                transport_event.add('dtstart', datetime.combine(stop.date, logistics.departure_time))

                if logistics.arrival_time:
                    transport_event.add('dtend', datetime.combine(stop.date, logistics.arrival_time))

                if logistics.departure_location:
                    transport_event.add('location', logistics.departure_location)

                # Description with all details
                transport_desc = []
                if logistics.departure_location:
                    transport_desc.append(f"Depart: {logistics.departure_location}")
                if logistics.arrival_location:
                    transport_desc.append(f"Arrivee: {logistics.arrival_location}")
                if logistics.confirmation_number:
                    transport_desc.append(f"Ref: {logistics.confirmation_number}")
                if logistics.notes:
                    transport_desc.append(f"Notes: {logistics.notes}")

                transport_event.add('description', '\n'.join(transport_desc))
                transport_event.add('dtstamp', datetime.utcnow())

                cal.add_component(transport_event)

    # Generate response
    response = make_response(cal.to_ical())
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=tour_stop_{stop.id}_{stop.date.strftime("%Y%m%d")}.ics'

    return response


@logistics_bp.route('/tour/<int:tour_id>/pdf', methods=['GET'])
@login_required
def export_tour_pdf(tour_id):
    """Export tour schedule as PDF file."""
    from app.utils.pdf_generator import generate_tour_pdf, PDF_AVAILABLE

    if not PDF_AVAILABLE:
        flash('Module reportlab non installe. Executez: pip install reportlab', 'error')
        return redirect(url_for('tours.detail', id=tour_id))

    tour = Tour.query.get_or_404(tour_id)

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Acces non autorise.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        pdf_bytes = generate_tour_pdf(tour)
        filename = f"{tour.name.replace(' ', '_')}_schedule.pdf"

        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        current_app.logger.error(f'PDF generation failed: {e}')
        flash('Erreur lors de la génération du PDF.', 'error')
        return redirect(url_for('tours.detail', id=tour_id))


@logistics_bp.route('/stop/<int:stop_id>/pdf', methods=['GET'])
@login_required
def export_stop_pdf(stop_id):
    """Export day sheet as PDF file."""
    from app.utils.pdf_generator import generate_daysheet_pdf, PDF_AVAILABLE

    if not PDF_AVAILABLE:
        flash('Module reportlab non installe. Executez: pip install reportlab', 'error')
        return redirect(url_for('logistics.day_sheet', stop_id=stop_id))

    stop = TourStop.query.get_or_404(stop_id)
    tour = stop.tour

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Acces non autorise.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        pdf_bytes = generate_daysheet_pdf(stop)
        date_str = stop.date.strftime('%Y%m%d') if stop.date else 'TBA'
        venue_name = stop.venue.name.replace(' ', '_') if stop.venue else 'TBA'
        filename = f"daysheet_{date_str}_{venue_name}.pdf"

        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        current_app.logger.error(f'PDF generation failed: {e}')
        flash('Erreur lors de la génération du PDF.', 'error')
        return redirect(url_for('logistics.day_sheet', stop_id=stop_id))


@logistics_bp.route('/tour/<int:tour_id>/ical')
@login_required
def export_tour_ical(tour_id):
    """Export entire tour schedule as iCal file."""
    try:
        from icalendar import Calendar, Event
    except ImportError:
        flash('Module icalendar non installe. Executez: pip install icalendar', 'error')
        return redirect(url_for('tours.detail', id=tour_id))

    tour = Tour.query.get_or_404(tour_id)

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Acces non autorise.', 'error')
        return redirect(url_for('main.dashboard'))

    # Create calendar
    cal = Calendar()
    cal.add('prodid', '-//GigRoute//GigRoute//FR')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('x-wr-calname', f'{tour.band_name} - {tour.name}')

    # Add each stop as an event
    for stop in sorted(tour.stops, key=lambda s: s.date):
        event = Event()
        event.add('uid', f'show-{stop.id}@gigroute.app')

        venue_name = stop.venue.name if stop.venue else 'TBA'
        event.add('summary', f'{tour.band_name} @ {venue_name}')

        show_time = stop.set_time or time(20, 30)
        event.add('dtstart', datetime.combine(stop.date, show_time))

        if stop.venue:
            location = f"{stop.venue.name}, {stop.venue.city}, {stop.venue.country}"
            event.add('location', location)

        # Build description
        desc_lines = []
        if stop.doors_time:
            desc_lines.append(f"Doors: {stop.doors_time.strftime('%H:%M')}")
        if stop.set_time:
            desc_lines.append(f"Show: {stop.set_time.strftime('%H:%M')}")
        if stop.status:
            desc_lines.append(f"Status: {stop.status.value}")

        event.add('description', '\n'.join(desc_lines))
        event.add('dtstamp', datetime.utcnow())

        cal.add_component(event)

    # Generate response
    response = make_response(cal.to_ical())
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=tour_{tour.id}_{tour.name.replace(" ", "_")}.ics'

    return response


# =============================================================================
# AIRPORT COORDINATES HELPER
# =============================================================================

# Major airports coordinates (IATA code -> (lat, lng))
AIRPORTS_COORDS = {
    # France
    'CDG': (49.0097, 2.5479),    # Paris Charles de Gaulle
    'ORY': (48.7233, 2.3794),    # Paris Orly
    'NCE': (43.6584, 7.2159),    # Nice
    'LYS': (45.7256, 5.0811),    # Lyon
    'MRS': (43.4393, 5.2214),    # Marseille
    'TLS': (43.6293, 1.3679),    # Toulouse
    'BOD': (44.8283, -0.7156),   # Bordeaux
    'NTE': (47.1532, -1.6108),   # Nantes
    # UK & Ireland
    'LHR': (51.4700, -0.4543),   # London Heathrow
    'LGW': (51.1537, -0.1821),   # London Gatwick
    'STN': (51.8850, 0.2350),    # London Stansted
    'LTN': (51.8747, -0.3683),   # London Luton
    'MAN': (53.3537, -2.2750),   # Manchester
    'EDI': (55.9500, -3.3725),   # Edinburgh
    'DUB': (53.4213, -6.2701),   # Dublin
    # Germany
    'FRA': (50.0379, 8.5622),    # Frankfurt
    'MUC': (48.3538, 11.7861),   # Munich
    'BER': (52.3667, 13.5033),   # Berlin Brandenburg
    'DUS': (51.2895, 6.7668),    # Dusseldorf
    'HAM': (53.6304, 9.9882),    # Hamburg
    'CGN': (50.8659, 7.1427),    # Cologne
    # Spain
    'MAD': (40.4719, -3.5626),   # Madrid
    'BCN': (41.2971, 2.0785),    # Barcelona
    'AGP': (36.6749, -4.4991),   # Malaga
    'PMI': (39.5517, 2.7388),    # Palma Mallorca
    'VLC': (39.4893, -0.4816),   # Valencia
    # Italy
    'FCO': (41.8003, 12.2389),   # Rome Fiumicino
    'MXP': (45.6306, 8.7281),    # Milan Malpensa
    'LIN': (45.4454, 9.2767),    # Milan Linate
    'VCE': (45.5053, 12.3519),   # Venice
    'NAP': (40.8860, 14.2908),   # Naples
    # Netherlands & Belgium
    'AMS': (52.3105, 4.7683),    # Amsterdam Schiphol
    'BRU': (50.9014, 4.4844),    # Brussels
    # Switzerland
    'ZRH': (47.4647, 8.5492),    # Zurich
    'GVA': (46.2370, 6.1092),    # Geneva
    # Austria
    'VIE': (48.1103, 16.5697),   # Vienna
    # Portugal
    'LIS': (38.7756, -9.1354),   # Lisbon
    'OPO': (41.2481, -8.6814),   # Porto
    # Scandinavia
    'CPH': (55.6180, 12.6508),   # Copenhagen
    'ARN': (59.6519, 17.9186),   # Stockholm Arlanda
    'OSL': (60.1939, 11.1004),   # Oslo
    'HEL': (60.3172, 24.9633),   # Helsinki
    # Eastern Europe
    'PRG': (50.1008, 14.2600),   # Prague
    'WAW': (52.1657, 20.9671),   # Warsaw
    'BUD': (47.4298, 19.2611),   # Budapest
    # USA (major hubs)
    'JFK': (40.6413, -73.7781),  # New York JFK
    'EWR': (40.6895, -74.1745),  # Newark
    'LGA': (40.7769, -73.8740),  # LaGuardia
    'LAX': (33.9425, -118.4081), # Los Angeles
    'SFO': (37.6213, -122.3790), # San Francisco
    'ORD': (41.9742, -87.9073),  # Chicago O'Hare
    'ATL': (33.6407, -84.4277),  # Atlanta
    'DFW': (32.8998, -97.0403),  # Dallas
    'MIA': (25.7959, -80.2870),  # Miami
    'BOS': (42.3656, -71.0096),  # Boston
    'DEN': (39.8561, -104.6737), # Denver
    'SEA': (47.4502, -122.3088), # Seattle
    'LAS': (36.0840, -115.1537), # Las Vegas
    # Canada
    'YYZ': (43.6777, -79.6248),  # Toronto
    'YVR': (49.1947, -123.1792), # Vancouver
    'YUL': (45.4657, -73.7455),  # Montreal
    # Asia-Pacific
    'NRT': (35.7720, 140.3929),  # Tokyo Narita
    'HND': (35.5494, 139.7798),  # Tokyo Haneda
    'ICN': (37.4602, 126.4407),  # Seoul Incheon
    'HKG': (22.3080, 113.9185),  # Hong Kong
    'SIN': (1.3644, 103.9915),   # Singapore
    'BKK': (13.6900, 100.7501),  # Bangkok
    'SYD': (-33.9399, 151.1753), # Sydney
    'MEL': (-37.6690, 144.8410), # Melbourne
    # Middle East
    'DXB': (25.2528, 55.3644),   # Dubai
    'DOH': (25.2731, 51.6081),   # Doha
    'AUH': (24.4330, 54.6511),   # Abu Dhabi
    'TLV': (32.0055, 34.8854),   # Tel Aviv
}


def _fill_airport_coordinates(logistics):
    """Fill GPS coordinates for flight departure and arrival airports."""
    if logistics.departure_airport:
        code = logistics.departure_airport.upper().strip()
        if code in AIRPORTS_COORDS:
            logistics.departure_lat = AIRPORTS_COORDS[code][0]
            logistics.departure_lng = AIRPORTS_COORDS[code][1]

    if logistics.arrival_airport:
        code = logistics.arrival_airport.upper().strip()
        if code in AIRPORTS_COORDS:
            logistics.arrival_lat = AIRPORTS_COORDS[code][0]
            logistics.arrival_lng = AIRPORTS_COORDS[code][1]


# =============================================================================
# LOGISTICS ASSIGNMENTS (Nominative Assignment)
# =============================================================================

@logistics_bp.route('/<int:id>/assign', methods=['GET', 'POST'])
@login_required
def assign_user(id):
    """Assign a user to a logistics item."""
    from flask import jsonify

    logistics = LogisticsInfo.query.get_or_404(id)
    stop = logistics.tour_stop
    tour = stop.tour

    # Check permission
    if not tour.band_is_manager(current_user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Permission refusée'}), 403
        flash('Seul le manager peut assigner des personnes.', 'error')
        return redirect(url_for('logistics.manage', stop_id=stop.id))

    form = LogisticsAssignmentForm()

    # Populate user choices - all active users
    users = get_org_users().order_by(User.last_name, User.first_name).all()
    form.user_id.choices = [(0, '-- Sélectionner --')] + [
        (u.id, f"{u.first_name} {u.last_name}") for u in users
    ]

    if form.validate_on_submit():
        user_id = form.user_id.data
        if user_id == 0:
            flash('Veuillez sélectionner une personne.', 'error')
        else:
            # Check if already assigned
            existing = LogisticsAssignment.query.filter_by(
                logistics_info_id=id,
                user_id=user_id
            ).first()

            if existing:
                flash('Cette personne est déjà assignée à cet élément.', 'warning')
            else:
                assignment = LogisticsAssignment(
                    logistics_info_id=id,
                    user_id=user_id,
                    seat_number=form.seat_number.data or None,
                    room_number=form.room_number.data or None,
                    room_sharing_with=form.room_sharing_with.data or None,
                    special_requests=form.special_requests.data or None,
                    assigned_by_id=current_user.id
                )
                db.session.add(assignment)
                db.session.commit()

                user = User.query.get(user_id)
                log_create('LogisticsAssignment', assignment.id, {
                    'logistics_id': id,
                    'user': f"{user.first_name} {user.last_name}"
                })

                flash(f'{user.first_name} {user.last_name} assigné(e) avec succès.', 'success')

        # Check if AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'redirect': url_for('logistics.manage', stop_id=stop.id)})
        return redirect(url_for('logistics.manage', stop_id=stop.id))

    # Get already assigned users for display
    assigned_users = [a.user for a in logistics.assignments.all()]

    # AJAX request returns partial
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template(
            'logistics/_assign_form.html',
            form=form,
            logistics=logistics,
            assigned_users=assigned_users
        )

    return render_template(
        'logistics/assign_form.html',
        form=form,
        logistics=logistics,
        stop=stop,
        tour=tour,
        assigned_users=assigned_users,
        title='Assigner une personne'
    )


@logistics_bp.route('/<int:id>/unassign/<int:user_id>', methods=['POST'])
@login_required
def unassign_user(id, user_id):
    """Remove a user assignment from a logistics item."""
    from flask import jsonify

    logistics = LogisticsInfo.query.get_or_404(id)
    stop = logistics.tour_stop
    tour = stop.tour

    # Check permission
    if not tour.band_is_manager(current_user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Permission refusée'}), 403
        flash('Seul le manager peut désassigner des personnes.', 'error')
        return redirect(url_for('logistics.manage', stop_id=stop.id))

    # Find assignment
    assignment = LogisticsAssignment.query.filter_by(
        logistics_info_id=id,
        user_id=user_id
    ).first()

    if assignment:
        user = assignment.user
        user_name = f"{user.first_name} {user.last_name}"
        log_delete('LogisticsAssignment', assignment.id, {
            'logistics_id': id,
            'user': user_name
        })
        db.session.delete(assignment)
        db.session.commit()
        flash(f'{user_name} a été désassigné(e).', 'success')
    else:
        flash('Assignation non trouvée.', 'error')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})

    return redirect(url_for('logistics.manage', stop_id=stop.id))


@logistics_bp.route('/<int:id>/assignments')
@login_required
def list_assignments(id):
    """API endpoint to list all assignments for a logistics item."""
    from flask import jsonify

    logistics = LogisticsInfo.query.get_or_404(id)
    stop = logistics.tour_stop
    tour = stop.tour

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        return jsonify({'success': False, 'error': 'Accès non autorisé'}), 403

    assignments = []
    for a in logistics.assignments.all():
        assignments.append({
            'id': a.id,
            'user_id': a.user_id,
            'user_name': f"{a.user.first_name} {a.user.last_name}",
            'seat_number': a.seat_number,
            'room_number': a.room_number,
            'room_sharing_with': a.room_sharing_with,
            'special_requests': a.special_requests,
            'display_details': a.display_details
        })

    return jsonify({
        'success': True,
        'logistics_id': id,
        'logistics_type': logistics.logistics_type.value,
        'assignments': assignments,
        'count': len(assignments)
    })
