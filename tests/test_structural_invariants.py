"""
Structural invariant tests for the climate-refactor bugfix spec.

These tests assert the EXPECTED POST-REFACTOR structural invariants.
They MUST FAIL on the current (unfixed) code — that failure is the
success condition for Task 1.

DO NOT fix the code to make these pass. They will pass naturally once
the refactor tasks (3–10) are complete.

Documented counterexamples (observed on unfixed code):
  Test 1 — update() line count:    actual 116 lines   (limit: 40)
  Test 2 — do_stat() line count:   actual 163 lines   (limit: 30)
  Test 3 — log_error() elif count: 12 elif branches   (expected: none)
  Test 4 — ISP violation:          set_floor_limit inherited from Neviweb130Thermostat
                                   base class → accessible via hasattr on WifiThermostat
  Test 5 — service extraction:     _register_climate_services does not exist
  Test 6 — ERROR_HANDLERS dict:    no module-level ERROR_HANDLERS dict
  Test 7 — _fetch_attributes:      no _fetch_attributes method on base class
"""

import inspect

import pytest

import custom_components.neviweb130.climate as climate_module
from custom_components.neviweb130.climate import (
    Neviweb130Thermostat,
    Neviweb130WifiThermostat,
)


@pytest.mark.unit
def test_update_line_count():
    """update() must be ≤ 40 lines after refactor.

    Counterexample on unfixed code: ~200 lines.
    """
    lines = inspect.getsourcelines(Neviweb130Thermostat.update)[0]
    actual = len(lines)
    assert actual <= 40, (
        f"Neviweb130Thermostat.update() is {actual} lines — "
        "expected ≤ 40 after SRP decomposition"
    )


@pytest.mark.unit
def test_do_stat_line_count():
    """do_stat() must be ≤ 30 lines after refactor.

    Counterexample on unfixed code: ~160 lines.
    """
    lines = inspect.getsourcelines(Neviweb130Thermostat.do_stat)[0]
    actual = len(lines)
    assert actual <= 30, (
        f"Neviweb130Thermostat.do_stat() is {actual} lines — "
        "expected ≤ 30 after SRP decomposition"
    )


@pytest.mark.unit
def test_log_error_no_elif():
    """log_error() must not contain elif branches after OCP refactor.

    Counterexample on unfixed code: 12+ elif branches in a flat dispatch chain.
    """
    source = inspect.getsource(Neviweb130Thermostat.log_error)
    assert "elif" not in source, (
        "Neviweb130Thermostat.log_error() still contains 'elif' — "
        "expected a lookup-table dispatch (ERROR_HANDLERS dict) with no elif chain"
    )


@pytest.mark.unit
def test_isp_wifi_thermostat_no_set_floor_limit():
    """Neviweb130WifiThermostat must NOT have set_floor_limit after ISP fix.

    Counterexample on unfixed code: method is inherited from Neviweb130Thermostat
    base class and therefore accessible via hasattr.
    """
    assert "set_floor_limit" not in Neviweb130WifiThermostat.__dict__ and not hasattr(
        Neviweb130WifiThermostat, "set_floor_limit"
    ), (
        "Neviweb130WifiThermostat still exposes set_floor_limit — "
        "expected this method to live only on FloorMixin / floor subclasses"
    )


@pytest.mark.unit
def test_register_climate_services_exists():
    """_register_climate_services must exist as a module-level function after SRP fix.

    Counterexample on unfixed code: no such function — services are registered
    inline inside async_setup_platform().
    """
    assert hasattr(climate_module, "_register_climate_services"), (
        "climate module has no _register_climate_services function — "
        "expected service registration to be extracted from async_setup_platform()"
    )


@pytest.mark.unit
def test_error_handlers_dict_exists():
    """ERROR_HANDLERS must exist as a module-level dict after OCP fix.

    Counterexample on unfixed code: no such module-level dict — error dispatch
    is done via a flat if/elif chain inside log_error().
    """
    assert hasattr(climate_module, "ERROR_HANDLERS"), (
        "climate module has no ERROR_HANDLERS dict — "
        "expected a module-level lookup table mapping error codes to handler functions"
    )


@pytest.mark.unit
def test_fetch_attributes_helper_exists():
    """Neviweb130Thermostat must have a _fetch_attributes helper after SRP fix.

    Counterexample on unfixed code: no such method — attribute fetching is done
    inline inside update().
    """
    assert hasattr(Neviweb130Thermostat, "_fetch_attributes"), (
        "Neviweb130Thermostat has no _fetch_attributes method — "
        "expected this helper to be extracted from update() during SRP decomposition"
    )
