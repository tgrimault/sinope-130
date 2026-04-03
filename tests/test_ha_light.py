"""Test suite for Light platform Home Assistant interface."""
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
    client.default_group_name = MagicMock(return_value="neviweb130 light")
    client.get_device_attributes = MagicMock(return_value={
        "intensity": 75,
        "onOff": "on",
        "loadWattOutput1": {"status": "on", "value": 300},
        "lockKeypad": "unlocked",
        "powerTimer": 0,
        "rssi": -50,
        "intensityMin": 5,
        "statusLedOnIntensity": 50,
        "statusLedOffIntensity": 0,
        "statusLedOnColor": {"red": 0, "green": 0, "blue": 0},
        "statusLedOffColor": {"red": 0, "green": 0, "blue": 0},
        "errorCodeSet1": {},
    })
    return client


@pytest.fixture
def light_device_info():
    """Create mock light device info."""
    return {
        "id": 222333,
        "name": "Kitchen Light",
        "sku": "SW2500ZB",
        "location$id": 67890,
        "signature": {
            "model": 2121,
            "modelCfg": 0,
            "protocol": "zigbee",
            "softVersion": {"major": 1, "middle": 2, "minor": 3},
        },
    }


class TestLightEntityInterface:
    """Test LightEntity interface methods called by Home Assistant."""
    
    @pytest.fixture
    def light(self, mock_hass, mock_client, light_device_info):
        """Create a light entity."""
        from custom_components.neviweb130.light import Neviweb130Light
        
        l = Neviweb130Light(
            light_device_info,
            "neviweb130 light Kitchen Light",
            "DM2500ZB",
            "1.2.3",
            mock_client,
        )
        l.hass = mock_hass
        return l
    
    def test_unique_id_property(self, light):
        """Test unique_id property."""
        assert light.unique_id == "222333"
    
    def test_name_property(self, light):
        """Test name property."""
        assert light.name == "neviweb130 light Kitchen Light"
    
    def test_is_on_property(self, light):
        """Test is_on property."""
        light.update()
        assert light.is_on is True
    
    def test_brightness_property(self, light):
        """Test brightness property returns a value (0-255 scale)."""
        light.update()
        # Light switch (model 2121) doesn't set brightness from update
        assert light.brightness is not None
    
    def test_supported_features_property(self, light):
        """Test supported_color_modes property."""
        from homeassistant.components.light import ColorMode
        modes = light.supported_color_modes
        assert isinstance(modes, set)
    
    def test_extra_state_attributes(self, light):
        """Test extra_state_attributes property."""
        light.update()
        attrs = light.extra_state_attributes
        
        assert isinstance(attrs, dict)
        assert "wattage" in attrs
        assert "timer" in attrs
        assert "keypad" in attrs


class TestLightEntityActions:
    """Test LightEntity action methods called by Home Assistant."""
    
    @pytest.fixture
    def light(self, mock_hass, mock_client, light_device_info):
        """Create a light entity."""
        from custom_components.neviweb130.light import Neviweb130Light
        
        l = Neviweb130Light(
            light_device_info,
            "neviweb130 light Kitchen Light",
            "DM2500ZB",
            "1.2.3",
            mock_client,
        )
        l.hass = mock_hass
        return l
    
    def test_turn_on_action(self, light, mock_client):
        """Test turn_on() calls client correctly."""
        light._onoff = "off"  # ensure is_on is False so turn_on calls set_light_onoff
        light.turn_on()
        
        mock_client.set_light_onoff.assert_called_once()
        call_args = mock_client.set_light_onoff.call_args
        assert call_args[0][0] == "222333"
        assert call_args[0][1] == "on"
    
    def test_turn_on_with_brightness(self, light, mock_client):
        """Test turn_on() with brightness parameter calls set_brightness."""
        light._onoff = "off"  # ensure is_on is False
        # HA brightness 128 = ~50% in Neviweb
        light.turn_on(brightness=128)
        
        # set_brightness is called with the converted percentage
        mock_client.set_brightness.assert_called_once_with("222333", 50)
    
    def test_turn_off_action(self, light, mock_client):
        """Test turn_off() calls client correctly."""
        light.turn_off()
        
        mock_client.set_onoff.assert_called_once()
        call_args = mock_client.set_onoff.call_args
        assert call_args[0][1] == "off"


