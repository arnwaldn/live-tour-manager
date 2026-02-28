"""
SQLAlchemy models for GigRoute.
All models are imported here for easy access.
"""
from app.models.user import (
    User, Role, user_roles,
    AccessLevel, ACCESS_LEVEL_LABELS, ACCESS_LEVEL_DESCRIPTIONS, ACCESS_HIERARCHY
)
from app.models.profession import (
    Profession, UserProfession, ProfessionCategory,
    CATEGORY_LABELS, CATEGORY_ICONS, CATEGORY_COLORS,
    PROFESSIONS_SEED, seed_professions
)
from app.models.label import Label
from app.models.band import Band, BandMembership
from app.models.venue import Venue, VenueContact
from app.models.tour import Tour
from app.models.tour_stop import (
    TourStop,
    TourStopMember,
    MemberAssignmentStatus,
    TourStopStatus,
    EventType,
)
from app.models.lineup import LineupSlot, PerformerType, PERFORMER_TYPE_LABELS
from app.models.ticket_tier import TicketTier
from app.models.guestlist import GuestlistEntry
from app.models.logistics import LogisticsInfo, LocalContact, PromotorExpenses, LogisticsAssignment
from app.models.document import Document, DocumentType, DocumentShare, ShareType
from app.models.notification import Notification, NotificationType, NotificationCategory
from app.models.oauth_token import OAuthToken, OAuthProvider
from app.models.mission_invitation import MissionInvitation, MissionInvitationStatus
from app.models.reminder import TourStopReminder
from app.models.system_settings import SystemSettings

# Crew Schedule module
from app.models.crew_schedule import (
    CrewScheduleSlot,
    CrewAssignment,
    ExternalContact,
    AssignmentStatus,
)

# Planning Slots (Daily Concert Planning Grid)
from app.models.planning_slot import PlanningSlot

# Financial module - Enterprise Grade
from app.models.payments import (
    TeamMemberPayment,
    UserPaymentConfig,
    StaffCategory,
    StaffRole,
    ContractType,
    PaymentFrequency,
    PaymentType,
    PaymentStatus,
    PaymentMethod,
    DEFAULT_RATES,
    CATEGORY_ROLES,
    get_category_for_role,
)
from app.models.invoices import (
    Invoice,
    InvoiceLine,
    InvoicePayment,
    InvoiceStatus,
    InvoiceType,
    VATRate,
    DEFAULT_ISSUER_CONFIG,
    DEFAULT_LEGAL_MENTIONS,
)
# Advancing module — event preparation workflow
from app.models.advancing import (
    AdvancingChecklistItem,
    AdvancingTemplate,
    RiderRequirement,
    AdvancingContact,
    AdvancingStatus,
    ChecklistCategory,
    RiderCategory,
    DEFAULT_CHECKLIST_ITEMS,
)
# Subscription (SaaS billing)
from app.models.subscription import (
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
# Security Breach (RGPD Art. 33-34)
from app.models.security_breach import SecurityBreach, BreachSeverity, BreachStatus
# AuditLog is in app/utils/audit.py (enriched existing model)

__all__ = [
    # User & Auth
    'User',
    'Role',
    'user_roles',
    # Access Levels (v2.0)
    'AccessLevel',
    'ACCESS_LEVEL_LABELS',
    'ACCESS_LEVEL_DESCRIPTIONS',
    'ACCESS_HIERARCHY',
    # Professions (v2.0)
    'Profession',
    'UserProfession',
    'ProfessionCategory',
    'CATEGORY_LABELS',
    'CATEGORY_ICONS',
    'CATEGORY_COLORS',
    'PROFESSIONS_SEED',
    'seed_professions',
    # Labels (v2.0)
    'Label',
    # Band
    'Band',
    'BandMembership',
    # Venue
    'Venue',
    'VenueContact',
    # Tour
    'Tour',
    'TourStop',
    'TourStopMember',
    'MemberAssignmentStatus',
    'TourStopStatus',
    'EventType',
    # Lineup
    'LineupSlot',
    'PerformerType',
    'PERFORMER_TYPE_LABELS',
    # Ticket Tiers
    'TicketTier',
    # Guestlist
    'GuestlistEntry',
    # Logistics
    'LogisticsInfo',
    'LocalContact',
    'PromotorExpenses',
    'LogisticsAssignment',
    # Documents
    'Document',
    'DocumentType',
    'DocumentShare',
    'ShareType',
    # Notifications
    'Notification',
    'NotificationType',
    'NotificationCategory',
    # OAuth
    'OAuthToken',
    'OAuthProvider',
    # Mission Invitations
    'MissionInvitation',
    'MissionInvitationStatus',
    # Reminders
    'TourStopReminder',
    # System Settings
    'SystemSettings',
    # === CREW SCHEDULE MODULE ===
    'CrewScheduleSlot',
    'CrewAssignment',
    'ExternalContact',
    'AssignmentStatus',
    # === PLANNING SLOTS (Daily Concert Grid) ===
    'PlanningSlot',
    # === FINANCIAL MODULE ===
    # Payments
    'TeamMemberPayment',
    'UserPaymentConfig',
    'StaffCategory',
    'StaffRole',
    'ContractType',
    'PaymentFrequency',
    'PaymentType',
    'PaymentStatus',
    'PaymentMethod',
    'DEFAULT_RATES',
    'CATEGORY_ROLES',
    'get_category_for_role',
    # Invoices
    'Invoice',
    'InvoiceLine',
    'InvoicePayment',
    'InvoiceStatus',
    'InvoiceType',
    'VATRate',
    'DEFAULT_ISSUER_CONFIG',
    'DEFAULT_LEGAL_MENTIONS',
    # Note: AuditLog is in app/utils/audit.py
    # === ADVANCING MODULE ===
    'AdvancingChecklistItem',
    'AdvancingTemplate',
    'RiderRequirement',
    'AdvancingContact',
    'AdvancingStatus',
    'ChecklistCategory',
    'RiderCategory',
    'DEFAULT_CHECKLIST_ITEMS',
    # === SUBSCRIPTION (SaaS Billing) ===
    'Subscription',
    'SubscriptionPlan',
    'SubscriptionStatus',
    # === SECURITY BREACH (RGPD Art. 33-34) ===
    'SecurityBreach',
    'BreachSeverity',
    'BreachStatus',
]
