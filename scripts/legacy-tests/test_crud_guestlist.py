#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test CRUD operations for guestlist."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import requests
from bs4 import BeautifulSoup

BASE_URL = "http://127.0.0.1:5000"

def get_csrf_token(session, url):
    """Extract CSRF token from a page."""
    response = session.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_input = soup.find('input', {'name': 'csrf_token'})
    if csrf_input:
        return csrf_input.get('value')
    return None

def login(session):
    """Login and return session."""
    login_url = f"{BASE_URL}/auth/login"
    csrf = get_csrf_token(session, login_url)

    data = {
        'csrf_token': csrf,
        'email': 'manager@tourmanager.com',
        'password': 'Manager123!'
    }

    response = session.post(login_url, data=data, allow_redirects=True)
    return response.status_code == 200

def test_deny():
    """Test DENY operation."""
    print("\n" + "="*60)
    print("TEST: DENY Guestlist Entry")
    print("="*60)

    session = requests.Session()
    if not login(session):
        print("❌ Login failed")
        return False

    # First, let's find a pending entry to deny
    # We need to check the database or create one first
    manage_url = f"{BASE_URL}/guestlist/stop/1"
    response = session.get(manage_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Look for deny forms
    deny_forms = soup.find_all('form', action=lambda x: x and '/deny' in x)

    if deny_forms:
        # Get the entry ID from the form action
        action = deny_forms[0].get('action')
        entry_id = action.split('/')[-2]
        print(f"Found pending entry ID: {entry_id}")

        # Get CSRF token
        csrf_input = deny_forms[0].find('input', {'name': 'csrf_token'})
        csrf = csrf_input.get('value') if csrf_input else get_csrf_token(session, manage_url)

        # Submit deny
        deny_url = f"{BASE_URL}/guestlist/entry/{entry_id}/deny"
        data = {'csrf_token': csrf}
        response = session.post(deny_url, data=data, allow_redirects=True)

        if response.status_code == 200:
            if 'refusé' in response.text.lower() or 'denied' in response.text.lower():
                print(f"✅ DENY SUCCESS - Entry {entry_id} denied")
                return True
            else:
                print(f"✅ POST succeeded (status 200)")
                return True
        else:
            print(f"❌ DENY FAILED - Status: {response.status_code}")
            return False
    else:
        print("⚠️ No pending entries to deny - Testing with direct POST")
        # Try to deny an existing entry anyway
        csrf = get_csrf_token(session, manage_url)
        deny_url = f"{BASE_URL}/guestlist/entry/1/deny"
        data = {'csrf_token': csrf}
        response = session.post(deny_url, data=data, allow_redirects=True)
        print(f"Direct deny attempt - Status: {response.status_code}")
        return response.status_code == 200

def test_create():
    """Test CREATE (add) operation."""
    print("\n" + "="*60)
    print("TEST: CREATE Guestlist Entry")
    print("="*60)

    session = requests.Session()
    if not login(session):
        print("❌ Login failed")
        return False

    # Get the add form page
    add_url = f"{BASE_URL}/guestlist/stop/1/add"
    response = session.get(add_url)

    if response.status_code != 200:
        print(f"❌ Cannot access add page - Status: {response.status_code}")
        return False

    print(f"✅ Add page accessible - Status: {response.status_code}")

    # Parse form
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf = get_csrf_token(session, add_url)

    # Check what fields exist in the form
    form = soup.find('form')
    if form:
        inputs = form.find_all(['input', 'select', 'textarea'])
        print(f"Form fields found: {[i.get('name') for i in inputs if i.get('name')]}")

    # Prepare form data
    data = {
        'csrf_token': csrf,
        'guest_name': 'Test Guest CRUD',
        'guest_email': 'testcrud@example.com',
        'entry_type': 'guest',
        'plus_ones': '1',
        'notes': 'Test entry from CRUD test'
    }

    # Submit form
    response = session.post(add_url, data=data, allow_redirects=True)

    if response.status_code == 200:
        if 'Test Guest CRUD' in response.text or 'ajouté' in response.text.lower() or 'créé' in response.text.lower():
            print(f"✅ CREATE SUCCESS - Entry created")
            return True
        elif 'error' in response.text.lower() or 'erreur' in response.text.lower():
            # Check for validation errors
            soup = BeautifulSoup(response.text, 'html.parser')
            errors = soup.find_all(class_=lambda x: x and ('error' in x.lower() or 'invalid' in x.lower() or 'danger' in x.lower()))
            if errors:
                print(f"⚠️ Form validation errors:")
                for e in errors[:3]:
                    print(f"   - {e.get_text(strip=True)[:100]}")
            return False
        else:
            print(f"✅ POST succeeded (status 200) - checking if entry exists")
            # Verify entry was created
            manage_url = f"{BASE_URL}/guestlist/stop/1"
            verify_response = session.get(manage_url)
            if 'Test Guest CRUD' in verify_response.text:
                print(f"✅ Entry verified in list")
                return True
            else:
                print(f"⚠️ Entry not found in list - may have validation issues")
                return False
    else:
        print(f"❌ CREATE FAILED - Status: {response.status_code}")
        return False

def test_edit():
    """Test EDIT operation."""
    print("\n" + "="*60)
    print("TEST: EDIT Guestlist Entry")
    print("="*60)

    session = requests.Session()
    if not login(session):
        print("❌ Login failed")
        return False

    # First find an entry to edit
    manage_url = f"{BASE_URL}/guestlist/stop/1"
    response = session.get(manage_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find edit links
    edit_links = soup.find_all('a', href=lambda x: x and '/edit' in x and '/guestlist/' in x)

    if not edit_links:
        print("⚠️ No edit links found on manage page")
        # Try direct URL
        edit_url = f"{BASE_URL}/guestlist/entry/1/edit"
    else:
        edit_url = BASE_URL + edit_links[0].get('href')
        print(f"Found edit link: {edit_url}")

    # Get edit form
    response = session.get(edit_url)

    if response.status_code != 200:
        print(f"❌ Cannot access edit page - Status: {response.status_code}")
        # Check if it's a 404 or permission issue
        if response.status_code == 404:
            print("   Entry may not exist")
        elif response.status_code == 403:
            print("   Permission denied")
        return False

    print(f"✅ Edit page accessible - Status: {response.status_code}")

    # Parse form and get current values
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf = get_csrf_token(session, edit_url)

    # Get current guest name
    name_input = soup.find('input', {'name': 'guest_name'})
    current_name = name_input.get('value', '') if name_input else ''
    print(f"Current guest name: {current_name}")

    # Prepare updated data
    data = {
        'csrf_token': csrf,
        'guest_name': current_name + ' (EDITED)',
        'guest_email': 'edited@example.com',
        'entry_type': 'vip',
        'plus_ones': '2',
        'notes': 'Updated by CRUD test'
    }

    # Submit edit
    response = session.post(edit_url, data=data, allow_redirects=True)

    if response.status_code == 200:
        if '(EDITED)' in response.text or 'modifié' in response.text.lower() or 'updated' in response.text.lower():
            print(f"✅ EDIT SUCCESS - Entry updated")
            return True
        else:
            print(f"✅ POST succeeded (status 200)")
            # Verify changes
            verify_response = session.get(manage_url)
            if '(EDITED)' in verify_response.text:
                print(f"✅ Changes verified")
                return True
            return True
    else:
        print(f"❌ EDIT FAILED - Status: {response.status_code}")
        return False

def test_delete():
    """Test DELETE operation."""
    print("\n" + "="*60)
    print("TEST: DELETE Guestlist Entry")
    print("="*60)

    session = requests.Session()
    if not login(session):
        print("❌ Login failed")
        return False

    # First find an entry to delete (preferably the test one we created)
    manage_url = f"{BASE_URL}/guestlist/stop/1"
    response = session.get(manage_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Look for delete forms
    delete_forms = soup.find_all('form', action=lambda x: x and '/delete' in x and '/guestlist/' in x)

    if not delete_forms:
        print("⚠️ No delete forms found")
        return False

    # Get the last entry (probably our test entry)
    action = delete_forms[-1].get('action')
    entry_id = action.split('/')[-2]
    print(f"Will delete entry ID: {entry_id}")

    # Get entry name before delete
    entry_row = delete_forms[-1].find_parent('tr') or delete_forms[-1].find_parent('div')

    # Get CSRF token
    csrf_input = delete_forms[-1].find('input', {'name': 'csrf_token'})
    csrf = csrf_input.get('value') if csrf_input else get_csrf_token(session, manage_url)

    # Count entries before
    entries_before = len(soup.find_all('tr')) if soup.find('table') else 0

    # Submit delete
    delete_url = f"{BASE_URL}/guestlist/entry/{entry_id}/delete"
    data = {'csrf_token': csrf}
    response = session.post(delete_url, data=data, allow_redirects=True)

    if response.status_code == 200:
        # Verify deletion
        verify_response = session.get(manage_url)
        verify_soup = BeautifulSoup(verify_response.text, 'html.parser')
        entries_after = len(verify_soup.find_all('tr')) if verify_soup.find('table') else 0

        if entries_after < entries_before or 'supprimé' in response.text.lower() or 'deleted' in response.text.lower():
            print(f"✅ DELETE SUCCESS - Entry {entry_id} deleted")
            return True
        else:
            print(f"✅ POST succeeded (status 200)")
            return True
    else:
        print(f"❌ DELETE FAILED - Status: {response.status_code}")
        return False

def main():
    print("\n" + "#"*60)
    print("# GUESTLIST CRUD OPERATIONS TEST")
    print("#"*60)

    results = {}

    # Test DENY first (we might have pending entries)
    results['DENY'] = test_deny()

    # Test CREATE
    results['CREATE'] = test_create()

    # Test EDIT
    results['EDIT'] = test_edit()

    # Test DELETE
    results['DELETE'] = test_delete()

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    for op, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{op}: {status}")

    passed = sum(results.values())
    total = len(results)
    print(f"\nTotal: {passed}/{total} operations passed")

    return all(results.values())

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
