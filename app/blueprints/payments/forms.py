"""
Payment management forms - Enterprise-Grade.
Forms for team member payments, per diems, and payment configuration.
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, DateField, SelectField,
    DecimalField, IntegerField, SubmitField, BooleanField,
    DateTimeLocalField, HiddenField
)
from wtforms.validators import DataRequired, Length, Optional, NumberRange, ValidationError
from decimal import Decimal

from app.models.payments import (
    StaffCategory, StaffRole, ContractType, PaymentFrequency,
    PaymentType, PaymentStatus, PaymentMethod
)


class PaymentForm(FlaskForm):
    """Form for creating/editing a team member payment."""

    # Beneficiaire
    user_id = SelectField('Membre equipe', coerce=int, validators=[
        DataRequired(message='Veuillez selectionner un membre')
    ])

    # Tournee/Concert (optionnel selon contexte)
    tour_id = SelectField('Tournée', coerce=int, validators=[Optional()])
    tour_stop_id = SelectField('Concert/Date', coerce=int, validators=[Optional()])

    # Classification
    staff_category = SelectField('Categorie', choices=[
        ('', '-- Selectionner --'),
        (StaffCategory.ARTISTIC.value, 'Artistique (Musiciens, Choristes)'),
        (StaffCategory.TECHNICAL.value, 'Technique (Son, Lumiere, Backline)'),
        (StaffCategory.MANAGEMENT.value, 'Management (TM, PM)'),
        (StaffCategory.SUPPORT.value, 'Support (Securite, Chauffeurs)'),
        (StaffCategory.EXTERNAL.value, 'Externe (Crew local, Prestataires)')
    ], validators=[DataRequired(message='La categorie est requise')])

    staff_role = SelectField('Role', choices=[
        ('', '-- Selectionner --'),
        # ARTISTIC
        ('LEAD_MUSICIAN', 'Musicien principal'),
        ('MUSICIAN', 'Musicien'),
        ('BACKING_VOCALIST', 'Choriste'),
        ('DANCER', 'Danseur'),
        # TECHNICAL - Audio
        ('FOH_ENGINEER', 'Ingenieur son facade'),
        ('MONITOR_ENGINEER', 'Ingenieur retours'),
        ('AUDIO_TECH', 'Technicien audio'),
        # TECHNICAL - Lighting
        ('LIGHTING_DIRECTOR', 'Directeur lumiere'),
        ('LIGHTING_TECH', 'Technicien lumiere'),
        ('VIDEO_TECH', 'Technicien video'),
        # TECHNICAL - Stage
        ('STAGE_MANAGER', 'Regisseur'),
        ('STAGEHAND', 'Technicien plateau'),
        ('RIGGER', 'Rigger'),
        # TECHNICAL - Backline
        ('GUITAR_TECH', 'Tech guitare'),
        ('BASS_TECH', 'Tech basse'),
        ('DRUM_TECH', 'Tech batterie'),
        ('KEYBOARD_TECH', 'Tech clavier'),
        # MANAGEMENT
        ('TOUR_MANAGER', 'Tour Manager'),
        ('PRODUCTION_MANAGER', 'Directeur de production'),
        ('PRODUCTION_ASSISTANT', 'Assistant production'),
        ('TOUR_COORDINATOR', 'Coordinateur tournee'),
        # SUPPORT
        ('SECURITY', 'Agent securite'),
        ('DRIVER', 'Chauffeur'),
        ('CHEF', 'Chef/Cuisinier'),
        ('CATERING_STAFF', 'Staff catering'),
        ('WARDROBE', 'Costumier/Habilleur'),
        ('HAIR_MAKEUP', 'Coiffure/Maquillage'),
        # EXTERNAL
        ('LOCAL_CREW', 'Crew local'),
        ('LOCAL_DRIVER', 'Chauffeur local'),
        ('CONTRACTOR', 'Prestataire externe')
    ], validators=[Optional()])

    # Type de paiement
    payment_type = SelectField('Type de paiement', choices=[
        (PaymentType.CACHET.value, 'Cachet'),
        (PaymentType.PER_DIEM.value, 'Per Diem'),
        (PaymentType.OVERTIME.value, 'Heures supplementaires'),
        (PaymentType.BONUS.value, 'Prime/Bonus'),
        (PaymentType.REIMBURSEMENT.value, 'Remboursement'),
        (PaymentType.ADVANCE.value, 'Avance'),
        (PaymentType.TRAVEL_ALLOWANCE.value, 'Indemnite deplacement'),
        (PaymentType.MEAL_ALLOWANCE.value, 'Indemnite repas')
    ], validators=[DataRequired()])

    payment_frequency = SelectField('Frequence', choices=[
        ('', '-- Selectionner --'),
        (PaymentFrequency.PER_SHOW.value, 'Par concert'),
        (PaymentFrequency.DAILY.value, 'Journalier'),
        (PaymentFrequency.WEEKLY.value, 'Hebdomadaire'),
        (PaymentFrequency.HOURLY.value, 'Horaire'),
        (PaymentFrequency.FIXED.value, 'Forfait')
    ], validators=[Optional()])

    # Description
    description = StringField('Description', validators=[
        Length(max=255)
    ])

    # Montants
    quantity = DecimalField('Quantite', validators=[
        Optional(),
        NumberRange(min=0)
    ], places=2, default=1)

    unit_rate = DecimalField('Taux unitaire (EUR)', validators=[
        Optional(),
        NumberRange(min=0)
    ], places=2)

    amount = DecimalField('Montant total (EUR)', validators=[
        DataRequired(message='Le montant est requis'),
        NumberRange(min=0)
    ], places=2)

    currency = SelectField('Devise', choices=[
        ('EUR', 'EUR - Euro'),
        ('USD', 'USD - Dollar US'),
        ('GBP', 'GBP - Livre Sterling'),
        ('CHF', 'CHF - Franc Suisse')
    ], default='EUR')

    # Dates
    work_date = DateField('Date de travail', validators=[Optional()])
    due_date = DateField('Date echeance', validators=[Optional()])

    # Methode de paiement
    payment_method = SelectField('Methode de paiement', choices=[
        ('', '-- Selectionner --'),
        (PaymentMethod.BANK_TRANSFER.value, 'Virement bancaire'),
        (PaymentMethod.SEPA.value, 'Virement SEPA'),
        (PaymentMethod.CHECK.value, 'Cheque'),
        (PaymentMethod.CASH.value, 'Especes'),
        (PaymentMethod.PAYPAL.value, 'PayPal'),
        (PaymentMethod.OTHER.value, 'Autre')
    ], validators=[Optional()])

    notes = TextAreaField('Notes', validators=[Length(max=1000)])

    submit = SubmitField('Enregistrer')


class PerDiemBatchForm(FlaskForm):
    """Form for generating per diems for a tour."""

    tour_id = SelectField('Tournée', coerce=int, validators=[
        DataRequired(message='Veuillez selectionner une tournee')
    ])

    per_diem_amount = DecimalField('Montant per diem (EUR)', validators=[
        DataRequired(),
        NumberRange(min=0, max=200)
    ], places=2, default=35.00)

    include_travel_days = BooleanField('Inclure jours de voyage', default=True)
    include_day_offs = BooleanField('Inclure jours off', default=True)

    # Selection des membres
    member_ids = SelectField('Membres', choices=[], validators=[Optional()])

    notes = TextAreaField('Notes', validators=[Length(max=500)])

    submit = SubmitField('Generer les per diems')


class UserPaymentConfigForm(FlaskForm):
    """Form for configuring a team member's payment defaults."""

    # Classification
    staff_category = SelectField('Categorie', choices=[
        ('', '-- Selectionner --'),
        (StaffCategory.ARTISTIC.value, 'Artistique'),
        (StaffCategory.TECHNICAL.value, 'Technique'),
        (StaffCategory.MANAGEMENT.value, 'Management'),
        (StaffCategory.SUPPORT.value, 'Support'),
        (StaffCategory.EXTERNAL.value, 'Externe')
    ], validators=[DataRequired()])

    staff_role = SelectField('Role principal', choices=[
        ('', '-- Selectionner --'),
        # Options dynamiquement chargees selon categorie
    ], validators=[Optional()])

    contract_type = SelectField('Type de contrat', choices=[
        ('', '-- Selectionner --'),
        (ContractType.CDDU.value, 'CDDU (Intermittent)'),
        (ContractType.CDD.value, 'CDD'),
        (ContractType.CDI.value, 'CDI'),
        (ContractType.FREELANCE.value, 'Auto-entrepreneur'),
        (ContractType.PRESTATION.value, 'Prestation (Societe)'),
        (ContractType.GUSO.value, 'GUSO')
    ], validators=[Optional()])

    payment_frequency = SelectField('Frequence de paiement', choices=[
        ('', '-- Selectionner --'),
        (PaymentFrequency.PER_SHOW.value, 'Par concert'),
        (PaymentFrequency.DAILY.value, 'Journalier'),
        (PaymentFrequency.WEEKLY.value, 'Hebdomadaire'),
        (PaymentFrequency.HOURLY.value, 'Horaire'),
        (PaymentFrequency.FIXED.value, 'Forfait')
    ], validators=[Optional()])

    # Taux par defaut
    show_rate = DecimalField('Taux par concert (EUR)', validators=[
        Optional(), NumberRange(min=0)
    ], places=2)

    daily_rate = DecimalField('Taux journalier (EUR)', validators=[
        Optional(), NumberRange(min=0)
    ], places=2)

    half_day_rate = DecimalField('Taux demi-journee (EUR)', validators=[
        Optional(), NumberRange(min=0)
    ], places=2)

    weekly_rate = DecimalField('Taux hebdomadaire (EUR)', validators=[
        Optional(), NumberRange(min=0)
    ], places=2)

    hourly_rate = DecimalField('Taux horaire (EUR)', validators=[
        Optional(), NumberRange(min=0)
    ], places=2)

    per_diem = DecimalField('Per diem (EUR)', validators=[
        Optional(), NumberRange(min=0, max=200)
    ], places=2, default=35.00)

    # Majorations
    overtime_rate_25 = DecimalField('Majoration +25% (coef)', validators=[
        Optional(), NumberRange(min=1, max=3)
    ], places=2, default=1.25)

    overtime_rate_50 = DecimalField('Majoration +50% (coef)', validators=[
        Optional(), NumberRange(min=1, max=3)
    ], places=2, default=1.50)

    weekend_rate = DecimalField('Majoration weekend (coef)', validators=[
        Optional(), NumberRange(min=1, max=3)
    ], places=2, default=1.25)

    holiday_rate = DecimalField('Majoration jours feries (coef)', validators=[
        Optional(), NumberRange(min=1, max=4)
    ], places=2, default=2.00)

    # Informations bancaires (SEPA)
    iban = StringField('IBAN', validators=[
        Optional(), Length(min=15, max=34)
    ])

    bic = StringField('BIC/SWIFT', validators=[
        Optional(), Length(min=8, max=11)
    ])

    bank_name = StringField('Nom de la banque', validators=[
        Optional(), Length(max=100)
    ])

    # Informations fiscales/sociales (France)
    siret = StringField('SIRET (si auto-entrepreneur/societe)', validators=[
        Optional(), Length(min=14, max=14)
    ])

    siren = StringField('SIREN', validators=[
        Optional(), Length(min=9, max=9)
    ])

    vat_number = StringField('Numéro TVA intracommunautaire', validators=[
        Optional(), Length(max=20)
    ])

    social_security_number = StringField('Numéro sécurité sociale', validators=[
        Optional(), Length(max=15)
    ])

    is_intermittent = BooleanField('Statut intermittent du spectacle', default=False)

    conges_spectacle_id = StringField('Numéro Congés Spectacles', validators=[
        Optional(), Length(max=20)
    ])

    audiens_id = StringField('Numéro Audiens', validators=[
        Optional(), Length(max=20)
    ])

    intermittent_id = StringField('Numéro Pôle Emploi Spectacle', validators=[
        Optional(), Length(max=20)
    ])

    notes = TextAreaField('Notes', validators=[Length(max=1000)])

    submit = SubmitField('Enregistrer la configuration')


