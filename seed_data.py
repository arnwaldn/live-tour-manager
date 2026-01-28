#!/usr/bin/env python3
"""
Tour Manager - Seed Data Script
Creates demo data for development and testing.

Usage:
    python seed_data.py          # Create all demo data
    python seed_data.py --clean  # Clean and recreate all data
"""

import sys
import os
from datetime import datetime, date, time, timedelta
from decimal import Decimal

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import (
    User, Role, Band, BandMembership, Venue, VenueContact,
    Tour, TourStop, GuestlistEntry, LogisticsInfo, LocalContact
)
from app.models.tour import TourStatus
from app.models.tour_stop import TourStopStatus
from app.models.guestlist import GuestlistStatus, EntryType
from app.models.logistics import LogisticsType


# =============================================================================
# Role Definitions with Permissions
# =============================================================================

ROLES_DATA = [
    {
        'name': 'MANAGER',
        'description': 'Tour/Band Manager - Full access',
        'permissions': [
            'manage_band', 'manage_tour', 'manage_guestlist', 'manage_logistics',
            'view_tour', 'view_show', 'request_guestlist', 'check_in_guests',
            'export_guestlist', 'manage_users', 'view_financials'
        ]
    },
    {
        'name': 'MUSICIAN',
        'description': 'Band Member - View tours and request guests',
        'permissions': [
            'view_tour', 'view_show', 'request_guestlist'
        ]
    },
    {
        'name': 'TECH',
        'description': 'Technical Crew - View shows and logistics',
        'permissions': [
            'view_tour', 'view_show', 'view_logistics'
        ]
    },
    {
        'name': 'PROMOTER',
        'description': 'Local Promoter - View show and check-in guests',
        'permissions': [
            'view_show', 'check_in_guests', 'view_guestlist'
        ]
    },
    {
        'name': 'VENUE_CONTACT',
        'description': 'Venue Staff - View show and check-in guests',
        'permissions': [
            'view_show', 'check_in_guests', 'view_guestlist'
        ]
    },
    {
        'name': 'GUESTLIST_MANAGER',
        'description': 'Guestlist Manager - Manage guestlist and check-in',
        'permissions': [
            'manage_guestlist', 'view_show', 'check_in_guests',
            'export_guestlist', 'view_guestlist'
        ]
    }
]


# =============================================================================
# User Data
# =============================================================================

USERS_DATA = [
    {
        'email': 'manager@tourmanager.com',
        'password': 'Manager123!',
        'first_name': 'Sophie',
        'last_name': 'Martin',
        'phone': '+33 6 12 34 56 78',
        'roles': ['MANAGER']
    },
    {
        'email': 'lead@cosmictravelers.com',
        'password': 'Lead123!',
        'first_name': 'Lucas',
        'last_name': 'Dubois',
        'phone': '+33 6 23 45 67 89',
        'roles': ['MUSICIAN']
    },
    {
        'email': 'drums@cosmictravelers.com',
        'password': 'Drums123!',
        'first_name': 'Emma',
        'last_name': 'Bernard',
        'phone': '+33 6 34 56 78 90',
        'roles': ['MUSICIAN']
    },
    {
        'email': 'tech@tourmanager.com',
        'password': 'Tech123!',
        'first_name': 'Thomas',
        'last_name': 'Petit',
        'phone': '+33 6 45 67 89 01',
        'roles': ['TECH']
    },
    {
        'email': 'promoter@concerts.de',
        'password': 'Promoter123!',
        'first_name': 'Hans',
        'last_name': 'Mueller',
        'phone': '+49 151 234 5678',
        'roles': ['PROMOTER']
    },
    {
        'email': 'guestlist@tourmanager.com',
        'password': 'Guest123!',
        'first_name': 'Marie',
        'last_name': 'Leroy',
        'phone': '+33 6 56 78 90 12',
        'roles': ['GUESTLIST_MANAGER']
    }
]


# =============================================================================
# Band Data
# =============================================================================

