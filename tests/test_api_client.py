"""Test suite for Neviweb130Client API calls."""
import pytest
from unittest.mock import MagicMock, patch, Mock
from custom_components.neviweb130 import Neviweb130Client, PyNeviweb130Error


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    
    # Mock the store
    mock_store = MagicMock()
    mock_future = MagicMock()
    mock_future.result.return_value = None
    
    hass.data = {
        "neviweb130": {
            "request_store": mock_store,
            "request_data": {"date": "2024-01-01", "count": 0},
            "ready": False,
            "translation_cache": None
        }
    }
    hass.loop = MagicMock()
    
    # Mock asyncio.run_coroutine_threadsafe to return a mock future
    with patch('custom_components.neviweb130.helpers.asyncio.run_coroutine_threadsafe', return_value=mock_future):
        yield hass


@pytest.fixture
def mock_requests():
    """Mock requests library."""
    import requests as real_requests
    with patch("custom_components.neviweb130.requests") as mock:
        # Add the real exceptions module so exception handling works
        mock.exceptions = real_requests.exceptions
        yield mock


@pytest.fixture
def client(mock_hass, mock_requests):
    """Create a Neviweb130Client instance with mocked login."""
    # Mock login response
    login_response = MagicMock()
    login_response.status_code = 200
    login_response.json.return_value = {
        "session": "test_session_token",
        "account": {"id": 12345},
        "user": {"id": 1}
    }
    login_response.cookies = {}
    
    # Mock locations response
    locations_response = MagicMock()
    locations_response.json.return_value = [
        {"id": 67890, "name": "Home", "mode": "home", "postalCode": "H1A1A1"}
    ]
    locations_response.cookies = {}
    
    # Mock gateway data response
    gateway_response = MagicMock()
    gateway_response.json.return_value = []
    gateway_response.cookies = {}
    
    mock_requests.post.return_value = login_response
    # Use side_effect for the first two calls, then switch to return_value
    mock_requests.get.side_effect = [locations_response, gateway_response]
    
    client_instance = Neviweb130Client(
        mock_hass,
        "test@example.com",
        "password",
        "Home",
        None,
        None,
        False,
        "",
        timeout=30
    )
    
    # After client is created, reset side_effect and use return_value for subsequent calls
    default_response = MagicMock()
    default_response.json.return_value = {}
    default_response.cookies = {}
    mock_requests.get.side_effect = None
    mock_requests.get.return_value = default_response
    
    return client_instance


class TestAuthentication:
    """Test authentication endpoints."""
    
    def test_login_success(self, mock_hass, mock_requests):
        """Test successful login."""
        login_response = MagicMock()
        login_response.status_code = 200
        login_response.json.return_value = {
            "session": "test_token",
            "account": {"id": 12345},
            "user": {"id": 1}
        }
        login_response.cookies = {}
        
        # Mock locations response
        locations_response = MagicMock()
        locations_response.json.return_value = [
            {"id": 67890, "name": "Home", "mode": "home", "postalCode": "H1A1A1"}
        ]
        locations_response.cookies = {}
        
        # Mock gateway devices response
        gateway_response = MagicMock()
        gateway_response.json.return_value = []
        gateway_response.cookies = {}
        
        mock_requests.post.return_value = login_response
        mock_requests.get.side_effect = [locations_response, gateway_response]
        
        client = Neviweb130Client(
            mock_hass, "user@test.com", "pass", None, None, None, False, ""
        )
        
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        assert call_args[0][0] == "https://neviweb.com/api/login"
        assert call_args[1]["json"]["username"] == "user@test.com"
        assert call_args[1]["json"]["password"] == "pass"
        assert call_args[1]["json"]["interface"] == "neviweb"
        assert call_args[1]["json"]["stayConnected"] == 1
    
    def test_login_bad_credentials(self, mock_hass, mock_requests):
        """Test login with bad credentials."""
        login_response = MagicMock()
        login_response.status_code = 200
        login_response.json.return_value = {
            "error": {"code": "USRBADLOGIN"}
        }
        
        mock_requests.post.return_value = login_response
        
        with pytest.raises(Exception):
            Neviweb130Client(
                mock_hass, "bad@test.com", "wrong", None, None, None, False, ""
            )


