"""
PDF Generator utility for Tour Manager.
Uses xhtml2pdf for cloud-compatible PDF generation.
Production-ready: works on all cloud platforms (Heroku, Railway, Render, Vercel, etc.)
No system dependencies required (pure Python).
"""
from io import BytesIO
from datetime import datetime
from typing import Dict, Any

try:
    from xhtml2pdf import pisa
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Alias for backwards compatibility with existing code
WEASYPRINT_AVAILABLE = PDF_AVAILABLE


def format_currency(amount: float, currency: str = 'EUR') -> str:
    """Format amount with currency symbol."""
    symbols = {
        'EUR': '\u20ac',
        'USD': '$',
        'GBP': '\u00a3',
        'CHF': 'CHF ',
    }
    symbol = symbols.get(currency, f'{currency} ')
    return f"{symbol}{amount:,.2f}"


def generate_settlement_pdf(settlement: Dict[str, Any]) -> bytes:
    """
    Generate a professional PDF settlement report using xhtml2pdf.
    Works on all cloud platforms without system dependencies.

    Args:
        settlement: Settlement data dictionary from calculate_settlement()

    Returns:
        PDF file as bytes
    """
    if not PDF_AVAILABLE:
        raise ImportError("xhtml2pdf is required for PDF generation. Install with: pip install xhtml2pdf")

    currency = settlement.get('currency', 'EUR')
    html_content = _build_settlement_html(settlement, currency)

    # Convert HTML to PDF
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_content.encode('utf-8')), result)

    if pdf.err:
        raise Exception(f"PDF generation error: {pdf.err}")

    return result.getvalue()


