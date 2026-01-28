"""
Venue management routes.
"""
import re
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.blueprints.venues import venues_bp
from app.blueprints.venues.forms import VenueForm, VenueContactForm
from app.models.venue import Venue, VenueContact
from app.extensions import db
from sqlalchemy import func
from app.decorators import requires_manager
from app.utils.audit import log_create, log_update, log_delete


def process_contacts_from_form(venue, form_data):
    """Process inline contacts from venue form.

    Handles creating new contacts, updating existing ones, and deleting removed ones.

    Args:
        venue: The Venue object to associate contacts with
        form_data: MultiDict from request.form
    """
    # Collect existing contact IDs
    existing_contact_ids = {contact.id for contact in venue.contacts}
    submitted_contact_ids = set()

    # Parse contacts from form data
    # Format: contacts[0][name], contacts[0][email], etc.
    contact_data = {}
    for key, value in form_data.items():
        if key.startswith('contacts['):
            match = re.match(r'contacts\[(\d+)\]\[(\w+)\]', key)
            if match:
                idx, field = match.groups()
                idx = int(idx)
                if idx not in contact_data:
                    contact_data[idx] = {}
                contact_data[idx][field] = value

    # Process each contact
    for idx, data in contact_data.items():
        name = data.get('name', '').strip()
        if not name:
            continue  # Skip empty rows

        contact_id = data.get('id')
        if contact_id:
            contact_id = int(contact_id)
            submitted_contact_ids.add(contact_id)
            # Update existing contact
            contact = VenueContact.query.get(contact_id)
            if contact and contact.venue_id == venue.id:
                contact.name = name
                contact.role = data.get('role') or None
                contact.email = data.get('email') or None
                contact.phone = data.get('phone') or None
        else:
            # Create new contact
            contact = VenueContact(
                venue_id=venue.id,
                name=name,
                role=data.get('role') or None,
                email=data.get('email') or None,
                phone=data.get('phone') or None
            )
            db.session.add(contact)
            log_create('VenueContact', None, {'venue_id': venue.id, 'name': name})

    # Delete removed contacts
    for contact_id in existing_contact_ids - submitted_contact_ids:
        contact = VenueContact.query.get(contact_id)
        if contact:
            log_delete('VenueContact', contact.id, {'name': contact.name})
            db.session.delete(contact)


@venues_bp.route('/')
@login_required
def index():
    """List all venues with optional filters."""
    # Filter parameters
    city_filter = request.args.get('city')
    type_filter = request.args.get('venue_type')  # BUG FIX: était 'type', template envoie 'venue_type'
    search = request.args.get('q', '').strip()

    query = Venue.query

    if city_filter:
        query = query.filter(Venue.city.ilike(f'%{city_filter}%'))

    if type_filter:
        # BUG FIX: Comparaison case-insensitive pour éviter mismatch "arena" vs "Arena"
        query = query.filter(func.lower(Venue.venue_type) == type_filter.lower())

    if search:
        query = query.filter(
            Venue.name.ilike(f'%{search}%') |
            Venue.city.ilike(f'%{search}%')
        )

    venues = query.order_by(Venue.name).all()

    # Get unique cities for filter dropdown
    # Note: On utilise title() en Python car initcap() n'existe pas dans SQLite
    raw_cities = db.session.query(Venue.city).distinct().order_by(Venue.city).all()
    cities = sorted(set(c[0].title() for c in raw_cities if c[0]))

    return render_template(
        'venues/list.html',
        venues=venues,
        cities=cities,
        city_filter=city_filter,
        type_filter=type_filter,
        search=search
    )


@venues_bp.route('/create', methods=['GET', 'POST'])
@login_required
@requires_manager
def create():
    """Create a new venue."""
    form = VenueForm()

    if form.validate_on_submit():
        venue = Venue(
            name=form.name.data,
            address=form.address.data,
            city=form.city.data.title() if form.city.data else None,  # BUG FIX: Normalise casse ville
            state=form.state_province.data,
            country=form.country.data,
            postal_code=form.postal_code.data,
            capacity=form.capacity.data,
            venue_type=form.venue_type.data or None,
            website=form.website.data,
            phone=form.phone.data,
            email=form.email.data,
            notes=form.notes.data
        )

        # Utiliser les coordonnees de l'autocompletion si fournies
        if form.latitude.data and form.longitude.data:
            try:
                venue.latitude = float(form.latitude.data)
                venue.longitude = float(form.longitude.data)
            except (ValueError, TypeError):
                pass

        db.session.add(venue)
        db.session.commit()

        # Process inline contacts from form
        process_contacts_from_form(venue, request.form)
        db.session.commit()

        # Geocodage automatique seulement si pas de coordonnees
        if not venue.has_coordinates:
            venue.geocode()
            db.session.commit()

        log_create('Venue', venue.id, {'name': venue.name, 'city': venue.city})

        flash(f'La salle "{venue.name}" a été créée.', 'success')
        return redirect(url_for('venues.detail', id=venue.id))

    return render_template('venues/form.html', form=form, title='Créer une salle')


