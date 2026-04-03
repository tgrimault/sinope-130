"""Class-level unit tests for Neviweb130Thermostat base class.

These tests cover constructor initialization, property logic, and service
method behaviour — complementing the existing contract-level tests in
test_ha_interface.py and test_climate_set_methods.py.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from homeassistant.components.climate.const import HVACMode, HVACAction, PRESET_AWAY, PRESET_HOME, PRESET_NONE

from tests.conftest import make_device_info


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_thermostat(mock_hass, mock_client, model=1123, firmware="1.2.3"):
    from custom_components.neviweb130.climate.base import Neviweb130Thermostat
    device_info = make_device_info(111, model, "Living Room", "TH1123ZB")
    t = Neviweb130Thermostat(device_info, "Living Room", "TH1123ZB", firmware, 67890, mock_client)
    t.hass = mock_hass
    return t


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestThermostatConstructor:
    def test_name_set(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t._name == "Living Room"

    def test_sku_set(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t._sku == "TH1123ZB"

    def test_firmware_set(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t._firmware == "1.2.3"

    def test_id_is_string(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t._id == "111"

    def test_active_defaults_true(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t._active is True

    def test_target_temp_default(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t._target_temp == 20.0

    def test_min_temp_default(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t._min_temp == 5

    def test_max_temp_default(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t._max_temp == 30

    def test_is_floor_false_for_base_model(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=1123)
        assert t._is_floor is False

    def test_is_floor_true_for_floor_model(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=737)
        assert t._is_floor is True

    def test_is_wifi_false_for_zigbee(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=1123)
        assert t._is_wifi is False

    def test_is_wifi_true_for_wifi_model(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=1510)
        assert t._is_wifi is True

    def test_is_HP_false_for_base(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=1123)
        assert t._is_HP is False

    def test_is_HP_true_for_hp_model(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=6810)
        assert t._is_HP is True

    def test_is_HC_false_for_base(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=1123)
        assert t._is_HC is False

    def test_is_HC_true_for_heatcool_model(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=6727)
        assert t._is_HC is True

    def test_location_is_string(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t._location == "67890"


# ---------------------------------------------------------------------------
# HA interface properties
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestThermostatProperties:
    def test_unique_id_delegates_to_client(self, mock_hass, mock_client):
        # conftest side_effect: scoped_unique_id(device_id) -> str(device_id)
        t = _make_thermostat(mock_hass, mock_client)
        assert t.unique_id == "111"
        mock_client.scoped_unique_id.assert_called_once_with("111")

    def test_name_property(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t.name == "Living Room"

    def test_current_temperature_returns_cur_temp(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._cur_temp = 21.5
        assert t.current_temperature == 21.5

    def test_target_temperature_returns_target(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._target_temp = 22.0
        t._drsetpoint_value = 0
        t._min_temp = 5
        t._max_temp = 30
        assert t.target_temperature == 22.0

    def test_target_temperature_clamped_to_min(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._target_temp = 3.0
        t._drsetpoint_value = 0
        t._min_temp = 5
        t._max_temp = 30
        assert t.target_temperature == 5

    def test_target_temperature_clamped_to_max(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._target_temp = 35.0
        t._drsetpoint_value = 0
        t._min_temp = 5
        t._max_temp = 30
        assert t.target_temperature == 30

    def test_target_temperature_applies_dr_delta(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._target_temp = 20.0
        t._drsetpoint_value = -2
        t._min_temp = 5
        t._max_temp = 30
        assert t.target_temperature == 18.0

    def test_min_temp_property(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._min_temp = 7
        assert t.min_temp == 7

    def test_max_temp_property(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._max_temp = 28
        assert t.max_temp == 28

    def test_hvac_mode_off(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._operation_mode = HVACMode.OFF
        assert t.hvac_mode == HVACMode.OFF

    def test_hvac_mode_heat(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._operation_mode = "heat"
        assert t.hvac_mode == HVACMode.HEAT

    def test_hvac_mode_auto(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._operation_mode = HVACMode.AUTO
        assert t.hvac_mode == HVACMode.AUTO

    def test_hvac_modes_zigbee_returns_heat_off(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=1123)
        modes = t.hvac_modes
        assert HVACMode.HEAT in modes
        assert HVACMode.OFF in modes
        assert HVACMode.AUTO not in modes

    def test_hvac_modes_wifi_includes_auto(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=1510)
        modes = t.hvac_modes
        assert HVACMode.AUTO in modes

    def test_preset_mode_home(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._occupancy = PRESET_HOME
        assert t.preset_mode == PRESET_HOME

    def test_preset_mode_away(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._occupancy = PRESET_AWAY
        assert t.preset_mode == PRESET_AWAY

    def test_preset_mode_none(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._occupancy = "other"
        assert t.preset_mode == PRESET_NONE

    def test_preset_modes_zigbee(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=1123)
        modes = t.preset_modes
        assert PRESET_AWAY in modes
        assert PRESET_NONE in modes

    def test_preset_modes_wifi_includes_home(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=1510)
        modes = t.preset_modes
        assert PRESET_HOME in modes

    def test_is_em_heat_false_by_default(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t.is_em_heat is False

    def test_is_em_heat_true_when_slave(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._em_heat = "slave"
        assert t.is_em_heat is True

    def test_is_em_heat_true_when_aux_cycle(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._aux_cycle_length = 15
        assert t.is_em_heat is True


# ---------------------------------------------------------------------------
# icon_type logic
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestIconType:
    def test_off_mode_returns_heat_off(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=1123)
        t._operation_mode = HVACMode.OFF
        assert t.icon_type == "/local/neviweb130/heat-off.png"

    def test_off_mode_floor_returns_floor_off(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=737)
        t._operation_mode = HVACMode.OFF
        assert t.icon_type == "/local/neviweb130/floor-off.png"

    def test_zero_demand_returns_heat_0(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=1123)
        t._operation_mode = HVACMode.HEAT
        t._heat_level = 0
        assert t.icon_type == "/local/neviweb130/heat-0.png"

    def test_high_demand_returns_heat_5(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=1123)
        t._operation_mode = HVACMode.HEAT
        t._heat_level = 100
        assert t.icon_type == "/local/neviweb130/heat-5.png"

    def test_auto_mode_uses_heat_auto_prefix(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client, model=1123)
        t._operation_mode = HVACMode.AUTO
        t._heat_level = 0
        assert "heat-auto" in t.icon_type


# ---------------------------------------------------------------------------
# extra_state_attributes
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestThermostatExtraStateAttributes:
    def test_returns_dict(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert isinstance(t.extra_state_attributes, dict)

    def test_contains_sku(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t.extra_state_attributes["sku"] == "TH1123ZB"

    def test_contains_id(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t.extra_state_attributes["id"] == "111"

    def test_contains_firmware(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t.extra_state_attributes["firmware"] == "1.2.3"

    def test_contains_activation(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t.extra_state_attributes["activation"] is True

    def test_contains_heat_level(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._heat_level = 42
        assert t.extra_state_attributes["heat_level"] == 42

    def test_contains_eco_status(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert "eco_status" in t.extra_state_attributes

    def test_contains_outdoor_temp(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert "outdoor_temp" in t.extra_state_attributes


# ---------------------------------------------------------------------------
# _parse_common_state
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestParseCommonState:
    def _make_data(self):
        # Keys must match the actual ATTR_* const values from const.py
        return {
            "roomTemperature": {"value": 21.5},   # ATTR_ROOM_TEMPERATURE
            "roomSetpoint": 20.0,                  # ATTR_ROOM_SETPOINT
            "roomSetpointMin": 5,                  # ATTR_ROOM_SETPOINT_MIN
            "roomSetpointMax": 30,                 # ATTR_ROOM_SETPOINT_MAX
            "temperatureFormat": "celsius",        # ATTR_TEMP
            "timeFormat": "24h",                   # ATTR_TIME_FORMAT
            "config2ndDisplay": "setpoint",        # ATTR_DISPLAY2
            "outputPercentDisplay": 50,            # ATTR_OUTPUT_PERCENT_DISPLAY
            "lockKeypad": "unlocked",              # ATTR_KEYPAD
            "backlightAdaptive": "auto",           # ATTR_BACKLIGHT
            "cycleLength": 15,                     # ATTR_CYCLE_LENGTH
            "rssi": -65,                           # ATTR_RSSI
            "systemMode": "heat",                  # ATTR_SYSTEM_MODE
            "loadConnected": 1500,                 # ATTR_WATTAGE
        }

    def test_assigns_cur_temp(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        data = self._make_data()
        t._parse_common_state(data)
        assert t._cur_temp == 21.5

    def test_assigns_target_temp(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        data = self._make_data()
        t._parse_common_state(data)
        assert t._target_temp == 20.0

    def test_assigns_min_temp(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        data = self._make_data()
        t._parse_common_state(data)
        assert t._min_temp == 5

    def test_assigns_max_temp(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        data = self._make_data()
        t._parse_common_state(data)
        assert t._max_temp == 30

    def test_assigns_operation_mode(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        data = self._make_data()
        t._parse_common_state(data)
        assert t._operation_mode == "heat"

    def test_assigns_heat_level(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        data = self._make_data()
        t._parse_common_state(data)
        assert t._heat_level == 50

    def test_cur_temp_none_keeps_previous(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._cur_temp = 19.0
        data = self._make_data()
        data["roomTemperature"] = {"value": None}
        t._parse_common_state(data)
        assert t._cur_temp == 19.0


# ---------------------------------------------------------------------------
# _parse_dr_state
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestParseDrState:
    def test_assigns_drsetpoint_status(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        data = {
            "drSetpoint": {"status": "active", "value": -2},
            "drStatus": {"drActive": "on", "optOut": "off", "setpoint": "on",
                         "powerAbsolute": "off", "powerRelative": "off"},
        }
        t._parse_dr_state(data)
        assert t._drsetpoint_status == "active"
        assert t._drsetpoint_value == -2

    def test_assigns_drstatus_active(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        data = {
            "drSetpoint": {"status": "off", "value": 0},
            "drStatus": {"drActive": "on", "optOut": "off", "setpoint": "off",
                         "powerAbsolute": "off", "powerRelative": "off"},
        }
        t._parse_dr_state(data)
        assert t._drstatus_active == "on"

    def test_drsetpoint_none_value_defaults_to_zero(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        data = {"drSetpoint": {"status": "off", "value": None}}
        t._parse_dr_state(data)
        assert t._drsetpoint_value == 0


# ---------------------------------------------------------------------------
# _handle_error
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestHandleError:
    def test_returns_false_for_clean_data(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t._handle_error({"roomTemperature": {"value": 21.0}}) is False

    def test_returns_true_for_error_key(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        with patch.object(t, "log_error"):
            assert t._handle_error({"error": {"code": "DVCUNVLB"}}) is True

    def test_calls_log_error_with_code(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        with patch.object(t, "log_error") as mock_log:
            t._handle_error({"error": {"code": "USRSESSEXP"}})
            mock_log.assert_called_once_with("USRSESSEXP")

    def test_returns_true_for_errorCode_key(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        assert t._handle_error({"errorCode": "ReadTimeout"}) is True


# ---------------------------------------------------------------------------
# Service methods
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestThermostatServiceMethods:
    def test_set_activation_deactivates(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t.set_activation({"active": False})
        assert t._active is False

    def test_set_activation_reactivates(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t._active = False
        t.set_activation({"active": True})
        assert t._active is True

    def test_set_second_display_calls_client(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t.set_second_display({"id": "111", "display": "outsideTemp"})
        mock_client.set_second_display.assert_called_once_with("111", "outsideTemp")

    def test_set_backlight_calls_client(self, mock_hass, mock_client):
        # Zigbee thermostat (model 1123, not wifi): "auto" maps to "onActive", is_wifi=False
        t = _make_thermostat(mock_hass, mock_client)
        t.set_backlight({"id": "111", "level": "auto"})
        mock_client.set_backlight.assert_called_once_with("111", "onActive", False)

    def test_set_keypad_lock_calls_client(self, mock_hass, mock_client):
        # Zigbee thermostat: lock value passed through unchanged, is_wifi=False
        t = _make_thermostat(mock_hass, mock_client)
        t.set_keypad_lock({"id": "111", "lock": "locked"})
        mock_client.set_keypad_lock.assert_called_once_with("111", "locked", False)
        assert t._keypad == "locked"

    def test_set_time_format_calls_client(self, mock_hass, mock_client):
        # set_time_format expects ATTR_TIME key (integer 12 or 24)
        from custom_components.neviweb130.const import ATTR_TIME
        t = _make_thermostat(mock_hass, mock_client)
        t.set_time_format({"id": "111", ATTR_TIME: 12})
        mock_client.set_time_format.assert_called_once_with("111", "12h")

    def test_set_temperature_format_calls_client(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t.set_temperature_format({"id": "111", "temp": "fahrenheit"})
        mock_client.set_temperature_format.assert_called_once_with("111", "fahrenheit")

    def test_set_setpoint_max_calls_client(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t.set_setpoint_max({"id": "111", "temp": 28})
        mock_client.set_setpoint_max.assert_called_once_with("111", 28)

    def test_set_setpoint_min_calls_client(self, mock_hass, mock_client):
        t = _make_thermostat(mock_hass, mock_client)
        t.set_setpoint_min({"id": "111", "temp": 7})
        mock_client.set_setpoint_min.assert_called_once_with("111", 7)

    def test_turn_em_heat_on_calls_client(self, mock_hass, mock_client):
        # Base model (1123): not low_voltage, not low_wifi → value="slave", low="floor", sec=0
        t = _make_thermostat(mock_hass, mock_client)
        t.turn_em_heat_on()
        mock_client.set_em_heat.assert_called_once_with("111", "slave", "floor", 0)

    def test_turn_em_heat_off_calls_client(self, mock_hass, mock_client):
        # Base model (1123): not low_voltage, not low_wifi → "off", low="floor", sec=0
        t = _make_thermostat(mock_hass, mock_client)
        t.turn_em_heat_off()
        mock_client.set_em_heat.assert_called_once_with("111", "off", "floor", 0)
