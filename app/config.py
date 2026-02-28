"""
Configuration classes for GigRoute application.
Supports Development, Testing, and Production environments.
"""
import os
from datetime import timedelta


class Config:
    """Base configuration with default settings."""

    # Security - SECRET_KEY is validated in production config
    # WARNING: Never use the fallback key in production!
    _secret_key = os.environ.get('SECRET_KEY')
    if not _secret_key:
        import warnings
        warnings.warn(
            "SECRET_KEY not set in environment. Using insecure default key. "
            "Set SECRET_KEY environment variable for production!",
            UserWarning
        )
        _secret_key = 'dev-secret-key-change-in-production'
    SECRET_KEY = _secret_key
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Engine options: PostgreSQL-specific settings only when not using SQLite
    SQLALCHEMY_ENGINE_OPTIONS = (
        {}
        if os.environ.get('DATABASE_URL', '').startswith('sqlite')
        else {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'connect_args': {'client_encoding': 'utf8'},
        }
    )

    # Rate Limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_DEFAULT = os.environ.get('RATE_LIMIT_GLOBAL', '100/minute')
    RATELIMIT_HEADERS_ENABLED = True

    # Account Lockout
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5))
    LOCKOUT_DURATION_MINUTES = int(os.environ.get('LOCKOUT_DURATION_MINUTES', 15))

    # Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@gigroute.app')

    # Caching
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300

    # Pagination
    ITEMS_PER_PAGE = 20

    # File Upload (for future use)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # Geoapify API Key (for international address autocomplete)
    # France uses API Adresse (free, unlimited), international uses Geoapify (3000/day free)
    GEOAPIFY_API_KEY = os.environ.get('GEOAPIFY_API_KEY')

    # JWT (separate key for API tokens — falls back to SECRET_KEY if not set)
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')

    # Fernet encryption key for sensitive settings (falls back to SECRET_KEY-derived key)
    FERNET_KEY = os.environ.get('FERNET_KEY')

    # Stripe (SaaS billing)
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
    STRIPE_PRO_PRICE_ID = os.environ.get('STRIPE_PRO_PRICE_ID')
    APP_URL = os.environ.get('APP_URL', 'http://localhost:5000')

    # Sentry (error monitoring — production only)
    SENTRY_DSN = os.environ.get('SENTRY_DSN')


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:postgres@localhost:5432/tour_manager_dev'

    # More verbose logging in development
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False  # Disable CSRF for testing

    # Use SQLite in-memory for tests (portable, no external DB required)
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///:memory:'

    # SQLite-specific settings
    SQLALCHEMY_ENGINE_OPTIONS = {}

    # Disable rate limiting in tests
    RATELIMIT_ENABLED = False

    # Stripe test values
    STRIPE_SECRET_KEY = 'sk_test_fake_key_for_testing'
    STRIPE_PUBLISHABLE_KEY = 'pk_test_fake_key_for_testing'
    STRIPE_WEBHOOK_SECRET = 'whsec_test_fake_secret'
    STRIPE_PRO_PRICE_ID = 'price_test_pro_monthly'
    APP_URL = 'http://localhost'

    # Use in-memory cache for tests
    CACHE_TYPE = 'SimpleCache'

    # Server name for url_for in tests
    SERVER_NAME = 'localhost'
    PREFERRED_URL_SCHEME = 'http'


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False

    # SECRET_KEY and DATABASE_URL - validated in init_app (not at import time)
    SECRET_KEY = os.environ.get('SECRET_KEY')
    # Fix postgres:// → postgresql:// (Render/Neon use postgres://, SQLAlchemy 2.x requires postgresql://)
    _db_url = os.environ.get('DATABASE_URL', '')
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url or None

    # Enhanced security for production
    SESSION_COOKIE_SECURE = True

    # Redis for rate limiting (REQUIRED in production for multi-worker consistency)
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')

    # Redis for caching (REQUIRED in production for multi-worker consistency)
    _redis_url = os.environ.get('REDIS_URL')
    CACHE_TYPE = 'RedisCache' if _redis_url else 'SimpleCache'
    CACHE_REDIS_URL = _redis_url
    CACHE_DEFAULT_TIMEOUT = 600

    # Database connection pool (production-tuned)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_size': 10,
        'max_overflow': 20,
        'connect_args': {'client_encoding': 'utf8'},
    }

    @classmethod
    def init_app(cls, app):
        """Production-specific initialization with validation."""
        import logging
        logger = logging.getLogger(__name__)

        # Validate required environment variables at runtime
        if not cls.SECRET_KEY:
            raise ValueError("SECRET_KEY environment variable is required in production")
        if not cls.SQLALCHEMY_DATABASE_URI:
            raise ValueError("DATABASE_URL environment variable is required in production")

        # Warn about Stripe keys if any are set (billing partially configured)
        stripe_keys = ['STRIPE_SECRET_KEY', 'STRIPE_PUBLISHABLE_KEY', 'STRIPE_WEBHOOK_SECRET', 'STRIPE_PRO_PRICE_ID']
        set_keys = [k for k in stripe_keys if os.environ.get(k)]
        missing_keys = [k for k in stripe_keys if not os.environ.get(k)]
        if set_keys and missing_keys:
            raise ValueError(
                f"Stripe partially configured. Missing: {', '.join(missing_keys)}. "
                "Set all 4 Stripe keys or none."
            )

        # Warn about Redis (critical for multi-worker deployments)
        if not os.environ.get('REDIS_URL'):
            logger.warning(
                "REDIS_URL not set — cache and rate limiter use in-memory storage. "
                "Each Gunicorn worker has independent counters and cache. "
                "Set REDIS_URL for production multi-worker consistency."
            )

        # Warn about Sentry
        if not os.environ.get('SENTRY_DSN'):
            logger.warning(
                "SENTRY_DSN not set — error tracking disabled. "
                "Set SENTRY_DSN for production error monitoring."
            )

        # Warn about JWT key sharing SECRET_KEY
        if not os.environ.get('JWT_SECRET_KEY'):
            logger.warning(
                "JWT_SECRET_KEY not set — JWT tokens signed with SECRET_KEY. "
                "Set JWT_SECRET_KEY for key separation."
            )


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
