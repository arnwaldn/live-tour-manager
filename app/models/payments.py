"""
Payment models for GigRoute - Enterprise Grade Financial Module.
Handles payments for all tour personnel: musicians, technicians, management, support staff.
Compliant with French labor law (Intermittent du spectacle) and SEPA standards.
"""
import enum
from datetime import datetime
from decimal import Decimal

from app.extensions import db


class StaffCategory(enum.Enum):
    """Categories de personnel de tournee"""
    ARTISTIC = "artistic"       # Musiciens, choristes, danseurs
    TECHNICAL = "technical"     # Son, lumiere, backline, scene
    MANAGEMENT = "management"   # Tour manager, prod manager
    SUPPORT = "support"         # Securite, chauffeurs, catering
    EXTERNAL = "external"       # Crew local, prestataires


class StaffRole(enum.Enum):
    """Roles specifiques par categorie"""
    # ARTISTIC - Performers
    LEAD_MUSICIAN = "lead_musician"
    MUSICIAN = "musician"
    BACKING_VOCALIST = "backing_vocalist"
    DANCER = "dancer"
    CHOREOGRAPHER = "choreographer"

    # TECHNICAL - Audio
    FOH_ENGINEER = "foh_engineer"
    MONITOR_ENGINEER = "monitor_engineer"
    AUDIO_TECH = "audio_tech"
    SYSTEM_TECH = "system_tech"

    # TECHNICAL - Lighting
    LIGHTING_DIRECTOR = "lighting_director"
    LIGHTING_TECH = "lighting_tech"
    LIGHTING_OPERATOR = "lighting_operator"

    # TECHNICAL - Video
    VIDEO_DIRECTOR = "video_director"
    VIDEO_TECH = "video_tech"
    VJ = "vj"

    # TECHNICAL - Stage
    STAGE_MANAGER = "stage_manager"
    STAGEHAND = "stagehand"
    RIGGER = "rigger"
    SCENIC_TECH = "scenic_tech"
    PYRO_TECH = "pyro_tech"

    # TECHNICAL - Backline
    GUITAR_TECH = "guitar_tech"
    BASS_TECH = "bass_tech"
    DRUM_TECH = "drum_tech"
    KEYBOARD_TECH = "keyboard_tech"
    PERCUSSION_TECH = "percussion_tech"

    # MANAGEMENT
    TOUR_MANAGER = "tour_manager"
    PRODUCTION_MANAGER = "production_manager"
    PRODUCTION_ASSISTANT = "production_assistant"
    TOUR_COORDINATOR = "tour_coordinator"
    ADVANCE_PERSON = "advance_person"
    TOUR_PUBLICIST = "tour_publicist"
    BUSINESS_MANAGER = "business_manager"

    # SUPPORT
    SECURITY = "security"
    DRIVER = "driver"
    BUS_DRIVER = "bus_driver"
    TRUCK_DRIVER = "truck_driver"
    CHEF = "chef"
    CATERING_STAFF = "catering_staff"
    WARDROBE = "wardrobe"
    HAIR_MAKEUP = "hair_makeup"
    HOSPITALITY = "hospitality"

    # EXTERNAL
    LOCAL_CREW = "local_crew"
    LOCAL_DRIVER = "local_driver"
    LOCAL_SECURITY = "local_security"
    CONTRACTOR = "contractor"
    VENDOR = "vendor"


class ContractType(enum.Enum):
    """Types de contrat (specificites francaises)"""
    CDDU = "cddu"              # CDD d'usage (intermittent du spectacle)
    CDD = "cdd"                # CDD standard
    CDI = "cdi"                # CDI (rare en tournee)
    FREELANCE = "freelance"    # Auto-entrepreneur / Micro-entreprise
    PRESTATION = "prestation"  # Facture societe (SARL, SAS, etc.)
    GUSO = "guso"              # Guichet Unique Spectacle Occasionnel


class PaymentFrequency(enum.Enum):
    """Frequence de paiement selon role"""
    PER_SHOW = "per_show"      # Par concert (musiciens)
    DAILY = "daily"            # Journalier (techniciens)
    HALF_DAY = "half_day"      # Demi-journee
    WEEKLY = "weekly"          # Hebdomadaire (management)
    HOURLY = "hourly"          # Horaire (crew local)
    FIXED = "fixed"            # Forfait (prestataires)
    MONTHLY = "monthly"        # Mensuel (CDI)