@venues_bp.route('/<int:id>')
@login_required
def detail(id):
    """View venue details."""
    venue = Venue.query.get_or_404(id)
    return render_template('venues/detail.html', venue=venue)


@venues_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@requires_manager
def edit(id):
    """Edit a venue."""
    venue = Venue.query.get_or_404(id)
    form = VenueForm(obj=venue)

    if form.validate_on_submit():
        form.populate_obj(venue)
        # BUG FIX: Normalise casse ville
        if venue.city:
            venue.city = venue.city.title()
        # Handle empty strings for optional fields
        if not venue.venue_type:
            venue.venue_type = None

        # Utiliser les coordonnees de l'autocompletion si fournies
        if form.latitude.data and form.longitude.data:
            try:
                venue.latitude = float(form.latitude.data)
                venue.longitude = float(form.longitude.data)
            except (ValueError, TypeError):
                pass

        # Process inline contacts from form
        process_contacts_from_form(venue, request.form)
        db.session.commit()

        # Geocodage automatique seulement si pas de coordonnees
        if not venue.has_coordinates:
            venue.geocode()
            db.session.commit()

        log_update('Venue', venue.id, {'name': venue.name})

        flash('La salle a été mise à jour.', 'success')
        return redirect(url_for('venues.detail', id=id))

    return render_template('venues/form.html', form=form, venue=venue, title='Modifier la salle')


@venues_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@requires_manager
def delete(id):
    """Delete a venue."""
    venue = Venue.query.get_or_404(id)

    # Check if venue has any tour stops
    if venue.tour_stops:
        flash('Impossible de supprimer cette salle car elle a des concerts associés.', 'error')
        return redirect(url_for('venues.detail', id=id))

    venue_name = venue.name
    log_delete('Venue', venue.id, {'name': venue_name})

    db.session.delete(venue)
    db.session.commit()

    flash(f'La salle "{venue_name}" a été supprimée.', 'success')
    return redirect(url_for('venues.index'))


# Venue Contacts
@venues_bp.route('/<int:id>/contacts/add', methods=['GET', 'POST'])
@login_required
@requires_manager
def add_contact(id):
    """Add a contact to a venue."""
    venue = Venue.query.get_or_404(id)
    form = VenueContactForm()

    if form.validate_on_submit():
        contact = VenueContact(
            venue_id=venue.id,
            name=form.name.data,
            role=form.role.data or None,
            email=form.email.data,
            phone=form.phone.data,
            notes=form.notes.data
        )
        db.session.add(contact)
        db.session.commit()

        log_create('VenueContact', contact.id, {'venue_id': venue.id, 'name': contact.name})

        flash(f'Le contact "{contact.name}" a été ajouté.', 'success')
        return redirect(url_for('venues.detail', id=id))

    return render_template('venues/contact_form.html', form=form, venue=venue, title='Ajouter un contact')


@venues_bp.route('/<int:id>/contacts/<int:contact_id>/edit', methods=['GET', 'POST'])
@login_required
@requires_manager
def edit_contact(id, contact_id):
    """Edit a venue contact."""
    venue = Venue.query.get_or_404(id)
    contact = VenueContact.query.filter_by(id=contact_id, venue_id=id).first_or_404()

    form = VenueContactForm(obj=contact)

    if form.validate_on_submit():
        form.populate_obj(contact)
        if not contact.role:
            contact.role = None
        db.session.commit()

        flash('Le contact a été mis à jour.', 'success')
        return redirect(url_for('venues.detail', id=id))

    return render_template('venues/contact_form.html', form=form, venue=venue, contact=contact, title='Modifier le contact')


@venues_bp.route('/<int:id>/contacts/<int:contact_id>/delete', methods=['POST'])
@login_required
@requires_manager
def delete_contact(id, contact_id):
    """Delete a venue contact."""
    contact = VenueContact.query.filter_by(id=contact_id, venue_id=id).first_or_404()

    contact_name = contact.name
    log_delete('VenueContact', contact.id, {'name': contact_name})

    db.session.delete(contact)
    db.session.commit()

    flash(f'Le contact "{contact_name}" a été supprimé.', 'success')
    return redirect(url_for('venues.detail', id=id))
