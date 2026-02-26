"""
Forms for document management.
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SelectField, TextAreaField, DateField
from wtforms.validators import DataRequired, Optional, Length

from app.models.document import DocumentType


class DocumentUploadForm(FlaskForm):
    """Form for uploading a new document."""

    name = StringField(
        'Nom du document',
        validators=[DataRequired(message='Le nom est requis'), Length(max=200)]
    )

    document_type = SelectField(
        'Type de document',
        choices=[
            (DocumentType.PASSPORT.value, 'Passeport'),
            (DocumentType.VISA.value, 'Visa'),
            (DocumentType.CONTRACT.value, 'Contrat'),
            (DocumentType.RIDER.value, 'Rider technique'),
            (DocumentType.INSURANCE.value, 'Assurance'),
            (DocumentType.WORK_PERMIT.value, 'Permis de travail'),
            (DocumentType.OTHER.value, 'Autre'),
        ],
        validators=[DataRequired()]
    )

    file = FileField(
        'Fichier',
        validators=[
            FileRequired(message='Veuillez selectionner un fichier'),
            FileAllowed(
                ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'doc', 'docx', 'xls', 'xlsx'],
                message='Types autorises: PDF, images, Word, Excel'
            )
        ]
    )

    description = TextAreaField(
        'Description',
        validators=[Optional(), Length(max=500)]
    )

    # For passports/visas
    document_number = StringField(
        'Numero de document',
        validators=[Optional(), Length(max=100)]
    )

    issue_date = DateField(
        'Date d\'emission',
        validators=[Optional()],
        format='%Y-%m-%d'
    )

    expiry_date = DateField(
        'Date d\'expiration',
        validators=[Optional()],
        format='%Y-%m-%d'
    )

    issuing_country = StringField(
        'Pays d\'emission',
        validators=[Optional(), Length(max=100)]
    )

    # Owner selection
    owner_type = SelectField(
        'Attribuer a',
        choices=[
            ('', '-- Selectionner --'),
            ('user', 'Membre de l\'equipe'),
            ('band', 'Groupe'),
            ('tour', 'Tournee'),
        ],
        validators=[Optional()]
    )

    owner_id = SelectField(
        'Proprietaire',
        choices=[],
        validators=[Optional()],
        coerce=int
    )


class DocumentEditForm(FlaskForm):
    """Form for editing document metadata."""

    name = StringField(
        'Nom du document',
        validators=[DataRequired(message='Le nom est requis'), Length(max=200)]
    )

    document_type = SelectField(
        'Type de document',
        choices=[
            (DocumentType.PASSPORT.value, 'Passeport'),
            (DocumentType.VISA.value, 'Visa'),
            (DocumentType.CONTRACT.value, 'Contrat'),
            (DocumentType.RIDER.value, 'Rider technique'),
            (DocumentType.INSURANCE.value, 'Assurance'),
            (DocumentType.WORK_PERMIT.value, 'Permis de travail'),
            (DocumentType.OTHER.value, 'Autre'),
        ],
        validators=[DataRequired()]
    )

    description = TextAreaField(
        'Description',
        validators=[Optional(), Length(max=500)]
    )

    document_number = StringField(
        'Numero de document',
        validators=[Optional(), Length(max=100)]
    )

    issue_date = DateField(
        'Date d\'emission',
        validators=[Optional()],
        format='%Y-%m-%d'
    )

    expiry_date = DateField(
        'Date d\'expiration',
        validators=[Optional()],
        format='%Y-%m-%d'
    )

    issuing_country = StringField(
        'Pays d\'emission',
        validators=[Optional(), Length(max=100)]
    )


class DocumentFilterForm(FlaskForm):
    """Form for filtering documents list."""

    document_type = SelectField(
        'Type',
        choices=[
            ('', 'Tous les types'),
            (DocumentType.PASSPORT.value, 'Passeport'),
            (DocumentType.VISA.value, 'Visa'),
            (DocumentType.CONTRACT.value, 'Contrat'),
            (DocumentType.RIDER.value, 'Rider technique'),
            (DocumentType.INSURANCE.value, 'Assurance'),
            (DocumentType.WORK_PERMIT.value, 'Permis de travail'),
            (DocumentType.OTHER.value, 'Autre'),
        ],
        validators=[Optional()]
    )

    user_id = SelectField(
        'Utilisateur',
        choices=[('', 'Tous les utilisateurs')],
        validators=[Optional()],
        coerce=str
    )

    owner_type = SelectField(
        'Proprietaire',
        choices=[
            ('', 'Tous'),
            ('user', 'Membres'),
            ('band', 'Groupes'),
            ('tour', 'Tournées'),
        ],
        validators=[Optional()]
    )

    expiry_status = SelectField(
        'Statut expiration',
        choices=[
            ('', 'Tous'),
            ('expired', 'Expirés'),
            ('expiring_soon', 'Expire bientôt'),
            ('valid', 'Valides'),
        ],
        validators=[Optional()]
    )
