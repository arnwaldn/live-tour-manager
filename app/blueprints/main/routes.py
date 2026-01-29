"""
Main blueprint routes - Dashboard and home.
"""
from datetime import date, timedelta
from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from app.blueprints.main import main_bp
from app.blueprints.main.forms import StandaloneEventForm
from app.extensions import db


@main_bp.route('/health')
def health_check():
    """Health check endpoint for Docker/load balancer."""
    try:
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'

    status = 'healthy' if db_status == 'healthy' else 'unhealthy'

    return jsonify({
        'status': status,
        'database': db_status,
        'service': 'tour-manager',
        'version': '2026-01-29-v8'  # Deployment version marker
    }), 200 if status == 'healthy' else 503


@main_bp.route('/health/diagnose')
def health_diagnose():
    """Diagnostic endpoint to check data integrity (no auth required)."""
    from app.models.tour import Tour
    from app.models.user import User

    diagnostics = {
        'version': '2026-01-29-v6',
        'tours': {},
        'users': {}
    }

    # Check tour ID 4
    try:
        tour = Tour.query.get(4)
        if tour:
            diagnostics['tours']['id_4'] = {
                'exists': True,
                'name': tour.name,
                'band_id': tour.band_id,
                'band_exists': tour.band is not None,
                'band_name': tour.band_name  # Uses safe property
            }
        else:
            diagnostics['tours']['id_4'] = {'exists': False}
    except Exception as e:
        diagnostics['tours']['id_4'] = {'error': str(e)}

    # Check user ID 3
    try:
        user = User.query.get(3)
        if user:
            # Test professions access (common error source)
            try:
                professions_count = len(user.professions)
                primary_prof = user.primary_profession
                primary_prof_name = primary_prof.name_fr if primary_prof else None
            except Exception as prof_err:
                professions_count = f'ERROR: {prof_err}'
                primary_prof_name = f'ERROR: {prof_err}'

            # Test travel_cards access
            try:
                travel_cards_count = len(user.travel_cards) if user.travel_cards else 0
            except Exception as tc_err:
                travel_cards_count = f'ERROR: {tc_err}'

            # Test roles access
            try:
                roles_count = len(user.roles) if user.roles else 0
            except Exception as r_err:
                roles_count = f'ERROR: {r_err}'

            # Test user_professions relationship
            try:
                user_profs = user.user_professions.all()
                user_profs_count = len(user_profs)
            except Exception as up_err:
                user_profs_count = f'ERROR: {up_err}'

            diagnostics['users']['id_3'] = {
                'exists': True,
                'email': user.email[:3] + '***',  # Partial for privacy
                'is_active': user.is_active,
                'professions_count': professions_count,
                'primary_profession': primary_prof_name,
                'access_level': user.access_level.name if user.access_level else None,
                'travel_cards_count': travel_cards_count,
                'roles_count': roles_count,
                'user_professions_raw': user_profs_count
            }
        else:
            diagnostics['users']['id_3'] = {'exists': False}
    except Exception as e:
        diagnostics['users']['id_3'] = {'error': str(e)}

    return jsonify(diagnostics)


from app.models.tour import Tour, TourStatus
from app.models.tour_stop import TourStop, TourStopStatus, EventType, tour_stop_members
from app.models.guestlist import GuestlistEntry, GuestlistStatus
from app.models.band import Band, BandMembership
from app.models.venue import Venue


