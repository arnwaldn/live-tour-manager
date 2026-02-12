"""
Guestlist management routes.
"""
import csv
from io import StringIO
from flask import render_template, redirect, url_for, flash, request, jsonify, Response, current_app
from flask_login import login_required, current_user

from app.blueprints.guestlist import guestlist_bp
from app.blueprints.guestlist.forms import (
    GuestlistEntryForm, GuestlistApprovalForm,
    GuestlistCheckInForm, GuestlistBulkActionForm
)
from app.models.tour import Tour
from app.models.tour_stop import TourStop
from app.models.guestlist import GuestlistEntry, GuestlistStatus, EntryType
from app.models.user import User
from app.extensions import db
from app.decorators import (
    tour_access_required, guestlist_manage_required, check_in_required
)
from app.utils.audit import log_create, log_update, log_delete
from app.utils.email import send_guestlist_notification


@guestlist_bp.route('/')
@login_required
def index():
    """Guestlist overview - select a tour stop to manage."""
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    # Get all tours for user's bands
    tours = Tour.query.filter(Tour.band_id.in_(user_band_ids)).order_by(Tour.start_date.desc()).all()

    return render_template('guestlist/index.html', tours=tours)


@guestlist_bp.route('/check-in')
@login_required
def check_in_select():
    """Check-in selection - select a tour stop for check-in."""
    if not current_user.is_staff_or_above():
        flash('Vous n\'avez pas la permission d\'effectuer des check-ins.', 'error')
        return redirect(url_for('main.dashboard'))

    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    # Get all tours for user's bands
    tours = Tour.query.filter(Tour.band_id.in_(user_band_ids)).order_by(Tour.start_date.desc()).all()

    return render_template('guestlist/check_in_select.html', tours=tours)


