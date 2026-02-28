"""
Financial reports utility module for GigRoute.
Handles calculations for tour financial analytics.
"""
from decimal import Decimal
from typing import Dict, Any
from datetime import date


def calculate_stop_financials(tour_stop) -> Dict[str, Any]:
    """
    Calculate financial metrics for a single tour stop.

    R2: Inclut maintenant GBOR (Gross) et NBOR (Net après frais billetterie).

    Returns dict with:
        - guarantee: Base guarantee amount
        - venue_rental_cost: Venue rental cost (location salle)
        - ticket_revenue: Revenue from ticket sales (GBOR)
        - ticketing_fees: Fees deducted (R2)
        - net_ticket_revenue: NBOR - Net Box Office Receipts (R2)
        - door_deal_revenue: Estimated door deal revenue
        - total_estimated_revenue: Total estimated revenue
        - capacity: Venue capacity
        - sold_tickets: Number of tickets sold
        - fill_rate: Percentage of capacity sold
        - currency: Currency code
    """
    guarantee = Decimal(str(tour_stop.guarantee or 0))
    venue_rental_cost = Decimal(str(tour_stop.venue_rental_cost or 0))
    door_deal_pct = Decimal(str(tour_stop.door_deal_percentage or 0))
    ticketing_fee_pct = Decimal(str(tour_stop.ticketing_fee_percentage or 5))  # R2: Default 5%
    capacity = tour_stop.venue.capacity or 0 if tour_stop.venue else 0
    currency = tour_stop.currency or 'EUR'

    # Tier-aware ticket calculations
    if tour_stop.has_tiers:
        sold_tickets = tour_stop.total_sold_tickets
        gross_ticket_revenue = Decimal(str(tour_stop.gross_ticket_revenue))
        ticket_price = Decimal(str(tour_stop.weighted_avg_price))
        tier_breakdown = tour_stop.tier_breakdown
    else:
        ticket_price = Decimal(str(tour_stop.ticket_price or 0))
        sold_tickets = tour_stop.sold_tickets or 0
        gross_ticket_revenue = ticket_price * sold_tickets
        tier_breakdown = None

    # R2: Calculate ticketing fees and NBOR (Net Box Office Receipts)
    ticketing_fees = gross_ticket_revenue * (ticketing_fee_pct / 100)
    net_ticket_revenue = gross_ticket_revenue - ticketing_fees

    # Calculate door deal revenue based on NET revenue (standard industrie)
    door_deal_revenue = Decimal('0')
    if door_deal_pct > 0:
        door_deal_revenue = net_ticket_revenue * (door_deal_pct / 100)

    # Total revenue is either guarantee or guarantee + door deal
    total_estimated = guarantee + door_deal_revenue

    # Calculate fill rate
    fill_rate = (sold_tickets / capacity * 100) if capacity > 0 else 0

    return {
        'guarantee': float(guarantee),
        'venue_rental_cost': float(venue_rental_cost),
        'ticket_revenue': float(gross_ticket_revenue),  # GBOR
        'ticket_price': float(ticket_price),  # weighted avg for multi-tier
        'ticketing_fee_percentage': float(ticketing_fee_pct),  # R2
        'ticketing_fees': float(ticketing_fees),  # R2
        'net_ticket_revenue': float(net_ticket_revenue),  # R2: NBOR
        'door_deal_revenue': float(door_deal_revenue),
        'total_estimated_revenue': float(total_estimated),
        'capacity': capacity,
        'sold_tickets': sold_tickets,
        'fill_rate': round(fill_rate, 1),
        'currency': currency,
        'has_tiers': tour_stop.has_tiers,
        'tier_breakdown': tier_breakdown,
        'date': tour_stop.date,
        'venue_name': tour_stop.venue.name if tour_stop.venue else 'N/A',
        'venue_city': tour_stop.venue.city if tour_stop.venue else 'N/A',
        'status': tour_stop.status.value if tour_stop.status else 'unknown',
    }