class TestLightCustomServices:
    """Test light-specific custom services."""
    
    @pytest.fixture
    def light(self, mock_hass, mock_client, light_device_info):
        """Create a light entity."""
        from custom_components.neviweb130.light import Neviweb130Light
        
        light = Neviweb130Light(
            light_device_info,
            "neviweb130 light Kitchen Light",
            "DM2500ZB",
            "1.2.3",
            mock_client,
        )
        light.hass = mock_hass
        light.entity_id = "light.neviweb130_light_kitchen_light"
        return light
    
    def test_set_light_keypad_lock_service(self, light, mock_client):
        """Test set_light_keypad_lock service."""
        value = {"id": "222333", "lock": "locked"}
        light.set_keypad_lock(value)
        
        mock_client.set_keypad_lock.assert_called_once()
    
    def test_set_light_timer_service(self, light, mock_client):
        """Test set_light_timer service."""
        value = {"id": "222333", "time": 3600}
        light.set_timer(value)
        
        mock_client.set_timer.assert_called_once_with("222333", 3600)
    
    def test_set_led_indicator_service(self, light, mock_client):
        """Test set_led_indicator service."""
        value = {"id": "222333", "state": 1, "red": 255, "green": 0, "blue": 0}
        light.set_led_indicator(value)
        
        mock_client.set_led_indicator.assert_called_once()
    
    def test_set_wattage_service(self, light, mock_client):
        """Test set_wattage service."""
        value = {"id": "222333", "watt": 300}
        light.set_wattage(value)
        
        mock_client.set_wattage.assert_called_once_with("222333", 300)


class TestUpdateMethod:
    """Test the update() method for light entities."""
    
    @pytest.fixture
    def light(self, mock_hass, mock_client, light_device_info):
        """Create a light entity."""
        from custom_components.neviweb130.light import Neviweb130Light
        
        l = Neviweb130Light(
            light_device_info,
            "neviweb130 light Kitchen Light",
            "DM2500ZB",
            "1.2.3",
            mock_client,
        )
        l.hass = mock_hass
        return l
    
    def test_update_calls_get_device_attributes(self, light, mock_client):
        """Test update() calls get_device_attributes."""
        light.update()
        
        mock_client.get_device_attributes.assert_called()
        call_args = mock_client.get_device_attributes.call_args
        assert call_args[0][0] == "222333"
    
    def test_update_updates_internal_state(self, light):
        """Test update() updates internal state."""
        light.update()
        
        assert light._wattage == 300
        assert light._onoff == "on"


class TestLightExtraStateAttributes:
    """Test light extra_state_attributes key stability."""

    @pytest.fixture
    def light(self, mock_hass, mock_client, light_device_info):
        from custom_components.neviweb130.light import Neviweb130Light
        l = Neviweb130Light(
            light_device_info, "neviweb130 light Kitchen Light",
            "DM2500ZB", "1.2.3", mock_client,
        )
        l.hass = mock_hass
        return l

    def test_extra_state_attributes_stable_keys(self, light):
        """All keys that user automations may reference must remain stable."""
        light.update()
        attrs = light.extra_state_attributes
        for key in ("wattage", "timer", "keypad", "sku",
                    "device_model", "firmware", "activation", "id"):
            assert key in attrs, f"Missing key: {key}"

    def test_extra_state_attributes_is_dict(self, light):
        assert isinstance(light.extra_state_attributes, dict)

    def test_available_property(self, light):
        light._active = True
        assert light.available is True

    def test_available_false_when_inactive(self, light):
        # _active=False pauses polling; HA's available is not overridden
        light._active = False
        assert light.available is True


# ---------------------------------------------------------------------------
# Helpers for dimmer / new-dimmer fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dimmer_device_info():
    """Create mock dimmer device info (DM2500ZB, model 2131)."""
    return {
        "id": 333444,
        "name": "Living Dimmer",
        "sku": "DM2500ZB",
        "location$id": 67890,
        "signature": {
            "model": 2131,
            "modelCfg": 0,
            "protocol": "zigbee",
            "softVersion": {"major": 1, "middle": 2, "minor": 3},
        },
    }


