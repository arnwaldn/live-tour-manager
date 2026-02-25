"""
Flask extensions initialization.
Extensions are initialized here and bound to the app in the factory.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_caching import Cache

# Database
db = SQLAlchemy()

# Database migrations
migrate = Migrate()

# User session management
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'warning'
login_manager.session_protection = 'strong'

# CSRF Protection
csrf = CSRFProtect()

# Rate Limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=['100 per minute']
)

# Email
mail = Mail()

# Caching
cache = Cache()


def init_extensions(app):
    """Initialize all extensions with the Flask app."""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)
    cache.init_app(app)

    # Exempt API blueprint from CSRF (uses JWT, not cookies)
    from app.blueprints.api import api_bp
    csrf.exempt(api_bp)

    # User loader for Flask-Login
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login.

        Returns None for deactivated users to force automatic logout.
        This ensures users deactivated by a manager lose access immediately.
        """
        user = User.query.get(int(user_id))
        # Force logout if user is deactivated or deleted
        if user and user.is_active:
            return user
        return None
