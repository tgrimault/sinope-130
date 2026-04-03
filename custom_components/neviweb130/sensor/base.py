"""Neviweb130Sensor base class."""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone
from typing import Any, override

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.persistent_notification import DOMAIN as PN_DOMAIN
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import ATTR_ENTITY_ID, PERCENTAGE, UnitOfTemperature
from homeassistant.core import ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity import Entity

from .. import NOTIFY
from .. import SCAN_INTERVAL as scan_interval
from .. import STAT_INTERVAL
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


class Neviweb130Sensor(Entity):
    """Implementation of a Neviweb sensor connected to GT130."""

    def __init__(self, device_info, name, device_type, sku, firmware, client):
        """Initialize."""
        _LOGGER.debug("Setting up %s: %s", name, device_info)
        self._name = name
        self._sku = sku
        self._firmware = firmware
        self._client = client
        self._id = str(device_info["id"])
        self._device_model = device_info["signature"]["model"]
        self._device_model_cfg = device_info["signature"]["modelCfg"]
        self._device_type = device_type
        self._is_leak = (
            device_info["signature"]["model"] in IMPLEMENTED_SENSOR_MODEL
            or device_info["signature"]["model"] in IMPLEMENTED_NEW_SENSOR_MODEL
        )
        self._is_connected = (
            device_info["signature"]["model"] in IMPLEMENTED_CONNECTED_SENSOR
            or device_info["signature"]["model"] in IMPLEMENTED_NEW_CONNECTED_SENSOR
        )
        self._is_new_connected = device_info["signature"]["model"] in IMPLEMENTED_NEW_CONNECTED_SENSOR
        self._is_new_leak = (
            device_info["signature"]["model"] in IMPLEMENTED_NEW_SENSOR_MODEL
            or device_info["signature"]["model"] in IMPLEMENTED_NEW_CONNECTED_SENSOR
        )
        self._is_monitor = device_info["signature"]["model"] in IMPLEMENTED_TANK_MONITOR
        self._is_gateway = device_info["signature"]["model"] in IMPLEMENTED_GATEWAY
        self._active = True
        self._angle = None
        self._batt_percent_normal = None
        self._batt_status_normal = None
        self._battery_alert = None
        self._battery_status = None
        self._battery_type = "alkaline"
        self._battery_voltage = None
        self._closure_action = None
        self._cur_temp = None
        self._error_code = None
        self._fuel_alert = None
        self._fuel_percent_alert = None
        self._gauge_type = None
        self._leak_alert = None
        self._leak_status = None
        self._rssi = None
        self._sampling = None
        self._sensor_type = None
        self._snooze = 0.0
        self._tank_height = None
        self._tank_percent = None
        self._tank_type = None
        self._temp_alert = None
        self._temp_status = None

    def update(self):
        if self._active:
            if self._is_leak:
                LEAK_ATTRIBUTE = [
                    ATTR_WATER_LEAK_STATUS,
                    ATTR_ROOM_TEMPERATURE,
                    ATTR_ROOM_TEMP_ALARM,
                    ATTR_LEAK_ALERT,
                    ATTR_BATTERY_TYPE,
                    ATTR_BATT_ALERT,
                    ATTR_TEMP_ALERT,
                    ATTR_RSSI,
                    ATTR_BATT_PERCENT_NORMAL,
                    ATTR_BATT_STATUS_NORMAL,
                ]
            else:
                LEAK_ATTRIBUTE = []
            if self._is_new_leak:
                NEW_LEAK_ATTRIBUTE = [ATTR_ERROR_CODE_SET1, ATTR_SENSOR_TYPE]
            else:
                NEW_LEAK_ATTRIBUTE = []

            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            attributes = UPDATE_ATTRIBUTES + LEAK_ATTRIBUTE + NEW_LEAK_ATTRIBUTE
            safe_mode = self.hass.data[DOMAIN]["safe_mode"]

            if safe_mode == self._id:
                device_data = safe_get_device_attributes(
                    self.hass,
                    self._client,
                    self._id,
                    attributes,
                    _LOGGER,
                    device_sku=self._sku,
                    device_model=self._device_model,
                    firmware=self._firmware,
                )
            else:
                device_data = self._client.get_device_attributes(self._id, attributes)
            end = time.time()
            elapsed = round(end - start, 3)
            _LOGGER.debug("Updating %s (%s sec): %s", self._name, elapsed, device_data)
            if "error" not in device_data or device_data is not None:
                if "errorCode" not in device_data:
                    if self._is_leak or self._is_new_leak:
                        if device_data[ATTR_WATER_LEAK_STATUS] == "probe":
                            code = device_data[ATTR_WATER_LEAK_STATUS]
                            self.notify_ha(
                                translated_or_default(
                                    self.hass,
                                    "error_code",
                                    (
                                        f"Warning: Neviweb Device error code detected: {code} for device: ",
                                        f"{self._name} ID: {self._id}, Sku: {self._sku}.",
                                    ),
                                    code=code,
                                    message="",
                                    name=self._name,
                                    id=self._id,
                                    sku=self._sku,
                                )
                            )
                            self._leak_status = device_data[ATTR_WATER_LEAK_STATUS]
                        else:
                            self._leak_status = (
                                STATE_WATER_LEAK if device_data[ATTR_WATER_LEAK_STATUS] == STATE_WATER_LEAK else "ok"
                            )
                        self._cur_temp = device_data[ATTR_ROOM_TEMPERATURE]
                        self._leak_alert = device_data[ATTR_LEAK_ALERT]
                        self._temp_status = device_data[ATTR_ROOM_TEMP_ALARM]
                        self._temp_alert = device_data[ATTR_TEMP_ALERT]
                        self._battery_alert = device_data[ATTR_BATT_ALERT]
                        if ATTR_BATTERY_STATUS in device_data:
                            self._battery_status = device_data[ATTR_BATTERY_STATUS]
                            self._battery_type = device_data[ATTR_BATTERY_TYPE]
                        if ATTR_BATT_PERCENT_NORMAL in device_data:
                            self._batt_percent_normal = device_data[ATTR_BATT_PERCENT_NORMAL]
                            self._batt_status_normal = device_data[ATTR_BATT_STATUS_NORMAL]
                        if self._is_new_leak:
                            if ATTR_ERROR_CODE_SET1 in device_data and len(device_data[ATTR_ERROR_CODE_SET1]) > 0:
                                if device_data[ATTR_ERROR_CODE_SET1]["raw"] != 0:
                                    self._error_code = device_data[ATTR_ERROR_CODE_SET1]["raw"]
                                    self.notify_ha(
                                        "Warning: Neviweb Device error code detected: "
                                        + str(device_data[ATTR_ERROR_CODE_SET1]["raw"])
                                        + " for device: "
                                        + self._name
                                        + ", Sku: "
                                        + self._sku
                                    )
                            if ATTR_SENSOR_TYPE in device_data:
                                self._sensor_type = device_data[ATTR_SENSOR_TYPE]
                        self._battery_voltage = device_data[ATTR_BATTERY_VOLTAGE]
                        if ATTR_RSSI in device_data:
                            self._rssi = device_data[ATTR_RSSI]
                    return
                _LOGGER.warning("Error in reading device %s: (%s)", self._name, device_data)
                return
            elif device_data is not None:
                self.log_error(device_data["error"]["code"])
        else:
            if time.time() - self._snooze > SNOOZE_TIME:
                self._active = True
                if NOTIFY == "notification" or NOTIFY == "both":
                    self.notify_ha(
                        translated_or_default(
                            self.hass,
                            "update_restarted",
                            f"Warning: Neviweb Device update restarted for {self._name}, Sku: {self._sku}.",
                            name=self._name,
                            sku=self._sku,
                        )
                    )

    @property
    @override
    def unique_id(self) -> str:
        """Return unique ID based on Neviweb device ID."""
        return self._client.scoped_unique_id(self._id)

    @property
    @override
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    @override
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        device_info = SENSOR_TYPES.get(self._device_type)
        if device_info is None:
            return None

        return device_info[1]

    @property
    def entity_picture(self) -> str | None:
        """Replace entity picture by leak icon."""
        if self._leak_status is None:
            return None

        icon_path = self.icon_type
        if icon_path is not None and file_exists(self.hass, icon_path):
            return icon_path

        return None

    @property
    @override
    def unit_of_measurement(self) -> str | None:
        """Return the unit of measurement of this entity, if any."""
        device_info = SENSOR_TYPES.get(self._device_type)
        if device_info is None:
            return None

        return device_info[0]

    @property
    def unit_class(self) -> str | None:
        device_info = SENSOR_TYPES.get(self._device_type)
        return device_info[3] if device_info else None

    @property
    def statistic_mean_type(self) -> StatisticMeanType | None:
        device_info = SENSOR_TYPES.get(self._device_type)
        return device_info[4] if device_info else None

    @property
    @override
    def device_class(self) -> BinarySensorDeviceClass | SensorStateClass | None:
        """Return the device class of this entity."""
        device_info = SENSOR_TYPES.get(self._device_type)
        if device_info is None:
            return None

        return device_info[2]

    @property
    def current_temperature(self):
        """Return the current sensor temperature."""
        return self._cur_temp

    @property
    def leak_status(self):
        """Return current sensor leak status: 'water' or 'ok'."""
        return self._leak_status

    @property
    def icon_type(self) -> str | None:
        """Select icon file based on leak_status value."""
        if self._is_gateway or self._is_monitor:
            return None

        is_water_sensor = self._is_leak or self._is_connected
        if is_water_sensor:
            return "/local/neviweb130/drop.png" if self.leak_status == "ok" else "/local/neviweb130/leak.png"
        return None

    @property
    def battery_icon(self) -> str | None:
        """Return battery icon file based on battery voltage."""
        if self._is_gateway:
            return None

        batt = (
            voltage_to_percentage(self._battery_voltage, "lithium") if self._is_monitor else self._batt_percent_normal
        )

        if batt is None:
            return "/local/neviweb130/battery-unknown.png"

        level = min(batt // 20 + 1, 5)
        return f"/local/neviweb130/battery-{level}.png"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        data = {}
        data.update(
            {
                "leak_status": self._leak_status,
                "icon_type": self.icon_type,
                "temperature": self._cur_temp,
                "temp_alarm": self._temp_status,
                "temperature_alert": self._temp_alert,
                "leak_alert": self._leak_alert,
                "battery_icon": self.battery_icon,
                "battery_level": voltage_to_percentage(self._battery_voltage, self._battery_type),
                "battery_voltage": self._battery_voltage,
                "battery_status": self._battery_status,
                "battery_percent_normalized": self._batt_percent_normal,
                "battery_status_normalized": self._batt_status_normal,
                "battery_alert": self._battery_alert,
                "battery_type": self._battery_type,
                "rssi": self._rssi,
            }
        )
        if self._is_new_leak:
            data.update(
                {
                    "error_code": self._error_code,
                    "sensor_type": self._sensor_type,
                }
            )
        data.update(
            {
                "sku": self._sku,
                "device_model": str(self._device_model),
                "device_model_cfg": self._device_model_cfg,
                "firmware": self._firmware,
                "activation": "Active" if self._active else "Inactive",
                "device_type": self._device_type,
                "id": self._id,
            }
        )
        return data

    @property
    def battery_voltage(self):
        """Return the current battery voltage of the sensor in %."""
        return voltage_to_percentage(self._battery_voltage, self._battery_type)

    @property
    def battery_status(self):
        """Return the current battery status."""
        return self._battery_status

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._leak_status

    def set_sensor_alert(self, value):
        """Set water leak sensor alert and action."""
        self._client.set_sensor_alert(value["id"], value["leak"], value["batt"], value["temp"], value["close"])
        self._leak_alert = True if value["leak"] == 1 else False
        self._temp_alert = True if value["temp"] == 1 else False
        self._battery_alert = True if value["batt"] == 1 else False
        self._closure_action = value["close"]

    def set_battery_type(self, value):
        """Set battery type, alkaline or lithium for water leak sensor."""
        self._client.set_battery_type(value["id"], value["type"])
        self._battery_type = value["type"]

    def set_activation(self, value):
        """Activate or deactivate neviweb polling for a missing device."""
        self._active = value["active"]

    def notify_ha(self, msg: str, title: str = "Neviweb130 integration " + VERSION):
        """Notify user via HA web frontend."""
        self.hass.services.call(
            PN_DOMAIN,
            "create",
            service_data={
                "title": title,
                "message": msg,
            },
            blocking=False,
        )
        return True

    def log_error(self, error_data):
        """Send error message to LOG."""
        if error_data == "USRSESSEXP":
            _LOGGER.warning(
                translated_or_default(
                    self.hass,
                    "usr_session",
                    (
                        "Warning: Got USRSESSEXP error, Neviweb session expired.\n"
                        "Set your scan_interval parameter to less than 10 minutes to avoid this...\n"
                        "Reconnecting..."
                    ),
                )
            )
            if NOTIFY == "notification" or NOTIFY == "both":
                self.notify_ha(
                    translated_or_default(
                        self.hass,
                        "usr_session",
                        (
                            "Warning: Got USRSESSEXP error, Neviweb session expired.\n"
                            "Set your scan_interval parameter to less than 10 minutes to avoid this...\n"
                            "Reconnecting..."
                        ),
                    )
                )
            self._client.reconnect()
        elif error_data == "ACCDAYREQMAX":
            _LOGGER.warning(
                translated_or_default(
                    self.hass,
                    "daily_access",
                    "Maximum daily request reached...Increase interval polling frequency on Neviweb, (scan_interval).",
                )
            )
        elif error_data == "TimeoutError":
            _LOGGER.warning("Timeout error detected... Retry later")
        elif error_data == "MAINTENANCE":
            _LOGGER.warning(
                translated_or_default(
                    self.hass,
                    "maintenance",
                    "Warning: Neviweb access temporary blocked for maintenance... Retry later.",
                )
            )
            self.notify_ha(
                translated_or_default(
                    self.hass,
                    "maintenance",
                    "Warning: Neviweb access temporary blocked for maintenance... Retry later.",
                )
            )
            self._client.reconnect()
        elif error_data == "ACCSESSEXC":
            _LOGGER.warning(
                translated_or_default(
                    self.hass,
                    "access_limit",
                    (
                        "Warning: ACCSESSEXC maximum Neviweb session number reached...\n"
                        "Close other connections and try again."
                    ),
                )
            )
            self.notify_ha(
                translated_or_default(
                    self.hass,
                    "access_limit",
                    (
                        "Warning: ACCSESSEXC maximum Neviweb session number reached...\n"
                        "Close other connections and try again."
                    ),
                )
            )
            self._client.reconnect()
        elif error_data == "DVCATTRNSPTD":
            _LOGGER.warning(
                "Device attribute not supported for %s (id: %s): %s... (SKU: %s)",
                self._name,
                str(self._id),
                error_data,
                self._sku,
            )
            safe_mode = self.hass.data[DOMAIN]["safe_mode"]
            if safe_mode == "-":
                _LOGGER.warning(
                    translated_or_default(
                        self.hass,
                        "safe_mode_enabled",
                        (
                            f"Auto-enabling safe mode for device {self._name} (id: {self._id}) "
                            "due to unsupported action."
                        ),
                        name=self._name,
                        id=self._id,
                    )
                )

                self.hass.data[DOMAIN]["safe_mode"] = self._id

        elif error_data == "DVCACTNSPTD":
            _LOGGER.warning(
                "Device action not supported for %s (id: %s)... (SKU: %s), (Model: %s). Report to maintainer",
                self._name,
                str(self._id),
                self._sku,
                str(self._device_model),
            )
        elif error_data == "DVCCOMMTO":
            _LOGGER.warning(
                "Device Communication Timeout for %s (id: %s)... The device "
                + "did not respond to the server within the prescribed delay"
                + "(SKU: %s)",
                self._name,
                str(self._id),
                self._sku,
            )
        elif error_data == "SVCERR":
            _LOGGER.warning(
                "Service error, device not available retry later %s (id: %s): %s... (SKU: %s)",
                self._name,
                str(self._id),
                error_data,
                self._sku,
            )
        elif error_data == "DVCBUSY":
            _LOGGER.warning(
                "Device busy can't reach (neviweb update ?), retry later %s (id: %s): %s... (SKU: %s)",
                self._name,
                str(self._id),
                error_data,
                self._sku,
            )
        elif error_data == "DVCUNVLB":
            if NOTIFY == "logging" or NOTIFY == "both":
                _LOGGER.warning(
                    "Device %s is disconnected from Neviweb: %s (id: %s)... (SKU: %s)",
                    self._name,
                    str(self._id),
                    error_data,
                    self._sku,
                )
                _LOGGER.warning(
                    "This device %s is de-activated and won't be updated for 20 minutes",
                    self._name,
                )
                _LOGGER.warning(
                    "You can re-activate device %s with "
                    + "service.neviweb130_set_activation or wait 20 minutes "
                    + "for update to restart or just restart HA",
                    self._name,
                )
            if NOTIFY == "notification" or NOTIFY == "both":
                self.notify_ha(
                    translated_or_default(
                        self.hass,
                        "update_stopped",
                        (
                            "Warning: Received message from Neviweb, device disconnected... Check your log...\n"
                            f"Neviweb update will be halted for 20 minutes for {self._name}, \n"
                            f"id: {self._id}, Sku: {self._sku}."
                        ),
                        name=self._name,
                        id=self._id,
                        sku=self._sku,
                    )
                )
            self._active = False
            self._snooze = time.time()
        else:
            _LOGGER.warning(
                translated_or_default(
                    self.hass,
                    "unknown_error",
                    (
                        f"Unknown error for {self._name} (id: {self._id}) (SKU: {self._sku}),\n"
                        f"(Model: {str(self._device_model)}). Report to maintainer.\n"
                        f"Data received: {error_data}."
                    ),
                    name=self._name,
                    id=self._id,
                    sku=self._sku,
                    model=str(self._device_model),
                    data=error_data,
                )
            )


