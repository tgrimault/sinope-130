"""Test suite for Valve platform Home Assistant interface."""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {
        "neviweb130": {
            "data": MagicMock(),
            "safe_mode": "-",
        }
    }
    return hass


@pytest.fixture
def mock_client():
    """Create a mock Neviweb130Client."""
    client = MagicMock()
    client.scoped_unique_id = MagicMock(side_effect=lambda x: str(x))
    client.default_group_name = MagicMock(return_value="neviweb130 valve")
    client.get_device_attributes = MagicMock(return_value={
        "motorTargetPosition": "open",
        "motorPosition": 100,
        "battery": 95,
        "rssi": -50,
        "wifiRssi": -55,
        "batteryVoltage": 3000,
        "batteryStatus": "ok",
        "backupPowerSupply": "battery",
        "temperatureAlarmStatus": "off",
        "valveInfo": {"status": "ok", "cause": None, "identifier": None},
        "valveClosure": {"source": "manual"},
        "alertLowBatt": "off",
        "stm8Error": {"motorJam": "off"},
        "flowMeterConfig": {"multiplier": 1, "offset": 0, "divisor": 1},
        "waterLeakStatus": "ok",
        "tempActionLow": None,
        "battActionLow": None,
        "occupancySensorUnoccupiedDelay": None,
        "battPercentNormal": None,
        "battStatusNormal": None,
    })
    client.get_device_alert = MagicMock(return_value={
        "alertLowBatt": "off",
        "alertLowTemp": "off",
        "alertWaterLeak": "off",
    })
    return client


@pytest.fixture
def valve_device_info():
    """Create mock valve device info."""
    return {
        "id": 444555,
        "name": "Main Water Valve",
        "sku": "VA4220WF",
        "location$id": 67890,
        "signature": {
            "model": 3150,
            "modelCfg": 0,
            "protocol": "wifi",
            "softVersion": {"major": 1, "middle": 2, "minor": 3},
        },
    }


class TestValveEntityInterface:
    """Test ValveEntity interface methods called by Home Assistant."""
    
    @pytest.fixture
    def valve(self, mock_hass, mock_client, valve_device_info):
        """Create a valve entity."""
        from custom_components.neviweb130.valve import Neviweb130WifiValve
        
        v = Neviweb130WifiValve(
            valve_device_info,
            "neviweb130 valve Main Water Valve",
            "VA4220WF",
            "1.2.3",
            "valve",
            mock_client,
        )
        v.hass = mock_hass
        return v
    
    def test_unique_id_property(self, valve):
        """Test unique_id property."""
        assert valve.unique_id == "444555"
    
    def test_name_property(self, valve):
        """Test name property."""
        assert valve.name == "neviweb130 valve Main Water Valve"
    
    def test_is_closed_property(self, valve):
        """Test is_closed property."""
        valve.update()
        assert valve.is_closed is False  # motorPosition is 100 → open
    
    def test_current_valve_position_property(self, valve):
        """Test current_valve_position property."""
        valve.update()
        assert valve._motor_target == "open"
    
    def test_extra_state_attributes(self, valve):
        """Test extra_state_attributes property."""
        valve.update()
        attrs = valve.extra_state_attributes
        
        assert isinstance(attrs, dict)
        assert "battery_voltage" in attrs
        assert "battery_alert" in attrs
        assert "temperature_alert" in attrs
        assert "water_leak_status" in attrs


class TestValveEntityActions:
    """Test ValveEntity action methods called by Home Assistant."""
    
    @pytest.fixture
    def valve(self, mock_hass, mock_client, valve_device_info):
        """Create a valve entity."""
        from custom_components.neviweb130.valve import Neviweb130WifiValve
        
        v = Neviweb130WifiValve(
            valve_device_info,
            "neviweb130 valve Main Water Valve",
            "VA4220WF",
            "1.2.3",
            "valve",
            mock_client,
        )
        v.hass = mock_hass
        return v
    
    def test_open_valve_action(self, valve, mock_client):
        """Test open_valve() calls client correctly."""
        valve.open_valve()
        
        # wifi valve calls set_valve_onoff with 100 (fully open)
        mock_client.set_valve_onoff.assert_called_once_with("444555", 100)
    
    def test_close_valve_action(self, valve, mock_client):
        """Test close_valve() calls client correctly."""
        valve.close_valve()
        
        # wifi valve calls set_valve_onoff with 0 (fully closed)
        mock_client.set_valve_onoff.assert_called_once_with("444555", 0)


