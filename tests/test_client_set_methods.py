"""
Unit tests for Neviweb130Client set_* methods.
Verifies the exact JSON attribute key names sent to the API.
"""
import pytest
from unittest.mock import MagicMock, patch, call


def make_client(hass):
    from custom_components.neviweb130 import Neviweb130Client
    with patch.object(Neviweb130Client, "__init__", lambda self, *a, **kw: None):
        c = Neviweb130Client.__new__(Neviweb130Client)
    c.hass = hass
    c._session = MagicMock()
    c.set_device_attributes = MagicMock()
    c.notify_ha = MagicMock()
    return c


@pytest.fixture
def hass():
    h = MagicMock()
    h.data = {"neviweb130": {"safe_mode": "-"}}
    h.config.language = "en"
    return h


@pytest.mark.unit
class TestClientSetTemperature:

    def test_set_temperature_uses_roomSetpoint(self, hass):
        c = make_client(hass)
        c.set_temperature("42", 21.5)
        c.set_device_attributes.assert_called_once_with("42", {"roomSetpoint": 21.5})

    def test_set_cool_temperature_uses_coolSetpoint(self, hass):
        c = make_client(hass)
        c.set_cool_temperature("42", 24.0)
        c.set_device_attributes.assert_called_once_with("42", {"coolSetpoint": 24.0})

    def test_set_room_setpoint_away_uses_roomSetpointAway(self, hass):
        c = make_client(hass)
        c.set_room_setpoint_away("42", 15.0)
        c.set_device_attributes.assert_called_once_with("42", {"roomSetpointAway": 15.0})

    def test_set_setpoint_min_uses_roomSetpointMin(self, hass):
        c = make_client(hass)
        c.set_setpoint_min("42", 5.0)
        c.set_device_attributes.assert_called_once_with("42", {"roomSetpointMin": 5.0})

    def test_set_setpoint_max_uses_roomSetpointMax(self, hass):
        c = make_client(hass)
        c.set_setpoint_max("42", 30.0)
        c.set_device_attributes.assert_called_once_with("42", {"roomSetpointMax": 30.0})

    def test_set_cool_setpoint_min_uses_coolSetpointMin(self, hass):
        c = make_client(hass)
        c.set_cool_setpoint_min("42", 16.0)
        c.set_device_attributes.assert_called_once_with("42", {"coolSetpointMin": 16.0})

    def test_set_cool_setpoint_max_uses_coolSetpointMax(self, hass):
        c = make_client(hass)
        c.set_cool_setpoint_max("42", 30.0)
        c.set_device_attributes.assert_called_once_with("42", {"coolSetpointMax": 30.0})


@pytest.mark.unit
class TestClientSetDisplay:

    def test_set_second_display_uses_config2ndDisplay(self, hass):
        c = make_client(hass)
        c.set_second_display("42", "outsideTemperature")
        c.set_device_attributes.assert_called_once_with("42", {"config2ndDisplay": "outsideTemperature"})

    def test_set_time_format_uses_timeFormat(self, hass):
        c = make_client(hass)
        c.set_time_format("42", "24h")
        c.set_device_attributes.assert_called_once_with("42", {"timeFormat": "24h"})

    def test_set_temperature_format_uses_temperatureFormat(self, hass):
        c = make_client(hass)
        c.set_temperature_format("42", "celsius")
        c.set_device_attributes.assert_called_once_with("42", {"temperatureFormat": "celsius"})

    def test_set_backlight_zigbee_uses_backlightAdaptive(self, hass):
        c = make_client(hass)
        c.set_backlight("42", "auto", is_wifi=False)
        c.set_device_attributes.assert_called_once_with("42", {"backlightAdaptive": "auto"})

    def test_set_backlight_wifi_uses_backlightAutoDim(self, hass):
        c = make_client(hass)
        c.set_backlight("42", "auto", is_wifi=True)
        c.set_device_attributes.assert_called_once_with("42", {"backlightAutoDim": "auto"})

    def test_set_keypad_lock_zigbee_uses_lockKeypad(self, hass):
        c = make_client(hass)
        c.set_keypad_lock("42", "locked", wifi=False)
        c.set_device_attributes.assert_called_once_with("42", {"lockKeypad": "locked"})

    def test_set_keypad_lock_wifi_uses_keyboardLock(self, hass):
        c = make_client(hass)
        c.set_keypad_lock("42", "locked", wifi=True)
        args = c.set_device_attributes.call_args[0]
        assert "keyboardLock" in args[1]
        assert args[1]["keyboardLock"] == "locked"


