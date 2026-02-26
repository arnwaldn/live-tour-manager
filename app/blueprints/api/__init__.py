"""
API v1 Blueprint — REST API with JWT authentication.
Provides JSON endpoints for mobile app and external integrations.
"""
from flask import Blueprint

api_bp = Blueprint('api', __name__)

from app.blueprints.api import auth, routes  # noqa: E402, F401
