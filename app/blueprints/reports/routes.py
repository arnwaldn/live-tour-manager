"""
Reports routes for Studio Palenque Tour.
Includes general stats and financial reports.
"""
from flask import render_template, redirect, url_for, flash, Response, request
from flask_login import login_required, current_user

from app.blueprints.reports import reports_bp
from app.models.tour import Tour
from app.models.guestlist import GuestlistEntry, GuestlistStatus
from app.models.tour_stop import TourStop
from app.models.payments import TeamMemberPayment, PaymentStatus
from app.models.user import User
from app.utils.reports import (
    calculate_tour_financials,
    calculate_multi_tour_summary,
    calculate_dashboard_kpis,
    calculate_settlement,
    generate_csv_report,
    format_currency
)
from app.utils.pdf_generator import generate_settlement_pdf, WEASYPRINT_AVAILABLE

# Import services for accounting exports
try:
    from app.services.report_service import ReportService
    from app.services.payment_service import PaymentService
    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False


@reports_bp.route('/')
@login_required
def index():
    """Reports overview page with general stats."""
    if not current_user.is_manager_or_above():
        flash('Acces reserve aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    # Get tours for stats
    tours = Tour.query.filter(Tour.band_id.in_(user_band_ids)).order_by(
        Tour.start_date.desc()
    ).all()

    # Calculate stats
    stats = {
        'total_tours': len(tours),
        'total_stops': sum(len(t.stops) for t in tours),
        'total_guestlist': 0,
        'total_checked_in': 0
    }

    for tour in tours:
        for stop in tour.stops:
            stats['total_guestlist'] += len(stop.guestlist_entries)
            stats['total_checked_in'] += sum(
                1 for e in stop.guestlist_entries
                if e.status == GuestlistStatus.CHECKED_IN
            )

    return render_template('reports/index.html', tours=tours, stats=stats)


@reports_bp.route('/financial')
@login_required
def financial():
    """Financial reports overview - all tours."""
    if not current_user.is_manager_or_above():
        flash('Acces reserve aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    # Get all tours
    tours = Tour.query.filter(Tour.band_id.in_(user_band_ids)).order_by(
        Tour.start_date.desc()
    ).all()

    # Calculate multi-tour summary
    summary = calculate_multi_tour_summary(tours)

    return render_template('reports/financial.html', summary=summary)


@reports_bp.route('/financial/<int:tour_id>')
@login_required
def financial_tour(tour_id):
    """Detailed financial report for a specific tour."""
    tour = Tour.query.get_or_404(tour_id)

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Acces non autorise.', 'error')
        return redirect(url_for('main.dashboard'))

    if not current_user.is_manager_or_above():
        flash('Acces reserve aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    # Calculate tour financials
    tour_data = calculate_tour_financials(tour)

    return render_template(
        'reports/financial_tour.html',
        tour=tour,
        tour_data=tour_data
    )


@reports_bp.route('/financial/<int:tour_id>/export')
@login_required
def export_financial_csv(tour_id):
    """Export tour financial report as CSV."""
    tour = Tour.query.get_or_404(tour_id)

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Acces non autorise.', 'error')
        return redirect(url_for('main.dashboard'))

    if not current_user.is_manager_or_above():
        flash('Acces reserve aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    # Generate CSV
    tour_data = calculate_tour_financials(tour)
    csv_content = generate_csv_report(tour_data)

    # Create filename
    filename = f"rapport_financier_{tour.name}_{tour.start_date.strftime('%Y%m%d')}.csv"
    filename = filename.replace(' ', '_').replace('/', '-')

    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@reports_bp.route('/guestlist')
@login_required
def guestlist_analytics():
    """Guestlist analytics report."""
    if not current_user.is_manager_or_above():
        flash('Acces reserve aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    # Get all tours
    tours = Tour.query.filter(Tour.band_id.in_(user_band_ids)).order_by(
        Tour.start_date.desc()
    ).all()

    # Calculate guestlist stats by tour
    tour_stats = []
    for tour in tours:
        stats = {
            'tour': tour,
            'total_entries': 0,
            'pending': 0,
            'approved': 0,
            'denied': 0,
            'checked_in': 0,
            'total_plus_ones': 0,
            'by_type': {},
        }

        for stop in tour.stops:
            for entry in stop.guestlist_entries:
                stats['total_entries'] += 1
                stats['total_plus_ones'] += entry.plus_ones or 0

                if entry.status == GuestlistStatus.PENDING:
                    stats['pending'] += 1
                elif entry.status == GuestlistStatus.APPROVED:
                    stats['approved'] += 1
                elif entry.status == GuestlistStatus.DENIED:
                    stats['denied'] += 1
                elif entry.status == GuestlistStatus.CHECKED_IN:
                    stats['checked_in'] += 1

                # By entry type
                entry_type = entry.entry_type.value if entry.entry_type else 'unknown'
                stats['by_type'][entry_type] = stats['by_type'].get(entry_type, 0) + 1

        if stats['total_entries'] > 0:
            tour_stats.append(stats)

    return render_template('reports/guestlist_analytics.html', tour_stats=tour_stats)


@reports_bp.route('/dashboard')
@login_required
def financial_dashboard():
    """Advanced financial dashboard with KPIs and charts."""
    if not current_user.is_manager_or_above():
        flash('Acces reserve aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    # Get all tours
    tours = Tour.query.filter(Tour.band_id.in_(user_band_ids)).order_by(
        Tour.start_date.desc()
    ).all()

    # Calculate advanced KPIs
    kpis = calculate_dashboard_kpis(tours)

    # Get upcoming shows that need settlement (confirmed, with sold_tickets > 0)
    from datetime import date
    upcoming_settlements = []
    for tour in tours:
        for stop in tour.stops:
            if stop.date and stop.date >= date.today() and stop.sold_tickets and stop.sold_tickets > 0:
                settlement = calculate_settlement(stop)
                upcoming_settlements.append(settlement)

    # Sort by date
    upcoming_settlements.sort(key=lambda x: x['date'])
    upcoming_settlements = upcoming_settlements[:10]  # Top 10

    return render_template(
        'reports/dashboard.html',
        kpis=kpis,
        tours=tours,
        upcoming_settlements=upcoming_settlements,
        format_currency=format_currency
    )


@reports_bp.route('/settlements')
@login_required
def settlements_list():
    """Liste complète de tous les settlements (passés et futurs)."""
    if not current_user.is_manager_or_above():
        flash('Acces reserve aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    # Get all tours
    tours = Tour.query.filter(Tour.band_id.in_(user_band_ids)).order_by(
        Tour.start_date.desc()
    ).all()

    # Collecter TOUS les stops (sans filtre de date)
    all_settlements = []
    for tour in tours:
        for stop in tour.stops:
            if stop.venue:  # Seulement les stops avec salle
                settlement_data = calculate_settlement(stop)
                all_settlements.append(settlement_data)

    # Trier par date (plus récent d'abord)
    all_settlements.sort(key=lambda x: x['date'] if x['date'] else '', reverse=True)

    # Filter param
    filter_type = request.args.get('filter', 'all')
    from datetime import date
    today = date.today()

    if filter_type == 'past':
        all_settlements = [s for s in all_settlements if s['date'] and s['date'] < today]
    elif filter_type == 'future':
        all_settlements = [s for s in all_settlements if s['date'] and s['date'] >= today]

    return render_template(
        'reports/settlements_list.html',
        settlements=all_settlements,
        format_currency=format_currency,
        filter_type=filter_type,
        today=today
    )


@reports_bp.route('/settlement/<int:stop_id>')
@login_required
def settlement(stop_id):
    """Settlement page (feuille de règlement) for a tour stop."""
    stop = TourStop.query.get_or_404(stop_id)

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    # Check if user has access to this stop (via tour or direct band)
    if stop.tour:
        if stop.tour.band_id not in user_band_ids:
            flash('Acces non autorise.', 'error')
            return redirect(url_for('main.dashboard'))
    elif stop.band:
        if stop.band_id not in user_band_ids:
            flash('Acces non autorise.', 'error')
            return redirect(url_for('main.dashboard'))

    if not current_user.is_manager_or_above():
        flash('Acces reserve aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    # Calculate settlement
    settlement_data = calculate_settlement(stop)

    return render_template(
        'reports/settlement.html',
        stop=stop,
        settlement=settlement_data,
        format_currency=format_currency
    )


@reports_bp.route('/settlement/<int:stop_id>/pdf')
@login_required
def settlement_pdf(stop_id):
    """Export settlement as PDF."""
    stop = TourStop.query.get_or_404(stop_id)

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    # Check if user has access to this stop (via tour or direct band)
    if stop.tour:
        if stop.tour.band_id not in user_band_ids:
            flash('Acces non autorise.', 'error')
            return redirect(url_for('main.dashboard'))
    elif stop.band:
        if stop.band_id not in user_band_ids:
            flash('Acces non autorise.', 'error')
            return redirect(url_for('main.dashboard'))

    if not current_user.is_manager_or_above():
        flash('Acces reserve aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    # Check if WeasyPrint is available
    if not WEASYPRINT_AVAILABLE:
        flash('La generation PDF n\'est pas disponible. Veuillez installer WeasyPrint.', 'error')
        return redirect(url_for('reports.settlement', stop_id=stop_id))

    # Calculate settlement
    settlement_data = calculate_settlement(stop)

    # Generate PDF
    try:
        pdf_bytes = generate_settlement_pdf(settlement_data)
    except Exception as e:
        flash(f'Erreur lors de la generation du PDF: {str(e)}', 'error')
        return redirect(url_for('reports.settlement', stop_id=stop_id))

    # Create filename
    venue_name = settlement_data['venue_name'].replace(' ', '_').replace('/', '-')
    date_str = settlement_data['date'].strftime('%Y%m%d') if settlement_data['date'] else 'NA'
    filename = f"settlement_{venue_name}_{date_str}.pdf"

    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@reports_bp.route('/dashboard/api/chart-data')
@login_required
def dashboard_chart_data():
    """API endpoint for dashboard chart data (JSON)."""
    import json

    if not current_user.is_manager_or_above():
        return {'error': 'Unauthorized'}, 403

    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    tours = Tour.query.filter(Tour.band_id.in_(user_band_ids)).order_by(
        Tour.start_date.desc()
    ).all()

    kpis = calculate_dashboard_kpis(tours)

    return {
        'monthly_revenue': kpis['monthly_revenue'],
        'revenue_by_tour': kpis['revenue_by_tour'],
        'guarantee_percentage': kpis['guarantee_percentage'],
        'door_deal_percentage': kpis['door_deal_percentage'],
        'top_stops': [
            {
                'venue': s['venue_name'],
                'city': s['venue_city'],
                'revenue': s['total_estimated_revenue'],
                'fill_rate': s['fill_rate']
            }
            for s in kpis['top_stops']
        ]
    }


# =============================================================================
# ACCOUNTING EXPORTS - Documents pour transmission a la comptabilite
# =============================================================================

@reports_bp.route('/accounting')
@login_required
def accounting_index():
    """Page d'accueil des exports comptables."""
    if not current_user.is_manager_or_above():
        flash('Acces reserve aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    if not SERVICES_AVAILABLE:
        flash('Les services d\'export ne sont pas disponibles.', 'error')
        return redirect(url_for('reports.index'))

    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    # Get tours for selection
    tours = Tour.query.filter(Tour.band_id.in_(user_band_ids)).order_by(
        Tour.start_date.desc()
    ).all()

    # Get team members with payment configs
    from app.models.payments import UserPaymentConfig
    team_members = User.query.join(UserPaymentConfig).all()

    return render_template(
        'reports/accounting_index.html',
        tours=tours,
        team_members=team_members
    )


@reports_bp.route('/accounting/bordereau/<int:tour_id>')
@login_required
def accounting_bordereau(tour_id):
    """Generer le bordereau de paiement PDF pour une tournee."""
    if not current_user.is_manager_or_above():
        flash('Acces reserve aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    if not SERVICES_AVAILABLE:
        flash('Les services d\'export ne sont pas disponibles.', 'error')
        return redirect(url_for('reports.index'))

    tour = Tour.query.get_or_404(tour_id)

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Acces non autorise.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        pdf_bytes = ReportService.generate_bordereau_paiement(tour_id)

        # Create filename
        tour_name = tour.name.replace(' ', '_').replace('/', '-')
        date_str = tour.start_date.strftime('%Y%m%d') if tour.start_date else 'NA'
        filename = f"bordereau_paiement_{tour_name}_{date_str}.pdf"

        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        flash(f'Erreur lors de la generation du bordereau: {str(e)}', 'error')
        return redirect(url_for('reports.accounting_index'))


@reports_bp.route('/accounting/masse-salariale/<int:tour_id>')
@login_required
def accounting_masse_salariale(tour_id):
    """Exporter la masse salariale CSV pour une tournee."""
    if not current_user.is_manager_or_above():
        flash('Acces reserve aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    if not SERVICES_AVAILABLE:
        flash('Les services d\'export ne sont pas disponibles.', 'error')
        return redirect(url_for('reports.index'))

    tour = Tour.query.get_or_404(tour_id)

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Acces non autorise.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        csv_content = ReportService.export_masse_salariale_csv(tour_id)

        # Create filename
        tour_name = tour.name.replace(' ', '_').replace('/', '-')
        date_str = tour.start_date.strftime('%Y%m%d') if tour.start_date else 'NA'
        filename = f"masse_salariale_{tour_name}_{date_str}.csv"

        return Response(
            csv_content,
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        flash(f'Erreur lors de l\'export CSV: {str(e)}', 'error')
        return redirect(url_for('reports.accounting_index'))


@reports_bp.route('/accounting/paiements-a-effectuer')
@login_required
def accounting_paiements_a_effectuer():
    """Exporter la liste des paiements a effectuer (approuves, non payes)."""
    if not current_user.is_manager_or_above():
        flash('Acces reserve aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    if not SERVICES_AVAILABLE:
        flash('Les services d\'export ne sont pas disponibles.', 'error')
        return redirect(url_for('reports.index'))

    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]

    try:
        from datetime import date
        csv_content = ReportService.export_paiements_a_effectuer_csv(user_band_ids)

        # Create filename
        today = date.today().strftime('%Y%m%d')
        filename = f"paiements_a_effectuer_{today}.csv"

        return Response(
            csv_content,
            mimetype='text/csv; charset=utf-8',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        flash(f'Erreur lors de l\'export CSV: {str(e)}', 'error')
        return redirect(url_for('reports.accounting_index'))


@reports_bp.route('/accounting/fiche-membre/<int:user_id>')
@login_required
def accounting_fiche_membre(user_id):
    """Generer la fiche recapitulative PDF pour un membre."""
    if not current_user.is_manager_or_above():
        flash('Acces reserve aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    if not SERVICES_AVAILABLE:
        flash('Les services d\'export ne sont pas disponibles.', 'error')
        return redirect(url_for('reports.index'))

    user = User.query.get_or_404(user_id)

    # Get optional date filters
    from datetime import datetime
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    try:
        pdf_bytes = ReportService.generate_fiche_membre(user_id, start_date, end_date)

        # Create filename
        user_name = user.full_name.replace(' ', '_').replace('/', '-')
        from datetime import date
        today = date.today().strftime('%Y%m%d')
        filename = f"fiche_membre_{user_name}_{today}.pdf"

        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        flash(f'Erreur lors de la generation de la fiche: {str(e)}', 'error')
        return redirect(url_for('reports.accounting_index'))


@reports_bp.route('/accounting/budget/<int:tour_id>')
@login_required
def accounting_budget(tour_id):
    """Generer le rapport budget PDF pour une tournee."""
    if not current_user.is_manager_or_above():
        flash('Acces reserve aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    if not SERVICES_AVAILABLE:
        flash('Les services d\'export ne sont pas disponibles.', 'error')
        return redirect(url_for('reports.index'))

    tour = Tour.query.get_or_404(tour_id)

    # Check access
    user_bands = current_user.bands + current_user.managed_bands
    user_band_ids = [b.id for b in user_bands]
    if tour.band_id not in user_band_ids:
        flash('Acces non autorise.', 'error')
        return redirect(url_for('main.dashboard'))

    try:
        pdf_bytes = ReportService.generate_budget_tournee(tour_id)

        # Create filename
        tour_name = tour.name.replace(' ', '_').replace('/', '-')
        date_str = tour.start_date.strftime('%Y%m%d') if tour.start_date else 'NA'
        filename = f"budget_tournee_{tour_name}_{date_str}.pdf"

        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        flash(f'Erreur lors de la generation du budget: {str(e)}', 'error')
        return redirect(url_for('reports.accounting_index'))


@reports_bp.route('/accounting/attestation/<int:payment_id>')
@login_required
def accounting_attestation(payment_id):
    """Generer l'attestation de paiement PDF."""
    if not current_user.is_manager_or_above():
        flash('Acces reserve aux managers.', 'error')
        return redirect(url_for('main.dashboard'))

    if not SERVICES_AVAILABLE:
        flash('Les services d\'export ne sont pas disponibles.', 'error')
        return redirect(url_for('reports.index'))

    from app.models.payments import TeamMemberPayment
    payment = TeamMemberPayment.query.get_or_404(payment_id)

    # Check access via tour
    if payment.tour:
        user_bands = current_user.bands + current_user.managed_bands
        user_band_ids = [b.id for b in user_bands]
        if payment.tour.band_id not in user_band_ids:
            flash('Acces non autorise.', 'error')
            return redirect(url_for('main.dashboard'))

    try:
        pdf_bytes = ReportService.generate_attestation_paiement(payment_id)

        # Create filename
        filename = f"attestation_{payment.reference}.pdf"

        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        flash(f'Erreur lors de la generation de l\'attestation: {str(e)}', 'error')
        return redirect(url_for('reports.accounting_index'))
