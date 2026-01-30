"""
Crew Schedule models for daily staff planning.
Manages time slots and assignments for tour stops.
"""
import enum
from datetime import datetime

from app.extensions import db
from app.models.profession import ProfessionCategory


class AssignmentStatus(enum.Enum):
    """Status for crew assignments."""
    ASSIGNED = 'assigned'       # Assigned, awaiting confirmation
    CONFIRMED = 'confirmed'     # Confirmed by the person
    DECLINED = 'declined'       # Declined
    UNAVAILABLE = 'unavailable' # Unavailable
    COMPLETED = 'completed'     # Completed (post-event)


class ExternalContact(db.Model):
    """External contact (freelancer without system account)."""
    __tablename__ = 'external_contacts'

    id = db.Column(db.Integer, primary_key=True)

    # Identity
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)

    # Contact
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))

    # Professional info
    profession_id = db.Column(db.Integer, db.ForeignKey('professions.id'))
    company = db.Column(db.String(100))  # Company/freelancer

    # Notes
    notes = db.Column(db.Text)

    # Ownership
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    profession = db.relationship('Profession', backref='external_contacts')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    assignments = db.relationship('CrewAssignment', back_populates='external_contact')

    def __repr__(self):
        return f'<ExternalContact {self.full_name}>'

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self):
        """Name with company if available."""
        if self.company:
            return f"{self.full_name} ({self.company})"
        return self.full_name


