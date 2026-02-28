#!/usr/bin/env python3
"""Debug Address Autocomplete Script"""

import os
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def main():
    print("=== DEBUG ADDRESS AUTOCOMPLETE ===\n")

    # Setup Chrome
    options = Options()
    options.add_argument("--start-maximized")
    # Enable console logging
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL', 'performance': 'ALL'})

    driver = webdriver.Chrome(options=options)

    # Collect data
    console_logs_before = []
    console_logs_after = []
    network_requests = []

    try:
        # Step 1: Login
        print("--- STEP 1: Navigating to login page ---")
        driver.get("http://127.0.0.1:5000/auth/login")
        time.sleep(2)

        print("--- STEP 2: Logging in ---")
        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")

        email_field.send_keys(os.environ.get("DEBUG_EMAIL", "manager@gigroute.app"))
        password_field.send_keys(os.environ.get("DEBUG_PASSWORD", "changeme"))

        # Try multiple selectors for submit button
        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
        except:
            try:
                submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            except:
                submit_btn = driver.find_element(By.CSS_SELECTOR, ".btn-primary.btn-lg")
        submit_btn.click()
        time.sleep(3)

        current_url = driver.current_url
        print(f"Current URL after login: {current_url}")

        # Step 3: Navigate to venue create
        print("\n--- STEP 3: Navigating to /venues/create ---")
        driver.get("http://127.0.0.1:5000/venues/create")
        time.sleep(3)

        # Step 4: Capture console BEFORE typing
        print("\n--- STEP 4: Console BEFORE typing ---")
        try:
            logs = driver.get_log('browser')
            console_logs_before = logs
            print(f"Found {len(logs)} console messages before typing:")
            for log in logs:
                level = log.get('level', 'INFO')
                message = log.get('message', '')
                print(f"  [{level}] {message[:200]}")
        except Exception as e:
            print(f"Could not get browser logs: {e}")

        # Check if initAddressAutocomplete exists
        print("\n--- Checking if initAddressAutocomplete function exists ---")
        func_exists = driver.execute_script("return typeof window.initAddressAutocomplete === 'function'")
        print(f"initAddressAutocomplete exists: {func_exists}")

        # Check if address field exists
        try:
            address_field = driver.find_element(By.ID, "address")
            print("#address field found: True")
        except:
            print("#address field found: False")
            return

        # Step 5: Type address
        print("\n--- STEP 5: Typing '45 rue de rivoli' ---")
        address_field.click()
        address_field.clear()

        # Type slowly to trigger autocomplete
        for char in "45 rue de rivoli":
            address_field.send_keys(char)
            time.sleep(0.05)

        # Step 6: Wait and observe
        print("\n--- STEP 6: Waiting 3 seconds for autocomplete ---")
        time.sleep(3)

        # Capture console AFTER typing
        print("\n--- Checking console AFTER typing ---")
        try:
            logs = driver.get_log('browser')
            console_logs_after = logs
            print(f"Found {len(logs)} NEW console messages after typing:")
            for log in logs:
                level = log.get('level', 'INFO')
                message = log.get('message', '')
                print(f"  [{level}] {message[:300]}")
        except Exception as e:
            print(f"Could not get browser logs: {e}")

        # Check for dropdown
        dropdowns = driver.find_elements(By.CSS_SELECTOR, ".autocomplete-dropdown.show")
        print(f"\nAutocomplete dropdown visible: {len(dropdowns) > 0}")

        if len(dropdowns) > 0:
            items = driver.find_elements(By.CSS_SELECTOR, ".autocomplete-item")
            print(f"Number of suggestions: {len(items)}")
            for i, item in enumerate(items):
                print(f"  Suggestion {i+1}: {item.text[:100]}...")
        else:
            # Check if dropdown exists at all
            all_dropdowns = driver.find_elements(By.CSS_SELECTOR, ".autocomplete-dropdown")
            print(f"Dropdown element exists (hidden): {len(all_dropdowns) > 0}")

            # Check for any wrapper
            wrappers = driver.find_elements(By.CSS_SELECTOR, ".autocomplete-wrapper")
            print(f"Autocomplete wrapper exists: {len(wrappers) > 0}")

        # Check network requests via Performance logs
        print("\n--- Checking Network requests ---")
        try:
            perf_logs = driver.get_log('performance')
            api_requests = []
            for entry in perf_logs:
                try:
                    log = json.loads(entry['message'])
                    message = log.get('message', {})
                    method = message.get('method', '')
                    params = message.get('params', {})

                    if method == 'Network.requestWillBeSent':
                        url = params.get('request', {}).get('url', '')
                        if 'api-adresse' in url or 'geoapify' in url:
                            api_requests.append({
                                'type': 'REQUEST',
                                'url': url,
                                'method': params.get('request', {}).get('method', 'GET')
                            })
                    elif method == 'Network.responseReceived':
                        url = params.get('response', {}).get('url', '')
                        if 'api-adresse' in url or 'geoapify' in url:
                            api_requests.append({
                                'type': 'RESPONSE',
                                'url': url,
                                'status': params.get('response', {}).get('status', 0)
                            })
                except:
                    pass

            if api_requests:
                print(f"Found {len(api_requests)} API requests:")
                for req in api_requests:
                    print(f"  {req['type']}: {req.get('method', req.get('status', ''))} {req['url'][:100]}")
            else:
                print("NO requests to api-adresse.data.gouv.fr detected!")
        except Exception as e:
            print(f"Could not get performance logs: {e}")

        # Execute JS to manually check for fetch errors
        print("\n--- Executing manual API test from browser ---")
        try:
            result = driver.execute_script("""
                return new Promise((resolve) => {
                    fetch('https://api-adresse.data.gouv.fr/search/?q=45+rue+de+rivoli&limit=3&autocomplete=1')
                        .then(response => {
                            if (!response.ok) {
                                resolve({success: false, error: 'HTTP ' + response.status});
                            }
                            return response.json();
                        })
                        .then(data => {
                            resolve({
                                success: true,
                                featuresCount: data.features ? data.features.length : 0,
                                firstLabel: data.features && data.features[0] ? data.features[0].properties.label : 'none'
                            });
                        })
                        .catch(err => {
                            resolve({success: false, error: err.message});
                        });
                });
            """)
            print(f"Manual API test result: {result}")
        except Exception as e:
            print(f"Manual API test error: {e}")

        # Final Report
        print("\n\n========================================")
        print("=== FINAL REPORT ===")
        print("========================================")

        print(f"\n1. initAddressAutocomplete exists: {func_exists}")
        print(f"2. Address field found: True")
        print(f"3. Autocomplete dropdown visible: {len(dropdowns) > 0}")
        print(f"4. Console errors before: {len([l for l in console_logs_before if l.get('level') == 'SEVERE'])}")
        print(f"5. Console errors after: {len([l for l in console_logs_after if l.get('level') == 'SEVERE'])}")

        # Screenshot
        print("\n--- Taking screenshot ---")
        driver.save_screenshot("C:/Claude-Code-Creation/projects/tour-manager/debug-autocomplete-screenshot.png")
        print("Screenshot saved to: debug-autocomplete-screenshot.png")

        # Keep browser open
        print("\n--- Browser will close in 10 seconds ---")
        time.sleep(10)

    except Exception as e:
        print(f"\nTest error: {e}")
        import traceback
        traceback.print_exc()
        driver.save_screenshot("C:/Claude-Code-Creation/projects/tour-manager/debug-error-screenshot.png")

    finally:
        driver.quit()
        print("\n=== DEBUG COMPLETE ===")

if __name__ == "__main__":
    main()
