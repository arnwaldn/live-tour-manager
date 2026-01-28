"""Venues management blueprint."""
from flask import Blueprint

venues_bp = Blueprint('venues', __name__, template_folder='templates')

from app.blueprints.venues import routes  # noqa: F401, E402
