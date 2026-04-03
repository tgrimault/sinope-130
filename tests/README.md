# Neviweb130 Test Suite

726 tests, 19 files. Run with `pytest --no-cov` from the repo root (venv must be active).

---

## Quick start

```bash
source ./venv/bin/activate
pytest --no-cov          # fast run
pytest                   # with coverage (slower)
```

---

## File overview

### Sinopé API contracts
Tests that verify the exact HTTP calls made to the Neviweb REST API — endpoint URLs, request payloads, and response parsing. These must pass before and after any refactoring.

| File | Tests | What it covers |
|---|---|---|
| `test_api_client.py` | 49 | All `Neviweb130Client` methods: login, device discovery, attribute read/write, energy stats, weather, alerts, HTTP helpers |
| `test_client_set_methods.py` | 41 | Exact JSON attribute key names for every `set_*` method |

### Home Assistant interface contracts
Tests that verify the HA entity interface — properties, action methods, and custom services. These are the primary regression gate during refactoring.

| File | Tests | What it covers |
|---|---|---|
| `test_ha_interface.py` | 61 | Climate platform: all entity properties, HA actions, 50+ custom services, update polling, error handling, multi-account |
| `test_ha_light.py` | 47 | Light platform: `Neviweb130Light`, `Neviweb130Dimmer`, `Neviweb130NewDimmer` |
| `test_ha_switch.py` | 30 | Switch platform: `Neviweb130Switch`, `Neviweb130PowerSwitch` |
| `test_ha_valve.py` | 35 | Valve platform: `Neviweb130Valve`, `Neviweb130WifiValve` |
| `test_ha_sensor.py` | 11 | Sensor platform: `Neviweb130GatewaySensor`, `NeviwebDailyRequestSensor` |

### Structural / preservation tests
Tests that encode the SOLID refactoring invariants and verify no observable behaviour changed.

| File | Tests | What it covers |
|---|---|---|
| `test_structural_invariants.py` | 7 | All 7 structural invariants (line counts, ISP, `ERROR_HANDLERS`, helper existence) |
| `test_preservation.py` | 38 | Service call signatures, `extra_state_attributes` key stability, polling contract, model→class dispatch, error code handling |

### Class-level unit tests
Tests that cover constructor initialisation, property logic, and service method behaviour at the class level — complementing the contract tests above.

| File | Tests | What it covers |
|---|---|---|
| `test_climate_base.py` | 77 | `Neviweb130Thermostat`: constructor, properties, `_parse_common_state`, `_parse_dr_state`, `_handle_error`, service methods |
| `test_climate_mixins.py` | 87 | `FloorMixin`, `LowVoltageMixin`, `HeatPumpMixin`, `HeatCoolMixin`: method presence, inheritance, ISP compliance |
| `test_climate_set_methods.py` | 51 | All climate service handlers → client method mapping |
| `test_climate_subclasses.py` | 38 | `Neviweb130HPThermostat`, `Neviweb130HcThermostat`, `Neviweb130HeatCoolThermostat` |
| `test_error_handlers.py` | 30 | `ERROR_HANDLERS` dict, all 13 handler functions, dispatch logic |
| `test_update_helpers.py` | 31 | `_fetch_attributes`, `_parse_common_state`, `_handle_error`, `_handle_snooze`, `update()` orchestration |
| `test_stat_helpers.py` | 17 | `_fetch_monthly_stats`, `_fetch_daily_stats`, `_fetch_hourly_stats`, `do_stat()` |
| `test_service_registration.py` | 4 | `_register_climate_services` extraction, service count, `async_setup_platform` line count |
| `test_setup_helpers.py` | 10 | `_apply_global_config`, `_schedule_version_check` |
| `test_sensor_update.py` | 62 | Sensor and update platforms: leak/tank/gateway sensors, `Neviweb130UpdateEntity` |

---

## Conventions

- **Framework**: `pytest` only — no `unittest.TestCase`
- **Mocking**: `unittest.mock.MagicMock` only
- **Fixtures**: reuse `mock_client`, `mock_hass`, `make_device_info()` from `conftest.py`
- **No real HTTP calls** — `Neviweb130Client` is always fully mocked
- **Markers**: `@pytest.mark.unit`, `@pytest.mark.api`, `@pytest.mark.ha_interface`
- **Venv**: all test execution must happen inside `./venv/` — activate first

---

## Project structure (production code)

```
custom_components/neviweb130/
├── __init__.py             # setup(), Neviweb130Client, Neviweb130Data
├── climate/                # Thermostat platform
│   ├── __init__.py         # async_setup_platform, _register_climate_services
│   ├── base.py             # Neviweb130Thermostat
│   ├── mixins.py           # FloorMixin, LowVoltageMixin, HeatPumpMixin, HeatCoolMixin
│   ├── zigbee.py           # G2, Floor, Low, Double subclasses
│   ├── wifi.py             # Wifi, WifiLite, ColorWifi, LowWifi, WifiFloor subclasses
│   ├── heatcool.py         # Hc, HeatCool subclasses
│   └── heatpump.py         # HP, WifiHP subclasses
├── switch/                 # Switch platform
│   ├── __init__.py         # async_setup_platform, _register_switch_services
│   ├── base.py             # Neviweb130Switch
│   └── subclasses.py       # PowerSwitch, WifiPowerSwitch, TankPowerSwitch, ...
├── valve/                  # Valve platform
│   ├── __init__.py         # async_setup_platform, _register_valve_services
│   ├── base.py             # Neviweb130Valve
│   └── subclasses.py       # WifiValve, MeshValve, WifiMeshValve
├── sensor/                 # Sensor platform
│   ├── __init__.py         # async_setup_platform
│   ├── base.py             # Neviweb130Sensor
│   └── subclasses.py       # ConnectedSensor, TankSensor, GatewaySensor, DailyRequestSensor
├── light.py                # Light platform (entry point + classes)
├── update.py               # OTA update entity
├── const.py                # All ATTR_*, SERVICE_*, CONF_*, MODE_* constants
├── schema.py               # voluptuous schemas
└── helpers.py              # safe_get_device_attributes, translated_or_default, ...
```

See `doc/architecture.md` for the full architecture reference.