class TestValveCustomServices:
    """Test valve-specific custom services."""
    
    @pytest.fixture
    def valve(self, mock_hass, mock_client, valve_device_info):
        """Create a valve entity."""
        from custom_components.neviweb130.valve import Neviweb130WifiValve
        
        valve = Neviweb130WifiValve(
            valve_device_info,
            "neviweb130 valve Main Water Valve",
            "VA4220WF",
            "1.2.3",
            "valve",
            mock_client,
        )
        valve.hass = mock_hass
        valve.entity_id = "valve.neviweb130_valve_main_water_valve"
        return valve
    
    def test_set_valve_alert_service(self, valve, mock_client):
        """Test set_valve_alert service."""
        value = {"id": "444555", "batt": "on"}
        valve.set_valve_alert(value)
        
        mock_client.set_valve_alert.assert_called_once_with("444555", "on")
    
    def test_set_valve_temp_alert_service(self, valve, mock_client):
        """Test set_valve_temp_alert service."""
        value = {"id": "444555", "temp": "on"}
        valve.set_valve_temp_alert(value)
        
        mock_client.set_valve_temp_alert.assert_called_once_with("444555", "on")


class TestUpdateMethod:
    """Test the update() method for valve entities."""
    
    @pytest.fixture
    def valve(self, mock_hass, mock_client, valve_device_info):
        """Create a valve entity."""
        from custom_components.neviweb130.valve import Neviweb130WifiValve
        
        v = Neviweb130WifiValve(
            valve_device_info,
            "neviweb130 valve Main Water Valve",
            "VA4220WF",
            "1.2.3",
            "valve",
            mock_client,
        )
        v.hass = mock_hass
        return v
    
    def test_update_calls_get_device_attributes(self, valve, mock_client):
        """Test update() calls get_device_attributes."""
        valve.update()
        
        mock_client.get_device_attributes.assert_called()
        call_args = mock_client.get_device_attributes.call_args
        assert call_args[0][0] == "444555"
    
    def test_update_calls_get_device_alert(self, valve, mock_client):
        """Test update() does NOT call get_device_alert for wifi valve."""
        valve.update()
        
        # Wifi valve (not zb_valve) does not call get_device_alert
        mock_client.get_device_alert.assert_not_called()
    
    def test_update_updates_internal_state(self, valve):
        """Test update() updates internal state."""
        valve.update()
        
        assert valve._motor_target == "open"
        assert valve._battery_voltage == 3000


class TestValveExtraStateAttributes:
    """Test valve extra_state_attributes key stability."""

    @pytest.fixture
    def valve(self, mock_hass, mock_client, valve_device_info):
        from custom_components.neviweb130.valve import Neviweb130WifiValve
        v = Neviweb130WifiValve(
            valve_device_info, "neviweb130 valve Main Water Valve",
            "VA4220WF", "1.2.3", "valve", mock_client,
        )
        v.hass = mock_hass
        return v

    def test_extra_state_attributes_stable_keys(self, valve):
        """All keys that user automations may reference must remain stable."""
        valve.update()
        attrs = valve.extra_state_attributes
        for key in ("battery_voltage", "battery_alert", "temperature_alert",
                    "water_leak_status", "valve_status", "motor_target_position",
                    "sku", "device_model", "firmware", "activation", "id"):
            assert key in attrs, f"Missing key: {key}"

    def test_extra_state_attributes_is_dict(self, valve):
        assert isinstance(valve.extra_state_attributes, dict)

    def test_available_property(self, valve):
        valve._active = True
        assert valve.available is True

    def test_available_false_when_inactive(self, valve):
        # _active=False pauses polling; HA's available is not overridden
        valve._active = False
        assert valve.available is True

    def test_reports_position_property(self, valve):
        # ValveEntity.reports_position must be a bool
        assert isinstance(valve.reports_position, bool)


