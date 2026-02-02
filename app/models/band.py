"""
Band and BandMembership models.
"""
from datetime import datetime

from flask import url_for

from app.extensions import db


class Band(db.Model):
    """Band/Artist model."""

    __tablename__ = 'bands'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    genre = db.Column(db.String(50))
    bio = db.Column(db.Text)
    logo_url = db.Column(db.String(500))  # URL externe (backward compatibility)
    logo_path = db.Column(db.String(255))  # Chemin fichier local uploade
    website = db.Column(db.String(255))
    social_links = db.Column(db.JSON, default=dict)  # {facebook, instagram, twitter, etc.}

    # Manager relationship
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    manager = db.relationship(
        'User',
        back_populates='managed_bands',
        foreign_keys=[manager_id]
    )

    memberships = db.relationship(
        'BandMembership',
        back_populates='band',
        cascade='all, delete-orphan'
    )

    tours = db.relationship(
        'Tour',
        back_populates='band',
        cascade='all, delete-orphan'
    )

    # Standalone events (not part of a tour)
    standalone_events = db.relationship(
        'TourStop',
        back_populates='band',
        foreign_keys='TourStop.band_id',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Band {self.name}>'

    @property
    def members(self):
        """Get all members of the band."""
        return [membership.user for membership in self.memberships]

    @property
    def active_tours(self):
        """Get active tours for the band."""
        from app.models.tour import TourStatus
        return [tour for tour in self.tours if tour.status == TourStatus.ACTIVE]

    @property
    def all_events(self):
        """Get all events (tour stops + standalone events) for the band."""
        events = list(self.standalone_events)
        for tour in self.tours:
            events.extend(tour.stops)
        return sorted(events, key=lambda e: e.date)

    def is_member(self, user):
        """Check if a user is a member of the band."""
        return any(m.user_id == user.id for m in self.memberships)

    def is_manager(self, user):
        """Check if a user is the manager of the band."""
        return self.manager_id == user.id

    def has_access(self, user):
        """Check if user has any access to this band."""
        return self.is_manager(user) or self.is_member(user)

    @property
    def logo_display_url(self):
        """Retourne l'URL d'affichage du logo (uploade ou externe)."""
        if self.logo_path:
            return url_for('bands.serve_logo', filename=self.logo_path)
        return self.logo_url  # Fallback vers URL externe

    def can_delete(self):
        """
        Check if band can be safely deleted.
        Returns True only if there are no active/confirmed tours.
        """
        blockers = self.get_deletion_blockers()
        return len(blockers) == 0

    def get_deletion_blockers(self):
        """
        Get list of reasons why the band cannot be deleted.
        Returns empty list if deletion is safe.
        """
        from app.models.tour import TourStatus
        blockers = []

        # Check for active or confirmed tours
        blocking_statuses = [TourStatus.ACTIVE, TourStatus.CONFIRMED]
        active_tours = [t for t in self.tours if t.status in blocking_statuses]
        if active_tours:
            tour_names = ', '.join([t.name for t in active_tours[:3]])
            if len(active_tours) > 3:
                tour_names += f' (+{len(active_tours) - 3} autres)'
            blockers.append(f"{len(active_tours)} tournée(s) active(s): {tour_names}")

        # Check for pending payments (only PENDING_APPROVAL blocks deletion)
        # APPROVED/SCHEDULED/PAID payments can be cancelled and don't block
        from app.models.payments import TeamMemberPayment, PaymentStatus
        pending_payments = TeamMemberPayment.query.join(
            TeamMemberPayment.tour
        ).filter(
            TeamMemberPayment.tour.has(band_id=self.id),
            TeamMemberPayment.status == PaymentStatus.PENDING_APPROVAL
        ).count()
        if pending_payments > 0:
            blockers.append(f"{pending_payments} paiement(s) en attente d'approbation")

        # Check for future standalone events
        from datetime import date
        future_events = [e for e in self.standalone_events if e.date and e.date >= date.today()]
        if future_events:
            blockers.append(f"{len(future_events)} événement(s) futur(s)")

        return blockers


class BandMembership(db.Model):
    """Band membership linking users to bands."""

    __tablename__ = 'band_memberships'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    band_id = db.Column(db.Integer, db.ForeignKey('bands.id'), nullable=False)
    instrument = db.Column(db.String(50))  # Guitar, Drums, Vocals, etc.
    role_in_band = db.Column(db.String(50))  # Lead singer, Bassist, etc.
    is_active = db.Column(db.Boolean, default=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint to prevent duplicate memberships
    __table_args__ = (
        db.UniqueConstraint('user_id', 'band_id', name='unique_band_membership'),
    )

    # Relationships
    user = db.relationship('User', back_populates='band_memberships')
    band = db.relationship('Band', back_populates='memberships')

    def __repr__(self):
        return f'<BandMembership user={self.user_id} band={self.band_id}>'