class CrewScheduleSlot(db.Model):
    """Time slot in the crew schedule."""
    __tablename__ = 'crew_schedule_slots'

    id = db.Column(db.Integer, primary_key=True)
    tour_stop_id = db.Column(db.Integer, db.ForeignKey('tour_stops.id', ondelete='CASCADE'), nullable=False)

    # Timing
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    # Task info
    task_name = db.Column(db.String(100), nullable=False)
    task_description = db.Column(db.Text)
    profession_category = db.Column(db.Enum(ProfessionCategory))

    # Display
    color = db.Column(db.String(7), default='#3B82F6')
    order = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    tour_stop = db.relationship('TourStop', backref=db.backref('crew_slots', lazy='dynamic', cascade='all, delete-orphan'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    assignments = db.relationship('CrewAssignment', back_populates='slot', cascade='all, delete-orphan')

    # Index for performance
    __table_args__ = (
        db.Index('ix_crew_slots_tour_stop', 'tour_stop_id'),
    )

    def __repr__(self):
        return f'<CrewScheduleSlot {self.task_name} {self.start_time}-{self.end_time}>'

    @property
    def duration_hours(self):
        """Calculate duration in hours."""
        from datetime import datetime, timedelta
        start = datetime.combine(datetime.today(), self.start_time)
        end = datetime.combine(datetime.today(), self.end_time)
        if end < start:
            end += timedelta(days=1)
        return (end - start).seconds / 3600

    @property
    def time_range(self):
        """Formatted time range."""
        return f"{self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"

    @property
    def confirmed_count(self):
        """Number of confirmed assignments."""
        return sum(1 for a in self.assignments if a.status == AssignmentStatus.CONFIRMED)

    @property
    def pending_count(self):
        """Number of pending assignments."""
        return sum(1 for a in self.assignments if a.status == AssignmentStatus.ASSIGNED)

    @property
    def category_label(self):
        """Human-readable category label."""
        if self.profession_category:
            labels = {
                ProfessionCategory.MUSICIEN: 'Musicien',
                ProfessionCategory.TECHNICIEN: 'Technicien',
                ProfessionCategory.PRODUCTION: 'Production',
                ProfessionCategory.STYLE: 'Style',
                ProfessionCategory.SECURITE: 'Sécurité',
                ProfessionCategory.MANAGEMENT: 'Management',
            }
            return labels.get(self.profession_category, self.profession_category.value)
        return 'Général'

    def to_dict(self):
        """Convert to dictionary for API."""
        return {
            'id': self.id,
            'tour_stop_id': self.tour_stop_id,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'task_name': self.task_name,
            'task_description': self.task_description,
            'profession_category': self.profession_category.value if self.profession_category else None,
            'color': self.color,
            'assignments': [a.to_dict() for a in self.assignments],
        }


class CrewAssignment(db.Model):
    """Assignment of a person to a time slot."""
    __tablename__ = 'crew_assignments'

    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.Integer, db.ForeignKey('crew_schedule_slots.id', ondelete='CASCADE'), nullable=False)

    # Assigned: system user OR external contact
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    external_contact_id = db.Column(db.Integer, db.ForeignKey('external_contacts.id'), nullable=True)

    # Profession override
    profession_id = db.Column(db.Integer, db.ForeignKey('professions.id'), nullable=True)

    # Status workflow
    status = db.Column(db.Enum(AssignmentStatus), default=AssignmentStatus.ASSIGNED)

    # Call time override
    call_time = db.Column(db.Time, nullable=True)

    # Notes
    notes = db.Column(db.Text)

    # Audit
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    slot = db.relationship('CrewScheduleSlot', back_populates='assignments')
    user = db.relationship('User', foreign_keys=[user_id], backref='crew_assignments')
    external_contact = db.relationship('ExternalContact', back_populates='assignments')
    profession = db.relationship('Profession')
    assigned_by = db.relationship('User', foreign_keys=[assigned_by_id])

    # Constraints
    __table_args__ = (
        db.CheckConstraint('user_id IS NOT NULL OR external_contact_id IS NOT NULL', name='ck_assignment_person'),
        db.UniqueConstraint('slot_id', 'user_id', name='uq_slot_user'),
        db.UniqueConstraint('slot_id', 'external_contact_id', name='uq_slot_external'),
        db.Index('ix_crew_assignments_user', 'user_id'),
    )

    def __repr__(self):
        person = self.person_name
        return f'<CrewAssignment {person} -> {self.slot.task_name if self.slot else "?"}>'

    @property
    def person_name(self):
        """Get assigned person's name."""
        if self.user:
            return self.user.full_name
        elif self.external_contact:
            return self.external_contact.full_name
        return 'Unknown'

    @property
    def person_email(self):
        """Get assigned person's email."""
        if self.user:
            return self.user.email
        elif self.external_contact:
            return self.external_contact.email
        return None

    @property
    def is_external(self):
        """Check if this is an external contact."""
        return self.external_contact_id is not None

    @property
    def is_confirmed(self):
        """Check if assignment is confirmed."""
        return self.status == AssignmentStatus.CONFIRMED

    @property
    def is_pending(self):
        """Check if assignment is pending."""
        return self.status == AssignmentStatus.ASSIGNED

    @property
    def effective_call_time(self):
        """Get effective call time (override or slot start)."""
        return self.call_time or self.slot.start_time

    @property
    def effective_profession(self):
        """Get effective profession (override or user's profession)."""
        if self.profession:
            return self.profession
        if self.user and hasattr(self.user, 'primary_profession'):
            return self.user.primary_profession
        if self.external_contact and self.external_contact.profession:
            return self.external_contact.profession
        return None

    @property
    def status_label(self):
        """Human-readable status label."""
        labels = {
            AssignmentStatus.ASSIGNED: 'En attente',
            AssignmentStatus.CONFIRMED: 'Confirmé',
            AssignmentStatus.DECLINED: 'Refusé',
            AssignmentStatus.UNAVAILABLE: 'Indisponible',
            AssignmentStatus.COMPLETED: 'Terminé',
        }
        return labels.get(self.status, self.status.value)

    @property
    def status_color(self):
        """Bootstrap color class for status."""
        colors = {
            AssignmentStatus.ASSIGNED: 'warning',
            AssignmentStatus.CONFIRMED: 'success',
            AssignmentStatus.DECLINED: 'danger',
            AssignmentStatus.UNAVAILABLE: 'secondary',
            AssignmentStatus.COMPLETED: 'info',
        }
        return colors.get(self.status, 'secondary')

    @property
    def status_icon(self):
        """Icon for status."""
        icons = {
            AssignmentStatus.ASSIGNED: 'hourglass-split',
            AssignmentStatus.CONFIRMED: 'check-circle-fill',
            AssignmentStatus.DECLINED: 'x-circle-fill',
            AssignmentStatus.UNAVAILABLE: 'slash-circle',
            AssignmentStatus.COMPLETED: 'check2-all',
        }
        return icons.get(self.status, 'question-circle')

    def confirm(self):
        """Confirm the assignment."""
        self.status = AssignmentStatus.CONFIRMED
        self.confirmed_at = datetime.utcnow()
        db.session.commit()

    def decline(self):
        """Decline the assignment."""
        self.status = AssignmentStatus.DECLINED
        self.confirmed_at = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        """Convert to dictionary for API."""
        return {
            'id': self.id,
            'slot_id': self.slot_id,
            'person_name': self.person_name,
            'person_email': self.person_email,
            'is_external': self.is_external,
            'status': self.status.value,
            'status_label': self.status_label,
            'call_time': self.call_time.strftime('%H:%M') if self.call_time else None,
            'notes': self.notes,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
        }
