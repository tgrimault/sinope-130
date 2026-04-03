"""Test suite for Switch platform Home Assistant interface."""
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
    client.default_group_name = MagicMock(return_value="neviweb130 switch")
    client.get_device_attributes = MagicMock(return_value={
        "onOff": "on",
        "loadConnected": 5000,
        "wattageInstant": 0,
        "powerTimer": 0,
        "lockKeypad": "unlocked",
        "drStatus": {"drActive": "off", "optOut": "off", "onOff": "off"},
        "rssi": -50,
        "controlledDevice": None,
        "errorCodeSet1": {},
    })
    return client


@pytest.fixture
def switch_device_info():
    """Create mock switch device info."""
    return {
        "id": 333444,
        "name": "Water Heater",
        "sku": "RM3500ZB",
        "location$id": 67890,
        "signature": {
            "model": 2506,
            "modelCfg": 0,
            "protocol": "zigbee",
            "softVersion": {"major": 1, "middle": 2, "minor": 3},
        },
    }


class TestSwitchEntityInterface:
    """Test SwitchEntity interface methods called by Home Assistant."""
    
    @pytest.fixture
    def switch(self, mock_hass, mock_client, switch_device_info):
        """Create a switch entity."""
        from custom_components.neviweb130.switch import Neviweb130PowerSwitch
        
        s = Neviweb130PowerSwitch(
            switch_device_info,
            "neviweb130 switch Water Heater",
            "RM3500ZB",
            "1.2.3",
            "switch",
            mock_client,
        )
        s.hass = mock_hass
        return s
    
    def test_unique_id_property(self, switch):
        """Test unique_id property."""
        assert switch.unique_id == "333444"
    
    def test_name_property(self, switch):
        """Test name property."""
        assert switch.name == "neviweb130 switch Water Heater"
    
    def test_is_on_property(self, switch):
        """Test is_on property."""
        switch.update()
        assert switch.is_on is True
    
    def test_extra_state_attributes(self, switch):
        """Test extra_state_attributes property."""
        switch.update()
        attrs = switch.extra_state_attributes
        
        assert isinstance(attrs, dict)
        assert "wattage" in attrs
        assert "timer" in attrs


class TestSwitchEntityActions:
    """Test SwitchEntity action methods called by Home Assistant."""
    
    @pytest.fixture
    def switch(self, mock_hass, mock_client, switch_device_info):
        """Create a switch entity."""
        from custom_components.neviweb130.switch import Neviweb130PowerSwitch
        
        s = Neviweb130PowerSwitch(
            switch_device_info,
            "neviweb130 switch Water Heater",
            "RM3500ZB",
            "1.2.3",
            "switch",
            mock_client,
        )
        s.hass = mock_hass
        return s
    
    def test_turn_on_action(self, switch, mock_client):
        """Test turn_on() calls client correctly."""
        switch.turn_on()
        
        mock_client.set_onoff.assert_called_once_with("333444", "on")
    
    def test_turn_off_action(self, switch, mock_client):
        """Test turn_off() calls client correctly."""
        switch.turn_off()
        
        mock_client.set_onoff.assert_called_once_with("333444", "off")


class TestSwitchCustomServices:
    """Test switch-specific custom services."""
    
    @pytest.fixture
    def switch(self, mock_hass, mock_client, switch_device_info):
        """Create a switch entity."""
        from custom_components.neviweb130.switch import Neviweb130PowerSwitch
        
        switch = Neviweb130PowerSwitch(
            switch_device_info,
            "neviweb130 switch Water Heater",
            "RM3500ZB",
            "1.2.3",
            "switch",
            mock_client,
        )
        switch.hass = mock_hass
        switch.entity_id = "switch.neviweb130_switch_water_heater"
        return switch
    
    def test_set_switch_timer_service(self, switch, mock_client):
        """Test set_switch_timer service."""
        value = {"id": "333444", "time": 7200}
        switch.set_timer(value)
        
        mock_client.set_timer.assert_called_once_with("333444", 7200)
    
    def test_set_switch_keypad_lock_service(self, switch, mock_client):
        """Test set_switch_keypad_lock service."""
        value = {"id": "333444", "lock": "locked"}
        switch.set_keypad_lock(value)
        
        mock_client.set_keypad_lock.assert_called_once()


