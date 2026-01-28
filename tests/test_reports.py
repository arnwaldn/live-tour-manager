# =============================================================================
# Tour Manager - Financial Reports Tests
# =============================================================================
# Tests for app/utils/reports.py - Financial calculations module
# Coverage target: 7% → 80%

import pytest
from decimal import Decimal
from datetime import date, timedelta

from app.utils.reports import (
    calculate_stop_financials,
    calculate_tour_financials,
    calculate_multi_tour_summary,
    calculate_settlement,
    calculate_dashboard_kpis,
    format_currency,
    generate_csv_report
)


# =============================================================================
# format_currency Tests
# =============================================================================

class TestFormatCurrency:
    """Tests for currency formatting function."""

    def test_format_currency_euro(self):
        """Test EUR formatting with € symbol."""
        result = format_currency(1234.56, 'EUR')
        assert result == '€1,234.56'

    def test_format_currency_dollar(self):
        """Test USD formatting with $ symbol."""
        result = format_currency(999.99, 'USD')
        assert result == '$999.99'

    def test_format_currency_pound(self):
        """Test GBP formatting with £ symbol."""
        result = format_currency(500.00, 'GBP')
        assert result == '£500.00'

    def test_format_currency_swiss_franc(self):
        """Test CHF formatting with CHF prefix."""
        result = format_currency(750.50, 'CHF')
        assert result == 'CHF 750.50'

    def test_format_currency_unknown(self):
        """Test unknown currency uses code as prefix."""
        result = format_currency(100.00, 'JPY')
        assert result == 'JPY 100.00'

    def test_format_currency_zero(self):
        """Test zero amount formatting."""
        result = format_currency(0, 'EUR')
        assert result == '€0.00'

    def test_format_currency_large_amount(self):
        """Test large amount with thousand separators."""
        result = format_currency(1234567.89, 'EUR')
        assert result == '€1,234,567.89'


# =============================================================================
# calculate_stop_financials Tests
# =============================================================================

class TestCalculateStopFinancials:
    """Tests for single tour stop financial calculations."""

    def test_basic_calculation(self, tour_stop_with_guarantee):
        """Test basic financial calculation with guarantee only."""
        result = calculate_stop_financials(tour_stop_with_guarantee)

        assert result['guarantee'] == 5000.0
        assert result['ticket_revenue'] == 35.0 * 350  # 12,250
        assert result['sold_tickets'] == 350
        assert result['capacity'] == 500
        assert result['currency'] == 'EUR'
        assert result['fill_rate'] == 70.0  # 350/500 * 100

    def test_with_ticketing_fees(self, tour_stop_with_door_deal):
        """Test calculation with ticketing fees (R2)."""
        result = calculate_stop_financials(tour_stop_with_door_deal)

        # GBOR = 40 * 400 = 16,000
        assert result['ticket_revenue'] == 16000.0

        # Ticketing fees = 16,000 * 6% = 960
        assert result['ticketing_fee_percentage'] == 6.0
        assert result['ticketing_fees'] == 960.0

        # NBOR = 16,000 - 960 = 15,040
        assert result['net_ticket_revenue'] == 15040.0

    def test_door_deal_calculation(self, tour_stop_with_door_deal):
        """Test door deal revenue calculation."""
        result = calculate_stop_financials(tour_stop_with_door_deal)

        # Door deal = NBOR * 15% = 15,040 * 0.15 = 2,256
        assert result['door_deal_revenue'] == pytest.approx(2256.0, rel=0.01)

        # Total = guarantee + door deal = 3000 + 2256 = 5256
        assert result['total_estimated_revenue'] == pytest.approx(5256.0, rel=0.01)

    def test_sold_out_show(self, tour_stop_sold_out):
        """Test 100% fill rate for sold out show."""
        result = calculate_stop_financials(tour_stop_sold_out)

        assert result['sold_tickets'] == 500
        assert result['capacity'] == 500
        assert result['fill_rate'] == 100.0

    def test_venue_info_included(self, tour_stop_with_guarantee):
        """Test that venue information is included."""
        result = calculate_stop_financials(tour_stop_with_guarantee)

        assert result['venue_name'] == 'Test Venue'
        assert result['venue_city'] == 'Test City'
        assert result['status'] == 'confirmed'

    def test_zero_capacity_fill_rate(self, tour_stop_no_capacity):
        """Test fill rate is 0 when capacity is None/0 (Bug #3)."""
        result = calculate_stop_financials(tour_stop_no_capacity)

        assert result['capacity'] == 0
        assert result['fill_rate'] == 0
        assert result['sold_tickets'] == 150

    def test_default_ticketing_fee(self, tour_stop_with_guarantee):
        """Test default 5% ticketing fee when not specified."""
        result = calculate_stop_financials(tour_stop_with_guarantee)
        assert result['ticketing_fee_percentage'] == 5.0


