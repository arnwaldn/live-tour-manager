"""
Initial user setup script - Run once during deployment
Creates admin and manager accounts with secure passwords
"""
import sys

def setup_initial_users():
    """Create initial admin and manager users with full access."""
    print("="*60)
    print("TOUR MANAGER - USER SETUP SCRIPT")
    print("="*60)

    try:
        from app import create_app, db
        from app.models.user import User, AccessLevel
        print("[OK] Imports successful")
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        return 0

    app = create_app()
    print("[OK] App created")

    # Passwords for initial setup - CHANGE AFTER FIRST LOGIN
    admin_password = "TourAdmin2026!Secure"
    manager_password = "TourManager2026!Secure"

    with app.app_context():
        print("[OK] App context entered")

        created_count = 0

        # ============================================
        # ADMIN USER - Full system access
        # ============================================
        admin_email = 'arnaud.porcel@gmail.com'
        existing_admin = User.query.filter_by(email=admin_email).first()

        if existing_admin:
            # Update existing user to ensure ADMIN access
            print(f"[UPDATE] Admin exists, ensuring ADMIN access level...")
            existing_admin.access_level = AccessLevel.ADMIN
            existing_admin.is_active = True
            existing_admin.email_verified = True
            db.session.commit()
            print(f"[OK] Admin updated: {admin_email} -> AccessLevel.ADMIN")
        else:
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
            db.session.commit()
            created_count += 1
            print(f"[CREATED] Admin: {admin_email}")
            print(f"         Access: ADMIN (full system access)")
            print(f"         Password: {admin_password}")

        # Verify admin
        verify_admin = User.query.filter_by(email=admin_email).first()
        if verify_admin:
            print(f"[VERIFY] Admin access_level = {verify_admin.access_level}")
            print(f"[VERIFY] Admin is_admin() = {verify_admin.is_admin()}")

        # ============================================
        # MANAGER USER - Tour/event management
        # ============================================
        manager_email = 'jonathan.studiopalenquegroup@gmail.com'
        existing_manager = User.query.filter_by(email=manager_email).first()

        if existing_manager:
            print(f"[UPDATE] Manager exists, ensuring MANAGER access level...")
            existing_manager.access_level = AccessLevel.MANAGER
            existing_manager.is_active = True
            existing_manager.email_verified = True
            db.session.commit()
            print(f"[OK] Manager updated: {manager_email} -> AccessLevel.MANAGER")
        else:
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
            db.session.commit()
            created_count += 1
            print(f"[CREATED] Manager: {manager_email}")
            print(f"         Access: MANAGER (tour/event management)")
            print(f"         Password: {manager_password}")

        # Verify manager
        verify_manager = User.query.filter_by(email=manager_email).first()
        if verify_manager:
            print(f"[VERIFY] Manager access_level = {verify_manager.access_level}")

        # Final summary
        print("\n" + "="*60)
        print("SETUP COMPLETE")
        print("="*60)
        print(f"Users in database: {User.query.count()}")
        print("")
        print("CREDENTIALS:")
        print(f"  ADMIN:   {admin_email}")
        print(f"           Password: {admin_password}")
        print(f"  MANAGER: {manager_email}")
        print(f"           Password: {manager_password}")
        print("="*60)

        return created_count

if __name__ == '__main__':
    setup_initial_users()
