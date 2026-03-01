"""
Organization context helpers for multi-tenancy.
All tenant-scoped queries should use get_current_org_id() for filtering.

For query filtering, use the helpers:
- org_filter_kwargs()  — for filter_by(): Model.query.filter_by(**org_filter_kwargs())
- org_scope(Model)     — for filter():    query.filter(org_scope(Model))

Both return no-op filters when org context is not set (pre-migration compat).
"""


def get_current_org_id():
    """Get current organization ID from session.

    Returns None if no org context is set (e.g., unauthenticated requests,
    CLI commands, or users without an organization).
    """
    from flask import session
    return session.get('current_org_id')


def org_filter_kwargs():
    """Return {'org_id': id} for filter_by(), or {} if no org context.

    Pre-migration safe: when org context isn't set, the filter is skipped
    entirely rather than generating WHERE org_id IS NULL (which matches nothing).

    Usage:
        Venue.query.filter_by(**org_filter_kwargs())
        Band.query.filter_by(id=band_id, **org_filter_kwargs())
    """
    org_id = get_current_org_id()
    if org_id is not None:
        return {'org_id': org_id}
    return {}


def org_scope(model_class):
    """Return SQLAlchemy filter clause for org scoping.

    Returns model.org_id == org_id when org context is set,
    or true() (no-op) when not set (pre-migration compat).

    Usage:
        query.filter(org_scope(Venue))
        Band.query.filter(Band.id.in_(ids), org_scope(Band))
    """
    from sqlalchemy import true
    org_id = get_current_org_id()
    if org_id is not None:
        return model_class.org_id == org_id
    return true()


def get_current_org():
    """Get the current Organization object from session context."""
    org_id = get_current_org_id()
    if org_id:
        from app.models.organization import Organization
        return Organization.query.get(org_id)
    return None


def set_current_org(org_id):
    """Set the current organization in session (called at login)."""
    from flask import session
    session['current_org_id'] = org_id


def clear_current_org():
    """Clear org context from session (called at logout)."""
    from flask import session
    session.pop('current_org_id', None)
