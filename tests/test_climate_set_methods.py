"""Unit tests for the ~65 set_* API methods in climate.py.

These tests verify that each service handler calls the correct client method
with the correct JSON attribute key names.
"""
import pytest
from unittest.mock import MagicMock


def make_device_info(device_id, model, name="Test", sku="TEST"):
    return {
        "id": device_id,
        "name": name,
        "sku": sku,
        "location$id": 1,
        "signature": {
            "model": model,
            "modelCfg": 0,
            "protocol": "zigbee",
            "softVersion": {"major": 1, "middle": 0, "minor": 0},
        },
    }


def make_thermostat(model, client, hass, device_id=111):
    from custom_components.neviweb130.climate import (
        Neviweb130Thermostat,
        Neviweb130HPThermostat,
        Neviweb130HcThermostat,
        Neviweb130HeatCoolThermostat,
        Neviweb130FloorThermostat,
        Neviweb130LowThermostat,
        Neviweb130WifiThermostat,
        Neviweb130WifiFloorThermostat,
    )
    model_map = {
        1123: Neviweb130Thermostat,
        6810: Neviweb130HPThermostat,
        1512: Neviweb130HcThermostat,
        6727: Neviweb130HeatCoolThermostat,
        737:  Neviweb130FloorThermostat,
        7372: Neviweb130LowThermostat,
        1510: Neviweb130WifiThermostat,
        738:  Neviweb130WifiFloorThermostat,
    }
    cls = model_map[model]
    info = make_device_info(device_id, model)
    t = cls(info, "Test Thermostat", "SKU", "1.0.0", 1, client)
    t.hass = hass
    return t


@pytest.fixture
def client():
    c = MagicMock()
    c.scoped_unique_id = MagicMock(side_effect=lambda x: str(x))
    c._account_prefix = ""
    c._is_primary = True
    c._network_name = "Home"
    return c


@pytest.fixture
def hass():
    h = MagicMock()
    h.data = {"neviweb130": {"safe_mode": "-", "translation_cache": None, "ready": False}}
    h.config.language = "en"
    return h