@guestlist_bp.route('/stop/<int:stop_id>')
@login_required
def manage(stop_id):
    """Manage guestlist for a tour stop."""
    stop = TourStop.query.get_or_404(stop_id)
    tour = stop.tour

    # Check access to tour
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('main.dashboard'))

    # Filters
    status_filter = request.args.get('status')
    type_filter = request.args.get('entry_type')
    search = request.args.get('search', '').strip()

    query = GuestlistEntry.query.filter_by(tour_stop_id=stop_id)

    # G-H2: Filter entries by permissions
    # Users without manage_guestlist can only see their own requests or entries where they are the artist
    if not current_user.is_staff_or_above():
        query = query.filter(
            db.or_(
                GuestlistEntry.requested_by_id == current_user.id,
                GuestlistEntry.user_id == current_user.id
            )
        )

    if status_filter:
        try:
            status = GuestlistStatus(status_filter)
            query = query.filter(GuestlistEntry.status == status)
        except ValueError:
            pass

    if type_filter:
        try:
            entry_type = EntryType(type_filter)
            query = query.filter(GuestlistEntry.entry_type == entry_type)
        except ValueError:
            pass

    if search:
        query = query.filter(
            GuestlistEntry.guest_name.ilike(f'%{search}%') |
            GuestlistEntry.guest_email.ilike(f'%{search}%') |
            GuestlistEntry.company.ilike(f'%{search}%')
        )

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    entries = query.order_by(GuestlistEntry.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get all entries for stats (without pagination) - with permission filter (G-H2)
    all_query = GuestlistEntry.query.filter_by(tour_stop_id=stop_id)
    if not current_user.is_staff_or_above():
        all_query = all_query.filter(
            db.or_(
                GuestlistEntry.requested_by_id == current_user.id,
                GuestlistEntry.user_id == current_user.id
            )
        )
    all_entries = all_query.all()

    # Pending entries for approval section (separate query, no filters) - with permission filter (G-H2)
    pending_query = GuestlistEntry.query.filter_by(
        tour_stop_id=stop_id,
        status=GuestlistStatus.PENDING
    )
    if not current_user.is_staff_or_above():
        pending_query = pending_query.filter(
            db.or_(
                GuestlistEntry.requested_by_id == current_user.id,
                GuestlistEntry.user_id == current_user.id
            )
        )
    pending_entries = pending_query.order_by(GuestlistEntry.created_at.desc()).all()

    # Stats based on all entries
    stats = {
        'total': len(all_entries),
        'pending': sum(1 for e in all_entries if e.status == GuestlistStatus.PENDING),
        'approved': sum(1 for e in all_entries if e.status == GuestlistStatus.APPROVED),
        'checked_in': sum(1 for e in all_entries if e.status == GuestlistStatus.CHECKED_IN),
        'total_guests': sum(1 + (e.plus_ones or 0) for e in all_entries if e.status in [GuestlistStatus.APPROVED, GuestlistStatus.CHECKED_IN])
    }

    bulk_form = GuestlistBulkActionForm()

    return render_template(
        'guestlist/manage.html',
        tour=tour,
        stop=stop,
        entries=entries,
        pending_entries=pending_entries,
        stats=stats,
        bulk_form=bulk_form,
        status_filter=status_filter,
        type_filter=type_filter,
        search=search
    )


@guestlist_bp.route('/stop/<int:stop_id>/add', methods=['GET', 'POST'])
@login_required
def add_entry(stop_id):
    """Add a guestlist entry."""
    stop = TourStop.query.get_or_404(stop_id)
    tour = stop.tour

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('main.dashboard'))

    # Check permission to request guestlist
    if not current_user.is_staff_or_above():
        flash('Vous n\'avez pas la permission d\'ajouter des invités.', 'error')
        return redirect(url_for('guestlist.manage', stop_id=stop_id))

    # Récupérer les membres du groupe pour le formulaire (type ARTIST)
    band = tour.band
    band_members = band.members if band else []

    form = GuestlistEntryForm(band_members=band_members)

    if form.validate_on_submit():
        # Déterminer les valeurs guest_name et guest_email
        guest_name = form.guest_name.data
        guest_email = form.guest_email.data
        user_id = None

        # Si type ARTIST et artiste sélectionné (artist_id > 0)
        if form.entry_type.data == 'artist' and form.artist_id.data and form.artist_id.data > 0:
            artist = User.query.get(form.artist_id.data)
            if artist and band and artist in band.members:
                user_id = artist.id
                guest_name = artist.full_name
                guest_email = artist.email
            else:
                flash('Artiste invalide ou non membre du groupe.', 'error')
                return redirect(url_for('guestlist.add_entry', stop_id=stop_id))
        elif form.entry_type.data == 'artist' and not guest_name:
            flash('Veuillez sélectionner un artiste ou entrer un nom.', 'error')
            return redirect(url_for('guestlist.add_entry', stop_id=stop_id))

        entry = GuestlistEntry(
            tour_stop_id=stop_id,
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=form.guest_phone.data,
            entry_type=EntryType(form.entry_type.data),
            plus_ones=form.plus_ones.data or 0,
            company=form.company.data,
            notes=form.notes.data,
            internal_notes=form.internal_notes.data,
            requested_by_id=current_user.id,
            status=GuestlistStatus.PENDING,
            user_id=user_id  # Lien vers l'utilisateur si artiste
        )

        # Auto-approve if user has guestlist management permission
        if current_user.is_staff_or_above():
            entry.status = GuestlistStatus.APPROVED
            entry.approved_by_id = current_user.id

        db.session.add(entry)
        db.session.commit()

        log_create('GuestlistEntry', entry.id, {
            'guest_name': entry.guest_name,
            'tour_stop_id': stop_id,
            'status': entry.status.value
        })

        # Send email notification
        try:
            if entry.status == GuestlistStatus.PENDING:
                # Notify managers of new request
                send_guestlist_notification(entry, 'request')
            elif entry.status == GuestlistStatus.APPROVED and entry.guest_email:
                # Auto-approved: notify guest
                send_guestlist_notification(entry, 'approved')
        except Exception as e:
            current_app.logger.error(f'Email guestlist échoué: {e}')

        flash(f'"{entry.guest_name}" a été ajouté à la guestlist.', 'success')
        return redirect(url_for('guestlist.manage', stop_id=stop_id))

    return render_template(
        'guestlist/entry_form.html',
        form=form,
        tour=tour,
        stop=stop,
        title='Ajouter un invité'
    )


