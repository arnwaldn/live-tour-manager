"""Invoice management blueprint - Factur-X compliant financial module."""
from flask import Blueprint

invoices_bp = Blueprint('invoices', __name__, template_folder='templates')

from app.blueprints.invoices import routes  # noqa: F401, E402
