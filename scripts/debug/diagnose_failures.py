#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Diagnose the 4 failing tests."""
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

def login(session):
    login_url = f"{BASE_URL}/auth/login"
    csrf = get_csrf_token(session, login_url)
    session.post(login_url, data={
        'csrf_token': csrf,
        'email': 'manager@tourmanager.com',
        'password': 'Manager123!'
    }, allow_redirects=True)

session = requests.Session()
login(session)

print("="*60)
print("DIAGNOSTIC DES 4 TESTS ECHOUES")
print("="*60)

# Test 1: Tours Export iCal
print("\n1. Tours: Export iCal")
response = session.get(f"{BASE_URL}/tours/1/ical")
print(f"   Status: {response.status_code}")
print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
print(f"   Content (first 200 chars): {response.text[:200]}")

# Test 2: Tours Page création
print("\n2. Tours: Page création")
response = session.get(f"{BASE_URL}/tours/create/1")
print(f"   Status: {response.status_code}")
print(f"   URL finale: {response.url}")
if response.status_code != 200:
    print(f"   Content: {response.text[:300]}")

# Test 3: Tours Page modification
print("\n3. Tours: Page modification")
response = session.get(f"{BASE_URL}/tours/1/edit")
print(f"   Status: {response.status_code}")
print(f"   URL finale: {response.url}")
if response.status_code != 200:
    print(f"   Content: {response.text[:300]}")

# Test 4: Reports Export CSV
print("\n4. Reports: Export CSV")
response = session.get(f"{BASE_URL}/reports/export/csv/1")
print(f"   Status: {response.status_code}")
print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
print(f"   Content (first 200 chars): {response.text[:200]}")

print("\n" + "="*60)
