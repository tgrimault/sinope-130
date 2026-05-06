"""Base thermostat class and module-level constants for neviweb130 climate platform."""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone
from typing import Any, Callable, Mapping, override

import homeassistant.util.dt as dt_util
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    PRESET_AWAY,
    PRESET_BOOST,
    PRESET_HOME,
    PRESET_NONE,
    HVACAction,
    HVACMode,
)
from homeassistant.components.persistent_notification import DOMAIN as PN_DOMAIN
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.event import call_later

from .. import HOMEKIT_MODE, NOTIFY
from .. import SCAN_INTERVAL as scan_interval
from .. import STAT_INTERVAL
from ..const import (
    ATTR_ACCESSORY_TYPE,
    ATTR_ACTIVE,
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
    ATTR_BACK_LIGHT,
    ATTR_BACKLIGHT,
    ATTR_BACKLIGHT_AUTO_DIM,
    ATTR_BALANCE_PT,
    ATTR_BALANCE_PT_TEMP_HIGH,
    ATTR_BALANCE_PT_TEMP_LOW,
    ATTR_COLD_LOAD_PICKUP,
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
    ATTR_FLOOR_AIR_LIMIT,
    ATTR_FLOOR_AUX,
    ATTR_FLOOR_MAX,
    ATTR_FLOOR_MIN,
    ATTR_FLOOR_MODE,
    ATTR_FLOOR_OUTPUT1,
    ATTR_FLOOR_OUTPUT2,
    ATTR_FLOOR_SENSOR,
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
    VERSION,
)
from ..helpers import file_exists, safe_get_device_attributes, translated_or_default
from ..schema import (
    AUX_HEATING,
    CYCLE_LENGTH_VALUES,
    FAN_SPEED,
    FAN_SPEED_VALUES,
    FAN_SPEED_VALUES_5,
    FULL_SWING,
    FULL_SWING_OFF,
    HP_FAN_SPEED,
    NEVIWEB_MODE_MAP,
    WIFI_FAN_SPEED,
)
from .mixins import (
    _BlockedMethod,
    FloorMixin,
    LowVoltageMixin,
    HeatPumpMixin,
    HeatCoolMixin,
    ERROR_HANDLERS,
    neviweb_to_ha,
    lock_to_ha,
    neviweb_to_ha_fan,
    neviweb_to_ha_mode,
    extract_capability_full,
    extract_capability,
    resolve_fan_speed,
)

_LOGGER = logging.getLogger(__name__)

NEVIWEB_TO_HA_MODE = {v: k for k, v in NEVIWEB_MODE_MAP.items()}

SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.PRESET_MODE
    | ClimateEntityFeature.TURN_OFF
    | ClimateEntityFeature.TURN_ON
)
SUPPORT_AUX_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.PRESET_MODE
    | ClimateEntityFeature.TURN_OFF
    | ClimateEntityFeature.TURN_ON
)

SUPPORT_HP_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.PRESET_MODE
    | ClimateEntityFeature.FAN_MODE
    | ClimateEntityFeature.SWING_HORIZONTAL_MODE
    | ClimateEntityFeature.SWING_MODE
    | ClimateEntityFeature.TURN_OFF
    | ClimateEntityFeature.TURN_ON
)

SUPPORT_H_c_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.PRESET_MODE
    | ClimateEntityFeature.FAN_MODE
    | ClimateEntityFeature.SWING_MODE
    | ClimateEntityFeature.TURN_OFF
    | ClimateEntityFeature.TURN_ON
)

SUPPORT_HC_FLAGS = ClimateEntityFeature.PRESET_MODE | ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON

SNOOZE_TIME = 1200
SCAN_INTERVAL = scan_interval

UPDATE_ATTRIBUTES = [
    ATTR_DRSETPOINT,
    ATTR_DRSTATUS,
    ATTR_OUTPUT_PERCENT_DISPLAY,
    ATTR_ROOM_SETPOINT,
    ATTR_ROOM_SETPOINT_MAX,
    ATTR_ROOM_SETPOINT_MIN,
    ATTR_ROOM_TEMPERATURE,
    ATTR_TEMP,
    ATTR_TIME_FORMAT,
]

UPDATE_LITE_ATTRIBUTES = [
    ATTR_DRSETPOINT,
    ATTR_DRSTATUS,
    ATTR_OUTPUT_PERCENT_DISPLAY,
    ATTR_ROOM_SETPOINT,
    ATTR_ROOM_SETPOINT_MAX,
    ATTR_ROOM_SETPOINT_MIN,
    ATTR_ROOM_TEMPERATURE,
    ATTR_TEMP,
]

UPDATE_HP_ATTRIBUTES = [
    ATTR_ROOM_SETPOINT,
    ATTR_ROOM_SETPOINT_MAX,
    ATTR_ROOM_SETPOINT_MIN,
    ATTR_COOL_SETPOINT_MIN,
    ATTR_COOL_SETPOINT_MAX,
    ATTR_ROOM_TEMPERATURE,
    ATTR_TEMP,
]

UPDATE_HEAT_COOL_ATTRIBUTES = [
    ATTR_DRSETPOINT,
    ATTR_DRSTATUS,
    ATTR_OUTPUT_PERCENT_DISPLAY,
    ATTR_ROOM_SETPOINT,
    ATTR_COOL_SETPOINT,
    ATTR_ROOM_SETPOINT_MAX,
    ATTR_ROOM_SETPOINT_MIN,
    ATTR_COOL_SETPOINT_MAX,
    ATTR_COOL_SETPOINT_MIN,
    ATTR_ROOM_TEMP_DISPLAY,
    ATTR_ROOM_TEMPERATURE,
    ATTR_TEMP,
    ATTR_TIME_FORMAT,
]

SUPPORTED_HVAC_WIFI_MODES: list[HVACMode] = [
    HVACMode.AUTO,
    HVACMode.HEAT,
    HVACMode.OFF,
]

SUPPORTED_HVAC_WIFI_LITE_MODES: list[HVACMode] = [
    HVACMode.AUTO,
    HVACMode.HEAT,
    HVACMode.OFF,
]

SUPPORTED_HVAC_MODES: list[HVACMode] = [
    HVACMode.HEAT,
    HVACMode.OFF,
]