class TestDeviceDiscovery:
    """Test device discovery endpoints."""
    
    def test_get_locations(self, client, mock_requests):
        """Test GET /api/locations."""
        # The client fixture already called get_locations during initialization
        # Just verify it was called with the right URL
        assert any(
            "locations?account$id=" in str(call[0][0])
            for call in mock_requests.get.call_args_list
        )
    
    def test_get_gateway_devices(self, client, mock_requests):
        """Test GET /api/devices?location$id=."""
        # The client fixture already called get_gateway_data during initialization
        # Just verify it was called with the right URL
        assert any(
            "devices?location$id=" in str(call[0][0])
            for call in mock_requests.get.call_args_list
        )


class TestDeviceAttributes:
    """Test device attribute endpoints."""
    
    def test_get_device_attributes(self, client, mock_requests):
        """Test GET /api/device/{id}/attribute."""
        response = MagicMock()
        response.json.return_value = {
            "roomTemperature": 21.5,
            "roomSetpoint": 20.0,
            "systemMode": "heat"
        }
        response.cookies = {}
        
        # Override the return value for this specific call
        mock_requests.get.return_value = response
        
        result = client.get_device_attributes("111222", ["roomTemperature", "roomSetpoint"])
        
        # Check that the call was made (it will be the 3rd call after locations and gateway)
        call_url = mock_requests.get.call_args[0][0]
        assert "/api/device/111222/attribute" in call_url
        assert "attributes=roomTemperature,roomSetpoint" in call_url
        assert result["roomTemperature"] == 21.5
    
    def test_set_device_attributes(self, client, mock_requests):
        """Test PUT /api/device/{id}/attribute."""
        response = MagicMock()
        response.json.return_value = {"roomSetpoint": 22.0}
        response.cookies = {}
        
        mock_requests.put.return_value = response
        
        client.set_device_attributes("111222", {"roomSetpoint": 22.0})
        
        mock_requests.put.assert_called_once()
        call_args = mock_requests.put.call_args
        assert "/api/device/111222/attribute" in call_args[0][0]
        assert call_args[1]["json"] == {"roomSetpoint": 22.0}


class TestDeviceControl:
    """Test device control methods."""
    
    def test_set_temperature(self, client, mock_requests):
        """Test setting temperature."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_temperature("111222", 21.5)
        
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"] == {"roomSetpoint": 21.5}
    
    def test_set_brightness(self, client, mock_requests):
        """Test setting brightness."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_brightness("111222", 75)
        
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"] == {"intensity": 75}
    
    def test_set_onoff(self, client, mock_requests):
        """Test setting on/off state."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_onoff("111222", "on")
        
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"] == {"onOff": "on"}


class TestEnergyStatistics:
    """Test energy statistics endpoints."""
    
    def test_get_hourly_stats(self, client, mock_requests):
        """Test GET /api/device/{id}/consumption/hourly."""
        response = MagicMock()
        response.json.return_value = {
            "history": [
                {"date": "2024-01-01T00:00:00.000Z", "period": 1500}
            ]
        }
        response.cookies = {}
        mock_requests.get.return_value = response
        
        result = client.get_device_hourly_stats("111222", False)
        
        call_url = mock_requests.get.call_args[0][0]
        assert "/api/device/111222/consumption/hourly" in call_url
        assert result is not None
        assert len(result) == 1
    
    def test_get_daily_stats(self, client, mock_requests):
        """Test GET /api/device/{id}/consumption/daily."""
        response = MagicMock()
        response.json.return_value = {
            "history": [
                {"date": "2024-01-01", "period": 35000}
            ]
        }
        response.cookies = {}
        mock_requests.get.return_value = response
        
        result = client.get_device_daily_stats("111222", False)
        
        call_url = mock_requests.get.call_args[0][0]
        assert "/api/device/111222/consumption/daily" in call_url
    
    def test_get_monthly_stats(self, client, mock_requests):
        """Test GET /api/device/{id}/consumption/monthly."""
        response = MagicMock()
        response.json.return_value = {
            "history": [
                {"date": "2024-01", "period": 1000000}
            ]
        }
        response.cookies = {}
        mock_requests.get.return_value = response
        
        result = client.get_device_monthly_stats("111222", False)
        
        call_url = mock_requests.get.call_args[0][0]
        assert "/api/device/111222/consumption/monthly" in call_url


class TestLocationStatus:
    """Test location status endpoints."""
    
    def test_get_neviweb_status(self, client, mock_requests):
        """Test GET /api/location/{id}/notifications."""
        response = MagicMock()
        response.json.return_value = {"occupancyMode": "home"}
        response.cookies = {}
        mock_requests.get.return_value = response
        
        result = client.get_neviweb_status(67890)
        
        call_url = mock_requests.get.call_args[0][0]
        assert "/api/location/67890/notifications" in call_url
        assert result["occupancyMode"] == "home"
    
    def test_post_neviweb_status(self, client, mock_requests):
        """Test POST /api/location/{id}/mode."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.post.return_value = response
        
        client.post_neviweb_status(67890, "away")
        
        call_args = mock_requests.post.call_args
        assert "/api/location/67890/mode" in call_args[0][0]
        assert call_args[1]["json"] == {"mode": "away"}


