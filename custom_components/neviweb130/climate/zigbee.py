"""Zigbee thermostat subclasses for neviweb130 climate platform."""
from __future__ import annotations

import logging
import time
from typing import Any, Mapping, override

from homeassistant.components.climate.const import (
    PRESET_AWAY,
    PRESET_HOME,
    PRESET_NONE,
    HVACAction,
    HVACMode,
)
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature

from .. import NOTIFY
from ..const import (
    ATTR_AVAIL_MODE,
    ATTR_BACK_LIGHT,
    ATTR_BACKLIGHT,
    ATTR_COLD_LOAD_PICKUP,
    ATTR_CYCLE_LENGTH,
    ATTR_CYCLE_OUTPUT2,
    ATTR_DISPLAY2,
    ATTR_DRSETPOINT,
    ATTR_DRSTATUS,
    ATTR_FLOOR_AIR_LIMIT,
    ATTR_FLOOR_AUX,
    ATTR_FLOOR_MAX,
    ATTR_FLOOR_MIN,
    ATTR_FLOOR_MODE,
    ATTR_FLOOR_OUTPUT2,
    ATTR_FLOOR_SENSOR,
    ATTR_GFCI_ALERT,
    ATTR_GFCI_STATUS,
    ATTR_HEAT_LOCK_TEMP,
    ATTR_HEAT_LOCKOUT_TEMP,
    ATTR_KEYPAD,
    ATTR_OUTPUT_PERCENT_DISPLAY,
    ATTR_PUMP_PROTEC,
    ATTR_PUMP_PROTEC_DURATION,
    ATTR_PUMP_PROTEC_PERIOD,
    ATTR_ROOM_SETPOINT,
    ATTR_ROOM_SETPOINT_MAX,
    ATTR_ROOM_SETPOINT_MIN,
    ATTR_ROOM_TEMP_DISPLAY,
    ATTR_ROOM_TEMPERATURE,
    ATTR_RSSI,
    ATTR_SETPOINT,
    ATTR_SYSTEM_MODE,
    ATTR_TEMP,
    ATTR_TIME_FORMAT,
    ATTR_WATTAGE,
    DOMAIN,
    MODE_AUTO_BYPASS,
    MODE_MANUAL,
    ATTR_FLOOR_OUTPUT1,
    ATTR_OCCUPANCY,)
from ..helpers import safe_get_device_attributes, translated_or_default
from ..schema import CYCLE_LENGTH_VALUES
from ..schema import (
    CYCLE_LENGTH_VALUES,
)
from .base import (
    Neviweb130Thermostat,
    DEVICE_MODEL_HEAT_G2,
    DEVICE_MODEL_FLOOR,
    DEVICE_MODEL_LOW,
    DEVICE_MODEL_DOUBLE,
    SNOOZE_TIME,
    UPDATE_ATTRIBUTES,
    SUPPORTED_HVAC_MODES,
    PRESET_MODES,
    SUPPORT_FLAGS,
    SUPPORT_AUX_FLAGS,
    neviweb_to_ha,
    lock_to_ha,
)
from .mixins import FloorMixin, LowVoltageMixin

_LOGGER = logging.getLogger(__name__)

