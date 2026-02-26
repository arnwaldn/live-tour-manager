"""
PDF Generator utility for Tour Manager.
Uses reportlab for cloud-compatible PDF generation.
Production-ready: works on all cloud platforms (Heroku, Railway, Render, Vercel, etc.)
No system dependencies required (pure Python).
"""
from io import BytesIO
from datetime import datetime
from typing import Dict, Any

from app import DAYS_FR, MONTHS_FR


def _format_date_fr(date, fmt='full'):
    """Format a date in French without relying on locale."""
    if not date:
        return ''
    day_fr = DAYS_FR.get(date.strftime('%A'), date.strftime('%A'))
    month_fr = MONTHS_FR.get(date.strftime('%B'), date.strftime('%B'))
    if fmt == 'full':
        return f"{day_fr} {date.day} {month_fr} {date.year}"
    return f"{date.day} {month_fr} {date.year}"


try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Alias for backwards compatibility with existing code
WEASYPRINT_AVAILABLE = PDF_AVAILABLE

# Color palette
GOLD = HexColor('#FFB72D')
DARK_BG = HexColor('#1A1A22')
BLUE = HexColor('#0d6efd')
GREEN = HexColor('#198754')
RED = HexColor('#dc3545')
YELLOW = HexColor('#ffc107')
GRAY = HexColor('#6c757d')
LIGHT_GRAY = HexColor('#f8f9fa')
LIGHT_GREEN = HexColor('#d4edda')
LIGHT_BLUE = HexColor('#e8f4f8')
WHITE = white
BLACK = black


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


def _get_fill_rate_class(fill_rate: float) -> str:
    """Get color for fill rate."""
    if fill_rate >= 90:
        return 'Excellent'
    elif fill_rate >= 75:
        return 'Bon'
    elif fill_rate >= 50:
        return 'Moyen'
    else:
        return 'Faible'


def _get_fill_rate_color(fill_rate: float) -> HexColor:
    """Get color for fill rate."""
    if not PDF_AVAILABLE:
        return None
    if fill_rate >= 90:
        return GREEN
    elif fill_rate >= 75:
        return BLUE
    elif fill_rate >= 50:
        return YELLOW
    else:
        return RED


def _get_deal_type(settlement: Dict[str, Any]) -> str:
    """Get deal type description."""
    if settlement['door_deal_percentage'] > 0 and settlement['guarantee'] > 0:
        return 'Hybrid (Guarantee + Door Deal)'
    elif settlement['door_deal_percentage'] > 0:
        return 'Door Deal'
    else:
        return 'Guarantee'


