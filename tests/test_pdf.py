# =============================================================================
# Tour Manager - PDF Generator Tests
# =============================================================================
# Tests for app/utils/pdf_generator.py - Settlement PDF generation
# Coverage target: 13% → 60%

import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from app.utils.pdf_generator import (
    format_currency,
    generate_settlement_pdf,
    _build_settlement_html,
    _get_fill_rate_class,
    _get_fill_rate_badge,
    _get_deal_type,
    PDF_AVAILABLE
)


# =============================================================================
# format_currency Tests (PDF module version)
# =============================================================================

class TestPdfFormatCurrency:
    """Tests for PDF module's format_currency function."""

    def test_format_euro(self):
        """Test EUR formatting."""
        result = format_currency(1500.50, 'EUR')
        assert '1,500.50' in result
        # Unicode euro symbol
        assert '\u20ac' in result or '€' in result

    def test_format_usd(self):
        """Test USD formatting."""
        result = format_currency(999.00, 'USD')
        assert '$' in result
        assert '999.00' in result

    def test_format_gbp(self):
        """Test GBP formatting."""
        result = format_currency(500.00, 'GBP')
        # Unicode pound symbol
        assert '\u00a3' in result or '£' in result

    def test_format_chf(self):
        """Test CHF formatting."""
        result = format_currency(750.00, 'CHF')
        assert 'CHF' in result


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestFillRateClass:
    """Tests for _get_fill_rate_class function."""

    def test_excellent_rate(self):
        """Test >= 90% returns excellent."""
        assert _get_fill_rate_class(95) == 'fill-rate-excellent'
        assert _get_fill_rate_class(90) == 'fill-rate-excellent'
        assert _get_fill_rate_class(100) == 'fill-rate-excellent'

    def test_good_rate(self):
        """Test 75-89% returns good."""
        assert _get_fill_rate_class(89) == 'fill-rate-good'
        assert _get_fill_rate_class(75) == 'fill-rate-good'
        assert _get_fill_rate_class(80) == 'fill-rate-good'

    def test_medium_rate(self):
        """Test 50-74% returns medium."""
        assert _get_fill_rate_class(74) == 'fill-rate-medium'
        assert _get_fill_rate_class(50) == 'fill-rate-medium'
        assert _get_fill_rate_class(60) == 'fill-rate-medium'

    def test_low_rate(self):
        """Test < 50% returns low."""
        assert _get_fill_rate_class(49) == 'fill-rate-low'
        assert _get_fill_rate_class(25) == 'fill-rate-low'
        assert _get_fill_rate_class(0) == 'fill-rate-low'


class TestFillRateBadge:
    """Tests for _get_fill_rate_badge function."""

    def test_excellent_badge(self):
        """Test >= 90% returns Excellent."""
        assert _get_fill_rate_badge(95) == 'Excellent'
        assert _get_fill_rate_badge(100) == 'Excellent'

    def test_good_badge(self):
        """Test 75-89% returns Bon."""
        assert _get_fill_rate_badge(85) == 'Bon'
        assert _get_fill_rate_badge(75) == 'Bon'

    def test_medium_badge(self):
        """Test 50-74% returns Moyen."""
        assert _get_fill_rate_badge(60) == 'Moyen'
        assert _get_fill_rate_badge(50) == 'Moyen'

    def test_low_badge(self):
        """Test < 50% returns Faible."""
        assert _get_fill_rate_badge(30) == 'Faible'
        assert _get_fill_rate_badge(0) == 'Faible'


class TestGetDealType:
    """Tests for _get_deal_type function."""

    def test_hybrid_deal(self):
        """Test both guarantee and door deal."""
        settlement = {
            'guarantee': 5000,
            'door_deal_percentage': 15
        }
        assert _get_deal_type(settlement) == 'Hybrid (Guarantee + Door Deal)'

    def test_door_deal_only(self):
        """Test door deal without guarantee."""
        settlement = {
            'guarantee': 0,
            'door_deal_percentage': 20
        }
        assert _get_deal_type(settlement) == 'Door Deal'

    def test_guarantee_only(self):
        """Test guarantee without door deal."""
        settlement = {
            'guarantee': 5000,
            'door_deal_percentage': 0
        }
        assert _get_deal_type(settlement) == 'Guarantee'