def calculate_tour_financials(tour) -> Dict[str, Any]:
    """
    Calculate financial metrics for an entire tour.

    Returns dict with:
        - total_guarantee: Sum of all guarantees
        - total_venue_rental_cost: Sum of all venue rental costs
        - total_ticket_revenue: Sum of all ticket revenues
        - total_door_deal_revenue: Sum of door deal revenues
        - total_estimated_revenue: Grand total revenue
        - avg_revenue_per_stop: Average revenue per stop
        - total_sold_tickets: Total tickets sold
        - total_capacity: Total venue capacity
        - avg_fill_rate: Average fill rate across stops
        - stops_data: List of individual stop financials
        - currency: Primary currency (most common)
    """
    stops_data = []
    currencies = {}

    total_guarantee = Decimal('0')
    total_venue_rental_cost = Decimal('0')
    total_ticket_revenue = Decimal('0')
    total_door_deal_revenue = Decimal('0')
    total_sold_tickets = 0
    total_capacity = 0

    for stop in tour.stops:
        stop_fin = calculate_stop_financials(stop)
        stops_data.append(stop_fin)

        total_guarantee += Decimal(str(stop_fin['guarantee']))
        total_venue_rental_cost += Decimal(str(stop_fin['venue_rental_cost']))
        total_ticket_revenue += Decimal(str(stop_fin['ticket_revenue']))
        total_door_deal_revenue += Decimal(str(stop_fin['door_deal_revenue']))
        total_sold_tickets += stop_fin['sold_tickets']
        total_capacity += stop_fin['capacity']

        # Track currency usage
        curr = stop_fin['currency']
        currencies[curr] = currencies.get(curr, 0) + 1

    # Determine primary currency
    primary_currency = max(currencies, key=currencies.get) if currencies else 'EUR'

    # Calculate totals
    total_estimated = total_guarantee + total_door_deal_revenue
    num_stops = len(tour.stops)
    avg_revenue = total_estimated / num_stops if num_stops > 0 else Decimal('0')
    avg_fill_rate = (total_sold_tickets / total_capacity * 100) if total_capacity > 0 else 0

    # ===== LOGISTICS COSTS (Informatif) =====
    logistics = calculate_tour_logistics_costs(tour)

    return {
        'tour_id': tour.id,
        'tour_name': tour.name,
        'band_name': tour.band.name if tour.band else 'N/A',
        'start_date': tour.start_date,
        'end_date': tour.end_date,
        'status': tour.status.value if tour.status else 'unknown',
        'total_guarantee': float(total_guarantee),
        'total_venue_rental_cost': float(total_venue_rental_cost),
        'total_ticket_revenue': float(total_ticket_revenue),
        'total_door_deal_revenue': float(total_door_deal_revenue),
        'total_estimated_revenue': float(total_estimated),
        'avg_revenue_per_stop': float(avg_revenue),
        'total_sold_tickets': total_sold_tickets,
        'total_capacity': total_capacity,
        'avg_fill_rate': round(avg_fill_rate, 1),
        'num_stops': num_stops,
        'currency': primary_currency,
        'stops_data': sorted(stops_data, key=lambda x: x['date']),
        # Logistics costs (informatif - pas de déduction du revenu)
        'logistics_costs': logistics['total'],
        'logistics_by_stop': logistics['by_stop'],
        'logistics_by_paid_by': logistics['by_paid_by'],
        'logistics_unpaid': logistics['unpaid_total'],
        'formatted_logistics_total': format_currency(logistics['total']['total'], primary_currency),
        'formatted_venue_rental_cost': format_currency(float(total_venue_rental_cost), primary_currency),
    }


def calculate_multi_tour_summary(tours) -> Dict[str, Any]:
    """
    Calculate summary financials across multiple tours.

    Returns summary statistics for all tours combined.
    """
    all_tour_data = []
    grand_total_revenue = Decimal('0')
    grand_total_tickets = 0
    grand_total_capacity = 0

    for tour in tours:
        tour_fin = calculate_tour_financials(tour)
        all_tour_data.append(tour_fin)
        grand_total_revenue += Decimal(str(tour_fin['total_estimated_revenue']))
        grand_total_tickets += tour_fin['total_sold_tickets']
        grand_total_capacity += tour_fin['total_capacity']

    avg_fill = (grand_total_tickets / grand_total_capacity * 100) if grand_total_capacity > 0 else 0

    return {
        'tours': all_tour_data,
        'num_tours': len(tours),
        'total_stops': sum(t['num_stops'] for t in all_tour_data),
        'grand_total_revenue': float(grand_total_revenue),
        'grand_total_tickets': grand_total_tickets,
        'grand_total_capacity': grand_total_capacity,
        'overall_fill_rate': round(avg_fill, 1),
    }


