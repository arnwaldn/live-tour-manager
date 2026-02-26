# =============================================================================
# Tour Manager - Advancing Module Tests (Phase 7a)
# =============================================================================
#
# NOTE: The `app` fixture already pushes an app context (via `with app.app_context():`
# in conftest.py). Do NOT wrap test bodies with `with app.app_context():` — nesting
# creates a second SQLAlchemy session, breaking fixture object identity.
# =============================================================================

import pytest
from datetime import date, time, timedelta

from app.extensions import db
from app.models.advancing import (
    AdvancingChecklistItem, AdvancingTemplate, RiderRequirement,
    AdvancingContact, AdvancingStatus, ChecklistCategory, RiderCategory,
    DEFAULT_CHECKLIST_ITEMS,
)
from app.models.tour_stop import TourStop
from app.services.advancing_service import AdvancingService


# =============================================================================
# Model Tests
# =============================================================================

class TestAdvancingModels:
    """Tests for advancing module models."""

    def test_advancing_status_enum_values(self):
        """Verify AdvancingStatus enum has all expected values."""
        expected = {'not_started', 'in_progress', 'waiting_venue', 'completed', 'issues'}
        actual = {s.value for s in AdvancingStatus}
        assert actual == expected

    def test_checklist_category_enum_values(self):
        """Verify ChecklistCategory enum has all 7 categories."""
        expected = {'accueil', 'technique', 'catering', 'hebergement',
                    'logistique', 'securite', 'admin'}
        actual = {c.value for c in ChecklistCategory}
        assert actual == expected

    def test_rider_category_enum_values(self):
        """Verify RiderCategory enum has all 6 categories."""
        expected = {'son', 'lumiere', 'scene', 'backline', 'catering', 'loges'}
        actual = {r.value for r in RiderCategory}
        assert actual == expected

    def test_default_checklist_has_26_items(self):
        """Verify default checklist contains exactly 26 items."""
        assert len(DEFAULT_CHECKLIST_ITEMS) == 26

    def test_default_checklist_all_categories_present(self):
        """Verify default checklist covers all 7 categories."""
        categories = {item['category'] for item in DEFAULT_CHECKLIST_ITEMS}
        expected = {c.value for c in ChecklistCategory}
        assert categories == expected

    def test_checklist_item_creation(self, app, sample_tour_stop):
        """Test creating a checklist item."""
        item = AdvancingChecklistItem(
            tour_stop_id=sample_tour_stop.id,
            category='technique',
            label='Fiche technique envoyée',
            sort_order=0,
        )
        db.session.add(item)
        db.session.commit()

        assert item.id is not None
        assert item.is_completed is False
        assert item.notes is None

    def test_checklist_item_toggle(self, app, sample_tour_stop, manager_user):
        """Test toggling a checklist item."""
        item = AdvancingChecklistItem(
            tour_stop_id=sample_tour_stop.id,
            category='accueil',
            label='Parking bus/camion',
            sort_order=0,
        )
        db.session.add(item)
        db.session.commit()

        # Toggle ON
        item.toggle(manager_user.id)
        assert item.is_completed is True
        assert item.completed_by_id == manager_user.id
        assert item.completed_at is not None

        # Toggle OFF
        item.toggle(manager_user.id)
        assert item.is_completed is False
        assert item.completed_by_id is None
        assert item.completed_at is None

    def test_checklist_item_to_dict(self, app, sample_tour_stop):
        """Test checklist item serialization."""
        item = AdvancingChecklistItem(
            tour_stop_id=sample_tour_stop.id,
            category='admin',
            label='Contrat signé',
            notes='En attente retour',
            sort_order=1,
        )
        db.session.add(item)
        db.session.commit()

        d = item.to_dict()
        assert d['category'] == 'admin'
        assert d['label'] == 'Contrat signé'
        assert d['is_completed'] is False
        assert d['notes'] == 'En attente retour'

    def test_rider_requirement_creation(self, app, sample_tour_stop):
        """Test creating a rider requirement."""
        rider = RiderRequirement(
            tour_stop_id=sample_tour_stop.id,
            category='son',
            requirement='Console Yamaha CL5',
            quantity=1,
            is_mandatory=True,
            sort_order=0,
        )
        db.session.add(rider)
        db.session.commit()

        assert rider.id is not None
        assert rider.is_confirmed is False

    def test_rider_requirement_to_dict(self, app, sample_tour_stop):
        """Test rider requirement serialization."""
        rider = RiderRequirement(
            tour_stop_id=sample_tour_stop.id,
            category='lumiere',
            requirement='12x PAR LED',
            quantity=12,
            is_mandatory=False,
            sort_order=0,
        )
        db.session.add(rider)
        db.session.commit()

        d = rider.to_dict()
        assert d['category'] == 'lumiere'
        assert d['quantity'] == 12
        assert d['is_mandatory'] is False

    def test_advancing_contact_creation(self, app, sample_tour_stop):
        """Test creating an advancing contact."""
        contact = AdvancingContact(
            tour_stop_id=sample_tour_stop.id,
            name='Jean Dupont',
            role='Régisseur général',
            email='jean@salle.fr',
            phone='06 12 34 56 78',
            is_primary=True,
        )
        db.session.add(contact)
        db.session.commit()

        assert contact.id is not None
        assert contact.is_primary is True

    def test_advancing_template_creation(self, app, manager_user):
        """Test creating an advancing template."""
        template = AdvancingTemplate(
            name='Concert standard',
            description='Template pour concerts 500+ places',
            items=DEFAULT_CHECKLIST_ITEMS[:5],
            created_by_id=manager_user.id,
        )
        db.session.add(template)
        db.session.commit()

        assert template.id is not None
        assert len(template.items) == 5

    def test_tour_stop_advancing_completion_empty(self, app, sample_tour_stop):
        """Test advancing_completion property with no items."""
        assert sample_tour_stop.advancing_completion == 0

    def test_tour_stop_advancing_completion_partial(self, app, sample_tour_stop, manager_user):
        """Test advancing_completion property with partial completion."""
        # Add 4 items, complete 1
        for i in range(4):
            item = AdvancingChecklistItem(
                tour_stop_id=sample_tour_stop.id,
                category='technique',
                label=f'Item {i}',
                sort_order=i,
            )
            db.session.add(item)
        db.session.commit()

        items = AdvancingChecklistItem.query.filter_by(
            tour_stop_id=sample_tour_stop.id
        ).all()
        items[0].toggle(manager_user.id)
        db.session.commit()

        db.session.refresh(sample_tour_stop)
        assert sample_tour_stop.advancing_completion == 25

    def test_tour_stop_advancing_status_label(self, app, sample_tour_stop):
        """Test advancing_status_label property."""
        assert sample_tour_stop.advancing_status_label == 'Non démarré'
        sample_tour_stop.advancing_status = 'completed'
        assert sample_tour_stop.advancing_status_label == 'Terminé'

    def test_tour_stop_advancing_status_color(self, app, sample_tour_stop):
        """Test advancing_status_color property."""
        assert sample_tour_stop.advancing_status_color == 'secondary'
        sample_tour_stop.advancing_status = 'issues'
        assert sample_tour_stop.advancing_status_color == 'danger'

    def test_cascade_delete_checklist(self, app, sample_tour_stop):
        """Test that checklist items are deleted when stop is deleted."""
        item = AdvancingChecklistItem(
            tour_stop_id=sample_tour_stop.id,
            category='admin',
            label='Test item',
            sort_order=0,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id

        db.session.delete(sample_tour_stop)
        db.session.commit()

        assert db.session.get(AdvancingChecklistItem, item_id) is None


# =============================================================================
# Service Tests
# =============================================================================

class TestAdvancingService:
    """Tests for AdvancingService."""

    def test_init_checklist_default(self, app, sample_tour_stop):
        """Test initializing checklist with default template."""
        AdvancingService.init_checklist(sample_tour_stop.id)

        items = AdvancingChecklistItem.query.filter_by(
            tour_stop_id=sample_tour_stop.id
        ).all()
        assert len(items) == 26

        db.session.refresh(sample_tour_stop)
        assert sample_tour_stop.advancing_status == 'in_progress'

    def test_init_checklist_custom_template(self, app, sample_tour_stop, manager_user):
        """Test initializing checklist from a custom template."""
        custom_items = [
            {'category': 'technique', 'label': 'Custom item 1'},
            {'category': 'admin', 'label': 'Custom item 2'},
        ]
        template = AdvancingTemplate(
            name='Custom',
            items=custom_items,
            created_by_id=manager_user.id,
        )
        db.session.add(template)
        db.session.commit()

        AdvancingService.init_checklist(sample_tour_stop.id, template.id)

        items = AdvancingChecklistItem.query.filter_by(
            tour_stop_id=sample_tour_stop.id
        ).all()
        assert len(items) == 2

    def test_init_checklist_prevents_double_init(self, app, sample_tour_stop):
        """Test that init_checklist raises ValueError if already initialized."""
        AdvancingService.init_checklist(sample_tour_stop.id)

        # Second init should raise ValueError
        with pytest.raises(ValueError, match="deja initialise"):
            AdvancingService.init_checklist(sample_tour_stop.id)

    def test_toggle_item(self, app, sample_tour_stop, manager_user):
        """Test toggling a checklist item via service."""
        AdvancingService.init_checklist(sample_tour_stop.id)
        item = AdvancingChecklistItem.query.filter_by(
            tour_stop_id=sample_tour_stop.id
        ).first()

        result = AdvancingService.toggle_item(item.id, manager_user.id)
        assert result.is_completed is True

    def test_update_item_notes(self, app, sample_tour_stop):
        """Test updating notes on a checklist item."""
        AdvancingService.init_checklist(sample_tour_stop.id)
        item = AdvancingChecklistItem.query.filter_by(
            tour_stop_id=sample_tour_stop.id
        ).first()

        AdvancingService.update_item_notes(item.id, 'Note de test')

        db.session.refresh(item)
        assert item.notes == 'Note de test'

    def test_get_advancing_summary(self, app, sample_tour, sample_tour_stop):
        """Test getting advancing summary for a tour."""
        AdvancingService.init_checklist(sample_tour_stop.id)

        summary = AdvancingService.get_advancing_summary(sample_tour.id)
        assert summary['total_stops'] >= 1

        stop_summary = summary['stops'][0]
        assert 'id' in stop_summary
        assert 'completion_pct' in stop_summary
        assert 'advancing_status' in stop_summary
        assert stop_summary['total_items'] == 26

    def test_add_rider_requirement(self, app, sample_tour_stop):
        """Test adding a rider requirement."""
        rider = AdvancingService.add_rider_requirement(
            tour_stop_id=sample_tour_stop.id,
            category='son',
            requirement='Console Yamaha CL5',
            quantity=1,
            is_mandatory=True,
        )

        assert rider.id is not None
        assert rider.category == RiderCategory.SON
        assert rider.requirement == 'Console Yamaha CL5'

    def test_confirm_rider_item(self, app, sample_tour_stop):
        """Test confirming a rider requirement."""
        rider = AdvancingService.add_rider_requirement(
            tour_stop_id=sample_tour_stop.id,
            category='lumiere',
            requirement='12x PAR LED',
            quantity=12,
            is_mandatory=True,
        )

        AdvancingService.confirm_rider_item(rider.id, 'OK, disponible')

        db.session.refresh(rider)
        assert rider.is_confirmed is True
        assert rider.venue_response == 'OK, disponible'

    def test_add_contact(self, app, sample_tour_stop):
        """Test adding a contact."""
        contact = AdvancingService.add_contact(
            tour_stop_id=sample_tour_stop.id,
            name='Marie Martin',
            role='Directrice technique',
            email='marie@salle.fr',
            phone='06 98 76 54 32',
            is_primary=True,
        )

        assert contact.id is not None
        assert contact.is_primary is True

    def test_add_contact_primary_unsets_others(self, app, sample_tour_stop):
        """Test that setting primary unsets other primary contacts."""
        c1 = AdvancingService.add_contact(
            tour_stop_id=sample_tour_stop.id,
            name='Contact 1',
            is_primary=True,
        )
        c2 = AdvancingService.add_contact(
            tour_stop_id=sample_tour_stop.id,
            name='Contact 2',
            is_primary=True,
        )

        db.session.refresh(c1)
        assert c1.is_primary is False
        assert c2.is_primary is True

    def test_update_production_specs(self, app, sample_tour_stop):
        """Test updating production specs."""
        AdvancingService.update_production_specs(
            tour_stop_id=sample_tour_stop.id,
            stage_width=12.0,
            stage_depth=10.0,
            stage_height=8.0,
            power_available='3x63A + 2x32A',
            rigging_points=24,
        )

        db.session.refresh(sample_tour_stop)
        assert sample_tour_stop.stage_width == 12.0
        assert sample_tour_stop.rigging_points == 24

    def test_update_advancing_status(self, app, sample_tour_stop):
        """Test manually updating advancing status."""
        AdvancingService.update_advancing_status(
            sample_tour_stop.id, 'waiting_venue'
        )

        db.session.refresh(sample_tour_stop)
        assert sample_tour_stop.advancing_status == 'waiting_venue'

    def test_create_template(self, app, manager_user):
        """Test creating a reusable template."""
        items = [
            {'category': 'technique', 'label': 'Son OK'},
            {'category': 'admin', 'label': 'Contrat'},
        ]
        template = AdvancingService.create_template(
            name='Mini template',
            description='Petit template test',
            items=items,
            created_by_id=manager_user.id,
        )

        assert template.id is not None
        assert len(template.items) == 2

    def test_get_stop_advancing_data(self, app, sample_tour_stop):
        """Test getting complete advancing data for a stop."""
        AdvancingService.init_checklist(sample_tour_stop.id)

        data = AdvancingService.get_stop_advancing_data(sample_tour_stop.id)

        assert data['total_items'] == 26
        assert data['completed_items'] == 0
        assert data['completion_pct'] == 0
        assert 'checklist_by_category' in data
        assert len(data['checklist_by_category']) == 7

    def test_delete_checklist(self, app, sample_tour_stop):
        """Test deleting/resetting a checklist."""
        AdvancingService.init_checklist(sample_tour_stop.id)
        assert AdvancingChecklistItem.query.filter_by(
            tour_stop_id=sample_tour_stop.id
        ).count() == 26

        AdvancingService.delete_checklist(sample_tour_stop.id)
        assert AdvancingChecklistItem.query.filter_by(
            tour_stop_id=sample_tour_stop.id
        ).count() == 0

        db.session.refresh(sample_tour_stop)
        assert sample_tour_stop.advancing_status == 'not_started'

    def test_auto_complete_status(self, app, sample_tour_stop, manager_user):
        """Test that completing all items auto-sets status to completed."""
        # Add only 2 items for simplicity
        for i in range(2):
            item = AdvancingChecklistItem(
                tour_stop_id=sample_tour_stop.id,
                category='technique',
                label=f'Item {i}',
                sort_order=i,
            )
            db.session.add(item)
        sample_tour_stop.advancing_status = 'in_progress'
        db.session.commit()

        items = AdvancingChecklistItem.query.filter_by(
            tour_stop_id=sample_tour_stop.id
        ).all()
        for item in items:
            AdvancingService.toggle_item(item.id, manager_user.id)

        db.session.refresh(sample_tour_stop)
        assert sample_tour_stop.advancing_status == 'completed'


# =============================================================================
# Route Tests
# =============================================================================

class TestAdvancingRoutes:
    """Tests for advancing blueprint routes.

    Uses actual client.post('/auth/login') for authentication,
    matching the pattern from test_routes.py. The session_transaction()
    approach in authenticated_client doesn't work with Flask-Login.
    """

    def _login(self, client):
        """Log in as the manager user."""
        client.post('/auth/login', data={
            'email': 'manager@test.com',
            'password': 'Manager123!',
        })

    def test_tour_dashboard_requires_auth(self, client, sample_tour):
        """Test that tour dashboard requires authentication."""
        response = client.get(f'/advancing/tour/{sample_tour.id}')
        assert response.status_code in (302, 401)

    def test_tour_dashboard_authenticated(self, client, manager_user, sample_tour):
        """Test tour dashboard renders for authenticated manager."""
        self._login(client)
        response = client.get(f'/advancing/tour/{sample_tour.id}')
        assert response.status_code == 200
        assert 'Advancing'.encode() in response.data

    def test_stop_detail_authenticated(self, client, manager_user, sample_tour_stop):
        """Test stop advancing detail renders."""
        self._login(client)
        response = client.get(f'/advancing/stop/{sample_tour_stop.id}')
        assert response.status_code == 200

    def test_init_checklist_post(self, client, manager_user, sample_tour_stop):
        """Test initializing checklist via POST."""
        self._login(client)
        response = client.post(
            f'/advancing/stop/{sample_tour_stop.id}/init',
            follow_redirects=True,
        )
        assert response.status_code == 200

        items = AdvancingChecklistItem.query.filter_by(
            tour_stop_id=sample_tour_stop.id
        ).count()
        assert items == 26

    def test_toggle_item_post(self, client, manager_user, sample_tour_stop):
        """Test toggling a checklist item via POST."""
        AdvancingService.init_checklist(sample_tour_stop.id)
        item = AdvancingChecklistItem.query.filter_by(
            tour_stop_id=sample_tour_stop.id
        ).first()

        self._login(client)
        response = client.post(
            f'/advancing/item/{item.id}/toggle',
            follow_redirects=True,
        )
        assert response.status_code == 200

    def test_contacts_page(self, client, manager_user, sample_tour_stop):
        """Test contacts page renders."""
        self._login(client)
        response = client.get(
            f'/advancing/stop/{sample_tour_stop.id}/contacts'
        )
        assert response.status_code == 200

    def test_rider_page(self, client, manager_user, sample_tour_stop):
        """Test rider page renders."""
        self._login(client)
        response = client.get(
            f'/advancing/stop/{sample_tour_stop.id}/rider'
        )
        assert response.status_code == 200

    def test_production_specs_page(self, client, manager_user, sample_tour_stop):
        """Test production specs page renders."""
        self._login(client)
        response = client.get(
            f'/advancing/stop/{sample_tour_stop.id}/production'
        )
        assert response.status_code == 200

    def test_templates_list_page(self, client, manager_user):
        """Test templates list page renders."""
        self._login(client)
        response = client.get('/advancing/templates')
        assert response.status_code == 200

    def test_add_contact_post(self, client, manager_user, sample_tour_stop):
        """Test adding a contact via POST."""
        self._login(client)
        response = client.post(
            f'/advancing/stop/{sample_tour_stop.id}/contacts',
            data={
                'name': 'Test Contact',
                'role': 'Régisseur',
                'email': 'test@salle.fr',
                'phone': '06 00 00 00 00',
                'is_primary': True,
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        contacts = AdvancingContact.query.filter_by(
            tour_stop_id=sample_tour_stop.id
        ).all()
        assert len(contacts) == 1
        assert contacts[0].name == 'Test Contact'

    def test_add_rider_post(self, client, manager_user, sample_tour_stop):
        """Test adding a rider requirement via POST."""
        self._login(client)
        response = client.post(
            f'/advancing/stop/{sample_tour_stop.id}/rider',
            data={
                'category': 'son',
                'requirement': 'Console Yamaha CL5',
                'quantity': 1,
                'is_mandatory': True,
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        riders = RiderRequirement.query.filter_by(
            tour_stop_id=sample_tour_stop.id
        ).all()
        assert len(riders) == 1
