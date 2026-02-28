# =============================================================================
# Tour Manager - Encryption Utility Tests
# =============================================================================

import pytest
from app.utils.encryption import encrypt_value, decrypt_value, _get_fernet


class TestEncryption:
    """Tests for Fernet encryption utilities (RGPD Art. 32)."""

    def test_encrypt_none_returns_none(self, app):
        assert encrypt_value(None) is None

    def test_encrypt_empty_string_returns_none(self, app):
        assert encrypt_value('') is None

    def test_encrypt_returns_different_value(self, app):
        plaintext = 'my-secret-api-key'
        encrypted = encrypt_value(plaintext)
        assert encrypted is not None
        assert encrypted != plaintext

    def test_decrypt_none_returns_none(self, app):
        assert decrypt_value(None) is None

    def test_decrypt_empty_string_returns_none(self, app):
        assert decrypt_value('') is None

    def test_encrypt_then_decrypt_roundtrip(self, app):
        plaintext = 'sensitive-data-12345'
        encrypted = encrypt_value(plaintext)
        decrypted = decrypt_value(encrypted)
        assert decrypted == plaintext

    def test_decrypt_invalid_ciphertext_returns_raw(self, app):
        """Graceful degradation: invalid ciphertext returns the raw value."""
        raw = 'not-encrypted-data'
        result = decrypt_value(raw)
        assert result == raw

    def test_encrypt_unicode(self, app):
        plaintext = 'Données sensibles avec accents éàü'
        encrypted = encrypt_value(plaintext)
        decrypted = decrypt_value(encrypted)
        assert decrypted == plaintext

    def test_get_fernet_derives_from_secret_key(self, app):
        """Fernet instance is created from SECRET_KEY when FERNET_KEY not set."""
        fernet = _get_fernet()
        assert fernet is not None

    def test_get_fernet_caches_instance(self, app):
        """Fernet instance is cached after first creation."""
        import app.utils.encryption as enc
        enc._fernet_instance = None  # Reset cache
        fernet1 = _get_fernet()
        fernet2 = _get_fernet()
        assert fernet1 is fernet2
        enc._fernet_instance = None  # Clean up
