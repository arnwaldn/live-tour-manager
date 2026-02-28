"""
Email utility module for GigRoute.
Handles all email notifications using Flask-Mailman.
Supports async sending via threading and retry with exponential backoff.
"""
import time
import uuid
import logging
import threading
from flask import render_template, current_app, url_for
from flask_mailman import EmailMessage, EmailMultiAlternatives
from app.extensions import mail

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds (2, 4, 8 with exponential backoff)


def send_email(subject, recipient, template, **kwargs):
    """
    Send an email using Flask-Mailman with retry logic.

    Args:
        subject: Email subject (will be prefixed with [GigRoute])
        recipient: Email address of the recipient
        template: Template name (without .html extension) in templates/email/
        **kwargs: Context variables for the template

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Check if user has emails disabled (master preference)
    from app.models.user import User
    user = User.query.filter_by(email=recipient).first()
    if user and not user.receive_emails:
        logger.info(f"[EMAIL] Ignoré - {recipient} a désactivé la réception des emails")
        return True  # Return True to avoid triggering error handling

    # Generate unique email ID for tracking
    email_id = str(uuid.uuid4())[:8]

    logger.info(f"[EMAIL:{email_id}] Envoi à {recipient} - {subject} (template: {template})")

    try:
        html_body = render_template(f'email/{template}.html', **kwargs)
        text_body = render_template(f'email/{template}.txt', **kwargs) if _template_exists(f'email/{template}.txt') else _html_to_text(html_body)

        msg = EmailMultiAlternatives(
            subject=f"[GigRoute] {subject}",
            body=text_body,
            from_email=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@gigroute.app'),
            to=[recipient],
        )
        msg.attach_alternative(html_body, 'text/html')

        # Send with retry
        return _send_with_retry(msg, email_id, recipient)
    except Exception as e:
        logger.error(f"[EMAIL:{email_id}] Échec construction message - {recipient}: {e}")
        return False


def _send_with_retry(msg, email_id, recipient):
    """
    Send a prepared Message with exponential backoff retry.

    Args:
        msg: EmailMessage object (already built)
        email_id: Tracking ID for logging
        recipient: Recipient email for logging

    Returns:
        bool: True if sent successfully after retries
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            msg.send()
            logger.info(f"[EMAIL:{email_id}] Succès - Email envoyé à {recipient}"
                        + (f" (tentative {attempt})" if attempt > 1 else ""))
            return True
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    f"[EMAIL:{email_id}] Tentative {attempt}/{MAX_RETRIES} échouée "
                    f"pour {recipient}: {e} — retry dans {delay}s"
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"[EMAIL:{email_id}] Échec définitif après {MAX_RETRIES} tentatives "
                    f"pour {recipient}: {last_error}"
                )
    return False


def send_async_email(subject, recipient, template, **kwargs):
    """
    Send email asynchronously in a background thread.

    The template is rendered in the current request context before
    dispatching to the thread, so Jinja context is preserved.

    Args:
        subject: Email subject
        recipient: Recipient email address
        template: Email template name
        **kwargs: Template context variables

    Returns:
        bool: True (always — fire-and-forget, errors are logged)
    """
    from app.models.user import User
    user = User.query.filter_by(email=recipient).first()
    if user and not user.receive_emails:
        logger.info(f"[EMAIL] Ignoré (async) - {recipient} a désactivé la réception des emails")
        return True

    email_id = str(uuid.uuid4())[:8]

    # Render templates in request context (before dispatching to thread)
    try:
        html_body = render_template(f'email/{template}.html', **kwargs)
        text_body = (render_template(f'email/{template}.txt', **kwargs)
                     if _template_exists(f'email/{template}.txt')
                     else _html_to_text(html_body))
        sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@gigroute.app')
    except Exception as e:
        logger.error(f"[EMAIL:{email_id}] Échec rendu template (async) - {recipient}: {e}")
        return False

    msg = EmailMultiAlternatives(
        subject=f"[GigRoute] {subject}",
        body=text_body,
        from_email=sender,
        to=[recipient],
    )
    msg.attach_alternative(html_body, 'text/html')

    # Dispatch to background thread with app context
    app = current_app._get_current_object()

    def _send_in_thread():
        with app.app_context():
            _send_with_retry(msg, email_id, recipient)

    thread = threading.Thread(target=_send_in_thread, daemon=True)
    thread.start()
    logger.info(f"[EMAIL:{email_id}] Dispatch async pour {recipient} - {subject}")
    return True


