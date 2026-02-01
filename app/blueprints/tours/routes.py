"""
Tour management routes.
"""
from datetime import timedelta

from flask import render_template, redirect, url_for, flash, request, jsonify, Response, current_app
from flask_login import login_required, current_user

from app.blueprints.tours import tours_bp
from app.blueprints.tours.forms import TourForm, TourStopForm, RescheduleStopForm, LineupSlotForm, MemberScheduleForm
from app.models.tour import Tour, TourStatus
from app.models.tour_stop import TourStop, TourStopStatus, EventType, tour_stop_members
from app.models.venue import Venue
from app.models.band import Band
from app.models.user import User
from app.models.logistics import LogisticsInfo, LogisticsType
from app.models.lineup import LineupSlot, PerformerType
from app.extensions import db
from app.decorators import tour_access_required, tour_edit_required
from app.utils.audit import log_create, log_update, log_delete
from app.utils.email import send_tour_stop_notification
from app.utils.geo import calculate_stops_distances, get_tour_total_distance
from app.utils.geocoding import geocode_address
from app.blueprints.logistics.routes import get_visible_logistics


def get_users_by_category(users_list=None, assigned_ids=None):
    """Retourne les utilisateurs groupés par catégorie de métier pour l'assignation.

    Args:
        users_list: Liste d'utilisateurs à grouper. Si None, récupère tous les utilisateurs.
        assigned_ids: Liste des IDs des utilisateurs déjà assignés au concert.

    Returns:
        tuple: (categories_data, users_without_profession)
            - categories_data: Liste de dicts avec key, label, icon, color, professions,
              total_users, assigned, required, is_critical
            - users_without_profession: Liste des utilisateurs sans profession assignée
    """
    from collections import defaultdict
    from app.models.profession import (
        ProfessionCategory, CATEGORY_LABELS, CATEGORY_ICONS, CATEGORY_COLORS
    )

    assigned_ids = set(assigned_ids) if assigned_ids else set()

    # Utiliser la liste fournie ou récupérer tous les utilisateurs
    if users_list is None:
        users_list = User.query.order_by(User.first_name, User.last_name).all()

    if not users_list:
        return [], []

    # Structure: {category: {profession_name: [users]}}
    users_by_category = defaultdict(lambda: defaultdict(list))
    users_without_profession = []
    seen = defaultdict(set)

    for user in users_list:
        if user.professions:
            for prof in user.professions:
                key = (prof.category, prof.name_fr)
                if user.id not in seen[key]:
                    users_by_category[prof.category][prof.name_fr].append(user)
                    seen[key].add(user.id)
        else:
            users_without_profession.append(user)

    # Ordre des catégories
    category_order = [
        ProfessionCategory.MUSICIEN,
        ProfessionCategory.TECHNICIEN,
        ProfessionCategory.PRODUCTION,
        ProfessionCategory.STYLE,
        ProfessionCategory.SECURITE,
        ProfessionCategory.MANAGEMENT,
    ]

    categories_data = []
    for cat in category_order:
        if cat in users_by_category:
            professions = [
                {'name': name, 'users': users}
                for name, users in sorted(users_by_category[cat].items())
            ]

            # Calculer les stats pour cette catégorie
            all_users_in_cat = []
            for prof in professions:
                all_users_in_cat.extend(prof['users'])
            # Dédupliquer (un user peut avoir plusieurs professions dans la même catégorie)
            unique_user_ids = set(u.id for u in all_users_in_cat)
            total_users = len(unique_user_ids)

            # Combien sont assignés au concert
            assigned_in_cat = len(unique_user_ids & assigned_ids)
        else:
            # Catégorie vide - toujours l'afficher pour cohérence UI
            professions = []
            total_users = 0
            assigned_in_cat = 0

        # Toujours ajouter la catégorie (même vide)
        categories_data.append({
            'key': cat.value,
            'label': CATEGORY_LABELS.get(cat, cat.value),
            'icon': CATEGORY_ICONS.get(cat, 'person'),
            'color': CATEGORY_COLORS.get(cat, 'secondary'),
            'professions': professions,
            'total_users': total_users,
            # Stats pour Overview Cards
            'assigned': assigned_in_cat,
            'required': total_users,  # Requis = tous les membres disponibles de cette catégorie
            'is_critical': False,  # Pas d'indicateur critique par défaut
        })

    return categories_data, users_without_profession


@tours_bp.route('/')
@login_required
def index():
    """List all tours for user's bands."""
    # Admin voit toutes les tournées
    if current_user.is_admin():
        user_bands = Band.query.all()
        query = Tour.query
    else:
        user_bands = current_user.bands + current_user.managed_bands
        user_band_ids = [b.id for b in user_bands]
        query = Tour.query.filter(Tour.band_id.in_(user_band_ids))

    # Filter by status if requested
    status_filter = request.args.get('status')

    if status_filter:
        try:
            status = TourStatus(status_filter)
            query = query.filter(Tour.status == status)
        except ValueError:
            pass

    tours = query.order_by(Tour.start_date.desc()).all()

    return render_template('tours/list.html', tours=tours, bands=user_bands, status_filter=status_filter)


@tours_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_tour():
    """Create a new tour - select band first."""
    managed_bands = current_user.managed_bands

    if not managed_bands:
        flash('Vous devez créer un groupe avant de créer une tournée.', 'warning')
        return redirect(url_for('bands.create'))

    form = TourForm()
    form.band_id.choices = [(b.id, b.name) for b in managed_bands]

    if form.validate_on_submit():
        band = Band.query.get(form.band_id.data)
        if not band or not band.is_manager(current_user):
            flash('Groupe invalide.', 'error')
            return redirect(url_for('tours.index'))

        tour = Tour(
            name=form.name.data,
            description=form.description.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            budget=form.budget.data,
            currency=form.currency.data,
            notes=form.notes.data,
            band_id=band.id
        )
        db.session.add(tour)
        db.session.commit()

        log_create('Tour', tour.id, {'name': tour.name, 'band_id': band.id})

        flash(f'La tournée "{tour.name}" a été créée.', 'success')
        return redirect(url_for('tours.detail', id=tour.id))

    return render_template('tours/form.html', form=form, band=None, title='Créer une tournée')


@tours_bp.route('/create/<int:band_id>', methods=['GET', 'POST'])
@login_required
def create(band_id):
    """Create a new tour for a band."""
    band = Band.query.get_or_404(band_id)

    if not band.is_manager(current_user):
        flash('Seul le manager peut créer une tournée.', 'error')
        return redirect(url_for('bands.detail', id=band_id))

    form = TourForm()
    # Définir les choix pour band_id (requis pour la validation même si on a déjà le band_id)
    form.band_id.choices = [(band.id, band.name)]

    if form.validate_on_submit():
        tour = Tour(
            name=form.name.data,
            description=form.description.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            budget=form.budget.data,
            currency=form.currency.data,
            notes=form.notes.data,
            band_id=band.id
        )
        db.session.add(tour)
        db.session.commit()

        log_create('Tour', tour.id, {'name': tour.name, 'band_id': band.id})

        flash(f'La tournée "{tour.name}" a été créée.', 'success')
        return redirect(url_for('tours.detail', id=tour.id))

    return render_template('tours/form.html', form=form, band=band, title='Créer une tournée')


@tours_bp.route('/<int:id>')
@login_required
@tour_access_required
def detail(id, tour=None):
    """View tour details and stops."""
    return render_template('tours/detail.html', tour=tour)


@tours_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@tour_edit_required
def edit(id, tour=None):
    """Edit a tour."""
    band = tour.band

    # Handle orphaned tour (band was deleted)
    if band is None:
        flash('Cette tournée est orpheline (groupe supprimé). Impossible de la modifier.', 'warning')
        return redirect(url_for('tours.detail', id=id))

    # Initialize form with tour data
    form = TourForm(obj=tour)

    # Set band_id choices BEFORE validation (required for SelectField)
    form.band_id.choices = [(band.id, band.name)]
    form.band_id.data = band.id  # Always set to current band

    if form.validate_on_submit():
        # Update tour fields (except band_id which stays unchanged)
        tour.name = form.name.data
        tour.description = form.description.data
        tour.start_date = form.start_date.data
        tour.end_date = form.end_date.data
        tour.budget = form.budget.data
        tour.currency = form.currency.data
        tour.notes = form.notes.data
        # band_id stays unchanged - tour cannot change bands

        db.session.commit()

        log_update('Tour', tour.id, {'name': tour.name})

        flash('La tournée a été mise à jour.', 'success')
        return redirect(url_for('tours.detail', id=id))

    return render_template('tours/form.html', form=form, tour=tour, band=band, title='Modifier la tournée')


