#!/usr/bin/env python
"""
Tour Manager Application Entry Point.
Run this file to start the development server.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app import create_app

# Create application instance
app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Get host and port from environment or use defaults
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

    print(f"""
    ============================================================
              GIGROUTE - Development Server
    ============================================================
      Running on: http://{host}:{port}
      Environment: {os.environ.get('FLASK_ENV', 'development')}
      Debug mode: {debug}
    ============================================================
    """)

    app.run(host=host, port=port, debug=debug)
