"""Heat pump thermostat subclasses for neviweb130 climate platform."""
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
    ATTR_BACKLIGHT,
    ATTR_BALANCE_PT,
    ATTR_BALANCE_PT_TEMP_HIGH,
    ATTR_BALANCE_PT_TEMP_LOW,
    ATTR_COOL_LOCK_TEMP,
    ATTR_COOL_SETPOINT,
    ATTR_COOL_SETPOINT_MAX,
    ATTR_COOL_SETPOINT_MIN,
    ATTR_DISPLAY_CAP,
    ATTR_DISPLAY_CONF,
    ATTR_FAN_CAP,
    ATTR_FAN_SPEED,
    ATTR_FAN_SWING_CAP,
    ATTR_FAN_SWING_CAP_HORIZ,
    ATTR_FAN_SWING_CAP_VERT,
    ATTR_FAN_SWING_HORIZ,
    ATTR_FAN_SWING_VERT,
    ATTR_HEAT_INSTALLATION_TYPE,
    ATTR_HEAT_LOCK_TEMP,
    ATTR_HEAT_LOCKOUT_TEMP,
    ATTR_KEYPAD,
    ATTR_MODEL,
    ATTR_OCCUPANCY,
    ATTR_OUTPUT_PERCENT_DISPLAY,
    ATTR_ROOM_SETPOINT,
    ATTR_ROOM_SETPOINT_MAX,
    ATTR_ROOM_SETPOINT_MIN,
    ATTR_ROOM_TEMPERATURE,
    ATTR_RSSI,
    ATTR_SETPOINT_MODE,
    ATTR_SOUND_CAP,
    ATTR_SOUND_CONF,
    ATTR_SYSTEM_MODE,
    ATTR_SYSTEM_MODE_AVAIL,
    ATTR_TEMP,
    ATTR_TYPE,
    DOMAIN,
    MODE_AUTO_BYPASS,
    MODE_MANUAL,
    ATTR_COOL_SETPOINT_AWAY,
    ATTR_DRSETPOINT,
    ATTR_DRSTATUS,
    ATTR_HEAT_COOL,
    ATTR_INTERLOCK_ID,
    ATTR_ROOM_SETPOINT_AWAY,
    ATTR_ROOM_TEMP_DISPLAY,
    ATTR_WIFI,
    ATTR_WIFI_KEYPAD,)
from ..helpers import safe_get_device_attributes, translated_or_default
from ..schema import (
    FAN_SPEED,
    FAN_SPEED_VALUES,
    FAN_SPEED_VALUES_5,
    FULL_SWING,
    FULL_SWING_OFF,
    HP_FAN_SPEED,
)
from .base import (
    Neviweb130Thermostat,
    DEVICE_MODEL_HEAT_PUMP,
    DEVICE_MODEL_WIFI_HEAT_PUMP,
    SNOOZE_TIME,
    UPDATE_HP_ATTRIBUTES,
    SUPPORTED_HVAC_HP_MODES,
    SUPPORTED_HVAC_WHP_MODES,
    SUPPORTED_HVAC_HEAT_MODES,
    SUPPORTED_HVAC_COOL_MODES,
    PRESET_HP_MODES,
    SUPPORT_HP_FLAGS,
    neviweb_to_ha,
    lock_to_ha,
    neviweb_to_ha_fan,
    neviweb_to_ha_mode,
    extract_capability_full,
    extract_capability,
    resolve_fan_speed,
)
from .mixins import HeatPumpMixin

_LOGGER = logging.getLogger(__name__)

