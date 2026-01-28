"""Bands management blueprint."""
from flask import Blueprint

bands_bp = Blueprint('bands', __name__, template_folder='templates')

from app.blueprints.bands import routes  # noqa: F401, E402