class TestWeather:
    """Test weather endpoint."""
    
    def test_get_weather(self, client, mock_requests):
        """Test GET /api/weather?code=."""
        response = MagicMock()
        response.json.return_value = {"temperature": -5.0, "icon": 3}
        response.cookies = {}
        mock_requests.get.return_value = response
        
        result = client.get_weather()
        
        call_url = mock_requests.get.call_args[0][0]
        assert "/api/weather?code=" in call_url
        assert result["temperature"] == -5.0


class TestDeviceStatus:
    """Test device status endpoints."""
    
    def test_get_device_status(self, client, mock_requests):
        """Test GET /api/device/{id}/status."""
        response = MagicMock()
        response.json.return_value = {"online": True}
        response.cookies = {}
        mock_requests.get.return_value = response
        
        result = client.get_device_status("111222")
        
        call_url = mock_requests.get.call_args[0][0]
        assert "/api/device/111222/status" in call_url
    
    def test_get_device_alert(self, client, mock_requests):
        """Test GET /api/device/{id}/alert."""
        response = MagicMock()
        response.json.return_value = {
            "alertLowBatt": "off",
            "alertLowTemp": "off",
            "alertWaterLeak": "off"
        }
        response.cookies = {}
        mock_requests.get.return_value = response
        
        result = client.get_device_alert("111222")
        
        call_url = mock_requests.get.call_args[0][0]
        assert "/api/device/111222/alert" in call_url
    
    def test_get_device_sensor_error(self, client, mock_requests):
        """Test GET /api/device/{id}/attribute?attributes=errorCodeSet1."""
        response = MagicMock()
        response.json.return_value = {"errorCodeSet1": {"raw": 0}}
        response.cookies = {}
        mock_requests.get.return_value = response
        
        result = client.get_device_sensor_error("111222")
        
        call_url = mock_requests.get.call_args[0][0]
        assert "/api/device/111222/attribute" in call_url
        assert "errorCodeSet1" in call_url