BAND_DATA = {
    'name': 'The Cosmic Travelers',
    'genre': 'Indie Rock / Electro',
    'bio': """The Cosmic Travelers est un groupe franco-belge formé en 2019 à Paris.
Leur son mélange rock indépendant, électronique et influences world music.
Après deux albums acclamés par la critique, ils se lancent dans leur première tournée européenne.""",
    # 'logo_url': 'https://example.com/cosmic-travelers-logo.png',  # Removed - broken placeholder
    'website': 'https://cosmictravelers.com',
    'social_links': {
        'instagram': '@cosmictravelers',
        'twitter': '@cosmic_travelers',
        'spotify': 'cosmictravelers',
        'youtube': 'TheCosmicTravelers'
    },
    'members': [
        {'instrument': 'Vocals, Guitar', 'role_in_band': 'Lead Singer'},
        {'instrument': 'Drums, Percussion', 'role_in_band': 'Drummer'}
    ]
}


# =============================================================================
# Venue Data
# =============================================================================

VENUES_DATA = [
    {
        'name': 'Le Bataclan',
        'address': '50 Boulevard Voltaire',
        'city': 'Paris',
        'state': 'Île-de-France',
        'country': 'France',
        'postal_code': '75011',
        'capacity': 1500,
        'venue_type': 'Concert Hall',
        'website': 'https://www.bataclan.fr',
        'stage_dimensions': '12m x 8m',
        'load_in_info': 'Accès par la rue Amelot. Quai de déchargement disponible.',
        'backline_available': True,
        'contacts': [
            {'name': 'Jean-Pierre Moreau', 'role': 'Production Manager',
             'email': 'jp.moreau@bataclan.fr', 'phone': '+33 1 43 14 00 30', 'is_primary': True},
            {'name': 'Claire Fontaine', 'role': 'Booking',
             'email': 'booking@bataclan.fr', 'phone': '+33 1 43 14 00 31', 'is_primary': False}
        ]
    },
    {
        'name': 'SO36',
        'address': 'Oranienstraße 190',
        'city': 'Berlin',
        'state': 'Berlin',
        'country': 'Germany',
        'postal_code': '10999',
        'capacity': 1000,
        'venue_type': 'Club',
        'website': 'https://www.so36.com',
        'stage_dimensions': '10m x 6m',
        'load_in_info': 'Load-in through back entrance on Skalitzer Str.',
        'backline_available': True,
        'contacts': [
            {'name': 'Klaus Weber', 'role': 'Venue Manager',
             'email': 'klaus@so36.com', 'phone': '+49 30 614 0306', 'is_primary': True}
        ]
    },
    {
        'name': 'Paradiso',
        'address': 'Weteringschans 6-8',
        'city': 'Amsterdam',
        'state': 'Noord-Holland',
        'country': 'Netherlands',
        'postal_code': '1017 SG',
        'capacity': 1500,
        'venue_type': 'Concert Hall',
        'website': 'https://www.paradiso.nl',
        'stage_dimensions': '14m x 10m',
        'load_in_info': 'Load-in via Weteringschans. Elevator available.',
        'backline_available': True,
        'contacts': [
            {'name': 'Pieter van der Berg', 'role': 'Production',
             'email': 'production@paradiso.nl', 'phone': '+31 20 626 4521', 'is_primary': True}
        ]
    },
    {
        'name': 'Electric Brixton',
        'address': '1 Town Hall Parade',
        'city': 'London',
        'state': 'Greater London',
        'country': 'United Kingdom',
        'postal_code': 'SW2 1RJ',
        'capacity': 3000,
        'venue_type': 'Concert Hall',
        'website': 'https://www.electricbrixton.uk.com',
        'stage_dimensions': '15m x 12m',
        'load_in_info': 'Loading bay on Brixton Road. Advance notice required.',
        'backline_available': False,
        'contacts': [
            {'name': 'James Smith', 'role': 'Production Manager',
             'email': 'james@electricbrixton.uk.com', 'phone': '+44 20 7274 2290', 'is_primary': True}
        ]
    }
]


# =============================================================================
# Tour Data
# =============================================================================

