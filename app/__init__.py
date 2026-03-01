"""
GigRoute Application Factory.
Creates and configures the Flask application instance.
"""
import os
import json
import logging
import secrets
import uuid
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone

import click
from flask import Flask, render_template, request, g

from app.config import config
from app.extensions import init_extensions, db


def _init_sentry(app):
    """Initialize Sentry error tracking for production."""
    dsn = app.config.get('SENTRY_DSN') or os.environ.get('SENTRY_DSN')
    if not dsn:
        app.logger.info('SENTRY_DSN not set — error tracking disabled.')
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[FlaskIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=float(os.environ.get('SENTRY_TRACES_RATE', '0.1')),
            environment=os.environ.get('FLASK_ENV', 'production'),
            send_default_pii=False,
        )
        app.logger.info('Sentry error tracking initialized.')
    except ImportError:
        app.logger.warning('sentry-sdk not installed — error tracking disabled.')


def create_app(config_name=None):
    """
    Application factory for creating Flask app instances.

    Args:
        config_name: Configuration to use (development, testing, production)

    Returns:
        Configured Flask application instance
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)

    # Load configuration
    config_class = config[config_name]
    app.config.from_object(config_class)

    # Initialize Sentry (production only)
    if config_name == 'production':
        _init_sentry(app)

    # Call init_app if available (production validation happens here)
    if hasattr(config_class, 'init_app'):
        config_class.init_app(app)

    # Initialize extensions
    init_extensions(app)

    # Enable response compression (gzip)
    from flask_compress import Compress
    Compress(app)

    # Initialize Stripe API key
    if app.config.get('STRIPE_SECRET_KEY'):
        import stripe
        stripe.api_key = app.config['STRIPE_SECRET_KEY']

    # Load mail config from database (if available)
    with app.app_context():
        try:
            from app.models.system_settings import SystemSettings
            db_config = SystemSettings.get_mail_config()
            if db_config.get('MAIL_SERVER'):
                app.config['MAIL_SERVER'] = db_config['MAIL_SERVER']
            if db_config.get('MAIL_PORT'):
                app.config['MAIL_PORT'] = int(db_config['MAIL_PORT'])
            if db_config.get('MAIL_USE_TLS') is not None:
                app.config['MAIL_USE_TLS'] = db_config['MAIL_USE_TLS'] == 'true'
            if db_config.get('MAIL_USERNAME'):
                app.config['MAIL_USERNAME'] = db_config['MAIL_USERNAME']
            if db_config.get('MAIL_PASSWORD'):
                app.config['MAIL_PASSWORD'] = db_config['MAIL_PASSWORD']
            if db_config.get('MAIL_DEFAULT_SENDER'):
                app.config['MAIL_DEFAULT_SENDER'] = db_config['MAIL_DEFAULT_SENDER']
        except Exception as e:
            app.logger.debug(f'Mail config from DB not available (expected during initial migration): {e}')

    # Register blueprints
    register_blueprints(app)

    # Register mail config auto-reloader (for multi-worker environments)
    register_mail_config_reloader(app)

    # Register error handlers
    register_error_handlers(app)

    # Register CLI commands
    register_cli_commands(app)

    # Register context processors
    register_context_processors(app)

    # Register template filters (French i18n)
    register_template_filters(app)

    # Configure logging
    configure_logging(app)

    # Add security headers
    register_security_headers(app)

    # Email verification warning for sensitive operations
    register_email_verification_guard(app)

    # Create database tables (development only)
    if config_name == 'development':
        with app.app_context():
            db.create_all()

    # Auto-seed professions if table is empty
    with app.app_context():
        try:
            from app.models.profession import Profession, seed_professions
            if Profession.query.count() == 0:
                seed_professions()
                app.logger.info('Auto-seeded professions table with default data')
        except Exception as e:
            app.logger.debug(f'Profession auto-seed not available (expected during initial migration): {e}')

    return app


def register_blueprints(app):
    """Register all application blueprints."""
    from app.blueprints.auth import auth_bp
    from app.blueprints.main import main_bp
    from app.blueprints.bands import bands_bp
    from app.blueprints.tours import tours_bp
    from app.blueprints.venues import venues_bp
    from app.blueprints.guestlist import guestlist_bp
    from app.blueprints.logistics import logistics_bp
    from app.blueprints.reports import reports_bp
    from app.blueprints.settings import settings_bp
    from app.blueprints.documents import documents_bp
    from app.blueprints.notifications import notifications_bp
    from app.blueprints.integrations import integrations_bp
    from app.blueprints.payments import payments_bp
    from app.blueprints.invoices import invoices_bp
    # Crew module - enabled for full crew scheduling functionality
    from app.blueprints.crew import crew_bp
    # REST API v1
    from app.blueprints.api import api_bp
    # Advancing module — event preparation workflow
    from app.blueprints.advancing import advancing_bp
    # Billing module — Stripe SaaS subscription management
    from app.blueprints.billing import billing_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(bands_bp, url_prefix='/bands')
    app.register_blueprint(tours_bp, url_prefix='/tours')
    app.register_blueprint(venues_bp, url_prefix='/venues')
    app.register_blueprint(guestlist_bp, url_prefix='/guestlist')
    app.register_blueprint(logistics_bp, url_prefix='/logistics')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(documents_bp, url_prefix='/documents')
    app.register_blueprint(notifications_bp, url_prefix='/notifications')
    app.register_blueprint(integrations_bp, url_prefix='/integrations')
    app.register_blueprint(payments_bp, url_prefix='/payments')
    app.register_blueprint(invoices_bp, url_prefix='/invoices')
    # Crew module - enabled for full crew scheduling functionality
    app.register_blueprint(crew_bp)
    # Advancing module — event preparation workflow
    app.register_blueprint(advancing_bp, url_prefix='/advancing')
    # Billing module — Stripe SaaS subscription management
    app.register_blueprint(billing_bp, url_prefix='/billing')
    # REST API v1 — JWT auth, no CSRF needed
    app.register_blueprint(api_bp, url_prefix='/api/v1')


def register_mail_config_reloader(app):
    """Register a before_request hook to auto-reload mail config.

    In multi-worker environments (e.g., Gunicorn with multiple workers),
    when one worker updates the mail config, other workers need to detect
    and reload the new configuration. This hook checks for config changes
    at most once every 60 seconds to avoid unnecessary DB queries.
    """
    import time as _time
    _last_mail_check = [0.0]  # mutable container for closure

    @app.before_request
    def check_mail_config():
        """Check if mail config needs reloading from database (throttled)."""
        now = _time.monotonic()
        if now - _last_mail_check[0] < 60:
            return
        _last_mail_check[0] = now

        try:
            from app.models.system_settings import SystemSettings
            from app.extensions import mail

            # Get timestamp from database
            db_timestamp = SystemSettings.get_mail_config_timestamp()

            # Get timestamp from app config (when config was last loaded)
            loaded_timestamp = app.config.get('_MAIL_CONFIG_LOADED_AT', 0)

            # If database timestamp is newer, reload config
            if db_timestamp > loaded_timestamp:
                db_config = SystemSettings.get_mail_config()

                if db_config.get('MAIL_SERVER'):
                    app.config['MAIL_SERVER'] = db_config['MAIL_SERVER']
                if db_config.get('MAIL_PORT'):
                    app.config['MAIL_PORT'] = int(db_config['MAIL_PORT'])
                if db_config.get('MAIL_USE_TLS') is not None:
                    app.config['MAIL_USE_TLS'] = db_config['MAIL_USE_TLS'] == 'true'
                if db_config.get('MAIL_USERNAME'):
                    app.config['MAIL_USERNAME'] = db_config['MAIL_USERNAME']
                if db_config.get('MAIL_PASSWORD'):
                    app.config['MAIL_PASSWORD'] = db_config['MAIL_PASSWORD']
                if db_config.get('MAIL_DEFAULT_SENDER'):
                    app.config['MAIL_DEFAULT_SENDER'] = db_config['MAIL_DEFAULT_SENDER']

                # Update loaded timestamp
                app.config['_MAIL_CONFIG_LOADED_AT'] = db_timestamp

                # Reinitialize Flask-Mailman with new config
                mail.init_app(app)
        except Exception:
            pass  # Silently ignore errors (table may not exist yet)


def _is_api_request():
    """Check if the current request targets the API (returns JSON)."""
    from flask import request
    return request.path.startswith('/api/')


def register_error_handlers(app):
    """Register error handlers for common HTTP errors."""
    from flask import jsonify

    @app.errorhandler(403)
    def forbidden(error):
        if _is_api_request():
            return jsonify({'error': {'code': 'forbidden', 'message': 'Access denied.'}}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        if _is_api_request():
            return jsonify({'error': {'code': 'not_found', 'message': 'Resource not found.'}}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        request_id = g.get('request_id', '-')
        app.logger.error('500 Internal Server Error: %s (request_id=%s)', type(error).__name__, request_id, exc_info=True)
        if _is_api_request():
            return jsonify({'error': {'code': 'internal_error', 'message': 'Internal server error.', 'request_id': request_id}}), 500
        return render_template('errors/500.html', request_id=request_id), 500

    @app.errorhandler(429)
    def ratelimit_error(error):
        if _is_api_request():
            return jsonify({'error': {'code': 'rate_limit_exceeded', 'message': 'Too many requests. Try again later.'}}), 429
        return render_template('errors/429.html'), 429


def register_cli_commands(app):
    """Register custom CLI commands."""

    @app.cli.command('init-db')
    def init_db():
        """Initialize database with default roles."""
        from app.models.user import Role
        from app.extensions import db

        # Define default roles with permissions
        default_roles = [
            {
                'name': 'MANAGER',
                'description': 'Band/Tour Manager - Full access',
                'permissions': [
                    'manage_band', 'manage_tour', 'manage_guestlist',
                    'manage_logistics', 'view_tour', 'request_guestlist',
                    'view_show', 'check_in_guests', 'export_guestlist'
                ]
            },
            {
                'name': 'MUSICIAN',
                'description': 'Band member',
                'permissions': ['view_tour', 'request_guestlist', 'view_show']
            },
            {
                'name': 'TECH',
                'description': 'Technical crew member',
                'permissions': ['view_tour', 'view_show', 'manage_logistics']
            },
            {
                'name': 'PROMOTER',
                'description': 'Local promoter',
                'permissions': ['view_show', 'check_in_guests']
            },
            {
                'name': 'VENUE_CONTACT',
                'description': 'Venue staff',
                'permissions': ['view_show', 'check_in_guests']
            },
            {
                'name': 'GUESTLIST_MANAGER',
                'description': 'Guestlist manager',
                'permissions': [
                    'manage_guestlist', 'view_tour', 'view_show',
                    'check_in_guests', 'export_guestlist'
                ]
            },
            {
                'name': 'CALENDAR_VIEWER',
                'description': 'Calendar-only access - view events without editing',
                'permissions': ['view_tour', 'view_show']
            },
            {
                'name': 'MANAGEMENT',
                'description': 'Artist management team - strategic overview',
                'permissions': ['view_tour', 'view_show', 'manage_band']
            },
            {
                'name': 'AGENT',
                'description': 'Booking agent - tour planning access',
                'permissions': ['view_tour', 'view_show', 'manage_tour']
            },
            {
                'name': 'LABEL',
                'description': 'Record label representative - promo access',
                'permissions': ['view_tour', 'view_show', 'request_guestlist']
            }
        ]

        for role_data in default_roles:
            existing = Role.query.filter_by(name=role_data['name']).first()
            if not existing:
                role = Role(
                    name=role_data['name'],
                    description=role_data['description'],
                    permissions=role_data['permissions']
                )
                db.session.add(role)
                print(f"Created role: {role_data['name']}")
            else:
                print(f"Role already exists: {role_data['name']}")

        db.session.commit()
        print("Database initialized with default roles.")

    @app.cli.command('geocode-venues')
    def geocode_venues():
        """Géocode toutes les salles sans coordonnées GPS."""
        from app.models.venue import Venue
        from app.utils.geocoding import batch_geocode_venues
        from app.extensions import db

        venues = Venue.query.filter(
            (Venue.latitude.is_(None)) | (Venue.longitude.is_(None))
        ).all()

        if not venues:
            print("Toutes les salles ont déjà des coordonnées GPS.")
            return

        print(f"Géocodage de {len(venues)} salle(s) en cours...")

        stats = batch_geocode_venues(
            venues,
            commit_callback=lambda: db.session.commit()
        )

        print(f"Terminé: {stats['success']} succès, {stats['failed']} échecs, {stats['skipped']} ignorées")

    @app.cli.command('send-reminders')
    @click.option('--dry-run', is_flag=True, help='Preview without sending emails')
    def send_reminders(dry_run):
        """Send tour stop reminder emails (J-7 and J-1)."""
        from app.services.reminders import (
            get_stops_needing_j7_reminders,
            get_stops_needing_j1_reminders,
            get_users_for_reminder
        )
        from app.models.reminder import TourStopReminder
        from app.utils.email import send_tour_reminder_email
        from app.extensions import db

        print("=" * 50)
        print("TOUR STOP REMINDERS")
        print("=" * 50)

        if dry_run:
            print("[DRY RUN] Aucun email ne sera envoye")
            print()

        stats = {'j7_sent': 0, 'j1_sent': 0, 'skipped': 0, 'errors': 0}

        # Process J-7 reminders
        j7_stops = get_stops_needing_j7_reminders()
        print(f"\nJ-7 Reminders: {len(j7_stops)} tour stop(s) found")

        for tour_stop in j7_stops:
            users = get_users_for_reminder(tour_stop)
            for user in users:
                if TourStopReminder.already_sent(tour_stop.id, user.id, 'j7'):
                    stats['skipped'] += 1
                    continue

                if dry_run:
                    print(f"  [DRY RUN] Would send J-7 to {user.email} for {tour_stop.event_label}")
                else:
                    try:
                        if send_tour_reminder_email(user, tour_stop, 'j7'):
                            TourStopReminder.mark_sent(tour_stop.id, user.id, 'j7')
                            stats['j7_sent'] += 1
                            print(f"  [OK] J-7 sent to {user.email}")
                        else:
                            stats['errors'] += 1
                            print(f"  [ERROR] Failed to send to {user.email}")
                    except Exception as e:
                        stats['errors'] += 1
                        print(f"  [ERROR] {user.email}: {e}")

        # Process J-1 reminders
        j1_stops = get_stops_needing_j1_reminders()
        print(f"\nJ-1 Reminders: {len(j1_stops)} tour stop(s) found")

        for tour_stop in j1_stops:
            users = get_users_for_reminder(tour_stop)
            for user in users:
                if TourStopReminder.already_sent(tour_stop.id, user.id, 'j1'):
                    stats['skipped'] += 1
                    continue

                if dry_run:
                    print(f"  [DRY RUN] Would send J-1 to {user.email} for {tour_stop.event_label}")
                else:
                    try:
                        if send_tour_reminder_email(user, tour_stop, 'j1'):
                            TourStopReminder.mark_sent(tour_stop.id, user.id, 'j1')
                            stats['j1_sent'] += 1
                            print(f"  [OK] J-1 sent to {user.email}")
                        else:
                            stats['errors'] += 1
                            print(f"  [ERROR] Failed to send to {user.email}")
                    except Exception as e:
                        stats['errors'] += 1
                        print(f"  [ERROR] {user.email}: {e}")

        # Commit all reminder records
        if not dry_run:
            db.session.commit()

        # Summary
        print()
        print("=" * 50)
        print("SUMMARY")
        print("=" * 50)
        print(f"J-7 reminders sent: {stats['j7_sent']}")
        print(f"J-1 reminders sent: {stats['j1_sent']}")
        print(f"Skipped (already sent): {stats['skipped']}")
        print(f"Errors: {stats['errors']}")

    @app.cli.command('seed-professions')
    @click.option('--force', is_flag=True, help='Force reseed even if professions exist')
    def seed_professions_cmd(force):
        """Seed professions table with default data (35 professions, 6 categories)."""
        from app.models.profession import Profession, seed_professions
        from app.extensions import db

        existing_count = Profession.query.count()
        if existing_count > 0 and not force:
            print(f"Professions already seeded ({existing_count} found).")
            print("Use --force to reseed (will not duplicate existing records).")
            return

        print("Seeding professions...")
        seed_professions()
        db.session.commit()

        new_count = Profession.query.count()
        print(f"Done! {new_count} professions available.")
        print("Categories: MUSICIEN, TECHNICIEN, PRODUCTION, STYLE, SECURITE, MANAGEMENT")

    @app.cli.command('clean-demo-data')
    @click.option('--confirm', is_flag=True, help='Confirm deletion without prompt')
    def clean_demo_data(confirm):
        """Clean all demo data for production delivery.

        Deletes: Tours, TourStops, GuestlistEntries, Payments, Documents, PlanningSlots, CrewScheduleSlots.
        Keeps: Users, Venues, Professions, Bands.
        """
        from app.models.tour import Tour
        from app.models.tour_stop import TourStop
        from app.models.guestlist import GuestlistEntry
        from app.models.payments import TeamMemberPayment
        from app.models.document import Document
        from app.models.planning_slot import PlanningSlot
        from app.models.crew_schedule import CrewScheduleSlot
        from app.models.notification import Notification
        from app.extensions import db

        if not confirm:
            print("WARNING: This will DELETE all tours and associated data!")
            print("Run with --confirm to proceed.")
            return

        print("Cleaning demo data...")

        # Delete in order of dependencies
        deleted = {}

        # Notifications
        count = Notification.query.delete()
        deleted['notifications'] = count

        # Guestlist entries
        count = GuestlistEntry.query.delete()
        deleted['guestlist_entries'] = count

        # Payments
        count = TeamMemberPayment.query.delete()
        deleted['payments'] = count

        # Planning slots
        count = PlanningSlot.query.delete()
        deleted['planning_slots'] = count

        # Crew schedule slots
        count = CrewScheduleSlot.query.delete()
        deleted['crew_schedule_slots'] = count

        # Documents
        count = Document.query.delete()
        deleted['documents'] = count

        # Tour stops
        count = TourStop.query.delete()
        deleted['tour_stops'] = count

        # Tours
        count = Tour.query.delete()
        deleted['tours'] = count

        db.session.commit()

        print("Done! Deleted:")
        for table, count in deleted.items():
            print(f"  - {table}: {count}")
        print("\nKept: Users, Venues, Professions, Bands")

    @app.cli.command('setup-users')
    @click.option('--admin-email', prompt='Admin email', help='Admin email', envvar='ADMIN_EMAIL')
    @click.option('--admin-password', prompt='Admin password', hide_input=True, confirmation_prompt=True, help='Admin password', envvar='ADMIN_PASSWORD')
    @click.option('--manager-email', prompt='Manager email', help='Manager email', envvar='MANAGER_EMAIL')
    @click.option('--manager-password', prompt='Manager password', hide_input=True, confirmation_prompt=True, help='Manager password', envvar='MANAGER_PASSWORD')
    def setup_users(admin_email, admin_password, manager_email, manager_password):
        """Create initial admin and manager users.

        Use this command to set up users on a fresh production deployment.
        """
        from app.models.user import User, AccessLevel
        from app.extensions import db

        print("="*60)
        print("GIGROUTE - USER SETUP")
        print("="*60)

        created_count = 0

        # Admin user
        existing_admin = User.query.filter_by(email=admin_email).first()
        if existing_admin:
            print("[UPDATE] Admin exists, ensuring ADMIN access level...")
            existing_admin.access_level = AccessLevel.ADMIN
            existing_admin.is_active = True
            existing_admin.email_verified = True
            db.session.commit()
            print(f"[OK] Admin updated: {admin_email} -> AccessLevel.ADMIN")
        else:
            admin = User(
                email=admin_email,
                first_name='Admin',
                last_name='GigRoute',
                access_level=AccessLevel.ADMIN,
                is_active=True,
                email_verified=True
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            created_count += 1
            print(f"[CREATED] Admin: {admin_email}")

        # Manager user
        existing_manager = User.query.filter_by(email=manager_email).first()
        if existing_manager:
            print("[UPDATE] Manager exists, ensuring MANAGER access level...")
            existing_manager.access_level = AccessLevel.MANAGER
            existing_manager.is_active = True
            existing_manager.email_verified = True
            db.session.commit()
            print(f"[OK] Manager updated: {manager_email} -> AccessLevel.MANAGER")
        else:
            manager = User(
                email=manager_email,
                first_name='Jonathan',
                last_name='GigRoute',
                access_level=AccessLevel.MANAGER,
                is_active=True,
                email_verified=True
            )
            manager.set_password(manager_password)
            db.session.add(manager)
            db.session.commit()
            created_count += 1
            print(f"[CREATED] Manager: {manager_email}")

        print("\n" + "="*60)
        print(f"SETUP COMPLETE - {created_count} user(s) created")
        print("="*60)
        print(f"Admin: {admin_email}")
        print(f"Manager: {manager_email}")
        print("="*60)

    @app.cli.command('cleanup-all')
    @click.option('--confirm', is_flag=True, help='Confirm deletion without prompt')
    def cleanup_all(confirm):
        """Delete ALL data except admin and manager users.

        Deletes: All users (except admin/manager), Tours, TourStops, Guestlists, etc.
        Keeps: Admin user, Manager user, Venues, Professions, Roles.
        """
        from app.models.user import User, AccessLevel
        from app.models.tour import Tour
        from app.models.tour_stop import TourStop, TourStopMember
        from app.models.guestlist import GuestlistEntry
        from app.models.payments import TeamMemberPayment
        from app.models.document import Document
        from app.models.planning_slot import PlanningSlot
        from app.models.crew_schedule import CrewScheduleSlot, CrewAssignment
        from app.models.notification import Notification
        from app.models.reminder import TourStopReminder
        from app.models.lineup import LineupSlot
        from app.models.logistics import LogisticsInfo, LogisticsAssignment
        from app.models.band import BandMembership
        from app.models.profession import UserProfession
        from app.models.mission_invitation import MissionInvitation
        from app.extensions import db

        if not confirm:
            print("WARNING: This will DELETE almost ALL data!")
            print("Only admin@... and manager@... users will be kept.")
            print("Run with --confirm to proceed.")
            return

        print("="*60)
        print("CLEANUP ALL DATA")
        print("="*60)

        deleted = {}

        # 1. Notifications
        count = Notification.query.delete()
        deleted['notifications'] = count

        # 2. Guestlist entries
        count = GuestlistEntry.query.delete()
        deleted['guestlist_entries'] = count

        # 3. Payments
        count = TeamMemberPayment.query.delete()
        deleted['payments'] = count

        # 4. Planning slots
        count = PlanningSlot.query.delete()
        deleted['planning_slots'] = count

        # 5. Crew assignments and slots
        count = CrewAssignment.query.delete()
        deleted['crew_assignments'] = count
        count = CrewScheduleSlot.query.delete()
        deleted['crew_schedule_slots'] = count

        # 6. Reminders
        count = TourStopReminder.query.delete()
        deleted['reminders'] = count

        # 7. Lineup slots
        count = LineupSlot.query.delete()
        deleted['lineup_slots'] = count

        # 8. Logistics
        count = LogisticsAssignment.query.delete()
        deleted['logistics_assignments'] = count
        count = LogisticsInfo.query.delete()
        deleted['logistics_info'] = count

        # 9. Documents
        count = Document.query.delete()
        deleted['documents'] = count

        # 10. Tour stop members
        count = TourStopMember.query.delete()
        deleted['tour_stop_members'] = count

        # 11. Tour stops
        count = TourStop.query.delete()
        deleted['tour_stops'] = count

        # 12. Tours
        count = Tour.query.delete()
        deleted['tours'] = count

        # 13. Mission invitations
        count = MissionInvitation.query.delete()
        deleted['mission_invitations'] = count

        # 14. Band memberships (keep bands but remove user links)
        count = BandMembership.query.delete()
        deleted['band_memberships'] = count

        # 15. User professions (for users to be deleted)
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@gigroute.app')
        manager_email = os.environ.get('MANAGER_EMAIL', 'manager@gigroute.app')

        # Get IDs of users to keep
        keep_users = User.query.filter(
            User.email.in_([admin_email, manager_email])
        ).all()
        keep_ids = [u.id for u in keep_users]

        # Delete UserProfessions for users NOT in keep list
        count = UserProfession.query.filter(
            ~UserProfession.user_id.in_(keep_ids)
        ).delete(synchronize_session=False)
        deleted['user_professions'] = count

        # 16. Delete users except admin and manager
        count = User.query.filter(
            ~User.email.in_([admin_email, manager_email])
        ).delete(synchronize_session=False)
        deleted['users'] = count

        db.session.commit()

        print("\nDeleted:")
        for table, count in deleted.items():
            if count > 0:
                print(f"  - {table}: {count}")

        print("\n" + "="*60)
        print("KEPT:")
        print(f"  - Admin: {admin_email}")
        print(f"  - Manager: {manager_email}")
        print("  - Venues, Professions, Roles, Bands (empty)")
        print("="*60)

    def _perform_full_reset(admin_email=None):
        if admin_email is None:
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@gigroute.app')
        """Core reset logic shared by CLI command and HTTP endpoint.

        Deletes ALL data except the admin user. Returns dict of deleted counts.
        """
        from app.models.user import User, TravelCard, user_roles
        from app.models.tour import Tour
        from app.models.tour_stop import TourStop, TourStopMember
        from app.models.guestlist import GuestlistEntry
        from app.models.payments import TeamMemberPayment, UserPaymentConfig
        from app.models.invoices import InvoicePayment, InvoiceLine, Invoice
        from app.models.document import Document, DocumentShare
        from app.models.planning_slot import PlanningSlot
        from app.models.crew_schedule import CrewScheduleSlot, CrewAssignment, ExternalContact
        from app.models.notification import Notification
        from app.models.reminder import TourStopReminder
        from app.models.lineup import LineupSlot
        from app.models.logistics import LogisticsInfo, LogisticsAssignment, LocalContact, PromotorExpenses
        from app.models.band import Band, BandMembership
        from app.models.profession import UserProfession
        from app.models.mission_invitation import MissionInvitation
        from app.models.venue import Venue, VenueContact
        from app.models.oauth_token import OAuthToken
        from app.extensions import db

        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            raise ValueError(f"Admin user {admin_email} not found!")
        admin_id = admin.id

        deleted = {}

        # Phase 1: Leaf tables (no FK dependencies from other tables)
        count = Notification.query.delete()
        deleted['notifications'] = count

        count = TourStopReminder.query.delete()
        deleted['reminders'] = count

        count = GuestlistEntry.query.delete()
        deleted['guestlist_entries'] = count

        count = InvoicePayment.query.delete()
        deleted['invoice_payments'] = count

        count = InvoiceLine.query.delete()
        deleted['invoice_lines'] = count

        count = Invoice.query.delete()
        deleted['invoices'] = count

        count = TeamMemberPayment.query.delete()
        deleted['payments'] = count

        count = PlanningSlot.query.delete()
        deleted['planning_slots'] = count

        count = CrewAssignment.query.delete()
        deleted['crew_assignments'] = count

        count = CrewScheduleSlot.query.delete()
        deleted['crew_schedule_slots'] = count

        count = ExternalContact.query.delete()
        deleted['external_contacts'] = count

        count = LineupSlot.query.delete()
        deleted['lineup_slots'] = count

        count = LogisticsAssignment.query.delete()
        deleted['logistics_assignments'] = count

        count = PromotorExpenses.query.delete()
        deleted['promotor_expenses'] = count

        count = LocalContact.query.delete()
        deleted['local_contacts'] = count

        count = LogisticsInfo.query.delete()
        deleted['logistics_info'] = count

        count = DocumentShare.query.delete()
        deleted['document_shares'] = count

        count = Document.query.delete()
        deleted['documents'] = count

        count = MissionInvitation.query.delete()
        deleted['mission_invitations'] = count

        # Phase 2: Tour structure
        count = TourStopMember.query.delete()
        deleted['tour_stop_members'] = count

        count = TourStop.query.delete()
        deleted['tour_stops'] = count

        count = Tour.query.delete()
        deleted['tours'] = count

        # Phase 3: Venues
        count = VenueContact.query.delete()
        deleted['venue_contacts'] = count

        count = Venue.query.delete()
        deleted['venues'] = count

        # Phase 4: Bands
        count = BandMembership.query.delete()
        deleted['band_memberships'] = count

        count = Band.query.delete()
        deleted['bands'] = count

        # Phase 5: User-related data (keep admin)
        count = UserPaymentConfig.query.filter(
            UserPaymentConfig.user_id != admin_id
        ).delete(synchronize_session=False)
        deleted['user_payment_configs'] = count

        count = UserProfession.query.filter(
            UserProfession.user_id != admin_id
        ).delete(synchronize_session=False)
        deleted['user_professions'] = count

        count = TravelCard.query.filter(
            TravelCard.user_id != admin_id
        ).delete(synchronize_session=False)
        deleted['travel_cards'] = count

        count = OAuthToken.query.filter(
            OAuthToken.user_id != admin_id
        ).delete(synchronize_session=False)
        deleted['oauth_tokens'] = count

        # Clean user_roles association table for non-admin users
        db.session.execute(
            user_roles.delete().where(user_roles.c.user_id != admin_id)
        )
        deleted['user_roles'] = '(cleaned)'

        # Phase 6: Delete all users except admin
        count = User.query.filter(
            User.id != admin_id
        ).delete(synchronize_session=False)
        deleted['users'] = count

        db.session.commit()
        return deleted, admin

    @app.cli.command('full-reset')
    @click.option('--confirm', is_flag=True, help='Confirm full reset')
    @click.option('--admin-email', prompt='Admin email to keep', help='Admin email to keep', envvar='ADMIN_EMAIL')
    def full_reset(confirm, admin_email):
        """Full application reset. Deletes ALL data except one admin user.

        Deletes: ALL tours, stops, venues, bands, users, payments, invoices, etc.
        Keeps: Only the specified admin user, professions, roles, system settings.
        """
        if not confirm:
            print("WARNING: This will DELETE ALL DATA!")
            print(f"Only admin user ({admin_email}) will be kept.")
            print("Run with --confirm to proceed.")
            return

        print("=" * 60)
        print("FULL APPLICATION RESET")
        print("=" * 60)

        try:
            deleted, admin = _perform_full_reset(admin_email)
        except ValueError as e:
            print(f"ERROR: {e}")
            return

        print("\nDeleted:")
        for table, count in deleted.items():
            if count and count != 0:
                print(f"  - {table}: {count}")

        print("\n" + "=" * 60)
        print("KEPT:")
        print(f"  - Admin: {admin.email} (id={admin.id})")
        print("  - Professions, Roles, System Settings")
        print("=" * 60)


# ─── French i18n: Template Filters ──────────────────────────────────

DAYS_FR = {
    'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi',
    'Thursday': 'Jeudi', 'Friday': 'Vendredi', 'Saturday': 'Samedi',
    'Sunday': 'Dimanche'
}

MONTHS_FR = {
    'January': 'janvier', 'February': 'février', 'March': 'mars',
    'April': 'avril', 'May': 'mai', 'June': 'juin',
    'July': 'juillet', 'August': 'août', 'September': 'septembre',
    'October': 'octobre', 'November': 'novembre', 'December': 'décembre'
}

TRANSLATIONS = {
    'tour_status': {
        'draft': 'Brouillon', 'planning': 'Planification', 'confirmed': 'Confirmée',
        'active': 'Active', 'completed': 'Terminée', 'cancelled': 'Annulée'
    },
    'stop_status': {
        'draft': 'Brouillon', 'pending': 'En négociation', 'confirmed': 'Confirmé',
        'performed': 'Réalisé', 'settled': 'Soldé', 'canceled': 'Annulé',
        'rescheduled': 'Reporté'
    },
    'payment_type': {
        'cachet': 'Cachet', 'per_diem': 'Per diem', 'overtime': 'Heures sup.',
        'bonus': 'Prime', 'reimbursement': 'Remboursement', 'advance': 'Avance',
        'travel': 'Transport', 'meal': 'Repas', 'accommodation': 'Hébergement',
        'equipment': 'Équipement', 'buyout': 'Rachat droits'
    },
    'payment_status': {
        'draft': 'Brouillon', 'pending': 'En attente', 'approved': 'Approuvé',
        'scheduled': 'Programmé', 'processing': 'En traitement', 'paid': 'Payé',
        'rejected': 'Rejeté', 'cancelled': 'Annulé'
    },
    'staff_role': {
        'lead_musician': 'Musicien principal', 'musician': 'Musicien',
        'backing_vocalist': 'Choriste', 'dancer': 'Danseur',
        'choreographer': 'Chorégraphe',
        'foh_engineer': 'Ingé son façade', 'monitor_engineer': 'Ingé retours',
        'audio_tech': 'Tech son', 'system_tech': 'Tech système',
        'lighting_director': 'Dir. lumière', 'lighting_tech': 'Tech lumière',
        'lighting_operator': 'Pupitreur lumière',
        'video_director': 'Dir. vidéo', 'video_tech': 'Tech vidéo', 'vj': 'VJ',
        'stage_manager': 'Régisseur plateau', 'stagehand': 'Machiniste',
        'rigger': 'Rigger', 'scenic_tech': 'Tech décor', 'pyro_tech': 'Tech pyro',
        'guitar_tech': 'Tech guitare', 'bass_tech': 'Tech basse',
        'drum_tech': 'Tech batterie', 'keyboard_tech': 'Tech claviers',
        'percussion_tech': 'Tech percussions',
        'tour_manager': 'Tour manager', 'production_manager': 'Dir. production',
        'production_assistant': 'Asst. production',
        'tour_coordinator': 'Coord. tournée', 'advance_person': 'Avanceur',
        'tour_publicist': 'Attaché presse',
        'business_manager': 'Dir. administratif',
        'security': 'Sécurité', 'driver': 'Chauffeur',
        'bus_driver': 'Chauffeur bus', 'truck_driver': 'Chauffeur camion',
        'chef': 'Chef cuisinier', 'catering_staff': 'Catering',
        'wardrobe': 'Costumier', 'hair_makeup': 'Coiffure/maquillage',
        'hospitality': 'Hospitalité',
        'local_crew': 'Crew local', 'local_driver': 'Chauffeur local',
        'local_security': 'Sécurité locale', 'contractor': 'Prestataire',
        'vendor': 'Fournisseur'
    },
    'logistics_type': {
        'flight': 'Vol', 'train': 'Train', 'bus': 'Bus', 'ferry': 'Ferry',
        'rental_car': 'Voiture location', 'taxi': 'Taxi',
        'ground_transport': 'Transport terrestre', 'hotel': 'Hôtel',
        'apartment': 'Appartement', 'rental': 'Location',
        'equipment': 'Matériel', 'backline': 'Backline',
        'catering': 'Restauration', 'meal': 'Repas'
    },
    'entry_type': {
        'guest': 'Invité', 'artist': 'Artiste', 'industry': 'Industrie',
        'press': 'Presse', 'vip': 'VIP', 'comp': 'Comp',
        'working': 'Professionnel'
    },
    'guestlist_status': {
        'pending': 'En attente', 'approved': 'Approuvé',
        'denied': 'Refusé', 'checked_in': 'Entré'
    },
    'invoice_status': {
        'draft': 'Brouillon', 'validated': 'Validée', 'sent': 'Envoyée',
        'paid': 'Payée', 'partial': 'Partielle', 'overdue': 'En retard',
        'disputed': 'Contestée', 'cancelled': 'Annulée', 'credited': 'Avoir'
    },
    'contract_type': {
        'cddu': 'CDDU', 'cdd': 'CDD', 'cdi': 'CDI',
        'freelance': 'Auto-entrepreneur', 'prestation': 'Prestation',
        'guso': 'GUSO'
    },
    'advancing_status': {
        'not_started': 'Non démarré', 'in_progress': 'En cours',
        'waiting_venue': 'Attente salle', 'completed': 'Terminé',
        'issues': 'Problèmes'
    },
    'advancing_category': {
        'accueil': 'Accueil', 'technique': 'Technique', 'catering': 'Catering',
        'hebergement': 'Hébergement', 'logistique': 'Logistique',
        'securite': 'Sécurité', 'admin': 'Administration'
    },
    'rider_category': {
        'son': 'Son', 'lumiere': 'Lumière', 'scene': 'Scène',
        'backline': 'Backline', 'catering': 'Catering', 'loges': 'Loges'
    }
}


def register_template_filters(app):
    """Register Jinja2 template filters for French i18n."""

    @app.template_filter('format_date_fr')
    def format_date_fr(date, fmt='full'):
        """Format a date in French without relying on system locale.

        Args:
            date: A date or datetime object.
            fmt: 'full' (Lundi 15 mars 2026), 'short' (15 mars 2026),
                 'day_month' (15 mars).
        """
        if not date:
            return ''
        # Handle ISO-format strings from serialized data
        if isinstance(date, str):
            from datetime import date as date_cls, datetime as dt_cls
            try:
                date = dt_cls.fromisoformat(date).date() if 'T' in date else date_cls.fromisoformat(date)
            except (ValueError, TypeError):
                return date
        day_en = date.strftime('%A')
        month_en = date.strftime('%B')
        day_fr = DAYS_FR.get(day_en, day_en)
        month_fr = MONTHS_FR.get(month_en, month_en)
        if fmt == 'full':
            return f"{day_fr} {date.day} {month_fr} {date.year}"
        elif fmt == 'short':
            return f"{date.day} {month_fr} {date.year}"
        elif fmt == 'day_month':
            return f"{date.day} {month_fr}"
        return str(date)

    @app.template_filter('tr')
    def translate_enum(value, enum_type):
        """Translate an enum value to French.

        Usage in templates: {{ entry.entry_type.value|tr('entry_type') }}
        """
        if not value:
            return ''
        translations = TRANSLATIONS.get(enum_type, {})
        return translations.get(str(value), str(value).replace('_', ' ').title())

    @app.template_filter('pluralize_fr')
    def pluralize_fr(count, singular, plural=None):
        """French pluralization: {{ count|pluralize_fr('concert', 'concerts') }}"""
        if plural is None:
            plural = singular + 's'
        count = int(count) if count else 0
        return f"{count} {singular}" if count <= 1 else f"{count} {plural}"


def register_context_processors(app):
    """Register template context processors."""
    from datetime import datetime
    from flask_login import current_user

    # Build a static file version map at startup (file mtime as cache buster)
    _static_versions = {}
    static_folder = app.static_folder
    if static_folder and os.path.isdir(static_folder):
        for root, _dirs, files in os.walk(static_folder):
            for fname in files:
                filepath = os.path.join(root, fname)
                rel = os.path.relpath(filepath, static_folder).replace('\\', '/')
                try:
                    _static_versions[rel] = int(os.path.getmtime(filepath))
                except OSError:
                    pass

    def _versioned_static(filename):
        """Return static URL with cache-busting version query param."""
        from flask import url_for as flask_url_for
        url = flask_url_for('static', filename=filename)
        version = _static_versions.get(filename, '')
        if version:
            url += f'?v={version}'
        return url

    @app.context_processor
    def utility_processor():
        """Provide utility functions to templates."""
        return {
            'now': datetime.now,
            'current_year': datetime.now().year,
            'csp_nonce': g.get('csp_nonce', ''),
            'versioned_static': _versioned_static,
        }

    # Per-user context cache (30s TTL) to avoid DB queries on every page render
    import time as _ctx_time
    _user_ctx_cache = {}  # {user_id: {'data': dict, 'ts': float}}
    _CTX_CACHE_TTL = 30  # seconds

    @app.context_processor
    def user_context_processor():
        """Provide pending registrations, notifications, and billing to templates.

        Cached per-user for 30 seconds to avoid 3-4 DB queries per page render.
        """
        defaults = {
            'pending_registrations_count': 0,
            'unread_notifications_count': 0,
            'recent_notifications': [],
            'current_plan': 'free',
        }
        if not current_user.is_authenticated:
            return defaults

        uid = current_user.id
        now = _ctx_time.monotonic()
        cached = _user_ctx_cache.get(uid)
        if cached and (now - cached['ts']) < _CTX_CACHE_TTL:
            return cached['data']

        data = dict(defaults)
        try:
            # Pending registrations (managers only)
            if current_user.is_manager_or_above():
                from app.models.user import User
                data['pending_registrations_count'] = User.query.filter(
                    User.is_active == False,
                    User.invitation_token.is_(None)
                ).count()

            # Notifications
            from app.models.notification import Notification
            data['unread_notifications_count'] = Notification.get_unread_count(uid)
            data['recent_notifications'] = Notification.get_recent(uid, limit=5)

            # Billing
            data['current_plan'] = current_user.current_plan
        except Exception:
            pass  # Table might not exist or DB connection issue

        _user_ctx_cache[uid] = {'data': data, 'ts': now}

        # Evict stale entries (keep cache bounded)
        if len(_user_ctx_cache) > 100:
            cutoff = now - _CTX_CACHE_TTL * 2
            stale = [k for k, v in _user_ctx_cache.items() if v['ts'] < cutoff]
            for k in stale:
                del _user_ctx_cache[k]

        return data

    @app.context_processor
    def pdf_availability_processor():
        """Provide PDF export availability status to templates."""
        try:
            from app.utils.pdf_generator import PDF_AVAILABLE
            return {'pdf_available': PDF_AVAILABLE}
        except ImportError:
            return {'pdf_available': False}

    # Register Jinja2 filters
    @app.template_filter('timeago')
    def timeago_filter(dt):
        """Convert a datetime to a 'time ago' string."""
        if dt is None:
            return ''
        now = datetime.utcnow()
        diff = now - dt

        seconds = diff.total_seconds()
        if seconds < 60:
            return "À l'instant"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"Il y a {minutes} min"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"Il y a {hours}h"
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f"Il y a {days}j"
        elif seconds < 2592000:
            weeks = int(seconds / 604800)
            return f"Il y a {weeks} sem."
        else:
            return dt.strftime('%d/%m/%Y')

    @app.template_filter('clean_country')
    def clean_country_filter(country):
        """Fix duplicated country names like 'FranceFrance' -> 'France'."""
        if not country:
            return ''
        country = str(country).strip()
        # Check if the country name is duplicated
        if len(country) >= 2 and len(country) % 2 == 0:
            half = len(country) // 2
            if country[:half] == country[half:]:
                return country[:half]
        return country


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production (Render, cloud platforms)."""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'line': record.lineno,
        }
        # Add request_id if available
        try:
            log_entry['request_id'] = g.get('request_id', '-')
        except RuntimeError:
            pass  # Outside request context
        # Add exception info
        if record.exc_info and record.exc_info[0]:
            log_entry['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def configure_logging(app):
    """Configure application logging.

    Production: JSON to stdout (for Render/cloud log aggregation).
    Development: plain text with colors.
    """
    if app.testing:
        return

    # Request ID middleware
    @app.before_request
    def assign_request_id():
        g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4())[:8])
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.after_request
    def log_request(response):
        if request.path.startswith('/static'):
            return response
        app.logger.info(
            '%s %s %s %dms',
            request.method,
            request.path,
            response.status_code,
            int((response.headers.get('X-Response-Time', 0)) or 0),
        )
        return response

    if not app.debug:
        # Production: JSON to stdout
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(JSONFormatter())
        stream_handler.setLevel(logging.INFO)

        # Clear existing handlers to avoid duplicates
        app.logger.handlers.clear()
        app.logger.addHandler(stream_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('GigRoute startup (JSON logging)')
    else:
        # Development: plain text
        app.logger.setLevel(logging.DEBUG)
        app.logger.info('GigRoute startup (development)')


def register_security_headers(app):
    """Register security headers for all responses."""

    @app.after_request
    def add_security_headers(response):
        """Add security headers to every response."""
        # Cache-Control for static assets (versioned_static adds ?v= for busting)
        if request.path.startswith('/static'):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            return response

        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Clickjacking protection
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'

        # XSS protection (legacy but still useful for older browsers)
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions policy (formerly Feature-Policy)
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        # HSTS - Force HTTPS (1 year, include subdomains)
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Prevent cross-domain policy loading
        response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'

        # Content Security Policy (nonce-based for scripts)
        if not app.debug:
            nonce = g.get('csp_nonce', '')
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://unpkg.com https://js.stripe.com; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https: blob:; "
                "connect-src 'self' https://*.tile.openstreetmap.org https://*.openstreetmap.org https://api-adresse.data.gouv.fr https://data.geopf.fr https://api.geoapify.com https://api.stripe.com; "
                "frame-src 'self' https://js.stripe.com https://hooks.stripe.com; "
                "frame-ancestors 'self';"
            )

        return response


def register_email_verification_guard(app):
    """Warn unverified users when accessing sensitive features (RGPD Art. 6)."""
    from flask_login import current_user

    SENSITIVE_PREFIXES = ('/payments', '/invoices', '/reports')

    @app.before_request
    def check_email_verification():
        from flask import request as req
        if (
            current_user.is_authenticated
            and not current_user.email_verified
            and req.path.startswith(SENSITIVE_PREFIXES)
            and req.method == 'GET'
        ):
            from flask import flash as _flash
            _flash(
                'Votre email n\'est pas encore verifie. '
                'Certaines fonctionnalites peuvent etre limitees.',
                'warning'
            )
