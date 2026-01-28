// Debug Address Autocomplete Script
import { chromium } from 'playwright';

(async () => {
    console.log('=== DEBUG ADDRESS AUTOCOMPLETE ===\n');

    const browser = await chromium.launch({
        headless: false,
        slowMo: 100
    });
    const context = await browser.newContext();
    const page = await context.newPage();

    // Collect console messages
    const consoleLogs = [];
    const consoleErrors = [];
    const consoleWarnings = [];

    page.on('console', msg => {
        const text = msg.text();
        const type = msg.type();
        const logEntry = `[${type.toUpperCase()}] ${text}`;

        if (type === 'error') {
            consoleErrors.push(logEntry);
        } else if (type === 'warning') {
            consoleWarnings.push(logEntry);
        } else {
            consoleLogs.push(logEntry);
        }
        console.log(logEntry);
    });

    // Collect network requests
    const networkRequests = [];
    page.on('request', request => {
        const url = request.url();
        if (url.includes('api-adresse') || url.includes('geoapify')) {
            networkRequests.push({
                type: 'REQUEST',
                method: request.method(),
                url: url
            });
            console.log(`[NETWORK REQUEST] ${request.method()} ${url}`);
        }
    });

    page.on('response', response => {
        const url = response.url();
        if (url.includes('api-adresse') || url.includes('geoapify')) {
            networkRequests.push({
                type: 'RESPONSE',
                status: response.status(),
                url: url
            });
            console.log(`[NETWORK RESPONSE] ${response.status()} ${url}`);
        }
    });

    // Collect JavaScript errors
    page.on('pageerror', error => {
        consoleErrors.push(`[PAGE ERROR] ${error.message}`);
        console.log(`[PAGE ERROR] ${error.message}`);
    });

    try {
        // Step 1: Login
        console.log('\n--- STEP 1: Navigating to login page ---');
        await page.goto('http://127.0.0.1:5000/auth/login');
        await page.waitForLoadState('networkidle');

        console.log('\n--- STEP 2: Logging in ---');
        await page.fill('input[name="email"]', 'arnaud.porcel@gmail.com');
        await page.fill('input[name="password"]', 'manager123');
        await page.click('button[type="submit"]');
        await page.waitForLoadState('networkidle');

        // Check login success
        const currentUrl = page.url();
        console.log(`Current URL after login: ${currentUrl}`);

        // Step 3: Navigate to venue create
        console.log('\n--- STEP 3: Navigating to /venues/create ---');
        await page.goto('http://127.0.0.1:5000/venues/create');
        await page.waitForLoadState('networkidle');

        // Step 4: Capture console BEFORE typing
        console.log('\n--- STEP 4: Console BEFORE typing (waiting 2 sec) ---');
        await page.waitForTimeout(2000);

        console.log('\n=== CONSOLE LOGS BEFORE TYPING ===');
        consoleLogs.forEach(log => console.log(log));
        console.log('\n=== CONSOLE ERRORS BEFORE TYPING ===');
        consoleErrors.forEach(err => console.log(err));
        console.log('\n=== CONSOLE WARNINGS BEFORE TYPING ===');
        consoleWarnings.forEach(warn => console.log(warn));

        // Check if initAddressAutocomplete exists
        console.log('\n--- Checking if initAddressAutocomplete function exists ---');
        const funcExists = await page.evaluate(() => {
            return typeof window.initAddressAutocomplete === 'function';
        });
        console.log(`initAddressAutocomplete exists: ${funcExists}`);

        // Check if address field exists
        const addressExists = await page.locator('#address').count();
        console.log(`#address field found: ${addressExists > 0}`);

        // Step 5: Type address
        console.log('\n--- STEP 5: Typing "45 rue de rivoli" ---');
        const addressField = page.locator('#address');
        await addressField.click();
        await addressField.fill('');

        // Type slowly to trigger autocomplete
        for (const char of '45 rue de rivoli') {
            await addressField.type(char, { delay: 50 });
        }

        // Step 6: Wait and observe
        console.log('\n--- STEP 6: Waiting 3 seconds for autocomplete ---');
        await page.waitForTimeout(3000);

        // Check for dropdown
        const dropdownVisible = await page.locator('.autocomplete-dropdown.show').count();
        console.log(`\nAutocomplete dropdown visible: ${dropdownVisible > 0}`);

        // Check dropdown content if visible
        if (dropdownVisible > 0) {
            const items = await page.locator('.autocomplete-item').count();
            console.log(`Number of suggestions: ${items}`);

            const suggestions = await page.locator('.autocomplete-item').allTextContents();
            suggestions.forEach((s, i) => console.log(`  Suggestion ${i+1}: ${s.substring(0, 100)}...`));
        }

        // Step 7: Final console report
        console.log('\n\n========================================');
        console.log('=== FINAL REPORT ===');
        console.log('========================================');

        console.log('\n--- ALL CONSOLE LOGS ---');
        consoleLogs.forEach(log => console.log(log));

        console.log('\n--- ALL CONSOLE ERRORS ---');
        if (consoleErrors.length === 0) {
            console.log('(No errors)');
        } else {
            consoleErrors.forEach(err => console.log(err));
        }

        console.log('\n--- ALL CONSOLE WARNINGS ---');
        if (consoleWarnings.length === 0) {
            console.log('(No warnings)');
        } else {
            consoleWarnings.forEach(warn => console.log(warn));
        }

        console.log('\n--- NETWORK REQUESTS TO API ---');
        if (networkRequests.length === 0) {
            console.log('(No requests to api-adresse.data.gouv.fr detected!)');
        } else {
            networkRequests.forEach(req => {
                console.log(`  ${req.type}: ${req.method || req.status} ${req.url}`);
            });
        }

        // Step 8: Screenshot
        console.log('\n--- STEP 8: Taking screenshot ---');
        await page.screenshot({
            path: 'C:/Claude-Code-Creation/projects/tour-manager/debug-autocomplete-screenshot.png',
            fullPage: true
        });
        console.log('Screenshot saved to: debug-autocomplete-screenshot.png');

        // Keep browser open for inspection
        console.log('\n--- Browser will close in 10 seconds ---');
        await page.waitForTimeout(10000);

    } catch (error) {
        console.error('Test error:', error.message);
        await page.screenshot({
            path: 'C:/Claude-Code-Creation/projects/tour-manager/debug-error-screenshot.png',
            fullPage: true
        });
    } finally {
        await browser.close();
        console.log('\n=== DEBUG COMPLETE ===');
    }
})();