SUPPORTED_HVAC_H_C_MODES: list[HVACMode] = [
    HVACMode.COOL,
    HVACMode.HEAT,
    HVACMode.OFF,
]

SUPPORTED_HVAC_HC_MODES: list[HVACMode] = [
    HVACMode.HEAT_COOL,
    HVACMode.HEAT,
    HVACMode.COOL,
    HVACMode.OFF,
]

SUPPORTED_HVAC_HP_MODES: list[HVACMode] = [
    HVACMode.COOL,
    HVACMode.DRY,
    HVACMode.FAN_ONLY,
    HVACMode.HEAT,
    HVACMode.OFF,
]

SUPPORTED_HVAC_WHP_MODES: list[HVACMode] = [
    HVACMode.HEAT_COOL,
    HVACMode.COOL,
    HVACMode.DRY,
    HVACMode.FAN_ONLY,
    HVACMode.HEAT,
    HVACMode.OFF,
]

SUPPORTED_HVAC_HEAT_MODES: list[HVACMode] = [
    HVACMode.FAN_ONLY,
    HVACMode.HEAT,
    HVACMode.OFF,
]

SUPPORTED_HVAC_COOL_MODES: list[HVACMode] = [
    HVACMode.COOL,
    HVACMode.DRY,
    HVACMode.FAN_ONLY,
    HVACMode.OFF,
]

PRESET_WIFI_MODES = [
    PRESET_HOME,
    PRESET_AWAY,
    PRESET_NONE,
]

PRESET_MODES = [
    PRESET_AWAY,
    PRESET_NONE,
]

PRESET_HP_MODES = [
    PRESET_HOME,
    PRESET_AWAY,
    PRESET_NONE,
]

PRESET_HC_MODES = [
    PRESET_HOME,
    PRESET_AWAY,
]

PRESET_h_c_MODES = [
    PRESET_HOME,
    PRESET_AWAY,
]

DEVICE_MODEL_LOW = [7372]
DEVICE_MODEL_LOW_WIFI = [739]
DEVICE_MODEL_FLOOR = [737]
DEVICE_MODEL_WIFI_FLOOR = [738]
DEVICE_MODEL_WIFI = [1510, 742]
DEVICE_MODEL_WIFI_LITE = [336, 343, 348]
DEVICE_MODEL_COLOR_WIFI = [350]
DEVICE_MODEL_HEAT = [1123, 1124]
DEVICE_MODEL_DOUBLE = [7373]
DEVICE_MODEL_HEAT_G2 = [300]
DEVICE_MODEL_HC = [1512]
DEVICE_MODEL_HEAT_PUMP = [6810, 6811, 6812]
DEVICE_MODEL_WIFI_HEAT_PUMP = [6813, 6814]
DEVICE_MODEL_HEAT_COOL = [6727, 6730, 6731]
IMPLEMENTED_DEVICE_MODEL = (
    DEVICE_MODEL_HEAT
    + DEVICE_MODEL_FLOOR
    + DEVICE_MODEL_LOW
    + DEVICE_MODEL_WIFI_FLOOR
    + DEVICE_MODEL_WIFI
    + DEVICE_MODEL_LOW_WIFI
    + DEVICE_MODEL_HEAT_G2
    + DEVICE_MODEL_HC
    + DEVICE_MODEL_DOUBLE
    + DEVICE_MODEL_HEAT_PUMP
    + DEVICE_MODEL_HEAT_COOL
    + DEVICE_MODEL_WIFI_LITE
    + DEVICE_MODEL_COLOR_WIFI
    + DEVICE_MODEL_WIFI_HEAT_PUMP
)



