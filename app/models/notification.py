"""
Notification model for in-app notifications.
"""
from datetime import datetime
from app.extensions import db


class NotificationType:
    """Types de notifications."""
    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    ERROR = 'error'


class NotificationCategory:
    """Catégories de notifications."""
    TOUR = 'tour'
    GUESTLIST = 'guestlist'
    SYSTEM = 'system'
    BAND = 'band'
    REGISTRATION = 'registration'
    DOCUMENT = 'document'


class Notification(db.Model):
    """
    Modèle pour les notifications in-app.

    Fonctionne en parallèle avec le système email existant.
    """
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Type et catégorie
    type = db.Column(db.String(20), default=NotificationType.INFO)
    category = db.Column(db.String(50), default=NotificationCategory.SYSTEM)

    # Contenu
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    link = db.Column(db.String(500))  # URL optionnelle pour redirection

    # État
    is_read = db.Column(db.Boolean, default=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)

    # Relations
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic',
                                                       order_by='Notification.created_at.desc()'))

    def __repr__(self):
        return f'<Notification {self.id}: {self.title[:30]}>'

    def mark_as_read(self):
        """Marquer la notification comme lue."""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
            db.session.commit()

    def to_dict(self):
        """Convertir en dictionnaire pour API JSON."""
        return {
            'id': self.id,
            'type': self.type,
            'category': self.category,
            'title': self.title,
            'message': self.message,
            'link': self.link,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None
        }

    @classmethod
    def get_unread_count(cls, user_id):
        """Obtenir le nombre de notifications non lues pour un utilisateur."""
        return cls.query.filter_by(user_id=user_id, is_read=False).count()

    @classmethod
    def get_recent(cls, user_id, limit=5):
        """Obtenir les notifications récentes pour un utilisateur."""
        return cls.query.filter_by(user_id=user_id).order_by(
            cls.created_at.desc()
        ).limit(limit).all()

    @classmethod
    def mark_all_read(cls, user_id):
        """Marquer toutes les notifications comme lues pour un utilisateur."""
        cls.query.filter_by(user_id=user_id, is_read=False).update({
            'is_read': True,
            'read_at': datetime.utcnow()
        })
        db.session.commit()
