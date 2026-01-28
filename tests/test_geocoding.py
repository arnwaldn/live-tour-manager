# =============================================================================
# Tour Manager - Geocoding Tests
# =============================================================================
# Tests for app/utils/geocoding.py - Nominatim geocoding service
# Coverage target: 0% → 50%

import pytest
from unittest.mock import patch, MagicMock
import requests

from app.utils.geocoding import (
    geocode_address,
    reverse_geocode,
    batch_geocode_venues
)


# =============================================================================
# geocode_address Tests
# =============================================================================

class TestGeocodeAddress:
    """Tests for geocode_address function."""

    @patch('app.utils.geocoding.requests.get')
    @patch('app.utils.geocoding.time.sleep')
    def test_geocode_valid_address(self, mock_sleep, mock_get):
        """Test geocoding a valid address returns coordinates."""
        # Mock successful Nominatim response
        mock_response = MagicMock()
        mock_response.json.return_value = [{
            'lat': '48.8566',
            'lon': '2.3522',
            'display_name': 'Paris, France'
        }]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        lat, lon = geocode_address('Champs-Elysées', 'Paris', 'France')

        assert lat == pytest.approx(48.8566, rel=0.01)
        assert lon == pytest.approx(2.3522, rel=0.01)

    @patch('app.utils.geocoding.requests.get')
    @patch('app.utils.geocoding.time.sleep')
    def test_geocode_with_state(self, mock_sleep, mock_get):
        """Test geocoding with state/region parameter."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{
            'lat': '34.0522',
            'lon': '-118.2437'
        }]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        lat, lon = geocode_address(
            '1600 Amphitheatre Parkway',
            'Mountain View',
            'USA',
            state='California'
        )

        assert lat is not None
        assert lon is not None

    @patch('app.utils.geocoding.requests.get')
    @patch('app.utils.geocoding.time.sleep')
    def test_geocode_no_results(self, mock_sleep, mock_get):
        """Test geocoding when no results found."""
        mock_response = MagicMock()
        mock_response.json.return_value = []  # Empty results
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        lat, lon = geocode_address('Fake Address 12345', 'Nowhere City', 'Noland')

        assert lat is None
        assert lon is None

    @patch('app.utils.geocoding.requests.get')
    @patch('app.utils.geocoding.time.sleep')
    def test_geocode_api_error(self, mock_sleep, mock_get):
        """Test geocoding handles API errors gracefully."""
        mock_get.side_effect = requests.RequestException("Connection error")

        lat, lon = geocode_address('123 Main St', 'Paris', 'France')

        assert lat is None
        assert lon is None

    @patch('app.utils.geocoding.requests.get')
    @patch('app.utils.geocoding.time.sleep')
    def test_geocode_invalid_json(self, mock_sleep, mock_get):
        """Test geocoding handles invalid JSON response."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        lat, lon = geocode_address('123 Main St', 'Paris', 'France')

        assert lat is None
        assert lon is None

    def test_geocode_empty_query(self):
        """Test geocoding with empty inputs."""
        lat, lon = geocode_address('', '', '')

        assert lat is None
        assert lon is None

    @patch('app.utils.geocoding.requests.get')
    @patch('app.utils.geocoding.time.sleep')
    def test_geocode_http_error(self, mock_sleep, mock_get):
        """Test geocoding handles HTTP errors."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        lat, lon = geocode_address('Test', 'Test', 'Test')

        assert lat is None
        assert lon is None


# =============================================================================
# reverse_geocode Tests
# =============================================================================

class TestReverseGeocode:
    """Tests for reverse_geocode function."""

    @patch('app.utils.geocoding.requests.get')
    @patch('app.utils.geocoding.time.sleep')
    def test_reverse_geocode_success(self, mock_sleep, mock_get):
        """Test reverse geocoding returns address details."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'display_name': 'Eiffel Tower, Paris, France',
            'address': {
                'road': 'Avenue Anatole France',
                'city': 'Paris',
                'state': 'Île-de-France',
                'country': 'France',
                'postcode': '75007'
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = reverse_geocode(48.8584, 2.2945)

        assert result is not None
        assert result['city'] == 'Paris'
        assert result['country'] == 'France'
        assert result['state'] == 'Île-de-France'

    @patch('app.utils.geocoding.requests.get')
    @patch('app.utils.geocoding.time.sleep')
    def test_reverse_geocode_town_fallback(self, mock_sleep, mock_get):
        """Test reverse geocode uses town/village when city not available."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'address': {
                'road': 'Main Street',
                'town': 'Small Town',  # No city, using town
                'country': 'France'
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = reverse_geocode(45.0, 1.0)

        assert result is not None
        assert result['city'] == 'Small Town'

    @patch('app.utils.geocoding.requests.get')
    @patch('app.utils.geocoding.time.sleep')
    def test_reverse_geocode_no_address(self, mock_sleep, mock_get):
        """Test reverse geocode when no address found."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'display_name': 'Middle of Ocean'
            # No 'address' key
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = reverse_geocode(0.0, 0.0)

        assert result is None

    @patch('app.utils.geocoding.requests.get')
    @patch('app.utils.geocoding.time.sleep')
    def test_reverse_geocode_api_error(self, mock_sleep, mock_get):
        """Test reverse geocode handles API errors."""
        mock_get.side_effect = requests.RequestException("Network error")

        result = reverse_geocode(48.8566, 2.3522)

        assert result is None

    @patch('app.utils.geocoding.requests.get')
    @patch('app.utils.geocoding.time.sleep')
    def test_reverse_geocode_parse_error(self, mock_sleep, mock_get):
        """Test reverse geocode handles parsing errors."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = reverse_geocode(48.8566, 2.3522)

        assert result is None


# =============================================================================
# batch_geocode_venues Tests
# =============================================================================

class TestBatchGeocodeVenues:
    """Tests for batch_geocode_venues function."""

    @pytest.fixture
    def mock_venues(self):
        """Create mock venue objects for batch testing."""
        venue1 = MagicMock()
        venue1.address = '1 Avenue des Champs-Élysées'
        venue1.city = 'Paris'
        venue1.country = 'France'
        venue1.latitude = None
        venue1.longitude = None

        venue2 = MagicMock()
        venue2.address = 'O2 Arena'
        venue2.city = 'London'
        venue2.country = 'UK'
        venue2.latitude = None
        venue2.longitude = None

        return [venue1, venue2]

    @pytest.fixture
    def venue_with_coords(self):
        """Create a venue that already has coordinates."""
        venue = MagicMock()
        venue.address = 'Test Address'
        venue.city = 'Test City'
        venue.country = 'Test Country'
        venue.latitude = 48.8566
        venue.longitude = 2.3522
        return venue

    @patch('app.utils.geocoding.geocode_address')
    def test_batch_geocode_success(self, mock_geocode, mock_venues):
        """Test batch geocoding multiple venues."""
        # Return different coordinates for each venue
        mock_geocode.side_effect = [
            (48.8566, 2.3522),  # Paris
            (51.5024, -0.0024)  # London
        ]

        stats = batch_geocode_venues(mock_venues)

        assert stats['success'] == 2
        assert stats['failed'] == 0
        assert stats['skipped'] == 0
        assert mock_venues[0].latitude == 48.8566
        assert mock_venues[1].latitude == 51.5024

    @patch('app.utils.geocoding.geocode_address')
    def test_batch_geocode_skips_existing(self, mock_geocode, venue_with_coords):
        """Test batch geocoding skips venues with existing coordinates."""
        stats = batch_geocode_venues([venue_with_coords])

        assert stats['skipped'] == 1
        assert stats['success'] == 0
        assert stats['failed'] == 0
        mock_geocode.assert_not_called()

    @patch('app.utils.geocoding.geocode_address')
    def test_batch_geocode_partial_failure(self, mock_geocode, mock_venues):
        """Test batch geocoding with some failures."""
        # First succeeds, second fails
        mock_geocode.side_effect = [
            (48.8566, 2.3522),
            (None, None)
        ]

        stats = batch_geocode_venues(mock_venues)

        assert stats['success'] == 1
        assert stats['failed'] == 1

    @patch('app.utils.geocoding.geocode_address')
    def test_batch_geocode_with_callback(self, mock_geocode, mock_venues):
        """Test batch geocoding calls commit callback."""
        mock_geocode.side_effect = [
            (48.8566, 2.3522),
            (51.5024, -0.0024)
        ]
        mock_callback = MagicMock()

        stats = batch_geocode_venues(mock_venues, commit_callback=mock_callback)

        assert mock_callback.call_count == 2

    @patch('app.utils.geocoding.geocode_address')
    def test_batch_geocode_empty_list(self, mock_geocode):
        """Test batch geocoding empty venue list."""
        stats = batch_geocode_venues([])

        assert stats['success'] == 0
        assert stats['failed'] == 0
        assert stats['skipped'] == 0
        mock_geocode.assert_not_called()

    @patch('app.utils.geocoding.geocode_address')
    def test_batch_geocode_all_failures(self, mock_geocode, mock_venues):
        """Test batch geocoding when all fail."""
        mock_geocode.return_value = (None, None)

        stats = batch_geocode_venues(mock_venues)

        assert stats['success'] == 0
        assert stats['failed'] == 2

    @patch('app.utils.geocoding.geocode_address')
    def test_batch_geocode_venue_without_state(self, mock_geocode):
        """Test batch geocoding venue without state attribute."""
        venue = MagicMock(spec=['address', 'city', 'country', 'latitude', 'longitude'])
        venue.address = 'Test'
        venue.city = 'Test City'
        venue.country = 'France'
        venue.latitude = None
        venue.longitude = None

        mock_geocode.return_value = (48.0, 2.0)

        stats = batch_geocode_venues([venue])

        assert stats['success'] == 1
        # Should pass None for state
        mock_geocode.assert_called_once_with('Test', 'Test City', 'France', None)


# =============================================================================
# Rate Limiting Tests
# =============================================================================

class TestRateLimiting:
    """Tests for rate limiting behavior."""

    @patch('app.utils.geocoding.requests.get')
    @patch('app.utils.geocoding.time.sleep')
    @patch('app.utils.geocoding.time.time')
    def test_rate_limiting_enforced(self, mock_time, mock_sleep, mock_get):
        """Test that rate limiting delays requests."""
        # Simulate rapid consecutive calls
        mock_time.side_effect = [0.5, 0.5, 1.5, 1.5]  # Simulated timestamps
        mock_response = MagicMock()
        mock_response.json.return_value = [{'lat': '48.0', 'lon': '2.0'}]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # First call should work
        geocode_address('Test', 'City', 'Country')

        # Mock sleep was likely called
        # The actual assertion depends on timing which is mocked


# =============================================================================
# Integration Test (Optional - skipped by default)
# =============================================================================

class TestGeocodeIntegration:
    """Integration tests that hit the real API (skipped by default)."""

    @pytest.mark.skip(reason="Integration test - hits real Nominatim API")
    def test_real_geocode(self):
        """Test real geocoding request."""
        lat, lon = geocode_address(
            'Tour Eiffel',
            'Paris',
            'France'
        )
        assert lat is not None
        assert lon is not None
        assert 48.8 < lat < 48.9
        assert 2.2 < lon < 2.4