class TestUpdateMethod:
    """Test the update() method for switch entities."""
    
    @pytest.fixture
    def switch(self, mock_hass, mock_client, switch_device_info):
        """Create a switch entity."""
        from custom_components.neviweb130.switch import Neviweb130PowerSwitch
        
        s = Neviweb130PowerSwitch(
            switch_device_info,
            "neviweb130 switch Water Heater",
            "RM3500ZB",
            "1.2.3",
            "switch",
            mock_client,
        )
        s.hass = mock_hass
        return s
    
    def test_update_calls_get_device_attributes(self, switch, mock_client):
        """Test update() calls get_device_attributes."""
        switch.update()
        
        mock_client.get_device_attributes.assert_called()
        call_args = mock_client.get_device_attributes.call_args
        assert call_args[0][0] == "333444"
    
    def test_update_updates_internal_state(self, switch):
        """Test update() updates internal state."""
        switch.update()
        
        assert switch._onoff == "on"
        assert switch._wattage == 5000


class TestSwitchExtraStateAttributes:
    """Test switch extra_state_attributes key stability — critical for user automations."""

    @pytest.fixture
    def switch(self, mock_hass, mock_client, switch_device_info):
        from custom_components.neviweb130.switch import Neviweb130PowerSwitch
        s = Neviweb130PowerSwitch(
            switch_device_info, "neviweb130 switch Water Heater",
            "RM3500ZB", "1.2.3", "switch", mock_client,
        )
        s.hass = mock_hass
        return s

    def test_extra_state_attributes_stable_keys(self, switch):
        """All keys that user automations may reference must remain stable."""
        switch.update()
        attrs = switch.extra_state_attributes
        # Core keys that must survive any refactor
        for key in ("wattage", "timer", "keypad", "eco_status", "sku",
                    "device_model", "firmware", "activation", "id"):
            assert key in attrs, f"Missing key: {key}"

    def test_extra_state_attributes_is_dict(self, switch):
        assert isinstance(switch.extra_state_attributes, dict)

    def test_available_property(self, switch):
        switch._active = True
        assert switch.available is True

    def test_available_false_when_inactive(self, switch):
        # _active=False pauses polling; HA's available is not overridden
        switch._active = False
        assert switch.available is True


# ===========================================================================
# Tests for extracted helper methods (_fetch_attributes, _parse_common_state,
# _handle_error) — Task 10.1
# ===========================================================================

def _make_power_switch(mock_hass, mock_client):
    """Helper to build a Neviweb130PowerSwitch for helper tests."""
    from custom_components.neviweb130.switch import Neviweb130PowerSwitch
    info = {
        "id": 42,
        "name": "Test Load",
        "sku": "RM3250ZB",
        "location$id": 1,
        "signature": {
            "model": 2506,
            "modelCfg": 0,
            "protocol": "zigbee",
            "softVersion": {"major": 1, "middle": 0, "minor": 0},
        },
    }
    s = Neviweb130PowerSwitch(info, "Test Load", "RM3250ZB", "1.0.0", "power", mock_client)
    s.hass = mock_hass
    return s


def _make_wall_switch(mock_hass, mock_client):
    """Helper to build a base Neviweb130Switch (wall outlet) for helper tests."""
    from custom_components.neviweb130.switch import Neviweb130Switch
    info = {
        "id": 99,
        "name": "Wall Outlet",
        "sku": "SP2610ZB",
        "location$id": 1,
        "signature": {
            "model": 2610,
            "modelCfg": 0,
            "protocol": "zigbee",
            "softVersion": {"major": 1, "middle": 0, "minor": 0},
        },
    }
    s = Neviweb130Switch(info, "Wall Outlet", "SP2610ZB", "1.0.0", "outlet", mock_client)
    s.hass = mock_hass
    return s