def send_guestlist_notification(entry, notification_type, extra_context=None):
    """
    Send guestlist notification email.

    Args:
        entry: GuestlistEntry object
        notification_type: 'approved', 'denied', 'request', or 'checked_in'
        extra_context: Additional context variables for the template

    Returns:
        bool: True if email sent successfully
    """
    tour_stop = entry.tour_stop
    # Support standalone events (tour_stop without tour)
    tour = tour_stop.tour if tour_stop else None
    band = tour_stop.associated_band if tour_stop else None  # Uses tour.band or tour_stop.band

    context = {
        'entry': entry,
        'tour_stop': tour_stop,
        'tour': tour,
        'venue': tour_stop.venue if tour_stop else None,
        'band': band,
    }

    if extra_context:
        context.update(extra_context)

    templates = {
        'approved': ('Votre demande guestlist a ete approuvee', 'guestlist_approved'),
        'denied': ('Votre demande guestlist a ete refusee', 'guestlist_denied'),
        'request': ('Nouvelle demande guestlist', 'guestlist_request'),
        'checked_in': ('Confirmation check-in', 'guestlist_checked_in'),
    }

    if notification_type not in templates:
        logger.error(f"Unknown notification type: {notification_type}")
        return False

    subject, template = templates[notification_type]

    # Determine recipient based on notification type
    if notification_type == 'request':
        # Notify managers - use associated band (from tour or standalone event)
        all_managers = _get_manager_emails(band) if band else []
        # Filter by notification preferences
        recipients = [r for r in all_managers if _user_accepts_notification(r, 'notify_guestlist_request')]
        if not recipients and all_managers:
            logger.info("Guestlist request notification skipped - all managers disabled notify_guestlist_request")
    else:
        # Notify the guest or requester
        recipient = entry.guest_email or (entry.requested_by.email if entry.requested_by else None)
        recipients = []
        if recipient:
            # Check notification preferences for approved/denied/checked_in
            if notification_type in ('approved', 'denied', 'checked_in'):
                if _user_accepts_notification(recipient, 'notify_guestlist_approved'):
                    recipients = [recipient]
                else:
                    logger.info(f"Guestlist {notification_type} notification skipped for {recipient} - user disabled notify_guestlist_approved")
            else:
                recipients = [recipient]

    success = True
    for recipient in recipients:
        if recipient:
            if not send_email(subject, recipient, template, **context):
                success = False

    return success


def send_password_reset_email(user, reset_token):
    """
    Send password reset email.

    Args:
        user: User object
        reset_token: Password reset token

    Returns:
        bool: True if email sent successfully
    """
    reset_url = url_for('auth.reset_password', token=reset_token, _external=True)

    return send_email(
        subject='Reinitialisation de votre mot de passe',
        recipient=user.email,
        template='password_reset',
        user=user,
        reset_url=reset_url,
        expiry_hours=1
    )


def send_welcome_email(user):
    """
    Send welcome email to new user.

    Args:
        user: User object

    Returns:
        bool: True if email sent successfully
    """
    login_url = url_for('auth.login', _external=True)

    return send_email(
        subject='Bienvenue sur GigRoute',
        recipient=user.email,
        template='welcome',
        user=user,
        login_url=login_url
    )


def send_invitation_email(user, invited_by):
    """
    Send invitation email to a new user created by a manager.

    Args:
        user: User object (newly created, with invitation_token set)
        invited_by: User object (manager who created the invitation)

    Returns:
        bool: True if email sent successfully
    """
    accept_url = url_for('auth.accept_invite', token=user.invitation_token, _external=True)

    return send_email(
        subject='Invitation a rejoindre GigRoute',
        recipient=user.email,
        template='invitation',
        user=user,
        invited_by=invited_by,
        accept_url=accept_url,
        expiry_hours=72
    )