@tours_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@tour_edit_required
def delete(id, tour=None):
    """Delete a tour."""
    # P-H2: Check if tour can be safely deleted
    if not tour.can_delete():
        blockers = tour.get_deletion_blockers()
        flash(f'Impossible de supprimer la tournée: {"; ".join(blockers)}', 'error')
        return redirect(url_for('tours.detail', id=id))

    tour_name = tour.name
    band_id = tour.band_id

    log_delete('Tour', tour.id, {'name': tour_name})

    db.session.delete(tour)
    db.session.commit()

    flash(f'La tournée "{tour_name}" a été supprimée.', 'success')
    return redirect(url_for('bands.detail', id=band_id))


@tours_bp.route('/<int:id>/duplicate', methods=['POST'])
@login_required
@tour_edit_required
def duplicate(id, tour=None):
    """Duplicate a tour."""
    new_tour = tour.duplicate()
    db.session.add(new_tour)
    db.session.commit()

    log_create('Tour', new_tour.id, {'name': new_tour.name, 'duplicated_from': tour.id})

    flash(f'La tournée a été dupliquée: "{new_tour.name}"', 'success')
    return redirect(url_for('tours.edit', id=new_tour.id))


@tours_bp.route('/<int:id>/status', methods=['POST'])
@login_required
@tour_edit_required
def update_status(id, tour=None):
    """Update tour status."""
    new_status = request.form.get('status')

    try:
        tour.status = TourStatus(new_status)
        db.session.commit()

        log_update('Tour', tour.id, {'status': new_status})
        flash('Le statut de la tournée a été mis à jour.', 'success')
    except ValueError:
        flash('Statut invalide.', 'error')

    return redirect(url_for('tours.detail', id=id))


# Tour Stops
@tours_bp.route('/<int:id>/stops/add', methods=['GET', 'POST'])
@login_required
@tour_edit_required
def add_stop(id, tour=None):
    """Add a stop to the tour."""
    form = TourStopForm()

    # Populate venue choices with empty option for non-venue events
    venues = Venue.query.order_by(Venue.name).all()
    form.venue_id.choices = [(0, '-- Aucune salle --')] + [(v.id, f'{v.name} - {v.city}') for v in venues]

    # Récupérer TOUS les utilisateurs actifs pour permettre d'assigner n'importe qui au concert
    all_users = User.query.filter_by(is_active=True).all()

    # Présélectionner les membres du groupe par défaut (modifiable par l'utilisateur)
    band_member_ids = [m.id for m in tour.band.members] if tour.band else []
    if tour.band and tour.band.manager:
        band_member_ids.append(tour.band.manager.id)

    # Grouper par catégorie de métier pour l'interface d'assignation
    categories_data, users_without_profession = get_users_by_category(all_users, assigned_ids=set(band_member_ids))

    if form.validate_on_submit():
        # Handle venue_id (0 means no venue for DAY_OFF, TRAVEL, etc.)
        venue_id = form.venue_id.data if form.venue_id.data != 0 else None

        stop = TourStop(
            tour_id=tour.id,
            venue_id=venue_id,
            # Location directe (si pas de venue)
            location_address=form.location_address.data or None,
            location_city=form.location_city.data or None,
            location_country=form.location_country.data or None,
            location_notes=form.location_notes.data or None,
            date=form.date.data,
            event_type=EventType(form.event_type.data),
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
            curfew_time=form.curfew_time.data,
            # Status and details
            status=TourStopStatus(form.status.data),
            show_type=form.show_type.data or None,
            # Financial fields
            guarantee=form.guarantee.data,
            venue_rental_cost=form.venue_rental_cost.data,
            ticket_price=form.ticket_price.data,
            sold_tickets=form.sold_tickets.data,
            door_deal_percentage=form.door_deal_percentage.data,
            # R1: Frais de billetterie (default 5%)
            ticketing_fee_percentage=form.ticketing_fee_percentage.data or 5.0,
            # R3: Currency inherited from tour
            currency=tour.currency,
            ticket_url=form.ticket_url.data or None,
            set_length_minutes=form.set_length_minutes.data,
            age_restriction=form.age_restriction.data or None,
            notes=form.notes.data,
            internal_notes=form.internal_notes.data
        )

        # Géocoder l'adresse directe si fournie (pour affichage sur carte)
        if stop.location_city or stop.location_address:
            try:
                lat, lon = geocode_address(
                    stop.location_address or '',
                    stop.location_city or '',
                    stop.location_country or ''
                )
                if lat is not None and lon is not None:
                    stop.location_latitude = lat
                    stop.location_longitude = lon
                    current_app.logger.info(f"Géocodage réussi pour stop: {lat}, {lon}")
            except Exception as e:
                current_app.logger.warning(f"Échec géocodage adresse tour stop: {e}")

        db.session.add(stop)
        db.session.commit()

        # Assigner les membres sélectionnés via checkboxes et envoyer les invitations
        member_ids = request.form.getlist('member_ids', type=int)
        invitations_sent = 0

        if member_ids:
            from app.models.mission_invitation import MissionInvitation
            from app.utils.email import send_mission_invitation_email

            selected_members = User.query.filter(User.id.in_(member_ids)).all()
            stop.assigned_members = selected_members
            db.session.commit()

            # Envoyer les invitations
            for member in selected_members:
                invitation, created = MissionInvitation.create_or_update(
                    tour_stop_id=stop.id,
                    user_id=member.id
                )
                if created:
                    db.session.commit()
                    if send_mission_invitation_email(invitation):
                        invitations_sent += 1

        log_create('TourStop', stop.id, {
            'tour_id': tour.id,
            'date': str(stop.date),
            'event_type': stop.event_type.value,
            'assigned_members': member_ids
        })

        # Send notification for new tour stop
        try:
            send_tour_stop_notification(stop, 'created')
        except Exception as e:
            current_app.logger.error(f'Email notification tour stop créé échoué: {e}')

        # Notification in-app pour nouvel événement
        try:
            from app.utils.notifications import notify_new_tour_stop
            notify_new_tour_stop(stop, exclude_user_id=current_user.id)
        except Exception as e:
            current_app.logger.error(f'In-app notification tour stop créé échoué: {e}')

        flash('La date a été ajoutée à la tournée.', 'success')
        return redirect(url_for('tours.detail', id=id))

    return render_template(
        'tours/stop_form.html',
        form=form,
        tour=tour,
        title='Ajouter une date',
        categories_data=categories_data,
        users_without_profession=users_without_profession,
        assigned_ids=band_member_ids,  # Membres du groupe présélectionnés
        confirmed_ids=[],
        pending_ids=[],
        declined_ids=[]
    )


@tours_bp.route('/<int:id>/stops/<int:stop_id>')
@login_required
@tour_access_required
def stop_detail(id, stop_id, tour=None):
    """View tour stop details."""
    from app.models.mission_invitation import MissionInvitation

    stop = TourStop.query.filter_by(id=stop_id, tour_id=id).first_or_404()

    # Préparer la programmation combinée (slots + groupe principal)
    all_performers = []
    main_band_in_lineup = False

    for slot in stop.lineup_slots:
        if tour.band and slot.performer_name.lower() == tour.band.name.lower():
            main_band_in_lineup = True
        all_performers.append({
            'name': slot.performer_name,
            'type': slot.performer_type.value,
            'type_label': slot.performer_type_label,
            'start_time': slot.start_time,
            'time_range': slot.time_range_formatted,
            'duration': slot.duration_formatted,
            'is_confirmed': slot.is_confirmed,
            'is_main_band': False
        })

    # Ajouter le groupe principal s'il n'est pas déjà dans la liste
    if not main_band_in_lineup:
        main_time = stop.set_time.strftime('%H:%M') if stop.set_time else None
        end_time = stop.curfew_time.strftime('%H:%M') if stop.curfew_time else None
        time_range = f"{main_time} - {end_time}" if main_time and end_time else (main_time or 'Horaire non défini')

        all_performers.append({
            'name': tour.band_name,
            'type': 'main_artist',
            'type_label': 'Artiste principal',
            'start_time': stop.set_time,
            'time_range': time_range,
            'duration': None,
            'is_confirmed': True,
            'is_main_band': True
        })

    # Trier par heure de début (None en dernier)
    all_performers.sort(key=lambda x: (x['start_time'] is None, x['start_time']))

    # Récupérer les invitations pour ce stop
    invitations = {}
    for inv in MissionInvitation.get_for_stop(stop.id):
        invitations[inv.user_id] = inv

    # Grouper les membres assignés par catégorie de métier
    assigned_ids = [m.id for m in stop.assigned_members]
    categories_data, users_without_profession = get_users_by_category(
        users_list=list(stop.assigned_members),
        assigned_ids=assigned_ids
    )

    return render_template('tours/stop_detail.html',
        tour=tour, stop=stop, performers=all_performers,
        invitations=invitations, categories_data=categories_data,
        users_without_profession=users_without_profession)


