"""
Settings routes.
"""
import os
import uuid
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, current_app, Response, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, TextAreaField, DateField, DecimalField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from sqlalchemy.exc import IntegrityError

from app.blueprints.settings import settings_bp
from app.blueprints.settings.forms import (
    UserCreateForm, UserEditForm, TravelCardForm,
    ProfessionCreateForm, ProfessionEditForm,
    get_access_level_choices, get_profession_choices, get_professions_by_category,
    get_category_choices
)
from app.extensions import db
from app.models.user import User, Role, TravelCard, AccessLevel
from app.models.profession import Profession, UserProfession
from app.models.label import Label
from app.models.document import Document, DocumentType
from app.models.band import Band
from app.models.guestlist import GuestlistEntry
from app.models.payments import UserPaymentConfig, StaffCategory, StaffRole, ContractType, PaymentFrequency
from app.decorators import requires_manager
from app.utils.email import send_invitation_email, send_registration_notification, send_approval_email, send_rejection_email


class ProfileForm(FlaskForm):
    """Profile edit form with crew information."""
    # Basic info
    first_name = StringField('Prénom', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Nom', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField('Téléphone', validators=[Optional(), Length(max=20)])

    # Personal information
    date_of_birth = DateField('Date de naissance', validators=[Optional()])
    nationality = StringField('Nationalité', validators=[Optional(), Length(max=100)])

    # Travel preferences
    preferred_airline = StringField('Compagnie aérienne préférée', validators=[Optional(), Length(max=100)])
    seat_preference = SelectField('Préférence siège', choices=[
        ('', 'Pas de préférence'),
        ('window', 'Hublot'),
        ('aisle', 'Couloir'),
        ('middle', 'Milieu')
    ], validators=[Optional()])
    meal_preference = SelectField('Préférence repas', choices=[
        ('', 'Standard'),
        ('vegetarian', 'Végétarien'),
        ('vegan', 'Végan'),
        ('halal', 'Halal'),
        ('kosher', 'Casher'),
        ('gluten_free', 'Sans gluten'),
        ('lactose_free', 'Sans lactose')
    ], validators=[Optional()])
    hotel_preferences = TextAreaField('Préférences hôtel', validators=[Optional(), Length(max=500)])

    # Emergency contact
    emergency_contact_name = StringField('Nom du contact', validators=[Optional(), Length(max=100)])
    emergency_contact_relation = StringField('Relation', validators=[Optional(), Length(max=50)])
    emergency_contact_phone = StringField('Téléphone', validators=[Optional(), Length(max=20)])
    emergency_contact_email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])

    # Health / Dietary
    dietary_restrictions = TextAreaField('Restrictions alimentaires', validators=[Optional(), Length(max=500)])
    allergies = TextAreaField('Allergies', validators=[Optional(), Length(max=500)])

    # ============ FACTURATION & PAIEMENT ============
    # Note: staff_category et staff_role supprimés - utiliser professions dans l'onglet Identité

    contract_type = SelectField('Type de contrat', choices=[
        ('', '-- Sélectionner --'),
        ('cddu', 'CDDU (Intermittent)'),
        ('cdd', 'CDD'),
        ('cdi', 'CDI'),
        ('freelance', 'Auto-entrepreneur'),
        ('prestation', 'Prestation (société)'),
        ('guso', 'GUSO')
    ], validators=[Optional()])

    payment_frequency = SelectField('Fréquence de paiement', choices=[
        ('', '-- Sélectionner --'),
        ('per_show', 'Par concert'),
        ('daily', 'Journalier'),
        ('half_day', 'Demi-journée'),
        ('weekly', 'Hebdomadaire'),
        ('hourly', 'Horaire'),
        ('fixed', 'Forfait'),
        ('monthly', 'Mensuel')
    ], validators=[Optional()])

    # Tarifs
    show_rate = DecimalField('Tarif concert (€)', validators=[Optional(), NumberRange(min=0)])
    daily_rate = DecimalField('Tarif journalier (€)', validators=[Optional(), NumberRange(min=0)])
    half_day_rate = DecimalField('Tarif demi-journée (€)', validators=[Optional(), NumberRange(min=0)])
    hourly_rate = DecimalField('Tarif horaire (€)', validators=[Optional(), NumberRange(min=0)])
    per_diem = DecimalField('Per diem (€)', validators=[Optional(), NumberRange(min=0)])

    # Majorations
    overtime_rate_25 = DecimalField('Majoration +25%', validators=[Optional()])
    overtime_rate_50 = DecimalField('Majoration +50%', validators=[Optional()])
    weekend_rate = DecimalField('Majoration weekend', validators=[Optional()])
    holiday_rate = DecimalField('Majoration jours fériés', validators=[Optional()])
    night_rate = DecimalField('Majoration nuit', validators=[Optional()])

    # Informations bancaires SEPA
    iban = StringField('IBAN', validators=[Optional(), Length(max=34)])
    bic = StringField('BIC', validators=[Optional(), Length(max=11)])
    bank_name = StringField('Nom de la banque', validators=[Optional(), Length(max=100)])
    account_holder = StringField('Titulaire du compte', validators=[Optional(), Length(max=200)])

    # Informations fiscales
    siret = StringField('SIRET', validators=[Optional(), Length(max=14)])
    siren = StringField('SIREN', validators=[Optional(), Length(max=9)])
    vat_number = StringField('N° TVA intracommunautaire', validators=[Optional(), Length(max=20)])

    submit = SubmitField('Enregistrer')


class PasswordForm(FlaskForm):
    """Password change form."""
    current_password = PasswordField('Mot de passe actuel', validators=[DataRequired()])
    new_password = PasswordField('Nouveau mot de passe', validators=[
        DataRequired(),
        Length(min=8, message='Le mot de passe doit contenir au moins 8 caractères.')
    ])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[
        DataRequired(),
        EqualTo('new_password', message='Les mots de passe ne correspondent pas.')
    ])
    submit = SubmitField('Changer le mot de passe')


class NotificationForm(FlaskForm):
    """Notification preferences form."""
    notify_new_tour = BooleanField('Nouvelle tournée créée')
    notify_guestlist_request = BooleanField('Nouvelle demande guestlist')
    notify_guestlist_approved = BooleanField('Guestlist approuvée/refusée')
    notify_tour_reminder = BooleanField('Rappel avant concert (24h)')
    notify_document_shared = BooleanField('Document partagé')
    submit = SubmitField('Enregistrer les préférences')


class ProfileDocumentForm(FlaskForm):
    """Form for uploading personal documents to user profile."""
    document_type = SelectField('Type de document', choices=[
        ('passport', 'Passeport'),
        ('visa', 'Visa'),
        ('work_permit', 'Permis de travail'),
        ('insurance', 'Assurance'),
        ('other', 'Autre')
    ], validators=[DataRequired()])
    title = StringField('Titre', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    expiry_date = DateField('Date d\'expiration', validators=[Optional()])
    file = FileField('Fichier', validators=[
        FileRequired(message='Veuillez sélectionner un fichier.'),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'],
                   'Formats autorisés: PDF, JPG, PNG, DOC, DOCX')
    ])
    submit = SubmitField('Envoyer')


