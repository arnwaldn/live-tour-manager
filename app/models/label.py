"""
Label model for record label affiliation.
"""
from datetime import datetime
from app.extensions import db


class Label(db.Model):
    """Record label entity."""
    __tablename__ = 'labels'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, index=True)  # Short code for internal use
    country = db.Column(db.String(100))
    website = db.Column(db.String(255))
    logo_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users = db.relationship('User', back_populates='label', lazy='dynamic')

    def __repr__(self):
        return f'<Label {self.name}>'

    @classmethod
    def get_choices(cls, include_empty=True):
        """Get choices for form select fields."""
        choices = []
        if include_empty:
            choices.append((0, '-- Aucun label --'))
        choices.extend([
            (label.id, label.name) for label in cls.query.filter_by(is_active=True).order_by(cls.name).all()
        ])
        return choices

    @classmethod
    def get_or_create(cls, name, code=None):
        """Get existing label or create new one."""
        label = cls.query.filter_by(name=name).first()
        if not label:
            label = cls(name=name, code=code)
            db.session.add(label)
            db.session.commit()
        return label