def calculate_settlement(tour_stop) -> Dict[str, Any]:
    """
    Calculate settlement (feuille de règlement) for a single tour stop.

    R2 & R5: Settlement professionnel selon standards industrie:
    - GBOR (Gross Box Office Receipts) - Recettes brutes
    - Ticketing fees déduction (R2)
    - NBOR (Net Box Office Receipts) - Recettes nettes (R2)
    - Venue rental cost (location salle)
    - Promoter expenses (R4/R5)
    - Split Point calculation (R5)
    - Artist payment: max(guarantee, split_point_backend)

    Settlement determines artist payment based on:
    - Guarantee (fixed amount)
    - Door deal (% of NET receipts after expenses)
    - Split Point: promoter_expenses + guarantee + venue_rental_cost
    - Artist receives the HIGHER of guarantee OR door deal on revenue above split point

    Returns complete settlement breakdown for PDF/display.
    """
    guarantee = Decimal(str(tour_stop.guarantee or 0))
    venue_rental_cost = Decimal(str(tour_stop.venue_rental_cost or 0))
    door_deal_pct = Decimal(str(tour_stop.door_deal_percentage or 0))
    ticketing_fee_pct = Decimal(str(tour_stop.ticketing_fee_percentage or 5))  # R2: Default 5%
    capacity = (tour_stop.venue.capacity or 0) if tour_stop.venue else 0
    currency = tour_stop.currency or 'EUR'

    # R4: Get promoter expenses if available
    promoter_expenses_total = Decimal('0')
    promoter_expenses_breakdown = None
    if hasattr(tour_stop, 'promotor_expenses') and tour_stop.promotor_expenses:
        promoter_expenses_total = Decimal(str(tour_stop.promotor_expenses.total_expenses))
        promoter_expenses_breakdown = tour_stop.promotor_expenses.expenses_breakdown

    # ===== BOX OFFICE CALCULATIONS =====

    # Tier-aware ticket calculations
    if tour_stop.has_tiers:
        sold_tickets = tour_stop.total_sold_tickets
        gross_revenue = Decimal(str(tour_stop.gross_ticket_revenue))
        ticket_price = Decimal(str(tour_stop.weighted_avg_price))
        tier_breakdown = tour_stop.tier_breakdown
    else:
        ticket_price = Decimal(str(tour_stop.ticket_price or 0))
        sold_tickets = tour_stop.sold_tickets or 0
        gross_revenue = ticket_price * sold_tickets
        tier_breakdown = None

    fill_rate = (sold_tickets / capacity * 100) if capacity > 0 else 0
    avg_ticket_price = (gross_revenue / sold_tickets) if sold_tickets > 0 else Decimal('0')

    # R2: Ticketing fees and NBOR
    ticketing_fees = gross_revenue * (ticketing_fee_pct / 100)
    nbor = gross_revenue - ticketing_fees  # Net Box Office Receipts

    # ===== SPLIT POINT CALCULATION (R5) =====

    # Split Point = Promoter recovers expenses + guarantee + venue rental before artist gets backend
    split_point = promoter_expenses_total + guarantee + venue_rental_cost

    # Revenue available for backend split (after split point)
    backend_base = max(nbor - split_point, Decimal('0'))

    # Door deal amount on backend (above split point)
    door_deal_amount = backend_base * (door_deal_pct / 100) if door_deal_pct > 0 else Decimal('0')

    # Simple door deal (% of NBOR) for comparison - legacy calculation
    simple_door_deal = nbor * (door_deal_pct / 100) if door_deal_pct > 0 else Decimal('0')

    # ===== BREAK-EVEN CALCULATION =====

    # Break-even: tickets needed for NBOR to equal split_point
    break_even_tickets = 0
    break_even_revenue = Decimal('0')
    if ticket_price > 0 and ticketing_fee_pct < 100:
        # NBOR = ticket_price * tickets * (1 - ticketing_fee_pct/100)
        # split_point = NBOR → tickets = split_point / (ticket_price * net_multiplier)
        net_multiplier = (100 - ticketing_fee_pct) / 100
        if net_multiplier > 0:
            break_even_tickets = int(split_point / (ticket_price * net_multiplier)) if split_point > 0 else 0
            break_even_revenue = split_point

    # ===== ARTIST PAYMENT DETERMINATION =====

    # Payment type: which method benefits artist more?
    # Option 1: Guarantee only
    # Option 2: Guarantee + backend door deal (if NBOR > split_point)
    # Option 3: Simple door deal (if no expenses tracked - legacy)

    if promoter_expenses_total > 0:
        # R5: Full split point model
        artist_payment = guarantee + door_deal_amount
        payment_type = 'split_point' if door_deal_amount > 0 else 'guarantee'
    else:
        # Legacy: simple versus deal (higher of guarantee vs simple door deal)
        if simple_door_deal > guarantee:
            artist_payment = simple_door_deal
            payment_type = 'door_deal'
        else:
            artist_payment = guarantee
            payment_type = 'guarantee'

    # ===== PROMOTER/VENUE SHARE =====

    # Promoter keeps: NBOR - artist_payment
    venue_share = nbor - artist_payment if nbor > artist_payment else Decimal('0')

    # Promoter profit: venue_share - promoter_expenses
    promoter_profit = venue_share - promoter_expenses_total

    return {
        # Event info
        'stop_id': tour_stop.id,
        'tour_id': tour_stop.tour_id,
        'tour_name': tour_stop.tour.name if tour_stop.tour else 'Événement Libre',
        'band_name': (
            tour_stop.tour.band.name if tour_stop.tour and tour_stop.tour.band
            else (tour_stop.band.name if tour_stop.band else 'N/A')
        ),
        'date': tour_stop.date,
        'venue_name': tour_stop.venue.name if tour_stop.venue else 'N/A',
        'venue_city': tour_stop.venue.city if tour_stop.venue else 'N/A',
        'venue_country': tour_stop.venue.country if tour_stop.venue else 'N/A',
        'status': tour_stop.status.value if tour_stop.status else 'unknown',

        # Box Office - GBOR (R2)
        'capacity': capacity,
        'sold_tickets': sold_tickets,
        'fill_rate': round(float(fill_rate), 1),
        'ticket_price': float(ticket_price),
        'avg_ticket_price': float(avg_ticket_price),
        'gross_revenue': float(gross_revenue),  # GBOR
        'has_tiers': tour_stop.has_tiers,
        'tier_breakdown': tier_breakdown,

        # R2: Ticketing fees and NBOR
        'ticketing_fee_percentage': float(ticketing_fee_pct),
        'ticketing_fees': float(ticketing_fees),
        'nbor': float(nbor),  # Net Box Office Receipts

        # R4: Promoter expenses (dict with total and breakdown for template access)
        'promoter_expenses': {
            'total': float(promoter_expenses_total),
            **(promoter_expenses_breakdown or {})
        },

        # Deal structure
        'guarantee': float(guarantee),
        'venue_rental_cost': float(venue_rental_cost),
        'door_deal_percentage': float(door_deal_pct),
        'door_deal_amount': float(door_deal_amount),  # Backend amount
        'simple_door_deal': float(simple_door_deal),  # Legacy calculation

        # R5: Split Point
        'split_point': float(split_point),
        'backend_base': float(backend_base),  # Revenue above split point

        # Break-even
        'break_even_tickets': break_even_tickets,
        'break_even_revenue': float(break_even_revenue),

        # Final settlement
        'artist_payment': float(artist_payment),
        'payment_type': payment_type,  # 'guarantee', 'door_deal', or 'split_point'
        'venue_share': float(venue_share),
        'promoter_profit': float(promoter_profit),  # R5: After expenses
        'currency': currency,

        # Profit/Loss indicators
        'is_above_break_even': sold_tickets >= break_even_tickets if break_even_tickets > 0 else True,
        'profit_above_guarantee': float(door_deal_amount) if door_deal_amount > 0 else 0,
        'has_promoter_expenses': promoter_expenses_total > 0,
    }


