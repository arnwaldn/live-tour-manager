"""
Report service for generating PDF documents and CSV exports.
Generates accounting-ready documents for external payment processing.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Optional
import csv
import io

from flask import render_template, current_app
from sqlalchemy.orm import joinedload
from io import BytesIO
from xhtml2pdf import pisa

from app.extensions import db
from app.models.payments import (
    TeamMemberPayment, UserPaymentConfig, PaymentType,
    PaymentStatus, StaffCategory
)
from app.models.tour import Tour
from app.models.user import User
from app.services.payment_service import PaymentService


class ReportService:
    """Service for generating financial reports and documents."""

    @staticmethod
    def generate_bordereau_paiement(tour_id: int) -> bytes:
        """
        Generate a payment slip (bordereau) PDF for a tour.
        This document lists all payments to be processed for accounting.

        Args:
            tour_id: Tour ID

        Returns:
            PDF bytes
        """
        tour = Tour.query.get_or_404(tour_id)

        # Get approved payments for this tour with eager loading (H3 fix: avoid N+1 queries)
        payments = TeamMemberPayment.query.filter_by(
            tour_id=tour_id
        ).filter(
            TeamMemberPayment.status.in_([
                PaymentStatus.APPROVED,
                PaymentStatus.SCHEDULED
            ])
        ).options(
            joinedload(TeamMemberPayment.user)
        ).order_by(TeamMemberPayment.user_id, TeamMemberPayment.work_date).all()

        # Pre-load all UserPaymentConfigs in one query (H3 fix: avoid N+1)
        user_ids = list(set(p.user_id for p in payments if p.user_id))
        configs_list = UserPaymentConfig.query.filter(
            UserPaymentConfig.user_id.in_(user_ids)
        ).all() if user_ids else []
        configs_by_user = {c.user_id: c for c in configs_list}

        # Group by user with bank details
        payments_by_user = {}
        for payment in payments:
            user_id = payment.user_id
            if user_id not in payments_by_user:
                config = configs_by_user.get(user_id)
                payments_by_user[user_id] = {
                    'user': payment.user,
                    'config': config,
                    'payments': [],
                    'total': Decimal('0')
                }
            payments_by_user[user_id]['payments'].append(payment)
            payments_by_user[user_id]['total'] += payment.amount

        # Calculate totals
        total_amount = sum(p['total'] for p in payments_by_user.values())
        total_beneficiaries = len(payments_by_user)

        # Render HTML template
        html_content = render_template(
            'reports/bordereau_paiement.html',
            tour=tour,
            payments_by_user=payments_by_user,
            total_amount=total_amount,
            total_beneficiaries=total_beneficiaries,
            generated_at=datetime.now(),
            payments=payments
        )

        # Convert to PDF using xhtml2pdf (cloud-compatible)
        result = BytesIO()
        pisa.pisaDocument(BytesIO(html_content.encode('utf-8')), result)
        return result.getvalue()

    @staticmethod
    def generate_fiche_membre(user_id: int, start_date: date = None, end_date: date = None) -> bytes:
        """
        Generate a member payment summary PDF.
        Lists all payments for a team member over a period.

        Args:
            user_id: User ID
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            PDF bytes
        """
        user = User.query.get_or_404(user_id)
        config = UserPaymentConfig.query.get(user_id)

        # Get payments
        payments = PaymentService.get_user_payments(user_id, start_date, end_date)

        # Calculate totals by type
        totals = PaymentService.calculate_user_totals(user_id)

        # Group by tour
        payments_by_tour = {}
        for payment in payments:
            tour_name = payment.tour.name if payment.tour else 'Hors tournee'
            if tour_name not in payments_by_tour:
                payments_by_tour[tour_name] = {
                    'payments': [],
                    'total': Decimal('0')
                }
            payments_by_tour[tour_name]['payments'].append(payment)
            payments_by_tour[tour_name]['total'] += payment.amount

        # Render HTML template
        html_content = render_template(
            'reports/fiche_membre.html',
            user=user,
            config=config,
            payments=payments,
            payments_by_tour=payments_by_tour,
            totals=totals,
            start_date=start_date,
            end_date=end_date,
            generated_at=datetime.now()
        )

        # Convert to PDF using xhtml2pdf (cloud-compatible)
        result = BytesIO()
        pisa.pisaDocument(BytesIO(html_content.encode('utf-8')), result)
        return result.getvalue()

    @staticmethod
    def generate_budget_tournee(tour_id: int) -> bytes:
        """
        Generate a tour budget report PDF.
        Shows planned vs actual expenses.

        Args:
            tour_id: Tour ID

        Returns:
            PDF bytes
        """
        tour = Tour.query.get_or_404(tour_id)

        # Get all payments for this tour
        payments = TeamMemberPayment.query.filter_by(tour_id=tour_id).all()

        # Get tour summary
        summary = PaymentService.get_tour_summary(tour_id)

        # Calculate by category
        by_category = []
        for cat in StaffCategory:
            cat_payments = [p for p in payments if p.staff_category == cat]
            if cat_payments:
                by_category.append({
                    'name': cat.value.title(),
                    'count': len(cat_payments),
                    'total': sum(p.amount for p in cat_payments)
                })

        # Calculate by payment type
        by_type = []
        for ptype in PaymentType:
            type_payments = [p for p in payments if p.payment_type == ptype]
            if type_payments:
                by_type.append({
                    'name': ptype.value.title(),
                    'count': len(type_payments),
                    'total': sum(p.amount for p in type_payments)
                })

        # Render HTML template
        html_content = render_template(
            'reports/budget_tournee.html',
            tour=tour,
            payments=payments,
            summary=summary,
            by_category=by_category,
            by_type=by_type,
            total_amount=summary['total_amount'],
            generated_at=datetime.now()
        )

        # Convert to PDF using xhtml2pdf (cloud-compatible)
        result = BytesIO()
        pisa.pisaDocument(BytesIO(html_content.encode('utf-8')), result)
        return result.getvalue()

    @staticmethod
    def generate_attestation_paiement(payment_id: int) -> bytes:
        """
        Generate a payment attestation PDF.
        Document confirming a payment was made.

        Args:
            payment_id: Payment ID

        Returns:
            PDF bytes
        """
        payment = TeamMemberPayment.query.get_or_404(payment_id)
        config = UserPaymentConfig.query.get(payment.user_id)

        # Render HTML template
        html_content = render_template(
            'reports/attestation_paiement.html',
            payment=payment,
            user=payment.user,
            config=config,
            generated_at=datetime.now()
        )

        # Convert to PDF using xhtml2pdf (cloud-compatible)
        result = BytesIO()
        pisa.pisaDocument(BytesIO(html_content.encode('utf-8')), result)
        return result.getvalue()

    @staticmethod
    def export_masse_salariale_csv(tour_id: int) -> str:
        """
        Export payroll data for accounting.
        Includes all payment details with bank information.

        Args:
            tour_id: Tour ID

        Returns:
            CSV string
        """
        tour = Tour.query.get_or_404(tour_id)

        # Get all approved/paid payments with eager loading (H3 fix: avoid N+1 queries)
        payments = TeamMemberPayment.query.filter_by(tour_id=tour_id).filter(
            TeamMemberPayment.status.in_([
                PaymentStatus.APPROVED,
                PaymentStatus.SCHEDULED,
                PaymentStatus.PAID
            ])
        ).options(
            joinedload(TeamMemberPayment.user)
        ).order_by(TeamMemberPayment.user_id).all()

        # Pre-load all UserPaymentConfigs in one query (H3 fix: avoid N+1)
        user_ids = list(set(p.user_id for p in payments if p.user_id))
        configs_list = UserPaymentConfig.query.filter(
            UserPaymentConfig.user_id.in_(user_ids)
        ).all() if user_ids else []
        configs_by_user = {c.user_id: c for c in configs_list}

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')

        # Header matching French accounting software format
        writer.writerow([
            'Reference',
            'Nom',
            'Prenom',
            'Email',
            'Type paiement',
            'Description',
            'Date travail',
            'Montant brut',
            'Devise',
            'IBAN',
            'BIC',
            'Banque',
            'Statut intermittent',
            'SIRET',
            'Numero conges spectacles',
            'Tournee',
            'Statut'
        ])

        for payment in payments:
            user = payment.user
            config = configs_by_user.get(payment.user_id) if payment.user_id else None

            writer.writerow([
                payment.reference,
                user.last_name if user else '',
                user.first_name if user else '',
                user.email if user else '',
                payment.payment_type.value if payment.payment_type else '',
                payment.description or '',
                payment.work_date.strftime('%d/%m/%Y') if payment.work_date else '',
                str(payment.amount),
                payment.currency,
                config.iban if config and config.iban else '',
                config.bic if config and config.bic else '',
                config.bank_name if config and config.bank_name else '',
                'Oui' if config and config.is_intermittent else 'Non',
                config.siret if config and config.siret else '',
                config.conges_spectacle_id if config and config.conges_spectacle_id else '',
                tour.name,
                payment.status.value if payment.status else ''
            ])

        return output.getvalue()

    @staticmethod
    def export_paiements_a_effectuer_csv(band_ids: Optional[List[int]] = None) -> str:
        """
        Export list of payments to be processed.
        Only includes approved payments not yet paid.

        Args:
            band_ids: Optional list of band IDs to filter by

        Returns:
            CSV string
        """
        query = TeamMemberPayment.query.filter_by(status=PaymentStatus.APPROVED)

        if band_ids:
            # Filter by tours belonging to these bands
            query = query.join(Tour).filter(Tour.band_id.in_(band_ids))

        # Add eager loading (H3 fix: avoid N+1 queries)
        payments = query.options(
            joinedload(TeamMemberPayment.user),
            joinedload(TeamMemberPayment.tour)
        ).order_by(
            TeamMemberPayment.user_id,
            TeamMemberPayment.work_date
        ).all()

        # Pre-load all UserPaymentConfigs in one query (H3 fix: avoid N+1)
        user_ids = list(set(p.user_id for p in payments if p.user_id))
        configs_list = UserPaymentConfig.query.filter(
            UserPaymentConfig.user_id.in_(user_ids)
        ).all() if user_ids else []
        configs_by_user = {c.user_id: c for c in configs_list}

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')

        # Header for bank import format
        writer.writerow([
            'Reference virement',
            'Beneficiaire',
            'IBAN',
            'BIC',
            'Montant',
            'Devise',
            'Motif',
            'Date execution'
        ])

        for payment in payments:
            user = payment.user
            config = configs_by_user.get(payment.user_id) if payment.user_id else None

            # Create payment reference for bank
            motif = f"{payment.reference} - {payment.payment_type.value if payment.payment_type else 'Paiement'}"
            if payment.tour:
                motif += f" - {payment.tour.name}"

            writer.writerow([
                payment.reference,
                user.full_name if user else '',
                config.iban if config and config.iban else '',
                config.bic if config and config.bic else '',
                str(payment.amount),
                payment.currency,
                motif,
                datetime.now().strftime('%d/%m/%Y')  # Suggested execution date
            ])

        return output.getvalue()

    @staticmethod
    def get_dashboard_stats() -> Dict[str, Any]:
        """
        Get financial dashboard statistics.

        Returns:
            Dictionary with dashboard stats
        """
        # Payments by status
        pending_count = TeamMemberPayment.query.filter_by(
            status=PaymentStatus.PENDING_APPROVAL
        ).count()

        approved_count = TeamMemberPayment.query.filter_by(
            status=PaymentStatus.APPROVED
        ).count()

        # Total approved amount waiting to be paid
        approved_amount = db.session.query(
            db.func.sum(TeamMemberPayment.amount)
        ).filter_by(status=PaymentStatus.APPROVED).scalar() or Decimal('0')

        # This month's payments
        today = date.today()
        first_of_month = today.replace(day=1)

        month_payments = TeamMemberPayment.query.filter(
            TeamMemberPayment.created_at >= first_of_month
        ).all()

        month_total = sum(p.amount for p in month_payments)

        # Payments by type this month
        month_by_type = {}
        for ptype in PaymentType:
            type_payments = [p for p in month_payments if p.payment_type == ptype]
            if type_payments:
                month_by_type[ptype.value] = {
                    'count': len(type_payments),
                    'total': sum(p.amount for p in type_payments)
                }

        return {
            'pending_approval_count': pending_count,
            'approved_count': approved_count,
            'approved_amount': approved_amount,
            'month_total': month_total,
            'month_payment_count': len(month_payments),
            'month_by_type': month_by_type
        }
