# Patch file - add this function after _get_band_member_emails

def _user_accepts_notification(email, preference_name):
    """
    Check if user with given email accepts this notification type.

    Args:
        email: User email address
        preference_name: Name of the preference flag (e.g., 'notify_guestlist_request')

    Returns:
        bool: True if user accepts notifications, False otherwise.
              Returns True for external users (not in database).
    """
    from app.models.user import User
    user = User.query.filter_by(email=email).first()
    if not user:
        return True  # External user, send by default
    return getattr(user, preference_name, True)
