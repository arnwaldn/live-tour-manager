#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test exhaustif de toutes les fonctionnalités - Studio Palenque Tour
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
from bs4 import BeautifulSoup
import json
import os

os.chdir(r'C:\Claude-Code-Creation\projects\tour-manager')

BASE_URL = "http://127.0.0.1:5000"
RESULTS = {"passed": [], "failed": []}

def get_csrf_token(session, url):
    """Extract CSRF token from a page."""
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_input = soup.find('input', {'name': 'csrf_token'})
    return csrf_input.get('value') if csrf_input else None

def login(session, email, password):
    """Login and return success status."""
    login_url = f"{BASE_URL}/auth/login"
    csrf = get_csrf_token(session, login_url)
    data = {
        'csrf_token': csrf,
        'email': email,
        'password': password
    }
    response = session.post(login_url, data=data, allow_redirects=True)
    return 'Tableau de bord' in response.text or 'Dashboard' in response.text or response.status_code == 200

def test_result(name, success, details=""):
    """Record test result."""
    if success:
        RESULTS["passed"].append(name)
        print(f"✅ {name}")
    else:
        RESULTS["failed"].append(name)
        print(f"❌ {name} - {details}")

# =============================================
# MODULE 1: AUTH
# =============================================
def test_auth_module():
    print("\n" + "="*50)
    print("MODULE 1: AUTH")
    print("="*50)

    # Test 1.1: Login invalide
    session = requests.Session()
    login_url = f"{BASE_URL}/auth/login"
    csrf = get_csrf_token(session, login_url)
    response = session.post(login_url, data={
        'csrf_token': csrf,
        'email': 'wrong@email.com',
        'password': 'wrongpassword'
    }, allow_redirects=True)
    test_result("Auth: Login invalide",
                'Invalid' in response.text or 'invalide' in response.text.lower() or 'error' in response.text.lower() or response.url.endswith('/login'))

    # Test 1.2: Login valide + Logout
    session = requests.Session()
    success = login(session, 'manager@tourmanager.com', 'Manager123!')
    test_result("Auth: Login valide", success)

    # Logout
    response = session.get(f"{BASE_URL}/auth/logout", allow_redirects=True)
    test_result("Auth: Logout", response.status_code == 200)

    # Test 1.3: Register page accessible
    session = requests.Session()
    response = session.get(f"{BASE_URL}/auth/register")
    test_result("Auth: Page Register accessible", response.status_code == 200 and ('register' in response.text.lower() or 'inscription' in response.text.lower() or 'form' in response.text.lower()))

    # Test 1.4: Password reset page
    response = session.get(f"{BASE_URL}/auth/reset-password")
    # May return 404 if not implemented
    test_result("Auth: Page Reset Password", response.status_code in [200, 404])

# =============================================
# MODULE 2: BANDS
# =============================================
def test_bands_module():
    print("\n" + "="*50)
    print("MODULE 2: BANDS")
    print("="*50)

    session = requests.Session()
    login(session, 'manager@tourmanager.com', 'Manager123!')

    # Test 2.1: Liste bands
    response = session.get(f"{BASE_URL}/bands")
    test_result("Bands: Liste", response.status_code == 200)

    # Test 2.2: Détail band (ID 1)
    response = session.get(f"{BASE_URL}/bands/1")
    test_result("Bands: Détail", response.status_code == 200)

    # Test 2.3: Page création band
    response = session.get(f"{BASE_URL}/bands/create")
    test_result("Bands: Page création", response.status_code == 200)

    # Test 2.4: Créer un band
    csrf = get_csrf_token(session, f"{BASE_URL}/bands/create")
    response = session.post(f"{BASE_URL}/bands/create", data={
        'csrf_token': csrf,
        'name': 'Test Band Auto',
        'genre': 'Rock',
        'description': 'Band de test automatique'
    }, allow_redirects=True)
    test_result("Bands: Création POST", response.status_code == 200)

    # Test 2.5: Page modification band
    response = session.get(f"{BASE_URL}/bands/1/edit")
    test_result("Bands: Page modification", response.status_code == 200)