@tours_bp.route('/<int:id>/stops/<int:stop_id>/edit', methods=['GET', 'POST'])
@login_required
@tour_edit_required
def edit_stop(id, stop_id, tour=None):
    """Edit a tour stop."""
    stop = TourStop.query.filter_by(id=stop_id, tour_id=id).first_or_404()

    # Capturer la date originale pour détecter les changements
    original_date = stop.date

    form = TourStopForm(obj=stop)

    # Set enum values for display
    form.status.data = stop.status.value
    form.event_type.data = stop.event_type.value if stop.event_type else 'show'

    # Populate venue choices with empty option
    venues = Venue.query.order_by(Venue.name).all()
    form.venue_id.choices = [(0, '-- Aucune salle --')] + [(v.id, f'{v.name} - {v.city}') for v in venues]

    # Récupérer TOUS les utilisateurs actifs pour permettre d'assigner n'importe qui au concert
    all_users = User.query.filter_by(is_active=True).all()
    # IDs des membres déjà assignés à cette date
    assigned_ids = [m.id for m in stop.assigned_members]
    # Grouper par catégorie de métier pour l'interface d'assignation
    categories_data, users_without_profession = get_users_by_category(all_users, assigned_ids=assigned_ids)

    # Récupérer les statuts des invitations pour affichage
    from app.models.mission_invitation import MissionInvitation, MissionInvitationStatus
    invitations = {inv.user_id: inv for inv in MissionInvitation.get_for_stop(stop.id)}
    confirmed_ids = [uid for uid, inv in invitations.items() if inv.status == MissionInvitationStatus.ACCEPTED]
    pending_ids = [uid for uid, inv in invitations.items() if inv.status == MissionInvitationStatus.PENDING]
    declined_ids = [uid for uid, inv in invitations.items() if inv.status == MissionInvitationStatus.DECLINED]

    # Set venue_id to 0 if None
    if not request.method == 'POST' and stop.venue_id is None:
        form.venue_id.data = 0

    if form.validate_on_submit():
        # Handle venue_id (0 means no venue)
        stop.venue_id = form.venue_id.data if form.venue_id.data != 0 else None
        # Location directe (si pas de venue)
        stop.location_address = form.location_address.data or None
        stop.location_city = form.location_city.data or None
        stop.location_country = form.location_country.data or None
        stop.location_notes = form.location_notes.data or None
        stop.date = form.date.data
        stop.event_type = EventType(form.event_type.data)
        # Call times
        stop.load_in_time = form.load_in_time.data
        stop.crew_call_time = form.crew_call_time.data
        stop.artist_call_time = form.artist_call_time.data
        stop.catering_time = form.catering_time.data
        stop.soundcheck_time = form.soundcheck_time.data
        stop.press_time = form.press_time.data
        stop.meet_greet_time = form.meet_greet_time.data
        stop.doors_time = form.doors_time.data
        stop.set_time = form.set_time.data
        stop.curfew_time = form.curfew_time.data
        # Status and details
        stop.status = TourStopStatus(form.status.data)
        stop.show_type = form.show_type.data or None
        # Financial fields
        stop.guarantee = form.guarantee.data
        stop.venue_rental_cost = form.venue_rental_cost.data
        stop.ticket_price = form.ticket_price.data
        stop.sold_tickets = form.sold_tickets.data
        stop.door_deal_percentage = form.door_deal_percentage.data
        # R1: Frais de billetterie
        stop.ticketing_fee_percentage = form.ticketing_fee_percentage.data or 5.0
        stop.ticket_url = form.ticket_url.data or None
        stop.set_length_minutes = form.set_length_minutes.data
        stop.age_restriction = form.age_restriction.data or None
        stop.notes = form.notes.data
        stop.internal_notes = form.internal_notes.data

        # Géocoder l'adresse directe si fournie ou modifiée
        if stop.location_city or stop.location_address:
            try:
                lat, lon = geocode_address(
                    stop.location_address or '',
                    stop.location_city or '',
                    stop.location_country or ''
                )
                if lat is not None and lon is not None:
                    stop.location_latitude = lat
                    stop.location_longitude = lon
                    current_app.logger.info(f"Géocodage réussi pour stop: {lat}, {lon}")
            except Exception as e:
                current_app.logger.warning(f"Échec géocodage adresse tour stop: {e}")
        elif not stop.location_city and not stop.location_address:
            # Effacer les coordonnées si l'adresse est supprimée
            stop.location_latitude = None
            stop.location_longitude = None

        db.session.commit()

        # Mettre à jour les membres assignés via checkboxes
        from app.models.mission_invitation import MissionInvitation
        from app.utils.email import send_mission_invitation_email

        member_ids = request.form.getlist('member_ids', type=int)
        currently_assigned_ids = {m.id for m in stop.assigned_members}
        new_member_ids = set(member_ids) if member_ids else set()
        newly_assigned_ids = new_member_ids - currently_assigned_ids

        selected_members = User.query.filter(User.id.in_(new_member_ids)).all() if new_member_ids else []
        stop.assigned_members = selected_members
        db.session.commit()

        # Invitations aux NOUVEAUX membres uniquement
        invitations_sent = 0
        for member in selected_members:
            if member.id in newly_assigned_ids:
                invitation, created = MissionInvitation.create_or_update(
                    tour_stop_id=stop.id,
                    user_id=member.id
                )
                if created:
                    db.session.commit()
                    if send_mission_invitation_email(invitation):
                        invitations_sent += 1

        log_update('TourStop', stop.id, {
            'event_type': stop.event_type.value,
            'assigned_members': member_ids,
            'invitations_sent': invitations_sent
        })

        # Send notification for updated tour stop
        try:
            send_tour_stop_notification(stop, 'updated')
        except Exception as e:
            current_app.logger.error(f'Email notification tour stop modifié échoué: {e}')

        # Notification in-app - différencier changement de date vs autres modifications
        try:
            from app.utils.notifications import notify_tour_stop_date_changed, notify_tour_stop_updated
            if stop.date != original_date:
                # Changement de date = notification prioritaire (WARNING)
                notify_tour_stop_date_changed(stop, original_date, exclude_user_id=current_user.id)
            else:
                # Autres modifications = notification standard
                notify_tour_stop_updated(stop, exclude_user_id=current_user.id)
        except Exception as e:
            current_app.logger.error(f'In-app notification tour stop modifié échoué: {e}')

        flash('La date a été mise à jour.', 'success')
        return redirect(url_for('tours.stop_detail', id=id, stop_id=stop_id))

    return render_template(
        'tours/stop_form.html',
        form=form,
        tour=tour,
        stop=stop,
        title='Modifier la date',
        categories_data=categories_data,
        users_without_profession=users_without_profession,
        assigned_ids=assigned_ids,
        confirmed_ids=confirmed_ids,
        pending_ids=pending_ids,
        declined_ids=declined_ids
    )


@tours_bp.route('/<int:id>/stops/<int:stop_id>/copy-crew', methods=['POST'])
@login_required
@tour_edit_required
def copy_previous_crew(id, stop_id, tour=None):
    """Copie l'équipe du stop précédent vers ce stop."""
    stop = TourStop.query.filter_by(id=stop_id, tour_id=id).first_or_404()

    # Trouver le stop précédent (par date)
    previous_stop = TourStop.query.filter(
        TourStop.tour_id == id,
        TourStop.date < stop.date
    ).order_by(TourStop.date.desc()).first()

    if not previous_stop:
        flash('Aucune date précédente trouvée.', 'warning')
        return redirect(url_for('tours.edit_stop', id=id, stop_id=stop_id))

    # Copier les membres (éviter les doublons)
    copied_count = 0
    current_member_ids = {m.id for m in stop.assigned_members}
    for member in previous_stop.assigned_members:
        if member.id not in current_member_ids:
            stop.assigned_members.append(member)
            copied_count += 1

    if copied_count > 0:
        db.session.commit()
        log_update('TourStop', stop.id, {'copied_crew_from': previous_stop.id, 'copied_count': copied_count})
        flash(f'{copied_count} membre(s) copié(s) depuis {previous_stop.venue_city}.', 'success')
    else:
        flash('Tous les membres sont déjà assignés.', 'info')

    return redirect(url_for('tours.edit_stop', id=id, stop_id=stop_id))


@tours_bp.route('/<int:id>/stops/<int:stop_id>/update-tickets', methods=['POST'])
@login_required
@tour_edit_required
def update_stop_tickets(id, stop_id, tour=None):
    """Quick update for sold_tickets field from stop detail page."""
    stop = TourStop.query.filter_by(id=stop_id, tour_id=id).first_or_404()

    sold_tickets = request.form.get('sold_tickets', type=int)
    if sold_tickets is not None and sold_tickets >= 0:
        stop.sold_tickets = sold_tickets
        db.session.commit()

        log_update('TourStop', stop.id, {'sold_tickets': sold_tickets})
        flash('Billets vendus mis à jour.', 'success')
    else:
        flash('Nombre de billets invalide.', 'error')

    return redirect(url_for('tours.stop_detail', id=id, stop_id=stop_id))


