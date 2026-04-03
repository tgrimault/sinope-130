"""Preservation tests — verify all externally observable behaviors on UNFIXED code.

These tests MUST ALL PASS on unfixed code. They establish the baseline to preserve
through the refactor. Do NOT modify production files to make these pass.

Test groups:
  A — service call preservation (entity method → client method mapping)
  B — extra_state_attributes key stability
  C — update() polling contract
  D — model→class dispatch
  E — error code handling
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_device_info(device_id: int, model: int, name: str = "Test", sku: str = "TEST"):
    return {
        "id": device_id,
        "name": name,
        "sku": sku,
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


def make_hass():
    hass = MagicMock()
    hass.data = {
        "neviweb130": {
            "safe_mode": "-",
            "translation_cache": None,
            "ready": False,
        }
    }
    hass.config.language = "en"
    return hass


def make_thermostat(model: int, client=None, hass=None, device_id: int = 111):
    """Instantiate the correct thermostat subclass for the given model number."""
    from custom_components.neviweb130.climate import (
        Neviweb130FloorThermostat,
        Neviweb130HPThermostat,
        Neviweb130HcThermostat,
        Neviweb130HeatCoolThermostat,
        Neviweb130LowThermostat,
        Neviweb130Thermostat,
        Neviweb130WifiThermostat,
    )

    model_map = {
        1123: Neviweb130Thermostat,
        737: Neviweb130FloorThermostat,
        7372: Neviweb130LowThermostat,
        1510: Neviweb130WifiThermostat,
        6810: Neviweb130HPThermostat,
        6727: Neviweb130HeatCoolThermostat,
        1512: Neviweb130HcThermostat,
    }
    cls = model_map[model]
    if client is None:
        client = make_client()
    if hass is None:
        hass = make_hass()
    info = make_device_info(device_id, model)
    entity = cls(info, "Test Thermostat", "SKU", "1.0.0", 67890, client)
    entity.hass = hass
    return entity


# ===========================================================================
# Group A — service call preservation
# ===========================================================================

@pytest.mark.unit
class TestGroupA_ServiceCallPreservation:
    """Verify each base-class service method calls the correct client method."""

    def test_set_second_display_calls_client(self):
        client = make_client()
        t = make_thermostat(1123, client)
        t.set_second_display({"id": "111", "display": "outsideTemperature"})
        client.set_second_display.assert_called_once_with("111", "outsideTemperature")

    def test_set_second_display_setpoint_calls_client(self):
        client = make_client()
        t = make_thermostat(1123, client)
        t.set_second_display({"id": "111", "display": "setpoint"})
        client.set_second_display.assert_called_once_with("111", "setpoint")

    def test_set_backlight_zigbee_auto_calls_client(self):
        """Zigbee 'auto' maps to 'onActive' internally."""
        client = make_client()
        t = make_thermostat(1123, client)
        t.set_backlight({"id": "111", "level": "auto"})
        client.set_backlight.assert_called_once_with("111", "onActive", False)

    def test_set_backlight_zigbee_on_calls_client(self):
        """Zigbee 'on' maps to 'always' internally."""
        client = make_client()
        t = make_thermostat(1123, client)
        t.set_backlight({"id": "111", "level": "on"})
        client.set_backlight.assert_called_once_with("111", "always", False)

    def test_set_keypad_lock_zigbee_locked(self):
        client = make_client()
        t = make_thermostat(1123, client)
        t.set_keypad_lock({"id": "111", "lock": "locked"})
        client.set_keypad_lock.assert_called_once_with("111", "locked", False)

    def test_set_keypad_lock_zigbee_unlocked(self):
        client = make_client()
        t = make_thermostat(1123, client)
        t.set_keypad_lock({"id": "111", "lock": "unlocked"})
        client.set_keypad_lock.assert_called_once_with("111", "unlocked", False)

    def test_set_time_format_24h(self):
        client = make_client()
        t = make_thermostat(1123, client)
        t.set_time_format({"id": "111", "time": 24})
        client.set_time_format.assert_called_once_with("111", "24h")

    def test_set_time_format_12h(self):
        client = make_client()
        t = make_thermostat(1123, client)
        t.set_time_format({"id": "111", "time": 12})
        client.set_time_format.assert_called_once_with("111", "12h")

    def test_set_temperature_format_celsius(self):
        client = make_client()
        t = make_thermostat(1123, client)
        t.set_temperature_format({"id": "111", "temp": "celsius"})
        client.set_temperature_format.assert_called_once_with("111", "celsius")

    def test_set_temperature_format_fahrenheit(self):
        client = make_client()
        t = make_thermostat(1123, client)
        t.set_temperature_format({"id": "111", "temp": "fahrenheit"})
        client.set_temperature_format.assert_called_once_with("111", "fahrenheit")

    def test_set_setpoint_max(self):
        client = make_client()
        t = make_thermostat(1123, client)
        t.set_setpoint_max({"id": "111", "temp": 30.0})
        client.set_setpoint_max.assert_called_once_with("111", 30.0)

    def test_set_setpoint_min(self):
        client = make_client()
        t = make_thermostat(1123, client)
        t.set_setpoint_min({"id": "111", "temp": 5.0})
        client.set_setpoint_min.assert_called_once_with("111", 5.0)

    def test_set_activation_deactivates(self):
        """set_activation does NOT call a client method — it sets _active directly."""
        client = make_client()
        t = make_thermostat(1123, client)
        t.set_activation({"id": "111", "active": False})
        assert t._active is False

    def test_set_activation_reactivates(self):
        client = make_client()
        t = make_thermostat(1123, client)
        t._active = False
        t.set_activation({"id": "111", "active": True})
        assert t._active is True


# ===========================================================================
# Group B — extra_state_attributes key stability
# ===========================================================================

@pytest.mark.unit
class TestGroupB_ExtraStateAttributesKeyStability:
    """Assert the returned dict always contains all expected keys."""

    # Keys that must always be present on Neviweb130Thermostat (base)
    BASE_KEYS = {
        "neviweb_occupancy_mode",
        "wattage",
        "cycle_length",
        "error_code",
        "heat_level",
        "pi_heating_demand",
        "icon_type",
        "temp_display_value",
        "second_display",
        "keypad",
        "backlight",
        "time_format",
        "temperature_format",
        "setpoint_max",
        "setpoint_min",
        "eco_status",
        "eco_optOut",
        "eco_setpoint",
        "eco_power_relative",
        "eco_power_absolute",
        "eco_setpoint_status",
        "eco_setpoint_delta",
        "total_kwh_count",
        "monthly_kwh_count",
        "daily_kwh_count",
        "hourly_kwh_count",
        "hourly_kwh",
        "daily_kwh",
        "monthly_kwh",
        "last_energy_stat_update",
        "outdoor_temp",
        "weather_icon",
        "rssi",
        "sku",
        "device_model",
        "device_model_cfg",
        "firmware",
        "activation",
        "id",
    }

    # Additional keys on FloorThermostat
    FLOOR_EXTRA_KEYS = {
        "gfci_status",
        "gfci_alert",
        "sensor_mode",
        "auxiliary_heat",
        "floor_sensor_type",
        "floor_setpoint_max",
        "floor_setpoint_low",
        "floor_air_limit",
    }

    # Keys on LowThermostat
    LOW_EXTRA_KEYS = {
        "pump_protection_status",
        "pump_protection_duration",
        "pump_protection_frequency",
        "sensor_mode",
        "floor_sensor_type",
        "cycle_length",
        "auxiliary_cycle_status",
        "auxiliary_cycle_value",
    }

    def test_base_thermostat_has_all_expected_keys(self):
        t = make_thermostat(1123)
        attrs = t.extra_state_attributes
        missing = self.BASE_KEYS - set(attrs.keys())
        assert not missing, f"Missing keys in Neviweb130Thermostat.extra_state_attributes: {missing}"

    def test_floor_thermostat_has_base_keys(self):
        t = make_thermostat(737)
        attrs = t.extra_state_attributes
        missing = self.BASE_KEYS - set(attrs.keys())
        assert not missing, f"Missing base keys in Neviweb130FloorThermostat.extra_state_attributes: {missing}"

    def test_floor_thermostat_has_floor_specific_keys(self):
        t = make_thermostat(737)
        attrs = t.extra_state_attributes
        missing = self.FLOOR_EXTRA_KEYS - set(attrs.keys())
        assert not missing, f"Missing floor keys in Neviweb130FloorThermostat.extra_state_attributes: {missing}"

    def test_low_thermostat_has_pump_protection_key(self):
        t = make_thermostat(7372)
        attrs = t.extra_state_attributes
        assert "pump_protection_status" in attrs, (
            "pump_protection_status missing from Neviweb130LowThermostat.extra_state_attributes"
        )

    def test_low_thermostat_has_cycle_length_key(self):
        t = make_thermostat(7372)
        attrs = t.extra_state_attributes
        assert "cycle_length" in attrs, (
            "cycle_length missing from Neviweb130LowThermostat.extra_state_attributes"
        )

    def test_low_thermostat_has_auxiliary_cycle_status_key(self):
        t = make_thermostat(7372)
        attrs = t.extra_state_attributes
        assert "auxiliary_cycle_status" in attrs, (
            "auxiliary_cycle_status missing from Neviweb130LowThermostat.extra_state_attributes"
        )

    def test_extra_state_attributes_returns_dict(self):
        """extra_state_attributes must return a dict (not None, not a list)."""
        for model in [1123, 737, 7372, 1510]:
            t = make_thermostat(model)
            attrs = t.extra_state_attributes
            assert isinstance(attrs, dict), f"Model {model}: extra_state_attributes is not a dict"

    def test_extra_state_attributes_id_matches_device(self):
        """The 'id' key must match the device id string."""
        t = make_thermostat(1123, device_id=42)
        attrs = t.extra_state_attributes
        assert attrs["id"] == "42"

    def test_extra_state_attributes_sku_matches(self):
        t = make_thermostat(1123)
        attrs = t.extra_state_attributes
        assert attrs["sku"] == "SKU"


# ===========================================================================
# Group C — update() polling contract
# ===========================================================================

@pytest.mark.unit
class TestGroupC_UpdatePollingContract:
    """Assert that update() calls get_device_attributes, get_neviweb_status, get_weather."""

    def _make_device_data(self):
        """Return a minimal valid device_data dict that update() can parse."""
        from custom_components.neviweb130.const import (
            ATTR_BACKLIGHT,
            ATTR_DISPLAY2,
            ATTR_DRSTATUS,
            ATTR_DRSETPOINT,
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
        return {
            ATTR_ROOM_TEMPERATURE: {"value": 21.0},
            ATTR_ROOM_SETPOINT: 20.0,
            ATTR_ROOM_SETPOINT_MIN: 5,
            ATTR_ROOM_SETPOINT_MAX: 30,
            ATTR_TEMP: "celsius",
            ATTR_TIME_FORMAT: "24h",
            ATTR_OUTPUT_PERCENT_DISPLAY: 0,
            ATTR_KEYPAD: "unlocked",
            ATTR_BACKLIGHT: "auto",
            ATTR_SYSTEM_MODE: "heat",
            ATTR_DISPLAY2: "setpoint",
            ATTR_WATTAGE: 1000,
        }

    def test_update_calls_get_device_attributes(self):
        client = make_client()
        hass = make_hass()
        client.get_device_attributes.return_value = self._make_device_data()
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        client.get_weather.return_value = {"temperature": 5.0, "icon": 1}
        client.get_device_sensor_error.return_value = {"raw": 0}

        t = make_thermostat(1123, client, hass)
        t.update()

        client.get_device_attributes.assert_called_once()

    def test_update_calls_get_neviweb_status(self):
        client = make_client()
        hass = make_hass()
        client.get_device_attributes.return_value = self._make_device_data()
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        client.get_weather.return_value = {"temperature": 5.0, "icon": 1}
        client.get_device_sensor_error.return_value = {"raw": 0}

        t = make_thermostat(1123, client, hass)
        t.update()

        client.get_neviweb_status.assert_called_once()

    def test_update_calls_get_weather(self):
        client = make_client()
        hass = make_hass()
        client.get_device_attributes.return_value = self._make_device_data()
        client.get_neviweb_status.return_value = {"occupancyMode": "home"}
        client.get_weather.return_value = {"temperature": 5.0, "icon": 1}
        client.get_device_sensor_error.return_value = {"raw": 0}

        t = make_thermostat(1123, client, hass)
        t.update()

        client.get_weather.assert_called_once()

    def test_update_skipped_when_inactive(self):
        """When _active is False, no client calls should be made (except snooze check)."""
        client = make_client()
        hass = make_hass()
        t = make_thermostat(1123, client, hass)
        t._active = False
        t._snooze = float("inf")  # never wake up

        t.update()

        client.get_device_attributes.assert_not_called()
        client.get_neviweb_status.assert_not_called()
        client.get_weather.assert_not_called()


# ===========================================================================
# Group D — model→class dispatch
# ===========================================================================

@pytest.mark.unit
class TestGroupD_ModelClassDispatch:
    """Assert each model number maps to the correct entity subclass."""

    def _dispatch(self, model: int):
        """Run async_setup_platform with a single device of the given model and return the entity."""
        import asyncio
        from custom_components.neviweb130.climate import async_setup_platform

        client = make_client()
        hass = make_hass()

        device_info = make_device_info(1, model)
        client.gateway_data = [device_info]
        client.gateway_data2 = []
        client.gateway_data3 = []
        client.default_group_name.return_value = "neviweb130 climate"

        data = MagicMock()
        data.migration_done = asyncio.Event()
        data.migration_done.set()
        data.neviweb130_clients = [client]
        hass.data["neviweb130"]["data"] = data

        captured = []

        def fake_add_entities(entities, update=False):
            captured.extend(entities)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                async_setup_platform(hass, {}, fake_add_entities, discovery_info=None)
            )
        finally:
            loop.close()

        assert len(captured) == 1, f"Expected 1 entity for model {model}, got {len(captured)}"
        return captured[0]

    def test_model_737_is_floor_thermostat(self):
        from custom_components.neviweb130.climate import Neviweb130FloorThermostat
        entity = self._dispatch(737)
        assert isinstance(entity, Neviweb130FloorThermostat), (
            f"Model 737 should be Neviweb130FloorThermostat, got {type(entity).__name__}"
        )

    def test_model_6810_is_hp_thermostat(self):
        from custom_components.neviweb130.climate import Neviweb130HPThermostat
        entity = self._dispatch(6810)
        assert isinstance(entity, Neviweb130HPThermostat), (
            f"Model 6810 should be Neviweb130HPThermostat, got {type(entity).__name__}"
        )

    def test_model_6727_is_heat_cool_thermostat(self):
        from custom_components.neviweb130.climate import Neviweb130HeatCoolThermostat
        entity = self._dispatch(6727)
        assert isinstance(entity, Neviweb130HeatCoolThermostat), (
            f"Model 6727 should be Neviweb130HeatCoolThermostat, got {type(entity).__name__}"
        )

    def test_model_1123_is_base_thermostat(self):
        from custom_components.neviweb130.climate import Neviweb130Thermostat
        entity = self._dispatch(1123)
        assert type(entity) is Neviweb130Thermostat, (
            f"Model 1123 should be Neviweb130Thermostat, got {type(entity).__name__}"
        )

    def test_model_1510_is_wifi_thermostat(self):
        from custom_components.neviweb130.climate import Neviweb130WifiThermostat
        entity = self._dispatch(1510)
        assert isinstance(entity, Neviweb130WifiThermostat), (
            f"Model 1510 should be Neviweb130WifiThermostat, got {type(entity).__name__}"
        )


# ===========================================================================
# Group E — error code handling
# ===========================================================================

@pytest.mark.unit
class TestGroupE_ErrorCodeHandling:
    """Assert error codes trigger the correct recovery behavior."""

    def test_usrsessexp_calls_reconnect(self):
        """USRSESSEXP error must call client.reconnect()."""
        client = make_client()
        hass = make_hass()
        t = make_thermostat(1123, client, hass)

        t.log_error("USRSESSEXP")

        client.reconnect.assert_called_once()

    def test_dvcunvlb_sets_active_false(self):
        """DVCUNVLB error must set entity._active = False."""
        client = make_client()
        hass = make_hass()
        t = make_thermostat(1123, client, hass)
        assert t._active is True  # precondition

        t.log_error("DVCUNVLB")

        assert t._active is False, "DVCUNVLB should deactivate the entity"

    def test_dvcunvlb_does_not_call_reconnect(self):
        """DVCUNVLB should NOT reconnect — it deactivates instead."""
        client = make_client()
        hass = make_hass()
        t = make_thermostat(1123, client, hass)

        t.log_error("DVCUNVLB")

        client.reconnect.assert_not_called()

    def test_usrsessexp_does_not_deactivate(self):
        """USRSESSEXP should reconnect, not deactivate."""
        client = make_client()
        hass = make_hass()
        t = make_thermostat(1123, client, hass)

        t.log_error("USRSESSEXP")

        assert t._active is True, "USRSESSEXP should not deactivate the entity"

    def test_unknown_error_does_not_raise(self):
        """Unknown error codes must not raise — they fall through to a warning log."""
        client = make_client()
        hass = make_hass()
        t = make_thermostat(1123, client, hass)

        # Should not raise
        t.log_error("SOME_UNKNOWN_ERROR_CODE_XYZ")

    def test_accdayreqmax_does_not_reconnect(self):
        """ACCDAYREQMAX should only log, not reconnect."""
        client = make_client()
        hass = make_hass()
        t = make_thermostat(1123, client, hass)

        t.log_error("ACCDAYREQMAX")

        client.reconnect.assert_not_called()
        assert t._active is True
