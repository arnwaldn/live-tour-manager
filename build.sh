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
import os, sys
db_url = os.environ.get('DATABASE_URL', '')
if not db_url:
    print('ERROR: DATABASE_URL not set. Cannot proceed.')
    sys.exit(1)
# Fix Render's postgres:// → postgresql:// (required by SQLAlchemy 2.x)
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
    os.environ['DATABASE_URL'] = db_url
    print('Fixed DATABASE_URL scheme: postgres:// → postgresql://')
from app import create_app
from app.extensions import db
app = create_app()
with app.app_context():
    try:
        result = db.session.execute(db.text('SELECT 1'))
        print('Database connection: OK')
    except Exception as e:
        print(f'Database connection FAILED: {e}')
        sys.exit(1)
"

echo ""
echo "=== Step 3: Running database migrations ==="
echo "Checking current migration status..."
flask db current || echo "No current migration (fresh database)"

echo "Applying migrations..."
flask db upgrade
echo "Migration completed."

echo ""
echo "=== Step 4: Verifying migration and creating missing tables ==="
python -c "
from app import create_app
from app.extensions import db
app = create_app()
with app.app_context():
    # Check alembic_version
    has_alembic = False
    try:
        result = db.session.execute(db.text('SELECT version_num FROM alembic_version'))
        version = result.fetchone()
        if version:
            print(f'Current Alembic version: {version[0]}')
            has_alembic = True
        else:
            print('WARNING: No alembic version found!')
        db.session.rollback()
    except Exception as e:
        print(f'Alembic table missing: {e}')
        db.session.rollback()

    # Check if users table exists (critical table)
    has_users = False
    try:
        result = db.session.execute(db.text('SELECT 1 FROM users LIMIT 1'))
        has_users = True
        print('Users table: EXISTS')
        db.session.rollback()
    except Exception as e:
        print(f'Users table: MISSING - {e}')
        db.session.rollback()

    # If critical tables missing, create all tables
    if not has_users:
        print('Critical tables missing! Creating all tables from models...')
        db.create_all()
        print('Tables created via db.create_all()')

        # Verify users table now exists
        try:
            result = db.session.execute(db.text('SELECT 1 FROM users LIMIT 1'))
            print('Users table created successfully!')
            db.session.rollback()
        except Exception as e:
            print(f'ERROR: Users table still missing after create_all: {e}')
            db.session.rollback()
            exit(1)
    else:
        print('All critical tables exist.')
"

echo ""
echo "=== Step 5: Seeding default data ==="
flask seed-professions || echo "Professions already seeded or table not ready"

echo ""
echo "============================================"
echo "  Build completed successfully!"
echo "============================================"
