"""
Settings forms - User management forms for managers.
Includes access levels, professions, and labels (v2.0).
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, BooleanField, SelectMultipleField,
    SubmitField, DateField, SelectField, TextAreaField, DecimalField,
    IntegerField
)
from wtforms.validators import (
    DataRequired, Email, Length, Optional, EqualTo, ValidationError, NumberRange
)

from app.extensions import db
from app.models.user import User, AccessLevel, ACCESS_LEVEL_LABELS
from app.models.profession import Profession, ProfessionCategory, CATEGORY_LABELS, CATEGORY_ICONS, CATEGORY_COLORS
from app.models.payments import ContractType, PaymentFrequency


def coerce_int_or_none(value):
    """Coerce function that handles empty strings for SelectField with optional int values."""
    if value is None or value == '' or value == 'None':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def get_access_level_choices():
    """Get access level choices for select field."""
    return [
        (level.name, ACCESS_LEVEL_LABELS.get(level, level.value))
        for level in AccessLevel
    ]


# get_label_choices() removed - label is now a free text field


def get_profession_choices():
    """Get profession choices grouped by category."""
    choices = []
    for category in ProfessionCategory:
        profs = Profession.query.filter_by(category=category, is_active=True).order_by(Profession.sort_order).all()
        for p in profs:
            # Use int (p.id) to match coerce=int in SelectMultipleField
            choices.append((p.id, f"{p.name_fr}"))
    return choices


def get_professions_by_category():
    """Get professions organized by category for template rendering."""
    result = {}
    for category in ProfessionCategory:
        profs = Profession.query.filter_by(category=category, is_active=True).order_by(Profession.sort_order).all()
        if profs:
            result[category] = {
                'label': CATEGORY_LABELS.get(category, category.value),
                'professions': profs
            }
    return result


class UserCreateForm(FlaskForm):
    """Form for creating a new user."""

    email = StringField('Email', validators=[
        DataRequired(message='L\'email est requis'),
        Email(message='Adresse email invalide'),
        Length(max=120)
    ])
    first_name = StringField('Prénom', validators=[
        DataRequired(message='Le prénom est requis'),
        Length(max=50)
    ])
    last_name = StringField('Nom', validators=[
        DataRequired(message='Le nom est requis'),
        Length(max=50)
    ])
    phone = StringField('Téléphone', validators=[
        Optional(),
        Length(max=20)
    ])

    # ============ PERMISSIONS & IDENTITY (v2.0) ============
    access_level = SelectField('Niveau d\'accès', validators=[
        DataRequired(message='Le niveau d\'accès est requis')
    ])
    label_name = StringField('Label', validators=[Optional(), Length(max=200)])
    profession = SelectField('Profession', coerce=coerce_int_or_none, validators=[Optional()])

    # Master email preference
    receive_emails = BooleanField('Recevoir les emails de l\'application', default=True)

    # Legacy roles field (deprecated, kept for backwards compatibility)
    roles = SelectMultipleField('Rôles (legacy)', coerce=int, validators=[Optional()])

    # Personal information
    date_of_birth = DateField('Date de naissance', validators=[Optional()])
    nationality = StringField('Nationalité', validators=[Optional(), Length(max=100)])

    # Travel preferences
    preferred_airline = StringField('Compagnie aérienne', validators=[Optional(), Length(max=100)])
    seat_preference = SelectField('Préférence siège', choices=[
        ('', 'Pas de préférence'),
        ('window', 'Hublot'),
        ('aisle', 'Couloir'),
        ('middle', 'Milieu')
    ], validators=[Optional()])
    meal_preference = SelectField('Préférence repas', choices=[
        ('', 'Standard'),
        ('vegetarian', 'Végétarien'),
        ('vegan', 'Végan'),
        ('halal', 'Halal'),
        ('kosher', 'Casher'),
        ('gluten_free', 'Sans gluten'),
        ('lactose_free', 'Sans lactose')
    ], validators=[Optional()])
    hotel_preferences = TextAreaField('Préférences hôtel', validators=[Optional(), Length(max=500)])

    # Emergency contact
    emergency_contact_name = StringField('Nom du contact', validators=[Optional(), Length(max=100)])
    emergency_contact_relation = StringField('Relation', validators=[Optional(), Length(max=50)])
    emergency_contact_phone = StringField('Téléphone urgence', validators=[Optional(), Length(max=20)])
    emergency_contact_email = StringField('Email urgence', validators=[Optional(), Email(), Length(max=120)])

    # Health / Dietary
    dietary_restrictions = TextAreaField('Restrictions alimentaires', validators=[Optional(), Length(max=500)])
    allergies = TextAreaField('Allergies', validators=[Optional(), Length(max=500)])

    # ============ FACTURATION & PAIEMENT ============
    # Note: staff_category et staff_role supprimés - utiliser professions à la place

    contract_type = SelectField('Type de contrat', choices=[
        ('', '-- Sélectionner --'),
        ('cddu', 'CDDU (Intermittent)'),
        ('cdd', 'CDD'),
        ('cdi', 'CDI'),
        ('freelance', 'Auto-entrepreneur'),
        ('prestation', 'Prestation (société)'),
        ('guso', 'GUSO')
    ], validators=[Optional()])

    payment_frequency = SelectField('Fréquence de paiement', choices=[
        ('', '-- Sélectionner --'),
        ('per_show', 'Par concert'),
        ('daily', 'Journalier'),
        ('half_day', 'Demi-journée'),
        ('weekly', 'Hebdomadaire'),
        ('hourly', 'Horaire'),
        ('fixed', 'Forfait'),
        ('monthly', 'Mensuel')
    ], validators=[Optional()])

    # Taux standards
    show_rate = DecimalField('Tarif concert (€)', validators=[Optional(), NumberRange(min=0)])
    daily_rate = DecimalField('Tarif journalier (€)', validators=[Optional(), NumberRange(min=0)])
    half_day_rate = DecimalField('Tarif demi-journée (€)', validators=[Optional(), NumberRange(min=0)])
    hourly_rate = DecimalField('Tarif horaire (€)', validators=[Optional(), NumberRange(min=0)])
    per_diem = DecimalField('Per diem (€)', validators=[Optional(), NumberRange(min=0)], default=35.00)

    # Majorations
    overtime_rate_25 = DecimalField('Majoration +25% (multiplicateur)', validators=[Optional()], default=1.25)
    overtime_rate_50 = DecimalField('Majoration +50% (multiplicateur)', validators=[Optional()], default=1.50)
    weekend_rate = DecimalField('Majoration weekend', validators=[Optional()], default=1.25)
    holiday_rate = DecimalField('Majoration jours fériés', validators=[Optional()], default=2.00)
    night_rate = DecimalField('Majoration nuit', validators=[Optional()], default=1.25)

    # Informations bancaires SEPA
    iban = StringField('IBAN', validators=[Optional(), Length(max=34)])
    bic = StringField('BIC', validators=[Optional(), Length(max=11)])
    bank_name = StringField('Nom de la banque', validators=[Optional(), Length(max=100)])
    account_holder = StringField('Titulaire du compte', validators=[Optional(), Length(max=200)])

    # Informations fiscales
    siret = StringField('SIRET', validators=[Optional(), Length(max=14)])
    siren = StringField('SIREN', validators=[Optional(), Length(max=9)])
    vat_number = StringField('N° TVA intracommunautaire', validators=[Optional(), Length(max=20)])

    submit = SubmitField('Créer et envoyer l\'invitation')

    def validate_email(self, field):
        """Check if email is already registered."""
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('Cette adresse email est déjà utilisée.')

    def validate_last_name(self, field):
        """Warn if a user with the same first+last name already exists."""
        if self.first_name.data and field.data:
            existing = User.query.filter(
                db.func.lower(User.first_name) == self.first_name.data.lower(),
                db.func.lower(User.last_name) == field.data.lower()
            ).first()
            if existing:
                raise ValidationError(
                    f'Un utilisateur "{existing.first_name} {existing.last_name}" existe déjà ({existing.email}). '
                    'Vérifiez qu\'il ne s\'agit pas d\'un doublon.'
                )


class UserEditForm(FlaskForm):
    """Form for editing an existing user."""

    email = StringField('Email', validators=[
        DataRequired(message='L\'email est requis'),
        Email(message='Adresse email invalide'),
        Length(max=120)
    ])
    first_name = StringField('Prénom', validators=[
        DataRequired(message='Le prénom est requis'),
        Length(max=50)
    ])
    last_name = StringField('Nom', validators=[
        DataRequired(message='Le nom est requis'),
        Length(max=50)
    ])
    phone = StringField('Téléphone', validators=[
        Optional(),
        Length(max=20)
    ])

    # ============ PERMISSIONS & IDENTITY (v2.0) ============
    access_level = SelectField('Niveau d\'accès', validators=[
        DataRequired(message='Le niveau d\'accès est requis')
    ])
    label_name = StringField('Label', validators=[Optional(), Length(max=200)])
    profession = SelectField('Profession', coerce=coerce_int_or_none, validators=[Optional()])

    # Master email preference
    receive_emails = BooleanField('Recevoir les emails de l\'application')

    # Legacy roles field (deprecated, kept for backwards compatibility)
    roles = SelectMultipleField('Rôles (legacy)', coerce=int, validators=[Optional()])
    is_active = BooleanField('Compte actif')

    # Personal information
    date_of_birth = DateField('Date de naissance', validators=[Optional()])
    nationality = StringField('Nationalité', validators=[Optional(), Length(max=100)])

    # Travel preferences
    preferred_airline = StringField('Compagnie aérienne', validators=[Optional(), Length(max=100)])
    seat_preference = SelectField('Préférence siège', choices=[
        ('', 'Pas de préférence'),
        ('window', 'Hublot'),
        ('aisle', 'Couloir'),
        ('middle', 'Milieu')
    ], validators=[Optional()])
    meal_preference = SelectField('Préférence repas', choices=[
        ('', 'Standard'),
        ('vegetarian', 'Végétarien'),
        ('vegan', 'Végan'),
        ('halal', 'Halal'),
        ('kosher', 'Casher'),
        ('gluten_free', 'Sans gluten'),
        ('lactose_free', 'Sans lactose')
    ], validators=[Optional()])
    hotel_preferences = TextAreaField('Préférences hôtel', validators=[Optional(), Length(max=500)])

    # Emergency contact
    emergency_contact_name = StringField('Nom du contact', validators=[Optional(), Length(max=100)])
    emergency_contact_relation = StringField('Relation', validators=[Optional(), Length(max=50)])
    emergency_contact_phone = StringField('Téléphone urgence', validators=[Optional(), Length(max=20)])
    emergency_contact_email = StringField('Email urgence', validators=[Optional(), Email(), Length(max=120)])

    # Health / Dietary
    dietary_restrictions = TextAreaField('Restrictions alimentaires', validators=[Optional(), Length(max=500)])
    allergies = TextAreaField('Allergies', validators=[Optional(), Length(max=500)])

    # ============ FACTURATION & PAIEMENT ============
    # Note: staff_category et staff_role supprimés - utiliser professions à la place

    contract_type = SelectField('Type de contrat', choices=[
        ('', '-- Sélectionner --'),
        ('cddu', 'CDDU (Intermittent)'),
        ('cdd', 'CDD'),
        ('cdi', 'CDI'),
        ('freelance', 'Auto-entrepreneur'),
        ('prestation', 'Prestation (société)'),
        ('guso', 'GUSO')
    ], validators=[Optional()])

    payment_frequency = SelectField('Fréquence de paiement', choices=[
        ('', '-- Sélectionner --'),
        ('per_show', 'Par concert'),
        ('daily', 'Journalier'),
        ('half_day', 'Demi-journée'),
        ('weekly', 'Hebdomadaire'),
        ('hourly', 'Horaire'),
        ('fixed', 'Forfait'),
        ('monthly', 'Mensuel')
    ], validators=[Optional()])

    # Taux standards
    show_rate = DecimalField('Tarif concert (€)', validators=[Optional(), NumberRange(min=0)])
    daily_rate = DecimalField('Tarif journalier (€)', validators=[Optional(), NumberRange(min=0)])
    half_day_rate = DecimalField('Tarif demi-journée (€)', validators=[Optional(), NumberRange(min=0)])
    hourly_rate = DecimalField('Tarif horaire (€)', validators=[Optional(), NumberRange(min=0)])
    per_diem = DecimalField('Per diem (€)', validators=[Optional(), NumberRange(min=0)], default=35.00)

    # Majorations
    overtime_rate_25 = DecimalField('Majoration +25% (multiplicateur)', validators=[Optional()], default=1.25)
    overtime_rate_50 = DecimalField('Majoration +50% (multiplicateur)', validators=[Optional()], default=1.50)
    weekend_rate = DecimalField('Majoration weekend', validators=[Optional()], default=1.25)
    holiday_rate = DecimalField('Majoration jours fériés', validators=[Optional()], default=2.00)
    night_rate = DecimalField('Majoration nuit', validators=[Optional()], default=1.25)

    # Informations bancaires SEPA
    iban = StringField('IBAN', validators=[Optional(), Length(max=34)])
    bic = StringField('BIC', validators=[Optional(), Length(max=11)])
    bank_name = StringField('Nom de la banque', validators=[Optional(), Length(max=100)])
    account_holder = StringField('Titulaire du compte', validators=[Optional(), Length(max=200)])

    # Informations fiscales
    siret = StringField('SIRET', validators=[Optional(), Length(max=14)])
    siren = StringField('SIREN', validators=[Optional(), Length(max=9)])
    vat_number = StringField('N° TVA intracommunautaire', validators=[Optional(), Length(max=20)])

    submit = SubmitField('Enregistrer les modifications')

    def __init__(self, original_email=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_email = original_email

    def validate_email(self, field):
        """Check if email is already used by another user."""
        if field.data.lower() != self.original_email:
            if User.query.filter_by(email=field.data.lower()).first():
                raise ValidationError('Cette adresse email est déjà utilisée.')


class SetPasswordForm(FlaskForm):
    """Form for setting password on invitation acceptance."""

    password = PasswordField('Mot de passe', validators=[
        DataRequired(message='Le mot de passe est requis'),
        Length(min=8, message='Le mot de passe doit contenir au moins 8 caractères')
    ])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[
        DataRequired(message='Veuillez confirmer le mot de passe'),
        EqualTo('password', message='Les mots de passe ne correspondent pas')
    ])
    submit = SubmitField('Définir mon mot de passe')


class TravelCardForm(FlaskForm):
    """Form for adding/editing a travel card."""

    card_number = StringField('Numéro de carte', validators=[
        DataRequired(message='Le numéro de carte est requis'),
        Length(max=50)
    ])
    card_type = SelectField('Type de carte', choices=[
        ('loyalty_airline', 'Fidélité aérienne'),
        ('rail_subscription', 'Abonnement rail (SNCF, Eurostar...)'),
        ('car_rental', 'Carte loueur (Hertz, Avis...)'),
        ('hotel_loyalty', 'Fidélité hôtel'),
        ('other', 'Autre')
    ], validators=[DataRequired(message='Le type de carte est requis')])
    card_name = StringField('Nom de la carte', validators=[
        Optional(),
        Length(max=100)
    ])
    expiry_date = DateField('Date de validité', validators=[Optional()])


# =============================================================================
# PROFESSION MANAGEMENT FORMS
# =============================================================================

def get_category_choices():
    """Get profession category choices for select field."""
    return [
        (cat.name, CATEGORY_LABELS.get(cat, cat.value))
        for cat in ProfessionCategory
    ]


class ProfessionCreateForm(FlaskForm):
    """Form for creating a new profession."""

    code = StringField('Code', validators=[
        DataRequired(message='Le code est requis'),
        Length(max=50)
    ])
    name_fr = StringField('Nom (FR)', validators=[
        DataRequired(message='Le nom français est requis'),
        Length(max=100)
    ])
    name_en = StringField('Nom (EN)', validators=[
        DataRequired(message='Le nom anglais est requis'),
        Length(max=100)
    ])
    category = SelectField('Catégorie', validators=[
        DataRequired(message='La catégorie est requise')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500)
    ])
    sort_order = IntegerField('Ordre d\'affichage', validators=[Optional()], default=0)
    default_access_level = SelectField('Niveau d\'accès par défaut', validators=[
        DataRequired(message='Le niveau d\'accès est requis')
    ])
    is_active = BooleanField('Active', default=True)

    # Default rates
    show_rate = DecimalField('Tarif concert (€)', validators=[Optional(), NumberRange(min=0)])
    daily_rate = DecimalField('Tarif journalier (€)', validators=[Optional(), NumberRange(min=0)])
    weekly_rate = DecimalField('Tarif hebdomadaire (€)', validators=[Optional(), NumberRange(min=0)])
    per_diem = DecimalField('Per diem (€)', validators=[Optional(), NumberRange(min=0)], default=35.00)
    default_frequency = SelectField('Fréquence par défaut', choices=[
        ('per_show', 'Par concert'),
        ('daily', 'Journalier'),
        ('weekly', 'Hebdomadaire'),
        ('monthly', 'Mensuel')
    ], validators=[Optional()])

    submit = SubmitField('Créer la profession')

    def validate_code(self, field):
        """Check if code is unique."""
        if Profession.query.filter_by(code=field.data.upper()).first():
            raise ValidationError('Ce code est déjà utilisé.')


class ProfessionEditForm(FlaskForm):
    """Form for editing an existing profession."""

    code = StringField('Code', validators=[
        DataRequired(message='Le code est requis'),
        Length(max=50)
    ])
    name_fr = StringField('Nom (FR)', validators=[
        DataRequired(message='Le nom français est requis'),
        Length(max=100)
    ])
    name_en = StringField('Nom (EN)', validators=[
        DataRequired(message='Le nom anglais est requis'),
        Length(max=100)
    ])
    category = SelectField('Catégorie', validators=[
        DataRequired(message='La catégorie est requise')
    ])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=500)
    ])
    sort_order = IntegerField('Ordre d\'affichage', validators=[Optional()], default=0)
    default_access_level = SelectField('Niveau d\'accès par défaut', validators=[
        DataRequired(message='Le niveau d\'accès est requis')
    ])
    is_active = BooleanField('Active', default=True)

    # Default rates
    show_rate = DecimalField('Tarif concert (€)', validators=[Optional(), NumberRange(min=0)])
    daily_rate = DecimalField('Tarif journalier (€)', validators=[Optional(), NumberRange(min=0)])
    weekly_rate = DecimalField('Tarif hebdomadaire (€)', validators=[Optional(), NumberRange(min=0)])
    per_diem = DecimalField('Per diem (€)', validators=[Optional(), NumberRange(min=0)])
    default_frequency = SelectField('Fréquence par défaut', choices=[
        ('per_show', 'Par concert'),
        ('daily', 'Journalier'),
        ('weekly', 'Hebdomadaire'),
        ('monthly', 'Mensuel')
    ], validators=[Optional()])

    submit = SubmitField('Enregistrer les modifications')

    def __init__(self, original_code=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_code = original_code

    def validate_code(self, field):
        """Check if code is unique (excluding current)."""
        if field.data.upper() != self.original_code:
            if Profession.query.filter_by(code=field.data.upper()).first():
                raise ValidationError('Ce code est déjà utilisé.')
