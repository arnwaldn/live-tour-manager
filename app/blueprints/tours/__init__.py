"""Tours management blueprint."""
from flask import Blueprint

tours_bp = Blueprint('tours', __name__, template_folder='templates')

from app.blueprints.tours import routes  # noqa: F401, E402
