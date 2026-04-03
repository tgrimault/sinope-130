"""Tests for _register_climate_services() extraction from async_setup_platform().

Validates that:
- _register_climate_services exists as a module-level function
- Calling it registers services on the hass object
- The number of registered services is > 30
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import custom_components.neviweb130.climate as climate_module


@pytest.mark.unit
def test_register_climate_services_is_module_level_function():
    """_register_climate_services must exist as a module-level function."""
    assert hasattr(climate_module, "_register_climate_services"), (
        "climate module has no _register_climate_services function"
    )
    assert callable(climate_module._register_climate_services), (
        "_register_climate_services is not callable"
    )


@pytest.mark.unit
def test_register_climate_services_registers_services():
    """Calling _register_climate_services must call hass.services.async_register."""
    hass = MagicMock()
    entities = []

    climate_module._register_climate_services(hass, entities)

    assert hass.services.async_register.called, (
        "hass.services.async_register was never called by _register_climate_services"
    )


@pytest.mark.unit
def test_register_climate_services_registers_more_than_30_services():
    """_register_climate_services must register > 30 services (there are ~50)."""
    hass = MagicMock()
    entities = []

    climate_module._register_climate_services(hass, entities)

    call_count = hass.services.async_register.call_count
    assert call_count > 30, (
        f"Expected > 30 services registered, got {call_count}"
    )


@pytest.mark.unit
def test_async_setup_platform_line_count():
    """async_setup_platform() must be ≤ 40 lines after service extraction."""
    import inspect
    lines = inspect.getsourcelines(climate_module.async_setup_platform)[0]
    actual = len(lines)
    assert actual <= 40, (
        f"async_setup_platform() is {actual} lines — expected ≤ 40 after service extraction"
    )