@guestlist_bp.route('/entry/<int:id>')
@login_required
def entry_detail(id):
    """View guestlist entry details."""
    entry = GuestlistEntry.query.get_or_404(id)
    stop = entry.tour_stop
    tour = stop.tour

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('main.dashboard'))

    return render_template('guestlist/entry_detail.html', entry=entry, tour=tour, stop=stop)


@guestlist_bp.route('/entry/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_entry(id):
    """Edit a guestlist entry."""
    entry = GuestlistEntry.query.get_or_404(id)
    stop = entry.tour_stop
    tour = stop.tour

    # G-H1: Block editing of locked entries (checked-in or no-show)
    if not entry.can_edit:
        flash('Cette entrée est verrouillée (déjà check-in) et ne peut plus être modifiée.', 'error')
        return redirect(url_for('guestlist.entry_detail', id=id))

    # Check access and permission
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('main.dashboard'))

    # Only requester or manager can edit
    if entry.requested_by_id != current_user.id and not current_user.is_staff_or_above():
        flash('Vous ne pouvez pas modifier cette entrée.', 'error')
        return redirect(url_for('guestlist.manage', stop_id=stop.id))

    # Récupérer les membres du groupe pour le formulaire
    band = stop.associated_band
    band_members = band.members if band else []

    form = GuestlistEntryForm(band_members=band_members, obj=entry)
    form.entry_type.data = entry.entry_type.value

    # Pré-remplir artist_id si l'entrée a un user_id (artiste lié)
    if entry.user_id:
        form.artist_id.data = entry.user_id

    if form.validate_on_submit():
        # Déterminer les valeurs guest_name et guest_email
        guest_name = form.guest_name.data
        guest_email = form.guest_email.data
        user_id = None

        # Si type ARTIST et artiste sélectionné (artist_id > 0)
        if form.entry_type.data == 'artist' and form.artist_id.data and form.artist_id.data > 0:
            artist = User.query.get(form.artist_id.data)
            if artist and band and artist in band.members:
                user_id = artist.id
                guest_name = artist.full_name
                guest_email = artist.email
            else:
                flash('Artiste invalide ou non membre du groupe.', 'error')
                return redirect(url_for('guestlist.edit_entry', id=id))
        elif form.entry_type.data == 'artist' and not guest_name:
            # Type artiste mais pas d'artiste sélectionné et pas de nom
            flash('Veuillez sélectionner un artiste ou entrer un nom.', 'error')
            return redirect(url_for('guestlist.edit_entry', id=id))
        else:
            # Type non-ARTIST: effacer le lien utilisateur si existait
            user_id = None

        entry.guest_name = guest_name
        entry.guest_email = guest_email
        entry.guest_phone = form.guest_phone.data
        entry.entry_type = EntryType(form.entry_type.data)
        entry.plus_ones = form.plus_ones.data or 0
        entry.company = form.company.data
        entry.notes = form.notes.data
        entry.internal_notes = form.internal_notes.data
        entry.user_id = user_id  # Mettre à jour le lien utilisateur

        db.session.commit()

        log_update('GuestlistEntry', entry.id, {'guest_name': entry.guest_name})

        flash('L\'entrée a été mise à jour.', 'success')
        return redirect(url_for('guestlist.manage', stop_id=stop.id))

    return render_template(
        'guestlist/entry_form.html',
        form=form,
        entry=entry,
        tour=tour,
        stop=stop,
        title='Modifier l\'entrée'
    )