class PaymentType(enum.Enum):
    """Types de paiement"""
    CACHET = "cachet"               # Fee artiste/technicien
    PER_DIEM = "per_diem"           # Indemnite journaliere
    OVERTIME = "overtime"           # Heures supplementaires
    BONUS = "bonus"                 # Prime exceptionnelle
    REIMBURSEMENT = "reimbursement" # Remboursement frais
    ADVANCE = "advance"             # Avance sur cachet
    TRAVEL_ALLOWANCE = "travel"     # Indemnite deplacement
    MEAL_ALLOWANCE = "meal"         # Indemnite repas
    ACCOMMODATION = "accommodation" # Indemnite logement
    EQUIPMENT = "equipment"         # Location equipement personnel
    BUYOUT = "buyout"               # Rachat droits


class PaymentStatus(enum.Enum):
    """Statuts de paiement avec workflow"""
    DRAFT = "draft"                 # Brouillon
    PENDING_APPROVAL = "pending"    # En attente approbation
    APPROVED = "approved"           # Approuve
    SCHEDULED = "scheduled"         # Programme pour paiement
    PROCESSING = "processing"       # En cours de traitement
    PAID = "paid"                   # Paye
    CANCELLED = "cancelled"         # Annule
    REJECTED = "rejected"           # Rejete


class PaymentMethod(enum.Enum):
    """Methodes de paiement"""
    BANK_TRANSFER = "bank_transfer"  # Virement bancaire standard
    SEPA = "sepa"                    # Virement SEPA
    CHECK = "check"                  # Cheque
    CASH = "cash"                    # Especes
    PAYPAL = "paypal"                # PayPal
    WISE = "wise"                    # Wise (TransferWise)
    OTHER = "other"                  # Autre


