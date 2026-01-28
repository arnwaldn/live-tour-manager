"""
Documents blueprint for managing tour documents.
Handles uploads, downloads, and management of passports, visas, contracts, etc.
"""
from flask import Blueprint

documents_bp = Blueprint('documents', __name__, template_folder='templates')

from app.blueprints.documents import routes  # noqa: E402, F401
