---
inclusion: always
---

# Home Assistant Integration Development Guide

## Integration Types

Choose the right integration type before writing any code:

| Type | Use when |
|---|---|
| `config_flow` | New integrations — UI-configured, supports re-auth, options flow |
| Legacy YAML | Existing integrations only — `setup()` + `configuration.yaml` |
| `cloud_polling` | Device state fetched by polling a cloud API on an interval |
| `cloud_push` | Cloud sends state updates via webhook or persistent connection |
| `local_polling` | Device polled directly on the local network |
| `local_push` | Device pushes state updates locally (preferred for responsiveness) |

**This codebase uses legacy YAML + `cloud_polling`.** New integrations should use `config_flow`.

---

## Entry Points

### Legacy YAML (`setup`)

```python
def setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data[DOMAIN] = {"data": MyData(hass, config[DOMAIN])}
    discovery.load_platform(hass, Platform.CLIMATE, DOMAIN, {}, config)
    return True
```

### Config Flow (`async_setup_entry`)

```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = MyApiClient(entry.data[CONF_HOST])
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True
```

### Platform setup

Each platform file exposes `async_setup_platform()` (legacy) or `async_setup_entry()` (config flow). Entity instances are created here and passed to `async_add_entities()`.

---

## Entity Development

### Choose the right base class

Always subclass the most specific HA entity class available:

- `ClimateEntity` — thermostats, heat pumps
- `LightEntity` — lights, dimmers
- `SwitchEntity` — on/off switches, load controllers
- `SensorEntity` — read-only measurements
- `BinarySensorEntity` — on/off state (leak, motion, door)
- `ValveEntity` — motorised valves
- `UpdateEntity` — OTA firmware updates
- `CoverEntity` — blinds, garage doors

### Required properties

Every entity must implement:

```python
@property
def unique_id(self) -> str:
    return str(self._device_id)  # stable, never changes

@property
def name(self) -> str:
    return self._name
```

### State properties must never raise

HA calls properties on every state write. Guard against missing data:

```python
@property
def current_temperature(self) -> float | None:
    return self._cur_temp  # return None, not raise
```

### `extra_state_attributes`

Return a flat `dict[str, Any]` of device-specific data not covered by standard HA attributes. Keep keys stable — renaming them breaks user automations and templates.

### `supported_features`

Declare capabilities using the platform's `EntityFeature` flags. Only advertise features the device actually supports:

```python
@property
def supported_features(self) -> ClimateEntityFeature:
    return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
```

---

## Polling vs Push

### Polling (`update()` / `async_update()`)

HA calls `update()` on every entity at `scan_interval`. Keep it efficient:

- Batch attribute reads into a single API call where possible.
- Cache the last known value and return it on transient errors — do not reset state to `None` on every timeout.
- Use `self._attr_available = False` to mark a device offline rather than returning stale data silently.

```python
def update(self) -> None:
    try:
        data = self._client.get_device_attributes(self._id, ATTRIBUTES)
    except TimeoutError:
        _LOGGER.warning("Timeout polling %s", self._name)
        return  # keep last known state
    self._parse(data)
```

### Push (coordinator pattern)

For push-based or shared-polling integrations, use `DataUpdateCoordinator`:

```python
coordinator = DataUpdateCoordinator(
    hass,
    _LOGGER,
    name="my_device",
    update_method=client.fetch_all,
    update_interval=timedelta(seconds=30),
)
await coordinator.async_config_entry_first_refresh()
```

Entities inherit from `CoordinatorEntity` and read from `coordinator.data` — no per-entity polling.

---

## Services

### Registering a service

```python
hass.services.async_register(
    DOMAIN,
    SERVICE_SET_TEMPERATURE,
    handle_set_temperature,
    schema=SET_TEMPERATURE_SCHEMA,
)
```

### Schema validation

Always validate service call data with `voluptuous` before any business logic:

```python
SET_TEMPERATURE_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_TEMPERATURE): vol.Coerce(float),
})
```

### Service handler pattern

```python
async def handle_set_temperature(call: ServiceCall) -> None:
    entity_id = call.data[ATTR_ENTITY_ID]
    temp = call.data[ATTR_TEMPERATURE]
    entity = get_entity(hass, entity_id)
    if entity is None:
        raise ServiceValidationError(f"Entity {entity_id} not found")
    entity.set_temperature_value(temp)
    entity.schedule_update_ha_state(True)
```

---

## Constants & Naming

- All API attribute names go in `const.py` as `ATTR_*` constants — never use raw strings in platform files.
- Service names: `SERVICE_SET_*` constants in `const.py`, registered in `services.yaml`.
- Config keys: `CONF_*` prefix. Mode strings: `MODE_*` prefix.
- Entity unique IDs must be **strings**, stable across restarts, and scoped to avoid collisions in multi-account setups.

---

## Error Handling

### API errors

Handle known error codes explicitly; let unknown errors propagate so they appear in logs:

```python
if "error" in data:
    code = data["error"]["code"]
    if code == "USRSESSEXP":
        self._client.reconnect()
        return
    if code == "DVCUNVLB":
        self._attr_available = False
        return
    _LOGGER.error("Unexpected API error for %s: %s", self._name, code)
```

### Session expiry

Re-authenticate on session expiry rather than marking the device unavailable. Implement a `reconnect()` method that re-runs login + discovery.

### Rate limits

Track API request counts. Respect the provider's daily limit — expose a sensor for the count so users can monitor it. Avoid polling more frequently than necessary.

---

## Async Best Practices

- Use `async def` for all HA callbacks (`async_setup_entry`, `async_update`, service handlers).
- Use `await hass.async_add_executor_job(blocking_fn)` for any synchronous/blocking I/O inside an async context.
- Never call `time.sleep()` in async code — use `await asyncio.sleep()`.
- Use `hass.async_create_task()` to fire-and-forget background coroutines.
- Use `async_track_time_interval()` for recurring background tasks instead of manual loops.

---

## Configuration Schema

Define the full `configuration.yaml` schema in `schema.py` using `voluptuous`:

```python
CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=300): cv.positive_int,
    })
}, extra=vol.ALLOW_EXTRA)
```

---

## Translations & Notifications

- Store UI strings in `strings.json` and `translations/en.json`. Never hardcode user-facing strings in Python.
- Use `hass.services.async_call("persistent_notification", "create", {...})` for user-facing alerts.
- Use `translated_or_default(hass, key, fallback)` to safely access translations before the cache is loaded.

---

## Testing

- Mock the API client entirely — never make real HTTP calls in tests.
- Use `pytest` with `unittest.mock.MagicMock`. No other mock library.
- Test entity properties, `update()` state parsing, and service handler → client call chains.
- Verify exact API attribute key names in client method tests — a wrong key silently sends bad data.
- Mark tests: `@pytest.mark.unit`, `@pytest.mark.api`, `@pytest.mark.ha_interface`.

---

## Checklist for a New Platform

1. Subclass the correct HA entity base class.
2. Implement `unique_id`, `name`, and all required properties for the platform.
3. Declare `supported_features` accurately.
4. Implement `update()` or use `DataUpdateCoordinator`.
5. Handle all known API error codes defensively.
6. Register services with `voluptuous` schemas.
7. Add constants to `const.py`, schemas to `schema.py`.
8. Add service definitions to `services.yaml`.
9. Add translations to `strings.json` and `translations/en.json`.
10. Write unit tests for properties, update parsing, and service handlers.
