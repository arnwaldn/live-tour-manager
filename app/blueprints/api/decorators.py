"""
JWT authentication decorators for the REST API.
"""
from functools import wraps
from datetime import datetime, timedelta, timezone

import jwt
from flask import request, jsonify, current_app

from app.models.user import User, AccessLevel, ACCESS_HIERARCHY


def create_access_token(user_id, expires_minutes=60):
    """Create a JWT access token."""
    payload = {
        'sub': str(user_id),
        'type': 'access',
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
    }
    secret = current_app.config.get('JWT_SECRET_KEY') or current_app.config['SECRET_KEY']
    return jwt.encode(payload, secret, algorithm='HS256')


def create_refresh_token(user_id, expires_days=30):
    """Create a JWT refresh token (longer-lived)."""
    payload = {
        'sub': str(user_id),
        'type': 'refresh',
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(days=expires_days),
    }
    secret = current_app.config.get('JWT_SECRET_KEY') or current_app.config['SECRET_KEY']
    return jwt.encode(payload, secret, algorithm='HS256')


def decode_token(token):
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        secret = current_app.config.get('JWT_SECRET_KEY') or current_app.config['SECRET_KEY']
        payload = jwt.decode(
            token,
            secret,
            algorithms=['HS256'],
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_api_user():
    """Extract user from Authorization header. Returns (user, error_response)."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None, (jsonify({
            'error': {
                'code': 'missing_token',
                'message': 'Authorization header with Bearer token required.',
            }
        }), 401)

    token = auth_header[7:]  # Strip "Bearer "
    payload = decode_token(token)

    if payload is None:
        return None, (jsonify({
            'error': {
                'code': 'invalid_token',
                'message': 'Token is invalid or expired.',
            }
        }), 401)

    if payload.get('type') != 'access':
        return None, (jsonify({
            'error': {
                'code': 'wrong_token_type',
                'message': 'Access token required (not refresh token).',
            }
        }), 401)

    try:
        user_id = int(payload['sub'])
    except (ValueError, TypeError):
        return None, (jsonify({
            'error': {
                'code': 'invalid_token',
                'message': 'Token contains invalid user ID.',
            }
        }), 401)

    user = User.query.get(user_id)
    if user is None or not user.is_active:
        return None, (jsonify({
            'error': {
                'code': 'user_not_found',
                'message': 'User not found or deactivated.',
            }
        }), 401)

    return user, None


def jwt_required(f):
    """Decorator: require valid JWT access token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user, error = get_current_api_user()
        if error:
            return error
        request.api_user = user
        return f(*args, **kwargs)
    return decorated


def requires_api_access(min_level):
    """Decorator: require minimum access level (RBAC).

    Usage: @requires_api_access(AccessLevel.MANAGER)
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user, error = get_current_api_user()
            if error:
                return error

            # Check access level hierarchy
            user_index = ACCESS_HIERARCHY.index(user.access_level)
            required_index = ACCESS_HIERARCHY.index(min_level)
            if user_index > required_index:
                return jsonify({
                    'error': {
                        'code': 'forbidden',
                        'message': 'Insufficient permissions.',
                    }
                }), 403

            request.api_user = user
            return f(*args, **kwargs)
        return decorated
    return decorator