def get_upload_folder():
    """Get the upload folder path, creating it if necessary."""
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    if not os.path.isabs(upload_folder):
        upload_folder = os.path.join(current_app.root_path, '..', upload_folder)
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder


def generate_unique_filename(original_filename):
    """Generate a unique filename while preserving the extension."""
    ext = os.path.splitext(original_filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return unique_name


@settings_bp.route('/')
@login_required
def index():
    """Settings overview page."""
    if not current_user.is_manager_or_above():
        flash('Accès réservé aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    return render_template('settings/index.html')


@settings_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Edit user profile, payment config and view documents."""
    form = ProfileForm(obj=current_user)

    # Load existing PaymentConfig
    payment_config = UserPaymentConfig.query.get(current_user.id)

    # Pre-fill PaymentConfig fields on GET
    if request.method == 'GET' and payment_config:
        # Note: staff_category et staff_role supprimés du formulaire
        form.contract_type.data = payment_config.contract_type.value if payment_config.contract_type else ''
        form.payment_frequency.data = payment_config.payment_frequency.value if payment_config.payment_frequency else ''
        form.show_rate.data = payment_config.show_rate
        form.daily_rate.data = payment_config.daily_rate
        form.half_day_rate.data = payment_config.half_day_rate
        form.hourly_rate.data = payment_config.hourly_rate
        form.per_diem.data = payment_config.per_diem
        form.overtime_rate_25.data = payment_config.overtime_rate_25
        form.overtime_rate_50.data = payment_config.overtime_rate_50
        form.weekend_rate.data = payment_config.weekend_rate
        form.holiday_rate.data = payment_config.holiday_rate
        form.night_rate.data = payment_config.night_rate
        form.iban.data = payment_config.iban
        form.bic.data = payment_config.bic
        form.bank_name.data = payment_config.bank_name
        form.account_holder.data = payment_config.account_holder
        form.siret.data = payment_config.siret
        form.siren.data = payment_config.siren
        form.vat_number.data = payment_config.vat_number

    if form.validate_on_submit():
        # Check if email is being changed to one that already exists
        if form.email.data != current_user.email:
            existing_user = User.query.filter_by(email=form.email.data).first()
            if existing_user:
                flash('Cette adresse email est déjà utilisée par un autre compte.', 'error')
                return render_template('settings/profile.html', form=form, documents=[])

        try:
            # Basic info
            current_user.first_name = form.first_name.data
            current_user.last_name = form.last_name.data
            current_user.email = form.email.data
            current_user.phone = form.phone.data

            # Personal information
            current_user.date_of_birth = form.date_of_birth.data
            current_user.nationality = form.nationality.data

            # Travel preferences
            current_user.preferred_airline = form.preferred_airline.data
            current_user.seat_preference = form.seat_preference.data or None
            current_user.meal_preference = form.meal_preference.data or None
            current_user.hotel_preferences = form.hotel_preferences.data

            # Emergency contact
            current_user.emergency_contact_name = form.emergency_contact_name.data
            current_user.emergency_contact_relation = form.emergency_contact_relation.data
            current_user.emergency_contact_phone = form.emergency_contact_phone.data
            current_user.emergency_contact_email = form.emergency_contact_email.data

            # Health / Dietary
            current_user.dietary_restrictions = form.dietary_restrictions.data
            current_user.allergies = form.allergies.data

            # ============ SAVE PAYMENT CONFIG ============
            if not payment_config:
                payment_config = UserPaymentConfig(user_id=current_user.id)
                db.session.add(payment_config)

            # Contrat (staff_category et staff_role supprimés - utiliser professions)
            payment_config.contract_type = ContractType(form.contract_type.data) if form.contract_type.data else None
            payment_config.payment_frequency = PaymentFrequency(form.payment_frequency.data) if form.payment_frequency.data else None

            # Tarifs
            payment_config.show_rate = form.show_rate.data
            payment_config.daily_rate = form.daily_rate.data
            payment_config.half_day_rate = form.half_day_rate.data
            payment_config.hourly_rate = form.hourly_rate.data
            payment_config.per_diem = form.per_diem.data

            # Majorations
            payment_config.overtime_rate_25 = form.overtime_rate_25.data
            payment_config.overtime_rate_50 = form.overtime_rate_50.data
            payment_config.weekend_rate = form.weekend_rate.data
            payment_config.holiday_rate = form.holiday_rate.data
            payment_config.night_rate = form.night_rate.data

            # Bancaire
            payment_config.iban = form.iban.data
            payment_config.bic = form.bic.data
            payment_config.bank_name = form.bank_name.data
            payment_config.account_holder = form.account_holder.data

            # Fiscal
            payment_config.siret = form.siret.data
            payment_config.siren = form.siren.data
            payment_config.vat_number = form.vat_number.data

            db.session.commit()
            flash('Profil mis à jour avec succès.', 'success')
            return redirect(url_for('settings.profile'))
        except IntegrityError:
            db.session.rollback()
            flash('Cette adresse email est déjà utilisée par un autre compte.', 'error')

    # Get user's documents
    documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.created_at.desc()).all()

    return render_template('settings/profile.html', form=form, documents=documents)


@settings_bp.route('/profile/documents/upload', methods=['GET', 'POST'])
@login_required
def upload_profile_document():
    """Upload a document to user's own profile."""
    form = ProfileDocumentForm()

    if form.validate_on_submit():
        file = form.file.data
        original_filename = secure_filename(file.filename)
        unique_filename = generate_unique_filename(original_filename)

        # Save file to disk
        upload_folder = get_upload_folder()
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)

        # Get file size
        file_size = os.path.getsize(file_path)

        # Create document record
        document = Document(
            name=original_filename,
            title=form.title.data,
            description=form.description.data,
            document_type=DocumentType(form.document_type.data),
            file_path=unique_filename,
            file_size=file_size,
            mime_type=file.content_type,
            user_id=current_user.id,
            uploaded_by_id=current_user.id,
            expiry_date=form.expiry_date.data
        )
        db.session.add(document)
        db.session.commit()

        flash(f'Document "{form.title.data}" ajouté à votre profil.', 'success')
        return redirect(url_for('settings.profile'))

    return render_template('settings/upload_profile_document.html', form=form)


@settings_bp.route('/profile/documents/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete_profile_document(doc_id):
    """Delete a document from user's own profile."""
    document = Document.query.get_or_404(doc_id)

    # Verify ownership
    if document.user_id != current_user.id:
        flash('Vous ne pouvez supprimer que vos propres documents.', 'error')
        return redirect(url_for('settings.profile'))

    doc_title = document.title

    # Delete file from disk
    upload_folder = get_upload_folder()
    file_path = os.path.join(upload_folder, document.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete record
    db.session.delete(document)
    db.session.commit()

    flash(f'Document "{doc_title}" supprimé.', 'success')
    return redirect(url_for('settings.profile'))


# =============================================================================
# PROFILE PICTURE
# =============================================================================

def resize_profile_picture(file_data, max_size=200):
    """
    Resize image to max_size x max_size pixels.
    Returns tuple (image_bytes, mime_type).
    """
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(file_data))

    # Convert RGBA to RGB if necessary (for JPEG)
    if img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Resize maintaining aspect ratio
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    # Save to bytes
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85, optimize=True)
    return output.getvalue(), 'image/jpeg'


@settings_bp.route('/profile/picture', methods=['POST'])
@login_required
def upload_profile_picture():
    """Upload and resize profile picture to database."""
    if 'picture' not in request.files:
        flash('Aucun fichier sélectionné.', 'error')
        return redirect(url_for('settings.profile'))

    file = request.files['picture']
    if file.filename == '':
        flash('Aucun fichier sélectionné.', 'error')
        return redirect(url_for('settings.profile'))

    # Check file extension
    allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        flash('Format non autorisé. Utilisez JPG, PNG ou GIF.', 'error')
        return redirect(url_for('settings.profile'))

    # Read and check file size (max 5MB before resize)
    file_data = file.read()
    if len(file_data) > 5 * 1024 * 1024:
        flash('Fichier trop volumineux (max 5 MB).', 'error')
        return redirect(url_for('settings.profile'))

    try:
        # Resize image to 200x200 max
        resized_data, mime_type = resize_profile_picture(file_data)

        # Store in database
        current_user.profile_picture_data = resized_data
        current_user.profile_picture_mime = mime_type
        db.session.commit()

        flash('Photo de profil mise à jour.', 'success')
    except Exception as e:
        current_app.logger.error(f'Error resizing profile picture: {e}')
        flash('Erreur lors du traitement de l\'image.', 'error')

    return redirect(url_for('settings.profile'))


@settings_bp.route('/profile/picture/delete', methods=['POST'])
@login_required
def delete_profile_picture():
    """Delete profile picture from database."""
    current_user.profile_picture_data = None
    current_user.profile_picture_mime = None
    db.session.commit()
    flash('Photo de profil supprimée.', 'success')
    return redirect(url_for('settings.profile'))


@settings_bp.route('/profile/picture/<int:user_id>')
def serve_profile_picture(user_id):
    """Serve profile picture from database with caching."""
    user = User.query.get_or_404(user_id)
    if not user.profile_picture_data:
        abort(404)

    return Response(
        user.profile_picture_data,
        mimetype=user.profile_picture_mime,
        headers={
            'Cache-Control': 'public, max-age=86400',  # Cache 24h
            'Content-Length': str(len(user.profile_picture_data))
        }
    )


@settings_bp.route('/password', methods=['GET', 'POST'])
@login_required
def password():
    """Change password."""
    form = PasswordForm()

    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Mot de passe actuel incorrect.', 'error')
            return redirect(url_for('settings.password'))

        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Mot de passe changé avec succès.', 'success')
        return redirect(url_for('settings.index'))

    return render_template('settings/password.html', form=form)


@settings_bp.route('/notifications', methods=['GET', 'POST'])
@login_required
def notifications():
    """Manage notification preferences."""
    form = NotificationForm(obj=current_user)

    if form.validate_on_submit():
        current_user.notify_new_tour = form.notify_new_tour.data
        current_user.notify_guestlist_request = form.notify_guestlist_request.data
        current_user.notify_guestlist_approved = form.notify_guestlist_approved.data
        current_user.notify_tour_reminder = form.notify_tour_reminder.data
        current_user.notify_document_shared = form.notify_document_shared.data
        db.session.commit()
        flash('Préférences de notification mises à jour.', 'success')
        return redirect(url_for('settings.notifications'))

    return render_template('settings/notifications.html', form=form)


# =============================================================================
# USER MANAGEMENT (Manager only)
# =============================================================================

@settings_bp.route('/users')
@login_required
@requires_manager
def users_list():
    """List all users."""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('settings/users.html', users=users)


@settings_bp.route('/users/<int:id>')
@login_required
@requires_manager
def user_detail(id):
    """View user profile with documents (manager only)."""
    user = User.query.get_or_404(id)
    documents = Document.query.filter_by(user_id=id).order_by(Document.created_at.desc()).all()
    return render_template('settings/user_detail.html', user=user, documents=documents)


@settings_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@requires_manager
def users_create():
    """Create a new user and send invitation email."""
    form = UserCreateForm()

    # Setup form choices with defensive handling for all database queries
    form.access_level.choices = get_access_level_choices()

    # Defensive handling for roles (table might not exist or be empty)
    try:
        form.roles.choices = [(r.id, r.name) for r in Role.query.order_by(Role.name).all()]
    except Exception as e:
        current_app.logger.warning(f'Could not load roles in users_create: {e}')
        form.roles.choices = []

    # Defensive handling for profession choices (table might not exist in production)
    try:
        form.profession.choices = [('', '-- Sélectionner --')] + get_profession_choices()
        professions_by_category = get_professions_by_category()
    except Exception as e:
        current_app.logger.warning(f'Could not load professions in users_create: {e}')
        form.profession.choices = [('', '-- Sélectionner --')]
        professions_by_category = {}

    if form.validate_on_submit():
        # Create user with a temporary password (will be set via invitation)
        user = User(
            email=form.email.data.lower(),
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            is_active=True,
            email_verified=False,
            invited_by_id=current_user.id,
            # Access level (v2.0)
            access_level=AccessLevel[form.access_level.data] if form.access_level.data else AccessLevel.STAFF,
            # Label affiliation (v2.0) - free text field
            label_name=form.label_name.data.strip() if form.label_name.data else None,
            # Crew information - Personal
            date_of_birth=form.date_of_birth.data,
            nationality=form.nationality.data,
            # Crew information - Travel preferences
            preferred_airline=form.preferred_airline.data,
            seat_preference=form.seat_preference.data or None,
            meal_preference=form.meal_preference.data or None,
            hotel_preferences=form.hotel_preferences.data,
            # Crew information - Emergency contact
            emergency_contact_name=form.emergency_contact_name.data,
            emergency_contact_relation=form.emergency_contact_relation.data,
            emergency_contact_phone=form.emergency_contact_phone.data,
            emergency_contact_email=form.emergency_contact_email.data,
            # Crew information - Health / Dietary
            dietary_restrictions=form.dietary_restrictions.data,
            allergies=form.allergies.data,
            # Master email preference
            receive_emails=form.receive_emails.data
        )
        # Set a random temporary password (user will set their own via invitation)
        import secrets
        user.set_password(secrets.token_urlsafe(32))

        # Add selected roles (legacy, kept for compatibility)
        for role_id in form.roles.data or []:
            role = Role.query.get(role_id)
            if role:
                user.add_role(role)

        # Generate invitation token (always needed for password setup)
        user.generate_invitation_token()

        db.session.add(user)
        db.session.flush()  # Get user.id before commit

        # Create UserPaymentConfig if any payment field is filled
        if any([form.contract_type.data, form.iban.data, form.show_rate.data, form.daily_rate.data]):
            payment_config = UserPaymentConfig(user_id=user.id)
            # Contrat (staff_category et staff_role supprimés - utiliser professions)
            if form.contract_type.data:
                payment_config.contract_type = ContractType(form.contract_type.data)
            if form.payment_frequency.data:
                payment_config.payment_frequency = PaymentFrequency(form.payment_frequency.data)
            # Taux
            payment_config.show_rate = form.show_rate.data
            payment_config.daily_rate = form.daily_rate.data
            payment_config.half_day_rate = form.half_day_rate.data
            payment_config.hourly_rate = form.hourly_rate.data
            payment_config.per_diem = form.per_diem.data
            # Majorations
            payment_config.overtime_rate_25 = form.overtime_rate_25.data
            payment_config.overtime_rate_50 = form.overtime_rate_50.data
            payment_config.weekend_rate = form.weekend_rate.data
            payment_config.holiday_rate = form.holiday_rate.data
            payment_config.night_rate = form.night_rate.data
            # Bancaire
            payment_config.iban = form.iban.data
            payment_config.bic = form.bic.data
            payment_config.bank_name = form.bank_name.data
            payment_config.account_holder = form.account_holder.data
            # Fiscal
            payment_config.siret = form.siret.data
            payment_config.siren = form.siren.data
            payment_config.vat_number = form.vat_number.data
            db.session.add(payment_config)

        db.session.commit()

        # Add professions (v2.1) - PLUSIEURS professions possibles (checkboxes)
        profession_ids = request.form.getlist('professions')
        primary_profession_id = request.form.get('primary_profession')

        for i, prof_id in enumerate(profession_ids):
            profession = Profession.query.get(int(prof_id))
            if profession:
                # La première profession cochée est principale si pas explicitement définie
                is_primary = (str(prof_id) == str(primary_profession_id)) if primary_profession_id else (i == 0)
                user_profession = UserProfession(
                    user_id=user.id,
                    profession_id=profession.id,
                    is_primary=is_primary
                )
                db.session.add(user_profession)

        db.session.commit()

        # Send invitation email (filtered by receive_emails preference in send_email)
        if form.receive_emails.data:
            try:
                send_invitation_email(user, current_user)
                flash(f'Utilisateur "{user.full_name}" créé. Invitation envoyée à {user.email}.', 'success')
            except Exception as e:
                flash(f'Utilisateur créé mais erreur lors de l\'envoi de l\'email: {str(e)}', 'warning')
        else:
            flash(f'Utilisateur "{user.full_name}" créé (emails désactivés).', 'success')

        return redirect(url_for('settings.users_list'))

    # Afficher les erreurs de validation si POST échoue
    if request.method == 'POST' and form.errors:
        current_app.logger.warning(f'Form validation failed for user creation: {form.errors}')
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'error')

    return render_template(
        'settings/user_form.html',
        form=form,
        title='Créer un utilisateur',
        professions_by_category=professions_by_category
    )


