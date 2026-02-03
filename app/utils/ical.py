"""
iCal utilities for Tour Manager.
Generates proper iCal/ICS files compatible with Google Calendar, Apple Calendar, Outlook, etc.
"""
from datetime import datetime, timedelta, date, time
from icalendar import Calendar, Event, Alarm
import pytz

# Default timezone for events
DEFAULT_TIMEZONE = pytz.timezone('Europe/Paris')


def create_calendar(name, description=None):
    """
    Create a new iCal calendar with proper headers.

    Args:
        name: Calendar name (e.g., tour name)
        description: Optional calendar description

    Returns:
        icalendar.Calendar object
    """
    cal = Calendar()
    cal.add('prodid', '-//Studio Palenque Tour//Tour Manager//FR')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')
    cal.add('x-wr-calname', name)
    cal.add('x-wr-timezone', 'Europe/Paris')

    if description:
        cal.add('x-wr-caldesc', description)

    return cal


def create_event(tour_stop, tour=None, include_alarm=True):
    """
    Create an iCal event from a TourStop.

    Args:
        tour_stop: TourStop model instance
        tour: Optional Tour model instance (for context)
        include_alarm: Whether to add a reminder (default: True)

    Returns:
        icalendar.Event object
    """
    from app.models.tour_stop import EventType

    event = Event()

    # Unique identifier
    tour_id = tour.id if tour else (tour_stop.tour_id or 0)
    event.add('uid', f'tourstop-{tour_stop.id}-tour-{tour_id}@tourmanager.studiopalenque.com')

    # Timestamps
    now = datetime.now(DEFAULT_TIMEZONE)
    event.add('dtstamp', now)
    event.add('created', tour_stop.created_at or now)
    event.add('last-modified', tour_stop.updated_at or now)

    # Build summary (title)
    summary = _build_summary(tour_stop, tour)
    event.add('summary', summary)

    # Date/time handling
    start_dt, end_dt = _get_event_times(tour_stop)
    if isinstance(start_dt, datetime):
        event.add('dtstart', start_dt)
        event.add('dtend', end_dt)
    else:
        # All-day event (for DAY_OFF, TRAVEL, etc.)
        event.add('dtstart', start_dt)
        event.add('dtend', end_dt)

    # Location
    location = build_location(tour_stop)
    if location:
        event.add('location', location)

    # Description with all details
    description = build_description(tour_stop, tour)
    event.add('description', description)

    # Category based on event type
    category = _get_event_category(tour_stop)
    if category:
        event.add('categories', [category])

    # Status
    status = _get_event_status(tour_stop)
    event.add('status', status)

    # Add alarm (reminder 1 day before)
    if include_alarm and tour_stop.event_type not in [EventType.DAY_OFF, EventType.TRAVEL]:
        alarm = Alarm()
        alarm.add('action', 'DISPLAY')
        alarm.add('description', f'Rappel: {summary}')
        alarm.add('trigger', timedelta(days=-1))
        event.add_component(alarm)

    return event


def build_location(tour_stop):
    """
    Build location string from tour stop data.

    Args:
        tour_stop: TourStop model instance

    Returns:
        str: Formatted location string or None
    """
    parts = []

    # Prefer venue if available
    if tour_stop.venue:
        venue = tour_stop.venue
        if venue.name:
            parts.append(venue.name)
        if venue.address:
            parts.append(venue.address)
        if venue.city:
            city_part = venue.city
            if venue.postal_code:
                city_part = f"{venue.postal_code} {city_part}"
            parts.append(city_part)
        if venue.country:
            parts.append(venue.country)
    else:
        # Use direct location fields
        if tour_stop.location_address:
            parts.append(tour_stop.location_address)
        if tour_stop.location_city:
            parts.append(tour_stop.location_city)
        if tour_stop.location_country:
            parts.append(tour_stop.location_country)

    return ', '.join(parts) if parts else None


