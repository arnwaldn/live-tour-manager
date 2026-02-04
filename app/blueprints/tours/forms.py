"""
Tour management forms.
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, DateField, SelectField,
    DecimalField, TimeField, IntegerField, SubmitField, BooleanField
)
from wtforms.validators import DataRequired, Length, Optional, NumberRange, URL, ValidationError


class TourForm(FlaskForm):
    """Form for creating/editing a tour."""

    band_id = SelectField('Groupe', coerce=int, validators=[
        DataRequired(message='Veuillez sélectionner un groupe')
    ])
    name = StringField('Nom de la tournée', validators=[
        DataRequired(message='Le nom est requis'),
        Length(min=2, max=100)
    ])
    description = TextAreaField('Description', validators=[
        Length(max=2000)
    ])
    start_date = DateField('Date de début', validators=[
        DataRequired(message='La date de début est requise')
    ])
    end_date = DateField('Date de fin', validators=[
        DataRequired(message='La date de fin est requise')
    ])

    def validate_end_date(self, field):
        """Validate that end_date is after start_date."""
        if self.start_date.data and field.data:
            if field.data < self.start_date.data:
                raise ValidationError('La date de fin doit être après la date de début')
    budget = DecimalField('Budget', validators=[
        Optional(),
        NumberRange(min=0)
    ], places=2)
    currency = SelectField('Devise', choices=[
        ('EUR', 'EUR - Euro'),
        ('USD', 'USD - Dollar US'),
        ('GBP', 'GBP - Livre Sterling'),
        ('CHF', 'CHF - Franc Suisse')
    ], default='EUR')
    notes = TextAreaField('Notes internes', validators=[
        Length(max=2000)
    ])
    submit = SubmitField('Enregistrer')


class TourStopForm(FlaskForm):
    """Form for creating/editing a tour stop."""

    # Type d'événement (inspiré TourManagement.com, Master Tour)
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
        Optional()  # Optionnel pour DAY_OFF, TRAVEL
    ])

    # Location directe (pour événements sans salle)
    location_address = StringField('Adresse', validators=[
        Optional(),
        Length(max=255)
    ])
    location_city = StringField('Ville', validators=[
        Optional(),
        Length(max=100)
    ])
    location_country = StringField('Pays', validators=[
        Optional(),
        Length(max=100)
    ])
    location_notes = TextAreaField('Notes sur le lieu', validators=[
        Length(max=500)
    ])
    # Coordonnées GPS (remplies automatiquement par l'autocomplétion)
    location_latitude = DecimalField('Latitude', validators=[Optional()], places=7)
    location_longitude = DecimalField('Longitude', validators=[Optional()], places=7)

    date = DateField('Date', validators=[
        DataRequired(message='La date est requise')
    ])

    # Call times / Horaires d'appel (standards industrie)
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
    venue_rental_cost = DecimalField('Prix location salle', validators=[
        Optional(),
        NumberRange(min=0, message='Le prix doit être positif')
    ], places=2)
    ticket_price = DecimalField('Prix du billet', validators=[
        Optional(),
        NumberRange(min=0)
    ], places=2)
    sold_tickets = IntegerField('Billets vendus', validators=[
        Optional(),
        NumberRange(min=0, message='Le nombre doit être positif')
    ])
    door_deal_percentage = DecimalField('% Door Deal', validators=[
        Optional(),
        NumberRange(min=0, max=100, message='Le pourcentage doit être entre 0 et 100')
    ], places=2)
    # R1: Frais de billetterie (standard industrie: 2-10%)
    ticketing_fee_percentage = DecimalField('% Frais billetterie', validators=[
        Optional(),
        NumberRange(min=0, max=100, message='Le pourcentage doit être entre 0 et 100')
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


class RescheduleStopForm(FlaskForm):
    """Form for rescheduling a tour stop to a new date."""

    new_date = DateField('Nouvelle date', validators=[
        DataRequired(message='La nouvelle date est requise')
    ])
    reason = SelectField('Raison du report', choices=[
        ('', '-- Sélectionner --'),
        ('weather', 'Conditions météo'),
        ('artist_health', 'Santé artiste'),
        ('venue_issue', 'Problème venue'),
        ('production', 'Production'),
        ('logistics', 'Logistique'),
        ('force_majeure', 'Force majeure'),
        ('low_sales', 'Ventes insuffisantes'),
        ('scheduling_conflict', 'Conflit de planning'),
        ('other', 'Autre')
    ], validators=[Optional()])
    notes = TextAreaField('Notes additionnelles', validators=[
        Length(max=500)
    ])
    submit = SubmitField('Reporter le concert')


class LineupSlotForm(FlaskForm):
    """Form for creating/editing a lineup slot (programmation)."""

    performer_name = StringField('Nom de l\'artiste', validators=[
        DataRequired(message='Le nom de l\'artiste est requis'),
        Length(min=1, max=100)
    ])
    performer_type = SelectField('Type', choices=[
        ('main_artist', 'Artiste Principal'),
        ('opening_act', 'Première Partie'),
        ('support', 'Support'),
        ('dj_set', 'DJ Set'),
        ('special_guest', 'Invité Spécial'),
        ('other', 'Autre')
    ], default='support')
    start_time = TimeField('Heure de début', validators=[
        DataRequired(message='L\'heure de début est requise')
    ])
    end_time = TimeField('Heure de fin', validators=[Optional()])
    set_length_minutes = IntegerField('Durée (minutes)', validators=[
        Optional(),
        NumberRange(min=5, max=300, message='La durée doit être entre 5 et 300 minutes')
    ])
    order = IntegerField('Position dans le programme', validators=[
        DataRequired(message='La position est requise'),
        NumberRange(min=1, max=20, message='La position doit être entre 1 et 20')
    ], default=1)
    notes = TextAreaField('Notes', validators=[
        Length(max=500)
    ])
    is_confirmed = BooleanField('Confirmé')
    submit = SubmitField('Enregistrer')


class MemberScheduleForm(FlaskForm):
    """Form for editing a member's schedule on a tour stop."""

    work_start = TimeField('Début de travail', validators=[Optional()])
    work_end = TimeField('Fin de travail', validators=[Optional()])
    break_start = TimeField('Début pause', validators=[Optional()])
    break_end = TimeField('Fin pause', validators=[Optional()])
    meal_time = TimeField('Heure repas', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Length(max=500)])
    submit = SubmitField('Enregistrer')
