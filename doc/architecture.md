# neviweb130 — Architecture & Developer Reference

## Table of Contents
1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Home Assistant Entry Points](#home-assistant-entry-points)
4. [Component Class Hierarchy](#component-class-hierarchy)
5. [SOLID Design Principles Applied](#solid-design-principles-applied)
6. [Sinopé API Reference](#sinopé-api-reference)
7. [Data Flow](#data-flow)

---

## Overview

`neviweb130` is a **legacy-style** (YAML-configured) Home Assistant custom integration. It uses the `cloud_polling` IoT class: all device communication goes through the Neviweb REST API (`https://neviweb.com/api/`). There is no local Zigbee/Wi-Fi communication — the GT130 gateway or the Wi-Fi devices themselves relay data to Neviweb, and HA polls Neviweb on a configurable interval.

---

## Project Structure

The integration was refactored from a set of monolithic platform files into a sub-package hierarchy. Each platform now has a dedicated sub-package containing focused modules, while the top-level platform file remains the HA entry point.

```
custom_components/neviweb130/
│
├── __init__.py             # HA entry point: setup(), Neviweb130Data, Neviweb130Client
├── climate/                # Thermostat & heat-pump platform
│   ├── __init__.py         # async_setup_platform(), _register_climate_services()
│   ├── base.py             # Neviweb130Thermostat base class (~1600 lines)
│   ├── mixins.py           # FloorMixin, LowVoltageMixin, HeatPumpMixin, HeatCoolMixin
│   ├── zigbee.py           # Zigbee subclasses: G2, Floor, Low, Double
│   ├── wifi.py             # Wi-Fi subclasses: Wifi, WifiLite, ColorWifi, LowWifi, WifiFloor
│   ├── heatcool.py         # Hc (interlock) and HeatCool (TH6xxx) subclasses
│   └── heatpump.py         # HP and WifiHP subclasses
│
├── switch/                 # Load controller / plug / multi-controller platform
│   ├── __init__.py         # async_setup_platform(), _register_switch_services()
│   ├── base.py             # Neviweb130Switch base class
│   └── subclasses.py       # PowerSwitch, WifiPowerSwitch, TankPowerSwitch,
│                           # WifiTankPowerSwitch, ControlerSwitch
│
├── valve/                  # Sedna valve platform
│   ├── __init__.py         # async_setup_platform(), _register_valve_services()
│   ├── base.py             # Neviweb130Valve base class
│   └── subclasses.py       # WifiValve, MeshValve, WifiMeshValve
│
├── sensor/                 # Gateway sensor / leak detector / tank monitor platform
│   ├── __init__.py         # async_setup_platform()
│   ├── base.py             # Neviweb130Sensor base class
│   └── subclasses.py       # ConnectedSensor, TankSensor, GatewaySensor,
│                           # NeviwebDailyRequestSensor
│
├── light.py                # Light switch / dimmer platform (entry point + classes)
├── update.py               # OTA update entity
├── const.py                # All ATTR_*, SERVICE_*, CONF_*, MODE_* constants
├── schema.py               # voluptuous schemas for configuration.yaml and services
└── helpers.py              # Logger setup, request counter, safe_get_device_attributes
```

**Approximate file sizes after refactor:**

| File | Lines |
|---|---|
| `__init__.py` | ~2160 |
| `api/client.py` | ~1875 |
| `climate/__init__.py` | ~1775 |
| `climate/base.py` | ~1615 |
| `climate/heatcool.py` | ~1260 |
| `light.py` | ~1215 |
| `climate/wifi.py` | ~1160 |
| `sensor/base.py` | ~1155 |
| `climate/zigbee.py` | ~845 |
| `valve/base.py` | ~840 |
| `climate/heatpump.py` | ~805 |
| `switch/base.py` | ~790 |
| `switch/subclasses.py` | ~775 |
| `climate/mixins.py` | ~770 |

No file exceeds ~1875 lines. The previous monolith (`climate.py` at 7279 lines) is now split across 7 focused files.

---

## Home Assistant Entry Points

### 1. `setup(hass, hass_config)` — `__init__.py`

Called by HA when the `neviweb130:` key is found in `configuration.yaml`.

```
configuration.yaml
      │
      ▼
setup(hass, hass_config)              ← __init__.py
  ├─ _apply_global_config()           ← sets SCAN_INTERVAL, HOMEKIT_MODE, STAT_INTERVAL, NOTIFY, safe_mode
  ├─ Neviweb130Data.__init__()        ← creates one Neviweb130Client per account
  ├─ migrate_entity_unique_id()       ← int → str unique_id migration (async job)
  ├─ _schedule_version_check()        ← fetches latest GitHub tag (async task)
  └─ discovery.load_platform() × 6
        climate / light / switch / sensor / valve / update
```

Global configuration values are extracted by `_apply_global_config()` and stored as module-level globals imported by the platform files.

### 2. `async_setup_platform(hass, config, async_add_entities, discovery_info)` — per platform

Each platform's `__init__.py` exposes this coroutine. HA calls it after `discovery.load_platform()`.

**climate flow (climate/__init__.py):**
```
async_setup_platform()
  ├─ await data.migration_done.wait()
  ├─ _build_climate_entities() per client / gateway_data[1-3]
  │     └─ match device_info["signature"]["model"] → instantiate correct subclass
  ├─ async_add_entities(entities, True)
  └─ _register_climate_services(hass, entities)   ← ~50 services registered here
```

Service registration is separated from entity creation into `_register_climate_services()` (SRP). The same pattern applies to `switch/__init__.py` (`_register_switch_services`), `valve/__init__.py` (`_register_valve_services`), and `light.py` (`_register_light_services`).

### 3. `update()` — entity method (sync, called by HA polling)

HA calls `entity.update()` on every entity at the configured `scan_interval`. The method is decomposed into focused private helpers:

```
entity.update()
  ├─ _fetch_attributes()                           ← GET /api/device/{id}/attribute
  ├─ client.get_neviweb_status(location_id)        ← GET /api/location/{id}/notifications
  ├─ _handle_error(device_data)                    ← dispatches via ERROR_HANDLERS dict
  ├─ _parse_common_state(device_data)              ← assigns temperature, mode, etc.
  ├─ _parse_dr_state(device_data)                  ← assigns DR setpoint/status fields
  ├─ do_stat(start)                                ← energy stats (every STAT_INTERVAL)
  │     ├─ _fetch_monthly_stats()
  │     ├─ _fetch_daily_stats()
  │     └─ _fetch_hourly_stats()
  ├─ get_sensor_error_code()
  └─ get_weather()
```

### 4. HA ClimateEntity interface methods

| HA method | What it does |
|---|---|
| `set_temperature(**kwargs)` | Sets heating setpoint → `client.set_temperature()` |
| `set_hvac_mode(hvac_mode)` | Changes operating mode → `client.set_setpoint_mode()` |
| `set_preset_mode(preset_mode)` | Sets away/home preset → `client.set_occupancy_mode()` |
| `set_fan_mode(speed)` | Sets fan speed (heat pumps only) → `client.set_fan_mode()` |
| `set_swing_mode(swing)` | Sets vertical swing (heat pumps only) |
| `set_swing_horizontal_mode(swing)` | Sets horizontal swing (heat pumps only) |
| `turn_on()` / `turn_off()` | Sets mode to HEAT / OFF → `client.set_setpoint_mode()` |

### 5. Custom HA Services (climate platform)

All registered in `_register_climate_services()` via `hass.services.async_register()`.

| Service name | Description |
|---|---|
| `set_second_display` | Switch 2nd display between setpoint / outdoor temp |
| `set_backlight` | Set backlight mode (on / auto / bedroom) |
| `set_climate_keypad_lock` | Lock / unlock keypad |
| `set_time_format` | 12h or 24h clock |
| `set_temperature_format` | Celsius or Fahrenheit |
| `set_setpoint_min` / `set_setpoint_max` | Heating setpoint limits |
| `set_cool_setpoint_min` / `set_cool_setpoint_max` | Cooling setpoint limits |
| `set_floor_limit_low` / `set_floor_limit_high` | Floor sensor temperature limits |
| `set_floor_air_limit` | Max air temperature for floor thermostats |
| `set_air_floor_mode` | Switch between floor / ambient sensor |
| `set_early_start` | Early heating on/off (Wi-Fi) |
| `set_hvac_dr_options` | Eco-Sinopé demand-response options |
| `set_hvac_dr_setpoint` | Eco-Sinopé setpoint delta |
| `set_auxiliary_load` | Auxiliary output wattage |
| `set_aux_cycle_output` | Auxiliary cycle length (low-voltage) |
| `set_cycle_output` | Main cycle length (low-voltage) |
| `set_pump_protection` | Pump protection on/off |
| `set_em_heat` | Emergency heat on/off |
| `set_sensor_type` | Floor sensor type (10k / 12k) |
| `set_activation` | Enable / disable polling for a device |
| `set_heat_pump_operation_limit` | Min temp for heat pump operation |
| `set_heat_lockout_temperature` | Max outside temp to allow heating |
| `set_cool_lockout_temperature` | Min outside temp to allow cooling |
| `set_display_config` | Display on/off (heat pump) |
| `set_sound_config` | Sound on/off (heat pump) |
| `set_hc_second_display` | 2nd display for TH1134ZB-HC |
| `set_language` | Display language for TH1134ZB-HC |
| `set_room_setpoint_away` | Away heating setpoint |
| `set_cool_setpoint_away` | Away cooling setpoint (TH6xxxWF) |
| `set_schedule_mode` | Schedule mode manual/auto (TH6xxxWF) |
| `set_heatcool_setpoint_delta` | Heat/cool delta (TH6xxxWF) |
| `set_fan_filter_reminder` | Fan filter reminder period (TH6xxxWF) |
| `set_temperature_offset` | Temperature sensor offset (TH6xxxWF) |
| `set_aux_heating_source` | Auxiliary heating source type (TH6xxxWF) |
| `set_fan_speed` | Fan speed on/auto (TH6xxxWF) |
| `set_humidity_mode` | Humidity setpoint mode (TH6xxxWF) |
| `set_heat_dissipation_time` | Heating purge time (TH6xxxWF) |
| `set_cool_dissipation_time` | Cooling purge time (TH6xxxWF) |
| `set_reversing_valve_polarity` | Reversing valve polarity (TH6xxxWF) |
| `set_min_time_on` / `set_min_time_off` | Min on/off times (TH6xxxWF) |
| `set_heat_interstage_delay` / `set_cool_interstage_delay` | Interstage delays (TH6xxxWF) |
| `set_aux_heat_start_delay` | Aux heat start delay (TH6xxxWF) |
| `set_accessory_type` | Humidifier/dehumidifier/air-exchanger type (TH6xxxWF) |
| `set_heat_installation_type` | Heater installation type (TH6xxxWF) |
| `set_climate_neviweb_status` | Global Neviweb home/away mode |

---

## Component Class Hierarchy

### Core data classes (`__init__.py`)

```
Neviweb130Data
  └─ neviweb130_clients: list[Neviweb130Client]

Neviweb130Client                        (__init__.py)
  # --- Session / Auth ---
  ├─ __post_login_page()      → POST /api/login
  ├─ reconnect()              → re-runs login + discovery
  # --- Network Discovery ---
  ├─ __get_network()          → GET  /api/locations?account$id=
  ├─ __get_gateway_data()     → GET  /api/devices?location$id=
  # --- Attribute I/O ---
  ├─ get_device_attributes()  → GET  /api/device/{id}/attribute
  ├─ set_device_attributes()  → PUT  /api/device/{id}/attribute
  ├─ _do_get()                → shared HTTP GET helper
  ├─ _do_put()                → shared HTTP PUT helper
  └─ _handle_response_error() → centralised error checking
  # --- Energy Statistics ---
  ├─ get_device_monthly_stats()
  ├─ get_device_daily_stats()
  └─ get_device_hourly_stats()
```

### Climate entity hierarchy (`climate/`)

All thermostat classes extend HA's `ClimateEntity`. Capability-specific methods live in mixins rather than the base class (ISP).

```
homeassistant.components.climate.ClimateEntity
└── Neviweb130Thermostat                    (climate/base.py — TH1123ZB, TH1124ZB)
    │
    │   ┌─ FloorMixin          (climate/mixins.py)
    │   │   set_floor_limit, set_air_floor_mode, set_floor_air_limit, set_sensor_type
    │   ├─ LowVoltageMixin     (climate/mixins.py)
    │   │   set_pump_protection, set_aux_cycle_output, set_cycle_output
    │   ├─ HeatPumpMixin       (climate/mixins.py)
    │   │   set_fan_mode, set_swing_mode, set_display_config, set_sound_config, ...
    │   └─ HeatCoolMixin       (climate/mixins.py)
    │       set_schedule_mode, set_heatcool_setpoint_delta, set_fan_speed, ...
    │
    ├── Neviweb130G2Thermostat              (climate/zigbee.py — TH1123ZB-G2, TH1124ZB-G2)
    ├── Neviweb130FloorThermostat           (climate/zigbee.py — FloorMixin)
    ├── Neviweb130LowThermostat             (climate/zigbee.py — LowVoltageMixin)
    ├── Neviweb130DoubleThermostat          (climate/zigbee.py — TH1500ZB)
    ├── Neviweb130HcThermostat              (climate/heatcool.py — TH1134ZB-HC)
    ├── Neviweb130HPThermostat              (climate/heatpump.py — HeatPumpMixin)
    ├── Neviweb130WifiHPThermostat          (climate/heatpump.py — HeatPumpMixin)
    ├── Neviweb130WifiThermostat            (climate/wifi.py — TH1123WF, TH1124WF, TH1500WF)
    ├── Neviweb130WifiFloorThermostat       (climate/wifi.py — FloorMixin)
    ├── Neviweb130LowWifiThermostat         (climate/wifi.py — LowVoltageMixin)
    ├── Neviweb130WifiLiteThermostat        (climate/wifi.py — TH1133WF/CR, TH1134WF/CR)
    ├── Neviweb130ColorWifiThermostat       (climate/wifi.py — TH1143WF, TH1144WF)
    └── Neviweb130HeatCoolThermostat        (climate/heatcool.py — HeatCoolMixin)
```

**Model number → class mapping:**

| Model numbers | Class | Module |
|---|---|---|
| 1123, 1124 | `Neviweb130Thermostat` | `climate/base.py` |
| 300 | `Neviweb130G2Thermostat` | `climate/zigbee.py` |
| 737 | `Neviweb130FloorThermostat` | `climate/zigbee.py` |
| 7372 | `Neviweb130LowThermostat` | `climate/zigbee.py` |
| 7373 | `Neviweb130DoubleThermostat` | `climate/zigbee.py` |
| 1512 | `Neviweb130HcThermostat` | `climate/heatcool.py` |
| 6810, 6811, 6812 | `Neviweb130HPThermostat` | `climate/heatpump.py` |
| 1510, 742 | `Neviweb130WifiThermostat` | `climate/wifi.py` |
| 738 | `Neviweb130WifiFloorThermostat` | `climate/wifi.py` |
| 739 | `Neviweb130LowWifiThermostat` | `climate/wifi.py` |
| 336, 343, 348 | `Neviweb130WifiLiteThermostat` | `climate/wifi.py` |
| 350 | `Neviweb130ColorWifiThermostat` | `climate/wifi.py` |
| 6813, 6814 | `Neviweb130WifiHPThermostat` | `climate/heatpump.py` |
| 6727, 6730, 6731 | `Neviweb130HeatCoolThermostat` | `climate/heatcool.py` |

### Other platform hierarchies

```
homeassistant.components.light.LightEntity
└── Neviweb130Light          (light.py — SW2500ZB, DM2500ZB, DM2550ZB and variants)
    ├── Neviweb130Dimmer
    └── Neviweb130NewDimmer

homeassistant.components.switch.SwitchEntity
└── Neviweb130Switch         (switch/base.py — SP2610ZB, SP2600ZB and -VA variants)
    ├── Neviweb130PowerSwitch          (switch/subclasses.py — RM3250ZB)
    ├── Neviweb130WifiPowerSwitch      (switch/subclasses.py — RM3250WF)
    ├── Neviweb130TankPowerSwitch      (switch/subclasses.py — RM3500ZB)
    ├── Neviweb130WifiTankPowerSwitch  (switch/subclasses.py — RM3500WF, RM3510WF)
    └── Neviweb130ControlerSwitch      (switch/subclasses.py — MC3100ZB)

homeassistant.components.valve.ValveEntity
└── Neviweb130Valve          (valve/base.py — VA4200/4201/4220/4221 ZB/WF)
    ├── Neviweb130WifiValve            (valve/subclasses.py)
    ├── Neviweb130MeshValve            (valve/subclasses.py)
    └── Neviweb130WifiMeshValve        (valve/subclasses.py)

homeassistant.helpers.entity.Entity
└── Neviweb130Sensor         (sensor/base.py — GT130 gateway, LM4110-ZB, WL42xx)
    ├── Neviweb130ConnectedSensor      (sensor/subclasses.py — leak detectors)
    ├── Neviweb130TankSensor           (sensor/subclasses.py — propane tank monitors)
    └── Neviweb130GatewaySensor        (sensor/subclasses.py — GT130 gateway sensor)
└── NeviwebDailyRequestSensor (sensor/subclasses.py — daily API request counter)

homeassistant.components.update.UpdateEntity
└── Neviweb130Update         (update.py — checks GitHub tags for new releases)
```

---

## SOLID Design Principles Applied

The refactor enforced the following structural invariants:

### Single Responsibility Principle

- `update()` on every entity is a ≤ 30-line orchestrator delegating to `_fetch_attributes()`, `_parse_common_state()`, `_parse_dr_state()`, `_handle_error()`.
- `do_stat()` delegates to `_fetch_monthly_stats()`, `_fetch_daily_stats()`, `_fetch_hourly_stats()`, `_record_stat()`.
- `async_setup_platform()` only creates entities and calls `async_add_entities()`. All service registration is in `_register_*_services()`.
- `setup()` in `__init__.py` delegates to `_wire_accounts()`, `_apply_global_config()`, `_schedule_version_check()`.
- `Neviweb130Client` methods are grouped into clearly bounded sections: Session/Auth, Network Discovery, Attribute I/O, Energy Statistics.

### Open/Closed Principle

- `log_error()` dispatches via a module-level `ERROR_HANDLERS: dict[str, Callable]` lookup table instead of a flat if/elif chain. Adding a new error code requires only adding an entry to the dict.

### Interface Segregation Principle

- Heat-pump-specific methods (`set_fan_mode`, `set_swing_mode`, etc.) live only in `HeatPumpMixin`, applied to `Neviweb130HPThermostat` and `Neviweb130WifiHPThermostat`.
- Floor-specific methods (`set_floor_limit`, `set_air_floor_mode`, etc.) live only in `FloorMixin`, applied to floor thermostat subclasses.
- Low-voltage methods (`set_pump_protection`, `set_aux_cycle_output`, etc.) live only in `LowVoltageMixin`.
- Heat/cool-specific methods live only in `HeatCoolMixin`, applied to `Neviweb130HeatCoolThermostat`.
- `Neviweb130WifiThermostat` does **not** inherit floor or low-voltage methods.

---

## Sinopé API Reference

Base URL: `https://neviweb.com/api`

All requests after login carry:
- Header: `Session-Id: <session_token>`
- Cookie jar maintained across requests

### Authentication

#### POST `/api/login`

**Request body:**
```json
{
  "username": "user@example.com",
  "password": "secret",
  "interface": "neviweb",
  "stayConnected": 1
}
```

**Response (200):**
```json
{
  "session": "<session_token>",
  "account": { "id": 12345 }
}
```

**Error codes:** `USRBADLOGIN`, `ACCSESSEXC`

---

### Locations (Networks)

#### GET `/api/locations?account$id={account_id}`

Returns all locations for the account. Used to resolve network names to numeric gateway IDs.

---

### Device Discovery

#### GET `/api/devices?location$id={location_id}`

Returns all devices registered under a location. The `signature.model` integer selects the entity class.

```json
{
  "id": 111222,
  "name": "Living Room",
  "sku": "TH1123ZB",
  "location$id": 67890,
  "signature": {
    "model": 1123,
    "modelCfg": 0,
    "softVersion": { "major": 1, "middle": 2, "minor": 3 }
  }
}
```

---

### Device Attributes

#### GET `/api/device/{device_id}/attribute?attributes={attr1},{attr2},...`

Reads one or more attributes in a single request.

**Common error codes in response:**

| Code | Meaning |
|---|---|
| `USRSESSEXP` | Session expired — call `client.reconnect()` |
| `DVCATTRNSPTD` | Attribute not supported by this device |
| `DVCACTNSPTD` | Action not supported |
| `DVCCOMMTO` | Device communication timeout |
| `DVCUNVLB` | Device unavailable (offline) — sets `_active = False` |
| `DVCBUSY` | Device busy |
| `ACCDAYREQMAX` | Daily request limit reached (30 000/day) |

#### PUT `/api/device/{device_id}/attribute`

Writes one or more attributes. Retried up to 3 times on error.

---

### Energy Statistics

| Endpoint | Description |
|---|---|
| `GET /api/device/{id}/consumption/hourly` | Last 24 hours in Wh/hour |
| `GET /api/device/{id}/consumption/daily` | Last 30 days in Wh/day |
| `GET /api/device/{id}/consumption/monthly` | Last 24 months in Wh/month |

HC variant (TH6xxxWF): `/energy/hourly`, `/energy/daily`, `/energy/monthly` — returns dict keyed by mode (`heat`, `cool`).

---

### Location Status

#### GET `/api/location/{location_id}/notifications`
Returns `{ "occupancyMode": "home" }`.

#### POST `/api/location/{location_id}/mode`
Sets global occupancy mode: `{ "mode": "away" }`.

---

### Weather

#### GET `/api/weather?code={postalCode}`
Returns `{ "temperature": -5.0, "icon": 3 }`.

---

## Data Flow

```
Home Assistant startup
        │
        ▼
setup() — __init__.py
        ├─ _apply_global_config()
        ├─ Neviweb130Client.__post_login_page()   POST /api/login
        ├─ Neviweb130Client.__get_network()        GET  /api/locations
        ├─ Neviweb130Client.__get_gateway_data()   GET  /api/devices
        ├─ _schedule_version_check()
        └─ discovery.load_platform() × 6

        │
        ▼
async_setup_platform() — climate/__init__.py (and switch, valve, sensor, light)
        ├─ _build_*_entities()   ← model → subclass dispatch
        ├─ async_add_entities()
        └─ _register_*_services()

        │
        ▼  (every scan_interval seconds)
entity.update()
        ├─ _fetch_attributes()          GET /api/device/{id}/attribute
        ├─ get_neviweb_status()         GET /api/location/{id}/notifications
        ├─ _handle_error()              → ERROR_HANDLERS dispatch
        ├─ _parse_common_state()
        ├─ _parse_dr_state()
        ├─ do_stat()                    GET /api/device/{id}/consumption/*
        ├─ get_sensor_error_code()
        └─ get_weather()                GET /api/weather?code=

        │
        ▼  (on user action or service call)
entity.set_temperature() / set_hvac_mode() / custom service handler
        └─ PUT /api/device/{id}/attribute  { attribute: value }
```

### Session management

- Session token stored in `Neviweb130Client._headers`; cookies in `_cookies`.
- On `USRSESSEXP`, `client.reconnect()` re-runs login + network + gateway discovery.
- Sessions expire if polling interval exceeds ~10 minutes (`scan_interval` ≤ 600 s recommended).
- Sinopé enforces 30 000 API requests/day per account. The `NeviwebDailyRequestSensor` entity tracks this count.

### Error handling

- `log_error()` on every entity dispatches via `ERROR_HANDLERS` dict (OCP).
- `DVCUNVLB` sets `entity._active = False` and starts a 20-minute snooze; `_handle_snooze()` re-activates after the timeout.
- `DVCATTRNSPTD` auto-enables safe mode for the device, switching to `safe_get_device_attributes()` which fetches attributes one at a time.
- Unknown error codes fall through to a `_LOGGER.warning()` call without raising.
