"""
Timezone utilities for calendar integrations.
Provides dynamic timezone resolution based on venue, user, or system defaults.
"""
import pytz

# Default timezone fallback
DEFAULT_TIMEZONE = 'Europe/Paris'


def get_timezone_for_event(stop=None, user=None):
    """
    Get appropriate timezone for a calendar event.

    Priority order:
    1. Venue timezone (most specific - based on event location)
    2. User timezone (user preference)
    3. Default fallback (Europe/Paris)

    Args:
        stop: TourStop object (optional) - will check venue timezone
        user: User object (optional) - will check user preference

    Returns:
        str: IANA timezone string (e.g., 'Europe/Paris', 'America/New_York')
    """
    # 1. Venue timezone (most specific for events)
    if stop and stop.venue:
        venue_tz = getattr(stop.venue, 'timezone', None)
        if venue_tz and is_valid_timezone(venue_tz):
            return venue_tz

    # 2. User timezone preference
    if user:
        user_tz = getattr(user, 'timezone', None)
        if user_tz and is_valid_timezone(user_tz):
            return user_tz

    # 3. Default fallback
    return DEFAULT_TIMEZONE


def is_valid_timezone(tz_string):
    """
    Validate timezone string against pytz database.

    Args:
        tz_string: Timezone string to validate (e.g., 'Europe/Paris')

    Returns:
        bool: True if valid IANA timezone
    """
    if not tz_string:
        return False
    return tz_string in pytz.all_timezones


def get_common_timezones():
    """
    Get list of commonly used timezones for UI dropdowns.

    Returns:
        list: List of tuples (timezone_id, display_name)
    """
    common = [
        ('Europe/Paris', 'Paris (CET/CEST)'),
        ('Europe/London', 'London (GMT/BST)'),
        ('Europe/Berlin', 'Berlin (CET/CEST)'),
        ('Europe/Amsterdam', 'Amsterdam (CET/CEST)'),
        ('Europe/Brussels', 'Brussels (CET/CEST)'),
        ('Europe/Madrid', 'Madrid (CET/CEST)'),
        ('Europe/Rome', 'Rome (CET/CEST)'),
        ('Europe/Zurich', 'Zurich (CET/CEST)'),
        ('Europe/Vienna', 'Vienna (CET/CEST)'),
        ('Europe/Stockholm', 'Stockholm (CET/CEST)'),
        ('Europe/Oslo', 'Oslo (CET/CEST)'),
        ('Europe/Copenhagen', 'Copenhagen (CET/CEST)'),
        ('Europe/Helsinki', 'Helsinki (EET/EEST)'),
        ('Europe/Warsaw', 'Warsaw (CET/CEST)'),
        ('Europe/Prague', 'Prague (CET/CEST)'),
        ('Europe/Dublin', 'Dublin (GMT/IST)'),
        ('Europe/Lisbon', 'Lisbon (WET/WEST)'),
        ('Europe/Athens', 'Athens (EET/EEST)'),
        ('Europe/Moscow', 'Moscow (MSK)'),
        ('America/New_York', 'New York (EST/EDT)'),
        ('America/Los_Angeles', 'Los Angeles (PST/PDT)'),
        ('America/Chicago', 'Chicago (CST/CDT)'),
        ('America/Denver', 'Denver (MST/MDT)'),
        ('America/Toronto', 'Toronto (EST/EDT)'),
        ('America/Montreal', 'Montreal (EST/EDT)'),
        ('America/Vancouver', 'Vancouver (PST/PDT)'),
        ('America/Mexico_City', 'Mexico City (CST/CDT)'),
        ('America/Sao_Paulo', 'Sao Paulo (BRT)'),
        ('America/Buenos_Aires', 'Buenos Aires (ART)'),
        ('Asia/Tokyo', 'Tokyo (JST)'),
        ('Asia/Shanghai', 'Shanghai (CST)'),
        ('Asia/Hong_Kong', 'Hong Kong (HKT)'),
        ('Asia/Singapore', 'Singapore (SGT)'),
        ('Asia/Seoul', 'Seoul (KST)'),
        ('Asia/Dubai', 'Dubai (GST)'),
        ('Australia/Sydney', 'Sydney (AEST/AEDT)'),
        ('Australia/Melbourne', 'Melbourne (AEST/AEDT)'),
        ('Pacific/Auckland', 'Auckland (NZST/NZDT)'),
        ('UTC', 'UTC'),
    ]
    return common