TOUR_DATA = {
    'name': 'European Winter Tour 2026',
    'description': """Première grande tournée européenne des Cosmic Travelers.
4 dates dans les plus grandes capitales européennes pour présenter leur nouvel album "Stellar Dreams".
Production complète avec light show et visuels synchronisés.""",
    'start_date': date(2026, 1, 15),
    'end_date': date(2026, 1, 30),
    'status': TourStatus.CONFIRMED,
    'budget': Decimal('50000.00'),
    'currency': 'EUR'
}


# =============================================================================
# Tour Stops Data
# =============================================================================

TOUR_STOPS_DATA = [
    {
        'venue_city': 'Paris',
        'date': date(2026, 1, 15),
        # Horaires complets (10 champs)
        'load_in_time': time(10, 0),
        'crew_call_time': time(11, 0),
        'artist_call_time': time(14, 0),
        'press_time': time(15, 0),
        'soundcheck_time': time(16, 0),
        'catering_time': time(17, 30),
        'meet_greet_time': time(18, 30),
        'doors_time': time(19, 0),
        'set_time': time(21, 0),
        'curfew_time': time(23, 30),
        'status': TourStopStatus.CONFIRMED,
        'guarantee': Decimal('5000.00'),
        'door_deal_percentage': Decimal('80.00'),
        'ticket_price': Decimal('25.00'),
        'capacity_sold': 1200,
        'notes': 'Release party pour le nouvel album. Presse invitée.',
        'local_contacts': [
            {'name': 'Julien Blanc', 'role': 'Local Promoter Rep',
             'phone': '+33 6 78 90 12 34', 'is_primary': True}
        ]
    },
    {
        'venue_city': 'Berlin',
        'date': date(2026, 1, 20),
        # Horaires complets (10 champs)
        'load_in_time': time(12, 0),
        'crew_call_time': time(13, 0),
        'artist_call_time': time(15, 0),
        'press_time': time(16, 0),
        'soundcheck_time': time(17, 0),
        'catering_time': time(18, 30),
        'meet_greet_time': time(19, 30),
        'doors_time': time(20, 0),
        'set_time': time(22, 0),
        'curfew_time': time(2, 0),
        'status': TourStopStatus.CONFIRMED,
        'guarantee': Decimal('4000.00'),
        'door_deal_percentage': Decimal('75.00'),
        'ticket_price': Decimal('20.00'),
        'capacity_sold': 800,
        'notes': 'After-party prévue au club.',
        'local_contacts': [
            {'name': 'Anna Schmidt', 'role': 'Runner',
             'phone': '+49 176 123 4567', 'is_primary': True}
        ]
    },
    {
        'venue_city': 'Amsterdam',
        'date': date(2026, 1, 25),
        # Horaires complets (10 champs)
        'load_in_time': time(9, 30),
        'crew_call_time': time(10, 30),
        'artist_call_time': time(13, 30),
        'press_time': time(14, 30),
        'soundcheck_time': time(15, 30),
        'catering_time': time(17, 0),
        'meet_greet_time': time(19, 0),
        'doors_time': time(19, 30),
        'set_time': time(21, 30),
        'curfew_time': time(23, 0),
        'status': TourStopStatus.DRAFT,
        'guarantee': Decimal('4500.00'),
        'door_deal_percentage': Decimal('70.00'),
        'ticket_price': Decimal('22.50'),
        'capacity_sold': 600,
        'notes': 'En attente confirmation finale du promoteur.',
        'local_contacts': []
    },
    {
        'venue_city': 'London',
        'date': date(2026, 1, 30),
        # Horaires complets (10 champs)
        'load_in_time': time(8, 0),
        'crew_call_time': time(9, 0),
        'artist_call_time': time(12, 0),
        'press_time': time(13, 0),
        'soundcheck_time': time(14, 0),
        'catering_time': time(16, 0),
        'meet_greet_time': time(18, 0),
        'doors_time': time(19, 0),
        'set_time': time(20, 30),
        'curfew_time': time(23, 0),
        'status': TourStopStatus.CONFIRMED,
        'guarantee': Decimal('6000.00'),
        'door_deal_percentage': Decimal('85.00'),
        'ticket_price': Decimal('30.00'),
        'capacity_sold': 2500,
        'notes': 'Dernière date de la tournée. Invités spéciaux possibles.',
        'local_contacts': [
            {'name': 'Sarah Johnson', 'role': 'Tour Rep UK',
             'phone': '+44 7700 900123', 'is_primary': True}
        ]
    }
]


