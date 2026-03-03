/**
 * GigRoute - CSP-compliant Event Delegation
 *
 * Replaces inline event handlers (onclick, onchange, onsubmit) with
 * delegated event listeners to comply with Content Security Policy.
 *
 * Data attributes:
 *   [data-confirm-url]     - Show confirm modal with POST to given URL
 *   [data-confirm-form]    - Show confirm modal with POST to closest form's action
 *   [data-confirm-message] - Confirm modal message text
 *   [data-confirm-btn]     - Confirm modal button label
 *   [data-confirm-variant] - Confirm modal variant ('success' or 'danger')
 *   [data-action]          - Simple actions: 'print', 'back', 'reload'
 *   [data-native-confirm]  - Native confirm() dialog before action
 *   [data-auto-submit]     - Auto-submit closest form on change
 *   [data-stop-propagation]- Stop click event propagation
 */
(function() {
    'use strict';

    // ================================================================
    // Click delegation
    // ================================================================
    document.addEventListener('click', function(e) {

        // [data-confirm-url]: confirm modal with direct URL
        var target = e.target.closest('[data-confirm-url]');
        if (target) {
            e.preventDefault();
            e.stopPropagation();
            window.showConfirmModal(
                target.dataset.confirmUrl,
                target.dataset.confirmMessage || 'Confirmer ?',
                target.dataset.confirmBtn || 'Confirmer',
                target.dataset.confirmVariant || null
            );
            return;
        }

        // [data-confirm-form]: confirm modal with closest form's action
        target = e.target.closest('[data-confirm-form]');
        if (target) {
            e.preventDefault();
            e.stopPropagation();
            var form = target.closest('form');
            if (form) {
                window.showConfirmModal(
                    form.action,
                    target.dataset.confirmMessage || 'Confirmer ?',
                    target.dataset.confirmBtn || 'Confirmer',
                    target.dataset.confirmVariant || null
                );
            }
            return;
        }

        // [data-action]: simple navigation/UI actions
        target = e.target.closest('[data-action]');
        if (target) {
            var action = target.dataset.action;
            if (action === 'print') {
                e.preventDefault();
                window.print();
            } else if (action === 'back') {
                e.preventDefault();
                history.back();
            } else if (action === 'reload') {
                e.preventDefault();
                location.reload();
            }
            return;
        }

        // [data-native-confirm]: native confirm() before click action
        target = e.target.closest('[data-native-confirm]');
        if (target) {
            if (!confirm(target.dataset.nativeConfirm)) {
                e.preventDefault();
                e.stopPropagation();
            }
            // If confirmed, let the default action proceed
        }
    });

    // ================================================================
    // Submit delegation
    // ================================================================
    document.addEventListener('submit', function(e) {
        var form = e.target;
        // [data-native-confirm] on form: confirm before submit
        if (form.dataset.nativeConfirm) {
            if (!confirm(form.dataset.nativeConfirm)) {
                e.preventDefault();
            }
        }
    });

    // ================================================================
    // Change delegation
    // ================================================================
    document.addEventListener('change', function(e) {
        // [data-auto-submit]: auto-submit form on change
        var target = e.target.closest('[data-auto-submit]');
        if (target) {
            var form = target.closest('form');
            if (form) form.submit();
        }
    });

    // ================================================================
    // Stop propagation (direct attachment on DOMContentLoaded)
    // ================================================================
    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('[data-stop-propagation]').forEach(function(el) {
            el.addEventListener('click', function(e) {
                e.stopPropagation();
            });
        });
    });

})();
