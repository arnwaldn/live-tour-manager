"""
Helper functions for creating in-app notifications.

Ce module fournit des fonctions pour créer des notifications in-app
en parallèle du système email existant.
"""
from app.extensions import db
from app.models.notification import Notification, NotificationType, NotificationCategory


def create_notification(user_id, title, message=None, type=NotificationType.INFO,
                       category=NotificationCategory.SYSTEM, link=None):
    """
    Créer une notification pour un utilisateur.
    
    Args:
        user_id: ID de l'utilisateur destinataire
        title: Titre de la notification
        message: Message détaillé (optionnel)
        type: Type de notification (info, success, warning, error)
        category: Catégorie (tour, guestlist, system, band, registration)
        link: URL de redirection (optionnel)
    
    Returns:
        Notification créée
    """
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
        category=category,
        link=link
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def create_notification_batch(notifications_data):
    """
    Créer plusieurs notifications en une seule transaction.
    
    Args:
        notifications_data: Liste de dictionnaires avec les données de notification
            [{'user_id': 1, 'title': '...', ...}, ...]
    
    Returns:
        Liste des notifications créées
    """
    notifications = []
    for data in notifications_data:
        notification = Notification(
            user_id=data['user_id'],
            title=data['title'],
            message=data.get('message'),
            type=data.get('type', NotificationType.INFO),
            category=data.get('category', NotificationCategory.SYSTEM),
            link=data.get('link')
        )
        db.session.add(notification)
        notifications.append(notification)
    
    db.session.commit()
    return notifications


def notify_user(user, title, message=None, type=NotificationType.INFO,
               category=NotificationCategory.SYSTEM, link=None):
    """
    Notifier un utilisateur (raccourci avec objet User).
    
    Args:
        user: Objet User
        title: Titre de la notification
        message: Message détaillé (optionnel)
        type: Type de notification
        category: Catégorie
        link: URL de redirection (optionnel)
    
    Returns:
        Notification créée
    """
    return create_notification(
        user_id=user.id,
        title=title,
        message=message,
        type=type,
        category=category,
        link=link
    )


def notify_band_members(band, title, message=None, type=NotificationType.INFO,
                        link=None, exclude_user_id=None):
    """
    Notifier tous les membres d'un groupe.
    
    Args:
        band: Objet Band
        title: Titre de la notification
        message: Message détaillé (optionnel)
        type: Type de notification
        link: URL de redirection (optionnel)
        exclude_user_id: ID utilisateur à exclure (ex: l'auteur de l'action)
    
    Returns:
        Liste des notifications créées
    """
    notifications_data = []
    
    for membership in band.memberships:
        if exclude_user_id and membership.user_id == exclude_user_id:
            continue
        
        notifications_data.append({
            'user_id': membership.user_id,
            'title': title,
            'message': message,
            'type': type,
            'category': NotificationCategory.BAND,
            'link': link
        })
    
    if notifications_data:
        return create_notification_batch(notifications_data)
    return []


def notify_managers(title, message=None, type=NotificationType.INFO,
                   category=NotificationCategory.SYSTEM, link=None):
    """
    Notifier tous les managers.
    
    Args:
        title: Titre de la notification
        message: Message détaillé (optionnel)
        type: Type de notification
        category: Catégorie
        link: URL de redirection (optionnel)
    
    Returns:
        Liste des notifications créées
    """
    from app.models.user import User, Role
    
    manager_role = Role.query.filter_by(name='manager').first()
    if not manager_role:
        return []
    
    managers = User.query.filter(User.roles.contains(manager_role)).all()
    
    notifications_data = []
    for manager in managers:
        notifications_data.append({
            'user_id': manager.id,
            'title': title,
            'message': message,
            'type': type,
            'category': category,
            'link': link
        })
    
    if notifications_data:
        return create_notification_batch(notifications_data)
    return []


# === Notifications spécifiques par événement ===

def notify_guestlist_request(guestlist_entry):
    """Notifier les managers d'une nouvelle demande de guestlist."""
    from flask import url_for
    
    title = f"Nouvelle demande guestlist - {guestlist_entry.tour_stop.venue.name}"
    message = (f"{guestlist_entry.name} demande {guestlist_entry.quantity} place(s) "
               f"pour le concert du {guestlist_entry.tour_stop.date.strftime('%d/%m/%Y')}")
    
    link = url_for('guestlist.manage_stop', tour_id=guestlist_entry.tour_stop.tour_id,
                   stop_id=guestlist_entry.tour_stop_id, _external=False)
    
    return notify_managers(
        title=title,
        message=message,
        type=NotificationType.INFO,
        category=NotificationCategory.GUESTLIST,
        link=link
    )


def notify_guestlist_approved(guestlist_entry):
    """Notifier l'utilisateur que sa demande guestlist est approuvée."""
    from flask import url_for
    
    title = "Votre demande guestlist a été approuvée"
    message = (f"Votre demande pour {guestlist_entry.quantity} place(s) "
               f"au concert du {guestlist_entry.tour_stop.date.strftime('%d/%m/%Y')} "
               f"à {guestlist_entry.tour_stop.venue.name} a été acceptée.")
    
    return create_notification(
        user_id=guestlist_entry.user_id,
        title=title,
        message=message,
        type=NotificationType.SUCCESS,
        category=NotificationCategory.GUESTLIST
    )