def send_registration_notification(user):
    """
    Send notification to all managers about a new user registration.

    Args:
        user: User object (newly registered, awaiting approval)

    Returns:
        bool: True if all emails sent successfully
    """
    # Get all system managers
    manager_emails = _get_manager_emails()

    if not manager_emails:
        logger.warning("No manager emails found to notify about new registration")
        return True  # Not a failure, just no recipients

    approval_url = url_for('settings.pending_registrations', _external=True)

    success = True
    for email in manager_emails:
        if not send_email(
            subject=f'Nouvelle inscription: {user.full_name}',
            recipient=email,
            template='registration_notification',
            user=user,
            approval_url=approval_url
        ):
            success = False

    return success


def send_approval_email(user):
    """
    Send email to user notifying that their registration was approved.

    Args:
        user: User object (newly approved)

    Returns:
        bool: True if email sent successfully
    """
    login_url = url_for('auth.login', _external=True)

    return send_email(
        subject='Votre inscription a ete approuvee',
        recipient=user.email,
        template='registration_approved',
        user=user,
        login_url=login_url
    )


def send_rejection_email(email, name):
    """
    Send email to user notifying that their registration was rejected.

    Args:
        email: Email address of the rejected user
        name: Full name of the rejected user

    Returns:
        bool: True if email sent successfully
    """
    return send_email(
        subject='Inscription refusee',
        recipient=email,
        template='registration_rejected',
        name=name
    )


def send_mission_invitation_email(invitation, resend=False):
    """
    Send mission invitation email to a band member.

    Args:
        invitation: MissionInvitation object
        resend: Whether this is a resend (changes subject line)

    Returns:
        bool: True if email sent successfully
    """
    user = invitation.user
    tour_stop = invitation.tour_stop
    tour = tour_stop.tour
    band = tour_stop.associated_band
    venue = tour_stop.venue

    # Check user notification preferences
    if not _user_accepts_notification(user.email, 'notify_new_tour'):
        logger.info(f"Mission invitation skipped for {user.email} - user disabled notify_new_tour")
        return True  # Not a failure, just skipped

    # Build location for subject
    location_name = venue.name if venue else tour_stop.location_city or 'Lieu à définir'

    # Build accept/decline URLs
    accept_url = url_for('tours.mission_accept', token=invitation.token, _external=True)
    decline_url = url_for('tours.mission_decline', token=invitation.token, _external=True)

    subject_prefix = '[RAPPEL] ' if resend else ''
    subject = f"{subject_prefix}Mission: {tour_stop.event_label} à {location_name} le {tour_stop.date.strftime('%d/%m/%Y')}"

    context = {
        'invitation': invitation,
        'user': user,
        'tour_stop': tour_stop,
        'tour': tour,
        'band': band,
        'venue': venue,
        'accept_url': accept_url,
        'decline_url': decline_url,
    }

    return send_email(subject, user.email, 'mission_invitation', **context)


def send_mission_response_notification(invitation):
    """
    Send notification to manager when a member responds to a mission invitation.

    Args:
        invitation: MissionInvitation object (with status already updated)

    Returns:
        bool: True if all emails sent successfully
    """
    tour_stop = invitation.tour_stop
    band = tour_stop.associated_band
    user = invitation.user

    if not band:
        logger.warning(f"Mission response notification skipped - no band for tour stop {tour_stop.id}")
        return True

    # Get manager emails
    manager_emails = _get_manager_emails(band)
    if not manager_emails:
        return True

    location_name = tour_stop.venue.name if tour_stop.venue else tour_stop.location_city or 'Lieu'
    status_text = 'accepté' if invitation.is_accepted else 'refusé'

    subject = f"Réponse mission: {user.full_name} a {status_text} - {location_name} ({tour_stop.date.strftime('%d/%m/%Y')})"

    context = {
        'invitation': invitation,
        'user': user,
        'tour_stop': tour_stop,
        'band': band,
    }

    success = True
    for email in manager_emails:
        if not send_email(subject, email, 'mission_response', **context):
            success = False

    return success


