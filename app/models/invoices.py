"""
Invoice models for GigRoute - Enterprise Grade Financial Module.
Compliant with French e-invoicing requirements (Sept 2026) and EN 16931 standard.
Supports Factur-X format (PDF + embedded XML).
"""
import enum
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.extensions import db


class InvoiceStatus(enum.Enum):
    """Statuts de facture"""
    DRAFT = "draft"             # Brouillon
    VALIDATED = "validated"     # Validee (prete a envoyer)
    SENT = "sent"               # Envoyee
    PAID = "paid"               # Payee
    PARTIAL = "partial"         # Partiellement payee
    OVERDUE = "overdue"         # En retard
    DISPUTED = "disputed"       # Contestee
    CANCELLED = "cancelled"     # Annulee
    CREDITED = "credited"       # Avoir emis


class InvoiceType(enum.Enum):
    """Types de facture"""
    INVOICE = "invoice"         # Facture standard
    CREDIT_NOTE = "credit"      # Avoir
    PROFORMA = "proforma"       # Facture proforma
    DEPOSIT = "deposit"         # Facture d'acompte
    FINAL = "final"             # Facture de solde


class VATRate(enum.Enum):
    """Taux de TVA France"""
    STANDARD = "20.00"          # Taux normal 20%
    INTERMEDIATE = "10.00"      # Taux intermediaire 10%
    REDUCED = "5.50"            # Taux reduit 5.5%
    SUPER_REDUCED = "2.10"      # Taux super reduit 2.1%
    ZERO = "0.00"               # Exonere ou non soumis