@guestlist_bp.route('/entry/<int:id>/approve', methods=['POST'])
@login_required
def approve_entry(id):
    """Approve a guestlist entry."""
    entry = GuestlistEntry.query.get_or_404(id)
    stop = entry.tour_stop
    tour = stop.tour

    # Check access and permission
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('main.dashboard'))

    if not current_user.is_staff_or_above():
        flash('Vous n\'avez pas la permission de gérer la guestlist.', 'error')
        return redirect(url_for('guestlist.manage', stop_id=stop.id))

    notes = request.form.get('notes', '')
    entry.approve(current_user, notes)

    log_update('GuestlistEntry', entry.id, {'status': 'approved', 'approved_by': current_user.id})

    # Send approval notification email
    try:
        send_guestlist_notification(entry, 'approved')
    except Exception as e:
        current_app.logger.error(f'Email approbation guestlist échoué: {e}')

    flash(f'"{entry.guest_name}" a été approuvé.', 'success')
    return redirect(url_for('guestlist.manage', stop_id=entry.tour_stop_id))


@guestlist_bp.route('/entry/<int:id>/deny', methods=['POST'])
@login_required
def deny_entry(id):
    """Deny a guestlist entry."""
    entry = GuestlistEntry.query.get_or_404(id)
    stop = entry.tour_stop
    tour = stop.tour

    # Check access and permission
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('main.dashboard'))

    if not current_user.is_staff_or_above():
        flash('Vous n\'avez pas la permission de gérer la guestlist.', 'error')
        return redirect(url_for('guestlist.manage', stop_id=stop.id))

    notes = request.form.get('notes', '')
    entry.deny(current_user, notes)

    log_update('GuestlistEntry', entry.id, {'status': 'denied', 'denied_by': current_user.id})

    # Send denial notification email
    try:
        send_guestlist_notification(entry, 'denied')
    except Exception as e:
        current_app.logger.error(f'Email refus guestlist échoué: {e}')

    flash(f'"{entry.guest_name}" a été refusé.', 'warning')
    return redirect(url_for('guestlist.manage', stop_id=entry.tour_stop_id))


@guestlist_bp.route('/entry/<int:id>/delete', methods=['POST'])
@login_required
def delete_entry(id):
    """Delete a guestlist entry."""
    entry = GuestlistEntry.query.get_or_404(id)
    stop = entry.tour_stop
    tour = stop.tour

    # G-H1: Block deletion of locked entries (checked-in or no-show)
    if not entry.can_edit:
        flash('Cette entrée est verrouillée (déjà check-in) et ne peut plus être supprimée.', 'error')
        return redirect(url_for('guestlist.entry_detail', id=id))

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('main.dashboard'))

    # Only requester or manager can delete
    if entry.requested_by_id != current_user.id and not current_user.is_staff_or_above():
        flash('Vous ne pouvez pas supprimer cette entrée.', 'error')
        return redirect(url_for('guestlist.manage', stop_id=stop.id))

    guest_name = entry.guest_name
    log_delete('GuestlistEntry', entry.id, {'guest_name': guest_name})

    db.session.delete(entry)
    db.session.commit()

    flash(f'"{guest_name}" a été supprimé de la guestlist.', 'success')
    return redirect(url_for('guestlist.manage', stop_id=stop.id))


# Check-in Interface
@guestlist_bp.route('/stop/<int:stop_id>/check-in')
@login_required
@check_in_required
def check_in_interface(stop_id, tour_stop=None):
    """Check-in interface for a tour stop."""
    # Get approved entries only
    entries = GuestlistEntry.query.filter_by(
        tour_stop_id=stop_id
    ).filter(
        GuestlistEntry.status.in_([GuestlistStatus.APPROVED, GuestlistStatus.CHECKED_IN])
    ).order_by(GuestlistEntry.guest_name).all()

    # Stats
    approved_entries = [e for e in entries if e.status == GuestlistStatus.APPROVED]
    checked_in_entries = [e for e in entries if e.status == GuestlistStatus.CHECKED_IN]
    stats = {
        'approved': len(approved_entries),  # À entrer (pas encore checked in)
        'checked_in': len(checked_in_entries),  # Déjà entrés
        'total_approved': len(entries),  # Total approuvés (approved + checked_in)
        'total_guests': sum(1 + (e.plus_ones or 0) for e in entries),
        'arrived': sum(1 + (e.checked_in_plus_ones or 0) for e in checked_in_entries)
    }

    return render_template(
        'guestlist/check_in.html',
        tour=tour_stop.tour,
        stop=tour_stop,
        entries=entries,
        stats=stats
    )


