"""Clean up test data from database."""
import os
os.environ["FLASK_ENV"] = "development"

from app import create_app
from app.extensions import db

app = create_app("development")

with app.app_context():
    real_email = "arnaud.porcel@gmail.com"

    print("=== NETTOYAGE BASE DE DONNEES ===")
    print()

    # Use raw SQL to clean up in correct order (respecting FK constraints)
    # Added local_contacts before tour_stops
    tables_to_clean = [
        "audit_logs",
        "documents",
        "guestlist_entries",
        "logistics_info",
        "local_contacts",
        "tour_stops",
        "tours",
        "venue_contacts",
        "venues",
        "band_memberships",
        "bands",
        # Note: user_roles are preserved for real users
    ]

    for table in tables_to_clean:
        try:
            result = db.session.execute(db.text(f"DELETE FROM {table}"))
            db.session.commit()
            print(f"{table}: {result.rowcount} rows deleted")
        except Exception as e:
            db.session.rollback()
            print(f"{table}: Error - {e}")

    # Delete test users
    result = db.session.execute(
        db.text("DELETE FROM users WHERE email != :email"),
        {"email": real_email}
    )
    print(f"users (test): {result.rowcount} rows deleted")

    db.session.commit()

    # Verify
    result = db.session.execute(db.text("SELECT email, first_name, last_name FROM users"))
    users = result.fetchall()

    print()
    print("=== UTILISATEURS RESTANTS ===")
    for u in users:
        print(f"  {u[0]} ({u[1]} {u[2]})")

    print()
    print("Nettoyage termine!")