@pytest.mark.unit
class TestClientSetFloor:

    def test_set_floor_air_limit_uses_floorMaxAirTemperature(self, hass):
        c = make_client(hass)
        c.set_floor_air_limit("42", "on", 28.0)
        args = c.set_device_attributes.call_args[0]
        assert "floorMaxAirTemperature" in args[1]
        assert args[1]["floorMaxAirTemperature"]["status"] == "on"
        assert args[1]["floorMaxAirTemperature"]["value"] == 28.0

    def test_set_floor_air_limit_zero_sends_none(self, hass):
        c = make_client(hass)
        c.set_floor_air_limit("42", "off", 0)
        args = c.set_device_attributes.call_args[0]
        assert args[1]["floorMaxAirTemperature"]["value"] is None

    def test_set_air_floor_mode_uses_airFloorMode(self, hass):
        c = make_client(hass)
        c.set_air_floor_mode("42", "airByFloor")
        c.set_device_attributes.assert_called_once_with("42", {"airFloorMode": "airByFloor"})

    def test_set_sensor_type_uses_floorSensorType(self, hass):
        c = make_client(hass)
        c.set_sensor_type("42", "10k")
        args = c.set_device_attributes.call_args[0]
        assert "floorSensorType" in args[1]
        assert args[1]["floorSensorType"] == "10k"


@pytest.mark.unit
class TestClientSetLowVoltage:

    def test_set_aux_cycle_output_zigbee_uses_cycleLengthOutput2(self, hass):
        c = make_client(hass)
        c.set_aux_cycle_output("42", 15, wifi=False)
        args = c.set_device_attributes.call_args[0]
        assert "cycleLengthOutput2" in args[1]
        assert args[1]["cycleLengthOutput2"]["value"] == 15

    def test_set_aux_cycle_output_wifi_uses_auxCycleLength(self, hass):
        c = make_client(hass)
        c.set_aux_cycle_output("42", 15, wifi=True)
        c.set_device_attributes.assert_called_once_with("42", {"auxCycleLength": 15})

    def test_set_cycle_output_normal_uses_cycleLength(self, hass):
        c = make_client(hass)
        c.set_cycle_output("42", 15, is_hc=False)
        c.set_device_attributes.assert_called_once_with("42", {"cycleLength": 15})

    def test_set_cycle_output_hc_uses_coolCycleLength(self, hass):
        c = make_client(hass)
        c.set_cycle_output("42", 15, is_hc=True)
        c.set_device_attributes.assert_called_once_with("42", {"coolCycleLength": 15})

    def test_set_pump_protection_zigbee_on_uses_pumpProtectDuration(self, hass):
        c = make_client(hass)
        c.set_pump_protection("42", "on", wifi=False)
        args = c.set_device_attributes.call_args[0]
        assert "pumpProtectDuration" in args[1]
        assert args[1]["pumpProtectDuration"]["status"] == "on"

    def test_set_pump_protection_wifi_uses_pumpProtection(self, hass):
        c = make_client(hass)
        c.set_pump_protection("42", "on", wifi=True)
        args = c.set_device_attributes.call_args[0]
        assert "pumpProtection" in args[1]


