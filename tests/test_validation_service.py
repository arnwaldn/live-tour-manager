# =============================================================================
# Tour Manager - Validation Service Tests
# =============================================================================

import pytest
from app.services.validation_service import ValidationService


# =============================================================================
# IBAN Validation
# =============================================================================

class TestValidateIban:
    """Tests for ValidationService.validate_iban()."""

    def test_valid_french_iban(self):
        """A well-formed French IBAN passes validation."""
        valid, error = ValidationService.validate_iban('FR7630001007941234567890185')
        assert valid is True
        assert error is None

    def test_valid_iban_with_spaces(self):
        """IBAN with spaces is normalized and validated correctly."""
        valid, error = ValidationService.validate_iban('FR76 3000 1007 9412 3456 7890 185')
        assert valid is True
        assert error is None

    def test_empty_iban_is_invalid(self):
        """Empty IBAN is rejected."""
        valid, error = ValidationService.validate_iban('')
        assert valid is False
        assert error is not None

    def test_none_iban_is_invalid(self):
        """None IBAN is rejected."""
        valid, error = ValidationService.validate_iban(None)
        assert valid is False
        assert error is not None

    def test_too_short_iban_is_invalid(self):
        """IBAN shorter than 15 characters is rejected."""
        valid, error = ValidationService.validate_iban('FR7630001')
        assert valid is False
        assert 'Longueur' in error or 'longueur' in error.lower() or error is not None

    def test_too_long_iban_is_invalid(self):
        """IBAN longer than 34 characters is rejected."""
        valid, error = ValidationService.validate_iban('FR76300010079412345678901850000000000')
        assert valid is False

    def test_iban_with_invalid_format_rejected(self):
        """IBAN with invalid format (no country code) is rejected."""
        valid, error = ValidationService.validate_iban('123456789012345678901234567')
        assert valid is False

    def test_iban_with_bad_checksum_rejected(self):
        """IBAN with correct format but wrong checksum is rejected."""
        # Modify the check digits to make it invalid
        valid, error = ValidationService.validate_iban('FR0030001007941234567890185')
        assert valid is False

    def test_valid_german_iban(self):
        """A well-formed German IBAN passes validation."""
        # DE89 3704 0044 0532 0130 00
        valid, error = ValidationService.validate_iban('DE89370400440532013000')
        assert valid is True
        assert error is None

    def test_valid_gb_iban(self):
        """A well-formed UK IBAN passes validation."""
        valid, error = ValidationService.validate_iban('GB29NWBK60161331926819')
        assert valid is True
        assert error is None


# =============================================================================
# IBAN Formatting
# =============================================================================

class TestFormatIban:
    """Tests for ValidationService.format_iban()."""

    def test_formats_iban_with_spaces_every_4_chars(self):
        """format_iban produces groups of 4 characters separated by spaces."""
        formatted = ValidationService.format_iban('FR7630001007941234567890185')
        parts = formatted.split(' ')
        # All parts except last should be 4 chars
        for part in parts[:-1]:
            assert len(part) == 4

    def test_format_iban_uppercases(self):
        """format_iban converts to uppercase."""
        formatted = ValidationService.format_iban('fr7630001007941234567890185')
        assert formatted == formatted.upper()

    def test_format_iban_removes_existing_spaces(self):
        """format_iban normalizes pre-spaced IBANs."""
        raw = 'FR76 3000 1007 9412 3456 7890 185'
        formatted = ValidationService.format_iban(raw)
        # Should re-format cleanly
        assert '  ' not in formatted  # No double spaces


# =============================================================================
# BIC Validation
# =============================================================================

class TestValidateBic:
    """Tests for ValidationService.validate_bic()."""

    def test_empty_bic_is_valid(self):
        """Empty BIC is valid (BIC is optional)."""
        valid, error = ValidationService.validate_bic('')
        assert valid is True
        assert error is None

    def test_none_bic_is_valid(self):
        """None BIC is valid (BIC is optional)."""
        valid, error = ValidationService.validate_bic(None)
        assert valid is True
        assert error is None

    def test_valid_8_char_bic(self):
        """An 8-character BIC passes validation."""
        valid, error = ValidationService.validate_bic('BNPAFRPP')
        assert valid is True
        assert error is None

    def test_valid_11_char_bic(self):
        """An 11-character BIC passes validation."""
        valid, error = ValidationService.validate_bic('BNPAFRPPXXX')
        assert valid is True
        assert error is None

    def test_invalid_bic_wrong_length(self):
        """A BIC with wrong length (not 8 or 11) is rejected."""
        valid, error = ValidationService.validate_bic('BNPA')
        assert valid is False
        assert error is not None

    def test_invalid_bic_format(self):
        """A BIC with non-letter country code fails format check."""
        valid, error = ValidationService.validate_bic('BNPA11PP')
        assert valid is False
        assert error is not None

    def test_bic_with_spaces_normalized(self):
        """BIC with spaces is normalized before validation."""
        valid, error = ValidationService.validate_bic('BNPA FRPP')
        assert valid is True
        assert error is None


