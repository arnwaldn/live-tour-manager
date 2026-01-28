"""
LogisticsInfo and LocalContact models.
"""
from datetime import datetime
import enum

from app.extensions import db


class LogisticsType(enum.Enum):
    """Logistics type enumeration."""
    FLIGHT = 'flight'
    TRAIN = 'train'
    BUS = 'bus'
    FERRY = 'ferry'  # Ferry/boat transport
    RENTAL_CAR = 'rental_car'
    TAXI = 'taxi'
    GROUND_TRANSPORT = 'ground_transport'  # Generic ground transport
    HOTEL = 'hotel'
    APARTMENT = 'apartment'
    RENTAL = 'rental'  # Equipment/vehicle rental
    EQUIPMENT = 'equipment'  # Equipment rental/logistics
    BACKLINE = 'backline'
    CATERING = 'catering'
    MEAL = 'meal'  # Specific meal arrangements
    PARKING = 'parking'  # Parking arrangements
    VISA = 'visa'  # Visa/travel documents
    OTHER = 'other'


class LogisticsStatus(enum.Enum):
    """Logistics booking status enumeration."""
    PENDING = 'pending'      # En attente
    BOOKED = 'booked'        # Réservé
    CONFIRMED = 'confirmed'  # Confirmé
    COMPLETED = 'completed'  # Terminé
    CANCELLED = 'cancelled'  # Annulé