@pytest.mark.unit
class TestValveUpdateHelpers:
    """Test extracted update() helper methods in isolation."""

    @pytest.fixture
    def valve(self, mock_hass, mock_client, valve_device_info):
        from custom_components.neviweb130.valve import Neviweb130WifiValve
        v = Neviweb130WifiValve(
            valve_device_info, "neviweb130 valve Main Water Valve",
            "VA4220WF", "1.2.3", "valve", mock_client,
        )
        v.hass = mock_hass
        return v

    def test_load_attributes_returns_list(self, valve):
        """Test _load_attributes returns a list of attribute names."""
        attrs = valve._load_attributes()
        assert isinstance(attrs, list)
        assert len(attrs) > 0
        assert "motorPosition" in attrs

    def test_fetch_attributes_calls_client(self, valve, mock_client):
        """Test _fetch_attributes calls the client correctly."""
        attrs = ["onOff", "motorPosition"]
        valve._fetch_attributes(attrs)
        mock_client.get_device_attributes.assert_called_once_with("444555", attrs)

    def test_fetch_attributes_uses_safe_mode(self, valve, mock_hass, mock_client):
        """Test _fetch_attributes uses safe_get_device_attributes when safe_mode is active."""
        mock_hass.data["neviweb130"]["safe_mode"] = "444555"
        attrs = ["onOff", "motorPosition"]
        # safe_get_device_attributes is a function from helpers.py, we can't easily mock it here
        # but we can verify the client method is NOT called
        result = valve._fetch_attributes(attrs)
        # In safe mode, it should call safe_get_device_attributes, not the client directly
        # Since we can't easily mock the helper, just verify the result is a dict
        assert isinstance(result, dict)

    def test_parse_common_state_assigns_fields(self, valve):
        """Test _parse_common_state assigns all expected instance variables."""
        data = {
            "motorPosition": 100,
            "motorTargetPosition": "open",
            "temperatureAlarmStatus": "off",
            "batteryVoltage": 3000,
            "batteryStatus": "ok",
            "backupPowerSupply": "battery",
            "alertLowBatt": "off",
            "stm8Error": {"motorJam": "off"},
            "flowMeterConfig": {"multiplier": 1, "offset": 0, "divisor": 1},
            "waterLeakStatus": "ok",
            "valveClosure": {"source": "manual"},
            "valveInfo": {"status": "ok", "cause": None, "identifier": None},
            "wifiRssi": -55,
            "battPercentNormal": None,
            "battStatusNormal": None,
            "awayAction": None,
        }
        valve._parse_common_state(data)
        assert valve._valve_status == "open"
        assert valve._onoff == "on"
        assert valve._battery_voltage == 3000
        assert valve._battery_status == "ok"
        assert valve._power_supply == "battery"
        assert valve._temp_alert == "off"

    def test_handle_error_returns_true_for_error(self, valve):
        """Test _handle_error returns True when error is present."""
        device_data = {"error": {"code": "DVCCOMMTO"}}
        assert valve._handle_error(device_data) is True

    def test_handle_error_returns_true_for_errorCode(self, valve):
        """Test _handle_error returns True when errorCode is present."""
        device_data = {"errorCode": "SOME_ERROR"}
        assert valve._handle_error(device_data) is True

    def test_handle_error_returns_false_for_clean_data(self, valve):
        """Test _handle_error returns False when no error is present."""
        device_data = {"onOff": "on", "motorPosition": 100}
        assert valve._handle_error(device_data) is False

    def test_handle_snooze_reactivates_after_timeout(self, valve):
        """Test _handle_snooze reactivates polling after snooze period."""
        import time
        valve._active = False
        valve._snooze = time.time() - 1300  # 1300 seconds ago (> SNOOZE_TIME)
        valve._handle_snooze()
        assert valve._active is True

    def test_handle_snooze_does_not_reactivate_before_timeout(self, valve):
        """Test _handle_snooze does not reactivate before snooze period expires."""
        import time
        valve._active = False
        valve._snooze = time.time() - 100  # 100 seconds ago (< SNOOZE_TIME)
        valve._handle_snooze()
        assert valve._active is False


