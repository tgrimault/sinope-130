"""Unit tests for ERROR_HANDLERS lookup table and log_error() dispatcher.

Validates:
- Each handler function produces the correct side-effects on the entity
- log_error() dispatches to the correct handler for each known error code
- Unknown error codes fall through to a warning log without raising
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

import custom_components.neviweb130.climate as climate_module
from custom_components.neviweb130.climate import (
    ERROR_HANDLERS,
    _handle_action_not_supported,
    _handle_attr_not_supported,
    _handle_comm_timeout,
    _handle_day_req_max,
    _handle_device_busy,
    _handle_device_error,
    _handle_device_unavailable,
    _handle_maintenance,
    _handle_service_error,
    _handle_service_unauthorized,
    _handle_session_exceeded,
    _handle_session_expired,
    _handle_timeout_error,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_entity(notify="logging"):
    """Build a minimal mock entity for handler testing."""
    entity = MagicMock()
    entity._name = "Test Thermostat"
    entity._id = 123
    entity._sku = "TH1123ZB"
    entity._device_model = 1123
    entity._active = True
    entity._snooze = 0.0
    entity.hass.data = {
        "neviweb130": {
            "safe_mode": "-",
        }
    }
    # Patch the module-level NOTIFY used by handlers
    return entity


# ---------------------------------------------------------------------------
# Tests for individual handler functions
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestHandlerFunctions:
    """Test each handler function directly with a mock entity."""

    def test_handle_session_expired_calls_reconnect(self):
        entity = make_entity()
        with patch.object(climate_module, "NOTIFY", "logging"):
            _handle_session_expired(entity)
        entity._client.reconnect.assert_called_once()

    def test_handle_session_expired_does_not_deactivate(self):
        entity = make_entity()
        with patch.object(climate_module, "NOTIFY", "logging"):
            _handle_session_expired(entity)
        assert entity._active is True

    def test_handle_session_expired_notifies_when_notify_notification(self):
        entity = make_entity()
        with patch.object(climate_module, "NOTIFY", "notification"):
            _handle_session_expired(entity)
        entity.notify_ha.assert_called_once()
        entity._client.reconnect.assert_called_once()

    def test_handle_day_req_max_does_not_reconnect(self):
        entity = make_entity()
        _handle_day_req_max(entity)
        entity._client.reconnect.assert_not_called()
        assert entity._active is True

    def test_handle_timeout_error_does_not_reconnect(self):
        entity = make_entity()
        _handle_timeout_error(entity)
        entity._client.reconnect.assert_not_called()

    def test_handle_maintenance_calls_reconnect(self):
        entity = make_entity()
        _handle_maintenance(entity)
        entity._client.reconnect.assert_called_once()
        entity.notify_ha.assert_called_once()

    def test_handle_session_exceeded_calls_reconnect(self):
        entity = make_entity()
        _handle_session_exceeded(entity)
        entity._client.reconnect.assert_called_once()
        entity.notify_ha.assert_called_once()

    def test_handle_attr_not_supported_enables_safe_mode(self):
        entity = make_entity()
        _handle_attr_not_supported(entity)
        assert entity.hass.data["neviweb130"]["safe_mode"] == entity._id

    def test_handle_attr_not_supported_skips_if_safe_mode_already_set(self):
        entity = make_entity()
        entity.hass.data["neviweb130"]["safe_mode"] = 999
        _handle_attr_not_supported(entity)
        # Should not overwrite existing safe_mode
        assert entity.hass.data["neviweb130"]["safe_mode"] == 999

    def test_handle_action_not_supported_enables_safe_mode(self):
        entity = make_entity()
        _handle_action_not_supported(entity)
        assert entity.hass.data["neviweb130"]["safe_mode"] == entity._id

    def test_handle_comm_timeout_does_not_reconnect(self):
        entity = make_entity()
        _handle_comm_timeout(entity)
        entity._client.reconnect.assert_not_called()

    def test_handle_service_error_does_not_reconnect(self):
        entity = make_entity()
        _handle_service_error(entity)
        entity._client.reconnect.assert_not_called()

    def test_handle_device_busy_does_not_reconnect(self):
        entity = make_entity()
        _handle_device_busy(entity)
        entity._client.reconnect.assert_not_called()

    def test_handle_device_unavailable_sets_active_false(self):
        entity = make_entity()
        with patch.object(climate_module, "NOTIFY", "logging"):
            _handle_device_unavailable(entity)
        assert entity._active is False

    def test_handle_device_unavailable_sets_snooze(self):
        entity = make_entity()
        before = time.time()
        with patch.object(climate_module, "NOTIFY", "logging"):
            _handle_device_unavailable(entity)
        assert entity._snooze >= before

    def test_handle_device_unavailable_does_not_reconnect(self):
        entity = make_entity()
        with patch.object(climate_module, "NOTIFY", "logging"):
            _handle_device_unavailable(entity)
        entity._client.reconnect.assert_not_called()

    def test_handle_device_unavailable_notifies_when_notify_notification(self):
        entity = make_entity()
        with patch.object(climate_module, "NOTIFY", "notification"):
            _handle_device_unavailable(entity)
        entity.notify_ha.assert_called_once()

    def test_handle_device_error_does_not_reconnect(self):
        entity = make_entity()
        _handle_device_error(entity)
        entity._client.reconnect.assert_not_called()

    def test_handle_service_unauthorized_does_not_reconnect(self):
        entity = make_entity()
        _handle_service_unauthorized(entity)
        entity._client.reconnect.assert_not_called()


# ---------------------------------------------------------------------------
# Tests for ERROR_HANDLERS dict structure
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestErrorHandlersDict:
    """Verify the ERROR_HANDLERS dict is complete and well-formed."""

    EXPECTED_CODES = {
        "USRSESSEXP",
        "ACCDAYREQMAX",
        "TimeoutError",
        "MAINTENANCE",
        "ACCSESSEXC",
        "DVCATTRNSPTD",
        "DVCACTNSPTD",
        "DVCCOMMTO",
        "SVCERR",
        "DVCBUSY",
        "DVCUNVLB",
        "DVCERR",
        "SVCUNAUTH",
    }

    def test_all_expected_codes_present(self):
        missing = self.EXPECTED_CODES - set(ERROR_HANDLERS.keys())
        assert not missing, f"Missing error codes in ERROR_HANDLERS: {missing}"

    def test_all_values_are_callable(self):
        for code, handler in ERROR_HANDLERS.items():
            assert callable(handler), f"Handler for {code!r} is not callable"

    def test_usrsessexp_maps_to_session_expired_handler(self):
        assert ERROR_HANDLERS["USRSESSEXP"] is _handle_session_expired

    def test_dvcunvlb_maps_to_device_unavailable_handler(self):
        assert ERROR_HANDLERS["DVCUNVLB"] is _handle_device_unavailable


# ---------------------------------------------------------------------------
# Tests for log_error() dispatcher
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestLogErrorDispatcher:
    """Test log_error() dispatches correctly and handles unknown codes."""

    def _make_thermostat(self):
        """Create a real Neviweb130Thermostat with mocked dependencies."""
        from tests.test_preservation import make_thermostat
        return make_thermostat(1123)

    def test_usrsessexp_calls_reconnect(self):
        t = self._make_thermostat()
        with patch.object(climate_module, "NOTIFY", "logging"):
            t.log_error("USRSESSEXP")
        t._client.reconnect.assert_called_once()

    def test_dvcunvlb_sets_active_false(self):
        t = self._make_thermostat()
        with patch.object(climate_module, "NOTIFY", "logging"):
            t.log_error("DVCUNVLB")
        assert t._active is False

    def test_accdayreqmax_does_not_reconnect(self):
        t = self._make_thermostat()
        t.log_error("ACCDAYREQMAX")
        t._client.reconnect.assert_not_called()
        assert t._active is True

    def test_unknown_error_does_not_raise(self):
        t = self._make_thermostat()
        # Must not raise for any unknown code
        t.log_error("SOME_UNKNOWN_ERROR_XYZ_999")

    def test_unknown_error_does_not_call_reconnect(self):
        t = self._make_thermostat()
        t.log_error("TOTALLY_UNKNOWN_CODE")
        t._client.reconnect.assert_not_called()

    def test_log_error_has_no_elif(self):
        """Structural check: log_error source must not contain elif."""
        import inspect
        from custom_components.neviweb130.climate import Neviweb130Thermostat
        source = inspect.getsource(Neviweb130Thermostat.log_error)
        assert "elif" not in source, "log_error() must not contain elif branches"

    def test_each_known_code_dispatches_without_raising(self):
        """Smoke test: every registered error code must not raise."""
        t = self._make_thermostat()
        for code in ERROR_HANDLERS:
            with patch.object(climate_module, "NOTIFY", "logging"):
                t.log_error(code)  # must not raise