@tours_bp.route('/<int:id>/stops/<int:stop_id>/delete', methods=['POST'])
@login_required
@tour_edit_required
def delete_stop(id, stop_id, tour=None):
    """Delete a tour stop."""
    stop = TourStop.query.filter_by(id=stop_id, tour_id=id).first_or_404()

    # Send notification before deletion
    try:
        send_tour_stop_notification(stop, 'cancelled')
    except Exception as e:
        current_app.logger.error(f'Email notification tour stop annulé échoué: {e}')

    log_delete('TourStop', stop.id, {'date': str(stop.date)})

    db.session.delete(stop)
    db.session.commit()

    flash('La date a été supprimée.', 'success')
    return redirect(url_for('tours.detail', id=id))


@tours_bp.route('/<int:id>/stops/<int:stop_id>/reschedule', methods=['GET', 'POST'])
@login_required
@tour_edit_required
def reschedule_stop(id, stop_id, tour=None):
    """Reporter un concert à une nouvelle date.

    Conserve la date originale pour affichage dual (grisée/barrée)
    avec lien visuel vers la nouvelle date.
    """
    stop = TourStop.query.filter_by(id=stop_id, tour_id=id).first_or_404()

    # Vérifier que le stop peut être reporté
    if not stop.can_transition_to(TourStopStatus.RESCHEDULED):
        flash('Ce concert ne peut pas être reporté dans son état actuel.', 'error')
        return redirect(url_for('tours.stop_detail', id=id, stop_id=stop_id))

    # Proposer le lendemain du concert actuel comme date par défaut
    default_date = stop.date + timedelta(days=1)
    # S'assurer que la date est dans les limites de la tournée
    if default_date > tour.end_date:
        default_date = tour.end_date

    form = RescheduleStopForm(data={'new_date': default_date})

    if form.validate_on_submit():
        original_date = stop.date
        reason = form.reason.data if form.reason.data else None

        # Effectuer le report
        if stop.reschedule(form.new_date.data, reason):
            # Ajouter les notes additionnelles si fournies
            if form.notes.data:
                existing_notes = stop.internal_notes or ''
                reschedule_note = f"\n[REPORT {stop.reschedule_count}] {original_date.strftime('%d/%m/%Y')} → {form.new_date.data.strftime('%d/%m/%Y')}"
                if reason:
                    reschedule_note += f" - Raison: {reason}"
                if form.notes.data:
                    reschedule_note += f"\n{form.notes.data}"
                stop.internal_notes = existing_notes + reschedule_note

            db.session.commit()

            log_update('TourStop', stop.id, {
                'action': 'reschedule',
                'original_date': str(original_date),
                'new_date': str(form.new_date.data),
                'reason': reason,
                'reschedule_count': stop.reschedule_count
            })

            # Notification du report
            try:
                send_tour_stop_notification(stop, 'rescheduled')
            except Exception as e:
                current_app.logger.error(f'Email notification report échoué: {e}')

            flash(f'Concert reporté du {original_date.strftime("%d/%m/%Y")} au {form.new_date.data.strftime("%d/%m/%Y")}.', 'success')
            return redirect(url_for('tours.stop_detail', id=id, stop_id=stop_id))
        else:
            flash('Impossible de reporter ce concert.', 'error')

    return render_template('tours/reschedule_stop.html', form=form, tour=tour, stop=stop)


# ============================================================================
# LINEUP / PROGRAMMATION ROUTES
# ============================================================================

@tours_bp.route('/<int:id>/stops/<int:stop_id>/lineup', methods=['GET', 'POST'])
@login_required
@tour_edit_required
def manage_lineup(id, stop_id, tour=None):
    """Gérer la programmation/lineup d'un concert."""
    stop = TourStop.query.filter_by(id=stop_id, tour_id=id).first_or_404()

    form = LineupSlotForm()

    if form.validate_on_submit():
        # Créer le nouveau slot
        slot = LineupSlot(
            tour_stop_id=stop.id,
            performer_name=form.performer_name.data,
            performer_type=PerformerType(form.performer_type.data),
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            set_length_minutes=form.set_length_minutes.data,
            order=form.order.data,
            notes=form.notes.data,
            is_confirmed=form.is_confirmed.data
        )
        db.session.add(slot)
        db.session.commit()

        log_create('LineupSlot', slot.id, {
            'tour_stop_id': stop.id,
            'performer_name': slot.performer_name,
            'performer_type': slot.performer_type.value,
            'start_time': str(slot.start_time)
        })

        flash(f'"{slot.performer_name}" ajouté à la programmation.', 'success')
        return redirect(url_for('tours.manage_lineup', id=id, stop_id=stop_id))

    # Pré-remplir l'ordre avec la prochaine position
    if not form.order.data:
        next_order = len(stop.lineup_slots) + 1
        form.order.data = next_order

    return render_template('tours/lineup_manage.html', tour=tour, stop=stop, form=form)


@tours_bp.route('/<int:id>/stops/<int:stop_id>/lineup/<int:slot_id>/edit', methods=['GET', 'POST'])
@login_required
@tour_edit_required
def edit_lineup_slot(id, stop_id, slot_id, tour=None):
    """Modifier un slot du lineup."""
    stop = TourStop.query.filter_by(id=stop_id, tour_id=id).first_or_404()
    slot = LineupSlot.query.filter_by(id=slot_id, tour_stop_id=stop_id).first_or_404()

    form = LineupSlotForm(obj=slot)

    # Convertir performer_type en string pour le formulaire
    if request.method == 'GET':
        form.performer_type.data = slot.performer_type.value

    if form.validate_on_submit():
        slot.performer_name = form.performer_name.data
        slot.performer_type = PerformerType(form.performer_type.data)
        slot.start_time = form.start_time.data
        slot.end_time = form.end_time.data
        slot.set_length_minutes = form.set_length_minutes.data
        slot.order = form.order.data
        slot.notes = form.notes.data
        slot.is_confirmed = form.is_confirmed.data

        db.session.commit()

        log_update('LineupSlot', slot.id, {
            'performer_name': slot.performer_name,
            'performer_type': slot.performer_type.value
        })

        flash(f'"{slot.performer_name}" mis à jour.', 'success')
        return redirect(url_for('tours.manage_lineup', id=id, stop_id=stop_id))

    return render_template('tours/lineup_edit.html', tour=tour, stop=stop, slot=slot, form=form)


@tours_bp.route('/<int:id>/stops/<int:stop_id>/lineup/<int:slot_id>/delete', methods=['POST'])
@login_required
@tour_edit_required
def delete_lineup_slot(id, stop_id, slot_id, tour=None):
    """Supprimer un slot du lineup."""
    slot = LineupSlot.query.filter_by(id=slot_id, tour_stop_id=stop_id).first_or_404()

    performer_name = slot.performer_name

    log_delete('LineupSlot', slot.id, {
        'performer_name': performer_name,
        'tour_stop_id': stop_id
    })

    db.session.delete(slot)
    db.session.commit()

    flash(f'"{performer_name}" retiré de la programmation.', 'success')
    return redirect(url_for('tours.manage_lineup', id=id, stop_id=stop_id))


@tours_bp.route('/<int:id>/stops/<int:stop_id>/lineup/reorder', methods=['POST'])
@login_required
@tour_edit_required
def reorder_lineup(id, stop_id, tour=None):
    """Réorganiser l'ordre du lineup via AJAX."""
    stop = TourStop.query.filter_by(id=stop_id, tour_id=id).first_or_404()

    data = request.get_json()
    if not data or 'order' not in data:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400

    # data['order'] est une liste d'IDs dans le nouvel ordre
    new_order = data['order']

    for index, slot_id in enumerate(new_order, start=1):
        slot = LineupSlot.query.filter_by(id=slot_id, tour_stop_id=stop.id).first()
        if slot:
            slot.order = index

    db.session.commit()

    return jsonify({'success': True})


@tours_bp.route('/<int:id>/stops/<int:stop_id>/day-sheet')
@login_required
@tour_access_required
def day_sheet(id, stop_id, tour=None):
    """Day Sheet view - detailed timeline for a tour stop."""
    stop = TourStop.query.filter_by(id=stop_id, tour_id=id).first_or_404()
    return render_template('tours/day_sheet.html', tour=tour, stop=stop)


@tours_bp.route('/<int:id>/overview')
@login_required
@tour_access_required
def overview(id, tour=None):
    """Tour overview dashboard with consolidated view."""
    from datetime import date
    return render_template('tours/overview.html', tour=tour, today=date.today())


@tours_bp.route('/<int:id>/calendar')
@login_required
@tour_access_required
def calendar(id, tour=None):
    """Calendar view of tour stops."""
    return render_template('tours/calendar.html', tour=tour)


