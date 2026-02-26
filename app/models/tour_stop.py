"""
TourStop model - represents a single show/date on a tour.
"""
from datetime import datetime
import enum

from app.extensions import db


# ============================================================
# LEGACY: Table d'association simple (pour migration progressive)
# ============================================================
# T-H2: ondelete='CASCADE' ensures cleanup when User or TourStop is deleted
tour_stop_members = db.Table(
    'tour_stop_members',
    db.Column('tour_stop_id', db.Integer, db.ForeignKey('tour_stops.id', ondelete='CASCADE'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow)
)


# ============================================================
# V2: Modèle TourStopMember - Assignation avec profession
# ============================================================

class MemberAssignmentStatus(enum.Enum):
    """Statut d'assignation d'un membre à un événement."""
    ASSIGNED = 'assigned'       # Assigné par le manager
    CONFIRMED = 'confirmed'     # Confirmé par le membre
    DECLINED = 'declined'       # Refusé par le membre
    TENTATIVE = 'tentative'     # Provisoire / à confirmer
    CANCELED = 'canceled'       # Annulé


class TourStopMember(db.Model):
    """
    Modèle d'assignation d'un membre à un événement (v2.0).

    Remplace la table d'association simple pour permettre:
    - Spécifier la profession/rôle pour cet événement
    - Gérer le statut (assigné, confirmé, refusé)
    - Définir des horaires spécifiques (call time)
    - Ajouter des notes d'assignation
    - Tracer qui a fait l'assignation
    """

    __tablename__ = 'tour_stop_members_v2'

    id = db.Column(db.Integer, primary_key=True)

    # Références principales
    tour_stop_id = db.Column(
        db.Integer,
        db.ForeignKey('tour_stops.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # En quelle qualité (profession) ce membre est-il assigné?
    # Si null, utiliser la profession principale de l'utilisateur
    profession_id = db.Column(
        db.Integer,
        db.ForeignKey('professions.id', ondelete='SET NULL'),
        nullable=True
    )

    # Statut de l'assignation
    status = db.Column(
        db.Enum(MemberAssignmentStatus, values_callable=lambda x: [e.value for e in x]),
        default=MemberAssignmentStatus.ASSIGNED,
        nullable=False,
        index=True
    )

    # Horaires spécifiques pour ce membre (override des horaires globaux)
    call_time = db.Column(db.Time, nullable=True)  # Heure de convocation spécifique

    # Planning horaire complet (v2.1) - colonnes ajoutées par migration
    work_start = db.Column(db.Time, nullable=True)  # Début de travail
    work_end = db.Column(db.Time, nullable=True)    # Fin de travail
    break_start = db.Column(db.Time, nullable=True) # Début pause
    break_end = db.Column(db.Time, nullable=True)   # Fin pause
    meal_time = db.Column(db.Time, nullable=True)   # Heure repas

    # Notes d'assignation
    notes = db.Column(db.Text, nullable=True)

    # Audit / Traçabilité
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    assigned_by_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )

    # Timestamp de confirmation/refus
    responded_at = db.Column(db.DateTime, nullable=True)

    # Timestamps standards
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ============ RELATIONSHIPS ============
    tour_stop = db.relationship(
        'TourStop',
        back_populates='member_assignments',
        foreign_keys=[tour_stop_id]
    )

    user = db.relationship(
        'User',
        back_populates='tour_stop_assignments',
        foreign_keys=[user_id]
    )

    profession = db.relationship(
        'Profession',
        foreign_keys=[profession_id]
    )

    assigned_by = db.relationship(
        'User',
        foreign_keys=[assigned_by_id]
    )

    # Contrainte d'unicité: un user ne peut être assigné qu'une fois par tour_stop
    __table_args__ = (
        db.UniqueConstraint('tour_stop_id', 'user_id', name='uq_tour_stop_user'),
    )

    def __repr__(self):
        return f'<TourStopMember {self.user_id} @ TourStop {self.tour_stop_id} [{self.status.value}]>'

    # ============ PROPERTIES ============

    @property
    def effective_profession(self):
        """
        Retourne la profession effective pour cette assignation.
        Si profession_id est défini, utilise celle-ci, sinon la profession principale de l'user.
        """
        if self.profession:
            return self.profession
        # Fallback: profession principale de l'utilisateur
        if self.user and self.user.professions:
            return self.user.professions[0] if self.user.professions else None
        return None

    @property
    def effective_profession_name(self):
        """Nom de la profession effective."""
        prof = self.effective_profession
        return prof.name_fr if prof else "Non défini"

    @property
    def effective_call_time(self):
        """
        Retourne l'heure de convocation effective.
        Si call_time spécifique, utilise celle-ci, sinon l'heure globale du tour_stop.
        """
        if self.call_time:
            return self.call_time
        if self.tour_stop:
            return self.tour_stop.crew_call_time
        return None

    @property
    def is_confirmed(self):
        """Vérifie si l'assignation est confirmée."""
        return self.status == MemberAssignmentStatus.CONFIRMED

    @property
    def is_pending(self):
        """Vérifie si l'assignation attend une réponse."""
        return self.status in (MemberAssignmentStatus.ASSIGNED, MemberAssignmentStatus.TENTATIVE)

    @property
    def status_label(self):
        """Label français du statut."""
        labels = {
            MemberAssignmentStatus.ASSIGNED: 'Assigné',
            MemberAssignmentStatus.CONFIRMED: 'Confirmé',
            MemberAssignmentStatus.DECLINED: 'Refusé',
            MemberAssignmentStatus.TENTATIVE: 'Provisoire',
            MemberAssignmentStatus.CANCELED: 'Annulé',
        }
        return labels.get(self.status, self.status.value)

    @property
    def status_color(self):
        """Couleur Bootstrap du statut."""
        colors = {
            MemberAssignmentStatus.ASSIGNED: 'info',
            MemberAssignmentStatus.CONFIRMED: 'success',
            MemberAssignmentStatus.DECLINED: 'danger',
            MemberAssignmentStatus.TENTATIVE: 'warning',
            MemberAssignmentStatus.CANCELED: 'secondary',
        }
        return colors.get(self.status, 'secondary')

    @property
    def schedule_display(self):
        """Affichage formaté du planning."""
        parts = []
        if self.work_start and self.work_end:
            parts.append(f"{self.work_start.strftime('%H:%M')}-{self.work_end.strftime('%H:%M')}")
        if self.meal_time:
            parts.append(f"Repas: {self.meal_time.strftime('%H:%M')}")
        if self.break_start and self.break_end:
            parts.append(f"Pause: {self.break_start.strftime('%H:%M')}-{self.break_end.strftime('%H:%M')}")
        return " | ".join(parts) if parts else "Non planifié"

    @property
    def has_schedule(self):
        """Vérifie si le membre a un planning défini."""
        return self.work_start is not None or self.work_end is not None

    @property
    def work_duration_hours(self):
        """Calcule la durée de travail en heures."""
        if self.work_start and self.work_end:
            from datetime import datetime, timedelta
            start = datetime.combine(datetime.today(), self.work_start)
            end = datetime.combine(datetime.today(), self.work_end)
            if end < start:
                end += timedelta(days=1)
            duration = (end - start).total_seconds() / 3600
            if self.break_start and self.break_end:
                break_start = datetime.combine(datetime.today(), self.break_start)
                break_end = datetime.combine(datetime.today(), self.break_end)
                pause_duration = (break_end - break_start).total_seconds() / 3600
                duration -= pause_duration
            return round(duration, 1)
        return 0

    # ============ METHODS ============

    def confirm(self):
        """Confirmer l'assignation."""
        if self.status in (MemberAssignmentStatus.ASSIGNED, MemberAssignmentStatus.TENTATIVE):
            self.status = MemberAssignmentStatus.CONFIRMED
            self.responded_at = datetime.utcnow()
            return True
        return False

    def decline(self):
        """Refuser l'assignation."""
        if self.status in (MemberAssignmentStatus.ASSIGNED, MemberAssignmentStatus.TENTATIVE):
            self.status = MemberAssignmentStatus.DECLINED
            self.responded_at = datetime.utcnow()
            return True
        return False

    def cancel(self):
        """Annuler l'assignation."""
        if self.status != MemberAssignmentStatus.CANCELED:
            self.status = MemberAssignmentStatus.CANCELED
            return True
        return False

    def to_dict(self):
        """Sérialisation pour API."""
        return {
            'id': self.id,
            'tour_stop_id': self.tour_stop_id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else None,
            'profession_id': self.profession_id,
            'profession_name': self.effective_profession_name,
            'status': self.status.value,
            'status_label': self.status_label,
            'status_color': self.status_color,
            'call_time': self.call_time.isoformat() if self.call_time else None,
            'effective_call_time': self.effective_call_time.isoformat() if self.effective_call_time else None,
            'work_start': self.work_start.isoformat() if self.work_start else None,
            'work_end': self.work_end.isoformat() if self.work_end else None,
            'break_start': self.break_start.isoformat() if self.break_start else None,
            'break_end': self.break_end.isoformat() if self.break_end else None,
            'meal_time': self.meal_time.isoformat() if self.meal_time else None,
            'schedule_display': self.schedule_display,
            'notes': self.notes,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'assigned_by_id': self.assigned_by_id,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None,
        }


class TourStopStatus(enum.Enum):
    """Tour stop status enumeration (Pattern Dolibarr - workflow professionnel)."""
    DRAFT = 'draft'           # Date placeholder, pas encore en négociation
    PENDING = 'pending'       # En négociation avec venue/promoteur
    CONFIRMED = 'confirmed'   # Contrat signé, date confirmée
    PERFORMED = 'performed'   # Concert réalisé
    SETTLED = 'settled'       # Settlement financier effectué
    CANCELED = 'canceled'     # Annulé
    RESCHEDULED = 'rescheduled'  # Concert reporté à nouvelle date


class EventType(enum.Enum):
    """Types d'événements sur une tournée (inspiré Master Tour, TourManagement.com)."""
    SHOW = 'show'              # Concert/Performance
    DAY_OFF = 'day_off'        # Jour de repos
    TRAVEL = 'travel'          # Jour de voyage uniquement
    STUDIO = 'studio'          # Session studio/enregistrement
    PROMO = 'promo'            # Promo/Press day
    REHEARSAL = 'rehearsal'    # Répétition
    PRESS = 'press'            # Interview/Média
    MEET_GREET = 'meet_greet'  # Rencontre fans
    PHOTO_VIDEO = 'photo_video'  # Shooting photo/vidéo
    OTHER = 'other'            # Autre


class TourStop(db.Model):
    """Tour stop model - a single show on a tour or standalone event."""

    __tablename__ = 'tour_stops'

    # C3: CHECK constraint - TourStop doit avoir soit tour_id soit band_id
    __table_args__ = (
        db.CheckConstraint(
            'tour_id IS NOT NULL OR band_id IS NOT NULL',
            name='check_tour_or_band_required'
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    # Tour and Venue references
    # tour_id is nullable to support standalone events (not linked to a specific tour)
    tour_id = db.Column(db.Integer, db.ForeignKey('tours.id'), nullable=True)
    # band_id is for standalone events that are not part of a tour
    band_id = db.Column(db.Integer, db.ForeignKey('bands.id'), nullable=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'), nullable=True)  # Nullable pour DAY_OFF, TRAVEL

    # Location directe (alternative à venue_id pour événements simples)
    location_address = db.Column(db.String(255))
    location_city = db.Column(db.String(100))
    location_country = db.Column(db.String(100))
    location_notes = db.Column(db.Text)
    # Coordonnées GPS pour affichage carte (géocodées automatiquement)
    location_latitude = db.Column(db.Numeric(10, 7))
    location_longitude = db.Column(db.Numeric(10, 7))

    # Date and times
    date = db.Column(db.Date, nullable=False, index=True)
    doors_time = db.Column(db.Time)
    soundcheck_time = db.Column(db.Time)
    set_time = db.Column(db.Time)
    curfew_time = db.Column(db.Time)

    # Call times / Horaires d'appel (standards industrie - Master Tour, High Road)
    load_in_time = db.Column(db.Time)           # Heure de chargement
    crew_call_time = db.Column(db.Time)         # Appel équipe technique
    artist_call_time = db.Column(db.Time)       # Appel artistes
    meet_greet_time = db.Column(db.Time)        # Heure meet & greet
    press_time = db.Column(db.Time)             # Heure presse/interviews
    catering_time = db.Column(db.Time)          # Heure repas

    # Event type (inspiré TourManagement.com)
    event_type = db.Column(
        db.Enum(EventType, values_callable=lambda x: [e.value for e in x]),
        default=EventType.SHOW,
        nullable=False,
        index=True
    )

    # Status and type
    status = db.Column(
        db.Enum(TourStopStatus, values_callable=lambda x: [e.value for e in x]),
        default=TourStopStatus.DRAFT,
        nullable=False,
        index=True
    )
    show_type = db.Column(db.String(50))  # Headline, Support, Festival, Private, etc.

    # Financial
    guarantee = db.Column(db.Numeric(10, 2))
    venue_rental_cost = db.Column(db.Numeric(10, 2))  # Prix location salle
    door_deal_percentage = db.Column(db.Numeric(5, 2))
    ticket_price = db.Column(db.Numeric(8, 2))
    ticket_url = db.Column(db.String(255))  # URL billetterie
    sold_tickets = db.Column(db.Integer, default=0)
    currency = db.Column(db.String(3), default='EUR')
    # R1: Frais de billetterie (standard industrie: 2-10%)
    ticketing_fee_percentage = db.Column(db.Numeric(5, 2), default=5.0)

    # Show details
    set_length_minutes = db.Column(db.Integer)
    age_restriction = db.Column(db.String(20))  # All ages, 18+, 21+
    notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)  # Private notes for band/management

    # Advancement status (legacy fields kept for backward compatibility)
    is_advanced = db.Column(db.Boolean, default=False)
    advanced_at = db.Column(db.DateTime)
    advance_notes = db.Column(db.Text)

    # Advancing module (Phase 7a)
    advancing_status = db.Column(
        db.String(20),
        default='not_started',
        nullable=False,
        index=True
    )
    advancing_deadline = db.Column(db.Date, nullable=True)

    # Production specs (stage/technical)
    stage_width = db.Column(db.Float, nullable=True)
    stage_depth = db.Column(db.Float, nullable=True)
    stage_height = db.Column(db.Float, nullable=True)
    power_available = db.Column(db.String(100), nullable=True)
    rigging_points = db.Column(db.Integer, nullable=True)

    # Venue contact for advancing
    venue_contact_name = db.Column(db.String(100), nullable=True)
    venue_contact_email = db.Column(db.String(255), nullable=True)
    venue_contact_phone = db.Column(db.String(50), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Status workflow timestamps (Pattern Dolibarr)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    performed_at = db.Column(db.DateTime, nullable=True)
    settled_at = db.Column(db.DateTime, nullable=True)
    canceled_at = db.Column(db.DateTime, nullable=True)

    # Reschedule tracking (dual date display)
    original_date = db.Column(db.Date, nullable=True)  # Date initiale si reporté
    rescheduled_from_id = db.Column(db.Integer, db.ForeignKey('tour_stops.id'), nullable=True)
    reschedule_reason = db.Column(db.String(255), nullable=True)  # Raison du report
    reschedule_count = db.Column(db.Integer, default=0)  # Nombre de reports
    rescheduled_at = db.Column(db.DateTime, nullable=True)  # Timestamp du report

    # Relationships
    tour = db.relationship('Tour', back_populates='stops')
    band = db.relationship('Band', back_populates='standalone_events', foreign_keys=[band_id])
    venue = db.relationship('Venue', back_populates='tour_stops')

    guestlist_entries = db.relationship(
        'GuestlistEntry',
        back_populates='tour_stop',
        cascade='all, delete-orphan'
    )

    logistics = db.relationship(
        'LogisticsInfo',
        back_populates='tour_stop',
        cascade='all, delete-orphan'
    )

    local_contacts = db.relationship(
        'LocalContact',
        back_populates='tour_stop',
        cascade='all, delete-orphan'
    )

    # R4: Dépenses promoteur (pour calcul Split Point)
    promotor_expenses = db.relationship(
        'PromotorExpenses',
        back_populates='tour_stop',
        uselist=False,  # One-to-one relationship
        cascade='all, delete-orphan'
    )

    # Membres assignés à cet événement (pour filtrage calendrier global)
    assigned_members = db.relationship(
        'User',
        secondary=tour_stop_members,
        backref=db.backref('assigned_tour_stops', lazy='dynamic')
    )

    # Self-reference for reschedule tracking
    rescheduled_from = db.relationship(
        'TourStop',
        remote_side='TourStop.id',
        foreign_keys=[rescheduled_from_id],
        backref=db.backref('rescheduled_to_stop', uselist=False)
    )

    # Lineup/Programming slots (artistes programmés)
    lineup_slots = db.relationship(
        'LineupSlot',
        back_populates='tour_stop',
        cascade='all, delete-orphan',
        order_by='LineupSlot.order'
    )

    # V2: Assignations avec profession (remplace assigned_members progressivement)
    member_assignments = db.relationship(
        'TourStopMember',
        back_populates='tour_stop',
        cascade='all, delete-orphan',
        foreign_keys='TourStopMember.tour_stop_id',
        lazy='dynamic'
    )

    # Advancing module (Phase 7a)
    checklist_items = db.relationship(
        'AdvancingChecklistItem',
        back_populates='tour_stop',
        cascade='all, delete-orphan',
        order_by='AdvancingChecklistItem.sort_order'
    )
    rider_requirements = db.relationship(
        'RiderRequirement',
        back_populates='tour_stop',
        cascade='all, delete-orphan',
        order_by='RiderRequirement.sort_order'
    )
    advancing_contacts = db.relationship(
        'AdvancingContact',
        back_populates='tour_stop',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        venue_name = self.venue.name if self.venue else 'N/A'
        return f'<TourStop {self.date} [{self.event_type.value}] @ {venue_name}>'

    @property
    def is_standalone(self):
        """Check if this is a standalone event (not part of a tour)."""
        return self.tour_id is None

    @property
    def associated_band(self):
        """Get the band associated with this event (from tour or direct)."""
        if self.tour:
            return self.tour.band
        return self.band

    # ============================================================
    # SAFE VENUE ACCESS PROPERTIES (handle deleted venues)
    # ============================================================

    @property
    def venue_name(self):
        """Get venue name safely (returns placeholder if venue is None)."""
        return self.venue.name if self.venue else 'Lieu TBD'

    @property
    def venue_city(self):
        """Get venue city safely (returns location_city or placeholder)."""
        if self.venue:
            return self.venue.city
        return self.location_city or 'Ville à définir'

    @property
    def venue_id_safe(self):
        """Get venue ID safely (returns None if venue is None)."""
        return self.venue.id if self.venue else None

    @property
    def associated_band_id(self):
        """Get the band ID associated with this event."""
        if self.tour:
            return self.tour.band_id
        return self.band_id

    # Event type display info (pour calendrier et templates)
    EVENT_TYPE_COLORS = {
        EventType.SHOW: '#198754',        # Vert
        EventType.DAY_OFF: '#6c757d',     # Gris
        EventType.TRAVEL: '#0d6efd',      # Bleu
        EventType.STUDIO: '#6f42c1',      # Violet
        EventType.PROMO: '#fd7e14',       # Orange
        EventType.REHEARSAL: '#ffc107',   # Jaune
        EventType.PRESS: '#d63384',       # Rose
        EventType.MEET_GREET: '#20c997',  # Teal
        EventType.PHOTO_VIDEO: '#e91e63', # Pink
        EventType.OTHER: '#6c757d',       # Gris
    }

    EVENT_TYPE_ICONS = {
        EventType.SHOW: 'bi-music-note-beamed',
        EventType.DAY_OFF: 'bi-moon',
        EventType.TRAVEL: 'bi-airplane',
        EventType.STUDIO: 'bi-soundwave',
        EventType.PROMO: 'bi-megaphone',
        EventType.REHEARSAL: 'bi-arrow-repeat',
        EventType.PRESS: 'bi-newspaper',
        EventType.MEET_GREET: 'bi-people',
        EventType.PHOTO_VIDEO: 'bi-camera',
        EventType.OTHER: 'bi-question-circle',
    }

    EVENT_TYPE_LABELS = {
        EventType.SHOW: 'Concert',
        EventType.DAY_OFF: 'Jour off',
        EventType.TRAVEL: 'Voyage',
        EventType.STUDIO: 'Studio',
        EventType.PROMO: 'Promo',
        EventType.REHEARSAL: 'Répétition',
        EventType.PRESS: 'Presse',
        EventType.MEET_GREET: 'Meet & Greet',
        EventType.PHOTO_VIDEO: 'Photo/Vidéo',
        EventType.OTHER: 'Autre',
    }

    @property
    def event_color(self):
        """Get the color for this event type."""
        return self.EVENT_TYPE_COLORS.get(self.event_type, '#6c757d')

    @property
    def event_icon(self):
        """Get the Bootstrap icon class for this event type."""
        return self.EVENT_TYPE_ICONS.get(self.event_type, 'bi-calendar')

    @property
    def event_label(self):
        """Get the French label for this event type."""
        return self.EVENT_TYPE_LABELS.get(self.event_type, 'Autre')

    @property
    def requires_venue(self):
        """Check if this event type requires a venue."""
        return self.event_type in (EventType.SHOW, EventType.STUDIO, EventType.REHEARSAL, EventType.MEET_GREET)

    @property
    def display_location(self):
        """Get display location (venue or direct location)."""
        if self.venue:
            return f"{self.venue.name}, {self.venue.city}"
        elif self.location_city:
            parts = [self.location_address, self.location_city, self.location_country]
            return ", ".join(filter(None, parts))
        return None

    @property
    def has_coordinates(self):
        """Check if this stop has GPS coordinates (from venue or direct location)."""
        if self.venue and self.venue.has_coordinates:
            return True
        if self.location_latitude is not None and self.location_longitude is not None:
            return True
        return False

    @property
    def get_coordinates(self):
        """Get GPS coordinates (lat, lon) from venue or direct location."""
        if self.venue and self.venue.has_coordinates:
            return (float(self.venue.latitude), float(self.venue.longitude))
        if self.location_latitude is not None and self.location_longitude is not None:
            return (float(self.location_latitude), float(self.location_longitude))
        return None

    @property
    def map_location_name(self):
        """Get the location name for map display."""
        if self.venue:
            return self.venue.name
        elif self.location_address or self.location_city:
            parts = [self.location_address, self.location_city]
            return ", ".join(filter(None, parts)) or "Lieu externe"
        return "Lieu non défini"

    @property
    def map_location_city(self):
        """Get the city for map display."""
        if self.venue:
            return self.venue.city
        return self.location_city or ""

    @property
    def map_location_country(self):
        """Get the country for map display."""
        if self.venue:
            return self.venue.country
        return self.location_country or ""

    @property
    def advancing_completion(self):
        """Calculate advancing checklist completion percentage."""
        items = self.checklist_items
        if not items:
            return 0
        completed = sum(1 for item in items if item.is_completed)
        return int((completed / len(items)) * 100)

    @property
    def advancing_status_label(self):
        """French label for advancing status."""
        labels = {
            'not_started': 'Non démarré',
            'in_progress': 'En cours',
            'waiting_venue': 'Attente salle',
            'completed': 'Terminé',
            'issues': 'Problèmes',
        }
        return labels.get(self.advancing_status, self.advancing_status)

    @property
    def advancing_status_color(self):
        """Bootstrap color for advancing status."""
        colors = {
            'not_started': 'secondary',
            'in_progress': 'primary',
            'waiting_venue': 'warning',
            'completed': 'success',
            'issues': 'danger',
        }
        return colors.get(self.advancing_status, 'secondary')

    @property
    def is_past(self):
        """Check if this stop is in the past."""
        from datetime import date
        return self.date < date.today()

    @property
    def is_today(self):
        """Check if this stop is today."""
        from datetime import date
        return self.date == date.today()

    @property
    def is_upcoming(self):
        """Check if this stop is in the future."""
        from datetime import date
        return self.date > date.today()

    @property
    def is_rescheduled(self):
        """Check if this concert has been rescheduled."""
        return self.original_date is not None

    @property
    def rescheduled_to(self):
        """Get the new TourStop if this concert was rescheduled."""
        return self.rescheduled_to_stop

    @property
    def guestlist_count(self):
        """Get total number of guests on the guestlist (including plus ones)."""
        from app.models.guestlist import GuestlistStatus
        approved = [e for e in self.guestlist_entries
                   if e.status in (GuestlistStatus.APPROVED, GuestlistStatus.CHECKED_IN)]
        return sum(1 + (e.plus_ones or 0) for e in approved)

    @property
    def checked_in_count(self):
        """Get number of checked-in guests."""
        from app.models.guestlist import GuestlistStatus
        checked_in = [e for e in self.guestlist_entries
                     if e.status == GuestlistStatus.CHECKED_IN]
        return sum(1 + (e.plus_ones or 0) for e in checked_in)

    @property
    def pending_guestlist_count(self):
        """Get number of pending guestlist requests."""
        from app.models.guestlist import GuestlistStatus
        return len([e for e in self.guestlist_entries
                   if e.status == GuestlistStatus.PENDING])

    def can_edit(self, user):
        """Check if user can edit this tour stop."""
        if self.tour:
            return self.tour.can_edit(user)
        # Standalone event: check band permissions
        if self.band:
            return self.band.is_manager(user)
        return False

    def can_view(self, user):
        """Check if user can view this tour stop."""
        if self.tour:
            return (self.tour.can_view(user) or
                    user.is_staff_or_above())
        # Standalone event: check band membership
        if self.band:
            return self.band.is_member(user) or user.is_staff_or_above()
        return user.is_staff_or_above()

    def can_manage_guestlist(self, user):
        """Check if user can manage guestlist for this stop."""
        if self.tour:
            return (self.tour.can_edit(user) or
                    user.is_staff_or_above())
        # Standalone event: check band permissions
        if self.band:
            return self.band.is_manager(user) or user.is_staff_or_above()
        return user.is_staff_or_above()

    def can_check_in_guests(self, user):
        """Check if user can check in guests at this stop."""
        return (self.can_manage_guestlist(user) or
                user.is_staff_or_above())

    # ============================================================
    # STATUS WORKFLOW METHODS (Pattern Dolibarr)
    # ============================================================

    def confirm(self):
        """Transition DRAFT/PENDING → CONFIRMED.

        Returns:
            bool: True if transition successful, False otherwise.
        """
        if self.status in [TourStopStatus.DRAFT, TourStopStatus.PENDING]:
            self.status = TourStopStatus.CONFIRMED
            self.confirmed_at = datetime.utcnow()
            return True
        return False

    def perform(self):
        """Transition CONFIRMED → PERFORMED (concert réalisé).

        Returns:
            bool: True if transition successful, False otherwise.
        """
        if self.status == TourStopStatus.CONFIRMED:
            self.status = TourStopStatus.PERFORMED
            self.performed_at = datetime.utcnow()
            return True
        return False

    def settle(self):
        """Transition PERFORMED → SETTLED (settlement financier effectué).

        Returns:
            bool: True if transition successful, False otherwise.
        """
        if self.status == TourStopStatus.PERFORMED:
            self.status = TourStopStatus.SETTLED
            self.settled_at = datetime.utcnow()
            return True
        return False

    def cancel(self):
        """Annuler le TourStop (depuis n'importe quel état sauf SETTLED).

        Returns:
            bool: True if cancellation successful, False otherwise.
        """
        if self.status != TourStopStatus.SETTLED:
            self.status = TourStopStatus.CANCELED
            self.canceled_at = datetime.utcnow()
            return True
        return False

    def can_transition_to(self, target_status):
        """Check if transition to target status is allowed.

        Args:
            target_status: TourStopStatus enum value

        Returns:
            bool: True if transition is allowed.
        """
        allowed_transitions = {
            TourStopStatus.DRAFT: [TourStopStatus.PENDING, TourStopStatus.CONFIRMED, TourStopStatus.CANCELED, TourStopStatus.RESCHEDULED],
            TourStopStatus.PENDING: [TourStopStatus.CONFIRMED, TourStopStatus.CANCELED, TourStopStatus.RESCHEDULED],
            TourStopStatus.CONFIRMED: [TourStopStatus.PERFORMED, TourStopStatus.CANCELED, TourStopStatus.RESCHEDULED],
            TourStopStatus.PERFORMED: [TourStopStatus.SETTLED, TourStopStatus.CANCELED],
            TourStopStatus.SETTLED: [],  # Terminal state
            TourStopStatus.CANCELED: [],  # Terminal state
            TourStopStatus.RESCHEDULED: [],  # Terminal state - original entry stays frozen
        }
        return target_status in allowed_transitions.get(self.status, [])

    def reschedule(self, new_date, reason=None):
        """Reporter ce concert à une nouvelle date.

        Cette méthode:
        1. Sauvegarde la date originale (si pas déjà reporté)
        2. Met à jour la date vers la nouvelle date
        3. Incrémente le compteur de reports
        4. Enregistre la raison et le timestamp

        Args:
            new_date: La nouvelle date du concert
            reason: Raison du report (optionnel)

        Returns:
            bool: True si le report a réussi, False sinon.
        """
        if not self.can_transition_to(TourStopStatus.RESCHEDULED):
            return False

        # Sauvegarder la date originale (première fois seulement)
        if not self.original_date:
            self.original_date = self.date

        # Mettre à jour vers la nouvelle date
        self.date = new_date
        self.reschedule_reason = reason
        self.reschedule_count += 1
        self.rescheduled_at = datetime.utcnow()
        # Note: On garde le statut actuel (CONFIRMED, etc.) pour que
        # le concert reporté soit toujours actif dans le calendrier
        return True
