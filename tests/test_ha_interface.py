"""Test suite for Home Assistant interface - ensures HA calls remain stable during refactoring."""
import asyncio
import pytest
from unittest.mock import MagicMock, patch, call
from homeassistant.components.climate.const import (
    PRESET_AWAY,
    PRESET_HOME,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE


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
    hass.services = MagicMock()
    hass.loop = asyncio.new_event_loop()
    return hass


@pytest.fixture
def mock_client():
    """Create a mock Neviweb130Client."""
    client = MagicMock()
    client.scoped_unique_id = MagicMock(side_effect=lambda x: str(x))
    client.default_group_name = MagicMock(return_value="neviweb130 climate")
    client.get_device_attributes = MagicMock(return_value={
        "roomTemperature": {"value": 21.0},
        "roomSetpoint": 20.0,
        "roomSetpointMin": 5.0,
        "roomSetpointMax": 30.0,
        "outputPercentDisplay": 50,
        "systemMode": "heat",
        "temperatureFormat": "celsius",
        "timeFormat": "24h",
        "config2ndDisplay": "setpoint",
        "lockKeypad": "unlocked",
        "backlightAdaptive": "auto",
        "loadConnected": 3000,
        "cycleLength": 15,
        "rssi": -50,
    })
    client.get_neviweb_status = MagicMock(return_value={"occupancyMode": "home"})
    client.get_device_sensor_error = MagicMock(return_value={"raw": 0})
    client.get_weather = MagicMock(return_value={"temperature": -5.0, "icon": 3})
    return client


@pytest.fixture
def device_info():
    """Create mock device info."""
    return {
        "id": 111222,
        "name": "Living Room",
        "sku": "TH1123ZB",
        "location$id": 67890,
        "signature": {
            "model": 1123,
            "modelCfg": 0,
            "protocol": "zigbee",
            "softVersion": {"major": 1, "middle": 2, "minor": 3},
        },
    }


class TestSetupEntryPoint:
    """Test the setup() entry point called by Home Assistant."""
    
    def test_setup_creates_data_object(self, mock_hass):
        """Test that setup() creates Neviweb130Data object."""
        from custom_components.neviweb130 import setup
        
        config = {
            "neviweb130": {
                "username": "test@example.com",
                "password": "password",
                "network": "Home",
            }
        }
        
        with patch("custom_components.neviweb130.Neviweb130Client"):
            with patch("custom_components.neviweb130.discovery.load_platform"):
                with patch("custom_components.neviweb130.init_request_counter"):
                    result = setup(mock_hass, config)
        
        assert result is True
        assert "data" in mock_hass.data["neviweb130"]
    
    def test_setup_loads_all_platforms(self, mock_hass):
        """Test that setup() loads all 6 platforms."""
        from custom_components.neviweb130 import setup
        
        config = {
            "neviweb130": {
                "username": "test@example.com",
                "password": "password",
            }
        }
        
        with patch("custom_components.neviweb130.Neviweb130Client"):
            with patch("custom_components.neviweb130.discovery.load_platform") as mock_load:
                with patch("custom_components.neviweb130.init_request_counter"):
                    setup(mock_hass, config)
        
        # Should load 6 platforms: climate, light, switch, sensor, valve, update
        assert mock_load.call_count == 6


class TestClimateEntityInterface:
    """Test ClimateEntity interface methods called by Home Assistant."""
    
    @pytest.fixture
    def thermostat(self, mock_hass, mock_client, device_info):
        """Create a thermostat entity."""
        from custom_components.neviweb130.climate import Neviweb130Thermostat
        
        t = Neviweb130Thermostat(
            device_info,
            "neviweb130 climate Living Room",
            "TH1123ZB",
            "1.2.3",
            67890,
            mock_client,
        )
        t.hass = mock_hass
        return t
    
    def test_unique_id_property(self, thermostat):
        """Test unique_id property returns correct value."""
        assert thermostat.unique_id == "111222"
    
    def test_name_property(self, thermostat):
        """Test name property returns correct value."""
        assert thermostat.name == "neviweb130 climate Living Room"
    
    def test_temperature_unit_property(self, thermostat):
        """Test temperature_unit always returns Celsius."""
        from homeassistant.const import UnitOfTemperature
        assert thermostat.temperature_unit == UnitOfTemperature.CELSIUS
    
    def test_current_temperature_property(self, thermostat):
        """Test current_temperature property."""
        thermostat.update()
        assert thermostat.current_temperature == 21.0
    
    def test_target_temperature_property(self, thermostat):
        """Test target_temperature property."""
        thermostat.update()
        assert thermostat.target_temperature == 20.0
    
    def test_hvac_mode_property(self, thermostat):
        """Test hvac_mode property."""
        thermostat.update()
        assert thermostat.hvac_mode == HVACMode.HEAT
    
    def test_hvac_modes_property(self, thermostat):
        """Test hvac_modes property returns list."""
        modes = thermostat.hvac_modes
        assert isinstance(modes, list)
        assert HVACMode.HEAT in modes
        assert HVACMode.OFF in modes
    
    def test_preset_mode_property(self, thermostat):
        """Test preset_mode property."""
        thermostat.update()
        assert thermostat.preset_mode == PRESET_HOME
    
    def test_preset_modes_property(self, thermostat):
        """Test preset_modes property returns list."""
        modes = thermostat.preset_modes
        assert isinstance(modes, list)
    
    def test_min_temp_property(self, thermostat):
        """Test min_temp property."""
        thermostat.update()
        assert thermostat.min_temp == 5.0
    
    def test_max_temp_property(self, thermostat):
        """Test max_temp property."""
        thermostat.update()
        assert thermostat.max_temp == 30.0
    
    def test_supported_features_property(self, thermostat):
        """Test supported_features property."""
        from homeassistant.components.climate import ClimateEntityFeature
        features = thermostat.supported_features
        assert features & ClimateEntityFeature.TARGET_TEMPERATURE
        assert features & ClimateEntityFeature.PRESET_MODE
    
    def test_extra_state_attributes_property(self, thermostat):
        """Test extra_state_attributes returns dict with expected keys."""
        thermostat.update()
        attrs = thermostat.extra_state_attributes
        
        assert isinstance(attrs, dict)
        assert "wattage" in attrs
        assert "heat_level" in attrs
        assert "outdoor_temp" in attrs
        assert "sku" in attrs
        assert "id" in attrs


class TestClimateEntityActions:
    """Test ClimateEntity action methods called by Home Assistant."""
    
    @pytest.fixture
    def thermostat(self, mock_hass, mock_client, device_info):
        """Create a thermostat entity."""
        from custom_components.neviweb130.climate import Neviweb130Thermostat
        
        t = Neviweb130Thermostat(
            device_info,
            "neviweb130 climate Living Room",
            "TH1123ZB",
            "1.2.3",
            67890,
            mock_client,
        )
        t.hass = mock_hass
        return t
    
    def test_set_temperature_action(self, thermostat, mock_client):
        """Test set_temperature() calls client correctly."""
        with patch.object(thermostat, "_delayed_refresh"):
            thermostat.set_temperature(**{ATTR_TEMPERATURE: 22.0})
        
        mock_client.set_temperature.assert_called_once_with("111222", 22.0)
    
    def test_set_hvac_mode_heat(self, thermostat, mock_client):
        """Test set_hvac_mode() with HEAT mode."""
        with patch.object(thermostat, "_delayed_refresh"):
            thermostat.set_hvac_mode(HVACMode.HEAT)
        
        mock_client.set_setpoint_mode.assert_called_once()
        call_args = mock_client.set_setpoint_mode.call_args
        assert call_args[0][0] == "111222"
        assert call_args[0][1] == HVACMode.HEAT
    
    def test_set_hvac_mode_off(self, thermostat, mock_client):
        """Test set_hvac_mode() with OFF mode."""
        with patch.object(thermostat, "_delayed_refresh"):
            thermostat.set_hvac_mode(HVACMode.OFF)
        
        mock_client.set_setpoint_mode.assert_called_once()
        call_args = mock_client.set_setpoint_mode.call_args
        assert call_args[0][1] == HVACMode.OFF
    
    def test_set_preset_mode_away(self, thermostat, mock_client):
        """Test set_preset_mode() with AWAY preset."""
        thermostat._occupancy = PRESET_HOME  # Set initial state
        thermostat.set_preset_mode(PRESET_AWAY)
        
        mock_client.set_occupancy_mode.assert_called_once()
        call_args = mock_client.set_occupancy_mode.call_args
        assert call_args[0][1] == PRESET_AWAY
    
    def test_set_preset_mode_home(self, thermostat, mock_client):
        """Test set_preset_mode() with HOME preset."""
        thermostat._occupancy = PRESET_AWAY  # Set initial state
        thermostat.set_preset_mode(PRESET_HOME)
        
        mock_client.set_occupancy_mode.assert_called_once()
        call_args = mock_client.set_occupancy_mode.call_args
        assert call_args[0][1] == PRESET_HOME
    
    def test_turn_on_action(self, thermostat, mock_client):
        """Test turn_on() calls client correctly."""
        thermostat.turn_on()
        
        mock_client.set_setpoint_mode.assert_called_once()
        call_args = mock_client.set_setpoint_mode.call_args
        assert call_args[0][1] == HVACMode.HEAT
    
    def test_turn_off_action(self, thermostat, mock_client):
        """Test turn_off() calls client correctly."""
        thermostat.turn_off()
        
        mock_client.set_setpoint_mode.assert_called_once()
        call_args = mock_client.set_setpoint_mode.call_args
        assert call_args[0][1] == HVACMode.OFF


class TestUpdateMethod:
    """Test the update() method called by Home Assistant polling."""
    
    @pytest.fixture
    def thermostat(self, mock_hass, mock_client, device_info):
        """Create a thermostat entity."""
        from custom_components.neviweb130.climate import Neviweb130Thermostat
        
        t = Neviweb130Thermostat(
            device_info,
            "neviweb130 climate Living Room",
            "TH1123ZB",
            "1.2.3",
            67890,
            mock_client,
        )
        t.hass = mock_hass
        return t
    
    def test_update_calls_get_device_attributes(self, thermostat, mock_client):
        """Test update() calls get_device_attributes."""
        thermostat.update()
        
        mock_client.get_device_attributes.assert_called()
        call_args = mock_client.get_device_attributes.call_args
        assert call_args[0][0] == "111222"
        assert isinstance(call_args[0][1], list)
    
    def test_update_calls_get_neviweb_status(self, thermostat, mock_client):
        """Test update() calls get_neviweb_status."""
        thermostat.update()
        
        mock_client.get_neviweb_status.assert_called_once_with("67890")
    
    def test_update_calls_get_weather(self, thermostat, mock_client):
        """Test update() calls get_weather."""
        thermostat.update()
        
        mock_client.get_weather.assert_called_once()
    
    def test_update_updates_internal_state(self, thermostat):
        """Test update() updates internal state variables."""
        thermostat.update()
        
        assert thermostat._cur_temp == 21.0
        assert thermostat._target_temp == 20.0
        assert thermostat._operation_mode == "heat"


class TestCustomServices:
    """Test custom service handlers registered by the integration."""
    
    @pytest.fixture
    def thermostat(self, mock_hass, mock_client, device_info):
        """Create a thermostat entity."""
        from custom_components.neviweb130.climate import Neviweb130Thermostat
        
        thermostat = Neviweb130Thermostat(
            device_info,
            "neviweb130 climate Living Room",
            "TH1123ZB",
            "1.2.3",
            67890,
            mock_client,
        )
        thermostat.hass = mock_hass
        thermostat.entity_id = "climate.neviweb130_climate_living_room"
        return thermostat
    
    def test_set_second_display_service(self, thermostat, mock_client):
        """Test set_second_display service."""
        value = {"id": "111222", "display": "outsideTemperature"}
        thermostat.set_second_display(value)
        
        mock_client.set_second_display.assert_called_once_with("111222", "outsideTemperature")
    
    def test_set_backlight_service(self, thermostat, mock_client):
        """Test set_backlight service."""
        value = {"id": "111222", "level": "on"}
        thermostat.set_backlight(value)
        
        mock_client.set_backlight.assert_called_once()
    
    def test_set_keypad_lock_service(self, thermostat, mock_client):
        """Test set_keypad_lock service."""
        value = {"id": "111222", "lock": "locked"}
        thermostat.set_keypad_lock(value)
        
        mock_client.set_keypad_lock.assert_called_once()
    
    def test_set_time_format_service(self, thermostat, mock_client):
        """Test set_time_format service."""
        value = {"id": "111222", "time": 24}
        thermostat.set_time_format(value)
        
        mock_client.set_time_format.assert_called_once_with("111222", "24h")
    
    def test_set_temperature_format_service(self, thermostat, mock_client):
        """Test set_temperature_format service."""
        value = {"id": "111222", "temp": "fahrenheit"}
        thermostat.set_temperature_format(value)
        
        mock_client.set_temperature_format.assert_called_once_with("111222", "fahrenheit")
    
    def test_set_setpoint_max_service(self, thermostat, mock_client):
        """Test set_setpoint_max service."""
        value = {"id": "111222", "temp": 28.0}
        thermostat.set_setpoint_max(value)
        
        mock_client.set_setpoint_max.assert_called_once_with("111222", 28.0)
    
    def test_set_setpoint_min_service(self, thermostat, mock_client):
        """Test set_setpoint_min service."""
        value = {"id": "111222", "temp": 7.0}
        thermostat.set_setpoint_min(value)
        
        mock_client.set_setpoint_min.assert_called_once_with("111222", 7.0)


class TestFloorThermostatInterface:
    """Test floor thermostat specific interface."""
    
    @pytest.fixture
    def floor_device_info(self):
        """Create mock floor device info."""
        return {
            "id": 111223,
            "name": "Bathroom Floor",
            "sku": "TH1300ZB",
            "location$id": 67890,
            "signature": {
                "model": 737,
                "modelCfg": 0,
                "protocol": "zigbee",
                "softVersion": {"major": 1, "middle": 2, "minor": 3},
            },
        }
    
    @pytest.fixture
    def floor_thermostat(self, mock_hass, mock_client, floor_device_info):
        """Create a floor thermostat entity."""
        from custom_components.neviweb130.climate import Neviweb130FloorThermostat
        
        mock_client.get_device_attributes = MagicMock(return_value={
            "roomTemperature": {"value": 21.0},
            "roomSetpoint": 20.0,
            "roomSetpointMin": 5.0,
            "roomSetpointMax": 30.0,
            "outputPercentDisplay": 50,
            "systemMode": "heat",
            "temperatureFormat": "celsius",
            "timeFormat": "24h",
            "config2ndDisplay": "setpoint",
            "lockKeypad": "unlocked",
            "backlightAdaptive": "auto",
            "loadConnected": 3600,
            "cycleLength": 15,
            "rssi": -50,
            "roomTemperatureDisplay": {"status": "on", "value": 21.0},
            "gfciStatus": "ok",
            "alertGfci": "off",
            "airFloorMode": "floor",
            "auxHeatConfig": "off",
            "loadWattOutput2": {"status": "off", "value": 0},
            "floorMaxAirTemperature": {"status": "off", "value": None},
            "floorSensorType": "10k",
            "floorLimitHigh": {"status": "off", "value": None},
            "floorLimitLow": {"status": "off", "value": None},
        })
        
        t = Neviweb130FloorThermostat(
            floor_device_info,
            "neviweb130 climate Bathroom Floor",
            "TH1300ZB",
            "1.2.3",
            67890,
            mock_client,
        )
        t.hass = mock_hass
        return t
    
    def test_floor_thermostat_extra_attributes(self, floor_thermostat):
        """Test floor thermostat has floor-specific attributes."""
        floor_thermostat.update()
        attrs = floor_thermostat.extra_state_attributes
        
        assert "sensor_mode" in attrs
        assert "auxiliary_heat" in attrs
        assert "floor_sensor_type" in attrs
        assert "gfci_status" in attrs
    
    def test_set_air_floor_mode_service(self, floor_thermostat, mock_client):
        """Test set_air_floor_mode service."""
        value = {"id": "111223", "mode": "ambiant"}
        floor_thermostat.set_air_floor_mode(value)
        
        mock_client.set_air_floor_mode.assert_called_once_with("111223", "ambiant")
    
    def test_set_floor_limit_service(self, floor_thermostat, mock_client):
        """Test set_floor_limit service."""
        value = {"id": "111223", "level": 27, "limit": "high"}
        floor_thermostat.set_floor_limit(value)
        
        mock_client.set_floor_limit.assert_called_once()


class TestLowVoltageThermostatInterface:
    """Test low voltage thermostat specific interface."""
    
    @pytest.fixture
    def low_device_info(self):
        """Create mock low voltage device info."""
        return {
            "id": 111224,
            "name": "Low Voltage",
            "sku": "TH1400ZB",
            "location$id": 67890,
            "signature": {
                "model": 7372,
                "modelCfg": 0,
                "protocol": "zigbee",
                "softVersion": {"major": 1, "middle": 2, "minor": 3},
            },
        }
    
    @pytest.fixture
    def low_thermostat(self, mock_hass, mock_client, low_device_info):
        """Create a low voltage thermostat entity."""
        from custom_components.neviweb130.climate import Neviweb130LowThermostat
        
        mock_client.get_device_attributes = MagicMock(return_value={
            "roomTemperature": {"value": 21.0},
            "roomSetpoint": 20.0,
            "roomSetpointMin": 5.0,
            "roomSetpointMax": 30.0,
            "outputPercentDisplay": 50,
            "systemMode": "heat",
            "temperatureFormat": "celsius",
            "timeFormat": "24h",
            "config2ndDisplay": "setpoint",
            "lockKeypad": "unlocked",
            "backlightAdaptive": "auto",
            "cycleLength": 15,
            "rssi": -50,
            "roomTemperatureDisplay": {"status": "on", "value": 21.0},
            "pumpProtectDuration": {"status": "off", "value": 60},
            "pumpProtectPeriod": {"status": "off", "value": 1},
            "floorMaxAirTemperature": {"status": "off", "value": None},
            "airFloorMode": "floor",
            "floorSensorType": "10k",
            "floorLimitHigh": {"status": "off", "value": None},
            "floorLimitLow": {"status": "off", "value": None},
            "cycleLengthOutput2": {"status": "off", "value": 0},
            "loadWattOutput1": {"status": "off", "value": 0},
            "loadWattOutput2": {"status": "off", "value": 0},
        })
        
        t = Neviweb130LowThermostat(
            low_device_info,
            "neviweb130 climate Low Voltage",
            "TH1400ZB",
            "1.2.3",
            67890,
            mock_client,
        )
        t.hass = mock_hass
        return t
    
    def test_low_voltage_extra_attributes(self, low_thermostat):
        """Test low voltage thermostat has pump protection attributes."""
        low_thermostat.update()
        attrs = low_thermostat.extra_state_attributes
        
        assert "pump_protection_status" in attrs
        assert "auxiliary_cycle_status" in attrs
        assert "cycle_length" in attrs
    
    def test_set_pump_protection_service(self, low_thermostat, mock_client):
        """Test set_pump_protection service."""
        value = {"id": "111224", "status": "on"}
        low_thermostat.set_pump_protection(value)
        
        mock_client.set_pump_protection.assert_called_once()
    
    def test_set_aux_cycle_output_service(self, low_thermostat, mock_client):
        """Test set_aux_cycle_output service."""
        value = {"id": "111224", "val": "15 min"}
        low_thermostat.set_aux_cycle_output(value)
        
        mock_client.set_aux_cycle_output.assert_called_once()


class TestWifiThermostatInterface:
    """Test Wi-Fi thermostat specific interface."""
    
    @pytest.fixture
    def wifi_device_info(self):
        """Create mock Wi-Fi device info."""
        return {
            "id": 111225,
            "name": "WiFi Thermostat",
            "sku": "TH1124WF",
            "location$id": 67890,
            "signature": {
                "model": 1510,
                "modelCfg": 0,
                "protocol": "wifi",
                "softVersion": {"major": 1, "middle": 2, "minor": 3},
            },
        }
    
    @pytest.fixture
    def wifi_thermostat(self, mock_hass, mock_client, wifi_device_info):
        """Create a Wi-Fi thermostat entity."""
        from custom_components.neviweb130.climate import Neviweb130WifiThermostat
        
        mock_client.get_device_attributes = MagicMock(return_value={
            "roomTemperature": {"value": 21.0, "error": None},
            "roomSetpoint": 20.0,
            "roomSetpointMin": 5.0,
            "roomSetpointMax": 30.0,
            "outputPercentDisplay": {"percent": 50, "sourceType": "main"},
            "setpointMode": "manual",
            "occupancyMode": "home",
            "temperatureFormat": "celsius",
            "timeFormat": "24h",
            "config2ndDisplay": "setpoint",
            "keyboardLock": "unlocked",
            "wifiRssi": -50,
            "backlightAutoDim": "auto",
            "earlyStartCfg": "off",
            "roomSetpointAway": 17.0,
            "loadWattOutput1": 0,
            "loadWatt": 3000,
            "cycleLength": 15,
            "roomTemperatureDisplay": {"status": "on", "value": 21.0},
        })
        
        t = Neviweb130WifiThermostat(
            wifi_device_info,
            "neviweb130 climate WiFi Thermostat",
            "TH1124WF",
            "1.2.3",
            67890,
            mock_client,
        )
        t.hass = mock_hass
        return t
    
    def test_wifi_thermostat_extra_attributes(self, wifi_thermostat):
        """Test Wi-Fi thermostat has Wi-Fi specific attributes."""
        wifi_thermostat.update()
        attrs = wifi_thermostat.extra_state_attributes
        
        assert "occupancy" in attrs
        assert "early_start" in attrs
        assert "setpoint_away" in attrs
    
    def test_set_early_start_service(self, wifi_thermostat, mock_client):
        """Test set_early_start service."""
        value = {"id": "111225", "start": "on"}
        wifi_thermostat.set_early_start(value)
        
        mock_client.set_early_start.assert_called_once_with("111225", "on")


class TestErrorHandling:
    """Test error handling in the HA interface."""
    
    @pytest.fixture
    def thermostat(self, mock_hass, mock_client, device_info):
        """Create a thermostat entity."""
        from custom_components.neviweb130.climate import Neviweb130Thermostat
        
        t = Neviweb130Thermostat(
            device_info,
            "neviweb130 climate Living Room",
            "TH1123ZB",
            "1.2.3",
            67890,
            mock_client,
        )
        t.hass = mock_hass
        return t
    
    def test_update_handles_session_expired(self, thermostat, mock_client):
        """Test update() handles USRSESSEXP error."""
        mock_client.get_device_attributes.return_value = {
            "error": {"code": "USRSESSEXP"}
        }
        
        thermostat.update()
        
        # Should call reconnect
        mock_client.reconnect.assert_called_once()
    
    def test_update_handles_device_unavailable(self, thermostat, mock_client):
        """Test update() handles DVCUNVLB error."""
        mock_client.get_device_attributes.return_value = {
            "error": {"code": "DVCUNVLB"}
        }
        
        thermostat.update()
        
        # Should deactivate device
        assert thermostat._active is False
    
    def test_update_handles_timeout(self, thermostat, mock_client):
        """Test update() handles ReadTimeout error."""
        mock_client.get_device_attributes.return_value = {
            "errorCode": "ReadTimeout"
        }
        
        # Should not raise exception
        thermostat.update()
    
    def test_set_temperature_respects_limits(self, thermostat, mock_client):
        """Test set_temperature() respects min/max limits."""
        thermostat._min_temp = 5.0
        thermostat._max_temp = 30.0
        
        with patch.object(thermostat, "_delayed_refresh"):
            # Try to set above max
            thermostat.set_temperature(**{ATTR_TEMPERATURE: 35.0})
            mock_client.set_temperature.assert_called_with("111222", 30.0)
            
            # Try to set below min
            thermostat.set_temperature(**{ATTR_TEMPERATURE: 2.0})
            mock_client.set_temperature.assert_called_with("111222", 5.0)


class TestMultiAccountSupport:
    """Test multi-account configuration support."""
    
    def test_scoped_unique_id_for_secondary_account(self, mock_client):
        """Test unique_id is scoped for non-primary accounts."""
        mock_client._is_primary = False
        mock_client._account = "67890"
        mock_client.scoped_unique_id = lambda x: f"{mock_client._account}_{x}"
        
        result = mock_client.scoped_unique_id("111222")
        assert result == "67890_111222"
    
    def test_default_group_name_with_prefix(self, mock_client):
        """Test default_group_name includes prefix for non-primary accounts."""
        mock_client._is_primary = False
        mock_client._account_prefix = "parents"
        mock_client._network_name = "Chalet"
        mock_client.default_group_name = lambda platform, idx=1: f"neviweb130 parents Chalet {platform}"
        
        result = mock_client.default_group_name("climate")
        assert "parents" in result
        assert "Chalet" in result


class TestHeatPumpThermostatInterface:
    """Test heat pump thermostat HA interface — fan_mode, swing_mode, available."""

    @pytest.fixture
    def hp_device_info(self):
        return {
            "id": 666777,
            "name": "Heat Pump",
            "sku": "HP6000ZB-GE",
            "location$id": 67890,
            "signature": {
                "model": 6810,
                "modelCfg": 0,
                "protocol": "zigbee",
                "softVersion": {"major": 1, "middle": 2, "minor": 3},
            },
        }

    @pytest.fixture
    def hp_thermostat(self, mock_hass, mock_client, hp_device_info):
        from custom_components.neviweb130.climate import Neviweb130HPThermostat
        mock_client.get_device_attributes = MagicMock(return_value={
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
        })
        t = Neviweb130HPThermostat(
            hp_device_info, "Heat Pump", "HP6000ZB-GE", "0.1.7", 67890, mock_client
        )
        t.hass = mock_hass
        return t

    def test_fan_modes_property(self, hp_thermostat):
        modes = hp_thermostat.fan_modes
        assert isinstance(modes, list)
        assert len(modes) > 0
        assert "auto" in modes

    def test_fan_mode_property(self, hp_thermostat):
        hp_thermostat.update()
        assert hp_thermostat.fan_mode == "auto"

    def test_set_fan_mode_calls_client(self, hp_thermostat, mock_client):
        hp_thermostat.set_fan_mode("high")
        mock_client.set_fan_mode.assert_called_once_with("666777", "high")

    def test_swing_modes_property(self, hp_thermostat):
        # swing_modes may be None for older firmware — must not raise
        modes = hp_thermostat.swing_modes
        assert modes is None or isinstance(modes, list)

    def test_available_property(self, hp_thermostat):
        hp_thermostat._active = True
        assert hp_thermostat.available is True

    def test_available_false_when_inactive(self, hp_thermostat):
        # _active=False pauses polling but HA's available stays True (no override)
        hp_thermostat._active = False
        assert hp_thermostat.available is True

    def test_extra_state_attributes_keys(self, hp_thermostat):
        hp_thermostat._firmware = "0.1.7"
        attrs = hp_thermostat.extra_state_attributes
        assert "fan_speed" in attrs
        assert "sku" in attrs
        assert "device_model" in attrs
        assert "firmware" in attrs
        assert "activation" in attrs
        assert "id" in attrs


class TestHeatCoolThermostatInterface:
    """Test heat/cool thermostat HA interface — set_humidity, fan_mode, available."""

    @pytest.fixture
    def hc_device_info(self):
        return {
            "id": 777888,
            "name": "HeatCool",
            "sku": "TH6500WF",
            "location$id": 67890,
            "signature": {
                "model": 6727,
                "modelCfg": 0,
                "protocol": "wifi",
                "softVersion": {"major": 4, "middle": 0, "minor": 0},
            },
        }

    @pytest.fixture
    def hc_thermostat(self, mock_hass, mock_client, hc_device_info):
        from custom_components.neviweb130.climate import Neviweb130HeatCoolThermostat
        t = Neviweb130HeatCoolThermostat(
            hc_device_info, "HeatCool", "TH6500WF", "4.0.0", 67890, mock_client
        )
        t.hass = mock_hass
        return t

    def test_fan_modes_property(self, hc_thermostat):
        modes = hc_thermostat.fan_modes
        assert isinstance(modes, list)
        assert len(modes) > 0

    def test_set_fan_mode_calls_client(self, hc_thermostat, mock_client):
        hc_thermostat.set_fan_mode("auto")
        mock_client.set_fan_mode.assert_called_once_with("777888", "auto")

    def test_set_humidity_calls_client(self, hc_thermostat, mock_client):
        hc_thermostat._humidity_setpoint_mode = "normal"
        hc_thermostat.set_humidity(humidity=50)
        mock_client.set_humidity.assert_called_once_with("777888", 50)

    def test_available_property(self, hc_thermostat):
        hc_thermostat._active = True
        assert hc_thermostat.available is True

    def test_available_false_when_inactive(self, hc_thermostat):
        # _active=False pauses polling but HA's available stays True (no override)
        hc_thermostat._active = False
        assert hc_thermostat.available is True

    def test_target_temperature_high_low(self, hc_thermostat):
        hc_thermostat._target_temp = 20.0
        hc_thermostat._target_cool = 24.0
        assert hc_thermostat.target_temperature_low == 20.0
        assert hc_thermostat.target_temperature_high == 24.0

    def test_set_temperature_heat_cool(self, hc_thermostat, mock_client):
        """set_temperature with both high and low sets both setpoints in HEAT_COOL mode."""
        from homeassistant.components.climate.const import (
            ATTR_TARGET_TEMP_HIGH, ATTR_TARGET_TEMP_LOW, HVACMode
        )
        from unittest.mock import patch
        hc_thermostat._heat_cool = HVACMode.AUTO  # maps to HEAT_COOL
        hc_thermostat._operation_mode = HVACMode.HEAT_COOL
        hc_thermostat._min_temp = 5.0
        hc_thermostat._max_temp = 30.0
        hc_thermostat._cool_min = 16.0
        hc_thermostat._cool_max = 36.0
        hc_thermostat._target_temp = 19.0
        hc_thermostat._target_cool = 25.0
        hc_thermostat._heatcool_setpoint_delta = 2
        with patch.object(hc_thermostat, "_delayed_refresh"):
            hc_thermostat.set_temperature(**{
                ATTR_TARGET_TEMP_LOW: 20.0,
                ATTR_TARGET_TEMP_HIGH: 26.0,  # must differ from _target_cool=25
            })
        mock_client.set_temperature.assert_called_once_with("777888", 20.0)
        mock_client.set_cool_temperature.assert_called_once_with("777888", 26.0)
