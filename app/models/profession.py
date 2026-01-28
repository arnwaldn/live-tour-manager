"""
Profession models for professional role categorization.
Separates professional identity from access permissions.
"""
from enum import Enum
from datetime import datetime
from app.extensions import db


class ProfessionCategory(str, Enum):
    """Professional categories for music industry roles."""
    MUSICIEN = "musicien"
    TECHNICIEN = "technicien"
    PRODUCTION = "production"
    STYLE = "style"
    SECURITE = "securite"
    MANAGEMENT = "management"


# Category display labels (French)
CATEGORY_LABELS = {
    ProfessionCategory.MUSICIEN: "Musiciens",
    ProfessionCategory.TECHNICIEN: "Techniciens",
    ProfessionCategory.PRODUCTION: "Production",
    ProfessionCategory.STYLE: "Style & Costumes",
    ProfessionCategory.SECURITE: "Sécurité",
    ProfessionCategory.MANAGEMENT: "Management",
}

# Category icons (Bootstrap Icons)
CATEGORY_ICONS = {
    ProfessionCategory.MUSICIEN: "music-note-beamed",
    ProfessionCategory.TECHNICIEN: "tools",
    ProfessionCategory.PRODUCTION: "clipboard-check",
    ProfessionCategory.STYLE: "brush",
    ProfessionCategory.SECURITE: "shield-check",
    ProfessionCategory.MANAGEMENT: "briefcase",
}

# Category badge colors (Bootstrap classes)
CATEGORY_COLORS = {
    ProfessionCategory.MUSICIEN: "info",
    ProfessionCategory.TECHNICIEN: "success",
    ProfessionCategory.PRODUCTION: "primary",
    ProfessionCategory.STYLE: "pink",
    ProfessionCategory.SECURITE: "danger",
    ProfessionCategory.MANAGEMENT: "secondary",
}


class Profession(db.Model):
    """
    Professional roles in the music industry.
    Reference data - seeded on initialization.
    """
    __tablename__ = 'professions'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name_fr = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100), nullable=False)
    category = db.Column(db.Enum(ProfessionCategory), nullable=False, index=True)
    description = db.Column(db.Text)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    # Default access level suggestion (can be overridden per user)
    default_access_level = db.Column(db.String(20), default='STAFF')

    # Relationships
    user_professions = db.relationship('UserProfession', back_populates='profession', lazy='dynamic')

    def __repr__(self):
        return f'<Profession {self.code}>'

    @property
    def category_label(self):
        """Get localized category label."""
        return CATEGORY_LABELS.get(self.category, self.category.value)

    @property
    def category_icon(self):
        """Get Bootstrap icon name for category."""
        return CATEGORY_ICONS.get(self.category, "person")

    @property
    def category_color(self):
        """Get Bootstrap color class for category."""
        return CATEGORY_COLORS.get(self.category, "secondary")

    @classmethod
    def get_by_category(cls):
        """Get all active professions grouped by category."""
        professions = cls.query.filter_by(is_active=True).order_by(
            cls.category, cls.sort_order
        ).all()

        grouped = {}
        for prof in professions:
            cat = prof.category
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(prof)

        return grouped

    @classmethod
    def get_choices(cls):
        """Get choices for form select fields."""
        return [(p.id, p.name_fr) for p in cls.query.filter_by(is_active=True).order_by(
            cls.category, cls.sort_order
        ).all()]

    def get_default_rates(self):
        """Get default payment rates for this profession."""
        from app.models.profession import PROFESSION_DEFAULT_RATES
        return PROFESSION_DEFAULT_RATES.get(self.code, {})

    def to_dict(self):
        """Serialize profession to dictionary for API responses."""
        rates = self.get_default_rates()
        return {
            'id': self.id,
            'code': self.code,
            'name_fr': self.name_fr,
            'name_en': self.name_en,
            'category': self.category.value,
            'category_label': self.category_label,
            'category_color': self.category_color,
            'default_access_level': self.default_access_level,
            'default_rates': rates
        }