def build_description(tour_stop, tour=None):
    """
    Build detailed event description with all relevant information.

    Args:
        tour_stop: TourStop model instance
        tour: Optional Tour model instance

    Returns:
        str: Multi-line description
    """
    from app.models.tour_stop import EventType

    lines = []

    # Tour info
    if tour:
        band_name = tour.band.name if tour.band else 'N/A'
        lines.append(f"🎤 Tournée: {tour.name}")
        lines.append(f"🎸 Groupe: {band_name}")
    elif tour_stop.band:
        lines.append(f"🎸 Groupe: {tour_stop.band.name}")

    lines.append("")

    # Venue info
    if tour_stop.venue:
        lines.append(f"📍 Lieu: {tour_stop.venue.name}")
        if tour_stop.venue.address:
            lines.append(f"   {tour_stop.venue.address}")
        if tour_stop.venue.city:
            lines.append(f"   {tour_stop.venue.city}, {tour_stop.venue.country or ''}")
        if tour_stop.venue.capacity:
            lines.append(f"   Capacité: {tour_stop.venue.capacity}")
        lines.append("")

    # Only show times for actual shows/events (not DAY_OFF, TRAVEL)
    if tour_stop.event_type not in [EventType.DAY_OFF, EventType.TRAVEL]:
        # Call times
        times_section = []
        if tour_stop.load_in_time:
            times_section.append(f"🚚 Load-in: {_format_time(tour_stop.load_in_time)}")
        if tour_stop.crew_call_time:
            times_section.append(f"👷 Crew call: {_format_time(tour_stop.crew_call_time)}")
        if tour_stop.artist_call_time:
            times_section.append(f"🎤 Artiste call: {_format_time(tour_stop.artist_call_time)}")
        if tour_stop.soundcheck_time:
            times_section.append(f"🔊 Soundcheck: {_format_time(tour_stop.soundcheck_time)}")
        if tour_stop.catering_time:
            times_section.append(f"🍽️ Catering: {_format_time(tour_stop.catering_time)}")
        if tour_stop.meet_greet_time:
            times_section.append(f"🤝 Meet & Greet: {_format_time(tour_stop.meet_greet_time)}")
        if tour_stop.doors_time:
            times_section.append(f"🚪 Portes: {_format_time(tour_stop.doors_time)}")
        if tour_stop.set_time:
            times_section.append(f"🎵 Début concert: {_format_time(tour_stop.set_time)}")
        if tour_stop.curfew_time:
            times_section.append(f"⏰ Couvre-feu: {_format_time(tour_stop.curfew_time)}")

        if times_section:
            lines.append("⏱️ HORAIRES:")
            lines.extend(times_section)
            lines.append("")

        # Show details
        if tour_stop.set_length_minutes:
            lines.append(f"⏱️ Durée set: {tour_stop.set_length_minutes} minutes")

        if tour_stop.age_restriction:
            lines.append(f"🔞 Restriction d'âge: {tour_stop.age_restriction}")

    # Notes
    if tour_stop.notes:
        lines.append("")
        lines.append(f"📝 Notes: {tour_stop.notes}")

    return '\n'.join(lines)


def _build_summary(tour_stop, tour=None):
    """Build event summary/title."""
    from app.models.tour_stop import EventType

    # Get event type label
    event_type = tour_stop.event_type
    type_labels = {
        EventType.SHOW: '🎤 Concert',
        EventType.REHEARSAL: '🎸 Répétition',
        EventType.STUDIO: '🎙️ Enregistrement',
        EventType.PRESS: '🎤 Interview',
        EventType.PROMO: '📢 Promo',
        EventType.PHOTO_VIDEO: '📸 Photoshoot',
        EventType.MEET_GREET: '🤝 Meet & Greet',
        EventType.DAY_OFF: '😴 Jour off',
        EventType.TRAVEL: '✈️ Voyage',
        EventType.OTHER: '📅 Événement',
    }
    type_label = type_labels.get(event_type, '📅')

    # Build location part
    if tour_stop.venue:
        location_part = tour_stop.venue.name
    elif tour_stop.location_city:
        location_part = tour_stop.location_city
    else:
        location_part = 'Lieu à définir'

    # Build full summary
    if tour and tour.band:
        return f"{type_label} {tour.band.name} @ {location_part}"
    elif tour_stop.band:
        return f"{type_label} {tour_stop.band.name} @ {location_part}"
    else:
        return f"{type_label} @ {location_part}"


def _get_event_times(tour_stop):
    """
    Calculate event start and end times.

    Returns tuple of (start, end) as datetime or date objects.
    """
    from app.models.tour_stop import EventType

    event_date = tour_stop.date

    # For DAY_OFF and TRAVEL, use all-day events
    if tour_stop.event_type in [EventType.DAY_OFF, EventType.TRAVEL]:
        return event_date, event_date + timedelta(days=1)

    # Try to get start time (prefer set_time, then doors_time)
    start_time = tour_stop.set_time or tour_stop.doors_time

    if start_time:
        # Create datetime with timezone
        start_dt = datetime.combine(event_date, start_time)
        start_dt = DEFAULT_TIMEZONE.localize(start_dt)

        # End time: curfew or +2 hours
        if tour_stop.curfew_time:
            end_dt = datetime.combine(event_date, tour_stop.curfew_time)
            end_dt = DEFAULT_TIMEZONE.localize(end_dt)
            # Handle events that go past midnight
            if end_dt < start_dt:
                end_dt += timedelta(days=1)
        else:
            end_dt = start_dt + timedelta(hours=2)

        return start_dt, end_dt
    else:
        # No time specified - use all-day event
        return event_date, event_date + timedelta(days=1)


