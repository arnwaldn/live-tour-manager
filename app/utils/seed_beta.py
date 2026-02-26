"""
Seed beta test data — realistic French tour management scenario.
TEMPORARY FILE — delete after seeding production.
"""
from datetime import datetime, date, time, timedelta
from decimal import Decimal

from app.extensions import db
from app.models.user import User, AccessLevel
from app.models.profession import (
    Profession, UserProfession, ProfessionCategory, seed_professions
)
from app.models.band import Band, BandMembership
from app.models.venue import Venue, VenueContact
from app.models.tour import Tour, TourStatus
from app.models.tour_stop import (
    TourStop, TourStopStatus, EventType, TourStopMember, MemberAssignmentStatus
)
from app.models.guestlist import GuestlistEntry, GuestlistStatus, EntryType
from app.models.logistics import LogisticsInfo, LogisticsType, LogisticsStatus
from app.models.payments import (
    TeamMemberPayment, PaymentType, PaymentStatus, PaymentMethod,
    StaffCategory, StaffRole, ContractType, PaymentFrequency
)
from app.models.notification import Notification, NotificationType, NotificationCategory
from app.models.crew_schedule import CrewScheduleSlot, CrewAssignment, AssignmentStatus


def run_seed():
    """
    Populate the database with realistic beta test data.
    Returns a summary dict of created objects.
    """
    results = {}

    # ================================================================
    # 0. SEED PROFESSIONS (truncated during reset)
    # ================================================================
    seed_professions()
    prof_count = Profession.query.count()
    results['professions'] = prof_count

    # Helper: get profession by code
    def prof(code):
        return Profession.query.filter_by(code=code).first()

    # ================================================================
    # 1. USERS (7 new users + admin already exists as id=1)
    # ================================================================
    admin = User.query.filter_by(email='arnaud.porcel@gmail.com').first()
    if not admin:
        return {'error': 'Admin user not found — run DB reset first'}

    users_data = [
        {
            'email': 'sophie.martin@gigroute.fr',
            'first_name': 'Sophie', 'last_name': 'Martin',
            'access_level': AccessLevel.MANAGER,
            'password': 'BetaTest2026!',
            'professions': [('TOUR_MANAGER', True)],
        },
        {
            'email': 'lucas.dubois@gigroute.fr',
            'first_name': 'Lucas', 'last_name': 'Dubois',
            'access_level': AccessLevel.STAFF,
            'password': 'BetaTest2026!',
            'professions': [('INGE_SON_FACADE', True)],
        },
        {
            'email': 'marie.leroy@gigroute.fr',
            'first_name': 'Marie', 'last_name': 'Leroy',
            'access_level': AccessLevel.STAFF,
            'password': 'BetaTest2026!',
            'professions': [('CHEF_LUMIERE', True)],
        },
        {
            'email': 'thomas.bernard@gigroute.fr',
            'first_name': 'Thomas', 'last_name': 'Bernard',
            'access_level': AccessLevel.STAFF,
            'password': 'BetaTest2026!',
            'professions': [('BACKLINE', True)],
        },
        {
            'email': 'julie.moreau@gigroute.fr',
            'first_name': 'Julie', 'last_name': 'Moreau',
            'access_level': AccessLevel.STAFF,
            'password': 'BetaTest2026!',
            'professions': [('CLAVIER', True)],
        },
        {
            'email': 'antoine.petit@gigroute.fr',
            'first_name': 'Antoine', 'last_name': 'Petit',
            'access_level': AccessLevel.STAFF,
            'password': 'BetaTest2026!',
            'professions': [('BATTEUR', True)],
        },
        {
            'email': 'camille.durand@gigroute.fr',
            'first_name': 'Camille', 'last_name': 'Durand',
            'access_level': AccessLevel.STAFF,
            'password': 'BetaTest2026!',
            'professions': [('REGISSEUR_GENERAL', True)],
        },
    ]

    created_users = {}
    for u_data in users_data:
        existing = User.query.filter_by(email=u_data['email']).first()
        if existing:
            created_users[u_data['first_name'].lower()] = existing
            continue
        user = User(
            email=u_data['email'],
            first_name=u_data['first_name'],
            last_name=u_data['last_name'],
            access_level=u_data['access_level'],
            is_active=True,
            email_verified=True,
        )
        user.set_password(u_data['password'])
        db.session.add(user)
        db.session.flush()  # get ID

        # Assign professions
        for prof_code, is_primary in u_data['professions']:
            p = prof(prof_code)
            if p:
                up = UserProfession(user_id=user.id, profession_id=p.id, is_primary=is_primary)
                db.session.add(up)

        created_users[u_data['first_name'].lower()] = user

    # Also assign profession to admin (manager)
    admin_prof = prof('MANAGER_ARTISTE')
    if admin_prof:
        existing_ap = UserProfession.query.filter_by(user_id=admin.id, profession_id=admin_prof.id).first()
        if not existing_ap:
            db.session.add(UserProfession(user_id=admin.id, profession_id=admin_prof.id, is_primary=True))

    db.session.flush()
    results['users'] = len(created_users)

    sophie = created_users.get('sophie')
    lucas = created_users.get('lucas')
    marie = created_users.get('marie')
    thomas = created_users.get('thomas')
    julie = created_users.get('julie')
    antoine = created_users.get('antoine')
    camille = created_users.get('camille')

    # ================================================================
    # 2. BAND: Les Satellites
    # ================================================================
    band = Band.query.filter_by(name='Les Satellites').first()
    if not band:
        band = Band(
            name='Les Satellites',
            genre='Rock Alternatif / Electro-Pop',
            bio=(
                "Formé en 2019 à Toulouse, Les Satellites mêlent guitares saturées, "
                "synthétiseurs analogiques et rythmiques électroniques. Après deux EP et "
                "plus de 150 concerts en France et en Europe, le groupe sort son premier "
                "album \"Orbite\" en janvier 2026. Un son à la croisée de Phoenix, Parcels "
                "et La Femme."
            ),
            website='https://les-satellites.fr',
            social_links='{"instagram": "@lessatellites", "spotify": "https://open.spotify.com/artist/satellites"}',
            manager_id=admin.id,
        )
        db.session.add(band)
        db.session.flush()

    # Band memberships
    memberships = [
        (admin.id, 'Chant / Guitare', 'leader'),
        (julie.id, 'Claviers / Synthétiseurs', 'member'),
        (antoine.id, 'Batterie / Machines', 'member'),
    ]
    for user_id, instrument, role_in_band in memberships:
        existing = BandMembership.query.filter_by(user_id=user_id, band_id=band.id).first()
        if not existing:
            db.session.add(BandMembership(
                user_id=user_id, band_id=band.id,
                instrument=instrument, role_in_band=role_in_band
            ))

    db.session.flush()
    results['band'] = band.name

    # ================================================================
    # 3. VENUES (8 real French venues)
    # ================================================================
    venues_data = [
        {
            'name': "L'Olympia",
            'address': '28 Boulevard des Capucines',
            'city': 'Paris', 'country': 'France', 'postal_code': '75009',
            'capacity': 1996, 'venue_type': 'Salle de concert',
            'latitude': Decimal('48.8698'), 'longitude': Decimal('2.3282'),
            'timezone': 'Europe/Paris',
            'contacts': [
                {'name': 'Philippe Arnaud', 'role': 'Directeur de production', 'email': 'production@olympia.fr', 'phone': '+33 1 47 42 25 49', 'is_primary': True},
            ]
        },
        {
            'name': 'Le Transbordeur',
            'address': '3 Boulevard de Stalingrad',
            'city': 'Villeurbanne', 'country': 'France', 'postal_code': '69100',
            'capacity': 1800, 'venue_type': 'SMAC',
            'latitude': Decimal('45.7833'), 'longitude': Decimal('4.8642'),
            'timezone': 'Europe/Paris',
            'contacts': [
                {'name': 'Estelle Girard', 'role': 'Responsable programmation', 'email': 'prog@transbordeur.fr', 'phone': '+33 4 78 93 08 33', 'is_primary': True},
            ]
        },
        {
            'name': 'La Laiterie',
            'address': '13 Rue du Hohwald',
            'city': 'Strasbourg', 'country': 'France', 'postal_code': '67000',
            'capacity': 900, 'venue_type': 'SMAC',
            'latitude': Decimal('48.5747'), 'longitude': Decimal('7.7492'),
            'timezone': 'Europe/Paris',
            'contacts': [
                {'name': 'Marc Weber', 'role': 'Régisseur général', 'email': 'technique@laiterie.artefact.org', 'phone': '+33 3 88 23 72 37', 'is_primary': True},
            ]
        },
        {
            'name': 'Le Bikini',
            'address': 'Rue Théodore Monod',
            'city': 'Ramonville-Saint-Agne', 'country': 'France', 'postal_code': '31520',
            'capacity': 1500, 'venue_type': 'SMAC',
            'latitude': Decimal('43.5587'), 'longitude': Decimal('1.4778'),
            'timezone': 'Europe/Paris',
            'contacts': [
                {'name': 'Hervé Sansonetto', 'role': 'Directeur', 'email': 'contact@lebikini.com', 'phone': '+33 5 62 24 09 50', 'is_primary': True},
            ]
        },
        {
            'name': "L'Aéronef",
            'address': '168 Avenue Willy Brandt',
            'city': 'Lille', 'country': 'France', 'postal_code': '59777',
            'capacity': 1100, 'venue_type': 'SMAC',
            'latitude': Decimal('50.6360'), 'longitude': Decimal('3.0706'),
            'timezone': 'Europe/Paris',
            'contacts': [
                {'name': 'Nathalie Coste', 'role': 'Programmatrice', 'email': 'prog@aeronef.fr', 'phone': '+33 3 20 13 50 00', 'is_primary': True},
            ]
        },
        {
            'name': 'La Cigale',
            'address': '120 Boulevard de Rochechouart',
            'city': 'Paris', 'country': 'France', 'postal_code': '75018',
            'capacity': 1400, 'venue_type': 'Salle de concert',
            'latitude': Decimal('48.8822'), 'longitude': Decimal('2.3486'),
            'timezone': 'Europe/Paris',
            'contacts': [
                {'name': 'Jean-François Koch', 'role': 'Directeur technique', 'email': 'technique@lacigale.fr', 'phone': '+33 1 49 25 81 75', 'is_primary': True},
            ]
        },
        {
            'name': 'Stereolux',
            'address': '4 Boulevard Léon Bureau',
            'city': 'Nantes', 'country': 'France', 'postal_code': '44200',
            'capacity': 1200, 'venue_type': 'SMAC',
            'latitude': Decimal('47.2055'), 'longitude': Decimal('-1.5641'),
            'timezone': 'Europe/Paris',
            'contacts': [
                {'name': 'Romain Cailleau', 'role': 'Chargé de production', 'email': 'production@stereolux.org', 'phone': '+33 2 40 43 20 43', 'is_primary': True},
            ]
        },
        {
            'name': 'La Rockhal',
            'address': '5 Avenue du Rock',
            'city': 'Esch-sur-Alzette', 'country': 'Luxembourg', 'postal_code': '4361',
            'capacity': 6500, 'venue_type': 'Salle de concert',
            'latitude': Decimal('49.4975'), 'longitude': Decimal('5.9765'),
            'timezone': 'Europe/Luxembourg',
            'contacts': [
                {'name': 'Olivier Toth', 'role': 'Booking Manager', 'email': 'booking@rockhal.lu', 'phone': '+352 24 55 1', 'is_primary': True},
            ]
        },
    ]

    created_venues = {}
    for v_data in venues_data:
        contacts = v_data.pop('contacts')
        existing = Venue.query.filter_by(name=v_data['name']).first()
        if existing:
            created_venues[v_data['name']] = existing
            continue
        venue = Venue(**v_data)
        db.session.add(venue)
        db.session.flush()
        for c in contacts:
            db.session.add(VenueContact(venue_id=venue.id, **c))
        created_venues[v_data['name']] = venue

    db.session.flush()
    results['venues'] = len(created_venues)

    # ================================================================
    # 4. TOUR: Tournée Orbite 2026
    # ================================================================
    tour = Tour.query.filter_by(name='Tournée Orbite 2026').first()
    if not tour:
        tour = Tour(
            name='Tournée Orbite 2026',
            description=(
                "Tournée de sortie d'album pour \"Orbite\", premier album des Satellites. "
                "8 dates en France et au Luxembourg, de mars à avril 2026. "
                "Production : Studio Palenque. Booking : Live Nation France."
            ),
            start_date=date(2026, 3, 15),
            end_date=date(2026, 4, 12),
            status=TourStatus.CONFIRMED,
            budget=Decimal('85000.00'),
            currency='EUR',
            band_id=band.id,
        )
        db.session.add(tour)
        db.session.flush()

    results['tour'] = tour.name

    # ================================================================
    # 5. TOUR STOPS (8 dates)
    # ================================================================
    stops_data = [
        {
            'date': date(2026, 3, 15),
            'venue_name': 'Le Bikini',
            'status': TourStopStatus.CONFIRMED,
            'event_type': EventType.SHOW,
            'show_type': 'Headline',
            'guarantee': Decimal('3500.00'),
            'ticket_price': Decimal('25.00'),
            'sold_tickets': 680,
            'doors_time': time(19, 30),
            'soundcheck_time': time(16, 0),
            'set_time': time(21, 0),
            'curfew_time': time(23, 0),
            'load_in_time': time(14, 0),
            'crew_call_time': time(14, 0),
            'artist_call_time': time(18, 0),
            'catering_time': time(18, 30),
            'set_length_minutes': 90,
            'notes': 'Première date de la tournée. Soirée release party album Orbite.',
            'internal_notes': 'Promoteur local : Détours Productions. Contact avancé OK.',
        },
        {
            'date': date(2026, 3, 18),
            'venue_name': 'Stereolux',
            'status': TourStopStatus.CONFIRMED,
            'event_type': EventType.SHOW,
            'show_type': 'Headline',
            'guarantee': Decimal('3000.00'),
            'ticket_price': Decimal('22.00'),
            'sold_tickets': 420,
            'doors_time': time(20, 0),
            'soundcheck_time': time(16, 30),
            'set_time': time(21, 0),
            'curfew_time': time(23, 30),
            'load_in_time': time(14, 0),
            'crew_call_time': time(14, 0),
            'artist_call_time': time(18, 30),
            'catering_time': time(19, 0),
            'set_length_minutes': 90,
            'notes': 'Nantes — forte communauté locale. Première partie : Halo Maud.',
        },
        {
            'date': date(2026, 3, 21),
            'venue_name': "L'Aéronef",
            'status': TourStopStatus.CONFIRMED,
            'event_type': EventType.SHOW,
            'show_type': 'Headline',
            'guarantee': Decimal('2800.00'),
            'ticket_price': Decimal('22.00'),
            'sold_tickets': 310,
            'doors_time': time(20, 0),
            'soundcheck_time': time(16, 0),
            'set_time': time(21, 0),
            'curfew_time': time(23, 0),
            'load_in_time': time(13, 30),
            'crew_call_time': time(13, 30),
            'artist_call_time': time(18, 0),
            'catering_time': time(18, 30),
            'set_length_minutes': 90,
            'notes': 'Lille. Transport en bus depuis Nantes (départ 8h).',
        },
        {
            'date': date(2026, 3, 25),
            'venue_name': 'La Laiterie',
            'status': TourStopStatus.CONFIRMED,
            'event_type': EventType.SHOW,
            'show_type': 'Headline',
            'guarantee': Decimal('2500.00'),
            'ticket_price': Decimal('20.00'),
            'sold_tickets': 250,
            'doors_time': time(20, 0),
            'soundcheck_time': time(16, 0),
            'set_time': time(21, 0),
            'curfew_time': time(23, 0),
            'load_in_time': time(14, 0),
            'crew_call_time': time(14, 0),
            'artist_call_time': time(18, 0),
            'catering_time': time(18, 30),
            'set_length_minutes': 90,
            'notes': 'Strasbourg. Jour off le 24 — visite ville.',
        },
        {
            'date': date(2026, 3, 27),
            'venue_name': 'La Rockhal',
            'status': TourStopStatus.PENDING,
            'event_type': EventType.SHOW,
            'show_type': 'Support',
            'guarantee': Decimal('2000.00'),
            'ticket_price': Decimal('35.00'),
            'sold_tickets': 0,
            'doors_time': time(19, 0),
            'soundcheck_time': time(15, 0),
            'set_time': time(20, 0),
            'curfew_time': time(23, 30),
            'load_in_time': time(12, 0),
            'crew_call_time': time(12, 0),
            'artist_call_time': time(17, 0),
            'catering_time': time(17, 30),
            'set_length_minutes': 45,
            'notes': 'Luxembourg — première partie de M83. Négociation en cours avec la Rockhal.',
        },
        {
            'date': date(2026, 4, 2),
            'venue_name': 'Le Transbordeur',
            'status': TourStopStatus.CONFIRMED,
            'event_type': EventType.SHOW,
            'show_type': 'Headline',
            'guarantee': Decimal('4000.00'),
            'ticket_price': Decimal('24.00'),
            'sold_tickets': 520,
            'doors_time': time(19, 30),
            'soundcheck_time': time(16, 0),
            'set_time': time(21, 0),
            'curfew_time': time(23, 0),
            'load_in_time': time(14, 0),
            'crew_call_time': time(14, 0),
            'artist_call_time': time(18, 0),
            'catering_time': time(18, 30),
            'set_length_minutes': 90,
            'notes': 'Lyon — salle quasi complète. Captation vidéo prévue.',
            'internal_notes': 'Équipe vidéo locale à confirmer. Budget captation : 2500€ HT.',
        },
        {
            'date': date(2026, 4, 8),
            'venue_name': 'La Cigale',
            'status': TourStopStatus.DRAFT,
            'event_type': EventType.SHOW,
            'show_type': 'Headline',
            'guarantee': Decimal('5000.00'),
            'ticket_price': Decimal('28.00'),
            'sold_tickets': 0,
            'doors_time': time(19, 30),
            'soundcheck_time': time(15, 0),
            'set_time': time(21, 0),
            'curfew_time': time(23, 30),
            'load_in_time': time(13, 0),
            'crew_call_time': time(13, 0),
            'artist_call_time': time(17, 30),
            'catering_time': time(18, 0),
            'set_length_minutes': 90,
            'notes': 'Paris — La Cigale. En attente confirmation label pour showcase presse.',
        },
        {
            'date': date(2026, 4, 12),
            'venue_name': "L'Olympia",
            'status': TourStopStatus.CONFIRMED,
            'event_type': EventType.SHOW,
            'show_type': 'Headline',
            'guarantee': Decimal('8000.00'),
            'ticket_price': Decimal('32.00'),
            'sold_tickets': 1450,
            'doors_time': time(19, 0),
            'soundcheck_time': time(14, 0),
            'set_time': time(20, 30),
            'curfew_time': time(23, 0),
            'load_in_time': time(10, 0),
            'crew_call_time': time(10, 0),
            'artist_call_time': time(17, 0),
            'catering_time': time(17, 30),
            'set_length_minutes': 100,
            'notes': 'Clôture de tournée à L\'Olympia ! Concert événement. Invités surprises prévus.',
            'internal_notes': 'Budget total Olympia : 15K€. Captation live pour futur album. Guest list élargie (presse + industrie + VIP label).',
        },
    ]

    created_stops = {}
    for s_data in stops_data:
        venue_name = s_data.pop('venue_name')
        venue = created_venues.get(venue_name)
        if not venue:
            continue

        existing = TourStop.query.filter_by(tour_id=tour.id, date=s_data['date']).first()
        if existing:
            created_stops[s_data['date'].isoformat()] = existing
            continue

        stop = TourStop(
            tour_id=tour.id,
            band_id=band.id,
            venue_id=venue.id,
            **s_data
        )
        db.session.add(stop)
        db.session.flush()
        created_stops[stop.date.isoformat()] = stop

    db.session.flush()
    results['tour_stops'] = len(created_stops)

    # ================================================================
    # 6. CREW ASSIGNMENTS (TourStopMember v2) — assign crew to stops
    # ================================================================
    crew_members = [sophie, lucas, marie, thomas, camille]
    artists = [admin, julie, antoine]
    assignment_count = 0

    for stop_key, stop in created_stops.items():
        # Assign all crew to confirmed stops
        if stop.status in (TourStopStatus.CONFIRMED, TourStopStatus.PENDING):
            for crew in crew_members:
                if not crew:
                    continue
                existing = TourStopMember.query.filter_by(
                    tour_stop_id=stop.id, user_id=crew.id
                ).first()
                if not existing:
                    p = None
                    up = UserProfession.query.filter_by(user_id=crew.id, is_primary=True).first()
                    if up:
                        p = up.profession_id

                    member = TourStopMember(
                        tour_stop_id=stop.id,
                        user_id=crew.id,
                        profession_id=p,
                        status=MemberAssignmentStatus.CONFIRMED if stop.status == TourStopStatus.CONFIRMED else MemberAssignmentStatus.ASSIGNED,
                        call_time=stop.crew_call_time,
                        work_start=stop.load_in_time,
                        work_end=time(23, 30),
                        meal_time=stop.catering_time,
                        assigned_by_id=admin.id,
                    )
                    db.session.add(member)
                    assignment_count += 1

            # Assign artists
            for artist in artists:
                if not artist:
                    continue
                existing = TourStopMember.query.filter_by(
                    tour_stop_id=stop.id, user_id=artist.id
                ).first()
                if not existing:
                    p = None
                    up = UserProfession.query.filter_by(user_id=artist.id, is_primary=True).first()
                    if up:
                        p = up.profession_id

                    member = TourStopMember(
                        tour_stop_id=stop.id,
                        user_id=artist.id,
                        profession_id=p,
                        status=MemberAssignmentStatus.CONFIRMED,
                        call_time=stop.artist_call_time,
                        work_start=stop.artist_call_time,
                        work_end=time(23, 0),
                        meal_time=stop.catering_time,
                        assigned_by_id=admin.id,
                    )
                    db.session.add(member)
                    assignment_count += 1

    db.session.flush()
    results['crew_assignments'] = assignment_count

    # ================================================================
    # 7. GUESTLIST — entries for 3 stops
    # ================================================================
    gl_count = 0
    # Olympia (final show) — big guestlist
    olympia_stop = created_stops.get('2026-04-12')
    if olympia_stop:
        gl_entries_olympia = [
            {'guest_name': 'Jean-Marc Fontaine', 'guest_email': 'jm.fontaine@musicweek.fr', 'company': 'Music Week', 'entry_type': EntryType.PRESS, 'plus_ones': 1, 'status': GuestlistStatus.APPROVED},
            {'guest_name': 'Isabelle Chen', 'guest_email': 'i.chen@lesinrocks.com', 'company': 'Les Inrockuptibles', 'entry_type': EntryType.PRESS, 'plus_ones': 0, 'status': GuestlistStatus.APPROVED},
            {'guest_name': 'PatrickMusic', 'guest_email': 'patrick@musicast.fr', 'company': 'Musicast Distribution', 'entry_type': EntryType.INDUSTRY, 'plus_ones': 2, 'status': GuestlistStatus.APPROVED},
            {'guest_name': 'Sarah Lenoir', 'guest_email': 'sarah.lenoir@warnermusic.fr', 'company': 'Warner Music France', 'entry_type': EntryType.INDUSTRY, 'plus_ones': 1, 'status': GuestlistStatus.APPROVED},
            {'guest_name': 'Alexandre Dupont', 'guest_email': 'alex@livenation.fr', 'company': 'Live Nation', 'entry_type': EntryType.INDUSTRY, 'plus_ones': 3, 'status': GuestlistStatus.APPROVED},
            {'guest_name': 'Claire Beaumont', 'guest_email': 'claire.b@gmail.com', 'entry_type': EntryType.VIP, 'plus_ones': 1, 'status': GuestlistStatus.APPROVED},
            {'guest_name': 'Marc Duval', 'guest_email': 'marc.d@hotmail.fr', 'entry_type': EntryType.GUEST, 'plus_ones': 1, 'status': GuestlistStatus.PENDING},
            {'guest_name': 'Emma Laurent', 'guest_email': 'emma.l@gmail.com', 'entry_type': EntryType.GUEST, 'plus_ones': 0, 'status': GuestlistStatus.PENDING},
            {'guest_name': 'Fabien Roche', 'guest_email': 'fab.roche@rtl2.fr', 'company': 'RTL2', 'entry_type': EntryType.PRESS, 'plus_ones': 1, 'status': GuestlistStatus.PENDING},
            {'guest_name': 'DJ Snake', 'guest_email': 'contact@djsnake.fr', 'entry_type': EntryType.ARTIST, 'plus_ones': 2, 'status': GuestlistStatus.APPROVED},
        ]
        for gl in gl_entries_olympia:
            existing = GuestlistEntry.query.filter_by(
                tour_stop_id=olympia_stop.id, guest_name=gl['guest_name']
            ).first()
            if not existing:
                entry = GuestlistEntry(
                    tour_stop_id=olympia_stop.id,
                    requested_by_id=admin.id,
                    **gl
                )
                if gl['status'] == GuestlistStatus.APPROVED:
                    entry.approved_by_id = admin.id
                    entry.approved_at = datetime.utcnow()
                db.session.add(entry)
                gl_count += 1

    # Bikini (opening night)
    bikini_stop = created_stops.get('2026-03-15')
    if bikini_stop:
        gl_entries_bikini = [
            {'guest_name': 'Thomas Lefèvre', 'guest_email': 'thomas@detours-prod.fr', 'company': 'Détours Productions', 'entry_type': EntryType.INDUSTRY, 'plus_ones': 1, 'status': GuestlistStatus.APPROVED},
            {'guest_name': 'Nina Ramos', 'guest_email': 'nina.ramos@tnt.fr', 'company': 'France Télévisions', 'entry_type': EntryType.PRESS, 'plus_ones': 0, 'status': GuestlistStatus.APPROVED},
            {'guest_name': 'Pierre Martin', 'guest_email': 'pierrem@free.fr', 'entry_type': EntryType.GUEST, 'plus_ones': 2, 'status': GuestlistStatus.APPROVED},
            {'guest_name': 'Famille Porcel', 'guest_email': 'famille@porcel.fr', 'entry_type': EntryType.VIP, 'plus_ones': 4, 'status': GuestlistStatus.APPROVED},
        ]
        for gl in gl_entries_bikini:
            existing = GuestlistEntry.query.filter_by(
                tour_stop_id=bikini_stop.id, guest_name=gl['guest_name']
            ).first()
            if not existing:
                entry = GuestlistEntry(
                    tour_stop_id=bikini_stop.id,
                    requested_by_id=admin.id,
                    **gl
                )
                if gl['status'] == GuestlistStatus.APPROVED:
                    entry.approved_by_id = admin.id
                    entry.approved_at = datetime.utcnow()
                db.session.add(entry)
                gl_count += 1

    # Lyon (Transbordeur)
    lyon_stop = created_stops.get('2026-04-02')
    if lyon_stop:
        gl_entries_lyon = [
            {'guest_name': 'Hugo Fernandez', 'guest_email': 'hugo@petit-bulletin.fr', 'company': 'Le Petit Bulletin', 'entry_type': EntryType.PRESS, 'plus_ones': 0, 'status': GuestlistStatus.APPROVED},
            {'guest_name': 'Mélanie Blanc', 'guest_email': 'melanie.b@sfrmail.fr', 'entry_type': EntryType.GUEST, 'plus_ones': 1, 'status': GuestlistStatus.PENDING},
        ]
        for gl in gl_entries_lyon:
            existing = GuestlistEntry.query.filter_by(
                tour_stop_id=lyon_stop.id, guest_name=gl['guest_name']
            ).first()
            if not existing:
                entry = GuestlistEntry(
                    tour_stop_id=lyon_stop.id,
                    requested_by_id=sophie.id if sophie else admin.id,
                    **gl
                )
                if gl['status'] == GuestlistStatus.APPROVED:
                    entry.approved_by_id = admin.id
                    entry.approved_at = datetime.utcnow()
                db.session.add(entry)
                gl_count += 1

    db.session.flush()
    results['guestlist_entries'] = gl_count

    # ================================================================
    # 8. LOGISTICS — hotels and transport for each stop
    # ================================================================
    logi_count = 0

    logistics_data = [
        # Bikini (Toulouse) — 15 mars
        {
            'stop_date': '2026-03-15',
            'items': [
                {
                    'logistics_type': LogisticsType.HOTEL,
                    'provider': 'Hôtel Mercure Toulouse Centre',
                    'confirmation_number': 'MER-TLS-2603',
                    'start_datetime': datetime(2026, 3, 15, 15, 0),
                    'end_datetime': datetime(2026, 3, 16, 11, 0),
                    'address': '13 Rue Saint-Jérôme', 'city': 'Toulouse', 'country': 'France',
                    'latitude': Decimal('43.6047'), 'longitude': Decimal('1.4442'),
                    'status': LogisticsStatus.CONFIRMED,
                    'cost': Decimal('890.00'), 'is_paid': True, 'paid_by': 'Production',
                    'number_of_rooms': 5, 'breakfast_included': True,
                    'check_in_time': time(15, 0), 'check_out_time': time(11, 0),
                    'notes': '5 chambres twin. Parking bus inclus.',
                },
            ]
        },
        # Stereolux (Nantes) — 18 mars
        {
            'stop_date': '2026-03-18',
            'items': [
                {
                    'logistics_type': LogisticsType.TRAIN,
                    'provider': 'SNCF',
                    'confirmation_number': 'TGV-8834-TLSNTS',
                    'start_datetime': datetime(2026, 3, 17, 8, 0),
                    'end_datetime': datetime(2026, 3, 17, 14, 30),
                    'status': LogisticsStatus.BOOKED,
                    'cost': Decimal('1260.00'), 'is_paid': True, 'paid_by': 'Production',
                    'notes': '7 billets Toulouse-Nantes via Paris (correspondance Montparnasse). 2nde classe.',
                },
                {
                    'logistics_type': LogisticsType.HOTEL,
                    'provider': 'Hôtel Amiral',
                    'confirmation_number': 'ADM-NTS-1803',
                    'start_datetime': datetime(2026, 3, 17, 15, 0),
                    'end_datetime': datetime(2026, 3, 19, 11, 0),
                    'address': '26 Rue Scribe', 'city': 'Nantes', 'country': 'France',
                    'latitude': Decimal('47.2173'), 'longitude': Decimal('-1.5534'),
                    'status': LogisticsStatus.CONFIRMED,
                    'cost': Decimal('1380.00'), 'is_paid': False,
                    'number_of_rooms': 5, 'breakfast_included': True,
                    'check_in_time': time(15, 0), 'check_out_time': time(11, 0),
                    'notes': '2 nuits (arrivée veille). 5 chambres single.',
                },
            ]
        },
        # Aéronef (Lille) — 21 mars
        {
            'stop_date': '2026-03-21',
            'items': [
                {
                    'logistics_type': LogisticsType.BUS,
                    'provider': 'Eurolines / Artiste Transport',
                    'confirmation_number': 'BUS-NTS-LIL-21',
                    'start_datetime': datetime(2026, 3, 20, 8, 0),
                    'end_datetime': datetime(2026, 3, 20, 16, 0),
                    'status': LogisticsStatus.CONFIRMED,
                    'cost': Decimal('1800.00'), 'is_paid': False,
                    'notes': 'Bus 16 places Nantes → Lille. Départ 8h, arrivée estimée 16h. Pause autoroute.',
                    'vehicle_type': 'Sprinter 16 places',
                    'driver_name': 'Michel Dupré',
                    'driver_phone': '+33 6 12 34 56 78',
                },
                {
                    'logistics_type': LogisticsType.HOTEL,
                    'provider': 'Hôtel Mercure Lille Centre Grand-Place',
                    'confirmation_number': 'MER-LIL-2103',
                    'start_datetime': datetime(2026, 3, 20, 15, 0),
                    'end_datetime': datetime(2026, 3, 22, 11, 0),
                    'address': '2 Boulevard Carnot', 'city': 'Lille', 'country': 'France',
                    'latitude': Decimal('50.6366'), 'longitude': Decimal('3.0705'),
                    'status': LogisticsStatus.CONFIRMED,
                    'cost': Decimal('1150.00'), 'is_paid': False,
                    'number_of_rooms': 5, 'breakfast_included': True,
                    'check_in_time': time(15, 0), 'check_out_time': time(11, 0),
                    'notes': '2 nuits (arrivée veille). Centre-ville.',
                },
            ]
        },
        # Lyon (Transbordeur) — 2 avril
        {
            'stop_date': '2026-04-02',
            'items': [
                {
                    'logistics_type': LogisticsType.TRAIN,
                    'provider': 'SNCF',
                    'confirmation_number': 'TGV-9212-PAR-LYO',
                    'start_datetime': datetime(2026, 4, 1, 10, 0),
                    'end_datetime': datetime(2026, 4, 1, 12, 0),
                    'status': LogisticsStatus.BOOKED,
                    'cost': Decimal('840.00'), 'is_paid': False,
                    'notes': '7 billets Paris-Lyon Part-Dieu. 2h TGV. 2nde classe.',
                },
                {
                    'logistics_type': LogisticsType.HOTEL,
                    'provider': 'Hôtel Globe et Cécil',
                    'confirmation_number': 'GEC-LYO-0204',
                    'start_datetime': datetime(2026, 4, 1, 14, 0),
                    'end_datetime': datetime(2026, 4, 3, 11, 0),
                    'address': '21 Rue Gasparin', 'city': 'Lyon', 'country': 'France',
                    'latitude': Decimal('45.7580'), 'longitude': Decimal('4.8340'),
                    'status': LogisticsStatus.CONFIRMED,
                    'cost': Decimal('1450.00'), 'is_paid': False,
                    'number_of_rooms': 5, 'breakfast_included': True,
                    'check_in_time': time(14, 0), 'check_out_time': time(11, 0),
                    'notes': '2 nuits. Presqu\'île centre, 15 min à pied du Transbordeur.',
                },
                {
                    'logistics_type': LogisticsType.BACKLINE,
                    'provider': 'Music & Son Lyon',
                    'confirmation_number': 'MSL-BACK-0204',
                    'start_datetime': datetime(2026, 4, 2, 12, 0),
                    'end_datetime': datetime(2026, 4, 2, 23, 30),
                    'status': LogisticsStatus.PENDING,
                    'cost': Decimal('650.00'),
                    'notes': 'Backline additionnel pour captation : amplis Fender Twin + Marshall JCM800, batterie Gretsch.',
                },
            ]
        },
        # Olympia (Paris) — 12 avril
        {
            'stop_date': '2026-04-12',
            'items': [
                {
                    'logistics_type': LogisticsType.HOTEL,
                    'provider': 'Hôtel Edouard VII',
                    'confirmation_number': 'EDW-PAR-1204',
                    'start_datetime': datetime(2026, 4, 11, 14, 0),
                    'end_datetime': datetime(2026, 4, 13, 12, 0),
                    'address': '39 Avenue de l\'Opéra', 'city': 'Paris', 'country': 'France',
                    'latitude': Decimal('48.8694'), 'longitude': Decimal('2.3341'),
                    'status': LogisticsStatus.CONFIRMED,
                    'cost': Decimal('2800.00'), 'is_paid': True, 'paid_by': 'Label',
                    'number_of_rooms': 7, 'breakfast_included': True,
                    'check_in_time': time(14, 0), 'check_out_time': time(12, 0),
                    'notes': '2 nuits. 7 chambres (équipe élargie pour Olympia). À 200m de la salle.',
                },
                {
                    'logistics_type': LogisticsType.CATERING,
                    'provider': 'Le Traiteur du Spectacle',
                    'confirmation_number': 'CAT-OLY-1204',
                    'start_datetime': datetime(2026, 4, 12, 12, 0),
                    'end_datetime': datetime(2026, 4, 12, 22, 0),
                    'status': LogisticsStatus.CONFIRMED,
                    'cost': Decimal('1200.00'), 'is_paid': False,
                    'notes': 'Déjeuner crew (12h) + dîner artistes (17h30). Menu bio/local. 15 personnes. Rider spécifique validé.',
                },
            ]
        },
    ]

    for logi_group in logistics_data:
        stop = created_stops.get(logi_group['stop_date'])
        if not stop:
            continue
        for item in logi_group['items']:
            existing = LogisticsInfo.query.filter_by(
                tour_stop_id=stop.id,
                logistics_type=item['logistics_type'],
                provider=item.get('provider', '')
            ).first()
            if not existing:
                logi = LogisticsInfo(tour_stop_id=stop.id, **item)
                db.session.add(logi)
                logi_count += 1

    db.session.flush()
    results['logistics'] = logi_count

    # ================================================================
    # 9. PAYMENTS — cachets for key stops
    # ================================================================
    pay_count = 0

    # Payment for Bikini (opening night) — musician cachets
    bikini_stop = created_stops.get('2026-03-15')
    if bikini_stop and julie and antoine:
        payments_data = [
            {
                'user': julie,
                'staff_category': StaffCategory.ARTISTIC,
                'staff_role': StaffRole.MUSICIAN,
                'payment_type': PaymentType.CACHET,
                'amount': Decimal('300.00'),
                'unit_rate': Decimal('300.00'),
                'quantity': 1,
                'contract_type': ContractType.CDDU,
                'status': PaymentStatus.APPROVED,
            },
            {
                'user': antoine,
                'staff_category': StaffCategory.ARTISTIC,
                'staff_role': StaffRole.MUSICIAN,
                'payment_type': PaymentType.CACHET,
                'amount': Decimal('300.00'),
                'unit_rate': Decimal('300.00'),
                'quantity': 1,
                'contract_type': ContractType.CDDU,
                'status': PaymentStatus.APPROVED,
            },
            {
                'user': lucas,
                'staff_category': StaffCategory.TECHNICAL,
                'staff_role': StaffRole.FOH_ENGINEER,
                'payment_type': PaymentType.CACHET,
                'amount': Decimal('350.00'),
                'unit_rate': Decimal('350.00'),
                'quantity': 1,
                'contract_type': ContractType.CDDU,
                'status': PaymentStatus.APPROVED,
            },
            {
                'user': marie,
                'staff_category': StaffCategory.TECHNICAL,
                'staff_role': StaffRole.LIGHTING_DIRECTOR,
                'payment_type': PaymentType.CACHET,
                'amount': Decimal('350.00'),
                'unit_rate': Decimal('350.00'),
                'quantity': 1,
                'contract_type': ContractType.CDDU,
                'status': PaymentStatus.APPROVED,
            },
        ]

        for p_data in payments_data:
            user = p_data.pop('user')
            existing = TeamMemberPayment.query.filter_by(
                user_id=user.id,
                tour_stop_id=bikini_stop.id,
                payment_type=p_data['payment_type']
            ).first()
            if not existing:
                payment = TeamMemberPayment(
                    user_id=user.id,
                    tour_id=tour.id,
                    tour_stop_id=bikini_stop.id,
                    work_date=bikini_stop.date,
                    currency='EUR',
                    payment_frequency=PaymentFrequency.PER_SHOW,
                    submitted_by_id=admin.id,
                    submitted_at=datetime.utcnow(),
                    approved_by_id=admin.id,
                    approved_at=datetime.utcnow(),
                    **p_data
                )
                payment.reference = payment.generate_reference()
                db.session.add(payment)
                pay_count += 1

    # Per diem for Bikini
    if bikini_stop:
        for crew_member in [lucas, marie, thomas, camille]:
            if not crew_member:
                continue
            existing = TeamMemberPayment.query.filter_by(
                user_id=crew_member.id,
                tour_stop_id=bikini_stop.id,
                payment_type=PaymentType.PER_DIEM
            ).first()
            if not existing:
                pd = TeamMemberPayment(
                    user_id=crew_member.id,
                    tour_id=tour.id,
                    tour_stop_id=bikini_stop.id,
                    staff_category=StaffCategory.TECHNICAL,
                    staff_role=StaffRole.STAGEHAND,
                    payment_type=PaymentType.PER_DIEM,
                    amount=Decimal('35.00'),
                    unit_rate=Decimal('35.00'),
                    quantity=1,
                    currency='EUR',
                    work_date=bikini_stop.date,
                    payment_frequency=PaymentFrequency.DAILY,
                    contract_type=ContractType.CDDU,
                    status=PaymentStatus.PENDING_APPROVAL,
                    submitted_by_id=sophie.id if sophie else admin.id,
                    submitted_at=datetime.utcnow(),
                )
                pd.reference = pd.generate_reference()
                db.session.add(pd)
                pay_count += 1

    db.session.flush()
    results['payments'] = pay_count

    # ================================================================
    # 10. NOTIFICATIONS
    # ================================================================
    notif_count = 0
    notifs = [
        {
            'user_id': admin.id,
            'type': NotificationType.SUCCESS,
            'category': NotificationCategory.TOUR,
            'title': 'Tournée confirmée',
            'message': 'La Tournée Orbite 2026 a été confirmée avec 8 dates.',
            'link': '/tours',
        },
        {
            'user_id': admin.id,
            'type': NotificationType.INFO,
            'category': NotificationCategory.GUESTLIST,
            'title': 'Nouvelles demandes guestlist',
            'message': "3 nouvelles demandes en attente pour L'Olympia (12/04).",
            'link': '/guestlist',
        },
        {
            'user_id': admin.id,
            'type': NotificationType.WARNING,
            'category': NotificationCategory.TOUR,
            'title': 'Date non confirmée',
            'message': 'La Cigale (08/04) est toujours en brouillon. Confirmation nécessaire.',
        },
    ]
    if sophie:
        notifs.append({
            'user_id': sophie.id,
            'type': NotificationType.INFO,
            'category': NotificationCategory.TOUR,
            'title': 'Assignation crew',
            'message': 'Vous avez été assignée comme Tour Manager sur la Tournée Orbite 2026.',
            'link': '/tours',
        })
    if lucas:
        notifs.append({
            'user_id': lucas.id,
            'type': NotificationType.INFO,
            'category': NotificationCategory.TOUR,
            'title': 'Assignation technique',
            'message': 'Vous êtes assigné comme ingénieur son façade sur 6 dates de la Tournée Orbite.',
            'link': '/tours',
        })

    for n_data in notifs:
        n = Notification(**n_data)
        db.session.add(n)
        notif_count += 1

    results['notifications'] = notif_count

    # ================================================================
    # COMMIT
    # ================================================================
    db.session.commit()

    results['status'] = 'success'
    return results