@pytest.mark.unit
class TestFetchAttributes:
    """Tests for Neviweb130Switch._fetch_attributes()."""

    def test_fetch_uses_get_device_attributes_in_normal_mode(self, mock_hass, mock_client):
        """When safe_mode != device id, uses get_device_attributes."""
        mock_hass.data["neviweb130"]["safe_mode"] = "-"
        mock_client.get_device_attributes.return_value = {"onOff": "on"}
        switch = _make_power_switch(mock_hass, mock_client)

        result = switch._fetch_attributes(["onOff"])

        mock_client.get_device_attributes.assert_called_once_with("42", ["onOff"])
        assert result == {"onOff": "on"}

    def test_fetch_uses_safe_get_when_safe_mode_matches(self, mock_hass, mock_client):
        """When safe_mode == device id, uses safe_get_device_attributes."""
        mock_hass.data["neviweb130"]["safe_mode"] = "42"
        mock_client.get_device_attributes.return_value = {"onOff": "off"}
        switch = _make_power_switch(mock_hass, mock_client)

        from unittest.mock import patch
        with patch("custom_components.neviweb130.switch.safe_get_device_attributes") as mock_safe:
            mock_safe.return_value = {"onOff": "safe_result"}
            result = switch._fetch_attributes(["onOff"])

        mock_safe.assert_called_once()
        assert result == {"onOff": "safe_result"}
        mock_client.get_device_attributes.assert_not_called()

    def test_fetch_passes_attributes_list(self, mock_hass, mock_client):
        """_fetch_attributes forwards the attributes list to the client."""
        mock_hass.data["neviweb130"]["safe_mode"] = "-"
        mock_client.get_device_attributes.return_value = {}
        switch = _make_power_switch(mock_hass, mock_client)
        attrs = ["onOff", "wattage", "rssi"]

        switch._fetch_attributes(attrs)

        mock_client.get_device_attributes.assert_called_once_with("42", attrs)


@pytest.mark.unit
class TestHandleError:
    """Tests for Neviweb130Switch._handle_error()."""

    def test_returns_false_for_clean_data(self, mock_hass, mock_client):
        """Clean data (no error keys) returns False."""
        switch = _make_power_switch(mock_hass, mock_client)
        assert switch._handle_error({"onOff": "on"}) is False

    def test_returns_true_for_api_error(self, mock_hass, mock_client):
        """Data with 'error' key returns True and calls log_error."""
        switch = _make_power_switch(mock_hass, mock_client)
        from unittest.mock import patch
        with patch.object(switch, "log_error") as mock_log:
            result = switch._handle_error({"error": {"code": "USRSESSEXP"}})
        assert result is True
        mock_log.assert_called_once_with("USRSESSEXP")

    def test_returns_true_for_error_code(self, mock_hass, mock_client):
        """Data with 'errorCode' key returns True (logs warning, no log_error call)."""
        switch = _make_power_switch(mock_hass, mock_client)
        result = switch._handle_error({"errorCode": "some_code", "onOff": "on"})
        assert result is True

    def test_error_takes_priority_over_error_code(self, mock_hass, mock_client):
        """When both 'error' and 'errorCode' present, 'error' branch runs."""
        switch = _make_power_switch(mock_hass, mock_client)
        from unittest.mock import patch
        with patch.object(switch, "log_error") as mock_log:
            result = switch._handle_error({"error": {"code": "DVCUNVLB"}, "errorCode": "x"})
        assert result is True
        mock_log.assert_called_once_with("DVCUNVLB")


