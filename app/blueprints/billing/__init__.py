"""Billing blueprint - Stripe SaaS subscription management."""
from flask import Blueprint

billing_bp = Blueprint('billing', __name__, template_folder='templates')

from app.blueprints.billing import routes  # noqa: F401, E402