@settings_bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@requires_manager
def users_edit(id):
    """Edit an existing user."""
    user = User.query.get_or_404(id)

    form = UserEditForm(original_email=user.email, obj=user)

    # Setup form choices
    form.access_level.choices = get_access_level_choices()

    # Defensive handling for profession choices (table might not exist)
    try:
        form.profession.choices = [('', '-- Sélectionner --')] + get_profession_choices()
        professions_by_category = get_professions_by_category()
    except Exception as e:
        current_app.logger.warning(f'Could not load professions: {e}')
        form.profession.choices = [('', '-- Sélectionner --')]
        professions_by_category = {}

    # Defensive handling for roles
    try:
        form.roles.choices = [(r.id, r.name) for r in Role.query.order_by(Role.name).all()]
    except Exception as e:
        current_app.logger.warning(f'Could not load roles in users_edit: {e}')
        form.roles.choices = []

    # Load existing PaymentConfig
    payment_config = UserPaymentConfig.query.get(user.id)

    # Get existing profession IDs for this user (for template pre-selection)
    # Defensive handling in case user_professions table/relation has issues
    try:
        selected_profession_ids = [up.profession_id for up in user.user_professions.all()]
        primary_profession = user.user_professions.filter_by(is_primary=True).first()
        primary_profession_id = primary_profession.profession_id if primary_profession else None
    except Exception as e:
        current_app.logger.warning(f'Could not load user professions for user {id}: {e}')
        selected_profession_ids = []
        primary_profession_id = None

    if request.method == 'GET':
        # Pre-fill new fields (v2.0)
        form.access_level.data = user.access_level.name if user.access_level else 'STAFF'
        form.label_name.data = user.label_name or ''
        # Multi-professions (v2.1) - handled by template with selected_profession_ids

        # Legacy fields
        form.roles.data = [r.id for r in user.roles]
        form.is_active.data = user.is_active

        # Pre-fill PaymentConfig fields (staff_category/staff_role supprimés)
        if payment_config:
            form.contract_type.data = payment_config.contract_type.value if payment_config.contract_type else ''
            form.payment_frequency.data = payment_config.payment_frequency.value if payment_config.payment_frequency else ''
            form.show_rate.data = payment_config.show_rate
            form.daily_rate.data = payment_config.daily_rate
            form.half_day_rate.data = payment_config.half_day_rate
            form.hourly_rate.data = payment_config.hourly_rate
            form.per_diem.data = payment_config.per_diem
            form.overtime_rate_25.data = payment_config.overtime_rate_25
            form.overtime_rate_50.data = payment_config.overtime_rate_50
            form.weekend_rate.data = payment_config.weekend_rate
            form.holiday_rate.data = payment_config.holiday_rate
            form.night_rate.data = payment_config.night_rate
            form.iban.data = payment_config.iban
            form.bic.data = payment_config.bic
            form.bank_name.data = payment_config.bank_name
            form.account_holder.data = payment_config.account_holder
            form.siret.data = payment_config.siret
            form.siren.data = payment_config.siren
            form.vat_number.data = payment_config.vat_number

    if form.validate_on_submit():
        user.email = form.email.data.lower()
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.phone = form.phone.data
        user.is_active = form.is_active.data

        # Update access level (v2.0)
        if form.access_level.data:
            user.access_level = AccessLevel[form.access_level.data]

        # Update label affiliation (v2.0) - free text field
        user.label_name = form.label_name.data.strip() if form.label_name.data else None

        # Update professions (v2.1) - PLUSIEURS professions possibles (checkboxes)
        # Remove existing professions
        UserProfession.query.filter_by(user_id=user.id).delete()

        # Add selected professions from checkboxes
        profession_ids = request.form.getlist('professions')
        primary_prof_id = request.form.get('primary_profession')

        for i, prof_id in enumerate(profession_ids):
            profession = Profession.query.get(int(prof_id))
            if profession:
                # Determine if this is the primary profession
                is_primary = (str(prof_id) == str(primary_prof_id)) if primary_prof_id else (i == 0)
                user_profession = UserProfession(
                    user_id=user.id,
                    profession_id=profession.id,
                    is_primary=is_primary
                )
                db.session.add(user_profession)

        # Crew information - Personal
        user.date_of_birth = form.date_of_birth.data
        user.nationality = form.nationality.data

        # Crew information - Travel preferences
        user.preferred_airline = form.preferred_airline.data
        user.seat_preference = form.seat_preference.data or None
        user.meal_preference = form.meal_preference.data or None
        user.hotel_preferences = form.hotel_preferences.data

        # Crew information - Emergency contact
        user.emergency_contact_name = form.emergency_contact_name.data
        user.emergency_contact_relation = form.emergency_contact_relation.data
        user.emergency_contact_phone = form.emergency_contact_phone.data
        user.emergency_contact_email = form.emergency_contact_email.data

        # Crew information - Health / Dietary
        user.dietary_restrictions = form.dietary_restrictions.data
        user.allergies = form.allergies.data

        # Master email preference
        user.receive_emails = form.receive_emails.data

        # Update roles (legacy, kept for compatibility)
        user.roles.clear()
        for role_id in form.roles.data or []:
            role = Role.query.get(role_id)
            if role:
                user.add_role(role)

        # Save PaymentConfig
        if not payment_config:
            payment_config = UserPaymentConfig(user_id=user.id)
            db.session.add(payment_config)

        # Contrat (staff_category/staff_role supprimés - utiliser professions)
        payment_config.contract_type = ContractType(form.contract_type.data) if form.contract_type.data else None
        payment_config.payment_frequency = PaymentFrequency(form.payment_frequency.data) if form.payment_frequency.data else None

        # Taux
        payment_config.show_rate = form.show_rate.data
        payment_config.daily_rate = form.daily_rate.data
        payment_config.half_day_rate = form.half_day_rate.data
        payment_config.hourly_rate = form.hourly_rate.data
        payment_config.per_diem = form.per_diem.data

        # Majorations
        payment_config.overtime_rate_25 = form.overtime_rate_25.data
        payment_config.overtime_rate_50 = form.overtime_rate_50.data
        payment_config.weekend_rate = form.weekend_rate.data
        payment_config.holiday_rate = form.holiday_rate.data
        payment_config.night_rate = form.night_rate.data

        # Bancaire
        payment_config.iban = form.iban.data
        payment_config.bic = form.bic.data
        payment_config.bank_name = form.bank_name.data
        payment_config.account_holder = form.account_holder.data

        # Fiscal
        payment_config.siret = form.siret.data
        payment_config.siren = form.siren.data
        payment_config.vat_number = form.vat_number.data

        db.session.commit()
        flash(f'Utilisateur "{user.full_name}" mis à jour.', 'success')
        return redirect(url_for('settings.users_list'))

    # Afficher les erreurs de validation si POST échoue
    if request.method == 'POST' and form.errors:
        current_app.logger.warning(f'Form validation failed for user {id}: {form.errors}')
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'error')

    return render_template(
        'settings/user_form.html',
        form=form,
        user=user,
        title='Modifier l\'utilisateur',
        professions_by_category=professions_by_category,
        selected_profession_ids=selected_profession_ids,
        primary_profession_id=primary_profession_id
    )


