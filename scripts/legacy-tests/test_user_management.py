"""
Test complet du systeme de gestion utilisateurs.
Executer avec: ./venv/Scripts/python.exe test_user_management.py
"""
import sys
import os
import io

# Forcer UTF-8 pour Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Ajouter le répertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.user import User, Role

def test_user_management():
    """Test complet du système de gestion utilisateurs."""
    app = create_app()

    with app.app_context():
        print("\n" + "="*60)
        print("TEST DU SYSTÈME DE GESTION UTILISATEURS")
        print("="*60)

        # 1. Vérifier que les colonnes invitation existent
        print("\n[1] Vérification des colonnes invitation...")
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('users')]

        required_cols = ['invitation_token', 'invitation_token_expires', 'invited_by_id']
        for col in required_cols:
            if col in columns:
                print(f"    ✓ Colonne '{col}' présente")
            else:
                print(f"    ✗ Colonne '{col}' MANQUANTE")
                return False

        # 2. Récupérer un manager existant
        print("\n[2] Recherche d'un manager existant...")
        manager = User.query.join(User.roles).filter(Role.name == 'MANAGER').first()

        if not manager:
            print("    ✗ Aucun manager trouvé. Création d'un manager test...")
            manager_role = Role.query.filter_by(name='MANAGER').first()
            if not manager_role:
                print("    ✗ Rôle MANAGER non trouvé!")
                return False

            manager = User(
                email='manager-test@example.com',
                first_name='Manager',
                last_name='Test',
                email_verified=True,
                is_active=True
            )
            manager.set_password('Manager123!')
            manager.roles.append(manager_role)
            db.session.add(manager)
            db.session.commit()
            print(f"    ✓ Manager créé: {manager.email}")
        else:
            print(f"    ✓ Manager trouvé: {manager.email}")

        # 3. Créer un utilisateur test avec invitation
        print("\n[3] Création d'un utilisateur test avec invitation...")

        # Supprimer l'utilisateur test s'il existe
        existing = User.query.filter_by(email='test-invite@example.com').first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            print("    - Ancien utilisateur test supprimé")

        # Créer le nouvel utilisateur
        musician_role = Role.query.filter_by(name='MUSICIAN').first()
        if not musician_role:
            print("    ✗ Rôle MUSICIAN non trouvé!")
            return False

        import secrets
        new_user = User(
            email='test-invite@example.com',
            first_name='Test',
            last_name='Invitation',
            phone='+33612345678',
            is_active=True,
            email_verified=False,
            invited_by_id=manager.id
        )
        # Set temporary random password (required by NOT NULL constraint)
        new_user.set_password(secrets.token_urlsafe(32))
        new_user.roles.append(musician_role)

        # Générer le token d'invitation
        token = new_user.generate_invitation_token()
        db.session.add(new_user)
        db.session.commit()

        print(f"    ✓ Utilisateur créé: {new_user.email}")
        print(f"    ✓ Token d'invitation: {token[:20]}...")
        print(f"    ✓ Expire: {new_user.invitation_token_expires}")
        print(f"    ✓ Invité par: {manager.full_name}")

        # 4. Vérifier le token
        print("\n[4] Vérification du token d'invitation...")
        verified_user = User.verify_invitation_token(token)

        if verified_user and verified_user.id == new_user.id:
            print(f"    ✓ Token valide pour: {verified_user.email}")
        else:
            print("    ✗ Token invalide!")
            return False

        # 5. Simuler l'activation du compte (définition du mot de passe)
        print("\n[5] Simulation de l'activation du compte...")
        new_user.set_password('TestPassword123!')
        new_user.clear_invitation_token()
        db.session.commit()

        if new_user.email_verified:
            print("    ✓ Email vérifié: True")
        else:
            print("    ✗ Email non vérifié!")
            return False

        if new_user.invitation_token is None:
            print("    ✓ Token d'invitation effacé")
        else:
            print("    ✗ Token non effacé!")
            return False

        if new_user.check_password('TestPassword123!'):
            print("    ✓ Mot de passe correctement défini")
        else:
            print("    ✗ Mot de passe incorrect!")
            return False

        # 6. Vérifier les statistiques
        print("\n[6] Statistiques utilisateurs...")
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        pending_invites = User.query.filter(User.invitation_token.isnot(None)).count()

        print(f"    - Total utilisateurs: {total_users}")
        print(f"    - Utilisateurs actifs: {active_users}")
        print(f"    - Invitations en attente: {pending_invites}")

        # 7. Lister les utilisateurs avec leurs rôles
        print("\n[7] Liste des utilisateurs...")
        users = User.query.order_by(User.created_at.desc()).limit(5).all()
        for u in users:
            roles = ', '.join([r.name for r in u.roles])
            status = '✓' if u.is_active else '✗'
            verified = '📧' if u.email_verified else '⏳'
            print(f"    {status} {verified} {u.full_name} ({u.email}) - {roles}")

        # 8. Nettoyer
        print("\n[8] Nettoyage...")
        db.session.delete(new_user)
        db.session.commit()
        print("    ✓ Utilisateur test supprimé")

        print("\n" + "="*60)
        print("✅ TOUS LES TESTS ONT RÉUSSI!")
        print("="*60)

        print("\n📌 URLs à tester manuellement:")
        print(f"   - Liste utilisateurs: http://127.0.0.1:5001/settings/users")
        print(f"   - Créer utilisateur: http://127.0.0.1:5001/settings/users/create")
        print(f"   - Paramètres: http://127.0.0.1:5001/settings")

        return True

if __name__ == '__main__':
    success = test_user_management()
    sys.exit(0 if success else 1)
