"""
Document model for storing passports, visas, contracts, and other tour documents.
"""
import os
import enum
from datetime import datetime
from werkzeug.utils import secure_filename

from app.extensions import db


class DocumentType(enum.Enum):
    """Types of documents that can be stored."""
    # Identity & Travel
    PASSPORT = 'passport'
    VISA = 'visa'
    ID_CARD = 'id_card'
    WORK_PERMIT = 'work_permit'

    # Contracts & Legal
    CONTRACT = 'contract'
    RIDER = 'rider'
    INSURANCE = 'insurance'

    # Financial & Banking (NEW - for payments module)
    RIB = 'rib'                           # Releve d'identite bancaire
    BANK_DETAILS = 'bank_details'         # Coordonnees bancaires

    # French Administrative (NEW - for payments module)
    URSSAF_CERTIFICATE = 'urssaf_cert'    # Attestation URSSAF
    CONGES_SPECTACLE = 'conges_spectacle' # Certificat conges spectacles
    SIRET_DOCUMENT = 'siret_doc'          # Extrait Kbis ou SIRET
    TAX_DOCUMENT = 'tax_doc'              # Documents fiscaux

    # Invoices & Receipts (NEW - for payments module)
    INVOICE = 'invoice'                   # Facture recue
    RECEIPT = 'receipt'                   # Recu de paiement
    EXPENSE_RECEIPT = 'expense_receipt'   # Justificatif de frais

    OTHER = 'other'


class Document(db.Model):
    """
    Document model for storing files related to tours, bands, and users.
    Supports passports, visas, contracts, riders, and other tour documents.
    """

    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    document_type = db.Column(db.Enum(DocumentType), nullable=False, default=DocumentType.OTHER)
    description = db.Column(db.Text, nullable=True)

    # File storage
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # Size in bytes
    mime_type = db.Column(db.String(100))

    # Polymorphic ownership - document can belong to user, band, or tour
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    band_id = db.Column(db.Integer, db.ForeignKey('bands.id'), nullable=True, index=True)
    tour_id = db.Column(db.Integer, db.ForeignKey('tours.id'), nullable=True, index=True)

    # Metadata for expiring documents (passports, visas)
    expiry_date = db.Column(db.Date, nullable=True)
    issue_date = db.Column(db.Date, nullable=True)
    document_number = db.Column(db.String(100), nullable=True)  # Passport/visa number
    issuing_country = db.Column(db.String(100), nullable=True)

    # Audit fields
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship(
        'User',
        foreign_keys=[user_id],
        backref=db.backref('documents', lazy='dynamic')
    )
    band = db.relationship(
        'Band',
        foreign_keys=[band_id],
        backref=db.backref('documents', lazy='dynamic')
    )
    tour = db.relationship(
        'Tour',
        foreign_keys=[tour_id],
        backref=db.backref('documents', lazy='dynamic')
    )
    uploaded_by = db.relationship(
        'User',
        foreign_keys=[uploaded_by_id],
        backref=db.backref('uploaded_documents', lazy='dynamic')
    )

    def __repr__(self):
        return f'<Document {self.name} ({self.document_type.value})>'

    @property
    def owner_type(self):
        """Return the type of owner for this document."""
        if self.user_id:
            return 'user'
        elif self.band_id:
            return 'band'
        elif self.tour_id:
            return 'tour'
        return None

    @property
    def owner(self):
        """Return the owner object."""
        if self.user_id:
            return self.user
        elif self.band_id:
            return self.band
        elif self.tour_id:
            return self.tour
        return None

    @property
    def owner_name(self):
        """Return a display name for the owner."""
        if self.user:
            return self.user.full_name
        elif self.band:
            return self.band.name
        elif self.tour:
            return self.tour.name
        return 'Non attribue'

    @property
    def is_expired(self):
        """Check if the document has expired."""
        if self.expiry_date:
            return self.expiry_date < datetime.now().date()
        return False

    @property
    def days_until_expiry(self):
        """Return the number of days until expiry, or None if no expiry date."""
        if self.expiry_date:
            delta = self.expiry_date - datetime.now().date()
            return delta.days
        return None

    @property
    def expiry_status(self):
        """Return expiry status: 'expired', 'expiring_soon', 'valid', or None."""
        days = self.days_until_expiry
        if days is None:
            return None
        if days < 0:
            return 'expired'
        elif days <= 90:  # 3 months warning
            return 'expiring_soon'
        return 'valid'

    @property
    def file_size_formatted(self):
        """Return human-readable file size."""
        if not self.file_size:
            return 'Inconnu'

        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'

    @staticmethod
    def allowed_extensions():
        """Return set of allowed file extensions."""
        return {'pdf', 'jpg', 'jpeg', 'png', 'gif', 'doc', 'docx', 'xls', 'xlsx'}

    @staticmethod
    def max_file_size():
        """Return maximum file size in bytes (16 MB)."""
        return 16 * 1024 * 1024

    # Magic byte signatures for content-based file type validation
    MAGIC_SIGNATURES = {
        'pdf':  [b'%PDF'],
        'jpg':  [b'\xff\xd8\xff'],
        'jpeg': [b'\xff\xd8\xff'],
        'png':  [b'\x89PNG\r\n\x1a\n'],
        'gif':  [b'GIF87a', b'GIF89a'],
        'doc':  [b'\xd0\xcf\x11\xe0'],  # OLE2 Compound Document
        'xls':  [b'\xd0\xcf\x11\xe0'],  # OLE2 Compound Document
        'docx': [b'PK\x03\x04'],        # ZIP archive (Office Open XML)
        'xlsx': [b'PK\x03\x04'],        # ZIP archive (Office Open XML)
    }

    @classmethod
    def is_allowed_file(cls, filename):
        """Check if a filename has an allowed extension."""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in cls.allowed_extensions()

    @classmethod
    def validate_file_content(cls, file_obj, filename):
        """Validate file content matches its extension using magic bytes.

        Args:
            file_obj: File-like object (werkzeug FileStorage or similar)
            filename: Original filename to determine expected type

        Returns:
            (bool, str): (is_valid, error_message)
        """
        if not cls.is_allowed_file(filename):
            return False, 'Extension de fichier non autorisée.'

        ext = filename.rsplit('.', 1)[1].lower()
        signatures = cls.MAGIC_SIGNATURES.get(ext)
        if not signatures:
            return True, ''  # No signature to check, extension is allowed

        # Read first 8 bytes for magic byte check
        header = file_obj.read(8)
        file_obj.seek(0)

        if len(header) < 4:
            return False, 'Fichier vide ou corrompu.'

        for sig in signatures:
            if header[:len(sig)] == sig:
                return True, ''

        return False, f'Le contenu du fichier ne correspond pas au format {ext.upper()}.'

    def get_full_path(self, upload_folder):
        """Return the full filesystem path to the document."""
        return os.path.join(upload_folder, self.stored_filename)

    def delete_file(self, upload_folder):
        """Delete the physical file from storage."""
        full_path = self.get_full_path(upload_folder)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False


