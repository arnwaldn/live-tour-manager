"""
Beta test server — file-based SQLite, single process.
Creates DB + seeds data + starts Flask in one shot.

Usage: python scripts/run_beta_server.py
"""
import sys
import os
import io

# UTF-8 for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'beta_test.db')
DB_URI = f'sqlite:///{DB_FILE}'

# Set env before importing app
os.environ['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'beta-test-secret-key-2026')
os.environ['TEST_DATABASE_URL'] = DB_URI

from app import create_app
from app.extensions import db

app = create_app('testing')

# Override config for local beta
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}
app.config['SERVER_NAME'] = None
app.config['WTF_CSRF_ENABLED'] = False
app.config['RATELIMIT_ENABLED'] = False

with app.app_context():
    # Drop and recreate for clean state
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
            print(f"[OK] Ancien fichier DB supprime")
        except PermissionError:
            print(f"[WARN] DB file locked, dropping all tables instead")
            db.drop_all()

    db.create_all()
    print(f"[OK] Tables creees dans {DB_FILE}")

    # Seed professions
    from app.models.profession import seed_professions
    try:
        seed_professions()
        db.session.commit()
        print("[OK] Professions seedees")
    except Exception as e:
        db.session.rollback()
        print(f"[WARN] Professions: {e}")

    # Create users
    from app.models.user import User, AccessLevel

    admin = User(
        email='arnaud.porcel@gmail.com',
        first_name='Arnaud',
        last_name='Porcel',
        is_active=True,
        email_verified=True,
        access_level=AccessLevel.ADMIN
    )
    admin.set_password('Adminnano')

    manager = User(
        email='manager@test.com',
        first_name='Marie',
        last_name='Dupont',
        is_active=True,
        email_verified=True,
        access_level=AccessLevel.MANAGER
    )
    manager.set_password('Manager123!')

    musician = User(
        email='musician@test.com',
        first_name='Lucas',
        last_name='Martin',
        is_active=True,
        email_verified=True,
        access_level=AccessLevel.STAFF
    )
    musician.set_password('Musician123!')

    viewer = User(
        email='viewer@test.com',
        first_name='Sophie',
        last_name='Bernard',
        is_active=True,
        email_verified=True,
        access_level=AccessLevel.VIEWER
    )
    viewer.set_password('Viewer123!')

    db.session.add_all([admin, manager, musician, viewer])
    db.session.commit()
    print(f"[OK] 4 utilisateurs crees (admin, manager, staff, viewer)")

    # Create sample data
    from app.models.band import Band, BandMembership
    from app.models.venue import Venue
    from app.models.tour import Tour, TourStatus
    from app.models.tour_stop import TourStop, EventType
    from datetime import date, time, timedelta

    band = Band(
        name='Les Nomades',
        genre='Rock Alternatif',
        bio='Groupe de rock alternatif francais.',
        manager_id=admin.id
    )
    db.session.add(band)
    db.session.flush()

    # Add members via BandMembership
    m1 = BandMembership(user_id=admin.id, band_id=band.id, role_in_band='Manager/Guitariste')
    m2 = BandMembership(user_id=musician.id, band_id=band.id, role_in_band='Bassiste')
    db.session.add_all([m1, m2])

    venue1 = Venue(
        name='Le Bataclan',
        city='Paris',
        country='France',
        address='50 Boulevard Voltaire',
        capacity=1500,
        phone='+33 1 43 14 00 30',
        email='contact@bataclan.fr'
    )
    venue2 = Venue(
        name="L'Olympia",
        city='Paris',
        country='France',
        address='28 Boulevard des Capucines',
        capacity=2000,
        email='contact@olympia.fr'
    )
    venue3 = Venue(
        name='Le Zenith',
        city='Lyon',
        country='France',
        address='Boulevard Stalingrad',
        capacity=5800,
        email='contact@zenith-lyon.fr'
    )
    db.session.add_all([venue1, venue2, venue3])
    db.session.flush()

    tour = Tour(
        name='Tour Europe 2026',
        band_id=band.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        status=TourStatus.ACTIVE,
        description='Tournee europeenne printemps 2026'
    )
    db.session.add(tour)
    db.session.flush()

    stop1 = TourStop(
        tour_id=tour.id,
        band_id=band.id,
        venue_id=venue1.id,
        date=date.today() + timedelta(days=3),
        event_type=EventType.SHOW,
        load_in_time=time(14, 0),
        doors_time=time(19, 0),
        set_time=time(20, 30),
        guarantee=5000.0,
        currency='EUR',
        notes='Premiere date de la tournee'
    )
    stop2 = TourStop(
        tour_id=tour.id,
        band_id=band.id,
        venue_id=venue2.id,
        date=date.today() + timedelta(days=7),
        event_type=EventType.SHOW,
        load_in_time=time(15, 0),
        doors_time=time(19, 30),
        set_time=time(21, 0),
        guarantee=8000.0,
        currency='EUR'
    )
    stop3 = TourStop(
        tour_id=tour.id,
        band_id=band.id,
        date=date.today() + timedelta(days=5),
        event_type=EventType.DAY_OFF,
        notes='Jour de repos a Paris'
    )
    stop4 = TourStop(
        tour_id=tour.id,
        band_id=band.id,
        venue_id=venue3.id,
        date=date.today() + timedelta(days=10),
        event_type=EventType.SHOW,
        load_in_time=time(13, 0),
        doors_time=time(18, 30),
        set_time=time(20, 0),
        guarantee=12000.0,
        currency='EUR'
    )
    db.session.add_all([stop1, stop2, stop3, stop4])
    db.session.commit()
    print(f"[OK] Donnees de test: 1 groupe, 3 salles, 1 tournee, 4 stops")

    # Verify
    user_count = User.query.count()
    band_count = Band.query.count()
    venue_count = Venue.query.count()
    tour_count = Tour.query.count()
    stop_count = TourStop.query.count()
    print(f"\n=== DB beta_test.db ===")
    print(f"  Users: {user_count}")
    print(f"  Bands: {band_count}")
    print(f"  Venues: {venue_count}")
    print(f"  Tours: {tour_count}")
    print(f"  Stops: {stop_count}")
    print(f"=======================\n")

print("Demarrage du serveur sur http://127.0.0.1:5001 ...")
print("Login: arnaud.porcel@gmail.com / Adminnano")
print("       manager@test.com / Manager123!")
print("       musician@test.com / Musician123!")
print("       viewer@test.com / Viewer123!")
print()

app.run(host='127.0.0.1', port=5001, debug=False)