class UserProfession(db.Model):
    """
    Association table linking users to their professions.
    A user can have multiple professions (e.g., guitarist + musical director).
    """
    __tablename__ = 'user_professions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    profession_id = db.Column(db.Integer, db.ForeignKey('professions.id', ondelete='CASCADE'), nullable=False)

    # Is this the user's primary profession?
    is_primary = db.Column(db.Boolean, default=False)

    # Optional notes (e.g., "Spécialiste guitare acoustique")
    notes = db.Column(db.String(255))

    # Audit
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='user_professions')
    profession = db.relationship('Profession', back_populates='user_professions')

    # Unique constraint: user can only have each profession once
    __table_args__ = (
        db.UniqueConstraint('user_id', 'profession_id', name='uq_user_profession'),
    )

    def __repr__(self):
        return f'<UserProfession user={self.user_id} profession={self.profession_id}>'


# ============================================================
# SEED DATA - 35 Professions
# ============================================================
PROFESSIONS_SEED = [
    # MUSICIENS (10)
    {"code": "CHANTEUR", "name_fr": "Chanteur/Chanteuse", "name_en": "Singer", "category": ProfessionCategory.MUSICIEN, "sort_order": 1, "default_access_level": "STAFF"},
    {"code": "GUITARISTE", "name_fr": "Guitariste", "name_en": "Guitarist", "category": ProfessionCategory.MUSICIEN, "sort_order": 2, "default_access_level": "STAFF"},
    {"code": "BATTEUR", "name_fr": "Batteur", "name_en": "Drummer", "category": ProfessionCategory.MUSICIEN, "sort_order": 3, "default_access_level": "STAFF"},
    {"code": "DIRECTEUR_MUSICAL", "name_fr": "Directeur musical", "name_en": "Musical Director", "category": ProfessionCategory.MUSICIEN, "sort_order": 4, "default_access_level": "STAFF"},
    {"code": "CLAVIER", "name_fr": "Claviériste", "name_en": "Keyboardist", "category": ProfessionCategory.MUSICIEN, "sort_order": 5, "default_access_level": "STAFF"},
    {"code": "BASSISTE", "name_fr": "Bassiste", "name_en": "Bassist", "category": ProfessionCategory.MUSICIEN, "sort_order": 6, "default_access_level": "STAFF"},
    {"code": "PERCUSSIONS", "name_fr": "Percussionniste", "name_en": "Percussionist", "category": ProfessionCategory.MUSICIEN, "sort_order": 7, "default_access_level": "STAFF"},
    {"code": "CORDES", "name_fr": "Musicien cordes", "name_en": "String Musician", "category": ProfessionCategory.MUSICIEN, "sort_order": 8, "default_access_level": "STAFF"},
    {"code": "CHORISTE", "name_fr": "Choriste", "name_en": "Backing Vocalist", "category": ProfessionCategory.MUSICIEN, "sort_order": 9, "default_access_level": "STAFF"},
    {"code": "DJ", "name_fr": "DJ", "name_en": "DJ", "category": ProfessionCategory.MUSICIEN, "sort_order": 10, "default_access_level": "STAFF"},

    # TECHNICIENS (13)
    {"code": "INGE_SON_FACADE", "name_fr": "Ingénieur son façade", "name_en": "FOH Sound Engineer", "category": ProfessionCategory.TECHNICIEN, "sort_order": 1, "default_access_level": "STAFF"},
    {"code": "INGE_SON_RETOUR", "name_fr": "Ingénieur son retour", "name_en": "Monitor Engineer", "category": ProfessionCategory.TECHNICIEN, "sort_order": 2, "default_access_level": "STAFF"},
    {"code": "CHEF_LUMIERE", "name_fr": "Chef éclairagiste", "name_en": "Lighting Director", "category": ProfessionCategory.TECHNICIEN, "sort_order": 3, "default_access_level": "STAFF"},
    {"code": "ASSISTANT_LUMIERE", "name_fr": "Assistant lumière", "name_en": "Lighting Assistant", "category": ProfessionCategory.TECHNICIEN, "sort_order": 4, "default_access_level": "STAFF"},
    {"code": "CHEF_PLATEAU", "name_fr": "Chef plateau", "name_en": "Stage Manager", "category": ProfessionCategory.TECHNICIEN, "sort_order": 5, "default_access_level": "STAFF"},
    {"code": "TECHNICIEN_PLATEAU", "name_fr": "Technicien plateau", "name_en": "Stage Technician", "category": ProfessionCategory.TECHNICIEN, "sort_order": 6, "default_access_level": "STAFF"},
    {"code": "ROAD", "name_fr": "Road", "name_en": "Roadie", "category": ProfessionCategory.TECHNICIEN, "sort_order": 7, "default_access_level": "STAFF"},
    {"code": "BACKLINE", "name_fr": "Backline", "name_en": "Backline Tech", "category": ProfessionCategory.TECHNICIEN, "sort_order": 8, "default_access_level": "STAFF"},
    {"code": "REGISSEUR_PLATEAU", "name_fr": "Régisseur plateau", "name_en": "Stage Director", "category": ProfessionCategory.TECHNICIEN, "sort_order": 9, "default_access_level": "STAFF"},
    {"code": "REGISSEUR_SON", "name_fr": "Régisseur son", "name_en": "Sound Director", "category": ProfessionCategory.TECHNICIEN, "sort_order": 10, "default_access_level": "STAFF"},
    {"code": "REGISSEUR_LUMIERE", "name_fr": "Régisseur lumière", "name_en": "Lighting Supervisor", "category": ProfessionCategory.TECHNICIEN, "sort_order": 11, "default_access_level": "STAFF"},
    {"code": "REGISSEUR_GENERAL", "name_fr": "Régisseur général", "name_en": "Production Manager", "category": ProfessionCategory.TECHNICIEN, "sort_order": 12, "default_access_level": "MANAGER"},
    {"code": "TECH_VIDEO", "name_fr": "Technicien vidéo", "name_en": "Video Technician", "category": ProfessionCategory.TECHNICIEN, "sort_order": 13, "default_access_level": "STAFF"},

    # PRODUCTION (4)
    {"code": "TOUR_MANAGER", "name_fr": "Tour manager", "name_en": "Tour Manager", "category": ProfessionCategory.PRODUCTION, "sort_order": 1, "default_access_level": "MANAGER"},
    {"code": "CHARGE_PRODUCTION", "name_fr": "Chargé de production", "name_en": "Production Coordinator", "category": ProfessionCategory.PRODUCTION, "sort_order": 2, "default_access_level": "STAFF"},
    {"code": "CHARGE_COMMUNICATION", "name_fr": "Chargé de communication", "name_en": "PR Coordinator", "category": ProfessionCategory.PRODUCTION, "sort_order": 3, "default_access_level": "STAFF"},
    {"code": "BOOKER", "name_fr": "Booker", "name_en": "Booking Agent", "category": ProfessionCategory.PRODUCTION, "sort_order": 4, "default_access_level": "STAFF"},

    # STYLE (3)
    {"code": "MAQUILLEUR", "name_fr": "Maquilleur/Maquilleuse", "name_en": "Makeup Artist", "category": ProfessionCategory.STYLE, "sort_order": 1, "default_access_level": "STAFF"},
    {"code": "HABILLEUR", "name_fr": "Habilleur/Habilleuse", "name_en": "Wardrobe Assistant", "category": ProfessionCategory.STYLE, "sort_order": 2, "default_access_level": "STAFF"},
    {"code": "CHEF_COSTUME", "name_fr": "Chef costume", "name_en": "Costume Designer", "category": ProfessionCategory.STYLE, "sort_order": 3, "default_access_level": "STAFF"},

    # SECURITE (2)
    {"code": "CHEF_SECURITE", "name_fr": "Chef sécurité", "name_en": "Security Director", "category": ProfessionCategory.SECURITE, "sort_order": 1, "default_access_level": "STAFF"},
    {"code": "AGENT_SECURITE", "name_fr": "Agent sécurité", "name_en": "Security Guard", "category": ProfessionCategory.SECURITE, "sort_order": 2, "default_access_level": "VIEWER"},

    # MANAGEMENT (2)
    {"code": "MANAGER_ARTISTE", "name_fr": "Manager", "name_en": "Artist Manager", "category": ProfessionCategory.MANAGEMENT, "sort_order": 1, "default_access_level": "MANAGER"},
    {"code": "COMMUNITY_MANAGER", "name_fr": "Community manager", "name_en": "Community Manager", "category": ProfessionCategory.MANAGEMENT, "sort_order": 2, "default_access_level": "STAFF"},
]


