"""
Invoice management forms - Factur-X compliant.
Forms for creating, editing, and filtering invoices.
"""
from datetime import date
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, DateField, SelectField,
    DecimalField, IntegerField, SubmitField, BooleanField, HiddenField
)
from wtforms.validators import DataRequired, Length, Optional, NumberRange

from app.models.invoices import InvoiceStatus, InvoiceType, VATRate


class InvoiceFilterForm(FlaskForm):
    """Filter form for invoice list."""

    tour_id = SelectField('Tournée', coerce=int, validators=[Optional()])
    status = SelectField('Statut', choices=[
        ('', 'Tous'),
        (InvoiceStatus.DRAFT.value, 'Brouillon'),
        (InvoiceStatus.VALIDATED.value, 'Validée'),
        (InvoiceStatus.SENT.value, 'Envoyée'),
        (InvoiceStatus.PAID.value, 'Payée'),
        (InvoiceStatus.PARTIAL.value, 'Partiellement payée'),
        (InvoiceStatus.OVERDUE.value, 'En retard'),
        (InvoiceStatus.DISPUTED.value, 'Contestée'),
        (InvoiceStatus.CANCELLED.value, 'Annulée'),
    ], validators=[Optional()])
    invoice_type = SelectField('Type', choices=[
        ('', 'Tous'),
        (InvoiceType.INVOICE.value, 'Facture'),
        (InvoiceType.CREDIT_NOTE.value, 'Avoir'),
        (InvoiceType.PROFORMA.value, 'Proforma'),
        (InvoiceType.DEPOSIT.value, 'Acompte'),
        (InvoiceType.FINAL.value, 'Solde'),
    ], validators=[Optional()])
    date_from = DateField('Du', validators=[Optional()])
    date_to = DateField('Au', validators=[Optional()])


class InvoiceForm(FlaskForm):
    """Form for creating/editing an invoice."""

    # Type
    type = SelectField('Type de facture', choices=[
        (InvoiceType.INVOICE.value, 'Facture'),
        (InvoiceType.PROFORMA.value, 'Proforma'),
        (InvoiceType.DEPOSIT.value, 'Acompte'),
        (InvoiceType.FINAL.value, 'Solde'),
    ], validators=[DataRequired(message='Type de facture requis')])

    # Context
    tour_id = SelectField('Tournée', coerce=int, validators=[Optional()])
    tour_stop_id = SelectField('Concert/Date', coerce=int, validators=[Optional()])

    # Issuer
    issuer_name = StringField('Nom emetteur', validators=[
        DataRequired(message="Nom de l'emetteur obligatoire"), Length(max=200)
    ])
    issuer_legal_form = StringField('Forme juridique', validators=[Optional(), Length(max=50)])
    issuer_address_line1 = StringField('Adresse', validators=[
        DataRequired(message="Adresse de l'emetteur obligatoire"), Length(max=200)
    ])
    issuer_address_line2 = StringField('Complement adresse', validators=[Optional(), Length(max=200)])
    issuer_city = StringField('Ville', validators=[DataRequired(), Length(max=100)])
    issuer_postal_code = StringField('Code postal', validators=[DataRequired(), Length(max=20)])
    issuer_country = StringField('Pays', validators=[Optional(), Length(max=2)], default='FR')
    issuer_siren = StringField('SIREN', validators=[Optional(), Length(min=9, max=9)])
    issuer_siret = StringField('SIRET', validators=[
        DataRequired(message="SIRET de l'emetteur obligatoire"), Length(min=14, max=14)
    ])
    issuer_vat = StringField('TVA intracommunautaire', validators=[Optional(), Length(max=20)])
    issuer_rcs = StringField('RCS', validators=[Optional(), Length(max=100)])
    issuer_capital = StringField('Capital social', validators=[Optional(), Length(max=50)])
    issuer_phone = StringField('Telephone', validators=[Optional(), Length(max=20)])
    issuer_email = StringField('Email', validators=[Optional(), Length(max=120)])
    issuer_iban = StringField('IBAN', validators=[Optional(), Length(max=34)])
    issuer_bic = StringField('BIC', validators=[Optional(), Length(max=11)])

    # Recipient
    recipient_id = SelectField('Destinataire (utilisateur)', coerce=int, validators=[Optional()])
    recipient_name = StringField('Nom destinataire', validators=[
        DataRequired(message='Nom du destinataire obligatoire'), Length(max=200)
    ])
    recipient_legal_form = StringField('Forme juridique', validators=[Optional(), Length(max=50)])
    recipient_address_line1 = StringField('Adresse', validators=[
        DataRequired(message='Adresse du destinataire obligatoire'), Length(max=200)
    ])
    recipient_address_line2 = StringField('Complement adresse', validators=[Optional(), Length(max=200)])
    recipient_city = StringField('Ville', validators=[DataRequired(), Length(max=100)])
    recipient_postal_code = StringField('Code postal', validators=[DataRequired(), Length(max=20)])
    recipient_country = StringField('Pays', validators=[Optional(), Length(max=2)], default='FR')
    recipient_siren = StringField('SIREN', validators=[Optional(), Length(min=9, max=9)])
    recipient_siret = StringField('SIRET', validators=[Optional(), Length(max=14)])
    recipient_vat = StringField('TVA intracommunautaire', validators=[Optional(), Length(max=20)])
    recipient_email = StringField('Email', validators=[Optional(), Length(max=120)])
    recipient_phone = StringField('Telephone', validators=[Optional(), Length(max=20)])

    # Dates
    issue_date = DateField("Date d'emission", validators=[
        DataRequired(message="Date d'emission obligatoire")
    ])
    due_date = DateField("Date d'echeance", validators=[
        DataRequired(message="Date d'echeance obligatoire")
    ])
    delivery_date = DateField('Date de prestation', validators=[Optional()])

    # Payment terms
    payment_terms = StringField('Conditions de paiement',
                                validators=[Optional(), Length(max=200)],
                                default='Paiement a 30 jours date de facture')
    payment_terms_days = IntegerField('Delai de paiement (jours)',
                                      validators=[Optional(), NumberRange(min=0, max=365)],
                                      default=30)
    payment_method_accepted = StringField('Mode de paiement accepte',
                                          validators=[Optional(), Length(max=200)],
                                          default='Virement bancaire')

    # Discount
    discount_amount = DecimalField('Remise globale (EUR)', validators=[Optional(), NumberRange(min=0)],
                                   places=2, default=0)

    # Legal mentions
    vat_mention = StringField('Mention TVA', validators=[Optional(), Length(max=200)])
    reverse_charge = BooleanField('Autoliquidation TVA', default=False)
    early_payment_discount = StringField("Conditions d'escompte", validators=[Optional(), Length(max=200)])
    no_discount_mention = BooleanField("Pas d'escompte pour paiement anticipe", default=True)
    special_mentions = TextAreaField('Mentions particulieres', validators=[Optional()])

    # Notes
    public_notes = TextAreaField('Notes visibles sur facture', validators=[Optional()])
    internal_notes = TextAreaField('Notes internes', validators=[Optional()])

    submit = SubmitField('Enregistrer')