@main_bp.route('/')
@login_required
def dashboard():
    """Main dashboard - adapted to user's role."""

    # Get user's bands (as member or manager)
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    # Active tours for user's bands
    active_tours = Tour.query.filter(
        Tour.band_id.in_(user_band_ids),
        Tour.status.in_([TourStatus.ACTIVE, TourStatus.CONFIRMED])
    ).order_by(Tour.start_date).all()

    # Upcoming shows (next 14 days)
    today = date.today()
    two_weeks = today + timedelta(days=14)

    upcoming_stops = TourStop.query.join(Tour).filter(
        Tour.band_id.in_(user_band_ids),
        TourStop.date >= today,
        TourStop.date <= two_weeks,
        TourStop.status != TourStopStatus.CANCELED
    ).order_by(TourStop.date).limit(5).all()

    # Today's shows
    today_stops = TourStop.query.join(Tour).filter(
        Tour.band_id.in_(user_band_ids),
        TourStop.date == today,
        TourStop.status != TourStopStatus.CANCELED
    ).all()

    # Pending guestlist requests (for managers)
    pending_guestlist = []
    if current_user.is_staff_or_above():
        pending_guestlist = GuestlistEntry.query.join(TourStop).join(Tour).filter(
            Tour.band_id.in_(user_band_ids),
            GuestlistEntry.status == GuestlistStatus.PENDING
        ).order_by(GuestlistEntry.created_at.desc()).limit(10).all()

    # Stats
    stats = {
        'total_tours': len(active_tours),
        'upcoming_shows': TourStop.query.join(Tour).filter(
            Tour.band_id.in_(user_band_ids),
            TourStop.date >= today,
            TourStop.status != TourStopStatus.CANCELED
        ).count(),
        'pending_guestlist': len(pending_guestlist),
        'total_bands': len(user_bands)
    }

    return render_template(
        'main/dashboard.html',
        active_tours=active_tours,
        upcoming_stops=upcoming_stops,
        today_stops=today_stops,
        pending_guestlist=pending_guestlist,
        stats=stats
    )


@main_bp.route('/calendar')
@login_required
def global_calendar():
    """Global calendar showing events based on user role.

    - MANAGER: voit TOUS les événements de TOUS les groupes
    - Autres: voient UNIQUEMENT les événements où ils sont assignés
    """
    is_manager = current_user.is_manager_or_above()

    if is_manager:
        # MANAGER voit toutes les tournées
        tours = Tour.query.order_by(Tour.start_date.desc()).all()
    else:
        # Autres rôles: tournées où l'utilisateur est:
        # 1. Explicitement assigné (tour_stop_members) OU
        # 2. Membre du groupe propriétaire de la tournée (BandMembership)
        tours = Tour.query.join(
            Band, Tour.band_id == Band.id
        ).outerjoin(
            TourStop, Tour.id == TourStop.tour_id
        ).outerjoin(
            tour_stop_members, TourStop.id == tour_stop_members.c.tour_stop_id
        ).outerjoin(
            BandMembership, Band.id == BandMembership.band_id
        ).filter(
            db.or_(
                tour_stop_members.c.user_id == current_user.id,
                BandMembership.user_id == current_user.id
            )
        ).distinct().order_by(Tour.start_date.desc()).all()

    return render_template(
        'main/global_calendar.html',
        tours=tours,
        is_manager=is_manager
    )


