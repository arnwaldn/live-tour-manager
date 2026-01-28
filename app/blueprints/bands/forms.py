"""
Band management forms.
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, URLField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, URL, Optional, Email


class BandForm(FlaskForm):
    """Form for creating/editing a band."""

    name = StringField('Nom du groupe', validators=[
        DataRequired(message='Le nom du groupe est requis'),
        Length(min=2, max=100, message='Le nom doit contenir entre 2 et 100 caractères')
    ])
    genre = StringField('Genre musical', validators=[
        Length(max=50)
    ])
    bio = TextAreaField('Biographie', validators=[
        Length(max=2000, message='La biographie ne doit pas dépasser 2000 caractères')
    ])
    logo_file = FileField('Logo (image)', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'],
                    'Seules les images sont autorisees (JPG, PNG, GIF, WebP)')
    ])
    logo_url = URLField('URL du logo (alternative)', validators=[
        Optional(),
        URL(message='Veuillez entrer une URL valide')
    ])
    website = URLField('Site web', validators=[
        Optional(),
        URL(message='Veuillez entrer une URL valide')
    ])
    submit = SubmitField('Enregistrer')


class BandMemberInviteForm(FlaskForm):
    """Form for inviting a member to a band."""

    user_id = SelectField('Utilisateur', coerce=int, validators=[
        DataRequired(message='Veuillez sélectionner un utilisateur')
    ])
    instrument = StringField('Instrument', validators=[
        Length(max=50)
    ])
    role_in_band = StringField('Rôle dans le groupe', validators=[
        Length(max=50)
    ])
    submit = SubmitField('Inviter')


class BandMemberEditForm(FlaskForm):
    """Form for editing a band member's details."""

    instrument = StringField('Instrument', validators=[
        Length(max=50)
    ])
    role_in_band = StringField('Rôle dans le groupe', validators=[
        Length(max=50)
    ])
    submit = SubmitField('Enregistrer')