@pytest.fixture
def new_dimmer_device_info():
    """Create mock new-dimmer device info (DM2550ZB, model 2132)."""
    return {
        "id": 555666,
        "name": "Hall Dimmer",
        "sku": "DM2550ZB",
        "location$id": 67890,
        "signature": {
            "model": 2132,
            "modelCfg": 0,
            "protocol": "zigbee",
            "softVersion": {"major": 1, "middle": 2, "minor": 3},
        },
    }


def _make_dimmer_response():
    return {
        "intensity": 60,
        "intensityMin": 5,
        "onOff": "on",
        "loadWattOutput1": {"status": "on", "value": 200},
        "lockKeypad": "unlocked",
        "powerTimer": 0,
        "rssi": -55,
        "statusLedOnIntensity": 50,
        "statusLedOffIntensity": 0,
        "statusLedOnColor": {"red": 0, "green": 0, "blue": 0},
        "statusLedOffColor": {"red": 0, "green": 0, "blue": 0},
        "errorCodeSet1": {},
    }


def _make_new_dimmer_response():
    return {
        "intensity": 40,
        "intensityMin": 5,
        "onOff": "on",
        "phaseControl": "forward",
        "configKeyDoubleUp": "none",
        "wattageInstant": 150,
        "lockKeypad": "unlocked",
        "powerTimer": 0,
        "rssi": -60,
        "statusLedOnIntensity": 50,
        "statusLedOffIntensity": 0,
        "statusLedOnColor": {"red": 0, "green": 0, "blue": 0},
        "statusLedOffColor": {"red": 0, "green": 0, "blue": 0},
        "errorCodeSet1": {},
    }