class InvoiceLineForm(FlaskForm):
    """Form for invoice line items (used dynamically via JS)."""

    description = StringField('Description', validators=[
        DataRequired(message='Description obligatoire'), Length(max=500)
    ])
    detail = TextAreaField('Details', validators=[Optional()])
    reference = StringField('Reference', validators=[Optional(), Length(max=50)])

    quantity = DecimalField('Quantite', validators=[
        DataRequired(message='Quantite requise'), NumberRange(min=0)
    ], places=3, default=1)
    unit = SelectField('Unite', choices=[
        ('unite', 'Unite'),
        ('jour', 'Jour'),
        ('heure', 'Heure'),
        ('forfait', 'Forfait'),
        ('concert', 'Concert'),
        ('mois', 'Mois'),
    ], default='unite')
    unit_price_ht = DecimalField('Prix unitaire HT', validators=[
        DataRequired(message='Prix unitaire requis'), NumberRange(min=0)
    ], places=2)
    vat_rate = SelectField('Taux TVA', choices=[
        ('20.00', '20% (Normal)'),
        ('10.00', '10% (Intermediaire)'),
        ('5.50', '5.5% (Reduit)'),
        ('2.10', '2.1% (Super-reduit)'),
        ('0.00', '0% (Exonere)'),
    ], default='20.00')
    discount_percent = DecimalField('Remise (%)', validators=[
        Optional(), NumberRange(min=0, max=100)
    ], places=2, default=0)

    service_date_start = DateField('Debut prestation', validators=[Optional()])
    service_date_end = DateField('Fin prestation', validators=[Optional()])


class InvoicePaymentForm(FlaskForm):
    """Form for recording a payment on an invoice."""

    amount = DecimalField('Montant', validators=[
        DataRequired(message='Montant obligatoire'), NumberRange(min=0.01)
    ], places=2)
    payment_date = DateField('Date de paiement', validators=[
        DataRequired(message='Date obligatoire')
    ])
    payment_method = SelectField('Mode de paiement', choices=[
        ('virement', 'Virement bancaire'),
        ('cheque', 'Cheque'),
        ('cb', 'Carte bancaire'),
        ('especes', 'Especes'),
        ('autre', 'Autre'),
    ], default='virement')
    reference = StringField('Reference paiement', validators=[Optional(), Length(max=100)])
    bank_reference = StringField('Reference bancaire', validators=[Optional(), Length(max=100)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])

    submit = SubmitField('Enregistrer le paiement')
