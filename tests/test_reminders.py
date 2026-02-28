# =============================================================================
# Tour Manager - Reminders Service Tests
# =============================================================================

import pytest
from datetime import date, time, timedelta
from unittest.mock import patch

from app.extensions import db
from app.models.tour_stop import TourStop, TourStopStatus, EventType
from app.services.reminders import (
    get_stops_needing_j7_reminders,
    get_stops_needing_j1_reminders,
    get_users_for_reminder,
)


class TestJ7Reminders:
    """Tests for get_stops_needing_j7_reminders()."""

    def test_returns_stop_7_days_away(self, app, sample_tour, sample_venue):
        stop = TourStop(
            tour=sample_tour, venue=sample_venue,
            date=date.today() + timedelta(days=7),
            status=TourStopStatus.CONFIRMED,
            event_type=EventType.SHOW,
        )
        db.session.add(stop)
        db.session.commit()

        results = get_stops_needing_j7_reminders()
        assert len(results) >= 1
        assert any(s.id == stop.id for s in results)

    def test_ignores_stop_not_7_days_away(self, app, sample_tour, sample_venue):
        stop = TourStop(
            tour=sample_tour, venue=sample_venue,
            date=date.today() + timedelta(days=3),
            status=TourStopStatus.CONFIRMED,
            event_type=EventType.SHOW,
        )
        db.session.add(stop)
        db.session.commit()

        results = get_stops_needing_j7_reminders()
        assert not any(s.id == stop.id for s in results)

    def test_ignores_cancelled_stop(self, app, sample_tour, sample_venue):
        stop = TourStop(
            tour=sample_tour, venue=sample_venue,
            date=date.today() + timedelta(days=7),
            status=TourStopStatus.CANCELED,
            event_type=EventType.SHOW,
        )
        db.session.add(stop)
        db.session.commit()

        results = get_stops_needing_j7_reminders()
        assert not any(s.id == stop.id for s in results)


class TestJ1Reminders:
    """Tests for get_stops_needing_j1_reminders()."""

    def test_returns_stop_1_day_away(self, app, sample_tour, sample_venue):
        stop = TourStop(
            tour=sample_tour, venue=sample_venue,
            date=date.today() + timedelta(days=1),
            status=TourStopStatus.CONFIRMED,
            event_type=EventType.SHOW,
        )
        db.session.add(stop)
        db.session.commit()

        results = get_stops_needing_j1_reminders()
        assert len(results) >= 1
        assert any(s.id == stop.id for s in results)

    def test_ignores_stop_not_tomorrow(self, app, sample_tour, sample_venue):
        stop = TourStop(
            tour=sample_tour, venue=sample_venue,
            date=date.today() + timedelta(days=5),
            status=TourStopStatus.CONFIRMED,
            event_type=EventType.SHOW,
        )
        db.session.add(stop)
        db.session.commit()

        results = get_stops_needing_j1_reminders()
        assert not any(s.id == stop.id for s in results)


class TestGetUsersForReminder:
    """Tests for get_users_for_reminder()."""

    def test_returns_empty_for_stop_without_band(self, app, sample_tour_stop):
        # Mock associated_band to None
        with patch.object(type(sample_tour_stop), 'associated_band', new_callable=lambda: property(lambda self: None)):
            result = get_users_for_reminder(sample_tour_stop)
            assert result == []

    def test_returns_manager_for_band_with_manager(self, app, sample_tour_stop, manager_user, sample_band):
        """Manager should receive reminder if band has no assigned members."""
        with patch.object(type(sample_tour_stop), 'associated_band', new_callable=lambda: property(lambda self: sample_band)):
            result = get_users_for_reminder(sample_tour_stop)
            assert manager_user in result