@main_bp.route('/calendar/events')
@login_required
def global_calendar_events():
    """API endpoint for global calendar events (tour stops + standalone events).

    Filtrage par rôle:
    - MANAGER: voit TOUS les événements de TOUS les groupes (admin global)
    - Autres rôles: voient UNIQUEMENT les événements où ils sont assignés
    """
    from datetime import datetime
    from sqlalchemy import or_

    # Get date range from request
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    tour_id = request.args.get('tour_id', type=int)

    # Build query based on user role
    if current_user.is_manager_or_above():
        # MANAGER = voit TOUT (admin global)
        # Pas de filtre par groupe - afficher tous les événements
        query = TourStop.query.outerjoin(Tour, TourStop.tour_id == Tour.id)
    else:
        # Autres rôles: événements où l'utilisateur est:
        # 1. Explicitement assigné (tour_stop_members) OU
        # 2. Membre du groupe propriétaire (via Tour.band_id ou TourStop.band_id pour standalone)
        query = TourStop.query.outerjoin(
            Tour, TourStop.tour_id == Tour.id
        ).outerjoin(
            tour_stop_members, TourStop.id == tour_stop_members.c.tour_stop_id
        ).outerjoin(
            BandMembership,
            db.or_(
                # Pour les tour stops: band via tour
                db.and_(Tour.band_id.isnot(None), BandMembership.band_id == Tour.band_id),
                # Pour les événements standalone: band directement sur TourStop
                db.and_(TourStop.band_id.isnot(None), BandMembership.band_id == TourStop.band_id)
            )
        ).filter(
            db.or_(
                tour_stop_members.c.user_id == current_user.id,
                BandMembership.user_id == current_user.id
            )
        ).distinct()

    # Filter by tour if specified (only shows tour stops, not standalone)
    if tour_id:
        query = query.filter(TourStop.tour_id == tour_id)

    # Filter by date range if provided
    if start_str:
        try:
            start_date = datetime.fromisoformat(start_str.replace('Z', '+00:00')).date()
            query = query.filter(TourStop.date >= start_date)
        except ValueError:
            pass

    if end_str:
        try:
            end_date = datetime.fromisoformat(end_str.replace('Z', '+00:00')).date()
            query = query.filter(TourStop.date <= end_date)
        except ValueError:
            pass

    stops = query.all()

    # Get view type to determine event generation strategy
    view_type = request.args.get('view', 'month')  # month, week, list

    # Schedule types with their display properties (attr, label, color)
    schedule_types = [
        ('load_in_time', 'Load-In', '#6c757d'),
        ('crew_call_time', 'Équipe', '#17a2b8'),
        ('artist_call_time', 'Artistes', '#ffc107'),
        ('catering_time', 'Catering', '#fd7e14'),
        ('soundcheck_time', 'Soundcheck', '#6f42c1'),
        ('press_time', 'Presse', '#20c997'),
        ('meet_greet_time', 'Meet & Greet', '#e83e8c'),
        ('doors_time', 'Portes', '#28a745'),
        ('set_time', 'Set', '#007bff'),
        ('curfew_time', 'Couvre-feu', '#dc3545'),
    ]

    events = []
    for stop in stops:
        status_value = stop.status.value if stop.status else 'pending'

        # Get band and title based on whether it's standalone or tour stop
        if stop.is_standalone:
            band = stop.band
            venue_name = stop.venue.name if stop.venue else stop.event_label
            base_title = f"{band.name} - {venue_name}" if stop.venue else f"{band.name} - {stop.event_label}"
            event_url = url_for('main.edit_standalone_event', event_id=stop.id)
            tour_name = None
        else:
            band = stop.tour.band
            venue_name = stop.venue.name if stop.venue else stop.event_label
            base_title = f"{band.name} @ {venue_name}"
            event_url = f"/tours/{stop.tour.id}#stop-{stop.id}"
            tour_name = stop.tour.name

        # Common extendedProps for all events
        common_props = {
            'tour_name': tour_name,
            'band_name': band.name,
            'venue_name': venue_name,
            'city': stop.venue.city if stop.venue else '',
            'country': stop.venue.country if stop.venue else '',
            'status': status_value,
            'stop_id': stop.id,
            'tour_id': stop.tour_id,
            'is_standalone': stop.is_standalone,
            'event_type': stop.event_type.value if stop.event_type else 'show',
            'event_label': stop.event_label,
            # Schedule times for popup
            'loadInTime': stop.load_in_time.strftime('%H:%M') if stop.load_in_time else None,
            'crewCallTime': stop.crew_call_time.strftime('%H:%M') if stop.crew_call_time else None,
            'artistCallTime': stop.artist_call_time.strftime('%H:%M') if stop.artist_call_time else None,
            'cateringTime': stop.catering_time.strftime('%H:%M') if stop.catering_time else None,
            'soundcheckTime': stop.soundcheck_time.strftime('%H:%M') if stop.soundcheck_time else None,
            'pressTime': stop.press_time.strftime('%H:%M') if stop.press_time else None,
            'meetGreetTime': stop.meet_greet_time.strftime('%H:%M') if stop.meet_greet_time else None,
            'doorsTime': stop.doors_time.strftime('%H:%M') if stop.doors_time else None,
            'setTime': stop.set_time.strftime('%H:%M') if stop.set_time else None,
            'curfewTime': stop.curfew_time.strftime('%H:%M') if stop.curfew_time else None,
            # Reschedule tracking for dual date display
            'isRescheduled': stop.is_rescheduled,
            'originalDate': stop.original_date.strftime('%d/%m/%Y') if stop.original_date else None,
            'rescheduleReason': stop.reschedule_reason,
            'rescheduleCount': stop.reschedule_count
        }

        if view_type == 'week':
            # Week view: Create separate event for each schedule time
            for attr, label, color in schedule_types:
                time_value = getattr(stop, attr)
                if time_value:
                    events.append({
                        'id': f"{stop.id}-{attr}",
                        'title': f"{label}: {base_title}",
                        'start': f"{stop.date.isoformat()}T{time_value.strftime('%H:%M:%S')}",
                        'allDay': False,
                        'url': event_url,
                        'backgroundColor': color,
                        'borderColor': color,
                        'textColor': '#ffffff' if color not in ['#ffc107', '#fd7e14'] else '#212529',
                        'extendedProps': {
                            **common_props,
                            'schedule_type': attr,
                            'schedule_label': label
                        }
                    })
        else:
            # Month/List view: Single event per TourStop
            if stop.set_time:
                event_start = f"{stop.date.isoformat()}T{stop.set_time.strftime('%H:%M:%S')}"
                all_day = False
            else:
                event_start = stop.date.isoformat()
                all_day = True

            events.append({
                'id': stop.id,
                'title': base_title,
                'start': event_start,
                'allDay': all_day,
                'url': event_url,
                'backgroundColor': stop.event_color,
                'borderColor': stop.event_color,
                'textColor': '#ffffff' if stop.event_type not in [EventType.REHEARSAL, EventType.PHOTO_VIDEO, EventType.OTHER] else '#212529',
                'extendedProps': common_props
            })

            # Ghost event pour les concerts reportés (date originale barrée)
            if stop.is_rescheduled and stop.original_date:
                ghost_event = {
                    'id': f"ghost-{stop.id}",
                    'title': f"[REPORTÉ] {base_title}",
                    'start': stop.original_date.isoformat(),
                    'allDay': True,
                    'className': 'ghost-event',
                    'backgroundColor': '#6c757d',
                    'borderColor': '#495057',
                    'textColor': '#ffffff',
                    'extendedProps': {
                        'isGhost': True,
                        'stop_id': stop.id,
                        'tour_id': stop.tour_id,
                        'band_name': band.name,
                        'venue_name': venue_name,
                        'city': stop.venue.city if stop.venue else '',
                        'country': stop.venue.country if stop.venue else '',
                        'newDate': stop.date.strftime('%d/%m/%Y'),
                        'originalDate': stop.original_date.strftime('%d/%m/%Y'),
                        'rescheduleReason': stop.reschedule_reason,
                        'is_standalone': stop.is_standalone
                    }
                }
                events.append(ghost_event)

    return jsonify(events)