@pytest.mark.unit
class TestClientSetHeatCool:

    def test_set_cool_setpoint_away_hc_uses_coolSetpointAway(self, hass):
        c = make_client(hass)
        c.set_cool_setpoint_away("42", 26.0, HC=True)
        c.set_device_attributes.assert_called_once_with("42", {"coolSetpointAway": 26.0})

    def test_set_cool_setpoint_away_non_hc_notifies(self, hass):
        c = make_client(hass)
        c.set_cool_setpoint_away("42", 26.0, HC=False)
        c.set_device_attributes.assert_not_called()
        c.notify_ha.assert_called_once()

    def test_set_schedule_mode_hc_uses_setpointMode(self, hass):
        c = make_client(hass)
        c.set_schedule_mode("42", "auto", HC=True)
        c.set_device_attributes.assert_called_once_with("42", {"setpointMode": "auto"})

    def test_set_schedule_mode_non_hc_notifies(self, hass):
        c = make_client(hass)
        c.set_schedule_mode("42", "auto", HC=False)
        c.set_device_attributes.assert_not_called()
        c.notify_ha.assert_called_once()

    def test_set_heatcool_delta_hc_uses_heatCoolSetpointMinDelta(self, hass):
        c = make_client(hass)
        c.set_heatcool_delta("42", 2, HC=True)
        c.set_device_attributes.assert_called_once_with("42", {"heatCoolSetpointMinDelta": 2})

    def test_set_fan_filter_reminder_hc_converts_months_to_hours(self, hass):
        c = make_client(hass)
        c.set_fan_filter_reminder("42", 3, HC=True)
        args = c.set_device_attributes.call_args[0]
        assert "fanFilterReminderPeriod" in args[1]
        assert args[1]["fanFilterReminderPeriod"] == 3 * 720

    def test_set_temperature_offset_hc_uses_temperatureOffsetHeat(self, hass):
        c = make_client(hass)
        c.set_temperature_offset("42", 1.0, HC=True)
        args = c.set_device_attributes.call_args[0]
        assert "temperatureOffsetHeat" in args[1]

    def test_set_humidity_mode_hc_uses_humiditySetpointMode(self, hass):
        c = make_client(hass)
        c.set_humidity_mode("42", "auto", HC=True)
        c.set_device_attributes.assert_called_once_with("42", {"humiditySetpointMode": "auto"})

    def test_set_accessory_type_humOnHeat(self, hass):
        c = make_client(hass)
        c.set_accessory_type("42", "humOnHeat")
        args = c.set_device_attributes.call_args[0]
        assert "accessoryType" in args[1]
        payload = args[1]["accessoryType"]
        assert payload["humOnHeat"] is True
        assert payload["humOnFan"] is False
        assert payload["dehumStandalone"] is False

    def test_set_accessory_type_dehum(self, hass):
        c = make_client(hass)
        c.set_accessory_type("42", "dehum")
        args = c.set_device_attributes.call_args[0]
        payload = args[1]["accessoryType"]
        assert payload["dehumStandalone"] is True
        assert payload["humOnHeat"] is False

    def test_set_heat_installation_type_uses_heatInstallationType(self, hass):
        c = make_client(hass)
        c.set_heat_installation_type("42", "conventional")
        args = c.set_device_attributes.call_args[0]
        assert "heatInstallationType" in args[1]


@pytest.mark.unit
class TestClientSetMode:

    def test_set_setpoint_mode_zigbee_uses_systemMode(self, hass):
        from homeassistant.components.climate.const import HVACMode
        c = make_client(hass)
        c.set_setpoint_mode("42", HVACMode.HEAT, wifi=False, HC=False)
        args = c.set_device_attributes.call_args[0]
        assert "systemMode" in args[1]

    def test_set_setpoint_mode_wifi_uses_setpointMode(self, hass):
        from homeassistant.components.climate.const import HVACMode
        c = make_client(hass)
        c.set_setpoint_mode("42", HVACMode.HEAT, wifi=True, HC=False)
        args = c.set_device_attributes.call_args[0]
        assert "setpointMode" in args[1]

    def test_set_setpoint_mode_wifi_hc_uses_heatCoolMode(self, hass):
        from homeassistant.components.climate.const import HVACMode
        c = make_client(hass)
        c.set_setpoint_mode("42", HVACMode.HEAT, wifi=True, HC=True)
        args = c.set_device_attributes.call_args[0]
        assert "heatCoolMode" in args[1]

    def test_set_occupancy_mode_wifi_away_uses_occupancyMode(self, hass):
        from homeassistant.components.climate.const import PRESET_AWAY
        c = make_client(hass)
        c.set_occupancy_mode("42", PRESET_AWAY, wifi=True)
        args = c.set_device_attributes.call_args[0]
        assert "occupancyMode" in args[1]

    def test_set_occupancy_mode_zigbee_uses_systemMode(self, hass):
        from homeassistant.components.climate.const import PRESET_AWAY
        c = make_client(hass)
        c.set_occupancy_mode("42", PRESET_AWAY, wifi=False)
        args = c.set_device_attributes.call_args[0]
        assert "systemMode" in args[1]


@pytest.mark.unit
class TestClientSetEarlyStart:

    def test_set_early_start_uses_earlyStartCfg(self, hass):
        c = make_client(hass)
        c.set_early_start("42", "on")
        c.set_device_attributes.assert_called_once_with("42", {"earlyStartCfg": "on"})