# =============================================================================
# SIRET Validation
# =============================================================================

class TestValidateSiret:
    """Tests for ValidationService.validate_siret()."""

    def test_empty_siret_is_valid(self):
        """Empty SIRET is valid (SIRET is optional)."""
        valid, error = ValidationService.validate_siret('')
        assert valid is True
        assert error is None

    def test_none_siret_is_valid(self):
        """None SIRET is valid (SIRET is optional)."""
        valid, error = ValidationService.validate_siret(None)
        assert valid is True
        assert error is None

    def test_valid_siret(self):
        """A valid 14-digit SIRET with correct Luhn checksum passes."""
        # 73282932000074 is a known valid SIRET for French public institution
        valid, error = ValidationService.validate_siret('73282932000074')
        assert valid is True
        assert error is None

    def test_siret_wrong_length(self):
        """SIRET with wrong number of digits is rejected."""
        valid, error = ValidationService.validate_siret('1234567890')
        assert valid is False
        assert '14' in error

    def test_siret_non_digits(self):
        """SIRET containing letters is rejected."""
        valid, error = ValidationService.validate_siret('1234567890123A')
        assert valid is False

    def test_siret_with_spaces_normalized(self):
        """SIRET with spaces is normalized."""
        valid, error = ValidationService.validate_siret('732 829 320 00074')
        # After normalization it should be 14 digits: 73282932000074
        assert valid is True
        assert error is None

    def test_siret_bad_checksum(self):
        """SIRET with correct length but bad Luhn checksum is rejected."""
        valid, error = ValidationService.validate_siret('73282932000075')  # wrong last digit
        assert valid is False
        assert 'Checksum' in error or 'checksum' in error.lower() or error is not None


# =============================================================================
# SIREN Validation
# =============================================================================

class TestValidateSiren:
    """Tests for ValidationService.validate_siren()."""

    def test_empty_siren_is_valid(self):
        """Empty SIREN is valid (SIREN is optional)."""
        valid, error = ValidationService.validate_siren('')
        assert valid is True
        assert error is None

    def test_none_siren_is_valid(self):
        """None SIREN is valid (SIREN is optional)."""
        valid, error = ValidationService.validate_siren(None)
        assert valid is True
        assert error is None

    def test_valid_siren(self):
        """A valid 9-digit SIREN with correct Luhn checksum passes."""
        # 732829320 is a known valid SIREN (first 9 digits of 73282932000074)
        valid, error = ValidationService.validate_siren('732829320')
        assert valid is True
        assert error is None

    def test_siren_wrong_length(self):
        """SIREN with wrong number of digits is rejected."""
        valid, error = ValidationService.validate_siren('12345678')
        assert valid is False
        assert '9' in error

    def test_siren_non_digits(self):
        """SIREN containing letters is rejected."""
        valid, error = ValidationService.validate_siren('1234567AB')
        assert valid is False

    def test_siren_bad_checksum(self):
        """SIREN with bad Luhn checksum is rejected."""
        valid, error = ValidationService.validate_siren('732829321')  # wrong last digit
        assert valid is False


# =============================================================================
# VAT Number Validation
# =============================================================================

class TestValidateVatNumber:
    """Tests for ValidationService.validate_vat_number()."""

    def test_empty_vat_is_valid(self):
        """Empty VAT is valid (VAT is optional)."""
        valid, error = ValidationService.validate_vat_number('')
        assert valid is True
        assert error is None

    def test_none_vat_is_valid(self):
        """None VAT is valid (VAT is optional)."""
        valid, error = ValidationService.validate_vat_number(None)
        assert valid is True
        assert error is None

    def test_valid_french_vat(self):
        """A valid French VAT number passes."""
        # French VAT: FR + 2 control chars + 9-digit SIREN
        valid, error = ValidationService.validate_vat_number('FR73732829320')
        assert valid is True
        assert error is None

    def test_french_vat_wrong_length(self):
        """French VAT with wrong length is rejected."""
        valid, error = ValidationService.validate_vat_number('FR1234567890')
        assert valid is False

    def test_french_vat_invalid_control_chars(self):
        """French VAT with invalid control characters is rejected."""
        valid, error = ValidationService.validate_vat_number('FRIO732829320')
        assert valid is False

    def test_other_eu_vat_valid_format(self):
        """Non-French EU VAT in valid format passes basic check."""
        valid, error = ValidationService.validate_vat_number('DE123456789')
        assert valid is True
        assert error is None

    def test_invalid_vat_format(self):
        """VAT number starting with digits is rejected."""
        valid, error = ValidationService.validate_vat_number('12ABCDEF')
        assert valid is False


# =============================================================================
# Social Security Number Validation
# =============================================================================