class TestThermostatControl:
    """Test thermostat-specific control methods."""
    
    def test_set_setpoint_mode_wifi(self, client, mock_requests):
        """Test setting thermostat mode for Wi-Fi devices."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_setpoint_mode("111222", "manual", True, False)
        
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"] == {"setpointMode": "manual"}
    
    def test_set_setpoint_mode_zigbee(self, client, mock_requests):
        """Test setting thermostat mode for Zigbee devices."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_setpoint_mode("111222", "heat", False, False)
        
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"] == {"systemMode": "heat"}
    
    def test_set_occupancy_mode(self, client, mock_requests):
        """Test setting occupancy mode."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_occupancy_mode("111222", "away", True)
        
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"] == {"occupancyMode": "away"}
    
    def test_set_cool_temperature(self, client, mock_requests):
        """Test setting cooling temperature."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_cool_temperature("111222", 24.0)
        
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"] == {"coolSetpoint": 24.0}


class TestAdvancedThermostatSettings:
    """Test advanced thermostat configuration methods."""
    
    def test_set_backlight(self, client, mock_requests):
        """Test setting backlight."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_backlight("111222", "auto", False)
        
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"] == {"backlightAdaptive": "auto"}
    
    def test_set_keypad_lock(self, client, mock_requests):
        """Test setting keypad lock."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_keypad_lock("111222", "locked", False)
        
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"] == {"lockKeypad": "locked"}
    
    def test_set_time_format(self, client, mock_requests):
        """Test setting time format."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_time_format("111222", 24)
        
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"] == {"timeFormat": 24}
    
    def test_set_temperature_format(self, client, mock_requests):
        """Test setting temperature format."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_temperature_format("111222", "celsius")
        
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"] == {"temperatureFormat": "celsius"}
    
    def test_set_setpoint_min_max(self, client, mock_requests):
        """Test setting setpoint limits."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_setpoint_min("111222", 5.0)
        assert mock_requests.put.call_args[1]["json"] == {"roomSetpointMin": 5.0}
        
        client.set_setpoint_max("111222", 30.0)
        assert mock_requests.put.call_args[1]["json"] == {"roomSetpointMax": 30.0}


class TestValveControl:
    """Test valve-specific control methods."""
    
    def test_set_valve_onoff(self, client, mock_requests):
        """Test setting valve on/off."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_valve_onoff("111222", "open")
        
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"] == {"motorTargetPosition": "open"}
    
    def test_set_valve_alert(self, client, mock_requests):
        """Test setting valve battery alert."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_valve_alert("111222", "on")
        
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"] == {"alertLowBatt": "on"}
    
    def test_set_flow_meter_model(self, client, mock_requests):
        """Test setting flow meter model."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_flow_meter_model("111222", "FS4220")
        
        call_args = mock_requests.put.call_args
        assert "flowMeterMeasurementConfig" in call_args[1]["json"]
        assert call_args[1]["json"]["flowMeterEnabled"] is True


