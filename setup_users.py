"""
Initial user setup script - Run once during deployment.
Creates admin and manager accounts with secure passwords.

Usage:
  Set environment variables before running:
    ADMIN_EMAIL=admin@example.com
    ADMIN_PASSWORD=YourSecurePassword
    MANAGER_EMAIL=manager@example.com
    MANAGER_PASSWORD=YourSecurePassword

  Or run interactively (will prompt for values).
"""
import os
import sys
import getpass


def setup_initial_users():
    """Create initial admin and manager users with full access."""
    print("=" * 60)
    print("GIGROUTE - USER SETUP SCRIPT")
    print("=" * 60)

    try:
        from app import create_app, db
        from app.models.user import User, AccessLevel
        print("[OK] Imports successful")
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        return 0

    app = create_app()
    print("[OK] App created")

    # Get credentials from env vars or prompt interactively
    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    manager_email = os.environ.get('MANAGER_EMAIL')
    manager_password = os.environ.get('MANAGER_PASSWORD')

    if not admin_email:
        admin_email = input("Admin email: ").strip()
    if not admin_password:
        admin_password = getpass.getpass("Admin password: ")
    if not manager_email:
        manager_email = input("Manager email: ").strip()
    if not manager_password:
        manager_password = getpass.getpass("Manager password: ")

    if not all([admin_email, admin_password, manager_email, manager_password]):
        print("[ERROR] All credentials are required.")
        return 0

    with app.app_context():
        print("[OK] App context entered")

        created_count = 0

        # ============================================
        # ADMIN USER - Full system access
        # ============================================
        existing_admin = User.query.filter_by(email=admin_email).first()

        if existing_admin:
            print("[UPDATE] Admin exists, ensuring ADMIN access level...")
            existing_admin.access_level = AccessLevel.ADMIN
            existing_admin.is_active = True
            existing_admin.email_verified = True
            db.session.commit()
            print(f"[OK] Admin updated: {admin_email} -> AccessLevel.ADMIN")
        else:
            admin = User(
                email=admin_email,
                first_name='Admin',
                last_name='GigRoute',
                access_level=AccessLevel.ADMIN,
                is_active=True,
                email_verified=True
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            created_count += 1
            print(f"[CREATED] Admin: {admin_email}")

        # ============================================
        # MANAGER USER - Tour/event management
        # ============================================
        existing_manager = User.query.filter_by(email=manager_email).first()

        if existing_manager:
            print("[UPDATE] Manager exists, ensuring MANAGER access level...")
            existing_manager.access_level = AccessLevel.MANAGER
            existing_manager.is_active = True
            existing_manager.email_verified = True
            db.session.commit()
            print(f"[OK] Manager updated: {manager_email} -> AccessLevel.MANAGER")
        else:
            manager = User(
                email=manager_email,
                first_name='Manager',
                last_name='GigRoute',
                access_level=AccessLevel.MANAGER,
                is_active=True,
                email_verified=True
            )
            manager.set_password(manager_password)
            db.session.add(manager)
            db.session.commit()
            created_count += 1
            print(f"[CREATED] Manager: {manager_email}")

        # Final summary
        print("\n" + "=" * 60)
        print("SETUP COMPLETE")
        print("=" * 60)
        print(f"Users in database: {User.query.count()}")
        print(f"Admin: {admin_email}")
        print(f"Manager: {manager_email}")
        print("=" * 60)

        return created_count


if __name__ == '__main__':
    setup_initial_users()
