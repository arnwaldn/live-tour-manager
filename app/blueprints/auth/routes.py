"""
Authentication routes.
"""
from flask import render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse

from app.blueprints.auth import auth_bp
from app.blueprints.auth.forms import (
    LoginForm, RegistrationForm, ForgotPasswordForm,
    ResetPasswordForm, ChangePasswordForm
)
from app.blueprints.settings.forms import SetPasswordForm
from app.models.user import User, Role, AccessLevel
from app.models.organization import Organization, OrganizationMembership, OrgRole
from app.extensions import db, limiter
from app.utils.audit import log_login, log_logout, log_create
from app.utils.org_context import set_current_org
from app.utils.email import send_password_reset_email, send_registration_notification, send_welcome_email


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('5 per minute', methods=['POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()


    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()

        # Check if account is locked
        if user and user.is_locked:
            flash('Votre compte est temporairement verrouillé. Réessayez plus tard.', 'error')
            log_login(user, success=False)
            return render_template('auth/login.html', form=form)

        # Validate credentials
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Votre compte est désactivé. Contactez l\'administrateur.', 'error')
                return render_template('auth/login.html', form=form)

            # Successful login
            user.reset_failed_logins()
            db.session.commit()

            # Regenerate session to prevent session fixation attacks
            session.clear()

            login_user(user, remember=form.remember_me.data)
            log_login(user, success=True)

            # Set org context from user's first membership
            if user.org_memberships:
                set_current_org(user.org_memberships[0].org_id)

            flash(f'Bienvenue, {user.first_name}!', 'success')

            # Redirect to requested page or dashboard (secure: prevent open redirect)
            next_page = request.args.get('next')
            if next_page:
                # Security: Validate the redirect URL to prevent open redirect attacks
                # Only allow paths that start with '/' and don't contain '//' or '\'
                # This prevents attacks like: //evil.com, /\evil.com, /..//..//evil.com
                is_safe = (
                    next_page.startswith('/') and
                    not next_page.startswith('//') and
                    not next_page.startswith('/\\') and
                    '\\' not in next_page
                )
                if is_safe:
                    return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        else:
            # Failed login
            if user:
                user.record_failed_login(
                    max_attempts=current_app.config.get('MAX_LOGIN_ATTEMPTS', 5),
                    lockout_minutes=current_app.config.get('LOCKOUT_DURATION_MINUTES', 15)
                )
                db.session.commit()
                log_login(user, success=False)

            flash('Email ou mot de passe incorrect.', 'error')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit('3 per minute', methods=['POST'])
def register():
    """Handle user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegistrationForm()

    if form.validate_on_submit():
        # Create new user — active immediately (they own the new org)
        user = User(
            email=form.email.data.lower(),
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data or None,
            is_active=True,
            email_verified=False,
            access_level=AccessLevel.ADMIN  # Org owner gets admin access
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.flush()  # Get user.id

        # Create the user's organization (workspace)
        org_name = f"Équipe de {user.full_name}"
        org = Organization(
            name=org_name,
            slug=Organization.generate_slug(org_name),
            email=user.email,
            created_by_id=user.id
        )
        db.session.add(org)
        db.session.flush()  # Get org.id

        # Make user the OWNER of the new org
        membership = OrganizationMembership(
            user_id=user.id,
            org_id=org.id,
            role=OrgRole.OWNER
        )
        db.session.add(membership)
        db.session.commit()

        log_create('User', user.id, {'email': user.email})
        log_create('Organization', org.id, {'name': org.name, 'owner_id': user.id})

        # Auto-login the new user
        login_user(user)
        set_current_org(org.id)
        log_login(user, success=True)

        # Send welcome email (non-blocking — don't prevent registration on failure)
        try:
            send_welcome_email(user)
        except Exception as e:
            current_app.logger.warning(f'Email de bienvenue échoué pour {user.email}: {e}')

        flash(f'Bienvenue {user.first_name} ! Votre espace de travail a été créé.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/pending-approval')
def pending_approval():
    """Page displayed to users waiting for manager approval."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('auth/pending_approval.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    log_logout(current_user)
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('3 per minute', methods=['POST'])
def forgot_password():
    """Handle password reset request."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = ForgotPasswordForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()

        if user:
            token = user.generate_reset_token()
            db.session.commit()

            # Send email with reset link
            email_sent = send_password_reset_email(user, token)

            if not email_sent:
                # Log the error but don't reveal to user
                # SECURITY: Never log tokens - they can be compromised via log aggregation
                current_app.logger.error(f'Failed to send password reset email for user id={user.id}')

        # Always show success message (security: don't reveal if email exists)
        flash('Si cet email est enregistré, vous recevrez un lien de réinitialisation.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset with token."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # Find user with this token
    user = User.query.filter_by(reset_token=token).first()

    if not user or not user.verify_reset_token(token):
        flash('Le lien de réinitialisation est invalide ou expiré.', 'error')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.clear_reset_token()
        user.reset_failed_logins()  # Clear any lockouts
        db.session.commit()

        flash('Votre mot de passe a été réinitialisé. Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form)


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
@limiter.limit('5 per minute', methods=['POST'])
def change_password():
    """Handle password change for logged-in users."""
    form = ChangePasswordForm()

    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Le mot de passe actuel est incorrect.', 'error')
            return render_template('auth/change_password.html', form=form)

        current_user.set_password(form.new_password.data)
        db.session.commit()

        flash('Votre mot de passe a été changé avec succès.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/change_password.html', form=form)


@auth_bp.route('/accept-invite/<token>', methods=['GET', 'POST'])
@limiter.limit('5 per hour')
def accept_invite(token):
    """Accept invitation and set password."""
    if current_user.is_authenticated:
        logout_user()

    # Find user with valid invitation token
    user = User.verify_invitation_token(token)

    if not user:
        flash('Ce lien d\'invitation est invalide ou a expiré.', 'error')
        return redirect(url_for('auth.login'))

    form = SetPasswordForm()

    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.clear_invitation_token()
        user.reset_failed_logins()
        db.session.commit()

        log_create('User', user.id, {'action': 'invitation_accepted', 'email': user.email})

        # Send welcome email
        try:
            send_welcome_email(user)
        except Exception as e:
            current_app.logger.warning(f'Email de bienvenue échoué: {e}')

        flash('Votre mot de passe a été créé avec succès. Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/accept_invite.html', form=form, user=user)
