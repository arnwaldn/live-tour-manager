"""
Google Calendar OAuth2 integration routes.
Handles authorization, sync, and disconnection.
"""
import os
import json
from datetime import datetime, timedelta
from flask import redirect, url_for, flash, request, session, current_app
from flask_login import login_required, current_user

from app.blueprints.integrations import integrations_bp
from app.models.oauth_token import OAuthToken, OAuthProvider
from app.models.tour_stop import TourStop, EventType
from app.extensions import db
from app.utils.timezone import get_timezone_for_event

# Google OAuth2 scopes needed
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]


def get_google_credentials():
    """Get Google OAuth2 credentials from environment."""
    return {
        'client_id': os.environ.get('GOOGLE_CLIENT_ID'),
        'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET'),
        'redirect_uri': os.environ.get('GOOGLE_REDIRECT_URI',
            url_for('integrations.google_callback', _external=True))
    }


def is_google_configured():
    """Check if Google OAuth is properly configured."""
    creds = get_google_credentials()
    return bool(creds['client_id'] and creds['client_secret'])


@integrations_bp.route('/google/status')
@login_required
def google_status():
    """Check Google Calendar connection status."""
    from flask import jsonify

    if not is_google_configured():
        return jsonify({
            'connected': False,
            'configured': False,
            'message': 'Google Calendar integration is not configured'
        })

    token = OAuthToken.get_for_user(current_user.id, OAuthProvider.GOOGLE.value)

    if token:
        return jsonify({
            'connected': True,
            'configured': True,
            'last_sync': token.last_sync.isoformat() if token.last_sync else None,
            'calendar_id': token.calendar_id,
            'sync_error': token.sync_error
        })
    else:
        return jsonify({
            'connected': False,
            'configured': True,
            'message': 'Not connected to Google Calendar'
        })


@integrations_bp.route('/google/authorize')
@login_required
def google_authorize():
    """Initiate Google OAuth2 authorization flow."""
    if not is_google_configured():
        flash('Google Calendar integration is not configured. Please contact the administrator.', 'error')
        return redirect(url_for('settings.integrations'))

    try:
        from google_auth_oauthlib.flow import Flow

        creds = get_google_credentials()

        # Build the authorization URL
        flow = Flow.from_client_config(
            {
                'web': {
                    'client_id': creds['client_id'],
                    'client_secret': creds['client_secret'],
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                    'redirect_uris': [creds['redirect_uri']]
                }
            },
            scopes=GOOGLE_SCOPES
        )
        flow.redirect_uri = creds['redirect_uri']

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force consent to get refresh token
        )

        # Store state in session for validation
        session['google_oauth_state'] = state

        return redirect(authorization_url)

    except ImportError:
        flash('Google Calendar dependencies not installed. Run: pip install google-auth-oauthlib google-api-python-client', 'error')
        return redirect(url_for('settings.integrations'))
    except Exception as e:
        current_app.logger.error(f'Google OAuth error: {e}')
        flash('Error initiating Google authorization.', 'error')
        return redirect(url_for('settings.integrations'))


