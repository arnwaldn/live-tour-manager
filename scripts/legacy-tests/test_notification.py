"""Script pour créer une notification de test."""
from app import create_app
from app.extensions import db
from app.models.notification import Notification, NotificationType, NotificationCategory
from app.models.user import User

app = create_app()
with app.app_context():
    user = User.query.first()
    if user:
        print(f'User found: {user.email}')
        n = Notification(
            user_id=user.id,
            title='Bienvenue!',
            message='Le système de notifications est maintenant actif.',
            type=NotificationType.SUCCESS,
            category=NotificationCategory.SYSTEM
        )
        db.session.add(n)
        db.session.commit()
        print(f'Notification created: {n.id}')
    else:
        print('No user found')
