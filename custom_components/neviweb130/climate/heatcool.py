"""Heat/cool thermostat subclasses for neviweb130 climate platform."""
from __future__ import annotations

import logging
import time
from typing import Any, Mapping, override

from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
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
    ATTR_ACCESSORY_TYPE,
    ATTR_AIR_ACTIVATION_TEMP,
    ATTR_AIR_CONFIG,
    ATTR_AIR_EX_MIN_TIME_ON,
    ATTR_AIR_MAX_POWER_TEMP,
    ATTR_AUX_CYCLE_LENGTH,
    ATTR_AUX_HEAT_MIN_TIME_OFF,
    ATTR_AUX_HEAT_MIN_TIME_ON,
    ATTR_AUX_HEAT_SOURCE_TYPE,
    ATTR_AUX_HEAT_START_DELAY,
    ATTR_AUX_OPTIM,
    ATTR_AVAIL_MODE,
    ATTR_BACKLIGHT,
    ATTR_BALANCE_PT,
    ATTR_BALANCE_PT_TEMP_HIGH,
    ATTR_BALANCE_PT_TEMP_LOW,
    ATTR_COOL_CYCLE_LENGTH,
    ATTR_COOL_INTERSTAGE_MIN_DELAY,
    ATTR_COOL_LOCK_TEMP,
    ATTR_COOL_MIN_TIME_OFF,
    ATTR_COOL_MIN_TIME_ON,
    ATTR_COOL_PURGE_TIME,
    ATTR_COOL_SETPOINT,
    ATTR_COOL_SETPOINT_AWAY,
    ATTR_COOL_SETPOINT_MAX,
    ATTR_COOL_SETPOINT_MIN,
    ATTR_CYCLE_LENGTH,
    ATTR_CYCLE_OUTPUT2,
    ATTR_DISPLAY2,
    ATTR_DISPLAY_CAP,
    ATTR_DISPLAY_CONF,
    ATTR_DRACCESORYCONF,
    ATTR_DRACTIVE,
    ATTR_DRAIR_CURT_CONF,
    ATTR_DRAUXCONF,
    ATTR_DRFANCONF,
    ATTR_DRSETPOINT,
    ATTR_DRSTATUS,
    ATTR_DUAL_STATUS,
    ATTR_EARLY_START,
    ATTR_FAN_CAP,
    ATTR_FAN_FILTER_REMAIN,
    ATTR_FAN_SPEED,
    ATTR_FAN_SPEED_OPTIM,
    ATTR_FAN_SWING_CAP,
    ATTR_FAN_SWING_CAP_HORIZ,
    ATTR_FAN_SWING_CAP_VERT,
    ATTR_FAN_SWING_HORIZ,
    ATTR_FAN_SWING_VERT,
    ATTR_FLOOR_AUX,
    ATTR_FLOOR_OUTPUT2,
    ATTR_GFCI_ALERT,
    ATTR_GFCI_STATUS,
    ATTR_HC_DEV,
    ATTR_HC_LOCK_STATUS,
    ATTR_HEAT_COOL,
    ATTR_HEAT_INSTALLATION_TYPE,
    ATTR_HEAT_INTERSTAGE_MIN_DELAY,
    ATTR_HEAT_LOCK_TEMP,
    ATTR_HEAT_LOCKOUT_TEMP,
    ATTR_HEAT_MIN_TIME_OFF,
    ATTR_HEAT_MIN_TIME_ON,
    ATTR_HEAT_OUTPUT_POLARITY,
    ATTR_HEAT_PURGE_TIME,
    ATTR_HEAT_SOURCE_TYPE,
    ATTR_HEATCOOL_SETPOINT_MIN_DELTA,
    ATTR_HUMIDIFIER_TYPE,
    ATTR_HUMIDITY_DISPLAY,
    ATTR_HUMIDITY_SETPOINT,
    ATTR_HUMIDITY_SETPOINT_MODE,
    ATTR_HUMIDITY_SETPOINT_OFFSET,
    ATTR_HVAC_INPUT_1_FUNCTION,
    ATTR_INTERLOCK_HC_MODE,
    ATTR_INTERLOCK_ID,
    ATTR_INTERLOCK_PARTNER,
    ATTR_KEYPAD,
    ATTR_LANGUAGE,
    ATTR_MODE,
    ATTR_MODEL,
    ATTR_OCCUPANCY,
    ATTR_OPTOUT,
    ATTR_OUTPUT1,
    ATTR_OUTPUT_CONNECT_STATE,
    ATTR_OUTPUT_PERCENT_DISPLAY,
    ATTR_POLARITY,
    ATTR_PUMP_PROTEC,
    ATTR_PUMP_PROTEC_DURATION,
    ATTR_PUMP_PROTEC_PERIOD,
    ATTR_REVERSING_VALVE_POLARITY,
    ATTR_ROOM_SETPOINT,
    ATTR_ROOM_SETPOINT_AWAY,
    ATTR_ROOM_SETPOINT_MAX,
    ATTR_ROOM_SETPOINT_MIN,
    ATTR_ROOM_TEMP_DISPLAY,
    ATTR_ROOM_TEMPERATURE,
    ATTR_RSSI,
    ATTR_SCHEDULED_PEAK_DELAY,
    ATTR_SETPOINT,
    ATTR_SETPOINT_MODE,
    ATTR_SOUND_CAP,
    ATTR_SOUND_CONF,
    ATTR_STATUS,
    ATTR_SYSTEM_MODE,
    ATTR_SYSTEM_MODE_AVAIL,
    ATTR_TEMP,
    ATTR_TEMP_OFFSET_HEAT,
    ATTR_TIME,
    ATTR_TIME_FORMAT,
    ATTR_TYPE,
    ATTR_VALUE,
    ATTR_WATTAGE,
    ATTR_WIFI,
    ATTR_WIFI_KEYPAD,
    ATTR_WIFI_WATTAGE,
    DOMAIN,
    MODE_AUTO_BYPASS,
    MODE_EM_HEAT,
    MODE_MANUAL,
    ATTR_BACKLIGHT_AUTO_DIM,
    ATTR_BACK_LIGHT,
    ATTR_SCHEDULED_PEAK_STATUS,)
