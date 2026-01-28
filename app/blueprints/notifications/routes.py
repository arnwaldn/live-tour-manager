"""
Routes for notifications management.
"""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app.blueprints.notifications import notifications_bp
from app.models.notification import Notification
from app.extensions import db


@notifications_bp.route('/')
@login_required
def list_notifications():
    """Afficher toutes les notifications de l'utilisateur (sans limite)."""
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Pagination pour l'affichage, mais toutes sont accessibles

    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Notification.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        'notifications/list.html',
        notifications=notifications,
        unread_count=Notification.get_unread_count(current_user.id)
    )


@notifications_bp.route('/api/unread-count')
@login_required
def api_unread_count():
    """API: Obtenir le nombre de notifications non lues."""
    count = Notification.get_unread_count(current_user.id)
    return jsonify({'count': count})


@notifications_bp.route('/api/recent')
@login_required
def api_recent():
    """API: Obtenir les notifications récentes pour le dropdown."""
    limit = request.args.get('limit', 10, type=int)
    notifications = Notification.get_recent(current_user.id, limit=limit)
    return jsonify({
        'notifications': [n.to_dict() for n in notifications],
        'unread_count': Notification.get_unread_count(current_user.id)
    })


@notifications_bp.route('/<int:id>/mark-read', methods=['POST'])
@login_required
def mark_read(id):
    """Marquer une notification comme lue."""
    notification = Notification.query.get_or_404(id)

    # Vérifier que l'utilisateur est le propriétaire
    if notification.user_id != current_user.id:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('notifications.list_notifications'))

    notification.mark_as_read()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})

    return redirect(url_for('notifications.list_notifications'))


@notifications_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    """Marquer toutes les notifications comme lues."""
    Notification.mark_all_read(current_user.id)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})

    flash('Toutes les notifications ont été marquées comme lues.', 'success')
    return redirect(url_for('notifications.list_notifications'))


@notifications_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_notification(id):
    """Supprimer une notification."""
    notification = Notification.query.get_or_404(id)

    # Vérifier que l'utilisateur est le propriétaire
    if notification.user_id != current_user.id:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('notifications.list_notifications'))

    db.session.delete(notification)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})

    flash('Notification supprimée.', 'success')
    return redirect(url_for('notifications.list_notifications'))


@notifications_bp.route('/delete-all', methods=['POST'])
@login_required
def delete_all_notifications():
    """Supprimer toutes les notifications de l'utilisateur."""
    Notification.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})

    flash('Toutes les notifications ont été supprimées.', 'success')
    return redirect(url_for('notifications.list_notifications'))


@notifications_bp.route('/delete-read', methods=['POST'])
@login_required
def delete_read_notifications():
    """Supprimer toutes les notifications lues."""
    Notification.query.filter_by(user_id=current_user.id, is_read=True).delete()
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True})

    flash('Les notifications lues ont été supprimées.', 'success')
    return redirect(url_for('notifications.list_notifications'))
