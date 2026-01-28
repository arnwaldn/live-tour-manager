"""
Service for tour stop reminders.
Provides queries to find tour stops needing J-7 and J-1 reminders.
"""
from datetime import date, timedelta
from app.models.tour_stop import TourStop, TourStopStatus, EventType


def get_stops_needing_j7_reminders():
    """
    Get tour stops needing J-7 reminders (7 days before).

    Returns:
        list: TourStop objects needing reminders
    """
    target_date = date.today() + timedelta(days=7)
    return TourStop.query.filter(
        TourStop.date == target_date,
        TourStop.status.in_([TourStopStatus.CONFIRMED, TourStopStatus.PENDING]),
        TourStop.event_type == EventType.SHOW
    ).all()


def get_stops_needing_j1_reminders():
    """
    Get tour stops needing J-1 reminders (1 day before).

    Returns:
        list: TourStop objects needing reminders
    """
    target_date = date.today() + timedelta(days=1)
    return TourStop.query.filter(
        TourStop.date == target_date,
        TourStop.status.in_([TourStopStatus.CONFIRMED, TourStopStatus.PENDING]),
        TourStop.event_type == EventType.SHOW
    ).all()


def get_users_for_reminder(tour_stop):
    """
    Get users who should receive a reminder for this tour stop.

    Priority:
    1. If tour_stop has assigned_members, use those
    2. Otherwise, use band manager + all band members

    Filters:
    - User must have notify_tour_reminder = True
    - User must be active

    Args:
        tour_stop: TourStop object

    Returns:
        list: User objects to receive reminders
    """
    band = tour_stop.associated_band
    if not band:
        return []

    recipients = set()

    # Priority: assigned members first
    if hasattr(tour_stop, 'assigned_members') and tour_stop.assigned_members:
        for user in tour_stop.assigned_members:
            recipients.add(user)
    else:
        # Fallback: all band members
        if band.manager:
            recipients.add(band.manager)
        for membership in band.memberships:
            if membership.user:
                recipients.add(membership.user)

    # Filter by notification preferences and active status
    return [
        u for u in recipients
        if u.is_active and getattr(u, 'notify_tour_reminder', True)
    ]
