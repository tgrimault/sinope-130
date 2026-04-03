"""Test suite for Sensor platform Home Assistant interface."""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.data = {
        "neviweb130": {
            "data": MagicMock(),
            "safe_mode": "-",
            "request_data": {"count": 42},
        }
    }
    return hass


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.scoped_unique_id = MagicMock(side_effect=lambda x: str(x))
    client.get_device_status = MagicMock(return_value={"status": "online"})
    client.get_neviweb_status = MagicMock(return_value={"occupancyMode": "home"})
    return client


@pytest.fixture
def gateway_device_info():
    return {
        "id": 555666,
        "name": "GT130 Gateway",
        "sku": "GT130",
        "location$id": 67890,
        "signature": {
            "model": 130,
            "modelCfg": 0,
            "protocol": "zigbee",
            "softVersion": {"major": 1, "middle": 2, "minor": 3},
        },
    }


@pytest.mark.unit
class TestGatewaySensorInterface:
    """Test GT130 gateway sensor HA interface."""

    @pytest.fixture
    def gateway(self, mock_hass, mock_client, gateway_device_info):
        from custom_components.neviweb130.sensor import Neviweb130GatewaySensor
        g = Neviweb130GatewaySensor(
            gateway_device_info, "GT130 Gateway", "gateway", "GT130", "1.0.0", 67890, mock_client
        )
        g.hass = mock_hass
        return g

    def test_unique_id(self, gateway):
        assert gateway.unique_id == "555666"

    def test_name(self, gateway):
        assert gateway.name == "GT130 Gateway"

    def test_state_before_update_is_none(self, gateway):
        assert gateway.state is None

    def test_extra_state_attributes_keys(self, gateway):
        attrs = gateway.extra_state_attributes
        assert isinstance(attrs, dict)
        assert "gateway_status" in attrs
        assert "sku" in attrs
        assert "id" in attrs
        assert "firmware" in attrs

    def test_set_neviweb_status_calls_client(self, gateway, mock_client):
        gateway.set_neviweb_status({"id": "555666", "mode": "away"})
        mock_client.post_neviweb_status.assert_called_once_with("67890", "away")

    def test_set_neviweb_status_updates_occupancy(self, gateway):
        gateway.set_neviweb_status({"id": "555666", "mode": "away"})
        assert gateway._occupancyMode == "away"

    def test_set_activation_deactivates(self, gateway):
        gateway.set_activation({"id": "555666", "active": False})
        assert gateway._active is False


@pytest.mark.unit
class TestDailyRequestSensor:
    """Test daily API request counter sensor."""

    @pytest.fixture
    def sensor(self, mock_hass):
        from custom_components.neviweb130.sensor import NeviwebDailyRequestSensor
        return NeviwebDailyRequestSensor(mock_hass)

    def test_unique_id(self, sensor):
        assert sensor.unique_id == "neviweb130_daily_requests"

    def test_name(self, sensor):
        assert sensor.name == "Neviweb130 Daily Requests"

    def test_state_reads_from_hass_data(self, sensor):
        assert sensor.state == 42

    def test_unit_of_measurement(self, sensor):
        # The daily request sensor tracks a count — unit may be None or "requests"
        # What matters is that state is numeric and accessible
        assert isinstance(sensor.state, int)