def calculate_dashboard_kpis(tours) -> Dict[str, Any]:
    """
    Calculate advanced KPIs for financial dashboard.

    Returns metrics with comparisons and trends for professional display.

    Bug Fixes (06/01/2026):
    - #3: Ajout stops_without_capacity pour identifier venues sans capacité
    - #4: Fill rate = None si capacity inconnue (afficher "N/A")
    - #5: Ajout total_ticket_revenue (GBOR) distinct des revenus artiste
    """
    from collections import defaultdict

    # Current period data
    all_stops = []
    monthly_revenue = defaultdict(lambda: Decimal('0'))
    revenue_by_tour = {}
    total_guarantees = Decimal('0')
    total_door_deals = Decimal('0')
    total_ticket_revenue = Decimal('0')  # Bug #5: GBOR distinct

    for tour in tours:
        tour_revenue = Decimal('0')
        for stop in tour.stops:
            stop_data = calculate_stop_financials(stop)
            all_stops.append(stop_data)

            # Monthly aggregation
            month_key = stop.date.strftime('%Y-%m') if stop.date else 'unknown'
            monthly_revenue[month_key] += Decimal(str(stop_data['total_estimated_revenue']))

            # Totals
            total_guarantees += Decimal(str(stop_data['guarantee']))
            total_door_deals += Decimal(str(stop_data['door_deal_revenue']))
            total_ticket_revenue += Decimal(str(stop_data['ticket_revenue']))  # Bug #5: GBOR
            tour_revenue += Decimal(str(stop_data['total_estimated_revenue']))

        revenue_by_tour[tour.name] = float(tour_revenue)

    # Calculate overall metrics
    total_revenue = total_guarantees + total_door_deals
    total_tickets = sum(s['sold_tickets'] for s in all_stops)
    total_capacity = sum(s['capacity'] for s in all_stops)

    # Bug #3: Compteur venues sans capacité connue
    stops_without_capacity = sum(1 for s in all_stops if s['capacity'] == 0)
    stops_with_capacity = len(all_stops) - stops_without_capacity

    # Bug #4: Fill rate intelligent - None si capacity inconnue
    if total_capacity > 0:
        avg_fill_rate = (total_tickets / total_capacity * 100)
    elif total_tickets > 0:
        # Billets vendus mais aucune capacité connue - impossible de calculer
        avg_fill_rate = None
    else:
        avg_fill_rate = 0

    avg_ticket_price = (total_ticket_revenue / total_tickets) if total_tickets > 0 else Decimal('0')

    # Revenue breakdown percentages
    guarantee_pct = (total_guarantees / total_revenue * 100) if total_revenue > 0 else 0
    door_deal_pct = (total_door_deals / total_revenue * 100) if total_revenue > 0 else 0

    # Sort monthly data for charts
    sorted_months = sorted(monthly_revenue.keys())
    monthly_data = [{'month': m, 'revenue': float(monthly_revenue[m])} for m in sorted_months]

    # Top performing stops
    top_stops = sorted(all_stops, key=lambda x: x['total_estimated_revenue'], reverse=True)[:10]

    # ===== LOGISTICS COSTS AGGREGATION =====
    total_logistics = {
        'transport': Decimal('0'),
        'accommodation': Decimal('0'),
        'equipment': Decimal('0'),
        'services': Decimal('0'),
        'total': Decimal('0')
    }
    logistics_by_paid_by = {}
    logistics_unpaid = Decimal('0')

    for tour in tours:
        tour_logistics = calculate_tour_logistics_costs(tour)
        for key in ['transport', 'accommodation', 'equipment', 'services', 'total']:
            total_logistics[key] += Decimal(str(tour_logistics['total'][key]))
        for paid_by, amount in tour_logistics['by_paid_by'].items():
            logistics_by_paid_by[paid_by] = logistics_by_paid_by.get(paid_by, Decimal('0')) + Decimal(str(amount))
        logistics_unpaid += Decimal(str(tour_logistics['unpaid_total']))

    return {
        # Main KPIs
        'total_revenue': float(total_revenue),
        'total_tickets': total_tickets,
        'total_capacity': total_capacity,
        'avg_fill_rate': round(avg_fill_rate, 1) if avg_fill_rate is not None else None,  # Bug #4
        'avg_ticket_price': float(avg_ticket_price),
        'num_shows': len(all_stops),

        # Bug #5: GBOR (Revenus Billetterie) distinct des revenus artiste
        'total_ticket_revenue': float(total_ticket_revenue),
        'formatted_ticket_revenue': format_currency(float(total_ticket_revenue), 'EUR'),

        # Bug #3: Compteur venues sans capacité
        'stops_without_capacity': stops_without_capacity,
        'stops_with_capacity': stops_with_capacity,

        # Revenue breakdown
        'total_guarantees': float(total_guarantees),
        'total_door_deals': float(total_door_deals),
        'guarantee_percentage': round(float(guarantee_pct), 1),
        'door_deal_percentage': round(float(door_deal_pct), 1),

        # Chart data
        'monthly_revenue': monthly_data,
        'revenue_by_tour': revenue_by_tour,
        'top_stops': top_stops,

        # Formatted values for display
        'formatted_revenue': format_currency(float(total_revenue), 'EUR'),
        'formatted_guarantees': format_currency(float(total_guarantees), 'EUR'),
        'formatted_door_deals': format_currency(float(total_door_deals), 'EUR'),

        # ===== LOGISTICS COSTS (Informatif) =====
        'logistics_costs': {
            'transport': float(total_logistics['transport']),
            'accommodation': float(total_logistics['accommodation']),
            'equipment': float(total_logistics['equipment']),
            'services': float(total_logistics['services']),
            'total': float(total_logistics['total']),
        },
        'logistics_by_paid_by': {k: float(v) for k, v in logistics_by_paid_by.items()},
        'logistics_unpaid': float(logistics_unpaid),
        'formatted_logistics_total': format_currency(float(total_logistics['total']), 'EUR'),
        'formatted_logistics_transport': format_currency(float(total_logistics['transport']), 'EUR'),
        'formatted_logistics_accommodation': format_currency(float(total_logistics['accommodation']), 'EUR'),
        'formatted_logistics_equipment': format_currency(float(total_logistics['equipment']), 'EUR'),
        'formatted_logistics_services': format_currency(float(total_logistics['services']), 'EUR'),
    }