# =============================================================================
# Guestlist Data
# =============================================================================

def get_guestlist_data(tour_stops, users):
    """Generate guestlist entries for tour stops."""
    manager = next(u for u in users if u.email == 'manager@tourmanager.com')
    musician1 = next(u for u in users if u.email == 'lead@cosmictravelers.com')
    musician2 = next(u for u in users if u.email == 'drums@cosmictravelers.com')
    guestlist_mgr = next(u for u in users if u.email == 'guestlist@tourmanager.com')

    # Paris stop guestlist
    paris_stop = next(s for s in tour_stops if s.venue.city == 'Paris')
    # Berlin stop guestlist
    berlin_stop = next(s for s in tour_stops if s.venue.city == 'Berlin')
    # London stop guestlist
    london_stop = next(s for s in tour_stops if s.venue.city == 'London')

    return [
        # Paris - Mix of statuses
        {
            'tour_stop': paris_stop,
            'guest_name': 'Antoine Dupont',
            'guest_email': 'antoine.dupont@email.fr',
            'entry_type': EntryType.PRESS,
            'plus_ones': 1,
            'status': GuestlistStatus.APPROVED,
            'requested_by': musician1,
            'approved_by': manager,
            'notes': 'Journaliste Les Inrocks - Interview confirmée'
        },
        {
            'tour_stop': paris_stop,
            'guest_name': 'Camille Laurent',
            'guest_email': 'camille@recordlabel.com',
            'entry_type': EntryType.INDUSTRY,
            'plus_ones': 2,
            'status': GuestlistStatus.APPROVED,
            'requested_by': manager,
            'approved_by': manager,
            'notes': 'A&R Universal Music'
        },
        {
            'tour_stop': paris_stop,
            'guest_name': 'Marc Lefebvre',
            'guest_email': 'marc.lef@gmail.com',
            'entry_type': EntryType.GUEST,
            'plus_ones': 1,
            'status': GuestlistStatus.PENDING,
            'requested_by': musician2,
            'approved_by': None,
            'notes': 'Ami de Emma'
        },

        # Berlin
        {
            'tour_stop': berlin_stop,
            'guest_name': 'Lisa Braun',
            'guest_email': 'lisa.braun@musikexpress.de',
            'entry_type': EntryType.PRESS,
            'plus_ones': 0,
            'status': GuestlistStatus.APPROVED,
            'requested_by': manager,
            'approved_by': guestlist_mgr,
            'notes': 'Photographe Musikexpress'
        },
        {
            'tour_stop': berlin_stop,
            'guest_name': 'Fritz Hoffmann',
            'guest_email': 'fritz@email.de',
            'entry_type': EntryType.VIP,
            'plus_ones': 3,
            'status': GuestlistStatus.CHECKED_IN,
            'requested_by': manager,
            'approved_by': manager,
            'notes': 'Sponsor principal',
            'checked_in_at': datetime(2025, 6, 20, 20, 15)
        },

        # London
        {
            'tour_stop': london_stop,
            'guest_name': 'Oliver Williams',
            'guest_email': 'oliver@bbc.co.uk',
            'entry_type': EntryType.PRESS,
            'plus_ones': 1,
            'status': GuestlistStatus.APPROVED,
            'requested_by': manager,
            'approved_by': manager,
            'notes': 'BBC Radio 6 - Interview backstage'
        },
        {
            'tour_stop': london_stop,
            'guest_name': 'Emily Brown',
            'guest_email': 'emily.b@gmail.com',
            'entry_type': EntryType.GUEST,
            'plus_ones': 0,
            'status': GuestlistStatus.DENIED,
            'requested_by': musician1,
            'approved_by': guestlist_mgr,
            'notes': 'Capacité atteinte - refusé'
        },
        {
            'tour_stop': london_stop,
            'guest_name': 'David Thompson',
            'guest_email': 'david.t@agency.uk',
            'entry_type': EntryType.INDUSTRY,
            'plus_ones': 2,
            'status': GuestlistStatus.PENDING,
            'requested_by': manager,
            'approved_by': None,
            'notes': 'Booking agent - CAA'
        }
    ]