def _build_settlement_html(s: Dict[str, Any], currency: str) -> str:
    """Build xhtml2pdf-compatible HTML for settlement report."""

    # Format date
    date_str = s['date'].strftime('%d/%m/%Y') if s['date'] else 'N/A'
    date_full = s['date'].strftime('%A %d %B %Y') if s['date'] else 'N/A'

    # R2: NBOR calculation values
    nbor = s.get('nbor', s['gross_revenue'])
    ticketing_fees = s.get('ticketing_fees', 0)
    ticketing_fee_pct = s.get('ticketing_fee_percentage', 5)

    # R4: Promoter expenses
    promoter_expenses = s.get('promoter_expenses', {})
    promoter_total = promoter_expenses.get('total', 0) if promoter_expenses else 0

    # R5: Split point values
    split_point = s.get('split_point', 0)
    backend_base = s.get('backend_base', 0)

    # Door deal section (conditional)
    door_deal_html = ""
    if s['door_deal_percentage'] > 0:
        door_deal_html = f'''
                        <tr>
                            <td class="label">Pourcentage Door Deal</td>
                            <td class="value">{s['door_deal_percentage']}%</td>
                        </tr>
                        <tr class="highlight">
                            <td class="label">Seuil de rentabilite (Break-even)</td>
                            <td class="value">{s['break_even_tickets']} billets</td>
                        </tr>'''

    # R4: Promoter expenses section (conditional)
    promoter_expenses_html = ""
    if promoter_total > 0:
        expense_rows = ""
        if promoter_expenses.get('venue_fee', 0) > 0:
            expense_rows += f'<tr><td class="label">Location salle</td><td class="value">{format_currency(promoter_expenses["venue_fee"], currency)}</td></tr>'
        if promoter_expenses.get('production_cost', 0) > 0:
            expense_rows += f'<tr><td class="label">Couts de production</td><td class="value">{format_currency(promoter_expenses["production_cost"], currency)}</td></tr>'
        if promoter_expenses.get('marketing_cost', 0) > 0:
            expense_rows += f'<tr><td class="label">Marketing/Promo</td><td class="value">{format_currency(promoter_expenses["marketing_cost"], currency)}</td></tr>'
        if promoter_expenses.get('insurance', 0) > 0:
            expense_rows += f'<tr><td class="label">Assurance</td><td class="value">{format_currency(promoter_expenses["insurance"], currency)}</td></tr>'
        if promoter_expenses.get('security', 0) > 0:
            expense_rows += f'<tr><td class="label">Securite</td><td class="value">{format_currency(promoter_expenses["security"], currency)}</td></tr>'
        if promoter_expenses.get('catering', 0) > 0:
            expense_rows += f'<tr><td class="label">Catering</td><td class="value">{format_currency(promoter_expenses["catering"], currency)}</td></tr>'
        if promoter_expenses.get('other', 0) > 0:
            other_desc = f' ({promoter_expenses.get("other_description", "")})' if promoter_expenses.get('other_description') else ''
            expense_rows += f'<tr><td class="label">Autres{other_desc}</td><td class="value">{format_currency(promoter_expenses["other"], currency)}</td></tr>'

        promoter_expenses_html = f'''
    <div class="section">
        <div class="section-header">DEPENSES PROMOTEUR</div>
        <div class="section-content">
            <table class="data">
                {expense_rows}
                <tr class="total">
                    <td class="label">TOTAL DEPENSES</td>
                    <td class="value negative">{format_currency(promoter_total, currency)}</td>
                </tr>
            </table>
        </div>
    </div>'''

    # Payment calculation rows - depends on whether we have split point
    if promoter_total > 0:
        # R5: Split Point mode
        door_deal_amount_html = f'''
                        <tr>
                            <td class="label">Recettes nettes (NBOR)</td>
                            <td class="value">{format_currency(nbor, currency)}</td>
                        </tr>
                        <tr>
                            <td class="label">Split Point (Depenses + Guarantee)</td>
                            <td class="value">{format_currency(split_point, currency)}</td>
                        </tr>
                        <tr>
                            <td class="label">Base pour Backend (NBOR - Split Point)</td>
                            <td class="value">{format_currency(backend_base, currency)}</td>
                        </tr>'''
        if s['door_deal_percentage'] > 0:
            door_deal_amount_html += f'''
                        <tr>
                            <td class="label">Backend artiste ({s['door_deal_percentage']}%)</td>
                            <td class="value positive">{format_currency(s['door_deal_amount'], currency)}</td>
                        </tr>'''
    else:
        # Legacy versus deal
        door_deal_amount_html = f'''
                        <tr>
                            <td class="label">Recettes nettes (NBOR)</td>
                            <td class="value">{format_currency(nbor, currency)}</td>
                        </tr>'''
        if s['door_deal_percentage'] > 0:
            door_deal_amount_html += f'''
                        <tr>
                            <td class="label">Part artiste ({s['door_deal_percentage']}%)</td>
                            <td class="value">{format_currency(s['door_deal_amount'], currency)}</td>
                        </tr>'''

    # Profit above guarantee (conditional)
    profit_html = ""
    if s.get('profit_above_guarantee', 0) > 0:
        profit_html = f'''
                        <tr>
                            <td class="label">Bonus au-dessus du guarantee</td>
                            <td class="value positive">+{format_currency(s['profit_above_guarantee'], currency)}</td>
                        </tr>'''

    # Payment type badge - includes split_point type now
    if s['payment_type'] == 'split_point':
        payment_type_text = 'Split Point (standard industrie)'
    elif s['payment_type'] == 'door_deal':
        payment_type_text = 'Door Deal (plus avantageux)'
    else:
        payment_type_text = 'Guarantee (protege)'

    # Fill rate styling
    fill_rate_class = _get_fill_rate_class(s['fill_rate'])
    fill_rate_badge = _get_fill_rate_badge(s['fill_rate'])

    # Deal type
    deal_type = _get_deal_type(s)

    # Status badge color
    status_bg = '#198754' if s['status'] == 'confirmed' else '#ffc107'
    status_color = 'white' if s['status'] == 'confirmed' else '#333'

    return f'''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Settlement - {s['venue_name']}</title>
    <style>
        @page {{
            size: A4;
            margin: 1.5cm;
        }}

        body {{
            font-family: Helvetica, Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.4;
            color: #333;
        }}

        .header {{
            background-color: #0d6efd;
            color: white;
            padding: 15px;
            margin-bottom: 15px;
        }}

        .header h1 {{
            font-size: 16pt;
            margin: 0 0 5px 0;
        }}

        .header-info {{
            font-size: 9pt;
            opacity: 0.9;
        }}

        .badge {{
            display: inline-block;
            padding: 2px 8px;
            font-size: 8pt;
            font-weight: 600;
            margin-right: 5px;
        }}

        .badge-secondary {{
            background-color: #6c757d;
            color: white;
        }}

        .section {{
            border: 1px solid #dee2e6;
            margin-bottom: 12px;
        }}

        .section-header {{
            background-color: #f8f9fa;
            padding: 8px 12px;
            font-weight: bold;
            border-bottom: 1px solid #dee2e6;
            font-size: 11pt;
        }}

        .section-content {{
            padding: 10px 12px;
        }}

        table.data {{
            width: 100%;
            border-collapse: collapse;
        }}

        table.data td {{
            padding: 6px 0;
            border-bottom: 1px solid #f0f0f0;
        }}

        table.data td.label {{
            color: #666;
            width: 60%;
        }}

        table.data td.value {{
            text-align: right;
            font-weight: 500;
            width: 40%;
        }}

        table.data tr.highlight td {{
            background-color: #f8f9fa;
            padding: 6px 8px;
        }}

        table.data tr.total td {{
            background-color: #e8f4f8;
            font-weight: bold;
            padding: 8px;
        }}

        table.data tr.artist-payment td {{
            background-color: #d4edda;
            font-weight: bold;
            font-size: 11pt;
            padding: 10px 8px;
        }}

        .positive {{
            color: #198754;
        }}

        .negative {{
            color: #dc3545;
        }}

        .fill-rate-excellent {{ color: #198754; }}
        .fill-rate-good {{ color: #0d6efd; }}
        .fill-rate-medium {{ color: #ffc107; }}
        .fill-rate-low {{ color: #dc3545; }}

        table.two-col {{
            width: 100%;
            border-collapse: collapse;
        }}

        table.two-col > tbody > tr > td {{
            width: 50%;
            vertical-align: top;
            padding: 0 5px;
        }}

        .summary {{
            background-color: #f8f9fa;
            padding: 15px;
            margin-bottom: 15px;
        }}

        table.summary-grid {{
            width: 100%;
        }}

        table.summary-grid td {{
            text-align: center;
            padding: 10px;
            width: 25%;
        }}

        .summary-label {{
            color: #6c757d;
            font-size: 9pt;
            margin-bottom: 5px;
        }}

        .summary-value {{
            font-size: 14pt;
            font-weight: 700;
        }}

        .signature-box {{
            border: 1px dashed #ccc;
            padding: 10px;
            margin-top: 10px;
        }}

        .signature-title {{
            font-weight: bold;
            margin-bottom: 5px;
        }}

        .signature-line {{
            border-bottom: 1px solid #333;
            margin: 40px 0 5px 0;
        }}

        .signature-fields {{
            font-size: 8pt;
            color: #6c757d;
        }}

        .footer {{
            text-align: center;
            color: #6c757d;
            font-size: 8pt;
            margin-top: 20px;
            border-top: 1px solid #ddd;
            padding-top: 10px;
        }}
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <h1>{s['band_name']}</h1>
        <div class="header-info">
            <strong>{s['venue_name']}</strong> - {s['venue_city']}, {s['venue_country']}<br/>
            {date_full}
        </div>
        <div style="margin-top: 10px;">
            <span class="badge badge-secondary">{s['tour_name']}</span>
            <span class="badge" style="background-color: {status_bg}; color: {status_color};">
                {s['status'].capitalize() if s['status'] else 'N/A'}
            </span>
        </div>
    </div>

    <!-- Two columns: Box Office + Deal Structure -->
    <table class="two-col">
        <tr>
            <td>
                <div class="section">
                    <div class="section-header">BOX OFFICE (GBOR)</div>
                    <div class="section-content">
                        <table class="data">
                            <tr>
                                <td class="label">Capacite salle</td>
                                <td class="value">{s['capacity']:,} places</td>
                            </tr>
                            <tr>
                                <td class="label">Billets vendus</td>
                                <td class="value">{s['sold_tickets']:,}</td>
                            </tr>
                            <tr class="highlight">
                                <td class="label">Taux de remplissage</td>
                                <td class="value {fill_rate_class}">{s['fill_rate']}% ({fill_rate_badge})</td>
                            </tr>
                            <tr>
                                <td class="label">Prix du billet</td>
                                <td class="value">{format_currency(s['ticket_price'], currency)}</td>
                            </tr>
                            <tr class="total">
                                <td class="label">RECETTES BRUTES (GBOR)</td>
                                <td class="value positive">{format_currency(s['gross_revenue'], currency)}</td>
                            </tr>
                        </table>
                    </div>
                </div>
            </td>
            <td>
                <div class="section">
                    <div class="section-header">STRUCTURE DU DEAL</div>
                    <div class="section-content">
                        <table class="data">
                            <tr>
                                <td class="label">Type de deal</td>
                                <td class="value">{deal_type}</td>
                            </tr>
                            <tr>
                                <td class="label">Cachet garanti</td>
                                <td class="value">{format_currency(s['guarantee'], currency)}</td>
                            </tr>
                            {door_deal_html}
                        </table>
                    </div>
                </div>
            </td>
        </tr>
    </table>

    <!-- R2: NBOR Section - Net Box Office Receipts -->
    <div class="section">
        <div class="section-header">RECETTES NETTES (NBOR)</div>
        <div class="section-content">
            <table class="data">
                <tr>
                    <td class="label">Recettes brutes (GBOR)</td>
                    <td class="value">{format_currency(s['gross_revenue'], currency)}</td>
                </tr>
                <tr>
                    <td class="label">Frais de billetterie ({ticketing_fee_pct}%)</td>
                    <td class="value negative">-{format_currency(ticketing_fees, currency)}</td>
                </tr>
                <tr class="total">
                    <td class="label">RECETTES NETTES (NBOR)</td>
                    <td class="value positive">{format_currency(nbor, currency)}</td>
                </tr>
            </table>
        </div>
    </div>

    {promoter_expenses_html}

    <!-- Payment Calculation Section -->
    <div class="section">
        <div class="section-header">CALCUL DU PAIEMENT ARTISTE</div>
        <div class="section-content">
            <table class="data">
                <tr>
                    <td class="label">Recettes nettes (NBOR)</td>
                    <td class="value">{format_currency(nbor, currency)}</td>
                </tr>
                {door_deal_amount_html}
                <tr>
                    <td class="label">vs. Cachet garanti</td>
                    <td class="value">{format_currency(s['guarantee'], currency)}</td>
                </tr>
                <tr class="highlight">
                    <td class="label">Methode de paiement retenue</td>
                    <td class="value">{payment_type_text}</td>
                </tr>
                {profit_html}
                <tr class="artist-payment">
                    <td class="label">PAIEMENT ARTISTE</td>
                    <td class="value positive">{format_currency(s['artist_payment'], currency)}</td>
                </tr>
            </table>
        </div>
    </div>

    <!-- Venue Share Section -->
    <div class="section">
        <div class="section-header">PART PROMOTEUR / SALLE</div>
        <div class="section-content">
            <table class="data">
                <tr>
                    <td class="label">Recettes nettes (NBOR)</td>
                    <td class="value">{format_currency(nbor, currency)}</td>
                </tr>
                <tr>
                    <td class="label">- Paiement artiste</td>
                    <td class="value negative">-{format_currency(s['artist_payment'], currency)}</td>
                </tr>
                <tr class="total">
                    <td class="label">PART PROMOTEUR</td>
                    <td class="value">{format_currency(s['venue_share'], currency)}</td>
                </tr>
            </table>
        </div>
    </div>

    <!-- Summary - 6 colonnes -->
    <div class="summary">
        <table class="summary-grid">
            <tr>
                <td style="width: 16.66%;">
                    <div class="summary-label">GBOR</div>
                    <div class="summary-value" style="color: #0d6efd; font-size: 11pt;">{format_currency(s['gross_revenue'], currency)}</div>
                </td>
                <td style="width: 16.66%;">
                    <div class="summary-label">NBOR</div>
                    <div class="summary-value" style="color: #17a2b8; font-size: 11pt;">{format_currency(nbor, currency)}</div>
                </td>
                <td style="width: 16.66%;">
                    <div class="summary-label">Artiste</div>
                    <div class="summary-value" style="color: #198754; font-size: 11pt;">{format_currency(s['artist_payment'], currency)}</div>
                </td>
                <td style="width: 16.66%;">
                    <div class="summary-label">Promoteur</div>
                    <div class="summary-value" style="color: #6c757d; font-size: 11pt;">{format_currency(s['venue_share'], currency)}</div>
                </td>
                <td style="width: 16.66%;">
                    <div class="summary-label">Remplissage</div>
                    <div class="summary-value {fill_rate_class}" style="font-size: 11pt;">{s['fill_rate']}%</div>
                </td>
                <td style="width: 16.66%;">
                    <div class="summary-label">Type</div>
                    <div class="summary-value" style="color: #6c757d; font-size: 9pt;">{deal_type}</div>
                </td>
            </tr>
        </table>
    </div>

    <!-- Signatures Section -->
    <div class="section">
        <div class="section-header">SIGNATURES</div>
        <div class="section-content">
            <table class="two-col">
                <tr>
                    <td>
                        <div class="signature-box">
                            <div class="signature-title">Representant de l'artiste / Tour Manager</div>
                            <div class="signature-line"></div>
                            <div class="signature-fields">
                                Nom: _______________________ &nbsp;&nbsp;&nbsp; Date: _______________________
                            </div>
                        </div>
                    </td>
                    <td>
                        <div class="signature-box">
                            <div class="signature-title">Promoteur / Responsable salle</div>
                            <div class="signature-line"></div>
                            <div class="signature-fields">
                                Nom: _______________________ &nbsp;&nbsp;&nbsp; Date: _______________________
                            </div>
                        </div>
                    </td>
                </tr>
            </table>
        </div>
    </div>

    <!-- Footer -->
    <div class="footer">
        <p>Ce document est une feuille de reglement generee par Tour Manager.</p>
        <p>Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')} - Reference: SETTLEMENT-{s['stop_id']}-{date_str.replace('/', '')}</p>
    </div>
</body>
</html>'''