from ..helpers import safe_get_device_attributes, translated_or_default
from ..schema import (
    AUX_HEATING,
    CYCLE_LENGTH_VALUES,
    FAN_SPEED,
    FAN_SPEED_VALUES,
    FAN_SPEED_VALUES_5,
    FULL_SWING,
    FULL_SWING_OFF,
    HP_FAN_SPEED,
    TH6_MODES_VALUES,
    WIFI_FAN_SPEED,
)
from .base import (
    Neviweb130Thermostat,
    DEVICE_MODEL_HC,
    DEVICE_MODEL_HEAT_COOL,
    SNOOZE_TIME,
    UPDATE_ATTRIBUTES,
    UPDATE_HEAT_COOL_ATTRIBUTES,
    SUPPORTED_HVAC_H_C_MODES,
    SUPPORTED_HVAC_HC_MODES,
    SUPPORTED_HVAC_HEAT_MODES,
    SUPPORTED_HVAC_COOL_MODES,
    PRESET_h_c_MODES,
    PRESET_HC_MODES,
    SUPPORT_FLAGS,
    SUPPORT_H_c_FLAGS,
    SUPPORT_HC_FLAGS,
    neviweb_to_ha,
    lock_to_ha,
    neviweb_to_ha_fan,
    neviweb_to_ha_mode,
    extract_capability_full,
    extract_capability,
    resolve_fan_speed,
)
from .mixins import HeatCoolMixin, LowVoltageMixin

_LOGGER = logging.getLogger(__name__)

class Neviweb130HcThermostat(Neviweb130Thermostat):
    """Implementation of Neviweb TH1134ZB-HC thermostat."""

    def __init__(self, device_info, name, sku, firmware, location, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, location, client)
        self._cool_max = 30
        self._cool_min = 16
        self._display_cap = None
        self._fan_cap = None
        self._hc_device = None
        self._model = None
        self._sound_cap = None

    @override
    def update(self) -> None:
        if self._active:
            HC_ATTRIBUTES = [
                ATTR_DISPLAY2,
                ATTR_RSSI,
                ATTR_COOL_SETPOINT,
                ATTR_COOL_SETPOINT_MIN,
                ATTR_COOL_SETPOINT_MAX,
                ATTR_SYSTEM_MODE,
                ATTR_CYCLE_LENGTH,
                ATTR_WATTAGE,
                ATTR_BACKLIGHT,
                ATTR_KEYPAD,
                ATTR_HC_DEV,
                ATTR_LANGUAGE,
                ATTR_MODEL,
                ATTR_FAN_SPEED,
                ATTR_FAN_SWING_VERT,
                ATTR_FAN_SWING_HORIZ,
                ATTR_FAN_CAP,
                ATTR_FAN_SWING_CAP,
                ATTR_FAN_SWING_CAP_HORIZ,
                ATTR_FAN_SWING_CAP_VERT,
                ATTR_BALANCE_PT,
                ATTR_HEAT_LOCK_TEMP,
                ATTR_COOL_LOCK_TEMP,
                ATTR_AVAIL_MODE,
                ATTR_DISPLAY_CONF,
                ATTR_DISPLAY_CAP,
                ATTR_SOUND_CONF,
                ATTR_SOUND_CAP,
                ATTR_ROOM_TEMP_DISPLAY,
            ]
            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            attributes = UPDATE_ATTRIBUTES + HC_ATTRIBUTES
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
                        float(device_data[ATTR_ROOM_TEMP_DISPLAY])
                        if device_data[ATTR_ROOM_TEMP_DISPLAY] is not None
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
                    if ATTR_OUTPUT_PERCENT_DISPLAY in device_data:
                        self._heat_level = device_data[ATTR_OUTPUT_PERCENT_DISPLAY]
                    self._keypad = device_data[ATTR_KEYPAD]
                    self._backlight = device_data[ATTR_BACKLIGHT]
                    if ATTR_RSSI in device_data:
                        self._rssi = device_data[ATTR_RSSI]
                    self._wattage = device_data[ATTR_WATTAGE]
                    self._cycle_length = device_data[ATTR_CYCLE_LENGTH]
                    self._target_cool = device_data[ATTR_COOL_SETPOINT]
                    self._cool_min = device_data[ATTR_COOL_SETPOINT_MIN]
                    self._cool_max = device_data[ATTR_COOL_SETPOINT_MAX]
                    self._hc_device = device_data[ATTR_HC_DEV]
                    self._language = device_data[ATTR_LANGUAGE]
                    self._model = device_data[ATTR_MODEL]
                    self._fan_speed = device_data[ATTR_FAN_SPEED]
                    self._fan_swing_vert = device_data[ATTR_FAN_SWING_VERT]
                    self._fan_swing_horiz = device_data[ATTR_FAN_SWING_HORIZ]
                    self._fan_cap = device_data[ATTR_FAN_CAP]
                    self._fan_swing_cap = device_data[ATTR_FAN_SWING_CAP]
                    self._fan_swing_cap_vert = device_data[ATTR_FAN_SWING_CAP_VERT]
                    self._fan_swing_cap_horiz = device_data[ATTR_FAN_SWING_CAP_HORIZ]
                    self._balance_pt = device_data[ATTR_BALANCE_PT]
                    self._heat_lockout_temp = device_data[ATTR_HEAT_LOCK_TEMP]
                    self._cool_lockout_temp = device_data[ATTR_COOL_LOCK_TEMP]
                    self._avail_mode = device_data[ATTR_AVAIL_MODE]
                    self._display_cap = device_data[ATTR_DISPLAY_CAP]
                    self._display_conf = device_data[ATTR_DISPLAY_CONF]
                    self._sound_cap = device_data[ATTR_SOUND_CAP]
                    self._sound_conf = device_data[ATTR_SOUND_CONF]
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
                "error_code": self._error_code,
                "cool setpoint min": self._cool_min,
                "cool setpoint max": self._cool_max,
                "cool setpoint": self._target_cool,
                "cycle_length": neviweb_to_ha(self._cycle_length),
                "hc_device": self._hc_device,
                "language": self._language,
                "model": self._model,
                "fan_speed": self._fan_speed,
                "fan_swing_vertical": self._fan_swing_vert,
                "fan_swing_horizontal": self._fan_swing_horiz,
                "fan_capability": self._fan_cap,
                "fan_swing_capability": extract_capability(self._fan_swing_cap),
                "fan_swing_capability_vertical": extract_capability_full(self._fan_swing_cap_vert),
                "fan_swing_capability_horizontal": extract_capability_full(self._fan_swing_cap_horiz),
                "display_conf": self._display_conf,
                "display_capability": extract_capability(self._display_cap),
                "sound_conf": self._sound_conf,
                "sound_capability": extract_capability(self._sound_cap),
                "balance_point": self._balance_pt,
                "heat_lock_temp": self._heat_lockout_temp,
                "cool_lock_temp": self._cool_lockout_temp,
                "available_mode": self._avail_mode,
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



