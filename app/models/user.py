"""
User and Role models with RBAC support.
Includes AccessLevel for permissions and Profession for professional identity.
"""
from enum import Enum
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from app.extensions import db


class AccessLevel(str, Enum):
    """
    Simplified access levels for permission control.
    Determines what users can do in the application.
    """
    ADMIN = "admin"           # Full access, can manage users and system
    MANAGER = "manager"       # Can manage tours, events, budgets, payments
    STAFF = "staff"           # Can view and edit assigned tours/events
    VIEWER = "viewer"         # Read-only access to assigned tours
    EXTERNAL = "external"     # Limited external access (promoters, venues)


# Access level display labels
ACCESS_LEVEL_LABELS = {
    AccessLevel.ADMIN: "Administrateur",
    AccessLevel.MANAGER: "Manager",
    AccessLevel.STAFF: "Staff",
    AccessLevel.VIEWER: "Lecture seule",
    AccessLevel.EXTERNAL: "Externe",
}

# Access level descriptions
ACCESS_LEVEL_DESCRIPTIONS = {
    AccessLevel.ADMIN: "Accès complet, gestion des utilisateurs et du système",
    AccessLevel.MANAGER: "Gestion des tournées, événements, budgets et paiements",
    AccessLevel.STAFF: "Consultation et édition des tournées/événements assignés",
    AccessLevel.VIEWER: "Consultation uniquement",
    AccessLevel.EXTERNAL: "Accès limité (promoteurs, salles)",
}

# Permission hierarchy (lower index = higher access)
ACCESS_HIERARCHY = [
    AccessLevel.ADMIN,
    AccessLevel.MANAGER,
    AccessLevel.STAFF,
    AccessLevel.VIEWER,
    AccessLevel.EXTERNAL,
]

# Association table for User-Role many-to-many relationship
user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)


class Role(db.Model):
    """Role model for RBAC."""

    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))
    permissions = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    users = db.relationship(
        'User',
        secondary=user_roles,
        back_populates='roles'
    )

    def __repr__(self):
        return f'<Role {self.name}>'

    def has_permission(self, permission):
        """Check if role has a specific permission."""
        return permission in (self.permissions or [])


