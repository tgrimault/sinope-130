"""Unit tests for Neviweb130Thermostat update() helper methods.

Tests:
  - _fetch_attributes: returns a dict (mock client)
  - _handle_error: returns True for error dicts, False for clean data
  - _parse_common_state: assigns _cur_temp, _target_temp, _operation_mode correctly
  - _parse_dr_state: assigns _drsetpoint_status, _drstatus_active correctly
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.neviweb130.const import (
    ATTR_BACKLIGHT,
    ATTR_DISPLAY2,
    ATTR_DRSETPOINT,
    ATTR_DRSTATUS,
    ATTR_KEYPAD,
    ATTR_OUTPUT_PERCENT_DISPLAY,
    ATTR_ROOM_SETPOINT,
    ATTR_ROOM_SETPOINT_MAX,
    ATTR_ROOM_SETPOINT_MIN,
    ATTR_ROOM_TEMPERATURE,
    ATTR_SYSTEM_MODE,
    ATTR_TEMP,
    ATTR_TIME_FORMAT,
    ATTR_WATTAGE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_device_info(device_id: int = 111, model: int = 1123):
    return {
        "id": device_id,
        "name": "Test Thermostat",
        "sku": "TH1123ZB",
        "location$id": 67890,
        "signature": {
            "model": model,
            "modelCfg": 0,
            "protocol": "zigbee",
            "softVersion": {"major": 1, "middle": 2, "minor": 3},
        },
    }


def make_client():
    client = MagicMock()
    client.scoped_unique_id.side_effect = lambda device_id: str(device_id)
    client._account_prefix = ""
    client._is_primary = True
    client._network_name = "Home"
    client._network_name2 = None
    client._network_name3 = None
    return client


def make_hass(safe_mode="-"):
    hass = MagicMock()
    hass.data = {
        "neviweb130": {
            "safe_mode": safe_mode,
            "translation_cache": None,
            "ready": False,
        }
    }
    hass.config.language = "en"
    return hass


def make_thermostat(client=None, hass=None, model: int = 1123):
    from custom_components.neviweb130.climate import Neviweb130Thermostat

    if client is None:
        client = make_client()
    if hass is None:
        hass = make_hass()
    info = make_device_info(model=model)
    entity = Neviweb130Thermostat(info, "Test Thermostat", "TH1123ZB", "1.0.0", 67890, client)
    entity.hass = hass
    return entity


def minimal_device_data():
    """Return a minimal valid device_data dict for _parse_common_state."""
    return {
        ATTR_ROOM_TEMPERATURE: {"value": 21.5},
        ATTR_ROOM_SETPOINT: 20.0,
        ATTR_ROOM_SETPOINT_MIN: 5,
        ATTR_ROOM_SETPOINT_MAX: 30,
        ATTR_TEMP: "celsius",
        ATTR_TIME_FORMAT: "24h",
        ATTR_OUTPUT_PERCENT_DISPLAY: 50,
        ATTR_KEYPAD: "unlocked",
        ATTR_BACKLIGHT: "auto",
        ATTR_SYSTEM_MODE: "heat",
        ATTR_DISPLAY2: "setpoint",
        ATTR_WATTAGE: 1000,
    }


# ===========================================================================
# _fetch_attributes
# ===========================================================================

@pytest.mark.unit
class TestFetchAttributes:
    """_fetch_attributes should return a dict from the client."""

    def test_returns_dict_from_client(self):
        client = make_client()
        expected = minimal_device_data()
        client.get_device_attributes.return_value = expected

        t = make_thermostat(client)
        result = t._fetch_attributes()

        assert isinstance(result, dict)
        assert result is expected

    def test_calls_get_device_attributes_with_device_id(self):
        client = make_client()
        client.get_device_attributes.return_value = minimal_device_data()

        t = make_thermostat(client)
        t._fetch_attributes()

        client.get_device_attributes.assert_called_once()
        call_args = client.get_device_attributes.call_args
        assert call_args[0][0] == "111"  # device id

    def test_uses_safe_get_when_safe_mode_matches(self):
        """When safe_mode == device id, safe_get_device_attributes is used."""
        client = make_client()
        hass = make_hass(safe_mode="111")  # matches device id
        client.get_device_attributes.return_value = minimal_device_data()

        t = make_thermostat(client, hass)

        # Patch safe_get_device_attributes to track calls
        from unittest.mock import patch
        with patch(
            "custom_components.neviweb130.climate.safe_get_device_attributes",
            return_value=minimal_device_data(),
        ) as mock_safe:
            result = t._fetch_attributes()
            mock_safe.assert_called_once()
            client.get_device_attributes.assert_not_called()

    def test_uses_regular_get_when_safe_mode_does_not_match(self):
        """When safe_mode != device id, regular get_device_attributes is used."""
        client = make_client()
        hass = make_hass(safe_mode="-")
        client.get_device_attributes.return_value = minimal_device_data()

        t = make_thermostat(client, hass)

        from unittest.mock import patch
        with patch(
            "custom_components.neviweb130.climate.safe_get_device_attributes",
        ) as mock_safe:
            t._fetch_attributes()
            mock_safe.assert_not_called()
            client.get_device_attributes.assert_called_once()


# ===========================================================================
# _handle_error
# ===========================================================================

@pytest.mark.unit
class TestHandleError:
    """_handle_error returns True for error dicts, False for clean data."""

    def test_returns_true_for_error_key(self):
        t = make_thermostat()
        result = t._handle_error({"error": {"code": "USRSESSEXP"}})
        assert result is True

    def test_returns_true_for_error_code_key(self):
        t = make_thermostat()
        result = t._handle_error({"errorCode": "ReadTimeout"})
        assert result is True

    def test_returns_false_for_clean_data(self):
        t = make_thermostat()
        result = t._handle_error(minimal_device_data())
        assert result is False

    def test_returns_false_for_empty_dict(self):
        t = make_thermostat()
        result = t._handle_error({})
        assert result is False

    def test_calls_log_error_for_error_key(self):
        client = make_client()
        t = make_thermostat(client)
        # log_error calls client.reconnect for USRSESSEXP
        t._handle_error({"error": {"code": "USRSESSEXP"}})
        client.reconnect.assert_called_once()

    def test_does_not_call_log_error_for_clean_data(self):
        client = make_client()
        t = make_thermostat(client)
        t._handle_error(minimal_device_data())
        client.reconnect.assert_not_called()

    def test_returns_true_for_unknown_error_code(self):
        t = make_thermostat()
        result = t._handle_error({"errorCode": "SomeOtherError"})
        assert result is True


# ===========================================================================
# _parse_common_state
# ===========================================================================

@pytest.mark.unit
class TestParseCommonState:
    """_parse_common_state assigns instance variables from device data."""

    def test_assigns_cur_temp(self):
        t = make_thermostat()
        data = minimal_device_data()
        t._parse_common_state(data)
        assert t._cur_temp == 21.5

    def test_assigns_target_temp(self):
        t = make_thermostat()
        data = minimal_device_data()
        t._parse_common_state(data)
        assert t._target_temp == 20.0

    def test_assigns_operation_mode(self):
        t = make_thermostat()
        data = minimal_device_data()
        t._parse_common_state(data)
        assert t._operation_mode == "heat"

    def test_assigns_min_temp(self):
        t = make_thermostat()
        data = minimal_device_data()
        t._parse_common_state(data)
        assert t._min_temp == 5

    def test_assigns_max_temp(self):
        t = make_thermostat()
        data = minimal_device_data()
        t._parse_common_state(data)
        assert t._max_temp == 30

    def test_assigns_temperature_format(self):
        t = make_thermostat()
        data = minimal_device_data()
        t._parse_common_state(data)
        assert t._temperature_format == "celsius"

    def test_assigns_time_format(self):
        t = make_thermostat()
        data = minimal_device_data()
        t._parse_common_state(data)
        assert t._time_format == "24h"

    def test_assigns_heat_level(self):
        t = make_thermostat()
        data = minimal_device_data()
        t._parse_common_state(data)
        assert t._heat_level == 50

    def test_assigns_keypad(self):
        t = make_thermostat()
        data = minimal_device_data()
        t._parse_common_state(data)
        assert t._keypad == "unlocked"

    def test_assigns_backlight(self):
        t = make_thermostat()
        data = minimal_device_data()
        t._parse_common_state(data)
        assert t._backlight == "auto"

    def test_cur_temp_clamped_to_min(self):
        """cur_temp must be >= min_temp."""
        t = make_thermostat()
        data = minimal_device_data()
        data[ATTR_ROOM_TEMPERATURE] = {"value": 2.0}  # below min of 5
        data[ATTR_ROOM_SETPOINT_MIN] = 5
        t._parse_common_state(data)
        assert t._cur_temp == 5

    def test_none_room_temp_keeps_previous(self):
        """None room temperature value keeps the previous _cur_temp."""
        t = make_thermostat()
        t._cur_temp = 19.0
        data = minimal_device_data()
        data[ATTR_ROOM_TEMPERATURE] = {"value": None}
        t._parse_common_state(data)
        assert t._cur_temp == max(19.0, data[ATTR_ROOM_SETPOINT_MIN])

    def test_assigns_wattage_for_non_low_voltage(self):
        t = make_thermostat(model=1123)
        assert t._is_low_voltage is False
        data = minimal_device_data()
        t._parse_common_state(data)
        assert t._wattage == 1000


# ===========================================================================
# _parse_dr_state
# ===========================================================================

@pytest.mark.unit
class TestParseDrState:
    """_parse_dr_state assigns DR setpoint and DR status fields."""

    def test_assigns_drsetpoint_status(self):
        t = make_thermostat()
        data = {
            ATTR_DRSETPOINT: {"status": "active", "value": 18.0},
        }
        t._parse_dr_state(data)
        assert t._drsetpoint_status == "active"

    def test_assigns_drsetpoint_value(self):
        t = make_thermostat()
        data = {
            ATTR_DRSETPOINT: {"status": "active", "value": 18.0},
        }
        t._parse_dr_state(data)
        assert t._drsetpoint_value == 18.0

    def test_drsetpoint_none_value_defaults_to_zero(self):
        t = make_thermostat()
        data = {
            ATTR_DRSETPOINT: {"status": "off", "value": None},
        }
        t._parse_dr_state(data)
        assert t._drsetpoint_value == 0

    def test_assigns_drstatus_active(self):
        t = make_thermostat()
        data = {
            ATTR_DRSTATUS: {
                "drActive": "on",
                "optOut": "off",
                "setpoint": 18.0,
                "powerAbsolute": 0,
                "powerRelative": 0,
            }
        }
        t._parse_dr_state(data)
        assert t._drstatus_active == "on"

    def test_assigns_drstatus_optout(self):
        t = make_thermostat()
        data = {
            ATTR_DRSTATUS: {
                "drActive": "on",
                "optOut": "off",
                "setpoint": 18.0,
                "powerAbsolute": 0,
                "powerRelative": 0,
            }
        }
        t._parse_dr_state(data)
        assert t._drstatus_optout == "off"

    def test_no_drsetpoint_key_leaves_state_unchanged(self):
        t = make_thermostat()
        t._drsetpoint_status = "original"
        t._parse_dr_state({})
        assert t._drsetpoint_status == "original"

    def test_no_drstatus_key_leaves_state_unchanged(self):
        t = make_thermostat()
        t._drstatus_active = "original"
        t._parse_dr_state({})
        assert t._drstatus_active == "original"