class LogisticsInfo(db.Model):
    """Logistics information for a tour stop."""

    __tablename__ = 'logistics_info'

    id = db.Column(db.Integer, primary_key=True)

    # Tour stop reference
    tour_stop_id = db.Column(
        db.Integer,
        db.ForeignKey('tour_stops.id'),
        nullable=False,
        index=True
    )

    # Logistics type and provider
    logistics_type = db.Column(
        db.Enum(LogisticsType),
        nullable=False
    )
    provider = db.Column(db.String(100))  # Hotel name, Airline, Car rental, etc.
    confirmation_number = db.Column(db.String(100))

    # Timing
    start_datetime = db.Column(db.DateTime)
    end_datetime = db.Column(db.DateTime)

    # Status
    status = db.Column(
        db.Enum(LogisticsStatus),
        default=LogisticsStatus.PENDING
    )

    # Location (for hotels, pickups, etc.)
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))

    # GPS Coordinates (for map display)
    latitude = db.Column(db.Numeric(10, 7), nullable=True)
    longitude = db.Column(db.Numeric(10, 7), nullable=True)

    # Cost
    cost = db.Column(db.Numeric(10, 2))
    currency = db.Column(db.String(3), default='EUR')
    is_paid = db.Column(db.Boolean, default=False)
    paid_by = db.Column(db.String(100))  # Who paid: Band, Promoter, etc.

    # Flight specific
    flight_number = db.Column(db.String(20))
    departure_airport = db.Column(db.String(10))
    arrival_airport = db.Column(db.String(10))
    departure_terminal = db.Column(db.String(20))
    arrival_terminal = db.Column(db.String(20))
    # GPS for airports (auto-filled from known airports)
    departure_lat = db.Column(db.Numeric(10, 7), nullable=True)
    departure_lng = db.Column(db.Numeric(10, 7), nullable=True)
    arrival_lat = db.Column(db.Numeric(10, 7), nullable=True)
    arrival_lng = db.Column(db.Numeric(10, 7), nullable=True)

    # Hotel specific
    room_type = db.Column(db.String(50))
    number_of_rooms = db.Column(db.Integer, default=1)
    breakfast_included = db.Column(db.Boolean, default=False)
    check_in_time = db.Column(db.Time, nullable=True)
    check_out_time = db.Column(db.Time, nullable=True)

    # Ground transport specific
    pickup_location = db.Column(db.String(255))
    dropoff_location = db.Column(db.String(255))
    vehicle_type = db.Column(db.String(50))  # Minivan, Bus, Sedan, etc.
    driver_name = db.Column(db.String(100))
    driver_phone = db.Column(db.String(30))

    # Contact
    contact_name = db.Column(db.String(100))
    contact_phone = db.Column(db.String(30))
    contact_email = db.Column(db.String(120))

    # Notes and additional details
    details = db.Column(db.JSON, default=dict)
    notes = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tour_stop = db.relationship('TourStop', back_populates='logistics')

    def __repr__(self):
        return f'<LogisticsInfo {self.logistics_type.value} - {self.provider}>'

    @property
    def is_transport(self):
        """Check if this is a transport item."""
        return self.logistics_type in (
            LogisticsType.FLIGHT,
            LogisticsType.TRAIN,
            LogisticsType.BUS,
            LogisticsType.FERRY,
            LogisticsType.RENTAL_CAR,
            LogisticsType.TAXI,
            LogisticsType.GROUND_TRANSPORT
        )

    @property
    def is_accommodation(self):
        """Check if this is an accommodation item."""
        return self.logistics_type in (
            LogisticsType.HOTEL,
            LogisticsType.APARTMENT
        )

    @property
    def display_name(self):
        """Get a display-friendly name for this logistics item."""
        type_name = self.logistics_type.value.replace('_', ' ').title()
        if self.provider:
            return f'{type_name}: {self.provider}'
        return type_name

    @property
    def has_coordinates(self):
        """Check if this logistics item has GPS coordinates."""
        return self.latitude is not None and self.longitude is not None

    @property
    def has_departure_coordinates(self):
        """Check if this transport has departure GPS coordinates."""
        return self.departure_lat is not None and self.departure_lng is not None

    @property
    def has_arrival_coordinates(self):
        """Check if this transport has arrival GPS coordinates."""
        return self.arrival_lat is not None and self.arrival_lng is not None

    @property
    def status_label(self):
        """Get French label for status."""
        labels = {
            LogisticsStatus.PENDING: 'En attente',
            LogisticsStatus.BOOKED: 'Réservé',
            LogisticsStatus.CONFIRMED: 'Confirmé',
            LogisticsStatus.COMPLETED: 'Terminé',
            LogisticsStatus.CANCELLED: 'Annulé'
        }
        return labels.get(self.status, 'Inconnu')

    @property
    def status_color(self):
        """Get Bootstrap color class for status."""
        colors = {
            LogisticsStatus.PENDING: 'warning',
            LogisticsStatus.BOOKED: 'info',
            LogisticsStatus.CONFIRMED: 'success',
            LogisticsStatus.COMPLETED: 'primary',
            LogisticsStatus.CANCELLED: 'danger'
        }
        return colors.get(self.status, 'secondary')

    @property
    def type_icon(self):
        """Get Bootstrap icon for logistics type."""
        icons = {
            LogisticsType.FLIGHT: 'bi-airplane',
            LogisticsType.TRAIN: 'bi-train-front',
            LogisticsType.BUS: 'bi-bus-front',
            LogisticsType.FERRY: 'bi-water',
            LogisticsType.RENTAL_CAR: 'bi-car-front',
            LogisticsType.TAXI: 'bi-taxi-front',
            LogisticsType.GROUND_TRANSPORT: 'bi-truck',
            LogisticsType.HOTEL: 'bi-building',
            LogisticsType.APARTMENT: 'bi-house-door',
            LogisticsType.RENTAL: 'bi-box-seam',
            LogisticsType.EQUIPMENT: 'bi-tools',
            LogisticsType.BACKLINE: 'bi-speaker',
            LogisticsType.CATERING: 'bi-cup-hot',
            LogisticsType.MEAL: 'bi-egg-fried',
            LogisticsType.PARKING: 'bi-p-circle',
            LogisticsType.VISA: 'bi-passport',
            LogisticsType.OTHER: 'bi-three-dots'
        }
        return icons.get(self.logistics_type, 'bi-geo-alt')

    @property
    def type_color(self):
        """Get color for logistics type (for map markers)."""
        colors = {
            LogisticsType.FLIGHT: '#0d6efd',      # Blue
            LogisticsType.TRAIN: '#198754',       # Green
            LogisticsType.BUS: '#fd7e14',         # Orange
            LogisticsType.FERRY: '#0dcaf0',       # Cyan
            LogisticsType.RENTAL_CAR: '#6f42c1',  # Purple
            LogisticsType.TAXI: '#ffc107',        # Yellow
            LogisticsType.GROUND_TRANSPORT: '#6c757d',  # Gray
            LogisticsType.HOTEL: '#20c997',       # Teal
            LogisticsType.APARTMENT: '#198754',   # Green
            LogisticsType.RENTAL: '#adb5bd',      # Light gray
            LogisticsType.EQUIPMENT: '#495057',   # Dark gray
            LogisticsType.BACKLINE: '#6f42c1',    # Purple
            LogisticsType.CATERING: '#dc3545',    # Red
            LogisticsType.MEAL: '#fd7e14',        # Orange
            LogisticsType.PARKING: '#adb5bd',     # Light gray
            LogisticsType.VISA: '#d63384',        # Pink
            LogisticsType.OTHER: '#6c757d'        # Gray
        }
        return colors.get(self.logistics_type, '#6c757d')

    def is_user_assigned(self, user):
        """Check if user is assigned to this logistics item.

        Used for role-based visibility filtering.
        """
        return any(a.user_id == user.id for a in self.assignments.all())


