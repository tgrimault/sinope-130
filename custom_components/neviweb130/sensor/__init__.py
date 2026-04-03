"""
Support for Neviweb sensors connected via GT130 Zigbee.
model 5051 = WL4200, WL4200C and WL4200S water leak detector connected to GT130.
model 5053 = WL4200C, perimeter cable water leak detector connected to GT130 (will be removed).
model 5050 = WL4200, WL4210 and WL4200S, water leak detector connected to Sedna valve.
model 5052 = WL4200C, perimeter cable water leak detector connected to sedna 2 gen.
model 4210 = WL4210, WL4210S connected to GT130.
model 42102 = WL4210, WL4210S connected to sedna valve.
model 5056 = LM4110-ZB, level monitor (SE500ZB).
model 5055 = LM4110-LTE, level monitor (SE5000), multiples tanks.
model 130 = gateway GT130.
model 3156 = gateway GT4220WF, GT4220WF-M for mesh valve network.
For more details about this platform, please refer to the documentation at
https://www.sinopetech.com/en/support/#api
"""

from __future__ import annotations

import datetime
import logging
import time
from threading import Lock
from typing import cast, override

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.persistent_notification import DOMAIN as PN_DOMAIN
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import ATTR_ENTITY_ID, PERCENTAGE
from homeassistant.core import ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity import Entity

from .. import NOTIFY
from .. import SCAN_INTERVAL as scan_interval
from ..const import (
    ATTR_ACTIVE,
    ATTR_ANGLE,
    ATTR_BATT_ALERT,
    ATTR_BATT_PERCENT_NORMAL,
    ATTR_BATT_STATUS_NORMAL,
    ATTR_BATTERY_STATUS,
    ATTR_BATTERY_TYPE,
    ATTR_BATTERY_VOLTAGE,
    ATTR_CONF_CLOSURE,
    ATTR_ERROR_CODE_SET1,
    ATTR_FUEL_ALERT,
    ATTR_FUEL_PERCENT_ALERT,
    ATTR_GAUGE_TYPE,
    ATTR_LEAK_ALERT,
    ATTR_MODE,
    ATTR_OCCUPANCY,
    ATTR_REFUEL,
    ATTR_ROOM_TEMP_ALARM,
    ATTR_ROOM_TEMPERATURE,
    ATTR_RSSI,
    ATTR_SAMPLING,
    ATTR_SENSOR_TYPE,
    ATTR_STATUS,
    ATTR_TANK_HEIGHT,
    ATTR_TANK_PERCENT,
    ATTR_TANK_TYPE,
    ATTR_TEMP_ALERT,
    ATTR_WATER_LEAK_STATUS,
    DOMAIN,
    SERVICE_SET_ACTIVATION,
    SERVICE_SET_BATTERY_ALERT,
    SERVICE_SET_BATTERY_TYPE,
    SERVICE_SET_FUEL_ALERT,
    SERVICE_SET_GAUGE_TYPE,
    SERVICE_SET_LOW_FUEL_ALERT,
    SERVICE_SET_NEVIWEB_STATUS,
    SERVICE_SET_REFUEL_ALERT,
    SERVICE_SET_SENSOR_ALERT,
    SERVICE_SET_TANK_HEIGHT,
    SERVICE_SET_TANK_TYPE,
    STATE_WATER_LEAK,
    VERSION,
)
from ..helpers import file_exists, get_daily_request_count, notify_ha, safe_get_device_attributes, translated_or_default
from ..schema import (
    SET_ACTIVATION_SCHEMA,
    SET_BATTERY_ALERT_SCHEMA,
    SET_BATTERY_TYPE_SCHEMA,
    SET_FUEL_ALERT_SCHEMA,
    SET_GAUGE_TYPE_SCHEMA,
    SET_LOW_FUEL_ALERT_SCHEMA,
    SET_NEVIWEB_STATUS_SCHEMA,
    SET_REFUEL_ALERT_SCHEMA,
    SET_SENSOR_ALERT_SCHEMA,
    SET_TANK_HEIGHT_SCHEMA,
    SET_TANK_TYPE_SCHEMA,
)

_LOGGER = logging.getLogger(__name__)

SNOOZE_TIME = 1200
SCAN_INTERVAL = scan_interval

UPDATE_ATTRIBUTES = [ATTR_BATTERY_VOLTAGE, ATTR_BATTERY_STATUS]

