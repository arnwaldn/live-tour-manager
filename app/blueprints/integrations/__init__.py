"""
Integrations blueprint for external calendar services.
Supports Google Calendar and Microsoft Outlook OAuth2 integrations.
"""
from flask import Blueprint

integrations_bp = Blueprint('integrations', __name__)

from app.blueprints.integrations import google_calendar, outlook_calendar
