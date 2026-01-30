"""Forms for crew schedule management."""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, TimeField, SelectField,
    HiddenField, IntegerField
)
from wtforms.validators import DataRequired, Optional, Length, Email

from app.models.profession import ProfessionCategory


class CrewSlotForm(FlaskForm):
    """Form for creating/editing a crew schedule slot."""
    task_name = StringField(
        'Nom de la tâche',
        validators=[DataRequired(), Length(max=100)]
    )
    task_description = TextAreaField(
        'Description',
        validators=[Optional(), Length(max=500)]
    )
    start_time = TimeField(
        'Heure de début',
        validators=[DataRequired()],
        format='%H:%M'
    )
    end_time = TimeField(
        'Heure de fin',
        validators=[DataRequired()],
        format='%H:%M'
    )
    profession_category = SelectField(
        'Catégorie',
        choices=[('', 'Toutes catégories')] + [
            (cat.value, cat.value.title()) for cat in ProfessionCategory
        ],
        validators=[Optional()]
    )
    color = StringField(
        'Couleur',
        validators=[Optional(), Length(max=7)],
        default='#3B82F6'
    )


class CrewAssignmentForm(FlaskForm):
    """Form for assigning a person to a slot."""
    assignment_type = SelectField(
        'Type',
        choices=[
            ('user', 'Utilisateur système'),
            ('external', 'Contact externe')
        ],
        validators=[DataRequired()]
    )
    user_id = SelectField(
        'Utilisateur',
        coerce=int,
        validators=[Optional()]
    )
    external_contact_id = SelectField(
        'Contact externe',
        coerce=int,
        validators=[Optional()]
    )
    profession_id = SelectField(
        'Profession (override)',
        coerce=int,
        validators=[Optional()]
    )
    call_time = TimeField(
        'Heure d\'appel (override)',
        validators=[Optional()],
        format='%H:%M'
    )
    notes = TextAreaField(
        'Notes',
        validators=[Optional(), Length(max=500)]
    )


class ExternalContactForm(FlaskForm):
    """Form for creating/editing an external contact."""
    first_name = StringField(
        'Prénom',
        validators=[DataRequired(), Length(max=50)]
    )
    last_name = StringField(
        'Nom',
        validators=[DataRequired(), Length(max=50)]
    )
    email = StringField(
        'Email',
        validators=[Optional(), Email(), Length(max=120)]
    )
    phone = StringField(
        'Téléphone',
        validators=[Optional(), Length(max=20)]
    )
    profession_id = SelectField(
        'Profession',
        coerce=int,
        validators=[Optional()]
    )
    company = StringField(
        'Société',
        validators=[Optional(), Length(max=100)]
    )
    notes = TextAreaField(
        'Notes',
        validators=[Optional(), Length(max=500)]
    )