IMPLEMENTED_GATEWAY = [130, 3156]
IMPLEMENTED_TANK_MONITOR = [5056]
IMPLEMENTED_LTE_TANK_MONITOR = [5055]
IMPLEMENTED_SENSOR_MODEL = [5051, 5053]
IMPLEMENTED_NEW_SENSOR_MODEL = [4210]
IMPLEMENTED_NEW_CONNECTED_SENSOR = [42102]
IMPLEMENTED_CONNECTED_SENSOR = [5050, 5052]
IMPLEMENTED_DEVICE_MODEL = (
    IMPLEMENTED_SENSOR_MODEL
    + IMPLEMENTED_TANK_MONITOR
    + IMPLEMENTED_LTE_TANK_MONITOR
    + IMPLEMENTED_CONNECTED_SENSOR
    + IMPLEMENTED_GATEWAY
    + IMPLEMENTED_NEW_SENSOR_MODEL
    + IMPLEMENTED_NEW_CONNECTED_SENSOR
)

SENSOR_TYPES: dict[
    str, tuple[str | None, str | None, BinarySensorDeviceClass | SensorStateClass, str | None, StatisticMeanType | None]
] = {
    "leak": (None, None, BinarySensorDeviceClass.MOISTURE, None, None),
    "level": (PERCENTAGE, None, SensorStateClass.MEASUREMENT, "percentage", StatisticMeanType.ARITHMETIC),
    "gateway": (None, None, BinarySensorDeviceClass.CONNECTIVITY, None, None),
}


