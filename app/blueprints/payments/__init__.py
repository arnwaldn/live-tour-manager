"""Payments management blueprint - Enterprise-Grade financial module."""
from flask import Blueprint

payments_bp = Blueprint('payments', __name__, template_folder='templates')

from app.blueprints.payments import routes  # noqa: F401, E402