@integrations_bp.route('/google/callback')
@login_required
def google_callback():
    """Handle Google OAuth2 callback."""
    if not is_google_configured():
        flash('Google Calendar integration is not configured.', 'error')
        return redirect(url_for('settings.integrations'))

    # Verify state to prevent CSRF
    if request.args.get('state') != session.get('google_oauth_state'):
        flash('Invalid OAuth state. Please try again.', 'error')
        return redirect(url_for('settings.integrations'))

    if request.args.get('error'):
        error = request.args.get('error')
        flash(f'Google authorization was denied: {error}', 'error')
        return redirect(url_for('settings.integrations'))

    try:
        from google_auth_oauthlib.flow import Flow
        from googleapiclient.discovery import build

        creds = get_google_credentials()

        # Complete the OAuth flow
        flow = Flow.from_client_config(
            {
                'web': {
                    'client_id': creds['client_id'],
                    'client_secret': creds['client_secret'],
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                    'redirect_uris': [creds['redirect_uri']]
                }
            },
            scopes=GOOGLE_SCOPES,
            state=session.get('google_oauth_state')
        )
        flow.redirect_uri = creds['redirect_uri']

        # Exchange authorization code for tokens
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials

        # Get user's primary calendar ID
        service = build('calendar', 'v3', credentials=credentials)
        calendar = service.calendars().get(calendarId='primary').execute()
        calendar_id = calendar.get('id', 'primary')

        # Calculate expiry datetime
        expires_at = datetime.utcnow() + timedelta(seconds=credentials.expiry.timestamp() - datetime.utcnow().timestamp()) if credentials.expiry else None

        # Store or update tokens
        OAuthToken.create_or_update(
            user_id=current_user.id,
            provider=OAuthProvider.GOOGLE.value,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            expires_at=expires_at,
            scopes=list(credentials.scopes) if credentials.scopes else GOOGLE_SCOPES,
            calendar_id=calendar_id
        )
        db.session.commit()

        # Clear session state
        session.pop('google_oauth_state', None)

        flash('Successfully connected to Google Calendar!', 'success')
        return redirect(url_for('settings.integrations'))

    except Exception as e:
        current_app.logger.error(f'Google callback error: {e}')
        flash(f'Error completing Google authorization: {str(e)}', 'error')
        return redirect(url_for('settings.integrations'))


@integrations_bp.route('/google/sync', methods=['POST'])
@login_required
def google_sync():
    """Sync tour events with Google Calendar."""
    from flask import jsonify

    token = OAuthToken.get_for_user(current_user.id, OAuthProvider.GOOGLE.value)
    if not token:
        return jsonify({'success': False, 'error': 'Not connected to Google Calendar'}), 400

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = get_google_credentials()

        # Build credentials object
        credentials = Credentials(
            token=token.access_token,
            refresh_token=token.refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=creds['client_id'],
            client_secret=creds['client_secret'],
            scopes=token.scopes
        )

        # Refresh if expired
        if token.is_expired and token.refresh_token:
            from google.auth.transport.requests import Request
            credentials.refresh(Request())

            # Update stored tokens
            token.update_tokens(
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                expires_at=credentials.expiry
            )
            db.session.commit()

        # Build calendar service
        service = build('calendar', 'v3', credentials=credentials)

        # Get user's tour stops to sync
        from app.models.band import Band
        user_bands = current_user.bands + current_user.managed_bands
        band_ids = [b.id for b in user_bands]

        # Get upcoming tour stops
        stops = TourStop.query.filter(
            TourStop.band_id.in_(band_ids),
            TourStop.date >= datetime.utcnow().date()
        ).all()

        synced_count = 0
        error_count = 0

        for stop in stops:
            try:
                event = create_google_event_from_stop(stop)
                # Insert or update event
                service.events().insert(
                    calendarId=token.calendar_id or 'primary',
                    body=event
                ).execute()
                synced_count += 1
            except Exception as e:
                current_app.logger.error(f'Error syncing stop {stop.id}: {e}')
                error_count += 1

        # Mark sync complete
        token.mark_sync_complete()
        db.session.commit()

        return jsonify({
            'success': True,
            'synced': synced_count,
            'errors': error_count
        })

    except Exception as e:
        current_app.logger.error(f'Google sync error: {e}')
        token.mark_sync_error(str(e))
        db.session.commit()
        return jsonify({'success': False, 'error': str(e)}), 500