@settings_bp.route('/users/<int:id>/delete', methods=['POST'])
@login_required
@requires_manager
def users_delete(id):
    """Deactivate a user (soft delete)."""
    user = User.query.get_or_404(id)

    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('Vous ne pouvez pas désactiver votre propre compte.', 'error')
        return redirect(url_for('settings.users_list'))

    user.is_active = False
    db.session.commit()
    flash(f'Utilisateur "{user.full_name}" désactivé.', 'success')
    return redirect(url_for('settings.users_list'))


@settings_bp.route('/users/<int:id>/resend', methods=['POST'])
@login_required
@requires_manager
def users_resend_invite(id):
    """Resend invitation email to a user."""
    user = User.query.get_or_404(id)

    # Only resend if user hasn't set their password yet
    if user.email_verified:
        flash('Cet utilisateur a déjà activé son compte.', 'info')
        return redirect(url_for('settings.users_list'))

    # Generate new invitation token
    user.generate_invitation_token()
    db.session.commit()

    # Send invitation email
    try:
        send_invitation_email(user, current_user)
        flash(f'Invitation renvoyée à {user.email}.', 'success')
    except Exception as e:
        flash(f'Erreur lors de l\'envoi de l\'email: {str(e)}', 'error')

    return redirect(url_for('settings.users_list'))


