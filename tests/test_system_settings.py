# =============================================================================
# Tour Manager - System Settings Model Tests
# =============================================================================

import pytest
from app.extensions import db
from app.models.system_settings import SystemSettings


class TestSystemSettingsGet:
    """Tests for SystemSettings.get()."""

    def test_get_nonexistent_returns_default(self, app):
        result = SystemSettings.get('nonexistent_key')
        assert result is None

    def test_get_nonexistent_with_custom_default(self, app):
        result = SystemSettings.get('nonexistent_key', default='fallback')
        assert result == 'fallback'

    def test_get_existing_value(self, app):
        SystemSettings.set('test_key', 'test_value')
        db.session.commit()
        result = SystemSettings.get('test_key')
        assert result == 'test_value'


class TestSystemSettingsSet:
    """Tests for SystemSettings.set()."""

    def test_set_creates_new_setting(self, app):
        setting = SystemSettings.set('new_key', 'new_value')
        db.session.commit()
        assert setting.key == 'new_key'
        assert setting.value == 'new_value'
        assert setting.is_encrypted is False

    def test_set_updates_existing_setting(self, app):
        SystemSettings.set('update_key', 'old_value')
        db.session.commit()
        SystemSettings.set('update_key', 'new_value')
        db.session.commit()
        result = SystemSettings.get('update_key')
        assert result == 'new_value'

    def test_set_with_encryption(self, app):
        SystemSettings.set('secret_key', 'secret_value', encrypted=True)
        db.session.commit()
        # The raw stored value should be encrypted
        setting = SystemSettings.query.filter_by(key='secret_key').first()
        assert setting.is_encrypted is True
        assert setting.value != 'secret_value'
        # But get() should decrypt it
        result = SystemSettings.get('secret_key')
        assert result == 'secret_value'

    def test_set_with_user_id(self, app, manager_user):
        setting = SystemSettings.set('tracked_key', 'value', user_id=manager_user.id)
        db.session.commit()
        assert setting.updated_by_id == manager_user.id


class TestSystemSettingsDelete:
    """Tests for SystemSettings.delete()."""

    def test_delete_existing_returns_true(self, app):
        SystemSettings.set('to_delete', 'value')
        db.session.commit()
        result = SystemSettings.delete('to_delete')
        db.session.commit()
        assert result is True
        assert SystemSettings.get('to_delete') is None

    def test_delete_nonexistent_returns_false(self, app):
        result = SystemSettings.delete('nonexistent')
        assert result is False


class TestSystemSettingsMailConfig:
    """Tests for mail configuration methods."""

    def test_get_mail_config_returns_dict(self, app):
        config = SystemSettings.get_mail_config()
        assert isinstance(config, dict)
        assert 'MAIL_SERVER' in config
        assert 'MAIL_PORT' in config
        assert 'MAIL_USERNAME' in config

    def test_get_mail_config_timestamp_default(self, app):
        ts = SystemSettings.get_mail_config_timestamp()
        assert ts == 0

    def test_touch_mail_config_updates_timestamp(self, app):
        SystemSettings.touch_mail_config()
        db.session.commit()
        ts = SystemSettings.get_mail_config_timestamp()
        assert ts > 0

    def test_get_mail_config_timestamp_invalid_value(self, app):
        SystemSettings.set('MAIL_CONFIG_UPDATED_AT', 'not_a_number')
        db.session.commit()
        ts = SystemSettings.get_mail_config_timestamp()
        assert ts == 0


class TestSystemSettingsRepr:
    """Tests for __repr__."""

    def test_repr(self, app):
        setting = SystemSettings.set('repr_key', 'value')
        assert 'repr_key' in repr(setting)
