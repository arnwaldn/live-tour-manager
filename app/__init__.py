"""
Tour Manager Application Factory.
Creates and configures the Flask application instance.
"""
import os
import logging
from logging.handlers import RotatingFileHandler

import click
from flask import Flask, render_template

from app.config import config
from app.extensions import init_extensions, db


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

    # Call init_app if available (production validation happens here)
    if hasattr(config_class, 'init_app'):
        config_class.init_app(app)

    # Initialize extensions
    init_extensions(app)

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

    # Configure logging
    configure_logging(app)

    # Add security headers
    register_security_headers(app)

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
    # Crew module - enabled for full crew scheduling functionality
    from app.blueprints.crew import crew_bp

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
    # Crew module - enabled for full crew scheduling functionality
    app.register_blueprint(crew_bp)


def register_mail_config_reloader(app):
    """Register a before_request hook to auto-reload mail config.

    In multi-worker environments (e.g., Gunicorn with multiple workers),
    when one worker updates the mail config, other workers need to detect
    and reload the new configuration. This hook checks for config changes
    on each request by comparing timestamps.
    """
    @app.before_request
    def check_mail_config():
        """Check if mail config needs reloading from database."""
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

                # Reinitialize Flask-Mail with new config
                mail.init_app(app)
        except Exception:
            pass  # Silently ignore errors (table may not exist yet)


def register_error_handlers(app):
    """Register error handlers for common HTTP errors."""

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    @app.errorhandler(429)
    def ratelimit_error(error):
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
    @click.option('--admin-email', default='arnaud.porcel@gmail.com', help='Admin email')
    @click.option('--admin-password', default='TourAdmin2026!Secure', help='Admin password')
    @click.option('--manager-email', default='jonathan.studiopalenquegroup@gmail.com', help='Manager email')
    @click.option('--manager-password', default='TourManager2026!Secure', help='Manager password')
    def setup_users(admin_email, admin_password, manager_email, manager_password):
        """Create initial admin and manager users.

        Use this command to set up users on a fresh production deployment.
        """
        from app.models.user import User, AccessLevel
        from app.extensions import db

        print("="*60)
        print("TOUR MANAGER - USER SETUP")
        print("="*60)

        created_count = 0

        # Admin user
        existing_admin = User.query.filter_by(email=admin_email).first()
        if existing_admin:
            print(f"[UPDATE] Admin exists, ensuring ADMIN access level...")
            existing_admin.access_level = AccessLevel.ADMIN
            existing_admin.is_active = True
            existing_admin.email_verified = True
            db.session.commit()
            print(f"[OK] Admin updated: {admin_email} -> AccessLevel.ADMIN")
        else:
            admin = User(
                email=admin_email,
                first_name='Arnaud',
                last_name='Porcel',
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
            print(f"[UPDATE] Manager exists, ensuring MANAGER access level...")
            existing_manager.access_level = AccessLevel.MANAGER
            existing_manager.is_active = True
            existing_manager.email_verified = True
            db.session.commit()
            print(f"[OK] Manager updated: {manager_email} -> AccessLevel.MANAGER")
        else:
            manager = User(
                email=manager_email,
                first_name='Jonathan',
                last_name='Studio Palenque',
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
        admin_email = 'arnaud.porcel@gmail.com'
        manager_email = 'jonathan.studiopalenquegroup@gmail.com'

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


def register_context_processors(app):
    """Register template context processors."""
    from datetime import datetime
    from flask_login import current_user

    @app.context_processor
    def utility_processor():
        """Provide utility functions to templates."""
        return {
            'now': datetime.now,
            'current_year': datetime.now().year
        }

    @app.context_processor
    def pending_registrations_processor():
        """Provide pending registrations count to templates (managers only)."""
        pending_count = 0
        if current_user.is_authenticated and current_user.is_manager_or_above():
            try:
                from app.models.user import User
                # Count users who are inactive and have no invitation token
                # (invitation_token means they were invited, not self-registered)
                pending_count = User.query.filter(
                    User.is_active == False,
                    User.invitation_token.is_(None)
                ).count()
            except Exception:
                # Table might not exist or DB connection issue
                pending_count = 0
        return {'pending_registrations_count': pending_count}

    @app.context_processor
    def notifications_processor():
        """Provide notifications data to templates."""
        unread_count = 0
        recent_notifications = []
        if current_user.is_authenticated:
            try:
                from app.models.notification import Notification
                unread_count = Notification.get_unread_count(current_user.id)
                recent_notifications = Notification.get_recent(current_user.id, limit=5)
            except Exception:
                # Table might not exist or DB connection issue
                unread_count = 0
                recent_notifications = []
        return {
            'unread_notifications_count': unread_count,
            'recent_notifications': recent_notifications
        }

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


def configure_logging(app):
    """Configure application logging."""
    if not app.debug and not app.testing:
        # Ensure logs directory exists
        if not os.path.exists('logs'):
            os.mkdir('logs')

        # File handler for errors
        file_handler = RotatingFileHandler(
            'logs/tour_manager.log',
            maxBytes=10240000,  # 10 MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Tour Manager startup')


def register_security_headers(app):
    """Register security headers for all responses."""

    @app.after_request
    def add_security_headers(response):
        """Add security headers to every response."""
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

        # Content Security Policy (basic - can be customized further)
        if not app.debug:
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://unpkg.com; "
                "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
                "img-src 'self' data: https: blob:; "
                "connect-src 'self' https://*.tile.openstreetmap.org https://*.openstreetmap.org https://api-adresse.data.gouv.fr https://data.geopf.fr https://api.geoapify.com;"
                "frame-ancestors 'self';"
            )

        return response