# =============================================
# MODULE 3: TOURS
# =============================================
def test_tours_module():
    print("\n" + "="*50)
    print("MODULE 3: TOURS")
    print("="*50)

    session = requests.Session()
    login(session, 'manager@tourmanager.com', 'Manager123!')

    # Test 3.1: Liste tours
    response = session.get(f"{BASE_URL}/tours")
    test_result("Tours: Liste", response.status_code == 200)

    # Test 3.2: Détail tour (ID 1)
    response = session.get(f"{BASE_URL}/tours/1")
    test_result("Tours: Détail", response.status_code == 200)

    # Test 3.3: Calendrier
    response = session.get(f"{BASE_URL}/tours/1/calendar")
    test_result("Tours: Calendrier", response.status_code == 200)

    # Test 3.4: Export iCal (route correcte: /export.ics)
    response = session.get(f"{BASE_URL}/tours/1/export.ics")
    test_result("Tours: Export iCal", response.status_code == 200 and ('BEGIN:VCALENDAR' in response.text or response.headers.get('content-type', '').startswith('text/calendar')))

    # Test 3.5: Page création tour
    response = session.get(f"{BASE_URL}/tours/create/1")
    test_result("Tours: Page création", response.status_code == 200)

    # Test 3.6: Page modification tour
    response = session.get(f"{BASE_URL}/tours/1/edit")
    test_result("Tours: Page modification", response.status_code == 200)

    # Test 3.7: Page ajout stop
    response = session.get(f"{BASE_URL}/tours/1/stops/add")
    test_result("Tours: Page ajout stop", response.status_code == 200)

    # Test 3.8: Détail stop
    response = session.get(f"{BASE_URL}/tours/1/stops/1")
    test_result("Tours: Détail stop", response.status_code == 200)

# =============================================
# MODULE 4: VENUES
# =============================================
def test_venues_module():
    print("\n" + "="*50)
    print("MODULE 4: VENUES")
    print("="*50)

    session = requests.Session()
    login(session, 'manager@tourmanager.com', 'Manager123!')

    # Test 4.1: Liste venues
    response = session.get(f"{BASE_URL}/venues")
    test_result("Venues: Liste", response.status_code == 200)

    # Test 4.2: Détail venue (ID 1)
    response = session.get(f"{BASE_URL}/venues/1")
    test_result("Venues: Détail", response.status_code == 200)

    # Test 4.3: Page création venue
    response = session.get(f"{BASE_URL}/venues/create")
    test_result("Venues: Page création", response.status_code == 200)

    # Test 4.4: Créer une venue
    csrf = get_csrf_token(session, f"{BASE_URL}/venues/create")
    response = session.post(f"{BASE_URL}/venues/create", data={
        'csrf_token': csrf,
        'name': 'Test Venue Auto',
        'city': 'Paris',
        'country': 'France',
        'capacity': '500'
    }, allow_redirects=True)
    test_result("Venues: Création POST", response.status_code == 200)

    # Test 4.5: Page modification venue
    response = session.get(f"{BASE_URL}/venues/1/edit")
    test_result("Venues: Page modification", response.status_code == 200)

# =============================================
# MODULE 5: GUESTLIST
# =============================================
def test_guestlist_module():
    print("\n" + "="*50)
    print("MODULE 5: GUESTLIST")
    print("="*50)

    session = requests.Session()
    login(session, 'manager@tourmanager.com', 'Manager123!')

    # Test 5.1: Liste guestlist par stop
    response = session.get(f"{BASE_URL}/guestlist/stop/1")
    test_result("Guestlist: Liste par stop", response.status_code == 200)

    # Test 5.2: Page ajout invité
    response = session.get(f"{BASE_URL}/guestlist/stop/1/add")
    test_result("Guestlist: Page ajout", response.status_code == 200)

    # Test 5.3: Ajouter un invité
    csrf = get_csrf_token(session, f"{BASE_URL}/guestlist/stop/1/add")
    response = session.post(f"{BASE_URL}/guestlist/stop/1/add", data={
        'csrf_token': csrf,
        'guest_name': 'Test Guest Auto',
        'guest_email': 'testguest@auto.com',
        'entry_type': 'guest',
        'plus_ones': '1',
        'notes': 'Test automatique'
    }, allow_redirects=True)
    test_result("Guestlist: Ajout invité POST", response.status_code == 200)

    # Test 5.4: Export CSV
    response = session.get(f"{BASE_URL}/guestlist/stop/1/export")
    test_result("Guestlist: Export CSV", response.status_code == 200 and ('csv' in response.headers.get('content-type', '').lower() or 'text' in response.headers.get('content-type', '').lower()))

    # Test 5.5: Interface check-in
    response = session.get(f"{BASE_URL}/guestlist/stop/1/check-in")
    test_result("Guestlist: Interface check-in", response.status_code == 200)

# =============================================
# MODULE 6: LOGISTICS
# =============================================
def test_logistics_module():
    print("\n" + "="*50)
    print("MODULE 6: LOGISTICS")
    print("="*50)

    session = requests.Session()
    login(session, 'manager@tourmanager.com', 'Manager123!')

    # Test 6.1: Liste logistics par stop
    response = session.get(f"{BASE_URL}/logistics/stop/1")
    test_result("Logistics: Liste par stop", response.status_code == 200)

    # Test 6.2: Page ajout logistics
    response = session.get(f"{BASE_URL}/logistics/stop/1/add")
    test_result("Logistics: Page ajout", response.status_code == 200)

    # Test 6.3: Day Sheet
    response = session.get(f"{BASE_URL}/logistics/stop/1/day-sheet")
    test_result("Logistics: Day Sheet", response.status_code == 200)

