"""
Advancing models for Tour Manager.
Handles event preparation (advancing) workflow for live shows.
"""
import enum
from datetime import datetime

from app.extensions import db


class AdvancingStatus(enum.Enum):
    """Advancing preparation status for a tour stop."""
    NOT_STARTED = 'not_started'
    IN_PROGRESS = 'in_progress'
    WAITING_VENUE = 'waiting_venue'
    COMPLETED = 'completed'
    ISSUES = 'issues'


class ChecklistCategory(enum.Enum):
    """Categories for advancing checklist items."""
    ACCUEIL = 'accueil'
    TECHNIQUE = 'technique'
    CATERING = 'catering'
    HEBERGEMENT = 'hebergement'
    LOGISTIQUE = 'logistique'
    SECURITE = 'securite'
    ADMIN = 'admin'


class RiderCategory(enum.Enum):
    """Categories for rider technical requirements."""
    SON = 'son'
    LUMIERE = 'lumiere'
    SCENE = 'scene'
    BACKLINE = 'backline'
    CATERING = 'catering'
    LOGES = 'loges'


class AdvancingChecklistItem(db.Model):
    """A single checklist item for advancing a tour stop."""

    __tablename__ = 'advancing_checklist_items'

    id = db.Column(db.Integer, primary_key=True)
    tour_stop_id = db.Column(
        db.Integer,
        db.ForeignKey('tour_stops.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    category = db.Column(
        db.Enum(ChecklistCategory, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    label = db.Column(db.String(255), nullable=False)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    completed_by_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    completed_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    sort_order = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tour_stop = db.relationship('TourStop', back_populates='checklist_items')
    completed_by = db.relationship('User', foreign_keys=[completed_by_id])

    def __repr__(self):
        status = '✓' if self.is_completed else '○'
        return f'<ChecklistItem [{status}] {self.label}>'

    def toggle(self, user_id):
        """Toggle completion status."""
        self.is_completed = not self.is_completed
        if self.is_completed:
            self.completed_by_id = user_id
            self.completed_at = datetime.utcnow()
        else:
            self.completed_by_id = None
            self.completed_at = None

    def to_dict(self):
        return {
            'id': self.id,
            'tour_stop_id': self.tour_stop_id,
            'category': self.category.value,
            'label': self.label,
            'is_completed': self.is_completed,
            'completed_by_id': self.completed_by_id,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'notes': self.notes,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'sort_order': self.sort_order,
        }


class AdvancingTemplate(db.Model):
    """Reusable checklist template for advancing."""

    __tablename__ = 'advancing_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    items = db.Column(db.JSON, nullable=False, default=list)
    is_default = db.Column(db.Boolean, default=False)
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def __repr__(self):
        return f'<AdvancingTemplate {self.name}>'


class RiderRequirement(db.Model):
    """A rider technical requirement for a tour stop."""

    __tablename__ = 'rider_requirements'

    id = db.Column(db.Integer, primary_key=True)
    tour_stop_id = db.Column(
        db.Integer,
        db.ForeignKey('tour_stops.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    category = db.Column(
        db.Enum(RiderCategory, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    requirement = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    is_mandatory = db.Column(db.Boolean, default=True)
    is_confirmed = db.Column(db.Boolean, default=False)
    venue_response = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tour_stop = db.relationship('TourStop', back_populates='rider_requirements')

    def __repr__(self):
        status = '✓' if self.is_confirmed else '?'
        return f'<RiderRequirement [{status}] {self.requirement}>'

    def to_dict(self):
        return {
            'id': self.id,
            'tour_stop_id': self.tour_stop_id,
            'category': self.category.value,
            'requirement': self.requirement,
            'quantity': self.quantity,
            'is_mandatory': self.is_mandatory,
            'is_confirmed': self.is_confirmed,
            'venue_response': self.venue_response,
            'notes': self.notes,
        }


class AdvancingContact(db.Model):
    """A venue contact for advancing purposes."""

    __tablename__ = 'advancing_contacts'

    id = db.Column(db.Integer, primary_key=True)
    tour_stop_id = db.Column(
        db.Integer,
        db.ForeignKey('tour_stops.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    is_primary = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    tour_stop = db.relationship('TourStop', back_populates='advancing_contacts')

    def __repr__(self):
        return f'<AdvancingContact {self.name} ({self.role})>'

    def to_dict(self):
        return {
            'id': self.id,
            'tour_stop_id': self.tour_stop_id,
            'name': self.name,
            'role': self.role,
            'email': self.email,
            'phone': self.phone,
            'is_primary': self.is_primary,
            'notes': self.notes,
        }


# ============================================================================
# DEFAULT CHECKLIST TEMPLATE (26 items - French live industry standard)
# ============================================================================

DEFAULT_CHECKLIST_ITEMS = [
    # Accueil
    {'category': 'accueil', 'label': 'Parking bus/camion confirmé', 'sort_order': 1},
    {'category': 'accueil', 'label': 'Accueil artistes organisé', 'sort_order': 2},
    {'category': 'accueil', 'label': 'Accès backstage communiqué', 'sort_order': 3},
    # Technique
    {'category': 'technique', 'label': 'Fiche technique envoyée', 'sort_order': 10},
    {'category': 'technique', 'label': 'Plan de scène confirmé', 'sort_order': 11},
    {'category': 'technique', 'label': 'Backline vérifié', 'sort_order': 12},
    {'category': 'technique', 'label': 'Horaires balance confirmés', 'sort_order': 13},
    # Catering
    {'category': 'catering', 'label': 'Rider catering envoyé', 'sort_order': 20},
    {'category': 'catering', 'label': 'Allergies communiquées', 'sort_order': 21},
    {'category': 'catering', 'label': 'Horaires repas confirmés', 'sort_order': 22},
    # Hébergement
    {'category': 'hebergement', 'label': 'Hôtel réservé', 'sort_order': 30},
    {'category': 'hebergement', 'label': 'Chambres attribuées', 'sort_order': 31},
    {'category': 'hebergement', 'label': 'Adresse communiquée à l\'équipe', 'sort_order': 32},
    {'category': 'hebergement', 'label': 'Check-in/check-out confirmé', 'sort_order': 33},
    # Logistique
    {'category': 'logistique', 'label': 'Transport confirmé', 'sort_order': 40},
    {'category': 'logistique', 'label': 'Itinéraire envoyé', 'sort_order': 41},
    {'category': 'logistique', 'label': 'Horaires chargement/déchargement confirmés', 'sort_order': 42},
    # Sécurité
    {'category': 'securite', 'label': 'Plan sécurité reçu', 'sort_order': 50},
    {'category': 'securite', 'label': 'Assurance vérifiée', 'sort_order': 51},
    {'category': 'securite', 'label': 'Contact sécurité identifié', 'sort_order': 52},
    # Admin
    {'category': 'admin', 'label': 'Contrat signé', 'sort_order': 60},
    {'category': 'admin', 'label': 'Facture préparée', 'sort_order': 61},
    {'category': 'admin', 'label': 'GUSO/intermittence traité', 'sort_order': 62},
    {'category': 'admin', 'label': 'Droits SACEM déclarés', 'sort_order': 63},
    {'category': 'admin', 'label': 'Billetterie confirmée', 'sort_order': 64},
    {'category': 'admin', 'label': 'Autorisations obtenues', 'sort_order': 65},
]
