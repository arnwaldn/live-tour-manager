"""Logistics management blueprint."""
from flask import Blueprint

logistics_bp = Blueprint('logistics', __name__, template_folder='templates')

from app.blueprints.logistics import routes  # noqa: F401, E402
