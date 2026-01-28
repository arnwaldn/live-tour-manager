"""Guestlist management blueprint."""
from flask import Blueprint

guestlist_bp = Blueprint('guestlist', __name__, template_folder='templates')

from app.blueprints.guestlist import routes  # noqa: F401, E402