@tours_bp.route('/<int:id>/map')
@login_required
@tour_access_required
def tour_map(id, tour=None):
    """Interactive map view of tour route."""
    # Get stops with coordinates (from venue OR direct location)
    stops_with_coords = [
        stop for stop in tour.stops
        if stop.has_coordinates
    ]

    # Calculate distances between stops
    distances = calculate_stops_distances(stops_with_coords)
    total_distance, valid_segments = get_tour_total_distance(stops_with_coords)

    # Create a distance lookup by stop ID
    distance_to_next = {}
    for d in distances:
        if d['distance_km'] is not None:
            distance_to_next[d['from_stop'].id] = {
                'distance_km': d['distance_km'],
                'travel_time': d['estimated_time_formatted'],
                'to_stop_id': d['to_stop'].id
            }

    # Collect logistics data for map layers (filtered by user role)
    hotels = []
    transports = []

    # Filter logistics by user role - managers see all, users see only assigned items
    all_logistics = []
    for stop in tour.stops:
        visible = get_visible_logistics(stop, current_user)
        all_logistics.extend(visible)

    for log_item in all_logistics:
        stop = log_item.tour_stop

        # Hotels and accommodations with GPS
        if log_item.is_accommodation and log_item.has_coordinates:
            # Get assigned users for this logistics item
            assigned_users = []
            for assignment in log_item.assignments.all():
                user = assignment.user
                assigned_users.append({
                    'name': f"{user.first_name} {user.last_name[0]}." if user.last_name else user.first_name,
                    'room': assignment.room_number or ''
                })

            hotels.append({
                'id': log_item.id,
                'lat': float(log_item.latitude),
                'lng': float(log_item.longitude),
                'name': log_item.provider or 'Hebergement',
                'address': log_item.address or '',
                'city': log_item.city or '',
                'type': log_item.logistics_type.value,
                'type_label': 'Hotel' if log_item.logistics_type == LogisticsType.HOTEL else 'Appartement',
                'check_in': log_item.check_in_time.strftime('%H:%M') if log_item.check_in_time else None,
                'check_out': log_item.check_out_time.strftime('%H:%M') if log_item.check_out_time else None,
                'rooms': log_item.number_of_rooms or 1,
                'breakfast': log_item.breakfast_included,
                'stop_date': stop.date.strftime('%d/%m/%Y') if stop else '',
                'stop_id': stop.id if stop else None,
                'status': log_item.status.value if log_item.status else 'pending',
                'status_label': log_item.status_label,
                'icon': log_item.type_icon,
                'color': log_item.type_color,
                'assigned_users': assigned_users
            })

        # Transports with departure/arrival GPS
        if log_item.is_transport:
            # Get assigned users (passengers) for this transport
            transport_users = []
            for assignment in log_item.assignments.all():
                user = assignment.user
                transport_users.append({
                    'name': f"{user.first_name} {user.last_name[0]}." if user.last_name else user.first_name,
                    'seat': assignment.seat_number or ''
                })

            transport_data = {
                'id': log_item.id,
                'type': log_item.logistics_type.value,
                'type_label': log_item.display_name,
                'provider': log_item.provider or '',
                'stop_date': stop.date.strftime('%d/%m/%Y') if stop else '',
                'stop_id': stop.id if stop else None,
                'status': log_item.status.value if log_item.status else 'pending',
                'status_label': log_item.status_label,
                'icon': log_item.type_icon,
                'color': log_item.type_color,
                'assigned_users': transport_users,
                'departure': None,
                'arrival': None
            }

            # Flight specific
            if log_item.logistics_type == LogisticsType.FLIGHT:
                transport_data['flight_number'] = log_item.flight_number

                if log_item.has_departure_coordinates:
                    transport_data['departure'] = {
                        'lat': float(log_item.departure_lat),
                        'lng': float(log_item.departure_lng),
                        'airport': log_item.departure_airport or '',
                        'terminal': log_item.departure_terminal or '',
                        'time': log_item.start_datetime.strftime('%H:%M') if log_item.start_datetime else ''
                    }

                if log_item.has_arrival_coordinates:
                    transport_data['arrival'] = {
                        'lat': float(log_item.arrival_lat),
                        'lng': float(log_item.arrival_lng),
                        'airport': log_item.arrival_airport or '',
                        'terminal': log_item.arrival_terminal or '',
                        'time': log_item.end_datetime.strftime('%H:%M') if log_item.end_datetime else ''
                    }

            # Ground transport with pickup/dropoff
            else:
                # Use departure_lat/lng for pickup location (preferred over generic latitude/longitude)
                if log_item.has_departure_coordinates:
                    transport_data['departure'] = {
                        'lat': float(log_item.departure_lat),
                        'lng': float(log_item.departure_lng),
                        'location': log_item.pickup_location or '',
                        'time': log_item.start_datetime.strftime('%H:%M') if log_item.start_datetime else ''
                    }
                elif log_item.has_coordinates:
                    # Fallback to generic coordinates for backward compatibility
                    transport_data['departure'] = {
                        'lat': float(log_item.latitude),
                        'lng': float(log_item.longitude),
                        'location': log_item.pickup_location or log_item.address or '',
                        'time': log_item.start_datetime.strftime('%H:%M') if log_item.start_datetime else ''
                    }

                # Use arrival_lat/lng for dropoff location
                if log_item.has_arrival_coordinates:
                    transport_data['arrival'] = {
                        'lat': float(log_item.arrival_lat),
                        'lng': float(log_item.arrival_lng),
                        'location': log_item.dropoff_location or '',
                        'time': log_item.end_datetime.strftime('%H:%M') if log_item.end_datetime else ''
                    }

            # Only add if we have at least one coordinate
            if transport_data['departure'] or transport_data['arrival']:
                transports.append(transport_data)

    return render_template(
        'tours/map.html',
        tour=tour,
        stops_with_coords=stops_with_coords,
        distances=distances,
        distance_to_next=distance_to_next,
        total_distance=total_distance,
        valid_segments=valid_segments,
        hotels=hotels,
        transports=transports
    )


@tours_bp.route('/<int:id>/calendar/events')
@login_required
@tour_access_required
def calendar_events(id, tour=None):
    """Return tour stops as JSON for FullCalendar."""
    events = []
    for stop in tour.stops:
        # Handle stops without venue (DAY_OFF, TRAVEL, etc.)
        if stop.venue:
            title = f'{stop.venue.name} - {stop.venue.city}'
        else:
            title = stop.location_city or stop.event_label or 'Non défini'

        events.append({
            'id': stop.id,
            'title': title,
            'start': stop.date.isoformat(),
            'url': url_for('tours.stop_detail', id=id, stop_id=stop.id),
            'className': f'status-{stop.status.value}' if stop.status else 'status-pending'
        })
    return jsonify(events)


@tours_bp.route('/<int:id>/export.ics')
@login_required
@tour_access_required
def export_ical(id, tour=None):
    """
    Export tour stops as iCal file.

    Generates a proper iCal calendar file with:
    - Timezone support (Europe/Paris)
    - Proper start/end times (set_time → curfew_time)
    - Rich descriptions with call times and venue info
    - VALARM reminders (1 day before)
    - Categories by event type
    - Status (CONFIRMED, TENTATIVE, CANCELLED)
    """
    from app.utils.ical import generate_tour_ical

    ical_content = generate_tour_ical(tour, include_alarms=True)

    response = Response(ical_content, mimetype='text/calendar')
    response.headers['Content-Disposition'] = f'attachment; filename="{tour.name}.ics"'
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    return response


@tours_bp.route('/<int:id>/stops/<int:stop_id>/export.ics')
@login_required
@tour_access_required
def export_stop_ical(id, stop_id, tour=None):
    """
    Export a single tour stop as iCal file.

    Allows users to add a single event to their calendar.
    """
    from app.utils.ical import generate_stop_ical

    stop = TourStop.query.filter_by(id=stop_id, tour_id=id).first_or_404()

    ical_content = generate_stop_ical(stop, tour, include_alarm=True)

    # Build filename
    date_str = stop.date.strftime('%Y-%m-%d')
    location = stop.venue.name if stop.venue else stop.location_city or 'event'
    filename = f"{date_str}_{location}.ics".replace(' ', '_')

    response = Response(ical_content, mimetype='text/calendar')
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    return response


@tours_bp.route('/<int:id>/calendar.ics')
def calendar_feed(id):
    """
    Calendar subscription feed (URL for Google Calendar/Apple Calendar).

    This endpoint can be used as a subscription URL - calendar apps will
    automatically fetch updates. No login required (uses token authentication).

    Usage:
        1. Copy the URL with token: /tours/123/calendar.ics?token=xxx
        2. In Google Calendar: Add calendar → From URL → Paste URL
        3. Calendar will auto-sync updates
    """
    from app.utils.ical import generate_tour_ical

    # Check token authentication for public access
    token = request.args.get('token')
    tour = Tour.query.get_or_404(id)

    # If user is logged in, allow access
    if current_user.is_authenticated:
        if not tour.can_view(current_user):
            abort(403)
    else:
        # For anonymous access, require valid token
        if not token:
            abort(401, description="Token requis pour accès au calendrier. Connectez-vous ou utilisez un lien avec token.")

        # Validate token (simple hash of tour_id + band_id + secret)
        expected_token = _generate_calendar_token(tour)
        if token != expected_token:
            abort(403, description="Token invalide")

    ical_content = generate_tour_ical(tour, include_alarms=False)  # No alarms for feeds

    response = Response(ical_content, mimetype='text/calendar')
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    # Allow caching for 1 hour (feeds are polled periodically)
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response


