# =============================================================================
# Tour Manager - Tour Model Tests (State Machine + Properties)
# =============================================================================

import pytest
from datetime import date, timedelta

from app.extensions import db
from app.models.tour import Tour, TourStatus, TOUR_STATUS_TRANSITIONS


# =============================================================================
# State Machine Tests
# =============================================================================

class TestTourStatusTransitions:
    """Tests for Tour status state machine."""

    def test_draft_can_go_to_planning(self, app, sample_band):
        tour = Tour(
            name='SM Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.DRAFT, band=sample_band
        )
        assert tour.can_transition_to(TourStatus.PLANNING) is True

    def test_draft_can_go_to_confirmed(self, app, sample_band):
        tour = Tour(
            name='SM Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.DRAFT, band=sample_band
        )
        assert tour.can_transition_to(TourStatus.CONFIRMED) is True

    def test_draft_can_go_to_cancelled(self, app, sample_band):
        tour = Tour(
            name='SM Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.DRAFT, band=sample_band
        )
        assert tour.can_transition_to(TourStatus.CANCELLED) is True

    def test_draft_cannot_go_to_active(self, app, sample_band):
        tour = Tour(
            name='SM Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.DRAFT, band=sample_band
        )
        assert tour.can_transition_to(TourStatus.ACTIVE) is False

    def test_completed_is_terminal(self, app, sample_band):
        tour = Tour(
            name='SM Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.COMPLETED, band=sample_band
        )
        assert tour.can_transition_to(TourStatus.DRAFT) is False
        assert tour.can_transition_to(TourStatus.ACTIVE) is False

    def test_cancelled_is_terminal(self, app, sample_band):
        tour = Tour(
            name='SM Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.CANCELLED, band=sample_band
        )
        assert tour.can_transition_to(TourStatus.DRAFT) is False

    def test_transition_to_valid_status(self, app, sample_band):
        tour = Tour(
            name='SM Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.DRAFT, band=sample_band
        )
        result = tour.transition_to(TourStatus.PLANNING)
        assert result is True
        assert tour.status == TourStatus.PLANNING

    def test_transition_to_invalid_status_raises(self, app, sample_band):
        tour = Tour(
            name='SM Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.DRAFT, band=sample_band
        )
        with pytest.raises(ValueError, match="Transition invalide"):
            tour.transition_to(TourStatus.COMPLETED)

    def test_start_planning(self, app, sample_band):
        tour = Tour(
            name='SM Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.DRAFT, band=sample_band
        )
        tour.start_planning()
        assert tour.status == TourStatus.PLANNING

    def test_confirm(self, app, sample_band):
        tour = Tour(
            name='SM Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.PLANNING, band=sample_band
        )
        tour.confirm()
        assert tour.status == TourStatus.CONFIRMED

    def test_activate(self, app, sample_band):
        tour = Tour(
            name='SM Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.CONFIRMED, band=sample_band
        )
        tour.activate()
        assert tour.status == TourStatus.ACTIVE

    def test_complete(self, app, sample_band):
        tour = Tour(
            name='SM Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.ACTIVE, band=sample_band
        )
        tour.complete()
        assert tour.status == TourStatus.COMPLETED

    def test_cancel_from_draft(self, app, sample_band):
        tour = Tour(
            name='SM Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.DRAFT, band=sample_band
        )
        tour.cancel()
        assert tour.status == TourStatus.CANCELLED

    def test_cancel_from_completed_raises(self, app, sample_band):
        tour = Tour(
            name='SM Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.COMPLETED, band=sample_band
        )
        with pytest.raises(ValueError, match="Cannot cancel"):
            tour.cancel()

    def test_cancel_from_cancelled_raises(self, app, sample_band):
        tour = Tour(
            name='SM Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.CANCELLED, band=sample_band
        )
        with pytest.raises(ValueError, match="Cannot cancel"):
            tour.cancel()


# =============================================================================
# Properties Tests
# =============================================================================