class User(UserMixin, db.Model):
    """User model with authentication and role management."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)

    # Account lockout
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)

    # Password reset
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)

    # Invitation system
    invitation_token = db.Column(db.String(100), unique=True, index=True, nullable=True)
    invitation_token_expires = db.Column(db.DateTime, nullable=True)
    invited_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # Personal information
    date_of_birth = db.Column(db.Date)
    nationality = db.Column(db.String(100))
    _passport_number_encrypted = db.Column('passport_number', db.String(256))
    passport_expiry = db.Column(db.Date)

    # Travel preferences
    preferred_airline = db.Column(db.String(100))
    seat_preference = db.Column(db.String(20))  # window, aisle, no_preference
    meal_preference = db.Column(db.String(50))  # standard, vegetarian, vegan, halal, kosher
    hotel_preferences = db.Column(db.Text)

    # Timezone preference (IANA format, e.g., 'Europe/Paris', 'America/New_York')
    timezone = db.Column(db.String(50), default='Europe/Paris')

    # Emergency contact
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_relation = db.Column(db.String(50))
    emergency_contact_phone = db.Column(db.String(20))
    emergency_contact_email = db.Column(db.String(120))

    # Medical/dietary info
    dietary_restrictions = db.Column(db.Text)
    allergies = db.Column(db.Text)
    medical_notes = db.Column(db.Text)  # Private, visible only to managers

    # RGPD Art. 9 — Explicit consent for health data processing
    health_data_consent = db.Column(db.Boolean, default=False)
    health_data_consent_date = db.Column(db.DateTime, nullable=True)

    # Notification preferences
    notify_new_tour = db.Column(db.Boolean, default=True)
    notify_guestlist_request = db.Column(db.Boolean, default=True)
    notify_guestlist_approved = db.Column(db.Boolean, default=True)
    notify_tour_reminder = db.Column(db.Boolean, default=True)
    notify_document_shared = db.Column(db.Boolean, default=True)

    # Master email preference (overrides all notification settings)
    receive_emails = db.Column(db.Boolean, default=True)

    # Profile picture (stored in database for production portability)
    profile_picture_data = db.Column(db.LargeBinary, nullable=True)
    profile_picture_mime = db.Column(db.String(50), nullable=True)

    # Stripe billing
    stripe_customer_id = db.Column(db.String(255), unique=True, nullable=True)

    # ============================================================
    # NEW: Access Level & Professional Identity (v2.0)
    # ============================================================

    # Access level (simplified permissions - replaces complex role checking)
    access_level = db.Column(
        db.Enum(AccessLevel),
        default=AccessLevel.STAFF,
        nullable=False,
        index=True
    )

    # Label affiliation (optional) - deprecated, use label_name instead
    label_id = db.Column(db.Integer, db.ForeignKey('labels.id'), nullable=True)

    # Label name (free text field for record label affiliation)
    label_name = db.Column(db.String(200), nullable=True)

    # Relationships
    roles = db.relationship(
        'Role',
        secondary=user_roles,
        back_populates='users'
    )

    # Label affiliation
    label = db.relationship('Label', back_populates='users')

    # Professional professions (many-to-many)
    user_professions = db.relationship(
        'UserProfession',
        back_populates='user',
        cascade='all, delete-orphan',
        lazy='selectin'  # Optimized: loads all professions in 1 query instead of N+1
    )

    band_memberships = db.relationship(
        'BandMembership',
        back_populates='user',
        cascade='all, delete-orphan'
    )

    managed_bands = db.relationship(
        'Band',
        back_populates='manager',
        foreign_keys='Band.manager_id'
    )

    guestlist_requests = db.relationship(
        'GuestlistEntry',
        back_populates='requested_by',
        foreign_keys='GuestlistEntry.requested_by_id'
    )

    guestlist_approvals = db.relationship(
        'GuestlistEntry',
        back_populates='approved_by',
        foreign_keys='GuestlistEntry.approved_by_id'
    )

    # Entrées guestlist où cet utilisateur est l'artiste (membre du groupe)
    guestlist_entries_as_artist = db.relationship(
        'GuestlistEntry',
        back_populates='user',
        foreign_keys='GuestlistEntry.user_id',
        lazy='dynamic'
    )

    # Cartes voyageur (fidélité, abonnements rail, etc.)
    travel_cards = db.relationship(
        'TravelCard',
        back_populates='user',
        cascade='all, delete-orphan',
        order_by='TravelCard.created_at.desc()'
    )

    invited_by = db.relationship(
        'User',
        remote_side='User.id',
        foreign_keys=[invited_by_id],
        backref='invited_users'
    )

    # V2: Assignations aux tour_stops avec profession
    tour_stop_assignments = db.relationship(
        'TourStopMember',
        back_populates='user',
        cascade='all, delete-orphan',
        foreign_keys='TourStopMember.user_id',
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<User {self.email}>'

    @property
    def passport_number(self):
        """Decrypt passport number on read (RGPD Art. 32)."""
        if not self._passport_number_encrypted:
            return None
        try:
            from app.utils.encryption import decrypt_value
            return decrypt_value(self._passport_number_encrypted)
        except Exception:
            return self._passport_number_encrypted

    @passport_number.setter
    def passport_number(self, value):
        """Encrypt passport number on write (RGPD Art. 32)."""
        if not value:
            self._passport_number_encrypted = None
            return
        try:
            from app.utils.encryption import encrypt_value
            self._passport_number_encrypted = encrypt_value(value)
        except Exception:
            self._passport_number_encrypted = value

    @property
    def full_name(self):
        """Return user's full name."""
        return f'{self.first_name} {self.last_name}'

    def set_password(self, password):
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        """Check if user has a specific role."""
        return any(role.name == role_name for role in self.roles)

    def has_any_role(self, role_names):
        """Check if user has any of the specified roles."""
        return any(self.has_role(role_name) for role_name in role_names)

    def has_permission(self, permission):
        """Check if user has a specific permission through any role."""
        return any(role.has_permission(permission) for role in self.roles)

    # ============================================================
    # ACCESS LEVEL METHODS (v2.0)
    # ============================================================

    def has_access(self, required_level):
        """
        Check if user has at least the required access level.
        Uses hierarchy: ADMIN > MANAGER > STAFF > VIEWER > EXTERNAL
        """
        if isinstance(required_level, str):
            required_level = AccessLevel(required_level.lower())
        user_index = ACCESS_HIERARCHY.index(self.access_level)
        required_index = ACCESS_HIERARCHY.index(required_level)
        return user_index <= required_index

    def is_admin(self):
        """Check if user is an administrator."""
        return self.access_level == AccessLevel.ADMIN

    def is_manager_or_above(self):
        """Check if user is manager or higher."""
        return self.access_level in [AccessLevel.ADMIN, AccessLevel.MANAGER]

    def is_staff_or_above(self):
        """Check if user is staff or higher."""
        return self.access_level in [AccessLevel.ADMIN, AccessLevel.MANAGER, AccessLevel.STAFF]

    @property
    def access_level_label(self):
        """Get localized access level label."""
        return ACCESS_LEVEL_LABELS.get(self.access_level, str(self.access_level))

    # ============================================================
    # PROFESSION METHODS (v2.0)
    # ============================================================

    @property
    def professions(self):
        """Get list of Profession objects (filters out deleted professions)."""
        # user_professions is now a list (lazy='selectin'), not a Query
        return [up.profession for up in self.user_professions if up.profession is not None]

    @property
    def primary_profession(self):
        """Get user's primary profession or first profession (handles deleted professions)."""
        # user_professions is now a list (lazy='selectin'), not a Query
        # Find primary profession
        for up in self.user_professions:
            if up.is_primary and up.profession is not None:
                return up.profession
        # Fallback to first valid profession
        for up in self.user_professions:
            if up.profession is not None:
                return up.profession
        return None

    @property
    def profession_categories(self):
        """Get unique set of profession categories."""
        return list(set(p.category for p in self.professions))

    def has_profession(self, profession_code):
        """Check if user has a specific profession."""
        return any(p.code == profession_code for p in self.professions)

    def has_profession_in_category(self, category):
        """Check if user has any profession in a category."""
        return any(p.category == category for p in self.professions)

    def add_role(self, role):
        """Add a role to the user."""
        if role not in self.roles:
            self.roles.append(role)

    def remove_role(self, role):
        """Remove a role from the user."""
        if role in self.roles:
            self.roles.remove(role)

    @property
    def is_locked(self):
        """Check if account is currently locked."""
        if self.locked_until:
            return datetime.utcnow() < self.locked_until
        return False

    def record_failed_login(self, max_attempts=5, lockout_minutes=15):
        """Record a failed login attempt."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)

    def reset_failed_logins(self):
        """Reset failed login counter on successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = datetime.utcnow()

    def generate_reset_token(self):
        """Generate a password reset token."""
        import secrets
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        return self.reset_token

    def verify_reset_token(self, token):
        """Verify a password reset token using constant-time comparison."""
        import secrets
        # SECURITY: Use constant-time comparison to prevent timing attacks
        if (self.reset_token and
                self.reset_token_expires and
                datetime.utcnow() < self.reset_token_expires and
                secrets.compare_digest(self.reset_token, token)):
            return True
        return False

    def clear_reset_token(self):
        """Clear the reset token after use."""
        self.reset_token = None
        self.reset_token_expires = None

    def generate_invitation_token(self):
        """Generate a secure invitation token valid for 72 hours."""
        import secrets
        self.invitation_token = secrets.token_urlsafe(32)
        self.invitation_token_expires = datetime.utcnow() + timedelta(hours=72)
        return self.invitation_token

    @staticmethod
    def verify_invitation_token(token):
        """Find user by valid invitation token."""
        user = User.query.filter_by(invitation_token=token).first()
        if user and user.invitation_token_expires and datetime.utcnow() < user.invitation_token_expires:
            return user
        return None

    def clear_invitation_token(self):
        """Clear invitation token after password is set."""
        self.invitation_token = None
        self.invitation_token_expires = None
        self.email_verified = True

    @property
    def bands(self):
        """Get all bands the user is a member of."""
        return [membership.band for membership in self.band_memberships]

    # ============================================================
    # BILLING / SUBSCRIPTION HELPERS
    # ============================================================

    @property
    def current_plan(self):
        """Get the user's current plan name ('free' or 'pro')."""
        if self.subscription and self.subscription.is_active:
            return self.subscription.plan.value
        return 'free'

    @property
    def is_pro(self):
        """Check if user has an active Pro subscription."""
        return self.subscription is not None and self.subscription.is_pro

    # ============================================================
    # PRE-DELETION VALIDATION (P-H1)
    # ============================================================

    def can_delete(self):
        """
        Check if user can be safely deleted.
        Prevents orphan payments and data loss.
        """
        blockers = self.get_deletion_blockers()
        return len(blockers) == 0

    def get_deletion_blockers(self):
        """
        Get list of reasons why the user cannot be deleted.
        Returns empty list if deletion is safe.
        """
        from app.models.payments import TeamMemberPayment, PaymentStatus

        blockers = []

        # Check for pending/non-terminal payments (P-H1)
        pending_statuses = [
            PaymentStatus.DRAFT,
            PaymentStatus.PENDING_APPROVAL,
            PaymentStatus.APPROVED,
            PaymentStatus.SCHEDULED,
            PaymentStatus.PROCESSING
        ]
        pending_payments = TeamMemberPayment.query.filter(
            TeamMemberPayment.user_id == self.id,
            TeamMemberPayment.status.in_(pending_statuses)
        ).count()

        if pending_payments > 0:
            blockers.append(f"{pending_payments} paiement(s) en attente")

        # Check for managed bands
        if self.managed_bands:
            band_names = ', '.join([b.name for b in self.managed_bands[:3]])
            if len(self.managed_bands) > 3:
                band_names += f' (+{len(self.managed_bands) - 3} autres)'
            blockers.append(f"Manager de: {band_names}")

        return blockers


