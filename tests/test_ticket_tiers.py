# =============================================================================
# Tests for multi-tier ticket pricing (TicketTier model)
# =============================================================================

import pytest
from decimal import Decimal
from datetime import date, time, timedelta

from app.extensions import db
from app.models.ticket_tier import TicketTier
from app.models.tour_stop import TourStop, TourStopStatus
from app.models.tour import Tour, TourStatus
from app.utils.reports import calculate_stop_financials, calculate_settlement


# =============================================================================
# TicketTier Model Tests
# =============================================================================

class TestTicketTierModel:
    """Test TicketTier CRUD and properties."""

    def test_create_tier(self, app, sample_tour_stop):
        """Test creating a ticket tier."""
        tier = TicketTier(
            tour_stop=sample_tour_stop,
            name='Fosse',
            price=Decimal('35.00'),
            quantity_available=250,
            sold=100,
            sort_order=0
        )
        db.session.add(tier)
        db.session.commit()

        assert tier.id is not None
        assert tier.name == 'Fosse'
        assert tier.price == Decimal('35.00')
        assert tier.quantity_available == 250
        assert tier.sold == 100
        assert tier.sort_order == 0
        assert tier.tour_stop_id == sample_tour_stop.id

    def test_revenue_property(self, app, sample_tour_stop):
        """Test tier revenue calculation."""
        tier = TicketTier(
            tour_stop=sample_tour_stop,
            name='Fosse',
            price=Decimal('35.00'),
            sold=100,
            sort_order=0
        )
        db.session.add(tier)
        db.session.commit()

        assert tier.revenue == 3500.0

    def test_revenue_zero_sold(self, app, sample_tour_stop):
        """Test revenue with zero sold."""
        tier = TicketTier(
            tour_stop=sample_tour_stop,
            name='VIP',
            price=Decimal('80.00'),
            sold=0,
            sort_order=0
        )
        db.session.add(tier)
        db.session.commit()

        assert tier.revenue == 0.0

    def test_is_sold_out(self, app, sample_tour_stop):
        """Test sold out detection."""
        tier = TicketTier(
            tour_stop=sample_tour_stop,
            name='Fosse',
            price=Decimal('35.00'),
            quantity_available=100,
            sold=100,
            sort_order=0
        )
        db.session.add(tier)
        db.session.commit()

        assert tier.is_sold_out is True

    def test_not_sold_out(self, app, sample_tour_stop):
        """Test not sold out."""
        tier = TicketTier(
            tour_stop=sample_tour_stop,
            name='Fosse',
            price=Decimal('35.00'),
            quantity_available=100,
            sold=50,
            sort_order=0
        )
        db.session.add(tier)
        db.session.commit()

        assert tier.is_sold_out is False

    def test_unlimited_never_sold_out(self, app, sample_tour_stop):
        """Test unlimited tier never sold out."""
        tier = TicketTier(
            tour_stop=sample_tour_stop,
            name='General',
            price=Decimal('25.00'),
            quantity_available=None,
            sold=9999,
            sort_order=0
        )
        db.session.add(tier)
        db.session.commit()

        assert tier.is_sold_out is False

    def test_remaining_tickets(self, app, sample_tour_stop):
        """Test remaining tickets calculation."""
        tier = TicketTier(
            tour_stop=sample_tour_stop,
            name='Fosse',
            price=Decimal('35.00'),
            quantity_available=100,
            sold=70,
            sort_order=0
        )
        db.session.add(tier)
        db.session.commit()

        assert tier.remaining == 30

    def test_remaining_unlimited(self, app, sample_tour_stop):
        """Test remaining is None for unlimited tiers."""
        tier = TicketTier(
            tour_stop=sample_tour_stop,
            name='General',
            price=Decimal('25.00'),
            quantity_available=None,
            sold=50,
            sort_order=0
        )
        db.session.add(tier)
        db.session.commit()

        assert tier.remaining is None

    def test_to_dict(self, app, sample_tour_stop):
        """Test JSON serialization."""
        tier = TicketTier(
            tour_stop=sample_tour_stop,
            name='VIP',
            price=Decimal('80.00'),
            quantity_available=30,
            sold=20,
            sort_order=2
        )
        db.session.add(tier)
        db.session.commit()

        d = tier.to_dict()
        assert d['name'] == 'VIP'
        assert d['price'] == 80.0
        assert d['quantity_available'] == 30
        assert d['sold'] == 20
        assert d['revenue'] == 1600.0
        assert d['is_sold_out'] is False
        assert d['remaining'] == 10
        assert d['sort_order'] == 2

    def test_cascade_delete(self, app, tour_stop_with_tiers):
        """Test tiers are deleted when tour stop is deleted."""
        stop_id = tour_stop_with_tiers.id
        tier_count = TicketTier.query.filter_by(tour_stop_id=stop_id).count()
        assert tier_count == 3

        db.session.delete(tour_stop_with_tiers)
        db.session.commit()

        remaining = TicketTier.query.filter_by(tour_stop_id=stop_id).count()
        assert remaining == 0

    def test_repr(self, app, sample_tour_stop):
        """Test string representation."""
        tier = TicketTier(
            tour_stop=sample_tour_stop,
            name='Fosse',
            price=Decimal('35.00'),
            sort_order=0
        )
        assert repr(tier) == '<TicketTier Fosse @ 35.00>'