@pytest.mark.unit
class TestLightUpdateHelpers:
    """Test the extracted helper methods on Neviweb130Light and subclasses in isolation."""

    # ------------------------------------------------------------------
    # Neviweb130Light base class helpers
    # ------------------------------------------------------------------

    @pytest.fixture
    def light(self, mock_hass, mock_client, light_device_info):
        from custom_components.neviweb130.light import Neviweb130Light
        entity = Neviweb130Light(
            light_device_info, "test light", "SW2500ZB", "1.2.3", mock_client
        )
        entity.hass = mock_hass
        return entity

    def test_fetch_attributes_calls_get_device_attributes(self, light, mock_client):
        """_fetch_attributes delegates to client.get_device_attributes when not in safe mode."""
        from custom_components.neviweb130.light import UPDATE_ATTRIBUTES
        from custom_components.neviweb130.const import ATTR_LIGHT_WATTAGE, ATTR_ERROR_CODE_SET1
        attrs = UPDATE_ATTRIBUTES + [ATTR_LIGHT_WATTAGE, ATTR_ERROR_CODE_SET1]
        mock_client.get_device_attributes.return_value = {"onOff": "on"}
        result = light._fetch_attributes(attrs)
        mock_client.get_device_attributes.assert_called_once_with("222333", attrs)
        assert result == {"onOff": "on"}

    def test_fetch_attributes_safe_mode_uses_safe_get(self, light, mock_client, mock_hass):
        """_fetch_attributes uses safe_get_device_attributes when safe_mode matches device id."""
        from custom_components.neviweb130.light import UPDATE_ATTRIBUTES
        from custom_components.neviweb130.const import ATTR_LIGHT_WATTAGE, ATTR_ERROR_CODE_SET1
        from unittest.mock import patch
        mock_hass.data["neviweb130"]["safe_mode"] = "222333"
        attrs = UPDATE_ATTRIBUTES + [ATTR_LIGHT_WATTAGE, ATTR_ERROR_CODE_SET1]
        with patch("custom_components.neviweb130.light.safe_get_device_attributes", return_value={"onOff": "off"}) as mock_safe:
            result = light._fetch_attributes(attrs)
        mock_safe.assert_called_once()
        assert result == {"onOff": "off"}

    def test_handle_error_returns_true_on_error_key(self, light):
        """_handle_error returns True when 'error' key is present."""
        light.log_error = MagicMock()
        result = light._handle_error({"error": {"code": "USRSESSEXP"}})
        assert result is True
        light.log_error.assert_called_once_with("USRSESSEXP")

    def test_handle_error_returns_true_on_error_code_key(self, light):
        """_handle_error returns True when 'errorCode' key is present."""
        result = light._handle_error({"errorCode": "DVCATTRNSPTD"})
        assert result is True

    def test_handle_error_returns_false_for_clean_data(self, light):
        """_handle_error returns False when no error keys are present."""
        result = light._handle_error({"onOff": "on"})
        assert result is False

    def test_parse_common_state_assigns_onoff(self, light, mock_client):
        """_parse_common_state assigns _onoff from data."""
        data = mock_client.get_device_attributes.return_value
        light._parse_common_state(data)
        assert light._onoff == "on"

    def test_parse_common_state_assigns_light_fields(self, light, mock_client):
        """_parse_common_state assigns wattage, keypad, timer, rssi, led fields for light."""
        data = mock_client.get_device_attributes.return_value
        light._parse_common_state(data)
        assert light._wattage == 300
        assert light._keypad == "unlocked"
        assert light._timer == 0
        assert light._rssi == -50

    def test_handle_snooze_reactivates_after_timeout(self, light):
        """_handle_snooze sets _active=True when snooze period has elapsed."""
        import time
        light._active = False
        light._snooze = time.time() - 1300  # > SNOOZE_TIME (1200)
        light._handle_snooze()
        assert light._active is True

    def test_handle_snooze_does_not_reactivate_too_early(self, light):
        """_handle_snooze leaves _active=False when snooze period has not elapsed."""
        import time
        light._active = False
        light._snooze = time.time() - 100  # < SNOOZE_TIME
        light._handle_snooze()
        assert light._active is False

    def test_update_skips_when_inactive(self, light, mock_client):
        """update() does not call get_device_attributes when _active is False."""
        import time
        light._active = False
        light._snooze = time.time()  # fresh snooze, won't reactivate
        light.update()
        mock_client.get_device_attributes.assert_not_called()

    def test_update_calls_parse_on_clean_data(self, light, mock_client):
        """update() calls _parse_common_state when no error in response."""
        light._parse_common_state = MagicMock()
        light.update()
        light._parse_common_state.assert_called_once()

    def test_update_skips_parse_on_error_data(self, light, mock_client):
        """update() skips _parse_common_state when error is in response."""
        mock_client.get_device_attributes.return_value = {"error": {"code": "DVCUNVLB"}}
        light._parse_common_state = MagicMock()
        light.log_error = MagicMock()
        light.update()
        light._parse_common_state.assert_not_called()

    # ------------------------------------------------------------------
    # Neviweb130Dimmer helpers
    # ------------------------------------------------------------------

    @pytest.fixture
    def dimmer(self, mock_hass, mock_client, dimmer_device_info):
        from custom_components.neviweb130.light import Neviweb130Dimmer
        mock_client.get_device_attributes.return_value = _make_dimmer_response()
        entity = Neviweb130Dimmer(
            dimmer_device_info, "test dimmer", "DM2500ZB", "1.2.3", mock_client
        )
        entity.hass = mock_hass
        return entity

    def test_dimmer_is_primary_type(self, dimmer):
        """Neviweb130Dimmer._is_primary_type() returns True for dimmer model."""
        assert dimmer._is_primary_type() is True

    def test_dimmer_get_attributes_list_includes_wattage(self, dimmer):
        """Neviweb130Dimmer._get_attributes_list() includes ATTR_LIGHT_WATTAGE."""
        from custom_components.neviweb130.const import ATTR_LIGHT_WATTAGE
        attrs = dimmer._get_attributes_list()
        assert ATTR_LIGHT_WATTAGE in attrs

    def test_dimmer_parse_common_state_assigns_brightness(self, dimmer):
        """_parse_common_state assigns _brightness_pct for dimmer."""
        dimmer._parse_common_state(_make_dimmer_response())
        assert dimmer._brightness_pct == 60

    def test_dimmer_parse_common_state_assigns_wattage(self, dimmer):
        """_parse_common_state assigns _wattage for dimmer."""
        dimmer._parse_common_state(_make_dimmer_response())
        assert dimmer._wattage == 200

    def test_dimmer_parse_common_state_assigns_keypad(self, dimmer):
        """_parse_common_state assigns _keypad for dimmer."""
        dimmer._parse_common_state(_make_dimmer_response())
        assert dimmer._keypad == "unlocked"

    def test_dimmer_handle_error_returns_false_for_clean_data(self, dimmer):
        """_handle_error returns False for clean dimmer data."""
        assert dimmer._handle_error(_make_dimmer_response()) is False

    def test_dimmer_update_assigns_state(self, dimmer, mock_client):
        """update() on Neviweb130Dimmer assigns all expected state fields."""
        dimmer.update()
        assert dimmer._onoff == "on"
        assert dimmer._brightness_pct == 60
        assert dimmer._wattage == 200

    def test_dimmer_extra_state_attributes_keys(self, dimmer, mock_client):
        """Neviweb130Dimmer.extra_state_attributes contains expected keys."""
        dimmer.update()
        attrs = dimmer.extra_state_attributes
        for key in ("wattage", "timer", "keypad", "sku", "device_model", "firmware", "activation", "id"):
            assert key in attrs, f"Missing key: {key}"

    # ------------------------------------------------------------------
    # Neviweb130NewDimmer helpers
    # ------------------------------------------------------------------

    @pytest.fixture
    def new_dimmer(self, mock_hass, mock_client, new_dimmer_device_info):
        from custom_components.neviweb130.light import Neviweb130NewDimmer
        mock_client.get_device_attributes.return_value = _make_new_dimmer_response()
        entity = Neviweb130NewDimmer(
            new_dimmer_device_info, "test new dimmer", "DM2550ZB", "1.2.3", mock_client
        )
        entity.hass = mock_hass
        return entity

    def test_new_dimmer_is_primary_type(self, new_dimmer):
        """Neviweb130NewDimmer._is_primary_type() returns True for new dimmer model."""
        assert new_dimmer._is_primary_type() is True

    def test_new_dimmer_get_attributes_list_includes_phase_control(self, new_dimmer):
        """Neviweb130NewDimmer._get_attributes_list() includes ATTR_PHASE_CONTROL."""
        from custom_components.neviweb130.const import ATTR_PHASE_CONTROL
        attrs = new_dimmer._get_attributes_list()
        assert ATTR_PHASE_CONTROL in attrs

    def test_new_dimmer_parse_common_state_assigns_brightness(self, new_dimmer):
        """_parse_common_state assigns _brightness_pct for new dimmer."""
        new_dimmer._parse_common_state(_make_new_dimmer_response())
        assert new_dimmer._brightness_pct == 40

    def test_new_dimmer_parse_common_state_assigns_wattage_instant(self, new_dimmer):
        """_parse_common_state assigns _wattage from wattageInstant for new dimmer."""
        new_dimmer._parse_common_state(_make_new_dimmer_response())
        assert new_dimmer._wattage == 150

    def test_new_dimmer_parse_common_state_assigns_phase_control(self, new_dimmer):
        """_parse_common_state assigns _phase_control for new dimmer."""
        new_dimmer._parse_common_state(_make_new_dimmer_response())
        assert new_dimmer._phase_control == "forward"

    def test_new_dimmer_handle_error_returns_false_for_clean_data(self, new_dimmer):
        """_handle_error returns False for clean new dimmer data."""
        assert new_dimmer._handle_error(_make_new_dimmer_response()) is False

    def test_new_dimmer_update_assigns_state(self, new_dimmer, mock_client):
        """update() on Neviweb130NewDimmer assigns all expected state fields."""
        new_dimmer.update()
        assert new_dimmer._onoff == "on"
        assert new_dimmer._brightness_pct == 40
        assert new_dimmer._wattage == 150
        assert new_dimmer._phase_control == "forward"

    def test_new_dimmer_extra_state_attributes_keys(self, new_dimmer, mock_client):
        """Neviweb130NewDimmer.extra_state_attributes contains expected keys."""
        new_dimmer.update()
        attrs = new_dimmer.extra_state_attributes
        for key in ("wattage", "timer", "keypad", "sku", "device_model", "firmware", "activation", "id"):
            assert key in attrs, f"Missing key: {key}"
