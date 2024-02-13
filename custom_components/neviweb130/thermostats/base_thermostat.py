from __future__ import annotations

import logging

import time

from ..schema import HOMEKIT_MODE
from ..schema import STAT_INTERVAL
from .. import VERSION

from homeassistant.components.climate.const import (
    PRESET_AWAY,
    PRESET_HOME,
    PRESET_NONE,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfTemperature,
)

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.persistent_notification import DOMAIN as PN_DOMAIN

from ..const import (
    ATTR_BACKLIGHT,
    ATTR_CYCLE,
    ATTR_DISPLAY2,
    ATTR_DRSTATUS,
    ATTR_DRSETPOINT,
    ATTR_ERROR_CODE_SET1,
    ATTR_KEYPAD,
    ATTR_OUTPUT_PERCENT_DISPLAY,
    ATTR_ROOM_SETPOINT,
    ATTR_ROOM_SETPOINT_MAX,
    ATTR_ROOM_SETPOINT_MIN,
    ATTR_ROOM_TEMP_DISPLAY,
    ATTR_ROOM_TEMPERATURE,
    ATTR_RSSI,
    ATTR_SYSTEM_MODE,
    ATTR_TEMP,
    ATTR_TIME,
    ATTR_WATTAGE,
    MODE_AUTO_BYPASS,
    MODE_MANUAL
)

from ..ha_utilities import temp_format_to_ha, lock_to_ha, HA_TO_NEVIWEB_PERIOD

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)

_LOGGER = logging.getLogger(__name__)

DEVICE_MODEL_LOW = [7372]
DEVICE_MODEL_LOW_WIFI = [739]
DEVICE_MODEL_FLOOR = [737]
DEVICE_MODEL_WIFI_FLOOR = [738]
DEVICE_MODEL_WIFI = [1510, 742]
DEVICE_MODEL_HEAT = [1123, 1124]
DEVICE_MODEL_DOUBLE = [7373]
DEVICE_MODEL_HEAT_G2 = [300]
DEVICE_MODEL_HC = [1134]

UPDATE_ATTRIBUTES = [
    ATTR_DRSETPOINT,
    ATTR_DRSTATUS,
    ATTR_OUTPUT_PERCENT_DISPLAY,
    ATTR_ROOM_SETPOINT,
    ATTR_ROOM_SETPOINT_MAX,
    ATTR_ROOM_SETPOINT_MIN,
    ATTR_ROOM_TEMP_DISPLAY,
    ATTR_ROOM_TEMPERATURE,
    ATTR_TEMP,
    ATTR_TIME,
]

SNOOZE_TIME = 1200

SUPPORT_FLAGS = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
)

SUPPORT_AUX_FLAGS = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.AUX_HEAT
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
)

SUPPORTED_HVAC_WIFI_MODES = [
    HVACMode.AUTO,
    HVACMode.HEAT,
    HVACMode.OFF,
]

SUPPORTED_HVAC_MODES = [
    HVACMode.HEAT,
    HVACMode.OFF,
]

SUPPORTED_HVAC_HC_MODES = [
    HVACMode.COOL,
    HVACMode.HEAT,
    HVACMode.OFF,
]

PRESET_WIFI_MODES = [
    PRESET_AWAY,
    PRESET_HOME,
    PRESET_NONE,
]

PRESET_MODES = [
    PRESET_AWAY,
    PRESET_NONE,
]