@pytest.mark.unit
class TestBaseSetMethods:

    def test_set_second_display_outside(self, client, hass):
        t = make_thermostat(1123, client, hass)
        t.set_second_display({"id": "111", "display": "outsideTemperature"})
        client.set_second_display.assert_called_once_with("111", "outsideTemperature")

    def test_set_second_display_setpoint(self, client, hass):
        t = make_thermostat(1123, client, hass)
        t.set_second_display({"id": "111", "display": "setpoint"})
        client.set_second_display.assert_called_once_with("111", "setpoint")

    def test_set_backlight(self, client, hass):
        # Zigbee "auto" maps to "onActive" internally
        t = make_thermostat(1123, client, hass)
        t.set_backlight({"id": "111", "level": "auto", "is_wifi": False})
        client.set_backlight.assert_called_once_with("111", "onActive", False)

    def test_set_keypad_lock(self, client, hass):
        t = make_thermostat(1123, client, hass)
        t.set_keypad_lock({"id": "111", "lock": "locked", "wifi": False})
        client.set_keypad_lock.assert_called_once_with("111", "locked", False)

    def test_set_time_format(self, client, hass):
        t = make_thermostat(1123, client, hass)
        t.set_time_format({"id": "111", "time": "24h"})
        client.set_time_format.assert_called_once_with("111", "24h")

    def test_set_temperature_format(self, client, hass):
        # key is "temp", not "format"
        t = make_thermostat(1123, client, hass)
        t.set_temperature_format({"id": "111", "temp": "celsius"})
        client.set_temperature_format.assert_called_once_with("111", "celsius")

    def test_set_setpoint_max(self, client, hass):
        t = make_thermostat(1123, client, hass)
        t.set_setpoint_max({"id": "111", "temp": 30.0})
        client.set_setpoint_max.assert_called_once_with("111", 30.0)

    def test_set_setpoint_min(self, client, hass):
        t = make_thermostat(1123, client, hass)
        t.set_setpoint_min({"id": "111", "temp": 5.0})
        client.set_setpoint_min.assert_called_once_with("111", 5.0)

    def test_set_sensor_type(self, client, hass):
        t = make_thermostat(1123, client, hass)
        t.set_sensor_type({"id": "111", "type": "10k"})
        client.set_sensor_type.assert_called_once_with("111", "10k")

    def test_set_activation_deactivate(self, client, hass):
        t = make_thermostat(1123, client, hass)
        t.set_activation({"id": "111", "active": False})
        assert t._active is False

    def test_set_activation_reactivate(self, client, hass):
        t = make_thermostat(1123, client, hass)
        t._active = False
        t.set_activation({"id": "111", "active": True})
        assert t._active is True

    def test_set_em_heat(self, client, hass):
        # em_heat is triggered via turn_em_heat_on/off on the base thermostat
        t = make_thermostat(1123, client, hass)
        t.turn_em_heat_on()
        client.set_em_heat.assert_called_once()
        args = client.set_em_heat.call_args[0]
        # floor thermostat sends "slave", "floor", 0
        assert args[1] == "slave"
        assert args[2] == "floor"

    def test_set_room_setpoint_away(self, client, hass):
        t = make_thermostat(1123, client, hass)
        t.set_room_setpoint_away({"id": "111", "temp": 15.0})
        client.set_room_setpoint_away.assert_called_once_with("111", 15.0)

    def test_set_heat_lockout_temperature(self, client, hass):
        t = make_thermostat(1123, client, hass)
        t.set_heat_lockout_temperature({"id": "111", "temp": -10.0})
        client.set_heat_lockout.assert_called_once()

    def test_set_cool_lockout_temperature(self, client, hass):
        t = make_thermostat(1123, client, hass)
        t.set_cool_lockout_temperature({"id": "111", "temp": 35.0})
        client.set_cool_lockout.assert_called_once()

    def test_set_hvac_dr_options(self, client, hass):
        t = make_thermostat(1123, client, hass)
        t.set_hvac_dr_options({"id": "111", "dractive": 1, "optout": 0, "setpoint": 0})
        client.set_hvac_dr_options.assert_called_once()

    def test_set_hvac_dr_setpoint(self, client, hass):
        t = make_thermostat(1123, client, hass)
        t.set_hvac_dr_setpoint({"id": "111", "status": "on", "val": 2})
        client.set_hvac_dr_setpoint.assert_called_once()

    def test_set_auxiliary_load(self, client, hass):
        t = make_thermostat(1123, client, hass)
        t.set_auxiliary_load({"id": "111", "status": "on", "val": 1000})
        client.set_auxiliary_load.assert_called_once()


@pytest.mark.unit
class TestFloorSetMethods:

    def test_set_floor_air_limit(self, client, hass):
        t = make_thermostat(737, client, hass)
        t.set_floor_air_limit({"id": "111", "status": "on", "temp": 28.0})
        client.set_floor_air_limit.assert_called_once_with("111", "on", 28.0)

    def test_set_air_floor_mode(self, client, hass):
        t = make_thermostat(737, client, hass)
        t.set_air_floor_mode({"id": "111", "mode": "airByFloor"})
        client.set_air_floor_mode.assert_called_once_with("111", "airByFloor")

    def test_set_floor_limit_high(self, client, hass):
        # method is set_floor_limit with limit="high"
        t = make_thermostat(737, client, hass)
        t.set_floor_limit({"id": "111", "level": 35.0, "limit": "high"})
        client.set_floor_limit.assert_called_once()
        args = client.set_floor_limit.call_args[0]
        assert args[0] == "111"
        assert args[1] == 35.0

    def test_set_floor_limit_low(self, client, hass):
        # method is set_floor_limit with limit="low"
        t = make_thermostat(737, client, hass)
        t.set_floor_limit({"id": "111", "level": 15.0, "limit": "low"})
        client.set_floor_limit.assert_called_once()
        args = client.set_floor_limit.call_args[0]
        assert args[0] == "111"
        assert args[1] == 15.0


@pytest.mark.unit
class TestLowVoltageSetMethods:

    def test_set_aux_cycle_output(self, client, hass):
        # val must be a valid CYCLE_LENGTH_VALUES key e.g. "15 sec"
        t = make_thermostat(7372, client, hass)
        t.set_aux_cycle_output({"id": "111", "val": "15 sec"})
        client.set_aux_cycle_output.assert_called_once_with("111", 15, False)

    def test_set_cycle_output(self, client, hass):
        # val must be a valid CYCLE_LENGTH_VALUES key e.g. "15 sec"
        t = make_thermostat(7372, client, hass)
        t.set_cycle_output({"id": "111", "val": "15 sec"})
        client.set_cycle_output.assert_called_once_with("111", 15, False)

    def test_set_pump_protection(self, client, hass):
        t = make_thermostat(7372, client, hass)
        t.set_pump_protection({"id": "111", "status": "on", "wifi": False})
        client.set_pump_protection.assert_called_once_with("111", "on", False)