class PromotorExpenses(db.Model):
    """
    R4: Dépenses promoteur pour un concert (standard industrie).

    Permet le calcul du Split Point réel selon les standards:
    split_point = promoter_expenses + guarantee

    Catégories standard:
    - venue_fee: Location/frais de salle
    - production_cost: Coûts de production (son, lumière, staff)
    - marketing_cost: Coûts marketing/promo
    - insurance: Assurance événement
    - security: Frais de sécurité
    - catering: Restauration équipes
    - other: Autres frais
    """

    __tablename__ = 'promotor_expenses'

    id = db.Column(db.Integer, primary_key=True)

    # Tour stop reference
    tour_stop_id = db.Column(
        db.Integer,
        db.ForeignKey('tour_stops.id'),
        nullable=False,
        index=True
    )

    # Expense categories (standard industrie - Pollstar, Billboard)
    venue_fee = db.Column(db.Numeric(10, 2), default=0)  # Location salle
    production_cost = db.Column(db.Numeric(10, 2), default=0)  # Son, lumière, staff
    marketing_cost = db.Column(db.Numeric(10, 2), default=0)  # Promo, affiches, digital
    insurance = db.Column(db.Numeric(10, 2), default=0)  # Assurance événement
    security = db.Column(db.Numeric(10, 2), default=0)  # Frais sécurité
    catering = db.Column(db.Numeric(10, 2), default=0)  # Restauration équipes
    other = db.Column(db.Numeric(10, 2), default=0)  # Autres frais
    other_description = db.Column(db.String(255))  # Description autres frais

    # Currency (hérité du TourStop normalement)
    currency = db.Column(db.String(3), default='EUR')

    # Notes
    notes = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tour_stop = db.relationship('TourStop', back_populates='promotor_expenses')

    def __repr__(self):
        return f'<PromotorExpenses {self.tour_stop_id} - {self.total_expenses}{self.currency}>'

    @property
    def total_expenses(self):
        """Calculate total promoter expenses."""
        from decimal import Decimal
        return float(
            Decimal(str(self.venue_fee or 0)) +
            Decimal(str(self.production_cost or 0)) +
            Decimal(str(self.marketing_cost or 0)) +
            Decimal(str(self.insurance or 0)) +
            Decimal(str(self.security or 0)) +
            Decimal(str(self.catering or 0)) +
            Decimal(str(self.other or 0))
        )

    @property
    def expenses_breakdown(self):
        """Return expenses breakdown as dict."""
        return {
            'venue_fee': float(self.venue_fee or 0),
            'production_cost': float(self.production_cost or 0),
            'marketing_cost': float(self.marketing_cost or 0),
            'insurance': float(self.insurance or 0),
            'security': float(self.security or 0),
            'catering': float(self.catering or 0),
            'other': float(self.other or 0),
            'total': self.total_expenses,
        }


