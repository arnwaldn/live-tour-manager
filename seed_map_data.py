"""Seed script for map test data."""
from datetime import date, time
from app.extensions import db
from app import create_app
from app.models.user import User
from app.models.band import Band
from app.models.venue import Venue
from app.models.tour import Tour, TourStatus
from app.models.tour_stop import TourStop, TourStopStatus, EventType

app = create_app()
with app.app_context():
    # Get or create test user
    user = User.query.filter_by(email='test@test.com').first()
    if not user:
        from werkzeug.security import generate_password_hash
        user = User(
            email='test@test.com',
            first_name='Test',
            last_name='User',
            password_hash=generate_password_hash('test123')
        )
        db.session.add(user)
        db.session.commit()
        print('Created test user')

    # Get or create test band
    band = Band.query.filter_by(name='GigRoute').first()
    if not band:
        band = Band(name='GigRoute', genre='World Music', bio='Groupe test')
        band.manager_id = user.id
        db.session.add(band)
        db.session.commit()
        print('Created band: GigRoute')
    else:
        print(f'Using existing band: {band.name}')

    # Create venues with GPS coordinates (real locations in France)
    venues_data = [
        {'name': 'Olympia', 'city': 'Paris', 'country': 'France', 'address': '28 Boulevard des Capucines', 'postal_code': '75009', 'latitude': 48.8701, 'longitude': 2.3284, 'capacity': 2000},
        {'name': 'Le Zenith', 'city': 'Paris', 'country': 'France', 'address': '211 Avenue Jean Jaures', 'postal_code': '75019', 'latitude': 48.8924, 'longitude': 2.3934, 'capacity': 6300},
        {'name': 'La Cigale', 'city': 'Paris', 'country': 'France', 'address': '120 Boulevard Marguerite de Rochechouart', 'postal_code': '75018', 'latitude': 48.8825, 'longitude': 2.3401, 'capacity': 1400},
        {'name': 'Stereolux', 'city': 'Nantes', 'country': 'France', 'address': '4 Boulevard Leon Bureau', 'postal_code': '44200', 'latitude': 47.2064, 'longitude': -1.5644, 'capacity': 1200},
        {'name': 'Le Krakatoa', 'city': 'Bordeaux', 'country': 'France', 'address': '3 Avenue Victor Hugo', 'postal_code': '33700', 'latitude': 44.8629, 'longitude': -0.5261, 'capacity': 1000},
        {'name': 'Le Bikini', 'city': 'Toulouse', 'country': 'France', 'address': 'Rue Theodore Monod', 'postal_code': '31200', 'latitude': 43.6144, 'longitude': 1.3943, 'capacity': 1500},
        {'name': 'Le Cargo', 'city': 'Caen', 'country': 'France', 'address': '9 Cours Caffarelli', 'postal_code': '14000', 'latitude': 49.1867, 'longitude': -0.3567, 'capacity': 800},
        {'name': "L'Aeronef", 'city': 'Lille', 'country': 'France', 'address': '168 Avenue Willy Brandt', 'postal_code': '59000', 'latitude': 50.6364, 'longitude': 3.0733, 'capacity': 2500},
        {'name': 'Le Transbordeur', 'city': 'Lyon', 'country': 'France', 'address': '3 Boulevard Stalingrad', 'postal_code': '69100', 'latitude': 45.7562, 'longitude': 4.8696, 'capacity': 1800},
        {'name': 'Le Rockstore', 'city': 'Montpellier', 'country': 'France', 'address': '20 Rue de Verdun', 'postal_code': '34000', 'latitude': 43.6095, 'longitude': 3.8767, 'capacity': 900},
    ]

    created_venues = []
    for vdata in venues_data:
        venue = Venue.query.filter_by(name=vdata['name']).first()
        if not venue:
            venue = Venue(**vdata)
            db.session.add(venue)
            print(f"Created venue: {vdata['name']} ({vdata['city']})")
        else:
            # Update GPS coordinates
            venue.latitude = vdata['latitude']
            venue.longitude = vdata['longitude']
            print(f'Updated GPS for: {venue.name}')
        created_venues.append(venue)

    db.session.commit()

    # Create tour
    tour = Tour.query.filter_by(name='Tournee France 2026').first()
    if not tour:
        tour = Tour(
            name='Tournee France 2026',
            band_id=band.id,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
            status=TourStatus.PLANNING,
            description='Tournee nationale de 10 dates',
            budget=50000.0,
            currency='EUR'
        )
        db.session.add(tour)
        db.session.commit()
        print(f'Created tour: {tour.name}')
    else:
        print(f'Using existing tour: {tour.name}')
        # Delete existing stops for fresh data
        TourStop.query.filter_by(tour_id=tour.id).delete()
        db.session.commit()
        print('Cleared existing tour stops')

    # Create tour stops with various event types
    stops_data = [
        {'venue_idx': 0, 'date': date(2026, 2, 1), 'event_type': 'show', 'status': 'confirmed'},
        {'venue_idx': 3, 'date': date(2026, 2, 3), 'event_type': 'show', 'status': 'confirmed'},
        {'venue_idx': 4, 'date': date(2026, 2, 5), 'event_type': 'show', 'status': 'pending'},
        {'venue_idx': 5, 'date': date(2026, 2, 6), 'event_type': 'show', 'status': 'confirmed'},
        {'venue_idx': 9, 'date': date(2026, 2, 8), 'event_type': 'show', 'status': 'confirmed'},
        {'venue_idx': 8, 'date': date(2026, 2, 10), 'event_type': 'show', 'status': 'hold'},
        {'venue_idx': 1, 'date': date(2026, 2, 12), 'event_type': 'rehearsal', 'status': 'confirmed'},
        {'venue_idx': 2, 'date': date(2026, 2, 13), 'event_type': 'show', 'status': 'confirmed'},
        {'venue_idx': 7, 'date': date(2026, 2, 15), 'event_type': 'show', 'status': 'confirmed'},
        {'venue_idx': 6, 'date': date(2026, 2, 17), 'event_type': 'show', 'status': 'pending'},
    ]

    for sdata in stops_data:
        venue_id = created_venues[sdata['venue_idx']].id if sdata['venue_idx'] is not None else None
        stop = TourStop(
            tour_id=tour.id,
            venue_id=venue_id,
            date=sdata['date'],
            event_type=EventType(sdata['event_type']),
            status=TourStopStatus(sdata['status']),
            load_in_time=time(9, 0) if sdata['event_type'] == 'show' else None,
            crew_call_time=time(10, 0) if sdata['event_type'] == 'show' else None,
            artist_call_time=time(14, 0) if sdata['event_type'] == 'show' else None,
            soundcheck_time=time(16, 0) if sdata['event_type'] == 'show' else None,
            doors_time=time(19, 0) if sdata['event_type'] == 'show' else None,
            set_time=time(20, 30) if sdata['event_type'] == 'show' else None,
            curfew_time=time(23, 0) if sdata['event_type'] == 'show' else None,
            guarantee=2500.0 if sdata['event_type'] == 'show' else None,
            ticket_price=25.0 if sdata['event_type'] == 'show' else None,
        )
        db.session.add(stop)
        venue_name = created_venues[sdata['venue_idx']].name if sdata['venue_idx'] is not None else 'N/A'
        print(f"Created stop: {sdata['date']} - {sdata['event_type']} @ {venue_name}")

    db.session.commit()
    print(f'\n=== DONE ===')
    print(f'Tour: {tour.name} (ID: {tour.id})')
    print(f'Total stops: {len(stops_data)}')
    print(f'Map URL: http://127.0.0.1:5001/tours/{tour.id}/map')
