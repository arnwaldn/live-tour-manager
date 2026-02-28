"""
Advancing service for GigRoute.
Handles business logic for event preparation (advancing) workflow.
"""
import json
from datetime import datetime, date
from typing import List, Dict, Optional, Any

from flask import current_app

from app.extensions import db
from app.models.advancing import (
    AdvancingChecklistItem, AdvancingTemplate, RiderRequirement,
    AdvancingContact, ChecklistCategory, RiderCategory,
    DEFAULT_CHECKLIST_ITEMS
)
from app.models.tour_stop import TourStop
from app.models.tour import Tour


class AdvancingService:
    """Service for managing advancing workflow."""

    @staticmethod
    def init_checklist(tour_stop_id: int, template_id: Optional[int] = None) -> List[AdvancingChecklistItem]:
        """Initialize advancing checklist for a tour stop from a template.

        Args:
            tour_stop_id: Tour stop to initialize
            template_id: Optional template ID (uses default if None)

        Returns:
            List of created checklist items

        Raises:
            ValueError: If checklist already exists or stop not found
        """
        stop = TourStop.query.get_or_404(tour_stop_id)

        # Check if already initialized
        existing = AdvancingChecklistItem.query.filter_by(tour_stop_id=tour_stop_id).count()
        if existing > 0:
            raise ValueError("L'advancing est deja initialise pour cette date")

        # Get template items
        if template_id:
            template = AdvancingTemplate.query.get_or_404(template_id)
            items_data = template.items
        else:
            items_data = DEFAULT_CHECKLIST_ITEMS

        created_items = []
        for item_data in items_data:
            item = AdvancingChecklistItem(
                tour_stop_id=tour_stop_id,
                category=ChecklistCategory(item_data['category']),
                label=item_data['label'],
                sort_order=item_data.get('sort_order', 0)
            )
            db.session.add(item)
            created_items.append(item)

        # Update advancing status
        stop.advancing_status = 'in_progress'
        db.session.commit()

        return created_items

    @staticmethod
    def toggle_item(item_id: int, user_id: int) -> AdvancingChecklistItem:
        """Toggle a checklist item completion status.

        Args:
            item_id: Checklist item ID
            user_id: User performing the toggle

        Returns:
            Updated checklist item
        """
        item = AdvancingChecklistItem.query.get_or_404(item_id)
        item.toggle(user_id)

        # Auto-update advancing status based on completion
        stop = item.tour_stop
        AdvancingService._update_advancing_status(stop)

        db.session.commit()
        return item

    @staticmethod
    def update_item_notes(item_id: int, notes: str) -> AdvancingChecklistItem:
        """Update notes on a checklist item.

        Args:
            item_id: Checklist item ID
            notes: New notes text

        Returns:
            Updated checklist item
        """
        item = AdvancingChecklistItem.query.get_or_404(item_id)
        item.notes = notes
        db.session.commit()
        return item

    @staticmethod
    def get_advancing_summary(tour_id: int) -> Dict[str, Any]:
        """Get advancing summary for all stops in a tour.

        Args:
            tour_id: Tour ID

        Returns:
            Dictionary with per-stop advancing stats
        """
        Tour.query.get_or_404(tour_id)

        stops = TourStop.query.filter_by(tour_id=tour_id).order_by(TourStop.date).all()

        summary = {
            'total_stops': len(stops),
            'not_started': 0,
            'in_progress': 0,
            'waiting_venue': 0,
            'completed': 0,
            'issues': 0,
            'stops': []
        }

        for stop in stops:
            items = AdvancingChecklistItem.query.filter_by(tour_stop_id=stop.id).all()
            total_items = len(items)
            completed_items = sum(1 for i in items if i.is_completed)
            completion_pct = int((completed_items / total_items) * 100) if total_items > 0 else 0

            stop_data = {
                'id': stop.id,
                'date': stop.date.isoformat(),
                'venue_name': stop.venue_name,
                'venue_city': stop.venue_city,
                'event_type': stop.event_type.value,
                'advancing_status': stop.advancing_status,
                'advancing_status_label': stop.advancing_status_label,
                'advancing_status_color': stop.advancing_status_color,
                'total_items': total_items,
                'completed_items': completed_items,
                'completion_pct': completion_pct,
                'advancing_deadline': stop.advancing_deadline.isoformat() if stop.advancing_deadline else None,
            }
            summary['stops'].append(stop_data)

            # Count by status
            status = stop.advancing_status
            if status in summary:
                summary[status] += 1

        overall_pct = 0
        if summary['total_stops'] > 0:
            overall_pct = int((summary['completed'] / summary['total_stops']) * 100)
        summary['overall_completion_pct'] = overall_pct

        return summary

    @staticmethod
    def add_rider_requirement(
        tour_stop_id: int,
        category: str,
        requirement: str,
        quantity: int = 1,
        is_mandatory: bool = True,
        notes: Optional[str] = None
    ) -> RiderRequirement:
        """Add a rider requirement to a tour stop.

        Args:
            tour_stop_id: Tour stop ID
            category: RiderCategory value
            requirement: Requirement description
            quantity: Quantity needed
            is_mandatory: Whether mandatory
            notes: Optional notes

        Returns:
            Created RiderRequirement
        """
        TourStop.query.get_or_404(tour_stop_id)

        # Get next sort order
        max_order = db.session.query(
            db.func.max(RiderRequirement.sort_order)
        ).filter_by(tour_stop_id=tour_stop_id).scalar() or 0

        rider = RiderRequirement(
            tour_stop_id=tour_stop_id,
            category=RiderCategory(category),
            requirement=requirement,
            quantity=quantity,
            is_mandatory=is_mandatory,
            notes=notes,
            sort_order=max_order + 1
        )
        db.session.add(rider)
        db.session.commit()
        return rider

    @staticmethod
    def confirm_rider_item(item_id: int, venue_response: Optional[str] = None) -> RiderRequirement:
        """Confirm a rider requirement (venue response).

        Args:
            item_id: RiderRequirement ID
            venue_response: Optional venue response text

        Returns:
            Updated RiderRequirement
        """
        item = RiderRequirement.query.get_or_404(item_id)
        item.is_confirmed = True
        if venue_response:
            item.venue_response = venue_response
        db.session.commit()
        return item

    @staticmethod
    def add_contact(
        tour_stop_id: int,
        name: str,
        role: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        is_primary: bool = False,
        notes: Optional[str] = None
    ) -> AdvancingContact:
        """Add an advancing contact for a tour stop.

        Args:
            tour_stop_id: Tour stop ID
            name: Contact name
            role: Contact role
            email: Contact email
            phone: Contact phone
            is_primary: Whether primary contact
            notes: Optional notes

        Returns:
            Created AdvancingContact
        """
        TourStop.query.get_or_404(tour_stop_id)

        # If marking as primary, unset other primary contacts
        if is_primary:
            AdvancingContact.query.filter_by(
                tour_stop_id=tour_stop_id, is_primary=True
            ).update({'is_primary': False})

        contact = AdvancingContact(
            tour_stop_id=tour_stop_id,
            name=name,
            role=role,
            email=email,
            phone=phone,
            is_primary=is_primary,
            notes=notes
        )
        db.session.add(contact)
        db.session.commit()
        return contact

    @staticmethod
    def update_production_specs(
        tour_stop_id: int,
        stage_width: Optional[float] = None,
        stage_depth: Optional[float] = None,
        stage_height: Optional[float] = None,
        power_available: Optional[str] = None,
        rigging_points: Optional[int] = None
    ) -> TourStop:
        """Update production specs for a tour stop.

        Args:
            tour_stop_id: Tour stop ID
            Various production spec fields

        Returns:
            Updated TourStop
        """
        stop = TourStop.query.get_or_404(tour_stop_id)
        if stage_width is not None:
            stop.stage_width = stage_width
        if stage_depth is not None:
            stop.stage_depth = stage_depth
        if stage_height is not None:
            stop.stage_height = stage_height
        if power_available is not None:
            stop.power_available = power_available
        if rigging_points is not None:
            stop.rigging_points = rigging_points
        db.session.commit()
        return stop

    @staticmethod
    def update_advancing_status(tour_stop_id: int, status: str) -> TourStop:
        """Manually update advancing status.

        Args:
            tour_stop_id: Tour stop ID
            status: New AdvancingStatus value

        Returns:
            Updated TourStop
        """
        stop = TourStop.query.get_or_404(tour_stop_id)
        valid_statuses = ['not_started', 'in_progress', 'waiting_venue', 'completed', 'issues']
        if status not in valid_statuses:
            raise ValueError(f"Statut invalide: {status}")
        stop.advancing_status = status
        if status == 'completed':
            stop.is_advanced = True
            stop.advanced_at = datetime.utcnow()
        db.session.commit()
        return stop

    @staticmethod
    def create_template(
        name: str,
        items: List[Dict],
        description: Optional[str] = None,
        created_by_id: Optional[int] = None
    ) -> AdvancingTemplate:
        """Create a reusable advancing template.

        Args:
            name: Template name
            items: List of item dicts with category, label, sort_order
            description: Optional description
            created_by_id: User creating the template

        Returns:
            Created AdvancingTemplate
        """
        template = AdvancingTemplate(
            name=name,
            description=description,
            items=items,
            created_by_id=created_by_id
        )
        db.session.add(template)
        db.session.commit()
        return template

    @staticmethod
    def get_stop_advancing_data(tour_stop_id: int) -> Dict[str, Any]:
        """Get complete advancing data for a tour stop (for API/detail view).

        Args:
            tour_stop_id: Tour stop ID

        Returns:
            Dictionary with all advancing data
        """
        stop = TourStop.query.get_or_404(tour_stop_id)

        items = AdvancingChecklistItem.query.filter_by(
            tour_stop_id=tour_stop_id
        ).order_by(AdvancingChecklistItem.sort_order).all()

        riders = RiderRequirement.query.filter_by(
            tour_stop_id=tour_stop_id
        ).order_by(RiderRequirement.sort_order).all()

        contacts = AdvancingContact.query.filter_by(
            tour_stop_id=tour_stop_id
        ).all()

        # Group checklist by category
        checklist_by_category = {}
        for item in items:
            cat = item.category.value
            if cat not in checklist_by_category:
                checklist_by_category[cat] = []
            checklist_by_category[cat].append(item.to_dict())

        # Group riders by category
        riders_by_category = {}
        for rider in riders:
            cat = rider.category.value
            if cat not in riders_by_category:
                riders_by_category[cat] = []
            riders_by_category[cat].append(rider.to_dict())

        total_items = len(items)
        completed_items = sum(1 for i in items if i.is_completed)

        return {
            'tour_stop_id': tour_stop_id,
            'advancing_status': stop.advancing_status,
            'advancing_status_label': stop.advancing_status_label,
            'advancing_status_color': stop.advancing_status_color,
            'advancing_deadline': stop.advancing_deadline.isoformat() if stop.advancing_deadline else None,
            'total_items': total_items,
            'completed_items': completed_items,
            'completion_pct': int((completed_items / total_items) * 100) if total_items > 0 else 0,
            'checklist_by_category': checklist_by_category,
            'riders_by_category': riders_by_category,
            'contacts': [c.to_dict() for c in contacts],
            'production_specs': {
                'stage_width': stop.stage_width,
                'stage_depth': stop.stage_depth,
                'stage_height': stop.stage_height,
                'power_available': stop.power_available,
                'rigging_points': stop.rigging_points,
            },
        }

    @staticmethod
    def _update_advancing_status(stop: TourStop) -> None:
        """Auto-update advancing status based on checklist completion.

        Called internally after toggling items.
        """
        items = AdvancingChecklistItem.query.filter_by(tour_stop_id=stop.id).all()
        if not items:
            return

        total = len(items)
        completed = sum(1 for i in items if i.is_completed)

        if completed == total:
            stop.advancing_status = 'completed'
            stop.is_advanced = True
            stop.advanced_at = datetime.utcnow()
        elif completed > 0:
            # Only change to in_progress if not manually set to waiting_venue or issues
            if stop.advancing_status in ('not_started', 'completed'):
                stop.advancing_status = 'in_progress'

    @staticmethod
    def delete_checklist(tour_stop_id: int) -> int:
        """Delete all checklist items for a tour stop (reset advancing).

        Args:
            tour_stop_id: Tour stop ID

        Returns:
            Number of items deleted
        """
        stop = TourStop.query.get_or_404(tour_stop_id)
        count = AdvancingChecklistItem.query.filter_by(tour_stop_id=tour_stop_id).delete()
        stop.advancing_status = 'not_started'
        stop.is_advanced = False
        stop.advanced_at = None
        db.session.commit()
        return count