class TeamMemberPayment(db.Model):
    """
    Paiement individuel a un membre de l'equipe.
    Couvre tous les types de personnel: artistique, technique, management, support, externe.
    """
    __tablename__ = 'team_member_payments'

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(20), unique=True, nullable=False, index=True)  # PAY-2026-00001

    # Relations
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    tour_id = db.Column(db.Integer, db.ForeignKey('tours.id'), nullable=True, index=True)
    tour_stop_id = db.Column(db.Integer, db.ForeignKey('tour_stops.id'), nullable=True, index=True)

    # Classification du beneficiaire
    staff_category = db.Column(db.Enum(StaffCategory), nullable=False)
    staff_role = db.Column(db.Enum(StaffRole), nullable=False)

    # Paiement
    payment_type = db.Column(db.Enum(PaymentType), nullable=False)
    payment_frequency = db.Column(db.Enum(PaymentFrequency))
    description = db.Column(db.String(255))
    notes = db.Column(db.Text)

    # Montants
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='EUR', nullable=False)
    quantity = db.Column(db.Numeric(10, 2), default=1)  # Nb heures/jours/shows
    unit_rate = db.Column(db.Numeric(10, 2))  # Taux unitaire

    # Majorations
    overtime_hours = db.Column(db.Numeric(5, 2), default=0)
    overtime_rate = db.Column(db.Numeric(5, 2), default=1.25)  # +25% par defaut
    weekend_work = db.Column(db.Boolean, default=False)
    holiday_work = db.Column(db.Boolean, default=False)

    # Dates de travail
    work_date = db.Column(db.Date)
    work_start = db.Column(db.DateTime)
    work_end = db.Column(db.DateTime)

    # Dates de paiement
    due_date = db.Column(db.Date)
    paid_date = db.Column(db.Date)
    scheduled_date = db.Column(db.Date)  # Date programmee pour virement

    # Statut et workflow
    status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.DRAFT, nullable=False, index=True)
    payment_method = db.Column(db.Enum(PaymentMethod))
    bank_reference = db.Column(db.String(100))  # Reference virement SEPA
    batch_id = db.Column(db.String(50))  # ID lot pour virements groupes

    # Approbation
    submitted_at = db.Column(db.DateTime)
    submitted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)

    # Lien facture (si applicable)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id', use_alter=True), nullable=True)

    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relations
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('payments_received', lazy='dynamic'))
    tour = db.relationship('Tour', backref=db.backref('team_payments', lazy='dynamic'))
    tour_stop = db.relationship('TourStop', backref=db.backref('team_payments', lazy='dynamic'))
    submitted_by = db.relationship('User', foreign_keys=[submitted_by_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def __repr__(self):
        return f'<TeamMemberPayment {self.reference} - {self.amount} {self.currency}>'

    @staticmethod
    def generate_reference():
        """Generate unique payment reference: PAY-YYYY-NNNNN"""
        year = datetime.utcnow().year
        last_payment = TeamMemberPayment.query.filter(
            TeamMemberPayment.reference.like(f'PAY-{year}-%')
        ).order_by(TeamMemberPayment.id.desc()).first()

        if last_payment:
            last_num = int(last_payment.reference.split('-')[2])
            new_num = last_num + 1
        else:
            new_num = 1

        return f'PAY-{year}-{new_num:05d}'

    @property
    def total_amount(self):
        """Calculate total amount including overtime and bonuses"""
        base = self.amount * (self.quantity or Decimal('1'))

        # Add overtime (P-H3 fix: handle NULL unit_rate)
        if self.overtime_hours and self.overtime_hours > 0 and self.unit_rate:
            overtime_amount = self.unit_rate * self.overtime_hours * (self.overtime_rate or Decimal('1.25'))
            base += overtime_amount

        return base

    @property
    def can_approve(self):
        """Check if payment can be approved"""
        return self.status == PaymentStatus.PENDING_APPROVAL

    @property
    def can_pay(self):
        """Check if payment can be marked as paid"""
        return self.status in [PaymentStatus.APPROVED, PaymentStatus.SCHEDULED]

    def submit_for_approval(self, submitted_by_id):
        """Submit payment for approval"""
        if self.status != PaymentStatus.DRAFT:
            raise ValueError("Only draft payments can be submitted for approval")
        self.status = PaymentStatus.PENDING_APPROVAL
        self.submitted_at = datetime.utcnow()
        self.submitted_by_id = submitted_by_id

    def approve(self, approved_by_id):
        """Approve payment"""
        if not self.can_approve:
            raise ValueError("Payment cannot be approved in current status")
        self.status = PaymentStatus.APPROVED
        self.approved_at = datetime.utcnow()
        self.approved_by_id = approved_by_id

    def reject(self, rejected_by_id, reason):
        """Reject payment"""
        if not self.can_approve:
            raise ValueError("Payment cannot be rejected in current status")
        self.status = PaymentStatus.REJECTED
        self.approved_at = datetime.utcnow()
        self.approved_by_id = rejected_by_id
        self.rejection_reason = reason

    def mark_as_paid(self, payment_method, bank_reference=None):
        """Mark payment as paid"""
        if not self.can_pay:
            raise ValueError("Payment cannot be marked as paid in current status")
        self.status = PaymentStatus.PAID
        self.paid_date = datetime.utcnow().date()
        self.payment_method = payment_method
        if bank_reference:
            self.bank_reference = bank_reference


class UserPaymentConfig(db.Model):
    """
    Configuration des taux par defaut pour un membre d'equipe.
    Stocke les informations contractuelles et bancaires pour faciliter la creation de paiements.
    """
    __tablename__ = 'user_payment_configs'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)

    # Classification
    staff_category = db.Column(db.Enum(StaffCategory))
    staff_role = db.Column(db.Enum(StaffRole))
    contract_type = db.Column(db.Enum(ContractType))
    payment_frequency = db.Column(db.Enum(PaymentFrequency))

    # Taux standards
    show_rate = db.Column(db.Numeric(10, 2))        # Par concert
    daily_rate = db.Column(db.Numeric(10, 2))       # Journalier
    half_day_rate = db.Column(db.Numeric(10, 2))    # Demi-journee
    weekly_rate = db.Column(db.Numeric(10, 2))      # Hebdomadaire
    monthly_rate = db.Column(db.Numeric(10, 2))     # Mensuel
    hourly_rate = db.Column(db.Numeric(10, 2))      # Horaire
    per_diem = db.Column(db.Numeric(10, 2), default=35.00)  # Per diem standard

    # Majorations (multiplicateurs)
    overtime_rate_25 = db.Column(db.Numeric(5, 2), default=1.25)   # +25% (1-8h sup)
    overtime_rate_50 = db.Column(db.Numeric(5, 2), default=1.50)   # +50% (>8h sup)
    weekend_rate = db.Column(db.Numeric(5, 2), default=1.25)       # Weekend
    holiday_rate = db.Column(db.Numeric(5, 2), default=2.00)       # Jours feries
    night_rate = db.Column(db.Numeric(5, 2), default=1.25)         # Travail de nuit

    # Informations bancaires (SEPA) — IBAN chiffre Fernet (RGPD Art. 32)
    _iban_encrypted = db.Column('iban', db.String(256))
    bic = db.Column(db.String(11))
    bank_name = db.Column(db.String(100))
    account_holder = db.Column(db.String(200))  # Titulaire du compte

    # Informations fiscales/sociales (France) — N° sécu chiffré Fernet (RGPD Art. 32)
    siret = db.Column(db.String(14))                    # Si auto-entrepreneur
    siren = db.Column(db.String(9))                     # Si societe
    vat_number = db.Column(db.String(20))               # TVA intracommunautaire
    _social_security_number_encrypted = db.Column('social_security_number', db.String(256))
    is_intermittent = db.Column(db.Boolean, default=False)  # Statut intermittent
    intermittent_id = db.Column(db.String(20))          # Numero Pole Emploi Spectacle
    conges_spectacle_id = db.Column(db.String(20))      # Numero Conges Spectacles
    audiens_id = db.Column(db.String(20))               # Numero Audiens (prevoyance)

    # Adresse facturation
    billing_address_line1 = db.Column(db.String(200))
    billing_address_line2 = db.Column(db.String(200))
    billing_city = db.Column(db.String(100))
    billing_postal_code = db.Column(db.String(20))
    billing_country = db.Column(db.String(2), default='FR')

    currency = db.Column(db.String(3), default='EUR')

    # Notes
    notes = db.Column(db.Text)

    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    user = db.relationship('User', backref=db.backref('payment_config', uselist=False))

    def __repr__(self):
        return f'<UserPaymentConfig user_id={self.user_id} role={self.staff_role}>'

    # ── Fernet encryption properties (RGPD Art. 32) ──

    @property
    def iban(self):
        """Decrypt IBAN on read."""
        if not self._iban_encrypted:
            return None
        try:
            from app.utils.encryption import decrypt_value
            return decrypt_value(self._iban_encrypted)
        except Exception:
            return self._iban_encrypted

    @iban.setter
    def iban(self, value):
        """Encrypt IBAN on write."""
        if not value:
            self._iban_encrypted = None
            return
        try:
            from app.utils.encryption import encrypt_value
            self._iban_encrypted = encrypt_value(value)
        except Exception:
            self._iban_encrypted = value

    @property
    def social_security_number(self):
        """Decrypt social security number on read."""
        if not self._social_security_number_encrypted:
            return None
        try:
            from app.utils.encryption import decrypt_value
            return decrypt_value(self._social_security_number_encrypted)
        except Exception:
            return self._social_security_number_encrypted

    @social_security_number.setter
    def social_security_number(self, value):
        """Encrypt social security number on write."""
        if not value:
            self._social_security_number_encrypted = None
            return
        try:
            from app.utils.encryption import encrypt_value
            self._social_security_number_encrypted = encrypt_value(value)
        except Exception:
            self._social_security_number_encrypted = value

    @property
    def default_rate(self):
        """Get the default rate based on payment frequency"""
        freq_to_rate = {
            PaymentFrequency.PER_SHOW: self.show_rate,
            PaymentFrequency.DAILY: self.daily_rate,
            PaymentFrequency.HALF_DAY: self.half_day_rate,
            PaymentFrequency.WEEKLY: self.weekly_rate,
            PaymentFrequency.MONTHLY: self.monthly_rate,
            PaymentFrequency.HOURLY: self.hourly_rate,
        }
        return freq_to_rate.get(self.payment_frequency)

    @property
    def has_valid_bank_info(self):
        """Check if bank information is complete for SEPA transfers"""
        return bool(self.iban and self.bic)

    @property
    def has_valid_tax_info(self):
        """Check if tax information is complete for invoicing"""
        # Either SIRET (auto-entrepreneur) or social security (salarie)
        return bool(self.siret or self.social_security_number)


# Taux par defaut selon role (reference marche francais 2026)
DEFAULT_RATES = {
    # ARTISTIC - par show (EUR)
    StaffRole.LEAD_MUSICIAN: {'show_rate': 500, 'per_diem': 35, 'frequency': PaymentFrequency.PER_SHOW},
    StaffRole.MUSICIAN: {'show_rate': 300, 'per_diem': 35, 'frequency': PaymentFrequency.PER_SHOW},
    StaffRole.BACKING_VOCALIST: {'show_rate': 250, 'per_diem': 35, 'frequency': PaymentFrequency.PER_SHOW},
    StaffRole.DANCER: {'show_rate': 200, 'per_diem': 35, 'frequency': PaymentFrequency.PER_SHOW},
    StaffRole.CHOREOGRAPHER: {'show_rate': 400, 'per_diem': 35, 'frequency': PaymentFrequency.PER_SHOW},

    # TECHNICAL - Audio (journalier)
    StaffRole.FOH_ENGINEER: {'daily_rate': 350, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.MONITOR_ENGINEER: {'daily_rate': 300, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.AUDIO_TECH: {'daily_rate': 200, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.SYSTEM_TECH: {'daily_rate': 250, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},

    # TECHNICAL - Lighting (journalier)
    StaffRole.LIGHTING_DIRECTOR: {'daily_rate': 350, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.LIGHTING_TECH: {'daily_rate': 200, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.LIGHTING_OPERATOR: {'daily_rate': 220, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},

    # TECHNICAL - Video (journalier)
    StaffRole.VIDEO_DIRECTOR: {'daily_rate': 350, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.VIDEO_TECH: {'daily_rate': 220, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.VJ: {'daily_rate': 250, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},

    # TECHNICAL - Stage (journalier)
    StaffRole.STAGE_MANAGER: {'daily_rate': 280, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.STAGEHAND: {'daily_rate': 150, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.RIGGER: {'daily_rate': 220, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.SCENIC_TECH: {'daily_rate': 200, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.PYRO_TECH: {'daily_rate': 300, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},

    # TECHNICAL - Backline (journalier)
    StaffRole.GUITAR_TECH: {'daily_rate': 220, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.BASS_TECH: {'daily_rate': 200, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.DRUM_TECH: {'daily_rate': 220, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.KEYBOARD_TECH: {'daily_rate': 200, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.PERCUSSION_TECH: {'daily_rate': 200, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},

    # MANAGEMENT - hebdomadaire (per diem souvent inclus)
    StaffRole.TOUR_MANAGER: {'weekly_rate': 3000, 'per_diem': 0, 'frequency': PaymentFrequency.WEEKLY},
    StaffRole.PRODUCTION_MANAGER: {'weekly_rate': 2500, 'per_diem': 0, 'frequency': PaymentFrequency.WEEKLY},
    StaffRole.PRODUCTION_ASSISTANT: {'weekly_rate': 1200, 'per_diem': 35, 'frequency': PaymentFrequency.WEEKLY},
    StaffRole.TOUR_COORDINATOR: {'weekly_rate': 1500, 'per_diem': 35, 'frequency': PaymentFrequency.WEEKLY},
    StaffRole.ADVANCE_PERSON: {'daily_rate': 300, 'per_diem': 50, 'frequency': PaymentFrequency.DAILY},
    StaffRole.TOUR_PUBLICIST: {'weekly_rate': 2000, 'per_diem': 35, 'frequency': PaymentFrequency.WEEKLY},
    StaffRole.BUSINESS_MANAGER: {'weekly_rate': 2500, 'per_diem': 0, 'frequency': PaymentFrequency.WEEKLY},

    # SUPPORT - journalier
    StaffRole.SECURITY: {'daily_rate': 180, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.DRIVER: {'daily_rate': 200, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.BUS_DRIVER: {'daily_rate': 250, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.TRUCK_DRIVER: {'daily_rate': 220, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.CHEF: {'daily_rate': 280, 'per_diem': 0, 'frequency': PaymentFrequency.DAILY},  # repas inclus
    StaffRole.CATERING_STAFF: {'daily_rate': 150, 'per_diem': 0, 'frequency': PaymentFrequency.DAILY},
    StaffRole.WARDROBE: {'daily_rate': 200, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.HAIR_MAKEUP: {'daily_rate': 220, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},
    StaffRole.HOSPITALITY: {'daily_rate': 150, 'per_diem': 35, 'frequency': PaymentFrequency.DAILY},

    # EXTERNAL - horaire
    StaffRole.LOCAL_CREW: {'hourly_rate': 15, 'per_diem': 0, 'frequency': PaymentFrequency.HOURLY},
    StaffRole.LOCAL_DRIVER: {'hourly_rate': 18, 'per_diem': 0, 'frequency': PaymentFrequency.HOURLY},
    StaffRole.LOCAL_SECURITY: {'hourly_rate': 16, 'per_diem': 0, 'frequency': PaymentFrequency.HOURLY},
    StaffRole.CONTRACTOR: {'daily_rate': 300, 'per_diem': 0, 'frequency': PaymentFrequency.FIXED},
    StaffRole.VENDOR: {'daily_rate': 0, 'per_diem': 0, 'frequency': PaymentFrequency.FIXED},
}


# Mapping categorie -> roles
CATEGORY_ROLES = {
    StaffCategory.ARTISTIC: [
        StaffRole.LEAD_MUSICIAN, StaffRole.MUSICIAN, StaffRole.BACKING_VOCALIST,
        StaffRole.DANCER, StaffRole.CHOREOGRAPHER
    ],
    StaffCategory.TECHNICAL: [
        StaffRole.FOH_ENGINEER, StaffRole.MONITOR_ENGINEER, StaffRole.AUDIO_TECH, StaffRole.SYSTEM_TECH,
        StaffRole.LIGHTING_DIRECTOR, StaffRole.LIGHTING_TECH, StaffRole.LIGHTING_OPERATOR,
        StaffRole.VIDEO_DIRECTOR, StaffRole.VIDEO_TECH, StaffRole.VJ,
        StaffRole.STAGE_MANAGER, StaffRole.STAGEHAND, StaffRole.RIGGER, StaffRole.SCENIC_TECH, StaffRole.PYRO_TECH,
        StaffRole.GUITAR_TECH, StaffRole.BASS_TECH, StaffRole.DRUM_TECH, StaffRole.KEYBOARD_TECH, StaffRole.PERCUSSION_TECH
    ],
    StaffCategory.MANAGEMENT: [
        StaffRole.TOUR_MANAGER, StaffRole.PRODUCTION_MANAGER, StaffRole.PRODUCTION_ASSISTANT,
        StaffRole.TOUR_COORDINATOR, StaffRole.ADVANCE_PERSON, StaffRole.TOUR_PUBLICIST, StaffRole.BUSINESS_MANAGER
    ],
    StaffCategory.SUPPORT: [
        StaffRole.SECURITY, StaffRole.DRIVER, StaffRole.BUS_DRIVER, StaffRole.TRUCK_DRIVER,
        StaffRole.CHEF, StaffRole.CATERING_STAFF, StaffRole.WARDROBE, StaffRole.HAIR_MAKEUP, StaffRole.HOSPITALITY
    ],
    StaffCategory.EXTERNAL: [
        StaffRole.LOCAL_CREW, StaffRole.LOCAL_DRIVER, StaffRole.LOCAL_SECURITY, StaffRole.CONTRACTOR, StaffRole.VENDOR
    ]
}


def get_category_for_role(role: StaffRole) -> StaffCategory:
    """Get the category for a given role"""
    for category, roles in CATEGORY_ROLES.items():
        if role in roles:
            return category
    return StaffCategory.EXTERNAL  # Default fallback
