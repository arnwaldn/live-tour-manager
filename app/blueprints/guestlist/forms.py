"""
Guestlist management forms.
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField,
    IntegerField, SubmitField, BooleanField
)
from wtforms.validators import DataRequired, Length, Email, Optional, NumberRange


class GuestlistEntryForm(FlaskForm):
    """Form for adding/editing a guestlist entry."""

    guest_name = StringField('Nom de l\'invité', validators=[
        Optional(),  # Devient optionnel car auto-rempli si artiste sélectionné
        Length(min=2, max=100)
    ])
    guest_email = StringField('Email', validators=[
        Optional(),
        Email(message='Email invalide'),
        Length(max=120)
    ])
    guest_phone = StringField('Téléphone', validators=[
        Length(max=30)
    ])

    entry_type = SelectField('Type d\'entrée', choices=[
        ('guest', 'Invité'),
        ('vip', 'VIP'),
        ('industry', 'Professionnel'),
        ('press', 'Presse'),
        ('artist', 'Artiste'),
        ('comp', 'Complimentary'),
        ('working', 'Crew/Staff')
    ], default='guest')

    # Nouveau champ pour sélectionner un artiste (membre du groupe)
    artist_id = SelectField(
        'Artiste (membre du groupe)',
        coerce=int,
        choices=[],  # Rempli dynamiquement dans __init__
        validators=[Optional()]
    )

    plus_ones = IntegerField('Accompagnants (+)', validators=[
        NumberRange(min=0, max=10, message='Maximum 10 accompagnants')
    ], default=0)

    company = StringField('Affiliation/Organisation', validators=[
        Length(max=100)
    ])

    notes = TextAreaField('Notes (visibles par l\'invité)', validators=[
        Length(max=500)
    ])
    internal_notes = TextAreaField('Notes internes', validators=[
        Length(max=500)
    ])

    status = SelectField('Statut', choices=[
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('denied', 'Refusé')
    ], default='pending')

    submit = SubmitField('Enregistrer')

    def __init__(self, band_members=None, *args, **kwargs):
        """Initialize form with optional band members for artist selection.

        Args:
            band_members: List of User objects who are members of the band.
                          Used to populate the artist_id dropdown.
        """
        super().__init__(*args, **kwargs)
        # Toujours définir les choices pour artist_id
        self.artist_id.choices = [(0, '-- Sélectionner un artiste --')]
        if band_members:
            self.artist_id.choices += [
                (m.id, f"{m.full_name} ({m.email})")
                for m in band_members
            ]


class GuestlistApprovalForm(FlaskForm):
    """Form for approving/denying a guestlist entry."""

    action = SelectField('Action', choices=[
        ('approve', 'Approuver'),
        ('deny', 'Refuser')
    ], validators=[DataRequired()])

    approval_notes = TextAreaField('Notes de décision', validators=[
        Length(max=500)
    ])

    submit = SubmitField('Confirmer')


class GuestlistCheckInForm(FlaskForm):
    """Form for checking in a guest."""

    plus_ones_arrived = IntegerField('Accompagnants présents', validators=[
        NumberRange(min=0, max=10)
    ], default=0)

    notes = TextAreaField('Notes de check-in', validators=[
        Length(max=200)
    ])

    submit = SubmitField('Check-in')


class GuestlistBulkActionForm(FlaskForm):
    """Form for bulk actions on guestlist entries."""

    action = SelectField('Action', choices=[
        ('approve', 'Approuver sélectionnés'),
        ('deny', 'Refuser sélectionnés'),
        ('delete', 'Supprimer sélectionnés')
    ], validators=[DataRequired()])

    submit = SubmitField('Appliquer')


class GuestlistSearchForm(FlaskForm):
    """Form for searching guestlist."""

    search = StringField('Rechercher', validators=[
        Length(max=100)
    ])
    status = SelectField('Statut', choices=[
        ('', 'Tous'),
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('denied', 'Refusé'),
        ('checked_in', 'Check-in effectué'),
        ('no_show', 'No-show')
    ])
    entry_type = SelectField('Type', choices=[
        ('', 'Tous'),
        ('guest', 'Invité'),
        ('vip', 'VIP'),
        ('industry', 'Professionnel'),
        ('press', 'Presse'),
        ('artist', 'Artiste'),
        ('comp', 'Complimentary'),
        ('working', 'Crew/Staff')
    ])

    submit = SubmitField('Filtrer')