class Neviweb130HeatCoolThermostat(HeatCoolMixin, Neviweb130Thermostat):
    """Implementation of Neviweb TH6500WF, TH6510WF, TH6250WF, TH6250WF-PRO heat cool thermostats."""

    def __init__(self, device_info, name, sku, firmware, location, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, location, client)
        self._accessory_type = "none"
        self._air_curt_activation_temp = None
        self._air_curt_activation_temp = None
        self._air_curt_conf = None
        self._air_curt_max_temp = None
        self._air_ex_min_time_on = None
        self._air_min_time_on = 0
        self._aux_heat_min_time_off = None
        self._aux_heat_min_time_on = None
        self._aux_heat_source_type = None
        self._aux_heat_start_delay = None
        self._aux_interstage_delay = None
        self._aux_interstage_min_delay = None
        self._reversing_valve_polarity = "cooling"
        self._backlight_auto_dim = None
        self._cool_cycle_length = 0
        self._cool_interstage_delay = None
        self._cool_interstage_min_delay = None
        self._cool_max = 36
        self._cool_min = 16
        self._cool_min_time_off = None
        self._cool_min_time_on = None
        self._cool_purge_time = 0
        self._cool_target_temp = None
        self._cool_target_temp_away = None
        self._dr_accessory_conf = None
        self._dr_air_curt_conf = None
        self._dr_aux_config = None
        self._dr_fan_speed_conf = None
        self._dual_status = None
        self._fan_filter_remain = None
        self._heat_cool = None
        self._heat_installation_type = None
        self._heat_interstage_delay = None
        self._heat_interstage_min_delay = None
        self._heat_level_source_type = "heating"
        self._heat_min_time_off = None
        self._heat_min_time_on = None
        self._heat_output_polarity = None
        self._heat_purge_time = 0
        self._heat_source_type = None
        self._heatcool_lock_balance_point_status = None
        self._heatcool_lock_cool_status = None
        self._heatcool_lock_heat_status = None
        self._heatcool_setpoint_delta = 2
        self._humidifier_type = None
        self._humidity_display = None
        self._humidity_setpoint = None
        self._humidity_setpoint_mode = None
        self._humidity_setpoint_offset = 0
        self._hvac_input1_function = None
        self._interlock_id = None
        self._output_connect_state = {
            "Y1": False,
            "Y2": False,
            "OB": False,
            "W": False,
            "W2": False,
            "G": False,
            "Rh": False,
            "Acc": False,
            "LC": False,
        }
        self._preset_before = None
        self._room_temp_error = None
        self._scheduled_peak_delay = None
        self._scheduled_peak_status = None
        self._temp_display_status = None
        self._temp_offset_heat = None
        for mode in TH6_MODES_VALUES:
            setattr(self, f"_{mode}_hourly_total_count", 0)
            setattr(self, f"_{mode}_hourly_count", 0)
            setattr(self, f"_{mode}_hourly_last_timestamp", None)
            setattr(self, f"_{mode}_hourly_last_timestamp_local", None)

    @override
    def update(self) -> None:
        if self._active:
            HC_ATTRIBUTES = [
                ATTR_AUX_CYCLE_LENGTH,
                ATTR_AUX_HEAT_MIN_TIME_ON,
                ATTR_AUX_HEAT_SOURCE_TYPE,
                ATTR_AUX_HEAT_START_DELAY,
                ATTR_BACK_LIGHT,
                ATTR_BACKLIGHT_AUTO_DIM,
                ATTR_BALANCE_PT,
                ATTR_CYCLE_LENGTH,
                ATTR_COOL_CYCLE_LENGTH,
                ATTR_COOL_LOCK_TEMP,
                ATTR_COOL_MIN_TIME_OFF,
                ATTR_COOL_MIN_TIME_ON,
                ATTR_COOL_SETPOINT_AWAY,
                ATTR_DUAL_STATUS,
                ATTR_EARLY_START,
                ATTR_FAN_FILTER_REMAIN,
                ATTR_FAN_SPEED,
                ATTR_HEAT_COOL,
                ATTR_HEATCOOL_SETPOINT_MIN_DELTA,
                ATTR_HEAT_INSTALLATION_TYPE,
                ATTR_HEAT_LOCK_TEMP,
                ATTR_HEAT_SOURCE_TYPE,
                ATTR_HUMIDIFIER_TYPE,
                ATTR_HUMIDITY_DISPLAY,
                ATTR_HUMIDITY_SETPOINT,
                ATTR_LANGUAGE,
                ATTR_OCCUPANCY,
                ATTR_OUTPUT_CONNECT_STATE,
                ATTR_REVERSING_VALVE_POLARITY,
                ATTR_ROOM_SETPOINT_AWAY,
                ATTR_SETPOINT_MODE,
                ATTR_TEMP_OFFSET_HEAT,
                ATTR_WIFI_KEYPAD,
            ]
            """Get specific attributes"""
            HC_SPECIAL_FIRMWARE = [
                ATTR_ACCESSORY_TYPE,
                ATTR_AIR_EX_MIN_TIME_ON,
                ATTR_AUX_HEAT_MIN_TIME_OFF,
                ATTR_COOL_PURGE_TIME,
                ATTR_DRACCESORYCONF,
                ATTR_DRAUXCONF,
                ATTR_DRFANCONF,
                ATTR_HC_LOCK_STATUS,
                ATTR_HEAT_MIN_TIME_ON,
                ATTR_HEAT_MIN_TIME_OFF,
                ATTR_HEAT_PURGE_TIME,
                ATTR_HUMIDITY_SETPOINT_OFFSET,
                ATTR_HUMIDITY_SETPOINT_MODE,
            ]
            if self._device_model == 6727:
                HC_EXTRA = [
                    ATTR_COOL_INTERSTAGE_MIN_DELAY,
                    ATTR_HEAT_INTERSTAGE_MIN_DELAY,
                    ATTR_HVAC_INPUT_1_FUNCTION,
                    ATTR_SCHEDULED_PEAK_DELAY,
                    #  ATTR_SCHEDULED_PEAK_STATUS,
                ]
            else:
                HC_EXTRA = []
            if self._device_model == 6727 or self._device_model == 6731:
                HC_CONFIG = [
                    ATTR_AIR_ACTIVATION_TEMP,
                    ATTR_AIR_CONFIG,
                    ATTR_AIR_MAX_POWER_TEMP,
                    ATTR_DRAIR_CURT_CONF,
                    ATTR_HEAT_OUTPUT_POLARITY,
                ]
            else:
                HC_CONFIG = []
            if self._firmware == "4.3.6":
                HC_43 = [ATTR_INTERLOCK_ID, ATTR_INTERLOCK_HC_MODE, ATTR_INTERLOCK_PARTNER]
            else:
                HC_43 = []

            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            attributes = (
                UPDATE_HEAT_COOL_ATTRIBUTES + HC_ATTRIBUTES + HC_EXTRA + HC_CONFIG + HC_SPECIAL_FIRMWARE + HC_43
            )
            _LOGGER.debug("Updated attributes for %s (firmware %s): %s", self._name, self._firmware, attributes)
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
                                    f"Temperature error {self._room_temp_error} for device {self._name}, "
                                    f"{self._id} ({self._sku})."
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
                                    f"Temperature error {self._room_temp_error} for device {self._name}, "
                                    f"{self._id} ({self._sku})."
                                ),
                                error=self._room_temp_error,
                                name=self._name,
                                id=self._id,
                                sku=self._sku,
                            )
                        )
                    self._heat_cool = device_data[ATTR_HEAT_COOL]
                    self._target_temp = float(device_data[ATTR_ROOM_SETPOINT])
                    self._min_temp = device_data[ATTR_ROOM_SETPOINT_MIN]
                    self._cur_temp = max(self._cur_temp, self._min_temp)
                    self._max_temp = device_data[ATTR_ROOM_SETPOINT_MAX]
                    self._target_cool = float(device_data[ATTR_COOL_SETPOINT])
                    self._cool_min = device_data[ATTR_COOL_SETPOINT_MIN]
                    self._cool_max = device_data[ATTR_COOL_SETPOINT_MAX]
                    self._heatcool_setpoint_delta = device_data[ATTR_HEATCOOL_SETPOINT_MIN_DELTA]
                    self._temperature_format = device_data[ATTR_TEMP]
                    self._time_format = device_data[ATTR_TIME_FORMAT]
                    self._heat_level = device_data[ATTR_OUTPUT_PERCENT_DISPLAY]["percent"]
                    self._heat_level_source_type = device_data[ATTR_OUTPUT_PERCENT_DISPLAY]["sourceType"]
                    self._heat_source_type = device_data[ATTR_HEAT_SOURCE_TYPE]
                    self._aux_heat_source_type = device_data[ATTR_AUX_HEAT_SOURCE_TYPE]
                    self._operation_mode = device_data[ATTR_SETPOINT_MODE]
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
                    self._fan_speed = device_data[ATTR_FAN_SPEED]
                    self._fan_filter_remain = device_data[ATTR_FAN_FILTER_REMAIN]
                    if ATTR_ROOM_TEMP_DISPLAY in device_data:
                        self._temp_display_status = device_data[ATTR_ROOM_TEMP_DISPLAY]["status"]
                        self._temp_display_value = device_data[ATTR_ROOM_TEMP_DISPLAY]["value"]
                    self._language = device_data[ATTR_LANGUAGE]
                    if ATTR_OCCUPANCY in device_data:
                        self._occupancy = device_data[ATTR_OCCUPANCY]
                    self._keypad = device_data[ATTR_WIFI_KEYPAD]
                    if ATTR_BACK_LIGHT in device_data:
                        self._backlight = device_data[ATTR_BACK_LIGHT]
                    self._backlight_auto_dim = device_data[ATTR_BACKLIGHT_AUTO_DIM]
                    self._early_start = device_data[ATTR_EARLY_START]
                    self._target_temp_away = device_data[ATTR_ROOM_SETPOINT_AWAY]
                    self._cool_target_temp_away = device_data[ATTR_COOL_SETPOINT_AWAY]
                    self._reversing_valve_polarity = device_data[ATTR_REVERSING_VALVE_POLARITY]
                    self._heat_lockout_temp = device_data[ATTR_HEAT_LOCK_TEMP]
                    self._cool_lockout_temp = device_data[ATTR_COOL_LOCK_TEMP]
                    self._balance_pt = device_data[ATTR_BALANCE_PT]
                    self._humidifier_type = device_data[ATTR_HUMIDIFIER_TYPE]
                    self._humidity_display = device_data[ATTR_HUMIDITY_DISPLAY]
                    self._humidity_setpoint = device_data[ATTR_HUMIDITY_SETPOINT]
                    if ATTR_CYCLE_LENGTH in device_data:
                        self._cycle_length = device_data[ATTR_CYCLE_LENGTH]
                    self._aux_cycle_length = device_data[ATTR_AUX_CYCLE_LENGTH]
                    self._cool_cycle_length = device_data[ATTR_COOL_CYCLE_LENGTH]
                    self._temp_offset_heat = device_data[ATTR_TEMP_OFFSET_HEAT]
                    self._aux_heat_min_time_on = device_data[ATTR_AUX_HEAT_MIN_TIME_ON]
                    self._aux_heat_start_delay = device_data[ATTR_AUX_HEAT_START_DELAY]
                    if ATTR_HEAT_INTERSTAGE_MIN_DELAY in device_data:
                        self._heat_interstage_min_delay = device_data[ATTR_HEAT_INTERSTAGE_MIN_DELAY]
                        self._cool_interstage_min_delay = device_data[ATTR_COOL_INTERSTAGE_MIN_DELAY]
                        self._hvac_input1_function = device_data[ATTR_HVAC_INPUT_1_FUNCTION]
                        self._scheduled_peak_delay = device_data[ATTR_SCHEDULED_PEAK_DELAY]
                        #  self._scheduled_peak_status = device_data[ATTR_SCHEDULED_PEAK_STATUS]
                    self._dual_status = device_data[ATTR_DUAL_STATUS]
                    self._cool_min_time_on = device_data[ATTR_COOL_MIN_TIME_ON]
                    self._cool_min_time_off = device_data[ATTR_COOL_MIN_TIME_OFF]
                    if ATTR_HEAT_INSTALLATION_TYPE in device_data:
                        self._heat_installation_type = device_data[ATTR_HEAT_INSTALLATION_TYPE]
                    self._output_connect_state = device_data[ATTR_OUTPUT_CONNECT_STATE]
                    accessory_type = [
                        str(accessory_type).removesuffix("Standalone")
                        for accessory_type, value in device_data[ATTR_ACCESSORY_TYPE].items()
                        if value
                    ]
                    self._accessory_type = accessory_type[0] if accessory_type else "none"
                    self._humidity_setpoint_offset = device_data[ATTR_HUMIDITY_SETPOINT_OFFSET]
                    self._humidity_setpoint_mode = device_data[ATTR_HUMIDITY_SETPOINT_MODE]
                    self._air_ex_min_time_on = device_data[ATTR_AIR_EX_MIN_TIME_ON]
                    self._heatcool_lock_cool_status = device_data[ATTR_HC_LOCK_STATUS]["cool"]
                    self._heatcool_lock_heat_status = device_data[ATTR_HC_LOCK_STATUS]["heat"]
                    self._heatcool_lock_balance_point_status = device_data[ATTR_HC_LOCK_STATUS]["balancePoint"]
                    self._dr_aux_config = device_data[ATTR_DRAUXCONF]
                    self._dr_fan_speed_conf = device_data[ATTR_DRFANCONF]
                    self._dr_accessory_conf = device_data[ATTR_DRACCESORYCONF]
                    self._heat_purge_time = device_data[ATTR_HEAT_PURGE_TIME]
                    self._cool_purge_time = device_data[ATTR_COOL_PURGE_TIME]
                    self._aux_heat_min_time_off = device_data[ATTR_AUX_HEAT_MIN_TIME_OFF]
                    self._heat_min_time_on = device_data[ATTR_HEAT_MIN_TIME_ON]
                    self._heat_min_time_off = device_data[ATTR_HEAT_MIN_TIME_OFF]
                    if self._firmware == "4.3.6":
                        self._interlock_id = device_data[ATTR_INTERLOCK_ID]
                        self._interlock_hc_mode = device_data[ATTR_INTERLOCK_HC_MODE]
                        self._interlock_partner = device_data[ATTR_INTERLOCK_PARTNER]
                    if self._device_model == 6727 or self._device_model == 6731:
                        self._air_curt_activation_temp = device_data[ATTR_AIR_ACTIVATION_TEMP]
                        self._heat_output_polarity = device_data[ATTR_HEAT_OUTPUT_POLARITY]
                        self._air_curt_conf = device_data[ATTR_AIR_CONFIG]
                        self._air_curt_max_temp = device_data[ATTR_AIR_MAX_POWER_TEMP]
                        self._dr_air_curt_conf = device_data[ATTR_DRAIR_CURT_CONF]

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
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        features = SUPPORT_HC_FLAGS

        if self._accessory_type != "none" and self._accessory_type != "heatAccumulator":
            features |= ClimateEntityFeature.TARGET_HUMIDITY

        if self.hvac_mode == HVACMode.HEAT_COOL:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        elif self.hvac_mode != HVACMode.OFF:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE

        can_control_fan = self._output_connect_state["G"]
        if can_control_fan:
            features |= ClimateEntityFeature.FAN_MODE

        return features

    @property
    @override
    def is_on(self) -> bool:
        """Return True if mode = HVACMode.HEAT or HVACMode.COOL."""
        return (
            self._heat_cool == HVACMode.HEAT
            or self._heat_cool == HVACMode.COOL
            or self._heat_cool == HVACMode.AUTO
            or self._heat_cool == MODE_EM_HEAT
        )

    @property
    @override
    def hvac_action(self) -> HVACAction | None:
        """Return current HVAC action."""
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self._heat_cool == HVACMode.COOL:
            return HVACAction.COOLING
        if self._heat_cool == HVACMode.HEAT:
            if self._heat_level == 0:
                return HVACAction.IDLE
            return HVACAction.HEATING
        if self._heat_cool in (HVACMode.HEAT_COOL, HVACMode.AUTO):
            if self._heat_level_source_type in ("heating", "auxHeating"):
                if self._heat_level == 0:
                    return HVACAction.IDLE
                return HVACAction.HEATING
            if self._heat_level_source_type == "cooling":
                return HVACAction.COOLING
        return None

    @property
    @override
    def hvac_mode(self) -> HVACMode:
        """Return current operation."""
        if self._heat_cool == HVACMode.OFF:
            return HVACMode.OFF
        elif self._heat_cool == HVACMode.AUTO:
            return HVACMode.HEAT_COOL
        elif self._heat_cool == HVACMode.COOL:
            return HVACMode.COOL
        else:
            return HVACMode.HEAT

    @property
    @override
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available operation modes."""
        outputs = self._output_connect_state
        hp_can_cool = self._reversing_valve_polarity == "heating" or outputs["OB"]
        hp_can_heat = self._reversing_valve_polarity == "cooling" or outputs["OB"]
        can_cool = outputs["Y1"] or outputs["Y2"] or hp_can_cool
        can_heat = outputs["W"] or outputs["W2"] or hp_can_heat

        return (
            ([HVACMode.HEAT_COOL] if can_heat and can_cool else [])
            + ([HVACMode.HEAT] if can_heat else [])
            + ([HVACMode.COOL] if can_cool else [])
            + [HVACMode.OFF]
        )

    @property
    @override
    def preset_mode(self) -> str:
        """Return current preset mode."""
        if self._heat_cool == MODE_EM_HEAT:
            return PRESET_BOOST

        return super().preset_mode

    @property
    @override
    def preset_modes(self) -> list[str]:
        """Return available preset modes."""
        outputs = self._output_connect_state

        hp_can_heat = self._reversing_valve_polarity == "cooling" or outputs["OB"]

        can_heat_emergency = (outputs["W"] or outputs["W2"]) and hp_can_heat and (outputs["Y1"] or outputs["Y2"])

        return PRESET_HC_MODES + ([PRESET_BOOST] if can_heat_emergency else [])

    @property
    def is_em_heat(self) -> bool:
        """Return emergency heat state."""
        return self._heat_cool == MODE_EM_HEAT

    @property
    @override
    def fan_modes(self) -> list[str] | None:
        """Return available fan modes."""
        return WIFI_FAN_SPEED

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
        if self.hvac_mode == HVACMode.COOL:
            return self.target_temperature_high
        else:
            return self.target_temperature_low

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

    @property
    @override
    def current_humidity(self) -> float | None:
        """Show current humidity percent."""
        return self._humidity_display

    @property
    @override
    def target_humidity(self) -> float | None:
        """Return target humidity."""
        if self._humidity_setpoint_mode == "defog":
            return self._humidity_setpoint_offset
        return self._humidity_setpoint

    @property
    @override
    def min_humidity(self) -> float:
        if self._humidity_setpoint_mode == "defog":
            return -10.0
        else:
            return 10.0

    @property
    @override
    def max_humidity(self) -> float:
        if self._humidity_setpoint_mode == "defog":
            return 10.0
        else:
            return 70.0

    @override
    def turn_on(self) -> None:
        """Turn the thermostat to HVACMode.HEAT_COOL."""
        self._heat_cool = HVACMode.AUTO
        self._client.set_setpoint_mode(self._id, self._heat_cool, self._is_wifi, self._is_HC)

    @override
    def turn_off(self) -> None:
        """Turn the thermostat to HVACMode.OFF."""
        self._heat_cool = HVACMode.OFF
        self._client.set_setpoint_mode(self._id, self._heat_cool, self._is_wifi, self._is_HC)

    @override
    def set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new hvac mode."""
        self._client.set_setpoint_mode(self._id, hvac_mode, self._is_wifi, self._is_HC)

        self._heat_cool = hvac_mode if hvac_mode != HVACMode.HEAT_COOL else HVACMode.AUTO

        # Reset the preset to the occupancy
        self.set_preset_mode(self._occupancy)
        self._delayed_refresh()

    def _em_heat_allowed(self) -> bool:
        """Check if device configuration allow turning on emergency heat. 'addOn' or 'conventional'."""
        if self._heat_installation_type == "conventional":
            return True
        return self._temperature < self._balance_pt

    @override
    def set_preset_mode(self, preset_mode: str) -> None:
        """Activate a preset, including BOOST which maps to emergency heat."""

        # --- BOOST = Emergency Heat ---
        if preset_mode == PRESET_BOOST:
            if not self._em_heat_allowed():
                # Condition not met → cannot activate PRESET_BOOST
                self.notify_ha(
                    translated_or_default(
                        self.hass,
                        "emergency_heat_error",
                        f"Emergency heat error for device {self._name}, ({self._sku}), cannot activate PRESET_BOOST",
                        name=self._name,
                        sku=self._sku,
                    )
                )
                return
            # Mode Conventional → always allowed
            self._heat_cool = MODE_EM_HEAT
            self._client.set_setpoint_mode(self._id, self._heat_cool, self._is_wifi, self._is_HC)
            return

        # --- Others presets (Home, Away) ---
        self._occupancy = preset_mode
        self._client.set_occupancy_mode(self._id, self._occupancy, self._is_wifi)

        if self._heat_cool == MODE_EM_HEAT:
            self.set_hvac_mode(HVACMode.HEAT)

    @override
    def turn_em_heat_on(self):
        """Set emergency heat 'on' depending on installation type and outdoor temperature."""
        self._preset_before = self.preset_mode
        # --- Mode Conventional : always allowed ---
        if not self._em_heat_allowed():
            # --- Condition not met : cannot turn on em_heat ---
            self.notify_ha(
                translated_or_default(
                    self.hass,
                    "emergency_heat_error",
                    f"Emergency heat error for device {self._name}, ({self._sku}), cannot turn emergency heat on.",
                    name=self._name,
                    sku=self._sku,
                )
            )
            return

        self._heat_cool = MODE_EM_HEAT
        self._client.set_setpoint_mode(self._id, self._heat_cool, self._is_wifi, self._is_HC)
        self.set_hvac_mode(HVACMode.HEAT)

    @override
    def turn_em_heat_off(self):
        """Set emergency heat off."""
        self._heat_cool = HVACMode.HEAT
        self._client.set_setpoint_mode(self._id, self._heat_cool, self._is_wifi, self._is_HC)
        if self._preset_before in PRESET_HC_MODES:
            self._occupancy = self._preset_before
            self._client.set_occupancy_mode(self._id, self._occupancy, self._is_wifi)

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
                temperature_low = min(temperature_low, self._target_cool - self._heatcool_setpoint_delta)
            else:
                temperature_low = min(temperature_low, self._max_temp)

            if self._target_temp != temperature_low:
                self._client.set_temperature(self._id, temperature_low)
                self._target_temp = temperature_low

        if temperature_high is not None:
            temperature_high = min(temperature_high, self._cool_max)
            if self.hvac_mode == HVACMode.HEAT_COOL:
                temperature_high = max(temperature_high, self._target_temp + self._heatcool_setpoint_delta)
            else:
                temperature_high = max(temperature_high, self._cool_min)

            if self._target_cool != temperature_high:
                self._client.set_cool_temperature(self._id, temperature_high)
                self._target_cool = temperature_high
        self._delayed_refresh()

    @override
    def set_humidity(self, humidity: int | None = None, **kwargs: Any) -> None:
        """Set new target humidity %."""
        if humidity is None:
            humidity = kwargs.get("humidity")
        if humidity is None:
            return

        if self._humidity_setpoint_mode == "defog":
            self._client.set_humidity_offset(self._id, humidity, self._is_HC)
            self._humidity_setpoint_offset = humidity
        else:
            self._client.set_humidity(self._id, humidity)
            self._humidity_setpoint = humidity

    def set_hvac_dr_options(self, value):
        """Set thermostat DR options for Eco Sinope."""
        aux_conf = value.get(ATTR_AUX_OPTIM)
        fan_speed_config = value.get(ATTR_FAN_SPEED_OPTIM)
        if aux_conf is None and fan_speed_config is None:
            param = f"{ATTR_AUX_OPTIM} or {ATTR_FAN_SPEED_OPTIM}"
            raise ServiceValidationError(
                translated_or_default(
                    self.hass,
                    "missing_parameter",
                    f"Missing required parameter: {param}.",
                    param=param,
                )
            )

        self._client.set_hvac_dr_options(value["id"], aux_conf=aux_conf, fan_speed_conf=fan_speed_config)
        if aux_conf is not None:
            self._dr_aux_config = "activated" if aux_conf == "on" else "deactivated"
        if fan_speed_config is not None:
            # Not a typo: Disabled is really sending "on" (allow fan to be always on when the optim is disabled)
            self._dr_fan_speed_conf = "auto" if fan_speed_config == "on" else "on"

    @override
    def set_heat_pump_operation_limit(self, value):
        """Set minimum temperature for heat pump operation."""
        temp = value["temp"]
        self._client.set_heat_pump_limit(value["id"], temp)
        self._balance_pt = temp

    @property
    @override
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return the state attributes."""
        data = {}
        data.update(
            {
                "eco_status": self._drstatus_active,
                "eco_optout": self._drstatus_optout,
                "eco_setpoint": self._drstatus_setpoint,
                "eco_power_relative": self._drstatus_rel,
                "eco_power_absolute": self._drstatus_abs,
                "eco_setpoint_status": self._drsetpoint_status,
                "eco_setpoint_delta": self._drsetpoint_value,
                "neviweb_occupancy_mode": self._occupancy_mode,
                "error_code": self._error_code,
                "operation_modes": self._operation_mode,
                "emergency_heating": self.is_em_heat,
                "cool_setpoint": self._target_cool,
                "cool_setpoint_min": self._cool_min,
                "cool_setpoint_max": self._cool_max,
                "setpoint_max": self._max_temp,
                "setpoint_min": self._min_temp,
                "temperature_format": self._temperature_format,
                "time_format": self._time_format,
                "keypad": lock_to_ha(self._keypad),
                "fan_speed": self._fan_speed,
                "backlight": self._backlight,
                "backlight_auto_dim": self._backlight_auto_dim,
                "early_start": self._early_start,
                "target_temp_away": self._target_temp_away,
                "cool_target_temp_away": self._cool_target_temp_away,
                "heat_cool_setpoint_delta": self._heatcool_setpoint_delta,
                "language": self._language,
                "occupancy": self._occupancy,
                "heat_source_type": self._heat_source_type,
                "heat_level": self._heat_level,
                "heat_level_source_type": self._heat_level_source_type,
                "aux_heat_source_type": self._aux_heat_source_type,
                "fan_filter_remain": self._fan_filter_remain,
                "sensor_temp_offset": self._temp_offset_heat,
                "cycle_length": self._cycle_length,
                "aux_cycle_length": self._aux_cycle_length,
                "cool_cycle_length": neviweb_to_ha(self._cool_cycle_length),
                "humidifier_type": self._humidifier_type,
                "humidity_display": self._humidity_display,
                "humidity_setpoint": self._humidity_setpoint,
                "accessory_type": self._accessory_type,
                "heat_cool": self._heat_cool,
                "temp_offset_heat": self._temp_offset_heat,
                "cool_min_time_on": self._cool_min_time_on,
                "cool_min_time_off": self._cool_min_time_off,
                "heat_installation_type": self._heat_installation_type,
                "aux_heat_min_time_on": self._aux_heat_min_time_on,
                "aux_heat_start_delay": self._aux_heat_start_delay,
                "reversing_valve_polarity": self._reversing_valve_polarity,
                "temp_display_status": self._temp_display_status,
                "temp_display_value": self._temp_display_value,
                "temp_display_error": self._room_temp_error,
                "dual_status": self._dual_status,
                "balance_point": self._balance_pt,
                "heat_lock_temp": self._heat_lockout_temp,
                "cool_lock_temp": self._cool_lockout_temp,
                "output_connect_state": self._output_connect_state,
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
        data.update(
            {
                "humidity_setpoint_offset": self._humidity_setpoint_offset,
                "humidity_setpoint_mode": self._humidity_setpoint_mode,
                "exchanger_min_time_on": self._air_min_time_on,
                "heatcool_lock_cool_status": self._heatcool_lock_cool_status,
                "heatcool_lock_heat_status": self._heatcool_lock_heat_status,
                "heatcool_lock_balancePoint_status": self._heatcool_lock_balance_point_status,
                "dr_aux_config": self._dr_aux_config,
                "dr_fan_speed_conf": self._dr_fan_speed_conf,
                "dr_accessory_conf": self._dr_accessory_conf,
                "heat_purge_time": self._heat_purge_time,
                "cool_purge_time": self._cool_purge_time,
                "aux_heat_min_time_off": self._aux_heat_min_time_off,
                "heat_min_time_on": self._heat_min_time_on,
                "heat_min_time_off": self._heat_min_time_off,
            }
        )
        if self._device_model == 6727:
            data.update(
                {
                    "heat_interstage_min_delay": self._aux_interstage_min_delay,
                    "cool_interstage_min_delay": self._cool_interstage_min_delay,
                    "hvac_input1_function": self._hvac_input1_function,
                    #  "scheduled_peak_status": self._scheduled_peak_status,
                    "scheduled_peak_delay": self._scheduled_peak_delay,
                }
            )
        if self._device_model == 6727 or self._device_model == 6731:
            data.update(
                {
                    "air_curtain_activation_temp": self._air_curt_activation_temp,
                    "heat_output_polarity": self._heat_output_polarity,
                    "air_curtain_conf": self._air_curt_conf,
                    "air_curtain_max_temp": self._air_curt_max_temp,
                    "dr_air_curtain_conf": self._dr_air_curt_conf,
                }
            )
        if self._firmware == "4.3.6":
            data.update(
                {
                    "interlock_id": self._interlock_id,
                    "interlock_hc_mode": self._interlock_hc_mode,
                    "interlock_partner": self._interlock_partner,
                }
            )
        for mode in TH6_MODES_VALUES:
            data[f"{mode}_hourly_total_count"] = getattr(self, f"_{mode}_hourly_total_count")
            data[f"{mode}_hourly_count"] = getattr(self, f"_{mode}_hourly_count")
            data[f"{mode}_hourly_last_timestamp"] = getattr(self, f"_{mode}_hourly_last_timestamp")
            data[f"{mode}_hourly_last_timestamp_local"] = getattr(self, f"_{mode}_hourly_last_timestamp_local")

        return data
