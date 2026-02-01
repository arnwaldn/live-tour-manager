"""Routes for crew schedule management."""
from datetime import datetime, time
from functools import wraps

from flask import (
    render_template, redirect, url_for, flash, request,
    abort, jsonify, Response
)
from flask_login import login_required, current_user

from app.blueprints.crew import crew_bp
from app.blueprints.crew.forms import (
    CrewSlotForm, CrewAssignmentForm, ExternalContactForm
)
from app.extensions import db
from app.models.tour_stop import TourStop
from app.models.crew_schedule import (
    CrewScheduleSlot, CrewAssignment, ExternalContact, AssignmentStatus
)
from app.models.profession import Profession, ProfessionCategory
from app.models.user import User
from app.utils.notifications import create_notification
from app.models.notification import NotificationType, NotificationCategory


# =============================================================================
# Permission Helpers
# =============================================================================

def _can_view_crew_schedule(tour_stop, user):
    """Check if user can view crew schedule for this tour stop."""
    if user.is_admin():
        return True

    # Manager of the band
    band = tour_stop.tour.band if tour_stop.tour else None
    if band and band.is_manager(user):
        return True

    # User is assigned to this stop
    assignment = CrewAssignment.query.join(CrewScheduleSlot).filter(
        CrewScheduleSlot.tour_stop_id == tour_stop.id,
        CrewAssignment.user_id == user.id
    ).first()
    if assignment:
        return True

    return False


def _can_edit_crew_schedule(tour_stop, user):
    """Check if user can edit crew schedule for this tour stop."""
    if user.is_admin():
        return True

    # Manager of the band
    band = tour_stop.tour.band if tour_stop.tour else None
    if band and band.is_manager(user):
        return True

    return False


def crew_view_required(f):
    """Decorator to check crew schedule view permission."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        stop_id = kwargs.get('stop_id')
        if stop_id:
            tour_stop = TourStop.query.get_or_404(stop_id)
            if not _can_view_crew_schedule(tour_stop, current_user):
                abort(403)
        return f(*args, **kwargs)
    return decorated_function


def crew_edit_required(f):
    """Decorator to check crew schedule edit permission."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        stop_id = kwargs.get('stop_id')
        slot_id = kwargs.get('slot_id')

        if stop_id:
            tour_stop = TourStop.query.get_or_404(stop_id)
        elif slot_id:
            slot = CrewScheduleSlot.query.get_or_404(slot_id)
            tour_stop = slot.tour_stop
        else:
            abort(400)

        if not _can_edit_crew_schedule(tour_stop, current_user):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# Notification Helpers
# =============================================================================

def notify_crew_assignment(assignment, notification_type='assigned'):
    """Notify user about crew assignment."""
    if not assignment.user:
        return None  # External contact, no in-app notification

    slot = assignment.slot
    tour_stop = slot.tour_stop
    location = tour_stop.venue.name if tour_stop.venue else tour_stop.location_city or 'Lieu'

    titles = {
        'assigned': f"Assignation: {slot.task_name}",
        'updated': f"Planning modifié: {slot.task_name}",
        'cancelled': f"Assignation annulée: {slot.task_name}",
    }

    types = {
        'assigned': NotificationType.INFO,
        'updated': NotificationType.WARNING,
        'cancelled': NotificationType.ERROR,
    }

    message = f"{slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')} à {location} le {tour_stop.date.strftime('%d/%m/%Y')}"
    link = url_for('crew.schedule', stop_id=tour_stop.id)

    return create_notification(
        user_id=assignment.user_id,
        title=titles.get(notification_type, 'Planning équipe'),
        message=message,
        type=types.get(notification_type, NotificationType.INFO),
        category=NotificationCategory.SYSTEM,
        link=link
    )


def notify_crew_response_to_manager(assignment):
    """Notify manager when crew member responds."""
    slot = assignment.slot
    tour_stop = slot.tour_stop
    band = tour_stop.tour.band if tour_stop.tour else None

    if not band:
        return None

    person_name = assignment.person_name
    status_text = 'confirmé' if assignment.status == AssignmentStatus.CONFIRMED else 'refusé'

    title = f"Planning: {person_name} a {status_text}"
    message = f"{slot.task_name} - {tour_stop.date.strftime('%d/%m/%Y')}"
    link = url_for('crew.schedule', stop_id=tour_stop.id)

    return create_notification(
        user_id=band.manager_id,
        title=title,
        message=message,
        type=NotificationType.SUCCESS if status_text == 'confirmé' else NotificationType.WARNING,
        category=NotificationCategory.SYSTEM,
        link=link
    )