async def async_setup_platform(
    hass,
    config,
    async_add_entities,
    discovery_info=None,
) -> None:
    """Set up the Neviweb sensor."""
    data = hass.data[DOMAIN]["data"]

    # Wait for async migration to be done
    await data.migration_done.wait()

    entities: list[Entity] = []
    entities.append(NeviwebDailyRequestSensor(hass))

    # Loop through all clients (supports multi-account)
    for client in data.neviweb130_clients:
        default_name = client.default_group_name("sensor")
        default_name_2 = client.default_group_name("sensor", 2)
        default_name_3 = client.default_group_name("sensor", 3)

        # Process gateway_data for this client
        for device_info in client.gateway_data:
            if (
                "signature" in device_info
                and "model" in device_info["signature"]
                and device_info["signature"]["model"] in IMPLEMENTED_DEVICE_MODEL
            ):
                device_name = "{} {}".format(default_name, device_info["name"])
                device_sku = device_info["sku"]
                location_id = device_info["location$id"]
                device_firmware = "{}.{}.{}".format(
                    device_info["signature"]["softVersion"]["major"],
                    device_info["signature"]["softVersion"]["middle"],
                    device_info["signature"]["softVersion"]["minor"],
                )
                if (
                    device_info["signature"]["model"] in IMPLEMENTED_SENSOR_MODEL
                    or device_info["signature"]["model"] in IMPLEMENTED_NEW_SENSOR_MODEL
                ):
                    device_type = "leak"
                    entities.append(
                        Neviweb130Sensor(device_info, device_name, device_type, device_sku, device_firmware, client)
                    )
                elif (
                    device_info["signature"]["model"] in IMPLEMENTED_CONNECTED_SENSOR
                    or device_info["signature"]["model"] in IMPLEMENTED_NEW_CONNECTED_SENSOR
                ):
                    device_type = "leak"
                    entities.append(
                        Neviweb130ConnectedSensor(
                            device_info, device_name, device_type, device_sku, device_firmware, client
                        )
                    )
                elif (
                    device_info["signature"]["model"] in IMPLEMENTED_TANK_MONITOR
                    or device_info["signature"]["model"] in IMPLEMENTED_LTE_TANK_MONITOR
                ):
                    device_type = "level"
                    entities.append(
                        Neviweb130TankSensor(device_info, device_name, device_type, device_sku, device_firmware, client)
                    )
                else:
                    device_type = "gateway"
                    entities.append(
                        Neviweb130GatewaySensor(
                            device_info, device_name, device_type, device_sku, device_firmware, location_id, client
                        )
                    )
        for device_info in client.gateway_data2:
            if (
                "signature" in device_info
                and "model" in device_info["signature"]
                and device_info["signature"]["model"] in IMPLEMENTED_DEVICE_MODEL
            ):
                device_name = "{} {}".format(default_name_2, device_info["name"])
                device_sku = device_info["sku"]
                location_id = device_info["location$id"]
                device_firmware = "{}.{}.{}".format(
                    device_info["signature"]["softVersion"]["major"],
                    device_info["signature"]["softVersion"]["middle"],
                    device_info["signature"]["softVersion"]["minor"],
                )
                if (
                    device_info["signature"]["model"] in IMPLEMENTED_SENSOR_MODEL
                    or device_info["signature"]["model"] in IMPLEMENTED_NEW_SENSOR_MODEL
                ):
                    device_type = "leak"
                    entities.append(
                        Neviweb130Sensor(device_info, device_name, device_type, device_sku, device_firmware, client)
                    )
                elif (
                    device_info["signature"]["model"] in IMPLEMENTED_CONNECTED_SENSOR
                    or device_info["signature"]["model"] in IMPLEMENTED_NEW_CONNECTED_SENSOR
                ):
                    device_type = "leak"
                    entities.append(
                        Neviweb130ConnectedSensor(
                            device_info, device_name, device_type, device_sku, device_firmware, client
                        )
                    )
                elif device_info["signature"]["model"] in IMPLEMENTED_TANK_MONITOR:
                    device_type = "level"
                    entities.append(
                        Neviweb130TankSensor(device_info, device_name, device_type, device_sku, device_firmware, client)
                    )
                else:
                    device_type = "gateway"
                    entities.append(
                        Neviweb130GatewaySensor(
                            device_info, device_name, device_type, device_sku, device_firmware, location_id, client
                        )
                    )
        for device_info in client.gateway_data3:
            if (
                "signature" in device_info
                and "model" in device_info["signature"]
                and device_info["signature"]["model"] in IMPLEMENTED_DEVICE_MODEL
            ):
                device_name = "{} {}".format(default_name_3, device_info["name"])
                device_sku = device_info["sku"]
                location_id = device_info["location$id"]
                device_firmware = "{}.{}.{}".format(
                    device_info["signature"]["softVersion"]["major"],
                    device_info["signature"]["softVersion"]["middle"],
                    device_info["signature"]["softVersion"]["minor"],
                )
                if (
                    device_info["signature"]["model"] in IMPLEMENTED_SENSOR_MODEL
                    or device_info["signature"]["model"] in IMPLEMENTED_NEW_SENSOR_MODEL
                ):
                    device_type = "leak"
                    entities.append(
                        Neviweb130Sensor(device_info, device_name, device_type, device_sku, device_firmware, client)
                    )
                elif (
                    device_info["signature"]["model"] in IMPLEMENTED_CONNECTED_SENSOR
                    or device_info["signature"]["model"] in IMPLEMENTED_NEW_CONNECTED_SENSOR
                ):
                    device_type = "leak"
                    entities.append(
                        Neviweb130ConnectedSensor(
                            device_info, device_name, device_type, device_sku, device_firmware, client
                        )
                    )
                elif device_info["signature"]["model"] in IMPLEMENTED_TANK_MONITOR:
                    device_type = "level"
                    entities.append(
                        Neviweb130TankSensor(device_info, device_name, device_type, device_sku, device_firmware, client)
                    )
                else:
                    device_type = "gateway"
                    entities.append(
                        Neviweb130GatewaySensor(
                            device_info, device_name, device_type, device_sku, device_firmware, location_id, client
                        )
                    )

    async_add_entities(entities, True)

    entity_map: dict[str, Entity] | None = None
    _entity_map_lock = Lock()

    def get_sensor(service: ServiceCall) -> Neviweb130Sensor:
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

        sensor = entity_map.get(entity_id)
        if sensor is None:
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "entity_must_be_domain",
                    f"Entity {entity_id} must be a {DOMAIN} sensor.",
                    entity=entity_id,
                    domain=DOMAIN,
                    platform="sensor",
                )
            )

        if not isinstance(sensor, Neviweb130Sensor):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "entity_must_be_domain",
                    f"Entity {entity_id} must be a {DOMAIN} sensor.",
                    entity=entity_id,
                    domain=DOMAIN,
                    platform="sensor",
                )
            )

        return cast(Neviweb130Sensor, sensor)

    def set_sensor_alert_service(service: ServiceCall) -> None:
        """Set different alert and action for water leak sensor."""
        sensor = get_sensor(service)
        value = {
            "id": sensor.unique_id,
            "leak": service.data[ATTR_LEAK_ALERT],
            "temp": service.data[ATTR_TEMP_ALERT],
            "batt": service.data[ATTR_BATT_ALERT],
            "close": service.data[ATTR_CONF_CLOSURE],
        }
        sensor.set_sensor_alert(value)
        sensor.schedule_update_ha_state(True)

    def set_battery_type_service(service: ServiceCall) -> None:
        """Set battery type for water leak sensor."""
        sensor = get_sensor(service)
        value = {
            "id": sensor.unique_id,
            "type": service.data[ATTR_BATTERY_TYPE],
        }
        sensor.set_battery_type(value)
        sensor.schedule_update_ha_state(True)

    def set_tank_type_service(service: ServiceCall) -> None:
        """Set tank type for fuel tank."""
        sensor = get_sensor(service)
        if not isinstance(sensor, Neviweb130TankSensor):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "cannot_use_entity",
                    f"Entity {sensor.entity_id} cannot be used with this service (action).",
                    entity=sensor.entity_id,
                )
            )
        value = {"id": sensor.unique_id, "type": service.data[ATTR_TANK_TYPE]}
        sensor.set_tank_type(value)
        sensor.schedule_update_ha_state(True)

    def set_gauge_type_service(service: ServiceCall) -> None:
        """Set gauge type for propane tank."""
        sensor = get_sensor(service)
        if not isinstance(sensor, Neviweb130TankSensor):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "entity_must_be_domain",
                    f"Entity {sensor.entity_id} must be a {DOMAIN} tank sensor.",
                    entity=sensor.entity_id,
                    domain=DOMAIN,
                    platform="tank sensor",
                )
            )
        value = {"id": sensor.unique_id, "gauge": service.data[ATTR_GAUGE_TYPE]}
        sensor.set_gauge_type(value)
        sensor.schedule_update_ha_state(True)

    def set_low_fuel_alert_service(service: ServiceCall) -> None:
        """Set low fuel alert on tank, propane or oil."""
        sensor = get_sensor(service)
        if not isinstance(sensor, Neviweb130TankSensor):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "entity_must_be_domain",
                    f"Entity {sensor.entity_id} must be a {DOMAIN} tank sensor.",
                    entity=sensor.entity_id,
                    domain=DOMAIN,
                    platform="tank sensor",
                )
            )
        value = {
            "id": sensor.unique_id,
            "low": service.data[ATTR_FUEL_PERCENT_ALERT],
        }
        sensor.set_low_fuel_alert(value)
        sensor.schedule_update_ha_state(True)

    def set_tank_height_service(service: ServiceCall) -> None:
        """Set tank height for oil tank."""
        sensor = get_sensor(service)
        if not isinstance(sensor, Neviweb130TankSensor):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "entity_must_be_domain",
                    f"Entity {sensor.entity_id} must be a {DOMAIN} tank sensor.",
                    entity=sensor.entity_id,
                    domain=DOMAIN,
                    platform="tank sensor",
                )
            )
        value = {
            "id": sensor.unique_id,
            "height": service.data[ATTR_TANK_HEIGHT],
        }
        sensor.set_tank_height(value)
        sensor.schedule_update_ha_state(True)

    def set_fuel_alert_service(service: ServiceCall) -> None:
        """Set fuel alert for LM4110-ZB."""
        sensor = get_sensor(service)
        if not isinstance(sensor, Neviweb130TankSensor):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "entity_must_be_domain",
                    f"Entity {sensor.entity_id} must be a {DOMAIN} tank sensor.",
                    entity=sensor.entity_id,
                    domain=DOMAIN,
                    platform="tank sensor",
                )
            )
        value = {"id": sensor.unique_id, "fuel": service.data[ATTR_FUEL_ALERT]}
        sensor.set_fuel_alert(value)
        sensor.schedule_update_ha_state(True)

    def set_refuel_alert_service(service: ServiceCall) -> None:
        """Set refuel alert for LM4110-ZB."""
        sensor = get_sensor(service)
        if not isinstance(sensor, Neviweb130TankSensor):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "entity_must_be_domain",
                    f"Entity {sensor.entity_id} must be a {DOMAIN} tank sensor.",
                    entity=sensor.entity_id,
                    domain=DOMAIN,
                    platform="tank sensor",
                )
            )
        value = {"id": sensor.unique_id, "refuel": service.data[ATTR_REFUEL]}
        sensor.set_refuel_alert(value)
        sensor.schedule_update_ha_state(True)

    def set_battery_alert_service(service: ServiceCall) -> None:
        """Set battery alert for LM4110-ZB."""
        sensor = get_sensor(service)
        if not isinstance(sensor, Neviweb130TankSensor):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "entity_must_be_domain",
                    f"Entity {sensor.entity_id} must be a {DOMAIN} tank sensor.",
                    entity=sensor.entity_id,
                    domain=DOMAIN,
                    platform="tank sensor",
                )
            )
        value = {"id": sensor.unique_id, "batt": service.data[ATTR_BATT_ALERT]}
        sensor.set_battery_alert(value)
        sensor.schedule_update_ha_state(True)

    def set_activation_service(service: ServiceCall) -> None:
        """Activate or deactivate Neviweb polling for missing device."""
        sensor = get_sensor(service)
        value = {"id": sensor.unique_id, "active": service.data[ATTR_ACTIVE]}
        sensor.set_activation(value)
        sensor.schedule_update_ha_state(True)

    def set_neviweb_status_service(service: ServiceCall) -> None:
        """Set Neviweb global status, home or away."""
        sensor = get_sensor(service)
        if not isinstance(sensor, Neviweb130GatewaySensor):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "entity_must_be_domain",
                    f"Entity {sensor.entity_id} must be a {DOMAIN} gateway sensor.",
                    entity=sensor.entity_id,
                    domain=DOMAIN,
                    platform="gateway sensor",
                )
            )
        value = {"id": sensor.unique_id, "mode": service.data[ATTR_MODE]}
        sensor.set_neviweb_status(value)
        sensor.schedule_update_ha_state(True)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SENSOR_ALERT,
        set_sensor_alert_service,
        schema=SET_SENSOR_ALERT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_BATTERY_TYPE,
        set_battery_type_service,
        schema=SET_BATTERY_TYPE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TANK_TYPE,
        set_tank_type_service,
        schema=SET_TANK_TYPE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_GAUGE_TYPE,
        set_gauge_type_service,
        schema=SET_GAUGE_TYPE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_LOW_FUEL_ALERT,
        set_low_fuel_alert_service,
        schema=SET_LOW_FUEL_ALERT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TANK_HEIGHT,
        set_tank_height_service,
        schema=SET_TANK_HEIGHT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FUEL_ALERT,
        set_fuel_alert_service,
        schema=SET_FUEL_ALERT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_REFUEL_ALERT,
        set_refuel_alert_service,
        schema=SET_REFUEL_ALERT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_BATTERY_ALERT,
        set_battery_alert_service,
        schema=SET_BATTERY_ALERT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ACTIVATION,
        set_activation_service,
        schema=SET_ACTIVATION_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_NEVIWEB_STATUS,
        set_neviweb_status_service,
        schema=SET_NEVIWEB_STATUS_SCHEMA,
    )


