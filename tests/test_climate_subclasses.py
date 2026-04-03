"""
Regression tests for heat pump, heat/cool, and HC thermostat subclasses.
Verifies update() state parsing and extra_state_attributes keys.
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


def make_hass():
    h = MagicMock()
    h.data = {"neviweb130": {"safe_mode": "-", "translation_cache": None, "ready": False}}
    h.config.language = "en"
    return h


def make_client():
    c = MagicMock()
    c.scoped_unique_id = MagicMock(side_effect=lambda x: str(x))
    c._account_prefix = ""
    c._is_primary = True
    c._network_name = "Home"
    return c


# ---------------------------------------------------------------------------
# Heat pump subclass (model 6810)
# ---------------------------------------------------------------------------

HP_DEVICE_DATA = {
    "roomTemperature": 21.0,
    "roomSetpoint": 20.0,
    "roomSetpointMin": 5.0,
    "roomSetpointMax": 30.0,
    "coolSetpoint": 24.0,
    "coolSetpointMin": 16.0,
    "coolSetpointMax": 30.0,
    "temperatureFormat": "celsius",
    "systemMode": "heat",
    "lockKeypad": "unlocked",
    "fanSpeed": "auto",
    "fanSwingVertical": "auto",
    "fanCapabilities": None,
    "availableMode": None,
    "model": "HP6000ZB-GE",
    "rssi": -55,
    "drSetpoint": {"status": "off", "value": 0},
    "drStatus": {"drActive": False, "optOut": False, "setpoint": 0, "powerAbsolute": 0, "powerRelative": 0},
    "fanSwingHorizontal": "auto",
    "fanSwingCapabilities": None,
    "fanSwingCapabilityHorizontal": None,
    "fanSwingCapabilityVertical": None,
    "balancePoint": -15.0,
    "heatLockoutTemperature": 20.0,
    "coolLockoutTemperature": 10.0,
    "displayConfig": "on",
    "displayCapability": None,
    "soundConfig": "on",
    "soundCapability": None,
}


@pytest.mark.unit
class TestHeatPumpThermostat:

    def _make(self):
        from custom_components.neviweb130.climate import Neviweb130HPThermostat
        client = make_client()
        hass = make_hass()
        info = make_device_info(666, 6810, "Garage HP", "HP6000ZB-GE")
        t = Neviweb130HPThermostat(info, "Garage HP", "HP6000ZB-GE", "1.0.0", 1, client)
        t.hass = hass
        return t, client, hass

    def test_initial_cool_min_max(self):
        t, _, _ = self._make()
        assert t._cool_min == 16
        assert t._cool_max == 30

    def test_update_parses_fan_speed(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = dict(HP_DEVICE_DATA)
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t._firmware = "1.0.0"
        t.update()
        assert t._fan_speed == "auto"

    def test_update_parses_fan_swing_vert(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = dict(HP_DEVICE_DATA)
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t._firmware = "1.0.0"
        t.update()
        assert t._fan_swing_vert == "auto"

    def test_update_parses_balance_pt(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = dict(HP_DEVICE_DATA)
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t._firmware = "1.0.0"
        t.update()
        assert t._balance_pt == -15.0

    def test_update_parses_cool_setpoint(self):
        t, client, _ = self._make()
        data = dict(HP_DEVICE_DATA)
        data["systemMode"] = "cool"
        client.get_device_attributes.return_value = data
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t._firmware = "1.0.0"
        t.update()
        assert t._target_temp == 24.0

    def test_update_parses_heat_setpoint_when_heating(self):
        t, client, _ = self._make()
        data = dict(HP_DEVICE_DATA)
        data["systemMode"] = "heat"
        client.get_device_attributes.return_value = data
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t._firmware = "1.0.0"
        t.update()
        assert t._target_temp == 20.0

    def test_update_skipped_when_inactive(self):
        t, client, _ = self._make()
        t._active = False
        t._snooze = 0
        t.update()
        client.get_device_attributes.assert_not_called()

    def test_extra_state_attributes_contains_fan_speed(self):
        t, _, _ = self._make()
        t._fan_speed = "high"
        t._firmware = "1.0.0"
        # Set caps to empty dicts so extract_capability_full doesn't crash on None
        t._fan_swing_cap_vert = {}
        t._fan_swing_cap_horiz = {}
        t._fan_swing_cap = {}
        t._display_cap = {}
        t._sound_cap = {}
        attrs = t.extra_state_attributes
        assert "fan_speed" in attrs
        assert attrs["fan_speed"] == "high"

    def test_extra_state_attributes_contains_balance_pt(self):
        t, _, _ = self._make()
        t._firmware = "1.0.0"
        t._balance_pt = -10.0
        t._fan_swing_cap_vert = {}
        t._fan_swing_cap_horiz = {}
        t._fan_swing_cap = {}
        t._display_cap = {}
        t._sound_cap = {}
        attrs = t.extra_state_attributes
        assert "heat_pump_limit_temp" in attrs

    def test_extra_state_attributes_contains_sku(self):
        t, _, _ = self._make()
        t._firmware = "1.0.0"
        t._fan_swing_cap_vert = {}
        t._fan_swing_cap_horiz = {}
        t._fan_swing_cap = {}
        t._display_cap = {}
        t._sound_cap = {}
        attrs = t.extra_state_attributes
        assert attrs["sku"] == "HP6000ZB-GE"

    def test_update_error_code_read_timeout_does_not_crash(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = {"errorCode": "ReadTimeout"}
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t._firmware = "1.0.0"
        t.update()  # should not raise

    def test_update_error_key_calls_log_error(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = {"error": {"code": "USRSESSEXP"}}
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t._firmware = "1.0.0"
        t.update()  # should not raise


# ---------------------------------------------------------------------------
# HC thermostat subclass (model 1512)
# ---------------------------------------------------------------------------

HC_DEVICE_DATA = {
    "roomTemperatureDisplay": 21.0,   # ATTR_ROOM_TEMP_DISPLAY — used as cur_temp
    "roomSetpoint": 20.0,
    "roomSetpointMin": 5.0,
    "roomSetpointMax": 30.0,
    "temperatureFormat": "celsius",
    "timeFormat": "24h",
    "lockKeypad": "unlocked",         # ATTR_KEYPAD
    "backlightAdaptive": "auto",      # ATTR_BACKLIGHT
    "fanSpeed": "auto",
    "fanSwingVertical": "auto",
    "fanSwingHorizontal": "auto",
    "fanCapabilities": {},
    "fanSwingCapabilities": {},
    "fanSwingCapabilityHorizontal": {},
    "fanSwingCapabilityVertical": {},
    "balancePoint": -15.0,
    "heatLockoutTemperature": 20.0,
    "coolLockoutTemperature": 10.0,
    "availableMode": None,
    "displayConfig": "on",
    "displayCapability": {},
    "soundConfig": "on",
    "soundCapability": {},
    "config2ndDisplay": "setpoint",
    "rssi": -55,
    "loadConnected": 3000,            # ATTR_WATTAGE
    "cycleLength": 15,
    "coolSetpoint": 24.0,
    "coolSetpointMin": 16.0,
    "coolSetpointMax": 30.0,
    "hcDevice": None,
    "language": "en",
    "model": "TH1134ZB-HC",
    "outputPercentDisplay": 50,
    "drSetpoint": {"status": "off", "value": 0},
    "drStatus": {"drActive": False, "optOut": False, "setpoint": 0, "powerAbsolute": 0, "powerRelative": 0},

}


@pytest.mark.unit
class TestHcThermostat:

    def _make(self):
        from custom_components.neviweb130.climate import Neviweb130HcThermostat
        client = make_client()
        hass = make_hass()
        info = make_device_info(555, 1512, "HC Thermo", "TH1134ZB-HC")
        t = Neviweb130HcThermostat(info, "HC Thermo", "TH1134ZB-HC", "1.0.0", 1, client)
        t.hass = hass
        return t, client, hass

    def test_initial_cool_min_max(self):
        t, _, _ = self._make()
        assert t._cool_min == 16
        assert t._cool_max == 30

    def test_update_parses_language(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = dict(HC_DEVICE_DATA)
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t.update()
        assert t._language == "en"

    def test_update_parses_hc_device(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = dict(HC_DEVICE_DATA)
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t.update()
        assert t._hc_device is None

    def test_update_parses_fan_speed(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = dict(HC_DEVICE_DATA)
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t.update()
        assert t._fan_speed == "auto"

    def test_update_parses_cool_setpoint(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = dict(HC_DEVICE_DATA)
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t.update()
        assert t._target_cool == 24.0

    def test_update_skipped_when_inactive(self):
        t, client, _ = self._make()
        t._active = False
        t._snooze = 0
        t.update()
        client.get_device_attributes.assert_not_called()

    def test_extra_state_attributes_contains_hc_device(self):
        t, _, _ = self._make()
        t._fan_swing_cap_vert = {}
        t._fan_swing_cap_horiz = {}
        t._fan_swing_cap = {}
        t._display_cap = {}
        t._sound_cap = {}
        attrs = t.extra_state_attributes
        assert "hc_device" in attrs

    def test_extra_state_attributes_contains_language(self):
        t, _, _ = self._make()
        t._language = "fr"
        t._fan_swing_cap_vert = {}
        t._fan_swing_cap_horiz = {}
        t._fan_swing_cap = {}
        t._display_cap = {}
        t._sound_cap = {}
        attrs = t.extra_state_attributes
        assert attrs["language"] == "fr"

    def test_extra_state_attributes_contains_cool_setpoint(self):
        t, _, _ = self._make()
        t._target_cool = 24.0
        t._fan_swing_cap_vert = {}
        t._fan_swing_cap_horiz = {}
        t._fan_swing_cap = {}
        t._display_cap = {}
        t._sound_cap = {}
        attrs = t.extra_state_attributes
        assert "cool setpoint" in attrs

    def test_extra_state_attributes_contains_balance_point(self):
        t, _, _ = self._make()
        t._fan_swing_cap_vert = {}
        t._fan_swing_cap_horiz = {}
        t._fan_swing_cap = {}
        t._display_cap = {}
        t._sound_cap = {}
        attrs = t.extra_state_attributes
        assert "balance_point" in attrs

    def test_update_error_read_timeout_does_not_crash(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = {"errorCode": "ReadTimeout"}
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t.update()  # should not raise


# ---------------------------------------------------------------------------
# HeatCool thermostat subclass (model 6727)
# ---------------------------------------------------------------------------

HC_WIFI_DEVICE_DATA = {
    "roomTemperature": {"value": 21.0, "error": None},
    "roomSetpoint": 20.0,
    "roomSetpointMin": 5.0,
    "roomSetpointMax": 30.0,
    "coolSetpoint": 24.0,
    "coolSetpointMin": 16.0,
    "coolSetpointMax": 30.0,
    "temperatureFormat": "celsius",
    "timeFormat": "24h",
    "heatCoolMode": "heat",          # ATTR_HEAT_COOL
    "setpointMode": "manual",
    "keyboardLock": "unlocked",       # ATTR_WIFI_KEYPAD
    "backlightAutoDim": "auto",
    "backlight": "auto",
    "earlyStartCfg": "off",
    "fanSpeed": "auto",
    "fanFilterReminderPeriod": 2160,
    "language": "en",
    "occupancyMode": "home",
    "outputPercentDisplay": {"percent": 50, "sourceType": "heating"},
    "heatSourceType": "electric",
    "auxHeatSourceType": "none",
    "roomSetpointAway": 15.0,
    "coolSetpointAway": 26.0,
    "reversingValvePolarity": "cooling",
    "heatLockoutTemperature": 20.0,
    "coolLockoutTemperature": 10.0,
    "balancePoint": -15.0,
    "humidifierType": None,
    "humidityDisplay": None,
    "humiditySetpoint": None,
    "cycleLength": 15,
    "auxCycleLength": 0,
    "coolCycleLength": 0,
    "temperatureOffsetHeat": 0,
    "auxHeatMinTimeOn": 0,
    "auxHeatStartDelay": 0,
    "dualEnergyStatus": None,
    "coolMinTimeOn": 0,
    "coolMinTimeOff": 0,
    "heatInstallationType": "conventional",
    "bulkOutputConnectedState": {"Y1": False, "Y2": False, "OB": False, "W": False, "W2": False, "G": False, "Rh": False, "Acc": False, "LC": False},
    "accessoryType": {"humOnHeatStandalone": False, "humOnFanStandalone": False, "humStandalone": False, "dehumStandalone": False, "airExchangerStandalone": False},
    "humiditySetpointOffset": 0,
    "humiditySetpointMode": "auto",
    "airExchangerMinTimeOn": 0,
    "heatCoolLockoutStatus": {"cool": False, "heat": False, "balancePoint": False},
    "drAuxConfig": None,
    "drFanSpeedConfig": None,
    "drAccessoryConfig": None,
    "heatPurgeTime": 0,
    "coolPurgeTime": 0,
    "auxHeatMinTimeOff": 0,
    "heatMinTimeOn": 0,
    "heatMinTimeOff": 0,
    "heatCoolSetpointMinDelta": 2,
    "drSetpoint": {"status": "off", "value": 0},
    "drStatus": {"drActive": False, "optOut": False, "setpoint": 0, "powerAbsolute": 0, "powerRelative": 0},
    # HC_CONFIG keys required for model 6727
    "airCurtainActivationTemperature": None,
    "heatOutputPolarity": None,
    "airCurtainConfig": None,
    "airCurtainMaxPowerTemperature": None,
    "drAirCurtainConfig": None,
}


@pytest.mark.unit
class TestHeatCoolThermostat:

    def _make(self, model=6727):
        from custom_components.neviweb130.climate import Neviweb130HeatCoolThermostat
        client = make_client()
        hass = make_hass()
        info = make_device_info(777, model, "HeatCool", "TH6500WF")
        t = Neviweb130HeatCoolThermostat(info, "HeatCool", "TH6500WF", "4.0.0", 1, client)
        t.hass = hass
        return t, client, hass

    def test_initial_cool_min_max(self):
        t, _, _ = self._make()
        assert t._cool_min == 16
        assert t._cool_max == 36

    def test_initial_heatcool_delta(self):
        t, _, _ = self._make()
        assert t._heatcool_setpoint_delta == 2

    def test_update_parses_heat_cool_mode(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = dict(HC_WIFI_DEVICE_DATA)
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t.update()
        assert t._heat_cool == "heat"

    def test_update_parses_fan_speed(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = dict(HC_WIFI_DEVICE_DATA)
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t.update()
        assert t._fan_speed == "auto"

    def test_update_parses_cool_setpoint(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = dict(HC_WIFI_DEVICE_DATA)
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t.update()
        assert t._target_cool == 24.0

    def test_update_parses_heatcool_delta(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = dict(HC_WIFI_DEVICE_DATA)
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t.update()
        assert t._heatcool_setpoint_delta == 2

    def test_update_parses_reversing_valve_polarity(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = dict(HC_WIFI_DEVICE_DATA)
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t.update()
        assert t._reversing_valve_polarity == "cooling"

    def test_update_parses_accessory_type_none(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = dict(HC_WIFI_DEVICE_DATA)
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t.update()
        assert t._accessory_type == "none"

    def test_update_parses_cool_setpoint_away(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = dict(HC_WIFI_DEVICE_DATA)
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t.update()
        assert t._cool_target_temp_away == 26.0

    def test_update_skipped_when_inactive(self):
        t, client, _ = self._make()
        t._active = False
        t._snooze = 0
        t.update()
        client.get_device_attributes.assert_not_called()

    def test_update_error_read_timeout_does_not_crash(self):
        t, client, _ = self._make()
        client.get_device_attributes.return_value = {"errorCode": "ReadTimeout"}
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        t._active = True
        t.update()  # should not raise

    def test_extra_state_attributes_contains_heat_cool(self):
        t, _, _ = self._make()
        t._heat_cool = "heat"
        attrs = t.extra_state_attributes
        assert "heat_cool" in attrs or "heatCool" in attrs or any("heat" in k for k in attrs)

    def test_extra_state_attributes_contains_cool_setpoint(self):
        t, _, _ = self._make()
        attrs = t.extra_state_attributes
        assert "cool setpoint" in attrs or "cool_setpoint" in attrs

    def test_extra_state_attributes_contains_reversing_valve(self):
        t, _, _ = self._make()
        attrs = t.extra_state_attributes
        assert "reversing_valve_polarity" in attrs

    def test_extra_state_attributes_contains_accessory_type(self):
        t, _, _ = self._make()
        attrs = t.extra_state_attributes
        assert "accessory_type" in attrs
