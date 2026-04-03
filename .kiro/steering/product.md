# Product: Sinope Neviweb130

A Home Assistant custom integration (HACS-compatible) for managing Sinopé smart devices via the Neviweb cloud portal.

## What it does
- Polls the Neviweb REST API (`https://neviweb.com/api/`) to control and monitor Sinopé devices
- Supports Zigbee devices connected via a GT130 gateway, and Wi-Fi devices connected directly to Neviweb
- Exposes devices as standard HA entities: `climate`, `light`, `switch`, `valve`, `sensor`, `update`

## Supported device categories
- Thermostats (Zigbee line/floor/low-voltage, Wi-Fi, heat pumps, heat/cool)
- Light switches and dimmers
- Load controllers, smart plugs, multi-controllers
- Sedna water valves and water leak detectors
- Propane tank level monitors
- GT130 gateway sensor and daily API request counter

## Key constraints
- Cloud-polling only — no local communication
- Sinopé enforces a 30,000 API requests/day limit per account
- `scan_interval` must stay ≤ 600 s (session expires beyond ~10 min idle)
- Legacy YAML-configured integration (no config flow UI)
- Minimum Home Assistant version: 2025.1.1