class TravelCard(db.Model):
    """Carte voyageur d'un utilisateur (fidélité aérienne, abonnement rail, etc.)"""

    __tablename__ = 'travel_cards'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    card_number = db.Column(db.String(50), nullable=False)
    card_type = db.Column(db.String(50), nullable=False)  # loyalty_airline, rail_subscription, car_rental, hotel_loyalty, other
    card_name = db.Column(db.String(100))  # Ex: "Carte Grand Voyageur SNCF", "Flying Blue"
    expiry_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    user = db.relationship('User', back_populates='travel_cards')

    # Type labels for display
    TYPE_LABELS = {
        'loyalty_airline': 'Fidélité aérienne',
        'rail_subscription': 'Abonnement rail',
        'car_rental': 'Carte loueur',
        'hotel_loyalty': 'Fidélité hôtel',
        'other': 'Autre'
    }

    def __repr__(self):
        return f'<TravelCard {self.card_name or self.card_number}>'

    @property
    def type_label(self):
        """Return human-readable type label."""
        return self.TYPE_LABELS.get(self.card_type, self.card_type)

    @property
    def is_expired(self):
        """Check if card is expired."""
        if self.expiry_date:
            from datetime import date
            return self.expiry_date < date.today()
        return False

    @property
    def expires_soon(self):
        """Check if card expires within 30 days."""
        if self.expiry_date:
            from datetime import date, timedelta
            return date.today() <= self.expiry_date <= date.today() + timedelta(days=30)
        return False
