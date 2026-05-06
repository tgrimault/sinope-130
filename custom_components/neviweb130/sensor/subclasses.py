"""Neviweb130Sensor subclasses."""
from __future__ import annotations

import logging
import time
from typing import override

from homeassistant.helpers.entity import Entity

from ..const import (
    ATTR_ANGLE,
    ATTR_BATTERY_STATUS,
    ATTR_BATTERY_TYPE,
    ATTR_BATTERY_VOLTAGE,
    ATTR_BATT_ALERT,
    ATTR_BATT_PERCENT_NORMAL,
    ATTR_BATT_STATUS_NORMAL,
    ATTR_CONF_CLOSURE,
    ATTR_ERROR_CODE_SET1,
    ATTR_FUEL_ALERT,
    ATTR_FUEL_PERCENT_ALERT,
    ATTR_GAUGE_TYPE,
    ATTR_OCCUPANCY,
    ATTR_REFUEL,
    ATTR_ROOM_TEMPERATURE,
    ATTR_ROOM_TEMP_ALARM,
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
    STATE_WATER_LEAK,
)
from ..helpers import translated_or_default, get_daily_request_count
from .base import (
    Neviweb130Sensor,
    voltage_to_percentage,
    convert,
    convert_to_percent,
    SNOOZE_TIME,
)

_LOGGER = logging.getLogger(__name__)

