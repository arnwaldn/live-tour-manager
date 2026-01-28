"""
Main blueprint forms - including standalone event form.
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, DateField, SelectField,
    DecimalField, TimeField, IntegerField, SubmitField
)
from wtforms.validators import DataRequired, Length, Optional, NumberRange, URL


class StandaloneEventForm(FlaskForm):
    """Form for creating a standalone event (not part of a specific tour)."""

    # Band selection (required for standalone events)
    band_id = SelectField('Groupe', coerce=int, validators=[
        DataRequired(message='Le groupe est requis')
    ])

    # Optional: link to an existing tour
    tour_id = SelectField('Tournée (optionnel)', coerce=int, validators=[
        Optional()
    ])

    # Type d'événement (tous les types disponibles)
    event_type = SelectField('Type d\'événement', choices=[
        ('show', 'Concert'),
        ('day_off', 'Jour off'),
        ('travel', 'Voyage'),
        ('studio', 'Studio'),
        ('promo', 'Promo'),
        ('rehearsal', 'Répétition'),
        ('press', 'Presse'),
        ('meet_greet', 'Meet & Greet'),
        ('photo_video', 'Photo/Vidéo'),
        ('other', 'Autre')
    ], default='show')

    venue_id = SelectField('Salle', coerce=int, validators=[
        Optional()  # Optionnel pour DAY_OFF, TRAVEL, etc.
    ])

    # Date WITHOUT min/max constraints
    date = DateField('Date', validators=[
        DataRequired(message='La date est requise')
    ])

    # Call times / Horaires d'appel
    load_in_time = TimeField('Load-In', validators=[Optional()])
    crew_call_time = TimeField('Appel équipe', validators=[Optional()])
    artist_call_time = TimeField('Appel artistes', validators=[Optional()])
    catering_time = TimeField('Repas/Catering', validators=[Optional()])

    # Show times
    soundcheck_time = TimeField('Soundcheck', validators=[Optional()])
    press_time = TimeField('Presse/Interviews', validators=[Optional()])
    meet_greet_time = TimeField('Meet & Greet', validators=[Optional()])
    doors_time = TimeField('Ouverture des portes', validators=[Optional()])
    set_time = TimeField('Heure du set', validators=[Optional()])
    curfew_time = TimeField('Couvre-feu', validators=[Optional()])

    status = SelectField('Statut', choices=[
        ('draft', 'Brouillon'),
        ('pending', 'En négociation'),
        ('confirmed', 'Confirmé'),
        ('performed', 'Réalisé'),
        ('settled', 'Réglé'),
        ('canceled', 'Annulé')
    ], default='draft')

    show_type = SelectField('Type de concert', choices=[
        ('', '-- Sélectionner --'),
        ('Headline', 'Tête d\'affiche'),
        ('Support', 'Première partie'),
        ('Festival', 'Festival'),
        ('Private', 'Privé'),
        ('Showcase', 'Showcase'),
        ('Residency', 'Résidence')
    ], validators=[Optional()])

    guarantee = DecimalField('Cachet garanti', validators=[
        Optional(),
        NumberRange(min=0)
    ], places=2)
    ticket_price = DecimalField('Prix du billet', validators=[
        Optional(),
        NumberRange(min=0)
    ], places=2)
    ticket_url = StringField('Lien billetterie', validators=[
        Optional(),
        URL(message='URL invalide'),
        Length(max=255)
    ])
    set_length_minutes = IntegerField('Durée du set (min)', validators=[
        Optional(),
        NumberRange(min=1, max=300)
    ])
    age_restriction = SelectField('Restriction d\'âge', choices=[
        ('', 'Aucune'),
        ('All ages', 'Tout public'),
        ('16+', '16+'),
        ('18+', '18+'),
        ('21+', '21+')
    ], validators=[Optional()])

    notes = TextAreaField('Notes', validators=[Length(max=2000)])
    internal_notes = TextAreaField('Notes internes', validators=[Length(max=2000)])

    submit = SubmitField('Enregistrer')
