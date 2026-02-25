"""
API Authentication endpoints — JWT login, refresh, and user info.
"""
from flask import request, jsonify, current_app

from app.blueprints.api import api_bp
from app.blueprints.api.decorators import (
    create_access_token,
    create_refresh_token,
    decode_token,
    jwt_required,
)
from app.blueprints.api.schemas import UserSchema
from app.extensions import db, limiter
from app.models.user import User


@api_bp.route('/auth/login', methods=['POST'])
@limiter.limit('10 per minute')
def api_login():
    """Authenticate user and return JWT tokens.

    Request body:
        {"email": "...", "password": "..."}

    Returns:
        {"data": {"access_token": "...", "refresh_token": "...", "user": {...}}}
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            'error': {
                'code': 'invalid_json',
                'message': 'Request body must be valid JSON.',
            }
        }), 400

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({
            'error': {
                'code': 'validation_error',
                'message': 'Email and password are required.',
                'details': [
                    {'field': f, 'message': f'{f} is required.', 'code': 'required'}
                    for f in ['email', 'password'] if not data.get(f)
                ],
            }
        }), 422

    user = User.query.filter_by(email=email).first()

    # Check account lockout (is_locked is a @property)
    if user and hasattr(user, 'is_locked') and user.is_locked:
        return jsonify({
            'error': {
                'code': 'account_locked',
                'message': 'Account temporarily locked due to too many failed attempts. Try again later.',
            }
        }), 429

    if user is None or not user.check_password(password):
        # Increment failed attempts if user exists
        if user and hasattr(user, 'record_failed_login'):
            user.record_failed_login()
            db.session.commit()
        return jsonify({
            'error': {
                'code': 'invalid_credentials',
                'message': 'Invalid email or password.',
            }
        }), 401

    if not user.is_active:
        return jsonify({
            'error': {
                'code': 'account_inactive',
                'message': 'Account is deactivated. Contact an administrator.',
            }
        }), 403

    # Reset failed attempts on successful login
    if hasattr(user, 'reset_failed_logins'):
        user.reset_failed_logins()
        db.session.commit()

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return jsonify({
        'data': {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': 3600,  # 60 minutes in seconds
            'user': UserSchema().dump(user),
        }
    }), 200


@api_bp.route('/auth/refresh', methods=['POST'])
@limiter.limit('20 per minute')
def api_refresh():
    """Refresh an expired access token using a refresh token.

    Request body:
        {"refresh_token": "..."}

    Returns:
        {"data": {"access_token": "...", "expires_in": 3600}}
    """
    data = request.get_json(silent=True)
    if not data or not data.get('refresh_token'):
        return jsonify({
            'error': {
                'code': 'validation_error',
                'message': 'refresh_token is required.',
            }
        }), 422

    payload = decode_token(data['refresh_token'])
    if payload is None:
        return jsonify({
            'error': {
                'code': 'invalid_token',
                'message': 'Refresh token is invalid or expired.',
            }
        }), 401

    if payload.get('type') != 'refresh':
        return jsonify({
            'error': {
                'code': 'wrong_token_type',
                'message': 'Refresh token required.',
            }
        }), 401

    user = User.query.get(int(payload['sub']))
    if user is None or not user.is_active:
        return jsonify({
            'error': {
                'code': 'user_not_found',
                'message': 'User not found or deactivated.',
            }
        }), 401

    new_access_token = create_access_token(user.id)

    return jsonify({
        'data': {
            'access_token': new_access_token,
            'token_type': 'Bearer',
            'expires_in': 3600,
        }
    }), 200


@api_bp.route('/auth/me', methods=['GET'])
@jwt_required
def api_me():
    """Get current authenticated user profile.

    Returns:
        {"data": {...user fields...}}
    """
    return jsonify({
        'data': UserSchema().dump(request.api_user),
    }), 200
