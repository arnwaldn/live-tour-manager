"""
Payment service for GigRoute.
Handles business logic for payments, per diems, and payroll.
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any
import csv
import io

from flask import current_app
from sqlalchemy import func

from app.extensions import db
from app.models.payments import (
    TeamMemberPayment, UserPaymentConfig, PaymentType,
    PaymentStatus, StaffCategory, PaymentFrequency
)
from app.models.tour import Tour
from app.models.tour_stop import TourStop
from app.models.user import User
from app.services.validation_service import ValidationService


class PaymentService:
    """Service for managing payments and payroll calculations."""

    @staticmethod
    def generate_reference() -> str:
        """
        Generate a unique payment reference.

        Format: PAY-YYYY-NNNNN (e.g., PAY-2026-00001)

        Returns:
            Unique payment reference string
        """
        year = datetime.now().year

        # Get the last reference number for this year
        last_payment = TeamMemberPayment.query.filter(
            TeamMemberPayment.reference.like(f'PAY-{year}-%')
        ).order_by(TeamMemberPayment.reference.desc()).first()

        if last_payment and last_payment.reference:
            try:
                last_num = int(last_payment.reference.split('-')[-1])
                next_num = last_num + 1
            except (ValueError, IndexError):
                next_num = 1
        else:
            next_num = 1

        return f"PAY-{year}-{next_num:05d}"

    @staticmethod
    def create_payment(
        user_id: int,
        payment_type: PaymentType,
        amount: Decimal,
        created_by_id: int,
        tour_id: Optional[int] = None,
        tour_stop_id: Optional[int] = None,
        work_date: Optional[date] = None,
        description: Optional[str] = None,
        quantity: Decimal = Decimal('1'),
        unit_rate: Optional[Decimal] = None
    ) -> TeamMemberPayment:
        """
        Create a new payment with validation.

        Args:
            user_id: ID of the user receiving the payment
            payment_type: Type of payment (cachet, per_diem, etc.)
            amount: Total amount
            created_by_id: ID of user creating the payment
            tour_id: Optional tour ID
            tour_stop_id: Optional tour stop ID
            work_date: Optional work date
            description: Optional description
            quantity: Quantity (default 1)
            unit_rate: Optional unit rate

        Returns:
            Created TeamMemberPayment instance

        Raises:
            ValueError: If validation fails
        """
        # Validate user exists
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"Utilisateur {user_id} introuvable")

        # Get user's payment config for category info
        config = UserPaymentConfig.query.get(user_id)

        payment = TeamMemberPayment(
            reference=PaymentService.generate_reference(),
            user_id=user_id,
            tour_id=tour_id,
            tour_stop_id=tour_stop_id,
            payment_type=payment_type,
            description=description,
            amount=amount,
            currency='EUR',
            quantity=quantity,
            unit_rate=unit_rate,
            work_date=work_date,
            status=PaymentStatus.DRAFT,
            created_by_id=created_by_id,
            created_at=datetime.utcnow()
        )

        # Set category from user config if available
        if config:
            payment.staff_category = config.staff_category
            payment.staff_role = config.staff_role
            payment.payment_frequency = config.payment_frequency

        db.session.add(payment)
        db.session.commit()

        return payment

    @staticmethod
    def generate_tour_per_diems(
        tour_id: int,
        per_diem_amount: Decimal,
        created_by_id: int,
        include_travel_days: bool = True,
        include_day_offs: bool = False
    ) -> List[TeamMemberPayment]:
        """
        Generate per diem payments for all eligible tour members.

        Args:
            tour_id: Tour ID to generate per diems for
            per_diem_amount: Amount per day per person
            created_by_id: User creating the payments
            include_travel_days: Include travel days
            include_day_offs: Include day offs

        Returns:
            List of created payments
        """
        Tour.query.get_or_404(tour_id)
        created_payments = []

        # Get all users with payment configs that have per_diem > 0
        configs = UserPaymentConfig.query.filter(
            UserPaymentConfig.per_diem > 0
        ).all()

        eligible_user_ids = [c.user_id for c in configs]

        if not eligible_user_ids:
            return []

        # Get tour stops to calculate dates
        stops = TourStop.query.filter_by(tour_id=tour_id).order_by(TourStop.date).all()

        if not stops:
            return []

        # Calculate all days in tour
        start_date = stops[0].date
        end_date = stops[-1].date

        current_date = start_date
        while current_date <= end_date:
            # Check if this date has a stop
            day_stops = [s for s in stops if s.date == current_date]

            # Determine day type
            is_travel_day = any(s.stop_type.value == 'travel' for s in day_stops)
            is_day_off = any(s.stop_type.value == 'day_off' for s in day_stops)

            # Skip based on settings
            if is_day_off and not include_day_offs:
                current_date += timedelta(days=1)
                continue

            if is_travel_day and not include_travel_days:
                current_date += timedelta(days=1)
                continue

            # Create per diem for each eligible user
            for user_id in eligible_user_ids:
                # Check if per diem already exists for this user/date/tour
                existing = TeamMemberPayment.query.filter_by(
                    user_id=user_id,
                    tour_id=tour_id,
                    work_date=current_date,
                    payment_type=PaymentType.PER_DIEM
                ).first()

                if existing:
                    continue  # Don't duplicate

                # Get stop for description
                stop = day_stops[0] if day_stops else None
                description = f"Per diem - {current_date.strftime('%d/%m/%Y')}"
                if stop and stop.venue:
                    description += f" - {stop.venue.city}"

                payment = PaymentService.create_payment(
                    user_id=user_id,
                    payment_type=PaymentType.PER_DIEM,
                    amount=per_diem_amount,
                    created_by_id=created_by_id,
                    tour_id=tour_id,
                    tour_stop_id=stop.id if stop else None,
                    work_date=current_date,
                    description=description
                )

                created_payments.append(payment)

            current_date += timedelta(days=1)

        return created_payments

    @staticmethod
    def submit_for_approval(payment_id: int) -> TeamMemberPayment:
        """
        Submit a payment for approval.

        Args:
            payment_id: Payment ID to submit

        Returns:
            Updated payment

        Raises:
            ValueError: If payment cannot be submitted
        """
        payment = TeamMemberPayment.query.get_or_404(payment_id)

        if payment.status != PaymentStatus.DRAFT:
            raise ValueError("Seuls les paiements en brouillon peuvent etre soumis")

        payment.status = PaymentStatus.PENDING_APPROVAL
        db.session.commit()

        return payment

    @staticmethod
    def approve_payment(payment_id: int, approved_by_id: int) -> TeamMemberPayment:
        """
        Approve a payment.

        Args:
            payment_id: Payment ID to approve
            approved_by_id: User approving the payment

        Returns:
            Updated payment

        Raises:
            ValueError: If payment cannot be approved or bank details invalid
        """
        payment = TeamMemberPayment.query.get_or_404(payment_id)

        if payment.status != PaymentStatus.PENDING_APPROVAL:
            raise ValueError("Seuls les paiements en attente peuvent etre approuves")

        # Validate bank details before approval (P-C1 fix)
        if payment.user_id:
            config = UserPaymentConfig.query.get(payment.user_id)
            if not config or not config.iban:
                raise ValueError(
                    f"Impossible d'approuver: l'utilisateur {payment.user.full_name} "
                    "n'a pas configure ses coordonnees bancaires (IBAN requis)"
                )

            # Validate IBAN format
            is_valid, error = ValidationService.validate_iban(config.iban)
            if not is_valid:
                raise ValueError(
                    f"Impossible d'approuver: IBAN invalide pour {payment.user.full_name} - {error}"
                )

            # Validate BIC if provided
            if config.bic:
                is_valid, error = ValidationService.validate_bic(config.bic)
                if not is_valid:
                    raise ValueError(
                        f"Impossible d'approuver: BIC invalide pour {payment.user.full_name} - {error}"
                    )

        payment.status = PaymentStatus.APPROVED
        payment.approved_by_id = approved_by_id
        payment.approved_at = datetime.utcnow()
        db.session.commit()

        return payment

    @staticmethod
    def reject_payment(payment_id: int, rejected_by_id: int, reason: str = None) -> TeamMemberPayment:
        """
        Reject a payment and return it to draft status.

        Args:
            payment_id: Payment ID to reject
            rejected_by_id: User rejecting the payment
            reason: Optional rejection reason

        Returns:
            Updated payment
        """
        payment = TeamMemberPayment.query.get_or_404(payment_id)

        if payment.status != PaymentStatus.PENDING_APPROVAL:
            raise ValueError("Seuls les paiements en attente peuvent etre rejetes")

        payment.status = PaymentStatus.DRAFT
        if reason:
            payment.description = f"{payment.description or ''}\n[Rejete: {reason}]"
        db.session.commit()

        return payment

    @staticmethod
    def mark_as_paid(payment_id: int, paid_date: date = None) -> TeamMemberPayment:
        """
        Mark a payment as paid.

        Args:
            payment_id: Payment ID to mark as paid
            paid_date: Optional payment date (defaults to today)

        Returns:
            Updated payment
        """
        payment = TeamMemberPayment.query.get_or_404(payment_id)

        if payment.status not in (PaymentStatus.APPROVED, PaymentStatus.SCHEDULED):
            raise ValueError("Seuls les paiements approuves peuvent etre marques payes")

        payment.status = PaymentStatus.PAID
        payment.paid_date = paid_date or date.today()
        db.session.commit()

        return payment

    @staticmethod
    def get_tour_summary(tour_id: int) -> Dict[str, Any]:
        """
        Get financial summary for a tour.

        Args:
            tour_id: Tour ID

        Returns:
            Dictionary with financial summary data
        """
        payments = TeamMemberPayment.query.filter_by(tour_id=tour_id).all()

        total = sum(p.amount for p in payments)

        # Group by category
        by_category = {}
        for cat in StaffCategory:
            cat_payments = [p for p in payments if p.staff_category == cat]
            by_category[cat.value] = {
                'count': len(cat_payments),
                'total': sum(p.amount for p in cat_payments)
            }

        # Group by type
        by_type = {}
        for ptype in PaymentType:
            type_payments = [p for p in payments if p.payment_type == ptype]
            by_type[ptype.value] = {
                'count': len(type_payments),
                'total': sum(p.amount for p in type_payments)
            }

        # Group by status
        by_status = {}
        for status in PaymentStatus:
            status_payments = [p for p in payments if p.status == status]
            by_status[status.value] = {
                'count': len(status_payments),
                'total': sum(p.amount for p in status_payments)
            }

        return {
            'total_amount': total,
            'payment_count': len(payments),
            'by_category': by_category,
            'by_type': by_type,
            'by_status': by_status
        }

    @staticmethod
    def get_user_payments(user_id: int, start_date: date = None, end_date: date = None) -> List[TeamMemberPayment]:
        """
        Get all payments for a user, optionally filtered by date range.

        Args:
            user_id: User ID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of payments
        """
        query = TeamMemberPayment.query.filter_by(user_id=user_id)

        if start_date:
            query = query.filter(TeamMemberPayment.work_date >= start_date)
        if end_date:
            query = query.filter(TeamMemberPayment.work_date <= end_date)

        return query.order_by(TeamMemberPayment.work_date.desc()).all()

    @staticmethod
    def get_pending_approval_count() -> int:
        """
        Get count of payments pending approval.

        Returns:
            Count of pending payments
        """
        return TeamMemberPayment.query.filter_by(
            status=PaymentStatus.PENDING_APPROVAL
        ).count()

    @staticmethod
    def batch_approve(payment_ids: List[int], approved_by_id: int) -> int:
        """
        Approve multiple payments at once.

        Args:
            payment_ids: List of payment IDs to approve
            approved_by_id: User approving

        Returns:
            Number of payments approved
        """
        count = 0
        for payment_id in payment_ids:
            try:
                PaymentService.approve_payment(payment_id, approved_by_id)
                count += 1
            except ValueError:
                continue

        return count

    @staticmethod
    def export_payments_csv(
        tour_id: Optional[int] = None,
        status: Optional[PaymentStatus] = None,
        include_bank_details: bool = True
    ) -> str:
        """
        Export payments to CSV format for accounting.

        Args:
            tour_id: Optional filter by tour
            status: Optional filter by status
            include_bank_details: Include IBAN/BIC in export

        Returns:
            CSV string
        """
        query = TeamMemberPayment.query

        if tour_id:
            query = query.filter_by(tour_id=tour_id)
        if status:
            query = query.filter_by(status=status)

        payments = query.order_by(TeamMemberPayment.work_date).all()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')

        # Header
        headers = [
            'Reference',
            'Beneficiaire',
            'Type',
            'Description',
            'Date travail',
            'Montant',
            'Devise',
            'Statut',
            'Tournée'
        ]

        if include_bank_details:
            headers.extend(['IBAN', 'BIC', 'Banque'])

        writer.writerow(headers)

        # Data rows
        for payment in payments:
            row = [
                payment.reference,
                payment.user.full_name if payment.user else 'N/A',
                payment.payment_type.value if payment.payment_type else '',
                payment.description or '',
                payment.work_date.strftime('%d/%m/%Y') if payment.work_date else '',
                str(payment.amount),
                payment.currency,
                payment.status.value if payment.status else '',
                payment.tour.name if payment.tour else ''
            ]

            if include_bank_details:
                config = UserPaymentConfig.query.get(payment.user_id) if payment.user_id else None
                row.extend([
                    config.iban if config and config.iban else '',
                    config.bic if config and config.bic else '',
                    config.bank_name if config and config.bank_name else ''
                ])

            writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def calculate_user_totals(user_id: int, tour_id: Optional[int] = None) -> Dict[str, Decimal]:
        """
        Calculate payment totals for a user.

        Args:
            user_id: User ID
            tour_id: Optional tour filter

        Returns:
            Dictionary with totals by payment type
        """
        query = TeamMemberPayment.query.filter_by(user_id=user_id)

        if tour_id:
            query = query.filter_by(tour_id=tour_id)

        payments = query.all()

        totals = {
            'cachets': Decimal('0'),
            'per_diems': Decimal('0'),
            'overtime': Decimal('0'),
            'bonus': Decimal('0'),
            'other': Decimal('0'),
            'total': Decimal('0')
        }

        for payment in payments:
            if payment.payment_type == PaymentType.CACHET:
                totals['cachets'] += payment.amount
            elif payment.payment_type == PaymentType.PER_DIEM:
                totals['per_diems'] += payment.amount
            elif payment.payment_type == PaymentType.OVERTIME:
                totals['overtime'] += payment.amount
            elif payment.payment_type == PaymentType.BONUS:
                totals['bonus'] += payment.amount
            else:
                totals['other'] += payment.amount

            totals['total'] += payment.amount

        return totals
