"""
Geocoding service using Nominatim (OpenStreetMap).
Gratuit et sans clé API - parfait pour applications internes.
"""
import time
import logging
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# Nominatim rate limiting: max 1 request per second
_last_request_time = 0


def geocode_address(
    address: str,
    city: str,
    country: str,
    state: Optional[str] = None
) -> Tuple[Optional[float], Optional[float]]:
    """
    Obtenir les coordonnées GPS depuis une adresse via Nominatim (OpenStreetMap).

    Args:
        address: Adresse de rue
        city: Ville
        country: Pays
        state: État/Région (optionnel)

    Returns:
        Tuple (latitude, longitude) ou (None, None) si échec

    Note:
        Respecte le rate limit de Nominatim (1 req/sec).
        User-Agent requis par Nominatim Terms of Service.
    """
    global _last_request_time

    # Build query parts
    query_parts = [p for p in [address, city, state, country] if p]
    query = ', '.join(query_parts)

    if not query:
        logger.warning("Geocoding: empty query")
        return None, None

    # Rate limiting (1 request per second)
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': query,
        'format': 'json',
        'limit': 1,
        'addressdetails': 0
    }
    headers = {
        'User-Agent': 'GigRoute/1.0 (Tour Management Application)',
        'Accept-Language': 'fr,en'
    }

    try:
        _last_request_time = time.time()
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        results = response.json()
        if results:
            result = results[0]
            lat = float(result['lat'])
            lon = float(result['lon'])
            logger.info(f"Geocoded '{query}' -> ({lat}, {lon})")
            return lat, lon
        else:
            logger.warning(f"Geocoding: no results for '{query}'")
            return None, None

    except requests.RequestException as e:
        logger.error(f"Geocoding error for '{query}': {e}")
        return None, None
    except (KeyError, ValueError, IndexError) as e:
        logger.error(f"Geocoding parse error for '{query}': {e}")
        return None, None


def reverse_geocode(
    latitude: float,
    longitude: float
) -> Optional[dict]:
    """
    Obtenir une adresse depuis des coordonnées GPS.

    Args:
        latitude: Latitude
        longitude: Longitude

    Returns:
        Dict avec address, city, country ou None si échec
    """
    global _last_request_time

    # Rate limiting
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        'lat': latitude,
        'lon': longitude,
        'format': 'json',
        'addressdetails': 1
    }
    headers = {
        'User-Agent': 'GigRoute/1.0 (Tour Management Application)',
        'Accept-Language': 'fr,en'
    }

    try:
        _last_request_time = time.time()
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        result = response.json()
        if 'address' in result:
            addr = result['address']
            return {
                'address': addr.get('road', addr.get('house_number', '')),
                'city': addr.get('city', addr.get('town', addr.get('village', ''))),
                'state': addr.get('state', ''),
                'country': addr.get('country', ''),
                'postal_code': addr.get('postcode', ''),
                'display_name': result.get('display_name', '')
            }
        return None

    except requests.RequestException as e:
        logger.error(f"Reverse geocoding error for ({latitude}, {longitude}): {e}")
        return None
    except (KeyError, ValueError) as e:
        logger.error(f"Reverse geocoding parse error: {e}")
        return None


def batch_geocode_venues(venues: list, commit_callback=None) -> dict:
    """
    Géocode plusieurs venues en batch (avec rate limiting).

    Args:
        venues: Liste d'objets Venue à géocoder
        commit_callback: Fonction à appeler après chaque venue pour commit DB

    Returns:
        Dict avec stats: {'success': n, 'failed': n, 'skipped': n}
    """
    stats = {'success': 0, 'failed': 0, 'skipped': 0}

    for venue in venues:
        # Skip if already has coordinates
        if venue.latitude is not None and venue.longitude is not None:
            stats['skipped'] += 1
            continue

        # Try to geocode
        lat, lon = geocode_address(
            venue.address,
            venue.city,
            venue.country,
            venue.state if hasattr(venue, 'state') else None
        )

        if lat is not None and lon is not None:
            venue.latitude = lat
            venue.longitude = lon
            stats['success'] += 1

            # Commit after each successful geocode
            if commit_callback:
                commit_callback()
        else:
            stats['failed'] += 1

    logger.info(f"Batch geocoding complete: {stats}")
    return stats