def generate_settlement_pdf(settlement: Dict[str, Any]) -> bytes:
    """
    Generate a professional PDF settlement report using reportlab.

    Args:
        settlement: Settlement data dictionary from calculate_settlement()

    Returns:
        PDF file as bytes
    """
    if not PDF_AVAILABLE:
        raise ImportError("reportlab is required for PDF generation. Install with: pip install reportlab")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5*cm,
                            bottomMargin=1.5*cm, leftMargin=1.5*cm, rightMargin=1.5*cm)

    styles = getSampleStyleSheet()
    elements = []
    s = settlement
    currency = s.get('currency', 'EUR')

    # Custom styles
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, textColor=WHITE,
                                 spaceAfter=6)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=10, textColor=WHITE)
    section_header_style = ParagraphStyle('SectionHeader', parent=styles['Heading2'], fontSize=11,
                                          textColor=BLACK, spaceBefore=12, spaceAfter=6,
                                          backColor=LIGHT_GRAY)
    normal_style = ParagraphStyle('NormalCustom', parent=styles['Normal'], fontSize=9)
    label_style = ParagraphStyle('Label', parent=styles['Normal'], fontSize=9, textColor=GRAY)
    value_style = ParagraphStyle('Value', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT)
    bold_value = ParagraphStyle('BoldValue', parent=styles['Normal'], fontSize=10, alignment=TA_RIGHT,
                                fontName='Helvetica-Bold')
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7,
                                  textColor=GRAY, alignment=TA_CENTER)

    # Format date
    date_str = s['date'].strftime('%d/%m/%Y') if s['date'] else 'N/A'
    date_full = _format_date_fr(s['date']) if s['date'] else 'N/A'

    # Header table (simulated colored header)
    header_data = [
        [Paragraph(f"<b>{s['band_name']}</b>", title_style)],
        [Paragraph(
            f"<b>{s['venue_name']}</b> - {s.get('venue_city', '')}, {s.get('venue_country', '')}",
            subtitle_style)],
        [Paragraph(f"{date_full}", subtitle_style)],
    ]
    header_table = Table(header_data, colWidths=[doc.width])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BLUE),
        ('TEXTCOLOR', (0, 0), (-1, -1), WHITE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (0, 0), 12),
        ('BOTTOMPADDING', (-1, -1), (-1, -1), 12),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 12))

    # R2: NBOR values
    nbor = s.get('nbor', s['gross_revenue'])
    ticketing_fees = s.get('ticketing_fees', 0)
    ticketing_fee_pct = s.get('ticketing_fee_percentage', 5)

    # Box Office Section
    elements.append(Paragraph("BOX OFFICE (GBOR)", section_header_style))
    fill_badge = _get_fill_rate_class(s['fill_rate'])
    box_data = [
        [Paragraph("Capacite salle", label_style), Paragraph(f"{s['capacity']:,} places", value_style)],
        [Paragraph("Billets vendus", label_style), Paragraph(f"{s['sold_tickets']:,}", value_style)],
        [Paragraph("Taux de remplissage", label_style), Paragraph(f"{s['fill_rate']}% ({fill_badge})", value_style)],
        [Paragraph("Prix du billet", label_style),
         Paragraph(format_currency(s['ticket_price'], currency), value_style)],
        [Paragraph("<b>RECETTES BRUTES (GBOR)</b>", normal_style),
         Paragraph(f"<b>{format_currency(s['gross_revenue'], currency)}</b>", bold_value)],
    ]
    box_table = Table(box_data, colWidths=[doc.width * 0.6, doc.width * 0.4])
    box_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, LIGHT_GRAY),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_BLUE),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(box_table)
    elements.append(Spacer(1, 8))

    # NBOR Section
    elements.append(Paragraph("RECETTES NETTES (NBOR)", section_header_style))
    nbor_data = [
        [Paragraph("Recettes brutes (GBOR)", label_style),
         Paragraph(format_currency(s['gross_revenue'], currency), value_style)],
        [Paragraph(f"Frais de billetterie ({ticketing_fee_pct}%)", label_style),
         Paragraph(f"-{format_currency(ticketing_fees, currency)}", value_style)],
        [Paragraph("<b>RECETTES NETTES (NBOR)</b>", normal_style),
         Paragraph(f"<b>{format_currency(nbor, currency)}</b>", bold_value)],
    ]
    nbor_table = Table(nbor_data, colWidths=[doc.width * 0.6, doc.width * 0.4])
    nbor_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, LIGHT_GRAY),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_BLUE),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(nbor_table)
    elements.append(Spacer(1, 8))

    # Deal Structure
    elements.append(Paragraph("STRUCTURE DU DEAL", section_header_style))
    deal_type = _get_deal_type(s)
    deal_data = [
        [Paragraph("Type de deal", label_style), Paragraph(deal_type, value_style)],
        [Paragraph("Cachet garanti", label_style), Paragraph(format_currency(s['guarantee'], currency), value_style)],
    ]
    if s['door_deal_percentage'] > 0:
        deal_data.append([Paragraph("Pourcentage Door Deal", label_style),
                          Paragraph(f"{s['door_deal_percentage']}%", value_style)])
        deal_data.append([Paragraph("Seuil de rentabilite", label_style),
                          Paragraph(f"{s['break_even_tickets']} billets", value_style)])
    deal_table = Table(deal_data, colWidths=[doc.width * 0.6, doc.width * 0.4])
    deal_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(deal_table)
    elements.append(Spacer(1, 8))

    # Promoter Expenses (conditional)
    promoter_expenses = s.get('promoter_expenses', {})
    promoter_total = promoter_expenses.get('total', 0) if promoter_expenses else 0
    if promoter_total > 0:
        elements.append(Paragraph("DEPENSES PROMOTEUR", section_header_style))
        exp_data = []
        expense_map = [
            ('venue_fee', 'Location salle'), ('production_cost', 'Couts de production'),
            ('marketing_cost', 'Marketing/Promo'), ('insurance', 'Assurance'),
            ('security', 'Securite'), ('catering', 'Catering'),
        ]
        for key, label in expense_map:
            val = promoter_expenses.get(key, 0)
            if val > 0:
                exp_data.append([Paragraph(label, label_style), Paragraph(format_currency(val, currency), value_style)])
        if promoter_expenses.get('other', 0) > 0:
            other_desc = (
                f" ({promoter_expenses.get('other_description', '')})"
                if promoter_expenses.get('other_description') else ''
            )
            exp_data.append([Paragraph(f"Autres{other_desc}", label_style),
                             Paragraph(format_currency(promoter_expenses['other'], currency), value_style)])
        exp_data.append([Paragraph("<b>TOTAL DEPENSES</b>", normal_style),
                         Paragraph(f"<b>{format_currency(promoter_total, currency)}</b>", bold_value)])
        exp_table = Table(exp_data, colWidths=[doc.width * 0.6, doc.width * 0.4])
        exp_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, LIGHT_GRAY),
            ('BACKGROUND', (0, -1), (-1, -1), LIGHT_BLUE),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(exp_table)
        elements.append(Spacer(1, 8))

    # Payment Calculation
    elements.append(Paragraph("CALCUL DU PAIEMENT ARTISTE", section_header_style))

    # Payment type text
    if s['payment_type'] == 'split_point':
        payment_type_text = 'Split Point (standard industrie)'
    elif s['payment_type'] == 'door_deal':
        payment_type_text = 'Door Deal (plus avantageux)'
    else:
        payment_type_text = 'Guarantee (protege)'

    pay_data = [
        [Paragraph("Recettes nettes (NBOR)", label_style), Paragraph(format_currency(nbor, currency), value_style)],
        [Paragraph("vs. Cachet garanti", label_style),
         Paragraph(format_currency(s['guarantee'], currency), value_style)],
        [Paragraph("Methode de paiement retenue", label_style), Paragraph(payment_type_text, value_style)],
    ]

    if s.get('profit_above_guarantee', 0) > 0:
        pay_data.append([Paragraph("Bonus au-dessus du guarantee", label_style),
                         Paragraph(f"+{format_currency(s['profit_above_guarantee'], currency)}", value_style)])

    pay_data.append([Paragraph("<b>PAIEMENT ARTISTE</b>", normal_style),
                     Paragraph(f"<b>{format_currency(s['artist_payment'], currency)}</b>", bold_value)])

    pay_table = Table(pay_data, colWidths=[doc.width * 0.6, doc.width * 0.4])
    pay_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, LIGHT_GRAY),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_GREEN),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(pay_table)
    elements.append(Spacer(1, 8))

    # Venue Share
    elements.append(Paragraph("PART PROMOTEUR / SALLE", section_header_style))
    venue_data = [
        [Paragraph("Recettes nettes (NBOR)", label_style), Paragraph(format_currency(nbor, currency), value_style)],
        [Paragraph("- Paiement artiste", label_style),
         Paragraph(f"-{format_currency(s['artist_payment'], currency)}", value_style)],
        [Paragraph("<b>PART PROMOTEUR</b>", normal_style),
         Paragraph(f"<b>{format_currency(s['venue_share'], currency)}</b>", bold_value)],
    ]
    venue_table = Table(venue_data, colWidths=[doc.width * 0.6, doc.width * 0.4])
    venue_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, LIGHT_GRAY),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_BLUE),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(venue_table)
    elements.append(Spacer(1, 16))

    # Signatures
    elements.append(Paragraph("SIGNATURES", section_header_style))
    sig_data = [
        [Paragraph("<b>Representant artiste / Tour Manager</b>", normal_style),
         Paragraph("<b>Promoteur / Responsable salle</b>", normal_style)],
        [Paragraph("", normal_style), Paragraph("", normal_style)],
        [Paragraph("Nom: _________________________", normal_style),
         Paragraph("Nom: _________________________", normal_style)],
        [Paragraph("Date: _________________________", normal_style),
         Paragraph("Date: _________________________", normal_style)],
    ]
    sig_table = Table(sig_data, colWidths=[doc.width * 0.5, doc.width * 0.5])
    sig_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 1), (0, 1), 1, GRAY),
        ('LINEBELOW', (1, 1), (1, 1), 1, GRAY),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 20))

    # Footer
    elements.append(Paragraph(
        f"Ce document est une feuille de reglement generee par Tour Manager. "
        f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')} - "
        f"Reference: SETTLEMENT-{s['stop_id']}-{date_str.replace('/', '')}",
        footer_style
    ))

    doc.build(elements)
    return buffer.getvalue()


