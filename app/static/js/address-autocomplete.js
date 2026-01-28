/**
 * Address Autocomplete Widget - Solution Professionnelle Mondiale
 *
 * France: API Adresse (data.gouv.fr) - Base Adresse Nationale
 * International: Geoapify (3000 req/jour gratuit)
 *
 * Usage:
 *   initAddressAutocomplete('#address', {
 *     latField: '#latitude',
 *     lngField: '#longitude',
 *     cityField: '#city',
 *     countryField: '#country',
 *     postalCodeField: '#postal_code',
 *     geoapifyKey: 'your_api_key'  // Optional, for international
 *   });
 */

(function() {
    'use strict';

    // APIs Endpoints
    const API_ADRESSE_FR = 'https://api-adresse.data.gouv.fr/search/';
    const GEOAPIFY_API = 'https://api.geoapify.com/v1/geocode/autocomplete';

    // Debounce delay for API requests (ms)
    const DEBOUNCE_DELAY = 300;

    // Minimum characters before searching
    const MIN_CHARS = 3;

    // Geoapify API Key (optional, for international support)
    let GEOAPIFY_KEY = null;

    /**
     * Initialize address autocomplete on an input field
     * @param {string} inputSelector - CSS selector for the address input
     * @param {Object} options - Configuration options
     */
    window.initAddressAutocomplete = function(inputSelector, options = {}) {
        const input = document.querySelector(inputSelector);
        if (!input) {
            console.warn('Address autocomplete: Input not found:', inputSelector);
            return;
        }

        // Store Geoapify key if provided
        GEOAPIFY_KEY = options.geoapifyKey || null;

        const config = {
            latField: options.latField || null,
            lngField: options.lngField || null,
            cityField: options.cityField || null,
            countryField: options.countryField || null,
            postalCodeField: options.postalCodeField || null,
            stateField: options.stateField || null,
            onSelect: options.onSelect || null,
            country: options.country || 'FR',  // Default to France
            limit: options.limit || 5
        };

        // Create autocomplete container
        const container = createAutocompleteContainer(input);

        // Track state
        let debounceTimer = null;
        let currentQuery = '';
        let selectedIndex = -1;
        let suggestions = [];

        // Observe country field changes if it exists
        if (config.countryField) {
            const countryInput = document.querySelector(config.countryField);
            if (countryInput) {
                countryInput.addEventListener('change', function() {
                    config.country = detectCountryCode(this.value);
                });
                // Initialize with current value
                if (countryInput.value) {
                    config.country = detectCountryCode(countryInput.value);
                }
            }
        }

        // Input event handler with debounce
        input.addEventListener('input', function() {
            const query = this.value.trim();

            // Clear timer
            if (debounceTimer) {
                clearTimeout(debounceTimer);
            }

            // Clear suggestions if query is too short
            if (query.length < MIN_CHARS) {
                hideSuggestions(container);
                return;
            }

            // Skip if query hasn't changed
            if (query === currentQuery) {
                return;
            }

            currentQuery = query;
            selectedIndex = -1;

            // Debounced API request
            debounceTimer = setTimeout(async function() {
                try {
                    suggestions = await fetchSuggestions(query, config);
                    displaySuggestions(container, suggestions, input, config);
                } catch (error) {
                    console.error('Address autocomplete error:', error);
                    hideSuggestions(container);
                }
            }, DEBOUNCE_DELAY);
        });

        // Keyboard navigation
        input.addEventListener('keydown', function(e) {
            if (!container.classList.contains('show')) {
                return;
            }

            const items = container.querySelectorAll('.autocomplete-item');

            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                    updateSelection(items, selectedIndex);
                    break;

                case 'ArrowUp':
                    e.preventDefault();
                    selectedIndex = Math.max(selectedIndex - 1, 0);
                    updateSelection(items, selectedIndex);
                    break;

                case 'Enter':
                    e.preventDefault();
                    if (selectedIndex >= 0 && suggestions[selectedIndex]) {
                        selectSuggestion(suggestions[selectedIndex], input, config);
                        hideSuggestions(container);
                    }
                    break;

                case 'Escape':
                    hideSuggestions(container);
                    break;
            }
        });

        // Hide on blur (with delay for click handling)
        input.addEventListener('blur', function() {
            setTimeout(function() {
                hideSuggestions(container);
            }, 200);
        });

        // Show on focus if there's a query
        input.addEventListener('focus', function() {
            if (this.value.trim().length >= MIN_CHARS && suggestions.length > 0) {
                showSuggestions(container);
            }
        });
    };

    /**
     * Create the autocomplete dropdown container
     */
    function createAutocompleteContainer(input) {
        // Create wrapper if needed
        let wrapper = input.parentElement;
        if (!wrapper.classList.contains('autocomplete-wrapper')) {
            wrapper = document.createElement('div');
            wrapper.className = 'autocomplete-wrapper position-relative';
            input.parentElement.insertBefore(wrapper, input);
            wrapper.appendChild(input);
        }

        // Create dropdown
        const container = document.createElement('div');
        container.className = 'autocomplete-dropdown dropdown-menu dropdown-menu-dark w-100';
        container.style.cssText = 'max-height: 300px; overflow-y: auto; z-index: 1050;';
        wrapper.appendChild(container);

        return container;
    }

    /**
     * Fetch suggestions based on country
     */
    async function fetchSuggestions(query, config) {
        // France → API Adresse (gratuit illimité, meilleure qualité)
        if (config.country === 'FR' || config.country === 'France') {
            return await fetchFromAPIAdresse(query, config);
        }

        // International → Geoapify (si clé disponible)
        if (GEOAPIFY_KEY) {
            return await fetchFromGeoapify(query, config);
        }

        // Fallback: API Adresse (fonctionne mais optimisé pour France)
        console.warn('Geoapify key not configured, using API Adresse for international search');
        return await fetchFromAPIAdresse(query, config);
    }

    /**
     * Fetch from API Adresse (France) - Gratuit, illimité, CORS activé
     * https://api-adresse.data.gouv.fr/
     */
    async function fetchFromAPIAdresse(query, config) {
        const params = new URLSearchParams({
            q: query,
            limit: config.limit,
            autocomplete: 1
        });

        const response = await fetch(`${API_ADRESSE_FR}?${params}`);
        if (!response.ok) {
            throw new Error(`API Adresse error: ${response.status}`);
        }

        const data = await response.json();
        return data.features.map(feature => ({
            display_name: feature.properties.label,
            address: feature.properties.name || feature.properties.street || '',
            house_number: feature.properties.housenumber || '',
            city: feature.properties.city || '',
            state: extractStateFromContext(feature.properties.context),
            country: 'France',
            postal_code: feature.properties.postcode || '',
            latitude: feature.geometry.coordinates[1],
            longitude: feature.geometry.coordinates[0],
            type: feature.properties.type || 'address',
            source: 'api-adresse'
        }));
    }

    /**
     * Fetch from Geoapify (International) - 3000 req/jour gratuit, CORS activé
     * https://www.geoapify.com/geocoding-api
     */
    async function fetchFromGeoapify(query, config) {
        const params = new URLSearchParams({
            text: query,
            limit: config.limit,
            apiKey: GEOAPIFY_KEY,
            format: 'json',
            lang: 'fr'
        });

        // Add country filter if specified (and not "ALL")
        if (config.country && config.country !== 'ALL' && config.country.length === 2) {
            params.append('filter', `countrycode:${config.country.toLowerCase()}`);
        }

        const response = await fetch(`${GEOAPIFY_API}?${params}`);
        if (!response.ok) {
            throw new Error(`Geoapify error: ${response.status}`);
        }

        const data = await response.json();
        return (data.results || []).map(feature => ({
            display_name: feature.formatted,
            address: feature.street || feature.name || '',
            house_number: feature.housenumber || '',
            city: feature.city || feature.town || feature.village || '',
            state: feature.state || '',
            country: feature.country || '',
            postal_code: feature.postcode || '',
            latitude: feature.lat,
            longitude: feature.lon,
            type: feature.result_type || 'address',
            source: 'geoapify'
        }));
    }

    /**
     * Extract state/region from API Adresse context
     * Format: "13, Bouches-du-Rhône, Provence-Alpes-Côte d'Azur"
     */
    function extractStateFromContext(context) {
        if (!context) return '';
        const parts = context.split(',');
        // Return the region (last part) or department (second part)
        if (parts.length >= 3) {
            return parts[2].trim(); // Region
        } else if (parts.length >= 2) {
            return parts[1].trim(); // Department
        }
        return '';
    }

    /**
     * Detect country code from country name
     */
    function detectCountryCode(countryName) {
        if (!countryName) return 'FR';

        const map = {
            'france': 'FR',
            'allemagne': 'DE', 'germany': 'DE',
            'espagne': 'ES', 'spain': 'ES',
            'italie': 'IT', 'italy': 'IT',
            'royaume-uni': 'GB', 'united kingdom': 'GB', 'uk': 'GB', 'great britain': 'GB',
            'états-unis': 'US', 'etats-unis': 'US', 'united states': 'US', 'usa': 'US',
            'belgique': 'BE', 'belgium': 'BE',
            'suisse': 'CH', 'switzerland': 'CH',
            'pays-bas': 'NL', 'netherlands': 'NL', 'holland': 'NL',
            'portugal': 'PT',
            'autriche': 'AT', 'austria': 'AT',
            'pologne': 'PL', 'poland': 'PL',
            'irlande': 'IE', 'ireland': 'IE',
            'danemark': 'DK', 'denmark': 'DK',
            'suède': 'SE', 'sweden': 'SE',
            'norvège': 'NO', 'norway': 'NO',
            'finlande': 'FI', 'finland': 'FI',
            'grèce': 'GR', 'greece': 'GR',
            'république tchèque': 'CZ', 'czech republic': 'CZ', 'czechia': 'CZ',
            'hongrie': 'HU', 'hungary': 'HU',
            'roumanie': 'RO', 'romania': 'RO',
            'bulgarie': 'BG', 'bulgaria': 'BG',
            'croatie': 'HR', 'croatia': 'HR',
            'slovénie': 'SI', 'slovenia': 'SI',
            'slovaquie': 'SK', 'slovakia': 'SK',
            'luxembourg': 'LU',
            'canada': 'CA',
            'mexique': 'MX', 'mexico': 'MX',
            'brésil': 'BR', 'brazil': 'BR',
            'argentine': 'AR', 'argentina': 'AR',
            'japon': 'JP', 'japan': 'JP',
            'chine': 'CN', 'china': 'CN',
            'corée du sud': 'KR', 'south korea': 'KR',
            'australie': 'AU', 'australia': 'AU',
            'nouvelle-zélande': 'NZ', 'new zealand': 'NZ'
        };

        const normalized = countryName.toLowerCase().trim();

        // Check if it's already a 2-letter code
        if (normalized.length === 2) {
            return normalized.toUpperCase();
        }

        return map[normalized] || 'FR';
    }

    /**
     * Display suggestions in dropdown
     */
    function displaySuggestions(container, suggestions, input, config) {
        container.innerHTML = '';

        if (suggestions.length === 0) {
            container.innerHTML = `
                <div class="dropdown-item text-muted">
                    <i class="bi bi-search me-2"></i>Aucune adresse trouvée
                </div>
            `;
            showSuggestions(container);
            return;
        }

        suggestions.forEach((suggestion, index) => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item dropdown-item d-flex align-items-start';
            item.style.cursor = 'pointer';

            // Icon based on type
            let icon = 'bi-geo-alt';
            if (suggestion.type === 'housenumber' || suggestion.type === 'house') {
                icon = 'bi-building';
            } else if (suggestion.type === 'street') {
                icon = 'bi-signpost-2';
            } else if (suggestion.type === 'city' || suggestion.type === 'municipality') {
                icon = 'bi-pin-map';
            } else if (suggestion.type === 'locality') {
                icon = 'bi-geo';
            }

            // Source badge
            const sourceBadge = suggestion.source === 'api-adresse'
                ? '<span class="badge bg-primary ms-2" style="font-size: 0.65em;">FR</span>'
                : '<span class="badge bg-secondary ms-2" style="font-size: 0.65em;">INT</span>';

            item.innerHTML = `
                <i class="bi ${icon} me-2 mt-1 text-primary"></i>
                <div class="flex-grow-1">
                    <div class="fw-medium">${escapeHtml(suggestion.display_name)}${sourceBadge}</div>
                    ${suggestion.latitude && suggestion.longitude ?
                        `<small class="text-muted"><i class="bi bi-check-circle text-success me-1"></i>Coordonnées disponibles</small>` :
                        `<small class="text-warning"><i class="bi bi-exclamation-triangle me-1"></i>Coordonnées non disponibles</small>`
                    }
                </div>
            `;

            item.addEventListener('mousedown', function(e) {
                e.preventDefault(); // Prevent blur from firing before selection
                selectSuggestion(suggestion, input, config);
                hideSuggestions(container);
            });

            item.addEventListener('mouseenter', function() {
                updateSelection(container.querySelectorAll('.autocomplete-item'), index);
            });

            container.appendChild(item);
        });

        showSuggestions(container);
    }

    /**
     * Select a suggestion and populate fields
     */
    function selectSuggestion(suggestion, input, config) {
        // Build full address
        let fullAddress = '';
        if (suggestion.house_number && suggestion.address) {
            fullAddress = `${suggestion.house_number} ${suggestion.address}`;
        } else if (suggestion.address) {
            fullAddress = suggestion.address;
        } else {
            fullAddress = suggestion.display_name.split(',')[0];
        }

        input.value = fullAddress;

        // Populate additional fields
        if (config.latField) {
            const latInput = document.querySelector(config.latField);
            if (latInput) latInput.value = suggestion.latitude || '';
        }

        if (config.lngField) {
            const lngInput = document.querySelector(config.lngField);
            if (lngInput) lngInput.value = suggestion.longitude || '';
        }

        if (config.cityField) {
            const cityInput = document.querySelector(config.cityField);
            if (cityInput) cityInput.value = suggestion.city || '';
        }

        if (config.countryField) {
            const countryInput = document.querySelector(config.countryField);
            if (countryInput) countryInput.value = suggestion.country || '';
        }

        if (config.postalCodeField) {
            const postalInput = document.querySelector(config.postalCodeField);
            if (postalInput) postalInput.value = suggestion.postal_code || '';
        }

        if (config.stateField) {
            const stateInput = document.querySelector(config.stateField);
            if (stateInput) stateInput.value = suggestion.state || '';
        }

        // Update validation indicator
        updateValidationIndicator(input, suggestion.latitude && suggestion.longitude);

        // Trigger callback if provided
        if (config.onSelect && typeof config.onSelect === 'function') {
            config.onSelect(suggestion);
        }

        // Trigger change event for form validation
        input.dispatchEvent(new Event('change', { bubbles: true }));
    }

    /**
     * Update visual selection in dropdown
     */
    function updateSelection(items, index) {
        items.forEach((item, i) => {
            if (i === index) {
                item.classList.add('active', 'bg-primary', 'text-white');
            } else {
                item.classList.remove('active', 'bg-primary', 'text-white');
            }
        });
    }

    /**
     * Show suggestions dropdown
     */
    function showSuggestions(container) {
        container.classList.add('show');
        container.style.display = 'block';
    }

    /**
     * Hide suggestions dropdown
     */
    function hideSuggestions(container) {
        container.classList.remove('show');
        container.style.display = 'none';
    }

    /**
     * Update validation indicator on input
     */
    function updateValidationIndicator(input, isValid) {
        // Remove existing indicator
        const existingIndicator = input.parentElement.querySelector('.validation-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }

        // Add new indicator
        const indicator = document.createElement('div');
        indicator.className = 'validation-indicator position-absolute';
        indicator.style.cssText = 'right: 10px; top: 50%; transform: translateY(-50%); pointer-events: none;';

        if (isValid) {
            indicator.innerHTML = '<i class="bi bi-check-circle-fill text-success"></i>';
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
        } else {
            indicator.innerHTML = '<i class="bi bi-exclamation-triangle-fill text-warning"></i>';
            input.classList.remove('is-valid');
            // Don't add is-invalid - just warning
        }

        input.parentElement.appendChild(indicator);
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

})();