def _generate_calendar_token(tour):
    """Generate a simple token for calendar feed authentication."""
    import hashlib
    from flask import current_app

    secret = current_app.config.get('SECRET_KEY', 'default-secret')
    data = f"calendar-{tour.id}-{tour.band_id}-{secret}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]


@tours_bp.route('/<int:id>/calendar-url')
@login_required
@tour_access_required
def get_calendar_url(id, tour=None):
    """
    Get the subscription URL for this tour's calendar.

    Returns JSON with the feed URL that can be added to calendar apps.
    """
    token = _generate_calendar_token(tour)
    feed_url = url_for('tours.calendar_feed', id=id, token=token, _external=True)

    return jsonify({
        'success': True,
        'feed_url': feed_url,
        'instructions': {
            'google': 'Google Calendar → Autres agendas → À partir de l\'URL → Coller l\'URL',
            'apple': 'Calendrier → Fichier → Nouvel abonnement → Coller l\'URL',
            'outlook': 'Outlook → Ajouter un calendrier → À partir d\'Internet → Coller l\'URL'
        }
    })


# ==================== GESTION DES MEMBRES ASSIGNÉS ====================

@tours_bp.route('/<int:id>/stops/<int:stop_id>/assign', methods=['GET', 'POST'])
@login_required
@tour_edit_required
def assign_members(id, stop_id, tour=None):
    """Assigner des membres à un tour stop (événement).

    Les membres assignés peuvent voir cet événement dans leur calendrier global.
    Une invitation de mission est envoyée automatiquement aux nouveaux membres.
    """
    from app.models.mission_invitation import MissionInvitation
    from app.utils.email import send_mission_invitation_email

    stop = TourStop.query.filter_by(id=stop_id, tour_id=id).first_or_404()

    # Récupérer tous les membres du groupe (membres + managers)
    band = tour.band
    if band is None:
        flash('Cette tournée est orpheline (groupe supprimé).', 'warning')
        return redirect(url_for('tours.stop_detail', id=id, stop_id=stop_id))
    band_members = band.members + [band.manager] if band.manager else band.members

    if request.method == 'POST':
        # Récupérer les IDs des membres sélectionnés
        member_ids = request.form.getlist('member_ids', type=int)

        # T-H1: Validate that all member_ids are actual band members
        valid_member_ids = {m.id for m in band_members}
        invalid_ids = [mid for mid in member_ids if mid not in valid_member_ids]
        if invalid_ids:
            flash(f'Certains utilisateurs ne sont pas membres du groupe: {invalid_ids}', 'error')
            return redirect(url_for('tours.assign_members', id=id, stop_id=stop_id))

        # Identifier les membres déjà assignés vs nouveaux
        currently_assigned_ids = {m.id for m in stop.assigned_members}
        newly_assigned_ids = set(member_ids) - currently_assigned_ids

        # Mettre à jour les membres assignés (only valid band members)
        selected_members = [m for m in band_members if m.id in member_ids] if member_ids else []
        stop.assigned_members = selected_members

        db.session.commit()

        # Créer des invitations et envoyer des emails pour les NOUVEAUX membres
        invitations_sent = 0
        for member in selected_members:
            if member.id in newly_assigned_ids:
                # Créer ou récupérer l'invitation
                invitation, created = MissionInvitation.create_or_update(
                    tour_stop_id=stop.id,
                    user_id=member.id
                )
                if created:
                    db.session.commit()
                    # Envoyer l'email d'invitation
                    if send_mission_invitation_email(invitation):
                        invitations_sent += 1

        log_update('TourStop', stop.id, {
            'assigned_members': [m.id for m in selected_members],
            'invitations_sent': invitations_sent
        })

        if invitations_sent > 0:
            flash(f'{len(selected_members)} membre(s) assigné(s). {invitations_sent} invitation(s) envoyée(s).', 'success')
        else:
            flash(f'{len(selected_members)} membre(s) assigné(s) à cet événement.', 'success')
        return redirect(url_for('tours.stop_detail', id=id, stop_id=stop_id))

    # GET: Afficher le formulaire d'assignation avec statuts invitations
    # Récupérer les invitations existantes pour ce stop
    invitations = {inv.user_id: inv for inv in MissionInvitation.get_for_stop(stop.id)}

    # Grouper les membres par catégorie de profession (comme dans add_stop/edit_stop)
    # FIX: Utiliser all_users au lieu de band_members (qui peut être vide)
    all_users = User.query.filter_by(is_active=True).all()
    assigned_ids_set = set(m.id for m in stop.assigned_members)
    categories_data, users_without_profession = get_users_by_category(
        all_users,
        assigned_ids=assigned_ids_set
    )

    # Statuts d'invitation pour affichage
    confirmed_ids = [uid for uid, inv in invitations.items() if inv.is_accepted]
    pending_ids = [uid for uid, inv in invitations.items() if inv.is_pending]
    declined_ids = [uid for uid, inv in invitations.items() if inv.is_declined]

    return render_template(
        'tours/assign_members.html',
        tour=tour,
        stop=stop,
        band_members=band_members,
        categories_data=categories_data,
        users_without_profession=users_without_profession,
        assigned_ids=list(assigned_ids_set),
        invitations=invitations,
        confirmed_ids=confirmed_ids,
        pending_ids=pending_ids,
        declined_ids=declined_ids
    )


@tours_bp.route('/<int:id>/stops/<int:stop_id>/assign-all', methods=['POST'])
@login_required
@tour_edit_required
def assign_all_members(id, stop_id, tour=None):
    """Assigner tous les membres du groupe à un tour stop et envoyer les invitations."""
    from app.models.mission_invitation import MissionInvitation
    from app.utils.email import send_mission_invitation_email

    stop = TourStop.query.filter_by(id=stop_id, tour_id=id).first_or_404()

    # Récupérer tous les membres du groupe
    band = tour.band
    if band is None:
        flash('Cette tournée est orpheline (groupe supprimé).', 'warning')
        return redirect(url_for('tours.stop_detail', id=id, stop_id=stop_id))
    all_members = band.members + ([band.manager] if band.manager else [])

    # Identifier les membres déjà assignés
    currently_assigned_ids = {m.id for m in stop.assigned_members}

    stop.assigned_members = all_members
    db.session.commit()

    # Envoyer des invitations aux nouveaux membres
    invitations_sent = 0
    for member in all_members:
        if member.id not in currently_assigned_ids:
            invitation, created = MissionInvitation.create_or_update(
                tour_stop_id=stop.id,
                user_id=member.id
            )
            if created:
                db.session.commit()
                if send_mission_invitation_email(invitation):
                    invitations_sent += 1

    log_update('TourStop', stop.id, {
        'assigned_members': [m.id for m in all_members],
        'action': 'assign_all',
        'invitations_sent': invitations_sent
    })

    flash(f'Tous les membres ({len(all_members)}) ont été assignés. {invitations_sent} invitation(s) envoyée(s).', 'success')
    return redirect(url_for('tours.stop_detail', id=id, stop_id=stop_id))


@tours_bp.route('/<int:id>/stops/<int:stop_id>/unassign-all', methods=['POST'])
@login_required
@tour_edit_required
def unassign_all_members(id, stop_id, tour=None):
    """Retirer tous les membres assignés d'un tour stop."""
    stop = TourStop.query.filter_by(id=stop_id, tour_id=id).first_or_404()

    stop.assigned_members = []
    db.session.commit()

    log_update('TourStop', stop.id, {
        'assigned_members': [],
        'action': 'unassign_all'
    })

    flash('Tous les membres ont été retirés.', 'success')
    return redirect(url_for('tours.stop_detail', id=id, stop_id=stop_id))


# ==================== MISSION INVITATIONS ====================

@tours_bp.route('/mission/<token>/accept')
def mission_accept(token):
    """Accepter une invitation de mission via lien email."""
    from app.models.mission_invitation import MissionInvitation
    from app.utils.email import send_mission_response_notification

    invitation = MissionInvitation.get_by_token(token)
    if not invitation:
        flash('Lien d\'invitation invalide ou expiré.', 'error')
        return redirect(url_for('main.dashboard'))

    if not invitation.is_pending:
        flash(f'Vous avez déjà répondu à cette invitation ({invitation.status_label}).', 'warning')
        return redirect(url_for('main.dashboard'))

    invitation.accept()
    db.session.commit()

    # Notifier le manager
    send_mission_response_notification(invitation)

    tour_stop = invitation.tour_stop
    location = tour_stop.venue.name if tour_stop.venue else tour_stop.location_city or 'Lieu'

    flash(f'Merci ! Vous avez accepté la mission du {tour_stop.date.strftime("%d/%m/%Y")} à {location}.', 'success')
    return redirect(url_for('main.dashboard'))