# =============================================================================
# HTML Generation Tests
# =============================================================================

class TestBuildSettlementHtml:
    """Tests for _build_settlement_html function."""

    @pytest.fixture
    def sample_settlement_data(self):
        """Create sample settlement data for testing."""
        return {
            'stop_id': 1,
            'tour_id': 1,
            'tour_name': 'Summer Tour 2025',
            'band_name': 'Test Band',
            'date': date(2025, 6, 15),
            'venue_name': 'Le Zenith',
            'venue_city': 'Paris',
            'venue_country': 'France',
            'status': 'confirmed',
            'capacity': 5000,
            'sold_tickets': 4200,
            'fill_rate': 84.0,
            'ticket_price': 45.0,
            'avg_ticket_price': 45.0,
            'gross_revenue': 189000.0,
            'ticketing_fee_percentage': 5.0,
            'ticketing_fees': 9450.0,
            'nbor': 179550.0,
            'promoter_expenses': {'total': 0},
            'guarantee': 15000.0,
            'door_deal_percentage': 10.0,
            'door_deal_amount': 16455.0,
            'simple_door_deal': 17955.0,
            'split_point': 15000.0,
            'backend_base': 164550.0,
            'break_even_tickets': 351,
            'break_even_revenue': 15000.0,
            'artist_payment': 17955.0,
            'payment_type': 'door_deal',
            'venue_share': 161595.0,
            'promoter_profit': 161595.0,
            'currency': 'EUR',
            'is_above_break_even': True,
            'profit_above_guarantee': 2955.0,
            'has_promoter_expenses': False,
        }

    def test_html_contains_band_name(self, sample_settlement_data):
        """Test HTML includes band name."""
        html = _build_settlement_html(sample_settlement_data, 'EUR')
        assert 'Test Band' in html

    def test_html_contains_venue_info(self, sample_settlement_data):
        """Test HTML includes venue information."""
        html = _build_settlement_html(sample_settlement_data, 'EUR')
        assert 'Le Zenith' in html
        assert 'Paris' in html
        assert 'France' in html

    def test_html_contains_box_office_section(self, sample_settlement_data):
        """Test HTML includes Box Office section."""
        html = _build_settlement_html(sample_settlement_data, 'EUR')
        assert 'BOX OFFICE' in html
        assert '5,000' in html  # capacity
        assert '4,200' in html  # sold tickets

    def test_html_contains_nbor_section(self, sample_settlement_data):
        """Test HTML includes NBOR (Net Box Office Receipts) section."""
        html = _build_settlement_html(sample_settlement_data, 'EUR')
        assert 'RECETTES NETTES (NBOR)' in html
        assert 'Frais de billetterie' in html

    def test_html_contains_artist_payment(self, sample_settlement_data):
        """Test HTML includes artist payment section."""
        html = _build_settlement_html(sample_settlement_data, 'EUR')
        assert 'PAIEMENT ARTISTE' in html
        assert 'CALCUL DU PAIEMENT ARTISTE' in html

    def test_html_contains_signatures_section(self, sample_settlement_data):
        """Test HTML includes signatures section."""
        html = _build_settlement_html(sample_settlement_data, 'EUR')
        assert 'SIGNATURES' in html
        assert "Representant de l'artiste" in html
        assert 'Promoteur' in html

    def test_html_door_deal_info(self, sample_settlement_data):
        """Test HTML includes door deal percentage."""
        html = _build_settlement_html(sample_settlement_data, 'EUR')
        assert '10' in html  # door deal percentage

    def test_html_with_promoter_expenses(self, sample_settlement_data):
        """Test HTML includes promoter expenses when present."""
        sample_settlement_data['promoter_expenses'] = {
            'total': 5000,
            'venue_fee': 2000,
            'security': 1500,
            'marketing_cost': 1500
        }
        sample_settlement_data['has_promoter_expenses'] = True

        html = _build_settlement_html(sample_settlement_data, 'EUR')
        assert 'DEPENSES PROMOTEUR' in html
        assert 'Location salle' in html
        assert 'Securite' in html

    def test_html_guarantee_only_deal(self, sample_settlement_data):
        """Test HTML for guarantee-only deal."""
        sample_settlement_data['door_deal_percentage'] = 0
        sample_settlement_data['payment_type'] = 'guarantee'

        html = _build_settlement_html(sample_settlement_data, 'EUR')
        assert 'Guarantee' in html

    def test_html_is_valid_structure(self, sample_settlement_data):
        """Test HTML has proper structure."""
        html = _build_settlement_html(sample_settlement_data, 'EUR')

        # Check basic HTML structure
        assert '<!DOCTYPE html>' in html
        assert '<html' in html
        assert '</html>' in html
        assert '<head>' in html
        assert '<body>' in html
        assert '<style>' in html


