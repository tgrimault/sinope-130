# Test Suite Summary

726 tests across 19 files. All pass. Zero regressions.

---

## Test Files

### Contract-level tests — Sinopé API

| File | Tests | Lines | What it covers |
|---|---|---|---|
| `test_api_client.py` | 49 | 848 | `Neviweb130Client` — all HTTP endpoints (login, discovery, attributes, energy stats, weather, alerts), HTTP helpers (`_do_get`, `_do_put`, `_handle_response_error`), error handling |
| `test_client_set_methods.py` | 41 | 295 | Exact JSON attribute key names for every `set_*` method on `Neviweb130Client` — temperature, display, floor, low-voltage, heat/cool, mode, early-start |

### Contract-level tests — Home Assistant interface

| File | Tests | Lines | What it covers |
|---|---|---|---|
| `test_ha_interface.py` | 61 | 906 | Climate platform: `setup()`, entity properties, HA action methods, 50+ custom services, update polling, error handling, multi-account, helper methods |
| `test_ha_light.py` | 47 | 571 | Light platform: `Neviweb130Light`, `Neviweb130Dimmer`, `Neviweb130NewDimmer` — properties, turn on/off, services, update, extra_state_attributes |
| `test_ha_switch.py` | 30 | 489 | Switch platform: `Neviweb130Switch`, `Neviweb130PowerSwitch` — properties, turn on/off, services, update helpers, safe mode |
| `test_ha_valve.py` | 35 | 495 | Valve platform: `Neviweb130Valve`, `Neviweb130WifiValve` — properties, open/close, services, update helpers |
| `test_ha_sensor.py` | 11 | 108 | Sensor platform: `Neviweb130GatewaySensor`, `NeviwebDailyRequestSensor` — properties, state, services |

### Property-based / structural tests

| File | Tests | Lines | What it covers |
|---|---|---|---|
| `test_structural_invariants.py` | 7 | 125 | All 7 SOLID structural invariants: `update()` ≤ 40 lines, `do_stat()` ≤ 30 lines, `log_error()` no elif, ISP (WifiThermostat has no `set_floor_limit`), `_register_climate_services` exists, `ERROR_HANDLERS` dict exists, `_fetch_attributes` helper exists |
| `test_preservation.py` | 38 | 567 | Observable behaviour unchanged after refactor: service call signatures (group A), `extra_state_attributes` key stability (group B), update polling contract (group C), model→class dispatch (group D), error code handling (group E) |

### Unit tests — refactored helpers

| File | Tests | Lines | What it covers |
|---|---|---|---|
| `test_climate_base.py` | 77 | 506 | `Neviweb130Thermostat` class-level: constructor, properties (`hvac_mode`, `preset_mode`, `target_temperature`, `icon_type`, `is_em_heat`), `_parse_common_state`, `_parse_dr_state`, `_handle_error`, service methods |
| `test_climate_mixins.py` | 87 | 478 | `FloorMixin`, `LowVoltageMixin`, `HeatPumpMixin`, `HeatCoolMixin` — method presence, inheritance, ISP compliance (WifiThermostat excluded), method implementations |
| `test_climate_set_methods.py` | 51 | 392 | ~65 climate service handlers — entity method → `Neviweb130Client` method mapping for all platforms |
| `test_climate_subclasses.py` | 38 | 537 | `Neviweb130HPThermostat`, `Neviweb130HcThermostat`, `Neviweb130HeatCoolThermostat` — update parsing, extra_state_attributes, error handling |
| `test_error_handlers.py` | 30 | 266 | `ERROR_HANDLERS` lookup table: all 13 handler functions, dispatch logic, unknown codes fall through without raising |
| `test_update_helpers.py` | 31 | 383 | `_fetch_attributes`, `_parse_common_state`, `_handle_error`, `_handle_snooze`, full `update()` orchestration, safe mode branching |
| `test_stat_helpers.py` | 17 | 297 | `_fetch_monthly_stats`, `_fetch_daily_stats`, `_fetch_hourly_stats`, `_record_stat`, `do_stat()` interval logic |
| `test_service_registration.py` | 4 | 63 | `_register_climate_services` exists as module-level function, registers > 30 services, `async_setup_platform` ≤ 40 lines |
| `test_setup_helpers.py` | 10 | 135 | `_apply_global_config` sets all globals, `_schedule_version_check` wires the async task |
| `test_sensor_update.py` | 62 | 458 | Sensor and update platforms: leak sensor alerts, tank sensor configuration, gateway sensor, `Neviweb130UpdateEntity` properties and install guard |

---

## Totals

| Category | Files | Tests |
|---|---|---|
| Sinopé API contracts | 2 | 90 |
| HA interface contracts | 5 | 184 |
| Structural / preservation | 2 | 45 |
| Class-level unit tests | 10 | 407 |
| **Total** | **19** | **726** |

---

## Running the suite

```bash
# Activate venv first (always required)
source ./venv/bin/activate

# Full suite
pytest --no-cov

# With coverage
pytest --cov=custom_components.neviweb130 --cov-report=html

# Single file
pytest tests/test_climate_base.py --no-cov -v

# By marker
pytest -m unit --no-cov
pytest -m api --no-cov
pytest -m ha_interface --no-cov
```

---

## What is NOT tested (by design)

- HA core internals (entity registry, state machine, UI)
- Real HTTP calls to Neviweb (all mocked)
- Home Assistant startup lifecycle beyond `setup()` and `async_setup_platform()`