class Invoice(db.Model):
    """
    Facture conforme e-invoicing France (Sept 2026).
    Respecte le standard EN 16931 et le format Factur-X.
    """
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), unique=True, nullable=False, index=True)  # FACT-2026-00001
    type = db.Column(db.Enum(InvoiceType), default=InvoiceType.INVOICE, nullable=False)

    # Reference facture creditee (pour avoir)
    credited_invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=True)

    # === EMETTEUR (GigRoute ou autre societe) ===
    issuer_name = db.Column(db.String(200), nullable=False)
    issuer_legal_form = db.Column(db.String(50))           # SARL, SAS, etc.
    issuer_address_line1 = db.Column(db.String(200))
    issuer_address_line2 = db.Column(db.String(200))
    issuer_city = db.Column(db.String(100))
    issuer_postal_code = db.Column(db.String(20))
    issuer_country = db.Column(db.String(2), default='FR')
    issuer_siren = db.Column(db.String(9))                 # SIREN (9 chiffres)
    issuer_siret = db.Column(db.String(14))                # SIRET (14 chiffres)
    issuer_vat = db.Column(db.String(20))                  # TVA intracommunautaire
    issuer_rcs = db.Column(db.String(100))                 # RCS (ville + numero)
    issuer_capital = db.Column(db.String(50))              # Capital social
    issuer_phone = db.Column(db.String(20))
    issuer_email = db.Column(db.String(120))
    issuer_website = db.Column(db.String(200))
    issuer_iban = db.Column(db.String(34))                 # IBAN pour paiement
    issuer_bic = db.Column(db.String(11))                  # BIC/SWIFT

    # === DESTINATAIRE ===
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    recipient_name = db.Column(db.String(200), nullable=False)
    recipient_legal_form = db.Column(db.String(50))
    recipient_address_line1 = db.Column(db.String(200))
    recipient_address_line2 = db.Column(db.String(200))
    recipient_city = db.Column(db.String(100))
    recipient_postal_code = db.Column(db.String(20))
    recipient_country = db.Column(db.String(2), default='FR')
    recipient_siren = db.Column(db.String(9))
    recipient_siret = db.Column(db.String(14))
    recipient_vat = db.Column(db.String(20))
    recipient_email = db.Column(db.String(120))
    recipient_phone = db.Column(db.String(20))

    # === MONTANTS ===
    subtotal_ht = db.Column(db.Numeric(12, 2), nullable=False, default=0)   # Total HT
    discount_amount = db.Column(db.Numeric(12, 2), default=0)               # Remise
    subtotal_after_discount = db.Column(db.Numeric(12, 2), default=0)       # HT apres remise
    vat_amount = db.Column(db.Numeric(12, 2), default=0)                    # Total TVA
    total_ttc = db.Column(db.Numeric(12, 2), nullable=False, default=0)     # Total TTC
    amount_paid = db.Column(db.Numeric(12, 2), default=0)                   # Montant deja paye
    amount_due = db.Column(db.Numeric(12, 2), default=0)                    # Reste a payer
    currency = db.Column(db.String(3), default='EUR', nullable=False)

    # === DATES ===
    issue_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=False)
    delivery_date = db.Column(db.Date)                     # Date de livraison/prestation
    paid_date = db.Column(db.Date)
    sent_date = db.Column(db.Date)

    # === STATUT ===
    status = db.Column(db.Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False, index=True)

    # === LIENS TOUR MANAGER ===
    tour_id = db.Column(db.Integer, db.ForeignKey('tours.id'), nullable=True, index=True)
    tour_stop_id = db.Column(db.Integer, db.ForeignKey('tour_stops.id'), nullable=True)

    # === CONDITIONS DE PAIEMENT (Mentions obligatoires) ===
    payment_terms = db.Column(db.String(200), default='Paiement a 30 jours')
    payment_terms_days = db.Column(db.Integer, default=30)
    payment_method_accepted = db.Column(db.String(200), default='Virement bancaire')

    # === PENALITES DE RETARD (Mentions obligatoires depuis loi LME) ===
    late_penalty_rate = db.Column(db.Numeric(5, 2), default=12.00)  # Taux annuel penalites
    recovery_fee = db.Column(db.Numeric(10, 2), default=40.00)       # Indemnite forfaitaire recouvrement

    # === MENTIONS LEGALES SPECIFIQUES ===
    # TVA
    vat_mention = db.Column(db.String(200))                # Ex: "TVA non applicable, art. 293 B du CGI"
    reverse_charge = db.Column(db.Boolean, default=False)  # Autoliquidation TVA

    # Escompte
    early_payment_discount = db.Column(db.String(200))     # Conditions escompte
    no_discount_mention = db.Column(db.Boolean, default=True)  # "Pas d'escompte pour paiement anticipe"

    # Autres
    special_mentions = db.Column(db.Text)                  # Mentions particulieres
    internal_notes = db.Column(db.Text)                    # Notes internes (non imprimees)
    public_notes = db.Column(db.Text)                      # Notes visibles sur facture

    # === E-INVOICING (Factur-X) ===
    facturx_xml = db.Column(db.Text)                       # XML Factur-X embarque
    facturx_profile = db.Column(db.String(20), default='EN16931')  # Profil Factur-X
    pdp_reference = db.Column(db.String(100))              # Reference PDP (Plateforme Dematerialisation)
    pdp_submission_date = db.Column(db.DateTime)           # Date soumission PDP
    pdp_status = db.Column(db.String(50))                  # Statut PDP

    # === AUDIT ===
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    validated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    validated_at = db.Column(db.DateTime)

    # === RELATIONS ===
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='invoices_received')
    tour = db.relationship('Tour', backref=db.backref('invoices', lazy='dynamic'))
    tour_stop = db.relationship('TourStop', backref=db.backref('invoices', lazy='dynamic'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    validated_by = db.relationship('User', foreign_keys=[validated_by_id])
    credited_invoice = db.relationship('Invoice', remote_side=[id], backref='credit_notes')

    def __repr__(self):
        return f'<Invoice {self.number} - {self.total_ttc} {self.currency}>'

    @staticmethod
    def generate_number(invoice_type=InvoiceType.INVOICE):
        """Generate unique invoice number: FACT-YYYY-NNNNN or AV-YYYY-NNNNN"""
        year = datetime.utcnow().year
        prefix = 'AV' if invoice_type == InvoiceType.CREDIT_NOTE else 'FACT'

        last_invoice = Invoice.query.filter(
            Invoice.number.like(f'{prefix}-{year}-%'),
            Invoice.type == invoice_type
        ).order_by(Invoice.id.desc()).first()

        if last_invoice:
            last_num = int(last_invoice.number.split('-')[2])
            new_num = last_num + 1
        else:
            new_num = 1

        return f'{prefix}-{year}-{new_num:05d}'

    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        if self.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.CREDITED]:
            return False
        return self.due_date and date.today() > self.due_date

    @property
    def days_overdue(self):
        """Calculate days overdue"""
        if not self.is_overdue:
            return 0
        return (date.today() - self.due_date).days

    @property
    def late_penalty_amount(self):
        """Calculate late payment penalty"""
        if not self.is_overdue or not self.amount_due:
            return Decimal('0')
        # Penalite = (montant du * taux * jours retard) / 365
        daily_rate = self.late_penalty_rate / Decimal('365')
        return (self.amount_due * daily_rate * self.days_overdue / 100).quantize(Decimal('0.01'))

    def calculate_totals(self):
        """Recalculate invoice totals from lines"""
        self.subtotal_ht = sum(line.total_ht for line in self.lines) or Decimal('0')
        self.subtotal_after_discount = self.subtotal_ht - (self.discount_amount or Decimal('0'))
        self.vat_amount = sum(line.vat_amount for line in self.lines) or Decimal('0')
        self.total_ttc = self.subtotal_after_discount + self.vat_amount
        self.amount_due = self.total_ttc - (self.amount_paid or Decimal('0'))

    def validate(self):
        """Validate invoice - check all required fields"""
        errors = []

        # Emetteur
        if not self.issuer_name:
            errors.append("Nom de l'emetteur obligatoire")
        if not self.issuer_siret:
            errors.append("SIRET de l'emetteur obligatoire")
        if not self.issuer_address_line1:
            errors.append("Adresse de l'emetteur obligatoire")

        # Destinataire
        if not self.recipient_name:
            errors.append("Nom du destinataire obligatoire")
        if not self.recipient_address_line1:
            errors.append("Adresse du destinataire obligatoire")

        # Dates
        if not self.issue_date:
            errors.append("Date d'emission obligatoire")
        if not self.due_date:
            errors.append("Date d'echeance obligatoire")

        # Lignes
        if not self.lines:
            errors.append("Au moins une ligne de facture obligatoire")

        # Montants
        if self.total_ttc <= 0:
            errors.append("Le montant total doit etre superieur a 0")

        return errors

    def mark_as_validated(self, validated_by_id):
        """Validate invoice and assign number if needed"""
        errors = self.validate()
        if errors:
            raise ValueError(f"Validation impossible: {', '.join(errors)}")

        if not self.number:
            self.number = Invoice.generate_number(self.type)

        self.status = InvoiceStatus.VALIDATED
        self.validated_at = datetime.utcnow()
        self.validated_by_id = validated_by_id

    def mark_as_sent(self):
        """Mark invoice as sent"""
        if self.status not in [InvoiceStatus.VALIDATED, InvoiceStatus.SENT]:
            raise ValueError("La facture doit etre validee avant envoi")
        self.status = InvoiceStatus.SENT
        self.sent_date = date.today()

    def record_payment(self, amount, payment_date=None):
        """Record a payment"""
        self.amount_paid = (self.amount_paid or Decimal('0')) + Decimal(str(amount))
        self.amount_due = self.total_ttc - self.amount_paid

        if self.amount_due <= 0:
            self.status = InvoiceStatus.PAID
            self.paid_date = payment_date or date.today()
            self.amount_due = Decimal('0')
        elif self.amount_paid > 0:
            self.status = InvoiceStatus.PARTIAL


class InvoiceLine(db.Model):
    """Ligne de facture"""
    __tablename__ = 'invoice_lines'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)
    line_number = db.Column(db.Integer, nullable=False)    # Ordre de la ligne

    # Description
    description = db.Column(db.String(500), nullable=False)
    detail = db.Column(db.Text)                            # Details supplementaires
    reference = db.Column(db.String(50))                   # Reference article/service

    # Quantite et prix
    quantity = db.Column(db.Numeric(10, 3), nullable=False, default=1)
    unit = db.Column(db.String(20), default='unite')       # unite, jour, heure, forfait
    unit_price_ht = db.Column(db.Numeric(10, 2), nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2), default=0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)

    # TVA
    vat_rate = db.Column(db.Numeric(5, 2), default=20.00)  # Taux TVA (ex: 20.00)
    vat_amount = db.Column(db.Numeric(10, 2), default=0)

    # Totaux
    total_ht = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total_ttc = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    # Lien optionnel vers paiement
    payment_id = db.Column(db.Integer, db.ForeignKey('team_member_payments.id'), nullable=True)

    # Periode de prestation (si applicable)
    service_date_start = db.Column(db.Date)
    service_date_end = db.Column(db.Date)

    # Relations
    invoice = db.relationship('Invoice', backref=db.backref('lines', order_by='InvoiceLine.line_number', cascade='all, delete-orphan'))
    payment = db.relationship('TeamMemberPayment', backref='invoice_lines')

    def __repr__(self):
        return f'<InvoiceLine {self.line_number}: {self.description[:30]}>'

    def calculate_totals(self):
        """Calculate line totals"""
        # Total HT avant remise
        gross_ht = self.quantity * self.unit_price_ht

        # Appliquer remise
        if self.discount_percent:
            self.discount_amount = gross_ht * self.discount_percent / 100
        self.total_ht = gross_ht - (self.discount_amount or Decimal('0'))

        # TVA
        self.vat_amount = self.total_ht * (self.vat_rate or Decimal('0')) / 100

        # Total TTC
        self.total_ttc = self.total_ht + self.vat_amount