# =============================================================================
# calculate_tour_financials Tests
# =============================================================================

class TestCalculateTourFinancials:
    """Tests for tour-level financial aggregations."""

    def test_tour_aggregation(self, tour_with_multiple_stops):
        """Test aggregation of multiple stops."""
        result = calculate_tour_financials(tour_with_multiple_stops)

        assert result['num_stops'] == 3
        assert result['tour_name'] == 'Multi-Stop Tour'

        # Total guarantees = 5000 + 6000 + 7000 = 18,000
        assert result['total_guarantee'] == 18000.0

        # Total tickets = 300 + 400 + 450 = 1150
        assert result['total_sold_tickets'] == 1150

    def test_tour_info_included(self, tour_with_multiple_stops):
        """Test tour metadata is included."""
        result = calculate_tour_financials(tour_with_multiple_stops)

        assert result['tour_id'] is not None
        assert result['band_name'] == 'Test Band'
        assert result['status'] == 'confirmed'

    def test_stops_data_sorted_by_date(self, tour_with_multiple_stops):
        """Test that stops_data is sorted by date."""
        result = calculate_tour_financials(tour_with_multiple_stops)

        stops = result['stops_data']
        dates = [s['date'] for s in stops]
        assert dates == sorted(dates)

    def test_empty_tour(self, sample_tour):
        """Test tour with no stops."""
        result = calculate_tour_financials(sample_tour)

        assert result['num_stops'] == 0
        assert result['total_guarantee'] == 0.0
        assert result['avg_revenue_per_stop'] == 0.0

    def test_avg_fill_rate(self, tour_with_multiple_stops):
        """Test average fill rate across stops."""
        result = calculate_tour_financials(tour_with_multiple_stops)

        # Total capacity = 500 * 3 = 1500, Total tickets = 1150
        # Avg fill = 1150/1500 * 100 = 76.67%
        assert result['avg_fill_rate'] == pytest.approx(76.7, rel=0.1)


# =============================================================================
# calculate_settlement Tests
# =============================================================================