@integrations_bp.route('/google/disconnect', methods=['POST'])
@login_required
def google_disconnect():
    """Disconnect Google Calendar integration."""
    from flask import jsonify

    token = OAuthToken.get_for_user(current_user.id, OAuthProvider.GOOGLE.value)
    if token:
        # Try to revoke the token
        try:
            import requests
            requests.post(
                'https://oauth2.googleapis.com/revoke',
                params={'token': token.access_token},
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
        except Exception as e:
            current_app.logger.warning(f'Error revoking Google token: {e}')

        # Deactivate locally
        token.deactivate()
        db.session.commit()

        return jsonify({'success': True, 'message': 'Disconnected from Google Calendar'})

    return jsonify({'success': False, 'error': 'Not connected to Google Calendar'}), 400


def create_google_event_from_stop(stop):
    """
    Create a Google Calendar event object from a TourStop.

    Args:
        stop: TourStop instance

    Returns:
        dict: Google Calendar event format
    """
    # Build event summary
    summary = f"{stop.event_label}"
    if stop.venue:
        summary += f" @ {stop.venue.name}"
    if stop.tour:
        summary += f" ({stop.tour.name})"

    # Build description with all details
    description_parts = []
    if stop.tour:
        description_parts.append(f"Tour: {stop.tour.name}")
    if stop.venue:
        description_parts.append(f"Venue: {stop.venue.name}")
        if stop.venue.city:
            description_parts.append(f"City: {stop.venue.city}")
    if stop.capacity:
        description_parts.append(f"Capacity: {stop.capacity}")
    if stop.guarantee:
        description_parts.append(f"Guarantee: {stop.guarantee} {stop.currency or 'EUR'}")
    if stop.notes:
        description_parts.append(f"\nNotes: {stop.notes}")

    # Add call times to description
    if stop.load_in_time:
        description_parts.append(f"Load-in: {stop.load_in_time.strftime('%H:%M')}")
    if stop.doors_time:
        description_parts.append(f"Doors: {stop.doors_time.strftime('%H:%M')}")
    if stop.set_time:
        description_parts.append(f"Set: {stop.set_time.strftime('%H:%M')}")

    # Build location
    location = None
    if stop.venue:
        location_parts = [stop.venue.name]
        if stop.venue.address:
            location_parts.append(stop.venue.address)
        if stop.venue.city:
            location_parts.append(stop.venue.city)
        if stop.venue.country:
            location_parts.append(stop.venue.country)
        location = ', '.join(location_parts)

    # Determine start/end times
    start_date = stop.date.isoformat()
    end_date = stop.date.isoformat()

    if stop.set_time:
        start_datetime = datetime.combine(stop.date, stop.set_time)
        # Assume 2 hour show duration if no curfew
        end_datetime = datetime.combine(stop.date, stop.curfew_time) if stop.curfew_time else start_datetime + timedelta(hours=2)

        # Get timezone from venue or user preferences
        event_timezone = get_timezone_for_event(stop=stop, user=current_user)

        return {
            'summary': summary,
            'description': '\n'.join(description_parts),
            'location': location,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': event_timezone
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': event_timezone
            },
            'colorId': get_event_color_id(stop.event_type)
        }
    else:
        # All-day event
        return {
            'summary': summary,
            'description': '\n'.join(description_parts),
            'location': location,
            'start': {
                'date': start_date
            },
            'end': {
                'date': end_date
            },
            'colorId': get_event_color_id(stop.event_type)
        }


def get_event_color_id(event_type):
    """
    Map EventType to Google Calendar color IDs.

    Google Calendar color IDs:
    1 = Lavender, 2 = Sage, 3 = Grape, 4 = Flamingo,
    5 = Banana, 6 = Tangerine, 7 = Peacock, 8 = Graphite,
    9 = Blueberry, 10 = Basil, 11 = Tomato
    """
    color_map = {
        EventType.SHOW: '10',       # Basil (green)
        EventType.DAY_OFF: '8',     # Graphite (gray)
        EventType.TRAVEL: '7',      # Peacock (blue)
        EventType.STUDIO: '3',      # Grape (purple)
        EventType.PROMO: '6',       # Tangerine (orange)
        EventType.REHEARSAL: '5',   # Banana (yellow)
        EventType.PRESS: '4',       # Flamingo (pink)
        EventType.MEET_GREET: '2',  # Sage (teal-ish)
        EventType.PHOTO_VIDEO: '4', # Flamingo (pink)
        EventType.OTHER: '8'        # Graphite (gray)
    }
    return color_map.get(event_type, '8')
