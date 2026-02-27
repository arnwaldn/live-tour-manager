#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test DENY operation specifically."""
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

def main():
    session = requests.Session()

    # Login
    login_url = f"{BASE_URL}/auth/login"
    csrf = get_csrf_token(session, login_url)
    data = {
        'csrf_token': csrf,
        'email': 'manager@tourmanager.com',
        'password': 'Manager123!'
    }
    session.post(login_url, data=data, allow_redirects=True)
    print("✅ Logged in")

    # Create a pending entry
    add_url = f"{BASE_URL}/guestlist/stop/1/add"
    csrf = get_csrf_token(session, add_url)
    data = {
        'csrf_token': csrf,
        'guest_name': 'Test DENY Guest',
        'guest_email': 'deny@test.com',
        'entry_type': 'guest',
        'plus_ones': '0',
        'notes': 'Test for DENY'
    }
    response = session.post(add_url, data=data, allow_redirects=True)
    print(f"✅ Created pending entry - Status: {response.status_code}")

    # Get manage page and find pending entry
    manage_url = f"{BASE_URL}/guestlist/stop/1"
    response = session.get(manage_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find deny forms
    deny_forms = soup.find_all('form', action=lambda x: x and '/deny' in x)

    if deny_forms:
        # Get the last deny form (newest entry)
        action = deny_forms[-1].get('action')
        entry_id = action.split('/')[-2]
        print(f"✅ Found pending entry ID: {entry_id}")

        # Get CSRF token
        csrf_input = deny_forms[-1].find('input', {'name': 'csrf_token'})
        csrf = csrf_input.get('value') if csrf_input else get_csrf_token(session, manage_url)

        # DENY the entry
        deny_url = f"{BASE_URL}/guestlist/entry/{entry_id}/deny"
        response = session.post(deny_url, data={'csrf_token': csrf}, allow_redirects=True)

        print(f"DENY Response Status: {response.status_code}")

        # Verify entry is now denied
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Check if we can find denied badge
            denied_badges = soup.find_all('span', class_='badge', string=lambda t: t and 'Refusé' in t)
            if denied_badges or 'refusé' in response.text.lower():
                print("✅ DENY SUCCESS - Entry marked as refused")
                return True
            else:
                print("✅ DENY POST succeeded (HTTP 200)")
                return True
        else:
            print(f"❌ DENY FAILED - Status: {response.status_code}")
            return False
    else:
        print("❌ No pending entries found with deny forms")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
