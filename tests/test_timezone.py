# =============================================================================
# Tour Manager - Timezone Utility Tests
# =============================================================================

from app.utils.timezone import (
    get_timezone_for_event,
    is_valid_timezone,
    get_common_timezones,
    DEFAULT_TIMEZONE,
)


class TestIsValidTimezone:
    """Tests for is_valid_timezone()."""

    def test_valid_timezone_europe_paris(self):
        assert is_valid_timezone('Europe/Paris') is True

    def test_valid_timezone_utc(self):
        assert is_valid_timezone('UTC') is True

    def test_valid_timezone_america_new_york(self):
        assert is_valid_timezone('America/New_York') is True

    def test_invalid_timezone_string(self):
        assert is_valid_timezone('Not/A/Timezone') is False

    def test_empty_string_is_invalid(self):
        assert is_valid_timezone('') is False

    def test_none_is_invalid(self):
        assert is_valid_timezone(None) is False


class TestGetTimezoneForEvent:
    """Tests for get_timezone_for_event()."""

    def test_returns_default_when_no_args(self):
        result = get_timezone_for_event()
        assert result == DEFAULT_TIMEZONE

    def test_returns_default_when_none_args(self):
        result = get_timezone_for_event(stop=None, user=None)
        assert result == DEFAULT_TIMEZONE

    def test_returns_venue_timezone_when_available(self):
        class MockVenue:
            timezone = 'America/New_York'
        class MockStop:
            venue = MockVenue()
        result = get_timezone_for_event(stop=MockStop())
        assert result == 'America/New_York'

    def test_returns_user_timezone_when_no_venue(self):
        class MockUser:
            timezone = 'Asia/Tokyo'
        result = get_timezone_for_event(user=MockUser())
        assert result == 'Asia/Tokyo'

    def test_venue_takes_priority_over_user(self):
        class MockVenue:
            timezone = 'Europe/London'
        class MockStop:
            venue = MockVenue()
        class MockUser:
            timezone = 'Asia/Tokyo'
        result = get_timezone_for_event(stop=MockStop(), user=MockUser())
        assert result == 'Europe/London'

    def test_falls_back_to_user_when_venue_tz_invalid(self):
        class MockVenue:
            timezone = 'Invalid/TZ'
        class MockStop:
            venue = MockVenue()
        class MockUser:
            timezone = 'Asia/Tokyo'
        result = get_timezone_for_event(stop=MockStop(), user=MockUser())
        assert result == 'Asia/Tokyo'

    def test_falls_back_to_default_when_both_invalid(self):
        class MockVenue:
            timezone = None
        class MockStop:
            venue = MockVenue()
        class MockUser:
            timezone = ''
        result = get_timezone_for_event(stop=MockStop(), user=MockUser())
        assert result == DEFAULT_TIMEZONE

    def test_stop_without_venue_falls_back(self):
        class MockStop:
            venue = None
        result = get_timezone_for_event(stop=MockStop())
        assert result == DEFAULT_TIMEZONE


class TestGetCommonTimezones:
    """Tests for get_common_timezones()."""

    def test_returns_list(self):
        result = get_common_timezones()
        assert isinstance(result, list)

    def test_returns_tuples(self):
        result = get_common_timezones()
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_contains_paris(self):
        result = get_common_timezones()
        tz_ids = [tz_id for tz_id, _ in result]
        assert 'Europe/Paris' in tz_ids

    def test_contains_utc(self):
        result = get_common_timezones()
        tz_ids = [tz_id for tz_id, _ in result]
        assert 'UTC' in tz_ids

    def test_all_timezones_are_valid(self):
        result = get_common_timezones()
        for tz_id, _ in result:
            assert is_valid_timezone(tz_id), f"{tz_id} is not a valid timezone"
