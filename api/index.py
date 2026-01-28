# =============================================================================
# Tour Manager - Vercel Serverless Entry Point
# Flask WSGI Application wrapper for Vercel Python Runtime
# =============================================================================

import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

# Create Flask app instance
app = create_app()

# Vercel Python runtime expects 'app' to be a WSGI application
# The app variable is automatically used by Vercel's @vercel/python builder