class Neviweb130Thermostat(ClimateEntity):
    """Implementation of Neviweb TH1123ZB, TH1124ZB thermostat."""

    _enable_turn_on_off_backwards_compatibility = False
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, data, device_info, name, sku, firmware):
        """Initialize."""
        self._name = name
        self._sku = sku
        self._firmware = firmware
        self._client = data.neviweb130_client
        self._id = device_info["id"]
        self._device_model = device_info["signature"]["model"]
        self._device_model_cfg = device_info["signature"]["modelCfg"]
        self._hour_energy_kwh_count = None
        self._today_energy_kwh_count = None
        self._month_energy_kwh_count = None
        self._hour_kwh = None
        self._today_kwh = None
        self._month_kwh = None
        self._drstatus_active = "off"
        self._drstatus_optout = "off"
        self._drstatus_setpoint = "off"
        self._drstatus_abs = "off"
        self._drstatus_rel = "off"
        self._drsetpoint_status = "off"
        self._drsetpoint_value = 0
        self._cur_temp = None
        self._cur_temp_before = None
        self._target_temp = None
        self._operation_mode = None
        self._occupancy = None
        self._wattage = 0
        self._min_temp = 0
        self._max_temp = 0
        self._temperature_format = UnitOfTemperature.CELSIUS
        self._time_format = "24h"
        self._temp_display_value = None
        self._display2 = None
        self._heat_level = 0
        self._keypad = None
        self._backlight = None
        self._cycle_length = 0
        self._rssi = None
        self._code_reference_sensor = None
        self._code_compensation_sensor = None
        self._code_air_sensor = None
        self._code_wire_sensor = None
        self._code_current_overload = None
        self._code_thermal_overload = None
        self._code_load_error = None
        self._code_end_of_life = None
        self._is_double = device_info["signature"]["model"] in \
            DEVICE_MODEL_DOUBLE
        self._is_hc = device_info["signature"]["model"] in \
            DEVICE_MODEL_HC
        self._is_gen2 = device_info["signature"]["model"] in \
            DEVICE_MODEL_HEAT_G2
        self._is_floor = device_info["signature"]["model"] in \
            DEVICE_MODEL_FLOOR
        self._is_wifi_floor = device_info["signature"]["model"] in \
            DEVICE_MODEL_WIFI_FLOOR
        self._is_wifi = device_info["signature"]["model"] in \
            DEVICE_MODEL_WIFI_FLOOR or device_info["signature"]["model"] in DEVICE_MODEL_WIFI or \
            device_info["signature"]["model"] in DEVICE_MODEL_LOW_WIFI
        self._is_low_voltage = device_info["signature"]["model"] in \
            DEVICE_MODEL_LOW
        self._is_low_wifi = device_info["signature"]["model"] in \
            DEVICE_MODEL_LOW_WIFI
        self._energy_stat_time = time.time() - 1500
        self._snooze = 0
        self._activ = True
        self._aux_cycle_length = None
        self._aux_heat = None
        self._cycle_length_output2_status = None
        self._pump_protec_status = None
        _LOGGER.debug("Setting up %s: %s", self._name, device_info)

    def update(self):
        if self._activ:
            HEAT_ATTRIBUTES = [ATTR_WATTAGE, ATTR_KEYPAD, ATTR_BACKLIGHT, ATTR_SYSTEM_MODE, ATTR_CYCLE, ATTR_DISPLAY2,
                               ATTR_RSSI]
            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            _LOGGER.debug("Updated attributes for %s: %s", self._name, UPDATE_ATTRIBUTES + HEAT_ATTRIBUTES)
            device_data = self._client.get_device_attributes(self._id, UPDATE_ATTRIBUTES + HEAT_ATTRIBUTES)
            end = time.time()
            elapsed = round(end - start, 3)
            _LOGGER.debug("Updating %s (%s sec): %s",
                          self._name, elapsed, device_data)

            if "error" not in device_data:
                if "errorCode" not in device_data:
                    self._cur_temp_before = self._cur_temp
                    self._cur_temp = float(device_data[ATTR_ROOM_TEMPERATURE]["value"]) if \
                        device_data[ATTR_ROOM_TEMPERATURE]["value"] != None else self._cur_temp_before
                    self._target_temp = float(device_data[ATTR_ROOM_SETPOINT])
                    self._min_temp = device_data[ATTR_ROOM_SETPOINT_MIN]
                    self._max_temp = device_data[ATTR_ROOM_SETPOINT_MAX]
                    self._temperature_format = device_data[ATTR_TEMP]
                    self._time_format = device_data[ATTR_TIME]
                    self._temp_display_value = device_data[ATTR_ROOM_TEMP_DISPLAY]
                    self._display2 = device_data[ATTR_DISPLAY2]
                    if ATTR_DRSETPOINT in device_data:
                        self._drsetpoint_status = device_data[ATTR_DRSETPOINT]["status"]
                        self._drsetpoint_value = device_data[ATTR_DRSETPOINT]["value"] if \
                            device_data[ATTR_DRSETPOINT]["value"] != None else 0
                    if ATTR_DRSTATUS in device_data:
                        self._drstatus_active = device_data[ATTR_DRSTATUS]["drActive"]
                        self._drstatus_optout = device_data[ATTR_DRSTATUS]["optOut"]
                        self._drstatus_setpoint = device_data[ATTR_DRSTATUS]["setpoint"]
                        self._drstatus_abs = device_data[ATTR_DRSTATUS]["powerAbsolute"]
                        self._drstatus_rel = device_data[ATTR_DRSTATUS]["powerRelative"]

                    self._heat_level = device_data[ATTR_OUTPUT_PERCENT_DISPLAY]
                    self._keypad = device_data[ATTR_KEYPAD]
                    self._backlight = device_data[ATTR_BACKLIGHT]
                    if ATTR_CYCLE in device_data:
                        self._cycle_length = device_data[ATTR_CYCLE]
                    if ATTR_RSSI in device_data:
                        self._rssi = device_data[ATTR_RSSI]
                    self._operation_mode = device_data[ATTR_SYSTEM_MODE]
                    if not self._is_low_voltage:
                        self._wattage = device_data[ATTR_WATTAGE]
                elif device_data["errorCode"] == "ReadTimeout":
                    _LOGGER.warning(
                        "A timeout occur during data update. Device %s do not respond. Check your network... (%s)",
                        self._name, device_data)
                else:
                    _LOGGER.warning("Error in updating device %s: (%s)", self._name, device_data)
            else:
                self.log_error(device_data["error"]["code"])
            if self._sku != "FLP55":
                self.do_stat(start)
            self.get_sensor_error_code(start)
        else:
            if time.time() - self._snooze > SNOOZE_TIME:
                self._activ = True
                self.notify_ha(
                    f"Warning: Neviweb Device update restarted for " + self._name + ", Sku: " + self._sku
                )

    @property
    def unique_id(self):
        """Return unique ID based on Neviweb130 device ID."""
        return self._id

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return temp_format_to_ha(self._temperature_format)

    @property
    def device_class(self):
        """Return the device class of this entity."""
        return SensorDeviceClass.TEMPERATURE

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        data = {}
        data.update({'wattage': self._wattage,
                     'cycle_length': self._cycle_length,
                     'status compensation sensor': self._code_compensation_sensor,
                     'status reference sensor': self._code_reference_sensor,
                     'status wire sensor': self._code_wire_sensor,
                     'status air sensor': self._code_air_sensor,
                     'status current sensor': self._code_current_overload,
                     'status thermal sensor': self._code_thermal_overload,
                     'status end of life sensor': self._code_end_of_life,
                     'status load sensor': self._code_load_error,
                     'heat_level': self._heat_level,
                     'pi_heating_demand': self._heat_level,
                     'temp_display_value': self._temp_display_value,
                     'second_display': self._display2,
                     'keypad': lock_to_ha(self._keypad),
                     'backlight': self._backlight,
                     'time_format': self._time_format,
                     'temperature_format': self._temperature_format,
                     'setpoint_max': self._max_temp,
                     'setpoint_min': self._min_temp,
                     'eco_status': self._drstatus_active,
                     'eco_optOut': self._drstatus_optout,
                     'eco_setpoint': self._drstatus_setpoint,
                     'eco_power_relative': self._drstatus_rel,
                     'eco_power_absolute': self._drstatus_abs,
                     'eco_setpoint_status': self._drsetpoint_status,
                     'eco_setpoint_delta': self._drsetpoint_value,
                     'hourly_kwh_count': self._hour_energy_kwh_count,
                     'daily_kwh_count': self._today_energy_kwh_count,
                     'monthly_kwh_count': self._month_energy_kwh_count,
                     'hourly_kwh': self._hour_kwh,
                     'daily_kwh': self._today_kwh,
                     'monthly_kwh': self._month_kwh,
                     'rssi': self._rssi,
                     'sku': self._sku,
                     'device_model': str(self._device_model),
                     'device_model_cfg': self._device_model_cfg,
                     'firmware': self._firmware,
                     'Activation': self._activ,
                     'id': str(self._id)})
        return data

    @property
    def pi_heating_demand(self) -> int:
        """Heating demand."""
        return self.heat_level

    @property
    def supported_features(self):
        """Return the list of supported features."""
        if self._is_floor or self._is_wifi_floor or self._is_low_wifi:
            return SUPPORT_AUX_FLAGS
        else:
            return SUPPORT_FLAGS

    @property
    def is_aux_heat(self):
        """return auxiliary heat state."""
        if self._aux_heat == "slave":
            return True
        elif self._cycle_length_output2_status == "on":
            return True
        elif self._aux_cycle_length > 0:
            return True
        else:
            return False

    @property
    def min_temp(self):
        """Return the min temperature."""
        return self._min_temp

    @property
    def max_temp(self):
        """Return the max temperature."""
        return self._max_temp

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def hvac_mode(self):
        """Return current operation"""
        if self._operation_mode == HVACMode.OFF:
            return HVACMode.OFF
        elif self._operation_mode in [HVACMode.AUTO, MODE_AUTO_BYPASS]:
            return HVACMode.AUTO
        else:
            return HVACMode.HEAT

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        if self._is_wifi:
            return SUPPORTED_HVAC_WIFI_MODES
        elif self._is_hc:
            return SUPPORTED_HVAC_HC_MODES
        else:
            return SUPPORTED_HVAC_MODES

    @property
    def current_temperature(self):
        """Return the room current temperature."""
        return self._cur_temp

    @property
    def target_temperature(self):
        """Return the temperature we try to reach less Eco Sinope dr_setpoint delta."""
        temp = self._target_temp + self._drsetpoint_value
        if temp < self._min_temp:
            return self._min_temp
        return temp

    @property
    def preset_modes(self):
        """Return available preset modes."""
        if self._is_wifi:
            return PRESET_WIFI_MODES
        else:
            return PRESET_MODES

    @property
    def preset_mode(self):
        """Return current preset mode."""
        if self._occupancy == PRESET_HOME:
            return PRESET_NONE
        elif self._occupancy == PRESET_AWAY:
            return PRESET_AWAY
        else:
            return PRESET_NONE

    @property
    def hvac_action(self):
        """Return current HVAC action."""
        if HOMEKIT_MODE:
            if self._operation_mode == HVACMode.OFF:
                return HVACAction.OFF
            elif self._heat_level == 0:
                return HVACAction.IDLE
            else:
                return HVACAction.HEATING
        else:
            if self._operation_mode == HVACMode.OFF:
                return HVACAction.OFF
            elif self._operation_mode == MODE_AUTO_BYPASS:
                return MODE_AUTO_BYPASS
            elif self._heat_level == 0:
                return HVACAction.IDLE
            else:
                return HVACAction.HEATING

    @property
    def is_on(self):
        """ Return True if mode = HVACMode.HEAT"""
        if self._operation_mode == HVACMode.HEAT or self._operation_mode == HVACMode.AUTO:
            return True
        return False

    def turn_on(self):
        """Turn the thermostat to HVACMode.heat on."""
        self._client.set_setpoint_mode(self._id, HVACMode.HEAT, self._is_wifi)
        self._operation_mode = HVACMode.HEAT

    def turn_off(self):
        """Turn the thermostat to HVACMode.off."""
        self._client.set_setpoint_mode(self._id, HVACMode.OFF, self._is_wifi)
        self._operation_mode = HVACMode.OFF

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._client.set_temperature(self._id, temperature)
        self._target_temp = temperature

    def set_second_display(self, value):
        """Set thermostat second display between outside and setpoint temperature"""
        display = value["display"]
        entity = value["id"]
        if display == "outsideTemperature":
            display_name = "Outside"
        else:
            display_name = "Setpoint"
        self._client.set_second_display(
            entity, display)
        self._display2 = display_name

    def set_backlight(self, value):
        """Set thermostat backlight «auto» = off when idle / on when active or «on» = always on"""
        """fonction differently for zigbee and wifi devices"""
        level = value["level"]
        device = value["type"]
        entity = value["id"]
        if level == "on":
            if device == "wifi":
                level_command = "alwaysOn"
            else:
                level_command = "always"
            level_name = "On"
        elif level == "bedroom":
            level_command = "bedroom"
            level_name = "bedroom"
        else:
            if device == "wifi":
                level_command = "onUserAction"
            else:
                level_command = "onActive"
            level_name = "Auto"
        self._client.set_backlight(
            entity, level_command, device)
        self._backlight = level_name

    def set_keypad_lock(self, value):
        """Lock or unlock device's keypad, locked = Locked, unlocked = Unlocked"""
        lock = value["lock"]
        entity = value["id"]
        if lock == "locked" and self._is_wifi:
            lock = "lock"
        elif lock == "partiallyLocked" and self._is_wifi:
            lock = "partialLock"
        else:
            if self._is_wifi:
                lock = "unlock"
        self._client.set_keypad_lock(
            entity, lock, self._is_wifi)
        self._keypad = lock

    def set_time_format(self, value):
        """set time format 12h or 24h"""
        time = value["time"]
        entity = value["id"]
        if time == 12:
            time_commande = "12h"
        else:
            time_commande = "24h"
        self._client.set_time_format(
            entity, time_commande)
        self._time_format = time_commande

    def set_temperature_format(self, value):
        """set temperature format, celsius or fahrenheit"""
        temp = value["temp"]
        entity = value["id"]
        self._client.set_temperature_format(
            entity, temp)
        self._temperature_format = temp

    def set_air_floor_mode(self, value):
        """switch temperature control between floor and ambiant sensor"""
        mode = value["mode"]
        entity = value["id"]
        self._client.set_air_floor_mode(
            entity, mode)
        self._floor_mode = mode

    def set_setpoint_max(self, value):
        """set maximum setpoint temperature"""
        temp = value["temp"]
        entity = value["id"]
        self._client.set_setpoint_max(
            entity, temp)
        self._max_temp = temp

    def set_setpoint_min(self, value):
        """ set minimum setpoint temperature. """
        temp = value["temp"]
        entity = value["id"]
        self._client.set_setpoint_min(
            entity, temp)
        self._min_temp = temp

    def set_cool_setpoint_max(self, value):
        """set maximum cooling setpoint temperature"""
        temp = value["temp"]
        entity = value["id"]
        self._client.set_cool_setpoint_max(
            entity, temp)
        self._cool_max = temp

    def set_cool_setpoint_min(self, value):
        """ set minimum cooling setpoint temperature. """
        temp = value["temp"]
        entity = value["id"]
        self._client.set_cool_setpoint_min(
            entity, temp)
        self._cool_min = temp

    def set_floor_air_limit(self, value):
        """ set maximum temperature air limit for floor thermostat. """
        temp = value["temp"]
        entity = value["id"]
        if temp == 0:
            status = "off"
        else:
            status = "on"
        self._client.set_floor_air_limit(
            entity, status, temp)
        self._floor_air_limit = temp

    def set_early_start(self, value):
        """ set early heating on/off for wifi thermostat. """
        start = value["start"]
        entity = value["id"]
        self._client.set_early_start(
            entity, start)
        self._early_start = start

    def set_hvac_dr_options(self, value):
        """ set thermostat DR options for Eco Sinope. """
        entity = value["id"]
        dr = value["dractive"]
        optout = value["optout"]
        setpoint = value["setpoint"]
        self._client.set_hvac_dr_options(
            entity, dr, optout, setpoint)
        self._drstatus_active = dr
        self._drstatus_optout = optout
        self._drstatus_setpoint = setpoint

    def set_hvac_dr_setpoint(self, value):
        """ set thermostat DR setpoint values for Eco Sinope. """
        entity = value["id"]
        status = value["status"]
        val = value["val"]
        self._client.set_hvac_dr_setpoint(
            entity, status, val)
        self._drsetpoint_status = status
        self._drsetpoint_value = val

    def set_hvac_mode(self, hvac_mode):
        """Set new hvac mode."""
        if hvac_mode == HVACMode.OFF:
            self._client.set_setpoint_mode(self._id, HVACMode.OFF, self._is_wifi)
        elif hvac_mode in [HVACMode.HEAT, MODE_MANUAL]:
            self._client.set_setpoint_mode(self._id, hvac_mode, self._is_wifi)
        elif hvac_mode == HVACMode.AUTO:
            self._client.set_setpoint_mode(self._id, HVACMode.AUTO, self._is_wifi)
        elif hvac_mode == MODE_AUTO_BYPASS:
            if self._operation_mode == HVACMode.AUTO:
                self._client.set_setpoint_mode(self._id, MODE_AUTO_BYPASS, self._is_wifi)
        else:
            _LOGGER.error("Unable to set hvac mode: %s.", hvac_mode)
        self._operation_mode = hvac_mode

    def set_preset_mode(self, preset_mode):
        """Activate a preset."""
        if preset_mode == self.preset_mode:
            return
        if preset_mode == PRESET_AWAY:
            self._client.set_occupancy_mode(self._id, PRESET_AWAY, self._is_wifi)
        elif preset_mode == PRESET_HOME:
            self._client.set_occupancy_mode(self._id, PRESET_HOME, self._is_wifi)
        elif preset_mode == PRESET_NONE:
            # Re-apply current hvac_mode without any preset
            self.set_hvac_mode(self.hvac_mode)
        else:
            _LOGGER.error("Unable to set preset mode: %s.", preset_mode)
        self._occupancy = preset_mode

    def turn_aux_heat_on(self):
        """Turn auxiliary heater on/off."""
        if self._is_low_voltage:
            value = "on"
            low = "voltage"
            sec = self._cycle_length_output2_value
            self._cycle_length_output2_status = "on"
        elif self._is_low_wifi:
            value = self._aux_cycle_length
            low = "wifi"
            sec = self._aux_cycle_length
        else:
            value = "slave"
            sec = 0
            low = "floor"
            self._aux_heat = "slave"
        self._client.set_aux_heat(
            self._id, value, low, sec)

    def turn_aux_heat_off(self):
        """Turn auxiliary heater on/off."""
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
            self._aux_heat = "off"
            sec = 0
        self._client.set_aux_heat(
            self._id, "off", low, sec)

    def set_auxiliary_load(self, value):
        """ set thermostat auxiliary output status and load. """
        entity = value["id"]
        status = value["status"]
        val = value["val"]
        self._client.set_auxiliary_load(
            entity, status, val)
        self._load2_status = status
        self._load2 = val

    def set_aux_cycle_output(self, value):
        """ set low voltage thermostats auxiliary cycle status and length. """
        entity = value["id"]
        status = value["status"]
        val = value["val"]
        length = [v for k, v in HA_TO_NEVIWEB_PERIOD.items() if k == val][0]
        self._client.set_aux_cycle_output(
            entity, status, length)
        self._cycle_length_output2_status = status
        self._cycle_length_output2_value = length

    def set_cycle_output(self, value):
        """ set low voltage thermostats main cycle output length. """
        entity = value["id"]
        val = value["val"]
        length = [v for k, v in HA_TO_NEVIWEB_PERIOD.items() if k == val][0]
        self._client.set_aux_cycle_output(
            entity, length)
        self._cycle_length = length

    def set_pump_protection(self, value):
        entity = value["id"]
        status = value["status"]
        self._client.set_pump_protection(
            entity, status, self._is_low_wifi)
        self._pump_protec_status = status
        self._pump_protec_duration = 60
        self._pump_protec_period = 1

    def set_sensor_type(self, value):
        entity = value["id"]
        tipe = value["type"]
        self._client.set_sensor_type(
            entity, tipe)
        self._floor_sensor_type = tipe

    def set_floor_limit(self, value):
        """set maximum/minimum floor setpoint temperature"""
        temp = value["level"]
        entity = value["id"]
        limit = value["limit"]
        wifi = self._is_wifi_floor
        if limit == "low":
            if temp > 0 and temp < 5:
                temp = 5
        else:
            if temp > 0 and temp < 7:
                temp = 7
        self._client.set_floor_limit(
            entity, temp, limit, wifi)
        if limit == "low":
            self._floor_min = temp if temp != 0 else None
            self._floor_min_status = "on"
        else:
            self._floor_max = temp if temp != 0 else None
            self._floor_max_status = "on"

    def set_activation(self, value):
        """ Activate or deactivate neviweb polling for a missing device """
        action = value["active"]
        self._activ = action

    def do_stat(self, start):
        """ Get device energy statistic """
        if start - self._energy_stat_time > STAT_INTERVAL and self._energy_stat_time != 0:
            device_hourly_stats = self._client.get_device_hourly_stats(self._id)
            #            _LOGGER.debug("Energy data for %s (SKU: %s): %s, size = %s", self._name, self._sku, device_hourly_stats, len(device_hourly_stats))
            if device_hourly_stats is not None and len(device_hourly_stats) > 1:
                self._hour_energy_kwh_count = device_hourly_stats[1]["counter"] / 1000
                self._hour_kwh = device_hourly_stats[1]["period"] / 1000
            else:
                _LOGGER.warning("Got None for device_hourly_stats")
            device_daily_stats = self._client.get_device_daily_stats(self._id)
            #            _LOGGER.warning("%s device_daily_stats = %s", self._name, device_daily_stats)
            if device_daily_stats is not None and len(device_daily_stats) > 1:
                self._today_energy_kwh_count = device_daily_stats[0]["counter"] / 1000
                self._today_kwh = device_daily_stats[0]["period"] / 1000
            else:
                _LOGGER.warning("Got None for device_daily_stats")
            device_monthly_stats = self._client.get_device_monthly_stats(self._id)
            #            _LOGGER.warning("%s device_monthly_stats = %s", self._name, device_monthly_stats)
            if device_monthly_stats is not None and len(device_monthly_stats) > 1:
                self._month_energy_kwh_count = device_monthly_stats[0]["counter"] / 1000
                self._month_kwh = device_monthly_stats[0]["period"] / 1000
            else:
                _LOGGER.warning("Got None for device_monthly_stats")
            self._energy_stat_time = time.time()
        if self._energy_stat_time == 0:
            self._energy_stat_time = start

    def get_sensor_error_code(self, start):
        """ Get device sensor error code """
        if not self._is_wifi and not self._is_hc:
            device_error_code = self._client.get_device_sensor_error(self._id)
            if device_error_code is not None and device_error_code != {}:
                _LOGGER.warning("Error code set1 updated: %s", device_error_code)
                if not self._is_hc:
                    self._code_compensation_sensor = device_error_code["compensationSensor"]
                    self._code_thermal_overload = device_error_code["thermalOverload"]
                else:
                    self._temp_status = device_error_code[ATTR_ERROR_CODE_SET1]["temperatureSensor"]
                    self._stm_mcu = device_error_code[ATTR_ERROR_CODE_SET1]["stm_mcu"]
                    self._thermal_overload = device_error_code[ATTR_ERROR_CODE_SET1]["thermalOverload"]
                    self._current_overload = device_error_code[ATTR_ERROR_CODE_SET1]["currentOverload"]
                    self._j2connector = device_error_code[ATTR_ERROR_CODE_SET1]["j2Connector"]
                    self._j3connector = device_error_code[ATTR_ERROR_CODE_SET1]["j3Connector"]
                    self._line_error = device_error_code[ATTR_ERROR_CODE_SET1]["lineError"]
                if self._is_floor and not self._is_wifi_floor:
                    self._code_floor_sensor = device_error_code["floorSensor"]
                    self._code_gfcibase = device_error_code["gfciBase"]
                if self._is_low_voltage or self._is_double:
                    self._code_air_sensor = device_error_code["airSensor"]
                    self._code_floor_sensor = device_error_code["floorSensor"]
                elif self._is_double:
                    self._base = device_error_code["base"]
                else:
                    self._code_wire_sensor = device_error_code["wireSensor"]
                    self._code_current_overload = device_error_code["currentOverload"]
                    self._code_end_of_life = device_error_code["endOfLife"]
                if self._is_gen2:
                    self._air_top = device_error_code["airTopSensor"]
                    self._air_bottom = device_error_code["airBottomSensor"]
                    self._line_error = device_error_code["lineError"]
                    self._inductive_mode = device_error_code["inductiveMode"]
                else:
                    self._code_air_sensor = device_error_code["airSensor"]
                    self._code_load_error = device_error_code["loadError"]
                    self._code_reference_sensor = device_error_code["referenceSensor"]
                self._energy_stat_time = time.time()
            if self._energy_stat_time == 0:
                self._energy_stat_time = start

    def log_error(self, error_data):
        """ Send error message to LOG """
        if error_data == "USRSESSEXP":
            _LOGGER.warning("Session expired... reconnecting...")
            self._client.reconnect()
        elif error_data == "ACCSESSEXC":
            _LOGGER.warning("Maximun session number reached...Close other connections and try again.")
            self.notify_ha(
                f"Warning: Maximun Neviweb session number reached...Close other connections and try again."
            )
            self._client.reconnect()
        elif error_data == "DVCATTRNSPTD":
            _LOGGER.warning("Device attribute not supported for %s (SKU: %s)", self._name, self._sku)
        elif error_data == "DVCACTNSPTD":
            _LOGGER.warning("Device action not supported for %s...(SKU: %s) Report to maintainer.", self._name,
                            self._sku)
        elif error_data == "DVCCOMMTO":
            _LOGGER.warning(
                "Device Communication Timeout... The device %s did not respond to the server within the prescribed "
                "delay. (SKU: %s)",
                self._name, self._sku)
        elif error_data == "SVCERR":
            _LOGGER.warning("Service error, device not available retry later %s...(SKU: %s)", self._name,
                            self._sku)
        elif error_data == "DVCBUSY":
            _LOGGER.warning("Device busy can't reach (neviweb update ?), retry later %s: (SKU: %s)", self._name,
                            self._sku)
        elif error_data == "DVCUNVLB":
            _LOGGER.warning("Device %s is disconected from Neviweb (SKU: %s)", self._name, self._sku)
            _LOGGER.warning("This device %s is de-activated and won't be updated for 20 minutes.", self._name)
            _LOGGER.warning(
                "You can re-activate device %s with service.neviweb130_set_activation or wait 20 minutes for update "
                "to restart or just restart HA.",
                self._name)
            self._activ = False
            self._snooze = time.time()
            self.notify_ha(
                f"Warning: Received message from Neviweb, device disconnected... Check you log... Neviweb update will "
                f"be halted for 20 minutes for " + self._name + ", Sku: " + self._sku
            )
        elif error_data == "DVCERR":
            _LOGGER.warning("Device error for %s, service already active...(SKU: %s)", self._name,
                            self._sku)
        elif error_data == "SVCUNAUTH":
            _LOGGER.warning("Service not authorised for device %s...(SKU: %s)", self._name, self._sku)
        else:
            _LOGGER.warning("Unknown error for %s...(SKU: %s) Report to maintainer.", self._name,
                            self._sku)

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