class TestLightControl:
    """Test light-specific control methods."""
    
    def test_set_light_onoff(self, client, mock_requests):
        """Test setting light on/off with brightness."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_light_onoff("111222", "on", 80)
        
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"] == {"onOff": "on", "intensity": 80}
    
    def test_set_led_indicator(self, client, mock_requests):
        """Test setting LED indicator color."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_led_indicator("111222", 1, 255, 0, 0)
        
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"]["statusLedOnColor"] == {"red": 255, "green": 0, "blue": 0}
    
    def test_set_wattage(self, client, mock_requests):
        """Test setting wattage."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response
        
        client.set_wattage("111222", 1500)
        
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"] == {"loadWattOutput1": {"status": "on", "value": 1500}}


class TestErrorHandling:
    """Test error handling."""
    
    def test_session_expired(self, mock_hass):
        """Test handling of session expiration."""
        with patch('custom_components.neviweb130.requests') as mock_requests:
            # Setup login
            login_response = MagicMock()
            login_response.status_code = 200
            login_response.json.return_value = {
                "session": "test_token",
                "account": {"id": 12345},
                "user": {"id": 1}
            }
            login_response.cookies = {}
            
            locations_response = MagicMock()
            locations_response.json.return_value = [
                {"id": 67890, "name": "Home", "mode": "home", "postalCode": "H1A1A1"}
            ]
            locations_response.cookies = {}
            
            gateway_response = MagicMock()
            gateway_response.json.return_value = []
            gateway_response.cookies = {}
            
            # Setup error response
            error_response = MagicMock()
            error_response.json.return_value = {
                "error": {"code": "USRSESSEXP"}
            }
            error_response.cookies = {}
            
            mock_requests.post.return_value = login_response
            mock_requests.get.side_effect = [
                locations_response,
                gateway_response,
                error_response  # This will be returned for get_device_attributes
            ]
            
            client = Neviweb130Client(
                mock_hass, "test@test.com", "pass", None, None, None, False, ""
            )
            
            result = client.get_device_attributes("111222", ["roomTemperature"])
            
            assert "error" in result
            assert result["error"]["code"] == "USRSESSEXP"
    
    def test_read_timeout(self, mock_hass):
        """Test handling of read timeout."""
        import requests as real_requests
        
        with patch('custom_components.neviweb130.requests') as mock_requests:
            # Setup login
            login_response = MagicMock()
            login_response.status_code = 200
            login_response.json.return_value = {
                "session": "test_token",
                "account": {"id": 12345},
                "user": {"id": 1}
            }
            login_response.cookies = {}
            
            locations_response = MagicMock()
            locations_response.json.return_value = [
                {"id": 67890, "name": "Home", "mode": "home", "postalCode": "H1A1A1"}
            ]
            locations_response.cookies = {}
            
            gateway_response = MagicMock()
            gateway_response.json.return_value = []
            gateway_response.cookies = {}
            
            mock_requests.post.return_value = login_response
            mock_requests.get.side_effect = [
                locations_response,
                gateway_response,
                real_requests.exceptions.ReadTimeout()  # Raise timeout
            ]
            mock_requests.exceptions = real_requests.exceptions
            
            client = Neviweb130Client(
                mock_hass, "test@test.com", "pass", None, None, None, False, ""
            )
            
            result = client.get_device_attributes("111222", ["roomTemperature"])
            
            assert result["errorCode"] == "ReadTimeout"


class TestDoGet:
    """Test _do_get private HTTP helper."""

    @pytest.mark.api
    def test_do_get_returns_json_on_success(self, client, mock_requests):
        """_do_get returns parsed JSON from a successful GET response."""
        response = MagicMock()
        response.json.return_value = {"key": "value"}
        response.cookies = {}
        mock_requests.get.return_value = response
        mock_requests.get.reset_mock()

        result = client._do_get("https://neviweb.com/api/test")

        assert result == {"key": "value"}
        mock_requests.get.assert_called_once()
        call_kwargs = mock_requests.get.call_args[1]
        assert call_kwargs["headers"] == client._headers
        assert call_kwargs["timeout"] == client._timeout

    @pytest.mark.api
    def test_do_get_returns_error_dict_on_read_timeout(self, client, mock_requests):
        """_do_get returns {'errorCode': 'ReadTimeout'} on ReadTimeout."""
        import requests as real_requests

        mock_requests.exceptions = real_requests.exceptions
        mock_requests.get.side_effect = real_requests.exceptions.ReadTimeout()

        result = client._do_get("https://neviweb.com/api/test")

        assert result == {"errorCode": "ReadTimeout"}

    @pytest.mark.api
    def test_do_get_raises_on_os_error(self, client, mock_requests):
        """_do_get raises PyNeviweb130Error on OSError."""
        mock_requests.get.side_effect = OSError("network down")

        with pytest.raises(PyNeviweb130Error):
            client._do_get("https://neviweb.com/api/test")

    @pytest.mark.api
    def test_do_get_updates_cookies(self, client, mock_requests):
        """_do_get updates session cookies from the response."""
        response = MagicMock()
        response.json.return_value = {}
        new_cookies = MagicMock()
        response.cookies = new_cookies
        mock_requests.get.return_value = response

        # Force cookies to be None so the assignment branch is taken
        client._cookies = None
        client._do_get("https://neviweb.com/api/test")

        assert client._cookies is new_cookies

    @pytest.mark.api
    def test_do_get_passes_extra_kwargs(self, client, mock_requests):
        """_do_get forwards extra kwargs to requests.get."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.get.return_value = response

        client._do_get("https://neviweb.com/api/test", verify=False)

        call_kwargs = mock_requests.get.call_args[1]
        assert call_kwargs.get("verify") is False