# =============================================================================
# API ENDPOINTS (for AJAX requests)
# =============================================================================

@settings_bp.route('/api/profession/<int:id>')
@login_required
def api_profession_defaults(id):
    """
    API endpoint to get profession defaults (access level, rates).
    Used by JavaScript to auto-fill user creation form.
    """
    from flask import jsonify
    profession = Profession.query.get_or_404(id)
    return jsonify(profession.to_dict())


@settings_bp.route('/api/professions')
@login_required
def api_professions_list():
    """
    API endpoint to get all professions with their defaults.
    Used by JavaScript for form auto-completion.
    """
    from flask import jsonify
    professions = Profession.query.filter_by(is_active=True).order_by(
        Profession.category, Profession.sort_order
    ).all()
    return jsonify([p.to_dict() for p in professions])


# =============================================================================
# PROFESSION MANAGEMENT (Manager only)
# =============================================================================

@settings_bp.route('/professions')
@login_required
@requires_manager
def professions_list():
    """List all professions grouped by category."""
    from app.models.profession import ProfessionCategory, CATEGORY_LABELS, CATEGORY_ICONS, CATEGORY_COLORS

    # Get all professions ordered by category and sort_order
    professions = Profession.query.order_by(
        Profession.category, Profession.sort_order, Profession.name_fr
    ).all()

    # Group by category
    professions_by_category = {}
    for cat in ProfessionCategory:
        professions_by_category[cat] = [p for p in professions if p.category == cat]

    # Stats
    total_count = len(professions)
    active_count = sum(1 for p in professions if p.is_active)
    inactive_count = total_count - active_count

    return render_template(
        'settings/professions.html',
        professions_by_category=professions_by_category,
        category_labels=CATEGORY_LABELS,
        category_icons=CATEGORY_ICONS,
        category_colors=CATEGORY_COLORS,
        total_count=total_count,
        active_count=active_count,
        inactive_count=inactive_count
    )


@settings_bp.route('/professions/create', methods=['GET', 'POST'])
@login_required
@requires_manager
def professions_create():
    """Create a new profession."""
    from app.models.profession import ProfessionCategory, AccessLevel as ProfessionAccessLevel

    form = ProfessionCreateForm()

    # Setup choices
    form.category.choices = get_category_choices()
    form.default_access_level.choices = get_access_level_choices()

    if form.validate_on_submit():
        profession = Profession(
            code=form.code.data.upper(),
            name_fr=form.name_fr.data,
            name_en=form.name_en.data,
            category=ProfessionCategory[form.category.data],
            description=form.description.data,
            sort_order=form.sort_order.data or 0,
            default_access_level=form.default_access_level.data,  # String, not Enum
            is_active=form.is_active.data,
            show_rate=form.show_rate.data,
            daily_rate=form.daily_rate.data,
            weekly_rate=form.weekly_rate.data,
            per_diem=form.per_diem.data,
            default_frequency=form.default_frequency.data or None
        )
        db.session.add(profession)
        db.session.commit()

        flash(f'Profession "{profession.name_fr}" créée avec succès.', 'success')
        return redirect(url_for('settings.professions_list'))

    return render_template(
        'settings/profession_form.html',
        form=form,
        title='Créer une profession'
    )


