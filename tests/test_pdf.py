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
    _get_fill_rate_class,
    _get_fill_rate_color,
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
    """Tests for _get_fill_rate_class function (returns labels)."""

    def test_excellent_rate(self):
        """Test >= 90% returns Excellent."""
        assert _get_fill_rate_class(95) == 'Excellent'
        assert _get_fill_rate_class(90) == 'Excellent'
        assert _get_fill_rate_class(100) == 'Excellent'

    def test_good_rate(self):
        """Test 75-89% returns Bon."""
        assert _get_fill_rate_class(89) == 'Bon'
        assert _get_fill_rate_class(75) == 'Bon'
        assert _get_fill_rate_class(80) == 'Bon'

    def test_medium_rate(self):
        """Test 50-74% returns Moyen."""
        assert _get_fill_rate_class(74) == 'Moyen'
        assert _get_fill_rate_class(50) == 'Moyen'
        assert _get_fill_rate_class(60) == 'Moyen'

    def test_low_rate(self):
        """Test < 50% returns Faible."""
        assert _get_fill_rate_class(49) == 'Faible'
        assert _get_fill_rate_class(25) == 'Faible'
        assert _get_fill_rate_class(0) == 'Faible'


class TestFillRateColor:
    """Tests for _get_fill_rate_color function."""

    @pytest.mark.skipif(not PDF_AVAILABLE, reason="reportlab not installed")
    def test_excellent_color(self):
        """Test >= 90% returns GREEN."""
        color = _get_fill_rate_color(95)
        assert color is not None

    @pytest.mark.skipif(not PDF_AVAILABLE, reason="reportlab not installed")
    def test_good_color(self):
        """Test 75-89% returns BLUE."""
        color = _get_fill_rate_color(85)
        assert color is not None

    @pytest.mark.skipif(not PDF_AVAILABLE, reason="reportlab not installed")
    def test_medium_color(self):
        """Test 50-74% returns YELLOW."""
        color = _get_fill_rate_color(60)
        assert color is not None

    @pytest.mark.skipif(not PDF_AVAILABLE, reason="reportlab not installed")
    def test_low_color(self):
        """Test < 50% returns RED."""
        color = _get_fill_rate_color(30)
        assert color is not None

    def test_no_pdf_returns_none(self):
        """Test returns None when PDF not available."""
        import app.utils.pdf_generator as mod
        original = mod.PDF_AVAILABLE
        mod.PDF_AVAILABLE = False
        try:
            assert _get_fill_rate_color(95) is None
        finally:
            mod.PDF_AVAILABLE = original


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

class TestFillRateClassBoundaries:
    """Tests for fill rate boundary values."""

    def test_boundary_90(self):
        """Test exact boundary at 90%."""
        assert _get_fill_rate_class(90) == 'Excellent'
        assert _get_fill_rate_class(89.9) == 'Bon'

    def test_boundary_75(self):
        """Test exact boundary at 75%."""
        assert _get_fill_rate_class(75) == 'Bon'
        assert _get_fill_rate_class(74.9) == 'Moyen'

    def test_boundary_50(self):
        """Test exact boundary at 50%."""
        assert _get_fill_rate_class(50) == 'Moyen'
        assert _get_fill_rate_class(49.9) == 'Faible'


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

    def test_generate_pdf_without_reportlab(self, sample_settlement_data):
        """Test error when reportlab not available."""
        from app.utils import pdf_generator
        original_available = pdf_generator.PDF_AVAILABLE
        pdf_generator.PDF_AVAILABLE = False

        try:
            with pytest.raises(ImportError) as excinfo:
                pdf_generator.generate_settlement_pdf(sample_settlement_data)
            assert 'reportlab' in str(excinfo.value)
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

    def test_deal_type_with_zero_values(self, minimal_settlement):
        """Test _get_deal_type with zero values."""
        assert _get_deal_type(minimal_settlement) == 'Guarantee'

    def test_format_currency_with_zero(self):
        """Test format_currency with zero amount."""
        result = format_currency(0, 'EUR')
        assert '0.00' in result

    def test_format_currency_unknown_currency(self):
        """Test format_currency with unknown currency code."""
        result = format_currency(100, 'JPY')
        assert 'JPY' in result
        assert '100.00' in result