class Neviweb130ConnectedSensor(Neviweb130Sensor):
    """Implementation of a Neviweb sensor connected to Sedna valve."""

    def update(self):
        if self._active:
            if self._is_connected or self._is_new_connected:
                LEAK_ATTRIBUTE = [
                    ATTR_WATER_LEAK_STATUS,
                    ATTR_ROOM_TEMPERATURE,
                    ATTR_ROOM_TEMP_ALARM,
                    ATTR_BATTERY_TYPE,
                    ATTR_BATT_ALERT,
                    ATTR_TEMP_ALERT,
                    ATTR_BATT_PERCENT_NORMAL,
                    ATTR_BATT_STATUS_NORMAL,
                    ATTR_CONF_CLOSURE,
                ]
            else:
                LEAK_ATTRIBUTE = []
            if self._is_new_connected:
                NEW_LEAK_ATTRIBUTE = [ATTR_SENSOR_TYPE]
            else:
                NEW_LEAK_ATTRIBUTE = []

            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            attributes = UPDATE_ATTRIBUTES + LEAK_ATTRIBUTE + NEW_LEAK_ATTRIBUTE
            _LOGGER.debug("Updated attributes for %s: %s", self._name, attributes)
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
                    if self._is_connected or self._is_new_connected:
                        if device_data[ATTR_WATER_LEAK_STATUS] == "probe":
                            code = device_data[ATTR_WATER_LEAK_STATUS]
                            self.notify_ha(
                                translated_or_default(
                                    self.hass,
                                    "error_code",
                                    (
                                        f"Warning: Neviweb Device error code detected: {code} "
                                        f"for device: {self._name}, "
                                        f"ID: {self._id}, Sku: {self._sku}."
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
                        self._temp_status = device_data[ATTR_ROOM_TEMP_ALARM]
                        if ATTR_TEMP_ALERT in device_data:
                            self._temp_alert = device_data[ATTR_TEMP_ALERT]
                        if ATTR_BATT_ALERT in device_data:
                            self._battery_alert = device_data[ATTR_BATT_ALERT]
                        if ATTR_BATTERY_STATUS in device_data:
                            self._battery_status = device_data[ATTR_BATTERY_STATUS]
                            self._battery_type = device_data[ATTR_BATTERY_TYPE]
                        if ATTR_BATT_PERCENT_NORMAL in device_data:
                            self._batt_percent_normal = device_data[ATTR_BATT_PERCENT_NORMAL]
                            self._batt_status_normal = device_data[ATTR_BATT_STATUS_NORMAL]
                        self._closure_action = device_data[ATTR_CONF_CLOSURE]
                        self._battery_voltage = device_data[ATTR_BATTERY_VOLTAGE]
                        if self._is_new_connected:
                            if ATTR_SENSOR_TYPE in device_data:
                                self._sensor_type = device_data[ATTR_SENSOR_TYPE]
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
                "battery_icon": self.battery_icon,
                "battery_level": voltage_to_percentage(self._battery_voltage, self._battery_type),
                "battery_voltage": self._battery_voltage,
                "battery_status": self._battery_status,
                "battery_percent_normalized": self._batt_percent_normal,
                "battery_status_normalized": self._batt_status_normal,
                "battery_alert": self._battery_alert,
                "battery_type": self._battery_type,
                "closure_action": self._closure_action,
            }
        )
        if self._is_new_connected:
            data.update(
                {
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


class Neviweb130TankSensor(Neviweb130Sensor):
    """Implementation of a Neviweb tank level sensor LM4110ZB."""

    def __init__(self, device_info, name, device_type, sku, firmware, client):
        """Initialize."""
        super().__init__(device_info, name, device_type, sku, firmware, client)
        self._refuel = False

    def update(self):
        """Update device."""
        if self._active:
            if self._is_monitor:
                MONITOR_ATTRIBUTE = [
                    ATTR_ANGLE,
                    ATTR_TANK_PERCENT,
                    ATTR_TANK_TYPE,
                    ATTR_GAUGE_TYPE,
                    ATTR_TANK_HEIGHT,
                    ATTR_FUEL_ALERT,
                    ATTR_REFUEL,
                    ATTR_BATT_ALERT,
                    ATTR_FUEL_PERCENT_ALERT,
                    ATTR_ERROR_CODE_SET1,
                    ATTR_RSSI,
                ]
            else:
                MONITOR_ATTRIBUTE = [
                    ATTR_ANGLE,
                    ATTR_TANK_PERCENT,
                    ATTR_TANK_TYPE,
                    ATTR_GAUGE_TYPE,
                    ATTR_TANK_HEIGHT,
                ]
            start = time.time()
            attributes = UPDATE_ATTRIBUTES + MONITOR_ATTRIBUTE
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
                    self._angle = device_data[ATTR_ANGLE]["value"]
                    if self._angle == -2:
                        self.notify_ha(
                            translated_or_default(
                                self.hass,
                                "gauge_disconnected",
                                (
                                    f"Warning: Tank monitor gauge disconnected: for device: {self._name} "
                                    f"id: {self._id}, Sku: {self._sku}."
                                ),
                                name=self._name,
                                id=self._id,
                                sku=self._sku,
                            )
                        )
                    self._sampling = device_data[ATTR_ANGLE][ATTR_SAMPLING]
                    self._tank_percent = device_data[ATTR_TANK_PERCENT]
                    self._tank_type = device_data[ATTR_TANK_TYPE]
                    self._tank_height = device_data[ATTR_TANK_HEIGHT]
                    self._gauge_type = device_data[ATTR_GAUGE_TYPE]
                    self._battery_voltage = device_data[ATTR_BATTERY_VOLTAGE]
                    if self._is_monitor:
                        self._fuel_alert = device_data[ATTR_FUEL_ALERT]
                        self._refuel = device_data[ATTR_REFUEL]
                        self._fuel_percent_alert = device_data[ATTR_FUEL_PERCENT_ALERT]
                        self._battery_alert = device_data[ATTR_BATT_ALERT]
                        if ATTR_RSSI in device_data:
                            self._rssi = device_data[ATTR_RSSI]
                        if ATTR_ERROR_CODE_SET1 in device_data and len(device_data[ATTR_ERROR_CODE_SET1]) > 0:
                            if device_data[ATTR_ERROR_CODE_SET1]["raw"] != 0:
                                self._error_code = device_data[ATTR_ERROR_CODE_SET1]["raw"]
                                code = str(device_data[ATTR_ERROR_CODE_SET1]["raw"])
                                self.notify_ha(
                                    translated_or_default(
                                        self.hass,
                                        "error_code",
                                        (
                                            f"Warning: Neviweb Device error code detected: {code} for device: "
                                            f"{self._name}, ID: {self._id}, Sku: {self._sku}."
                                        ),
                                        code=code,
                                        message="",
                                        name=self._name,
                                        id=self._id,
                                        sku=self._sku,
                                    )
                                )
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
    def entity_picture(self) -> str | None:
        """Replace entity picture by tank percent icon."""
        if self._tank_percent is None:
            return None

        icon_path = self.icon_type
        if icon_path is not None and file_exists(self.hass, icon_path):
            return icon_path

        return None

    @property
    @override
    def icon_type(self) -> str | None:
        """Select icon based on _tank_percent value."""
        base = "propane"
        if not self._is_monitor:
            return None

        if self._tank_percent is None:
            return "/local/neviweb130/{base}-unknown.png"

        demand = self._tank_percent or 0

        thresholds = [
            (1, "-0"),
            (11, "-1"),
            (21, "-2"),
            (31, "-3"),
            (41, "-4"),
            (51, "-5"),
            (61, "-6"),
            (71, "-7"),
        ]

        for limit, suffix in thresholds:
            if demand < limit:
                return f"/local/neviweb130/{base}{suffix}.png"

        return f"/local/neviweb130/{base}-8.png"

    @property
    def level_status(self):
        """Return current sensor fuel level status."""
        if self._fuel_alert:
            return "OK"
        else:
            return "Low"

    @property
    def refuel_status(self):
        """Return current sensor refuel status."""
        if self._refuel:
            return "Refueled"
        else:
            return "Normal"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        data = {}
        data.update(
            {
                "gauge_angle": self._angle,
                "last_sampling_time": convert(self._sampling),
                "battery_icon": self.battery_icon,
                "battery_level": voltage_to_percentage(self._battery_voltage, "lithium"),
                "battery_voltage": self._battery_voltage,
                "tank_type": self._tank_type,
                "tank_height": self._tank_height,
                "tank_percent": self._tank_percent,
                "gauge_type": self._gauge_type,
            }
        )
        if self._is_monitor:
            data.update(
                {
                    "battery_alert": self._battery_alert,
                    "fuel_alert": "OK" if self._fuel_alert else "Low",
                    "refuel_alert": "Refueled" if self._refuel else "Normal",
                    "fuel_percent_alert": ("Off" if self._fuel_percent_alert == 0 else self._fuel_percent_alert),
                    "error_code": self._error_code,
                    "rssi": self._rssi,
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
    def state(self):
        """Return the state of the tank sensor."""
        return self._tank_percent

    #        return convert_to_percent(self._angle, 10, 80)

    def set_tank_type(self, value):
        """Set tank type for LM4110-ZB sensor."""
        self._client.set_tank_type(value["id"], value["type"])
        self._tank_type = value["type"]

    def set_gauge_type(self, value):
        """Set gauge type for LM4110-ZB sensor."""
        self._client.set_gauge_type(value["id"], str(value["gauge"]))
        self._gauge_type = str(value["gauge"])

    def set_low_fuel_alert(self, value):
        """Set low fuel alert limit LM4110-ZB sensor."""
        self._client.set_low_fuel_alert(value["id"], value["low"])
        self._fuel_percent_alert = value["low"]

    def set_refuel_alert(self, value):
        """ "Set refuel alert for LM4110-ZB sensor True/False."""
        self._client.set_refuel_alert(value["id"], value["refuel"])
        self._refuel = value["refuel"]

    def set_tank_height(self, value):
        """Set low fuel alert LM4110-ZB sensor."""
        self._client.set_tank_height(value["id"], value["height"])
        self._tank_height = value["height"]

    def set_fuel_alert(self, value):
        """Set low fuel alert LM4110-ZB sensor."""
        self._client.set_fuel_alert(value["id"], value["fuel"])
        self._fuel_alert = value["fuel"]

    def set_battery_alert(self, value):
        """Set low battery alert LM4110-ZB sensor."""
        self._client.set_battery_alert(value["id"], value["batt"])
        self._battery_alert = value["batt"]


class Neviweb130GatewaySensor(Neviweb130Sensor):
    """Implementation of a Neviweb gateway sensor, GT130, GT4220WF."""

    def __init__(self, device_info, name, device_type, sku, firmware, location, client):
        """Initialize."""
        super().__init__(device_info, name, device_type, sku, firmware, client)
        self._location = str(location)
        self._gateway_status = None
        self._occupancyMode = "home"

    def update(self):
        """Update device."""
        if self._active:
            start = time.time()
            device_status = self._client.get_device_status(self._id)
            neviweb_status = self._client.get_neviweb_status(self._location)
            end = time.time()
            elapsed = round(end - start, 3)
            _LOGGER.debug("Updating %s (%s sec): %s", self._name, elapsed, device_status)
            if not device_status:
                return

            if "error" in device_status:
                self.log_error(device_status["error"]["code"])
                return

            if "errorCode" in device_status:
                _LOGGER.warning(
                    "Error in reading device status for %s: (%s)",
                    self._name,
                    device_status,
                )
                return

            if ATTR_STATUS not in device_status:
                _LOGGER.warning(
                    "Gateway status missing for %s: (%s)",
                    self._name,
                    device_status,
                )
                return

            self._gateway_status = device_status[ATTR_STATUS]
            if neviweb_status and ATTR_OCCUPANCY in neviweb_status:
                self._occupancyMode = neviweb_status[ATTR_OCCUPANCY]
            return

    @property
    def gateway_status(self):
        """Return current gateway status: 'online' or 'offline'."""
        return self._gateway_status is not None

    @property
    def state(self):
        """Return the state of the gateway."""
        return self._gateway_status

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        data = {}
        data.update(
            {
                "gateway_status": self._gateway_status,
                "neviweb_occupancyMode": self._occupancyMode,
                "sku": self._sku,
                "device_model": str(self._device_model),
                "device_model_cfg": self._device_model_cfg,
                "firmware": self._firmware,
                "activation": "Active" if self._active else "Inactive",
                "device_type": self._device_type,
                "neviweb_location": str(self._location),
                "id": self._id,
            }
        )
        return data

    def set_neviweb_status(self, value):
        """Set Neviweb global occupancy mode, away or home"""
        self._client.post_neviweb_status(self._location, value["mode"])
        self._occupancyMode = value["mode"]


class NeviwebDailyRequestSensor(Entity):
    """Internal sensor : number of neviweb130 requests to Neviweb Today."""

    def __init__(self, hass):
        self.hass = hass
        self._attr_name = "Neviweb130 Daily Requests"
        self._attr_unique_id = f"{DOMAIN}_daily_requests"
        self._notified = False

    @property
    def name(self):
        return self._attr_name

    @property
    def unique_id(self):
        return self._attr_unique_id

    @property
    def state(self):
        return get_daily_request_count(self.hass)

    @property
    def icon(self):
        return "mdi:counter"

    @property
    def state_class(self):
        return "total"

    @property
    def device_class(self):
        return "measurement"

    @property
    def unit_of_measurement(self):
        return "requests"

    @property
    def extra_state_attributes(self):
        data = self.hass.data[DOMAIN]["request_data"]
        return {
            "date": data["date"],
            "safety_limit": 25000,
            "limit": 30000,
        }

    def update(self):
        """Send notification if we reach limit for request."""
        count = get_daily_request_count(self.hass)

        # Secure limit for notification
        if count > 25000 and not self._notified:
            self._notified = True
            notify_ha(
                self.hass,
                translated_or_default(
                    self.hass,
                    "request_count",
                    f"Warning: {count} requests today. Safety limit: 25000, Daily limit: 30000.",
                    count=count,
                    limit=25000,
                ),
            )

        # Reset flag when we pass midnight
        data = self.hass.data[DOMAIN]["request_data"]
        today = datetime.date.today().isoformat()

        if data["date"] != today:
            self._notified = False

        return None