# =============================================================================
# TourStop Computed Properties with Tiers
# =============================================================================

class TestTourStopTierProperties:
    """Test TourStop computed properties when tiers exist."""

    def test_has_tiers_true(self, app, tour_stop_with_tiers):
        """Test has_tiers returns True when tiers exist."""
        assert tour_stop_with_tiers.has_tiers is True

    def test_has_tiers_false(self, app, sample_tour_stop):
        """Test has_tiers returns False when no tiers."""
        assert sample_tour_stop.has_tiers is False

    def test_total_sold_tickets_with_tiers(self, app, tour_stop_with_tiers):
        """Test total sold tickets sums all tiers (250+120+30=400)."""
        assert tour_stop_with_tiers.total_sold_tickets == 400

    def test_total_sold_tickets_without_tiers(self, app, sample_tour_stop):
        """Test total sold tickets falls back to legacy field."""
        sample_tour_stop.sold_tickets = 150
        db.session.commit()
        assert sample_tour_stop.total_sold_tickets == 150

    def test_total_quantity_available(self, app, tour_stop_with_tiers):
        """Test total quantity sums all tiers (250+120+30=400)."""
        assert tour_stop_with_tiers.total_quantity_available == 400

    def test_total_quantity_available_with_unlimited(self, app, sample_tour_stop):
        """Test total quantity is None when any tier is unlimited."""
        t1 = TicketTier(tour_stop=sample_tour_stop, name='GA', price=Decimal('25.00'),
                        quantity_available=None, sold=50, sort_order=0)
        t2 = TicketTier(tour_stop=sample_tour_stop, name='VIP', price=Decimal('80.00'),
                        quantity_available=30, sold=10, sort_order=1)
        db.session.add_all([t1, t2])
        db.session.commit()

        assert sample_tour_stop.total_quantity_available is None

    def test_gross_ticket_revenue(self, app, tour_stop_with_tiers):
        """Test GBOR: 250*35 + 120*45 + 30*80 = 16550."""
        assert tour_stop_with_tiers.gross_ticket_revenue == 16550.0

    def test_gross_ticket_revenue_no_tiers(self, app, sample_tour_stop):
        """Test GBOR returns 0 when no tiers and no legacy data."""
        assert sample_tour_stop.gross_ticket_revenue == 0

    def test_weighted_avg_price(self, app, tour_stop_with_tiers):
        """Test weighted avg: 16550/400 = 41.375."""
        assert tour_stop_with_tiers.weighted_avg_price == pytest.approx(41.375, abs=0.01)

    def test_weighted_avg_price_no_sales(self, app, sample_tour_stop):
        """Test weighted avg falls back to simple average when no sales."""
        t = TicketTier(tour_stop=sample_tour_stop, name='GA', price=Decimal('25.00'),
                       sold=0, sort_order=0)
        db.session.add(t)
        db.session.commit()

        # With 0 sold, falls back to simple avg of tier prices
        assert sample_tour_stop.weighted_avg_price == 25.0

    def test_tier_breakdown(self, app, tour_stop_with_tiers):
        """Test tier breakdown list of dicts."""
        breakdown = tour_stop_with_tiers.tier_breakdown
        assert len(breakdown) == 3
        assert breakdown[0]['name'] == 'Fosse'
        assert breakdown[0]['price'] == 35.0
        assert breakdown[0]['sold'] == 250
        assert breakdown[0]['revenue'] == 8750.0
        assert breakdown[2]['name'] == 'VIP'


