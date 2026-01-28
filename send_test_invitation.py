"""
Script de test pour envoyer une vraie invitation email.
Execute avec: ./venv/Scripts/python.exe send_test_invitation.py
"""
import sys
import os
import io

# Forcer UTF-8 pour Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Charger les variables d'environnement depuis .env
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.utils.email import send_invitation_email
import secrets

def send_test_invitation():
    """Envoie une vraie invitation email de test."""
    app = create_app()

    with app.app_context():
        print("\n" + "="*60)
        print("TEST D'ENVOI D'INVITATION EMAIL")
        print("="*60)

        # Email de destination (alias Gmail pour recevoir dans la meme boite)
        test_email = "arnaud.porcel+test@gmail.com"

        # 1. Trouver le manager (celui qui invite)
        print("\n[1] Recherche du manager...")
        manager = User.query.join(User.roles).filter(Role.name == 'MANAGER').first()

        if not manager:
            print("    ERREUR: Aucun manager trouve!")
            return False

        print(f"    Manager trouve: {manager.full_name} ({manager.email})")

        # 2. Verifier si l'utilisateur test existe deja
        print(f"\n[2] Verification si {test_email} existe deja...")
        existing = User.query.filter_by(email=test_email).first()

        if existing:
            print(f"    Utilisateur existant trouve (id={existing.id}), suppression...")
            db.session.delete(existing)
            db.session.commit()
            print("    Ancien utilisateur supprime.")

        # 3. Creer l'utilisateur de test
        print(f"\n[3] Creation de l'utilisateur de test...")
        musician_role = Role.query.filter_by(name='MUSICIAN').first()

        if not musician_role:
            print("    ERREUR: Role MUSICIAN non trouve!")
            return False

        new_user = User(
            email=test_email,
            first_name="Test",
            last_name="Invitation",
            phone="+33600000000",
            is_active=True,
            email_verified=False,
            invited_by_id=manager.id
        )
        # Password temporaire (requis par contrainte NOT NULL)
        new_user.set_password(secrets.token_urlsafe(32))
        new_user.roles.append(musician_role)

        # Generer le token d'invitation (72h)
        token = new_user.generate_invitation_token()

        db.session.add(new_user)
        db.session.commit()

        print(f"    Utilisateur cree: {new_user.email}")
        print(f"    Role: MUSICIAN")
        print(f"    Token: {token[:20]}...")
        print(f"    Expire: {new_user.invitation_token_expires}")

        # 4. Generer l'URL d'acceptation
        # Note: On construit l'URL manuellement car url_for necessite SERVER_NAME
        base_url = "http://127.0.0.1:5001"
        accept_url = f"{base_url}/auth/accept-invite/{token}"
        print(f"\n[4] URL d'invitation:")
        print(f"    {accept_url}")

        # 5. Envoyer l'email
        print("\n[5] Envoi de l'email d'invitation...")

        # Verifier la configuration email
        mail_server = app.config.get('MAIL_SERVER')
        mail_username = app.config.get('MAIL_USERNAME')
        mail_password = app.config.get('MAIL_PASSWORD')

        print(f"    Serveur: {mail_server}")
        print(f"    Username: {mail_username or 'NON CONFIGURE'}")
        print(f"    Password: {'***' if mail_password else 'NON CONFIGURE'}")

        if not mail_username or not mail_password:
            print("\n    ATTENTION: Email non configure!")
            print("    Pour configurer, creez un fichier .env avec:")
            print("    MAIL_USERNAME=votre-email@gmail.com")
            print("    MAIL_PASSWORD=votre-app-password")
            print("\n    L'URL d'invitation ci-dessus reste valide 72h.")
            print("    Vous pouvez la copier et l'ouvrir manuellement.")

            # Laisser l'utilisateur en base pour test manuel
            print("\n" + "="*60)
            print("URL A COPIER POUR TEST MANUEL:")
            print("="*60)
            print(f"\n{accept_url}\n")
            print("="*60)
            return True

        # Tenter l'envoi
        try:
            success = send_invitation_email(new_user, manager)

            if success:
                print("\n    EMAIL ENVOYE AVEC SUCCES!")
                print(f"    Verifiez votre boite: {test_email}")
            else:
                print("\n    ECHEC de l'envoi (voir logs)")
                print(f"    URL manuelle: {accept_url}")
        except Exception as e:
            print(f"\n    ERREUR lors de l'envoi: {e}")
            print(f"    URL manuelle: {accept_url}")

        print("\n" + "="*60)
        print("FIN DU TEST")
        print("="*60)

        return True

if __name__ == '__main__':
    send_test_invitation()