class TestTourProperties:
    """Tests for Tour computed properties."""

    def test_duration_days(self, sample_tour):
        assert sample_tour.duration_days == 31  # 30 days + 1

    def test_duration_days_same_day(self, app, sample_band):
        tour = Tour(
            name='Same Day', start_date=date.today(),
            end_date=date.today(),
            status=TourStatus.DRAFT, band=sample_band
        )
        assert tour.duration_days == 1

    def test_total_shows(self, sample_tour):
        assert sample_tour.total_shows == 0

    def test_total_shows_with_stops(self, tour_with_multiple_stops):
        assert tour_with_multiple_stops.total_shows == 3

    def test_is_editable_draft(self, app, sample_band):
        tour = Tour(
            name='Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.DRAFT, band=sample_band
        )
        assert tour.is_editable is True

    def test_is_editable_completed(self, app, sample_band):
        tour = Tour(
            name='Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.COMPLETED, band=sample_band
        )
        assert tour.is_editable is False

    def test_is_terminal_completed(self, app, sample_band):
        tour = Tour(
            name='Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.COMPLETED, band=sample_band
        )
        assert tour.is_terminal is True

    def test_is_terminal_draft(self, app, sample_band):
        tour = Tour(
            name='Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.DRAFT, band=sample_band
        )
        assert tour.is_terminal is False

    def test_allowed_transitions_draft(self, app, sample_band):
        tour = Tour(
            name='Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=10),
            status=TourStatus.DRAFT, band=sample_band
        )
        assert TourStatus.PLANNING in tour.allowed_transitions
        assert TourStatus.CONFIRMED in tour.allowed_transitions
        assert TourStatus.CANCELLED in tour.allowed_transitions

    def test_band_name_with_band(self, sample_tour):
        assert sample_tour.band_name == 'Test Band'

    def test_repr(self, sample_tour):
        assert 'Test Tour 2025' in repr(sample_tour)


# =============================================================================
# Duplicate Tests
# =============================================================================

class TestTourDuplicate:
    """Tests for Tour.duplicate()."""

    def test_duplicate_basic(self, sample_tour):
        copy = sample_tour.duplicate()
        assert copy.name == f'{sample_tour.name} (Copy)'
        assert copy.status == TourStatus.DRAFT
        assert copy.band_id == sample_tour.band_id

    def test_duplicate_with_custom_name(self, sample_tour):
        copy = sample_tour.duplicate(new_name='My Copy Tour')
        assert copy.name == 'My Copy Tour'

    def test_duplicate_with_new_start_date(self, sample_tour):
        new_start = date.today() + timedelta(days=60)
        copy = sample_tour.duplicate(new_start_date=new_start)
        assert copy.start_date == new_start

    def test_duplicate_without_stops(self, tour_with_multiple_stops):
        copy = tour_with_multiple_stops.duplicate(include_stops=False)
        assert len(copy.stops) == 0

    def test_duplicate_with_stops(self, tour_with_multiple_stops):
        copy = tour_with_multiple_stops.duplicate(include_stops=True)
        assert len(copy.stops) == 3

    def test_duplicate_stops_reset_to_draft(self, tour_with_multiple_stops):
        from app.models.tour_stop import TourStopStatus
        copy = tour_with_multiple_stops.duplicate()
        for stop in copy.stops:
            assert stop.status == TourStopStatus.DRAFT

    def test_duplicate_preserves_financial_data(self, tour_with_multiple_stops):
        copy = tour_with_multiple_stops.duplicate()
        original_stop = tour_with_multiple_stops.stops[0]
        copy_stop = copy.stops[0]
        assert copy_stop.guarantee == original_stop.guarantee
        assert copy_stop.ticket_price == original_stop.ticket_price


# =============================================================================
# Status Transitions Map Tests
# =============================================================================

class TestStatusTransitionsMap:
    """Tests for TOUR_STATUS_TRANSITIONS constant."""

    def test_all_statuses_have_entry(self):
        for status in TourStatus:
            assert status in TOUR_STATUS_TRANSITIONS

    def test_terminal_states_have_no_transitions(self):
        assert TOUR_STATUS_TRANSITIONS[TourStatus.COMPLETED] == []
        assert TOUR_STATUS_TRANSITIONS[TourStatus.CANCELLED] == []
