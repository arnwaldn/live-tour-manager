"""
API helper functions — pagination, error formatting, response builders.
"""
from flask import request, jsonify


def paginate_query(query, schema, default_per_page=20, max_per_page=100):
    """Apply offset-based pagination to a SQLAlchemy query.

    Query params:
        page (int): Page number (1-indexed, default 1)
        per_page (int): Items per page (default 20, max 100)

    Returns:
        JSON-ready dict with data, meta, and links.
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', default_per_page, type=int)

    # Clamp values
    page = max(1, page)
    per_page = max(1, min(per_page, max_per_page))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    total_pages = pagination.pages if pagination.pages else 1

    # Build links
    base_url = request.base_url
    links = {
        'self': f'{base_url}?page={page}&per_page={per_page}',
    }
    if pagination.has_next:
        links['next'] = f'{base_url}?page={page + 1}&per_page={per_page}'
    if pagination.has_prev:
        links['prev'] = f'{base_url}?page={page - 1}&per_page={per_page}'
    links['first'] = f'{base_url}?page=1&per_page={per_page}'
    links['last'] = f'{base_url}?page={total_pages}&per_page={per_page}'

    return {
        'data': schema.dump(pagination.items, many=True),
        'meta': {
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
        },
        'links': links,
    }


def api_error(code, message, status=400, details=None):
    """Build a standard API error response."""
    error_body = {
        'error': {
            'code': code,
            'message': message,
        }
    }
    if details:
        error_body['error']['details'] = details
    return jsonify(error_body), status


def api_success(data, status=200):
    """Build a standard API success response."""
    return jsonify({'data': data}), status
