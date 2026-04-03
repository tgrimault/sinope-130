"""Wi-Fi thermostat subclasses for neviweb130 climate platform."""
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
    ATTR_BACKLIGHT_AUTO_DIM,
    ATTR_COLD_LOAD_PICKUP,
    ATTR_CYCLE_LENGTH,
    ATTR_CYCLE_OUTPUT2,
    ATTR_DISPLAY2,
    ATTR_DRSETPOINT,
    ATTR_DRSTATUS,
    ATTR_EARLY_START,
    ATTR_FLOOR_AIR_LIMIT,
    ATTR_FLOOR_AUX,
    ATTR_FLOOR_MAX,
    ATTR_FLOOR_MIN,
    ATTR_FLOOR_MODE,
    ATTR_FLOOR_OUTPUT2,
    ATTR_FLOOR_SENSOR,
    ATTR_GFCI_ALERT,
    ATTR_GFCI_STATUS,
    ATTR_KEYPAD,
    ATTR_OUTPUT_PERCENT_DISPLAY,
    ATTR_PUMP_PROTEC,
    ATTR_PUMP_PROTEC_DURATION,
    ATTR_PUMP_PROTEC_PERIOD,
    ATTR_ROOM_SETPOINT,
    ATTR_ROOM_SETPOINT_AWAY,
    ATTR_ROOM_SETPOINT_MAX,
    ATTR_ROOM_SETPOINT_MIN,
    ATTR_ROOM_TEMP_DISPLAY,
    ATTR_ROOM_TEMPERATURE,
    ATTR_RSSI,
    ATTR_SETPOINT_MODE,
    ATTR_SYSTEM_MODE,
    ATTR_TEMP,
    ATTR_TIME_FORMAT,
    ATTR_WIFI,
    ATTR_WIFI_KEYPAD,
    ATTR_WIFI_WATTAGE,
    DOMAIN,
    MODE_MANUAL,
    ATTR_AUX_CYCLE_LENGTH,
    ATTR_FLOOR_OUTPUT1,
    ATTR_INTERLOCK_HC_MODE,
    ATTR_INTERLOCK_ID,
    ATTR_INTERLOCK_PARTNER,
    ATTR_LANGUAGE,
    ATTR_OCCUPANCY,
    ATTR_OUTPUT1,)
from ..helpers import safe_get_device_attributes, translated_or_default
from ..schema import CYCLE_LENGTH_VALUES
from ..schema import (
    CYCLE_LENGTH_VALUES,
)
from .base import (
    Neviweb130Thermostat,
    DEVICE_MODEL_WIFI,
    DEVICE_MODEL_WIFI_LITE,
    DEVICE_MODEL_COLOR_WIFI,
    DEVICE_MODEL_LOW_WIFI,
    DEVICE_MODEL_WIFI_FLOOR,
    SNOOZE_TIME,
    UPDATE_ATTRIBUTES,
    UPDATE_LITE_ATTRIBUTES,
    SUPPORTED_HVAC_WIFI_MODES,
    SUPPORTED_HVAC_WIFI_LITE_MODES,
    PRESET_WIFI_MODES,
    PRESET_MODES,
    SUPPORT_FLAGS,
    SUPPORT_AUX_FLAGS,
    neviweb_to_ha,
    lock_to_ha,
)
from .mixins import _BlockedMethod, FloorMixin, LowVoltageMixin

_LOGGER = logging.getLogger(__name__)

