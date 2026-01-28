"""
Decorators package.
Includes both legacy role-based and new access-level-based decorators.
"""
from app.decorators.auth import (
    # Access level decorators (v2.0)
    requires_access,
    requires_admin,
    requires_manager,
    requires_staff,
    # Legacy role decorators
    role_required,
    permission_required,
    # Resource access decorators
    band_access_required,
    tour_access_required,
    tour_edit_required,
    tour_stop_access_required,
    guestlist_manage_required,
    check_in_required,
    ajax_login_required,
)

__all__ = [
    # Access level decorators (v2.0)
    'requires_access',
    'requires_admin',
    'requires_manager',
    'requires_staff',
    # Legacy role decorators
    'role_required',
    'permission_required',
    # Resource access decorators
    'band_access_required',
    'tour_access_required',
    'tour_edit_required',
    'tour_stop_access_required',
    'guestlist_manage_required',
    'check_in_required',
    'ajax_login_required',
]