@main_bp.route('/search')
@login_required
def search():
    """Global search across tours, venues, guests."""
    query = request.args.get('q', '').strip()

    if not query or len(query) < 2:
        return render_template('main/search.html', query=query, results=None)

    # Get user's bands
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    results = {
        'tours': [],
        'venues': [],
        'guests': [],
        'bands': []
    }

    # Search tours
    from app.models.tour import Tour
    results['tours'] = Tour.query.filter(
        Tour.band_id.in_(user_band_ids),
        Tour.name.ilike(f'%{query}%')
    ).limit(10).all()

    # Search venues
    from app.models.venue import Venue
    results['venues'] = Venue.query.filter(
        Venue.name.ilike(f'%{query}%') |
        Venue.city.ilike(f'%{query}%')
    ).limit(10).all()

    # Search guestlist entries
    results['guests'] = GuestlistEntry.query.join(TourStop).join(Tour).filter(
        Tour.band_id.in_(user_band_ids),
        GuestlistEntry.guest_name.ilike(f'%{query}%')
    ).limit(10).all()

    # Search bands
    results['bands'] = Band.query.filter(
        Band.id.in_(user_band_ids),
        Band.name.ilike(f'%{query}%')
    ).limit(10).all()

    total_results = sum(len(v) for v in results.values())

    return render_template(
        'main/search.html',
        query=query,
        results=results,
        total_results=total_results
    )