class Neviweb130Thermostat(ClimateEntity):
    """Implementation of Neviweb TH1123ZB, TH1124ZB thermostat."""

    _enable_turn_on_off_backwards_compatibility = False
    _attr_precision = 0.1
    _attr_target_temperature_step = 0.5

    def __init__(self, device_info, name, sku, firmware, location, client):
        """Initialize."""
        _LOGGER.debug("Setting up %s: %s", name, device_info)
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_unit_class = "energy"
        self._attr_statistic_mean_type = StatisticMeanType.ARITHMETIC

        self._name = name
        self._location = str(location)
        self._sku = sku
        self._firmware = firmware
        self._client = client
        self._id = str(device_info["id"])
        self._device_model = device_info["signature"]["model"]
        self._device_model_cfg = device_info["signature"]["modelCfg"]
        self._is_double = device_info["signature"]["model"] in DEVICE_MODEL_DOUBLE
        self._is_h_c = device_info["signature"]["model"] in DEVICE_MODEL_HC
        self._is_HC = device_info["signature"]["model"] in DEVICE_MODEL_HEAT_COOL
        self._is_gen2 = device_info["signature"]["model"] in DEVICE_MODEL_HEAT_G2
        self._is_floor = device_info["signature"]["model"] in DEVICE_MODEL_FLOOR
        self._is_wifi_floor = device_info["signature"]["model"] in DEVICE_MODEL_WIFI_FLOOR
        self._is_wifi = (
            device_info["signature"]["model"] in DEVICE_MODEL_WIFI_FLOOR
            or device_info["signature"]["model"] in DEVICE_MODEL_WIFI
            or device_info["signature"]["model"] in DEVICE_MODEL_LOW_WIFI
            or device_info["signature"]["model"] in DEVICE_MODEL_WIFI_LITE
            or device_info["signature"]["model"] in DEVICE_MODEL_HEAT_COOL
            or device_info["signature"]["model"] in DEVICE_MODEL_COLOR_WIFI
            or device_info["signature"]["model"] in DEVICE_MODEL_WIFI_HEAT_PUMP
        )
        self._is_wifi_lite = device_info["signature"]["model"] in DEVICE_MODEL_WIFI_LITE
        self._is_low_voltage = device_info["signature"]["model"] in DEVICE_MODEL_LOW
        self._is_low_wifi = device_info["signature"]["model"] in DEVICE_MODEL_LOW_WIFI
        self._is_HP = device_info["signature"]["model"] in DEVICE_MODEL_HEAT_PUMP
        self._is_WHP = device_info["signature"]["model"] in DEVICE_MODEL_WIFI_HEAT_PUMP
        self._is_color_wifi = device_info["signature"]["model"] in DEVICE_MODEL_COLOR_WIFI
        self._active = True
        self._active_errors = set()
        self._aux_cycle_length = 0
        self._avail_mode = None
        self._backlight = None
        self._balance_pt: float = -15.0
        self._balance_pt_high = None
        self._balance_pt_low = None
        self._cool_lockout_temp = None
        self._cool_max = 36
        self._cool_min = 15
        self._cur_temp = 0.0
        self._cur_temp_before = 0.0
        self._cycle_length = 0
        self._cycle_length_output2_status = "off"
        self._cycle_length_output2_value = 0
        self._daily_kwh_count = 0
        self._display2 = None
        self._display_conf = None
        self._drsetpoint_status = "off"
        self._drsetpoint_value = 0
        self._drstatus_abs = "off"
        self._drstatus_active = "off"
        self._drstatus_onoff = "off"
        self._drstatus_optout = "off"
        self._drstatus_rel = "off"
        self._drstatus_setpoint = "off"
        self._early_start = None
        self._em_heat = "off"
        self._energy_stat_time = time.time() - 1500
        self._error_code = 0
        self._fan_speed = None
        self._fan_swing_cap = None
        self._fan_swing_cap_horiz = None
        self._fan_swing_cap_vert = None
        self._fan_swing_horiz = None
        self._fan_swing_vert = None
        self._floor_air_limit = None
        self._floor_max = None
        self._floor_max_status = None
        self._floor_min = None
        self._floor_min_status = None
        self._floor_mode = None
        self._floor_sensor_type = None
        self._heat_level = 0
        self._heat_lockout_temp = None
        self._hour_kwh = 0
        self._hourly_kwh_count = 0
        self._keypad = "unlocked"
        self._language = None
        self._load2 = None
        self._load2_status = None
        self._mark = None
        self._marker = None
        self._max_temp = 30
        self._min_temp = 5
        self._month_kwh = 0
        self._monthly_kwh_count = 0
        self._occupancy = "home"
        self._occupancy_mode = "home"
        self._operation_mode = None
        self._pump_protec_duration = None
        self._pump_protec_period = None
        self._pump_protec_status = "off"
        self._rssi = None
        self._snooze = 0.0
        self._sound_conf = None
        self._target_cool = 21.5
        self._target_temp = 20.0
        self._target_temp_away = None
        self._temp_display_value = None
        self._temperature: float = 20.0
        self._temperature_format = "celsius"
        self._time_format = "24h"
        self._today_kwh = 0
        self._total_kwh_count = 0
        self._wattage = 0
        self._weather_icon = 0

    def _fetch_attributes(self) -> dict:
        """Fetch device attributes from Neviweb, handling safe_mode branching."""
        HEAT_ATTRIBUTES = [
            ATTR_WATTAGE,
            ATTR_KEYPAD,
            ATTR_BACKLIGHT,
            ATTR_SYSTEM_MODE,
            ATTR_CYCLE_LENGTH,
            ATTR_DISPLAY2,
            ATTR_RSSI,
        ]
        if self._firmware == "0.6.4" or self._firmware == "0.6.0":
            FIRMWARE_SPECIAL = []
        else:
            FIRMWARE_SPECIAL = [ATTR_ROOM_TEMP_DISPLAY]
        attributes = UPDATE_ATTRIBUTES + HEAT_ATTRIBUTES + FIRMWARE_SPECIAL
        _LOGGER.debug("4.2.3, updated attributes for %s: %s", self._name, attributes)
        safe_mode = self.hass.data[DOMAIN]["safe_mode"]
        if safe_mode == self._id:
            from custom_components.neviweb130.climate import safe_get_device_attributes as _safe_get
            return _safe_get(
                self.hass,
                self._client,
                self._id,
                attributes,
                _LOGGER,
                device_sku=self._sku,
                device_model=self._device_model,
                firmware=self._firmware,
            )
        return self._client.get_device_attributes(self._id, attributes)

    def _parse_dr_state(self, data: dict) -> None:
        """Assign all DR setpoint and DR status fields from device data."""
        if ATTR_DRSETPOINT in data:
            self._drsetpoint_status = data[ATTR_DRSETPOINT]["status"]
            self._drsetpoint_value = (
                data[ATTR_DRSETPOINT]["value"]
                if data[ATTR_DRSETPOINT]["value"] is not None
                else 0
            )
        if ATTR_DRSTATUS in data:
            self._drstatus_active = data[ATTR_DRSTATUS]["drActive"]
            self._drstatus_optout = data[ATTR_DRSTATUS]["optOut"]
            self._drstatus_setpoint = data[ATTR_DRSTATUS]["setpoint"]
            self._drstatus_abs = data[ATTR_DRSTATUS]["powerAbsolute"]
            self._drstatus_rel = data[ATTR_DRSTATUS]["powerRelative"]

    def _parse_common_state(self, data: dict) -> None:
        """Assign common thermostat state fields from device data."""
        self._cur_temp_before = self._cur_temp
        self._cur_temp = (
            float(data[ATTR_ROOM_TEMPERATURE]["value"])
            if data[ATTR_ROOM_TEMPERATURE]["value"] is not None
            else self._cur_temp_before
        )
        self._target_temp = float(data[ATTR_ROOM_SETPOINT])
        self._min_temp = data[ATTR_ROOM_SETPOINT_MIN]
        self._cur_temp = max(self._cur_temp, self._min_temp)
        self._max_temp = data[ATTR_ROOM_SETPOINT_MAX]
        self._temperature_format = data[ATTR_TEMP]
        self._time_format = data[ATTR_TIME_FORMAT]
        if ATTR_ROOM_TEMP_DISPLAY in data:
            self._temp_display_value = data[ATTR_ROOM_TEMP_DISPLAY]
        self._display2 = data[ATTR_DISPLAY2]
        self._heat_level = data[ATTR_OUTPUT_PERCENT_DISPLAY]
        self._keypad = data[ATTR_KEYPAD]
        self._backlight = data[ATTR_BACKLIGHT]
        if ATTR_CYCLE_LENGTH in data:
            self._cycle_length = data[ATTR_CYCLE_LENGTH]
        if ATTR_RSSI in data:
            self._rssi = data[ATTR_RSSI]
        self._operation_mode = data[ATTR_SYSTEM_MODE]
        if not self._is_low_voltage:
            self._wattage = data[ATTR_WATTAGE]

    def _handle_error(self, device_data: dict) -> bool:
        """Handle error keys in device_data. Returns True if an error was found."""
        if "error" in device_data:
            self.log_error(device_data["error"]["code"])
            return True
        if "errorCode" in device_data:
            if device_data["errorCode"] == "ReadTimeout":
                _LOGGER.warning(
                    "A timeout occur during data update. Device %s do not respond. Check your network... (%s)",
                    self._name,
                    device_data,
                )
            else:
                _LOGGER.warning("Error in updating device %s: (%s)", self._name, device_data)
            return True
        return False

    def update(self) -> None:
        """Get the latest data from Neviweb and update the state."""
        if not self._active:
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
            return
        start = time.time()
        device_data = self._fetch_attributes()
        neviweb_status = self._client.get_neviweb_status(self._location)
        elapsed = round(time.time() - start, 3)
        _LOGGER.debug("Updating %s (%s sec): %s", self._name, elapsed, device_data)
        if not self._handle_error(device_data):
            self._parse_dr_state(device_data)
            self._parse_common_state(device_data)
        status = neviweb_status.get(ATTR_OCCUPANCY)
        if isinstance(status, str):
            self._occupancy_mode = status
        self.do_stat(start)
        self.get_sensor_error_code()
        self.get_weather()

    @property
    @override
    def unique_id(self) -> str:
        """Return unique ID based on Neviweb130 device ID."""
        return self._client.scoped_unique_id(self._id)

    @property
    @override
    def name(self) -> str:
        """Return the name of the thermostat."""
        return self._name

    @property
    def entity_picture(self) -> str | None:
        """Replace entity picture by heat level icon."""
        if self._heat_level is None:
            return None

        icon_path = self.icon_type
        if file_exists(self.hass, icon_path):
            return icon_path

        return None

    @property
    @override
    def temperature_unit(self) -> UnitOfTemperature:
        """Return the unit of measurement of this entity, if any."""
        # Will always send Celsius values even if it's configured to display in Fahrenheit
        return UnitOfTemperature.CELSIUS

    @property
    @override
    def device_class(self) -> SensorDeviceClass:
        """Return the device class of this entity."""
        return SensorDeviceClass.TEMPERATURE

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

    @property
    def pi_heating_demand(self) -> int:
        """Heating demand."""
        return self._heat_level

    @property
    def icon_type(self) -> str:
        """Select icon based on pi_heating_demand value."""
        is_floor = self._is_floor or self._is_wifi_floor
        base = "floor" if is_floor else "heat"

        # OFF mode set off icon
        if self.hvac_mode == HVACMode.OFF:
            return f"/local/neviweb130/{base}-off.png"

        # AUTO mode → change prefix
        if self.hvac_mode == HVACMode.AUTO:
            base = "floor-auto" if is_floor else "heat-auto"

        demand = self.pi_heating_demand or 0

        thresholds = [
            (1, "-0"),
            (21, "-1"),
            (41, "-2"),
            (61, "-3"),
            (81, "-4"),
        ]

        for limit, suffix in thresholds:
            if demand < limit:
                return f"/local/neviweb130/{base}{suffix}.png"

        return f"/local/neviweb130/{base}-5.png"

    @property
    @override
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        if self._is_floor or self._is_wifi_floor or self._is_low_wifi or self._is_low_voltage:
            return SUPPORT_AUX_FLAGS
        elif self._is_HP or self._is_WHP:
            return SUPPORT_HP_FLAGS
        elif self._is_h_c:
            return SUPPORT_H_c_FLAGS
        else:
            return SUPPORT_FLAGS

    @property
    def is_em_heat(self) -> bool:
        """Return emergency heat state."""
        if self._em_heat == "slave":
            return True
        elif self._cycle_length_output2_status == "on":
            return True
        elif self._aux_cycle_length > 0:
            return True
        else:
            return False

    @property
    @override
    def target_temperature_low(self) -> float:
        """(deprecated, use min_temp) Return the minimum heating temperature."""
        return self._min_temp

    @property
    @override
    def target_temperature_high(self) -> float:
        """(deprecated, use max_temp) Return the maximum heating temperature."""
        return self._max_temp

    @property
    @override
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return self._min_temp

    @property
    @override
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return self._max_temp

    @property
    def min_cool_temp(self) -> float:
        """Return the minimum cooling temperature."""
        return self._cool_min

    @property
    def max_cool_temp(self) -> float:
        """Return the maximum cooling temperature."""
        return self._cool_max

    @property
    def outdoor_temp(self) -> float:
        return self._temperature

    @property
    def weather_icon(self) -> int:
        return self._weather_icon

    @property
    @override
    def hvac_mode(self) -> HVACMode:
        """Return current operation."""
        if self._operation_mode == HVACMode.OFF:
            return HVACMode.OFF
        elif self._operation_mode in [HVACMode.AUTO, MODE_AUTO_BYPASS]:
            return HVACMode.AUTO
        elif self._operation_mode == HVACMode.COOL:
            return HVACMode.COOL
        elif self._operation_mode == HVACMode.DRY:
            return HVACMode.DRY
        elif self._operation_mode == HVACMode.FAN_ONLY:
            return HVACMode.FAN_ONLY
        else:
            return HVACMode.HEAT

    @property
    @override
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available operation modes."""
        if self._is_wifi_lite:
            return SUPPORTED_HVAC_WIFI_LITE_MODES
        elif self._is_WHP:
            return SUPPORTED_HVAC_WHP_MODES
        elif self._is_wifi:
            return SUPPORTED_HVAC_WIFI_MODES
        elif self._is_h_c:
            if self._avail_mode == "heatingOnly":
                return SUPPORTED_HVAC_HEAT_MODES
            elif self._avail_mode == "coolingOnly":
                return SUPPORTED_HVAC_COOL_MODES
            else:
                return SUPPORTED_HVAC_H_C_MODES
        elif self._is_HP:
            if self._avail_mode == "heatingOnly":
                return SUPPORTED_HVAC_HEAT_MODES
            elif self._avail_mode == "coolingOnly":
                return SUPPORTED_HVAC_COOL_MODES
            else:
                return SUPPORTED_HVAC_HP_MODES
        else:
            return SUPPORTED_HVAC_MODES

    @property
    @override
    def current_temperature(self) -> float | None:
        """Return the room current temperature."""
        return self._cur_temp

    @property
    @override
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach less Eco Sinope dr_setpoint delta."""
        if self._target_temp is not None:
            temp = self._target_temp + self._drsetpoint_value
        else:
            temp = 0
        if temp < self._min_temp:
            return self._min_temp
        if temp > self._max_temp:
            return self._max_temp
        return temp

    @property
    def target_cool_temperature(self) -> float:
        """Return the cooling temperature we try to reach."""
        if self._target_cool is not None:
            temp = self._target_cool
        else:
            temp = 0
        if temp < self._cool_min:
            return self._cool_min
        if temp > self._cool_max:
            return self._cool_max
        return temp

    @property
    @override
    def preset_mode(self) -> str:
        """Return current preset mode."""
        if self._occupancy == PRESET_HOME:
            return PRESET_HOME
        elif self._occupancy == PRESET_AWAY:
            return PRESET_AWAY
        else:
            return PRESET_NONE

    @property
    @override
    def preset_modes(self) -> list[str]:
        """Return available preset modes."""
        if self._is_h_c:
            return PRESET_h_c_MODES
        elif self._is_wifi:
            return PRESET_WIFI_MODES
        elif self._is_HP or self._is_WHP:
            return PRESET_HP_MODES
        else:
            return PRESET_MODES

    @property
    @override
    def hvac_action(self) -> str | HVACAction | None:  # type: ignore[override]
        """Return current HVAC action."""
        if self._operation_mode == HVACMode.OFF:
            return HVACAction.OFF
        elif self._operation_mode == HVACMode.COOL:
            return HVACAction.COOLING
        elif self._operation_mode == HVACMode.FAN_ONLY:
            return HVACAction.FAN
        elif self._operation_mode == HVACMode.DRY:
            return HVACAction.DRYING
        elif not HOMEKIT_MODE and self._operation_mode == MODE_AUTO_BYPASS:
            if self._heat_level == 0:
                return f"{HVACAction.IDLE.value} ({MODE_AUTO_BYPASS})"
            else:
                return f"{HVACAction.HEATING.value} ({MODE_AUTO_BYPASS})"
        elif self._heat_level == 0:
            return HVACAction.IDLE
        else:
            return HVACAction.HEATING

    @property
    def is_on(self) -> bool:
        """Return True if mode = HVACMode.HEAT or HVACMode.COOL."""
        return (
            self._operation_mode == HVACMode.HEAT
            or self._operation_mode == HVACMode.COOL
            or self._operation_mode == HVACMode.DRY
            or self._operation_mode == HVACMode.AUTO
            or self._operation_mode == MODE_MANUAL
            or self._operation_mode == HVACMode.FAN_ONLY
        )

    @property
    @override
    def fan_mode(self) -> str | None:
        """Return the fan setting."""
        return self._fan_speed

    @property
    @override
    def fan_modes(self) -> list[str] | None:
        """Return available fan modes."""
        if self._is_HP or self._is_h_c:
            return FAN_SPEED
        elif self._is_WHP:
            return HP_FAN_SPEED
        else:
            return None

    @property
    @override
    def swing_mode(self) -> str | None:
        """Return the fan vertical swing setting."""
        if self._is_HP or self._is_WHP or self._is_h_c:
            return self._fan_swing_vert
        return None

    @property
    @override
    def swing_modes(self) -> list[str] | None:
        """Return available vertical swing modes."""
        if self._is_HP or self._is_WHP or self._is_h_c:
            if self._fan_swing_cap is None or self._fan_swing_cap_vert is None:
                return None
            elif not extract_capability(self._fan_swing_cap):
                return None
            elif "fullVertical" in extract_capability(self._fan_swing_cap):
                return FULL_SWING + extract_capability_full(self._fan_swing_cap_vert)
            else:
                return extract_capability_full(self._fan_swing_cap_vert)
        else:
            return None

    @property
    @override
    def swing_horizontal_mode(self) -> str | None:
        """Return the fan swing setting."""
        if self._is_HP or self._is_WHP or self._is_h_c:
            return self._fan_swing_horiz
        return None

    @property
    @override
    def swing_horizontal_modes(self) -> list[str] | None:
        """Return available horizontal swing modes"""
        if self._is_HP or self._is_WHP or self._is_h_c:
            if self._fan_swing_cap is None or self._fan_swing_cap_horiz is None:
                return None
            elif not extract_capability(self._fan_swing_cap):
                return None
            elif "fullHorizontal" in extract_capability(self._fan_swing_cap):
                return FULL_SWING + extract_capability_full(self._fan_swing_cap_horiz)
            else:
                return extract_capability_full(self._fan_swing_cap_horiz)
        else:
            return None

    @property
    def _is_HC_like(self) -> bool:
        """Return True if device must be managed as HC."""
        return self._is_HC or self._is_WHP

    @override
    def turn_on(self) -> None:
        """Turn the thermostat to HVACMode.HEAT."""
        self._client.set_setpoint_mode(self._id, HVACMode.HEAT, self._is_wifi, self._is_HC)
        self._operation_mode = HVACMode.HEAT

    @override
    def turn_off(self) -> None:
        """Turn the thermostat to HVACMode.OFF."""
        self._client.set_setpoint_mode(self._id, HVACMode.OFF, self._is_wifi, self._is_HC)
        self._operation_mode = HVACMode.OFF

    @override
    def set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        temperature = min(temperature, self._max_temp)
        temperature = max(temperature, self._min_temp)
        self._client.set_temperature(self._id, temperature)
        self._target_temp = temperature
        self._delayed_refresh()

    def set_second_display(self, value):
        """Set thermostat second display between outside and setpoint temperature."""
        if value["display"] == "outsideTemperature":
            display_name = "Outside"
        else:
            display_name = "Setpoint"
        self._client.set_second_display(value["id"], value["display"])
        self._display2 = display_name

    def set_backlight(self, value):
        """Set thermostat backlight «auto» = off when idle / on when active or «on» = always on.
        Work differently for Zigbee and Wi-Fi devices."""
        is_wifi = self._is_wifi or self._is_low_wifi or self._is_wifi_lite or self._is_wifi_floor
        if value["level"] == "on":
            if is_wifi:
                level_command = "alwaysOn"
            else:
                level_command = "always"
            level_name = "On"
        elif value["level"] == "bedroom":
            level_command = "bedroom"
            level_name = "bedroom"
        else:
            if is_wifi:
                level_command = "onUserAction"
            else:
                level_command = "onActive"
            level_name = "Auto"
        self._client.set_backlight(value["id"], level_command, is_wifi)
        self._backlight = level_name

    def set_keypad_lock(self, value):
        """Lock or unlock device's keypad, Zigbee: locked, unlocked, partiallyLocked."""
        """ Wi-Fi: lock, unlock, partialLock."""
        lock = value["lock"]
        if lock == "partiallyLocked" and self._is_HP:
            raise ServiceValidationError(
                translated_or_default(
                    self.hass,
                    "Invalid_lock_value",
                    "Invalid lock value for model HP (partiallyLocked)",
                    lock="partiallyLocked",
                    model="HP",
                )
            )
        if self._is_wifi:
            match lock:
                case "locked":
                    lock = "lock"
                case "unlocked":
                    lock = "unlock"
                case "partiallyLocked":
                    lock = "partialLock"
                case _:
                    raise ServiceValidationError(
                        translated_or_default(
                            self.hass,
                            "Invalid_lock_value",
                            f"Invalid lock value for model 'Any' ({lock})",
                            lock=lock,
                            model="Any",
                        )
                    )

        self._client.set_keypad_lock(value["id"], lock, self._is_wifi)
        self._keypad = lock

    def set_time_format(self, value):
        """Set time format 12h or 24h."""
        if value[ATTR_TIME] == 12:
            time_command = "12h"
        else:
            time_command = "24h"
        self._client.set_time_format(value["id"], time_command)
        self._time_format = time_command

    def set_temperature_format(self, value):
        """Set temperature format, celsius or fahrenheit."""
        self._client.set_temperature_format(value["id"], value["temp"])
        self._temperature_format = value["temp"]

    def set_setpoint_max(self, value):
        """Set maximum setpoint temperature."""
        self._client.set_setpoint_max(value["id"], value["temp"])
        self._max_temp = value["temp"]

    def set_setpoint_min(self, value):
        """Set minimum setpoint temperature."""
        self._client.set_setpoint_min(value["id"], value["temp"])
        self._min_temp = value["temp"]

    def set_room_setpoint_away(self, value):
        """Set device away heating setpoint."""
        self._client.set_room_setpoint_away(value["id"], value["temp"])
        self._target_temp_away = value["temp"]

    def set_early_start(self, value):
        """Set early heating on/off for Wi-Fi thermostat."""
        self._client.set_early_start(value["id"], value["start"])
        self._early_start = value["start"]

    def set_hvac_dr_options(self, value):
        """Set thermostat DR options for Eco Sinope."""
        self._client.set_hvac_dr_options(
            value["id"], dractive=value["dractive"], optout=value["optout"], setpoint=value["setpoint"]
        )
        self._drstatus_active = value["dractive"]
        self._drstatus_optout = value["optout"]
        self._drstatus_setpoint = value["setpoint"]

    def set_hvac_dr_setpoint(self, value):
        """Set thermostat DR setpoint values for Eco Sinope."""
        self._client.set_hvac_dr_setpoint(value["id"], value["status"], value["val"])
        self._drsetpoint_status = value["status"]
        self._drsetpoint_value = value["val"]

    @override
    def set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new hvac mode."""

        # Simple modes, we call directly set_point_mode
        simple_modes = [
            HVACMode.OFF,
            HVACMode.HEAT,
            MODE_MANUAL,
            HVACMode.COOL,
            HVACMode.DRY,
            HVACMode.FAN_ONLY,
            MODE_EM_HEAT,
        ]

        if hvac_mode in simple_modes:
            self._client.set_setpoint_mode(self._id, hvac_mode, self._is_wifi, self._is_HC_like)

        elif hvac_mode == HVACMode.AUTO:
            self._client.set_setpoint_mode(self._id, hvac_mode, self._is_wifi, self._is_HC_like)

        elif hvac_mode == HVACMode.HEAT_COOL:
            self._client.set_setpoint_mode(self._id, hvac_mode, self._is_wifi, self._is_HC_like)

        elif hvac_mode == MODE_AUTO_BYPASS:
            if self._operation_mode == HVACMode.AUTO:
                self._client.set_setpoint_mode(self._id, hvac_mode, self._is_wifi, self._is_HC_like)

        else:
            _LOGGER.error("Unable to set hvac mode: %s", hvac_mode)

        self._operation_mode = hvac_mode
        self._delayed_refresh()

    @override
    def set_preset_mode(self, preset_mode: str) -> None:
        """Activate a preset."""
        if preset_mode == self.preset_mode:
            return
        if preset_mode == PRESET_AWAY:
            self._client.set_occupancy_mode(self._id, PRESET_AWAY, self._is_wifi)
        elif preset_mode == PRESET_HOME:
            self._client.set_occupancy_mode(self._id, PRESET_HOME, self._is_wifi)
        elif preset_mode == PRESET_NONE:
            self._client.set_occupancy_mode(self._id, PRESET_NONE, self._is_wifi)
            # Re-apply current hvac_mode without any preset
            self.set_hvac_mode(self.hvac_mode)
        else:
            _LOGGER.error("Unable to set preset mode: %s", preset_mode)
        self._occupancy = preset_mode

    def turn_em_heat_on(self):
        """Turn emergency heater on."""
        if self._is_low_voltage:
            value = "on"
            low = "voltage"
            sec = self._cycle_length_output2_value
            self._cycle_length_output2_status = "on"
        elif self._is_low_wifi:
            value = ""
            low = "wifi"
            sec = self._aux_cycle_length
        else:
            value = "slave"
            sec = 0
            low = "floor"
            self._em_heat = "slave"
        self._client.set_em_heat(self._id, value, low, sec)

    def turn_em_heat_off(self):
        """Turn emergency heater off."""
        if self._is_low_voltage:
            low = "voltage"
            self._cycle_length_output2_status = "off"
            sec = self._cycle_length_output2_value
        elif self._is_low_wifi:
            low = "wifi"
            self._aux_cycle_length = 0
            sec = 0
        else:
            low = "floor"
            self._em_heat = "off"
            sec = 0
        self._client.set_em_heat(self._id, "off", low, sec)

    def set_auxiliary_load(self, value):
        """Set thermostat auxiliary output status and load."""
        self._client.set_auxiliary_load(value["id"], value["status"], value["val"])
        self._load2_status = value["status"]
        self._load2 = value["val"]

    def set_sensor_type(self, value):
        """Set floor sensor type."""
        self._client.set_sensor_type(value["id"], value["type"])
        self._floor_sensor_type = value["type"]

    def set_heat_lockout_temperature(self, value):
        """Set maximum outside temperature limit to allow heating device operation."""
        self._client.set_heat_lockout(value["id"], value["temp"], self._is_gen2)
        self._heat_lockout_temp = value["temp"]

    def set_cool_lockout_temperature(self, value):
        """Set minimum outside temperature limit to allow cooling device operation."""
        self._client.set_cool_lockout(value["id"], value["temp"])
        self._cool_lockout_temp = value["temp"]

    def set_activation(self, value):
        """Activate or deactivate neviweb polling for a missing device."""
        self._active = value["active"]

    def set_hc_second_display(self, value):
        """Set second display value for TH1134ZB-HC."""
        self._client.set_hc_display(value["id"], value["display"])
        self._display2 = value["display"]

    def set_language(self, value):
        """Set display language value for TH1134ZB-HC."""
        self._client.set_language(value["id"], value["lang"])
        self._language = value["lang"]

    def get_weather(self):
        """Get weather temperature for my location."""
        weather = self._client.get_weather()

        # Check that weather is a valid dict
        if not isinstance(weather, dict):
            _LOGGER.warning("Neviweb returned invalid weather data: %s", weather)
            return

        # Check if neviweb return an error
        if "error" in weather:
            _LOGGER.warning("Neviweb weather error: %s", weather["error"])
            return

        # Check that needed attributes exist
        temperature = weather.get("temperature")
        icon = weather.get("icon")

        if temperature is None or icon is None:
            _LOGGER.warning("Neviweb weather data incomplete: %s (missing temperature or icon)", weather)
            return

        # Update weather data
        self._temperature = temperature
        self._weather_icon = icon

    def set_climate_neviweb_status(self, value):
        """Set Neviweb global occupancy mode, away or home"""
        self._client.post_neviweb_status(self._location, value["mode"])
        self._occupancy_mode = value["mode"]

    def _delayed_refresh(self, delay: float = 2.0) -> None:
        """Push immediate state and schedule a delayed refresh."""
        self.schedule_update_ha_state()

        # Set a delayed refresh to wait from Neviweb to finish his setting
        call_later(self.hass, delay, lambda _: self.update())

    def do_stat(self, start):
        """Get device energy statistic."""
        if self._energy_stat_time == 0:
            self._energy_stat_time = start
            return
        if start - self._energy_stat_time <= STAT_INTERVAL:
            return
        today = date.today()
        if not self._is_HC:
            self._fetch_monthly_stats()
            self._fetch_daily_stats(today.month)
            self._fetch_hourly_stats(today.day)
            self._record_stat()
        else:
            self._fetch_hc_hourly_stats()
        self._energy_stat_time = time.time()

    def _fetch_monthly_stats(self) -> None:
        """Fetch and assign monthly energy statistics."""
        device_monthly_stats = self._client.get_device_monthly_stats(self._id, False)
        _LOGGER.debug("%s device_monthly_stats = %s", self._name, device_monthly_stats)
        if device_monthly_stats is not None and len(device_monthly_stats) > 1:
            n = len(device_monthly_stats)
            monthly_kwh_count = 0
            k = 0
            while k < n:
                monthly_kwh_count += device_monthly_stats[k]["period"] / 1000
                k += 1
            self._monthly_kwh_count = round(monthly_kwh_count, 3)
            self._month_kwh = round(device_monthly_stats[n - 1]["period"] / 1000, 3)
            dt_month = datetime.fromisoformat(device_monthly_stats[n - 1]["date"][:-1] + "+00:00").astimezone(
                timezone.utc
            )
            _LOGGER.debug("stat month = %s", dt_month.month)
        else:
            self._month_kwh = 0
            _LOGGER.warning(
                translated_or_default(
                    self.hass,
                    "no_stat",
                    f"No statistic available for frequency monthly for {self.entity_id}",
                    param="monthly",
                    name=self._name,
                )
            )

    def _fetch_daily_stats(self, current_month: int) -> None:
        """Fetch and assign daily energy statistics."""
        device_daily_stats = self._client.get_device_daily_stats(self._id, False)
        _LOGGER.debug("%s device_daily_stats = %s", self._name, device_daily_stats)
        if device_daily_stats is not None and len(device_daily_stats) > 1:
            n = len(device_daily_stats)
            daily_kwh_count = 0
            k = 0
            while k < n:
                if (
                    datetime.fromisoformat(device_daily_stats[k]["date"][:-1] + "+00:00")
                    .astimezone(timezone.utc)
                    .month
                    == current_month
                ):
                    daily_kwh_count += device_daily_stats[k]["period"] / 1000
                k += 1
            self._daily_kwh_count = round(daily_kwh_count, 3)
            self._today_kwh = round(device_daily_stats[n - 1]["period"] / 1000, 3)
            dt_day = datetime.fromisoformat(device_daily_stats[n - 1]["date"][:-1].replace("Z", "+00:00"))
            _LOGGER.debug("stat day = %s", dt_day.day)
        else:
            self._today_kwh = 0
            _LOGGER.warning(
                translated_or_default(
                    self.hass,
                    "no_stat",
                    f"No statistic available for frequency daily for {self.entity_id}",
                    param="monthly",
                    name=self._name,
                )
            )

    def _fetch_hourly_stats(self, current_day: int) -> None:
        """Fetch and assign hourly energy statistics."""
        device_hourly_stats = self._client.get_device_hourly_stats(self._id, False)
        _LOGGER.debug(
            "%s device hourly stat (SKU: %s): %s, size = %s",
            self._name,
            self._sku,
            device_hourly_stats,
            len(device_hourly_stats),
        )
        if device_hourly_stats is not None and len(device_hourly_stats) > 1:
            n = len(device_hourly_stats)
            hourly_kwh_count = 0
            k = 0
            while k < n:
                if (
                    datetime.fromisoformat(device_hourly_stats[k]["date"][:-1].replace("Z", "+00:00")).day
                    == current_day
                ):
                    hourly_kwh_count += device_hourly_stats[k]["period"] / 1000
                k += 1
            self._hourly_kwh_count = round(hourly_kwh_count, 3)
            self._hour_kwh = round(device_hourly_stats[n - 1]["period"] / 1000, 3)
            self._marker = device_hourly_stats[n - 1]["date"]
            dt_hour = datetime.strptime(device_hourly_stats[n - 1]["date"], "%Y-%m-%dT%H:%M:%S.%fZ")
            _LOGGER.debug("stat hour = %s", dt_hour.hour)
        else:
            self._hour_kwh = 0
            _LOGGER.warning(
                translated_or_default(
                    self.hass,
                    "no_stat",
                    f"No statistic available for frequency hourly for {self.entity_id}",
                    param="monthly",
                    name=self._name,
                )
            )

    def _record_stat(self) -> None:
        """Update total kWh count and mark based on latest hourly marker."""
        if self._total_kwh_count == 0:
            self._total_kwh_count = round(
                self._monthly_kwh_count + self._daily_kwh_count + self._hourly_kwh_count,
                3,
            )
            # await async_add_data(self._id, self._total_kwh_count, self._marker)
            # self.async_write_ha_state()
            self._mark = self._marker
        else:
            if self._marker != self._mark:
                self._total_kwh_count += round(self._hour_kwh, 3)
                # save_data(self._id, self._total_kwh_count, self._marker)
                self._mark = self._marker

    def _fetch_hc_hourly_stats(self) -> None:
        """Fetch and assign HC (heat/cool) hourly energy statistics."""
        device_hourly_stats = self._client.get_device_hourly_stats(self._id, True)
        _LOGGER.debug(
            "%s device hourly stats (SKU: %s): %s, size = %s",
            self._name,
            self._sku,
            device_hourly_stats,
            len(device_hourly_stats),
        )
        # Get the hourly stats
        for mode, key in TH6_MODES_VALUES.items():
            data = device_hourly_stats.get(key, [])

            # Device Attributes
            total_attr = f"_{mode}_hourly_total_count"
            hourly_attr = f"_{mode}_hourly_count"
            ts_attr = f"_{mode}_hourly_last_timestamp"
            local_ts_attr = f"_{mode}_hourly_last_timestamp_local"

            if data and len(data) >= 2:
                last_entry = data[-1]
                prev_entry = data[-2]

                last_value = last_entry["value"]
                prev_value = prev_entry["value"]

                # Timestamp Sinopé (UTC to local)
                ts_utc = datetime.strptime(last_entry["timestamp"], "%Y-%m-%d %H:%M:%S").replace(
                    tzinfo=timezone.utc
                )
                ts_local = dt_util.as_local(ts_utc)

                # Check if timestamp changed
                if getattr(self, ts_attr, None) != last_entry["timestamp"]:
                    # New data → we update
                    setattr(self, total_attr, last_value)
                    setattr(self, hourly_attr, max(0, last_value - prev_value))
                    setattr(self, ts_attr, last_entry["timestamp"])
                    setattr(self, local_ts_attr, ts_local.isoformat())

                else:
                    # No timestamp change → do nothing
                    pass

            else:
                # Unsupported modes for this thermostat
                setattr(self, total_attr, 0)
                setattr(self, hourly_attr, 0)

    def get_sensor_error_code(self):
        """Get device sensor error code."""
        device_error_code = self._client.get_device_sensor_error(self._id)
        raw_code = device_error_code.get("raw", 0) if device_error_code else 0

        # Message list
        error_messages = {
            1048576: "External sensor disconnected (not implemented)",
        }

        if raw_code == 0:
            if self._active_errors:
                self.notify_ha(
                    translated_or_default(
                        self.hass,
                        "error_resolved",
                        f"All errors resolved for device {self._name}, ID: {self._id}, Sku: {self._sku}",
                        name=self._name,
                        id=self._id,
                        sku=self._sku,
                    )
                )
                _LOGGER.info("All errors resolved: %s", self._active_errors)
                self._active_errors.clear()
            return

        # If we receive a new error code
        if raw_code not in self._active_errors:
            # Default message if code is unknown
            error_message = error_messages.get(raw_code, "Unknown error")

            # Send notification
            self.notify_ha(
                translated_or_default(
                    self.hass,
                    "error_code",
                    f"Error code detected for {self._name}, {self._id} ({self._sku}), {error_message}",
                    message="(" + error_message + ")",
                    name=self._name,
                    id=self._id,
                    sku=self._sku,
                )
            )
            _LOGGER.warning(
                translated_or_default(
                    self.hass,
                    "error_code",
                    f"Error code detected for {self._name}, {self._id} ({self._sku}), {error_message}",
                    message="(" + error_message + ")",
                    name=self._name,
                    id=self._id,
                    sku=self._sku,
                )
            )
            self._active_errors.add(raw_code)

        # Save last error code
        self._error_code = raw_code

    def log_error(self, error_data: str) -> None:
        """Send error message to LOG via ERROR_HANDLERS lookup table."""
        handler = ERROR_HANDLERS.get(error_data)
        if handler:
            handler(self)
        else:
            _LOGGER.warning(
                translated_or_default(
                    self.hass,
                    "unknown_error",
                    (
                        f"Unknown error for {self._name}, {self._id} ({self._sku}), "
                        f"model {self._device_model} encountered an error: {error_data}"
                    ),
                    name=self._name,
                    id=self._id,
                    sku=self._sku,
                    model=str(self._device_model),
                    data=error_data,
                )
            )

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


