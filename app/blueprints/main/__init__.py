"""Main blueprint - Dashboard and home."""
from flask import Blueprint

main_bp = Blueprint('main', __name__, template_folder='templates')

from app.blueprints.main import routes  # noqa: F401, E402
