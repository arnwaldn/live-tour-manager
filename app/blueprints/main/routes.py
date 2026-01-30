"""
Main blueprint routes - Dashboard and home.
"""
from datetime import date, timedelta
from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from app.blueprints.main import main_bp
from app.blueprints.main.forms import StandaloneEventForm
from app.extensions import db


@main_bp.route('/health')
def health_check():
    """Health check endpoint for Docker/load balancer."""
    try:
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'

    status = 'healthy' if db_status == 'healthy' else 'unhealthy'

    return jsonify({
        'status': status,
        'database': db_status,
        'service': 'tour-manager',
        'version': '2026-01-30-v2'  # Deployment version marker
    }), 200 if status == 'healthy' else 503


@main_bp.route('/health/db-raw')
def db_raw_check():
    """Raw DB check - no model imports. For debugging migration issues."""
    try:
        # Check if venue_rental_cost column exists in tour_stops
        result = db.session.execute(db.text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'tour_stops'
            AND column_name = 'venue_rental_cost'
        """))
        col_exists = result.fetchone() is not None

        # Get migration status from alembic
        result2 = db.session.execute(db.text(
            "SELECT version_num FROM alembic_version"
        ))
        version_row = result2.fetchone()
        version = version_row[0] if version_row else None

        # Count tables
        result3 = db.session.execute(db.text("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
        """))
        table_count = result3.fetchone()[0]

        return jsonify({
            'db_connected': True,
            'venue_rental_cost_exists': col_exists,
            'alembic_version': version,
            'expected_version': '6ea92203edbe',
            'migration_ok': version == '6ea92203edbe',
            'table_count': table_count,
            'diagnosis': 'OK' if col_exists and version == '6ea92203edbe' else 'MIGRATION_MISSING'
        })
    except Exception as e:
        return jsonify({
            'db_connected': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500


@main_bp.route('/health/diagnose')
def health_diagnose():
    """Diagnostic endpoint to check data integrity (no auth required)."""
    from app.models.tour import Tour
    from app.models.user import User

    diagnostics = {
        'version': '2026-01-29-v6',
        'tours': {},
        'users': {}
    }

    # Check tour ID 4
    try:
        tour = Tour.query.get(4)
        if tour:
            diagnostics['tours']['id_4'] = {
                'exists': True,
                'name': tour.name,
                'band_id': tour.band_id,
                'band_exists': tour.band is not None,
                'band_name': tour.band_name  # Uses safe property
            }
        else:
            diagnostics['tours']['id_4'] = {'exists': False}
    except Exception as e:
        diagnostics['tours']['id_4'] = {'error': str(e)}

    # Check user ID 3
    try:
        user = User.query.get(3)
        if user:
            # Test professions access (common error source)
            try:
                professions_count = len(user.professions)
                primary_prof = user.primary_profession
                primary_prof_name = primary_prof.name_fr if primary_prof else None
            except Exception as prof_err:
                professions_count = f'ERROR: {prof_err}'
                primary_prof_name = f'ERROR: {prof_err}'

            # Test travel_cards access
            try:
                travel_cards_count = len(user.travel_cards) if user.travel_cards else 0
            except Exception as tc_err:
                travel_cards_count = f'ERROR: {tc_err}'

            # Test roles access
            try:
                roles_count = len(user.roles) if user.roles else 0
            except Exception as r_err:
                roles_count = f'ERROR: {r_err}'

            # Test user_professions relationship
            try:
                user_profs = user.user_professions.all()
                user_profs_count = len(user_profs)
            except Exception as up_err:
                user_profs_count = f'ERROR: {up_err}'

            diagnostics['users']['id_3'] = {
                'exists': True,
                'email': user.email[:3] + '***',  # Partial for privacy
                'is_active': user.is_active,
                'professions_count': professions_count,
                'primary_profession': primary_prof_name,
                'access_level': user.access_level.name if user.access_level else None,
                'travel_cards_count': travel_cards_count,
                'roles_count': roles_count,
                'user_professions_raw': user_profs_count
            }
        else:
            diagnostics['users']['id_3'] = {'exists': False}
    except Exception as e:
        diagnostics['users']['id_3'] = {'error': str(e)}

    # Test template-style access (what template line 214 does)
    try:
        user = User.query.get(3)
        if user:
            # This is exactly what the template does at line 214
            prof_ids = [p.id for p in user.professions]
            diagnostics['users']['id_3']['template_prof_ids'] = prof_ids
    except Exception as tmpl_err:
        diagnostics['users']['id_3']['template_error'] = str(tmpl_err)

    return jsonify(diagnostics)


@main_bp.route('/health/test-user-edit/<int:user_id>')
def test_user_edit(user_id):
    """Test endpoint that simulates user edit form setup."""
    from app.models.user import User
    from app.blueprints.settings.forms import UserEditForm, get_access_level_choices, get_profession_choices, get_professions_by_category

    result = {'version': '2026-01-29-v10', 'steps': {}}

    # Step 1: Get user
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': f'User {user_id} not found'}), 404
        result['steps']['1_get_user'] = 'OK'
    except Exception as e:
        result['steps']['1_get_user'] = f'ERROR: {e}'
        return jsonify(result)

    # Step 2: Create form
    try:
        form = UserEditForm(original_email=user.email, obj=user)
        result['steps']['2_create_form'] = 'OK'
    except Exception as e:
        result['steps']['2_create_form'] = f'ERROR: {e}'
        return jsonify(result)

    # Step 3: Get access level choices
    try:
        form.access_level.choices = get_access_level_choices()
        result['steps']['3_access_level_choices'] = 'OK'
    except Exception as e:
        result['steps']['3_access_level_choices'] = f'ERROR: {e}'

    # Step 4: Get profession choices
    try:
        form.profession.choices = [('', '-- Sélectionner --')] + get_profession_choices()
        result['steps']['4_profession_choices'] = 'OK'
    except Exception as e:
        result['steps']['4_profession_choices'] = f'ERROR: {e}'

    # Step 5: Get professions by category
    try:
        professions_by_category = get_professions_by_category()
        result['steps']['5_professions_by_category'] = f'OK ({len(professions_by_category)} categories)'
    except Exception as e:
        result['steps']['5_professions_by_category'] = f'ERROR: {e}'

    # Step 6: Access user.professions
    try:
        profs = user.professions
        result['steps']['6_user_professions'] = f'OK ({len(profs)} professions)'
    except Exception as e:
        result['steps']['6_user_professions'] = f'ERROR: {e}'

    # Step 7: Access user.primary_profession
    try:
        primary = user.primary_profession
        result['steps']['7_primary_profession'] = f'OK ({"exists" if primary else "None"})'
    except Exception as e:
        result['steps']['7_primary_profession'] = f'ERROR: {e}'

    return jsonify(result)


@main_bp.route('/health/fix-professions-schema')
def fix_professions_schema():
    """Emergency endpoint to add missing columns to professions table.

    This fixes the issue where migration r0s2t4v6x8z0 was not applied.
    """
    from sqlalchemy import inspect, text

    result = {
        'version': '2026-01-29-v11',
        'action': 'fix_professions_schema',
        'columns_checked': [],
        'columns_added': [],
        'errors': []
    }

    # Columns that should exist (from migration r0s2t4v6x8z0)
    required_columns = {
        'show_rate': 'NUMERIC(10, 2)',
        'daily_rate': 'NUMERIC(10, 2)',
        'weekly_rate': 'NUMERIC(10, 2)',
        'per_diem': 'NUMERIC(10, 2)',
        'default_frequency': 'VARCHAR(20)'
    }

    try:
        # Check which columns exist
        inspector = inspect(db.engine)
        existing_columns = {col['name'] for col in inspector.get_columns('professions')}
        result['existing_columns'] = list(existing_columns)

        # Add missing columns
        for col_name, col_type in required_columns.items():
            result['columns_checked'].append(col_name)

            if col_name not in existing_columns:
                try:
                    # Add the column
                    db.session.execute(text(
                        f'ALTER TABLE professions ADD COLUMN {col_name} {col_type}'
                    ))
                    result['columns_added'].append(col_name)
                except Exception as add_err:
                    result['errors'].append(f'{col_name}: {str(add_err)}')

        # Commit all changes
        if result['columns_added']:
            db.session.commit()
            result['status'] = 'columns_added'
        else:
            result['status'] = 'all_columns_exist'

    except Exception as e:
        db.session.rollback()
        result['status'] = 'error'
        result['errors'].append(str(e))

    return jsonify(result)


@main_bp.route('/health/bands-debug')
def bands_debug():
    """Debug endpoint to check band counting logic."""
    from flask_login import current_user
    from app.models.band import Band, BandMembership
    from app.models.user import User

    result = {
        'version': '2026-01-30-v4',
        'action': 'bands_debug'
    }

    # Show all bands and their manager_ids first
    all_bands = Band.query.all()
    result['all_bands'] = [
        {'id': b.id, 'name': b.name, 'manager_id': b.manager_id}
        for b in all_bands
    ]

    # Get user ID from query param (default 3)
    user_id = request.args.get('user_id', 3, type=int)

    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': f'User {user_id} not found'}), 404

        # Get bands via the property (BandMembership)
        bands_via_membership = user.bands  # This is a property

        # Get managed bands (relationship)
        managed_bands = list(user.managed_bands)  # Force evaluation

        # Check BandMembership directly
        memberships = BandMembership.query.filter_by(user_id=user_id).all()

        # Check Band.manager_id directly
        bands_as_manager = Band.query.filter_by(manager_id=user_id).all()

        result['user'] = {
            'id': user.id,
            'email': user.email[:3] + '***',
            'full_name': user.full_name,
            'access_level': user.access_level.value if user.access_level else None,
            'is_admin': user.is_admin()
        }

        result['bands_property'] = {
            'count': len(bands_via_membership),
            'bands': [{'id': b.id, 'name': b.name} for b in bands_via_membership]
        }

        result['managed_bands_relationship'] = {
            'count': len(managed_bands),
            'bands': [{'id': b.id, 'name': b.name} for b in managed_bands]
        }

        result['memberships_direct'] = {
            'count': len(memberships),
            'memberships': [{'band_id': m.band_id, 'role_in_band': m.role_in_band} for m in memberships]
        }

        result['bands_manager_id_direct'] = {
            'count': len(bands_as_manager),
            'bands': [{'id': b.id, 'name': b.name, 'manager_id': b.manager_id} for b in bands_as_manager]
        }

        # Simulate dashboard logic
        user_bands_dict = {b.id: b for b in bands_via_membership + managed_bands}
        user_bands = list(user_bands_dict.values())

        result['dashboard_deduplication'] = {
            'total_combined': len(bands_via_membership + managed_bands),
            'after_dedup': len(user_bands),
            'bands': [{'id': b.id, 'name': b.name} for b in user_bands]
        }

    except Exception as e:
        result['error'] = str(e)
        import traceback
        result['traceback'] = traceback.format_exc()

    return jsonify(result)


@main_bp.route('/health/admin-bands-check')
def admin_bands_check():
    """NO AUTH endpoint to verify admin logic."""
    from app.models.user import User

    result = {'version': '2026-01-30-v7'}

    # Check user ID 1 (Arnaud)
    user = User.query.get(1)
    if user:
        is_admin = user.is_admin()
        result['user_1'] = {
            'id': 1,
            'name': user.full_name,
            'access_level': user.access_level.value if user.access_level else None,
            'is_admin': is_admin
        }

        # Simulate dashboard logic for admin
        if is_admin:
            all_bands = Band.query.order_by(Band.name).all()
            result['admin_branch_result'] = {
                'count': len(all_bands),
                'bands': [{'id': b.id, 'name': b.name} for b in all_bands]
            }

    return jsonify(result)


@main_bp.route('/health/dashboard-debug')
@login_required
def dashboard_debug():
    """Debug endpoint to check dashboard band count for CURRENT user."""
    result = {
        'version': '2026-01-30-v5',
        'action': 'dashboard_debug'
    }

    try:
        result['current_user'] = {
            'id': current_user.id,
            'email': current_user.email[:3] + '***',
            'full_name': current_user.full_name,
            'access_level': current_user.access_level.value if current_user.access_level else None,
            'is_admin': current_user.is_admin()
        }

        # Same logic as dashboard route
        if current_user.is_admin():
            user_bands = Band.query.order_by(Band.name).all()
            result['branch'] = 'admin'
        else:
            managed_bands = Band.query.filter_by(manager_id=current_user.id).all()
            member_band_ids = [m.band_id for m in BandMembership.query.filter_by(user_id=current_user.id).all()]
            member_bands = Band.query.filter(Band.id.in_(member_band_ids)).all() if member_band_ids else []
            user_bands_dict = {b.id: b for b in member_bands + managed_bands}
            user_bands = list(user_bands_dict.values())
            result['branch'] = 'non-admin'

        result['user_bands'] = {
            'count': len(user_bands),
            'bands': [{'id': b.id, 'name': b.name} for b in user_bands]
        }

    except Exception as e:
        result['error'] = str(e)
        import traceback
        result['traceback'] = traceback.format_exc()

    return jsonify(result)


@main_bp.route('/health/migration-status')
def migration_status():
    """Check Alembic migration status in production."""
    from sqlalchemy import text

    result = {
        'version': '2026-01-29-v11',
        'action': 'migration_status'
    }

    try:
        # Get current migration head from alembic_version table
        version_result = db.session.execute(
            text('SELECT version_num FROM alembic_version')
        ).fetchone()

        if version_result:
            result['current_head'] = version_result[0]
        else:
            result['current_head'] = None

        # Check if professions table exists and its columns
        from sqlalchemy import inspect
        inspector = inspect(db.engine)

        if 'professions' in inspector.get_table_names():
            columns = inspector.get_columns('professions')
            result['professions_columns'] = [col['name'] for col in columns]
            result['professions_table'] = 'exists'
        else:
            result['professions_table'] = 'missing'
            result['professions_columns'] = []

        # Expected head (latest migration)
        result['expected_head'] = 'r0s2t4v6x8z0'  # add_rate_columns_to_professions
        result['migration_up_to_date'] = result.get('current_head') == result['expected_head']

    except Exception as e:
        result['error'] = str(e)

    return jsonify(result)


from app.models.tour import Tour, TourStatus
from app.models.tour_stop import TourStop, TourStopStatus, EventType, tour_stop_members
from app.models.guestlist import GuestlistEntry, GuestlistStatus
from app.models.band import Band, BandMembership
from app.models.venue import Venue


@main_bp.route('/')
@login_required
def dashboard():
    """Main dashboard - adapted to user's role."""

    # DEBUG v9: If ?debug=1, return JSON or HTML debug page
    if request.args.get('debug'):
        is_admin = current_user.is_admin()
        if is_admin:
            user_bands = Band.query.order_by(Band.name).all()
        else:
            managed_bands = Band.query.filter_by(manager_id=current_user.id).all()
            member_band_ids = [m.band_id for m in BandMembership.query.filter_by(user_id=current_user.id).all()]
            member_bands = Band.query.filter(Band.id.in_(member_band_ids)).all() if member_band_ids else []
            user_bands_dict = {b.id: b for b in member_bands + managed_bands}
            user_bands = list(user_bands_dict.values())

        debug_data = {
            'version': '2026-01-30-v9',
            'current_user': {
                'id': current_user.id,
                'email': current_user.email[:5] + '***',
                'full_name': current_user.full_name,
                'access_level': current_user.access_level.value if current_user.access_level else None,
                'is_admin': is_admin
            },
            'branch': 'admin' if is_admin else 'non-admin',
            'user_bands': {
                'count': len(user_bands),
                'bands': [{'id': b.id, 'name': b.name} for b in user_bands]
            }
        }

        # If debug=html, return HTML page that's easy to screenshot
        if request.args.get('debug') == 'html':
            import json
            html = f"""<!DOCTYPE html>
<html><head><title>Debug Dashboard v9</title></head>
<body style="background:#1a1a1a;color:#fff;font-family:monospace;padding:20px;">
<h1 style="color:#C9A962;">Dashboard Debug v9</h1>
<pre style="background:#2a2a2a;padding:15px;border-radius:5px;">
{json.dumps(debug_data, indent=2)}
</pre>
</body></html>"""
            return html

        return jsonify(debug_data)

    # Admin sees ALL bands (consistent with bands/routes.py behavior)
    is_admin = current_user.is_admin()
    if is_admin:
        user_bands = Band.query.order_by(Band.name).all()
        user_band_ids = [b.id for b in user_bands]
    else:
        # Get user's bands (as member or manager) - using direct queries for reliability
        # 1. Bands where user is manager (via Band.manager_id)
        managed_bands = Band.query.filter_by(manager_id=current_user.id).all()

        # 2. Bands where user is member (via BandMembership)
        member_band_ids = [m.band_id for m in BandMembership.query.filter_by(user_id=current_user.id).all()]
        member_bands = Band.query.filter(Band.id.in_(member_band_ids)).all() if member_band_ids else []

        # 3. Combine and deduplicate by ID
        user_bands_dict = {b.id: b for b in member_bands + managed_bands}
        user_bands = list(user_bands_dict.values())
        user_band_ids = list(user_bands_dict.keys())

    # Active tours for user's bands
    active_tours = Tour.query.filter(
        Tour.band_id.in_(user_band_ids),
        Tour.status.in_([TourStatus.ACTIVE, TourStatus.CONFIRMED])
    ).order_by(Tour.start_date).all() if user_band_ids else []

    # Date ranges
    today = date.today()
    two_weeks = today + timedelta(days=14)

    # Upcoming shows (next 14 days) - displayed in section
    upcoming_stops = TourStop.query.join(Tour).filter(
        Tour.band_id.in_(user_band_ids),
        TourStop.date >= today,
        TourStop.date <= two_weeks,
        TourStop.status != TourStopStatus.CANCELED
    ).order_by(TourStop.date).limit(5).all() if user_band_ids else []

    # Count of concerts BEYOND 14 days (for UI message)
    beyond_two_weeks_count = TourStop.query.join(Tour).filter(
        Tour.band_id.in_(user_band_ids),
        TourStop.date > two_weeks,
        TourStop.status != TourStopStatus.CANCELED
    ).count() if user_band_ids else 0

    # Today's shows
    today_stops = TourStop.query.join(Tour).filter(
        Tour.band_id.in_(user_band_ids),
        TourStop.date == today,
        TourStop.status != TourStopStatus.CANCELED
    ).all() if user_band_ids else []

    # Pending guestlist requests (for managers)
    pending_guestlist = []
    if current_user.is_staff_or_above() and user_band_ids:
        pending_guestlist = GuestlistEntry.query.join(TourStop).join(Tour).filter(
            Tour.band_id.in_(user_band_ids),
            GuestlistEntry.status == GuestlistStatus.PENDING
        ).order_by(GuestlistEntry.created_at.desc()).limit(10).all()

    # Stats - upcoming_shows now uses same 14-day window as the section for consistency
    stats = {
        'total_tours': len(active_tours),
        'upcoming_shows': len(upcoming_stops) + beyond_two_weeks_count,  # Total future concerts
        'upcoming_shows_14days': len(upcoming_stops),  # Just next 14 days
        'beyond_two_weeks': beyond_two_weeks_count,  # Concerts beyond 14 days
        'pending_guestlist': len(pending_guestlist),
        'total_bands': len(user_bands)
    }

    return render_template(
        'main/dashboard.html',
        active_tours=active_tours,
        upcoming_stops=upcoming_stops,
        today_stops=today_stops,
        pending_guestlist=pending_guestlist,
        stats=stats
    )


@main_bp.route('/calendar')
@login_required
def global_calendar():
    """Global calendar showing events based on user role.

    - MANAGER: voit TOUS les événements de TOUS les groupes
    - Autres: voient UNIQUEMENT les événements où ils sont assignés
    """
    is_manager = current_user.is_manager_or_above()

    if is_manager:
        # MANAGER voit toutes les tournées
        tours = Tour.query.order_by(Tour.start_date.desc()).all()
    else:
        # Autres rôles: tournées où l'utilisateur est:
        # 1. Explicitement assigné (tour_stop_members) OU
        # 2. Membre du groupe propriétaire de la tournée (BandMembership)
        tours = Tour.query.join(
            Band, Tour.band_id == Band.id
        ).outerjoin(
            TourStop, Tour.id == TourStop.tour_id
        ).outerjoin(
            tour_stop_members, TourStop.id == tour_stop_members.c.tour_stop_id
        ).outerjoin(
            BandMembership, Band.id == BandMembership.band_id
        ).filter(
            db.or_(
                tour_stop_members.c.user_id == current_user.id,
                BandMembership.user_id == current_user.id
            )
        ).distinct().order_by(Tour.start_date.desc()).all()

    return render_template(
        'main/global_calendar.html',
        tours=tours,
        is_manager=is_manager
    )


@main_bp.route('/calendar/events')
@login_required
def global_calendar_events():
    """API endpoint for global calendar events (tour stops + standalone events).

    Filtrage par rôle:
    - MANAGER: voit TOUS les événements de TOUS les groupes (admin global)
    - Autres rôles: voient UNIQUEMENT les événements où ils sont assignés
    """
    from datetime import datetime
    from sqlalchemy import or_

    # Get date range from request
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    tour_id = request.args.get('tour_id', type=int)

    # Build query based on user role
    if current_user.is_manager_or_above():
        # MANAGER = voit TOUT (admin global)
        # Pas de filtre par groupe - afficher tous les événements
        query = TourStop.query.outerjoin(Tour, TourStop.tour_id == Tour.id)
    else:
        # Autres rôles: événements où l'utilisateur est:
        # 1. Explicitement assigné (tour_stop_members) OU
        # 2. Membre du groupe propriétaire (via Tour.band_id ou TourStop.band_id pour standalone)
        query = TourStop.query.outerjoin(
            Tour, TourStop.tour_id == Tour.id
        ).outerjoin(
            tour_stop_members, TourStop.id == tour_stop_members.c.tour_stop_id
        ).outerjoin(
            BandMembership,
            db.or_(
                # Pour les tour stops: band via tour
                db.and_(Tour.band_id.isnot(None), BandMembership.band_id == Tour.band_id),
                # Pour les événements standalone: band directement sur TourStop
                db.and_(TourStop.band_id.isnot(None), BandMembership.band_id == TourStop.band_id)
            )
        ).filter(
            db.or_(
                tour_stop_members.c.user_id == current_user.id,
                BandMembership.user_id == current_user.id
            )
        ).distinct()

    # Filter by tour if specified (only shows tour stops, not standalone)
    if tour_id:
        query = query.filter(TourStop.tour_id == tour_id)

    # Filter by date range if provided
    if start_str:
        try:
            start_date = datetime.fromisoformat(start_str.replace('Z', '+00:00')).date()
            query = query.filter(TourStop.date >= start_date)
        except ValueError:
            pass

    if end_str:
        try:
            end_date = datetime.fromisoformat(end_str.replace('Z', '+00:00')).date()
            query = query.filter(TourStop.date <= end_date)
        except ValueError:
            pass

    stops = query.all()

    # Get view type to determine event generation strategy
    view_type = request.args.get('view', 'month')  # month, week, list

    # Schedule types with their display properties (attr, label, color)
    schedule_types = [
        ('load_in_time', 'Load-In', '#6c757d'),
        ('crew_call_time', 'Équipe', '#17a2b8'),
        ('artist_call_time', 'Artistes', '#ffc107'),
        ('catering_time', 'Catering', '#fd7e14'),
        ('soundcheck_time', 'Soundcheck', '#6f42c1'),
        ('press_time', 'Presse', '#20c997'),
        ('meet_greet_time', 'Meet & Greet', '#e83e8c'),
        ('doors_time', 'Portes', '#28a745'),
        ('set_time', 'Set', '#007bff'),
        ('curfew_time', 'Couvre-feu', '#dc3545'),
    ]

    events = []
    for stop in stops:
        status_value = stop.status.value if stop.status else 'pending'

        # Get band and title based on whether it's standalone or tour stop
        if stop.is_standalone:
            band = stop.band
            venue_name = stop.venue.name if stop.venue else stop.event_label
            base_title = f"{band.name} - {venue_name}" if stop.venue else f"{band.name} - {stop.event_label}"
            event_url = url_for('main.edit_standalone_event', event_id=stop.id)
            tour_name = None
        else:
            band = stop.tour.band
            venue_name = stop.venue.name if stop.venue else stop.event_label
            base_title = f"{band.name} @ {venue_name}"
            event_url = f"/tours/{stop.tour.id}#stop-{stop.id}"
            tour_name = stop.tour.name

        # Common extendedProps for all events
        common_props = {
            'tour_name': tour_name,
            'band_name': band.name,
            'venue_name': venue_name,
            'city': stop.venue.city if stop.venue else '',
            'country': stop.venue.country if stop.venue else '',
            'status': status_value,
            'stop_id': stop.id,
            'tour_id': stop.tour_id,
            'is_standalone': stop.is_standalone,
            'event_type': stop.event_type.value if stop.event_type else 'show',
            'event_label': stop.event_label,
            # Schedule times for popup
            'loadInTime': stop.load_in_time.strftime('%H:%M') if stop.load_in_time else None,
            'crewCallTime': stop.crew_call_time.strftime('%H:%M') if stop.crew_call_time else None,
            'artistCallTime': stop.artist_call_time.strftime('%H:%M') if stop.artist_call_time else None,
            'cateringTime': stop.catering_time.strftime('%H:%M') if stop.catering_time else None,
            'soundcheckTime': stop.soundcheck_time.strftime('%H:%M') if stop.soundcheck_time else None,
            'pressTime': stop.press_time.strftime('%H:%M') if stop.press_time else None,
            'meetGreetTime': stop.meet_greet_time.strftime('%H:%M') if stop.meet_greet_time else None,
            'doorsTime': stop.doors_time.strftime('%H:%M') if stop.doors_time else None,
            'setTime': stop.set_time.strftime('%H:%M') if stop.set_time else None,
            'curfewTime': stop.curfew_time.strftime('%H:%M') if stop.curfew_time else None,
            # Reschedule tracking for dual date display
            'isRescheduled': stop.is_rescheduled,
            'originalDate': stop.original_date.strftime('%d/%m/%Y') if stop.original_date else None,
            'rescheduleReason': stop.reschedule_reason,
            'rescheduleCount': stop.reschedule_count
        }

        if view_type == 'week':
            # Week view: Create separate event for each schedule time
            for attr, label, color in schedule_types:
                time_value = getattr(stop, attr)
                if time_value:
                    events.append({
                        'id': f"{stop.id}-{attr}",
                        'title': f"{label}: {base_title}",
                        'start': f"{stop.date.isoformat()}T{time_value.strftime('%H:%M:%S')}",
                        'allDay': False,
                        'url': event_url,
                        'backgroundColor': color,
                        'borderColor': color,
                        'textColor': '#ffffff' if color not in ['#ffc107', '#fd7e14'] else '#212529',
                        'extendedProps': {
                            **common_props,
                            'schedule_type': attr,
                            'schedule_label': label
                        }
                    })
        else:
            # Month/List view: Single event per TourStop
            if stop.set_time:
                event_start = f"{stop.date.isoformat()}T{stop.set_time.strftime('%H:%M:%S')}"
                all_day = False
            else:
                event_start = stop.date.isoformat()
                all_day = True

            events.append({
                'id': stop.id,
                'title': base_title,
                'start': event_start,
                'allDay': all_day,
                'url': event_url,
                'backgroundColor': stop.event_color,
                'borderColor': stop.event_color,
                'textColor': '#ffffff' if stop.event_type not in [EventType.REHEARSAL, EventType.PHOTO_VIDEO, EventType.OTHER] else '#212529',
                'extendedProps': common_props
            })

            # Ghost event pour les concerts reportés (date originale barrée)
            if stop.is_rescheduled and stop.original_date:
                ghost_event = {
                    'id': f"ghost-{stop.id}",
                    'title': f"[REPORTÉ] {base_title}",
                    'start': stop.original_date.isoformat(),
                    'allDay': True,
                    'className': 'ghost-event',
                    'backgroundColor': '#6c757d',
                    'borderColor': '#495057',
                    'textColor': '#ffffff',
                    'extendedProps': {
                        'isGhost': True,
                        'stop_id': stop.id,
                        'tour_id': stop.tour_id,
                        'band_name': band.name,
                        'venue_name': venue_name,
                        'city': stop.venue.city if stop.venue else '',
                        'country': stop.venue.country if stop.venue else '',
                        'newDate': stop.date.strftime('%d/%m/%Y'),
                        'originalDate': stop.original_date.strftime('%d/%m/%Y'),
                        'rescheduleReason': stop.reschedule_reason,
                        'is_standalone': stop.is_standalone
                    }
                }
                events.append(ghost_event)

    return jsonify(events)


@main_bp.route('/search')
@login_required
def search():
    """Global search across tours, venues, guests."""
    query = request.args.get('q', '').strip()

    if not query or len(query) < 2:
        return render_template('main/search.html', query=query, results=None)

    # Get user's bands
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    results = {
        'tours': [],
        'venues': [],
        'guests': [],
        'bands': []
    }

    # Search tours
    from app.models.tour import Tour
    results['tours'] = Tour.query.filter(
        Tour.band_id.in_(user_band_ids),
        Tour.name.ilike(f'%{query}%')
    ).limit(10).all()

    # Search venues
    from app.models.venue import Venue
    results['venues'] = Venue.query.filter(
        Venue.name.ilike(f'%{query}%') |
        Venue.city.ilike(f'%{query}%')
    ).limit(10).all()

    # Search guestlist entries
    results['guests'] = GuestlistEntry.query.join(TourStop).join(Tour).filter(
        Tour.band_id.in_(user_band_ids),
        GuestlistEntry.guest_name.ilike(f'%{query}%')
    ).limit(10).all()

    # Search bands
    results['bands'] = Band.query.filter(
        Band.id.in_(user_band_ids),
        Band.name.ilike(f'%{query}%')
    ).limit(10).all()

    total_results = sum(len(v) for v in results.values())

    return render_template(
        'main/search.html',
        query=query,
        results=results,
        total_results=total_results
    )


@main_bp.route('/calendar/add', methods=['GET', 'POST'])
@login_required
def add_standalone_event():
    """Add a standalone event (not linked to a specific tour)."""
    form = StandaloneEventForm()

    # Get user's bands for the band selector
    user_bands = current_user.bands + current_user.managed_bands
    # Filter to only bands where user is manager (can create events)
    manageable_bands = [b for b in user_bands if b.is_manager(current_user)]

    if not manageable_bands:
        flash('Vous devez être manager d\'un groupe pour ajouter un événement.', 'warning')
        return redirect(url_for('main.global_calendar'))

    form.band_id.choices = [(0, '-- Sélectionner un groupe --')] + [
        (b.id, b.name) for b in manageable_bands
    ]

    # Tour selector (optional) - only tours for the selected band
    all_tours = Tour.query.filter(
        Tour.band_id.in_([b.id for b in manageable_bands])
    ).order_by(Tour.start_date.desc()).all()
    form.tour_id.choices = [(0, '-- Événement libre (sans tournée) --')] + [
        (t.id, f"{t.name} ({t.band.name})") for t in all_tours
    ]

    # Venue selector
    venues = Venue.query.order_by(Venue.name).all()
    form.venue_id.choices = [(0, '-- Sans salle --')] + [
        (v.id, f"{v.name} - {v.city}, {v.country}") for v in venues
    ]

    # Pre-fill date from URL parameter if provided
    prefill_date = request.args.get('date')

    if form.validate_on_submit():
        # Create the tour stop / standalone event
        event = TourStop(
            date=form.date.data,
            event_type=EventType(form.event_type.data),
            status=TourStopStatus(form.status.data),
            venue_id=form.venue_id.data if form.venue_id.data != 0 else None,
            show_type=form.show_type.data if form.show_type.data else None,
            guarantee=form.guarantee.data,
            ticket_price=form.ticket_price.data,
            ticket_url=form.ticket_url.data,
            set_length_minutes=form.set_length_minutes.data,
            age_restriction=form.age_restriction.data if form.age_restriction.data else None,
            notes=form.notes.data,
            internal_notes=form.internal_notes.data,
            # Call times
            load_in_time=form.load_in_time.data,
            crew_call_time=form.crew_call_time.data,
            artist_call_time=form.artist_call_time.data,
            catering_time=form.catering_time.data,
            soundcheck_time=form.soundcheck_time.data,
            press_time=form.press_time.data,
            meet_greet_time=form.meet_greet_time.data,
            doors_time=form.doors_time.data,
            set_time=form.set_time.data,
            curfew_time=form.curfew_time.data
        )

        # Set tour_id OR band_id (not both)
        if form.tour_id.data and form.tour_id.data != 0:
            event.tour_id = form.tour_id.data
            event.band_id = None
        else:
            event.tour_id = None
            event.band_id = form.band_id.data

        db.session.add(event)
        db.session.commit()

        flash('Événement créé avec succès.', 'success')
        return redirect(url_for('main.global_calendar'))

    return render_template(
        'main/event_form.html',
        form=form,
        prefill_date=prefill_date,
        title='Ajouter un événement'
    )


@main_bp.route('/calendar/event/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_standalone_event(event_id):
    """Edit a standalone event."""
    event = TourStop.query.get_or_404(event_id)

    # Check permissions
    if not event.can_edit(current_user):
        flash('Vous n\'avez pas la permission de modifier cet événement.', 'danger')
        return redirect(url_for('main.global_calendar'))

    form = StandaloneEventForm(obj=event)

    # Get user's bands for the band selector
    user_bands = current_user.bands + current_user.managed_bands
    manageable_bands = [b for b in user_bands if b.is_manager(current_user)]

    form.band_id.choices = [(0, '-- Sélectionner un groupe --')] + [
        (b.id, b.name) for b in manageable_bands
    ]

    # Tour selector
    all_tours = Tour.query.filter(
        Tour.band_id.in_([b.id for b in manageable_bands])
    ).order_by(Tour.start_date.desc()).all()
    form.tour_id.choices = [(0, '-- Événement libre (sans tournée) --')] + [
        (t.id, f"{t.name} ({t.band.name})") for t in all_tours
    ]

    # Venue selector
    venues = Venue.query.order_by(Venue.name).all()
    form.venue_id.choices = [(0, '-- Sans salle --')] + [
        (v.id, f"{v.name} - {v.city}, {v.country}") for v in venues
    ]

    if request.method == 'GET':
        # Pre-fill form values
        form.event_type.data = event.event_type.value if event.event_type else 'show'
        form.status.data = event.status.value if event.status else 'hold'
        form.band_id.data = event.band_id if event.band_id else (event.tour.band_id if event.tour else 0)
        form.tour_id.data = event.tour_id if event.tour_id else 0
        form.venue_id.data = event.venue_id if event.venue_id else 0

    if form.validate_on_submit():
        event.date = form.date.data
        event.event_type = EventType(form.event_type.data)
        event.status = TourStopStatus(form.status.data)
        event.venue_id = form.venue_id.data if form.venue_id.data != 0 else None
        event.show_type = form.show_type.data if form.show_type.data else None
        event.guarantee = form.guarantee.data
        event.ticket_price = form.ticket_price.data
        event.ticket_url = form.ticket_url.data
        event.set_length_minutes = form.set_length_minutes.data
        event.age_restriction = form.age_restriction.data if form.age_restriction.data else None
        event.notes = form.notes.data
        event.internal_notes = form.internal_notes.data
        # Call times
        event.load_in_time = form.load_in_time.data
        event.crew_call_time = form.crew_call_time.data
        event.artist_call_time = form.artist_call_time.data
        event.catering_time = form.catering_time.data
        event.soundcheck_time = form.soundcheck_time.data
        event.press_time = form.press_time.data
        event.meet_greet_time = form.meet_greet_time.data
        event.doors_time = form.doors_time.data
        event.set_time = form.set_time.data
        event.curfew_time = form.curfew_time.data

        # Set tour_id OR band_id
        if form.tour_id.data and form.tour_id.data != 0:
            event.tour_id = form.tour_id.data
            event.band_id = None
        else:
            event.tour_id = None
            event.band_id = form.band_id.data

        db.session.commit()

        flash('Événement mis à jour avec succès.', 'success')
        return redirect(url_for('main.global_calendar'))

    return render_template(
        'main/event_form.html',
        form=form,
        event=event,
        title='Modifier l\'événement'
    )


@main_bp.route('/calendar/event/<int:event_id>/delete', methods=['POST'])
@login_required
def delete_standalone_event(event_id):
    """Delete a standalone event."""
    event = TourStop.query.get_or_404(event_id)

    # Check permissions
    if not event.can_edit(current_user):
        flash('Vous n\'avez pas la permission de supprimer cet événement.', 'danger')
        return redirect(url_for('main.global_calendar'))

    db.session.delete(event)
    db.session.commit()

    flash('Événement supprimé avec succès.', 'success')
    return redirect(url_for('main.global_calendar'))