@main_bp.route('/calendar/add', methods=['GET', 'POST'])
@login_required
def add_standalone_event():
    """Add a standalone event (not linked to a specific tour)."""
    form = StandaloneEventForm()

    # Get user's bands for the band selector
    user_bands = current_user.bands + current_user.managed_bands
    # Filter to only bands where user is manager (can create events)
    manageable_bands = [b for b in user_bands if b.is_manager(current_user)]

    if not manageable_bands:
        flash('Vous devez être manager d\'un groupe pour ajouter un événement.', 'warning')
        return redirect(url_for('main.global_calendar'))

    form.band_id.choices = [(0, '-- Sélectionner un groupe --')] + [
        (b.id, b.name) for b in manageable_bands
    ]

    # Tour selector (optional) - only tours for the selected band
    all_tours = Tour.query.filter(
        Tour.band_id.in_([b.id for b in manageable_bands])
    ).order_by(Tour.start_date.desc()).all()
    form.tour_id.choices = [(0, '-- Événement libre (sans tournée) --')] + [
        (t.id, f"{t.name} ({t.band.name})") for t in all_tours
    ]

    # Venue selector
    venues = Venue.query.order_by(Venue.name).all()
    form.venue_id.choices = [(0, '-- Sans salle --')] + [
        (v.id, f"{v.name} - {v.city}, {v.country}") for v in venues
    ]

    # Pre-fill date from URL parameter if provided
    prefill_date = request.args.get('date')

    if form.validate_on_submit():
        # Create the tour stop / standalone event
        event = TourStop(
            date=form.date.data,
            event_type=EventType(form.event_type.data),
            status=TourStopStatus(form.status.data),
            venue_id=form.venue_id.data if form.venue_id.data != 0 else None,
            show_type=form.show_type.data if form.show_type.data else None,
            guarantee=form.guarantee.data,
            ticket_price=form.ticket_price.data,
            ticket_url=form.ticket_url.data,
            set_length_minutes=form.set_length_minutes.data,
            age_restriction=form.age_restriction.data if form.age_restriction.data else None,
            notes=form.notes.data,
            internal_notes=form.internal_notes.data,
            # Call times
            load_in_time=form.load_in_time.data,
            crew_call_time=form.crew_call_time.data,
            artist_call_time=form.artist_call_time.data,
            catering_time=form.catering_time.data,
            soundcheck_time=form.soundcheck_time.data,
            press_time=form.press_time.data,
            meet_greet_time=form.meet_greet_time.data,
            doors_time=form.doors_time.data,
            set_time=form.set_time.data,
            curfew_time=form.curfew_time.data
        )

        # Set tour_id OR band_id (not both)
        if form.tour_id.data and form.tour_id.data != 0:
            event.tour_id = form.tour_id.data
            event.band_id = None
        else:
            event.tour_id = None
            event.band_id = form.band_id.data

        db.session.add(event)
        db.session.commit()

        flash('Événement créé avec succès.', 'success')
        return redirect(url_for('main.global_calendar'))

    return render_template(
        'main/event_form.html',
        form=form,
        prefill_date=prefill_date,
        title='Ajouter un événement'
    )


