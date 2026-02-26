"""Advancing blueprint - Event preparation workflow for live shows."""
from flask import Blueprint

advancing_bp = Blueprint('advancing', __name__, template_folder='templates')

from app.blueprints.advancing import routes  # noqa: F401, E402