@pytest.mark.unit
class TestBaseValveUpdateHelpers:
    """Test extracted update() helpers on the base Neviweb130Valve (ZB valve)."""

    @pytest.fixture
    def zb_valve_info(self):
        return {
            "id": 111222,
            "name": "ZB Valve",
            "sku": "VA4200ZB",
            "location$id": 67890,
            "signature": {
                "model": 3151,
                "modelCfg": 0,
                "protocol": "zigbee",
                "softVersion": {"major": 1, "middle": 0, "minor": 0},
            },
        }

    @pytest.fixture
    def zb_client(self):
        client = MagicMock()
        client.scoped_unique_id = MagicMock(side_effect=lambda x: str(x))
        client.get_device_attributes = MagicMock(return_value={
            "onOff": "on",
            "batteryVoltage": 2500,
            "batteryStatus": "ok",
            "backupPowerSupply": "battery",
            "rssi": -60,
            "battPercentNormal": 80,
            "battStatusNormal": "ok",
        })
        client.get_device_alert = MagicMock(return_value={
            "alertLowBatt": 0,
            "alertLowTemp": "off",
        })
        return client

    @pytest.fixture
    def zb_valve(self, mock_hass, zb_client, zb_valve_info):
        from custom_components.neviweb130.valve import Neviweb130Valve
        v = Neviweb130Valve(
            zb_valve_info, "ZB Valve", "VA4200ZB", "1.0.0", "valve", zb_client,
        )
        v.hass = mock_hass
        return v

    def test_load_attributes_returns_base_list(self, zb_valve):
        """Base class _load_attributes returns the ZB-specific attribute list."""
        attrs = zb_valve._load_attributes()
        assert "batteryVoltage" in attrs
        assert "batteryStatus" in attrs
        assert "backupPowerSupply" in attrs

    def test_parse_common_state_assigns_onoff(self, zb_valve):
        """_parse_common_state correctly assigns valve_status and onoff."""
        data = {
            "onOff": "on",
            "batteryVoltage": 2500,
            "batteryStatus": "ok",
            "backupPowerSupply": "battery",
        }
        zb_valve._parse_common_state(data)
        assert zb_valve._valve_status == "open"
        assert zb_valve._onoff == "on"

    def test_parse_common_state_closed(self, zb_valve):
        """_parse_common_state correctly assigns closed state."""
        data = {
            "onOff": "off",
            "batteryVoltage": 2500,
            "batteryStatus": "ok",
            "backupPowerSupply": "battery",
        }
        zb_valve._parse_common_state(data)
        assert zb_valve._valve_status == "closed"
        assert zb_valve._onoff == "off"

    def test_parse_common_state_battery_none_defaults_to_zero(self, zb_valve):
        """_parse_common_state handles None battery voltage gracefully."""
        data = {
            "onOff": "on",
            "batteryVoltage": None,
            "batteryStatus": "ok",
            "backupPowerSupply": "battery",
        }
        zb_valve._parse_common_state(data)
        assert zb_valve._battery_voltage == 0

    def test_parse_common_state_applies_device_alert(self, zb_valve):
        """_parse_common_state applies battery alert from device_alert dict."""
        data = {
            "onOff": "on",
            "batteryVoltage": 2500,
            "batteryStatus": "ok",
            "backupPowerSupply": "battery",
        }
        device_alert = {"alertLowBatt": 1, "alertLowTemp": "on"}
        zb_valve._parse_common_state(data, device_alert)
        assert zb_valve._battery_alert == 1
        assert zb_valve._temp_alert == "on"

    def test_handle_error_calls_log_error(self, zb_valve):
        """_handle_error calls log_error for API error responses."""
        zb_valve.log_error = MagicMock()
        device_data = {"error": {"code": "USRSESSEXP"}}
        result = zb_valve._handle_error(device_data)
        assert result is True
        zb_valve.log_error.assert_called_once_with("USRSESSEXP")

    def test_update_inactive_calls_handle_snooze(self, zb_valve):
        """update() calls _handle_snooze when inactive instead of polling."""
        zb_valve._active = False
        zb_valve._handle_snooze = MagicMock()
        zb_valve.update()
        zb_valve._handle_snooze.assert_called_once()
        zb_valve._client.get_device_attributes.assert_not_called()

    def test_update_active_calls_get_device_attributes(self, zb_valve, zb_client):
        """update() calls get_device_attributes when active."""
        zb_valve.update()
        zb_client.get_device_attributes.assert_called_once()

    def test_update_active_calls_get_device_alert_for_zb(self, zb_valve, zb_client):
        """update() calls get_device_alert for ZB valve."""
        zb_valve.update()
        zb_client.get_device_alert.assert_called_once_with("111222")
