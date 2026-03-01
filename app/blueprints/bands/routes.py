"""
Band management routes.
"""
import os
import uuid
from datetime import datetime

from flask import render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.blueprints.bands import bands_bp
from app.blueprints.bands.forms import BandForm, BandMemberInviteForm, BandMemberEditForm
from app.models.band import Band, BandMembership
from app.models.user import User
from app.extensions import db
from app.decorators import requires_manager, band_access_required
from app.utils.audit import log_create, log_update, log_delete
from app.utils.org_context import get_current_org_id, org_filter_kwargs


# Logo upload settings
ALLOWED_LOGO_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
MAX_LOGO_SIZE = 5 * 1024 * 1024  # 5MB


def get_logos_folder():
    """Get the logos upload folder, creating if needed."""
    logos_folder = os.path.join(current_app.root_path, '..', 'uploads', 'logos')
    os.makedirs(logos_folder, exist_ok=True)
    return logos_folder


def save_logo_file(file):
    """Save uploaded logo and return filename, or None if invalid."""
    if not file or not file.filename:
        return None

    # Sanitize filename and validate extension
    from werkzeug.utils import secure_filename
    safe_name = secure_filename(file.filename)
    ext = safe_name.rsplit('.', 1)[1].lower() if '.' in safe_name else ''
    if ext not in ALLOWED_LOGO_EXTENSIONS:
        return None

    # Validate magic bytes match image format
    image_signatures = {
        'jpg': b'\xff\xd8\xff', 'jpeg': b'\xff\xd8\xff',
        'png': b'\x89PNG', 'gif': b'GIF8', 'webp': b'RIFF',
    }
    header = file.read(8)
    file.seek(0)
    expected_sig = image_signatures.get(ext, b'')
    if expected_sig and not header.startswith(expected_sig):
        return None

    # Check file size via seek (avoid reading full file into memory)
    file.seek(0, 2)
    if file.tell() > MAX_LOGO_SIZE:
        file.seek(0)
        return None
    file.seek(0)

    # Generate unique filename and save
    unique_name = f"{uuid.uuid4().hex}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{ext}"
    logos_folder = get_logos_folder()
    file.save(os.path.join(logos_folder, unique_name))

    return unique_name


def delete_logo_file(filename):
    """Delete logo file from disk."""
    if not filename:
        return
    logos_folder = get_logos_folder()
    filepath = os.path.join(logos_folder, filename)
    if os.path.exists(filepath):
        os.remove(filepath)


@bands_bp.route('/')
@login_required
def index():
    """List all bands accessible to the user."""
    # Admin voit tous les groupes de l'org
    if current_user.is_admin():
        all_bands = Band.query.filter_by(**org_filter_kwargs()).order_by(Band.name).all()
        return render_template(
            'bands/list.html',
            managed_bands=all_bands,
            member_bands=[]
        )

    # Get bands where user is manager or member
    managed_bands = current_user.managed_bands
    member_bands = current_user.bands

    return render_template(
        'bands/list.html',
        managed_bands=managed_bands,
        member_bands=member_bands
    )


@bands_bp.route('/create', methods=['GET', 'POST'])
@login_required
@requires_manager
def create():
    """Create a new band."""
    form = BandForm()

    if form.validate_on_submit():
        # Handle logo upload
        logo_path = None
        if form.logo_file.data:
            logo_path = save_logo_file(form.logo_file.data)

        band = Band(
            org_id=get_current_org_id(),
            name=form.name.data,
            genre=form.genre.data,
            bio=form.bio.data,
            logo_url=form.logo_url.data if not logo_path else None,
            logo_path=logo_path,
            website=form.website.data,
            manager_id=current_user.id
        )
        db.session.add(band)
        db.session.commit()

        log_create('Band', band.id, {'name': band.name})

        flash(f'Le groupe "{band.name}" a été créé avec succès.', 'success')
        return redirect(url_for('bands.detail', id=band.id))

    return render_template('bands/form.html', form=form, title='Créer un groupe')


@bands_bp.route('/<int:id>')
@login_required
@band_access_required
def detail(id, band=None):
    """View band details."""
    return render_template('bands/detail.html', band=band)


@bands_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@band_access_required
def edit(id, band=None):
    """Edit a band."""
    # Only manager or admin can edit
    if not band.is_manager(current_user) and not current_user.is_admin():
        flash('Seul le manager peut modifier le groupe.', 'error')
        return redirect(url_for('bands.detail', id=id))

    form = BandForm(obj=band)

    if form.validate_on_submit():
        # Handle new logo upload
        if form.logo_file.data:
            # Delete old logo if exists
            delete_logo_file(band.logo_path)
            # Save new logo
            band.logo_path = save_logo_file(form.logo_file.data)
            band.logo_url = None  # Clear URL since we have uploaded file
        elif form.logo_url.data and form.logo_url.data != band.logo_url:
            # If URL changed and no file uploaded, use URL
            if band.logo_path:
                delete_logo_file(band.logo_path)
                band.logo_path = None
            band.logo_url = form.logo_url.data

        # Update other fields
        band.name = form.name.data
        band.genre = form.genre.data
        band.bio = form.bio.data
        band.website = form.website.data

        db.session.commit()

        log_update('Band', band.id, {'name': band.name})

        flash('Le groupe a été mis à jour.', 'success')
        return redirect(url_for('bands.detail', id=id))

    return render_template('bands/form.html', form=form, band=band, title='Modifier le groupe')