class Neviweb130WifiThermostat(Neviweb130Thermostat):
    """Implementation of Neviweb TH1123WF, TH1124WF, TH1500WF thermostats."""

    # ISP: floor-specific methods must not be accessible on Wi-Fi thermostats
    set_sensor_type = _BlockedMethod()

    def __init__(self, device_info, name, sku, firmware, location, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, location, client)
        self._early_start = "off"
        self._heat_source_type = None
        self._load1 = 0
        self._room_temp_error = None
        self._room_temp_error = None
        self._target_temp_away = None
        self._temp_display_status = None

    @override
    def update(self) -> None:
        if self._active:
            WIFI_ATTRIBUTES = [
                ATTR_ROOM_TEMP_DISPLAY,
                ATTR_CYCLE_LENGTH,
                ATTR_FLOOR_OUTPUT1,
                ATTR_WIFI_WATTAGE,
                ATTR_WIFI,
                ATTR_WIFI_KEYPAD,
                ATTR_DISPLAY2,
                ATTR_SETPOINT_MODE,
                ATTR_OCCUPANCY,
                ATTR_BACKLIGHT_AUTO_DIM,
                ATTR_EARLY_START,
                ATTR_ROOM_SETPOINT_AWAY,
            ]
            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            attributes = UPDATE_ATTRIBUTES + WIFI_ATTRIBUTES
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
                    self._room_temp_error = device_data[ATTR_ROOM_TEMPERATURE]["error"]
                    self._target_temp = float(device_data[ATTR_ROOM_SETPOINT])
                    self._min_temp = device_data[ATTR_ROOM_SETPOINT_MIN]
                    self._max_temp = device_data[ATTR_ROOM_SETPOINT_MAX]
                    self._temperature_format = device_data[ATTR_TEMP]
                    self._time_format = device_data[ATTR_TIME_FORMAT]
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
                        self._drstatus_onoff = device_data[ATTR_DRSTATUS]["onOff"]
                    self._heat_level = device_data[ATTR_OUTPUT_PERCENT_DISPLAY]["percent"]
                    self._heat_source_type = device_data[ATTR_OUTPUT_PERCENT_DISPLAY]["sourceType"]
                    self._operation_mode = device_data[ATTR_SETPOINT_MODE]
                    self._occupancy = device_data[ATTR_OCCUPANCY]
                    self._keypad = device_data[ATTR_WIFI_KEYPAD]
                    self._rssi = device_data[ATTR_WIFI]
                    self._backlight = device_data[ATTR_BACKLIGHT_AUTO_DIM]
                    self._early_start = device_data[ATTR_EARLY_START]
                    self._target_temp_away = device_data[ATTR_ROOM_SETPOINT_AWAY]
                    self._load1 = device_data[ATTR_FLOOR_OUTPUT1]
                    if ATTR_WIFI_WATTAGE in device_data:
                        self._wattage = device_data[ATTR_WIFI_WATTAGE]
                    if ATTR_CYCLE_LENGTH in device_data:
                        self._cycle_length = device_data[ATTR_CYCLE_LENGTH]
                    if ATTR_ROOM_TEMP_DISPLAY in device_data:
                        self._temp_display_status = device_data[ATTR_ROOM_TEMP_DISPLAY]["status"]
                        self._temp_display_value = device_data[ATTR_ROOM_TEMP_DISPLAY]["value"]
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
                "occupancy": self._occupancy,
                "temp_display_status": self._temp_display_status,
                "temp_display_error": self._room_temp_error,
                "source_type": self._heat_source_type,
                "early_start": self._early_start,
                "setpoint_away": self._target_temp_away,
                "load_watt_1": self._load1,
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
                "eco_onOff": self._drstatus_onoff,
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

    def set_cool_setpoint_max(self, value):
        """Set maximum cooling setpoint temperature."""
        self._client.set_cool_setpoint_max(value["id"], value["temp"])
        self._cool_max = value["temp"]

    def set_cool_setpoint_min(self, value):
        """Set minimum cooling setpoint temperature."""
        self._client.set_cool_setpoint_min(value["id"], value["temp"])
        self._cool_min = value["temp"]


