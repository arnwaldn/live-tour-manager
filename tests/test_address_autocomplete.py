#!/usr/bin/env python
"""
Test Address Autocomplete - International Support
Tests API Adresse (France) and Geoapify (International)
"""

import requests
import os
import sys
from dotenv import load_dotenv

# Load .env from project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, '.env'))

# APIs
API_ADRESSE_FR = 'https://api-adresse.data.gouv.fr/search/'
GEOAPIFY_API = 'https://api.geoapify.com/v1/geocode/autocomplete'
GEOAPIFY_KEY = os.environ.get('GEOAPIFY_API_KEY')

# Test cases
TEST_CASES = [
    {
        'name': 'France - Paris',
        'query': '45 rue de rivoli, Paris',
        'country': 'FR',
        'api': 'API Adresse',
        'expected_city': 'Paris'
    },
    {
        'name': 'Allemagne - Berlin',
        'query': 'Alexanderplatz, Berlin',
        'country': 'DE',
        'api': 'Geoapify',
        'expected_city': 'Berlin'
    },
    {
        'name': 'USA - New York',
        'query': 'Times Square, New York',
        'country': 'US',
        'api': 'Geoapify',
        'expected_city': 'New York'
    },
    {
        'name': 'UK - London',
        'query': 'Abbey Road, London',
        'country': 'GB',
        'api': 'Geoapify',
        'expected_city': 'London'
    }
]


def test_api_adresse(query: str, limit: int = 5) -> dict:
    """Test API Adresse (France)"""
    params = {
        'q': query,
        'limit': limit,
        'autocomplete': 1
    }

    response = requests.get(API_ADRESSE_FR, params=params)
    response.raise_for_status()

    data = response.json()
    results = []

    for feature in data.get('features', []):
        props = feature.get('properties', {})
        coords = feature.get('geometry', {}).get('coordinates', [None, None])

        results.append({
            'display_name': props.get('label', ''),
            'city': props.get('city', ''),
            'postal_code': props.get('postcode', ''),
            'country': 'France',
            'latitude': coords[1],
            'longitude': coords[0]
        })

    return {
        'success': len(results) > 0,
        'count': len(results),
        'results': results
    }


def test_geoapify(query: str, country_code: str = None, limit: int = 5) -> dict:
    """Test Geoapify (International)"""
    if not GEOAPIFY_KEY:
        return {
            'success': False,
            'error': 'GEOAPIFY_API_KEY not configured',
            'count': 0,
            'results': []
        }

    params = {
        'text': query,
        'limit': limit,
        'apiKey': GEOAPIFY_KEY,
        'format': 'json',
        'lang': 'fr'
    }

    if country_code and country_code != 'ALL':
        params['filter'] = f'countrycode:{country_code.lower()}'

    response = requests.get(GEOAPIFY_API, params=params)
    response.raise_for_status()

    data = response.json()
    results = []

    for feature in data.get('results', []):
        results.append({
            'display_name': feature.get('formatted', ''),
            'city': feature.get('city', feature.get('town', feature.get('village', ''))),
            'postal_code': feature.get('postcode', ''),
            'country': feature.get('country', ''),
            'latitude': feature.get('lat'),
            'longitude': feature.get('lon')
        })

    return {
        'success': len(results) > 0,
        'count': len(results),
        'results': results
    }


def run_tests():
    """Run all test cases"""
    print("=" * 70)
    print("TEST: Autocompletion d'adresses internationales")
    print("=" * 70)
    print()

    # Check Geoapify key
    if GEOAPIFY_KEY:
        print(f"[OK] Geoapify API Key: {GEOAPIFY_KEY[:10]}...")
    else:
        print("[WARN] Geoapify API Key not configured - International tests will fail")
    print()

    all_passed = True

    for test in TEST_CASES:
        print(f"--- {test['name']} ---")
        print(f"Query: {test['query']}")
        print(f"Country: {test['country']}")
        print(f"API: {test['api']}")

        try:
            if test['country'] == 'FR':
                result = test_api_adresse(test['query'])
            else:
                result = test_geoapify(test['query'], test['country'])

            if result['success']:
                print(f"[PASS] {result['count']} suggestions found")

                # Show first result
                if result['results']:
                    first = result['results'][0]
                    print(f"  First result: {first['display_name']}")
                    print(f"  City: {first['city']}")

                    if first['latitude'] and first['longitude']:
                        print(f"  GPS: {first['latitude']:.6f}, {first['longitude']:.6f}")
                        print(f"  [OK] Coordinates available")
                    else:
                        print(f"  [WARN] No coordinates")
            else:
                print(f"[FAIL] No results - {result.get('error', 'Unknown error')}")
                all_passed = False

        except Exception as e:
            print(f"[ERROR] {str(e)}")
            all_passed = False

        print()

    print("=" * 70)
    if all_passed:
        print("RESULT: All tests PASSED")
        return 0
    else:
        print("RESULT: Some tests FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())