class Neviweb130G2Thermostat(Neviweb130Thermostat):
    """Implementation of Neviweb TH1123ZB-G2, TH1124ZB-G2 thermostats."""

    def __init__(self, device_info, name, sku, firmware, location, client):
        super().__init__(device_info, name, sku, firmware, location, client)
        self._cold_load_pickup = None

    @override
    def update(self) -> None:
        if self._active:
            GEN2_ATTRIBUTES = [
                ATTR_ROOM_TEMP_DISPLAY,
                ATTR_WATTAGE,
                ATTR_DISPLAY2,
                ATTR_KEYPAD,
                ATTR_BACKLIGHT,
                ATTR_SYSTEM_MODE,
                ATTR_CYCLE_LENGTH,
                ATTR_COLD_LOAD_PICKUP,
                ATTR_HEAT_LOCKOUT_TEMP,
            ]
            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            attributes = UPDATE_ATTRIBUTES + GEN2_ATTRIBUTES
            _LOGGER.debug(
                "Updated attributes for %s: %s",
                self._name,
                attributes,
            )
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
            neviweb_status = self._client.get_neviweb_status(self._location)
            end = time.time()
            elapsed = round(end - start, 3)
            _LOGGER.debug("Updating %s (%s sec): %s", self._name, elapsed, device_data)
            if "error" not in device_data:
                if "errorCode" not in device_data:
                    self._cur_temp_before = self._cur_temp
                    self._cur_temp = (
                        float(device_data[ATTR_ROOM_TEMPERATURE]["value"])
                        if device_data[ATTR_ROOM_TEMPERATURE]["value"] is not None
                        else self._cur_temp_before
                    )
                    self._target_temp = float(device_data[ATTR_ROOM_SETPOINT])
                    self._min_temp = device_data[ATTR_ROOM_SETPOINT_MIN]
                    self._max_temp = device_data[ATTR_ROOM_SETPOINT_MAX]
                    self._temperature_format = device_data[ATTR_TEMP]
                    self._time_format = device_data[ATTR_TIME_FORMAT]
                    self._temp_display_value = device_data[ATTR_ROOM_TEMP_DISPLAY]
                    self._display2 = device_data[ATTR_DISPLAY2]
                    if ATTR_DRSETPOINT in device_data:
                        self._drsetpoint_status = device_data[ATTR_DRSETPOINT]["status"]
                        self._drsetpoint_value = (
                            device_data[ATTR_DRSETPOINT]["value"]
                            if device_data[ATTR_DRSETPOINT]["value"] is not None
                            else 0
                        )
                    if ATTR_DRSTATUS in device_data:
                        self._drstatus_active = device_data[ATTR_DRSTATUS]["drActive"]
                        self._drstatus_optout = device_data[ATTR_DRSTATUS]["optOut"]
                        self._drstatus_setpoint = device_data[ATTR_DRSTATUS]["setpoint"]
                        self._drstatus_abs = device_data[ATTR_DRSTATUS]["powerAbsolute"]
                        self._drstatus_rel = device_data[ATTR_DRSTATUS]["powerRelative"]
                    if ATTR_COLD_LOAD_PICKUP in device_data:
                        self._cold_load_pickup = device_data[ATTR_COLD_LOAD_PICKUP]
                    if ATTR_HEAT_LOCKOUT_TEMP in device_data:
                        self._heat_lockout_temp = device_data[ATTR_HEAT_LOCKOUT_TEMP]
                    self._heat_level = device_data[ATTR_OUTPUT_PERCENT_DISPLAY]
                    self._keypad = device_data[ATTR_KEYPAD]
                    self._backlight = device_data[ATTR_BACKLIGHT]
                    if ATTR_CYCLE_LENGTH in device_data:
                        self._cycle_length = device_data[ATTR_CYCLE_LENGTH]
                    self._operation_mode = device_data[ATTR_SYSTEM_MODE]
                    self._wattage = device_data[ATTR_WATTAGE]
                elif device_data["errorCode"] == "ReadTimeout":
                    _LOGGER.warning(
                        "A timeout occur during data update. Device %s do not respond. Check your network... (%s)",
                        self._name,
                        device_data,
                    )
                else:
                    _LOGGER.warning("Error in updating device %s: (%s)", self._name, device_data)
            else:
                self.log_error(device_data["error"]["code"])
            self._occupancy_mode = neviweb_status[ATTR_OCCUPANCY]
            self.do_stat(start)
            self.get_sensor_error_code()
            self.get_weather()
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
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return the state attributes."""
        data = {}
        data.update(
            {
                "neviweb_occupancy_mode": self._occupancy_mode,
                "wattage": self._wattage,
                "cycle_length": neviweb_to_ha(self._cycle_length),
                "error_code": self._error_code,
                "heat_level": self._heat_level,
                "pi_heating_demand": self._heat_level,
                "icon_type": self.icon_type,
                "temp_display_value": self._temp_display_value,
                "second_display": self._display2,
                "keypad": lock_to_ha(self._keypad),
                "backlight": self._backlight,
                "time_format": self._time_format,
                "temperature_format": self._temperature_format,
                "setpoint_max": self._max_temp,
                "setpoint_min": self._min_temp,
                "eco_status": self._drstatus_active,
                "eco_optOut": self._drstatus_optout,
                "eco_setpoint": self._drstatus_setpoint,
                "eco_power_relative": self._drstatus_rel,
                "eco_power_absolute": self._drstatus_abs,
                "eco_setpoint_status": self._drsetpoint_status,
                "eco_setpoint_delta": self._drsetpoint_value,
                "cold_load_pickup": self._cold_load_pickup,
                "heat_lockout_temp": self._heat_lockout_temp,
                "total_kwh_count": self._total_kwh_count,
                "monthly_kwh_count": self._monthly_kwh_count,
                "daily_kwh_count": self._daily_kwh_count,
                "hourly_kwh_count": self._hourly_kwh_count,
                "hourly_kwh": self._hour_kwh,
                "daily_kwh": self._today_kwh,
                "monthly_kwh": self._month_kwh,
                "last_energy_stat_update": self._mark,
                "outdoor_temp": self._temperature,
                "weather_icon": self._weather_icon,
                "sku": self._sku,
                "device_model": str(self._device_model),
                "device_model_cfg": self._device_model_cfg,
                "firmware": self._firmware,
                "activation": self._active,
                "id": self._id,
            }
        )
        return data


class Neviweb130FloorThermostat(FloorMixin, Neviweb130Thermostat):
    """Implementation of Neviweb TH1300ZB, TH1320ZB-04, OTH3600-GA-ZB thermostat."""

    def __init__(self, device_info, name, sku, firmware, location, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, location, client)
        self._floor_air_limit_status = None
        self._floor_max_status = "off"
        self._floor_min_status = "off"
        self._gfci_alert = None
        self._gfci_status = None
        self._load2 = 0

    @override
    def update(self) -> None:
        if self._active:
            FLOOR_ATTRIBUTES = [
                ATTR_ROOM_TEMP_DISPLAY,
                ATTR_WATTAGE,
                ATTR_GFCI_STATUS,
                ATTR_GFCI_ALERT,
                ATTR_FLOOR_MODE,
                ATTR_FLOOR_AUX,
                ATTR_FLOOR_OUTPUT2,
                ATTR_FLOOR_AIR_LIMIT,
                ATTR_FLOOR_SENSOR,
                ATTR_FLOOR_MAX,
                ATTR_FLOOR_MIN,
                ATTR_KEYPAD,
                ATTR_BACKLIGHT,
                ATTR_SYSTEM_MODE,
                ATTR_CYCLE_LENGTH,
                ATTR_DISPLAY2,
                ATTR_RSSI,
            ]
            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            attributes = UPDATE_ATTRIBUTES + FLOOR_ATTRIBUTES
            _LOGGER.debug(
                "Updated attributes for %s: %s",
                self._name,
                attributes,
            )
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
            neviweb_status = self._client.get_neviweb_status(self._location)
            end = time.time()
            elapsed = round(end - start, 3)
            _LOGGER.debug("Updating %s (%s sec): %s", self._name, elapsed, device_data)
            if "error" not in device_data:
                if "errorCode" not in device_data:
                    self._cur_temp_before = self._cur_temp
                    self._cur_temp = (
                        float(device_data[ATTR_ROOM_TEMPERATURE]["value"])
                        if device_data[ATTR_ROOM_TEMPERATURE]["value"] is not None
                        else self._cur_temp_before
                    )
                    self._target_temp = float(device_data[ATTR_ROOM_SETPOINT])
                    self._min_temp = device_data[ATTR_ROOM_SETPOINT_MIN]
                    self._max_temp = device_data[ATTR_ROOM_SETPOINT_MAX]
                    self._temperature_format = device_data[ATTR_TEMP]
                    self._time_format = device_data[ATTR_TIME_FORMAT]
                    self._temp_display_value = device_data[ATTR_ROOM_TEMP_DISPLAY]
                    self._display2 = device_data[ATTR_DISPLAY2]
                    if ATTR_DRSETPOINT in device_data:
                        self._drsetpoint_status = device_data[ATTR_DRSETPOINT]["status"]
                        self._drsetpoint_value = (
                            device_data[ATTR_DRSETPOINT]["value"]
                            if device_data[ATTR_DRSETPOINT]["value"] is not None
                            else 0
                        )
                    if ATTR_DRSTATUS in device_data:
                        self._drstatus_active = device_data[ATTR_DRSTATUS]["drActive"]
                        self._drstatus_optout = device_data[ATTR_DRSTATUS]["optOut"]
                        self._drstatus_setpoint = device_data[ATTR_DRSTATUS]["setpoint"]
                        self._drstatus_abs = device_data[ATTR_DRSTATUS]["powerAbsolute"]
                        self._drstatus_rel = device_data[ATTR_DRSTATUS]["powerRelative"]
                    self._heat_level = device_data[ATTR_OUTPUT_PERCENT_DISPLAY]
                    self._keypad = device_data[ATTR_KEYPAD]
                    self._backlight = device_data[ATTR_BACKLIGHT]
                    if ATTR_CYCLE_LENGTH in device_data:
                        self._cycle_length = device_data[ATTR_CYCLE_LENGTH]
                    if ATTR_RSSI in device_data:
                        self._rssi = device_data[ATTR_RSSI]
                    self._operation_mode = device_data[ATTR_SYSTEM_MODE]
                    self._wattage = device_data[ATTR_WATTAGE]
                    self._gfci_status = device_data[ATTR_GFCI_STATUS]
                    self._floor_mode = device_data[ATTR_FLOOR_MODE]
                    self._em_heat = device_data[ATTR_FLOOR_AUX]
                    self._floor_air_limit = device_data[ATTR_FLOOR_AIR_LIMIT]["value"]
                    self._floor_air_limit_status = device_data[ATTR_FLOOR_AIR_LIMIT]["status"]
                    self._floor_sensor_type = device_data[ATTR_FLOOR_SENSOR]
                    if ATTR_FLOOR_MAX in device_data:
                        self._floor_max = device_data[ATTR_FLOOR_MAX]["value"]
                        self._floor_max_status = device_data[ATTR_FLOOR_MAX]["status"]
                    if ATTR_FLOOR_MIN in device_data:
                        self._floor_min = device_data[ATTR_FLOOR_MIN]["value"]
                        self._floor_min_status = device_data[ATTR_FLOOR_MIN]["status"]
                    self._load2_status = device_data[ATTR_FLOOR_OUTPUT2]["status"]
                    if device_data[ATTR_FLOOR_OUTPUT2]["status"] == "on":
                        self._load2 = device_data[ATTR_FLOOR_OUTPUT2]["value"]
                    else:
                        self._load2 = 0
                    self._gfci_alert = device_data[ATTR_GFCI_ALERT]
                elif device_data["errorCode"] == "ReadTimeout":
                    _LOGGER.warning(
                        "A timeout occur during data update. Device %s do not respond. Check your network... (%s)",
                        self._name,
                        device_data,
                    )
                else:
                    _LOGGER.warning("Error in updating device %s: (%s)", self._name, device_data)
            else:
                self.log_error(device_data["error"]["code"])
            self._occupancy_mode = neviweb_status[ATTR_OCCUPANCY]
            self.do_stat(start)
            self.get_sensor_error_code()
            self.get_weather()
        else:
            if time.time() - self._snooze > SNOOZE_TIME:
                self._active = True
                if NOTIFY == "notification" or NOTIFY == "both":
                    self.notify_ha(
                        translated_or_default(
                            self.hass,
                            "update_restarted",
                            "Warning: Neviweb Device update restarted for {self._name}, Sku: {self._sku}.",
                            name=self._name,
                            sku=self._sku,
                        )
                    )

    @property
    @override
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return the state attributes."""
        data = {}
        data.update(
            {
                "neviweb_occupancy_mode": self._occupancy_mode,
                "wattage": self._wattage,
                "gfci_status": self._gfci_status,
                "gfci_alert": self._gfci_alert,
                "sensor_mode": self._floor_mode,
                "auxiliary_heat": self._em_heat,
                "emergency_heating": self.is_em_heat,
                "auxiliary_status": self._load2_status,
                "auxiliary_load": self._load2,
                "floor_setpoint_max": self._floor_max,
                "floor_setpoint_low": self._floor_min,
                "floor_air_limit": self._floor_air_limit,
                "floor_sensor_type": self._floor_sensor_type,
                "load_watt": self._wattage,
                "error_code": self._error_code,
                "heat_level": self._heat_level,
                "pi_heating_demand": self._heat_level,
                "icon_type": self.icon_type,
                "cycle_length": neviweb_to_ha(self._cycle_length),
                "temp_display_value": self._temp_display_value,
                "second_display": self._display2,
                "keypad": lock_to_ha(self._keypad),
                "backlight": self._backlight,
                "time_format": self._time_format,
                "temperature_format": self._temperature_format,
                "setpoint_max": self._max_temp,
                "setpoint_min": self._min_temp,
                "eco_status": self._drstatus_active,
                "eco_optOut": self._drstatus_optout,
                "eco_setpoint": self._drstatus_setpoint,
                "eco_power_relative": self._drstatus_rel,
                "eco_power_absolute": self._drstatus_abs,
                "eco_setpoint_status": self._drsetpoint_status,
                "eco_setpoint_delta": self._drsetpoint_value,
                "total_kwh_count": self._total_kwh_count,
                "monthly_kwh_count": self._monthly_kwh_count,
                "daily_kwh_count": self._daily_kwh_count,
                "hourly_kwh_count": self._hourly_kwh_count,
                "hourly_kwh": self._hour_kwh,
                "daily_kwh": self._today_kwh,
                "monthly_kwh": self._month_kwh,
                "last_energy_stat_update": self._mark,
                "outdoor_temp": self._temperature,
                "weather_icon": self._weather_icon,
                "rssi": self._rssi,
                "sku": self._sku,
                "device_model": str(self._device_model),
                "device_model_cfg": self._device_model_cfg,
                "firmware": self._firmware,
                "activation": self._active,
                "id": self._id,
            }
        )
        return data