def generate_invoice_pdf(invoice) -> bytes:
    """
    Generate a professional invoice PDF compliant with French e-invoicing requirements.

    Args:
        invoice: Invoice model instance (with lines loaded)

    Returns:
        PDF file as bytes
    """
    if not PDF_AVAILABLE:
        raise ImportError("reportlab is required for PDF generation. Install with: pip install reportlab")

    from reportlab.lib.enums import TA_LEFT

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5*cm,
                            bottomMargin=1.5*cm, leftMargin=1.5*cm, rightMargin=1.5*cm)

    styles = getSampleStyleSheet()
    elements = []
    currency = invoice.currency or 'EUR'

    # Custom styles
    title_style = ParagraphStyle('InvTitle', parent=styles['Heading1'], fontSize=18,
                                 textColor=WHITE, alignment=TA_CENTER, spaceAfter=4)
    subtitle_style = ParagraphStyle('InvSub', parent=styles['Normal'], fontSize=10,
                                    textColor=WHITE, alignment=TA_CENTER)
    section_header_style = ParagraphStyle('InvSection', parent=styles['Heading2'], fontSize=11,
                                          textColor=BLACK, spaceBefore=12, spaceAfter=6,
                                          backColor=LIGHT_GRAY)
    label_style = ParagraphStyle('InvLabel', parent=styles['Normal'], fontSize=9, textColor=GRAY)
    value_style = ParagraphStyle('InvValue', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT)
    bold_value = ParagraphStyle('InvBoldValue', parent=styles['Normal'], fontSize=10,
                                alignment=TA_RIGHT, fontName='Helvetica-Bold')
    cell_style = ParagraphStyle('InvCell', parent=styles['Normal'], fontSize=9)
    cell_bold = ParagraphStyle('InvCellBold', parent=styles['Normal'], fontSize=9,
                               fontName='Helvetica-Bold')
    small_style = ParagraphStyle('InvSmall', parent=styles['Normal'], fontSize=8, textColor=GRAY)
    footer_style = ParagraphStyle('InvFooter', parent=styles['Normal'], fontSize=7,
                                  textColor=GRAY, alignment=TA_CENTER)
    addr_style = ParagraphStyle('InvAddr', parent=styles['Normal'], fontSize=9,
                                alignment=TA_LEFT, leading=13)

    # Type labels
    type_labels = {
        'invoice': 'FACTURE', 'credit': 'AVOIR', 'proforma': 'FACTURE PROFORMA',
        'deposit': "FACTURE D'ACOMPTE", 'final': 'FACTURE DE SOLDE',
    }
    invoice_type_label = type_labels.get(invoice.type.value, 'FACTURE')

    # Header
    issue_date_str = invoice.issue_date.strftime('%d/%m/%Y') if invoice.issue_date else ''
    due_date_str = invoice.due_date.strftime('%d/%m/%Y') if invoice.due_date else ''

    header_data = [
        [Paragraph(f"<b>{invoice_type_label}</b>", title_style)],
        [Paragraph(f"N° {invoice.number}", subtitle_style)],
        [Paragraph(f"Date: {issue_date_str} | Echeance: {due_date_str}", subtitle_style)],
    ]
    header_table = Table(header_data, colWidths=[doc.width])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BLUE),
        ('TOPPADDING', (0, 0), (0, 0), 14),
        ('BOTTOMPADDING', (-1, -1), (-1, -1), 14),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 14))

    # Issuer and Recipient side by side
    issuer_lines = [f"<b>{invoice.issuer_name or ''}</b>"]
    if invoice.issuer_legal_form:
        issuer_lines[0] += f" ({invoice.issuer_legal_form})"
    if invoice.issuer_address_line1:
        issuer_lines.append(invoice.issuer_address_line1)
    if invoice.issuer_address_line2:
        issuer_lines.append(invoice.issuer_address_line2)
    postal_city = f"{invoice.issuer_postal_code or ''} {invoice.issuer_city or ''}".strip()
    if postal_city:
        issuer_lines.append(postal_city)
    if invoice.issuer_siret:
        issuer_lines.append(f"SIRET: {invoice.issuer_siret}")
    if invoice.issuer_vat:
        issuer_lines.append(f"TVA: {invoice.issuer_vat}")
    if invoice.issuer_rcs:
        issuer_lines.append(f"RCS: {invoice.issuer_rcs}")
    if invoice.issuer_phone:
        issuer_lines.append(f"Tel: {invoice.issuer_phone}")
    if invoice.issuer_email:
        issuer_lines.append(invoice.issuer_email)

    recipient_lines = [f"<b>{invoice.recipient_name or ''}</b>"]
    if invoice.recipient_legal_form:
        recipient_lines[0] += f" ({invoice.recipient_legal_form})"
    if invoice.recipient_address_line1:
        recipient_lines.append(invoice.recipient_address_line1)
    if invoice.recipient_address_line2:
        recipient_lines.append(invoice.recipient_address_line2)
    postal_city_r = f"{invoice.recipient_postal_code or ''} {invoice.recipient_city or ''}".strip()
    if postal_city_r:
        recipient_lines.append(postal_city_r)
    if invoice.recipient_siret:
        recipient_lines.append(f"SIRET: {invoice.recipient_siret}")
    if invoice.recipient_vat:
        recipient_lines.append(f"TVA: {invoice.recipient_vat}")

    addr_data = [[
        Paragraph("<br/>".join(issuer_lines), addr_style),
        Paragraph("<br/>".join(recipient_lines), addr_style),
    ]]
    addr_table = Table(addr_data, colWidths=[doc.width * 0.48, doc.width * 0.48],
                       spaceBefore=0, spaceAfter=0)
    addr_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 0), (0, 0), LIGHT_BLUE),
        ('BACKGROUND', (1, 0), (1, 0), LIGHT_GRAY),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(addr_table)
    elements.append(Spacer(1, 12))

    # Invoice lines table
    elements.append(Paragraph("LIGNES DE FACTURE", section_header_style))

    right_cell = ParagraphStyle('RCell', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT)
    right_bold = ParagraphStyle('RBold', parent=styles['Normal'], fontSize=9,
                                alignment=TA_RIGHT, fontName='Helvetica-Bold')

    lines_header = [
        Paragraph("<b>#</b>", cell_bold),
        Paragraph("<b>Description</b>", cell_bold),
        Paragraph("<b>Qte</b>", cell_bold),
        Paragraph("<b>P.U. HT</b>", cell_bold),
        Paragraph("<b>TVA</b>", cell_bold),
        Paragraph("<b>Total HT</b>", cell_bold),
    ]
    lines_data = [lines_header]

    for line in invoice.lines:
        lines_data.append([
            Paragraph(str(line.line_number), cell_style),
            Paragraph(line.description or '', cell_style),
            Paragraph(f"{line.quantity}", right_cell),
            Paragraph(format_currency(float(line.unit_price_ht or 0), currency), right_cell),
            Paragraph(f"{line.vat_rate or 0}%", right_cell),
            Paragraph(format_currency(float(line.total_ht or 0), currency), right_bold),
        ])

    col_widths = [doc.width * 0.06, doc.width * 0.38, doc.width * 0.1,
                  doc.width * 0.16, doc.width * 0.1, doc.width * 0.2]
    lines_table = Table(lines_data, colWidths=col_widths, repeatRows=1)
    lines_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(lines_table)
    elements.append(Spacer(1, 10))

    # Totals section
    elements.append(Paragraph("TOTAUX", section_header_style))
    totals_data = [
        [Paragraph("Sous-total HT", label_style),
         Paragraph(format_currency(float(invoice.subtotal_ht or 0), currency), value_style)],
    ]
    if invoice.discount_amount and float(invoice.discount_amount) > 0:
        totals_data.append([
            Paragraph("Remise", label_style),
            Paragraph(f"-{format_currency(float(invoice.discount_amount), currency)}", value_style),
        ])
        totals_data.append([
            Paragraph("Sous-total apres remise", label_style),
            Paragraph(format_currency(float(invoice.subtotal_after_discount or 0), currency), value_style),
        ])
    totals_data.append([
        Paragraph("TVA", label_style),
        Paragraph(format_currency(float(invoice.vat_amount or 0), currency), value_style),
    ])
    totals_data.append([
        Paragraph("<b>TOTAL TTC</b>", cell_bold),
        Paragraph(f"<b>{format_currency(float(invoice.total_ttc or 0), currency)}</b>", bold_value),
    ])
    if invoice.amount_paid and float(invoice.amount_paid) > 0:
        totals_data.append([
            Paragraph("Deja paye", label_style),
            Paragraph(f"-{format_currency(float(invoice.amount_paid), currency)}", value_style),
        ])
        totals_data.append([
            Paragraph("<b>RESTE A PAYER</b>", cell_bold),
            Paragraph(f"<b>{format_currency(float(invoice.amount_due or 0), currency)}</b>", bold_value),
        ])

    totals_table = Table(totals_data, colWidths=[doc.width * 0.6, doc.width * 0.4])
    totals_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, LIGHT_GRAY),
        ('BACKGROUND', (0, -1), (-1, -1), LIGHT_GREEN),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 10))

    # Payment info
    elements.append(Paragraph("CONDITIONS DE PAIEMENT", section_header_style))
    pay_info = []
    if invoice.payment_terms:
        pay_info.append(f"<b>Conditions:</b> {invoice.payment_terms}")
    if invoice.payment_method_accepted:
        pay_info.append(f"<b>Mode de paiement:</b> {invoice.payment_method_accepted}")
    if invoice.issuer_iban:
        pay_info.append(f"<b>IBAN:</b> {invoice.issuer_iban}")
    if invoice.issuer_bic:
        pay_info.append(f"<b>BIC:</b> {invoice.issuer_bic}")
    elements.append(Paragraph("<br/>".join(pay_info) if pay_info else "Non specifie", cell_style))
    elements.append(Spacer(1, 8))

    # Legal mentions (mandatory in France)
    elements.append(Paragraph("MENTIONS LEGALES", section_header_style))
    legal_lines = []
    if invoice.vat_mention:
        legal_lines.append(invoice.vat_mention)
    if invoice.no_discount_mention:
        legal_lines.append("Pas d'escompte pour paiement anticipe.")
    if invoice.late_penalty_rate:
        legal_lines.append(
            f"Penalites de retard: {invoice.late_penalty_rate}% par an. "
            f"Indemnite forfaitaire de recouvrement: {format_currency(float(invoice.recovery_fee or 40), currency)}."
        )
    if invoice.special_mentions:
        legal_lines.append(invoice.special_mentions)
    elements.append(Paragraph("<br/>".join(legal_lines) if legal_lines else "Aucune mention particuliere.", small_style))

    # Public notes
    if invoice.public_notes:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("NOTES", section_header_style))
        elements.append(Paragraph(invoice.public_notes, cell_style))

    elements.append(Spacer(1, 20))

    # Footer
    generation_date = datetime.now().strftime('%d/%m/%Y %H:%M')
    elements.append(Paragraph(
        f"Document genere le {generation_date} par GigRoute - "
        f"Reference: {invoice.number}",
        footer_style
    ))

    doc.build(elements)
    return buffer.getvalue()


