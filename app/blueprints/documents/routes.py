"""
Routes for document management.
Handles upload, download, edit, and delete operations.
"""
import os
import uuid
import mimetypes
from datetime import datetime

from flask import (
    render_template, redirect, url_for, flash, request,
    current_app, send_from_directory, abort
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.utils.org_context import get_current_org_id, org_filter_kwargs
from app.models.document import Document, DocumentType, DocumentShare, ShareType
from app.models.user import User
from app.models.band import Band
from app.models.tour import Tour
from app.decorators.auth import requires_manager
from app.blueprints.documents import documents_bp
from app.blueprints.documents.forms import (
    DocumentUploadForm, DocumentEditForm, DocumentFilterForm
)


def get_upload_folder():
    """Get the upload folder path, creating it if necessary."""
    upload_folder = current_app.config.get(
        'UPLOAD_FOLDER',
        os.path.join(current_app.root_path, '..', 'uploads', 'documents')
    )
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder


def generate_unique_filename(original_filename):
    """Generate a unique filename while preserving extension."""
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    unique_name = f"{uuid.uuid4().hex}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return f"{unique_name}.{ext}" if ext else unique_name


def can_access_document(document, user):
    """Check if user has access to a document based on ownership or sharing."""
    # User's own documents
    if document.user_id == user.id:
        return True

    # Documents uploaded by user
    if document.uploaded_by_id == user.id:
        return True

    # Get user's bands
    user_bands = user.bands + user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    # Band documents
    if document.band_id and document.band_id in user_band_ids:
        return True

    # Tour documents (check if tour belongs to user's band)
    if document.tour_id:
        for band in user_bands:
            tour_ids = [t.id for t in band.tours]
            if document.tour_id in tour_ids:
                return True

    # Documents partagés avec l'utilisateur
    if DocumentShare.is_shared_with(document.id, user.id):
        return True

    return False


def can_manage_document(document, user):
    """Check if user can manage (edit/share/delete) a document."""
    # Propriétaire ou uploadeur
    if document.user_id == user.id:
        return True
    if document.uploaded_by_id == user.id:
        return True

    # Manager du groupe
    user_bands = user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if document.band_id and document.band_id in user_band_ids:
        return True

    # Manager d'une tournée
    if document.tour_id:
        for band in user_bands:
            tour_ids = [t.id for t in band.tours]
            if document.tour_id in tour_ids:
                return True

    return False


@documents_bp.route('/')
@login_required
def index():
    """List all documents with filtering."""
    form = DocumentFilterForm(request.args, meta={'csrf': False})

    # Get all active users for filter dropdown
    all_users = User.query.filter_by(is_active=True).order_by(User.first_name).all()
    form.user_id.choices = [('', 'Tous les utilisateurs')] + [
        (str(u.id), u.full_name) for u in all_users
    ]

    # Get user's bands for filtering (security: only show documents from user's bands)
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    # Get tour IDs from user's bands
    user_tour_ids = []
    for band in user_bands:
        user_tour_ids.extend([t.id for t in band.tours])

    # Base query - filter by user's access
    query = Document.query.filter(
        db.or_(
            Document.band_id.in_(user_band_ids),           # Band documents
            Document.tour_id.in_(user_tour_ids),           # Tour documents
            Document.user_id == current_user.id,           # User's own documents
            Document.uploaded_by_id == current_user.id     # Documents user uploaded
        )
    )

    # Apply filters
    doc_type = request.args.get('document_type')
    if doc_type:
        try:
            query = query.filter(Document.document_type == DocumentType(doc_type))
        except ValueError:
            pass

    # Filter by user
    user_id_filter = request.args.get('user_id')
    if user_id_filter:
        query = query.filter(Document.user_id == int(user_id_filter))

    owner_type = request.args.get('owner_type')
    if owner_type == 'user':
        query = query.filter(Document.user_id.isnot(None))
    elif owner_type == 'band':
        query = query.filter(Document.band_id.isnot(None))
    elif owner_type == 'tour':
        query = query.filter(Document.tour_id.isnot(None))

    expiry_status = request.args.get('expiry_status')
    if expiry_status == 'expired':
        query = query.filter(Document.expiry_date < datetime.now().date())
    elif expiry_status == 'expiring_soon':
        from datetime import timedelta
        soon = datetime.now().date() + timedelta(days=90)
        query = query.filter(
            Document.expiry_date.isnot(None),
            Document.expiry_date >= datetime.now().date(),
            Document.expiry_date <= soon
        )
    elif expiry_status == 'valid':
        query = query.filter(
            db.or_(
                Document.expiry_date.is_(None),
                Document.expiry_date > datetime.now().date()
            )
        )

    # Order by most recent
    documents = query.order_by(Document.created_at.desc()).all()

    # Count expiring documents for alert
    expiring_count = Document.query.filter(
        Document.expiry_date.isnot(None),
        Document.expiry_date >= datetime.now().date(),
        Document.expiry_date <= datetime.now().date() + __import__('datetime').timedelta(days=90)
    ).count()

    expired_count = Document.query.filter(
        Document.expiry_date < datetime.now().date()
    ).count()

    return render_template(
        'documents/list.html',
        documents=documents,
        form=form,
        expiring_count=expiring_count,
        expired_count=expired_count
    )


@documents_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@requires_manager
def upload():
    """Upload a new document."""
    form = DocumentUploadForm()

    # Populate owner choices
    users = User.query.filter_by(is_active=True).order_by(User.first_name).all()
    bands = Band.query.filter_by(**org_filter_kwargs()).order_by(Band.name).all()
    tours = Tour.query.order_by(Tour.start_date.desc()).all()

    if form.validate_on_submit():
        file = form.file.data

        # Validate file extension + magic bytes
        is_valid, error_msg = Document.validate_file_content(file, file.filename)
        if not is_valid:
            flash(error_msg, 'danger')
            return render_template('documents/upload.html', form=form,
                                   users=users, bands=bands, tours=tours)

        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning

        if file_size > Document.max_file_size():
            flash('Le fichier est trop volumineux (max 16 MB).', 'danger')
            return render_template('documents/upload.html', form=form,
                                   users=users, bands=bands, tours=tours)

        # Generate secure filename
        original_filename = secure_filename(file.filename)
        stored_filename = generate_unique_filename(original_filename)

        # Save file
        upload_folder = get_upload_folder()
        file_path = os.path.join(upload_folder, stored_filename)
        file.save(file_path)

        # Get MIME type
        mime_type = mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'

        # Determine owner
        owner_type = request.form.get('owner_type')
        owner_id = request.form.get('owner_id')

        user_id = None
        band_id = None
        tour_id = None

        if owner_type == 'user' and owner_id:
            user_id = int(owner_id)
        elif owner_type == 'band' and owner_id:
            band_id = int(owner_id)
        elif owner_type == 'tour' and owner_id:
            tour_id = int(owner_id)

        # Create document record
        document = Document(
            name=form.name.data,
            document_type=DocumentType(form.document_type.data),
            description=form.description.data,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            user_id=user_id,
            band_id=band_id,
            tour_id=tour_id,
            document_number=form.document_number.data,
            issue_date=form.issue_date.data,
            expiry_date=form.expiry_date.data,
            issuing_country=form.issuing_country.data,
            uploaded_by_id=current_user.id
        )

        db.session.add(document)
        db.session.commit()

        flash(f'Document "{document.name}" televerse avec succes.', 'success')
        return redirect(url_for('documents.index'))

    return render_template(
        'documents/upload.html',
        form=form,
        users=users,
        bands=bands,
        tours=tours
    )


@documents_bp.route('/<int:id>')
@login_required
def detail(id):
    """View document details."""
    document = Document.query.get_or_404(id)

    # Security: verify user has access to this document
    if not can_access_document(document, current_user):
        abort(403)

    return render_template('documents/detail.html', document=document)


@documents_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@requires_manager
def edit(id):
    """Edit document metadata."""
    document = Document.query.get_or_404(id)

    # Security: verify user has access to this document
    if not can_access_document(document, current_user):
        abort(403)

    form = DocumentEditForm(obj=document)

    if form.validate_on_submit():
        document.name = form.name.data
        document.document_type = DocumentType(form.document_type.data)
        document.description = form.description.data
        document.document_number = form.document_number.data
        document.issue_date = form.issue_date.data
        document.expiry_date = form.expiry_date.data
        document.issuing_country = form.issuing_country.data

        db.session.commit()
        flash('Document mis a jour avec succes.', 'success')
        return redirect(url_for('documents.detail', id=document.id))

    # Pre-fill form
    form.document_type.data = document.document_type.value

    return render_template('documents/edit.html', form=form, document=document)


@documents_bp.route('/<int:id>/download')
@login_required
def download(id):
    """Download a document file."""
    document = Document.query.get_or_404(id)

    # Security: verify user has access to this document
    if not can_access_document(document, current_user):
        abort(403)

    upload_folder = get_upload_folder()

    if not os.path.exists(os.path.join(upload_folder, document.stored_filename)):
        flash('Fichier introuvable.', 'danger')
        return redirect(url_for('documents.index'))

    return send_from_directory(
        upload_folder,
        document.stored_filename,
        download_name=document.original_filename,
        as_attachment=True
    )


@documents_bp.route('/<int:id>/view')
@login_required
def view(id):
    """View a document inline (for images and PDFs)."""
    document = Document.query.get_or_404(id)

    # Security: verify user has access to this document
    if not can_access_document(document, current_user):
        abort(403)

    upload_folder = get_upload_folder()

    if not os.path.exists(os.path.join(upload_folder, document.stored_filename)):
        flash('Fichier introuvable.', 'danger')
        return redirect(url_for('documents.index'))

    return send_from_directory(
        upload_folder,
        document.stored_filename,
        download_name=document.original_filename,
        as_attachment=False  # Affichage inline au lieu de telechargement
    )


@documents_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@requires_manager
def delete(id):
    """Delete a document."""
    document = Document.query.get_or_404(id)

    # Security: verify user has access to this document
    if not can_access_document(document, current_user):
        abort(403)

    # Delete file from storage
    upload_folder = get_upload_folder()
    document.delete_file(upload_folder)

    # Delete database record
    name = document.name
    db.session.delete(document)
    db.session.commit()

    flash(f'Document "{name}" supprime.', 'success')
    return redirect(url_for('documents.index'))


@documents_bp.route('/user/<int:user_id>')
@login_required
def by_user(user_id):
    """List documents for a specific user."""
    user = User.query.get_or_404(user_id)

    # Security: only allow viewing own documents or if manager
    if user_id != current_user.id and not current_user.is_manager_or_above():
        abort(403)

    documents = Document.query.filter_by(user_id=user_id).order_by(Document.created_at.desc()).all()

    return render_template(
        'documents/by_owner.html',
        documents=documents,
        owner=user,
        owner_type='user',
        owner_name=user.full_name
    )


@documents_bp.route('/band/<int:band_id>')
@login_required
def by_band(band_id):
    """List documents for a specific band."""
    band = Band.query.filter_by(id=band_id, **org_filter_kwargs()).first_or_404()

    # Security: verify user is member of this band
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if band_id not in user_band_ids:
        abort(403)

    documents = Document.query.filter_by(band_id=band_id).order_by(Document.created_at.desc()).all()

    return render_template(
        'documents/by_owner.html',
        documents=documents,
        owner=band,
        owner_type='band',
        owner_name=band.name
    )


@documents_bp.route('/tour/<int:tour_id>')
@login_required
def by_tour(tour_id):
    """List documents for a specific tour."""
    tour = Tour.query.get_or_404(tour_id)

    # Security: verify user has access to this tour's band
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        abort(403)

    documents = Document.query.filter_by(tour_id=tour_id).order_by(Document.created_at.desc()).all()

    return render_template(
        'documents/by_owner.html',
        documents=documents,
        owner=tour,
        owner_type='tour',
        owner_name=tour.name
    )


@documents_bp.route('/expiring')
@login_required
def expiring():
    """List documents expiring within 90 days."""
    from datetime import timedelta

    # Get user's bands for filtering
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    # Get tour IDs from user's bands
    user_tour_ids = []
    for band in user_bands:
        user_tour_ids.extend([t.id for t in band.tours])

    soon = datetime.now().date() + timedelta(days=90)

    # Security: only show expiring documents user has access to
    documents = Document.query.filter(
        Document.expiry_date.isnot(None),
        Document.expiry_date <= soon,
        db.or_(
            Document.band_id.in_(user_band_ids),
            Document.tour_id.in_(user_tour_ids),
            Document.user_id == current_user.id,
            Document.uploaded_by_id == current_user.id
        )
    ).order_by(Document.expiry_date.asc()).all()

    return render_template(
        'documents/expiring.html',
        documents=documents
    )


# ==================== PARTAGE DE DOCUMENTS ====================

@documents_bp.route('/<int:id>/share', methods=['GET', 'POST'])
@login_required
def share_document(id):
    """Partager un document avec d'autres utilisateurs."""
    from app.utils.notifications import notify_document_shared

    document = Document.query.get_or_404(id)

    # Vérifier que l'utilisateur peut partager ce document
    if not can_manage_document(document, current_user):
        abort(403)

    if request.method == 'POST':
        user_id = request.form.get('user_id', type=int)
        share_type = request.form.get('share_type', 'view')

        if not user_id:
            flash('Veuillez sélectionner un utilisateur.', 'warning')
            return redirect(url_for('documents.share_document', id=id))

        recipient = User.query.get_or_404(user_id)

        # Vérifier que le destinataire n'est pas l'utilisateur courant
        if recipient.id == current_user.id:
            flash('Vous ne pouvez pas partager un document avec vous-même.', 'warning')
            return redirect(url_for('documents.share_document', id=id))

        # Vérifier si le document n'est pas déjà partagé avec cet utilisateur
        existing_share = DocumentShare.get_share(document.id, recipient.id)
        if existing_share:
            flash(f'Ce document est déjà partagé avec {recipient.full_name}.', 'info')
            return redirect(url_for('documents.share_document', id=id))

        # Créer le partage
        share = DocumentShare(
            document_id=document.id,
            shared_by_id=current_user.id,
            shared_to_user_id=recipient.id,
            share_type=ShareType.EDIT if share_type == 'edit' else ShareType.VIEW
        )
        db.session.add(share)
        db.session.commit()

        # Notification in-app
        try:
            notify_document_shared(document, current_user, recipient)
        except Exception as e:
            current_app.logger.error(f'Notification partage document échoué: {e}')

        # Email notification
        try:
            from app.utils.email import send_document_shared_email
            send_document_shared_email(document, current_user, recipient)
        except Exception as e:
            current_app.logger.error(f'Email partage document échoué: {e}')

        flash(f'Document partagé avec {recipient.full_name}.', 'success')
        return redirect(url_for('documents.detail', id=document.id))

    # GET: Afficher le formulaire de partage
    # Récupérer les utilisateurs avec qui on peut partager
    all_users = User.query.filter(
        User.is_active == True,
        User.id != current_user.id
    ).order_by(User.first_name).all()

    # Récupérer les partages existants
    existing_shares = document.shares.all()

    return render_template(
        'documents/share.html',
        document=document,
        users=all_users,
        existing_shares=existing_shares
    )


@documents_bp.route('/<int:id>/share/<int:share_id>/remove', methods=['POST'])
@login_required
def remove_share(id, share_id):
    """Retirer un partage de document."""
    document = Document.query.get_or_404(id)

    # Vérifier que l'utilisateur peut gérer ce document
    if not can_manage_document(document, current_user):
        abort(403)

    share = DocumentShare.query.filter_by(id=share_id, document_id=id).first_or_404()

    recipient_name = share.shared_to.full_name
    db.session.delete(share)
    db.session.commit()

    flash(f'Partage avec {recipient_name} retiré.', 'success')
    return redirect(url_for('documents.share_document', id=id))


@documents_bp.route('/shared-with-me')
@login_required
def shared_with_me():
    """Liste des documents partagés avec l'utilisateur courant."""
    shares = DocumentShare.get_shared_with_user(current_user.id)

    return render_template(
        'documents/shared_with_me.html',
        shares=shares
    )
