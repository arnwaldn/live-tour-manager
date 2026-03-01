"""
Organization and OrganizationMembership models for multi-tenancy.
Each organization is an isolated workspace with its own bands, venues, tours, and billing.
"""
import enum
import re
import unicodedata
from datetime import datetime

from app.extensions import db


class OrgRole(str, enum.Enum):
    """Role within an organization."""
    OWNER = 'owner'       # Created the org, full control, billing
    ADMIN = 'admin'       # Can manage users, settings
    MEMBER = 'member'     # Standard access (AccessLevel determines permissions)


# Display labels for OrgRole
ORG_ROLE_LABELS = {
    OrgRole.OWNER: 'Proprietaire',
    OrgRole.ADMIN: 'Administrateur',
    OrgRole.MEMBER: 'Membre',
}


class Organization(db.Model):
    """Organization (tenant) model — the root isolation unit for multi-tenancy."""

    __tablename__ = 'organizations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)

    # Branding
    logo_path = db.Column(db.String(255))
    website = db.Column(db.String(255))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)

    # Business info (for invoicing)
    siret = db.Column(db.String(14))
    vat_number = db.Column(db.String(20))

    # Creator (the user who registered this org)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    memberships = db.relationship(
        'OrganizationMembership',
        back_populates='organization',
        cascade='all, delete-orphan',
    )
    bands = db.relationship('Band', back_populates='organization')
    venues = db.relationship('Venue', back_populates='organization')

    def __repr__(self):
        return f'<Organization {self.name}>'

    @property
    def members(self):
        """Get all users in this organization."""
        return [m.user for m in self.memberships]

    @property
    def owner(self):
        """Get the org owner (first OWNER membership)."""
        for m in self.memberships:
            if m.role == OrgRole.OWNER:
                return m.user
        return None

    @property
    def member_count(self):
        """Number of members in the organization."""
        return len(self.memberships)

    def has_member(self, user):
        """Check if user is a member of this organization."""
        return any(m.user_id == user.id for m in self.memberships)

    def get_membership(self, user):
        """Get the membership record for a user."""
        for m in self.memberships:
            if m.user_id == user.id:
                return m
        return None

    def is_owner(self, user):
        """Check if user is the owner."""
        m = self.get_membership(user)
        return m is not None and m.role == OrgRole.OWNER

    def is_admin_or_owner(self, user):
        """Check if user is admin or owner."""
        m = self.get_membership(user)
        return m is not None and m.role in (OrgRole.OWNER, OrgRole.ADMIN)

    @staticmethod
    def generate_slug(name):
        """Generate a URL-safe slug from a name.

        Handles unicode (accents), deduplication, and length limits.
        """
        # Normalize unicode and transliterate accents
        normalized = unicodedata.normalize('NFKD', name)
        ascii_name = normalized.encode('ascii', 'ignore').decode('ascii')
        # Lowercase and replace non-alphanumeric with hyphens
        slug = re.sub(r'[^a-z0-9]+', '-', ascii_name.lower()).strip('-')
        # Limit length
        slug = slug[:80]
        # Ensure uniqueness
        base_slug = slug
        counter = 1
        while Organization.query.filter_by(slug=slug).first() is not None:
            slug = f'{base_slug}-{counter}'
            counter += 1
        return slug


class OrganizationMembership(db.Model):
    """Membership linking a user to an organization with a role."""

    __tablename__ = 'organization_memberships'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    role = db.Column(
        db.Enum(OrgRole, values_callable=lambda x: [e.value for e in x]),
        default=OrgRole.MEMBER,
        nullable=False,
    )
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'org_id', name='uq_user_org'),
    )

    # Relationships
    user = db.relationship('User', back_populates='org_memberships')
    organization = db.relationship('Organization', back_populates='memberships')

    def __repr__(self):
        return f'<OrgMembership user={self.user_id} org={self.org_id} role={self.role.value}>'

    @property
    def role_label(self):
        """Get localized role label."""
        return ORG_ROLE_LABELS.get(self.role, str(self.role.value))