def _get_fill_rate_class(fill_rate: float) -> str:
    """Get CSS class for fill rate coloring."""
    if fill_rate >= 90:
        return 'fill-rate-excellent'
    elif fill_rate >= 75:
        return 'fill-rate-good'
    elif fill_rate >= 50:
        return 'fill-rate-medium'
    else:
        return 'fill-rate-low'


def _get_fill_rate_badge(fill_rate: float) -> str:
    """Get badge text for fill rate."""
    if fill_rate >= 90:
        return 'Excellent'
    elif fill_rate >= 75:
        return 'Bon'
    elif fill_rate >= 50:
        return 'Moyen'
    else:
        return 'Faible'


def _get_deal_type(settlement: Dict[str, Any]) -> str:
    """Get deal type description."""
    if settlement['door_deal_percentage'] > 0 and settlement['guarantee'] > 0:
        return 'Hybrid (Guarantee + Door Deal)'
    elif settlement['door_deal_percentage'] > 0:
        return 'Door Deal'
    else:
        return 'Guarantee'


def generate_tour_pdf(tour) -> bytes:
    """
    Generate a PDF with tour schedule (all stops).

    Args:
        tour: Tour model instance

    Returns:
        PDF file as bytes
    """
    if not PDF_AVAILABLE:
        raise ImportError("xhtml2pdf is required for PDF generation. Install with: pip install xhtml2pdf")

    html_content = _build_tour_html(tour)

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_content.encode('utf-8')), result)

    if pdf.err:
        raise Exception(f"PDF generation error: {pdf.err}")

    return result.getvalue()