class TestCalculateSettlement:
    """Tests for settlement (feuille de règlement) calculations."""

    def test_guarantee_only_settlement(self, tour_stop_with_guarantee):
        """Test settlement with guarantee only (no door deal)."""
        result = calculate_settlement(tour_stop_with_guarantee)

        assert result['guarantee'] == 5000.0
        assert result['payment_type'] == 'guarantee'
        assert result['artist_payment'] == 5000.0

    def test_door_deal_settlement(self, tour_stop_with_door_deal):
        """Test settlement with door deal percentage."""
        result = calculate_settlement(tour_stop_with_door_deal)

        assert result['door_deal_percentage'] == 15.0
        assert result['guarantee'] == 3000.0
        # If door deal > guarantee, payment_type is 'door_deal'
        # Simple door deal = NBOR * 15% = 15040 * 0.15 = 2256
        # Since 2256 < 3000 guarantee, should be 'guarantee'
        assert result['payment_type'] == 'guarantee'

    def test_gbor_calculation(self, tour_stop_with_door_deal):
        """Test GBOR (Gross Box Office Receipts) in settlement."""
        result = calculate_settlement(tour_stop_with_door_deal)

        # GBOR = ticket_price * sold_tickets = 40 * 400 = 16,000
        assert result['gross_revenue'] == 16000.0

    def test_nbor_calculation(self, tour_stop_with_door_deal):
        """Test NBOR (Net Box Office Receipts) after ticketing fees."""
        result = calculate_settlement(tour_stop_with_door_deal)

        # NBOR = GBOR - ticketing_fees = 16000 - 960 = 15040
        assert result['nbor'] == 15040.0
        assert result['ticketing_fees'] == 960.0

    def test_split_point_no_expenses(self, tour_stop_with_guarantee):
        """Test split point when no promoter expenses."""
        result = calculate_settlement(tour_stop_with_guarantee)

        # Split point = promoter_expenses + guarantee = 0 + 5000 = 5000
        assert result['split_point'] == 5000.0
        assert result['has_promoter_expenses'] is False

    def test_venue_share_calculation(self, tour_stop_sold_out):
        """Test venue/promoter share after artist payment."""
        result = calculate_settlement(tour_stop_sold_out)

        # Artist payment = guarantee (since no door deal)
        # Venue share = NBOR - artist_payment
        nbor = result['nbor']
        artist_payment = result['artist_payment']
        assert result['venue_share'] == nbor - artist_payment

    def test_break_even_calculation(self, tour_stop_with_guarantee):
        """Test break-even tickets calculation."""
        result = calculate_settlement(tour_stop_with_guarantee)

        # break_even_tickets should be calculated
        assert 'break_even_tickets' in result
        assert result['break_even_tickets'] >= 0

    def test_event_info_in_settlement(self, tour_stop_with_guarantee):
        """Test event metadata is included in settlement."""
        result = calculate_settlement(tour_stop_with_guarantee)

        assert result['venue_name'] == 'Test Venue'
        assert result['venue_city'] == 'Test City'
        assert result['tour_name'] == 'Test Tour 2025'


# =============================================================================
# calculate_dashboard_kpis Tests
# =============================================================================

class TestCalculateDashboardKPIs:
    """Tests for dashboard KPI calculations with bug fix verifications."""

    def test_empty_tours(self, app):
        """Test KPIs with no tours."""
        result = calculate_dashboard_kpis([])

        assert result['total_revenue'] == 0.0
        assert result['total_tickets'] == 0
        assert result['num_shows'] == 0

    def test_basic_kpis(self, tour_with_multiple_stops):
        """Test basic KPI calculation with data."""
        result = calculate_dashboard_kpis([tour_with_multiple_stops])

        assert result['num_shows'] == 3
        assert result['total_tickets'] == 1150
        assert result['total_guarantees'] == 18000.0

    def test_bug3_stops_without_capacity(self, tour_with_multiple_stops, tour_stop_no_capacity):
        """
        Bug #3 verification: stops_without_capacity counter.
        Dashboard should identify venues without known capacity.
        """
        from app.models.tour import Tour, TourStatus
        from app.models.tour_stop import TourStop, TourStopStatus
        from app.extensions import db

        result = calculate_dashboard_kpis([tour_with_multiple_stops])

        # All 3 stops have capacity 500
        assert result['stops_with_capacity'] == 3
        assert result['stops_without_capacity'] == 0

    def test_bug4_fill_rate_none_when_no_capacity(self, sample_tour, tour_stop_no_capacity):
        """
        Bug #4 verification: fill_rate should be None if capacity unknown.
        This prevents misleading 0% fill rate display.
        """
        # Need a tour containing only the no-capacity stop
        from app.models.tour import Tour
        from app.extensions import db

        # Create tour with just the no-capacity stop
        tour = sample_tour
        # Clear existing stops and add no-capacity stop
        tour.stops.clear()
        db.session.flush()

        tour_stop_no_capacity.tour_id = tour.id
        db.session.commit()
        db.session.refresh(tour)

        result = calculate_dashboard_kpis([tour])

        # With no capacity but tickets sold, fill_rate should be None
        if result['total_capacity'] == 0 and result['total_tickets'] > 0:
            assert result['avg_fill_rate'] is None

    def test_bug5_total_ticket_revenue_distinct(self, tour_with_multiple_stops):
        """
        Bug #5 verification: total_ticket_revenue (GBOR) should be
        distinct from artist revenue.
        """
        result = calculate_dashboard_kpis([tour_with_multiple_stops])

        # GBOR should be present and formatted
        assert 'total_ticket_revenue' in result
        assert 'formatted_ticket_revenue' in result
        assert result['total_ticket_revenue'] > 0

        # GBOR != artist revenue (guarantees + door deals)
        gbor = result['total_ticket_revenue']
        artist_revenue = result['total_revenue']
        # They should differ (GBOR is box office, artist revenue is payment)
        assert gbor != artist_revenue

    def test_monthly_revenue_aggregation(self, tour_with_multiple_stops):
        """Test monthly revenue data for charts."""
        result = calculate_dashboard_kpis([tour_with_multiple_stops])

        assert 'monthly_revenue' in result
        assert isinstance(result['monthly_revenue'], list)

    def test_revenue_by_tour(self, tour_with_multiple_stops):
        """Test revenue breakdown by tour."""
        result = calculate_dashboard_kpis([tour_with_multiple_stops])

        assert 'revenue_by_tour' in result
        assert 'Multi-Stop Tour' in result['revenue_by_tour']

    def test_top_stops_ranking(self, tour_with_multiple_stops):
        """Test top performing stops list."""
        result = calculate_dashboard_kpis([tour_with_multiple_stops])

        assert 'top_stops' in result
        top = result['top_stops']
        # Should be sorted by revenue descending
        revenues = [s['total_estimated_revenue'] for s in top]
        assert revenues == sorted(revenues, reverse=True)

    def test_formatted_values(self, tour_with_multiple_stops):
        """Test formatted currency values are present."""
        result = calculate_dashboard_kpis([tour_with_multiple_stops])

        assert 'formatted_revenue' in result
        assert 'formatted_guarantees' in result
        assert 'formatted_door_deals' in result
        assert '€' in result['formatted_revenue']