def generate_tour_pdf(tour) -> bytes:
    """
    Generate a PDF with tour schedule (all stops).

    Args:
        tour: Tour model instance

    Returns:
        PDF file as bytes
    """
    if not PDF_AVAILABLE:
        raise ImportError("reportlab is required for PDF generation. Install with: pip install reportlab")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=1.5*cm,
                            bottomMargin=1.5*cm, leftMargin=1.5*cm, rightMargin=1.5*cm)

    styles = getSampleStyleSheet()
    elements = []

    # Custom styles
    title_style = ParagraphStyle('TourTitle', parent=styles['Heading1'], fontSize=20,
                                 textColor=GOLD, alignment=TA_CENTER, spaceAfter=4)
    subtitle_style = ParagraphStyle('TourSubtitle', parent=styles['Normal'], fontSize=12,
                                    textColor=WHITE, alignment=TA_CENTER)
    date_style = ParagraphStyle('TourDates', parent=styles['Normal'], fontSize=10,
                                textColor=HexColor('#aaaaaa'), alignment=TA_CENTER)
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=9)
    cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
    cell_small = ParagraphStyle('CellSmall', parent=styles['Normal'], fontSize=8, textColor=GRAY)
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7,
                                  textColor=GRAY, alignment=TA_CENTER)

    # Tour dates
    start_date = tour.start_date.strftime('%d/%m/%Y') if tour.start_date else 'TBA'
    end_date = tour.end_date.strftime('%d/%m/%Y') if tour.end_date else 'TBA'
    band_name = tour.band.name if tour.band else 'TBA'

    # Header
    header_data = [
        [Paragraph(f"<b>{band_name}</b>", title_style)],
        [Paragraph(tour.name, subtitle_style)],
        [Paragraph(f"{start_date} - {end_date}", date_style)],
    ]
    header_table = Table(header_data, colWidths=[doc.width])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK_BG),
        ('TOPPADDING', (0, 0), (0, 0), 16),
        ('BOTTOMPADDING', (-1, -1), (-1, -1), 16),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 12))

    # Sort stops by date
    stops = sorted(tour.stops, key=lambda s: s.date if s.date else datetime.max.date())

    # Table header
    table_data = [
        [Paragraph("<b>Date</b>", cell_bold),
         Paragraph("<b>Venue</b>", cell_bold),
         Paragraph("<b>Location</b>", cell_bold),
         Paragraph("<b>Doors</b>", cell_bold),
         Paragraph("<b>Show</b>", cell_bold),
         Paragraph("<b>Status</b>", cell_bold)]
    ]

    status_labels = {
        'hold': 'En attente', 'pending': 'En négo', 'confirmed': 'Confirmé',
        'advanced': 'Avancé', 'completed': 'Terminé', 'cancelled': 'Annulé'
    }

    for stop in stops:
        date_str = stop.date.strftime('%a %d/%m/%Y') if stop.date else 'TBA'
        venue_name = stop.venue.name if stop.venue else 'TBA'
        city = stop.venue.city if stop.venue else ''
        country = stop.venue.country if stop.venue else ''
        location = f"{city}, {country}" if city else ''
        doors = stop.doors_time.strftime('%H:%M') if stop.doors_time else '-'
        show = stop.set_time.strftime('%H:%M') if stop.set_time else '-'
        status = stop.status.value if stop.status else '-'
        status_label = status_labels.get(status, status)

        table_data.append([
            Paragraph(f"<b>{date_str}</b>", cell_bold),
            Paragraph(f"<b>{venue_name}</b>", cell_bold),
            Paragraph(location, cell_small),
            Paragraph(doors, cell_style),
            Paragraph(show, cell_style),
            Paragraph(status_label, cell_style),
        ])

    # Create table
    col_widths = [doc.width * 0.18, doc.width * 0.25, doc.width * 0.22,
                  doc.width * 0.1, doc.width * 0.1, doc.width * 0.15]
    schedule_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    schedule_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), GOLD),
        ('TEXTCOLOR', (0, 0), (-1, 0), DARK_BG),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        # Alternating rows
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        # Grid
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, HexColor('#dddddd')),
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(schedule_table)
    elements.append(Spacer(1, 12))

    # Total stops
    total_style = ParagraphStyle('Total', parent=styles['Normal'], fontSize=10,
                                 textColor=GRAY, alignment=TA_RIGHT)
    elements.append(Paragraph(f"Total: {len(stops)} date(s)", total_style))
    elements.append(Spacer(1, 16))

    # Footer
    generation_date = datetime.now().strftime('%d/%m/%Y %H:%M')
    elements.append(Paragraph(f"GigRoute - Genere le {generation_date}", footer_style))

    doc.build(elements)
    return buffer.getvalue()