def format_currency(amount: float, currency: str = 'EUR') -> str:
    """Format amount with currency symbol."""
    symbols = {
        'EUR': '€',
        'USD': '$',
        'GBP': '£',
        'CHF': 'CHF ',
    }
    symbol = symbols.get(currency, f'{currency} ')
    return f"{symbol}{amount:,.2f}"


# ===== LOGISTICS COSTS CALCULATION =====

# Categories for logistics type grouping
TRANSPORT_TYPES = ['FLIGHT', 'TRAIN', 'BUS', 'FERRY', 'RENTAL_CAR', 'TAXI', 'GROUND_TRANSPORT']
ACCOMMODATION_TYPES = ['HOTEL', 'APARTMENT']
EQUIPMENT_TYPES = ['RENTAL', 'EQUIPMENT', 'BACKLINE']
# Services: CATERING, MEAL, PARKING, OTHER


def calculate_logistics_costs(tour_stop) -> Dict[str, Any]:
    """
    Agrège les coûts logistiques d'un stop par catégorie.

    Returns dict with:
        - transport: Total transport costs (flights, trains, buses, etc.)
        - accommodation: Total accommodation costs (hotels, apartments)
        - equipment: Total equipment costs (rentals, backline)
        - services: Total service costs (catering, meals, parking, other)
        - total: Grand total of all logistics costs
        - by_type: Detailed breakdown by logistics type
        - by_paid_by: Breakdown by who paid (band, promoter, etc.)
        - unpaid_total: Total of unpaid costs
    """
    costs = {
        'transport': Decimal('0'),
        'accommodation': Decimal('0'),
        'equipment': Decimal('0'),
        'services': Decimal('0'),
        'total': Decimal('0')
    }
    costs_by_type = {}
    costs_by_paid_by = {}
    unpaid_total = Decimal('0')

    # Check if stop has logistics attribute
    if not hasattr(tour_stop, 'logistics'):
        return {
            'transport': 0, 'accommodation': 0, 'equipment': 0,
            'services': 0, 'total': 0, 'by_type': {},
            'by_paid_by': {}, 'unpaid_total': 0
        }

    for item in tour_stop.logistics:
        if item.cost:
            # Get type name (handle enum or string)
            type_name = item.logistics_type.value if hasattr(item.logistics_type, 'value') else str(item.logistics_type)
            cost_val = Decimal(str(item.cost))

            # Agrégation par type précis
            costs_by_type[type_name] = costs_by_type.get(type_name, Decimal('0')) + cost_val

            # Agrégation par catégorie
            if type_name in TRANSPORT_TYPES:
                costs['transport'] += cost_val
            elif type_name in ACCOMMODATION_TYPES:
                costs['accommodation'] += cost_val
            elif type_name in EQUIPMENT_TYPES:
                costs['equipment'] += cost_val
            else:
                costs['services'] += cost_val

            # Track by paid_by
            paid_by = item.paid_by or 'non_specifie'
            costs_by_paid_by[paid_by] = costs_by_paid_by.get(paid_by, Decimal('0')) + cost_val

            # Track unpaid
            if not item.is_paid:
                unpaid_total += cost_val

    costs['total'] = costs['transport'] + costs['accommodation'] + costs['equipment'] + costs['services']

    return {
        'transport': float(costs['transport']),
        'accommodation': float(costs['accommodation']),
        'equipment': float(costs['equipment']),
        'services': float(costs['services']),
        'total': float(costs['total']),
        'by_type': {k: float(v) for k, v in costs_by_type.items()},
        'by_paid_by': {k: float(v) for k, v in costs_by_paid_by.items()},
        'unpaid_total': float(unpaid_total)
    }