@pytest.mark.unit
class TestWifiSetMethods:

    def test_set_early_start(self, client, hass):
        t = make_thermostat(1510, client, hass)
        t.set_early_start({"id": "111", "start": "on"})
        client.set_early_start.assert_called_once_with("111", "on")

    def test_set_cool_setpoint_max(self, client, hass):
        t = make_thermostat(1510, client, hass)
        t.set_cool_setpoint_max({"id": "111", "temp": 30.0})
        client.set_cool_setpoint_max.assert_called_once_with("111", 30.0)

    def test_set_cool_setpoint_min(self, client, hass):
        t = make_thermostat(1510, client, hass)
        t.set_cool_setpoint_min({"id": "111", "temp": 16.0})
        client.set_cool_setpoint_min.assert_called_once_with("111", 16.0)


@pytest.mark.unit
class TestHeatPumpSetMethods:

    def test_set_heat_pump_operation_limit(self, client, hass):
        # _balance_pt_low must be set to avoid TypeError on comparison
        t = make_thermostat(6810, client, hass)
        t._balance_pt_low = -20.0
        t.set_heat_pump_operation_limit({"id": "111", "temp": -15.0})
        client.set_heat_pump_limit.assert_called_once_with("111", -15.0)

    def test_set_display_config(self, client, hass):
        # key is "display", client method is set_hp_display
        t = make_thermostat(6810, client, hass)
        t.set_display_config({"id": "111", "display": "on"})
        client.set_hp_display.assert_called_once_with("111", "on")

    def test_set_sound_config(self, client, hass):
        # key is "sound", client method is set_hp_sound
        t = make_thermostat(6810, client, hass)
        t.set_sound_config({"id": "111", "sound": "off"})
        client.set_hp_sound.assert_called_once_with("111", "off")


@pytest.mark.unit
class TestHcSetMethods:

    def test_set_hc_second_display(self, client, hass):
        t = make_thermostat(1512, client, hass)
        t.set_hc_second_display({"id": "111", "display": "outsideTemperature"})
        client.set_hc_display.assert_called_once_with("111", "outsideTemperature")

    def test_set_language(self, client, hass):
        # key is "lang", not "language"
        t = make_thermostat(1512, client, hass)
        t.set_language({"id": "111", "lang": "fr"})
        client.set_language.assert_called_once_with("111", "fr")