@settings_bp.route('/professions/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@requires_manager
def professions_edit(id):
    """Edit an existing profession."""
    from app.models.profession import ProfessionCategory

    profession = Profession.query.get_or_404(id)
    form = ProfessionEditForm(original_code=profession.code, obj=profession)

    # Setup choices
    form.category.choices = get_category_choices()
    form.default_access_level.choices = get_access_level_choices()

    if request.method == 'GET':
        # Pre-fill form
        form.category.data = profession.category.name if profession.category else ''
        form.default_access_level.data = profession.default_access_level or 'STAFF'  # Already a string

    if form.validate_on_submit():
        profession.code = form.code.data.upper()
        profession.name_fr = form.name_fr.data
        profession.name_en = form.name_en.data
        profession.category = ProfessionCategory[form.category.data]
        profession.description = form.description.data
        profession.sort_order = form.sort_order.data or 0
        profession.default_access_level = form.default_access_level.data  # String, not Enum
        profession.is_active = form.is_active.data
        profession.show_rate = form.show_rate.data
        profession.daily_rate = form.daily_rate.data
        profession.weekly_rate = form.weekly_rate.data
        profession.per_diem = form.per_diem.data
        profession.default_frequency = form.default_frequency.data or None

        db.session.commit()
        flash(f'Profession "{profession.name_fr}" mise à jour.', 'success')
        return redirect(url_for('settings.professions_list'))

    return render_template(
        'settings/profession_form.html',
        form=form,
        profession=profession,
        title='Modifier la profession'
    )


@settings_bp.route('/professions/<int:id>/toggle', methods=['POST'])
@login_required
@requires_manager
def professions_toggle(id):
    """Toggle profession active/inactive status."""
    profession = Profession.query.get_or_404(id)

    profession.is_active = not profession.is_active
    db.session.commit()

    status = 'activée' if profession.is_active else 'désactivée'
    flash(f'Profession "{profession.name_fr}" {status}.', 'success')
    return redirect(url_for('settings.professions_list'))


@settings_bp.route('/professions/<int:id>/delete', methods=['POST'])
@login_required
@requires_manager
def professions_delete(id):
    """Delete a profession (only if not used by any user)."""
    profession = Profession.query.get_or_404(id)

    # Check if profession is used by any user
    users_count = UserProfession.query.filter_by(profession_id=id).count()
    if users_count > 0:
        flash(f'Impossible de supprimer: {users_count} utilisateur(s) utilisent cette profession.', 'error')
        return redirect(url_for('settings.professions_list'))

    profession_name = profession.name_fr
    db.session.delete(profession)
    db.session.commit()

    flash(f'Profession "{profession_name}" supprimée.', 'success')
    return redirect(url_for('settings.professions_list'))


# =============================================================================
# TRAVEL CARDS MANAGEMENT
# =============================================================================

@settings_bp.route('/users/<int:id>/travel-cards', methods=['POST'])
@login_required
@requires_manager
def add_travel_card(id):
    """Add a travel card to a user (manager only)."""
    user = User.query.get_or_404(id)
    form = TravelCardForm()

    if form.validate_on_submit():
        card = TravelCard(
            user_id=user.id,
            card_number=form.card_number.data,
            card_type=form.card_type.data,
            card_name=form.card_name.data,
            expiry_date=form.expiry_date.data
        )
        db.session.add(card)
        db.session.commit()
        flash(f'Carte "{form.card_name.data or form.card_number.data}" ajoutée.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{error}', 'error')

    return redirect(url_for('settings.users_edit', id=id) + '#voyage')


@settings_bp.route('/users/<int:id>/travel-cards/<int:card_id>/delete', methods=['POST'])
@login_required
@requires_manager
def delete_travel_card(id, card_id):
    """Delete a travel card from a user (manager only)."""
    card = TravelCard.query.filter_by(id=card_id, user_id=id).first_or_404()
    card_name = card.card_name or card.card_number
    db.session.delete(card)
    db.session.commit()
    flash(f'Carte "{card_name}" supprimée.', 'success')
    return redirect(url_for('settings.users_edit', id=id) + '#voyage')


@settings_bp.route('/profile/travel-cards', methods=['POST'])
@login_required
def add_own_travel_card():
    """Add a travel card to current user's own profile."""
    form = TravelCardForm()

    if form.validate_on_submit():
        card = TravelCard(
            user_id=current_user.id,
            card_number=form.card_number.data,
            card_type=form.card_type.data,
            card_name=form.card_name.data,
            expiry_date=form.expiry_date.data
        )
        db.session.add(card)
        db.session.commit()
        flash(f'Carte "{form.card_name.data or form.card_number.data}" ajoutée.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{error}', 'error')

    return redirect(url_for('settings.profile') + '#voyage')


@settings_bp.route('/profile/travel-cards/<int:card_id>/delete', methods=['POST'])
@login_required
def delete_own_travel_card(card_id):
    """Delete a travel card from current user's own profile."""
    card = TravelCard.query.filter_by(id=card_id, user_id=current_user.id).first_or_404()
    card_name = card.card_name or card.card_number
    db.session.delete(card)
    db.session.commit()
    flash(f'Carte "{card_name}" supprimée.', 'success')
    return redirect(url_for('settings.profile') + '#voyage')


@settings_bp.route('/users/<int:id>/hard-delete', methods=['POST'])
@login_required
@requires_manager
def users_hard_delete(id):
    """Permanently delete a user from the system."""
    user = User.query.get_or_404(id)

    # 1. Prevent self-deletion
    if user.id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'error')
        return redirect(url_for('settings.users_list'))

    # P-H1: Check if user can be safely deleted (pending payments, managed bands, etc.)
    if not user.can_delete():
        blockers = user.get_deletion_blockers()
        flash(f'Impossible de supprimer cet utilisateur: {"; ".join(blockers)}', 'error')
        return redirect(url_for('settings.user_detail', id=id))

    # 3. Nullify FK references
    Document.query.filter_by(user_id=user.id).update({'user_id': None})
    Document.query.filter_by(uploaded_by_id=user.id).update({'uploaded_by_id': None})
    GuestlistEntry.query.filter_by(requested_by_id=user.id).update({'requested_by_id': None})
    GuestlistEntry.query.filter_by(approved_by_id=user.id).update({'approved_by_id': None})
    User.query.filter_by(invited_by_id=user.id).update({'invited_by_id': None})

    # 4. Delete role associations
    user.roles.clear()

    # 5. Store name for flash message
    user_name = user.full_name

    # 6. Delete user (BandMembership will cascade)
    db.session.delete(user)
    db.session.commit()

    flash(f'Utilisateur "{user_name}" supprimé définitivement.', 'success')
    return redirect(url_for('settings.users_list'))


# =============================================================================
# PENDING REGISTRATIONS (Manager only)
# =============================================================================

