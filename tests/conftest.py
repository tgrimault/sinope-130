"""Shared pytest fixtures for neviweb130 tests."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Minimal device_info factories
# ---------------------------------------------------------------------------

def make_device_info(device_id: int, model: int, name: str = "Test Device", sku: str = "TEST"):
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


# ---------------------------------------------------------------------------
# Mock Neviweb130Client
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client():
    client = MagicMock()
    client.scoped_unique_id.side_effect = lambda device_id: str(device_id)
    client._account_prefix = ""
    client._is_primary = True
    client._network_name = "Home"
    client._network_name2 = None
    client._network_name3 = None
    return client


# ---------------------------------------------------------------------------
# Mock hass
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.data = {
        "neviweb130": {
            "safe_mode": "-",
            "translation_cache": None,
            "ready": False,
        }
    }
    hass.config.language = "en"
    hass.loop = asyncio.new_event_loop()
    return hass


# ---------------------------------------------------------------------------
# Thermostat device_info presets
# ---------------------------------------------------------------------------

@pytest.fixture
def zigbee_thermostat_info():
    return make_device_info(111, 1123, "Living Room", "TH1123ZB")


@pytest.fixture
def wifi_thermostat_info():
    return make_device_info(222, 1510, "Bedroom", "TH1123WF")


@pytest.fixture
def floor_thermostat_info():
    return make_device_info(333, 737, "Bathroom", "TH1300ZB")


@pytest.fixture
def low_voltage_thermostat_info():
    return make_device_info(444, 7372, "Office", "TH1400ZB")


@pytest.fixture
def heat_cool_thermostat_info():
    return make_device_info(555, 6727, "Master", "TH6500WF")


@pytest.fixture
def heat_pump_thermostat_info():
    return make_device_info(666, 6810, "Garage", "HP6000ZB-GE")


# ---------------------------------------------------------------------------
# Light device_info presets
# ---------------------------------------------------------------------------

@pytest.fixture
def light_switch_info():
    return make_device_info(777, 2121, "Hall Light", "SW2500ZB")


@pytest.fixture
def dimmer_info():
    return make_device_info(888, 2131, "Living Dimmer", "DM2500ZB")


# ---------------------------------------------------------------------------
# Switch device_info presets
# ---------------------------------------------------------------------------

@pytest.fixture
def load_controller_info():
    return make_device_info(999, 2506, "Pool Pump", "RM3250ZB")


@pytest.fixture
def wall_outlet_info():
    return make_device_info(1000, 2610, "Kitchen Outlet", "SP2610ZB")


@pytest.fixture
def water_heater_info():
    return make_device_info(1001, 2151, "Water Heater", "RM3500ZB")