@pytest.mark.unit
class TestHeatCoolSetMethods:

    def test_set_cool_setpoint_away(self, client, hass):
        t = make_thermostat(6727, client, hass)
        t.set_cool_setpoint_away({"id": "111", "temp": 26.0})
        client.set_cool_setpoint_away.assert_called_once()

    def test_set_schedule_mode(self, client, hass):
        t = make_thermostat(6727, client, hass)
        t.set_schedule_mode({"id": "111", "mode": "auto"})
        client.set_schedule_mode.assert_called_once()

    def test_set_heatcool_setpoint_delta(self, client, hass):
        # key is "level", not "delta"
        t = make_thermostat(6727, client, hass)
        t.set_heatcool_setpoint_delta({"id": "111", "level": 2})
        client.set_heatcool_delta.assert_called_once()

    def test_set_fan_filter_reminder(self, client, hass):
        t = make_thermostat(6727, client, hass)
        t.set_fan_filter_reminder({"id": "111", "month": 3})
        client.set_fan_filter_reminder.assert_called_once()

    def test_set_temperature_offset(self, client, hass):
        t = make_thermostat(6727, client, hass)
        t.set_temperature_offset({"id": "111", "temp": 1.0})
        client.set_temperature_offset.assert_called_once()

    def test_set_aux_heating_source(self, client, hass):
        # key is ATTR_AUX_HEAT_SOURCE_TYPE = "auxHeatSourceType", value must be in AUX_HEATING
        t = make_thermostat(6727, client, hass)
        t.set_aux_heating_source({"id": "111", "auxHeatSourceType": "Electric"})
        client.set_aux_heating_source.assert_called_once()

    def test_set_fan_speed(self, client, hass):
        # client method is set_fan_mode, not set_fan_speed
        t = make_thermostat(6727, client, hass)
        t.set_fan_speed({"id": "111", "speed": "auto"})
        client.set_fan_mode.assert_called_once_with("111", "auto")

    def test_set_humidity_mode(self, client, hass):
        t = make_thermostat(6727, client, hass)
        t.set_humidity_mode({"id": "111", "mode": "auto"})
        client.set_humidity_mode.assert_called_once()

    def test_set_heat_dissipation_time(self, client, hass):
        t = make_thermostat(6727, client, hass)
        t.set_heat_dissipation_time({"id": "111", "time": 60})
        client.set_heat_dissipation_time.assert_called_once()

    def test_set_cool_dissipation_time(self, client, hass):
        t = make_thermostat(6727, client, hass)
        t.set_cool_dissipation_time({"id": "111", "time": 60})
        client.set_cool_dissipation_time.assert_called_once()

    def test_set_reversing_valve_polarity(self, client, hass):
        # key is ATTR_POLARITY = "polarity"
        t = make_thermostat(6727, client, hass)
        t.set_reversing_valve_polarity({"id": "111", "polarity": "cooling"})
        client.set_reversing_valve_polarity.assert_called_once()

    def test_set_min_time_on(self, client, hass):
        # uses ATTR_HEAT_MIN_TIME_ON = "heatMinTimeOn"
        t = make_thermostat(6727, client, hass)
        t.set_min_time_on({"id": "111", "heatMinTimeOn": 5})
        client.set_heat_min_time_on.assert_called_once()

    def test_set_min_time_off(self, client, hass):
        # uses ATTR_HEAT_MIN_TIME_OFF = "heatMinTimeOff"
        t = make_thermostat(6727, client, hass)
        t.set_min_time_off({"id": "111", "heatMinTimeOff": 5})
        client.set_heat_min_time_off.assert_called_once()

    def test_set_heat_interstage_delay(self, client, hass):
        # key is ATTR_TIME = "time"; needs output_connect_state with Y1+Y2 for multi-stage
        t = make_thermostat(6727, client, hass)
        t._output_connect_state = {"Y1": True, "Y2": True, "OB": False, "W": False, "W2": False,
                                    "G": False, "Rh": False, "Acc": False, "LC": False}
        t._reversing_valve_polarity = "cooling"
        t.set_heat_interstage_delay({"id": "111", "time": 10})
        client.set_heat_interstage_delay.assert_called_once()

    def test_set_cool_interstage_delay(self, client, hass):
        # key is ATTR_TIME = "time"; needs Y1+Y2 with OB for multi-stage cooling
        t = make_thermostat(6727, client, hass)
        t._output_connect_state = {"Y1": True, "Y2": True, "OB": True, "W": False, "W2": False,
                                    "G": False, "Rh": False, "Acc": False, "LC": False}
        t._reversing_valve_polarity = "cooling"
        t.set_cool_interstage_delay({"id": "111", "time": 10})
        client.set_cool_interstage_delay.assert_called_once()

    def test_set_aux_heat_start_delay(self, client, hass):
        # key is ATTR_TIME = "time"; needs heat pump + aux heater wiring
        t = make_thermostat(6727, client, hass)
        t._output_connect_state = {"Y1": True, "Y2": False, "OB": False, "W": True, "W2": False,
                                    "G": False, "Rh": False, "Acc": False, "LC": False}
        t._reversing_valve_polarity = "cooling"
        t.set_aux_heat_start_delay({"id": "111", "time": 30.0})
        client.set_aux_heat_start_delay.assert_called_once()

    def test_set_accessory_type(self, client, hass):
        t = make_thermostat(6727, client, hass)
        t.set_accessory_type({"id": "111", "type": "humOnHeat"})
        client.set_accessory_type.assert_called_once()

    def test_set_heat_installation_type(self, client, hass):
        t = make_thermostat(6727, client, hass)
        t.set_heat_installation_type({"id": "111", "type": "conventional"})
        client.set_heat_installation_type.assert_called_once()