@main_bp.route('/calendar/event/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_standalone_event(event_id):
    """Edit a standalone event."""
    event = TourStop.query.get_or_404(event_id)

    # Check permissions
    if not event.can_edit(current_user):
        flash('Vous n\'avez pas la permission de modifier cet événement.', 'danger')
        return redirect(url_for('main.global_calendar'))

    form = StandaloneEventForm(obj=event)

    # Get user's bands for the band selector
    user_bands = current_user.bands + current_user.managed_bands
    manageable_bands = [b for b in user_bands if b.is_manager(current_user)]

    form.band_id.choices = [(0, '-- Sélectionner un groupe --')] + [
        (b.id, b.name) for b in manageable_bands
    ]

    # Tour selector
    all_tours = Tour.query.filter(
        Tour.band_id.in_([b.id for b in manageable_bands])
    ).order_by(Tour.start_date.desc()).all()
    form.tour_id.choices = [(0, '-- Événement libre (sans tournée) --')] + [
        (t.id, f"{t.name} ({t.band.name})") for t in all_tours
    ]

    # Venue selector
    venues = Venue.query.order_by(Venue.name).all()
    form.venue_id.choices = [(0, '-- Sans salle --')] + [
        (v.id, f"{v.name} - {v.city}, {v.country}") for v in venues
    ]

    if request.method == 'GET':
        # Pre-fill form values
        form.event_type.data = event.event_type.value if event.event_type else 'show'
        form.status.data = event.status.value if event.status else 'hold'
        form.band_id.data = event.band_id if event.band_id else (event.tour.band_id if event.tour else 0)
        form.tour_id.data = event.tour_id if event.tour_id else 0
        form.venue_id.data = event.venue_id if event.venue_id else 0

    if form.validate_on_submit():
        event.date = form.date.data
        event.event_type = EventType(form.event_type.data)
        event.status = TourStopStatus(form.status.data)
        event.venue_id = form.venue_id.data if form.venue_id.data != 0 else None
        event.show_type = form.show_type.data if form.show_type.data else None
        event.guarantee = form.guarantee.data
        event.ticket_price = form.ticket_price.data
        event.ticket_url = form.ticket_url.data
        event.set_length_minutes = form.set_length_minutes.data
        event.age_restriction = form.age_restriction.data if form.age_restriction.data else None
        event.notes = form.notes.data
        event.internal_notes = form.internal_notes.data
        # Call times
        event.load_in_time = form.load_in_time.data
        event.crew_call_time = form.crew_call_time.data
        event.artist_call_time = form.artist_call_time.data
        event.catering_time = form.catering_time.data
        event.soundcheck_time = form.soundcheck_time.data
        event.press_time = form.press_time.data
        event.meet_greet_time = form.meet_greet_time.data
        event.doors_time = form.doors_time.data
        event.set_time = form.set_time.data
        event.curfew_time = form.curfew_time.data

        # Set tour_id OR band_id
        if form.tour_id.data and form.tour_id.data != 0:
            event.tour_id = form.tour_id.data
            event.band_id = None
        else:
            event.tour_id = None
            event.band_id = form.band_id.data

        db.session.commit()

        flash('Événement mis à jour avec succès.', 'success')
        return redirect(url_for('main.global_calendar'))

    return render_template(
        'main/event_form.html',
        form=form,
        event=event,
        title='Modifier l\'événement'
    )


@main_bp.route('/calendar/event/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_standalone_event(event_id):
    """Delete a standalone event."""
    event = TourStop.query.get_or_404(event_id)

    # Check permissions
    if not event.can_edit(current_user):
        flash('Vous n\'avez pas la permission de supprimer cet événement.', 'danger')
        return redirect(url_for('main.global_calendar'))

    db.session.delete(event)
    db.session.commit()

    flash('Événement supprimé avec succès.', 'success')
    return redirect(url_for('main.global_calendar'))