@bands_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@band_access_required
def delete(id, band=None):
    """Delete a band."""
    # Only manager or admin can delete
    if not band.is_manager(current_user) and not current_user.is_admin():
        flash('Seul le manager peut supprimer le groupe.', 'error')
        return redirect(url_for('bands.detail', id=id))

    # Check if band can be safely deleted
    if not band.can_delete():
        blockers = band.get_deletion_blockers()
        flash(f'Impossible de supprimer le groupe: {"; ".join(blockers)}', 'error')
        return redirect(url_for('bands.detail', id=id))

    band_name = band.name
    log_delete('Band', band.id, {'name': band_name})

    # Delete logo file if exists
    delete_logo_file(band.logo_path)

    db.session.delete(band)
    db.session.commit()

    flash(f'Le groupe "{band_name}" a été supprimé.', 'success')
    return redirect(url_for('bands.index'))


@bands_bp.route('/logos/<filename>')
@login_required
def serve_logo(filename):
    """Serve uploaded logo files."""
    logos_folder = get_logos_folder()
    return send_from_directory(logos_folder, filename)


@bands_bp.route('/<int:id>/invite', methods=['GET', 'POST'])
@login_required
@band_access_required
def invite_member(id, band=None):
    """Invite a member to the band."""
    if not band.is_manager(current_user) and not current_user.is_admin():
        flash('Seul le manager peut inviter des membres.', 'error')
        return redirect(url_for('bands.detail', id=id))

    form = BandMemberInviteForm()

    # Récupérer les IDs des membres existants
    existing_member_ids = [m.user_id for m in band.memberships]
    
    # Récupérer les utilisateurs disponibles (pas déjà membres, pas le manager)
    excluded_ids = existing_member_ids + [band.manager_id]
    available_users = User.query.filter(
        User.id.notin_(excluded_ids),
        User.is_active == True
    ).order_by(User.last_name, User.first_name).all()

    # Peupler le SelectField avec les utilisateurs disponibles
    form.user_id.choices = [(0, 'Sélectionner un utilisateur...')] + [
        (u.id, f"{u.full_name} ({u.email})") for u in available_users
    ]

    if form.validate_on_submit():
        if form.user_id.data == 0:
            flash('Veuillez sélectionner un utilisateur.', 'error')
            return render_template('bands/invite_member.html', form=form, band=band)

        user = User.query.get(form.user_id.data)

        if not user:
            flash('Utilisateur non trouvé.', 'error')
            return render_template('bands/invite_member.html', form=form, band=band)

        # Create membership
        membership = BandMembership(
            user_id=user.id,
            band_id=band.id,
            instrument=form.instrument.data,
            role_in_band=form.role_in_band.data
        )
        db.session.add(membership)
        db.session.commit()

        log_create('BandMembership', membership.id, {
            'user_id': user.id,
            'band_id': band.id
        })

        flash(f'{user.full_name} a été ajouté au groupe.', 'success')
        return redirect(url_for('bands.detail', id=id))

    return render_template('bands/invite_member.html', form=form, band=band)


@bands_bp.route('/<int:id>/members/<int:member_id>/edit', methods=['GET', 'POST'])
@login_required
@band_access_required
def edit_member(id, member_id, band=None):
    """Edit a band member's details."""
    if not band.is_manager(current_user) and not current_user.is_admin():
        flash('Seul le manager peut modifier les membres.', 'error')
        return redirect(url_for('bands.detail', id=id))

    membership = BandMembership.query.filter_by(
        id=member_id,
        band_id=band.id
    ).first_or_404()

    form = BandMemberEditForm(obj=membership)

    if form.validate_on_submit():
        form.populate_obj(membership)
        db.session.commit()

        flash('Les informations du membre ont été mises à jour.', 'success')
        return redirect(url_for('bands.detail', id=id))

    return render_template('bands/edit_member.html', form=form, band=band, membership=membership)


@bands_bp.route('/<int:id>/members/<int:member_id>/remove', methods=['POST'])
@login_required
@band_access_required
def remove_member(id, member_id, band=None):
    """Remove a member from the band."""
    if not band.is_manager(current_user) and not current_user.is_admin():
        flash('Seul le manager peut retirer des membres.', 'error')
        return redirect(url_for('bands.detail', id=id))

    membership = BandMembership.query.filter_by(
        id=member_id,
        band_id=band.id
    ).first_or_404()

    member_name = membership.user.full_name

    log_delete('BandMembership', membership.id, {
        'user_name': member_name,
        'band_id': band.id
    })

    db.session.delete(membership)
    db.session.commit()

    flash(f'{member_name} a été retiré du groupe.', 'success')
    return redirect(url_for('bands.detail', id=id))