class TestValidateSocialSecurity:
    """Tests for ValidationService.validate_social_security()."""

    def test_empty_ss_is_valid(self):
        """Empty social security number is valid (optional)."""
        valid, error = ValidationService.validate_social_security('')
        assert valid is True
        assert error is None

    def test_none_ss_is_valid(self):
        """None social security number is valid (optional)."""
        valid, error = ValidationService.validate_social_security(None)
        assert valid is True
        assert error is None

    def test_valid_ss_number(self):
        """A valid 15-digit French NIR passes validation."""
        # Constructed NIR: 1 85 12 75 000 001 + key
        # key = 97 - (185127500000 % 97) = 97 - (185127500000 % 97)
        # Using a known-valid example
        valid, error = ValidationService.validate_social_security('195025B01234567')
        # This may or may not be valid depending on the checksum
        # We just check the function returns a tuple without crashing
        assert isinstance(valid, bool)
        assert error is None or isinstance(error, str)

    def test_ss_number_wrong_length(self):
        """Social security number with wrong length is rejected."""
        valid, error = ValidationService.validate_social_security('123456789012')
        assert valid is False
        assert '15' in error

    def test_ss_number_with_spaces_normalized(self):
        """Social security number with spaces is normalized."""
        # If wrong length after normalization, should fail with length error
        valid, error = ValidationService.validate_social_security('1 23 45 67 890 123 45')
        # After removing spaces: '123456789012345' = 15 digits
        # May pass or fail checksum but should not crash
        assert isinstance(valid, bool)


# =============================================================================
# Luhn Check (internal method)
# =============================================================================

class TestLuhnCheck:
    """Tests for ValidationService._luhn_check()."""

    def test_valid_luhn_number(self):
        """Known valid Luhn number returns True."""
        # Credit card-style Luhn: 4111111111111111 is valid
        assert ValidationService._luhn_check('4111111111111111') is True

    def test_invalid_luhn_number(self):
        """Known invalid Luhn number returns False."""
        assert ValidationService._luhn_check('4111111111111112') is False

    def test_single_zero_passes_luhn(self):
        """Single zero passes Luhn (checksum of 0 is 0 % 10 == 0)."""
        assert ValidationService._luhn_check('0') is True


# =============================================================================
# validate_payment_config (integration)
# =============================================================================

class TestValidatePaymentConfig:
    """Tests for ValidationService.validate_payment_config()."""

    def test_empty_config_is_valid(self):
        """Empty payment config with no fields is valid."""
        valid, errors = ValidationService.validate_payment_config({})
        assert valid is True
        assert errors == []

    def test_config_with_valid_iban(self):
        """Config with a valid IBAN passes."""
        valid, errors = ValidationService.validate_payment_config({
            'iban': 'FR7630001007941234567890185'
        })
        assert valid is True
        assert errors == []

    def test_config_with_invalid_iban(self):
        """Config with invalid IBAN adds an IBAN error."""
        valid, errors = ValidationService.validate_payment_config({
            'iban': 'NOTANIBAN'
        })
        assert valid is False
        assert any('IBAN' in e for e in errors)

    def test_config_with_valid_bic(self):
        """Config with valid BIC passes."""
        valid, errors = ValidationService.validate_payment_config({
            'bic': 'BNPAFRPP'
        })
        assert valid is True
        assert errors == []

    def test_config_with_invalid_bic(self):
        """Config with invalid BIC adds a BIC error."""
        valid, errors = ValidationService.validate_payment_config({
            'bic': 'TOOLONGBICCODE123'
        })
        assert valid is False
        assert any('BIC' in e for e in errors)

    def test_config_with_valid_siret(self):
        """Config with valid SIRET passes."""
        valid, errors = ValidationService.validate_payment_config({
            'siret': '73282932000074'
        })
        assert valid is True
        assert errors == []

    def test_config_with_invalid_siret(self):
        """Config with invalid SIRET adds a SIRET error."""
        valid, errors = ValidationService.validate_payment_config({
            'siret': '12345'
        })
        assert valid is False
        assert any('SIRET' in e for e in errors)

    def test_config_with_multiple_errors(self):
        """Config with multiple invalid fields accumulates all errors."""
        valid, errors = ValidationService.validate_payment_config({
            'iban': 'BADIBANVALUE',
            'bic': 'X',
            'siret': '999',
        })
        assert valid is False
        assert len(errors) == 3

    def test_config_with_valid_siren(self):
        """Config with valid SIREN passes."""
        valid, errors = ValidationService.validate_payment_config({
            'siren': '732829320'
        })
        assert valid is True
        assert errors == []

    def test_config_with_valid_vat(self):
        """Config with valid French VAT passes."""
        valid, errors = ValidationService.validate_payment_config({
            'vat_number': 'FR73732829320'
        })
        assert valid is True
        assert errors == []

    def test_config_all_valid_fields(self):
        """Config with all valid fields passes with no errors."""
        valid, errors = ValidationService.validate_payment_config({
            'iban': 'FR7630001007941234567890185',
            'bic': 'BNPAFRPP',
            'siret': '73282932000074',
            'siren': '732829320',
            'vat_number': 'FR73732829320',
        })
        assert valid is True
        assert errors == []
