"""
API Authentication endpoints — JWT login, register, refresh, and user profile.
"""
import re

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
from app.models.user import User, AccessLevel
from app.models.organization import Organization, OrganizationMembership, OrgRole


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


@api_bp.route('/auth/register', methods=['POST'])
@limiter.limit('5 per minute')
def api_register():
    """Register a new user and return JWT tokens.

    Request body:
        {
            "email": "...",
            "password": "...",
            "first_name": "...",
            "last_name": "...",
            "phone": "..."  (optional)
        }

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

    # Validate required fields
    required = ['email', 'password', 'first_name', 'last_name']
    missing = [f for f in required if not data.get(f, '').strip()]
    if missing:
        return jsonify({
            'error': {
                'code': 'validation_error',
                'message': 'Missing required fields.',
                'details': [
                    {'field': f, 'message': f'{f} is required.', 'code': 'required'}
                    for f in missing
                ],
            }
        }), 422

    email = data['email'].strip().lower()
    password = data['password']
    first_name = data['first_name'].strip()
    last_name = data['last_name'].strip()
    phone = data.get('phone', '').strip() or None

    # Validate email format
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return jsonify({
            'error': {
                'code': 'validation_error',
                'message': 'Invalid email format.',
                'details': [{'field': 'email', 'message': 'Invalid email format.', 'code': 'invalid'}],
            }
        }), 422

    # Validate password strength
    if len(password) < 8:
        return jsonify({
            'error': {
                'code': 'validation_error',
                'message': 'Password must be at least 8 characters.',
                'details': [{'field': 'password', 'message': 'Minimum 8 characters.', 'code': 'too_short'}],
            }
        }), 422

    # Check if email already taken
    if User.query.filter_by(email=email).first():
        return jsonify({
            'error': {
                'code': 'email_taken',
                'message': 'An account with this email already exists.',
            }
        }), 409

    # Create user
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        is_active=True,
        email_verified=False,
        access_level=AccessLevel.ADMIN,
    )
    user.set_password(password)

    db.session.add(user)
    db.session.flush()

    # Create default organization (workspace)
    org_name = f"Équipe de {user.full_name}"
    org = Organization(
        name=org_name,
        slug=Organization.generate_slug(org_name),
        email=user.email,
        created_by_id=user.id,
    )
    db.session.add(org)
    db.session.flush()

    # Make user the owner of their organization
    membership = OrganizationMembership(
        user_id=user.id,
        org_id=org.id,
        role=OrgRole.OWNER,
    )
    db.session.add(membership)
    db.session.commit()

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return jsonify({
        'data': {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': 3600,
            'user': UserSchema().dump(user),
        }
    }), 201


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


@api_bp.route('/auth/me', methods=['PUT'])
@jwt_required
def api_update_me():
    """Update current user profile.

    Request body (all fields optional):
        {
            "first_name": "...",
            "last_name": "...",
            "phone": "...",
            "timezone": "...",
            "dietary_restrictions": "...",
            "allergies": "...",
            "emergency_contact_name": "...",
            "emergency_contact_phone": "...",
            "emergency_contact_relation": "...",
            "emergency_contact_email": "..."
        }

    Returns:
        {"data": {...updated user fields...}}
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            'error': {
                'code': 'invalid_json',
                'message': 'Request body must be valid JSON.',
            }
        }), 400

    user = request.api_user

    # Allowed updatable fields (whitelist approach)
    updatable_fields = [
        'first_name', 'last_name', 'phone', 'timezone',
        'dietary_restrictions', 'allergies',
        'emergency_contact_name', 'emergency_contact_phone',
        'emergency_contact_relation', 'emergency_contact_email',
        'preferred_airline', 'seat_preference', 'meal_preference',
        'hotel_preferences',
    ]

    for field in updatable_fields:
        if field in data:
            value = data[field]
            if isinstance(value, str):
                value = value.strip()
            setattr(user, field, value or None)

    # Validate non-empty first/last name
    if not user.first_name or not user.last_name:
        db.session.rollback()
        return jsonify({
            'error': {
                'code': 'validation_error',
                'message': 'first_name and last_name cannot be empty.',
            }
        }), 422

    db.session.commit()

    return jsonify({
        'data': UserSchema().dump(user),
    }), 200
