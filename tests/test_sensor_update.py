"""
Unit tests for sensor.py and update.py behavior.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


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
# Neviweb130Sensor (water leak, model 5051)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestLeakSensor:

    def _make(self, model=5051):
        from custom_components.neviweb130.sensor import Neviweb130Sensor
        client = make_client()
        hass = make_hass()
        info = make_device_info(100, model, "Leak Sensor", "WL4200")
        s = Neviweb130Sensor(info, "Leak Sensor", "leak", "WL4200", "1.0.0", client)
        s.hass = hass
        return s, client

    def test_set_sensor_alert_calls_client_with_correct_args(self):
        s, client = self._make()
        s.set_sensor_alert({"id": "100", "leak": 1, "batt": 1, "temp": 0, "close": "never"})
        client.set_sensor_alert.assert_called_once_with("100", 1, 1, 0, "never")

    def test_set_sensor_alert_updates_leak_alert_true(self):
        s, client = self._make()
        s.set_sensor_alert({"id": "100", "leak": 1, "batt": 0, "temp": 0, "close": "never"})
        assert s._leak_alert is True

    def test_set_sensor_alert_updates_leak_alert_false(self):
        s, client = self._make()
        s.set_sensor_alert({"id": "100", "leak": 0, "batt": 0, "temp": 0, "close": "never"})
        assert s._leak_alert is False

    def test_set_sensor_alert_updates_temp_alert(self):
        s, client = self._make()
        s.set_sensor_alert({"id": "100", "leak": 0, "batt": 0, "temp": 1, "close": "never"})
        assert s._temp_alert is True

    def test_set_sensor_alert_updates_battery_alert(self):
        s, client = self._make()
        s.set_sensor_alert({"id": "100", "leak": 0, "batt": 1, "temp": 0, "close": "never"})
        assert s._battery_alert is True

    def test_set_sensor_alert_updates_closure_action(self):
        s, client = self._make()
        s.set_sensor_alert({"id": "100", "leak": 1, "batt": 0, "temp": 0, "close": "closeImmediately"})
        assert s._closure_action == "closeImmediately"

    def test_set_battery_type_calls_client(self):
        s, client = self._make()
        s.set_battery_type({"id": "100", "type": "lithium"})
        client.set_battery_type.assert_called_once_with("100", "lithium")

    def test_set_battery_type_updates_state(self):
        s, client = self._make()
        s.set_battery_type({"id": "100", "type": "alkaline"})
        assert s._battery_type == "alkaline"

    def test_set_activation_deactivates(self):
        s, client = self._make()
        s.set_activation({"id": "100", "active": False})
        assert s._active is False

    def test_set_activation_reactivates(self):
        s, client = self._make()
        s._active = False
        s.set_activation({"id": "100", "active": True})
        assert s._active is True


# ---------------------------------------------------------------------------
# Client set_sensor_alert JSON keys
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestClientSensorAlertKeys:

    def _make_client(self):
        from custom_components.neviweb130 import Neviweb130Client
        with patch.object(Neviweb130Client, "__init__", lambda self, *a, **kw: None):
            c = Neviweb130Client.__new__(Neviweb130Client)
        c.hass = make_hass()
        c.set_device_attributes = MagicMock()
        return c

    def test_set_sensor_alert_uses_alertLowBatt(self):
        c = self._make_client()
        c.set_sensor_alert("100", 1, 1, 0, "never")
        args = c.set_device_attributes.call_args[0]
        assert "alertLowBatt" in args[1]
        assert args[1]["alertLowBatt"] == 1

    def test_set_sensor_alert_uses_alertWaterLeak(self):
        c = self._make_client()
        c.set_sensor_alert("100", 1, 0, 0, "never")
        args = c.set_device_attributes.call_args[0]
        assert "alertWaterLeak" in args[1]
        assert args[1]["alertWaterLeak"] == 1

    def test_set_sensor_alert_uses_cfgValveClosure(self):
        c = self._make_client()
        c.set_sensor_alert("100", 0, 0, 0, "closeImmediately")
        args = c.set_device_attributes.call_args[0]
        assert "cfgValveClosure" in args[1]
        assert args[1]["cfgValveClosure"] == "closeImmediately"

    def test_set_battery_type_uses_batteryType(self):
        c = self._make_client()
        c.set_battery_type("100", "lithium")
        c.set_device_attributes.assert_called_once_with("100", {"batteryType": "lithium"})

    def test_set_tank_type_uses_tankType(self):
        c = self._make_client()
        c.set_tank_type("100", "propane")
        c.set_device_attributes.assert_called_once_with("100", {"tankType": "propane"})

    def test_set_gauge_type_uses_gaugeType(self):
        c = self._make_client()
        c.set_gauge_type("100", "1")
        args = c.set_device_attributes.call_args[0]
        assert "gaugeType" in args[1]

    def test_set_low_fuel_alert_uses_alertLowFuelPercent(self):
        c = self._make_client()
        c.set_low_fuel_alert("100", 20)
        c.set_device_attributes.assert_called_once_with("100", {"alertLowFuelPercent": 20})

    def test_set_refuel_alert_uses_alertRefuel(self):
        c = self._make_client()
        c.set_refuel_alert("100", True)
        c.set_device_attributes.assert_called_once_with("100", {"alertRefuel": True})

    def test_set_tank_height_uses_tankHeight(self):
        c = self._make_client()
        c.set_tank_height("100", 120)
        c.set_device_attributes.assert_called_once_with("100", {"tankHeight": 120})

    def test_set_fuel_alert_uses_alertLowFuel(self):
        c = self._make_client()
        c.set_fuel_alert("100", True)
        c.set_device_attributes.assert_called_once_with("100", {"alertLowFuel": True})

    def test_set_battery_alert_uses_alertLowBatt(self):
        c = self._make_client()
        c.set_battery_alert("100", True)
        c.set_device_attributes.assert_called_once_with("100", {"alertLowBatt": True})


# ---------------------------------------------------------------------------
# TankSensor set_* methods (model 5056)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTankSensor:

    def _make(self):
        from custom_components.neviweb130.sensor import Neviweb130TankSensor
        client = make_client()
        hass = make_hass()
        info = make_device_info(200, 5056, "Tank Sensor", "LM4110-ZB")
        s = Neviweb130TankSensor(info, "Tank Sensor", "level", "LM4110-ZB", "1.0.0", client)
        s.hass = hass
        return s, client

    def test_set_tank_type_calls_client(self):
        s, client = self._make()
        s.set_tank_type({"id": "200", "type": "propane"})
        client.set_tank_type.assert_called_once_with("200", "propane")

    def test_set_tank_type_updates_state(self):
        s, client = self._make()
        s.set_tank_type({"id": "200", "type": "oil"})
        assert s._tank_type == "oil"

    def test_set_gauge_type_calls_client(self):
        s, client = self._make()
        s.set_gauge_type({"id": "200", "gauge": 1})
        client.set_gauge_type.assert_called_once_with("200", "1")

    def test_set_gauge_type_updates_state(self):
        s, client = self._make()
        s.set_gauge_type({"id": "200", "gauge": 2})
        assert s._gauge_type == "2"

    def test_set_low_fuel_alert_calls_client(self):
        s, client = self._make()
        s.set_low_fuel_alert({"id": "200", "low": 20})
        client.set_low_fuel_alert.assert_called_once_with("200", 20)

    def test_set_low_fuel_alert_updates_state(self):
        s, client = self._make()
        s.set_low_fuel_alert({"id": "200", "low": 15})
        assert s._fuel_percent_alert == 15

    def test_set_refuel_alert_calls_client(self):
        s, client = self._make()
        s.set_refuel_alert({"id": "200", "refuel": True})
        client.set_refuel_alert.assert_called_once_with("200", True)

    def test_set_tank_height_calls_client(self):
        s, client = self._make()
        s.set_tank_height({"id": "200", "height": 120})
        client.set_tank_height.assert_called_once_with("200", 120)

    def test_set_tank_height_updates_state(self):
        s, client = self._make()
        s.set_tank_height({"id": "200", "height": 100})
        assert s._tank_height == 100

    def test_set_fuel_alert_calls_client(self):
        s, client = self._make()
        s.set_fuel_alert({"id": "200", "fuel": True})
        client.set_fuel_alert.assert_called_once_with("200", True)

    def test_set_fuel_alert_updates_state(self):
        s, client = self._make()
        s.set_fuel_alert({"id": "200", "fuel": False})
        assert s._fuel_alert is False

    def test_set_battery_alert_calls_client(self):
        s, client = self._make()
        s.set_battery_alert({"id": "200", "batt": True})
        client.set_battery_alert.assert_called_once_with("200", True)


# ---------------------------------------------------------------------------
# GatewaySensor set_neviweb_status (model 130)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGatewaySensor:

    def _make(self):
        from custom_components.neviweb130.sensor import Neviweb130GatewaySensor
        client = make_client()
        hass = make_hass()
        info = make_device_info(300, 130, "GT130", "GT130")
        # signature: (device_info, name, device_type, sku, firmware, location, client)
        s = Neviweb130GatewaySensor(info, "GT130", "gateway", "GT130", "1.0.0", 1, client)
        s.hass = hass
        return s, client

    def test_set_neviweb_status_calls_post(self):
        s, client = self._make()
        s.set_neviweb_status({"id": "300", "mode": "away"})
        client.post_neviweb_status.assert_called_once_with(s._location, "away")

    def test_set_neviweb_status_updates_occupancy(self):
        s, client = self._make()
        s.set_neviweb_status({"id": "300", "mode": "home"})
        assert s._occupancyMode == "home"

    def test_set_neviweb_status_away(self):
        s, client = self._make()
        s.set_neviweb_status({"id": "300", "mode": "away"})
        assert s._occupancyMode == "away"


# ---------------------------------------------------------------------------
# Neviweb130UpdateEntity
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestUpdateEntity:

    def _make(self, installed="1.0.0", latest="1.1.0", notes=""):
        from custom_components.neviweb130.update import Neviweb130UpdateEntity
        hass = MagicMock()
        hass.config.path = MagicMock(return_value="/tmp/neviweb130")
        data = MagicMock()
        data.current_version = installed
        data.available_version = latest
        data.release_notes = notes
        data.release_title = "Test Release"
        entity = Neviweb130UpdateEntity(hass, data)
        return entity, hass

    def test_installed_version(self):
        e, _ = self._make(installed="1.0.0")
        assert e.installed_version == "1.0.0"

    def test_latest_version(self):
        e, _ = self._make(latest="1.2.0")
        assert e.latest_version == "1.2.0"

    def test_update_available_when_versions_differ(self):
        e, _ = self._make(installed="1.0.0", latest="1.1.0")
        attrs = e.extra_state_attributes
        assert attrs["update_available"] is True

    def test_no_update_when_versions_same(self):
        e, _ = self._make(installed="1.0.0", latest="1.0.0")
        attrs = e.extra_state_attributes
        assert attrs["update_available"] is False

    def test_extra_state_attributes_contains_update_status(self):
        e, _ = self._make()
        attrs = e.extra_state_attributes
        assert "update_status" in attrs

    def test_extra_state_attributes_contains_rollback_status(self):
        e, _ = self._make()
        attrs = e.extra_state_attributes
        assert "rollback_status" in attrs

    def test_has_breaking_changes_false_by_default(self):
        e, _ = self._make(notes="Some release notes")
        assert e.has_breaking_changes is False

    def test_has_breaking_changes_detected(self):
        e, _ = self._make(notes="## Breaking Changes\nThis update requires manual changes.")
        assert e.has_breaking_changes is True

    def test_title_contains_version(self):
        e, _ = self._make(latest="1.2.0")
        assert "1.2.0" in e.title

    def test_title_marks_prerelease(self):
        e, _ = self._make(latest="1.2.0b1")
        assert "PRE-RELEASE" in e.title or "🚧" in e.title

    def test_title_marks_breaking(self):
        e, _ = self._make(latest="2.0.0", notes="breaking change: requires reconfiguration")
        assert "BREAKING" in e.title or "🛑" in e.title

    def test_release_url_contains_version(self):
        e, _ = self._make(latest="1.2.0")
        assert "1.2.0" in e.release_url

    def test_release_summary_shown_when_update_available(self):
        e, _ = self._make(installed="1.0.0", latest="1.1.0")
        assert e.release_summary is not None

    def test_release_summary_none_when_up_to_date(self):
        e, _ = self._make(installed="1.0.0", latest="1.0.0")
        assert e.release_summary is None

    def test_in_progress_false_initially(self):
        e, _ = self._make()
        assert e.in_progress is False

    def test_update_percentage_none_initially(self):
        e, _ = self._make()
        assert e.update_percentage is None

    def test_requires_restart_true(self):
        e, _ = self._make()
        assert e.requires_restart is True


@pytest.mark.unit
class TestUpdateEntityHelpers:
    """Tests for helpers used by the update entity."""

    def test_has_breaking_changes_keyword_breaking_change(self):
        from custom_components.neviweb130.helpers import has_breaking_changes
        assert has_breaking_changes("## breaking change in this release") is True

    def test_has_breaking_changes_keyword_requires_manual(self):
        from custom_components.neviweb130.helpers import has_breaking_changes
        assert has_breaking_changes("This update requires manual changes.") is True

    def test_has_breaking_changes_false_for_normal_notes(self):
        from custom_components.neviweb130.helpers import has_breaking_changes
        assert has_breaking_changes("Bug fixes and improvements") is False

    def test_has_breaking_changes_false_for_empty(self):
        from custom_components.neviweb130.helpers import has_breaking_changes
        assert has_breaking_changes("") is False

    def test_has_breaking_changes_false_for_none(self):
        from custom_components.neviweb130.helpers import has_breaking_changes
        assert has_breaking_changes(None) is False

    def test_build_update_summary_contains_compare_link(self):
        from custom_components.neviweb130.helpers import build_update_summary
        result = build_update_summary("1.0.0", "1.1.0", "## What's Changed\n* Fix bug in https://github.com/x")
        assert "1.0.0" in result
        assert "1.1.0" in result
        assert "compare" in result

    def test_build_update_summary_empty_versions(self):
        from custom_components.neviweb130.helpers import build_update_summary
        result = build_update_summary("", "", "")
        assert "latest" in result.lower()

    def test_build_update_summary_strips_github_links(self):
        from custom_components.neviweb130.helpers import build_update_summary
        notes = "## What's Changed\n* Fix something in https://github.com/claudegel/sinope-130/pull/1\n"
        result = build_update_summary("1.0.0", "1.1.0", notes)
        # The PR URL in the body should be stripped; only the compare link remains
        assert "* Fix something" in result
        assert "/pull/1" not in result


@pytest.mark.unit
class TestUpdateEntityAsyncInstall:
    """Tests for async_install downgrade guard."""

    def _make(self, installed="1.1.0", latest="1.2.0"):
        from custom_components.neviweb130.update import Neviweb130UpdateEntity
        import asyncio
        hass = MagicMock()
        hass.config.path = MagicMock(return_value="/tmp/neviweb130")
        hass.async_add_executor_job = AsyncMock(return_value=None)
        hass.services.async_call = AsyncMock()
        hass.loop = asyncio.new_event_loop()
        data = MagicMock()
        data.current_version = installed
        data.available_version = latest
        data.release_notes = ""
        data.release_title = ""
        entity = Neviweb130UpdateEntity(hass, data)
        entity.async_write_ha_state = MagicMock()
        return entity, hass

    def test_downgrade_refused(self):
        import asyncio
        e, _ = self._make(installed="1.2.0", latest="1.1.0")
        asyncio.get_event_loop().run_until_complete(e._do_update("1.0.0"))
        assert e._in_progress is False
        assert e._update_percentage is None