class Neviweb130WifiLiteThermostat(Neviweb130Thermostat):
    """Implementation of Neviweb TH1133WF, TH1133CR, TH1134WF, TH1134CR and THEWF01 thermostats."""

    _attr_precision = 1.0
    _attr_target_temperature_step = 1.0

    def __init__(self, device_info, name, sku, firmware, location, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, location, client)
        self._early_start = "off"
        self._heat_source_type = None
        self._load1 = 0
        self._room_temp_error = None
        self._target_temp_away = None
        self._temp_display_status = None
        self._interlock_id = None
        self._interlock_partner = None
        self._interlock_hc_mode = None

    @override
    def update(self) -> None:
        if self._active:
            LITE_ATTRIBUTES = [
                ATTR_ROOM_TEMP_DISPLAY,
                ATTR_CYCLE_LENGTH,
                ATTR_OUTPUT1,
                ATTR_WIFI,
                ATTR_WIFI_KEYPAD,
                ATTR_SETPOINT_MODE,
                ATTR_OCCUPANCY,
                ATTR_BACKLIGHT_AUTO_DIM,
                ATTR_EARLY_START,
                ATTR_ROOM_SETPOINT_AWAY,
                ATTR_INTERLOCK_PARTNER,
                ATTR_INTERLOCK_ID,
                ATTR_INTERLOCK_HC_MODE,
            ]
            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            attributes = UPDATE_LITE_ATTRIBUTES + LITE_ATTRIBUTES
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
                    self._room_temp_error = device_data[ATTR_ROOM_TEMPERATURE]["error"]
                    self._target_temp = float(device_data[ATTR_ROOM_SETPOINT])
                    self._min_temp = device_data[ATTR_ROOM_SETPOINT_MIN]
                    self._max_temp = device_data[ATTR_ROOM_SETPOINT_MAX]
                    self._temperature_format = device_data[ATTR_TEMP]
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
                        self._drstatus_onoff = device_data[ATTR_DRSTATUS]["onOff"]
                    self._heat_level = device_data.get(ATTR_OUTPUT_PERCENT_DISPLAY, {}).get("percent")
                    source_info = device_data.get(ATTR_OUTPUT_PERCENT_DISPLAY, {})
                    if isinstance(source_info, dict) and "sourceType" in source_info:
                        self._heat_source_type = source_info["sourceType"]
                    self._operation_mode = device_data[ATTR_SETPOINT_MODE]
                    self._occupancy = device_data[ATTR_OCCUPANCY]
                    self._keypad = device_data[ATTR_WIFI_KEYPAD]
                    self._rssi = device_data[ATTR_WIFI]
                    self._backlight = device_data[ATTR_BACKLIGHT_AUTO_DIM]
                    self._early_start = device_data[ATTR_EARLY_START]
                    self._target_temp_away = device_data[ATTR_ROOM_SETPOINT_AWAY]
                    self._load1 = device_data[ATTR_OUTPUT1]
                    if ATTR_CYCLE_LENGTH in device_data:
                        self._cycle_length = device_data[ATTR_CYCLE_LENGTH]
                    if ATTR_ROOM_TEMP_DISPLAY in device_data:
                        self._temp_display_status = device_data[ATTR_ROOM_TEMP_DISPLAY]["status"]
                        self._temp_display_value = device_data[ATTR_ROOM_TEMP_DISPLAY]["value"]
                    if ATTR_INTERLOCK_ID in device_data:
                        self._interlock_id = device_data[ATTR_INTERLOCK_ID]
                        self._interlock_partner = device_data[ATTR_INTERLOCK_PARTNER]
                        self._interlock_hc_mode = device_data[ATTR_INTERLOCK_HC_MODE]

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
            if (
                self._sku != "TH1133WF"
                and self._sku != "TH1133CR"
                and self._sku != "TH1134WF"
                and self._sku != "TH1134CR"
            ):
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
                "occupancy": self._occupancy,
                "temp_display_status": self._temp_display_status,
                "temp_display_error": self._room_temp_error,
                "source_type": self._heat_source_type,
                "early_start": self._early_start,
                "setpoint_away": self._target_temp_away,
                "load_watt_1": self._load1,
                "cycle_length": neviweb_to_ha(self._cycle_length),
                "error_code": self._error_code,
                "heat_level": self._heat_level,
                "pi_heating_demand": self._heat_level,
                "icon_type": self.icon_type,
                "temp_display_value": self._temp_display_value,
                "keypad": lock_to_ha(self._keypad),
                "backlight": self._backlight,
                "temperature_format": self._temperature_format,
                "setpoint_max": self._max_temp,
                "setpoint_min": self._min_temp,
                "eco_status": self._drstatus_active,
                "eco_optOut": self._drstatus_optout,
                "eco_setpoint": self._drstatus_setpoint,
                "eco_power_relative": self._drstatus_rel,
                "eco_power_absolute": self._drstatus_abs,
                "eco_onOff": self._drstatus_onoff,
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
                "interlock_id": self._interlock_id,
                "interlock_partner": self._interlock_partner,
                "interlock_hc_mode": self._interlock_hc_mode,
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