def _build_tour_html(tour) -> str:
    """Build xhtml2pdf-compatible HTML for tour schedule."""

    # Get tour dates
    start_date = tour.start_date.strftime('%d/%m/%Y') if tour.start_date else 'TBA'
    end_date = tour.end_date.strftime('%d/%m/%Y') if tour.end_date else 'TBA'
    band_name = tour.band.name if tour.band else 'TBA'

    # Sort stops by date
    stops = sorted(tour.stops, key=lambda s: s.date if s.date else datetime.max.date())

    # Build stops table rows
    stops_html = ""
    for stop in stops:
        date_str = stop.date.strftime('%a %d/%m/%Y') if stop.date else 'TBA'
        venue_name = stop.venue.name if stop.venue else 'TBA'
        city = stop.venue.city if stop.venue else ''
        country = stop.venue.country if stop.venue else ''
        location = f"{city}, {country}" if city else ''

        doors = stop.doors_time.strftime('%H:%M') if stop.doors_time else '-'
        show = stop.set_time.strftime('%H:%M') if stop.set_time else '-'

        status = stop.status.value if stop.status else '-'
        status_class = 'confirmed' if status == 'confirmed' else 'pending' if status == 'pending' else ''

        stops_html += f'''
            <tr>
                <td class="date">{date_str}</td>
                <td class="venue">{venue_name}</td>
                <td class="location">{location}</td>
                <td class="time">{doors}</td>
                <td class="time">{show}</td>
                <td class="status {status_class}">{status}</td>
            </tr>'''

    generation_date = datetime.now().strftime('%d/%m/%Y %H:%M')

    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            size: A4 landscape;
            margin: 1.5cm;
        }}
        body {{
            font-family: Helvetica, Arial, sans-serif;
            font-size: 10pt;
            color: #333;
            margin: 0;
            padding: 0;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            color: #C9A962;
            padding: 20px;
            margin: -1.5cm -1.5cm 20px -1.5cm;
            text-align: center;
        }}
        .header h1 {{
            margin: 0 0 5px 0;
            font-size: 24pt;
            color: #C9A962;
        }}
        .header h2 {{
            margin: 0;
            font-size: 14pt;
            color: #fff;
            font-weight: normal;
        }}
        .header .dates {{
            margin-top: 10px;
            font-size: 11pt;
            color: #aaa;
        }}
        .schedule-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        .schedule-table th {{
            background: #C9A962;
            color: #1a1a1a;
            padding: 10px 8px;
            text-align: left;
            font-weight: bold;
            font-size: 9pt;
            text-transform: uppercase;
        }}
        .schedule-table td {{
            padding: 8px;
            border-bottom: 1px solid #ddd;
            vertical-align: middle;
        }}
        .schedule-table tr:nth-child(even) {{
            background: #f9f9f9;
        }}
        .schedule-table .date {{
            font-weight: bold;
            white-space: nowrap;
        }}
        .schedule-table .venue {{
            font-weight: bold;
        }}
        .schedule-table .location {{
            color: #666;
            font-size: 9pt;
        }}
        .schedule-table .time {{
            text-align: center;
            font-family: monospace;
        }}
        .schedule-table .status {{
            text-align: center;
            font-size: 8pt;
            text-transform: uppercase;
            padding: 3px 8px;
            border-radius: 3px;
        }}
        .schedule-table .status.confirmed {{
            background: #d4edda;
            color: #155724;
        }}
        .schedule-table .status.pending {{
            background: #fff3cd;
            color: #856404;
        }}
        .footer {{
            margin-top: 20px;
            text-align: center;
            font-size: 8pt;
            color: #999;
        }}
        .total-stops {{
            margin-top: 15px;
            text-align: right;
            font-size: 10pt;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{band_name}</h1>
        <h2>{tour.name}</h2>
        <div class="dates">{start_date} - {end_date}</div>
    </div>

    <table class="schedule-table">
        <thead>
            <tr>
                <th>Date</th>
                <th>Venue</th>
                <th>Location</th>
                <th>Doors</th>
                <th>Show</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {stops_html}
        </tbody>
    </table>

    <div class="total-stops">
        Total: {len(stops)} date(s)
    </div>

    <div class="footer">
        Studio Palenque Tour - Generated on {generation_date}
    </div>
</body>
</html>'''

    return html


def generate_daysheet_pdf(stop) -> bytes:
    """
    Generate a PDF day sheet for a single tour stop.

    Args:
        stop: TourStop model instance

    Returns:
        PDF file as bytes
    """
    if not PDF_AVAILABLE:
        raise ImportError("xhtml2pdf is required for PDF generation. Install with: pip install xhtml2pdf")

    html_content = _build_daysheet_html(stop)

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html_content.encode('utf-8')), result)

    if pdf.err:
        raise Exception(f"PDF generation error: {pdf.err}")

    return result.getvalue()


def _build_daysheet_html(stop) -> str:
    """Build xhtml2pdf-compatible HTML for day sheet."""

    # Get basic info
    tour = stop.tour
    band_name = tour.band.name if tour.band else 'TBA'
    tour_name = tour.name
    date_str = stop.date.strftime('%d/%m/%Y') if stop.date else 'TBA'
    date_full = stop.date.strftime('%A %d %B %Y') if stop.date else 'TBA'

    # Venue info
    venue_name = stop.venue.name if stop.venue else 'TBA'
    venue_city = stop.venue.city if stop.venue else ''
    venue_country = stop.venue.country if stop.venue else ''
    venue_address = stop.venue.address if stop.venue else ''
    venue_postal = stop.venue.postal_code if stop.venue else ''
    venue_phone = stop.venue.phone if stop.venue else ''
    venue_capacity = stop.venue.capacity if stop.venue else ''

    # Event type
    event_type = stop.event_type.value if stop.event_type else 'show'
    event_labels = {
        'show': 'Concert',
        'day_off': 'Jour off',
        'travel': 'Voyage',
        'studio': 'Studio',
        'promo': 'Promo',
        'rehearsal': 'Repetition',
        'press': 'Presse',
        'meet_greet': 'Meet & Greet',
        'photo_video': 'Photo/Video',
        'other': 'Autre'
    }
    event_label = event_labels.get(event_type, 'Concert')

    # Status
    status = stop.status.value if stop.status else '-'
    status_labels = {
        'hold': 'En attente',
        'pending': 'En negociation',
        'confirmed': 'Confirme',
        'advanced': 'Avance',
        'completed': 'Termine',
        'cancelled': 'Annule'
    }
    status_label = status_labels.get(status, status)

    # Build schedule HTML
    schedule_html = ""
    schedule_items = [
        ('load_in_time', 'Load-In', 'bi-truck'),
        ('crew_call_time', 'Appel Equipe', 'bi-tools'),
        ('artist_call_time', 'Appel Artistes', 'bi-person-badge'),
        ('catering_time', 'Repas / Catering', 'bi-cup-hot'),
        ('soundcheck_time', 'Soundcheck', 'bi-soundwave'),
        ('press_time', 'Presse / Interviews', 'bi-newspaper'),
        ('meet_greet_time', 'Meet & Greet', 'bi-people'),
        ('doors_time', 'Ouverture Portes', 'bi-door-open'),
        ('set_time', 'SET TIME', 'bi-music-note-beamed'),
        ('curfew_time', 'Couvre-feu', 'bi-moon'),
    ]

    for attr, label, icon in schedule_items:
        time_val = getattr(stop, attr, None)
        if time_val:
            is_set_time = attr == 'set_time'
            row_style = 'background-color: #d4edda; font-weight: bold;' if is_set_time else ''
            time_style = 'color: #198754; font-size: 14pt;' if is_set_time else 'color: #0d6efd;'
            schedule_html += f'''
                <tr style="{row_style}">
                    <td style="{time_style} font-weight: bold; width: 80px;">{time_val.strftime('%H:%M')}</td>
                    <td>{label}</td>
                </tr>'''

    if not schedule_html:
        schedule_html = '<tr><td colspan="2" style="color: #6c757d; text-align: center; padding: 20px;">Aucun horaire defini</td></tr>'

    # Build logistics HTML (transport)
    transport_html = ""
    hotel_html = ""

    if hasattr(stop, 'logistics') and stop.logistics:
        for item in stop.logistics:
            if item.logistics_type.value in ['flight', 'ground_transport', 'train', 'bus']:
                provider = item.provider or 'Transport'
                conf = f" (Ref: {item.confirmation_number})" if item.confirmation_number else ''
                time_info = ''
                if item.start_datetime:
                    time_info = item.start_datetime.strftime('%H:%M')
                    if item.end_datetime:
                        time_info += f" - {item.end_datetime.strftime('%H:%M')}"
                transport_html += f'''
                    <tr>
                        <td style="font-weight: bold;">{provider}{conf}</td>
                        <td style="text-align: right;">{time_info}</td>
                    </tr>'''
                if item.details:
                    transport_html += f'<tr><td colspan="2" style="color: #6c757d; font-size: 9pt; padding-left: 10px;">{item.details}</td></tr>'

            elif item.logistics_type.value == 'hotel':
                provider = item.provider or 'Hotel'
                conf = f"Reservation: {item.confirmation_number}" if item.confirmation_number else ''
                hotel_html += f'''
                    <tr>
                        <td style="font-weight: bold;">{provider}</td>
                    </tr>'''
                if conf:
                    hotel_html += f'<tr><td style="color: #6c757d; font-size: 9pt;">{conf}</td></tr>'
                if item.details:
                    hotel_html += f'<tr><td style="color: #6c757d; font-size: 9pt;">{item.details}</td></tr>'

    # Build contacts HTML
    contacts_html = ""
    if stop.venue and hasattr(stop.venue, 'contacts') and stop.venue.contacts:
        for contact in stop.venue.contacts:
            name = contact.name
            role = f" ({contact.role})" if contact.role else ''
            phone = contact.phone or ''
            contacts_html += f'''
                <tr>
                    <td style="font-weight: bold;">{name}{role}</td>
                    <td style="text-align: right;">{phone}</td>
                </tr>'''

    if hasattr(stop, 'local_contacts') and stop.local_contacts:
        for contact in stop.local_contacts:
            name = contact.name
            role = f" ({contact.role})" if contact.role else ''
            phone = contact.phone or ''
            contacts_html += f'''
                <tr>
                    <td style="font-weight: bold;">{name}{role}</td>
                    <td style="text-align: right;">{phone}</td>
                </tr>'''

    if not contacts_html:
        contacts_html = '<tr><td colspan="2" style="color: #6c757d; text-align: center;">Aucun contact</td></tr>'

    # Notes
    notes_html = ""
    if stop.notes:
        notes_html = f'''
        <div class="section">
            <div class="section-header">NOTES</div>
            <div class="section-content">
                <p>{stop.notes}</p>
            </div>
        </div>'''

    generation_date = datetime.now().strftime('%d/%m/%Y %H:%M')

    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            size: A4;
            margin: 1.5cm;
        }}
        body {{
            font-family: Helvetica, Arial, sans-serif;
            font-size: 10pt;
            color: #333;
            margin: 0;
            padding: 0;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            color: #C9A962;
            padding: 20px;
            margin: -1.5cm -1.5cm 20px -1.5cm;
            text-align: center;
        }}
        .header h1 {{
            margin: 0 0 5px 0;
            font-size: 24pt;
            color: #C9A962;
        }}
        .header h2 {{
            margin: 0;
            font-size: 14pt;
            color: #fff;
            font-weight: normal;
        }}
        .header .info {{
            margin-top: 10px;
            font-size: 11pt;
            color: #aaa;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            font-size: 9pt;
            font-weight: 600;
            background: rgba(255,255,255,0.2);
            border-radius: 4px;
            margin: 5px;
        }}
        .section {{
            border: 1px solid #dee2e6;
            margin-bottom: 15px;
        }}
        .section-header {{
            background: #C9A962;
            color: #1a1a1a;
            padding: 8px 12px;
            font-weight: bold;
            font-size: 11pt;
            text-transform: uppercase;
        }}
        .section-content {{
            padding: 10px 12px;
        }}
        table.data {{
            width: 100%;
            border-collapse: collapse;
        }}
        table.data td {{
            padding: 6px 4px;
            border-bottom: 1px solid #f0f0f0;
        }}
        table.two-col {{
            width: 100%;
            border-collapse: collapse;
        }}
        table.two-col > tbody > tr > td {{
            width: 50%;
            vertical-align: top;
            padding: 0 8px;
        }}
        .venue-info p {{
            margin: 3px 0;
        }}
        .footer {{
            margin-top: 20px;
            text-align: center;
            font-size: 8pt;
            color: #999;
            border-top: 1px solid #ddd;
            padding-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <span class="badge">{event_label}</span>
        <h1>{band_name}</h1>
        <h2>{tour_name}</h2>
        <div class="info">
            {date_full}<br/>
            {venue_city}, {venue_country}
        </div>
    </div>

    <table class="two-col">
        <tr>
            <td>
                <!-- Venue -->
                <div class="section">
                    <div class="section-header">SALLE / VENUE</div>
                    <div class="section-content venue-info">
                        <p><strong>{venue_name}</strong></p>
                        <p>{venue_address}</p>
                        <p>{venue_postal} {venue_city}</p>
                        <p>{venue_country}</p>
                        {'<p>Tel: ' + venue_phone + '</p>' if venue_phone else ''}
                        {'<p>Capacite: ' + str(venue_capacity) + ' places</p>' if venue_capacity else ''}
                        <p><strong>Statut:</strong> {status_label}</p>
                    </div>
                </div>

                <!-- Contacts -->
                <div class="section">
                    <div class="section-header">CONTACTS</div>
                    <div class="section-content">
                        <table class="data">
                            {contacts_html}
                        </table>
                    </div>
                </div>
            </td>
            <td>
                <!-- Schedule -->
                <div class="section">
                    <div class="section-header">HORAIRES / SCHEDULE</div>
                    <div class="section-content">
                        <table class="data">
                            {schedule_html}
                        </table>
                    </div>
                </div>

                <!-- Transport -->
                {'<div class="section"><div class="section-header">TRANSPORT</div><div class="section-content"><table class="data">' + transport_html + '</table></div></div>' if transport_html else ''}

                <!-- Hotel -->
                {'<div class="section"><div class="section-header">HEBERGEMENT</div><div class="section-content"><table class="data">' + hotel_html + '</table></div></div>' if hotel_html else ''}
            </td>
        </tr>
    </table>

    {notes_html}

    <div class="footer">
        <p>Day Sheet genere le {generation_date} - Studio Palenque Tour Manager</p>
        <p>Reference: DAYSHEET-{stop.id}-{date_str.replace('/', '')}</p>
    </div>
</body>
</html>'''

    return html