def voltage_to_percentage(voltage, type_val):
    """Convert voltage level from volt to percentage."""
    if type_val == "alkaline":
        return int((min(voltage, 3.0) - 2.0) / (3.0 - 2.0) * 100)
    else:
        return int((min(voltage, 3.0) - 2.2) / (3.0 - 2.2) * 100)


def convert(sampling):
    sample = str(sampling)
    date = datetime.datetime.fromtimestamp(int(sample[0:-3]))
    return date


def convert_to_percent(angle, low, high):
    x = angle
    x_min = 110
    if low == 5:
        x_max = 415
        delta = 55
    else:
        x_max = 406
        delta = 46
    if delta <= x <= 70:
        x = delta
    if 0 <= x <= delta:
        x = x + 360
    y = (x - x_min) / (x_max - x_min)
    lower_limit = low
    upper_limit = high
    value_range = upper_limit - lower_limit
    pct = y * value_range + lower_limit
    return round(pct)



# Re-export classes from sub-modules for backward compatibility
from .base import (  # noqa: E402
    Neviweb130Sensor,
    SNOOZE_TIME,
    SCAN_INTERVAL,
    UPDATE_ATTRIBUTES,
    IMPLEMENTED_DEVICE_MODEL,
    IMPLEMENTED_GATEWAY,
    IMPLEMENTED_TANK_MONITOR,
    IMPLEMENTED_LTE_TANK_MONITOR,
    IMPLEMENTED_SENSOR_MODEL,
    IMPLEMENTED_NEW_SENSOR_MODEL,
    IMPLEMENTED_NEW_CONNECTED_SENSOR,
    IMPLEMENTED_CONNECTED_SENSOR,
    voltage_to_percentage,
    convert,
    convert_to_percent,
)
from .subclasses import (  # noqa: E402
    Neviweb130ConnectedSensor,
    Neviweb130TankSensor,
    Neviweb130GatewaySensor,
    NeviwebDailyRequestSensor,
)