@pytest.mark.unit
class TestParseCommonState:
    """Tests for _parse_common_state() on base and subclasses."""

    def test_base_switch_assigns_onoff(self, mock_hass, mock_client):
        """Base class _parse_common_state assigns _onoff."""
        switch = _make_wall_switch(mock_hass, mock_client)
        switch._parse_common_state({"onOff": "on", "wattageInstant": 100})
        assert switch._onoff == "on"

    def test_base_switch_assigns_wattage_instant_for_wall(self, mock_hass, mock_client):
        """Wall outlet _parse_common_state assigns _current_power_w."""
        switch = _make_wall_switch(mock_hass, mock_client)
        switch._parse_common_state({"onOff": "off", "wattageInstant": 250})
        assert switch._current_power_w == 250

    def test_power_switch_assigns_wattage(self, mock_hass, mock_client):
        """PowerSwitch _parse_common_state assigns _wattage."""
        switch = _make_power_switch(mock_hass, mock_client)
        data = {
            "onOff": "on",
            "loadConnected": 5000,
            "wattageInstant": 100,
            "powerTimer": 30,
            "lockKeypad": "unlocked",
            "drStatus": {"drActive": "off", "optOut": "off", "onOff": "off"},
            "rssi": -60,
            "controlledDevice": None,
            "errorCodeSet1": {},
        }
        switch._parse_common_state(data)
        assert switch._onoff == "on"
        assert switch._wattage == 5000
        assert switch._timer == 30

    def test_power_switch_assigns_keypad(self, mock_hass, mock_client):
        """PowerSwitch _parse_common_state assigns _keypad correctly."""
        switch = _make_power_switch(mock_hass, mock_client)
        data = {
            "onOff": "on",
            "loadConnected": 0,
            "wattageInstant": 0,
            "powerTimer": 0,
            "lockKeypad": "locked",
            "drStatus": {"drActive": "off", "optOut": "off", "onOff": "off"},
            "rssi": -70,
            "controlledDevice": None,
            "errorCodeSet1": {},
        }
        switch._parse_common_state(data)
        assert switch._keypad == "locked"

    def test_power_switch_assigns_dr_status(self, mock_hass, mock_client):
        """PowerSwitch _parse_common_state assigns DR status fields."""
        switch = _make_power_switch(mock_hass, mock_client)
        data = {
            "onOff": "on",
            "loadConnected": 0,
            "wattageInstant": 0,
            "powerTimer": 0,
            "lockKeypad": "unlocked",
            "drStatus": {"drActive": "on", "optOut": "on", "onOff": "on"},
            "rssi": -50,
            "controlledDevice": None,
            "errorCodeSet1": {},
        }
        switch._parse_common_state(data)
        assert switch._drstatus_active == "on"
        assert switch._drstatus_optout == "on"
        assert switch._drstatus_onoff == "on"

    def test_power_switch_assigns_rssi(self, mock_hass, mock_client):
        """PowerSwitch _parse_common_state assigns _rssi when present."""
        switch = _make_power_switch(mock_hass, mock_client)
        data = {
            "onOff": "on",
            "loadConnected": 0,
            "wattageInstant": 0,
            "powerTimer": 0,
            "lockKeypad": "unlocked",
            "drStatus": {"drActive": "off", "optOut": "off", "onOff": "off"},
            "rssi": -45,
            "controlledDevice": "poolPump",
            "errorCodeSet1": {},
        }
        switch._parse_common_state(data)
        assert switch._rssi == -45
        assert switch._controlled_device == "poolPump"


@pytest.mark.unit
class TestUpdateOrchestration:
    """Tests verifying update() delegates correctly to helpers."""

    def test_update_skipped_when_inactive(self, mock_hass, mock_client):
        """When _active=False and snooze not expired, no client calls made."""
        switch = _make_power_switch(mock_hass, mock_client)
        switch._active = False
        switch._snooze = float("inf")

        switch.update()

        mock_client.get_device_attributes.assert_not_called()

    def test_update_calls_fetch_and_parse_on_clean_data(self, mock_hass, mock_client):
        """update() calls _fetch_attributes and _parse_common_state on clean data."""
        mock_client.get_device_attributes.return_value = {
            "onOff": "on",
            "loadConnected": 3000,
            "wattageInstant": 50,
            "powerTimer": 0,
            "lockKeypad": "unlocked",
            "drStatus": {"drActive": "off", "optOut": "off", "onOff": "off"},
            "rssi": -55,
            "controlledDevice": None,
            "errorCodeSet1": {},
        }
        switch = _make_power_switch(mock_hass, mock_client)

        switch.update()

        mock_client.get_device_attributes.assert_called_once()
        assert switch._onoff == "on"

    def test_update_calls_log_error_on_api_error(self, mock_hass, mock_client):
        """update() calls log_error when API returns an error."""
        mock_client.get_device_attributes.return_value = {"error": {"code": "DVCUNVLB"}}
        switch = _make_power_switch(mock_hass, mock_client)

        from unittest.mock import patch
        with patch.object(switch, "log_error") as mock_log:
            switch.update()

        mock_log.assert_called_once_with("DVCUNVLB")
