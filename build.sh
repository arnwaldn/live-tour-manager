#!/usr/bin/env bash
# Build script for Render deployment
# This script runs during the build phase

set -e  # Exit on any error

echo "============================================"
echo "  Tour Manager - Build Script v2"
echo "============================================"

echo ""
echo "=== Step 1: Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Step 2: Checking database connection ==="
python -c "
from app import create_app
from app.extensions import db
app = create_app()
with app.app_context():
    try:
        result = db.session.execute(db.text('SELECT 1'))
        print('Database connection: OK')
    except Exception as e:
        print(f'Database connection FAILED: {e}')
        exit(1)
"

echo ""
echo "=== Step 3: Running database migrations ==="
echo "Checking current migration status..."
flask db current || echo "No current migration (fresh database)"

echo "Applying migrations..."
flask db upgrade
echo "Migration completed."

echo ""
echo "=== Step 4: Verifying migration ==="
python -c "
from app import create_app
from app.extensions import db
app = create_app()
with app.app_context():
    try:
        result = db.session.execute(db.text('SELECT version_num FROM alembic_version'))
        version = result.fetchone()
        if version:
            print(f'Current Alembic version: {version[0]}')
        else:
            print('WARNING: No alembic version found!')
    except Exception as e:
        print(f'Migration verification FAILED: {e}')
        print('Attempting to create tables from scratch...')
        db.create_all()
        print('Tables created via db.create_all()')
"

echo ""
echo "=== Step 5: Seeding default data ==="
flask seed-professions || echo "Professions already seeded or table not ready"

echo ""
echo "============================================"
echo "  Build completed successfully!"
echo "============================================"
