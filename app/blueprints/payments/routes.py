"""
Payment routes - Enterprise-Grade financial module.
CRUD operations, approval workflow, batch operations, exports.
"""
from datetime import datetime, date
from decimal import Decimal
import csv
import io

from flask import (
    render_template, redirect, url_for, flash, request,
    jsonify, abort, Response, current_app
)
from flask_login import login_required, current_user

from app.blueprints.payments import payments_bp
from app.blueprints.payments.forms import (
    PaymentForm, PerDiemBatchForm, UserPaymentConfigForm,
    PaymentApprovalForm, PaymentFilterForm, BatchPaymentForm
)
from app.extensions import db
from app.models.payments import (
    TeamMemberPayment, UserPaymentConfig,
    StaffCategory, StaffRole, PaymentType, PaymentStatus, PaymentMethod,
    PaymentFrequency, ContractType, DEFAULT_RATES, get_category_for_role
)
from app.models.user import User
from app.models.tour import Tour
from app.models.tour_stop import TourStop
from app.utils.audit import log_action, log_create, log_update


def manager_required(f):
    """Decorator to require manager role."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.has_role('MANAGER'):
            flash('Acces reserve aux managers.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# PAYMENT LISTING & DASHBOARD
# ============================================================================

@payments_bp.route('/')
@login_required
@manager_required
def index():
    """List all payments with filters."""
    form = PaymentFilterForm(request.args)

    # Populate select fields
    form.tour_id.choices = [(0, 'Toutes les tournees')] + [
        (t.id, t.name) for t in Tour.query.order_by(Tour.start_date.desc()).all()
    ]
    form.user_id.choices = [(0, 'Tous les membres')] + [
        (u.id, u.full_name) for u in User.query.filter_by(is_active=True).order_by(User.last_name).all()
    ]

    # Build query
    query = TeamMemberPayment.query

    # Apply filters
    if form.tour_id.data and form.tour_id.data != 0:
        query = query.filter_by(tour_id=form.tour_id.data)
    if form.user_id.data and form.user_id.data != 0:
        query = query.filter_by(user_id=form.user_id.data)
    if form.status.data:
        query = query.filter_by(status=PaymentStatus(form.status.data))
    if form.payment_type.data:
        query = query.filter_by(payment_type=PaymentType(form.payment_type.data))
    if form.staff_category.data:
        query = query.filter_by(staff_category=StaffCategory(form.staff_category.data))
    if form.date_from.data:
        query = query.filter(TeamMemberPayment.work_date >= form.date_from.data)
    if form.date_to.data:
        query = query.filter(TeamMemberPayment.work_date <= form.date_to.data)

    # Order by most recent first
    payments = query.order_by(TeamMemberPayment.created_at.desc()).all()

    # Calculate summary stats
    total_amount = sum(p.amount for p in payments if p.status != PaymentStatus.CANCELLED)
    pending_amount = sum(p.amount for p in payments if p.status == PaymentStatus.PENDING_APPROVAL)
    paid_amount = sum(p.amount for p in payments if p.status == PaymentStatus.PAID)

    return render_template(
        'payments/list.html',
        payments=payments,
        form=form,
        total_amount=total_amount,
        pending_amount=pending_amount,
        paid_amount=paid_amount
    )


@payments_bp.route('/dashboard')
@login_required
@manager_required
def dashboard():
    """Financial dashboard with KPIs."""
    # Pending approvals
    pending_approvals = TeamMemberPayment.query.filter_by(
        status=PaymentStatus.PENDING_APPROVAL
    ).count()

    # Total to pay this month
    today = date.today()
    first_of_month = today.replace(day=1)
    monthly_payments = TeamMemberPayment.query.filter(
        TeamMemberPayment.status.in_([PaymentStatus.APPROVED, PaymentStatus.SCHEDULED]),
        TeamMemberPayment.due_date >= first_of_month,
        TeamMemberPayment.due_date <= today.replace(day=28)
    ).all()
    monthly_total = sum(p.amount for p in monthly_payments)

    # Payments by category
    category_totals = {}
    for category in StaffCategory:
        total = db.session.query(db.func.sum(TeamMemberPayment.amount)).filter(
            TeamMemberPayment.staff_category == category,
            TeamMemberPayment.status != PaymentStatus.CANCELLED
        ).scalar() or Decimal('0')
        category_totals[category.value] = float(total)

    # Recent payments
    recent_payments = TeamMemberPayment.query.order_by(
        TeamMemberPayment.created_at.desc()
    ).limit(10).all()

    return render_template(
        'payments/dashboard.html',
        pending_approvals=pending_approvals,
        monthly_total=monthly_total,
        category_totals=category_totals,
        recent_payments=recent_payments
    )


# ============================================================================
# PAYMENT CRUD
# ============================================================================

@payments_bp.route('/add', methods=['GET', 'POST'])
@login_required
@manager_required
def add():
    """Create a new payment."""
    form = PaymentForm()

    # Populate select fields
    form.user_id.choices = [(0, '-- Selectionner --')] + [
        (u.id, f"{u.full_name} ({u.email})") for u in User.query.filter_by(is_active=True).order_by(User.last_name).all()
    ]
    form.tour_id.choices = [(0, '-- Optionnel --')] + [
        (t.id, t.name) for t in Tour.query.order_by(Tour.start_date.desc()).all()
    ]
    form.tour_stop_id.choices = [(0, '-- Optionnel --')]

    if form.validate_on_submit():
        payment = TeamMemberPayment(
            user_id=form.user_id.data,
            tour_id=form.tour_id.data if form.tour_id.data != 0 else None,
            tour_stop_id=form.tour_stop_id.data if form.tour_stop_id.data != 0 else None,
            staff_category=StaffCategory(form.staff_category.data) if form.staff_category.data else None,
            staff_role=StaffRole[form.staff_role.data] if form.staff_role.data else None,
            payment_type=PaymentType(form.payment_type.data),
            payment_frequency=PaymentFrequency(form.payment_frequency.data) if form.payment_frequency.data else None,
            description=form.description.data,
            quantity=form.quantity.data or Decimal('1'),
            unit_rate=form.unit_rate.data,
            amount=form.amount.data,
            currency=form.currency.data,
            work_date=form.work_date.data,
            due_date=form.due_date.data,
            payment_method=PaymentMethod(form.payment_method.data) if form.payment_method.data else None,
            notes=form.notes.data,
            status=PaymentStatus.DRAFT,
            created_by_id=current_user.id
        )

        payment.reference = TeamMemberPayment.generate_reference()
        db.session.add(payment)
        db.session.commit()

        log_create('TeamMemberPayment', payment.id, {
            'reference': payment.reference,
            'user_id': payment.user_id,
            'amount': str(payment.amount),
            'type': payment.payment_type.value
        })

        flash(f'Paiement {payment.reference} cree avec succes.', 'success')
        return redirect(url_for('payments.detail', payment_id=payment.id))

    return render_template('payments/form.html', form=form, title='Nouveau paiement')


@payments_bp.route('/<int:payment_id>')
@login_required
@manager_required
def detail(payment_id):
    """View payment details."""
    payment = TeamMemberPayment.query.get_or_404(payment_id)
    return render_template('payments/detail.html', payment=payment)


@payments_bp.route('/<int:payment_id>/edit', methods=['GET', 'POST'])
@login_required
@manager_required
def edit(payment_id):
    """Edit an existing payment."""
    payment = TeamMemberPayment.query.get_or_404(payment_id)

    # Cannot edit paid or cancelled payments
    if payment.status in [PaymentStatus.PAID, PaymentStatus.CANCELLED]:
        flash('Ce paiement ne peut plus etre modifie.', 'warning')
        return redirect(url_for('payments.detail', payment_id=payment_id))

    form = PaymentForm(obj=payment)

    # Populate select fields
    form.user_id.choices = [(0, '-- Selectionner --')] + [
        (u.id, f"{u.full_name} ({u.email})") for u in User.query.filter_by(is_active=True).order_by(User.last_name).all()
    ]
    form.tour_id.choices = [(0, '-- Optionnel --')] + [
        (t.id, t.name) for t in Tour.query.order_by(Tour.start_date.desc()).all()
    ]
    form.tour_stop_id.choices = [(0, '-- Optionnel --')]

    if request.method == 'GET':
        # Set form values from payment
        form.staff_category.data = payment.staff_category.value if payment.staff_category else ''
        form.staff_role.data = payment.staff_role.name if payment.staff_role else ''
        form.payment_type.data = payment.payment_type.value if payment.payment_type else ''
        form.payment_frequency.data = payment.payment_frequency.value if payment.payment_frequency else ''
        form.payment_method.data = payment.payment_method.value if payment.payment_method else ''

    if form.validate_on_submit():
        old_amount = payment.amount

        payment.user_id = form.user_id.data
        payment.tour_id = form.tour_id.data if form.tour_id.data != 0 else None
        payment.tour_stop_id = form.tour_stop_id.data if form.tour_stop_id.data != 0 else None
        payment.staff_category = StaffCategory(form.staff_category.data) if form.staff_category.data else None
        payment.staff_role = StaffRole[form.staff_role.data] if form.staff_role.data else None
        payment.payment_type = PaymentType(form.payment_type.data)
        payment.payment_frequency = PaymentFrequency(form.payment_frequency.data) if form.payment_frequency.data else None
        payment.description = form.description.data
        payment.quantity = form.quantity.data or Decimal('1')
        payment.unit_rate = form.unit_rate.data
        payment.amount = form.amount.data
        payment.currency = form.currency.data
        payment.work_date = form.work_date.data
        payment.due_date = form.due_date.data
        payment.payment_method = PaymentMethod(form.payment_method.data) if form.payment_method.data else None
        payment.notes = form.notes.data
        payment.updated_at = datetime.utcnow()

        db.session.commit()

        log_update('TeamMemberPayment', payment.id, {
            'old_amount': str(old_amount),
            'new_amount': str(payment.amount)
        })

        flash('Paiement mis a jour avec succes.', 'success')
        return redirect(url_for('payments.detail', payment_id=payment_id))

    return render_template('payments/form.html', form=form, payment=payment, title='Modifier le paiement')


@payments_bp.route('/<int:payment_id>/delete', methods=['POST'])
@login_required
@manager_required
def delete(payment_id):
    """Delete a draft payment."""
    payment = TeamMemberPayment.query.get_or_404(payment_id)

    if payment.status != PaymentStatus.DRAFT:
        flash('Seuls les paiements en brouillon peuvent etre supprimes.', 'warning')
        return redirect(url_for('payments.detail', payment_id=payment_id))

    reference = payment.reference
    db.session.delete(payment)
    db.session.commit()

    log_action('DELETE', 'TeamMemberPayment', payment_id, {'reference': reference})

    flash(f'Paiement {reference} supprime.', 'success')
    return redirect(url_for('payments.index'))


# ============================================================================
# APPROVAL WORKFLOW
# ============================================================================

@payments_bp.route('/<int:payment_id>/submit', methods=['POST'])
@login_required
@manager_required
def submit_for_approval(payment_id):
    """Submit a payment for approval."""
    payment = TeamMemberPayment.query.get_or_404(payment_id)

    if payment.status != PaymentStatus.DRAFT:
        flash('Ce paiement ne peut pas etre soumis.', 'warning')
        return redirect(url_for('payments.detail', payment_id=payment_id))

    payment.submit_for_approval()
    db.session.commit()

    log_action('SUBMIT', 'TeamMemberPayment', payment.id, {
        'reference': payment.reference,
        'amount': str(payment.amount)
    })

    flash(f'Paiement {payment.reference} soumis pour approbation.', 'success')
    return redirect(url_for('payments.detail', payment_id=payment_id))


@payments_bp.route('/approval-queue')
@login_required
@manager_required
def approval_queue():
    """View payments pending approval."""
    payments = TeamMemberPayment.query.filter_by(
        status=PaymentStatus.PENDING_APPROVAL
    ).order_by(TeamMemberPayment.created_at).all()

    total_pending = sum(p.amount for p in payments)

    return render_template(
        'payments/approval_queue.html',
        payments=payments,
        total_pending=total_pending
    )


@payments_bp.route('/<int:payment_id>/approve', methods=['POST'])
@login_required
@manager_required
def approve(payment_id):
    """Approve a payment."""
    payment = TeamMemberPayment.query.get_or_404(payment_id)

    if payment.status != PaymentStatus.PENDING_APPROVAL:
        flash('Ce paiement ne peut pas etre approuve.', 'warning')
        return redirect(url_for('payments.detail', payment_id=payment_id))

    payment.approve(current_user.id)  # P-C2 fix: pass user_id, not user object
    db.session.commit()

    log_action('APPROVE', 'TeamMemberPayment', payment.id, {
        'reference': payment.reference,
        'amount': str(payment.amount),
        'approved_by': current_user.id
    })

    flash(f'Paiement {payment.reference} approuve.', 'success')

    # Return to queue if there are more
    if TeamMemberPayment.query.filter_by(status=PaymentStatus.PENDING_APPROVAL).count() > 0:
        return redirect(url_for('payments.approval_queue'))

    return redirect(url_for('payments.detail', payment_id=payment_id))


@payments_bp.route('/<int:payment_id>/reject', methods=['POST'])
@login_required
@manager_required
def reject(payment_id):
    """Reject a payment."""
    payment = TeamMemberPayment.query.get_or_404(payment_id)
    reason = request.form.get('reason', '')

    if payment.status != PaymentStatus.PENDING_APPROVAL:
        flash('Ce paiement ne peut pas etre rejete.', 'warning')
        return redirect(url_for('payments.detail', payment_id=payment_id))

    payment.reject(current_user, reason)
    db.session.commit()

    log_action('REJECT', 'TeamMemberPayment', payment.id, {
        'reference': payment.reference,
        'reason': reason
    })

    flash(f'Paiement {payment.reference} rejete.', 'warning')
    return redirect(url_for('payments.approval_queue'))


@payments_bp.route('/<int:payment_id>/mark-paid', methods=['POST'])
@login_required
@manager_required
def mark_paid(payment_id):
    """Mark a payment as paid."""
    payment = TeamMemberPayment.query.get_or_404(payment_id)

    if payment.status not in [PaymentStatus.APPROVED, PaymentStatus.SCHEDULED]:
        flash('Ce paiement ne peut pas etre marque comme paye.', 'warning')
        return redirect(url_for('payments.detail', payment_id=payment_id))

    bank_reference = request.form.get('bank_reference', '')
    payment.mark_as_paid(bank_reference)
    db.session.commit()

    log_action('PAY', 'TeamMemberPayment', payment.id, {
        'reference': payment.reference,
        'amount': str(payment.amount),
        'bank_reference': bank_reference
    })

    flash(f'Paiement {payment.reference} marque comme paye.', 'success')
    return redirect(url_for('payments.detail', payment_id=payment_id))


# ============================================================================
# BATCH OPERATIONS
# ============================================================================

@payments_bp.route('/batch/per-diems', methods=['GET', 'POST'])
@login_required
@manager_required
def batch_per_diems():
    """Generate per diems for a tour."""
    form = PerDiemBatchForm()

    form.tour_id.choices = [(0, '-- Selectionner --')] + [
        (t.id, f"{t.name} ({t.start_date.strftime('%d/%m/%Y')} - {t.end_date.strftime('%d/%m/%Y') if t.end_date else '?'})")
        for t in Tour.query.order_by(Tour.start_date.desc()).all()
    ]

    if form.validate_on_submit():
        tour = Tour.query.get_or_404(form.tour_id.data)

        # Get all tour stops
        tour_stops = TourStop.query.filter_by(tour_id=tour.id).order_by(TourStop.date).all()

        if not tour_stops:
            flash('Cette tournee n\'a pas de dates.', 'warning')
            return redirect(url_for('payments.batch_per_diems'))

        # Get team members with payment config (those who get per diems)
        members_with_config = UserPaymentConfig.query.filter(
            UserPaymentConfig.per_diem > 0
        ).all()

        if not members_with_config:
            flash('Aucun membre n\'a de configuration de per diem.', 'warning')
            return redirect(url_for('payments.batch_per_diems'))

        created_count = 0
        per_diem_amount = form.per_diem_amount.data

        for stop in tour_stops:
            # Skip if not show day and option not selected
            if stop.event_type == 'travel' and not form.include_travel_days.data:
                continue
            if stop.event_type == 'day_off' and not form.include_day_offs.data:
                continue

            for config in members_with_config:
                # Check if payment already exists
                existing = TeamMemberPayment.query.filter_by(
                    user_id=config.user_id,
                    tour_stop_id=stop.id,
                    payment_type=PaymentType.PER_DIEM
                ).first()

                if existing:
                    continue

                # Create per diem payment
                payment = TeamMemberPayment(
                    user_id=config.user_id,
                    tour_id=tour.id,
                    tour_stop_id=stop.id,
                    staff_category=config.staff_category,
                    staff_role=config.staff_role,
                    payment_type=PaymentType.PER_DIEM,
                    description=f"Per diem - {stop.date.strftime('%d/%m/%Y')}",
                    amount=per_diem_amount,
                    currency='EUR',
                    work_date=stop.date,
                    status=PaymentStatus.DRAFT,
                    created_by_id=current_user.id,
                    notes=form.notes.data
                )
                payment.reference = TeamMemberPayment.generate_reference()
                db.session.add(payment)
                created_count += 1

        db.session.commit()

        log_action('CREATE', 'TeamMemberPayment', None, {
            'batch': 'per_diems',
            'tour_id': tour.id,
            'count': created_count,
            'amount_each': str(per_diem_amount)
        })

        flash(f'{created_count} per diems generes pour la tournee {tour.name}.', 'success')
        return redirect(url_for('payments.index', tour_id=tour.id))

    return render_template('payments/batch_per_diems.html', form=form)


@payments_bp.route('/batch/approve', methods=['POST'])
@login_required
@manager_required
def batch_approve():
    """Approve multiple payments at once."""
    payment_ids = request.form.getlist('payment_ids')

    if not payment_ids:
        flash('Aucun paiement selectionne.', 'warning')
        return redirect(url_for('payments.approval_queue'))

    approved_count = 0
    for pid in payment_ids:
        payment = TeamMemberPayment.query.get(int(pid))
        if payment and payment.status == PaymentStatus.PENDING_APPROVAL:
            payment.approve(current_user.id)  # P-C2 fix: pass user_id, not user object
            approved_count += 1

    db.session.commit()

    log_action('APPROVE', 'TeamMemberPayment', None, {
        'batch': True,
        'count': approved_count,
        'approved_by': current_user.id
    })

    flash(f'{approved_count} paiement(s) approuve(s).', 'success')
    return redirect(url_for('payments.approval_queue'))


# ============================================================================
# EXPORTS
# ============================================================================

@payments_bp.route('/export/csv')
@login_required
@manager_required
def export_csv():
    """Export payments to CSV."""
    # Get filter parameters
    tour_id = request.args.get('tour_id', type=int)
    status = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    query = TeamMemberPayment.query

    if tour_id:
        query = query.filter_by(tour_id=tour_id)
    if status:
        query = query.filter_by(status=PaymentStatus(status))
    if date_from:
        query = query.filter(TeamMemberPayment.work_date >= date_from)
    if date_to:
        query = query.filter(TeamMemberPayment.work_date <= date_to)

    payments = query.order_by(TeamMemberPayment.work_date).all()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')

    # Header
    writer.writerow([
        'Reference', 'Date travail', 'Beneficiaire', 'Email',
        'Categorie', 'Role', 'Type', 'Description',
        'Montant', 'Devise', 'Statut', 'Date paiement',
        'Tournee', 'Concert'
    ])

    for p in payments:
        writer.writerow([
            p.reference,
            p.work_date.strftime('%d/%m/%Y') if p.work_date else '',
            p.user.full_name if p.user else '',
            p.user.email if p.user else '',
            p.staff_category.value if p.staff_category else '',
            p.staff_role.value if p.staff_role else '',
            p.payment_type.value if p.payment_type else '',
            p.description or '',
            str(p.amount),
            p.currency,
            p.status.value if p.status else '',
            p.paid_date.strftime('%d/%m/%Y') if p.paid_date else '',
            p.tour.name if p.tour else '',
            p.tour_stop.date.strftime('%d/%m/%Y') if p.tour_stop else ''
        ])

    log_action('EXPORT_CSV', 'TeamMemberPayment', None, {
        'count': len(payments),
        'filters': {'tour_id': tour_id, 'status': status}
    })

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=paiements_{datetime.now().strftime("%Y%m%d")}.csv'
        }
    )


@payments_bp.route('/export/sepa')
@login_required
@manager_required
def export_sepa():
    """Export approved payments as SEPA XML file."""
    # Get approved payments ready for SEPA export
    payments = TeamMemberPayment.query.filter(
        TeamMemberPayment.status.in_([PaymentStatus.APPROVED, PaymentStatus.SCHEDULED]),
        TeamMemberPayment.payment_method == PaymentMethod.SEPA
    ).all()

    if not payments:
        flash('Aucun paiement SEPA a exporter.', 'warning')
        return redirect(url_for('payments.index'))

    # For now, return a simple message - full SEPA XML generation would be in a service
    flash(f'{len(payments)} paiements prets pour export SEPA. Fonctionnalite complete a venir.', 'info')

    log_action('EXPORT_SEPA', 'TeamMemberPayment', None, {
        'count': len(payments),
        'total': str(sum(p.amount for p in payments))
    })

    return redirect(url_for('payments.index'))


# ============================================================================
# USER PAYMENT CONFIG
# ============================================================================

@payments_bp.route('/config')
@login_required
@manager_required
def config_list():
    """List all user payment configurations."""
    configs = UserPaymentConfig.query.join(User).order_by(User.last_name).all()
    users_without_config = User.query.filter(
        ~User.id.in_([c.user_id for c in configs]),
        User.is_active == True
    ).all()

    return render_template(
        'payments/config_list.html',
        configs=configs,
        users_without_config=users_without_config
    )


@payments_bp.route('/config/<int:user_id>', methods=['GET', 'POST'])
@login_required
@manager_required
def config_edit(user_id):
    """Edit user payment configuration."""
    user = User.query.get_or_404(user_id)
    config = UserPaymentConfig.query.get(user_id)

    if config is None:
        config = UserPaymentConfig(user_id=user_id)
        db.session.add(config)

    form = UserPaymentConfigForm(obj=config)

    if request.method == 'GET' and config.staff_category:
        form.staff_category.data = config.staff_category.value
        if config.staff_role:
            form.staff_role.data = config.staff_role.name
        if config.contract_type:
            form.contract_type.data = config.contract_type.value
        if config.payment_frequency:
            form.payment_frequency.data = config.payment_frequency.value

    if form.validate_on_submit():
        config.staff_category = StaffCategory(form.staff_category.data) if form.staff_category.data else None
        config.staff_role = StaffRole[form.staff_role.data] if form.staff_role.data else None
        config.contract_type = ContractType(form.contract_type.data) if form.contract_type.data else None
        config.payment_frequency = PaymentFrequency(form.payment_frequency.data) if form.payment_frequency.data else None

        config.show_rate = form.show_rate.data
        config.daily_rate = form.daily_rate.data
        config.half_day_rate = form.half_day_rate.data
        config.weekly_rate = form.weekly_rate.data
        config.hourly_rate = form.hourly_rate.data
        config.per_diem = form.per_diem.data

        config.overtime_rate_25 = form.overtime_rate_25.data
        config.overtime_rate_50 = form.overtime_rate_50.data
        config.weekend_rate = form.weekend_rate.data
        config.holiday_rate = form.holiday_rate.data

        config.iban = form.iban.data
        config.bic = form.bic.data
        config.bank_name = form.bank_name.data

        config.siret = form.siret.data
        config.siren = form.siren.data
        config.vat_number = form.vat_number.data
        config.social_security_number = form.social_security_number.data
        config.is_intermittent = form.is_intermittent.data
        config.conges_spectacle_id = form.conges_spectacle_id.data
        config.audiens_id = form.audiens_id.data
        config.intermittent_id = form.intermittent_id.data
        config.notes = form.notes.data

        db.session.commit()

        log_update('UserPaymentConfig', user_id, {'updated': True})

        flash(f'Configuration de paiement pour {user.full_name} mise a jour.', 'success')
        return redirect(url_for('payments.config_list'))

    return render_template(
        'payments/config_form.html',
        form=form,
        user=user,
        config=config
    )


@payments_bp.route('/config/<int:user_id>/apply-defaults', methods=['POST'])
@login_required
@manager_required
def config_apply_defaults(user_id):
    """Apply default rates based on role."""
    config = UserPaymentConfig.query.get_or_404(user_id)

    if config.staff_role and config.staff_role in DEFAULT_RATES:
        defaults = DEFAULT_RATES[config.staff_role]
        config.show_rate = defaults.get('show_rate')
        config.daily_rate = defaults.get('daily_rate')
        config.weekly_rate = defaults.get('weekly_rate')
        config.hourly_rate = defaults.get('hourly_rate')
        config.per_diem = defaults.get('per_diem', 35)

        db.session.commit()
        flash('Taux par defaut appliques.', 'success')
    else:
        flash('Aucun taux par defaut disponible pour ce role.', 'warning')

    return redirect(url_for('payments.config_edit', user_id=user_id))


# ============================================================================
# TOUR PAYMENTS SUMMARY
# ============================================================================

@payments_bp.route('/tour/<int:tour_id>')
@login_required
@manager_required
def tour_summary(tour_id):
    """Financial summary for a tour."""
    tour = Tour.query.get_or_404(tour_id)

    payments = TeamMemberPayment.query.filter_by(tour_id=tour_id).all()

    # Group by category
    by_category = {}
    for cat in StaffCategory:
        cat_payments = [p for p in payments if p.staff_category == cat]
        by_category[cat.value] = {
            'payments': cat_payments,
            'total': sum(p.amount for p in cat_payments if p.status != PaymentStatus.CANCELLED),
            'count': len(cat_payments)
        }

    # Group by type
    by_type = {}
    for ptype in PaymentType:
        type_payments = [p for p in payments if p.payment_type == ptype]
        by_type[ptype.value] = {
            'total': sum(p.amount for p in type_payments if p.status != PaymentStatus.CANCELLED),
            'count': len(type_payments)
        }

    # Group by status
    by_status = {}
    for status in PaymentStatus:
        status_payments = [p for p in payments if p.status == status]
        by_status[status.value] = {
            'total': sum(p.amount for p in status_payments),
            'count': len(status_payments)
        }

    total_amount = sum(p.amount for p in payments if p.status != PaymentStatus.CANCELLED)

    return render_template(
        'payments/tour_summary.html',
        tour=tour,
        payments=payments,
        by_category=by_category,
        by_type=by_type,
        by_status=by_status,
        total_amount=total_amount
    )


# ============================================================================
# API ENDPOINTS (for AJAX)
# ============================================================================

@payments_bp.route('/api/tour-stops/<int:tour_id>')
@login_required
def api_tour_stops(tour_id):
    """Get tour stops for a tour (AJAX)."""
    stops = TourStop.query.filter_by(tour_id=tour_id).order_by(TourStop.date).all()
    return jsonify([
        {
            'id': s.id,
            'date': s.date.strftime('%d/%m/%Y'),
            'venue': s.venue.name if s.venue else s.location_city or 'N/A',
            'event_type': s.event_type
        }
        for s in stops
    ])


@payments_bp.route('/api/user-config/<int:user_id>')
@login_required
def api_user_config(user_id):
    """Get user payment config (AJAX)."""
    config = UserPaymentConfig.query.get(user_id)
    if not config:
        return jsonify({})

    return jsonify({
        'staff_category': config.staff_category.value if config.staff_category else None,
        'staff_role': config.staff_role.name if config.staff_role else None,
        'show_rate': str(config.show_rate) if config.show_rate else None,
        'daily_rate': str(config.daily_rate) if config.daily_rate else None,
        'weekly_rate': str(config.weekly_rate) if config.weekly_rate else None,
        'hourly_rate': str(config.hourly_rate) if config.hourly_rate else None,
        'per_diem': str(config.per_diem) if config.per_diem else None
    })


@payments_bp.route('/api/default-rates/<role>')
@login_required
def api_default_rates(role):
    """Get default rates for a role (AJAX)."""
    try:
        staff_role = StaffRole[role]
        if staff_role in DEFAULT_RATES:
            return jsonify(DEFAULT_RATES[staff_role])
    except KeyError:
        pass
    return jsonify({})