class ShareType(enum.Enum):
    """Types de partage de document."""
    VIEW = 'view'     # Lecture seule
    EDIT = 'edit'     # Modification autorisée


class DocumentShare(db.Model):
    """
    Modèle pour le partage de documents entre utilisateurs.

    Permet à un utilisateur de partager un document avec d'autres utilisateurs
    avec différents niveaux de permission (lecture seule ou modification).
    """
    __tablename__ = 'document_shares'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)
    shared_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    shared_to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # Type de partage
    share_type = db.Column(db.Enum(ShareType), default=ShareType.VIEW, nullable=False)

    # Timestamps
    shared_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    document = db.relationship('Document', backref=db.backref('shares', lazy='dynamic', cascade='all, delete-orphan'))
    shared_by = db.relationship('User', foreign_keys=[shared_by_id], backref=db.backref('documents_shared', lazy='dynamic'))
    shared_to = db.relationship('User', foreign_keys=[shared_to_user_id], backref=db.backref('documents_received', lazy='dynamic'))

    # Contrainte unique: un document ne peut être partagé qu'une fois avec le même utilisateur
    __table_args__ = (
        db.UniqueConstraint('document_id', 'shared_to_user_id', name='uq_document_share_recipient'),
    )

    def __repr__(self):
        return f'<DocumentShare doc={self.document_id} to={self.shared_to_user_id}>'

    @property
    def can_edit(self):
        """Vérifier si le destinataire peut modifier le document."""
        return self.share_type == ShareType.EDIT

    @classmethod
    def get_shared_with_user(cls, user_id):
        """Récupérer tous les documents partagés avec un utilisateur."""
        return cls.query.filter_by(shared_to_user_id=user_id).all()

    @classmethod
    def is_shared_with(cls, document_id, user_id):
        """Vérifier si un document est partagé avec un utilisateur."""
        return cls.query.filter_by(document_id=document_id, shared_to_user_id=user_id).first() is not None

    @classmethod
    def get_share(cls, document_id, user_id):
        """Récupérer le partage pour un document et un utilisateur."""
        return cls.query.filter_by(document_id=document_id, shared_to_user_id=user_id).first()
