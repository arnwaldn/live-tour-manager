"""
Authentication forms.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, ValidationError, Regexp
)

from app.models.user import User


class LoginForm(FlaskForm):
    """User login form."""

    email = StringField('Email', validators=[
        DataRequired(message='L\'email est requis'),
        Email(message='Veuillez entrer un email valide')
    ])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(message='Le mot de passe est requis')
    ])
    remember_me = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')


class RegistrationForm(FlaskForm):
    """User registration form."""

    email = StringField('Email', validators=[
        DataRequired(message='L\'email est requis'),
        Email(message='Veuillez entrer un email valide'),
        Length(max=120)
    ])
    first_name = StringField('Prénom', validators=[
        DataRequired(message='Le prénom est requis'),
        Length(min=2, max=50, message='Le prénom doit contenir entre 2 et 50 caractères')
    ])
    last_name = StringField('Nom', validators=[
        DataRequired(message='Le nom est requis'),
        Length(min=2, max=50, message='Le nom doit contenir entre 2 et 50 caractères')
    ])
    phone = StringField('Téléphone', validators=[
        Length(max=20)
    ])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(message='Le mot de passe est requis'),
        Length(min=8, message='Le mot de passe doit contenir au moins 8 caractères'),
        Regexp(
            r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)',
            message='Le mot de passe doit contenir au moins une majuscule, une minuscule et un chiffre'
        )
    ])
    password_confirm = PasswordField('Confirmer le mot de passe', validators=[
        DataRequired(message='Veuillez confirmer le mot de passe'),
        EqualTo('password', message='Les mots de passe ne correspondent pas')
    ])
    submit = SubmitField('S\'inscrire')

    def validate_email(self, field):
        """Check if email is already registered."""
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('Cet email est déjà utilisé.')


class ForgotPasswordForm(FlaskForm):
    """Password reset request form."""

    email = StringField('Email', validators=[
        DataRequired(message='L\'email est requis'),
        Email(message='Veuillez entrer un email valide')
    ])
    submit = SubmitField('Envoyer le lien de réinitialisation')


class ResetPasswordForm(FlaskForm):
    """Password reset form."""

    password = PasswordField('Nouveau mot de passe', validators=[
        DataRequired(message='Le mot de passe est requis'),
        Length(min=8, message='Le mot de passe doit contenir au moins 8 caractères'),
        Regexp(
            r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)',
            message='Le mot de passe doit contenir au moins une majuscule, une minuscule et un chiffre'
        )
    ])
    password_confirm = PasswordField('Confirmer le mot de passe', validators=[
        DataRequired(message='Veuillez confirmer le mot de passe'),
        EqualTo('password', message='Les mots de passe ne correspondent pas')
    ])
    submit = SubmitField('Réinitialiser le mot de passe')


class ChangePasswordForm(FlaskForm):
    """Change password form for logged-in users."""

    current_password = PasswordField('Mot de passe actuel', validators=[
        DataRequired(message='Le mot de passe actuel est requis')
    ])
    new_password = PasswordField('Nouveau mot de passe', validators=[
        DataRequired(message='Le nouveau mot de passe est requis'),
        Length(min=8, message='Le mot de passe doit contenir au moins 8 caractères'),
        Regexp(
            r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)',
            message='Le mot de passe doit contenir au moins une majuscule, une minuscule et un chiffre'
        )
    ])
    new_password_confirm = PasswordField('Confirmer le nouveau mot de passe', validators=[
        DataRequired(message='Veuillez confirmer le nouveau mot de passe'),
        EqualTo('new_password', message='Les mots de passe ne correspondent pas')
    ])
    submit = SubmitField('Changer le mot de passe')