# =============================================================================
# Logistics Data
# =============================================================================

def get_logistics_data(tour_stops):
    """Generate logistics entries for tour stops."""
    paris_stop = next(s for s in tour_stops if s.venue.city == 'Paris')
    berlin_stop = next(s for s in tour_stops if s.venue.city == 'Berlin')
    amsterdam_stop = next(s for s in tour_stops if s.venue.city == 'Amsterdam')
    london_stop = next(s for s in tour_stops if s.venue.city == 'London')

    return [
        # Paris - Hotel
        {
            'tour_stop': paris_stop,
            'logistics_type': LogisticsType.HOTEL,
            'provider': 'Hôtel Le Marais',
            'confirmation_number': 'HLM-2025-0615',
            'cost': Decimal('450.00'),
            'currency': 'EUR',
            'start_datetime': datetime(2025, 6, 14, 15, 0),
            'end_datetime': datetime(2025, 6, 16, 11, 0),
            'details': {
                'address': '15 Rue de Turenne, 75003 Paris',
                'phone': '+33 1 42 72 00 00'
            },
            'room_type': 'Double',
            'number_of_rooms': 3,
            'breakfast_included': True,
            'notes': '3 chambres doubles avec petit-déjeuner. Check-in à partir de 15h.'
        },

        # Paris to Berlin - Train
        {
            'tour_stop': berlin_stop,
            'logistics_type': LogisticsType.TRAIN,
            'provider': 'Deutsche Bahn / SNCF',
            'confirmation_number': 'DB-FR-98765',
            'cost': Decimal('890.00'),
            'currency': 'EUR',
            'start_datetime': datetime(2025, 6, 17, 8, 30),
            'end_datetime': datetime(2025, 6, 17, 17, 45),
            'details': {
                'departure_station': 'Paris Gare de l\'Est',
                'arrival_station': 'Berlin Hauptbahnhof',
                'train_number': 'ICE 557',
                'coach': '12',
                'seats': '45-50'
            },
            'notes': '6 places en 1ère classe. Changement à Frankfurt.'
        },

        # Berlin - Hotel
        {
            'tour_stop': berlin_stop,
            'logistics_type': LogisticsType.HOTEL,
            'provider': 'Hotel Michelberger',
            'confirmation_number': 'MIC-2025-0619',
            'cost': Decimal('520.00'),
            'currency': 'EUR',
            'start_datetime': datetime(2025, 6, 19, 14, 0),
            'end_datetime': datetime(2025, 6, 21, 12, 0),
            'details': {
                'address': 'Warschauer Str. 39-40, 10243 Berlin',
                'phone': '+49 30 2977 8590'
            },
            'room_type': 'Studio',
            'number_of_rooms': 3,
            'breakfast_included': False,
            'notes': '3 studios. Proche de la salle SO36. Petit-déjeuner en option (15€/pers).'
        },

        # Berlin to Amsterdam - Flight
        {
            'tour_stop': amsterdam_stop,
            'logistics_type': LogisticsType.FLIGHT,
            'provider': 'KLM',
            'confirmation_number': 'KL-COSMIC-2025',
            'cost': Decimal('680.00'),
            'currency': 'EUR',
            'start_datetime': datetime(2025, 6, 23, 10, 45),
            'end_datetime': datetime(2025, 6, 23, 12, 15),
            'details': {
                'booking_reference': 'ABC123'
            },
            'flight_number': 'KL1820',
            'departure_airport': 'BER',
            'arrival_airport': 'AMS',
            'notes': '6 billets. Bagages enregistrés inclus (23kg). Transfert aéroport inclus côté Amsterdam.'
        },

        # Amsterdam - Hotel
        {
            'tour_stop': amsterdam_stop,
            'logistics_type': LogisticsType.HOTEL,
            'provider': 'Hotel V Nesplein',
            'confirmation_number': 'HVN-2025-0624',
            'cost': Decimal('580.00'),
            'currency': 'EUR',
            'start_datetime': datetime(2025, 6, 24, 15, 0),
            'end_datetime': datetime(2025, 6, 26, 11, 0),
            'details': {
                'address': 'Nes 49, 1012 KD Amsterdam',
                'phone': '+31 20 662 3233'
            },
            'room_type': 'Superior',
            'number_of_rooms': 3,
            'breakfast_included': True,
            'notes': 'À 5 minutes à pied du Paradiso. Parking vélos disponible.'
        },

        # Amsterdam to London - Flight
        {
            'tour_stop': london_stop,
            'logistics_type': LogisticsType.FLIGHT,
            'provider': 'British Airways',
            'confirmation_number': 'BA-COSMIC-LDN',
            'cost': Decimal('750.00'),
            'currency': 'GBP',
            'start_datetime': datetime(2025, 6, 28, 14, 20),
            'end_datetime': datetime(2025, 6, 28, 14, 50),
            'details': {
                'booking_reference': 'XYZ789'
            },
            'flight_number': 'BA435',
            'departure_airport': 'AMS',
            'arrival_airport': 'LHR',
            'notes': '6 billets. Terminal 5. Taxi pré-réservé pour le groupe.'
        }
    ]


