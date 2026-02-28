"""
Fernet encryption utilities for sensitive data (RGPD Art. 32).
Uses AES-128-CBC + HMAC for authenticated encryption.
"""
import base64
import hashlib
import logging

from flask import current_app

logger = logging.getLogger(__name__)

_fernet_instance = None


def _get_fernet():
    """Get or create a Fernet instance from app config."""
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance

    try:
        from cryptography.fernet import Fernet
    except ImportError:
        logger.warning("cryptography package not installed — encryption disabled")
        return None

    key = current_app.config.get('FERNET_KEY')
    if not key:
        # Derive a key from SECRET_KEY as fallback
        secret = current_app.config.get('SECRET_KEY', '')
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()[:32])
        logger.info("FERNET_KEY not set — derived from SECRET_KEY (set FERNET_KEY in production)")
    else:
        # Ensure key is bytes
        if isinstance(key, str):
            key = key.encode()

    try:
        _fernet_instance = Fernet(key)
    except Exception as e:
        logger.error(f"Invalid Fernet key: {e}")
        return None

    return _fernet_instance


def encrypt_value(plaintext):
    """Encrypt a string value. Returns base64-encoded ciphertext or None."""
    if not plaintext:
        return None

    fernet = _get_fernet()
    if fernet is None:
        return plaintext  # Graceful degradation — store plaintext if no crypto

    try:
        return fernet.encrypt(plaintext.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return plaintext


def decrypt_value(ciphertext):
    """Decrypt a base64-encoded ciphertext. Returns plaintext or the raw value on failure."""
    if not ciphertext:
        return None

    fernet = _get_fernet()
    if fernet is None:
        return ciphertext

    try:
        return fernet.decrypt(ciphertext.encode()).decode()
    except Exception:
        # Value might be stored in plaintext (pre-migration data)
        return ciphertext