# =============================================================================
# Financial Calculations with Tiers
# =============================================================================

class TestFinancialsWithTiers:
    """Test calculate_stop_financials and calculate_settlement with tiers."""

    def test_stop_financials_with_tiers(self, app, tour_stop_with_tiers):
        """Test stop financials reads GBOR from tiers."""
        financials = calculate_stop_financials(tour_stop_with_tiers)
        assert financials['has_tiers'] is True
        assert financials['ticket_revenue'] == 16550.0  # GBOR
        assert financials['sold_tickets'] == 400
        assert financials['ticket_price'] == pytest.approx(41.375, abs=0.01)
        assert len(financials['tier_breakdown']) == 3

    def test_stop_financials_without_tiers(self, app, tour_stop_with_guarantee):
        """Test stop financials uses legacy fields (backward compat)."""
        financials = calculate_stop_financials(tour_stop_with_guarantee)
        assert financials['has_tiers'] is False
        assert financials['sold_tickets'] == 350
        assert financials['ticket_revenue'] == 12250.0  # 350 * 35
        assert financials['ticket_price'] == 35.0

    def test_settlement_with_tiers(self, app, tour_stop_with_tiers):
        """Test settlement reads GBOR from tiers."""
        settlement = calculate_settlement(tour_stop_with_tiers)
        assert settlement['has_tiers'] is True
        assert settlement['gross_revenue'] == 16550.0
        assert settlement['sold_tickets'] == 400
        assert len(settlement['tier_breakdown']) == 3


# =============================================================================
# Tour Clone with Tiers
# =============================================================================

class TestTourCloneWithTiers:
    """Test tour duplication copies tiers with sold=0."""

    def test_clone_copies_tiers(self, app, tour_stop_with_tiers):
        """Test that cloning a tour copies tier structure with sold=0."""
        tour = tour_stop_with_tiers.tour
        new_tour = tour.duplicate(new_name='Cloned Tour')
        db.session.add(new_tour)
        db.session.commit()

        assert len(new_tour.stops) == len(tour.stops)
        cloned_stop = new_tour.stops[0]
        assert len(cloned_stop.ticket_tiers) == 3

        # All sold counts reset to 0
        for tier in cloned_stop.ticket_tiers:
            assert tier.sold == 0

        # Tier names and prices preserved
        tier_names = {t.name for t in cloned_stop.ticket_tiers}
        assert tier_names == {'Fosse', 'Assis', 'VIP'}

        fosse = next(t for t in cloned_stop.ticket_tiers if t.name == 'Fosse')
        assert fosse.price == Decimal('35.00')
        assert fosse.quantity_available == 250


# =============================================================================
# Route Tests for Tier CRUD
# =============================================================================

class TestTierRoutes:
    """Test route handling for ticket tiers in update flow."""

    def test_update_tickets_multi_tier_direct(self, app, tour_stop_with_tiers):
        """Test the update_stop_tickets route logic directly via model."""
        stop = tour_stop_with_tiers
        assert stop.has_tiers is True

        # Simulate what the route does
        for tier in stop.ticket_tiers:
            tier.sold = 10
        db.session.commit()

        db.session.expire_all()
        updated = db.session.get(TourStop, stop.id)
        assert updated.total_sold_tickets == 30  # 3 tiers * 10
        for tier in updated.ticket_tiers:
            assert tier.sold == 10

    def test_update_tickets_simple_mode_direct(self, app, sample_tour_stop):
        """Test simple mode sold_tickets update."""
        stop = sample_tour_stop
        assert stop.has_tiers is False

        stop.sold_tickets = 150
        db.session.commit()

        db.session.expire_all()
        updated = db.session.get(TourStop, stop.id)
        assert updated.sold_tickets == 150
        assert updated.total_sold_tickets == 150