def calculate_tour_logistics_costs(tour) -> Dict[str, Any]:
    """
    Agrège tous les coûts logistiques d'une tournée.

    Returns dict with:
        - total: Aggregated costs by category for entire tour
        - by_stop: Dict of stop_id -> costs breakdown
        - unpaid_total: Total unpaid costs across tour
        - by_paid_by: Aggregated by who paid across all stops
    """
    total = {
        'transport': Decimal('0'),
        'accommodation': Decimal('0'),
        'equipment': Decimal('0'),
        'services': Decimal('0'),
        'total': Decimal('0')
    }
    by_stop = {}
    all_by_paid_by = {}
    unpaid_total = Decimal('0')

    for stop in tour.stops:
        stop_costs = calculate_logistics_costs(stop)
        by_stop[stop.id] = stop_costs

        # Aggregate totals
        for key in ['transport', 'accommodation', 'equipment', 'services', 'total']:
            total[key] += Decimal(str(stop_costs[key]))

        # Aggregate by paid_by
        for paid_by, amount in stop_costs['by_paid_by'].items():
            all_by_paid_by[paid_by] = all_by_paid_by.get(paid_by, Decimal('0')) + Decimal(str(amount))

        unpaid_total += Decimal(str(stop_costs['unpaid_total']))

    return {
        'total': {k: float(v) for k, v in total.items()},
        'by_stop': by_stop,
        'by_paid_by': {k: float(v) for k, v in all_by_paid_by.items()},
        'unpaid_total': float(unpaid_total)
    }


