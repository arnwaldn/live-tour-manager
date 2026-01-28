"""
GuestlistEntry model with approval workflow.
"""
from datetime import datetime
import enum

from app.extensions import db


class GuestlistStatus(enum.Enum):
    """Guestlist entry status enumeration."""
    PENDING = 'pending'
    APPROVED = 'approved'
    DENIED = 'denied'
    CHECKED_IN = 'checked_in'
    NO_SHOW = 'no_show'


# Valid status transitions (state machine - G-H3)
GUESTLIST_STATUS_TRANSITIONS = {
    GuestlistStatus.PENDING: [GuestlistStatus.APPROVED, GuestlistStatus.DENIED],
    GuestlistStatus.APPROVED: [GuestlistStatus.CHECKED_IN, GuestlistStatus.NO_SHOW, GuestlistStatus.DENIED],
    GuestlistStatus.DENIED: [GuestlistStatus.PENDING],  # Can be reconsidered
    GuestlistStatus.CHECKED_IN: [],  # Terminal - locked (G-H1)
    GuestlistStatus.NO_SHOW: [],  # Terminal
}


class EntryType(enum.Enum):
    """Guestlist entry type enumeration."""
    GUEST = 'guest'
    ARTIST = 'artist'
    INDUSTRY = 'industry'
    PRESS = 'press'
    VIP = 'vip'
    COMP = 'comp'
    WORKING = 'working'


class GuestlistEntry(db.Model):
    """Guestlist entry model with approval workflow."""

    __tablename__ = 'guestlist_entries'

    id = db.Column(db.Integer, primary_key=True)

    # Tour stop reference
    tour_stop_id = db.Column(
        db.Integer,
        db.ForeignKey('tour_stops.id'),
        nullable=False,
        index=True
    )

    # Guest information
    guest_name = db.Column(db.String(100), nullable=False, index=True)
    guest_email = db.Column(db.String(120), nullable=False)
    guest_phone = db.Column(db.String(30))
    company = db.Column(db.String(100))  # Record label, Press outlet, etc.

    # Entry details
    entry_type = db.Column(
        db.Enum(EntryType),
        default=EntryType.GUEST,
        nullable=False
    )
    plus_ones = db.Column(db.Integer, default=0)
    plus_one_names = db.Column(db.String(255))  # Optional names of plus ones

    # Status and workflow
    status = db.Column(
        db.Enum(GuestlistStatus),
        default=GuestlistStatus.PENDING,
        nullable=False,
        index=True
    )

    # Request details
    requested_by_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )
    request_reason = db.Column(db.Text)

    # Approval details
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    approval_notes = db.Column(db.Text)

    # Lien optionnel vers un utilisateur (pour type ARTIST - membre du groupe)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=True,
        index=True
    )

    # Check-in details
    checked_in_at = db.Column(db.DateTime)
    checked_in_plus_ones = db.Column(db.Integer, default=0)

    # Notes
    notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)  # Internal notes, not shown to guest

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tour_stop = db.relationship('TourStop', back_populates='guestlist_entries')

    requested_by = db.relationship(
        'User',
        back_populates='guestlist_requests',
        foreign_keys=[requested_by_id]
    )

    approved_by = db.relationship(
        'User',
        back_populates='guestlist_approvals',
        foreign_keys=[approved_by_id]
    )

    # Relation vers l'utilisateur lié (pour artistes/membres du groupe)
    user = db.relationship(
        'User',
        back_populates='guestlist_entries_as_artist',
        foreign_keys=[user_id]
    )

    def __repr__(self):
        return f'<GuestlistEntry {self.guest_name} - {self.status.value}>'

    @property
    def total_guests(self):
        """Total number of guests (1 + plus_ones)."""
        return 1 + (self.plus_ones or 0)

    @property
    def is_pending(self):
        """Check if entry is pending approval."""
        return self.status == GuestlistStatus.PENDING

    @property
    def is_approved(self):
        """Check if entry is approved."""
        return self.status == GuestlistStatus.APPROVED

    @property
    def is_checked_in(self):
        """Check if entry is checked in."""
        return self.status == GuestlistStatus.CHECKED_IN

    @property
    def can_check_in(self):
        """Check if this entry can be checked in."""
        return self.status == GuestlistStatus.APPROVED

    def approve(self, user, notes=None):
        """Approve this guestlist entry."""
        self.status = GuestlistStatus.APPROVED
        self.approved_by_id = user.id
        self.approved_at = datetime.utcnow()
        if notes:
            self.approval_notes = notes

    def deny(self, user, notes=None):
        """Deny this guestlist entry."""
        self.status = GuestlistStatus.DENIED
        self.approved_by_id = user.id
        self.approved_at = datetime.utcnow()
        if notes:
            self.approval_notes = notes

    def check_in(self, plus_ones_arrived=None):
        """Check in this guest."""
        if not self.can_check_in:
            raise ValueError("Cannot check in - entry not approved")

        self.status = GuestlistStatus.CHECKED_IN
        self.checked_in_at = datetime.utcnow()
        self.checked_in_plus_ones = plus_ones_arrived if plus_ones_arrived is not None else self.plus_ones

    def mark_no_show(self):
        """Mark this entry as no-show."""
        if self.status == GuestlistStatus.APPROVED:
            self.status = GuestlistStatus.NO_SHOW

    def reset_to_pending(self):
        """Reset entry back to pending status."""
        if self.is_locked:
            raise ValueError("Cannot reset a checked-in entry")
        self.status = GuestlistStatus.PENDING
        self.approved_by_id = None
        self.approved_at = None
        self.approval_notes = None
        self.checked_in_at = None
        self.checked_in_plus_ones = 0

    # ============================================================
    # STATE MACHINE & LOCKING (G-H1, G-H3)
    # ============================================================

    @property
    def is_locked(self):
        """
        Check if entry is locked (checked in or no show).
        Locked entries cannot be modified.
        """
        return self.status in (GuestlistStatus.CHECKED_IN, GuestlistStatus.NO_SHOW)

    @property
    def is_terminal(self):
        """Check if entry is in a terminal state."""
        return self.is_locked

    @property
    def can_edit(self):
        """Check if entry can be edited (not locked)."""
        return not self.is_locked

    def can_transition_to(self, target_status):
        """
        Check if transition to target status is allowed.

        Args:
            target_status: GuestlistStatus enum value

        Returns:
            bool: True if transition is allowed
        """
        allowed = GUESTLIST_STATUS_TRANSITIONS.get(self.status, [])
        return target_status in allowed

    def transition_to(self, target_status):
        """
        Transition to a new status if allowed.

        Args:
            target_status: GuestlistStatus enum value

        Returns:
            bool: True if transition successful

        Raises:
            ValueError: If transition is not allowed
        """
        if not self.can_transition_to(target_status):
            raise ValueError(
                f"Transition invalide: {self.status.value} → {target_status.value}. "
                f"Transitions permises: {[s.value for s in GUESTLIST_STATUS_TRANSITIONS.get(self.status, [])]}"
            )

        self.status = target_status
        self.updated_at = datetime.utcnow()
        return True

    @property
    def allowed_transitions(self):
        """Get list of allowed status transitions from current state."""
        return GUESTLIST_STATUS_TRANSITIONS.get(self.status, [])
