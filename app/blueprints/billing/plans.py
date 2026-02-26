"""
Plan limits configuration for GigRoute SaaS billing.
Defines Free and Pro plan constraints.
"""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass(frozen=True)
class PlanLimits:
    """Immutable plan limits definition."""
    max_tours: Optional[int]  # None = unlimited
    max_stops_per_tour: Optional[int]  # None = unlimited
    features: List[str] = field(default_factory=list)


PLAN_LIMITS = {
    'free': PlanLimits(
        max_tours=1,
        max_stops_per_tour=5,
        features=['advancing', 'guestlist'],
    ),
    'pro': PlanLimits(
        max_tours=None,
        max_stops_per_tour=None,
        features=[
            'advancing', 'guestlist', 'invoices',
            'api', 'export_pdf', 'email_venue',
        ],
    ),
}


def get_plan_limits(plan_name: str) -> PlanLimits:
    """Get limits for a given plan name. Defaults to free."""
    return PLAN_LIMITS.get(plan_name, PLAN_LIMITS['free'])
