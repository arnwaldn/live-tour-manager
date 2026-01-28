/**
 * Airport Autocomplete Widget
 * Recherche par code IATA/ICAO, nom d'aeroport ou ville
 * Base de donnees statique (airports-data.js) - Recherche instantanee, pas de CORS
 *
 * Usage:
 *   initAirportAutocomplete('#departure_airport', {
 *     latField: '#departure_lat',
 *     lngField: '#departure_lng',
 *     onSelect: function(airport) { ... }
 *   });
 */

(function() {
    'use strict';

    // Debounce delay (ms) - court car recherche locale
    const DEBOUNCE_DELAY = 50;

    // Minimum characters before searching
    const MIN_CHARS = 2;

    /**
     * Initialize airport autocomplete on an input field
     * @param {string} inputSelector - CSS selector for the airport input
     * @param {Object} options - Configuration options
     */
    window.initAirportAutocomplete = function(inputSelector, options = {}) {
        const input = document.querySelector(inputSelector);
        if (!input) {
            console.warn('Airport autocomplete: Input not found:', inputSelector);
            return;
        }

        // Verify AIRPORTS_DATABASE is loaded
        if (typeof AIRPORTS_DATABASE === 'undefined' || !Array.isArray(AIRPORTS_DATABASE)) {
            console.error('Airport autocomplete: AIRPORTS_DATABASE not loaded. Include airports-data.js first.');
            return;
        }

        const config = {
            latField: options.latField || null,
            lngField: options.lngField || null,
            displayFormat: options.displayFormat || 'code', // 'code' = CDG, 'full' = CDG - Paris Charles de Gaulle
            onSelect: options.onSelect || null,
            limit: options.limit || 8
        };

        // Create autocomplete container
        const container = createAutocompleteContainer(input);

        // Track state
        let debounceTimer = null;
        let selectedIndex = -1;
        let suggestions = [];

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
                suggestions = [];
                return;
            }

            selectedIndex = -1;

            // Debounced search (very short delay since it's local)
            debounceTimer = setTimeout(function() {
                suggestions = searchAirports(query, config.limit);
                displaySuggestions(container, suggestions, input, config);
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
                        selectAirport(suggestions[selectedIndex], input, config);
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
            if (this.value.trim().length >= MIN_CHARS) {
                suggestions = searchAirports(this.value.trim(), config.limit);
                if (suggestions.length > 0) {
                    displaySuggestions(container, suggestions, input, config);
                }
            }
        });
    };

    /**
     * Search airports in the database
     * @param {string} query - Search query
     * @param {number} limit - Max results
     * @returns {Array} - Matching airports
     */
    function searchAirports(query, limit) {
        const q = query.toLowerCase().trim();
        if (q.length < MIN_CHARS) return [];

        // Exact IATA code match gets priority
        const exactIata = AIRPORTS_DATABASE.find(a => a.iata.toLowerCase() === q);

        // Search in all fields
        const results = AIRPORTS_DATABASE.filter(a => {
            // Skip exact match (will be added first)
            if (exactIata && a.iata === exactIata.iata) return false;

            return (
                a.iata.toLowerCase().includes(q) ||
                a.icao.toLowerCase().includes(q) ||
                a.name.toLowerCase().includes(q) ||
                a.city.toLowerCase().includes(q) ||
                a.country.toLowerCase().includes(q)
            );
        });

        // Score and sort results
        results.sort((a, b) => {
            // IATA exact start gets highest priority
            const aIataStart = a.iata.toLowerCase().startsWith(q) ? 0 : 1;
            const bIataStart = b.iata.toLowerCase().startsWith(q) ? 0 : 1;
            if (aIataStart !== bIataStart) return aIataStart - bIataStart;

            // City exact start gets second priority
            const aCityStart = a.city.toLowerCase().startsWith(q) ? 0 : 1;
            const bCityStart = b.city.toLowerCase().startsWith(q) ? 0 : 1;
            if (aCityStart !== bCityStart) return aCityStart - bCityStart;

            // Name contains query
            const aNameMatch = a.name.toLowerCase().includes(q) ? 0 : 1;
            const bNameMatch = b.name.toLowerCase().includes(q) ? 0 : 1;
            if (aNameMatch !== bNameMatch) return aNameMatch - bNameMatch;

            // Alphabetical by city
            return a.city.localeCompare(b.city);
        });

        // Add exact IATA match at the beginning
        if (exactIata) {
            results.unshift(exactIata);
        }

        return results.slice(0, limit);
    }

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
        container.style.cssText = 'max-height: 350px; overflow-y: auto; z-index: 1050;';
        wrapper.appendChild(container);

        return container;
    }

    /**
     * Display suggestions in dropdown
     */
    function displaySuggestions(container, suggestions, input, config) {
        container.innerHTML = '';

        if (suggestions.length === 0) {
            container.innerHTML = `
                <div class="dropdown-item text-muted">
                    <i class="bi bi-search me-2"></i>Aucun aeroport trouve
                </div>
            `;
            showSuggestions(container);
            return;
        }

        suggestions.forEach((airport, index) => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item dropdown-item d-flex align-items-start py-2';
            item.style.cursor = 'pointer';

            // Flag emoji based on country (simplified)
            const flag = getCountryFlag(airport.country);

            item.innerHTML = `
                <span class="me-2 mt-1" style="font-size: 1.2em;">${flag}</span>
                <div class="flex-grow-1">
                    <div class="d-flex align-items-center">
                        <span class="badge bg-primary me-2">${escapeHtml(airport.iata)}</span>
                        <span class="fw-medium">${escapeHtml(airport.name)}</span>
                    </div>
                    <small class="text-muted">
                        <i class="bi bi-geo-alt me-1"></i>${escapeHtml(airport.city)}, ${escapeHtml(airport.country)}
                        <span class="ms-2 text-success">
                            <i class="bi bi-check-circle"></i> GPS
                        </span>
                    </small>
                </div>
            `;

            item.addEventListener('mousedown', function(e) {
                e.preventDefault(); // Prevent blur from firing before selection
                selectAirport(airport, input, config);
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
     * Select an airport and populate fields
     */
    function selectAirport(airport, input, config) {
        // Set input value based on display format
        if (config.displayFormat === 'full') {
            input.value = `${airport.iata} - ${airport.city} ${airport.name}`;
        } else {
            input.value = airport.iata;
        }

        // Populate latitude/longitude fields
        if (config.latField) {
            const latInput = document.querySelector(config.latField);
            if (latInput) latInput.value = airport.lat || '';
        }

        if (config.lngField) {
            const lngInput = document.querySelector(config.lngField);
            if (lngInput) lngInput.value = airport.lng || '';
        }

        // Update validation indicator
        updateValidationIndicator(input, true);

        // Trigger callback if provided
        if (config.onSelect && typeof config.onSelect === 'function') {
            config.onSelect(airport);
        }

        // Trigger change event for form validation
        input.dispatchEvent(new Event('change', { bubbles: true }));
    }

    /**
     * Get country flag emoji (simplified mapping)
     */
    function getCountryFlag(country) {
        const flags = {
            'France': '🇫🇷',
            'Royaume-Uni': '🇬🇧', 'UK': '🇬🇧', 'United Kingdom': '🇬🇧',
            'Allemagne': '🇩🇪', 'Germany': '🇩🇪',
            'Espagne': '🇪🇸', 'Spain': '🇪🇸',
            'Italie': '🇮🇹', 'Italy': '🇮🇹',
            'Etats-Unis': '🇺🇸', 'USA': '🇺🇸', 'United States': '🇺🇸',
            'Canada': '🇨🇦',
            'Japon': '🇯🇵', 'Japan': '🇯🇵',
            'Chine': '🇨🇳', 'China': '🇨🇳',
            'Coree du Sud': '🇰🇷', 'South Korea': '🇰🇷',
            'Australie': '🇦🇺', 'Australia': '🇦🇺',
            'Bresil': '🇧🇷', 'Brazil': '🇧🇷',
            'Mexique': '🇲🇽', 'Mexico': '🇲🇽',
            'Pays-Bas': '🇳🇱', 'Netherlands': '🇳🇱',
            'Belgique': '🇧🇪', 'Belgium': '🇧🇪',
            'Suisse': '🇨🇭', 'Switzerland': '🇨🇭',
            'Autriche': '🇦🇹', 'Austria': '🇦🇹',
            'Portugal': '🇵🇹',
            'Grece': '🇬🇷', 'Greece': '🇬🇷',
            'Pologne': '🇵🇱', 'Poland': '🇵🇱',
            'Suede': '🇸🇪', 'Sweden': '🇸🇪',
            'Norvege': '🇳🇴', 'Norway': '🇳🇴',
            'Danemark': '🇩🇰', 'Denmark': '🇩🇰',
            'Finlande': '🇫🇮', 'Finland': '🇫🇮',
            'Irlande': '🇮🇪', 'Ireland': '🇮🇪',
            'Russie': '🇷🇺', 'Russia': '🇷🇺',
            'Turquie': '🇹🇷', 'Turkey': '🇹🇷',
            'Emirats Arabes Unis': '🇦🇪', 'UAE': '🇦🇪', 'United Arab Emirates': '🇦🇪',
            'Arabie Saoudite': '🇸🇦', 'Saudi Arabia': '🇸🇦',
            'Qatar': '🇶🇦',
            'Inde': '🇮🇳', 'India': '🇮🇳',
            'Singapour': '🇸🇬', 'Singapore': '🇸🇬',
            'Thailande': '🇹🇭', 'Thailand': '🇹🇭',
            'Indonesie': '🇮🇩', 'Indonesia': '🇮🇩',
            'Malaisie': '🇲🇾', 'Malaysia': '🇲🇾',
            'Philippines': '🇵🇭',
            'Vietnam': '🇻🇳',
            'Hong Kong': '🇭🇰',
            'Taiwan': '🇹🇼',
            'Argentine': '🇦🇷', 'Argentina': '🇦🇷',
            'Chili': '🇨🇱', 'Chile': '🇨🇱',
            'Colombie': '🇨🇴', 'Colombia': '🇨🇴',
            'Perou': '🇵🇪', 'Peru': '🇵🇪',
            'Afrique du Sud': '🇿🇦', 'South Africa': '🇿🇦',
            'Maroc': '🇲🇦', 'Morocco': '🇲🇦',
            'Egypte': '🇪🇬', 'Egypt': '🇪🇬',
            'Kenya': '🇰🇪',
            'Nigeria': '🇳🇬',
            'Nouvelle-Zelande': '🇳🇿', 'New Zealand': '🇳🇿',
            'Croatie': '🇭🇷', 'Croatia': '🇭🇷',
            'Republique Tcheque': '🇨🇿', 'Czech Republic': '🇨🇿', 'Czechia': '🇨🇿',
            'Hongrie': '🇭🇺', 'Hungary': '🇭🇺',
            'Roumanie': '🇷🇴', 'Romania': '🇷🇴',
            'Ukraine': '🇺🇦',
            'Israel': '🇮🇱',
            'Cuba': '🇨🇺',
            'Republique Dominicaine': '🇩🇴', 'Dominican Republic': '🇩🇴',
            'Jamaique': '🇯🇲', 'Jamaica': '🇯🇲',
            'Costa Rica': '🇨🇷',
            'Panama': '🇵🇦',
            'Islande': '🇮🇸', 'Iceland': '🇮🇸',
            'Luxembourg': '🇱🇺',
            'Slovenie': '🇸🇮', 'Slovenia': '🇸🇮',
            'Slovaquie': '🇸🇰', 'Slovakia': '🇸🇰',
            'Bulgarie': '🇧🇬', 'Bulgaria': '🇧🇬',
            'Serbie': '🇷🇸', 'Serbia': '🇷🇸',
            'Malte': '🇲🇹', 'Malta': '🇲🇹',
            'Chypre': '🇨🇾', 'Cyprus': '🇨🇾',
            'Estonie': '🇪🇪', 'Estonia': '🇪🇪',
            'Lettonie': '🇱🇻', 'Latvia': '🇱🇻',
            'Lituanie': '🇱🇹', 'Lithuania': '🇱🇹'
        };

        return flags[country] || '✈️';
    }

    /**
     * Update visual selection in dropdown
     */
    function updateSelection(items, index) {
        items.forEach((item, i) => {
            if (i === index) {
                item.classList.add('active', 'bg-primary', 'text-white');
                // Also update nested elements
                item.querySelectorAll('.text-muted, .text-success').forEach(el => {
                    el.classList.remove('text-muted', 'text-success');
                    el.classList.add('text-white-50');
                });
            } else {
                item.classList.remove('active', 'bg-primary', 'text-white');
                // Restore nested elements
                const small = item.querySelector('small');
                if (small) {
                    small.classList.remove('text-white-50');
                    small.classList.add('text-muted');
                }
                const gps = item.querySelector('.text-white-50:last-child');
                if (gps) {
                    gps.classList.remove('text-white-50');
                    gps.classList.add('text-success');
                }
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
        const wrapper = input.closest('.autocomplete-wrapper') || input.parentElement;
        const existingIndicator = wrapper.querySelector('.validation-indicator');
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
        }

        wrapper.appendChild(indicator);
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
