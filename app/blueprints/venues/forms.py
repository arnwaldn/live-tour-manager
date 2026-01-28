"""
Venue management forms.
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, URLField, SelectField,
    IntegerField, SubmitField, HiddenField, FloatField
)
from wtforms.validators import DataRequired, Length, URL, Optional, Email, NumberRange


class VenueForm(FlaskForm):
    """Form for creating/editing a venue."""

    name = StringField('Nom de la salle', validators=[
        DataRequired(message='Le nom est requis'),
        Length(min=2, max=100)
    ])
    address = StringField('Adresse', validators=[
        DataRequired(message='L\'adresse est requise'),
        Length(max=200)
    ])
    city = StringField('Ville', validators=[
        DataRequired(message='La ville est requise'),
        Length(max=100)
    ])
    state_province = StringField('Région/État', validators=[
        Length(max=100)
    ])
    country = StringField('Pays', validators=[
        DataRequired(message='Le pays est requis'),
        Length(max=100)
    ], default='France')
    postal_code = StringField('Code postal', validators=[
        Length(max=20)
    ])
    
    # GPS Coordinates (remplis automatiquement par l'autocomplétion)
    latitude = HiddenField('Latitude')
    longitude = HiddenField('Longitude')

    capacity = IntegerField('Capacité', validators=[
        Optional(),
        NumberRange(min=1, max=500000)
    ])
    venue_type = SelectField('Type de salle', choices=[
        ('', '-- Sélectionner --'),
        ('Club', 'Club'),
        ('Theater', 'Théâtre'),
        ('Arena', 'Arena'),
        ('Stadium', 'Stade'),
        ('Festival', 'Festival'),
        ('Bar', 'Bar'),
        ('Restaurant', 'Restaurant'),
        ('Outdoor', 'Plein air'),
        ('Church', 'Église'),
        ('Other', 'Autre')
    ], validators=[Optional()])

    website = URLField('Site web', validators=[
        Optional(),
        URL(message='URL invalide')
    ])
    phone = StringField('Téléphone', validators=[
        Length(max=30)
    ])
    email = StringField('Email', validators=[
        Optional(),
        Email(message='Email invalide'),
        Length(max=120)
    ])

    notes = TextAreaField('Notes', validators=[
        Length(max=2000)
    ])
    technical_specs = TextAreaField('Spécifications techniques', validators=[
        Length(max=5000)
    ])

    submit = SubmitField('Enregistrer')


class VenueContactForm(FlaskForm):
    """Form for adding/editing a venue contact."""

    name = StringField('Nom', validators=[
        DataRequired(message='Le nom est requis'),
        Length(min=2, max=100)
    ])
    role = SelectField('Rôle', choices=[
        ('', '-- Sélectionner --'),
        ('Booker', 'Booker'),
        ('Production', 'Production'),
        ('Sound Engineer', 'Ingénieur son'),
        ('Lighting', 'Éclairagiste'),
        ('Stage Manager', 'Régisseur'),
        ('Security', 'Sécurité'),
        ('Marketing', 'Marketing'),
        ('Box Office', 'Billetterie'),
        ('Hospitality', 'Hospitalité'),
        ('General Manager', 'Directeur'),
        ('Other', 'Autre')
    ], validators=[Optional()])
    email = StringField('Email', validators=[
        Optional(),
        Email(message='Email invalide'),
        Length(max=120)
    ])
    phone = StringField('Téléphone', validators=[
        Length(max=30)
    ])
    notes = TextAreaField('Notes', validators=[
        Length(max=500)
    ])

    submit = SubmitField('Enregistrer')
