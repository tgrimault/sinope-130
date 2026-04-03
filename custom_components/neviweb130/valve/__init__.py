"""
Support for Neviweb Zigbee valve connected via GT130 and Wi-Fi valves.

Water valves
model 3150 = VA4201WZ, sedna valve 1 inch via Wi-Fi
model 3150 = VA4200WZ, sedna valve 3/4 inch via Wi-Fi
model 3151 = VA4200ZB, sedna valve 3/4 inch via GT130, Zigbee
model 3153 = VA4220ZB, sedna 2e generation 3/4 inch, Zigbee
model 3150 = VA4220WZ, sedna 2e gen 3/4 inch
model 3155 = ACT4220WF-M, sedna multi-residential master valve 2e gen 3/4 inch, Wi-Fi
model 31532 = ACT4220ZB-M, sedna multi-residential slave valve 2e gen 3/4 inch, Zigbee
model 3150 = VA4220WF, sedna 2e generation 3/4 inch, Wi-Fi
model 3150 = VA4221WZ, sedna 2e gen 1 inch
model 3150 = VA4221WF, sedna 2e generation 1 inch, Wi-Fi
model 3155 = ACT4221WF-M, sedna multi-residential master valve 2e gen. 1 inch, Wi-Fi
model 31532 = ACT4221ZB-M, sedna multi-residential slave valve 2e gen. 1 inch, Zigbee

Flow sensors
FS4220 flow sensor 3/4 inch connected to sedna valve second gen
FS4221 flow sensor 1 inch connected to sedna valve second gen

For more details about this platform, please refer to the documentation at
https://www.sinopetech.com/en/support/#api
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone
from enum import StrEnum
from threading import Lock
from typing import Any, cast, override

from homeassistant.components.persistent_notification import DOMAIN as PN_DOMAIN
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.valve import ValveDeviceClass, ValveEntity, ValveEntityFeature
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import ServiceCall
from homeassistant.exceptions import ServiceValidationError

from .. import NOTIFY
from .. import SCAN_INTERVAL as scan_interval
from .. import STAT_INTERVAL
from ..const import (
    ATTR_ACTIVE,
    ATTR_AWAY_ACTION,
    ATTR_BATT_ACTION_LOW,
    ATTR_BATT_ALERT,
    ATTR_BATT_PERCENT_NORMAL,
    ATTR_BATT_STATUS_NORMAL,
    ATTR_BATTERY_STATUS,
    ATTR_BATTERY_VOLTAGE,
    ATTR_CLOSE_VALVE,
    ATTR_ERROR_CODE_SET1,
    ATTR_FLOW_ALARM1,
    ATTR_FLOW_ALARM1_LENGTH,
    ATTR_FLOW_ALARM1_OPTION,
    ATTR_FLOW_ALARM1_PERIOD,
    ATTR_FLOW_ALARM2,
    ATTR_FLOW_ALARM_TIMER,
    ATTR_FLOW_ENABLED,
    ATTR_FLOW_METER_CONFIG,
    ATTR_FLOW_MODEL_CONFIG,
    ATTR_FLOW_THRESHOLD,
    ATTR_MOTOR_POS,
    ATTR_MOTOR_TARGET,
    ATTR_OCCUPANCY_SENSOR_DELAY,
    ATTR_ONOFF,
    ATTR_POWER_SUPPLY,
    ATTR_RSSI,
    ATTR_STM8_ERROR,
    ATTR_TEMP_ACTION_LOW,
    ATTR_TEMP_ALARM,
    ATTR_TEMP_ALERT,
    ATTR_TRIGGER_ALARM,
    ATTR_VALVE_CLOSURE,
    ATTR_VALVE_INFO,
    ATTR_WATER_LEAK_STATUS,
    ATTR_WIFI,
    DOMAIN,
    MODE_AUTO,
    MODE_MANUAL,
    MODE_OFF,
    SERVICE_SET_ACTIVATION,
    SERVICE_SET_FLOW_ALARM_DISABLE_TIMER,
    SERVICE_SET_FLOW_METER_DELAY,
    SERVICE_SET_FLOW_METER_MODEL,
    SERVICE_SET_FLOW_METER_OPTIONS,
    SERVICE_SET_POWER_SUPPLY,
    SERVICE_SET_VALVE_ALERT,
    SERVICE_SET_VALVE_TEMP_ALERT,
    STATE_VALVE_STATUS,
    VERSION,
)
from ..helpers import file_exists, safe_get_device_attributes, translated_or_default
from ..schema import (
    SET_ACTIVATION_SCHEMA,
    SET_FLOW_ALARM_DISABLE_TIMER_SCHEMA,
    SET_FLOW_METER_DELAY_SCHEMA,
    SET_FLOW_METER_MODEL_SCHEMA,
    SET_FLOW_METER_OPTIONS_SCHEMA,
    SET_POWER_SUPPLY_SCHEMA,
    SET_VALVE_ALERT_SCHEMA,
    SET_VALVE_TEMP_ALERT_SCHEMA,
)

_LOGGER = logging.getLogger(__name__)

SNOOZE_TIME = 1200
SCAN_INTERVAL = scan_interval

SUPPORT_FLAGS = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE

UPDATE_ATTRIBUTES = [ATTR_ONOFF]

HA_TO_NEVIWEB_DELAY = {
    "off": 0,
    "1 min": 60,
    "2 min": 120,
    "5 min": 300,
    "10 min": 600,
    "15 min": 900,
    "30 min": 1800,
    "45 min": 2700,
    "60 min": 3600,
    "75 min": 4500,
    "90 min": 5400,
    "1 h": 3600,
    "2 h": 7200,
    "3 h": 10800,
    "6 h": 21600,
    "12 h": 43200,
    "24 h": 86400,
    "48 h": 172800,
    "1 week": 604800,
}

VALVE_TYPES: dict[str, tuple[str, StrEnum, str | None, str | None, StatisticMeanType | None]] = {
    "flow": ("mdi:pipe-valve", SensorDeviceClass.WATER, None, "volume_flow_rate", StatisticMeanType.ARITHMETIC),
    "valve": ("mdi:pipe-valve", ValveDeviceClass.WATER, None, None, None),
}

SUPPORTED_WIFI_MODES = [
    MODE_AUTO,
    MODE_MANUAL,
    MODE_OFF,
]

IMPLEMENTED_WIFI_MESH_VALVE_MODEL = [3155]
IMPLEMENTED_ZB_MESH_VALVE_MODEL = [3153, 31532]
IMPLEMENTED_WIFI_VALVE_MODEL = [3150]
IMPLEMENTED_ZB_VALVE_MODEL = [3151]

IMPLEMENTED_DEVICE_MODEL = (
    IMPLEMENTED_WIFI_VALVE_MODEL
    + IMPLEMENTED_ZB_VALVE_MODEL
    + IMPLEMENTED_WIFI_MESH_VALVE_MODEL
    + IMPLEMENTED_ZB_MESH_VALVE_MODEL
)


def _build_valve_entities(gateway_data: list, group_name: str, client: Any) -> list:
    """Instantiate valve entities for one gateway data list."""
    result = []
    for device_info in gateway_data:
        if not (
            "signature" in device_info
            and "model" in device_info["signature"]
            and device_info["signature"]["model"] in IMPLEMENTED_DEVICE_MODEL
        ):
            continue
        device_name = "{} {}".format(group_name, device_info["name"])
        device_sku = device_info["sku"]
        sv = device_info["signature"]["softVersion"]
        device_firmware = "{}.{}.{}".format(sv["major"], sv["middle"], sv["minor"])
        model = device_info["signature"]["model"]
        if model in IMPLEMENTED_ZB_VALVE_MODEL:
            result.append(Neviweb130Valve(device_info, device_name, device_sku, device_firmware, "valve", client))
        elif model in IMPLEMENTED_WIFI_VALVE_MODEL:
            result.append(Neviweb130WifiValve(device_info, device_name, device_sku, device_firmware, "valve", client))
        elif model in IMPLEMENTED_ZB_MESH_VALVE_MODEL:
            result.append(Neviweb130MeshValve(device_info, device_name, device_sku, device_firmware, "flow", client))
        else:
            result.append(Neviweb130WifiMeshValve(device_info, device_name, device_sku, device_firmware, "flow", client))
    return result


async def async_setup_platform(
    hass,
    config,
    async_add_entities,
    discovery_info=None,
) -> None:
    """Set up the Neviweb130 valve."""
    data = hass.data[DOMAIN]["data"]

    # Wait for async migration to be done
    await data.migration_done.wait()

    entities: list[Neviweb130Valve] = []

    for client in data.neviweb130_clients:
        entities.extend(_build_valve_entities(
            client.gateway_data, client.default_group_name("valve"), client
        ))
        entities.extend(_build_valve_entities(
            client.gateway_data2, client.default_group_name("valve", 2), client
        ))
        entities.extend(_build_valve_entities(
            client.gateway_data3, client.default_group_name("valve", 3), client
        ))

    async_add_entities(entities, True)
    _register_valve_services(hass, entities)


def _register_valve_services(hass: Any, entities: list) -> None:
    """Register all valve services with Home Assistant."""
    entity_map: dict[str, Neviweb130Valve] | None = None
    _entity_map_lock = Lock()

    def get_valve(service: ServiceCall) -> Neviweb130Valve:
        entity_id = service.data.get(ATTR_ENTITY_ID)
        if entity_id is None:
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "missing_parameter",
                    f"Missing required parameter: {ATTR_ENTITY_ID}.",
                    param=ATTR_ENTITY_ID,
                )
            )

        nonlocal entity_map
        if entity_map is None:
            with _entity_map_lock:
                if entity_map is None:
                    entity_map = {entity.entity_id: entity for entity in entities if entity.entity_id is not None}
                    if len(entity_map) != len(entities):
                        entity_map = None
                        raise ServiceValidationError(
                            translated_or_default(
                                hass,
                                "entities_not_ready",
                                "Entities not finished loading, try again shortly.",
                            )
                        )

        valve = entity_map.get(entity_id)
        if valve is None:
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "entity_must_be_domain",
                    f"Entity {entity_id} must be a {DOMAIN} valve.",
                    entity=entity_id,
                    domain=DOMAIN,
                    platform="valve",
                )
            )
        return valve

    def set_valve_alert_service(service: ServiceCall) -> None:
        """Set alert for water valve."""
        valve = get_valve(service)
        value = {"id": valve.unique_id, "batt": service.data[ATTR_BATT_ALERT]}
        valve.set_valve_alert(value)
        valve.schedule_update_ha_state(True)

    def set_valve_temp_alert_service(service: ServiceCall) -> None:
        """Set alert for water valve temperature location."""
        valve = get_valve(service)
        value = {"id": valve.unique_id, "temp": service.data[ATTR_TEMP_ALERT]}
        valve.set_valve_temp_alert(value)
        valve.schedule_update_ha_state(True)

    def set_flow_meter_model_service(service: ServiceCall) -> None:
        """Set the flow meter model connected to water valve."""
        valve = get_valve(service)
        value = {"id": valve.unique_id, "model": service.data[ATTR_FLOW_MODEL_CONFIG][0]}
        valve.set_flow_meter_model(value)
        valve.schedule_update_ha_state(True)

    def set_flow_meter_delay_service(service: ServiceCall) -> None:
        """Set the flow meter delay before alert is turned on."""
        valve = get_valve(service)
        value = {"id": valve.unique_id, "delay": service.data[ATTR_FLOW_ALARM1_PERIOD][0]}
        valve.set_flow_meter_delay(value)
        valve.schedule_update_ha_state(True)

    def set_flow_meter_options_service(service: ServiceCall) -> None:
        """Set the flow meter options when leak is detected."""
        valve = get_valve(service)
        value = {
            "id": valve.unique_id,
            "alarm": service.data[ATTR_TRIGGER_ALARM],
            "close": service.data[ATTR_CLOSE_VALVE],
        }
        valve.set_flow_meter_options(value)
        valve.schedule_update_ha_state(True)

    def set_power_supply_service(service: ServiceCall) -> None:
        """Set power supply type for water valve."""
        valve = get_valve(service)
        value = {"id": valve.unique_id, "supply": service.data[ATTR_POWER_SUPPLY]}
        valve.set_power_supply(value)
        valve.schedule_update_ha_state(True)

    def set_activation_service(service: ServiceCall) -> None:
        """Activate or deactivate Neviweb polling for missing device."""
        valve = get_valve(service)
        value = {"id": valve.unique_id, "active": service.data[ATTR_ACTIVE]}
        valve.set_activation(value)
        valve.schedule_update_ha_state(True)

    def set_flow_alarm_disable_timer_service(service: ServiceCall) -> None:
        """Set flow alarm disable timer for water valve."""
        valve = get_valve(service)
        value = {"id": valve.unique_id, "timer": service.data[ATTR_FLOW_ALARM_TIMER]}
        valve.set_flow_alarm_disable_timer(value)
        valve.schedule_update_ha_state(True)

    hass.services.async_register(
        DOMAIN, SERVICE_SET_VALVE_ALERT, set_valve_alert_service, schema=SET_VALVE_ALERT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_VALVE_TEMP_ALERT, set_valve_temp_alert_service, schema=SET_VALVE_TEMP_ALERT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_FLOW_METER_MODEL, set_flow_meter_model_service, schema=SET_FLOW_METER_MODEL_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_FLOW_METER_DELAY, set_flow_meter_delay_service, schema=SET_FLOW_METER_DELAY_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_FLOW_METER_OPTIONS, set_flow_meter_options_service, schema=SET_FLOW_METER_OPTIONS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_POWER_SUPPLY, set_power_supply_service, schema=SET_POWER_SUPPLY_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_FLOW_ALARM_DISABLE_TIMER, set_flow_alarm_disable_timer_service, schema=SET_FLOW_ALARM_DISABLE_TIMER_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SET_ACTIVATION, set_activation_service, schema=SET_ACTIVATION_SCHEMA,
    )


def voltage_to_percentage(voltage, num):
    """Convert voltage level from volt to percentage."""
    if num == 2:
        return int((min(voltage, 2.7) - 2.3) / (2.7 - 2.3) * 100)
    else:
        return int((min(voltage, 6.0) - 3.0) / (6.0 - 3.0) * 100)


def alert_to_text(alert, value):
    """Convert numeric alert activation to text."""
    if alert == 1:
        match value:
            case "bat":
                return "Active"
            case "temp":
                return "Active"
    else:
        match value:
            case "bat":
                return "Off"
            case "temp":
                return "Off"

    return None


def neviweb_to_ha_delay(value):
    """Convert Neviweb values to HA values."""
    keys = [k for k, v in HA_TO_NEVIWEB_DELAY.items() if v == value]
    if keys:
        return keys[0]
    return None


def trigger_close(action, alarm):
    """ "No action", "Close and send", "Close only", "Send only." """
    if action:
        if alarm:
            return "Close and send"
        else:
            return "Close only"
    else:
        if alarm:
            return "Send only"
        else:
            return "No action"


def L_2_sqm(value):
    """Convert liters valuer to cubic meter for water flow stat."""
    if value is not None:
        return round(value / 1000, 5)
    else:
        return None


def model_to_HA(value):
    if value == 9887:
        return "FS4221"
    elif value == 4546:
        return "FS4220"
    else:
        return "No flow meter"



# Re-export classes from sub-modules for backward compatibility
from .base import (  # noqa: E402
    Neviweb130Valve,
    SNOOZE_TIME,
    SCAN_INTERVAL,
    UPDATE_ATTRIBUTES,
    SUPPORTED_WIFI_MODES,
    IMPLEMENTED_WIFI_MESH_VALVE_MODEL,
    IMPLEMENTED_ZB_MESH_VALVE_MODEL,
    IMPLEMENTED_WIFI_VALVE_MODEL,
    IMPLEMENTED_ZB_VALVE_MODEL,
    IMPLEMENTED_DEVICE_MODEL,
    lock_to_ha,
    L_2_sqm,
    model_to_HA,
)
from .subclasses import (  # noqa: E402
    Neviweb130WifiValve,
    Neviweb130MeshValve,
    Neviweb130WifiMeshValve,
)
