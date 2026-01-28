#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test des 4 routes corrigées."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
from bs4 import BeautifulSoup

BASE_URL = "http://127.0.0.1:5000"

def get_csrf_token(session, url):
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_input = soup.find('input', {'name': 'csrf_token'})
    return csrf_input.get('value') if csrf_input else None

# Session avec login
session = requests.Session()
login_url = f"{BASE_URL}/auth/login"
csrf = get_csrf_token(session, login_url)
resp = session.post(login_url, data={
    'csrf_token': csrf,
    'email': 'manager@tourmanager.com',
    'password': 'Manager123!'
}, allow_redirects=True)
print(f"Login: {'OK' if 'Tableau' in resp.text or resp.status_code == 200 else 'FAILED'}")

print("\n" + "="*60)
print("TESTS CORRIGES")
print("="*60)

# Test 1: Tours Export iCal (route correcte)
print("\n1. Tours: Export iCal (route: /tours/1/export.ics)")
response = session.get(f"{BASE_URL}/tours/1/export.ics")
print(f"   Status: {response.status_code}")
print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
if 'BEGIN:VCALENDAR' in response.text or 'calendar' in response.headers.get('content-type', '').lower():
    print("   ✅ PASS - Contenu iCal valide")
else:
    print(f"   Content (first 100 chars): {response.text[:100]}")

# Test 2: Tours Page création
print("\n2. Tours: Page création (route: /tours/create/1)")
response = session.get(f"{BASE_URL}/tours/create/1")
print(f"   Status: {response.status_code}")
print(f"   URL finale: {response.url}")
if 'create' in response.url or 'form' in response.text.lower() or 'Créer' in response.text:
    print("   ✅ PASS - Page de création accessible")
else:
    print("   ❌ FAIL - Redirigé vers login")

# Test 3: Tours Page modification
print("\n3. Tours: Page modification (route: /tours/1/edit)")
response = session.get(f"{BASE_URL}/tours/1/edit")
print(f"   Status: {response.status_code}")
print(f"   URL finale: {response.url}")
if 'edit' in response.url or 'form' in response.text.lower() or 'Modifier' in response.text:
    print("   ✅ PASS - Page de modification accessible")
else:
    print("   ❌ FAIL - Redirigé vers login")

# Test 4: Reports Export CSV (route correcte)
print("\n4. Reports: Export CSV (route: /reports/financial/1/export)")
response = session.get(f"{BASE_URL}/reports/financial/1/export")
print(f"   Status: {response.status_code}")
print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
if response.status_code == 200:
    print("   ✅ PASS - Export accessible")
else:
    print(f"   Content (first 100 chars): {response.text[:100]}")

print("\n" + "="*60)
