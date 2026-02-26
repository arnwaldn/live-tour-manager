"""
Subscription model for GigRoute SaaS billing.
Tracks user subscription plan (Free/Pro) and Stripe integration.
"""
import enum
from datetime import datetime, date

from app.extensions import db


class SubscriptionPlan(str, enum.Enum):
    """Available subscription plans."""
    FREE = 'free'
    PRO = 'pro'


class SubscriptionStatus(str, enum.Enum):
    """Stripe-aligned subscription statuses."""
    ACTIVE = 'active'
    PAST_DUE = 'past_due'
    CANCELED = 'canceled'
    TRIALING = 'trialing'
    INCOMPLETE = 'incomplete'


class Subscription(db.Model):
    """User subscription for SaaS billing."""

    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        unique=True,
        nullable=False,
        index=True,
    )

    plan = db.Column(
        db.Enum(SubscriptionPlan, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SubscriptionPlan.FREE,
    )
    status = db.Column(
        db.Enum(SubscriptionStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )

    # Stripe IDs
    stripe_subscription_id = db.Column(
        db.String(255), unique=True, nullable=True, index=True,
    )
    stripe_customer_id = db.Column(db.String(255), nullable=True)

    # Billing period
    current_period_start = db.Column(db.DateTime, nullable=True)
    current_period_end = db.Column(db.DateTime, nullable=True)
    cancel_at_period_end = db.Column(db.Boolean, nullable=False, default=False)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('subscription', uselist=False))

    def __repr__(self):
        return f'<Subscription user={self.user_id} plan={self.plan.value}>'

    @property
    def is_active(self):
        """Check if subscription is currently active (not canceled or expired)."""
        if self.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
            return True
        # Past due is still considered active (grace period)
        if self.status == SubscriptionStatus.PAST_DUE:
            return True
        return False

    @property
    def is_pro(self):
        """Check if user has an active Pro subscription."""
        return self.plan == SubscriptionPlan.PRO and self.is_active

    @property
    def days_remaining(self):
        """Days remaining in current billing period. None for free plan."""
        if self.plan == SubscriptionPlan.FREE or not self.current_period_end:
            return None
        delta = self.current_period_end.date() - date.today()
        return max(0, delta.days)

    @property
    def plan_label(self):
        """French label for plan."""
        labels = {
            SubscriptionPlan.FREE: 'Gratuit',
            SubscriptionPlan.PRO: 'Pro',
        }
        return labels.get(self.plan, str(self.plan.value))

    @property
    def status_label(self):
        """French label for status."""
        labels = {
            SubscriptionStatus.ACTIVE: 'Actif',
            SubscriptionStatus.PAST_DUE: 'Paiement en retard',
            SubscriptionStatus.CANCELED: 'Annule',
            SubscriptionStatus.TRIALING: 'Essai',
            SubscriptionStatus.INCOMPLETE: 'Incomplet',
        }
        return labels.get(self.status, str(self.status.value))

    def to_dict(self):
        """Serialize subscription to dict."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan': self.plan.value,
            'status': self.status.value,
            'is_active': self.is_active,
            'is_pro': self.is_pro,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'cancel_at_period_end': self.cancel_at_period_end,
            'days_remaining': self.days_remaining,
        }
