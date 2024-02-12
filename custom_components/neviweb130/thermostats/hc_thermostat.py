

class Neviweb130HcThermostat(Neviweb130Thermostat):
    """Implementation of Neviweb TH1134ZB-HC thermostat."""

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
        self._backlight = None
        self._keypad = None
        self._display2 = None
        self._temp_display_status = None
        self._temp_display_value = None
        self._heat_level = 0
        self._rssi = None
        self._target_cool = None
        self._cool_min = None
        self._cool_max = None
        self._cycle_length = 0
        self._cycle_length_output2_status = "off"
        self._aux_cycle_length = 0
        self._HC_device = None
        self._language = None
        self._model = None
        self._fan_speed = 0
        self._fan_swing_vert = None
        self._fan_swing_horiz = None
        self._fan_cap = None
        self._fan_swing_cap = None
        self._fan_swing_cap_vert = None
        self._fan_swing_cap_horiz = None
        self._balance_pt = None
        self._heat_lock_temp = None
        self._cool_lock_temp = None
        self._avail_mode = None
        self._temp_status = None
        self._stm_mcu = None
        self._thermal_overload = None
        self._current_overload = None
        self._j2connector = None
        self._j3connector = None
        self._line_error = None
        self._is_hc = device_info["signature"]["model"] in \
                      DEVICE_MODEL_HC
        self._is_double = False
        self._is_low_voltage = False
        self._is_gen2 = False
        self._is_wifi = False
        self._is_wifi_floor = False
        self._is_floor = False
        self._is_low_wifi = False
        self._energy_stat_time = time.time() - 1500
        self._snooze = 0
        self._activ = True
        _LOGGER.debug("Setting up %s: %s", self._name, device_info)

    def update(self):
        if self._activ:
            HC_ATTRIBUTES = [ATTR_DISPLAY2, ATTR_RSSI, ATTR_COOL_SETPOINT, ATTR_COOL_SETPOINT_MIN,
                             ATTR_COOL_SETPOINT_MAX, ATTR_SYSTEM_MODE, ATTR_CYCLE, ATTR_WATTAGE, ATTR_BACKLIGHT,
                             ATTR_KEYPAD, ATTR_HC_DEV, ATTR_ERROR_CODE_SET1, ATTR_LANGUAGE, ATTR_MODEL,
                             ATTR_FAN_SPEED, ATTR_FAN_SWING_VERT, ATTR_FAN_SWING_HORIZ, ATTR_FAN_CAP,
                             ATTR_FAN_SWING_CAP, ATTR_FAN_SWING_CAP_HORIZ, ATTR_FAN_SWING_CAP_VERT, ATTR_BALANCE_PT,
                             ATTR_HEAT_LOCK_TEMP, ATTR_COOL_LOCK_TEMP, ATTR_AVAIL_MODE]
            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            _LOGGER.debug("Updated attributes for %s: %s", self._name, UPDATE_ATTRIBUTES + HC_ATTRIBUTES)
            device_data = self._client.get_device_attributes(self._id, UPDATE_ATTRIBUTES + HC_ATTRIBUTES)
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
                    if ATTR_RSSI in device_data:
                        self._rssi = device_data[ATTR_RSSI]
                    self._wattage = device_data[ATTR_WATTAGE]
                    self._cycle_length = device_data[ATTR_CYCLE]
                    self._target_cool = device_data[ATTR_COOL_SETPOINT]
                    self._cool_min = device_data[ATTR_COOL_SETPOINT_MIN]
                    self._cool_max = device_data[ATTR_COOL_SETPOINT_MAX]
                    self._HC_device = device_data[ATTR_HC_DEV]
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
                    self._heat_lock_temp = device_data[ATTR_HEAT_LOCK_TEMP]
                    self._cool_lock_temp = device_data[ATTR_COOL_LOCK_TEMP]
                    self._avail_mode = device_data[ATTR_AVAIL_MODE]
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
    def extra_state_attributes(self):
        """Return the state attributes."""
        data = {}
        data.update({'wattage': self._wattage,
                     'status temp': self._temp_status,
                     'status stm mcu': self._stm_mcu,
                     'status current sensor': self._current_overload,
                     'status thermal sensor': self._thermal_overload,
                     'status line error': self._line_error,
                     'status j2 connector': self._j2connector,
                     'status j3 connector': self._j3connector,
                     'cool setpoint min': self._cool_min,
                     'cool setpoint max': self._cool_max,
                     'cool setpoint': self._target_cool,
                     'cycle_length': self._cycle_length,
                     'hc_device': self._HC_device,
                     'language': self._language,
                     'model': self._model,
                     'fan_speed': self._fan_speed,
                     'fan_swing_vertical': self._fan_swing_vert,
                     'fan_swing_horizontal': self._fan_swing_horiz,
                     'fan_capability': self._fan_cap,
                     'fan_swing_capability': self._fan_swing_cap,
                     'fan_swing_capability_vertical': self._fan_swing_cap_vert,
                     'fan_swing_capability_horizontal': self._fan_swing_cap_horiz,
                     'balance_point': self._balance_pt,
                     'heat_lock_temp': self._heat_lock_temp,
                     'cool_lock_temp': self._cool_lock_temp,
                     'available_mode': self._avail_mode,
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