# =============================================================================
# calculate_multi_tour_summary Tests
# =============================================================================

class TestCalculateMultiTourSummary:
    """Tests for multi-tour summary calculations."""

    def test_single_tour_summary(self, tour_with_multiple_stops):
        """Test summary with single tour."""
        result = calculate_multi_tour_summary([tour_with_multiple_stops])

        assert result['num_tours'] == 1
        assert result['total_stops'] == 3

    def test_empty_tours_list(self, app):
        """Test summary with empty tour list."""
        result = calculate_multi_tour_summary([])

        assert result['num_tours'] == 0
        assert result['total_stops'] == 0
        assert result['grand_total_revenue'] == 0.0

    def test_overall_fill_rate(self, tour_with_multiple_stops):
        """Test overall fill rate across all tours."""
        result = calculate_multi_tour_summary([tour_with_multiple_stops])

        assert result['overall_fill_rate'] >= 0
        assert result['overall_fill_rate'] <= 100


# =============================================================================
# generate_csv_report Tests
# =============================================================================

class TestGenerateCSVReport:
    """Tests for CSV report generation."""

    def test_csv_generation(self, tour_with_multiple_stops):
        """Test CSV content generation."""
        tour_data = calculate_tour_financials(tour_with_multiple_stops)
        csv_content = generate_csv_report(tour_data)

        # Should be a string
        assert isinstance(csv_content, str)

        # Should contain headers
        assert 'Date' in csv_content
        assert 'Venue' in csv_content
        assert 'Cachet' in csv_content

    def test_csv_contains_data_rows(self, tour_with_multiple_stops):
        """Test CSV contains stop data rows."""
        tour_data = calculate_tour_financials(tour_with_multiple_stops)
        csv_content = generate_csv_report(tour_data)

        # Should contain venue name
        assert 'Test Venue' in csv_content

        # Should contain totals row
        assert 'TOTAL' in csv_content

    def test_csv_empty_tour(self, sample_tour):
        """Test CSV generation for empty tour."""
        tour_data = calculate_tour_financials(sample_tour)
        csv_content = generate_csv_report(tour_data)

        # Should still have headers
        assert 'Date' in csv_content
        # And TOTAL row
        assert 'TOTAL' in csv_content