# =============================================================================
# PDF Generation Tests
# =============================================================================

class TestGenerateSettlementPdf:
    """Tests for generate_settlement_pdf function."""

    @pytest.fixture
    def sample_settlement_data(self):
        """Create sample settlement data for PDF testing."""
        return {
            'stop_id': 1,
            'tour_id': 1,
            'tour_name': 'Test Tour',
            'band_name': 'Test Band',
            'date': date(2025, 6, 15),
            'venue_name': 'Test Venue',
            'venue_city': 'Test City',
            'venue_country': 'France',
            'status': 'confirmed',
            'capacity': 500,
            'sold_tickets': 400,
            'fill_rate': 80.0,
            'ticket_price': 35.0,
            'avg_ticket_price': 35.0,
            'gross_revenue': 14000.0,
            'ticketing_fee_percentage': 5.0,
            'ticketing_fees': 700.0,
            'nbor': 13300.0,
            'promoter_expenses': {'total': 0},
            'guarantee': 5000.0,
            'door_deal_percentage': 0,
            'door_deal_amount': 0,
            'simple_door_deal': 0,
            'split_point': 5000.0,
            'backend_base': 8300.0,
            'break_even_tickets': 150,
            'break_even_revenue': 5000.0,
            'artist_payment': 5000.0,
            'payment_type': 'guarantee',
            'venue_share': 8300.0,
            'promoter_profit': 8300.0,
            'currency': 'EUR',
            'is_above_break_even': True,
            'profit_above_guarantee': 0,
            'has_promoter_expenses': False,
        }

    @pytest.mark.skipif(not PDF_AVAILABLE, reason="xhtml2pdf not installed")
    def test_generate_pdf_returns_bytes(self, sample_settlement_data):
        """Test PDF generation returns bytes."""
        result = generate_settlement_pdf(sample_settlement_data)
        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.skipif(not PDF_AVAILABLE, reason="xhtml2pdf not installed")
    def test_generate_pdf_is_valid_pdf(self, sample_settlement_data):
        """Test generated content is a valid PDF."""
        result = generate_settlement_pdf(sample_settlement_data)
        # PDF files start with %PDF
        assert result[:4] == b'%PDF'

    def test_generate_pdf_without_xhtml2pdf(self, sample_settlement_data):
        """Test error when xhtml2pdf not available."""
        with patch('app.utils.pdf_generator.PDF_AVAILABLE', False):
            # Re-import to get the patched version
            from app.utils import pdf_generator
            original_available = pdf_generator.PDF_AVAILABLE
            pdf_generator.PDF_AVAILABLE = False

            try:
                with pytest.raises(ImportError) as excinfo:
                    pdf_generator.generate_settlement_pdf(sample_settlement_data)
                assert 'xhtml2pdf' in str(excinfo.value)
            finally:
                pdf_generator.PDF_AVAILABLE = original_available

    @pytest.mark.skipif(not PDF_AVAILABLE, reason="xhtml2pdf not installed")
    def test_generate_pdf_with_door_deal(self, sample_settlement_data):
        """Test PDF with door deal settlement."""
        sample_settlement_data['door_deal_percentage'] = 15.0
        sample_settlement_data['door_deal_amount'] = 1995.0
        sample_settlement_data['payment_type'] = 'door_deal'
        sample_settlement_data['artist_payment'] = 6995.0

        result = generate_settlement_pdf(sample_settlement_data)
        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.skipif(not PDF_AVAILABLE, reason="xhtml2pdf not installed")
    def test_generate_pdf_with_promoter_expenses(self, sample_settlement_data):
        """Test PDF with promoter expenses section."""
        sample_settlement_data['promoter_expenses'] = {
            'total': 3000,
            'venue_fee': 1500,
            'production_cost': 1000,
            'catering': 500
        }
        sample_settlement_data['has_promoter_expenses'] = True

        result = generate_settlement_pdf(sample_settlement_data)
        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.skipif(not PDF_AVAILABLE, reason="xhtml2pdf not installed")
    def test_generate_pdf_different_currencies(self, sample_settlement_data):
        """Test PDF generation with different currencies."""
        for currency in ['EUR', 'USD', 'GBP', 'CHF']:
            sample_settlement_data['currency'] = currency
            result = generate_settlement_pdf(sample_settlement_data)
            assert isinstance(result, bytes)
            assert len(result) > 0


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestPdfEdgeCases:
    """Tests for edge cases in PDF generation."""

    @pytest.fixture
    def minimal_settlement(self):
        """Create minimal settlement data."""
        return {
            'stop_id': 1,
            'tour_id': None,
            'tour_name': 'N/A',
            'band_name': 'Unknown Band',
            'date': None,  # No date
            'venue_name': 'Unknown',
            'venue_city': 'Unknown',
            'venue_country': 'Unknown',
            'status': None,
            'capacity': 0,
            'sold_tickets': 0,
            'fill_rate': 0,
            'ticket_price': 0,
            'avg_ticket_price': 0,
            'gross_revenue': 0,
            'ticketing_fee_percentage': 5.0,
            'ticketing_fees': 0,
            'nbor': 0,
            'promoter_expenses': {'total': 0},
            'guarantee': 0,
            'door_deal_percentage': 0,
            'door_deal_amount': 0,
            'simple_door_deal': 0,
            'split_point': 0,
            'backend_base': 0,
            'break_even_tickets': 0,
            'break_even_revenue': 0,
            'artist_payment': 0,
            'payment_type': 'guarantee',
            'venue_share': 0,
            'promoter_profit': 0,
            'currency': 'EUR',
            'is_above_break_even': False,
            'profit_above_guarantee': 0,
            'has_promoter_expenses': False,
        }

    def test_html_with_null_date(self, minimal_settlement):
        """Test HTML generation with null date."""
        html = _build_settlement_html(minimal_settlement, 'EUR')
        assert 'N/A' in html

    def test_html_with_zero_values(self, minimal_settlement):
        """Test HTML generation with zero values."""
        html = _build_settlement_html(minimal_settlement, 'EUR')
        # Should not raise any errors
        assert '<!DOCTYPE html>' in html

    def test_fill_rate_boundary_values(self):
        """Test fill rate boundaries."""
        # Exactly at boundaries
        assert _get_fill_rate_class(90) == 'fill-rate-excellent'
        assert _get_fill_rate_class(89.9) == 'fill-rate-good'
        assert _get_fill_rate_class(75) == 'fill-rate-good'
        assert _get_fill_rate_class(74.9) == 'fill-rate-medium'
        assert _get_fill_rate_class(50) == 'fill-rate-medium'
        assert _get_fill_rate_class(49.9) == 'fill-rate-low'