class Neviweb130ColorWifiThermostat(Neviweb130Thermostat):
    """Implementation of Neviweb TH1143WF, TH1144WF thermostats."""

    _attr_precision = 0.5
    _attr_target_temperature_step = 0.5

    def __init__(self, device_info, name, sku, firmware, location, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, location, client)
        self._early_start = "off"
        self._heat_source_type = None
        self._load1 = 0
        self._room_temp_error = None
        self._target_temp_away = None
        self._temp_display_status = None

    @override
    def update(self) -> None:
        if self._active:
            LITE_ATTRIBUTES = [
                ATTR_ROOM_TEMP_DISPLAY,
                ATTR_OUTPUT1,
                ATTR_WIFI,
                ATTR_WIFI_KEYPAD,
                ATTR_SETPOINT_MODE,
                ATTR_OCCUPANCY,
                ATTR_BACKLIGHT_AUTO_DIM,
                ATTR_EARLY_START,
                ATTR_ROOM_SETPOINT_AWAY,
                ATTR_LANGUAGE,
            ]
            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            attributes = UPDATE_ATTRIBUTES + LITE_ATTRIBUTES
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
                    self._room_temp_error = device_data[ATTR_ROOM_TEMPERATURE]["error"]
                    self._target_temp = float(device_data[ATTR_ROOM_SETPOINT])
                    self._min_temp = device_data[ATTR_ROOM_SETPOINT_MIN]
                    self._max_temp = device_data[ATTR_ROOM_SETPOINT_MAX]
                    self._temperature_format = device_data[ATTR_TEMP]
                    self._time_format = device_data[ATTR_TIME_FORMAT]
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
                        self._drstatus_onoff = device_data[ATTR_DRSTATUS]["onOff"]
                    self._heat_level = device_data.get(ATTR_OUTPUT_PERCENT_DISPLAY, {}).get("percent")
                    source_info = device_data.get(ATTR_OUTPUT_PERCENT_DISPLAY, {})
                    if isinstance(source_info, dict) and "sourceType" in source_info:
                        self._heat_source_type = source_info["sourceType"]
                    self._operation_mode = device_data[ATTR_SETPOINT_MODE]
                    self._occupancy = device_data[ATTR_OCCUPANCY]
                    self._keypad = device_data[ATTR_WIFI_KEYPAD]
                    self._rssi = device_data[ATTR_WIFI]
                    self._backlight = device_data[ATTR_BACKLIGHT_AUTO_DIM]
                    self._early_start = device_data[ATTR_EARLY_START]
                    self._target_temp_away = device_data[ATTR_ROOM_SETPOINT_AWAY]
                    self._load1 = device_data[ATTR_OUTPUT1]
                    self._language = device_data[ATTR_LANGUAGE]
                    if ATTR_ROOM_TEMP_DISPLAY in device_data:
                        self._temp_display_status = device_data[ATTR_ROOM_TEMP_DISPLAY]["status"]
                        self._temp_display_value = device_data[ATTR_ROOM_TEMP_DISPLAY]["value"]

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
                "occupancy": self._occupancy,
                "temp_display_status": self._temp_display_status,
                "temp_display_error": self._room_temp_error,
                "source_type": self._heat_source_type,
                "early_start": self._early_start,
                "setpoint_away": self._target_temp_away,
                "load_watt_1": self._load1,
                "error_code": self._error_code,
                "heat_level": self._heat_level,
                "pi_heating_demand": self._heat_level,
                "icon_type": self.icon_type,
                "temp_display_value": self._temp_display_value,
                "keypad": lock_to_ha(self._keypad),
                "backlight": self._backlight,
                "temperature_format": self._temperature_format,
                "time_format": self._time_format,
                "language": self._language,
                "setpoint_max": self._max_temp,
                "setpoint_min": self._min_temp,
                "eco_status": self._drstatus_active,
                "eco_optOut": self._drstatus_optout,
                "eco_setpoint": self._drstatus_setpoint,
                "eco_power_relative": self._drstatus_rel,
                "eco_power_absolute": self._drstatus_abs,
                "eco_onOff": self._drstatus_onoff,
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