@settings_bp.route('/pending-registrations')
@login_required
@requires_manager
def pending_registrations():
    """List all pending user registrations awaiting approval."""
    # Get users who are inactive and have no invitation token
    # (invitation_token means they were invited by a manager, not self-registered)
    pending_users = User.query.filter(
        User.is_active == False,
        User.invitation_token.is_(None)
    ).order_by(User.created_at.desc()).all()

    return render_template('settings/pending_registrations.html', users=pending_users)


@settings_bp.route('/users/<int:id>/approve', methods=['POST'])
@login_required
@requires_manager
def approve_user(id):
    """Approve a pending user registration."""
    user = User.query.get_or_404(id)

    # Verify this is a pending registration
    if user.is_active:
        flash('Cet utilisateur est déjà actif.', 'info')
        return redirect(url_for('settings.pending_registrations'))

    if user.invitation_token:
        flash('Cet utilisateur a été invité par un manager et doit accepter son invitation.', 'info')
        return redirect(url_for('settings.pending_registrations'))

    # Approve the user
    user.is_active = True
    db.session.commit()

    # Send approval email
    try:
        send_approval_email(user)
        flash(f'Inscription de "{user.full_name}" approuvée. Email de confirmation envoyé.', 'success')
    except Exception as e:
        flash(f'Inscription approuvée mais erreur lors de l\'envoi de l\'email: {str(e)}', 'warning')

    return redirect(url_for('settings.pending_registrations'))


@settings_bp.route('/users/<int:id>/reject', methods=['POST'])
@login_required
@requires_manager
def reject_user(id):
    """Reject and delete a pending user registration."""
    user = User.query.get_or_404(id)

    # Verify this is a pending registration
    if user.is_active:
        flash('Impossible de refuser: cet utilisateur est déjà actif.', 'error')
        return redirect(url_for('settings.pending_registrations'))

    if user.invitation_token:
        flash('Cet utilisateur a été invité par un manager, utilisez la suppression standard.', 'info')
        return redirect(url_for('settings.pending_registrations'))

    # Store info before deletion
    user_name = user.full_name
    user_email = user.email

    # Delete role associations
    user.roles.clear()

    # Delete the user
    db.session.delete(user)
    db.session.commit()

    # Send rejection email
    try:
        send_rejection_email(user_email, user_name)
        flash(f'Inscription de "{user_name}" refusée. Email de notification envoyé.', 'info')
    except Exception as e:
        flash(f'Inscription refusée mais erreur lors de l\'envoi de l\'email: {str(e)}', 'warning')

    return redirect(url_for('settings.pending_registrations'))


# =============================================================================
# CALENDAR INTEGRATIONS
# =============================================================================

@settings_bp.route('/integrations')
@login_required
def integrations():
    """Manage external calendar integrations (Google, Outlook)."""
    from app.models.oauth_token import OAuthToken, OAuthProvider
    from app.blueprints.integrations.google_calendar import is_google_configured
    from app.blueprints.integrations.outlook_calendar import is_microsoft_configured

    # Get current connection status
    google_token = OAuthToken.get_for_user(current_user.id, OAuthProvider.GOOGLE.value)
    outlook_token = OAuthToken.get_for_user(current_user.id, OAuthProvider.MICROSOFT.value)

    return render_template(
        'settings/integrations.html',
        google_configured=is_google_configured(),
        google_connected=google_token is not None,
        google_token=google_token,
        outlook_configured=is_microsoft_configured(),
        outlook_connected=outlook_token is not None,
        outlook_token=outlook_token
    )


# =============================================================================
# EMAIL PREVIEW (Admin/Debug)
# =============================================================================

@settings_bp.route('/email-preview')
@login_required
@requires_manager
def email_preview_list():
    """List all available email templates for preview."""
    templates = [
        {'name': 'password_reset', 'title': 'Reinitialisation mot de passe'},
        {'name': 'welcome', 'title': 'Bienvenue'},
        {'name': 'invitation', 'title': 'Invitation'},
        {'name': 'registration_notification', 'title': 'Notification inscription'},
        {'name': 'registration_approved', 'title': 'Inscription approuvee'},
        {'name': 'registration_rejected', 'title': 'Inscription refusee'},
        {'name': 'guestlist_request', 'title': 'Demande guestlist'},
        {'name': 'guestlist_approved', 'title': 'Guestlist approuvee'},
        {'name': 'guestlist_denied', 'title': 'Guestlist refusee'},
        {'name': 'guestlist_checked_in', 'title': 'Check-in confirme'},
        {'name': 'tour_stop_notification', 'title': 'Notification tournee'},
    ]
    return render_template('settings/email_preview_list.html', templates=templates)


@settings_bp.route('/email-preview/<template_name>')
@login_required
@requires_manager
def email_preview(template_name):
    """Preview a specific email template with mock data."""
    from datetime import date, time
    from app.models.guestlist import EntryType, GuestlistStatus

    # Mock data for all templates
    mock_user = type('User', (), {
        'first_name': 'Jean',
        'last_name': 'Dupont',
        'full_name': 'Jean Dupont',
        'email': 'jean.dupont@example.com',
        'phone': '+33 6 12 34 56 78'
    })()

    mock_band = type('Band', (), {
        'name': 'The Amazing Band'
    })()

    mock_tour = type('Tour', (), {
        'name': 'European Tour 2026'
    })()

    mock_venue = type('Venue', (), {
        'name': 'Le Zenith',
        'address': '211 Avenue Jean Jaures',
        'city': 'Paris',
        'postal_code': '75019',
        'country': 'France'
    })()

    mock_tour_stop = type('TourStop', (), {
        'date': date.today(),
        'doors_time': time(19, 0),
        'soundcheck_time': time(16, 0),
        'set_time': time(21, 0)
    })()

    mock_entry = type('GuestlistEntry', (), {
        'guest_name': 'Marie Martin',
        'guest_email': 'marie.martin@example.com',
        'entry_type': EntryType.VIP,
        'plus_ones': 2,
        'notes': 'VIP - Industrie'
    })()

    mock_invited_by = type('User', (), {
        'full_name': 'Admin Manager'
    })()

    # Template context mapping
    contexts = {
        'password_reset': {
            'user': mock_user,
            'reset_url': 'http://localhost:5000/auth/reset/mock-token-123',
            'expiry_hours': 1
        },
        'welcome': {
            'user': mock_user,
            'login_url': 'http://localhost:5000/auth/login'
        },
        'invitation': {
            'user': mock_user,
            'invited_by': mock_invited_by,
            'accept_url': 'http://localhost:5000/auth/accept/mock-invite-token',
            'expiry_hours': 72
        },
        'registration_notification': {
            'user': mock_user,
            'approval_url': 'http://localhost:5000/settings/pending-registrations'
        },
        'registration_approved': {
            'user': mock_user,
            'login_url': 'http://localhost:5000/auth/login'
        },
        'registration_rejected': {
            'name': 'Pierre Rejected'
        },
        'guestlist_request': {
            'entry': mock_entry,
            'tour_stop': mock_tour_stop,
            'tour': mock_tour,
            'venue': mock_venue,
            'band': mock_band
        },
        'guestlist_approved': {
            'entry': mock_entry,
            'tour_stop': mock_tour_stop,
            'tour': mock_tour,
            'venue': mock_venue,
            'band': mock_band
        },
        'guestlist_denied': {
            'entry': mock_entry,
            'tour_stop': mock_tour_stop,
            'tour': mock_tour,
            'venue': mock_venue,
            'band': mock_band
        },
        'guestlist_checked_in': {
            'entry': mock_entry,
            'tour_stop': mock_tour_stop,
            'tour': mock_tour,
            'venue': mock_venue,
            'band': mock_band
        },
        'tour_stop_notification': {
            'tour_stop': mock_tour_stop,
            'tour': mock_tour,
            'venue': mock_venue,
            'band': mock_band,
            'notification_type': request.args.get('type', 'created')
        },
    }

    if template_name not in contexts:
        abort(404)

    # Check format (html or txt)
    fmt = request.args.get('format', 'html')
    template_file = f'email/{template_name}.{fmt}'

    try:
        content = render_template(template_file, **contexts[template_name])
        if fmt == 'txt':
            return Response(content, mimetype='text/plain')
        return content
    except Exception as e:
        current_app.logger.error(f"Email preview error: {e}")
        abort(404)