# =============================================================================
# Seed Functions
# =============================================================================

def create_roles():
    """Create predefined roles with permissions."""
    print("Creating roles...")
    roles = {}
    for role_data in ROLES_DATA:
        role = Role.query.filter_by(name=role_data['name']).first()
        if not role:
            role = Role(
                name=role_data['name'],
                description=role_data['description'],
                permissions=role_data['permissions']
            )
            db.session.add(role)
        roles[role_data['name']] = role
    db.session.commit()
    print(f"  [OK] Created {len(roles)} roles")
    return roles


def create_users(roles):
    """Create demo users with assigned roles."""
    print("Creating users...")
    users = []
    for user_data in USERS_DATA:
        user = User.query.filter_by(email=user_data['email']).first()
        if not user:
            user = User(
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                phone=user_data['phone'],
                is_active=True
            )
            user.set_password(user_data['password'])

            for role_name in user_data['roles']:
                if role_name in roles:
                    user.roles.append(roles[role_name])

            db.session.add(user)
        users.append(user)
    db.session.commit()
    print(f"  [OK] Created {len(users)} users")
    return users


def create_band(users):
    """Create the demo band with members."""
    print("Creating band...")
    manager = next(u for u in users if u.email == 'manager@tourmanager.com')

    band = Band.query.filter_by(name=BAND_DATA['name']).first()
    if not band:
        band = Band(
            name=BAND_DATA['name'],
            genre=BAND_DATA['genre'],
            bio=BAND_DATA['bio'],
            logo_url=BAND_DATA.get('logo_url'),  # Optional - may be None
            website=BAND_DATA['website'],
            social_links=BAND_DATA['social_links'],
            manager_id=manager.id
        )
        db.session.add(band)
        db.session.commit()

        # Add band members
        musicians = [u for u in users if 'MUSICIAN' in [r.name for r in u.roles]]
        for i, musician in enumerate(musicians):
            if i < len(BAND_DATA['members']):
                member_data = BAND_DATA['members'][i]
                membership = BandMembership(
                    user_id=musician.id,
                    band_id=band.id,
                    instrument=member_data['instrument'],
                    role_in_band=member_data['role_in_band'],
                    is_active=True,
                    joined_at=datetime(2019, 1, 15)
                )
                db.session.add(membership)
        db.session.commit()

    print(f"  [OK] Created band: {band.name}")
    return band


