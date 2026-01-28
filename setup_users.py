"""
Initial user setup script - Run once during deployment
Creates admin and manager accounts with secure passwords
"""
import os
import secrets

def setup_initial_users():
    """Create initial admin and manager users."""
    from app import create_app, db
    from app.models.user import User, AccessLevel

    app = create_app()

    # Pre-generated secure passwords (change these after first login!)
    # Using fixed passwords for initial setup - MUST be changed immediately
    admin_password = "TourAdmin2026!Secure"
    manager_password = "TourManager2026!Secure"

    with app.app_context():
        created_users = []

        # Create Admin user
        admin_email = 'arnaud.porcel@gmail.com'
        if not User.query.filter_by(email=admin_email).first():
            admin = User(
                email=admin_email,
                first_name='Arnaud',
                last_name='Porcel',
                access_level=AccessLevel.ADMIN,
                is_active=True,
                email_verified=True
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            created_users.append(f"ADMIN: {admin_email}")
            print(f"[CREATED] Admin: {admin_email}")
        else:
            print(f"[EXISTS] Admin: {admin_email}")

        # Create Manager user
        manager_email = 'jonathan.studiopalenquegroup@gmail.com'
        if not User.query.filter_by(email=manager_email).first():
            manager = User(
                email=manager_email,
                first_name='Jonathan',
                last_name='Studio Palenque',
                access_level=AccessLevel.MANAGER,
                is_active=True,
                email_verified=True
            )
            manager.set_password(manager_password)
            db.session.add(manager)
            created_users.append(f"MANAGER: {manager_email}")
            print(f"[CREATED] Manager: {manager_email}")
        else:
            print(f"[EXISTS] Manager: {manager_email}")

        # Commit all changes
        if created_users:
            db.session.commit()
            print("\n" + "="*50)
            print("USERS CREATED SUCCESSFULLY")
            print("="*50)
            for user in created_users:
                print(f"  - {user}")
            print("\nINITIAL PASSWORDS (CHANGE IMMEDIATELY!):")
            print(f"  Admin:   {admin_password}")
            print(f"  Manager: {manager_password}")
            print("="*50)
        else:
            print("\nNo new users created (all already exist)")

        return len(created_users)

if __name__ == '__main__':
    setup_initial_users()
