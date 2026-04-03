# Project Structure

```
sinope-130/
├── custom_components/neviweb130/   # The integration — all production code lives here
│   ├── __init__.py                 # setup(), Neviweb130Client (API wrapper), Neviweb130Data (multi-account)
│   ├── climate.py                  # Thermostat & heat-pump entities + ~50 climate services
│   ├── light.py                    # Light switch / dimmer entities + light services
│   ├── switch.py                   # Load controller / plug / multi-controller entities + switch services
│   ├── valve.py                    # Sedna valve entities + valve services
│   ├── sensor.py                   # GT130 gateway sensor, daily request counter
│   ├── update.py                   # OTA update entity (checks GitHub tags)
│   ├── const.py                    # All ATTR_*, SERVICE_*, CONF_*, MODE_* constants
│   ├── schema.py                   # voluptuous schemas for configuration.yaml and every service call
│   ├── helpers.py                  # Logger, request counter, translation helpers, safe_get_device_attributes
│   ├── manifest.json               # Integration metadata (domain, version, dependencies)
│   ├── services.yaml               # HA service definitions
│   ├── strings.json                # UI strings
│   └── translations/               # en.json, fr.json
│
├── tests/                          # Test suite
│   ├── conftest.py                 # Shared fixtures: mock_client, mock_hass, device_info factories
│   ├── test_api_client.py          # Neviweb130Client unit tests
│   ├── test_ha_interface.py        # HA entity interface stability tests
│   ├── test_ha_light.py            # Light entity tests
│   ├── test_ha_switch.py           # Switch entity tests
│   └── test_ha_valve.py            # Valve entity tests
│
├── doc/
│   ├── architecture.md             # Detailed API reference, class hierarchy, data flow diagrams
│   └── readme_fr.md                # French README
│
├── www/                            # Static assets (icons, images) served by HA frontend
├── scripts/                        # update-version.sh
├── pyproject.toml                  # pytest config
├── pytest.ini                      # Canonical pytest config (takes precedence)
├── tox.ini                         # Multi-env test matrix
└── .pre-commit-config.yaml         # Linting hooks
```

## Architecture Patterns

- **One file per HA platform**: `climate.py`, `light.py`, `switch.py`, `valve.py`, `sensor.py`, `update.py` each register their entities and services in `async_setup_platform()`.
- **Constants in `const.py`**: All attribute names, service names, config keys, and mode strings are defined as module-level constants. Never use raw strings for API attribute names.
- **Schemas in `schema.py`**: Every service call and the `configuration.yaml` schema is validated with `voluptuous`. Add new service schemas here.
- **Entity class selection by model number**: `signature.model` (integer) from the API determines which entity subclass to instantiate. Model→class mappings are in `doc/architecture.md`.
- **API errors handled per-attribute**: Responses can contain `DVCATTRNSPTD` (unsupported attribute), `USRSESSEXP` (session expired), etc. Use `safe_get_device_attributes` from `helpers.py` for safe access.
- **Multi-account support**: `Neviweb130Data` holds a list of `Neviweb130Client` instances. Platform setup iterates over all clients.

## Test Conventions
- Fixtures for `mock_client` and `mock_hass` are in `conftest.py` — reuse them.
- `make_device_info(device_id, model, name, sku)` factory creates minimal device dicts.
- Tests are marked with `@pytest.mark.unit`, `@pytest.mark.api`, `@pytest.mark.ha_interface`, etc.
- Mock the `Neviweb130Client` entirely — never make real HTTP calls in tests.
- **Test framework: `pytest` only.** Using `unittest.TestCase` or the `unittest` runner is forbidden.
- **Mocking: `unittest.mock.MagicMock` only.** Do not use any other mock library.
- **All test execution must happen inside the virtual environment** (`./venv/`). Never run `pytest` or any Python command outside of it.