class LocalContact(db.Model):
    """Local contact for a tour stop (promoter rep, driver, etc.)."""

    __tablename__ = 'local_contacts'

    id = db.Column(db.Integer, primary_key=True)

    # Tour stop reference
    tour_stop_id = db.Column(
        db.Integer,
        db.ForeignKey('tour_stops.id'),
        nullable=False,
        index=True
    )

    # Contact info
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50))  # Promoter Rep, Driver, Production Manager, etc.
    company = db.Column(db.String(100))  # Company/organization name
    email = db.Column(db.String(120))
    phone = db.Column(db.String(30), nullable=False)
    phone_secondary = db.Column(db.String(30))  # Secondary phone number
    is_primary = db.Column(db.Boolean, default=False)

    # Availability
    available_from = db.Column(db.Time)
    available_until = db.Column(db.Time)

    # Notes
    notes = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    tour_stop = db.relationship('TourStop', back_populates='local_contacts')

    def __repr__(self):
        return f'<LocalContact {self.name} ({self.role})>'

    @property
    def display_name(self):
        """Get display name with role."""
        if self.role:
            return f'{self.name} ({self.role})'
        return self.name


class LogisticsAssignment(db.Model):
    """
    Assignation d'un élément logistique à une personne.

    Permet d'assigner des vols, hôtels, transports à des utilisateurs spécifiques
    avec des détails comme le numéro de siège ou de chambre.
    """

    __tablename__ = 'logistics_assignments'

    id = db.Column(db.Integer, primary_key=True)

    # Références
    logistics_info_id = db.Column(
        db.Integer,
        db.ForeignKey('logistics_info.id'),
        nullable=False,
        index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
        index=True
    )

    # Détails spécifiques à l'assignation
    seat_number = db.Column(db.String(20))  # Vol: "12A", Train: "Voiture 6 Place 45"
    room_number = db.Column(db.String(20))  # Hôtel: "101", "Suite 5"
    room_sharing_with = db.Column(db.String(100))  # Nom du colocataire si partage
    special_requests = db.Column(db.Text)  # Demandes spéciales

    # Tracking
    confirmation_sent = db.Column(db.Boolean, default=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_by_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=True
    )

    # Relationships
    logistics_info = db.relationship(
        'LogisticsInfo',
        backref=db.backref('assignments', lazy='dynamic', cascade='all, delete-orphan')
    )
    user = db.relationship(
        'User',
        foreign_keys=[user_id],
        backref=db.backref('logistics_assignments', lazy='dynamic')
    )
    assigned_by = db.relationship(
        'User',
        foreign_keys=[assigned_by_id]
    )

    # Contrainte unique: un user ne peut être assigné qu'une fois par élément logistique
    __table_args__ = (
        db.UniqueConstraint('logistics_info_id', 'user_id', name='unique_logistics_user_assignment'),
    )

    def __repr__(self):
        return f'<LogisticsAssignment {self.user_id} -> {self.logistics_info_id}>'

    @property
    def display_details(self):
        """Get display string for assignment details."""
        details = []
        if self.seat_number:
            details.append(f"Siège {self.seat_number}")
        if self.room_number:
            details.append(f"Chambre {self.room_number}")
        if self.room_sharing_with:
            details.append(f"avec {self.room_sharing_with}")
        return " - ".join(details) if details else None
