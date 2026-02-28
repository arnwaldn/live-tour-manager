/**
 * GigRoute - Main JavaScript
 * Core functionality for sidebar, modals, forms, and UI interactions
 */

(function() {
    'use strict';

    // ==========================================================================
    // Configuration
    // ==========================================================================

    const CONFIG = {
        sidebarBreakpoint: 992, // Bootstrap lg breakpoint
        toastDuration: 3000,
        debounceDelay: 300,
        animationDuration: 300
    };

    // ==========================================================================
    // DOM Ready
    // ==========================================================================

    document.addEventListener('DOMContentLoaded', function() {
        initSidebar();
        initDropdowns();
        initForms();
        initTables();
        initToasts();
        initConfirmDialogs();
        initSearch();
        initTooltips();
    });

    // ==========================================================================
    // Sidebar Management
    // ==========================================================================

    function initSidebar() {
        const sidebar = document.getElementById('sidebarOffcanvas');
        if (!sidebar) return;

        // Close offcanvas when a nav link is clicked (mobile only)
        sidebar.querySelectorAll('.nav-link[href], a[href]').forEach(function(link) {
            link.addEventListener('click', function() {
                // Only close on mobile (when offcanvas is active, below lg breakpoint)
                if (window.innerWidth < CONFIG.sidebarBreakpoint) {
                    var offcanvasInstance = bootstrap.Offcanvas.getInstance(sidebar);
                    if (offcanvasInstance) {
                        offcanvasInstance.hide();
                    }
                }
            });
        });
    }

    // ==========================================================================
    // Dropdown Enhancements
    // ==========================================================================

    function initDropdowns() {
        // Close dropdowns when clicking outside
        document.addEventListener('click', function(e) {
            const dropdowns = document.querySelectorAll('.dropdown-menu.show');
            dropdowns.forEach(function(dropdown) {
                if (!dropdown.parentElement.contains(e.target)) {
                    const bsDropdown = bootstrap.Dropdown.getInstance(dropdown.previousElementSibling);
                    if (bsDropdown) bsDropdown.hide();
                }
            });
        });
    }

    // ==========================================================================
    // Form Handling
    // ==========================================================================

    function initForms() {
        // Form validation styling
        const forms = document.querySelectorAll('form[novalidate]');
        forms.forEach(function(form) {
            form.addEventListener('submit', function(e) {
                if (!form.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();

                    // BUG #1 FIX: Scroll to first invalid field and focus
                    const firstInvalid = form.querySelector(':invalid');
                    if (firstInvalid) {
                        firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        setTimeout(function() {
                            firstInvalid.focus();
                        }, 300);
                    }
                }
                form.classList.add('was-validated');
            });
        });

        // Submit button loading state - improved to handle validation properly
        document.querySelectorAll('form').forEach(function(form) {
            form.addEventListener('submit', function(e) {
                const submitBtn = form.querySelector('[type="submit"]');
                if (!submitBtn || form.dataset.noLoading) return;

                // Don't disable button if form validation failed (prevent multiple clicks issue)
                if (form.hasAttribute('novalidate') && !form.checkValidity()) {
                    return; // First handler already prevented submission
                }

                const originalText = submitBtn.innerHTML;
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Chargement...';

                // Store original text for potential reset
                submitBtn.dataset.originalText = originalText;

                // Reset button after timeout (fallback for server errors or slow responses)
                setTimeout(function() {
                    if (submitBtn.disabled) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = submitBtn.dataset.originalText || originalText;
                    }
                }, 10000); // 10 second timeout for slow connections
            });
        });

        // Auto-resize textareas
        document.querySelectorAll('textarea[data-auto-resize]').forEach(function(textarea) {
            textarea.addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = (this.scrollHeight) + 'px';
            });
        });

        // Character counter for textareas
        document.querySelectorAll('textarea[maxlength]').forEach(function(textarea) {
            const maxLength = textarea.getAttribute('maxlength');
            const counter = document.createElement('small');
            counter.className = 'text-muted float-end';
            // Initialize with current value length (for edit forms)
            counter.textContent = textarea.value.length + ' / ' + maxLength;
            textarea.parentElement.appendChild(counter);

            textarea.addEventListener('input', function() {
                counter.textContent = this.value.length + ' / ' + maxLength;
            });
        });
    }

    // ==========================================================================
    // Table Enhancements
    // ==========================================================================

    function initTables() {
        // Sortable table headers
        document.querySelectorAll('th[data-sort]').forEach(function(th) {
            th.style.cursor = 'pointer';
            th.addEventListener('click', function() {
                const table = th.closest('table');
                const tbody = table.querySelector('tbody');
                const column = th.dataset.sort;
                const rows = Array.from(tbody.querySelectorAll('tr'));
                const isAsc = th.classList.contains('sort-asc');

                // Reset other headers
                table.querySelectorAll('th[data-sort]').forEach(function(header) {
                    header.classList.remove('sort-asc', 'sort-desc');
                });

                // Sort rows
                rows.sort(function(a, b) {
                    const aVal = a.querySelector('[data-' + column + ']')?.dataset[column] || a.cells[th.cellIndex]?.textContent || '';
                    const bVal = b.querySelector('[data-' + column + ']')?.dataset[column] || b.cells[th.cellIndex]?.textContent || '';

                    if (!isNaN(aVal) && !isNaN(bVal)) {
                        return isAsc ? bVal - aVal : aVal - bVal;
                    }
                    return isAsc ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal);
                });

                // Update DOM
                rows.forEach(function(row) {
                    tbody.appendChild(row);
                });

                th.classList.add(isAsc ? 'sort-desc' : 'sort-asc');
            });
        });

        // Clickable rows
        document.querySelectorAll('.table-clickable tbody tr').forEach(function(row) {
            row.addEventListener('click', function(e) {
                // Ignore if clicking on a link or button
                if (e.target.closest('a, button, input, .dropdown')) return;

                const link = row.querySelector('a[data-row-link]') || row.querySelector('a:first-of-type');
                if (link) {
                    window.location.href = link.href;
                }
            });
        });

        // Select all checkbox
        document.querySelectorAll('[data-select-all]').forEach(function(selectAll) {
            const table = selectAll.closest('table');
            const checkboxes = table.querySelectorAll('tbody input[type="checkbox"]');

            selectAll.addEventListener('change', function() {
                checkboxes.forEach(function(cb) {
                    cb.checked = selectAll.checked;
                    cb.dispatchEvent(new Event('change'));
                });
                updateBulkActions(table);
            });

            checkboxes.forEach(function(cb) {
                cb.addEventListener('change', function() {
                    updateBulkActions(table);
                    // Update select all state
                    const allChecked = Array.from(checkboxes).every(function(c) { return c.checked; });
                    const someChecked = Array.from(checkboxes).some(function(c) { return c.checked; });
                    selectAll.checked = allChecked;
                    selectAll.indeterminate = someChecked && !allChecked;
                });
            });
        });

        function updateBulkActions(table) {
            const checked = table.querySelectorAll('tbody input[type="checkbox"]:checked');
            const bulkActions = document.querySelector('[data-bulk-actions]');
            if (bulkActions) {
                bulkActions.style.display = checked.length > 0 ? 'flex' : 'none';
                const counter = bulkActions.querySelector('[data-selected-count]');
                if (counter) {
                    counter.textContent = checked.length;
                }
            }
        }
    }

    // ==========================================================================
    // Toast Notifications
    // ==========================================================================

    function initToasts() {
        // Auto-hide flash messages
        document.querySelectorAll('.alert-dismissible').forEach(function(alert) {
            setTimeout(function() {
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                bsAlert.close();
            }, CONFIG.toastDuration);
        });
    }

    // Global toast function
    window.showToast = function(message, type) {
        type = type || 'info';
        let container = document.querySelector('.toast-container');

        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            container.style.zIndex = '1090';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-' + type + ' border-0';
        toast.setAttribute('role', 'alert');
        toast.innerHTML =
            '<div class="d-flex">' +
                '<div class="toast-body">' + message + '</div>' +
                '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>' +
            '</div>';

        container.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { delay: CONFIG.toastDuration });
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    };

    // ==========================================================================
    // Confirmation Dialogs (Bootstrap Modal)
    // ==========================================================================

    function initConfirmDialogs() {
        // [data-confirm] — generic confirmation before click action
        document.querySelectorAll('[data-confirm]').forEach(function(element) {
            element.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                var message = element.dataset.confirm || 'Êtes-vous sûr de vouloir continuer ?';
                var form = element.closest('form');
                if (form) {
                    showConfirmModal(form.action, message, 'Confirmer');
                } else if (element.href) {
                    showConfirmModal(null, message, 'Confirmer', null, function() {
                        window.location.href = element.href;
                    });
                }
            });
        });

        // [data-delete-confirm] — delete confirmation
        document.querySelectorAll('[data-delete-confirm]').forEach(function(btn) {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                var itemName = btn.dataset.deleteConfirm || 'cet élément';
                var form = btn.closest('form') || document.querySelector(btn.dataset.form);
                var message = 'Supprimer ' + itemName + ' ? Cette action est irréversible.';

                if (form) {
                    showConfirmModal(form.action, message, 'Supprimer');
                } else if (btn.href) {
                    showConfirmModal(null, message, 'Supprimer', null, function() {
                        window.location.href = btn.href;
                    });
                }
            });
        });
    }

    // ==========================================================================
    // Global showConfirmModal
    // ==========================================================================

    /**
     * Show a Bootstrap confirmation modal.
     * @param {string|null} url   - POST form action URL (null if using onConfirm callback)
     * @param {string} message    - Confirmation message
     * @param {string} btnText    - Confirm button label
     * @param {string} variant    - 'success' or 'danger' (default: 'danger')
     * @param {Function} onConfirm - Optional callback instead of POST form submit
     */
    window.showConfirmModal = function(url, message, btnText, variant, onConfirm) {
        var modal = document.getElementById('confirmModal');
        if (!modal) return;

        var form = document.getElementById('confirmModalForm');
        var msgEl = document.getElementById('confirmModalMessage');
        var btnEl = document.getElementById('confirmModalBtn');
        var header = document.getElementById('confirmModalHeader');
        var labelEl = document.getElementById('confirmModalLabel');
        var submitBtn = document.getElementById('confirmModalSubmitBtn');

        msgEl.textContent = message;
        if (btnText) btnEl.textContent = btnText;

        // Variant styling
        if (variant === 'success') {
            header.className = 'modal-header bg-success bg-opacity-10';
            labelEl.className = 'modal-title text-success';
            submitBtn.className = 'btn btn-success';
        } else {
            header.className = 'modal-header bg-danger bg-opacity-10';
            labelEl.className = 'modal-title text-danger';
            submitBtn.className = 'btn btn-danger';
        }

        // Clean up previous callback handler
        if (form._confirmHandler) {
            form.removeEventListener('submit', form._confirmHandler);
            form._confirmHandler = null;
        }

        if (onConfirm) {
            // Callback mode: prevent default form submit, call callback
            form.action = '';
            form._confirmHandler = function(e) {
                e.preventDefault();
                bootstrap.Modal.getInstance(modal).hide();
                onConfirm();
            };
            form.addEventListener('submit', form._confirmHandler);
        } else {
            // POST mode: set form action, use default submit
            form.action = url;
        }

        new bootstrap.Modal(modal).show();
    };

    // ==========================================================================
    // Search Functionality
    // ==========================================================================

    function initSearch() {
        const searchInputs = document.querySelectorAll('[data-search]');

        searchInputs.forEach(function(input) {
            const targetSelector = input.dataset.search;
            const items = document.querySelectorAll(targetSelector);

            input.addEventListener('input', debounce(function() {
                const query = input.value.toLowerCase().trim();

                items.forEach(function(item) {
                    const text = item.textContent.toLowerCase();
                    const match = query === '' || text.includes(query);
                    item.style.display = match ? '' : 'none';
                });

                // Show/hide empty state
                const visibleItems = Array.from(items).filter(function(item) {
                    return item.style.display !== 'none';
                });
                const emptyState = document.querySelector('[data-search-empty]');
                if (emptyState) {
                    emptyState.style.display = visibleItems.length === 0 ? 'block' : 'none';
                }
            }, CONFIG.debounceDelay));

            // Clear button
            const clearBtn = input.parentElement.querySelector('[data-search-clear]');
            if (clearBtn) {
                clearBtn.addEventListener('click', function() {
                    input.value = '';
                    input.dispatchEvent(new Event('input'));
                    input.focus();
                });
            }
        });
    }

    // ==========================================================================
    // Tooltips
    // ==========================================================================

    function initTooltips() {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltipTriggerList.forEach(function(el) {
            new bootstrap.Tooltip(el);
        });
    }

    // ==========================================================================
    // Utility Functions
    // ==========================================================================

    function debounce(func, wait) {
        let timeout;
        return function() {
            const context = this;
            const args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                func.apply(context, args);
            }, wait);
        };
    }

    // Format date for display
    window.formatDate = function(dateString, options) {
        options = options || { day: '2-digit', month: '2-digit', year: 'numeric' };
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR', options);
    };

    // Format time for display
    window.formatTime = function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    };

    // Format currency
    window.formatCurrency = function(amount, currency) {
        currency = currency || 'EUR';
        return new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: currency
        }).format(amount);
    };

    // ==========================================================================
    // AJAX Helpers
    // ==========================================================================

    window.fetchJSON = function(url, options) {
        options = options || {};
        options.headers = options.headers || {};
        options.headers['Content-Type'] = 'application/json';
        options.headers['Accept'] = 'application/json';

        // Add CSRF token if available
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ||
                         document.querySelector('input[name="csrf_token"]')?.value;
        if (csrfToken) {
            options.headers['X-CSRFToken'] = csrfToken;
        }

        return fetch(url, options).then(function(response) {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        });
    };

    // ==========================================================================
    // Keyboard Shortcuts
    // ==========================================================================

    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K: Focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('[data-global-search]');
            if (searchInput) {
                searchInput.focus();
            }
        }

        // Escape: Close modals and dropdowns
        if (e.key === 'Escape') {
            const openModal = document.querySelector('.modal.show');
            if (openModal) {
                const bsModal = bootstrap.Modal.getInstance(openModal);
                if (bsModal) bsModal.hide();
            }
        }
    });

    // ==========================================================================
    // Orientation Change Handler
    // ==========================================================================

    window.addEventListener('orientationchange', function() {
        // Close sidebar offcanvas on orientation change
        var sidebar = document.getElementById('sidebarOffcanvas');
        if (sidebar) {
            var offcanvasInstance = bootstrap.Offcanvas.getInstance(sidebar);
            if (offcanvasInstance) {
                offcanvasInstance.hide();
            }
        }

        // Trigger resize event after orientation change settles
        setTimeout(function() {
            window.dispatchEvent(new Event('resize'));
        }, 100);
    });

    // ==========================================================================
    // Collapsible Filters (Mobile)
    // ==========================================================================

    document.addEventListener('DOMContentLoaded', function() {
        // Initialize filter toggles
        document.querySelectorAll('.filter-toggle').forEach(function(toggle) {
            toggle.addEventListener('click', function() {
                const targetId = this.dataset.target || this.dataset.bsTarget;
                const target = document.querySelector(targetId);

                if (target) {
                    target.classList.toggle('show');
                    this.classList.toggle('collapsed');

                    // Toggle chevron icon
                    const chevron = this.querySelector('.bi-chevron-down, .bi-chevron-up');
                    if (chevron) {
                        chevron.classList.toggle('bi-chevron-down');
                        chevron.classList.toggle('bi-chevron-up');
                    }
                }
            });
        });

        // Auto-scroll active tab into view on mobile
        if (window.innerWidth < 576) {
            document.querySelectorAll('.nav-tabs, .nav-pills').forEach(function(tabs) {
                const activeTab = tabs.querySelector('.nav-link.active');
                if (activeTab) {
                    setTimeout(function() {
                        activeTab.scrollIntoView({
                            behavior: 'smooth',
                            inline: 'center',
                            block: 'nearest'
                        });
                    }, 100);
                }
            });
        }
    });

    // ==========================================================================
    // Portrait Mode Detection
    // ==========================================================================

    window.isPortrait = function() {
        return window.innerHeight > window.innerWidth;
    };

    window.isMobile = function() {
        return window.innerWidth < 576;
    };

    window.isTablet = function() {
        return window.innerWidth >= 576 && window.innerWidth < 992;
    };

    // ==========================================================================
    // PWA Install Prompt
    // ==========================================================================

    let deferredPrompt;

    window.addEventListener('beforeinstallprompt', function(e) {
        // Prevent Chrome 67+ from automatically showing the prompt
        e.preventDefault();
        // Stash the event so it can be triggered later
        deferredPrompt = e;

        // Show install banner if not already installed
        const banner = document.querySelector('.pwa-install-banner');
        if (banner && !window.matchMedia('(display-mode: standalone)').matches) {
            setTimeout(function() {
                banner.classList.add('show');
            }, 3000);
        }
    });

    // Handle install button click
    document.addEventListener('click', function(e) {
        if (e.target.matches('.btn-install')) {
            e.preventDefault();

            if (deferredPrompt) {
                deferredPrompt.prompt();
                deferredPrompt.userChoice.then(function(choiceResult) {
                    if (choiceResult.outcome === 'accepted') {
                        console.log('PWA installed');
                    }
                    deferredPrompt = null;

                    const banner = document.querySelector('.pwa-install-banner');
                    if (banner) banner.classList.remove('show');
                });
            }
        }

        // Dismiss banner
        if (e.target.matches('.btn-dismiss')) {
            const banner = e.target.closest('.pwa-install-banner');
            if (banner) banner.classList.remove('show');
        }
    });

})();