def send_tour_stop_notification(tour_stop, notification_type='created'):
    """
    Send tour stop notification to band members.

    Args:
        tour_stop: TourStop object
        notification_type: 'created', 'updated', or 'cancelled'

    Returns:
        bool: True if all emails sent successfully
    """
    # Support standalone events (tour_stop without tour)
    tour = tour_stop.tour
    band = tour_stop.associated_band  # Uses tour.band or tour_stop.band
    venue = tour_stop.venue

    context = {
        'tour_stop': tour_stop,
        'tour': tour,
        'venue': venue,
        'band': band,
    }

    # Build location name for subject
    location_name = venue.name if venue else tour_stop.location_city or 'Lieu non defini'

    subjects = {
        'created': f'Nouvelle date ajoutee: {location_name}',
        'updated': f'Date modifiee: {location_name}',
        'cancelled': f'Date annulee: {location_name}',
    }

    subject = subjects.get(notification_type, 'Mise a jour tournee')

    # Get all band members - handle case where band is None
    if not band:
        logger.warning(f"Tour stop {tour_stop.id} has no associated band - skipping notification")
        return True  # Not a failure, just nothing to do

    all_recipients = _get_band_member_emails(band)

    # Filter by notification preferences (notify_new_tour)
    recipients = [r for r in all_recipients if _user_accepts_notification(r, 'notify_new_tour')]

    if not recipients and all_recipients:
        logger.info("Tour stop notification skipped - all band members disabled notify_new_tour")

    success = True
    for recipient in recipients:
        if not send_email(subject, recipient, 'tour_stop_notification',
                         notification_type=notification_type, **context):
            success = False

    return success


def send_invoice_email(invoice):
    """
    Send invoice by email to recipient with PDF attachment.

    Args:
        invoice: Invoice model instance

    Returns:
        bool: True if email sent successfully
    """
    if not invoice.recipient_email:
        logger.error(f"[EMAIL] Invoice {invoice.number}: no recipient email")
        return False

    # Check if recipient has emails disabled
    from app.models.user import User
    user = User.query.filter_by(email=invoice.recipient_email).first()
    if user and not user.receive_emails:
        logger.info(f"[EMAIL] Invoice email skipped - {invoice.recipient_email} disabled emails")
        return True

    email_id = str(uuid.uuid4())[:8]
    logger.info(f"[EMAIL:{email_id}] Sending invoice {invoice.number} to {invoice.recipient_email}")

    try:
        # Generate PDF attachment
        from app.utils.pdf_generator import generate_invoice_pdf, PDF_AVAILABLE
        pdf_bytes = None
        if PDF_AVAILABLE:
            pdf_bytes = generate_invoice_pdf(invoice)

        # Type labels for subject
        type_labels = {
            'invoice': 'Facture', 'credit': 'Avoir', 'proforma': 'Proforma',
            'deposit': 'Acompte', 'final': 'Solde',
        }
        type_label = type_labels.get(invoice.type.value, 'Facture')
        subject = f"{type_label} {invoice.number}"

        # Render email body
        context = {
            'invoice': invoice,
            'issuer_name': invoice.issuer_name,
            'recipient_name': invoice.recipient_name,
            'type_label': type_label,
        }
        html_body = render_template('email/invoice_sent.html', **context)
        text_body = _html_to_text(html_body)

        msg = EmailMultiAlternatives(
            subject=f"[GigRoute] {subject}",
            body=text_body,
            from_email=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@gigroute.app'),
            to=[invoice.recipient_email],
        )
        msg.attach_alternative(html_body, 'text/html')

        # Attach PDF
        if pdf_bytes:
            safe_number = invoice.number.replace('/', '-')
            msg.attach(
                f"{safe_number}.pdf",
                pdf_bytes,
                "application/pdf",
            )

        return _send_with_retry(msg, email_id, invoice.recipient_email)
    except Exception as e:
        logger.error(f"[EMAIL:{email_id}] Failed to build invoice email {invoice.number}: {e}")
        return False