def generate_csv_report(tour_data: Dict[str, Any]) -> str:
    """
    Generate CSV content for a tour financial report.

    Returns CSV string ready for download.
    """
    import csv
    from io import StringIO

    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'Date', 'Venue', 'Ville', 'Statut',
        'Cachet (Guarantee)', 'Location Salle', 'Prix Billet', 'Billets Vendus',
        'Capacité', 'Taux Remplissage (%)',
        'Revenus Billetterie', 'Part Porte', 'Revenu Total Estimé',
        'Devise'
    ])

    # Data rows
    for stop in tour_data['stops_data']:
        writer.writerow([
            stop['date'].strftime('%d/%m/%Y') if isinstance(stop['date'], date) else stop['date'],
            stop['venue_name'],
            stop['venue_city'],
            stop['status'],
            stop['guarantee'],
            stop.get('venue_rental_cost', 0),
            stop.get('ticket_price', 0),
            stop['sold_tickets'],
            stop['capacity'],
            stop['fill_rate'],
            stop['ticket_revenue'],
            stop['door_deal_revenue'],
            stop['total_estimated_revenue'],
            stop['currency']
        ])

    # Summary row
    writer.writerow([])
    writer.writerow(['TOTAL', '', '', '',
                     tour_data['total_guarantee'],
                     tour_data.get('total_venue_rental_cost', 0),
                     '',
                     tour_data['total_sold_tickets'],
                     tour_data['total_capacity'],
                     tour_data['avg_fill_rate'],
                     tour_data['total_ticket_revenue'],
                     tour_data['total_door_deal_revenue'],
                     tour_data['total_estimated_revenue'],
                     tour_data['currency']])

    output.seek(0)
    return output.getvalue()