class Neviweb130LowThermostat(LowVoltageMixin, Neviweb130Thermostat):
    """Implementation of Neviweb TH1400ZB thermostat."""

    def __init__(self, device_info, name, sku, firmware, location, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, location, client)
        self._floor_air_limit_status = "off"
        self._floor_max_status = "off"
        self._floor_min_status = "off"
        self._load1 = 0
        self._load1_status = "off"
        self._load2 = 0
        self._pump_protec_period_status = "off"

    @override
    def update(self) -> None:
        if self._active:
            LOW_VOLTAGE_ATTRIBUTES = [
                ATTR_ROOM_TEMP_DISPLAY,
                ATTR_KEYPAD,
                ATTR_BACKLIGHT,
                ATTR_SYSTEM_MODE,
                ATTR_CYCLE_LENGTH,
                ATTR_DISPLAY2,
                ATTR_RSSI,
                ATTR_PUMP_PROTEC_DURATION,
                ATTR_PUMP_PROTEC_PERIOD,
                ATTR_FLOOR_AIR_LIMIT,
                ATTR_FLOOR_MODE,
                ATTR_FLOOR_SENSOR,
                ATTR_FLOOR_MAX,
                ATTR_FLOOR_MIN,
                ATTR_CYCLE_OUTPUT2,
                ATTR_FLOOR_OUTPUT1,
                ATTR_FLOOR_OUTPUT2,
            ]
            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            attributes = UPDATE_ATTRIBUTES + LOW_VOLTAGE_ATTRIBUTES
            _LOGGER.debug(
                "Updated attributes for %s: %s",
                self._name,
                attributes,
            )
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
            neviweb_status = self._client.get_neviweb_status(self._location)
            end = time.time()
            elapsed = round(end - start, 3)
            _LOGGER.debug("Updating %s (%s sec): %s", self._name, elapsed, device_data)

            if "error" not in device_data:
                if "errorCode" not in device_data:
                    self._cur_temp_before = self._cur_temp
                    self._cur_temp = (
                        float(device_data[ATTR_ROOM_TEMPERATURE]["value"])
                        if device_data[ATTR_ROOM_TEMPERATURE]["value"] is not None
                        else self._cur_temp_before
                    )
                    self._target_temp = float(device_data[ATTR_ROOM_SETPOINT])
                    self._min_temp = device_data[ATTR_ROOM_SETPOINT_MIN]
                    self._max_temp = device_data[ATTR_ROOM_SETPOINT_MAX]
                    self._temperature_format = device_data[ATTR_TEMP]
                    self._time_format = device_data[ATTR_TIME_FORMAT]
                    self._temp_display_value = device_data[ATTR_ROOM_TEMP_DISPLAY]
                    self._display2 = device_data[ATTR_DISPLAY2]
                    self._heat_level = device_data[ATTR_OUTPUT_PERCENT_DISPLAY]
                    self._keypad = device_data[ATTR_KEYPAD]
                    self._backlight = device_data[ATTR_BACKLIGHT]
                    if ATTR_DRSETPOINT in device_data:
                        self._drsetpoint_status = device_data[ATTR_DRSETPOINT]["status"]
                        self._drsetpoint_value = (
                            device_data[ATTR_DRSETPOINT]["value"]
                            if device_data[ATTR_DRSETPOINT]["value"] is not None
                            else 0
                        )
                    if ATTR_DRSTATUS in device_data:
                        self._drstatus_active = device_data[ATTR_DRSTATUS]["drActive"]
                        self._drstatus_optout = device_data[ATTR_DRSTATUS]["optOut"]
                        self._drstatus_setpoint = device_data[ATTR_DRSTATUS]["setpoint"]
                        self._drstatus_abs = device_data[ATTR_DRSTATUS]["powerAbsolute"]
                        self._drstatus_rel = device_data[ATTR_DRSTATUS]["powerRelative"]
                    if ATTR_CYCLE_LENGTH in device_data:
                        self._cycle_length = device_data[ATTR_CYCLE_LENGTH]
                    if ATTR_RSSI in device_data:
                        self._rssi = device_data[ATTR_RSSI]
                    self._operation_mode = device_data[ATTR_SYSTEM_MODE]
                    self._floor_mode = device_data[ATTR_FLOOR_MODE]
                    self._floor_air_limit = device_data[ATTR_FLOOR_AIR_LIMIT]["value"]
                    self._floor_air_limit_status = device_data[ATTR_FLOOR_AIR_LIMIT]["status"]
                    self._cycle_length_output2_status = device_data[ATTR_CYCLE_OUTPUT2]["status"]
                    self._cycle_length_output2_value = (
                        int(device_data[ATTR_CYCLE_OUTPUT2]["value"])
                        if device_data[ATTR_CYCLE_OUTPUT2]["value"] is not None
                        else 0
                    )
                    self._floor_max = device_data[ATTR_FLOOR_MAX]["value"]
                    self._floor_max_status = device_data[ATTR_FLOOR_MAX]["status"]
                    self._floor_min = device_data[ATTR_FLOOR_MIN]["value"]
                    self._floor_min_status = device_data[ATTR_FLOOR_MIN]["status"]
                    self._pump_protec_status = device_data[ATTR_PUMP_PROTEC_DURATION]["status"]
                    self._pump_protec_duration = device_data[ATTR_PUMP_PROTEC_DURATION]["value"]
                    self._pump_protec_period = device_data[ATTR_PUMP_PROTEC_PERIOD]["value"]
                    self._pump_protec_period_status = device_data[ATTR_PUMP_PROTEC_PERIOD]["status"]
                    self._floor_sensor_type = device_data[ATTR_FLOOR_SENSOR]
                    if ATTR_FLOOR_OUTPUT1 in device_data:
                        self._load1_status = device_data[ATTR_FLOOR_OUTPUT1]["status"]
                        if device_data[ATTR_FLOOR_OUTPUT1]["status"] == "on":
                            self._load1 = device_data[ATTR_FLOOR_OUTPUT1]["value"]
                    if ATTR_FLOOR_OUTPUT2 in device_data:
                        self._load2_status = device_data[ATTR_FLOOR_OUTPUT2]["status"]
                        if device_data[ATTR_FLOOR_OUTPUT2]["status"] == "on":
                            self._load2 = device_data[ATTR_FLOOR_OUTPUT2]["value"]
                elif device_data["errorCode"] == "ReadTimeout":
                    _LOGGER.warning(
                        "A timeout occur during data update. Device %s do not respond. Check your network... (%s)",
                        self._name,
                        device_data,
                    )
                else:
                    _LOGGER.warning("Error updating device %s: (%s)", self._name, device_data)
            else:
                self.log_error(device_data["error"]["code"])
            self._occupancy_mode = neviweb_status[ATTR_OCCUPANCY]
            self.do_stat(start)
            self.get_sensor_error_code()
            self.get_weather()
        else:
            if time.time() - self._snooze > SNOOZE_TIME:
                self._active = True
                if NOTIFY == "notification" or NOTIFY == "both":
                    self.notify_ha(
                        translated_or_default(
                            self.hass,
                            "update_restarted",
                            "Warning: Neviweb Device update restarted for {self._name}, Sku: {self._sku}.",
                            name=self._name,
                            sku=self._sku,
                        )
                    )

    @property
    @override
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return the state attributes."""
        data = {}
        data.update(
            {
                "neviweb_occupancy_mode": self._occupancy_mode,
                "sensor_mode": self._floor_mode,
                "cycle_length": neviweb_to_ha(self._cycle_length),
                "auxiliary_cycle_status": self._cycle_length_output2_status,
                "auxiliary_cycle_value": neviweb_to_ha(self._cycle_length_output2_value),
                "emergency_heating": self.is_em_heat,
                "floor_limit_high": self._floor_max,
                "floor_limit_high_status": self._floor_max_status,
                "floor_limit_low": self._floor_min,
                "floor_limit_low_status": self._floor_min_status,
                "max_air_limit": self._floor_air_limit,
                "max_air_limit_status": self._floor_air_limit_status,
                "floor_sensor_type": self._floor_sensor_type,
                "pump_protection_status": self._pump_protec_status,
                "pump_protection_duration": self._pump_protec_duration,
                "pump_protection_frequency": self._pump_protec_period,
                "pump_protection_frequency_status": self._pump_protec_period_status,
                "error_code": self._error_code,
                "heat_level": self._heat_level,
                "pi_heating_demand": self._heat_level,
                "icon_type": self.icon_type,
                "temp_display_value": self._temp_display_value,
                "second_display": self._display2,
                "keypad": lock_to_ha(self._keypad),
                "backlight": self._backlight,
                "time_format": self._time_format,
                "temperature_format": self._temperature_format,
                "setpoint_max": self._max_temp,
                "setpoint_min": self._min_temp,
                "cycle_length_output": self._load1,
                "cycle_length_output_2": self._load2,
                "cycle_length_output_status": self._load1_status,
                "cycle_length_output_2_status": self._load2_status,
                "eco_status": self._drstatus_active,
                "eco_optOut": self._drstatus_optout,
                "eco_setpoint": self._drstatus_setpoint,
                "eco_power_relative": self._drstatus_rel,
                "eco_power_absolute": self._drstatus_abs,
                "eco_setpoint_status": self._drsetpoint_status,
                "eco_setpoint_delta": self._drsetpoint_value,
                "total_kwh_count": self._total_kwh_count,
                "monthly_kwh_count": self._monthly_kwh_count,
                "daily_kwh_count": self._daily_kwh_count,
                "hourly_kwh_count": self._hourly_kwh_count,
                "hourly_kwh": self._hour_kwh,
                "daily_kwh": self._today_kwh,
                "monthly_kwh": self._month_kwh,
                "last_energy_stat_update": self._mark,
                "outdoor_temp": self._temperature,
                "weather_icon": self._weather_icon,
                "rssi": self._rssi,
                "sku": self._sku,
                "device_model": str(self._device_model),
                "device_model_cfg": self._device_model_cfg,
                "firmware": self._firmware,
                "activation": self._active,
                "id": self._id,
            }
        )
        return data


class Neviweb130DoubleThermostat(Neviweb130Thermostat):
    """Implementation of Neviweb TH1500ZB thermostat."""

    @override
    def update(self) -> None:
        if self._active:
            DOUBLE_ATTRIBUTES = [
                ATTR_ROOM_TEMP_DISPLAY,
                ATTR_KEYPAD,
                ATTR_BACKLIGHT,
                ATTR_SYSTEM_MODE,
                ATTR_CYCLE_LENGTH,
                ATTR_DISPLAY2,
                ATTR_RSSI,
                ATTR_WATTAGE,
            ]
            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            attributes = UPDATE_ATTRIBUTES + DOUBLE_ATTRIBUTES
            _LOGGER.debug(
                "Updated attributes for %s: %s",
                self._name,
                attributes,
            )
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
            neviweb_status = self._client.get_neviweb_status(self._location)
            end = time.time()
            elapsed = round(end - start, 3)
            _LOGGER.debug("Updating %s (%s sec): %s", self._name, elapsed, device_data)

            if "error" not in device_data:
                if "errorCode" not in device_data:
                    self._cur_temp_before = self._cur_temp
                    self._cur_temp = (
                        float(device_data[ATTR_ROOM_TEMPERATURE]["value"])
                        if device_data[ATTR_ROOM_TEMPERATURE]["value"] is not None
                        else self._cur_temp_before
                    )
                    self._target_temp = float(device_data[ATTR_ROOM_SETPOINT])
                    self._min_temp = device_data[ATTR_ROOM_SETPOINT_MIN]
                    self._max_temp = device_data[ATTR_ROOM_SETPOINT_MAX]
                    self._temperature_format = device_data[ATTR_TEMP]
                    self._time_format = device_data[ATTR_TIME_FORMAT]
                    self._temp_display_value = device_data[ATTR_ROOM_TEMP_DISPLAY]
                    self._display2 = device_data[ATTR_DISPLAY2]
                    if ATTR_DRSETPOINT in device_data:
                        self._drsetpoint_status = device_data[ATTR_DRSETPOINT]["status"]
                        self._drsetpoint_value = (
                            device_data[ATTR_DRSETPOINT]["value"]
                            if device_data[ATTR_DRSETPOINT]["value"] is not None
                            else 0
                        )
                    if ATTR_DRSTATUS in device_data:
                        self._drstatus_active = device_data[ATTR_DRSTATUS]["drActive"]
                        self._drstatus_optout = device_data[ATTR_DRSTATUS]["optOut"]
                        self._drstatus_setpoint = device_data[ATTR_DRSTATUS]["setpoint"]
                        self._drstatus_abs = device_data[ATTR_DRSTATUS]["powerAbsolute"]
                        self._drstatus_rel = device_data[ATTR_DRSTATUS]["powerRelative"]
                    self._heat_level = device_data[ATTR_OUTPUT_PERCENT_DISPLAY]
                    self._keypad = device_data[ATTR_KEYPAD]
                    self._backlight = device_data[ATTR_BACKLIGHT]
                    if ATTR_CYCLE_LENGTH in device_data:
                        self._cycle_length = device_data[ATTR_CYCLE_LENGTH]
                    if ATTR_RSSI in device_data:
                        self._rssi = device_data[ATTR_RSSI]
                    self._operation_mode = device_data[ATTR_SYSTEM_MODE]
                    self._wattage = device_data[ATTR_WATTAGE]
                elif device_data["errorCode"] == "ReadTimeout":
                    _LOGGER.warning(
                        "A timeout occur during data update. Device %s do not respond. Check your network... (%s)",
                        self._name,
                        device_data,
                    )
                else:
                    _LOGGER.warning("Error in updating device %s: (%s)", self._name, device_data)
            else:
                self.log_error(device_data["error"]["code"])
            self._occupancy_mode = neviweb_status[ATTR_OCCUPANCY]
            self.do_stat(start)
            self.get_sensor_error_code()
            self.get_weather()
        else:
            if time.time() - self._snooze > SNOOZE_TIME:
                self._active = True
                if NOTIFY == "notification" or NOTIFY == "both":
                    self.notify_ha(
                        translated_or_default(
                            self.hass,
                            "update_restarted",
                            "Warning: Neviweb Device update restarted for {self._name}, Sku: {self._sku}.",
                            name=self._name,
                            sku=self._sku,
                        )
                    )

    @property
    @override
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return the state attributes."""
        data = {}
        data.update(
            {
                "neviweb_occupancy_mode": self._occupancy_mode,
                "wattage": self._wattage,
                "cycle_length": neviweb_to_ha(self._cycle_length),
                "error_code": self._error_code,
                "heat_level": self._heat_level,
                "pi_heating_demand": self._heat_level,
                "icon_type": self.icon_type,
                "temp_display_value": self._temp_display_value,
                "second_display": self._display2,
                "keypad": lock_to_ha(self._keypad),
                "backlight": self._backlight,
                "time_format": self._time_format,
                "temperature_format": self._temperature_format,
                "setpoint_max": self._max_temp,
                "setpoint_min": self._min_temp,
                "eco_status": self._drstatus_active,
                "eco_optOut": self._drstatus_optout,
                "eco_setpoint": self._drstatus_setpoint,
                "eco_power_relative": self._drstatus_rel,
                "eco_power_absolute": self._drstatus_abs,
                "eco_setpoint_status": self._drsetpoint_status,
                "eco_setpoint_delta": self._drsetpoint_value,
                "total_kwh_count": self._total_kwh_count,
                "monthly_kwh_count": self._monthly_kwh_count,
                "daily_kwh_count": self._daily_kwh_count,
                "hourly_kwh_count": self._hourly_kwh_count,
                "hourly_kwh": self._hour_kwh,
                "daily_kwh": self._today_kwh,
                "monthly_kwh": self._month_kwh,
                "last_energy_stat_update": self._mark,
                "outdoor_temp": self._temperature,
                "weather_icon": self._weather_icon,
                "rssi": self._rssi,
                "sku": self._sku,
                "device_model": str(self._device_model),
                "device_model_cfg": self._device_model_cfg,
                "firmware": self._firmware,
                "activation": self._active,
                "id": self._id,
            }
        )
        return data