def _get_event_category(tour_stop):
    """Get iCal category based on event type."""
    from app.models.tour_stop import EventType

    categories = {
        EventType.SHOW: 'CONCERT',
        EventType.REHEARSAL: 'REHEARSAL',
        EventType.STUDIO: 'RECORDING',
        EventType.PRESS: 'PRESS',
        EventType.PROMO: 'PROMO',
        EventType.PHOTO_VIDEO: 'PRESS',
        EventType.MEET_GREET: 'MEET-GREET',
        EventType.DAY_OFF: 'DAY-OFF',
        EventType.TRAVEL: 'TRAVEL',
        EventType.OTHER: 'OTHER',
    }
    return categories.get(tour_stop.event_type, 'OTHER')


def _get_event_status(tour_stop):
    """Get iCal status based on tour stop status."""
    from app.models.tour_stop import TourStopStatus

    if tour_stop.status == TourStopStatus.CANCELED:
        return 'CANCELLED'
    elif tour_stop.status == TourStopStatus.CONFIRMED:
        return 'CONFIRMED'
    else:
        return 'TENTATIVE'


def _format_time(t):
    """Format time object for display."""
    if t:
        return t.strftime('%H:%M')
    return ''


def generate_tour_ical(tour, include_alarms=True):
    """
    Generate complete iCal calendar for a tour.

    Args:
        tour: Tour model instance with stops loaded
        include_alarms: Whether to add reminders

    Returns:
        bytes: iCal file content
    """
    description = f"Tournée {tour.name}"
    if tour.band:
        description += f" - {tour.band.name}"

    cal = create_calendar(tour.name, description)

    for stop in tour.stops:
        event = create_event(stop, tour, include_alarm=include_alarms)
        cal.add_component(event)

    return cal.to_ical()


def generate_stop_ical(tour_stop, tour=None, include_alarm=True):
    """
    Generate iCal for a single tour stop.

    Args:
        tour_stop: TourStop model instance
        tour: Optional Tour model instance
        include_alarm: Whether to add reminder

    Returns:
        bytes: iCal file content
    """
    if tour is None and tour_stop.tour:
        tour = tour_stop.tour

    name = _build_summary(tour_stop, tour)
    cal = create_calendar(name)

    event = create_event(tour_stop, tour, include_alarm=include_alarm)
    cal.add_component(event)

    return cal.to_ical()


def generate_crew_schedule_ical(tour_stop, user=None):
    """
    Generate iCal for crew schedule of a tour stop.

    Args:
        tour_stop: TourStop model instance
        user: Optional User to filter assignments (shows only their slots)

    Returns:
        bytes: iCal file content
    """
    from app.models.crew_schedule import CrewScheduleSlot, CrewAssignment

    # Get slots (filtered if user provided)
    if user:
        slots = CrewScheduleSlot.query.filter_by(tour_stop_id=tour_stop.id).join(
            CrewAssignment
        ).filter(CrewAssignment.user_id == user.id).all()
        cal_name = f"Mon planning - {tour_stop.venue.name if tour_stop.venue else tour_stop.date}"
    else:
        slots = list(tour_stop.crew_slots)
        cal_name = f"Planning équipe - {tour_stop.venue.name if tour_stop.venue else tour_stop.date}"

    cal = create_calendar(cal_name)

    for slot in slots:
        event = _create_crew_slot_event(slot, tour_stop)
        cal.add_component(event)

    return cal.to_ical()


def _create_crew_slot_event(slot, tour_stop):
    """Create an iCal event for a crew schedule slot."""
    event = Event()

    event.add('uid', f'crewslot-{slot.id}@tourmanager.studiopalenque.com')
    event.add('dtstamp', datetime.now(DEFAULT_TIMEZONE))

    # Summary with category
    category_label = slot.profession_category.value.title() if slot.profession_category else 'Général'
    event.add('summary', f"👷 {slot.task_name} ({category_label})")

    # Date/time
    start_dt = datetime.combine(tour_stop.date, slot.start_time)
    start_dt = DEFAULT_TIMEZONE.localize(start_dt)
    end_dt = datetime.combine(tour_stop.date, slot.end_time)
    end_dt = DEFAULT_TIMEZONE.localize(end_dt)

    # Handle slots that go past midnight
    if end_dt < start_dt:
        end_dt += timedelta(days=1)

    event.add('dtstart', start_dt)
    event.add('dtend', end_dt)

    # Location
    location = build_location(tour_stop)
    if location:
        event.add('location', location)

    # Description with assignments
    lines = [f"Tâche: {slot.task_name}"]
    if slot.task_description:
        lines.append(f"Description: {slot.task_description}")
    lines.append("")
    lines.append("Équipe assignée:")
    for assignment in slot.assignments:
        name = assignment.user.full_name if assignment.user else assignment.external_contact.full_name
        status = "✓" if assignment.status.value == 'confirmed' else "⏳"
        lines.append(f"  {status} {name}")

    event.add('description', '\n'.join(lines))

    # Category
    event.add('categories', ['CREW'])

    # Alarm 1h before
    alarm = Alarm()
    alarm.add('action', 'DISPLAY')
    alarm.add('description', f'Rappel: {slot.task_name}')
    alarm.add('trigger', timedelta(hours=-1))
    event.add_component(alarm)

    return event
