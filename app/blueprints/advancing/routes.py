"""
Advancing routes - Event preparation workflow.
16 web routes + integration with API blueprint.
"""
from functools import wraps

from flask import (
    render_template, redirect, url_for, flash, request,
    jsonify, abort, current_app
)
from flask_login import login_required, current_user

from app.blueprints.advancing import advancing_bp
from app.blueprints.advancing.forms import (
    RiderRequirementForm, AdvancingContactForm, ProductionSpecsForm,
    AdvancingTemplateForm, AdvancingStatusForm, ChecklistItemNoteForm
)
from app.extensions import db
from app.models.advancing import (
    AdvancingChecklistItem, AdvancingTemplate, RiderRequirement,
    AdvancingContact, ChecklistCategory, RiderCategory,
    DEFAULT_CHECKLIST_ITEMS
)
from app.models.tour_stop import TourStop
from app.models.tour import Tour
from app.services.advancing_service import AdvancingService


def manager_required(f):
    """Decorator to require manager role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_manager_or_above():
            flash('Accès réservé aux managers.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# TOUR ADVANCING DASHBOARD
# ============================================================================

@advancing_bp.route('/tour/<int:tour_id>')
@login_required
def tour_dashboard(tour_id):
    """Tour advancing overview - progress for all stops."""
    tour = Tour.query.get_or_404(tour_id)
    summary = AdvancingService.get_advancing_summary(tour_id)
    return render_template(
        'advancing/tour_dashboard.html',
        tour=tour,
        summary=summary
    )


# ============================================================================
# STOP ADVANCING DETAIL
# ============================================================================

@advancing_bp.route('/stop/<int:stop_id>')
@login_required
def stop_detail(stop_id):
    """Advancing detail for a single tour stop."""
    stop = TourStop.query.get_or_404(stop_id)
    data = AdvancingService.get_stop_advancing_data(stop_id)
    status_form = AdvancingStatusForm(
        status=stop.advancing_status,
        advancing_deadline=stop.advancing_deadline
    )
    note_form = ChecklistItemNoteForm()
    return render_template(
        'advancing/stop_detail.html',
        stop=stop,
        data=data,
        status_form=status_form,
        note_form=note_form,
        ChecklistCategory=ChecklistCategory
    )


@advancing_bp.route('/stop/<int:stop_id>/init', methods=['POST'])
@login_required
@manager_required
def init_checklist(stop_id):
    """Initialize advancing checklist from template."""
    template_id = request.form.get('template_id', type=int)
    try:
        items = AdvancingService.init_checklist(stop_id, template_id)
        flash(f'{len(items)} éléments ajoutés à la checklist.', 'success')
    except ValueError as e:
        flash(str(e), 'warning')
    return redirect(url_for('advancing.stop_detail', stop_id=stop_id))


@advancing_bp.route('/stop/<int:stop_id>/status', methods=['POST'])
@login_required
@manager_required
def update_status(stop_id):
    """Update advancing status and deadline."""
    form = AdvancingStatusForm()
    if form.validate_on_submit():
        stop = TourStop.query.get_or_404(stop_id)
        try:
            AdvancingService.update_advancing_status(stop_id, form.status.data)
            stop.advancing_deadline = form.advancing_deadline.data
            db.session.commit()
            flash('Statut mis à jour.', 'success')
        except ValueError as e:
            flash(str(e), 'danger')
    return redirect(url_for('advancing.stop_detail', stop_id=stop_id))


@advancing_bp.route('/stop/<int:stop_id>/reset', methods=['POST'])
@login_required
@manager_required
def reset_checklist(stop_id):
    """Reset advancing checklist (delete all items)."""
    count = AdvancingService.delete_checklist(stop_id)
    flash(f'Checklist réinitialisée ({count} éléments supprimés).', 'info')
    return redirect(url_for('advancing.stop_detail', stop_id=stop_id))


# ============================================================================
# CHECKLIST ITEM ACTIONS
# ============================================================================

@advancing_bp.route('/item/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_item(item_id):
    """Toggle a checklist item completion."""
    item = AdvancingService.toggle_item(item_id, current_user.id)
    # If AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'is_completed': item.is_completed,
            'completion_pct': item.tour_stop.advancing_completion
        })
    return redirect(url_for('advancing.stop_detail', stop_id=item.tour_stop_id))


@advancing_bp.route('/item/<int:item_id>/note', methods=['POST'])
@login_required
def update_item_note(item_id):
    """Update notes on a checklist item."""
    form = ChecklistItemNoteForm()
    if form.validate_on_submit():
        AdvancingService.update_item_notes(item_id, form.notes.data)
        flash('Note mise à jour.', 'success')
    item = AdvancingChecklistItem.query.get_or_404(item_id)
    return redirect(url_for('advancing.stop_detail', stop_id=item.tour_stop_id))


# ============================================================================
# RIDER REQUIREMENTS
# ============================================================================

@advancing_bp.route('/stop/<int:stop_id>/rider')
@login_required
def rider_detail(stop_id):
    """Rider requirements view."""
    stop = TourStop.query.get_or_404(stop_id)
    riders = RiderRequirement.query.filter_by(
        tour_stop_id=stop_id
    ).order_by(RiderRequirement.category, RiderRequirement.sort_order).all()

    # Group by category
    riders_by_category = {}
    for rider in riders:
        cat = rider.category.value
        if cat not in riders_by_category:
            riders_by_category[cat] = []
        riders_by_category[cat].append(rider)

    form = RiderRequirementForm()
    return render_template(
        'advancing/rider.html',
        stop=stop,
        riders_by_category=riders_by_category,
        form=form,
        RiderCategory=RiderCategory
    )


@advancing_bp.route('/stop/<int:stop_id>/rider', methods=['POST'])
@login_required
@manager_required
def add_rider(stop_id):
    """Add a rider requirement."""
    form = RiderRequirementForm()
    if form.validate_on_submit():
        AdvancingService.add_rider_requirement(
            tour_stop_id=stop_id,
            category=form.category.data,
            requirement=form.requirement.data,
            quantity=form.quantity.data,
            is_mandatory=form.is_mandatory.data,
            notes=form.notes.data
        )
        flash('Exigence rider ajoutée.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{error}', 'danger')
    return redirect(url_for('advancing.rider_detail', stop_id=stop_id))


@advancing_bp.route('/rider/<int:rider_id>/confirm', methods=['POST'])
@login_required
def confirm_rider(rider_id):
    """Confirm a rider requirement."""
    venue_response = request.form.get('venue_response', '')
    AdvancingService.confirm_rider_item(rider_id, venue_response)
    flash('Exigence confirmée par la salle.', 'success')
    rider = RiderRequirement.query.get_or_404(rider_id)
    return redirect(url_for('advancing.rider_detail', stop_id=rider.tour_stop_id))


@advancing_bp.route('/rider/<int:rider_id>/delete', methods=['POST'])
@login_required
@manager_required
def delete_rider(rider_id):
    """Delete a rider requirement."""
    rider = RiderRequirement.query.get_or_404(rider_id)
    stop_id = rider.tour_stop_id
    db.session.delete(rider)
    db.session.commit()
    flash('Exigence rider supprimée.', 'info')
    return redirect(url_for('advancing.rider_detail', stop_id=stop_id))


# ============================================================================
# CONTACTS
# ============================================================================

@advancing_bp.route('/stop/<int:stop_id>/contacts')
@login_required
def contacts(stop_id):
    """Venue contacts for advancing."""
    stop = TourStop.query.get_or_404(stop_id)
    contact_list = AdvancingContact.query.filter_by(tour_stop_id=stop_id).all()
    form = AdvancingContactForm()
    return render_template(
        'advancing/contacts.html',
        stop=stop,
        contacts=contact_list,
        form=form
    )


@advancing_bp.route('/stop/<int:stop_id>/contacts', methods=['POST'])
@login_required
@manager_required
def add_contact(stop_id):
    """Add a venue contact."""
    form = AdvancingContactForm()
    if form.validate_on_submit():
        AdvancingService.add_contact(
            tour_stop_id=stop_id,
            name=form.name.data,
            role=form.role.data,
            email=form.email.data,
            phone=form.phone.data,
            is_primary=form.is_primary.data,
            notes=form.notes.data
        )
        flash('Contact ajouté.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{error}', 'danger')
    return redirect(url_for('advancing.contacts', stop_id=stop_id))


@advancing_bp.route('/contact/<int:contact_id>/delete', methods=['POST'])
@login_required
@manager_required
def delete_contact(contact_id):
    """Delete a venue contact."""
    contact = AdvancingContact.query.get_or_404(contact_id)
    stop_id = contact.tour_stop_id
    db.session.delete(contact)
    db.session.commit()
    flash('Contact supprimé.', 'info')
    return redirect(url_for('advancing.contacts', stop_id=stop_id))


# ============================================================================
# TEMPLATES
# ============================================================================

@advancing_bp.route('/templates')
@login_required
@manager_required
def templates_list():
    """List advancing templates."""
    templates = AdvancingTemplate.query.order_by(
        AdvancingTemplate.is_default.desc(),
        AdvancingTemplate.name
    ).all()
    return render_template(
        'advancing/templates_list.html',
        templates=templates
    )


@advancing_bp.route('/templates/create', methods=['GET', 'POST'])
@login_required
@manager_required
def create_template():
    """Create a new advancing template."""
    form = AdvancingTemplateForm()
    if form.validate_on_submit():
        # Build items from form data (checklist items submitted as JSON or form fields)
        items_json = request.form.get('items_json', '[]')
        import json
        try:
            items = json.loads(items_json)
        except (json.JSONDecodeError, TypeError):
            items = DEFAULT_CHECKLIST_ITEMS  # Fallback to default

        template = AdvancingService.create_template(
            name=form.name.data,
            items=items,
            description=form.description.data,
            created_by_id=current_user.id
        )
        flash(f'Template "{template.name}" créé.', 'success')
        return redirect(url_for('advancing.templates_list'))
    return render_template(
        'advancing/template_form.html',
        form=form,
        default_items=DEFAULT_CHECKLIST_ITEMS
    )


@advancing_bp.route('/templates/<int:template_id>/delete', methods=['POST'])
@login_required
@manager_required
def delete_template(template_id):
    """Delete an advancing template."""
    template = AdvancingTemplate.query.get_or_404(template_id)
    if template.is_default:
        flash('Impossible de supprimer le template par défaut.', 'danger')
        return redirect(url_for('advancing.templates_list'))
    db.session.delete(template)
    db.session.commit()
    flash('Template supprimé.', 'info')
    return redirect(url_for('advancing.templates_list'))


# ============================================================================
# PRODUCTION SPECS
# ============================================================================

@advancing_bp.route('/stop/<int:stop_id>/production')
@login_required
def production_specs(stop_id):
    """Production specs view (stage dimensions, power, rigging)."""
    stop = TourStop.query.get_or_404(stop_id)
    form = ProductionSpecsForm(obj=stop)
    return render_template(
        'advancing/production_specs.html',
        stop=stop,
        form=form
    )


@advancing_bp.route('/stop/<int:stop_id>/production', methods=['POST'])
@login_required
@manager_required
def update_production_specs(stop_id):
    """Save production specs."""
    form = ProductionSpecsForm()
    if form.validate_on_submit():
        AdvancingService.update_production_specs(
            tour_stop_id=stop_id,
            stage_width=form.stage_width.data,
            stage_depth=form.stage_depth.data,
            stage_height=form.stage_height.data,
            power_available=form.power_available.data,
            rigging_points=form.rigging_points.data
        )
        flash('Fiche technique mise à jour.', 'success')
    return redirect(url_for('advancing.production_specs', stop_id=stop_id))


# ============================================================================
# PDF EXPORT
# ============================================================================

@advancing_bp.route('/stop/<int:stop_id>/export/pdf')
@login_required
def export_pdf(stop_id):
    """Export advancing data as PDF."""
    stop = TourStop.query.get_or_404(stop_id)
    data = AdvancingService.get_stop_advancing_data(stop_id)

    try:
        from app.utils.pdf_generator import PDF_AVAILABLE
        if not PDF_AVAILABLE:
            flash('Export PDF non disponible (ReportLab non installé).', 'warning')
            return redirect(url_for('advancing.stop_detail', stop_id=stop_id))

        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from io import BytesIO
        from flask import make_response

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16)
        elements.append(Paragraph(f"Advancing - {stop.venue_name}", title_style))
        elements.append(Paragraph(f"{stop.date.strftime('%d/%m/%Y')} - {stop.venue_city}", styles['Normal']))
        elements.append(Spacer(1, 10*mm))

        # Status
        elements.append(Paragraph(f"Statut: {data['advancing_status_label']} ({data['completion_pct']}%)", styles['Normal']))
        elements.append(Spacer(1, 5*mm))

        # Checklist
        elements.append(Paragraph("Checklist", styles['Heading2']))
        for category, items in data['checklist_by_category'].items():
            category_labels = {
                'accueil': 'Accueil', 'technique': 'Technique', 'catering': 'Catering',
                'hebergement': 'Hébergement', 'logistique': 'Logistique',
                'securite': 'Sécurité', 'admin': 'Administration'
            }
            elements.append(Paragraph(category_labels.get(category, category), styles['Heading3']))
            for item in items:
                check = '✓' if item['is_completed'] else '○'
                text = f"{check} {item['label']}"
                if item.get('notes'):
                    text += f" — {item['notes']}"
                elements.append(Paragraph(text, styles['Normal']))
            elements.append(Spacer(1, 3*mm))

        # Rider
        if data['riders_by_category']:
            elements.append(Paragraph("Rider technique", styles['Heading2']))
            for category, riders in data['riders_by_category'].items():
                rider_labels = {
                    'son': 'Son', 'lumiere': 'Lumière', 'scene': 'Scène',
                    'backline': 'Backline', 'catering': 'Catering', 'loges': 'Loges'
                }
                elements.append(Paragraph(rider_labels.get(category, category), styles['Heading3']))
                for rider in riders:
                    mandatory = '(obligatoire)' if rider['is_mandatory'] else '(optionnel)'
                    confirmed = '✓' if rider['is_confirmed'] else '?'
                    text = f"[{confirmed}] {rider['requirement']} x{rider['quantity']} {mandatory}"
                    elements.append(Paragraph(text, styles['Normal']))
            elements.append(Spacer(1, 3*mm))

        # Production specs
        specs = data['production_specs']
        if any(v for v in specs.values() if v is not None):
            elements.append(Paragraph("Fiche technique", styles['Heading2']))
            if specs['stage_width'] or specs['stage_depth'] or specs['stage_height']:
                dims = []
                if specs['stage_width']:
                    dims.append(f"L={specs['stage_width']}m")
                if specs['stage_depth']:
                    dims.append(f"P={specs['stage_depth']}m")
                if specs['stage_height']:
                    dims.append(f"H={specs['stage_height']}m")
                elements.append(Paragraph(f"Scène: {' x '.join(dims)}", styles['Normal']))
            if specs['power_available']:
                elements.append(Paragraph(f"Puissance: {specs['power_available']}", styles['Normal']))
            if specs['rigging_points']:
                elements.append(Paragraph(f"Points d'accroche: {specs['rigging_points']}", styles['Normal']))

        # Contacts
        if data['contacts']:
            elements.append(Spacer(1, 5*mm))
            elements.append(Paragraph("Contacts", styles['Heading2']))
            for contact in data['contacts']:
                primary = ' (principal)' if contact['is_primary'] else ''
                text = f"{contact['name']}{primary}"
                if contact['role']:
                    text += f" — {contact['role']}"
                if contact['email']:
                    text += f" — {contact['email']}"
                if contact['phone']:
                    text += f" — {contact['phone']}"
                elements.append(Paragraph(text, styles['Normal']))

        doc.build(elements)

        response = make_response(buffer.getvalue())
        filename = f"advancing_{stop.date.strftime('%Y%m%d')}_{stop.venue_name.replace(' ', '_')}.pdf"
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        current_app.logger.error(f'PDF export error: {e}')
        flash('Erreur lors de l\'export PDF.', 'danger')
        return redirect(url_for('advancing.stop_detail', stop_id=stop_id))


# ============================================================================
# EMAIL SENDING
# ============================================================================

@advancing_bp.route('/stop/<int:stop_id>/send', methods=['POST'])
@login_required
@manager_required
def send_to_venue(stop_id):
    """Send advancing summary email to venue contact."""
    stop = TourStop.query.get_or_404(stop_id)
    recipient_email = request.form.get('recipient_email')

    if not recipient_email:
        # Try primary advancing contact
        primary_contact = AdvancingContact.query.filter_by(
            tour_stop_id=stop_id, is_primary=True
        ).first()
        if primary_contact and primary_contact.email:
            recipient_email = primary_contact.email
        elif stop.venue_contact_email:
            recipient_email = stop.venue_contact_email
        else:
            flash('Aucune adresse email de contact trouvée.', 'danger')
            return redirect(url_for('advancing.stop_detail', stop_id=stop_id))

    try:
        from flask_mail import Message
        from app.extensions import mail

        data = AdvancingService.get_stop_advancing_data(stop_id)
        band_name = stop.associated_band.name if stop.associated_band else 'GigRoute'

        msg = Message(
            subject=f"Advancing - {band_name} - {stop.date.strftime('%d/%m/%Y')} - {stop.venue_name}",
            recipients=[recipient_email],
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )

        msg.html = render_template(
            'advancing/email_advancing.html',
            stop=stop,
            data=data,
            band_name=band_name,
            sender_name=current_user.full_name
        )
        mail.send(msg)

        # Mark as waiting for venue
        if stop.advancing_status in ('in_progress', 'not_started'):
            stop.advancing_status = 'waiting_venue'
            db.session.commit()

        flash(f'Email envoyé à {recipient_email}.', 'success')
    except Exception as e:
        current_app.logger.error(f'Advancing email error: {e}')
        flash('Erreur lors de l\'envoi de l\'email. Veuillez réessayer.', 'danger')

    return redirect(url_for('advancing.stop_detail', stop_id=stop_id))
