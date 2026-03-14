"""
API v1 Blueprint — REST API with JWT authentication.
Provides JSON endpoints for mobile app and external integrations.
"""
import os
from flask import Blueprint
from flask_cors import CORS

api_bp = Blueprint('api', __name__)

# Enable CORS for API endpoints (mobile app, external integrations)
# Configure allowed origins via APP_CORS_ORIGINS env var (comma-separated)
_cors_origins = os.environ.get('APP_CORS_ORIGINS', 'http://localhost:5000,http://localhost:3000')
_allowed_origins = [o.strip() for o in _cors_origins.split(',') if o.strip()]

CORS(api_bp, resources={r"/*": {
    "origins": _allowed_origins,
    "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type"],
    "expose_headers": ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    "max_age": 600,
}})


from flask import request as _req, g
from markupsafe import escape as _html_escape
import uuid


def _sanitize_value(v):
    """Recursively sanitize string values in JSON data."""
    if isinstance(v, str):
        return str(_html_escape(v))
    if isinstance(v, dict):
        return {k: _sanitize_value(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_sanitize_value(item) for item in v]
    return v


@api_bp.before_request
def _sanitize_json_input():
    """Sanitize all string values in JSON request bodies to prevent XSS."""
    g.request_id = uuid.uuid4().hex[:8]
    if _req.is_json and _req.data:
        try:
            raw = _req.get_json(silent=True)
            if raw and isinstance(raw, dict):
                sanitized = _sanitize_value(raw)
                # Replace the parsed JSON cache
                _req._cached_json = (sanitized, sanitized)
        except Exception:
            pass  # Let the route handler deal with invalid JSON

from app.blueprints.api import auth, routes  # noqa: E402, F401