@guestlist_bp.route('/entry/<int:id>/check-in', methods=['POST'])
@login_required
def do_check_in(id):
    """Perform check-in for a guest."""
    entry = GuestlistEntry.query.get_or_404(id)
    stop = entry.tour_stop

    # Check permission
    if not current_user.is_staff_or_above():
        return jsonify({'success': False, 'message': 'Permission refusée'}), 403

    if entry.status != GuestlistStatus.APPROVED:
        return jsonify({'success': False, 'message': 'Entrée non approuvée'}), 400

    plus_ones = request.form.get('plus_ones', entry.plus_ones, type=int)
    entry.check_in(plus_ones_arrived=plus_ones)

    log_update('GuestlistEntry', entry.id, {'status': 'checked_in', 'plus_ones_arrived': plus_ones})

    # Send check-in confirmation email (non-blocking)
    if entry.guest_email:
        import threading
        app = current_app._get_current_object()
        entry_id = entry.id

        def send_email_async():
            with app.app_context():
                try:
                    e = GuestlistEntry.query.get(entry_id)
                    if e:
                        send_guestlist_notification(e, 'checked_in')
                except Exception as ex:
                    app.logger.error(f'Email check-in guestlist échoué: {ex}')

        threading.Thread(target=send_email_async, daemon=True).start()

    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': f'{entry.guest_name} check-in effectué',
            'entry_id': entry.id
        })

    flash(f'Check-in effectué pour "{entry.guest_name}"', 'success')
    return redirect(url_for('guestlist.check_in_interface', stop_id=stop.id))


@guestlist_bp.route('/entry/<int:id>/undo-check-in', methods=['POST'])
@login_required
def undo_check_in(id):
    """Undo check-in for a guest."""
    entry = GuestlistEntry.query.get_or_404(id)
    stop = entry.tour_stop

    # Check permission
    if not current_user.is_staff_or_above():
        return jsonify({'success': False, 'message': 'Permission refusée'}), 403

    if entry.status != GuestlistStatus.CHECKED_IN:
        return jsonify({'success': False, 'message': 'Invité non check-in'}), 400

    entry.status = GuestlistStatus.APPROVED
    entry.checked_in_at = None
    entry.checked_in_plus_ones = None
    db.session.commit()

    log_update('GuestlistEntry', entry.id, {'status': 'approved', 'action': 'undo_check_in'})

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': f'Check-in annulé pour {entry.guest_name}',
            'entry_id': entry.id
        })

    flash(f'Check-in annulé pour "{entry.guest_name}"', 'info')
    return redirect(url_for('guestlist.check_in_interface', stop_id=stop.id))