def create_venues():
    """Create demo venues with contacts."""
    print("Creating venues...")
    venues = []
    for venue_data in VENUES_DATA:
        venue = Venue.query.filter_by(name=venue_data['name']).first()
        if not venue:
            venue = Venue(
                name=venue_data['name'],
                address=venue_data['address'],
                city=venue_data['city'],
                state=venue_data['state'],
                country=venue_data['country'],
                postal_code=venue_data['postal_code'],
                capacity=venue_data['capacity'],
                venue_type=venue_data['venue_type'],
                website=venue_data['website'],
                stage_dimensions=venue_data['stage_dimensions'],
                load_in_info=venue_data['load_in_info'],
                backline_available=venue_data['backline_available']
            )
            db.session.add(venue)
            db.session.commit()

            # Add venue contacts
            for contact_data in venue_data.get('contacts', []):
                contact = VenueContact(
                    venue_id=venue.id,
                    name=contact_data['name'],
                    role=contact_data['role'],
                    email=contact_data['email'],
                    phone=contact_data['phone'],
                    is_primary=contact_data['is_primary']
                )
                db.session.add(contact)
            db.session.commit()
        venues.append(venue)

    print(f"  [OK] Created {len(venues)} venues")
    return venues


def create_tour(band, venues):
    """Create demo tour with stops."""
    print("Creating tour...")

    tour = Tour.query.filter_by(name=TOUR_DATA['name']).first()
    if not tour:
        tour = Tour(
            name=TOUR_DATA['name'],
            description=TOUR_DATA['description'],
            band_id=band.id,
            start_date=TOUR_DATA['start_date'],
            end_date=TOUR_DATA['end_date'],
            status=TOUR_DATA['status'],
            budget=TOUR_DATA['budget'],
            currency=TOUR_DATA['currency']
        )
        db.session.add(tour)
        db.session.commit()

    print(f"  [OK] Created tour: {tour.name}")
    return tour


def create_tour_stops(tour, venues):
    """Create tour stops for each venue."""
    print("Creating tour stops...")
    tour_stops = []

    for stop_data in TOUR_STOPS_DATA:
        venue = next(v for v in venues if v.city == stop_data['venue_city'])

        existing = TourStop.query.filter_by(
            tour_id=tour.id,
            venue_id=venue.id,
            date=stop_data['date']
        ).first()

        if not existing:
            tour_stop = TourStop(
                tour_id=tour.id,
                venue_id=venue.id,
                date=stop_data['date'],
                # Tous les horaires (10 champs)
                load_in_time=stop_data.get('load_in_time'),
                crew_call_time=stop_data.get('crew_call_time'),
                artist_call_time=stop_data.get('artist_call_time'),
                press_time=stop_data.get('press_time'),
                soundcheck_time=stop_data['soundcheck_time'],
                catering_time=stop_data.get('catering_time'),
                meet_greet_time=stop_data.get('meet_greet_time'),
                doors_time=stop_data['doors_time'],
                set_time=stop_data['set_time'],
                curfew_time=stop_data['curfew_time'],
                status=stop_data['status'],
                guarantee=stop_data['guarantee'],
                door_deal_percentage=stop_data['door_deal_percentage'],
                ticket_price=stop_data['ticket_price'],
                sold_tickets=stop_data['capacity_sold'],
                notes=stop_data['notes']
            )
            db.session.add(tour_stop)
            db.session.commit()

            # Add local contacts
            for contact_data in stop_data.get('local_contacts', []):
                contact = LocalContact(
                    tour_stop_id=tour_stop.id,
                    name=contact_data['name'],
                    role=contact_data['role'],
                    phone=contact_data['phone'],
                    is_primary=contact_data['is_primary']
                )
                db.session.add(contact)
            db.session.commit()

            tour_stops.append(tour_stop)
        else:
            tour_stops.append(existing)

    print(f"  [OK] Created {len(tour_stops)} tour stops")
    return tour_stops