# =============================================================================
# Main Schedule View
# =============================================================================

@crew_bp.route('/stops/<int:stop_id>/crew')
@login_required
@crew_view_required
def schedule(stop_id):
    """Main crew schedule view."""
    tour_stop = TourStop.query.get_or_404(stop_id)
    can_edit = _can_edit_crew_schedule(tour_stop, current_user)

    # Get all slots grouped by category
    slots = CrewScheduleSlot.query.filter_by(tour_stop_id=stop_id).order_by(
        CrewScheduleSlot.profession_category,
        CrewScheduleSlot.start_time,
        CrewScheduleSlot.order
    ).all()

    # Group by category
    slots_by_category = {}
    for slot in slots:
        cat = slot.profession_category.value if slot.profession_category else 'general'
        if cat not in slots_by_category:
            slots_by_category[cat] = []
        slots_by_category[cat].append(slot)

    # Get users and external contacts for assignment form
    users = []
    external_contacts = []
    professions = []
    if can_edit:
        users = User.query.filter_by(is_active=True).order_by(User.first_name).all()
        external_contacts = ExternalContact.query.order_by(ExternalContact.last_name).all()
        professions = Profession.query.order_by(Profession.name_fr).all()

    return render_template(
        'crew/schedule.html',
        tour_stop=tour_stop,
        slots_by_category=slots_by_category,
        categories=ProfessionCategory,
        can_edit=can_edit,
        users=users,
        external_contacts=external_contacts,
        professions=professions,
        slot_form=CrewSlotForm(),
        assignment_form=CrewAssignmentForm(),
        contact_form=ExternalContactForm(),
        AssignmentStatus=AssignmentStatus
    )


@crew_bp.route('/stops/<int:stop_id>/crew/my')
@login_required
def my_schedule(stop_id):
    """Personal view showing only user's assignments."""
    tour_stop = TourStop.query.get_or_404(stop_id)

    # Get user's assignments
    assignments = CrewAssignment.query.join(CrewScheduleSlot).filter(
        CrewScheduleSlot.tour_stop_id == stop_id,
        CrewAssignment.user_id == current_user.id
    ).all()

    if not assignments:
        flash("Vous n'avez pas d'assignation pour cette date.", 'info')
        return redirect(url_for('tours.stop_detail', id=stop_id))

    return render_template(
        'crew/my_schedule.html',
        tour_stop=tour_stop,
        assignments=assignments,
        AssignmentStatus=AssignmentStatus
    )


# =============================================================================
# Slot CRUD
# =============================================================================

