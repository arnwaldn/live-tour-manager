"""
API v1 Blueprint — REST API with JWT authentication.
Provides JSON endpoints for mobile app and external integrations.
"""
from flask import Blueprint
from flask_cors import CORS

api_bp = Blueprint('api', __name__)

# Enable CORS for API endpoints (mobile app, external integrations)
CORS(api_bp, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type"],
    "expose_headers": ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    "max_age": 600,
}})

from app.blueprints.api import auth, routes  # noqa: E402, F401