class TestDoPut:
    """Test _do_put private HTTP helper."""

    @pytest.mark.api
    def test_do_put_returns_json_on_success(self, client, mock_requests):
        """_do_put returns parsed JSON from a successful PUT response."""
        response = MagicMock()
        response.json.return_value = {"updated": True}
        response.cookies = {}
        mock_requests.put.return_value = response

        result = client._do_put("https://neviweb.com/api/device/123/attribute", {"roomSetpoint": 21.0})

        assert result == {"updated": True}
        mock_requests.put.assert_called_once()
        call_kwargs = mock_requests.put.call_args[1]
        assert call_kwargs["json"] == {"roomSetpoint": 21.0}
        assert call_kwargs["headers"] == client._headers
        assert call_kwargs["timeout"] == client._timeout

    @pytest.mark.api
    def test_do_put_raises_on_os_error(self, client, mock_requests):
        """_do_put raises PyNeviweb130Error on OSError."""
        mock_requests.put.side_effect = OSError("connection refused")

        with pytest.raises(PyNeviweb130Error):
            client._do_put("https://neviweb.com/api/device/123/attribute", {})

    @pytest.mark.api
    def test_do_put_updates_cookies(self, client, mock_requests):
        """_do_put updates session cookies from the response."""
        response = MagicMock()
        response.json.return_value = {}
        new_cookies = MagicMock()
        response.cookies = new_cookies
        mock_requests.put.return_value = response

        client._cookies = None
        client._do_put("https://neviweb.com/api/device/123/attribute", {"onOff": "on"})

        assert client._cookies is new_cookies

    @pytest.mark.api
    def test_do_put_passes_extra_kwargs(self, client, mock_requests):
        """_do_put forwards extra kwargs to requests.put."""
        response = MagicMock()
        response.json.return_value = {}
        response.cookies = {}
        mock_requests.put.return_value = response

        client._do_put("https://neviweb.com/api/device/123/attribute", {}, verify=False)

        call_kwargs = mock_requests.put.call_args[1]
        assert call_kwargs.get("verify") is False


class TestHandleResponseError:
    """Test _handle_response_error centralised error checking."""

    @pytest.mark.unit
    def test_no_error_key_does_nothing(self, client):
        """_handle_response_error is a no-op when 'error' is absent."""
        # Should not raise
        client._handle_response_error({"roomTemperature": 21.5})

    @pytest.mark.unit
    def test_usrsessexp_logs_error(self, client):
        """_handle_response_error logs an error on USRSESSEXP."""
        import logging

        with patch("custom_components.neviweb130._LOGGER") as mock_logger:
            client._handle_response_error({"error": {"code": "USRSESSEXP"}})
            mock_logger.error.assert_called_once()

    @pytest.mark.unit
    def test_other_error_codes_do_not_log(self, client):
        """_handle_response_error does not log for non-session-expiry codes."""
        with patch("custom_components.neviweb130._LOGGER") as mock_logger:
            client._handle_response_error({"error": {"code": "DVCUNVLB"}})
            mock_logger.error.assert_not_called()

    @pytest.mark.unit
    def test_empty_error_dict_does_not_raise(self, client):
        """_handle_response_error handles a malformed error dict gracefully."""
        # Should not raise even if 'code' key is missing
        client._handle_response_error({"error": {}})

    @pytest.mark.unit
    def test_accdayreqmax_does_not_log_error(self, client):
        """_handle_response_error does not log for ACCDAYREQMAX (handled elsewhere)."""
        with patch("custom_components.neviweb130._LOGGER") as mock_logger:
            client._handle_response_error({"error": {"code": "ACCDAYREQMAX"}})
            mock_logger.error.assert_not_called()