# ============================================================
# PROFESSION DEFAULT RATES (Taux par défaut par profession)
# Basé sur le marché français 2026
# ============================================================
PROFESSION_DEFAULT_RATES = {
    # MUSICIENS - par concert
    'CHANTEUR': {'show_rate': 350, 'per_diem': 35, 'frequency': 'per_show'},
    'GUITARISTE': {'show_rate': 300, 'per_diem': 35, 'frequency': 'per_show'},
    'BATTEUR': {'show_rate': 300, 'per_diem': 35, 'frequency': 'per_show'},
    'DIRECTEUR_MUSICAL': {'show_rate': 400, 'per_diem': 35, 'frequency': 'per_show'},
    'CLAVIER': {'show_rate': 300, 'per_diem': 35, 'frequency': 'per_show'},
    'BASSISTE': {'show_rate': 300, 'per_diem': 35, 'frequency': 'per_show'},
    'PERCUSSIONS': {'show_rate': 300, 'per_diem': 35, 'frequency': 'per_show'},
    'CORDES': {'show_rate': 300, 'per_diem': 35, 'frequency': 'per_show'},
    'CHORISTE': {'show_rate': 250, 'per_diem': 35, 'frequency': 'per_show'},
    'DJ': {'show_rate': 350, 'per_diem': 35, 'frequency': 'per_show'},

    # TECHNICIENS - journalier
    'INGE_SON_FACADE': {'daily_rate': 350, 'per_diem': 35, 'frequency': 'daily'},
    'INGE_SON_RETOUR': {'daily_rate': 300, 'per_diem': 35, 'frequency': 'daily'},
    'CHEF_LUMIERE': {'daily_rate': 350, 'per_diem': 35, 'frequency': 'daily'},
    'ASSISTANT_LUMIERE': {'daily_rate': 200, 'per_diem': 35, 'frequency': 'daily'},
    'CHEF_PLATEAU': {'daily_rate': 280, 'per_diem': 35, 'frequency': 'daily'},
    'TECHNICIEN_PLATEAU': {'daily_rate': 200, 'per_diem': 35, 'frequency': 'daily'},
    'ROAD': {'daily_rate': 150, 'per_diem': 35, 'frequency': 'daily'},
    'BACKLINE': {'daily_rate': 220, 'per_diem': 35, 'frequency': 'daily'},
    'REGISSEUR_PLATEAU': {'daily_rate': 280, 'per_diem': 35, 'frequency': 'daily'},
    'REGISSEUR_SON': {'daily_rate': 300, 'per_diem': 35, 'frequency': 'daily'},
    'REGISSEUR_LUMIERE': {'daily_rate': 300, 'per_diem': 35, 'frequency': 'daily'},
    'REGISSEUR_GENERAL': {'daily_rate': 350, 'per_diem': 35, 'frequency': 'daily'},
    'TECH_VIDEO': {'daily_rate': 250, 'per_diem': 35, 'frequency': 'daily'},

    # PRODUCTION - hebdomadaire
    'TOUR_MANAGER': {'weekly_rate': 3000, 'per_diem': 0, 'frequency': 'weekly'},
    'CHARGE_PRODUCTION': {'daily_rate': 300, 'per_diem': 35, 'frequency': 'daily'},
    'CHARGE_COMMUNICATION': {'daily_rate': 250, 'per_diem': 35, 'frequency': 'daily'},
    'BOOKER': {'daily_rate': 300, 'per_diem': 35, 'frequency': 'daily'},

    # STYLE - journalier
    'MAQUILLEUR': {'daily_rate': 220, 'per_diem': 35, 'frequency': 'daily'},
    'HABILLEUR': {'daily_rate': 200, 'per_diem': 35, 'frequency': 'daily'},
    'CHEF_COSTUME': {'daily_rate': 280, 'per_diem': 35, 'frequency': 'daily'},

    # SECURITE - journalier
    'CHEF_SECURITE': {'daily_rate': 220, 'per_diem': 35, 'frequency': 'daily'},
    'AGENT_SECURITE': {'daily_rate': 180, 'per_diem': 35, 'frequency': 'daily'},

    # MANAGEMENT - hebdomadaire
    'MANAGER_ARTISTE': {'weekly_rate': 2500, 'per_diem': 0, 'frequency': 'weekly'},
    'COMMUNITY_MANAGER': {'daily_rate': 200, 'per_diem': 35, 'frequency': 'daily'},
}


def seed_professions():
    """Seed professions table with default data."""
    for data in PROFESSIONS_SEED:
        existing = Profession.query.filter_by(code=data['code']).first()
        if not existing:
            profession = Profession(**data)
            db.session.add(profession)
    db.session.commit()