def create_guestlist_entries(tour_stops, users):
    """Create demo guestlist entries."""
    print("Creating guestlist entries...")
    entries = []
    guestlist_data = get_guestlist_data(tour_stops, users)

    for entry_data in guestlist_data:
        existing = GuestlistEntry.query.filter_by(
            tour_stop_id=entry_data['tour_stop'].id,
            guest_email=entry_data['guest_email']
        ).first()

        if not existing:
            entry = GuestlistEntry(
                tour_stop_id=entry_data['tour_stop'].id,
                guest_name=entry_data['guest_name'],
                guest_email=entry_data['guest_email'],
                entry_type=entry_data['entry_type'],
                plus_ones=entry_data['plus_ones'],
                status=entry_data['status'],
                requested_by_id=entry_data['requested_by'].id,
                approved_by_id=entry_data['approved_by'].id if entry_data['approved_by'] else None,
                notes=entry_data['notes']
            )

            # Set timestamps based on status
            if entry_data['status'] in [GuestlistStatus.APPROVED, GuestlistStatus.DENIED]:
                entry.approved_at = datetime.now() - timedelta(days=5)
            if entry_data['status'] == GuestlistStatus.CHECKED_IN:
                entry.checked_in_at = entry_data.get('checked_in_at', datetime.now())

            db.session.add(entry)
            entries.append(entry)

    db.session.commit()
    print(f"  [OK] Created {len(entries)} guestlist entries")
    return entries


def create_logistics(tour_stops):
    """Create logistics entries for tour stops."""
    print("Creating logistics...")
    logistics_list = []
    logistics_data = get_logistics_data(tour_stops)

    for log_data in logistics_data:
        existing = LogisticsInfo.query.filter_by(
            tour_stop_id=log_data['tour_stop'].id,
            confirmation_number=log_data['confirmation_number']
        ).first()

        if not existing:
            logistics = LogisticsInfo(
                tour_stop_id=log_data['tour_stop'].id,
                logistics_type=log_data['logistics_type'],
                provider=log_data['provider'],
                confirmation_number=log_data['confirmation_number'],
                cost=log_data['cost'],
                currency=log_data.get('currency', 'EUR'),
                start_datetime=log_data['start_datetime'],
                end_datetime=log_data.get('end_datetime'),
                details=log_data.get('details', {}),
                notes=log_data.get('notes', '')
            )

            # Set type-specific fields
            if log_data['logistics_type'] == LogisticsType.FLIGHT:
                logistics.flight_number = log_data.get('flight_number')
                logistics.departure_airport = log_data.get('departure_airport')
                logistics.arrival_airport = log_data.get('arrival_airport')
            elif log_data['logistics_type'] == LogisticsType.HOTEL:
                logistics.room_type = log_data.get('room_type')
                logistics.number_of_rooms = log_data.get('number_of_rooms')
                logistics.breakfast_included = log_data.get('breakfast_included', False)

            db.session.add(logistics)
            logistics_list.append(logistics)

    db.session.commit()
    print(f"  [OK] Created {len(logistics_list)} logistics entries")
    return logistics_list


def clean_database():
    """Remove all data from database."""
    print("Cleaning database...")

    # Delete in order to respect foreign keys
    LocalContact.query.delete()
    LogisticsInfo.query.delete()
    GuestlistEntry.query.delete()
    TourStop.query.delete()
    Tour.query.delete()
    VenueContact.query.delete()
    Venue.query.delete()
    BandMembership.query.delete()
    Band.query.delete()

    # Clear user_roles association table
    db.session.execute(db.text('DELETE FROM user_roles'))

    User.query.delete()
    Role.query.delete()

    db.session.commit()
    print("  [OK] Database cleaned")


def seed_all():
    """Run all seed functions."""
    print("\n" + "=" * 60)
    print("Tour Manager - Seeding Database")
    print("=" * 60 + "\n")

    roles = create_roles()
    users = create_users(roles)
    band = create_band(users)
    venues = create_venues()
    tour = create_tour(band, venues)
    tour_stops = create_tour_stops(tour, venues)
    create_guestlist_entries(tour_stops, users)
    create_logistics(tour_stops)

    print("\n" + "=" * 60)
    print("[OK] Seeding complete!")
    print("=" * 60)
    print("\nDemo Credentials:")
    print("-" * 40)
    for user_data in USERS_DATA:
        print(f"  {user_data['email']}")
        print(f"    Password: {user_data['password']}")
        print(f"    Role: {', '.join(user_data['roles'])}")
        print()


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    app = create_app()

    with app.app_context():
        if '--clean' in sys.argv:
            clean_database()

        seed_all()


