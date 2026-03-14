"""
Firebase Cloud Messaging service for push notifications.

Uses firebase-admin SDK to send push notifications to registered devices.
Requires GOOGLE_APPLICATION_CREDENTIALS env var pointing to a Firebase
service account JSON file, or FIREBASE_CREDENTIALS_JSON with inline JSON.
"""
import json
import logging
import os

logger = logging.getLogger(__name__)

# Lazy-initialized Firebase app
_firebase_app = None


def _init_firebase():
    """Initialize Firebase Admin SDK (once)."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        logger.warning('firebase-admin not installed — push notifications disabled')
        return None

    # Option 1: env var with path to service account JSON
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    # Option 2: env var with inline JSON (for Render/Heroku)
    creds_json = os.environ.get('FIREBASE_CREDENTIALS_JSON')

    try:
        if creds_json:
            cred = credentials.Certificate(json.loads(creds_json))
        elif creds_path:
            cred = credentials.Certificate(creds_path)
        else:
            logger.warning('No Firebase credentials configured — push notifications disabled')
            return None

        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info('Firebase Admin SDK initialized successfully')
        return _firebase_app
    except Exception as e:
        logger.error('Failed to initialize Firebase: %s', e)
        return None


def send_push_notification(tokens, title, body, data=None):
    """
    Send a push notification to one or more FCM tokens.

    Args:
        tokens: str or list of FCM token strings
        title: notification title
        body: notification body text
        data: optional dict of custom data (all values must be strings)

    Returns:
        dict with 'success_count' and 'failure_count'
    """
    if not tokens:
        return {'success_count': 0, 'failure_count': 0}

    app = _init_firebase()
    if app is None:
        logger.debug('Firebase not available — skipping push for: %s', title)
        return {'success_count': 0, 'failure_count': 0, 'skipped': True}

    from firebase_admin import messaging

    if isinstance(tokens, str):
        tokens = [tokens]

    # Ensure data values are strings (FCM requirement)
    clean_data = {}
    if data:
        clean_data = {k: str(v) for k, v in data.items()}

    notification = messaging.Notification(title=title, body=body)

    if len(tokens) == 1:
        message = messaging.Message(
            notification=notification,
            data=clean_data,
            token=tokens[0],
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    channel_id='gigroute_notifications',
                    icon='ic_notification',
                ),
            ),
        )
        try:
            messaging.send(message)
            return {'success_count': 1, 'failure_count': 0}
        except messaging.UnregisteredError:
            _deactivate_token(tokens[0])
            return {'success_count': 0, 'failure_count': 1}
        except Exception as e:
            logger.error('FCM send error: %s', e)
            return {'success_count': 0, 'failure_count': 1}
    else:
        # Batch send for multiple tokens
        messages = [
            messaging.Message(
                notification=notification,
                data=clean_data,
                token=token,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        channel_id='gigroute_notifications',
                        icon='ic_notification',
                    ),
                ),
            )
            for token in tokens
        ]
        try:
            response = messaging.send_each(messages)
            # Deactivate tokens that got UnregisteredError
            for i, send_response in enumerate(response.responses):
                if send_response.exception and isinstance(
                    send_response.exception, messaging.UnregisteredError
                ):
                    _deactivate_token(tokens[i])

            return {
                'success_count': response.success_count,
                'failure_count': response.failure_count,
            }
        except Exception as e:
            logger.error('FCM batch send error: %s', e)
            return {'success_count': 0, 'failure_count': len(tokens)}


def send_push_to_user(user_id, title, body, data=None):
    """Send push notification to all active devices of a user."""
    from app.models.device_token import DeviceToken

    device_tokens = DeviceToken.get_active_tokens(user_id)
    if not device_tokens:
        return {'success_count': 0, 'failure_count': 0, 'no_tokens': True}

    tokens = [dt.token for dt in device_tokens]
    return send_push_notification(tokens, title, body, data)


def send_push_to_users(user_ids, title, body, data=None):
    """Send push notification to all active devices of multiple users."""
    from app.models.device_token import DeviceToken

    device_tokens = DeviceToken.get_active_tokens_for_users(user_ids)
    if not device_tokens:
        return {'success_count': 0, 'failure_count': 0, 'no_tokens': True}

    tokens = [dt.token for dt in device_tokens]
    return send_push_notification(tokens, title, body, data)


def _deactivate_token(token):
    """Deactivate an invalid/unregistered token."""
    try:
        from app.models.device_token import DeviceToken
        DeviceToken.unregister_token(token)
        logger.info('Deactivated unregistered FCM token: %s...', token[:20])
    except Exception as e:
        logger.error('Failed to deactivate token: %s', e)