def notify_guestlist_denied(guestlist_entry, reason=None):
    """Notifier l'utilisateur que sa demande guestlist est refusée."""
    title = "Votre demande guestlist a été refusée"
    message = (f"Votre demande pour le concert du "
               f"{guestlist_entry.tour_stop.date.strftime('%d/%m/%Y')} "
               f"à {guestlist_entry.tour_stop.venue.name} a été refusée.")
    
    if reason:
        message += f"\nRaison: {reason}"
    
    return create_notification(
        user_id=guestlist_entry.user_id,
        title=title,
        message=message,
        type=NotificationType.WARNING,
        category=NotificationCategory.GUESTLIST
    )


def notify_registration_pending(user):
    """Notifier les managers d'une nouvelle inscription en attente."""
    from flask import url_for
    
    title = "Nouvelle inscription en attente"
    message = f"{user.first_name} {user.last_name} ({user.email}) demande à rejoindre la plateforme."
    link = url_for('admin.pending_registrations', _external=False)
    
    return notify_managers(
        title=title,
        message=message,
        type=NotificationType.INFO,
        category=NotificationCategory.REGISTRATION,
        link=link
    )


def notify_registration_approved(user):
    """Notifier l'utilisateur que son inscription est approuvée."""
    title = "Bienvenue ! Votre compte a été activé"
    message = "Votre demande d'inscription a été approuvée. Vous pouvez maintenant accéder à toutes les fonctionnalités."
    
    return create_notification(
        user_id=user.id,
        title=title,
        message=message,
        type=NotificationType.SUCCESS,
        category=NotificationCategory.REGISTRATION
    )


def notify_new_tour_stop(tour_stop, exclude_user_id=None):
    """Notifier les membres du groupe d'un nouveau tour stop."""
    from flask import url_for

    band = tour_stop.associated_band
    if not band:
        return []

    # Gérer le cas où venue est null
    location = tour_stop.venue.name if tour_stop.venue else (tour_stop.location_city or 'Lieu à définir')
    city = tour_stop.venue.city if tour_stop.venue else ''

    title = f"Nouvel événement : {tour_stop.event_label}"
    message = f"Un événement a été ajouté le {tour_stop.date.strftime('%d/%m/%Y')}"
    if city:
        message += f" à {city}"
    message += "."

    link = url_for('tours.stop_detail', id=tour_stop.tour_id, stop_id=tour_stop.id, _external=False)

    return notify_band_members(
        band=band,
        title=title,
        message=message,
        type=NotificationType.INFO,
        link=link,
        exclude_user_id=exclude_user_id
    )


def notify_tour_stop_updated(tour_stop, exclude_user_id=None):
    """Notifier les membres du groupe qu'un tour stop a été modifié."""
    from flask import url_for

    band = tour_stop.associated_band
    if not band:
        return []

    location = tour_stop.venue.name if tour_stop.venue else (tour_stop.location_city or 'Lieu à définir')

    title = f"Événement modifié : {tour_stop.event_label}"
    message = f"L'événement du {tour_stop.date.strftime('%d/%m/%Y')} ({location}) a été mis à jour."
    link = url_for('tours.stop_detail', id=tour_stop.tour_id, stop_id=tour_stop.id, _external=False)

    return notify_band_members(
        band=band,
        title=title,
        message=message,
        type=NotificationType.INFO,
        link=link,
        exclude_user_id=exclude_user_id
    )


def notify_tour_stop_date_changed(tour_stop, original_date, exclude_user_id=None):
    """
    Notifier les membres du groupe d'un changement de date.

    Cette notification est plus importante qu'une simple mise à jour
    car le changement de date impacte les plannings de tous.
    """
    from flask import url_for

    band = tour_stop.associated_band
    if not band:
        return []

    location = tour_stop.venue.name if tour_stop.venue else (tour_stop.location_city or 'Lieu à définir')

    title = f"Date modifiée : {tour_stop.event_label}"
    message = (f"La date de l'événement à {location} a été changée "
               f"du {original_date.strftime('%d/%m/%Y')} "
               f"au {tour_stop.date.strftime('%d/%m/%Y')}.")
    link = url_for('tours.stop_detail', id=tour_stop.tour_id, stop_id=tour_stop.id, _external=False)

    return notify_band_members(
        band=band,
        title=title,
        message=message,
        type=NotificationType.WARNING,  # WARNING car changement important
        link=link,
        exclude_user_id=exclude_user_id
    )


def notify_document_shared(document, shared_by, shared_to):
    """
    Notifier un utilisateur qu'un document a été partagé avec lui.

    Args:
        document: Objet Document
        shared_by: Objet User (celui qui partage)
        shared_to: Objet User (destinataire)

    Returns:
        Notification créée ou None si préférence désactivée
    """
    from flask import url_for

    # Vérifier les préférences de l'utilisateur
    if not getattr(shared_to, 'notify_document_shared', True):
        return None

    title = f"Document partagé : {document.name}"
    message = f"{shared_by.full_name} a partagé le document '{document.name}' avec vous."
    link = url_for('documents.detail', id=document.id, _external=False)

    return create_notification(
        user_id=shared_to.id,
        title=title,
        message=message,
        type=NotificationType.INFO,
        category=NotificationCategory.DOCUMENT,
        link=link
    )