class PaymentApprovalForm(FlaskForm):
    """Form for approving/rejecting a payment."""

    payment_id = HiddenField()
    action = SelectField('Action', choices=[
        ('approve', 'Approuver'),
        ('reject', 'Rejeter')
    ], validators=[DataRequired()])

    rejection_reason = TextAreaField('Motif de rejet', validators=[
        Optional(), Length(max=500)
    ])

    submit = SubmitField('Valider')


class PaymentFilterForm(FlaskForm):
    """Form for filtering payments list."""

    tour_id = SelectField('Tournée', coerce=int, validators=[Optional()])
    user_id = SelectField('Membre', coerce=int, validators=[Optional()])

    status = SelectField('Statut', choices=[
        ('', 'Tous'),
        (PaymentStatus.DRAFT.value, 'Brouillon'),
        (PaymentStatus.PENDING_APPROVAL.value, 'En attente'),
        (PaymentStatus.APPROVED.value, 'Approuve'),
        (PaymentStatus.SCHEDULED.value, 'Programme'),
        (PaymentStatus.PAID.value, 'Paye'),
        (PaymentStatus.CANCELLED.value, 'Annule')
    ], validators=[Optional()])

    payment_type = SelectField('Type', choices=[
        ('', 'Tous'),
        (PaymentType.CACHET.value, 'Cachets'),
        (PaymentType.PER_DIEM.value, 'Per Diems'),
        (PaymentType.OVERTIME.value, 'Heures sup.'),
        (PaymentType.BONUS.value, 'Bonus'),
        (PaymentType.REIMBURSEMENT.value, 'Remboursements'),
        (PaymentType.ADVANCE.value, 'Avances')
    ], validators=[Optional()])

    staff_category = SelectField('Categorie', choices=[
        ('', 'Toutes'),
        (StaffCategory.ARTISTIC.value, 'Artistique'),
        (StaffCategory.TECHNICAL.value, 'Technique'),
        (StaffCategory.MANAGEMENT.value, 'Management'),
        (StaffCategory.SUPPORT.value, 'Support'),
        (StaffCategory.EXTERNAL.value, 'Externe')
    ], validators=[Optional()])

    date_from = DateField('Du', validators=[Optional()])
    date_to = DateField('Au', validators=[Optional()])

    submit = SubmitField('Filtrer')


class BatchPaymentForm(FlaskForm):
    """Form for creating batch payments (e.g., all per diems for a tour stop)."""

    tour_stop_id = SelectField('Concert/Date', coerce=int, validators=[
        DataRequired(message='Veuillez selectionner un concert')
    ])

    payment_type = SelectField('Type de paiement', choices=[
        (PaymentType.CACHET.value, 'Cachets'),
        (PaymentType.PER_DIEM.value, 'Per Diems')
    ], validators=[DataRequired()])

    apply_default_rates = BooleanField('Appliquer les taux par defaut', default=True)

    notes = TextAreaField('Notes', validators=[Length(max=500)])

    submit = SubmitField('Generer les paiements')
