"""
Audit logging utility for tracking user actions.
Enhanced for Enterprise Grade financial compliance (SOX/PCI).
Retention: 6-10 years for financial records.
"""
import enum
from datetime import datetime
from flask import request, has_request_context
from flask_login import current_user

from app.extensions import db


class AuditAction(enum.Enum):
    """Types d'actions auditees"""
    # CRUD operations
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    # Workflow actions
    SUBMIT = "SUBMIT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    CANCEL = "CANCEL"
    # Payment actions
    PAY = "PAY"
    REFUND = "REFUND"
    SCHEDULE = "SCHEDULE"
    # Invoice actions
    VALIDATE = "VALIDATE"
    SEND = "SEND"
    CREDIT = "CREDIT"
    # Export actions
    EXPORT_CSV = "EXPORT_CSV"
    EXPORT_PDF = "EXPORT_PDF"
    EXPORT_SEPA = "EXPORT_SEPA"
    # Access actions
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    # Legacy actions (for compatibility)
    GUESTLIST_REQUEST = "GUESTLIST_REQUEST"
    GUESTLIST_APPROVE = "GUESTLIST_APPROVE"
    GUESTLIST_DENY = "GUESTLIST_DENY"
    GUESTLIST_CHECKIN = "GUESTLIST_CHECKIN"


class AuditSeverity(enum.Enum):
    """Niveau de severite pour filtrage"""
    INFO = "info"           # Actions de lecture
    LOW = "low"             # Modifications mineures
    MEDIUM = "medium"       # Modifications significatives
    HIGH = "high"           # Approbations, paiements
    CRITICAL = "critical"   # Suppressions, annulations


class AuditLog(db.Model):
    """
    Audit log for tracking user actions.
    Enhanced for Enterprise Grade financial compliance.
    """

    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    action = db.Column(db.String(50), nullable=False, index=True)
    entity_type = db.Column(db.String(50), index=True)  # GuestlistEntry, Tour, Payment, Invoice
    entity_id = db.Column(db.Integer)
    entity_reference = db.Column(db.String(50))  # Human-readable ref (PAY-2026-00001)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Enhanced fields for financial compliance
    user_email = db.Column(db.String(120))   # Copie pour historique
    user_name = db.Column(db.String(100))    # Nom complet au moment de l'action
    severity = db.Column(db.String(20))      # info, low, medium, high, critical
    module = db.Column(db.String(50))        # payments, invoices, guestlist, etc.
    old_values = db.Column(db.JSON)          # Valeurs avant modification
    new_values = db.Column(db.JSON)          # Valeurs apres modification
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)

    # Relationships
    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))

    def __repr__(self):
        return f'<AuditLog {self.action} {self.entity_type} by user {self.user_id}>'

    @staticmethod
    def _get_severity(action):
        """Determine severity based on action type"""
        high_actions = ['APPROVE', 'REJECT', 'PAY', 'EXPORT_SEPA', 'LOGIN_FAILED']
        critical_actions = ['DELETE', 'CANCEL', 'REFUND', 'CREDIT']
        medium_actions = ['VALIDATE', 'SEND', 'SCHEDULE', 'SUBMIT']
        low_actions = ['CREATE', 'UPDATE']

        if action in critical_actions:
            return 'critical'
        elif action in high_actions:
            return 'high'
        elif action in medium_actions:
            return 'medium'
        elif action in low_actions:
            return 'low'
        return 'info'


def log_action(action, entity_type=None, entity_id=None, details=None, user=None):
    """
    Log an action to the audit trail.

    Args:
        action: Action type (CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc.)
        entity_type: Type of entity affected (Tour, GuestlistEntry, etc.)
        entity_id: ID of the entity affected
        details: Additional details as dict
        user: User performing action (defaults to current_user)
    """
    try:
        if user is None and current_user and current_user.is_authenticated:
            user = current_user

        audit_entry = AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=request.remote_addr if request else None,
            user_agent=request.user_agent.string[:500] if request and request.user_agent else None
        )
        db.session.add(audit_entry)
        db.session.commit()
        return audit_entry
    except Exception as e:
        # Don't let audit logging break the application
        db.session.rollback()
        print(f"Audit log error: {e}")
        return None


def log_login(user, success=True):
    """Log a login attempt."""
    action = 'LOGIN_SUCCESS' if success else 'LOGIN_FAILED'
    return log_action(
        action=action,
        entity_type='User',
        entity_id=user.id if user else None,
        details={'success': success},
        user=user if success else None
    )


def log_logout(user):
    """Log a logout."""
    return log_action(
        action='LOGOUT',
        entity_type='User',
        entity_id=user.id,
        user=user
    )


def log_create(entity_type, entity_id, details=None):
    """Log entity creation."""
    return log_action(
        action='CREATE',
        entity_type=entity_type,
        entity_id=entity_id,
        details=details
    )


def log_update(entity_type, entity_id, changes=None):
    """Log entity update."""
    return log_action(
        action='UPDATE',
        entity_type=entity_type,
        entity_id=entity_id,
        details={'changes': changes} if changes else None
    )


def log_delete(entity_type, entity_id, details=None):
    """Log entity deletion."""
    return log_action(
        action='DELETE',
        entity_type=entity_type,
        entity_id=entity_id,
        details=details
    )


def log_guestlist_action(entry, action, notes=None):
    """Log guestlist-specific actions."""
    return log_action(
        action=f'GUESTLIST_{action.upper()}',
        entity_type='GuestlistEntry',
        entity_id=entry.id,
        details={
            'guest_name': entry.guest_name,
            'tour_stop_id': entry.tour_stop_id,
            'notes': notes
        }
    )