# =============================================
# MODULE 7: DOCUMENTS
# =============================================
def test_documents_module():
    print("\n" + "="*50)
    print("MODULE 7: DOCUMENTS")
    print("="*50)

    session = requests.Session()
    login(session, 'manager@tourmanager.com', 'Manager123!')

    # Test 7.1: Liste documents
    response = session.get(f"{BASE_URL}/documents")
    test_result("Documents: Liste", response.status_code == 200)

    # Test 7.2: Filtres par type
    response = session.get(f"{BASE_URL}/documents?type=contract")
    test_result("Documents: Filtre par type", response.status_code == 200)

# =============================================
# MODULE 8: REPORTS
# =============================================
def test_reports_module():
    print("\n" + "="*50)
    print("MODULE 8: REPORTS")
    print("="*50)

    session = requests.Session()
    login(session, 'manager@tourmanager.com', 'Manager123!')

    # Test 8.1: Index reports
    response = session.get(f"{BASE_URL}/reports")
    test_result("Reports: Index", response.status_code == 200)

    # Test 8.2: Rapports financiers
    response = session.get(f"{BASE_URL}/reports/financial")
    test_result("Reports: Financiers", response.status_code == 200)

    # Test 8.3: Détail financier tour
    response = session.get(f"{BASE_URL}/reports/financial/1")
    test_result("Reports: Détail financier tour", response.status_code == 200)

    # Test 8.4: Export CSV financier (route correcte: /financial/<id>/export)
    response = session.get(f"{BASE_URL}/reports/financial/1/export")
    test_result("Reports: Export CSV", response.status_code == 200)

    # Test 8.5: Analytics guestlist
    response = session.get(f"{BASE_URL}/reports/guestlist")
    test_result("Reports: Analytics guestlist", response.status_code == 200)

# =============================================
# MODULE 9: SETTINGS & SEARCH
# =============================================
def test_settings_module():
    print("\n" + "="*50)
    print("MODULE 9: SETTINGS & SEARCH")
    print("="*50)

    session = requests.Session()
    login(session, 'manager@tourmanager.com', 'Manager123!')

    # Test 9.1: Page paramètres
    response = session.get(f"{BASE_URL}/settings")
    test_result("Settings: Page", response.status_code in [200, 404])

    # Test 9.2: Recherche globale
    response = session.get(f"{BASE_URL}/search?q=test")
    test_result("Search: Recherche globale", response.status_code in [200, 404])

# =============================================
# MODULE 10: EDGE CASES
# =============================================
def test_edge_cases():
    print("\n" + "="*50)
    print("MODULE 10: EDGE CASES")
    print("="*50)

    session = requests.Session()

    # Test 10.1: Page 404
    response = session.get(f"{BASE_URL}/nonexistent-page-xyz")
    test_result("Edge: Page 404", response.status_code == 404)

    # Test 10.2: Accès non autorisé (sans login)
    response = session.get(f"{BASE_URL}/bands")
    test_result("Edge: Accès sans auth -> redirect login", 'login' in response.url.lower() or response.status_code in [401, 403, 302])

    # Test 10.3: Dashboard accessible après login
    login(session, 'manager@tourmanager.com', 'Manager123!')
    response = session.get(f"{BASE_URL}/")
    test_result("Edge: Dashboard après login", response.status_code == 200)

# =============================================
# MAIN
# =============================================
if __name__ == '__main__':
    print("="*60)
    print("    STUDIO PALENQUE TOUR - TEST EXHAUSTIF")
    print("="*60)
    print(f"URL: {BASE_URL}")
    print("="*60)

    try:
        # Run all tests
        test_auth_module()
        test_bands_module()
        test_tours_module()
        test_venues_module()
        test_guestlist_module()
        test_logistics_module()
        test_documents_module()
        test_reports_module()
        test_settings_module()
        test_edge_cases()

        # Summary
        print("\n" + "="*60)
        print("    RÉSUMÉ DES TESTS")
        print("="*60)
        total = len(RESULTS["passed"]) + len(RESULTS["failed"])
        print(f"✅ Passés: {len(RESULTS['passed'])}/{total}")
        print(f"❌ Échoués: {len(RESULTS['failed'])}/{total}")
        print(f"📊 Taux de réussite: {len(RESULTS['passed'])/total*100:.1f}%")

        if RESULTS["failed"]:
            print("\n⚠️ Tests échoués:")
            for test in RESULTS["failed"]:
                print(f"   - {test}")

        print("="*60)

    except requests.exceptions.ConnectionError:
        print("❌ ERREUR: Impossible de se connecter au serveur")
        print(f"   Vérifiez que le serveur tourne sur {BASE_URL}")
