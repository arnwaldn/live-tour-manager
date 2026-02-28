# =============================================================================
# GigRoute E2E Tests — Playwright Configuration
# =============================================================================
#
# Setup:
#   pip install -r requirements-e2e.txt
#   playwright install chromium
#
# Run:
#   pytest tests/e2e/ -m e2e --headed   (visible browser)
#   pytest tests/e2e/ -m e2e            (headless)
#
# =============================================================================

import os
import pytest
import threading
import time

from app import create_app
from app.extensions import db


@pytest.fixture(scope="session")
def app_server():
    """Start the Flask app on a local port for E2E testing."""
    app = create_app('testing')

    # Use a file-based SQLite so the server and test share state
    test_db_path = os.path.join(os.path.dirname(__file__), 'e2e_test.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{test_db_path}'

    with app.app_context():
        db.create_all()

    # Run server in background thread
    port = 5199
    server_thread = threading.Thread(
        target=lambda: app.run(port=port, use_reloader=False),
        daemon=True,
    )
    server_thread.start()
    time.sleep(1)  # Wait for server to start

    yield f'http://127.0.0.1:{port}'

    # Cleanup
    with app.app_context():
        db.drop_all()
        db.engine.dispose()
    if os.path.exists(test_db_path):
        os.unlink(test_db_path)


@pytest.fixture(scope="session")
def base_url(app_server):
    """Base URL for Playwright tests."""
    return app_server