# Bulk Actions
@guestlist_bp.route('/stop/<int:stop_id>/bulk-action', methods=['POST'])
@login_required
def bulk_action(stop_id):
    """Perform bulk action on guestlist entries."""
    stop = TourStop.query.get_or_404(stop_id)
    tour = stop.tour

    # Check access and permission
    if not current_user.is_staff_or_above():
        flash('Permission refusée.', 'error')
        return redirect(url_for('guestlist.manage', stop_id=stop_id))

    action = request.form.get('action')
    entry_ids = request.form.getlist('entry_ids')

    if not entry_ids:
        flash('Aucune entrée sélectionnée.', 'warning')
        return redirect(url_for('guestlist.manage', stop_id=stop_id))

    entries = GuestlistEntry.query.filter(
        GuestlistEntry.id.in_(entry_ids),
        GuestlistEntry.tour_stop_id == stop_id
    ).all()

    count = 0
    approved_entries = []
    denied_entries = []

    for entry in entries:
        if action == 'approve' and entry.status == GuestlistStatus.PENDING:
            entry.approve(current_user)
            approved_entries.append(entry)
            count += 1
        elif action == 'deny' and entry.status == GuestlistStatus.PENDING:
            entry.deny(current_user)
            denied_entries.append(entry)
            count += 1
        elif action == 'delete':
            db.session.delete(entry)
            count += 1

    db.session.commit()

    # Send email notifications for bulk actions
    for entry in approved_entries:
        try:
            send_guestlist_notification(entry, 'approved')
        except Exception as e:
            current_app.logger.error(f'Email bulk approbation échoué pour {entry.guest_name}: {e}')
    for entry in denied_entries:
        try:
            send_guestlist_notification(entry, 'denied')
        except Exception as e:
            current_app.logger.error(f'Email bulk refus échoué pour {entry.guest_name}: {e}')

    action_labels = {
        'approve': 'approuvée(s)',
        'deny': 'refusée(s)',
        'delete': 'supprimée(s)'
    }

    flash(f'{count} entrée(s) {action_labels.get(action, "traitée(s)")}.', 'success')
    return redirect(url_for('guestlist.manage', stop_id=stop_id))


# Export
@guestlist_bp.route('/stop/<int:stop_id>/export')
@login_required
def export_csv(stop_id):
    """Export guestlist to CSV."""
    stop = TourStop.query.get_or_404(stop_id)
    tour = stop.tour

    # Check access and permission
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Accès non autorisé.', 'error')
        return redirect(url_for('main.dashboard'))

    if not current_user.is_staff_or_above():
        flash('Permission refusée.', 'error')
        return redirect(url_for('guestlist.manage', stop_id=stop_id))

    # Get entries
    status_filter = request.args.get('status', 'approved')
    query = GuestlistEntry.query.filter_by(tour_stop_id=stop_id)

    if status_filter == 'approved':
        query = query.filter(GuestlistEntry.status.in_([
            GuestlistStatus.APPROVED, GuestlistStatus.CHECKED_IN
        ]))
    elif status_filter != 'all':
        try:
            status = GuestlistStatus(status_filter)
            query = query.filter(GuestlistEntry.status == status)
        except ValueError:
            pass

    entries = query.order_by(GuestlistEntry.guest_name).all()

    # Create CSV
    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'Nom', 'Email', 'Téléphone', 'Type', '+1', 'Affiliation',
        'Statut', 'Demandé par', 'Notes'
    ])

    # Data
    for entry in entries:
        writer.writerow([
            entry.guest_name,
            entry.guest_email or '',
            entry.guest_phone or '',
            entry.entry_type.value,
            entry.plus_ones or 0,
            entry.company or '',
            entry.status.value,
            entry.requested_by.full_name if entry.requested_by else '',
            entry.notes or ''
        ])

    output.seek(0)

    # Filename
    filename = f"guestlist_{tour.name}_{stop.date}_{status_filter}.csv"
    filename = filename.replace(' ', '_').replace('/', '-')

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


# API Endpoints for AJAX
@guestlist_bp.route('/api/stop/<int:stop_id>/search')
@login_required
def api_search(stop_id):
    """API endpoint for searching guestlist."""
    query = request.args.get('q', '').strip()

    if len(query) < 2:
        return jsonify([])

    entries = GuestlistEntry.query.filter_by(tour_stop_id=stop_id).filter(
        GuestlistEntry.guest_name.ilike(f'%{query}%') |
        GuestlistEntry.guest_email.ilike(f'%{query}%')
    ).filter(
        GuestlistEntry.status.in_([GuestlistStatus.APPROVED, GuestlistStatus.CHECKED_IN])
    ).limit(20).all()

    return jsonify([{
        'id': e.id,
        'name': e.guest_name,
        'email': e.guest_email,
        'type': e.entry_type.value,
        'plus_ones': e.plus_ones,
        'status': e.status.value
    } for e in entries])