def send_document_shared_email(document, shared_by, shared_to):
    """
    Send email when a document is shared with a user.

    Args:
        document: Document object
        shared_by: User who shared the document
        shared_to: User receiving the document

    Returns:
        bool: True if email sent successfully
    """
    # Check user notification preferences
    if not _user_accepts_notification(shared_to.email, 'notify_document_shared'):
        logger.info(f"Document shared email skipped for {shared_to.email} - user disabled notify_document_shared")
        return True  # Not a failure, just skipped

    view_url = url_for('documents.detail', id=document.id, _external=True)

    subject = f'Document partage: {document.name}'

    return send_email(
        subject=subject,
        recipient=shared_to.email,
        template='document_shared',
        document=document,
        shared_by=shared_by,
        shared_to=shared_to,
        view_url=view_url
    )


def send_tour_reminder_email(user, tour_stop, reminder_type):
    """
    Send tour reminder email (J-7 or J-1).

    Args:
        user: User object to send reminder to
        tour_stop: TourStop object
        reminder_type: 'j7' or 'j1'

    Returns:
        bool: True if email sent successfully
    """
    # Check user notification preferences
    if not _user_accepts_notification(user.email, 'notify_tour_reminder'):
        logger.info(f"Tour reminder skipped for {user.email} - user disabled notify_tour_reminder")
        return True  # Not a failure, just skipped

    tour = tour_stop.tour
    band = tour_stop.associated_band
    venue = tour_stop.venue
    location_name = venue.name if venue else tour_stop.location_city or 'Lieu'

    days_text = '7 jours' if reminder_type == 'j7' else 'demain'
    subject = f'Rappel: {tour_stop.event_label} a {location_name} dans {days_text}'

    return send_email(
        subject=subject,
        recipient=user.email,
        template='tour_reminder',
        user=user,
        tour_stop=tour_stop,
        tour=tour,
        band=band,
        venue=venue,
        reminder_type=reminder_type
    )


def _get_manager_emails(band=None):
    """Get email addresses of managers.

    Args:
        band: If provided, get managers for this band. If None, get all system managers.

    Returns:
        list: List of email addresses
    """
    from app.models.user import User, Role

    if band:
        # Band-specific managers
        emails = []
        if band.manager and band.manager.email:
            emails.append(band.manager.email)

        # Also get users with MANAGER level or above
        for membership in band.memberships:
            if membership.user and membership.user.email:
                if membership.user.is_manager_or_above():
                    if membership.user.email not in emails:
                        emails.append(membership.user.email)
        return emails
    else:
        # All system managers
        manager_role = Role.query.filter_by(name='MANAGER').first()
        if not manager_role:
            return []

        managers = User.query.filter(
            User.is_active == True,
            User.roles.contains(manager_role)
        ).all()

        return [m.email for m in managers if m.email]


def _get_band_member_emails(band):
    """Get email addresses of all band members."""
    emails = []
    if band.manager and band.manager.email:
        emails.append(band.manager.email)

    for membership in band.memberships:
        if membership.user and membership.user.email:
            if membership.user.email not in emails:
                emails.append(membership.user.email)

    return emails


def _user_accepts_notification(email, preference_name):
    """
    Check if user with given email accepts this notification type.

    Args:
        email: User email address
        preference_name: Name of the preference flag (e.g., 'notify_guestlist_request')

    Returns:
        bool: True if user accepts notifications, False otherwise.
              Returns True for external users (not in database).
    """
    from app.models.user import User
    user = User.query.filter_by(email=email).first()
    if not user:
        return True  # External user, send by default
    return getattr(user, preference_name, True)


def _template_exists(template_name):
    """Check if a template file exists."""
    try:
        current_app.jinja_env.get_template(template_name)
        return True
    except Exception:
        return False


def _html_to_text(html_content):
    """
    Basic HTML to plain text conversion.
    Strips HTML tags for plain text email version.
    """
    import re
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_content)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Replace multiple newlines
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text
