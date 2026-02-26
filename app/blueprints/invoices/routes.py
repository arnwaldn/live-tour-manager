"""
Invoice routes - Factur-X compliant financial module.
CRUD operations, validation workflow, payment recording, PDF generation.
"""
from datetime import date, datetime
from decimal import Decimal
from functools import wraps

from flask import (
    render_template, redirect, url_for, flash, request,
    jsonify, abort, current_app
)
from flask_login import login_required, current_user

from app.blueprints.invoices import invoices_bp
from app.blueprints.invoices.forms import (
    InvoiceForm, InvoiceFilterForm, InvoiceLineForm, InvoicePaymentForm
)
from app.extensions import db
from app.models.invoices import (
    Invoice, InvoiceLine, InvoicePayment,
    InvoiceStatus, InvoiceType, VATRate,
    DEFAULT_ISSUER_CONFIG, DEFAULT_LEGAL_MENTIONS
)
from app.models.tour import Tour
from app.models.tour_stop import TourStop
from app.models.user import User
from app.utils.audit import log_create, log_update, log_action


def manager_required(f):
    """Decorator to require manager role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_manager_or_above():
            flash('Acces reserve aux managers.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# INVOICE LISTING
# ============================================================================

@invoices_bp.route('/')
@login_required
@manager_required
def index():
    """List all invoices with filters."""
    form = InvoiceFilterForm(request.args)

    # Populate select fields
    form.tour_id.choices = [(0, 'Toutes les tournées')] + [
        (t.id, t.name) for t in Tour.query.order_by(Tour.start_date.desc()).all()
    ]

    # Build query
    query = Invoice.query

    # Apply filters
    if form.tour_id.data and form.tour_id.data != 0:
        query = query.filter_by(tour_id=form.tour_id.data)
    if form.status.data:
        query = query.filter_by(status=InvoiceStatus(form.status.data))
    if form.invoice_type.data:
        query = query.filter_by(type=InvoiceType(form.invoice_type.data))
    if form.date_from.data:
        query = query.filter(Invoice.issue_date >= form.date_from.data)
    if form.date_to.data:
        query = query.filter(Invoice.issue_date <= form.date_to.data)

    # Order by most recent
    query = query.order_by(Invoice.created_at.desc())

    # Calculate summary stats
    all_invoices = query.all()
    total_ht = sum(i.subtotal_ht or 0 for i in all_invoices)
    total_ttc = sum(i.total_ttc or 0 for i in all_invoices)
    total_due = sum(i.amount_due or 0 for i in all_invoices if i.status not in [
        InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.CREDITED
    ])
    total_paid = sum(i.amount_paid or 0 for i in all_invoices)
    overdue_count = sum(1 for i in all_invoices if i.is_overdue)

    return render_template('invoices/list.html',
                           form=form,
                           invoices=all_invoices,
                           total_ht=total_ht,
                           total_ttc=total_ttc,
                           total_due=total_due,
                           total_paid=total_paid,
                           overdue_count=overdue_count)


# ============================================================================
# CREATE INVOICE
# ============================================================================

@invoices_bp.route('/add', methods=['GET', 'POST'])
@login_required
@manager_required
def add():
    """Create a new invoice."""
    form = InvoiceForm()

    # Populate choices
    form.tour_id.choices = [(0, '-- Optionnel --')] + [
        (t.id, t.name) for t in Tour.query.order_by(Tour.start_date.desc()).all()
    ]
    form.tour_stop_id.choices = [(0, '-- Optionnel --')]
    form.recipient_id.choices = [(0, '-- Saisie manuelle --')] + [
        (u.id, u.full_name) for u in User.query.filter_by(is_active=True).order_by(User.last_name).all()
    ]

    if request.method == 'GET':
        # Pre-fill issuer info from defaults
        for field_name, value in DEFAULT_ISSUER_CONFIG.items():
            form_field = getattr(form, f'issuer_{field_name}', None)
            if form_field and value:
                form_field.data = value
        # Set default dates
        form.issue_date.data = date.today()
        form.due_date.data = date.today() + __import__('datetime').timedelta(days=30)

    if form.validate_on_submit():
        invoice = Invoice(
            type=InvoiceType(form.type.data),
            tour_id=form.tour_id.data if form.tour_id.data and form.tour_id.data != 0 else None,
            tour_stop_id=form.tour_stop_id.data if form.tour_stop_id.data and form.tour_stop_id.data != 0 else None,
            # Issuer
            issuer_name=form.issuer_name.data,
            issuer_legal_form=form.issuer_legal_form.data,
            issuer_address_line1=form.issuer_address_line1.data,
            issuer_address_line2=form.issuer_address_line2.data,
            issuer_city=form.issuer_city.data,
            issuer_postal_code=form.issuer_postal_code.data,
            issuer_country=form.issuer_country.data or 'FR',
            issuer_siren=form.issuer_siren.data,
            issuer_siret=form.issuer_siret.data,
            issuer_vat=form.issuer_vat.data,
            issuer_rcs=form.issuer_rcs.data,
            issuer_capital=form.issuer_capital.data,
            issuer_phone=form.issuer_phone.data,
            issuer_email=form.issuer_email.data,
            issuer_iban=form.issuer_iban.data,
            issuer_bic=form.issuer_bic.data,
            # Recipient
            recipient_id=form.recipient_id.data if form.recipient_id.data and form.recipient_id.data != 0 else None,
            recipient_name=form.recipient_name.data,
            recipient_legal_form=form.recipient_legal_form.data,
            recipient_address_line1=form.recipient_address_line1.data,
            recipient_address_line2=form.recipient_address_line2.data,
            recipient_city=form.recipient_city.data,
            recipient_postal_code=form.recipient_postal_code.data,
            recipient_country=form.recipient_country.data or 'FR',
            recipient_siren=form.recipient_siren.data,
            recipient_siret=form.recipient_siret.data,
            recipient_vat=form.recipient_vat.data,
            recipient_email=form.recipient_email.data,
            recipient_phone=form.recipient_phone.data,
            # Dates
            issue_date=form.issue_date.data,
            due_date=form.due_date.data,
            delivery_date=form.delivery_date.data,
            # Payment terms
            payment_terms=form.payment_terms.data,
            payment_terms_days=form.payment_terms_days.data,
            payment_method_accepted=form.payment_method_accepted.data,
            # Amounts (will be recalculated from lines)
            discount_amount=form.discount_amount.data or Decimal('0'),
            # Legal mentions
            vat_mention=form.vat_mention.data,
            reverse_charge=form.reverse_charge.data,
            early_payment_discount=form.early_payment_discount.data,
            no_discount_mention=form.no_discount_mention.data,
            special_mentions=form.special_mentions.data,
            # Notes
            public_notes=form.public_notes.data,
            internal_notes=form.internal_notes.data,
            # Audit
            created_by_id=current_user.id,
            # Temporary number for draft
            number=f'BROUILLON-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}',
            status=InvoiceStatus.DRAFT,
        )
        db.session.add(invoice)
        db.session.commit()

        log_create('invoice', invoice.id, details=f'Facture brouillon creee: {invoice.number}')
        flash('Facture creee en brouillon. Ajoutez des lignes puis validez.', 'success')
        return redirect(url_for('invoices.view', invoice_id=invoice.id))

    return render_template('invoices/form.html',
                           form=form,
                           title='Nouvelle facture',
                           action='create')


# ============================================================================
# VIEW INVOICE
# ============================================================================

@invoices_bp.route('/<int:invoice_id>')
@login_required
@manager_required
def view(invoice_id):
    """View invoice details."""
    invoice = Invoice.query.get_or_404(invoice_id)
    payment_form = InvoicePaymentForm()
    payment_form.payment_date.data = date.today()

    return render_template('invoices/view.html',
                           invoice=invoice,
                           payment_form=payment_form)


# ============================================================================
# EDIT INVOICE
# ============================================================================

@invoices_bp.route('/<int:invoice_id>/edit', methods=['GET', 'POST'])
@login_required
@manager_required
def edit(invoice_id):
    """Edit an invoice (DRAFT only)."""
    invoice = Invoice.query.get_or_404(invoice_id)

    if invoice.status != InvoiceStatus.DRAFT:
        flash('Seules les factures en brouillon peuvent etre modifiees.', 'warning')
        return redirect(url_for('invoices.view', invoice_id=invoice.id))

    form = InvoiceForm()

    # Populate choices
    form.tour_id.choices = [(0, '-- Optionnel --')] + [
        (t.id, t.name) for t in Tour.query.order_by(Tour.start_date.desc()).all()
    ]
    form.tour_stop_id.choices = [(0, '-- Optionnel --')]
    if invoice.tour_id:
        stops = TourStop.query.filter_by(tour_id=invoice.tour_id).order_by(TourStop.date).all()
        form.tour_stop_id.choices += [
            (s.id, f"{s.date.strftime('%d/%m/%Y')} - {s.venue.name if s.venue else s.location_city}")
            for s in stops
        ]
    form.recipient_id.choices = [(0, '-- Saisie manuelle --')] + [
        (u.id, u.full_name) for u in User.query.filter_by(is_active=True).order_by(User.last_name).all()
    ]

    if form.validate_on_submit():
        # Update all fields
        invoice.type = InvoiceType(form.type.data)
        invoice.tour_id = form.tour_id.data if form.tour_id.data and form.tour_id.data != 0 else None
        invoice.tour_stop_id = form.tour_stop_id.data if form.tour_stop_id.data and form.tour_stop_id.data != 0 else None
        # Issuer
        for field in ['name', 'legal_form', 'address_line1', 'address_line2', 'city',
                       'postal_code', 'country', 'siren', 'siret', 'vat', 'rcs',
                       'capital', 'phone', 'email', 'iban', 'bic']:
            setattr(invoice, f'issuer_{field}', getattr(form, f'issuer_{field}').data)
        # Recipient
        invoice.recipient_id = form.recipient_id.data if form.recipient_id.data and form.recipient_id.data != 0 else None
        for field in ['name', 'legal_form', 'address_line1', 'address_line2', 'city',
                       'postal_code', 'country', 'siren', 'siret', 'vat', 'email', 'phone']:
            setattr(invoice, f'recipient_{field}', getattr(form, f'recipient_{field}').data)
        # Dates
        invoice.issue_date = form.issue_date.data
        invoice.due_date = form.due_date.data
        invoice.delivery_date = form.delivery_date.data
        # Payment terms
        invoice.payment_terms = form.payment_terms.data
        invoice.payment_terms_days = form.payment_terms_days.data
        invoice.payment_method_accepted = form.payment_method_accepted.data
        invoice.discount_amount = form.discount_amount.data or Decimal('0')
        # Legal
        invoice.vat_mention = form.vat_mention.data
        invoice.reverse_charge = form.reverse_charge.data
        invoice.early_payment_discount = form.early_payment_discount.data
        invoice.no_discount_mention = form.no_discount_mention.data
        invoice.special_mentions = form.special_mentions.data
        # Notes
        invoice.public_notes = form.public_notes.data
        invoice.internal_notes = form.internal_notes.data

        # Recalculate totals
        invoice.calculate_totals()
        db.session.commit()

        log_update('invoice', invoice.id, changes='Facture modifiee')
        flash('Facture mise a jour.', 'success')
        return redirect(url_for('invoices.view', invoice_id=invoice.id))

    elif request.method == 'GET':
        # Pre-populate form
        form.type.data = invoice.type.value
        form.tour_id.data = invoice.tour_id or 0
        form.tour_stop_id.data = invoice.tour_stop_id or 0
        form.recipient_id.data = invoice.recipient_id or 0
        # Issuer
        for field in ['name', 'legal_form', 'address_line1', 'address_line2', 'city',
                       'postal_code', 'country', 'siren', 'siret', 'vat', 'rcs',
                       'capital', 'phone', 'email', 'iban', 'bic']:
            form_field = getattr(form, f'issuer_{field}', None)
            if form_field:
                form_field.data = getattr(invoice, f'issuer_{field}')
        # Recipient
        for field in ['name', 'legal_form', 'address_line1', 'address_line2', 'city',
                       'postal_code', 'country', 'siren', 'siret', 'vat', 'email', 'phone']:
            form_field = getattr(form, f'recipient_{field}', None)
            if form_field:
                form_field.data = getattr(invoice, f'recipient_{field}')
        # Dates
        form.issue_date.data = invoice.issue_date
        form.due_date.data = invoice.due_date
        form.delivery_date.data = invoice.delivery_date
        # Payment terms
        form.payment_terms.data = invoice.payment_terms
        form.payment_terms_days.data = invoice.payment_terms_days
        form.payment_method_accepted.data = invoice.payment_method_accepted
        form.discount_amount.data = invoice.discount_amount
        # Legal
        form.vat_mention.data = invoice.vat_mention
        form.reverse_charge.data = invoice.reverse_charge
        form.early_payment_discount.data = invoice.early_payment_discount
        form.no_discount_mention.data = invoice.no_discount_mention
        form.special_mentions.data = invoice.special_mentions
        # Notes
        form.public_notes.data = invoice.public_notes
        form.internal_notes.data = invoice.internal_notes

    return render_template('invoices/form.html',
                           form=form,
                           invoice=invoice,
                           title=f'Modifier {invoice.number}',
                           action='edit')


# ============================================================================
# DELETE INVOICE (DRAFT only)
# ============================================================================

@invoices_bp.route('/<int:invoice_id>/delete', methods=['POST'])
@login_required
@manager_required
def delete(invoice_id):
    """Delete an invoice (DRAFT only)."""
    invoice = Invoice.query.get_or_404(invoice_id)

    if invoice.status != InvoiceStatus.DRAFT:
        flash('Seules les factures en brouillon peuvent etre supprimees.', 'danger')
        return redirect(url_for('invoices.view', invoice_id=invoice.id))

    number = invoice.number
    db.session.delete(invoice)
    db.session.commit()

    log_action('delete', 'invoice', invoice_id, details=f'Facture supprimee: {number}')
    flash(f'Facture {number} supprimee.', 'success')
    return redirect(url_for('invoices.index'))


# ============================================================================
# INVOICE LINES (AJAX)
# ============================================================================

@invoices_bp.route('/<int:invoice_id>/lines/add', methods=['POST'])
@login_required
@manager_required
def add_line(invoice_id):
    """Add a line to an invoice (AJAX or form post)."""
    invoice = Invoice.query.get_or_404(invoice_id)

    if invoice.status != InvoiceStatus.DRAFT:
        flash('Impossible de modifier une facture validee.', 'warning')
        return redirect(url_for('invoices.view', invoice_id=invoice.id))

    # Get next line number
    max_line = db.session.query(db.func.max(InvoiceLine.line_number))\
        .filter_by(invoice_id=invoice.id).scalar() or 0

    line = InvoiceLine(
        invoice_id=invoice.id,
        line_number=max_line + 1,
        description=request.form.get('description', ''),
        detail=request.form.get('detail', ''),
        reference=request.form.get('reference', ''),
        quantity=Decimal(request.form.get('quantity', '1')),
        unit=request.form.get('unit', 'unite'),
        unit_price_ht=Decimal(request.form.get('unit_price_ht', '0')),
        vat_rate=Decimal(request.form.get('vat_rate', '20.00')),
        discount_percent=Decimal(request.form.get('discount_percent', '0')),
        service_date_start=_parse_date(request.form.get('service_date_start')),
        service_date_end=_parse_date(request.form.get('service_date_end')),
    )
    line.calculate_totals()

    db.session.add(line)
    invoice.calculate_totals()
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'line_id': line.id,
            'subtotal_ht': str(invoice.subtotal_ht),
            'vat_amount': str(invoice.vat_amount),
            'total_ttc': str(invoice.total_ttc),
        })

    flash('Ligne ajoutee.', 'success')
    return redirect(url_for('invoices.view', invoice_id=invoice.id))


@invoices_bp.route('/<int:invoice_id>/lines/<int:line_id>/delete', methods=['POST'])
@login_required
@manager_required
def delete_line(invoice_id, line_id):
    """Delete an invoice line."""
    invoice = Invoice.query.get_or_404(invoice_id)

    if invoice.status != InvoiceStatus.DRAFT:
        flash('Impossible de modifier une facture validee.', 'warning')
        return redirect(url_for('invoices.view', invoice_id=invoice.id))

    line = InvoiceLine.query.get_or_404(line_id)
    if line.invoice_id != invoice.id:
        abort(403)

    db.session.delete(line)
    invoice.calculate_totals()
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'subtotal_ht': str(invoice.subtotal_ht),
            'vat_amount': str(invoice.vat_amount),
            'total_ttc': str(invoice.total_ttc),
        })

    flash('Ligne supprimee.', 'success')
    return redirect(url_for('invoices.view', invoice_id=invoice.id))


# ============================================================================
# WORKFLOW: VALIDATE
# ============================================================================

@invoices_bp.route('/<int:invoice_id>/validate', methods=['POST'])
@login_required
@manager_required
def validate_invoice(invoice_id):
    """Validate an invoice (assign number, lock from editing)."""
    invoice = Invoice.query.get_or_404(invoice_id)

    if invoice.status != InvoiceStatus.DRAFT:
        flash('Cette facture est deja validee.', 'warning')
        return redirect(url_for('invoices.view', invoice_id=invoice.id))

    try:
        invoice.mark_as_validated(current_user.id)
        db.session.commit()
        log_action('validate', 'invoice', invoice.id, details=f'Facture validee: {invoice.number}')
        flash(f'Facture validee avec le numero {invoice.number}.', 'success')
    except ValueError as e:
        flash(str(e), 'danger')

    return redirect(url_for('invoices.view', invoice_id=invoice.id))


# ============================================================================
# WORKFLOW: MARK AS SENT
# ============================================================================

@invoices_bp.route('/<int:invoice_id>/send', methods=['POST'])
@login_required
@manager_required
def mark_sent(invoice_id):
    """Mark invoice as sent."""
    invoice = Invoice.query.get_or_404(invoice_id)

    try:
        invoice.mark_as_sent()
        db.session.commit()
        log_action('send', 'invoice', invoice.id, details=f'Facture envoyee: {invoice.number}')
        flash('Facture marquee comme envoyee.', 'success')
    except ValueError as e:
        flash(str(e), 'danger')

    return redirect(url_for('invoices.view', invoice_id=invoice.id))


# ============================================================================
# WORKFLOW: RECORD PAYMENT
# ============================================================================

@invoices_bp.route('/<int:invoice_id>/payment', methods=['POST'])
@login_required
@manager_required
def record_payment(invoice_id):
    """Record a payment on an invoice."""
    invoice = Invoice.query.get_or_404(invoice_id)
    form = InvoicePaymentForm()

    if invoice.status in [InvoiceStatus.CANCELLED, InvoiceStatus.CREDITED, InvoiceStatus.DRAFT]:
        flash('Impossible d\'enregistrer un paiement sur cette facture.', 'danger')
        return redirect(url_for('invoices.view', invoice_id=invoice.id))

    if form.validate_on_submit():
        # Create payment record
        payment = InvoicePayment(
            invoice_id=invoice.id,
            amount=form.amount.data,
            payment_date=form.payment_date.data,
            payment_method=form.payment_method.data,
            reference=form.reference.data,
            bank_reference=form.bank_reference.data,
            notes=form.notes.data,
            created_by_id=current_user.id,
        )
        db.session.add(payment)

        # Update invoice amounts
        invoice.record_payment(form.amount.data, form.payment_date.data)
        db.session.commit()

        log_action('payment', 'invoice', invoice.id,
                   details=f'Paiement de {form.amount.data} EUR enregistre')
        flash(f'Paiement de {form.amount.data} EUR enregistre.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{error}', 'danger')

    return redirect(url_for('invoices.view', invoice_id=invoice.id))


# ============================================================================
# WORKFLOW: CANCEL
# ============================================================================

@invoices_bp.route('/<int:invoice_id>/cancel', methods=['POST'])
@login_required
@manager_required
def cancel(invoice_id):
    """Cancel an invoice."""
    invoice = Invoice.query.get_or_404(invoice_id)

    if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.CREDITED]:
        flash('Cette facture ne peut pas etre annulee.', 'warning')
        return redirect(url_for('invoices.view', invoice_id=invoice.id))

    invoice.status = InvoiceStatus.CANCELLED
    db.session.commit()

    log_action('cancel', 'invoice', invoice.id, details=f'Facture annulee: {invoice.number}')
    flash('Facture annulee.', 'success')
    return redirect(url_for('invoices.view', invoice_id=invoice.id))


# ============================================================================
# WORKFLOW: MARK OVERDUE (auto-check)
# ============================================================================

@invoices_bp.route('/<int:invoice_id>/mark-overdue', methods=['POST'])
@login_required
@manager_required
def mark_overdue(invoice_id):
    """Mark an invoice as overdue."""
    invoice = Invoice.query.get_or_404(invoice_id)

    if invoice.is_overdue and invoice.status not in [
        InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.CREDITED
    ]:
        invoice.status = InvoiceStatus.OVERDUE
        db.session.commit()
        flash('Facture marquee en retard.', 'warning')

    return redirect(url_for('invoices.view', invoice_id=invoice.id))


# ============================================================================
# API: Tour stops for dynamic dropdown
# ============================================================================

@invoices_bp.route('/api/tour-stops/<int:tour_id>')
@login_required
def api_tour_stops(tour_id):
    """Return tour stops for dynamic dropdown."""
    stops = TourStop.query.filter_by(tour_id=tour_id).order_by(TourStop.date).all()
    return jsonify([{
        'id': s.id,
        'date': s.date.strftime('%d/%m/%Y') if s.date else '',
        'venue': s.venue.name if s.venue else s.location_city or '',
    } for s in stops])


# ============================================================================
# HELPERS
# ============================================================================

def _parse_date(date_str):
    """Parse a date string, return None if invalid."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None
