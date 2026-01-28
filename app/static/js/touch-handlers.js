/**
 * Tour Manager - Touch Handlers
 * Mobile touch interactions: swipe gestures, pull to refresh, touch feedback
 */

(function() {
    'use strict';

    // ==========================================================================
    // Configuration
    // ==========================================================================

    const TOUCH_CONFIG = {
        swipeThreshold: 80,      // Minimum distance for swipe
        swipeVelocity: 0.3,      // Minimum velocity for swipe
        tapThreshold: 10,        // Maximum movement for tap
        holdDuration: 500,       // Long press duration
        pullRefreshThreshold: 80 // Pull to refresh distance
    };

    // ==========================================================================
    // Touch State
    // ==========================================================================

    let touchState = {
        startX: 0,
        startY: 0,
        startTime: 0,
        currentX: 0,
        currentY: 0,
        isSwiping: false,
        element: null
    };

    // ==========================================================================
    // Initialization
    // ==========================================================================

    document.addEventListener('DOMContentLoaded', function() {
        if (!isTouchDevice()) return;

        initSwipeActions();
        initTouchFeedback();
        initPullToRefresh();
        initSwipeNavigation();
    });

    // ==========================================================================
    // Device Detection
    // ==========================================================================

    function isTouchDevice() {
        return ('ontouchstart' in window) ||
               (navigator.maxTouchPoints > 0) ||
               (navigator.msMaxTouchPoints > 0);
    }

    // ==========================================================================
    // Swipe Actions (for check-in cards, etc.)
    // ==========================================================================

    function initSwipeActions() {
        const swipeableCards = document.querySelectorAll('[data-swipe-action]');

        swipeableCards.forEach(function(card) {
            let startX = 0;
            let currentX = 0;
            let isDragging = false;

            card.addEventListener('touchstart', function(e) {
                startX = e.touches[0].clientX;
                isDragging = true;
                card.style.transition = 'none';
            }, { passive: true });

            card.addEventListener('touchmove', function(e) {
                if (!isDragging) return;

                currentX = e.touches[0].clientX;
                const diffX = currentX - startX;

                // Only allow right swipe for positive actions
                if (diffX > 0 && diffX < 150) {
                    card.style.transform = 'translateX(' + diffX + 'px)';

                    // Show action indicator
                    const indicator = card.querySelector('.swipe-action-indicator');
                    if (indicator) {
                        indicator.style.opacity = Math.min(diffX / TOUCH_CONFIG.swipeThreshold, 1);
                    }
                }
            }, { passive: true });

            card.addEventListener('touchend', function(e) {
                if (!isDragging) return;
                isDragging = false;

                const diffX = currentX - startX;
                card.style.transition = 'transform 0.3s ease';

                if (diffX >= TOUCH_CONFIG.swipeThreshold) {
                    // Execute swipe action
                    const action = card.dataset.swipeAction;
                    executeSwipeAction(card, action);
                } else {
                    // Reset position
                    card.style.transform = 'translateX(0)';
                }
            }, { passive: true });
        });
    }

    function executeSwipeAction(card, action) {
        switch (action) {
            case 'check-in':
                // Find and submit the check-in form
                const form = card.querySelector('.check-in-form');
                if (form) {
                    // Animate card out
                    card.style.transform = 'translateX(100%)';
                    card.style.opacity = '0';

                    // Submit form
                    setTimeout(function() {
                        form.dispatchEvent(new Event('submit', { cancelable: true }));
                    }, 300);
                }
                break;

            case 'approve':
                const approveForm = card.querySelector('[data-action="approve"]');
                if (approveForm) {
                    card.style.transform = 'translateX(100%)';
                    setTimeout(function() {
                        approveForm.submit();
                    }, 300);
                }
                break;

            case 'delete':
                const deleteForm = card.querySelector('[data-action="delete"]');
                if (deleteForm && confirm('Supprimer cet élément?')) {
                    card.style.transform = 'translateX(-100%)';
                    setTimeout(function() {
                        deleteForm.submit();
                    }, 300);
                } else {
                    card.style.transform = 'translateX(0)';
                }
                break;

            default:
                card.style.transform = 'translateX(0)';
        }
    }

    // ==========================================================================
    // Touch Feedback (Ripple Effect)
    // ==========================================================================

    function initTouchFeedback() {
        const touchElements = document.querySelectorAll('.btn, .nav-link, .list-group-item, .card-clickable');

        touchElements.forEach(function(el) {
            el.addEventListener('touchstart', function(e) {
                const rect = el.getBoundingClientRect();
                const x = e.touches[0].clientX - rect.left;
                const y = e.touches[0].clientY - rect.top;

                // Add ripple effect
                const ripple = document.createElement('span');
                ripple.className = 'touch-ripple';
                ripple.style.left = x + 'px';
                ripple.style.top = y + 'px';

                el.style.position = 'relative';
                el.style.overflow = 'hidden';
                el.appendChild(ripple);

                setTimeout(function() {
                    ripple.remove();
                }, 600);
            }, { passive: true });
        });

        // Add ripple CSS
        if (!document.querySelector('#touch-ripple-styles')) {
            const style = document.createElement('style');
            style.id = 'touch-ripple-styles';
            style.textContent = [
                '.touch-ripple {',
                '  position: absolute;',
                '  border-radius: 50%;',
                '  background: rgba(255, 255, 255, 0.4);',
                '  width: 100px;',
                '  height: 100px;',
                '  margin-top: -50px;',
                '  margin-left: -50px;',
                '  animation: ripple-effect 0.6s ease-out;',
                '  pointer-events: none;',
                '}',
                '@keyframes ripple-effect {',
                '  0% { transform: scale(0); opacity: 1; }',
                '  100% { transform: scale(4); opacity: 0; }',
                '}'
            ].join('\n');
            document.head.appendChild(style);
        }
    }

    // ==========================================================================
    // Pull to Refresh
    // ==========================================================================

    function initPullToRefresh() {
        const pullRefreshContainers = document.querySelectorAll('[data-pull-refresh]');

        pullRefreshContainers.forEach(function(container) {
            let startY = 0;
            let currentY = 0;
            let isPulling = false;
            let refreshIndicator = null;

            // Create refresh indicator
            refreshIndicator = document.createElement('div');
            refreshIndicator.className = 'pull-refresh-indicator';
            refreshIndicator.innerHTML = '<div class="spinner-border spinner-border-sm"></div>';
            refreshIndicator.style.cssText = [
                'position: absolute;',
                'top: -50px;',
                'left: 50%;',
                'transform: translateX(-50%);',
                'transition: top 0.2s;',
                'padding: 10px;',
                'background: var(--sp-bg-card, #1A1A1A);',
                'border-radius: 50%;',
                'box-shadow: 0 2px 10px rgba(0,0,0,0.3);'
            ].join('');
            container.style.position = 'relative';
            container.insertBefore(refreshIndicator, container.firstChild);

            container.addEventListener('touchstart', function(e) {
                if (container.scrollTop === 0) {
                    startY = e.touches[0].clientY;
                    isPulling = true;
                }
            }, { passive: true });

            container.addEventListener('touchmove', function(e) {
                if (!isPulling) return;

                currentY = e.touches[0].clientY;
                const pullDistance = currentY - startY;

                if (pullDistance > 0 && pullDistance < 150) {
                    e.preventDefault();
                    refreshIndicator.style.top = (pullDistance - 50) + 'px';

                    if (pullDistance >= TOUCH_CONFIG.pullRefreshThreshold) {
                        refreshIndicator.classList.add('ready');
                    } else {
                        refreshIndicator.classList.remove('ready');
                    }
                }
            }, { passive: false });

            container.addEventListener('touchend', function() {
                if (!isPulling) return;
                isPulling = false;

                const pullDistance = currentY - startY;

                if (pullDistance >= TOUCH_CONFIG.pullRefreshThreshold) {
                    // Show loading state
                    refreshIndicator.style.top = '10px';
                    refreshIndicator.classList.add('loading');

                    // Reload page or fetch new data
                    setTimeout(function() {
                        window.location.reload();
                    }, 500);
                } else {
                    // Reset indicator
                    refreshIndicator.style.top = '-50px';
                }
            }, { passive: true });
        });
    }

    // ==========================================================================
    // Swipe Navigation (Between pages/tabs)
    // ==========================================================================

    function initSwipeNavigation() {
        const navContainers = document.querySelectorAll('[data-swipe-nav]');

        navContainers.forEach(function(container) {
            let startX = 0;
            let startY = 0;

            container.addEventListener('touchstart', function(e) {
                startX = e.touches[0].clientX;
                startY = e.touches[0].clientY;
            }, { passive: true });

            container.addEventListener('touchend', function(e) {
                const endX = e.changedTouches[0].clientX;
                const endY = e.changedTouches[0].clientY;

                const diffX = endX - startX;
                const diffY = endY - startY;

                // Ensure horizontal swipe is dominant
                if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > TOUCH_CONFIG.swipeThreshold) {
                    const direction = diffX > 0 ? 'right' : 'left';
                    handleSwipeNavigation(container, direction);
                }
            }, { passive: true });
        });
    }

    function handleSwipeNavigation(container, direction) {
        const navItems = container.querySelectorAll('[data-nav-item]');
        const activeIndex = Array.from(navItems).findIndex(function(item) {
            return item.classList.contains('active');
        });

        let newIndex;
        if (direction === 'left' && activeIndex < navItems.length - 1) {
            newIndex = activeIndex + 1;
        } else if (direction === 'right' && activeIndex > 0) {
            newIndex = activeIndex - 1;
        }

        if (newIndex !== undefined && navItems[newIndex]) {
            navItems[newIndex].click();
        }
    }

    // ==========================================================================
    // Long Press Handler
    // ==========================================================================

    function initLongPress() {
        const longPressElements = document.querySelectorAll('[data-long-press]');
        let pressTimer = null;

        longPressElements.forEach(function(el) {
            el.addEventListener('touchstart', function(e) {
                pressTimer = setTimeout(function() {
                    const action = el.dataset.longPress;
                    handleLongPress(el, action);
                }, TOUCH_CONFIG.holdDuration);
            }, { passive: true });

            el.addEventListener('touchend', function() {
                clearTimeout(pressTimer);
            }, { passive: true });

            el.addEventListener('touchmove', function() {
                clearTimeout(pressTimer);
            }, { passive: true });
        });
    }

    function handleLongPress(element, action) {
        // Haptic feedback (if supported)
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }

        switch (action) {
            case 'context-menu':
                // Show context menu
                const menu = element.querySelector('.context-menu');
                if (menu) {
                    menu.classList.add('show');
                }
                break;

            case 'edit':
                // Enter edit mode
                element.classList.add('editing');
                break;

            case 'select':
                // Toggle selection
                const checkbox = element.querySelector('input[type="checkbox"]');
                if (checkbox) {
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change'));
                }
                break;
        }
    }

    // ==========================================================================
    // Double Tap Handler
    // ==========================================================================

    function initDoubleTap() {
        const doubleTapElements = document.querySelectorAll('[data-double-tap]');
        let lastTap = 0;

        doubleTapElements.forEach(function(el) {
            el.addEventListener('touchend', function(e) {
                const currentTime = new Date().getTime();
                const tapLength = currentTime - lastTap;

                if (tapLength < 300 && tapLength > 0) {
                    // Double tap detected
                    const action = el.dataset.doubleTap;
                    handleDoubleTap(el, action);
                    e.preventDefault();
                }

                lastTap = currentTime;
            }, { passive: false });
        });
    }

    function handleDoubleTap(element, action) {
        switch (action) {
            case 'zoom':
                element.classList.toggle('zoomed');
                break;

            case 'like':
                // Heart animation
                const heart = document.createElement('div');
                heart.className = 'double-tap-heart';
                heart.innerHTML = '❤️';
                element.appendChild(heart);
                setTimeout(function() { heart.remove(); }, 1000);
                break;
        }
    }

    // ==========================================================================
    // Utility: Add swipe indicator to elements
    // ==========================================================================

    window.addSwipeIndicator = function(element, direction, icon) {
        direction = direction || 'right';
        icon = icon || 'bi-chevron-right';

        const indicator = document.createElement('div');
        indicator.className = 'swipe-action-indicator';
        indicator.innerHTML = '<i class="bi ' + icon + '"></i>';
        indicator.style.cssText = [
            'position: absolute;',
            direction + ': 10px;',
            'top: 50%;',
            'transform: translateY(-50%);',
            'opacity: 0;',
            'transition: opacity 0.2s;',
            'font-size: 1.5rem;',
            'color: var(--tm-success);'
        ].join('');

        element.style.position = 'relative';
        element.appendChild(indicator);
    };

})();
