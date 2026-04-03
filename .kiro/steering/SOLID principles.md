---
inclusion: always
---

# SOLID Principles & Code Conventions

## Single Responsibility Principle

- Each platform file (`climate.py`, `light.py`, `switch.py`, `valve.py`, `sensor.py`, `update.py`) owns exactly one HA platform: entity classes, service registrations, and the `async_setup_platform()` entry point for that platform only.
- `const.py` is the single source of truth for all `ATTR_*`, `SERVICE_*`, `CONF_*`, and `MODE_*` names. Never use raw API attribute strings outside of `const.py`.
- `schema.py` owns all `voluptuous` validation. Every service call schema and the `configuration.yaml` schema must be defined there — not inline in platform files.
- `helpers.py` owns cross-cutting utilities: logging setup, request counter, translation helpers, and `safe_get_device_attributes`. Do not duplicate these in platform files.
- `__init__.py` owns integration setup, `Neviweb130Client` (API wrapper), and `Neviweb130Data` (multi-account container). Platform files must not instantiate clients directly.

## Open/Closed Principle

- Add support for a new device model by subclassing the nearest existing thermostat/light/switch/valve class and overriding only the methods that differ. Do not modify the base class to accommodate a single model's quirks.
- New HA services must be registered in `async_setup_platform()` via `hass.services.async_register()` and validated with a schema from `schema.py`. Do not add service logic directly to entity methods.
- Model-to-class dispatch in `async_setup_platform()` uses `signature.model` (integer). Add new model numbers to the existing dispatch block; do not restructure the dispatch logic.

## Liskov Substitution Principle

- Subclasses must honour the HA entity interface contracts (`ClimateEntity`, `LightEntity`, `SwitchEntity`, `ValveEntity`, `SensorEntity`, `UpdateEntity`). Override only what the device actually supports; return `None` or the appropriate HA default for unsupported properties.
- Do not raise exceptions from HA interface properties (`current_temperature`, `hvac_mode`, etc.). Return `None` or a safe default when data is unavailable.

## Interface Segregation Principle

- Entity classes expose only the HA interface methods their device supports. A base thermostat class must not implement heat-pump-specific methods (`set_fan_mode`, `set_swing_mode`) — those belong in the heat-pump subclass.
- Custom services are registered per-platform. A climate service must not be registered in `light.py` or `switch.py`.

## Dependency Inversion Principle

- Platform files depend on `Neviweb130Client` through the `hass.data[DOMAIN]` data object injected by `setup()`. Platform files must not import or instantiate `Neviweb130Client` directly.
- All API attribute names flow through `const.py` constants. Platform files import constants, not raw strings.

---

## API Error Handling

- Always use `safe_get_device_attributes` from `helpers.py` when fetching device attributes. It handles `DVCATTRNSPTD` (unsupported attribute) and silent empty responses gracefully.
- On `USRSESSEXP`, call `client.reconnect()` — do not re-implement login logic in platform files.
- Known API error codes: `DVCATTRNSPTD`, `DVCACTNSPTD`, `DVCCOMMTO`, `DVCUNVLB`, `DVCBUSY`, `ACCDAYREQMAX`. Handle these defensively; never let them propagate as unhandled exceptions to HA.

## Constants & Naming

- All API attribute names are camelCase strings (e.g. `"roomTemperature"`). Their Python constants use `ATTR_` prefix and SCREAMING_SNAKE_CASE (e.g. `ATTR_ROOM_TEMPERATURE`).
- Service name constants use `SERVICE_` prefix (e.g. `SERVICE_SET_BACKLIGHT`).
- Config keys use `CONF_` prefix; mode strings use `MODE_` prefix.
- Never introduce a new raw string for an API attribute — always add a constant to `const.py` first.

## Testing Conventions

- Use `pytest` only. `unittest.TestCase` and the `unittest` runner are forbidden.
- Mock with `unittest.mock.MagicMock` only. No other mock library.
- Reuse fixtures from `conftest.py`: `mock_client`, `mock_hass`, `make_device_info(device_id, model, name, sku)`.
- Never make real HTTP calls in tests. Mock `Neviweb130Client` entirely.
- Mark tests with `@pytest.mark.unit`, `@pytest.mark.api`, or `@pytest.mark.ha_interface` as appropriate.
- All test execution must happen inside the virtual environment (`./venv/`). Activate with `source ./venv/bin/activate` before running `pytest`.