class Neviweb130LowWifiThermostat(LowVoltageMixin, Neviweb130Thermostat):
    """Implementation of Neviweb TH1400WF thermostat."""

    def __init__(self, device_info, name, sku, firmware, location, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, location, client)
        self._early_start = "off"
        self._floor_air_limit_status = None
        self._floor_max_status = "off"
        self._floor_min_status = "off"
        self._heat_source_type = None
        self._load1 = 0
        self._load2 = 0
        self._pump_duration_value = None
        self._room_temp_error = None
        self._target_temp_away = None
        self._temp_display_status = None

    @override
    def update(self) -> None:
        if self._active:
            LOW_WIFI_ATTRIBUTES = [
                ATTR_ROOM_TEMP_DISPLAY,
                ATTR_FLOOR_OUTPUT2,
                ATTR_FLOOR_AUX,
                ATTR_ROOM_SETPOINT_AWAY,
                ATTR_EARLY_START,
                ATTR_BACKLIGHT_AUTO_DIM,
                ATTR_OCCUPANCY,
                ATTR_SETPOINT_MODE,
                ATTR_DISPLAY2,
                ATTR_WIFI_KEYPAD,
                ATTR_WIFI,
                ATTR_WIFI_WATTAGE,
                ATTR_FLOOR_OUTPUT1,
                ATTR_PUMP_PROTEC,
                ATTR_PUMP_PROTEC_DURATION,
                ATTR_FLOOR_AIR_LIMIT,
                ATTR_FLOOR_MODE,
                ATTR_FLOOR_SENSOR,
                ATTR_AUX_CYCLE_LENGTH,
                ATTR_CYCLE_LENGTH,
                ATTR_FLOOR_MAX,
                ATTR_FLOOR_MIN,
            ]
            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            attributes = UPDATE_ATTRIBUTES + LOW_WIFI_ATTRIBUTES
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
                    self._room_temp_error = device_data[ATTR_ROOM_TEMPERATURE]["error"]
                    self._target_temp = float(device_data[ATTR_ROOM_SETPOINT])
                    self._min_temp = device_data[ATTR_ROOM_SETPOINT_MIN]
                    self._max_temp = device_data[ATTR_ROOM_SETPOINT_MAX]
                    self._temperature_format = device_data[ATTR_TEMP]
                    self._time_format = device_data[ATTR_TIME_FORMAT]
                    self._temp_display_value = device_data[ATTR_ROOM_TEMP_DISPLAY]["value"]
                    self._temp_display_status = device_data[ATTR_ROOM_TEMP_DISPLAY]["status"]
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
                    self._heat_level = device_data[ATTR_OUTPUT_PERCENT_DISPLAY]["percent"]
                    self._heat_source_type = device_data[ATTR_OUTPUT_PERCENT_DISPLAY]["sourceType"]
                    self._operation_mode = device_data[ATTR_SETPOINT_MODE]
                    self._occupancy = device_data[ATTR_OCCUPANCY]
                    self._keypad = device_data[ATTR_WIFI_KEYPAD]
                    self._rssi = device_data[ATTR_WIFI]
                    self._wattage = device_data[ATTR_WIFI_WATTAGE]
                    self._backlight = device_data[ATTR_BACKLIGHT_AUTO_DIM]
                    self._early_start = device_data[ATTR_EARLY_START]
                    self._target_temp_away = device_data[ATTR_ROOM_SETPOINT_AWAY]
                    self._load1 = device_data[ATTR_FLOOR_OUTPUT1]
                    self._floor_mode = device_data[ATTR_FLOOR_MODE]
                    self._floor_sensor_type = device_data[ATTR_FLOOR_SENSOR]
                    self._aux_cycle_length = device_data[ATTR_AUX_CYCLE_LENGTH]
                    self._cycle_length = device_data[ATTR_CYCLE_LENGTH]
                    self._floor_max = device_data[ATTR_FLOOR_MAX]["value"]
                    self._floor_max_status = device_data[ATTR_FLOOR_MAX]["status"]
                    self._floor_min = device_data[ATTR_FLOOR_MIN]["value"]
                    self._floor_min_status = device_data[ATTR_FLOOR_MIN]["status"]
                    self._floor_air_limit = device_data[ATTR_FLOOR_AIR_LIMIT]["value"]
                    status = device_data[ATTR_FLOOR_AIR_LIMIT]["status"]
                    self._floor_air_limit_status = status
                    self._pump_protec_status = device_data[ATTR_PUMP_PROTEC]["status"]
                    if device_data[ATTR_PUMP_PROTEC]["status"] == "on":
                        self._pump_protec_period = device_data[ATTR_PUMP_PROTEC]["frequency"]
                        self._pump_protec_duration = device_data[ATTR_PUMP_PROTEC]["duration"]
                    if ATTR_PUMP_PROTEC_DURATION in device_data:
                        self._pump_duration_value = device_data[ATTR_PUMP_PROTEC_DURATION]
                    if ATTR_FLOOR_AUX in device_data:
                        self._em_heat = device_data[ATTR_FLOOR_AUX]
                    self._load2 = device_data[ATTR_FLOOR_OUTPUT2]
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
                "sensor_mode": self._floor_mode,
                "floor_sensor_type": self._floor_sensor_type,
                "temp_display_error": self._room_temp_error,
                "load_watt": self._wattage,
                "auxiliary_cycle_length": neviweb_to_ha(self._aux_cycle_length),
                "emergency_heating": self.is_em_heat,
                "cycle_length": neviweb_to_ha(self._cycle_length),
                "pump_protection_status": self._pump_protec_status,
                "pump_protection_duration": self._pump_protec_duration,
                "pump_protection_frequency": self._pump_protec_period,
                "pump_duration_value": self._pump_duration_value,
                "floor_limit_high": self._floor_max,
                "floor_limit_high_status": self._floor_max_status,
                "floor_limit_low": self._floor_min,
                "floor_limit_low_status": self._floor_min_status,
                "max_air_limit": self._floor_air_limit,
                "max_air_limit_status": self._floor_air_limit_status,
                "temp_display_status": self._temp_display_status,
                "temp_display_value": self._temp_display_value,
                "source_type": self._heat_source_type,
                "early_start": self._early_start,
                "setpoint_away": self._target_temp_away,
                "load_watt_1": self._load1,
                "second_display": self._display2,
                "occupancy": self._occupancy,
                "operation_mode": self._operation_mode,
                "auxiliary_heat": self._em_heat,
                "auxiliary_load": self._load2,
                "error_code": self._error_code,
                "heat_level": self._heat_level,
                "pi_heating_demand": self._heat_level,
                "icon_type": self.icon_type,
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


