#!/usr/bin/env bash
# =============================================================================
# GigRoute - Build Script (Render.com)
# Installs dependencies and runs database migrations
# =============================================================================
set -o errexit  # Exit on error

echo "============================================"
echo "  GigRoute - Build Script"
echo "============================================"

echo ""
echo "=== Step 1: Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Step 2: Checking database connection ==="
python -c "
import os, sys
db_url = os.environ.get('DATABASE_URL', '')
if not db_url:
    print('WARNING: DATABASE_URL not set. Skipping DB checks (build-time only).')
    sys.exit(0)
# Fix Render's postgres:// → postgresql:// (required by SQLAlchemy 2.x)
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
    os.environ['DATABASE_URL'] = db_url
    print('Fixed DATABASE_URL scheme: postgres:// → postgresql://')
from app import create_app
from app.extensions import db
app = create_app('production')
with app.app_context():
    try:
        db.session.execute(db.text('SELECT 1'))
        print('Database connection: OK')
    except Exception as e:
        print(f'Database connection FAILED: {e}')
        sys.exit(1)
"

echo ""
echo "=== Step 3: Running database migrations ==="
flask db upgrade || {
    echo "ERROR: Migrations failed. Check DATABASE_URL and migration files."
    exit 1
}
echo "Migrations applied successfully."

echo ""
echo "=== Step 4: Initializing default data ==="
flask init-db || echo "Roles already initialized or table not ready"
flask seed-professions || echo "Professions already seeded or table not ready"

echo ""
echo "============================================"
echo "  Build completed successfully!"
echo "============================================"