class Neviweb130HPThermostat(HeatPumpMixin, Neviweb130Thermostat):
    """Implementation of Neviweb HP6000ZB-GE, HP6000ZB-MA and HP6000ZB-HS heat pump interfaces thermostats."""

    def __init__(self, device_info, name, sku, firmware, location, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, location, client)
        self._cool_max = 30
        self._cool_min = 16
        self._display_cap = None
        self._fan_cap = None
        self._model = None
        self._sound_cap = None

    @override
    def update(self) -> None:
        if self._active:
            HP_ATTRIBUTES = [
                ATTR_RSSI,
                ATTR_COOL_SETPOINT,
                ATTR_SYSTEM_MODE,
                ATTR_KEYPAD,
                ATTR_MODEL,
                ATTR_FAN_SPEED,
                ATTR_FAN_SWING_VERT,
                ATTR_FAN_CAP,
                ATTR_AVAIL_MODE,
            ]
            if self._firmware != "0.1.7":
                NEW_HP_ATTRIBUTES = [
                    ATTR_DRSTATUS,
                    ATTR_DRSETPOINT,
                    ATTR_FAN_SWING_HORIZ,
                    ATTR_FAN_SWING_CAP,
                    ATTR_FAN_SWING_CAP_HORIZ,
                    ATTR_FAN_SWING_CAP_VERT,
                    ATTR_BALANCE_PT,
                    ATTR_HEAT_LOCK_TEMP,
                    ATTR_COOL_LOCK_TEMP,
                    ATTR_DISPLAY_CONF,
                    ATTR_DISPLAY_CAP,
                    ATTR_SOUND_CONF,
                    ATTR_SOUND_CAP,
                ]
            else:
                NEW_HP_ATTRIBUTES = []
            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            attributes = UPDATE_HP_ATTRIBUTES + HP_ATTRIBUTES + NEW_HP_ATTRIBUTES
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
                        float(device_data[ATTR_ROOM_TEMPERATURE])
                        if device_data[ATTR_ROOM_TEMPERATURE] is not None
                        else self._cur_temp_before
                    )
                    self._operation_mode = device_data[ATTR_SYSTEM_MODE]
                    self._target_temp = (
                        float(device_data[ATTR_COOL_SETPOINT])
                        if self._operation_mode == "cool"
                        else float(device_data[ATTR_ROOM_SETPOINT])
                    )
                    self._min_temp = device_data[ATTR_ROOM_SETPOINT_MIN]
                    self._max_temp = device_data[ATTR_ROOM_SETPOINT_MAX]
                    self._target_cool = device_data[ATTR_COOL_SETPOINT]
                    self._cool_min = device_data[ATTR_COOL_SETPOINT_MIN]
                    self._cool_max = device_data[ATTR_COOL_SETPOINT_MAX]
                    self._temperature_format = device_data[ATTR_TEMP]
                    if ATTR_MODEL in device_data and ATTR_MODEL is not None:
                        self._model = device_data[ATTR_MODEL]
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
                    self._keypad = device_data[ATTR_KEYPAD]
                    if ATTR_RSSI in device_data:
                        self._rssi = device_data[ATTR_RSSI]
                    self._fan_speed = device_data[ATTR_FAN_SPEED]
                    self._fan_swing_vert = device_data[ATTR_FAN_SWING_VERT]
                    self._fan_cap = device_data[ATTR_FAN_CAP]
                    self._avail_mode = device_data[ATTR_AVAIL_MODE]
                    if ATTR_FAN_SWING_HORIZ in device_data:
                        self._fan_swing_horiz = device_data[ATTR_FAN_SWING_HORIZ]
                        self._fan_swing_cap = device_data[ATTR_FAN_SWING_CAP]
                        self._fan_swing_cap_horiz = device_data[ATTR_FAN_SWING_CAP_HORIZ]
                        self._fan_swing_cap_vert = device_data[ATTR_FAN_SWING_CAP_VERT]
                        self._balance_pt = device_data[ATTR_BALANCE_PT]
                        self._heat_lockout_temp = device_data[ATTR_HEAT_LOCK_TEMP]
                        self._cool_lockout_temp = device_data[ATTR_COOL_LOCK_TEMP]
                    if ATTR_BALANCE_PT_TEMP_LOW in device_data:
                        self._balance_pt_low = device_data[ATTR_BALANCE_PT_TEMP_LOW]
                        self._balance_pt_high = device_data[ATTR_BALANCE_PT_TEMP_HIGH]
                    if ATTR_DISPLAY_CONF in device_data:
                        self._display_conf = device_data[ATTR_DISPLAY_CONF]
                        self._display_cap = device_data[ATTR_DISPLAY_CAP]
                        self._sound_conf = device_data[ATTR_SOUND_CONF]
                        self._sound_cap = device_data[ATTR_SOUND_CAP]
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
                "heat_pump_model": self._model,
                "error_code": self._error_code,
                "operation modes": self._operation_mode,
                "cool setpoint min": self._cool_min,
                "cool setpoint max": self._cool_max,
                "setpoint_max": self._max_temp,
                "setpoint_min": self._min_temp,
                "temperature_format": self._temperature_format,
                "keypad": lock_to_ha(self._keypad),
                "fan_speed": self._fan_speed,
                "fan_swing_vertical": self._fan_swing_vert,
                "fan_capability": self._fan_cap,
                "available_mode": self._avail_mode,
            }
        )
        if self._firmware != "0.1.7":
            data.update(
                {
                    "heat_pump_limit_temp": self._balance_pt,
                    #                         'min_heat_pump_limit_temp': self._balance_pt_low,
                    #                         'max_heat_pump_limit_temp': self._balance_pt_high,
                    "heat_lock_temp": self._heat_lockout_temp,
                    "cool_lock_temp": self._cool_lockout_temp,
                    "fan_swing_horizontal": self._fan_swing_horiz,
                    "fan_swing_capability": extract_capability(self._fan_swing_cap),
                    "fan_swing_capability_vertical": extract_capability_full(self._fan_swing_cap_vert),
                    "fan_swing_capability_horizontal": extract_capability_full(self._fan_swing_cap_horiz),
                    "display_conf": self._display_conf,
                    "display_capability": extract_capability(self._display_cap),
                    "sound_conf": self._sound_conf,
                    "sound_capability": extract_capability(self._sound_cap),
                    "eco_status": self._drstatus_active,
                    "eco_optOut": self._drstatus_optout,
                    "eco_setpoint": self._drstatus_setpoint,
                    "eco_power_relative": self._drstatus_rel,
                    "eco_power_absolute": self._drstatus_abs,
                    "eco_setpoint_status": self._drsetpoint_status,
                    "eco_setpoint_delta": self._drsetpoint_value,
                }
            )
        data.update(
            {
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


class Neviweb130WifiHPThermostat(HeatPumpMixin, Neviweb130Thermostat):
    """Implementation of Neviweb HP6000WF-MA and HP6000WF-XX Wi-Fi heat pump interfaces thermostats."""

    def __init__(self, device_info, name, sku, firmware, location, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, location, client)
        self._cool_max = 31
        self._cool_min = 16
        self._cool_target_temp_away = None
        self._display_cap = None
        self._fan_cap = None
        self._heat_cool = None
        self._heatcool_setpoint_delta = 2
        self._interlock_id = None
        self._system_mode_avail = None
        self._model = None
        self._room_temp_error = None
        self._sound_cap = None

    @override
    def update(self) -> None:
        if self._active:
            WHP_ATTRIBUTES = [
                ATTR_BALANCE_PT,
                ATTR_COOL_LOCK_TEMP,
                ATTR_COOL_SETPOINT,
                ATTR_COOL_SETPOINT_AWAY,
                ATTR_DISPLAY_CAP,
                ATTR_DISPLAY_CONF,
                ATTR_DRSETPOINT,
                ATTR_DRSTATUS,
                ATTR_FAN_CAP,
                ATTR_FAN_SPEED,
                ATTR_FAN_SWING_CAP,
                ATTR_FAN_SWING_CAP_HORIZ,
                ATTR_FAN_SWING_CAP_VERT,
                ATTR_FAN_SWING_HORIZ,
                ATTR_FAN_SWING_VERT,
                ATTR_HEAT_COOL,
                ATTR_HEAT_LOCK_TEMP,
                ATTR_INTERLOCK_ID,
                ATTR_MODEL,
                ATTR_OCCUPANCY,
                ATTR_ROOM_SETPOINT_AWAY,
                ATTR_ROOM_TEMP_DISPLAY,
                ATTR_SETPOINT_MODE,
                ATTR_SOUND_CAP,
                ATTR_SOUND_CONF,
                ATTR_SYSTEM_MODE_AVAIL,
                ATTR_WIFI,
                ATTR_WIFI_KEYPAD,
            ]

            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            attributes = UPDATE_HP_ATTRIBUTES + WHP_ATTRIBUTES
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
                    if self._room_temp_error is not None:
                        self.notify_ha(
                            translated_or_default(
                                self.hass,
                                "temp_error",
                                (
                                    f"Temperature error code detected for {self._name}, {self._id} ({self._sku}), "
                                    f"{self._room_temp_error}"
                                ),
                                error=self._room_temp_error,
                                name=self._name,
                                id=self._id,
                                sku=self._sku,
                            )
                        )
                        _LOGGER.warning(
                            translated_or_default(
                                self.hass,
                                "temp_error",
                                (
                                    f"Temperature error code detected for {self._name}, {self._id} ({self._sku}), "
                                    f"{self._room_temp_error}"
                                ),
                                error=self._room_temp_error,
                                name=self._name,
                                id=self._id,
                                sku=self._sku,
                            )
                        )
                    self._operation_mode = device_data[ATTR_SETPOINT_MODE]
                    try:
                        self._heat_cool = neviweb_to_ha_mode(device_data[ATTR_HEAT_COOL])
                    except ValueError:
                        raise ServiceValidationError(
                            translated_or_default(
                                self.hass,
                                "unknown_mode",
                                f"Unknown mode {device_data[ATTR_HEAT_COOL]} for model {self._device_model}.",
                                model=self._device_model,
                                mode=device_data[ATTR_HEAT_COOL],
                            )
                        )
                    self._target_temp = (
                        float(device_data[ATTR_COOL_SETPOINT])
                        if self._heat_cool == "cool"
                        else float(device_data[ATTR_ROOM_SETPOINT])
                    )
                    self._temp_display_value = device_data[ATTR_ROOM_TEMP_DISPLAY]["value"]
                    self._temp_display_status = device_data[ATTR_ROOM_TEMP_DISPLAY]["status"]
                    self._min_temp = device_data[ATTR_ROOM_SETPOINT_MIN]
                    self._cur_temp = max(self._cur_temp, self._min_temp)
                    self._max_temp = device_data[ATTR_ROOM_SETPOINT_MAX]
                    self._target_temp_away = device_data[ATTR_ROOM_SETPOINT_AWAY]
                    self._target_cool = device_data[ATTR_COOL_SETPOINT]
                    self._cool_min = device_data[ATTR_COOL_SETPOINT_MIN]
                    self._cool_max = device_data[ATTR_COOL_SETPOINT_MAX]
                    self._cool_target_temp_away = device_data[ATTR_COOL_SETPOINT_AWAY]
                    self._temperature_format = device_data[ATTR_TEMP]
                    if ATTR_OCCUPANCY in device_data:
                        self._occupancy = device_data[ATTR_OCCUPANCY]
                    if ATTR_MODEL in device_data and ATTR_MODEL is not None:
                        self._model = device_data[ATTR_MODEL]
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
                    self._keypad = device_data[ATTR_WIFI_KEYPAD]
                    if ATTR_WIFI in device_data:
                        self._rssi = device_data[ATTR_WIFI]
                    try:
                        self._fan_speed = neviweb_to_ha_fan(device_data[ATTR_FAN_SPEED], self._device_model)
                    except ValueError:
                        raise ServiceValidationError(
                            translated_or_default(
                                self.hass,
                                "fan_model_not_supported",
                                f"Fan model not supported for model {self._device_model}.",
                                model=self._device_model,
                            )
                        )
                    self._fan_swing_vert = device_data[ATTR_FAN_SWING_VERT]
                    self._fan_cap = device_data[ATTR_FAN_CAP]
                    self._system_mode_avail = device_data[ATTR_SYSTEM_MODE_AVAIL]
                    if ATTR_FAN_SWING_HORIZ in device_data:
                        self._fan_swing_horiz = device_data[ATTR_FAN_SWING_HORIZ]
                        self._fan_swing_cap = device_data[ATTR_FAN_SWING_CAP]
                        self._fan_swing_cap_horiz = device_data[ATTR_FAN_SWING_CAP_HORIZ]
                        self._fan_swing_cap_vert = device_data[ATTR_FAN_SWING_CAP_VERT]
                        self._balance_pt = device_data[ATTR_BALANCE_PT]
                        self._heat_lockout_temp = device_data[ATTR_HEAT_LOCK_TEMP]
                        self._cool_lockout_temp = device_data[ATTR_COOL_LOCK_TEMP]
                    if ATTR_DISPLAY_CONF in device_data:
                        self._display_conf = device_data[ATTR_DISPLAY_CONF]
                        self._display_cap = device_data[ATTR_DISPLAY_CAP]
                        self._sound_conf = device_data[ATTR_SOUND_CONF]
                        self._sound_cap = device_data[ATTR_SOUND_CAP]
                    self._interlock_id = device_data[ATTR_INTERLOCK_ID]
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
    def is_on(self) -> bool:
        """Return True if mode = HVACMode.HEAT or HVACMode.COOL."""
        return (
            self._heat_cool == HVACMode.HEAT
            or self._heat_cool == HVACMode.COOL
            or self._heat_cool == HVACMode.HEAT_COOL
            or self._heat_cool == HVACMode.DRY
            or self._heat_cool == HVACMode.FAN_ONLY
        )

    @property
    @override
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        mode = self._heat_cool

        # If Neviweb return an unknown mode
        if mode not in (
            HVACMode.OFF,
            HVACMode.HEAT_COOL,
            HVACMode.COOL,
            HVACMode.DRY,
            HVACMode.FAN_ONLY,
            HVACMode.HEAT,
        ):
            return HVACMode.HEAT

        return mode

    @property
    @override
    def hvac_action(self) -> HVACAction | None:
        """Return current HVAC action."""
        mode = self.hvac_mode
        temp = self.current_temperature

        if temp is None:
            return HVACAction.IDLE

        if mode == HVACMode.OFF:
            return HVACAction.OFF
        if mode == HVACMode.COOL:
            if temp > self.target_temperature_high:
                return HVACAction.COOLING
            return HVACAction.IDLE
        if mode == HVACMode.HEAT:
            if temp < self.target_temperature_low:
                return HVACAction.HEATING
            return HVACAction.IDLE
        if mode == HVACMode.DRY:
            return HVACAction.DRYING
        if mode == HVACMode.FAN_ONLY:
            return HVACAction.FAN
        if mode == HVACMode.HEAT_COOL:
            if temp < self.target_temperature_low:
                return HVACAction.HEATING
            if temp > self.target_temperature_high:
                return HVACAction.COOLING
            return HVACAction.IDLE

        return HVACAction.IDLE

    @property
    @override
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        if self.hvac_mode == HVACMode.HEAT_COOL:
            return min(self._min_temp, self._cool_min)
        elif self.hvac_mode == HVACMode.COOL:
            return self._cool_min
        else:
            return self._min_temp

    @property
    @override
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        if self.hvac_mode == HVACMode.HEAT_COOL:
            return max(self._max_temp, self._cool_max)
        elif self.hvac_mode == HVACMode.COOL:
            return self._cool_max
        else:
            return self._max_temp

    @property
    @override
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach less Eco Sinope dr_setpoint delta."""

        # Default temp
        temp = self._target_temp

        # If HVACMode.heat, apply target_temperature_low
        if self.hvac_mode == HVACMode.HEAT and self._target_temp is not None:
            temp = self.target_temperature_low

        # If HVACMode.cool, apply target_temperature_high
        elif self.hvac_mode == HVACMode.COOL:
            temp = self.target_temperature_high

        # If HVACMode.heatCool, apply target_temperature_low
        elif self.hvac_mode in (HVACMode.HEAT_COOL, HVACMode.AUTO):
            temp = self.target_temperature_low

        # Other modes
        else:
            temp = self._target_temp

        # if temp is None → return None
        if temp is None:
            return None

        # Apply limit
        if temp < self._min_temp:
            return self._min_temp
        if temp > self._max_temp:
            return self._max_temp

        return temp

    @property
    @override
    def target_temperature_low(self) -> float:
        """Return the heating temperature we try to reach less Eco Sinope dr_setpoint delta."""
        return self._target_temp + self._drsetpoint_value

    @property
    @override
    def target_temperature_high(self) -> float:
        """Return the cooling temperature we try to reach."""
        return self._target_cool

    @override
    def turn_on(self) -> None:
        """Turn the thermostat to HVACMode.HEAT."""
        self._heat_cool = HVACMode.HEAT
        self._client.set_setpoint_mode(self._id, self._heat_cool, self._is_wifi, self._is_WHP)

    @override
    def turn_off(self) -> None:
        """Turn the thermostat to HVACMode.OFF."""
        self._heat_cool = HVACMode.OFF
        self._client.set_setpoint_mode(self._id, self._heat_cool, self._is_wifi, self._is_WHP)

    @override
    def set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new hvac mode."""
        self._client.set_setpoint_mode(self._id, hvac_mode, self._is_wifi, self._is_WHP)

        self._heat_cool = hvac_mode if hvac_mode != HVACMode.HEAT_COOL else HVACMode.AUTO

        # Reset the preset to the occupancy
        self.set_preset_mode(self._occupancy)
        self._delayed_refresh()

    @override
    def set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature_low = None
        temperature_high = None
        if self.hvac_mode == HVACMode.HEAT_COOL:
            temperature_low = kwargs.get(ATTR_TARGET_TEMP_LOW)
            temperature_high = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        else:
            temperature = kwargs.get(ATTR_TEMPERATURE)
            if self.hvac_mode == HVACMode.COOL:
                temperature_high = temperature
            else:
                temperature_low = temperature

        if temperature_low is not None:
            temperature_low = max(temperature_low, self._min_temp)
            if self.hvac_mode == HVACMode.HEAT_COOL:
                temperature_low = min(
                    temperature_low, self._target_cool - self._heatcool_setpoint_delta
                )  # a corriger le delta
            else:
                temperature_low = min(temperature_low, self._max_temp)

            if self._target_temp != temperature_low:
                self._client.set_temperature(self._id, temperature_low)
                self._target_temp = temperature_low

        if temperature_high is not None:
            temperature_high = min(temperature_high, self._cool_max)
            if self.hvac_mode == HVACMode.HEAT_COOL:
                temperature_high = max(
                    temperature_high, self._target_temp + self._heatcool_setpoint_delta
                )  # a corriger le delta
            else:
                temperature_high = max(temperature_high, self._cool_min)

            if self._target_cool != temperature_high:
                self._client.set_cool_temperature(self._id, temperature_high)
                self._target_cool = temperature_high
        self._delayed_refresh()

    @property
    @override
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return the state attributes."""
        data = {}
        data.update(
            {
                "neviweb_occupancy_mode": self._occupancy_mode,
                "heat_pump_model": self._model,
                "error_code": self._error_code,
                "operation modes": self._operation_mode,
                "cool setpoint min": self._cool_min,
                "cool setpoint max": self._cool_max,
                "setpoint_max": self._max_temp,
                "setpoint_min": self._min_temp,
                "temperature_format": self._temperature_format,
                "temp_display_status": self._temp_display_status,
                "temp_display_value": self._temp_display_value,
                "temp_display_error": self._room_temp_error,
                "keypad": lock_to_ha(self._keypad),
                "fan_speed": self._fan_speed,
                "fan_swing_vertical": self._fan_swing_vert,
                "fan_capability": self._fan_cap,
                "modes_availables": self._system_mode_avail,
                "heat_pump_limit_temp": self._balance_pt,
                "min_heat_pump_limit_temp": self._balance_pt_low,
                "max_heat_pump_limit_temp": self._balance_pt_high,
                "heat_lock_temp": self._heat_lockout_temp,
                "cool_lock_temp": self._cool_lockout_temp,
                "fan_swing_horizontal": self._fan_swing_horiz,
                "fan_swing_capability": extract_capability(self._fan_swing_cap),
                "fan_swing_capability_vertical": extract_capability_full(self._fan_swing_cap_vert),
                "fan_swing_capability_horizontal": extract_capability_full(self._fan_swing_cap_horiz),
                "display_conf": self._display_conf,
                "display_capability": extract_capability(self._display_cap),
                "sound_conf": self._sound_conf,
                "sound_capability": extract_capability(self._sound_cap),
                "eco_status": self._drstatus_active,
                "eco_optOut": self._drstatus_optout,
                "eco_setpoint": self._drstatus_setpoint,
                "eco_power_relative": self._drstatus_rel,
                "eco_power_absolute": self._drstatus_abs,
                "eco_onOff": self._drstatus_onoff,
                "eco_setpoint_status": self._drsetpoint_status,
                "eco_setpoint_delta": self._drsetpoint_value,
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