class Neviweb130WifiFloorThermostat(FloorMixin, Neviweb130Thermostat):
    """Implementation of Neviweb TH1300WF, TH1325WF, TH1310WF, SRM40 and True Comfort thermostat."""

    def __init__(self, device_info, name, sku, firmware, location, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, location, client)
        self._early_start = "off"
        self._floor_air_limit_status = None
        self._floor_max_status = "off"
        self._floor_min_status = "off"
        self._gfci_alert = None
        self._gfci_status = None
        self._heat_source_type = None
        self._load1 = 0
        self._load2 = 0
        self._room_temp_error = None
        self._target_temp_away = None

    @override
    def update(self) -> None:
        if self._active:
            WIFI_FLOOR_ATTRIBUTES = [
                ATTR_ROOM_TEMP_DISPLAY,
                ATTR_GFCI_ALERT,
                ATTR_FLOOR_MAX,
                ATTR_FLOOR_MIN,
                ATTR_GFCI_STATUS,
                ATTR_FLOOR_MODE,
                ATTR_FLOOR_AUX,
                ATTR_FLOOR_OUTPUT2,
                ATTR_FLOOR_AIR_LIMIT,
                ATTR_FLOOR_SENSOR,
                ATTR_FLOOR_OUTPUT1,
                ATTR_WIFI_WATTAGE,
                ATTR_WIFI,
                ATTR_WIFI_KEYPAD,
                ATTR_DISPLAY2,
                ATTR_SETPOINT_MODE,
                ATTR_OCCUPANCY,
                ATTR_BACKLIGHT_AUTO_DIM,
                ATTR_EARLY_START,
                ATTR_ROOM_SETPOINT_AWAY,
                ATTR_ROOM_SETPOINT_MIN,
                ATTR_ROOM_SETPOINT_MAX,
            ]
            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            attributes = UPDATE_ATTRIBUTES + WIFI_FLOOR_ATTRIBUTES
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
                    self._room_temp_error = device_data[ATTR_ROOM_TEMPERATURE]["error"]
                    self._target_temp = float(device_data[ATTR_ROOM_SETPOINT])
                    self._min_temp = device_data[ATTR_ROOM_SETPOINT_MIN]
                    self._max_temp = device_data[ATTR_ROOM_SETPOINT_MAX]
                    self._temperature_format = device_data[ATTR_TEMP]
                    self._time_format = device_data[ATTR_TIME_FORMAT]
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
                    self._heat_level = device_data[ATTR_OUTPUT_PERCENT_DISPLAY]["percent"]
                    self._heat_source_type = device_data[ATTR_OUTPUT_PERCENT_DISPLAY]["sourceType"]
                    self._operation_mode = device_data[ATTR_SETPOINT_MODE]
                    self._occupancy = device_data[ATTR_OCCUPANCY]
                    self._keypad = device_data[ATTR_WIFI_KEYPAD]
                    self._rssi = device_data[ATTR_WIFI]
                    self._wattage = device_data[ATTR_WIFI_WATTAGE]
                    self._backlight = device_data[ATTR_BACKLIGHT_AUTO_DIM]
                    self._early_start = device_data[ATTR_EARLY_START]
                    self._target_temp_away = device_data[ATTR_ROOM_SETPOINT_AWAY]
                    self._load1 = device_data[ATTR_FLOOR_OUTPUT1]
                    self._gfci_status = device_data[ATTR_GFCI_STATUS]
                    self._floor_mode = device_data[ATTR_FLOOR_MODE]
                    self._em_heat = device_data[ATTR_FLOOR_AUX]
                    self._floor_sensor_type = device_data[ATTR_FLOOR_SENSOR]
                    if ATTR_FLOOR_AIR_LIMIT in device_data:
                        self._floor_air_limit = device_data[ATTR_FLOOR_AIR_LIMIT]["value"]
                        self._floor_air_limit_status = device_data[ATTR_FLOOR_AIR_LIMIT]["status"]
                    if ATTR_FLOOR_MAX in device_data:
                        self._floor_max = device_data[ATTR_FLOOR_MAX]["value"]
                        self._floor_max_status = device_data[ATTR_FLOOR_MAX]["status"]
                    if ATTR_FLOOR_MIN in device_data:
                        self._floor_min = device_data[ATTR_FLOOR_MIN]["value"]
                        self._floor_min_status = device_data[ATTR_FLOOR_MIN]["status"]
                    self._gfci_alert = device_data[ATTR_GFCI_ALERT]
                    self._load2 = device_data[ATTR_FLOOR_OUTPUT2]
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
            if self._sku != "FLP55" and self._sku != "PS120_240WF":
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
                "load_watt": self._wattage,
                "gfci_status": self._gfci_status,
                "temp_display_error": self._room_temp_error,
                "sensor_mode": self._floor_mode,
                "operation_mode": self._operation_mode,
                "auxiliary_heat": self._em_heat,
                "emergency_heating": self.is_em_heat,
                "auxiliary_load": self._load2,
                "floor_sensor_type": self._floor_sensor_type,
                "floor_limit_high": self._floor_max,
                "floor_limit_high_status": self._floor_max_status,
                "floor_limit_low": self._floor_min,
                "floor_limit_low_status": self._floor_min_status,
                "max_air_limit": self._floor_air_limit,
                "max_air_limit_status": self._floor_air_limit_status,
                "occupancy": self._occupancy,
                "gfci_alert": self._gfci_alert,
                "source_type": self._heat_source_type,
                "early_start": self._early_start,
                "setpoint_away": self._target_temp_away,
                "load_watt_1": self._load1,
                "error_code": self._error_code,
                "heat_level": self._heat_level,
                "pi_heating_demand": self._heat_level,
                "icon_type": self.icon_type,
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


