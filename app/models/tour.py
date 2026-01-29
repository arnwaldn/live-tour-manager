"""
Tour model with state machine for status transitions.
"""
from datetime import datetime
import enum

from app.extensions import db


class TourStatus(enum.Enum):
    """Tour status enumeration."""
    DRAFT = 'draft'
    PLANNING = 'planning'
    CONFIRMED = 'confirmed'
    ACTIVE = 'active'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


# Valid status transitions (state machine)
TOUR_STATUS_TRANSITIONS = {
    TourStatus.DRAFT: [TourStatus.PLANNING, TourStatus.CONFIRMED, TourStatus.CANCELLED],
    TourStatus.PLANNING: [TourStatus.CONFIRMED, TourStatus.CANCELLED],
    TourStatus.CONFIRMED: [TourStatus.ACTIVE, TourStatus.CANCELLED],
    TourStatus.ACTIVE: [TourStatus.COMPLETED, TourStatus.CANCELLED],
    TourStatus.COMPLETED: [],  # Terminal state
    TourStatus.CANCELLED: [],  # Terminal state
}


class Tour(db.Model):
    """Tour model representing a tour/series of shows."""

    __tablename__ = 'tours'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(
        db.Enum(TourStatus),
        default=TourStatus.DRAFT,
        nullable=False,
        index=True
    )
    budget = db.Column(db.Numeric(12, 2))
    currency = db.Column(db.String(3), default='EUR')
    notes = db.Column(db.Text)

    # Band relationship
    band_id = db.Column(db.Integer, db.ForeignKey('bands.id'), nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    band = db.relationship('Band', back_populates='tours')

    stops = db.relationship(
        'TourStop',
        back_populates='tour',
        cascade='all, delete-orphan',
        order_by='TourStop.date'
    )

    def __repr__(self):
        return f'<Tour {self.name}>'

    # ============================================================
    # SAFE BAND ACCESS PROPERTIES (handle orphaned tours)
    # ============================================================

    @property
    def band_name(self):
        """Get band name safely (returns placeholder if band is None)."""
        return self.band.name if self.band else '[Groupe supprimé]'

    @property
    def band_id_safe(self):
        """Get band ID safely (returns None if band is None)."""
        return self.band.id if self.band else None

    def band_is_manager(self, user):
        """Check if user is band manager (safely handles None band)."""
        if self.band is None:
            return user.is_manager_or_above()
        return self.band.is_manager(user)

    @property
    def band_manager(self):
        """Get band manager safely (returns None if band is None)."""
        return self.band.manager if self.band else None

    @property
    def duration_days(self):
        """Calculate tour duration in days."""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0

    @property
    def total_shows(self):
        """Get total number of shows on this tour."""
        return len(self.stops)

    @property
    def upcoming_stops(self):
        """Get upcoming tour stops."""
        from datetime import date
        today = date.today()
        return [stop for stop in self.stops if stop.date >= today]

    @property
    def past_stops(self):
        """Get past tour stops."""
        from datetime import date
        today = date.today()
        return [stop for stop in self.stops if stop.date < today]

    @property
    def next_stop(self):
        """Get the next upcoming tour stop."""
        upcoming = self.upcoming_stops
        return upcoming[0] if upcoming else None

    def can_edit(self, user):
        """Check if user can edit this tour."""
        # Defensive: handle case where band relationship is broken
        if self.band is None:
            return user.is_manager_or_above()
        return (self.band.is_manager(user) or
                user.is_manager_or_above())

    def can_view(self, user):
        """Check if user can view this tour."""
        # Defensive: handle case where band relationship is broken
        if self.band is None:
            return user.is_staff_or_above()
        return (self.band.has_access(user) or
                user.is_staff_or_above())

    def duplicate(self, new_name=None, new_start_date=None, include_stops=True):
        """
        Create a copy of this tour with all its stops.

        Args:
            new_name: Optional name for the new tour
            new_start_date: Optional new start date (shifts all stop dates)
            include_stops: Whether to duplicate tour stops (default: True)

        Returns:
            Tour: New tour instance (not yet committed to database)
        """
        from datetime import timedelta
        from app.models.tour_stop import TourStop, TourStopStatus

        # Calculate date offset
        offset = timedelta(0)
        if new_start_date and new_start_date != self.start_date:
            offset = new_start_date - self.start_date

        new_tour = Tour(
            name=new_name or f'{self.name} (Copy)',
            description=self.description,
            start_date=new_start_date or self.start_date,
            end_date=self.end_date + offset if offset else self.end_date,
            status=TourStatus.DRAFT,
            budget=self.budget,
            currency=self.currency,
            notes=self.notes,
            band_id=self.band_id
        )

        # Duplicate tour stops if requested
        if include_stops:
            for stop in self.stops:
                new_stop = TourStop(
                    # Date shifted by offset
                    date=stop.date + offset if offset else stop.date,
                    # Venue and location
                    venue_id=stop.venue_id,
                    location_address=stop.location_address,
                    location_city=stop.location_city,
                    location_country=stop.location_country,
                    location_notes=stop.location_notes,
                    location_latitude=stop.location_latitude,
                    location_longitude=stop.location_longitude,
                    # Times
                    doors_time=stop.doors_time,
                    soundcheck_time=stop.soundcheck_time,
                    set_time=stop.set_time,
                    curfew_time=stop.curfew_time,
                    load_in_time=stop.load_in_time,
                    crew_call_time=stop.crew_call_time,
                    artist_call_time=stop.artist_call_time,
                    meet_greet_time=stop.meet_greet_time,
                    press_time=stop.press_time,
                    catering_time=stop.catering_time,
                    # Event info
                    event_type=stop.event_type,
                    status=TourStopStatus.DRAFT,  # Reset status to DRAFT
                    show_type=stop.show_type,
                    # Financial (copy structure, not actual amounts)
                    guarantee=stop.guarantee,
                    door_deal_percentage=stop.door_deal_percentage,
                    ticket_price=stop.ticket_price,
                    currency=stop.currency,
                    ticketing_fee_percentage=stop.ticketing_fee_percentage,
                    # Show details
                    set_length_minutes=stop.set_length_minutes,
                    age_restriction=stop.age_restriction,
                    notes=stop.notes,
                    internal_notes=stop.internal_notes,
                    # Reset advancement status
                    is_advanced=False,
                )
                new_tour.stops.append(new_stop)

        return new_tour

    # ============================================================
    # STATUS WORKFLOW METHODS (State Machine - T-C3)
    # ============================================================

    def can_transition_to(self, target_status):
        """
        Check if transition to target status is allowed.

        Args:
            target_status: TourStatus enum value

        Returns:
            bool: True if transition is allowed
        """
        allowed = TOUR_STATUS_TRANSITIONS.get(self.status, [])
        return target_status in allowed

    def transition_to(self, target_status):
        """
        Transition to a new status if allowed.

        Args:
            target_status: TourStatus enum value

        Returns:
            bool: True if transition successful

        Raises:
            ValueError: If transition is not allowed
        """
        if not self.can_transition_to(target_status):
            raise ValueError(
                f"Transition invalide: {self.status.value} → {target_status.value}. "
                f"Transitions permises: {[s.value for s in TOUR_STATUS_TRANSITIONS.get(self.status, [])]}"
            )

        self.status = target_status
        self.updated_at = datetime.utcnow()
        return True

    def start_planning(self):
        """Transition DRAFT → PLANNING."""
        return self.transition_to(TourStatus.PLANNING)

    def confirm(self):
        """Transition DRAFT/PLANNING → CONFIRMED."""
        return self.transition_to(TourStatus.CONFIRMED)

    def activate(self):
        """Transition CONFIRMED → ACTIVE."""
        return self.transition_to(TourStatus.ACTIVE)

    def complete(self):
        """Transition ACTIVE → COMPLETED."""
        return self.transition_to(TourStatus.COMPLETED)

    def cancel(self):
        """Cancel tour (from any non-terminal state)."""
        if self.status in (TourStatus.COMPLETED, TourStatus.CANCELLED):
            raise ValueError(f"Cannot cancel tour in {self.status.value} status")
        self.status = TourStatus.CANCELLED
        self.updated_at = datetime.utcnow()
        return True

    @property
    def is_editable(self):
        """Check if tour can be edited (not completed/cancelled)."""
        return self.status not in (TourStatus.COMPLETED, TourStatus.CANCELLED)

    @property
    def is_terminal(self):
        """Check if tour is in a terminal state."""
        return self.status in (TourStatus.COMPLETED, TourStatus.CANCELLED)

    @property
    def allowed_transitions(self):
        """Get list of allowed status transitions from current state."""
        return TOUR_STATUS_TRANSITIONS.get(self.status, [])

    # ============================================================
    # PRE-DELETION VALIDATION (P-H2)
    # ============================================================

    def can_delete(self):
        """
        Check if tour can be safely deleted.
        Prevents orphan payments and data loss.
        """
        blockers = self.get_deletion_blockers()
        return len(blockers) == 0

    def get_deletion_blockers(self):
        """
        Get list of reasons why the tour cannot be deleted.
        Returns empty list if deletion is safe.
        """
        from app.models.payments import TeamMemberPayment, PaymentStatus

        blockers = []

        # Check for pending/non-terminal payments (P-H2)
        pending_statuses = [
            PaymentStatus.DRAFT,
            PaymentStatus.PENDING_APPROVAL,
            PaymentStatus.APPROVED,
            PaymentStatus.SCHEDULED,
            PaymentStatus.PROCESSING
        ]
        pending_payments = TeamMemberPayment.query.filter(
            TeamMemberPayment.tour_id == self.id,
            TeamMemberPayment.status.in_(pending_statuses)
        ).count()

        if pending_payments > 0:
            blockers.append(f"{pending_payments} paiement(s) en attente")

        # Check for active status
        if self.status == TourStatus.ACTIVE:
            blockers.append("Tournée actuellement active")

        return blockers
