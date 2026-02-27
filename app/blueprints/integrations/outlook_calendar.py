"""
Microsoft Outlook Calendar OAuth2 integration routes.
Uses MSAL (Microsoft Authentication Library) for OAuth2.
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

# Microsoft Graph API scopes needed
MICROSOFT_SCOPES = [
    'Calendars.ReadWrite',
    'User.Read'
]

# Microsoft Graph API endpoints
GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'


def get_microsoft_credentials():
    """Get Microsoft OAuth2 credentials from environment."""
    return {
        'client_id': os.environ.get('MICROSOFT_CLIENT_ID'),
        'client_secret': os.environ.get('MICROSOFT_CLIENT_SECRET'),
        'tenant_id': os.environ.get('MICROSOFT_TENANT_ID', 'common'),
        'redirect_uri': os.environ.get('MICROSOFT_REDIRECT_URI',
            url_for('integrations.outlook_callback', _external=True))
    }


def is_microsoft_configured():
    """Check if Microsoft OAuth is properly configured."""
    creds = get_microsoft_credentials()
    return bool(creds['client_id'] and creds['client_secret'])


def get_msal_app():
    """Create MSAL ConfidentialClientApplication."""
    try:
        import msal
        creds = get_microsoft_credentials()

        return msal.ConfidentialClientApplication(
            client_id=creds['client_id'],
            client_credential=creds['client_secret'],
            authority=f"https://login.microsoftonline.com/{creds['tenant_id']}"
        )
    except ImportError:
        return None


@integrations_bp.route('/outlook/status')
@login_required
def outlook_status():
    """Check Outlook Calendar connection status."""
    from flask import jsonify

    if not is_microsoft_configured():
        return jsonify({
            'connected': False,
            'configured': False,
            'message': 'Outlook Calendar integration is not configured'
        })

    token = OAuthToken.get_for_user(current_user.id, OAuthProvider.MICROSOFT.value)

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
            'message': 'Not connected to Outlook Calendar'
        })


@integrations_bp.route('/outlook/authorize')
@login_required
def outlook_authorize():
    """Initiate Microsoft OAuth2 authorization flow."""
    if not is_microsoft_configured():
        flash('Outlook Calendar integration is not configured. Please contact the administrator.', 'error')
        return redirect(url_for('settings.integrations'))

    msal_app = get_msal_app()
    if not msal_app:
        flash('Microsoft authentication dependencies not installed. Run: pip install msal', 'error')
        return redirect(url_for('settings.integrations'))

    try:
        creds = get_microsoft_credentials()

        # Initiate auth code flow
        flow = msal_app.initiate_auth_code_flow(
            scopes=MICROSOFT_SCOPES,
            redirect_uri=creds['redirect_uri']
        )

        # Store flow in session for callback
        session['msal_flow'] = flow

        return redirect(flow['auth_uri'])

    except Exception as e:
        current_app.logger.error(f'Outlook OAuth error: {e}')
        flash('Error initiating Outlook authorization.', 'error')
        return redirect(url_for('settings.integrations'))


@integrations_bp.route('/outlook/callback')
@login_required
def outlook_callback():
    """Handle Microsoft OAuth2 callback."""
    if not is_microsoft_configured():
        flash('Outlook Calendar integration is not configured.', 'error')
        return redirect(url_for('settings.integrations'))

    flow = session.get('msal_flow')
    if not flow:
        flash('Invalid OAuth flow. Please try again.', 'error')
        return redirect(url_for('settings.integrations'))

    msal_app = get_msal_app()
    if not msal_app:
        flash('Microsoft authentication library not available.', 'error')
        return redirect(url_for('settings.integrations'))

    try:
        # Complete the auth code flow
        result = msal_app.acquire_token_by_auth_code_flow(
            flow,
            dict(request.args)
        )

        if 'error' in result:
            flash(f'Outlook authorization failed: {result.get("error_description", result["error"])}', 'error')
            return redirect(url_for('settings.integrations'))

        # Calculate expiry
        expires_in = result.get('expires_in', 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Store or update tokens
        OAuthToken.create_or_update(
            user_id=current_user.id,
            provider=OAuthProvider.MICROSOFT.value,
            access_token=result['access_token'],
            refresh_token=result.get('refresh_token'),
            expires_at=expires_at,
            scopes=MICROSOFT_SCOPES,
            calendar_id='primary'  # Microsoft uses 'primary' or 'calendar'
        )
        db.session.commit()

        # Clear session flow
        session.pop('msal_flow', None)

        flash('Successfully connected to Outlook Calendar!', 'success')
        return redirect(url_for('settings.integrations'))

    except Exception as e:
        current_app.logger.error(f'Outlook callback error: {e}')
        current_app.logger.error(f'Outlook OAuth callback failed: {e}')
        flash('Erreur lors de l\'autorisation Outlook. Veuillez réessayer.', 'error')
        return redirect(url_for('settings.integrations'))


@integrations_bp.route('/outlook/sync', methods=['POST'])
@login_required
def outlook_sync():
    """Sync tour events with Outlook Calendar."""
    from flask import jsonify
    import requests

    token = OAuthToken.get_for_user(current_user.id, OAuthProvider.MICROSOFT.value)
    if not token:
        return jsonify({'success': False, 'error': 'Not connected to Outlook Calendar'}), 400

    try:
        # Refresh token if expired
        if token.is_expired and token.refresh_token:
            if not refresh_microsoft_token(token):
                return jsonify({'success': False, 'error': 'Failed to refresh token'}), 401

        headers = {
            'Authorization': f'Bearer {token.access_token}',
            'Content-Type': 'application/json'
        }

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
                event = create_outlook_event_from_stop(stop)
                # Create event in Outlook
                response = requests.post(
                    f'{GRAPH_API_ENDPOINT}/me/calendar/events',
                    headers=headers,
                    json=event
                )
                if response.status_code in [200, 201]:
                    synced_count += 1
                else:
                    current_app.logger.error(f'Outlook sync error for stop {stop.id}: {response.text}')
                    error_count += 1
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
        current_app.logger.error(f'Outlook sync error: {e}')
        token.mark_sync_error(str(e))
        db.session.commit()
        return jsonify({'success': False, 'error': str(e)}), 500


@integrations_bp.route('/outlook/disconnect', methods=['POST'])
@login_required
def outlook_disconnect():
    """Disconnect Outlook Calendar integration."""
    from flask import jsonify

    token = OAuthToken.get_for_user(current_user.id, OAuthProvider.MICROSOFT.value)
    if token:
        # Deactivate locally (Microsoft doesn't have a simple token revocation endpoint)
        token.deactivate()
        db.session.commit()

        return jsonify({'success': True, 'message': 'Disconnected from Outlook Calendar'})

    return jsonify({'success': False, 'error': 'Not connected to Outlook Calendar'}), 400


def refresh_microsoft_token(token):
    """
    Refresh an expired Microsoft access token.

    Args:
        token: OAuthToken instance

    Returns:
        bool: True if refresh was successful
    """
    msal_app = get_msal_app()
    if not msal_app or not token.refresh_token:
        return False

    try:
        result = msal_app.acquire_token_by_refresh_token(
            token.refresh_token,
            scopes=MICROSOFT_SCOPES
        )

        if 'access_token' in result:
            expires_in = result.get('expires_in', 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            token.update_tokens(
                access_token=result['access_token'],
                refresh_token=result.get('refresh_token', token.refresh_token),
                expires_at=expires_at
            )
            db.session.commit()
            return True
        else:
            current_app.logger.error(f'Token refresh failed: error={result.get("error")}, codes={result.get("error_codes")}')
            return False

    except Exception as e:
        current_app.logger.error(f'Error refreshing Microsoft token: {e}')
        return False


def create_outlook_event_from_stop(stop):
    """
    Create a Microsoft Graph Calendar event object from a TourStop.

    Args:
        stop: TourStop instance

    Returns:
        dict: Microsoft Graph Calendar event format
    """
    # Build event subject
    subject = f"{stop.event_label}"
    if stop.venue:
        subject += f" @ {stop.venue.name}"
    if stop.tour:
        subject += f" ({stop.tour.name})"

    # Build body with details
    body_parts = []
    if stop.tour:
        body_parts.append(f"<strong>Tour:</strong> {stop.tour.name}")
    if stop.venue:
        body_parts.append(f"<strong>Venue:</strong> {stop.venue.name}")
        if stop.venue.city:
            body_parts.append(f"<strong>City:</strong> {stop.venue.city}")
    if stop.capacity:
        body_parts.append(f"<strong>Capacity:</strong> {stop.capacity}")
    if stop.guarantee:
        body_parts.append(f"<strong>Guarantee:</strong> {stop.guarantee} {stop.currency or 'EUR'}")

    # Add call times
    if stop.load_in_time:
        body_parts.append(f"<strong>Load-in:</strong> {stop.load_in_time.strftime('%H:%M')}")
    if stop.doors_time:
        body_parts.append(f"<strong>Doors:</strong> {stop.doors_time.strftime('%H:%M')}")
    if stop.set_time:
        body_parts.append(f"<strong>Set:</strong> {stop.set_time.strftime('%H:%M')}")

    if stop.notes:
        body_parts.append(f"<br><strong>Notes:</strong> {stop.notes}")

    body_content = '<br>'.join(body_parts)

    # Build location
    location = None
    if stop.venue:
        location = {
            'displayName': stop.venue.name
        }
        address_parts = []
        if stop.venue.address:
            address_parts.append(stop.venue.address)
        if stop.venue.city:
            address_parts.append(stop.venue.city)
        if stop.venue.country:
            address_parts.append(stop.venue.country)
        if address_parts:
            location['address'] = {
                'street': stop.venue.address or '',
                'city': stop.venue.city or '',
                'countryOrRegion': stop.venue.country or ''
            }

    # Determine start/end times
    if stop.set_time:
        start_datetime = datetime.combine(stop.date, stop.set_time)
        end_datetime = datetime.combine(stop.date, stop.curfew_time) if stop.curfew_time else start_datetime + timedelta(hours=2)

        # Get timezone from venue or user preferences
        event_timezone = get_timezone_for_event(stop=stop, user=current_user)

        return {
            'subject': subject,
            'body': {
                'contentType': 'HTML',
                'content': body_content
            },
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': event_timezone
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': event_timezone
            },
            'location': location,
            'categories': [get_outlook_category(stop.event_type)]
        }
    else:
        # All-day event
        # Get timezone from venue or user preferences
        event_timezone = get_timezone_for_event(stop=stop, user=current_user)

        return {
            'subject': subject,
            'body': {
                'contentType': 'HTML',
                'content': body_content
            },
            'start': {
                'dateTime': datetime.combine(stop.date, datetime.min.time()).isoformat(),
                'timeZone': event_timezone
            },
            'end': {
                'dateTime': datetime.combine(stop.date + timedelta(days=1), datetime.min.time()).isoformat(),
                'timeZone': event_timezone
            },
            'isAllDay': True,
            'location': location,
            'categories': [get_outlook_category(stop.event_type)]
        }


def get_outlook_category(event_type):
    """
    Map EventType to Outlook Calendar category names.

    Outlook uses preset category names that can be color-coded by users.
    """
    category_map = {
        EventType.SHOW: 'Green Category',
        EventType.DAY_OFF: 'Gray Category',
        EventType.TRAVEL: 'Blue Category',
        EventType.STUDIO: 'Purple Category',
        EventType.PROMO: 'Orange Category',
        EventType.REHEARSAL: 'Yellow Category',
        EventType.PRESS: 'Red Category',
        EventType.MEET_GREET: 'Teal Category',
        EventType.PHOTO_VIDEO: 'Pink Category',
        EventType.OTHER: 'Gray Category'
    }
    return category_map.get(event_type, 'Gray Category')
