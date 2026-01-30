"""Crew schedule management blueprint."""
from flask import Blueprint

crew_bp = Blueprint('crew', __name__, template_folder='templates')

from app.blueprints.crew import routes  # noqa: F401, E402
