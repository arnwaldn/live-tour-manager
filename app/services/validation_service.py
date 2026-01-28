"""
Validation service for French administrative identifiers.
Handles IBAN, BIC, SIRET, SIREN validation.
"""
import re
from typing import Tuple, Optional


class ValidationService:
    """Service for validating financial and administrative identifiers."""

    @staticmethod
    def validate_iban(iban: str) -> Tuple[bool, Optional[str]]:
        """
        Validate IBAN format and checksum.

        Args:
            iban: IBAN string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not iban:
            return False, "IBAN requis"

        # Remove spaces and convert to uppercase
        iban = iban.replace(' ', '').replace('-', '').upper()

        # Check length (French IBANs are 27 characters)
        if len(iban) < 15 or len(iban) > 34:
            return False, "Longueur IBAN invalide"

        # Check format: 2 letters country code, 2 digits check, rest alphanumeric
        if not re.match(r'^[A-Z]{2}[0-9]{2}[A-Z0-9]+$', iban):
            return False, "Format IBAN invalide"

        # Move first 4 characters to end
        rearranged = iban[4:] + iban[:4]

        # Convert letters to numbers (A=10, B=11, ..., Z=35)
        numeric = ''
        for char in rearranged:
            if char.isalpha():
                numeric += str(ord(char) - ord('A') + 10)
            else:
                numeric += char

        # Validate checksum (mod 97 should equal 1)
        if int(numeric) % 97 != 1:
            return False, "Checksum IBAN invalide"

        return True, None

    @staticmethod
    def format_iban(iban: str) -> str:
        """
        Format IBAN with spaces every 4 characters.

        Args:
            iban: Raw IBAN string

        Returns:
            Formatted IBAN (e.g., "FR76 3000 1007 9412 3456 7890 185")
        """
        iban = iban.replace(' ', '').replace('-', '').upper()
        return ' '.join([iban[i:i+4] for i in range(0, len(iban), 4)])

    @staticmethod
    def validate_bic(bic: str) -> Tuple[bool, Optional[str]]:
        """
        Validate BIC/SWIFT code format.

        Args:
            bic: BIC string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not bic:
            return True, None  # BIC is optional

        bic = bic.replace(' ', '').upper()

        # BIC is 8 or 11 characters
        if len(bic) not in (8, 11):
            return False, "BIC doit contenir 8 ou 11 caracteres"

        # Format: 4 letters (bank) + 2 letters (country) + 2 alphanumeric (location)
        # + optional 3 alphanumeric (branch)
        if not re.match(r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$', bic):
            return False, "Format BIC invalide"

        return True, None

    @staticmethod
    def validate_siret(siret: str) -> Tuple[bool, Optional[str]]:
        """
        Validate French SIRET number (14 digits).
        Uses Luhn algorithm for checksum validation.

        Args:
            siret: SIRET string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not siret:
            return True, None  # SIRET is optional

        # Remove spaces
        siret = siret.replace(' ', '').replace('-', '')

        # Must be 14 digits
        if len(siret) != 14:
            return False, "SIRET doit contenir 14 chiffres"

        if not siret.isdigit():
            return False, "SIRET ne doit contenir que des chiffres"

        # Luhn algorithm validation
        if not ValidationService._luhn_check(siret):
            return False, "Checksum SIRET invalide"

        return True, None

    @staticmethod
    def validate_siren(siren: str) -> Tuple[bool, Optional[str]]:
        """
        Validate French SIREN number (9 digits).
        SIREN is the first 9 digits of SIRET.

        Args:
            siren: SIREN string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not siren:
            return True, None  # SIREN is optional

        # Remove spaces
        siren = siren.replace(' ', '').replace('-', '')

        # Must be 9 digits
        if len(siren) != 9:
            return False, "SIREN doit contenir 9 chiffres"

        if not siren.isdigit():
            return False, "SIREN ne doit contenir que des chiffres"

        # Luhn algorithm validation
        if not ValidationService._luhn_check(siren):
            return False, "Checksum SIREN invalide"

        return True, None

    @staticmethod
    def validate_vat_number(vat: str) -> Tuple[bool, Optional[str]]:
        """
        Validate EU VAT number format.
        Focuses on French format (FR + 2 chars + 9 digits SIREN).

        Args:
            vat: VAT number string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not vat:
            return True, None  # VAT is optional

        vat = vat.replace(' ', '').upper()

        # French VAT: FR + 2 control chars + 9 digit SIREN
        if vat.startswith('FR'):
            if len(vat) != 13:
                return False, "TVA francaise doit contenir 13 caracteres (FR + 11)"

            control = vat[2:4]
            siren = vat[4:]

            # Control chars can be 2 digits, 1 letter + 1 digit, or 2 letters (except O and I)
            if not re.match(r'^([0-9]{2}|[0-9][A-HJ-NP-Z]|[A-HJ-NP-Z][0-9]|[A-HJ-NP-Z]{2})$', control):
                return False, "Cle de controle TVA invalide"

            if not siren.isdigit() or len(siren) != 9:
                return False, "SIREN dans TVA invalide"

            return True, None

        # Basic validation for other EU countries (2 letters + alphanumeric)
        if not re.match(r'^[A-Z]{2}[A-Z0-9]{2,12}$', vat):
            return False, "Format TVA invalide"

        return True, None

    @staticmethod
    def validate_social_security(ss_number: str) -> Tuple[bool, Optional[str]]:
        """
        Validate French social security number (NIR).
        Format: 1 digit (sex) + 2 digits (year) + 2 digits (month) + 5 digits (dept+commune)
                + 3 digits (order) + 2 digits (control key)

        Args:
            ss_number: Social security number to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not ss_number:
            return True, None  # Optional

        ss_number = ss_number.replace(' ', '').replace('-', '')

        # Must be 15 digits (13 + 2 control)
        if len(ss_number) != 15:
            return False, "Numero de secu doit contenir 15 chiffres"

        # Handle special case for Corsica (2A, 2B)
        ss_for_check = ss_number
        if ss_number[5:7] in ('2A', '2a'):
            ss_for_check = ss_number[:5] + '19' + ss_number[7:]
        elif ss_number[5:7] in ('2B', '2b'):
            ss_for_check = ss_number[:5] + '18' + ss_number[7:]

        if not ss_for_check.isdigit():
            return False, "Format numero de secu invalide"

        # Validate control key
        base = int(ss_for_check[:13])
        key = int(ss_for_check[13:])
        expected_key = 97 - (base % 97)

        if key != expected_key:
            return False, "Cle de controle numero de secu invalide"

        return True, None

    @staticmethod
    def _luhn_check(number: str) -> bool:
        """
        Luhn algorithm checksum validation.
        Used for SIRET/SIREN validation.

        Args:
            number: String of digits to validate

        Returns:
            True if checksum is valid
        """
        digits = [int(d) for d in number]
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]

        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(divmod(d * 2, 10))

        return checksum % 10 == 0

    @staticmethod
    def validate_payment_config(config_data: dict) -> Tuple[bool, list]:
        """
        Validate all fields in a payment configuration.

        Args:
            config_data: Dictionary with payment config fields

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Validate IBAN if provided
        if config_data.get('iban'):
            valid, error = ValidationService.validate_iban(config_data['iban'])
            if not valid:
                errors.append(f"IBAN: {error}")

        # Validate BIC if provided
        if config_data.get('bic'):
            valid, error = ValidationService.validate_bic(config_data['bic'])
            if not valid:
                errors.append(f"BIC: {error}")

        # Validate SIRET if provided
        if config_data.get('siret'):
            valid, error = ValidationService.validate_siret(config_data['siret'])
            if not valid:
                errors.append(f"SIRET: {error}")

        # Validate SIREN if provided
        if config_data.get('siren'):
            valid, error = ValidationService.validate_siren(config_data['siren'])
            if not valid:
                errors.append(f"SIREN: {error}")

        # Validate VAT number if provided
        if config_data.get('vat_number'):
            valid, error = ValidationService.validate_vat_number(config_data['vat_number'])
            if not valid:
                errors.append(f"TVA: {error}")

        # Validate social security number if provided
        if config_data.get('social_security_number'):
            valid, error = ValidationService.validate_social_security(
                config_data['social_security_number']
            )
            if not valid:
                errors.append(f"Numero secu: {error}")

        return len(errors) == 0, errors
