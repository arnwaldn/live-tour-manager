const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  // Collect console errors
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  try {
    // 1. Navigate to login
    console.log('1. Navigating to login page...');
    await page.goto('http://127.0.0.1:5000/auth/login');
    await page.waitForLoadState('networkidle');

    // 2. Login
    console.log('2. Logging in...');
    await page.fill('input[name="email"]', 'arnaud.porcel@gmail.com');
    await page.fill('input[name="password"]', 'manager123');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);

    // 3. Navigate to venue create
    console.log('3. Navigating to venue create form...');
    await page.goto('http://127.0.0.1:5000/venues/create');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // 4. Take screenshot
    console.log('4. Taking screenshot...');
    await page.screenshot({ path: 'venue_form_verification.png', fullPage: true });
    console.log('Screenshot saved: venue_form_verification.png');

    // 5. Check for GPS coordinates section
    console.log('5. Checking for GPS coordinates section...');
    const pageContent = await page.content();
    const hasGPSSection = pageContent.includes('Coordonnées GPS') ||
                          pageContent.includes('Coordonn');
    const hasLatField = await page.locator('input[name="latitude"]').count();
    const hasLngField = await page.locator('input[name="longitude"]').count();
    const hasLatLabel = pageContent.includes('Latitude');
    const hasLngLabel = pageContent.includes('Longitude');

    console.log('  - GPS section text found:', hasGPSSection);
    console.log('  - Latitude input field count:', hasLatField);
    console.log('  - Longitude input field count:', hasLngField);
    console.log('  - Latitude label found:', hasLatLabel);
    console.log('  - Longitude label found:', hasLngLabel);

    // 6. Check console errors
    console.log('6. JavaScript console errors:', consoleErrors.length);
    if (consoleErrors.length > 0) {
      consoleErrors.forEach(e => console.log('  ERROR:', e));
    }

    // Summary
    console.log('\n========== RAPPORT ==========');
    const gpsRemoved = !hasGPSSection && hasLatField === 0 && hasLngField === 0 && !hasLatLabel && !hasLngLabel;
    console.log('[' + (gpsRemoved ? 'OK' : 'FAIL') + '] Encart "Coordonnees GPS" avec Lat/Lng supprime');
    console.log('[' + (consoleErrors.length === 0 ? 'OK' : 'FAIL') + '] Pas d\'erreurs JavaScript dans la console');
    console.log('[OK] Screenshot sauvegarde: venue_form_verification.png');
    console.log('==============================');

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();