@tours_bp.route('/mission/<token>/decline', methods=['GET', 'POST'])
def mission_decline(token):
    """Refuser une invitation de mission via lien email."""
    from app.models.mission_invitation import MissionInvitation
    from app.utils.email import send_mission_response_notification

    invitation = MissionInvitation.get_by_token(token)
    if not invitation:
        flash('Lien d\'invitation invalide ou expiré.', 'error')
        return redirect(url_for('main.dashboard'))

    if not invitation.is_pending:
        flash(f'Vous avez déjà répondu à cette invitation ({invitation.status_label}).', 'warning')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        reason = request.form.get('reason', '').strip()
        invitation.decline(note=reason if reason else None)
        db.session.commit()

        # Notifier le manager
        send_mission_response_notification(invitation)

        tour_stop = invitation.tour_stop
        location = tour_stop.venue.name if tour_stop.venue else tour_stop.location_city or 'Lieu'

        flash(f'Votre refus pour la mission du {tour_stop.date.strftime("%d/%m/%Y")} à {location} a été enregistré.', 'info')
        return redirect(url_for('main.dashboard'))

    # GET: Afficher formulaire pour saisir la raison
    return render_template(
        'tours/mission_decline.html',
        invitation=invitation,
        tour_stop=invitation.tour_stop
    )


@tours_bp.route('/<int:id>/stops/<int:stop_id>/invitation/<int:inv_id>/resend', methods=['POST'])
@login_required
@tour_edit_required
def resend_invitation(id, stop_id, inv_id, tour=None):
    """Renvoyer une invitation de mission."""
    from app.models.mission_invitation import MissionInvitation
    from app.utils.email import send_mission_invitation_email

    invitation = MissionInvitation.query.filter_by(
        id=inv_id,
        tour_stop_id=stop_id
    ).first_or_404()

    # Regénérer le token et renvoyer
    invitation.regenerate_token()
    invitation.record_reminder()
    db.session.commit()

    if send_mission_invitation_email(invitation, resend=True):
        flash(f'Invitation renvoyée à {invitation.user.full_name}.', 'success')
    else:
        flash(f'Erreur lors de l\'envoi de l\'invitation à {invitation.user.full_name}.', 'error')

    return redirect(url_for('tours.assign_members', id=id, stop_id=stop_id))


# ============================================================================
# STAFF PLANNING - Planning du Personnel par Utilisateur Assigné
# ============================================================================

@tours_bp.route('/<int:id>/stops/<int:stop_id>/planning')
@tours_bp.route('/<int:id>/stops/<int:stop_id>/planning/<category>')
@login_required
@tour_access_required
def staff_planning(id, stop_id, category='tous', tour=None):
    """Planning du personnel - Vue Gantt avec utilisateurs individuels groupés par profession."""
    from app.models.tour_stop import TourStopMember
    from app.models.planning_slot import PlanningSlot, CATEGORY_COLORS, CATEGORY_LABELS
    from app.models.profession import Profession, ProfessionCategory

    stop = TourStop.query.filter_by(id=stop_id, tour_id=id).first_or_404()

    # Catégories valides avec leurs métadonnées
    categories_config = [
        {'key': 'musicien', 'label': 'ARTISTES', 'color': '#8b5cf6', 'icon': 'music-note-beamed'},
        {'key': 'technicien', 'label': 'TECHNICIENS', 'color': '#3b82f6', 'icon': 'tools'},
        {'key': 'production', 'label': 'PRODUCTION', 'color': '#f97316', 'icon': 'clipboard-check'},
        {'key': 'style', 'label': 'HABILLEURS & MAQUILL.', 'color': '#ec4899', 'icon': 'brush'},
        {'key': 'securite', 'label': 'SÉCURITÉ', 'color': '#ef4444', 'icon': 'shield-check'},
        {'key': 'management', 'label': 'MANAGERS', 'color': '#22c55e', 'icon': 'briefcase'},
    ]
    valid_categories = ['tous'] + [c['key'] for c in categories_config]

    if category not in valid_categories:
        flash('Catégorie invalide.', 'error')
        return redirect(url_for('tours.staff_planning', id=id, stop_id=stop_id, category='tous'))

    # Charger les membres assignés avec statuts valides (En attente, Confirmé, Provisoire)
    from app.models.tour_stop import MemberAssignmentStatus
    valid_statuses = [
        MemberAssignmentStatus.ASSIGNED,
        MemberAssignmentStatus.CONFIRMED,
        MemberAssignmentStatus.TENTATIVE
    ]
    all_members = TourStopMember.query.filter(
        TourStopMember.tour_stop_id == stop_id,
        TourStopMember.status.in_(valid_statuses)
    ).all()

    # Charger tous les slots pour ce concert (indexés par user_id)
    all_slots = PlanningSlot.query.filter_by(tour_stop_id=stop_id).order_by(PlanningSlot.start_time).all()
    slots_by_user = {}
    for slot in all_slots:
        if slot.user_id:
            if slot.user_id not in slots_by_user:
                slots_by_user[slot.user_id] = []
            slots_by_user[slot.user_id].append(slot)

    # Grouper les membres par catégorie
    members_by_category = {}
    for member in all_members:
        # Déterminer la profession et sa catégorie
        if member.profession:
            profession = member.profession
        elif member.user and member.user.professions:
            profession = member.user.professions[0]
        else:
            profession = None

        if profession and profession.category:
            cat_key = profession.category.value
        else:
            cat_key = 'autre'

        # Filtrer si une catégorie spécifique est demandée
        if category != 'tous' and cat_key != category:
            continue

        if cat_key not in members_by_category:
            members_by_category[cat_key] = []

        # Récupérer les slots de ce membre
        user_slots = slots_by_user.get(member.user_id, []) if member.user_id else []

        members_by_category[cat_key].append({
            'id': member.user_id,
            'member_id': member.id,
            'name': member.user.full_name if member.user else 'Inconnu',
            'profession': profession.name_fr if profession else 'Non définie',
            'slots': user_slots
        })

    # Construire planning_data avec la structure attendue par le template
    planning_data = []
    total_slots = 0
    active_categories = 0

    for cat_config in categories_config:
        cat_key = cat_config['key']
        if category != 'tous' and cat_key != category:
            continue

        members_list = members_by_category.get(cat_key, [])
        if members_list:
            active_categories += 1
            for m in members_list:
                total_slots += len(m.get('slots', []))

        planning_data.append({
            'key': cat_key,
            'label': cat_config['label'],
            'color': cat_config['color'],
            'icon': cat_config['icon'],
            'members': members_list
        })

    # Heures de la grille (01:00 à 00:00 minuit)
    hours = list(range(1, 24)) + [0]

    # Permissions
    can_edit = tour.band.is_manager(current_user) if tour and tour.band else current_user.is_admin()

    # Total des membres assignés
    total_members = sum(len(cat.get('members', [])) for cat in planning_data)

    return render_template(
        'tours/planning_gantt.html',
        tour=tour,
        stop=stop,
        planning_data=planning_data,
        categories_config=categories_config,
        current_category=category,
        can_edit=can_edit,
        hours=hours,
        total_members=total_members,
        total_slots=total_slots,
        active_categories=active_categories
    )


@tours_bp.route('/<int:id>/stops/<int:stop_id>/planning/member/<int:member_id>', methods=['POST'])
@login_required
@tour_edit_required
def update_member_schedule(id, stop_id, member_id, tour=None):
    """Mettre à jour le planning d'un membre assigné au concert."""
    from app.models.tour_stop import TourStopMember
    from datetime import datetime

    member = TourStopMember.query.filter_by(
        id=member_id,
        tour_stop_id=stop_id
    ).first_or_404()

    # Fonction helper pour parser les heures
    def parse_time(time_str):
        if not time_str:
            return None
        try:
            return datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            return None

    # Mettre à jour les horaires
    member.call_time = parse_time(request.form.get('call_time'))
    member.work_start = parse_time(request.form.get('work_start'))
    member.work_end = parse_time(request.form.get('work_end'))
    member.break_start = parse_time(request.form.get('break_start'))
    member.break_end = parse_time(request.form.get('break_end'))
    member.meal_time = parse_time(request.form.get('meal_time'))
    member.notes = request.form.get('notes', '').strip() or None

    db.session.commit()
    log_update('TourStopMember', member.id, {
        'user_id': member.user_id,
        'call_time': str(member.call_time) if member.call_time else None,
        'work_start': str(member.work_start) if member.work_start else None,
        'work_end': str(member.work_end) if member.work_end else None
    })

    flash(f'Planning de {member.user.full_name} mis à jour.', 'success')

    # Rediriger vers la bonne catégorie
    category = request.args.get('category', 'tous')
    return redirect(url_for('tours.staff_planning', id=id, stop_id=stop_id, category=category))


