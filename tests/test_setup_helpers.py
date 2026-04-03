"""Unit tests for setup() helper functions extracted from __init__.py.

Tests:
  - _apply_global_config sets all module-level globals and hass.data["safe_mode"]
  - _schedule_version_check calls hass.loop.call_soon_threadsafe
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import custom_components.neviweb130 as init_module
from custom_components.neviweb130 import _apply_global_config, _schedule_version_check
from custom_components.neviweb130.schema import (
    HOMEKIT_MODE as DEFAULT_HOMEKIT_MODE,
    IGNORE_MIWI as DEFAULT_IGNORE_MIWI,
    NOTIFY as DEFAULT_NOTIFY,
    SAFE_MODE as DEFAULT_SAFE_MODE,
    SCAN_INTERVAL as DEFAULT_SCAN_INTERVAL,
    STAT_INTERVAL as DEFAULT_STAT_INTERVAL,
)
from custom_components.neviweb130.const import (
    CONF_HOMEKIT_MODE,
    CONF_IGNORE_MIWI,
    CONF_NOTIFY,
    CONF_SAFE_MODE,
    CONF_STAT_INTERVAL,
    DOMAIN,
)
from homeassistant.const import CONF_SCAN_INTERVAL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_hass():
    hass = MagicMock()
    hass.data = {DOMAIN: {"safe_mode": None}}
    return hass


# ===========================================================================
# _apply_global_config
# ===========================================================================

@pytest.mark.unit
class TestApplyGlobalConfig:
    """_apply_global_config must set all module-level globals and hass.data safe_mode."""

    def test_sets_scan_interval(self):
        hass = make_hass()
        config = {CONF_SCAN_INTERVAL: 120}
        _apply_global_config(hass, config)
        assert init_module.SCAN_INTERVAL == 120

    def test_sets_homekit_mode(self):
        hass = make_hass()
        config = {CONF_HOMEKIT_MODE: True}
        _apply_global_config(hass, config)
        assert init_module.HOMEKIT_MODE is True

    def test_sets_ignore_miwi(self):
        hass = make_hass()
        config = {CONF_IGNORE_MIWI: True}
        _apply_global_config(hass, config)
        assert init_module.IGNORE_MIWI is True

    def test_sets_stat_interval(self):
        hass = make_hass()
        config = {CONF_STAT_INTERVAL: 3600}
        _apply_global_config(hass, config)
        assert init_module.STAT_INTERVAL == 3600

    def test_sets_notify(self):
        hass = make_hass()
        config = {CONF_NOTIFY: "email"}
        _apply_global_config(hass, config)
        assert init_module.NOTIFY == "email"

    def test_sets_safe_mode_in_hass_data(self):
        hass = make_hass()
        config = {CONF_SAFE_MODE: True}
        _apply_global_config(hass, config)
        assert hass.data[DOMAIN]["safe_mode"] is True

    def test_uses_defaults_when_keys_absent(self):
        hass = make_hass()
        _apply_global_config(hass, {})
        assert init_module.SCAN_INTERVAL == DEFAULT_SCAN_INTERVAL
        assert init_module.HOMEKIT_MODE == DEFAULT_HOMEKIT_MODE
        assert init_module.IGNORE_MIWI == DEFAULT_IGNORE_MIWI
        assert init_module.STAT_INTERVAL == DEFAULT_STAT_INTERVAL
        assert init_module.NOTIFY == DEFAULT_NOTIFY
        assert hass.data[DOMAIN]["safe_mode"] == DEFAULT_SAFE_MODE

    def test_all_globals_set_together(self):
        hass = make_hass()
        config = {
            CONF_SCAN_INTERVAL: 60,
            CONF_HOMEKIT_MODE: False,
            CONF_IGNORE_MIWI: False,
            CONF_STAT_INTERVAL: 1800,
            CONF_NOTIFY: "push",
            CONF_SAFE_MODE: False,
        }
        _apply_global_config(hass, config)
        assert init_module.SCAN_INTERVAL == 60
        assert init_module.HOMEKIT_MODE is False
        assert init_module.IGNORE_MIWI is False
        assert init_module.STAT_INTERVAL == 1800
        assert init_module.NOTIFY == "push"
        assert hass.data[DOMAIN]["safe_mode"] is False


# ===========================================================================
# _schedule_version_check
# ===========================================================================

@pytest.mark.unit
class TestScheduleVersionCheck:
    """_schedule_version_check must call hass.loop.call_soon_threadsafe."""

    def test_calls_call_soon_threadsafe(self):
        hass = make_hass()
        _schedule_version_check(hass)
        hass.loop.call_soon_threadsafe.assert_called_once()

    def test_passes_async_create_task_as_first_arg(self):
        hass = make_hass()
        _schedule_version_check(hass)
        args = hass.loop.call_soon_threadsafe.call_args[0]
        # First positional arg must be hass.async_create_task
        assert args[0] is hass.async_create_task