@crew_bp.route('/stops/<int:stop_id>/crew/slots', methods=['POST'])
@login_required
@crew_edit_required
def create_slot(stop_id):
    """Create a new crew schedule slot."""
    tour_stop = TourStop.query.get_or_404(stop_id)
    form = CrewSlotForm()

    if form.validate_on_submit():
        category = None
        if form.profession_category.data:
            category = ProfessionCategory(form.profession_category.data)

        slot = CrewScheduleSlot(
            tour_stop_id=stop_id,
            task_name=form.task_name.data,
            task_description=form.task_description.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            profession_category=category,
            color=form.color.data or '#3B82F6',
            created_by_id=current_user.id
        )
        db.session.add(slot)
        db.session.commit()

        flash(f"Créneau '{slot.task_name}' créé.", 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')

    return redirect(url_for('crew.schedule', stop_id=stop_id))


@crew_bp.route('/crew/slots/<int:slot_id>', methods=['POST'])
@login_required
@crew_edit_required
def update_slot(slot_id):
    """Update a crew schedule slot."""
    slot = CrewScheduleSlot.query.get_or_404(slot_id)
    form = CrewSlotForm()

    if form.validate_on_submit():
        slot.task_name = form.task_name.data
        slot.task_description = form.task_description.data
        slot.start_time = form.start_time.data
        slot.end_time = form.end_time.data
        if form.profession_category.data:
            slot.profession_category = ProfessionCategory(form.profession_category.data)
        else:
            slot.profession_category = None
        slot.color = form.color.data or '#3B82F6'
        slot.updated_at = datetime.utcnow()

        db.session.commit()
        flash(f"Créneau '{slot.task_name}' mis à jour.", 'success')

    return redirect(url_for('crew.schedule', stop_id=slot.tour_stop_id))


@crew_bp.route('/crew/slots/<int:slot_id>/delete', methods=['POST'])
@login_required
@crew_edit_required
def delete_slot(slot_id):
    """Delete a crew schedule slot."""
    slot = CrewScheduleSlot.query.get_or_404(slot_id)
    stop_id = slot.tour_stop_id
    task_name = slot.task_name

    # Notify assigned users
    for assignment in slot.assignments:
        notify_crew_assignment(assignment, 'cancelled')

    db.session.delete(slot)
    db.session.commit()

    flash(f"Créneau '{task_name}' supprimé.", 'success')
    return redirect(url_for('crew.schedule', stop_id=stop_id))


# =============================================================================
# Assignment CRUD
# =============================================================================

@crew_bp.route('/crew/slots/<int:slot_id>/assign', methods=['POST'])
@login_required
@crew_edit_required
def assign_person(slot_id):
    """Assign a person to a slot."""
    slot = CrewScheduleSlot.query.get_or_404(slot_id)

    assignment_type = request.form.get('assignment_type')
    user_id = request.form.get('user_id', type=int)
    external_contact_id = request.form.get('external_contact_id', type=int)
    profession_id = request.form.get('profession_id', type=int) or None
    call_time_str = request.form.get('call_time')
    notes = request.form.get('notes', '')

    call_time = None
    if call_time_str:
        try:
            call_time = datetime.strptime(call_time_str, '%H:%M').time()
        except ValueError:
            pass

    # Validate assignment
    if assignment_type == 'user' and user_id:
        # Check not already assigned
        existing = CrewAssignment.query.filter_by(
            slot_id=slot_id, user_id=user_id
        ).first()
        if existing:
            flash("Cet utilisateur est déjà assigné à ce créneau.", 'warning')
            return redirect(url_for('crew.schedule', stop_id=slot.tour_stop_id))

        assignment = CrewAssignment(
            slot_id=slot_id,
            user_id=user_id,
            profession_id=profession_id,
            call_time=call_time,
            notes=notes,
            assigned_by_id=current_user.id
        )
    elif assignment_type == 'external' and external_contact_id:
        # Check not already assigned
        existing = CrewAssignment.query.filter_by(
            slot_id=slot_id, external_contact_id=external_contact_id
        ).first()
        if existing:
            flash("Ce contact est déjà assigné à ce créneau.", 'warning')
            return redirect(url_for('crew.schedule', stop_id=slot.tour_stop_id))

        assignment = CrewAssignment(
            slot_id=slot_id,
            external_contact_id=external_contact_id,
            profession_id=profession_id,
            call_time=call_time,
            notes=notes,
            assigned_by_id=current_user.id
        )
    else:
        flash("Veuillez sélectionner une personne à assigner.", 'danger')
        return redirect(url_for('crew.schedule', stop_id=slot.tour_stop_id))

    db.session.add(assignment)
    db.session.commit()

    # Send notification
    notify_crew_assignment(assignment, 'assigned')

    flash(f"{assignment.person_name} assigné(e) à '{slot.task_name}'.", 'success')
    return redirect(url_for('crew.schedule', stop_id=slot.tour_stop_id))


@crew_bp.route('/crew/assignments/<int:id>/delete', methods=['POST'])
@login_required
def delete_assignment(id):
    """Remove an assignment."""
    assignment = CrewAssignment.query.get_or_404(id)
    slot = assignment.slot

    # Check permission
    if not _can_edit_crew_schedule(slot.tour_stop, current_user):
        abort(403)

    person_name = assignment.person_name

    # Notify before deletion
    notify_crew_assignment(assignment, 'cancelled')

    db.session.delete(assignment)
    db.session.commit()

    flash(f"{person_name} retiré(e) de '{slot.task_name}'.", 'success')
    return redirect(url_for('crew.schedule', stop_id=slot.tour_stop_id))


@crew_bp.route('/crew/assignments/<int:id>/confirm', methods=['POST'])
@login_required
def confirm_assignment(id):
    """Confirm an assignment (by the assigned person)."""
    assignment = CrewAssignment.query.get_or_404(id)

    # Check if current user is the assigned person
    if assignment.user_id != current_user.id:
        abort(403)

    assignment.status = AssignmentStatus.CONFIRMED
    assignment.confirmed_at = datetime.utcnow()
    db.session.commit()

    # Notify manager
    notify_crew_response_to_manager(assignment)

    flash("Votre présence a été confirmée.", 'success')
    return redirect(url_for('crew.my_schedule', stop_id=assignment.slot.tour_stop_id))


@crew_bp.route('/crew/assignments/<int:id>/decline', methods=['POST'])
@login_required
def decline_assignment(id):
    """Decline an assignment (by the assigned person)."""
    assignment = CrewAssignment.query.get_or_404(id)

    # Check if current user is the assigned person
    if assignment.user_id != current_user.id:
        abort(403)

    assignment.status = AssignmentStatus.DECLINED
    assignment.confirmed_at = datetime.utcnow()
    db.session.commit()

    # Notify manager
    notify_crew_response_to_manager(assignment)

    flash("Vous avez décliné cette assignation.", 'info')
    return redirect(url_for('crew.my_schedule', stop_id=assignment.slot.tour_stop_id))


# =============================================================================
# External Contacts
# =============================================================================

@crew_bp.route('/crew/contacts')
@login_required
def list_contacts():
    """List all external contacts."""
    contacts = ExternalContact.query.order_by(ExternalContact.last_name).all()
    return render_template(
        'crew/contacts.html',
        contacts=contacts,
        form=ExternalContactForm()
    )


@crew_bp.route('/crew/contacts', methods=['POST'])
@login_required
def create_contact():
    """Create a new external contact."""
    form = ExternalContactForm()

    # Populate profession choices
    form.profession_id.choices = [(0, 'Aucune')] + [
        (p.id, p.name_fr) for p in Profession.query.order_by(Profession.name_fr).all()
    ]

    if form.validate_on_submit():
        contact = ExternalContact(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            profession_id=form.profession_id.data if form.profession_id.data else None,
            company=form.company.data,
            notes=form.notes.data,
            created_by_id=current_user.id
        )
        db.session.add(contact)
        db.session.commit()

        flash(f"Contact '{contact.full_name}' créé.", 'success')

        # Return to referrer if from schedule page
        if request.referrer and 'crew' in request.referrer:
            return redirect(request.referrer)
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')

    return redirect(url_for('crew.list_contacts'))


@crew_bp.route('/crew/contacts/<int:id>', methods=['POST'])
@login_required
def update_contact(id):
    """Update an external contact."""
    contact = ExternalContact.query.get_or_404(id)
    form = ExternalContactForm()

    if form.validate_on_submit():
        contact.first_name = form.first_name.data
        contact.last_name = form.last_name.data
        contact.email = form.email.data
        contact.phone = form.phone.data
        contact.profession_id = form.profession_id.data if form.profession_id.data else None
        contact.company = form.company.data
        contact.notes = form.notes.data

        db.session.commit()
        flash(f"Contact '{contact.full_name}' mis à jour.", 'success')

    return redirect(url_for('crew.list_contacts'))


@crew_bp.route('/crew/contacts/<int:id>/delete', methods=['POST'])
@login_required
def delete_contact(id):
    """Delete an external contact."""
    contact = ExternalContact.query.get_or_404(id)
    name = contact.full_name

    # Check if contact has assignments
    if contact.assignments:
        flash(f"Impossible de supprimer '{name}': des assignations existent.", 'danger')
        return redirect(url_for('crew.list_contacts'))

    db.session.delete(contact)
    db.session.commit()

    flash(f"Contact '{name}' supprimé.", 'success')
    return redirect(url_for('crew.list_contacts'))


# =============================================================================
# iCal Export
# =============================================================================

@crew_bp.route('/stops/<int:stop_id>/crew/export.ics')
@login_required
@crew_view_required
def export_ical(stop_id):
    """Export crew schedule as iCal."""
    from app.utils.ical import generate_crew_schedule_ical

    tour_stop = TourStop.query.get_or_404(stop_id)

    # If staff, export only their slots
    if not _can_edit_crew_schedule(tour_stop, current_user):
        ical_data = generate_crew_schedule_ical(tour_stop, user=current_user)
    else:
        ical_data = generate_crew_schedule_ical(tour_stop)

    return Response(
        ical_data,
        mimetype='text/calendar',
        headers={'Content-Disposition': f'attachment; filename=planning-{stop_id}.ics'}
    )


# =============================================================================
# API Endpoints (JSON)
# =============================================================================

@crew_bp.route('/api/stops/<int:stop_id>/crew')
@login_required
@crew_view_required
def api_schedule(stop_id):
    """Get crew schedule as JSON."""
    slots = CrewScheduleSlot.query.filter_by(tour_stop_id=stop_id).all()
    return jsonify([slot.to_dict() for slot in slots])


@crew_bp.route('/api/crew/contacts')
@login_required
def api_contacts():
    """Get external contacts as JSON."""
    contacts = ExternalContact.query.order_by(ExternalContact.last_name).all()
    return jsonify([{
        'id': c.id,
        'full_name': c.full_name,
        'email': c.email,
        'phone': c.phone,
        'company': c.company
    } for c in contacts])
