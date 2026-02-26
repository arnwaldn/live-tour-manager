"""Forms for advancing blueprint."""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, IntegerField,
    FloatField, BooleanField, DateField, HiddenField
)
from wtforms.validators import DataRequired, Optional, Email, Length, NumberRange


class RiderRequirementForm(FlaskForm):
    """Form for adding a rider requirement."""
    category = SelectField(
        'Catégorie',
        choices=[
            ('son', 'Son'),
            ('lumiere', 'Lumière'),
            ('scene', 'Scène'),
            ('backline', 'Backline'),
            ('catering', 'Catering'),
            ('loges', 'Loges'),
        ],
        validators=[DataRequired()]
    )
    requirement = StringField(
        'Exigence',
        validators=[DataRequired(), Length(max=255)]
    )
    quantity = IntegerField(
        'Quantité',
        default=1,
        validators=[NumberRange(min=1)]
    )
    is_mandatory = BooleanField('Obligatoire', default=True)
    notes = TextAreaField('Notes', validators=[Optional()])


class AdvancingContactForm(FlaskForm):
    """Form for adding an advancing contact."""
    name = StringField(
        'Nom',
        validators=[DataRequired(), Length(max=100)]
    )
    role = StringField(
        'Rôle',
        validators=[Optional(), Length(max=100)]
    )
    email = StringField(
        'Email',
        validators=[Optional(), Email(), Length(max=255)]
    )
    phone = StringField(
        'Téléphone',
        validators=[Optional(), Length(max=50)]
    )
    is_primary = BooleanField('Contact principal', default=False)
    notes = TextAreaField('Notes', validators=[Optional()])


class ProductionSpecsForm(FlaskForm):
    """Form for updating production specs."""
    stage_width = FloatField('Largeur scène (m)', validators=[Optional()])
    stage_depth = FloatField('Profondeur scène (m)', validators=[Optional()])
    stage_height = FloatField('Hauteur scène (m)', validators=[Optional()])
    power_available = StringField(
        'Puissance électrique disponible',
        validators=[Optional(), Length(max=100)]
    )
    rigging_points = IntegerField(
        'Points d\'accroche',
        validators=[Optional(), NumberRange(min=0)]
    )


class AdvancingTemplateForm(FlaskForm):
    """Form for creating an advancing template."""
    name = StringField(
        'Nom du template',
        validators=[DataRequired(), Length(max=100)]
    )
    description = TextAreaField('Description', validators=[Optional()])


class AdvancingStatusForm(FlaskForm):
    """Form for updating advancing status."""
    status = SelectField(
        'Statut',
        choices=[
            ('not_started', 'Non démarré'),
            ('in_progress', 'En cours'),
            ('waiting_venue', 'Attente salle'),
            ('completed', 'Terminé'),
            ('issues', 'Problèmes'),
        ],
        validators=[DataRequired()]
    )
    advancing_deadline = DateField(
        'Date limite',
        validators=[Optional()],
        format='%Y-%m-%d'
    )


class ChecklistItemNoteForm(FlaskForm):
    """Form for adding notes to a checklist item."""
    notes = TextAreaField('Notes', validators=[Optional()])