# =============================================================================
# EMAIL CONFIGURATION (Manager only)
# =============================================================================

@settings_bp.route('/email-config', methods=['GET', 'POST'])
@login_required
@requires_manager
def email_config():
    """Configure SMTP settings via web interface."""
    from app.models.system_settings import SystemSettings

    if request.method == 'POST':
        # Save settings
        SystemSettings.set('MAIL_SERVER', request.form.get('mail_server'), user_id=current_user.id)
        SystemSettings.set('MAIL_PORT', request.form.get('mail_port'), user_id=current_user.id)
        SystemSettings.set('MAIL_USE_TLS', 'true' if request.form.get('mail_use_tls') else 'false', user_id=current_user.id)
        SystemSettings.set('MAIL_USERNAME', request.form.get('mail_username'), user_id=current_user.id)

        # Only update password if provided
        password = request.form.get('mail_password')
        if password:
            SystemSettings.set('MAIL_PASSWORD', password, encrypted=True, user_id=current_user.id)

        SystemSettings.set('MAIL_DEFAULT_SENDER', request.form.get('mail_default_sender'), user_id=current_user.id)

        # Update timestamp to trigger reload on all workers
        SystemSettings.touch_mail_config()

        db.session.commit()

        # Reload mail config in current app
        _reload_mail_config(current_app)

        flash('Configuration email mise a jour.', 'success')
        return redirect(url_for('settings.email_config'))

    # GET: Load current config (DB takes priority over .env)
    config = {
        'MAIL_SERVER': SystemSettings.get('MAIL_SERVER') or current_app.config.get('MAIL_SERVER'),
        'MAIL_PORT': SystemSettings.get('MAIL_PORT') or current_app.config.get('MAIL_PORT'),
        'MAIL_USE_TLS': SystemSettings.get('MAIL_USE_TLS', 'true'),
        'MAIL_USERNAME': SystemSettings.get('MAIL_USERNAME') or current_app.config.get('MAIL_USERNAME'),
        'MAIL_PASSWORD': SystemSettings.get('MAIL_PASSWORD') or current_app.config.get('MAIL_PASSWORD'),
        'MAIL_DEFAULT_SENDER': SystemSettings.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_DEFAULT_SENDER'),
    }

    email_configured = bool(config['MAIL_USERNAME'] and config['MAIL_PASSWORD'])

    return render_template('settings/email_config.html', config=config, email_configured=email_configured)


@settings_bp.route('/email-config/test', methods=['POST'])
@login_required
@requires_manager
def email_config_test():
    """Test email configuration by sending a test email."""
    from flask_mail import Message
    from app.extensions import mail
    from app.models.system_settings import SystemSettings

    try:
        # Temporarily apply form values for testing
        original_config = {
            'MAIL_SERVER': current_app.config.get('MAIL_SERVER'),
            'MAIL_PORT': current_app.config.get('MAIL_PORT'),
            'MAIL_USE_TLS': current_app.config.get('MAIL_USE_TLS'),
            'MAIL_USERNAME': current_app.config.get('MAIL_USERNAME'),
            'MAIL_PASSWORD': current_app.config.get('MAIL_PASSWORD'),
            'MAIL_DEFAULT_SENDER': current_app.config.get('MAIL_DEFAULT_SENDER'),
        }

        # Apply form values temporarily
        current_app.config['MAIL_SERVER'] = request.form.get('mail_server')
        current_app.config['MAIL_PORT'] = int(request.form.get('mail_port', 587))
        current_app.config['MAIL_USE_TLS'] = request.form.get('mail_use_tls') == 'on'
        current_app.config['MAIL_USERNAME'] = request.form.get('mail_username')

        # Use form password if provided, otherwise use existing
        form_password = request.form.get('mail_password')
        if form_password:
            current_app.config['MAIL_PASSWORD'] = form_password
        else:
            # Try DB password, then fall back to original
            db_password = SystemSettings.get('MAIL_PASSWORD')
            current_app.config['MAIL_PASSWORD'] = db_password or original_config['MAIL_PASSWORD']

        sender = request.form.get('mail_default_sender') or request.form.get('mail_username')
        current_app.config['MAIL_DEFAULT_SENDER'] = sender

        # Reinitialize mail with new config
        mail.init_app(current_app)

        # Send test email
        msg = Message(
            subject='[Test] Configuration Email Tour Manager',
            recipients=[current_user.email],
            body=f'Ce message confirme que la configuration email fonctionne correctement.\n\nEnvoye depuis Tour Manager a {current_user.email}.',
            sender=sender
        )
        mail.send(msg)

        return {'success': True}

    except Exception as e:
        current_app.logger.error(f'Email test failed: {e}')
        return {'success': False, 'error': str(e)}

    finally:
        # Restore original config
        for key, value in original_config.items():
            if value is not None:
                current_app.config[key] = value
        # Reinitialize mail with original config
        mail.init_app(current_app)


def _reload_mail_config(app):
    """Reload mail configuration from database into app config."""
    from app.models.system_settings import SystemSettings
    from app.extensions import mail

    db_config = SystemSettings.get_mail_config()

    if db_config.get('MAIL_SERVER'):
        app.config['MAIL_SERVER'] = db_config['MAIL_SERVER']
    if db_config.get('MAIL_PORT'):
        app.config['MAIL_PORT'] = int(db_config['MAIL_PORT'])
    if db_config.get('MAIL_USE_TLS') is not None:
        app.config['MAIL_USE_TLS'] = db_config['MAIL_USE_TLS'] == 'true'
    if db_config.get('MAIL_USERNAME'):
        app.config['MAIL_USERNAME'] = db_config['MAIL_USERNAME']
    if db_config.get('MAIL_PASSWORD'):
        app.config['MAIL_PASSWORD'] = db_config['MAIL_PASSWORD']
    if db_config.get('MAIL_DEFAULT_SENDER'):
        app.config['MAIL_DEFAULT_SENDER'] = db_config['MAIL_DEFAULT_SENDER']

    # Reinitialize Flask-Mail with updated config
    mail.init_app(app)