@tours_bp.route('/<int:id>/stops/<int:stop_id>/planning/member/<int:member_id>/json', methods=['GET'])
@login_required
@tour_access_required
def get_member_schedule_json(id, stop_id, member_id, tour=None):
    """Récupérer le planning d'un membre en JSON pour l'édition."""
    from app.models.tour_stop import TourStopMember

    member = TourStopMember.query.filter_by(
        id=member_id,
        tour_stop_id=stop_id
    ).first_or_404()

    return jsonify({
        'id': member.id,
        'user_name': member.user.full_name if member.user else 'Inconnu',
        'profession': member.profession.name_fr if member.profession else (
            member.user.professions[0].name_fr if member.user and member.user.professions else 'Non définie'
        ),
        'call_time': member.call_time.strftime('%H:%M') if member.call_time else '',
        'work_start': member.work_start.strftime('%H:%M') if member.work_start else '',
        'work_end': member.work_end.strftime('%H:%M') if member.work_end else '',
        'break_start': member.break_start.strftime('%H:%M') if member.break_start else '',
        'break_end': member.break_end.strftime('%H:%M') if member.break_end else '',
        'meal_time': member.meal_time.strftime('%H:%M') if member.meal_time else '',
        'notes': member.notes or ''
    })


# ==================== PLANNING SLOTS CRUD ====================

@tours_bp.route('/<int:id>/stops/<int:stop_id>/planning/add-slot', methods=['POST'])
@login_required
@tour_edit_required
def add_planning_slot(id, stop_id, tour=None):
    """Ajouter un créneau horaire au planning."""
    from app.models.planning_slot import PlanningSlot
    from datetime import datetime

    stop = TourStop.query.filter_by(id=stop_id, tour_id=id).first_or_404()

    # Récupérer les données du formulaire
    role_name = request.form.get('role_name', '').strip()
    slot_category = request.form.get('slot_category', '').strip()
    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')
    task_description = request.form.get('task_description', '').strip()

    if not all([role_name, slot_category, start_time_str, end_time_str, task_description]):
        flash('Tous les champs sont requis.', 'error')
        category = request.form.get('category', 'tous')
        return redirect(url_for('tours.staff_planning', id=id, stop_id=stop_id, category=category))

    try:
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
    except ValueError:
        flash('Format d\'heure invalide.', 'error')
        category = request.form.get('category', 'tous')
        return redirect(url_for('tours.staff_planning', id=id, stop_id=stop_id, category=category))

    # Créer le slot
    slot = PlanningSlot(
        tour_stop_id=stop_id,
        role_name=role_name,
        category=slot_category,
        start_time=start_time,
        end_time=end_time,
        task_description=task_description,
        created_by_id=current_user.id
    )
    db.session.add(slot)
    db.session.commit()

    flash('Créneau ajouté avec succès.', 'success')
    category = request.form.get('category', 'tous')
    return redirect(url_for('tours.staff_planning', id=id, stop_id=stop_id, category=category))


@tours_bp.route('/<int:id>/stops/<int:stop_id>/planning/edit-slot/<int:slot_id>', methods=['POST'])
@login_required
@tour_edit_required
def edit_planning_slot(id, stop_id, slot_id, tour=None):
    """Modifier un créneau horaire."""
    from app.models.planning_slot import PlanningSlot
    from datetime import datetime

    slot = PlanningSlot.query.filter_by(id=slot_id, tour_stop_id=stop_id).first_or_404()

    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')
    task_description = request.form.get('task_description', '').strip()

    if start_time_str:
        try:
            slot.start_time = datetime.strptime(start_time_str, '%H:%M').time()
        except ValueError:
            pass

    if end_time_str:
        try:
            slot.end_time = datetime.strptime(end_time_str, '%H:%M').time()
        except ValueError:
            pass

    if task_description:
        slot.task_description = task_description

    db.session.commit()

    flash('Créneau modifié avec succès.', 'success')
    category = request.form.get('category', 'tous')
    return redirect(url_for('tours.staff_planning', id=id, stop_id=stop_id, category=category))


@tours_bp.route('/<int:id>/stops/<int:stop_id>/planning/delete-slot/<int:slot_id>', methods=['POST'])
@login_required
@tour_edit_required
def delete_planning_slot(id, stop_id, slot_id, tour=None):
    """Supprimer un créneau horaire."""
    from app.models.planning_slot import PlanningSlot

    slot = PlanningSlot.query.filter_by(id=slot_id, tour_stop_id=stop_id).first_or_404()
    db.session.delete(slot)
    db.session.commit()

    flash('Créneau supprimé.', 'success')
    category = request.form.get('category', 'tous')
    return redirect(url_for('tours.staff_planning', id=id, stop_id=stop_id, category=category))


@tours_bp.route('/<int:id>/stops/<int:stop_id>/planning/slots.json')
@login_required
@tour_access_required
def planning_slots_json(id, stop_id, tour=None):
    """API JSON pour les créneaux du planning."""
    from app.models.planning_slot import PlanningSlot

    slots = PlanningSlot.query.filter_by(tour_stop_id=stop_id).all()
    return jsonify([slot.to_dict() for slot in slots])


# ==================== PLANNING SLOTS JSON API (for Gantt view) ====================

@tours_bp.route('/<int:id>/stops/<int:stop_id>/planning/slot/<int:slot_id>/json')
@login_required
@tour_access_required
def get_planning_slot_json(id, stop_id, slot_id, tour=None):
    """Récupérer un créneau en JSON pour l'édition."""
    from app.models.planning_slot import PlanningSlot

    slot = PlanningSlot.query.filter_by(id=slot_id, tour_stop_id=stop_id).first_or_404()
    return jsonify(slot.to_dict())


@tours_bp.route('/<int:id>/stops/<int:stop_id>/planning/slot/add', methods=['POST'])
@login_required
@tour_edit_required
def add_slot_json(id, stop_id, tour=None):
    """Ajouter un créneau (API JSON)."""
    from app.models.planning_slot import PlanningSlot
    from datetime import datetime

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400

    member_id = data.get('member_id')
    category = data.get('category')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    task_description = data.get('task_description', '').strip()

    if not all([member_id, category, start_time_str, end_time_str, task_description]):
        return jsonify({'success': False, 'error': 'Tous les champs sont requis'}), 400

    try:
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
    except ValueError:
        return jsonify({'success': False, 'error': 'Format d\'heure invalide'}), 400

    # Récupérer le nom de l'utilisateur pour role_name
    user = User.query.get(member_id)
    role_name = user.full_name if user else 'Membre'

    slot = PlanningSlot(
        tour_stop_id=stop_id,
        role_name=role_name,
        category=category,
        start_time=start_time,
        end_time=end_time,
        task_description=task_description,
        user_id=int(member_id),
        created_by_id=current_user.id
    )
    db.session.add(slot)
    db.session.commit()

    return jsonify({'success': True, 'slot': slot.to_dict()})


@tours_bp.route('/<int:id>/stops/<int:stop_id>/planning/slot/<int:slot_id>', methods=['PUT'])
@login_required
@tour_edit_required
def update_slot_json(id, stop_id, slot_id, tour=None):
    """Modifier un créneau (API JSON)."""
    from app.models.planning_slot import PlanningSlot
    from datetime import datetime

    slot = PlanningSlot.query.filter_by(id=slot_id, tour_stop_id=stop_id).first_or_404()

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400

    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    task_description = data.get('task_description', '').strip()

    if start_time_str:
        try:
            slot.start_time = datetime.strptime(start_time_str, '%H:%M').time()
        except ValueError:
            return jsonify({'success': False, 'error': 'Format heure début invalide'}), 400

    if end_time_str:
        try:
            slot.end_time = datetime.strptime(end_time_str, '%H:%M').time()
        except ValueError:
            return jsonify({'success': False, 'error': 'Format heure fin invalide'}), 400

    if task_description:
        slot.task_description = task_description

    db.session.commit()

    return jsonify({'success': True, 'slot': slot.to_dict()})


@tours_bp.route('/<int:id>/stops/<int:stop_id>/planning/slot/<int:slot_id>', methods=['DELETE'])
@login_required
@tour_edit_required
def delete_slot_json(id, stop_id, slot_id, tour=None):
    """Supprimer un créneau (API JSON)."""
    from app.models.planning_slot import PlanningSlot

    slot = PlanningSlot.query.filter_by(id=slot_id, tour_stop_id=stop_id).first_or_404()
    db.session.delete(slot)
    db.session.commit()

    return jsonify({'success': True})


