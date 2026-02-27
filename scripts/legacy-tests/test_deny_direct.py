#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test DENY by creating pending entry directly in DB."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
os.chdir(r'C:\Claude-Code-Creation\projects\tour-manager')

# Setup Flask app context
from app import create_app
from app.extensions import db
from app.models import GuestlistEntry, TourStop, User
from app.models.guestlist import GuestlistStatus, EntryType

app = create_app()
with app.app_context():
    # Find a stop and manager
    stop = TourStop.query.first()
    manager = User.query.filter_by(email='manager@tourmanager.com').first()

    if not stop or not manager:
        print("❌ Missing stop or manager in database")
        sys.exit(1)

    print(f"Using stop ID: {stop.id}, manager: {manager.email}")

    # Create a pending entry directly (bypassing auto-approval)
    entry = GuestlistEntry(
        tour_stop_id=stop.id,
        guest_name='Test DENY Direct',
        guest_email='denydirect@test.com',
        entry_type=EntryType.GUEST,
        plus_ones=0,
        status=GuestlistStatus.PENDING,  # Force pending
        requested_by_id=manager.id
    )
    db.session.add(entry)
    db.session.commit()

    entry_id = entry.id
    print(f"✅ Created pending entry ID: {entry_id}")
    print(f"   Status: {entry.status.value}")

    # Now test DENY via HTTP
    import requests
    from bs4 import BeautifulSoup

    BASE_URL = "http://127.0.0.1:5000"
    session = requests.Session()

    # Login
    login_url = f"{BASE_URL}/auth/login"
    resp = session.get(login_url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    csrf = soup.find('input', {'name': 'csrf_token'}).get('value')

    session.post(login_url, data={
        'csrf_token': csrf,
        'email': 'manager@tourmanager.com',
        'password': 'Manager123!'
    }, allow_redirects=True)

    # Get fresh CSRF from manage page
    manage_resp = session.get(f"{BASE_URL}/guestlist/stop/{stop.id}")
    soup = BeautifulSoup(manage_resp.text, 'html.parser')
    csrf = soup.find('input', {'name': 'csrf_token'}).get('value')

    # DENY the entry
    deny_url = f"{BASE_URL}/guestlist/entry/{entry_id}/deny"
    deny_resp = session.post(deny_url, data={'csrf_token': csrf}, allow_redirects=True)

    print(f"\n--- DENY TEST ---")
    print(f"DENY URL: {deny_url}")
    print(f"Response Status: {deny_resp.status_code}")

    # Check result in DB
    db.session.refresh(entry)
    print(f"Entry status after DENY: {entry.status.value}")

    if entry.status == GuestlistStatus.DENIED:
        print("✅ DENY SUCCESS - Entry status changed to DENIED")
    else:
        print(f"❌ DENY FAILED - Expected DENIED, got {entry.status.value}")

    # Cleanup
    db.session.delete(entry)
    db.session.commit()
    print("\n✅ Test entry cleaned up")