def generate_daysheet_pdf(stop) -> bytes:
    """
    Generate a PDF day sheet for a single tour stop.

    Args:
        stop: TourStop model instance

    Returns:
        PDF file as bytes
    """
    if not PDF_AVAILABLE:
        raise ImportError("reportlab is required for PDF generation. Install with: pip install reportlab")

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5*cm,
                            bottomMargin=1.5*cm, leftMargin=1.5*cm, rightMargin=1.5*cm)

    styles = getSampleStyleSheet()
    elements = []

    # Custom styles
    title_style = ParagraphStyle('DayTitle', parent=styles['Heading1'], fontSize=20,
                                 textColor=GOLD, alignment=TA_CENTER, spaceAfter=4)
    subtitle_style = ParagraphStyle('DaySub', parent=styles['Normal'], fontSize=12,
                                    textColor=WHITE, alignment=TA_CENTER)
    info_style = ParagraphStyle('DayInfo', parent=styles['Normal'], fontSize=10,
                                textColor=HexColor('#aaaaaa'), alignment=TA_CENTER)
    section_header_style = ParagraphStyle(
        'SecHeader', parent=styles['Heading2'], fontSize=11,
        textColor=DARK_BG, backColor=GOLD, spaceBefore=10, spaceAfter=4)
    cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=9)
    cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
    time_style = ParagraphStyle('TimeStyle', parent=styles['Normal'], fontSize=10,
                                textColor=BLUE, fontName='Helvetica-Bold')
    highlight_time_style = ParagraphStyle(
        'HighlightTime', parent=styles['Normal'], fontSize=12,
        textColor=GREEN, fontName='Helvetica-Bold')
    cell_small = ParagraphStyle('CellSmall', parent=styles['Normal'], fontSize=8, textColor=GRAY)
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7,
                                  textColor=GRAY, alignment=TA_CENTER)

    # Get basic info
    tour = stop.tour
    band_name = tour.band.name if tour.band else 'TBA'
    date_str = stop.date.strftime('%d/%m/%Y') if stop.date else 'TBA'
    date_full = _format_date_fr(stop.date) if stop.date else 'TBA'

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
        'show': 'Concert', 'day_off': 'Jour off', 'travel': 'Voyage',
        'studio': 'Studio', 'promo': 'Promo', 'rehearsal': 'Repetition',
        'press': 'Presse', 'meet_greet': 'Meet & Greet',
        'photo_video': 'Photo/Video', 'other': 'Autre'
    }
    event_label = event_labels.get(event_type, 'Concert')

    # Status
    status = stop.status.value if stop.status else '-'
    status_labels = {
        'hold': 'En attente', 'pending': 'En négociation', 'confirmed': 'Confirmé',
        'advanced': 'Avancé', 'completed': 'Terminé', 'cancelled': 'Annulé'
    }
    status_label = status_labels.get(status, status)

    # Header
    header_data = [
        [Paragraph(f"<i>{event_label}</i>", info_style)],
        [Paragraph(f"<b>{band_name}</b>", title_style)],
        [Paragraph(tour.name, subtitle_style)],
        [Paragraph(f"{date_full} - {venue_city}, {venue_country}", info_style)],
    ]
    header_table = Table(header_data, colWidths=[doc.width])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK_BG),
        ('TOPPADDING', (0, 0), (0, 0), 12),
        ('BOTTOMPADDING', (-1, -1), (-1, -1), 12),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))

    # Venue Section
    elements.append(Paragraph("SALLE / VENUE", section_header_style))
    venue_info = f"<b>{venue_name}</b><br/>{venue_address}<br/>{venue_postal} {venue_city}<br/>{venue_country}"
    if venue_phone:
        venue_info += f"<br/>Tel: {venue_phone}"
    if venue_capacity:
        venue_info += f"<br/>Capacite: {venue_capacity} places"
    venue_info += f"<br/><b>Statut:</b> {status_label}"
    elements.append(Paragraph(venue_info, cell_style))
    elements.append(Spacer(1, 8))

    # Schedule Section
    elements.append(Paragraph("HORAIRES / SCHEDULE", section_header_style))
    schedule_items = [
        ('load_in_time', 'Load-In'), ('crew_call_time', 'Appel Equipe'),
        ('artist_call_time', 'Appel Artistes'), ('catering_time', 'Repas / Catering'),
        ('soundcheck_time', 'Soundcheck'), ('press_time', 'Presse / Interviews'),
        ('meet_greet_time', 'Meet & Greet'), ('doors_time', 'Ouverture Portes'),
        ('set_time', 'SET TIME'), ('curfew_time', 'Couvre-feu'),
    ]

    schedule_data = []
    for attr, label in schedule_items:
        time_val = getattr(stop, attr, None)
        if time_val:
            is_set = attr == 'set_time'
            ts = highlight_time_style if is_set else time_style
            schedule_data.append([
                Paragraph(time_val.strftime('%H:%M'), ts),
                Paragraph(f"<b>{label}</b>" if is_set else label, cell_bold if is_set else cell_style)
            ])

    if schedule_data:
        sched_table = Table(schedule_data, colWidths=[doc.width * 0.2, doc.width * 0.8])
        sched_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(sched_table)
    else:
        elements.append(Paragraph("Aucun horaire defini", cell_small))

    elements.append(Spacer(1, 8))

    # Contacts Section
    elements.append(Paragraph("CONTACTS", section_header_style))
    contacts_data = []
    if hasattr(stop, 'local_contacts') and stop.local_contacts:
        for contact in stop.local_contacts:
            role_text = f" ({contact.role})" if contact.role else ''
            contacts_data.append([
                Paragraph(f"<b>{contact.name}{role_text}</b>", cell_bold),
                Paragraph(contact.phone or '', cell_style)
            ])
    if stop.venue and hasattr(stop.venue, 'contacts') and stop.venue.contacts:
        for contact in stop.venue.contacts:
            role_text = f" ({contact.role})" if contact.role else ''
            contacts_data.append([
                Paragraph(f"<b>{contact.name}{role_text}</b>", cell_bold),
                Paragraph(contact.phone or '', cell_style)
            ])

    if contacts_data:
        contact_table = Table(contacts_data, colWidths=[doc.width * 0.6, doc.width * 0.4])
        contact_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(contact_table)
    else:
        elements.append(Paragraph("Aucun contact", cell_small))

    # Notes
    if stop.notes:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("NOTES", section_header_style))
        elements.append(Paragraph(stop.notes, cell_style))

    elements.append(Spacer(1, 20))

    # Footer
    generation_date = datetime.now().strftime('%d/%m/%Y %H:%M')
    elements.append(Paragraph(
        f"Day Sheet genere le {generation_date} - GigRoute - "
        f"Reference: DAYSHEET-{stop.id}-{date_str.replace('/', '')}",
        footer_style
    ))

    doc.build(elements)
    return buffer.getvalue()
