"""
Logistics management forms.
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, DecimalField,
    DateTimeLocalField, SubmitField, IntegerField, BooleanField,
    TimeField, EmailField, SelectMultipleField, HiddenField
)
from wtforms.validators import DataRequired, Length, Optional, NumberRange, Email
from wtforms.widgets import ListWidget, CheckboxInput


class LogisticsInfoForm(FlaskForm):
    """Form for creating/editing logistics information."""

    # Type selection
    logistics_type = SelectField('Type', choices=[
        ('FLIGHT', 'Vol'),
        ('TRAIN', 'Train'),
        ('BUS', 'Bus/Van'),
        ('FERRY', 'Ferry'),
        ('RENTAL_CAR', 'Location voiture'),
        ('TAXI', 'Taxi'),
        ('GROUND_TRANSPORT', 'Transport terrestre'),
        ('HOTEL', 'Hôtel'),
        ('APARTMENT', 'Appartement'),
        ('RENTAL', 'Location équipement'),
        ('EQUIPMENT', 'Équipement'),
        ('BACKLINE', 'Backline'),
        ('CATERING', 'Catering'),
        ('MEAL', 'Repas'),
        ('PARKING', 'Parking'),
        ('OTHER', 'Autre')
    ], validators=[DataRequired()])

    # Status
    status = SelectField('Statut', choices=[
        ('PENDING', 'En attente'),
        ('BOOKED', 'Réservé'),
        ('CONFIRMED', 'Confirmé'),
        ('COMPLETED', 'Terminé'),
        ('CANCELLED', 'Annulé')
    ], default='PENDING')

    # Basic info
    provider = StringField('Fournisseur/Compagnie', validators=[
        Length(max=100)
    ])
    confirmation_number = StringField('Numéro de confirmation', validators=[
        Length(max=100)
    ])

    # Timing
    start_datetime = DateTimeLocalField('Date/Heure de début', validators=[
        Optional()
    ], format='%Y-%m-%dT%H:%M')
    end_datetime = DateTimeLocalField('Date/Heure de fin', validators=[
        Optional()
    ], format='%Y-%m-%dT%H:%M')

    # ===== LOCATION SECTION (hotels, pickups, etc.) =====
    address = StringField('Adresse', validators=[
        Length(max=255)
    ])
    city = StringField('Ville', validators=[
        Length(max=100)
    ])
    country = StringField('Pays', validators=[
        Length(max=100)
    ])
    # GPS coordinates (filled by frontend autocomplete)
    latitude = HiddenField('Latitude')
    longitude = HiddenField('Longitude')

    # ===== FLIGHT SECTION =====
    flight_number = StringField('Numéro de vol', validators=[
        Length(max=20)
    ])
    departure_airport = StringField('Aéroport de départ (code)', validators=[
        Length(max=10)
    ])
    arrival_airport = StringField('Aéroport d\'arrivée (code)', validators=[
        Length(max=10)
    ])
    departure_terminal = StringField('Terminal départ', validators=[
        Length(max=20)
    ])
    arrival_terminal = StringField('Terminal arrivée', validators=[
        Length(max=20)
    ])

    # ===== HOTEL SECTION =====
    room_type = SelectField('Type de chambre', choices=[
        ('', '-- Sélectionner --'),
        ('single', 'Single'),
        ('double', 'Double'),
        ('twin', 'Twin (2 lits)'),
        ('triple', 'Triple'),
        ('suite', 'Suite'),
        ('apartment', 'Appartement'),
        ('dorm', 'Dortoir')
    ], validators=[Optional()])
    number_of_rooms = IntegerField('Nombre de chambres', validators=[
        Optional(),
        NumberRange(min=1, max=100)
    ], default=1)
    breakfast_included = BooleanField('Petit-déjeuner inclus')
    check_in_time = TimeField('Heure de check-in', validators=[Optional()])
    check_out_time = TimeField('Heure de check-out', validators=[Optional()])

    # ===== GROUND TRANSPORT SECTION =====
    pickup_location = StringField('Lieu de départ/pickup', validators=[
        Length(max=255)
    ])
    dropoff_location = StringField('Lieu d\'arrivée/dropoff', validators=[
        Length(max=255)
    ])
    # GPS coordinates for transport (filled by frontend autocomplete)
    departure_lat = HiddenField('Departure Latitude')
    departure_lng = HiddenField('Departure Longitude')
    arrival_lat = HiddenField('Arrival Latitude')
    arrival_lng = HiddenField('Arrival Longitude')
    vehicle_type = SelectField('Type de véhicule', choices=[
        ('', '-- Sélectionner --'),
        ('sedan', 'Berline'),
        ('suv', 'SUV'),
        ('van', 'Van (9 places)'),
        ('minibus', 'Minibus (15-20 places)'),
        ('bus', 'Bus (30+ places)'),
        ('sleeper_bus', 'Bus couchettes'),
        ('sprinter', 'Sprinter'),
        ('limousine', 'Limousine'),
        ('other', 'Autre')
    ], validators=[Optional()])
    driver_name = StringField('Nom du chauffeur', validators=[
        Length(max=100)
    ])
    driver_phone = StringField('Téléphone du chauffeur', validators=[
        Length(max=30)
    ])

    # ===== CONTACT SECTION =====
    contact_name = StringField('Nom du contact', validators=[
        Length(max=100)
    ])
    contact_phone = StringField('Téléphone du contact', validators=[
        Length(max=30)
    ])
    contact_email = EmailField('Email du contact', validators=[
        Optional(),
        Email(message='Email invalide'),
        Length(max=120)
    ])

    # ===== COST SECTION =====
    cost = DecimalField('Coût', validators=[
        Optional(),
        NumberRange(min=0)
    ], places=2)
    currency = SelectField('Devise', choices=[
        ('EUR', 'EUR'),
        ('USD', 'USD'),
        ('GBP', 'GBP'),
        ('CHF', 'CHF'),
        ('CAD', 'CAD'),
        ('AUD', 'AUD'),
        ('JPY', 'JPY')
    ], default='EUR')
    is_paid = BooleanField('Payé')
    paid_by = SelectField('Payé par', choices=[
        ('', '-- Sélectionner --'),
        ('band', 'Groupe'),
        ('promoter', 'Promoteur'),
        ('label', 'Label'),
        ('sponsor', 'Sponsor'),
        ('other', 'Autre')
    ], validators=[Optional()])

    # Notes
    notes = TextAreaField('Notes', validators=[
        Length(max=2000)
    ])

    # ===== ASSIGNATION SECTION =====
    # Multi-select for users to assign to this logistics item
    assigned_users = SelectMultipleField(
        'Personnes assignées',
        coerce=int,
        validators=[Optional()],
        widget=ListWidget(prefix_label=False),
        option_widget=CheckboxInput()
    )

    submit = SubmitField('Enregistrer')


class LocalContactForm(FlaskForm):
    """Form for creating/editing local contacts."""

    name = StringField('Nom', validators=[
        DataRequired(message='Le nom est requis'),
        Length(min=2, max=100)
    ])
    role = SelectField('Rôle', choices=[
        ('', '-- Sélectionner --'),
        ('Promoter', 'Promoteur'),
        ('Production Manager', 'Directeur de production'),
        ('Stage Manager', 'Régisseur'),
        ('Sound Engineer', 'Ingénieur son'),
        ('Lighting Designer', 'Éclairagiste'),
        ('Monitor Engineer', 'Ingénieur retours'),
        ('Backline Tech', 'Tech backline'),
        ('Runner', 'Runner'),
        ('Security', 'Sécurité'),
        ('Catering', 'Catering'),
        ('Hospitality', 'Hospitalité'),
        ('Local Crew Chief', 'Chef équipe locale'),
        ('Tour Rep', 'Représentant tournée'),
        ('Driver', 'Chauffeur'),
        ('Hotel Contact', 'Contact hôtel'),
        ('Airport Rep', 'Représentant aéroport'),
        ('Other', 'Autre')
    ], validators=[Optional()])

    company = StringField('Entreprise', validators=[
        Length(max=100)
    ])
    email = StringField('Email', validators=[
        Optional(),
        Length(max=120)
    ])
    phone = StringField('Téléphone', validators=[
        DataRequired(message='Le téléphone est requis'),
        Length(max=30)
    ])
    phone_secondary = StringField('Téléphone secondaire', validators=[
        Length(max=30)
    ])

    notes = TextAreaField('Notes', validators=[
        Length(max=500)
    ])
    is_primary = SelectField('Contact principal?', choices=[
        ('0', 'Non'),
        ('1', 'Oui')
    ], default='0')

    submit = SubmitField('Enregistrer')


class LogisticsAssignmentForm(FlaskForm):
    """Form for assigning users to logistics items."""

    user_id = SelectField('Personne', coerce=int, validators=[
        DataRequired(message='Sélectionnez une personne')
    ])

    # Transport specific (flight, train, bus)
    seat_number = StringField('Numéro de siège/place', validators=[
        Length(max=20)
    ])

    # Accommodation specific (hotel, apartment)
    room_number = StringField('Numéro de chambre', validators=[
        Length(max=20)
    ])
    room_sharing_with = StringField('Partage avec', validators=[
        Length(max=100)
    ])

    # Common
    special_requests = TextAreaField('Demandes spéciales', validators=[
        Length(max=500)
    ])

    submit = SubmitField('Assigner')