class InvoicePayment(db.Model):
    """Historique des paiements sur une facture"""
    __tablename__ = 'invoice_payments'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False, index=True)

    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_date = db.Column(db.Date, nullable=False, default=date.today)
    payment_method = db.Column(db.String(50))              # virement, cheque, CB, etc.
    reference = db.Column(db.String(100))                  # Reference du paiement
    bank_reference = db.Column(db.String(100))             # Reference bancaire

    notes = db.Column(db.Text)

    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relations
    invoice = db.relationship('Invoice', backref=db.backref('payments', order_by='InvoicePayment.payment_date'))
    created_by = db.relationship('User')

    def __repr__(self):
        return f'<InvoicePayment {self.amount} EUR on {self.payment_date}>'


# Configuration emetteur par defaut (GigRoute)
DEFAULT_ISSUER_CONFIG = {
    'name': 'GigRoute',
    'legal_form': 'SARL',
    'address_line1': '',
    'city': '',
    'postal_code': '',
    'country': 'FR',
    'siren': '',
    'siret': '',
    'vat': '',
    'rcs': '',
    'capital': '',
    'phone': '',
    'email': '',
    'iban': '',
    'bic': '',
}

# Mentions legales par defaut
DEFAULT_LEGAL_MENTIONS = {
    'payment_terms': 'Paiement a 30 jours date de facture',
    'late_penalty_rate': Decimal('12.00'),  # Taux BCE + 10 points (2026)
    'recovery_fee': Decimal('40.00'),       # Indemnite forfaitaire recouvrement
    'no_discount_mention': "Pas d'escompte pour paiement anticipe",
    'late_penalty_mention': "En cas de retard de paiement, une penalite de {rate}% par an sera appliquee, ainsi qu'une indemnite forfaitaire de {fee}EUR pour frais de recouvrement (art. L.441-10 et D.441-5 du Code de commerce)."
}
