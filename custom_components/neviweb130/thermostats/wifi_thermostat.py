


class Neviweb130WifiThermostat(Neviweb130Thermostat):
    """Implementation of Neviweb TH1123WF, TH1124WF, TH1500WF thermostats."""

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
        self._temp_display_status = None
        self._heat_source_type = None
        self._early_start = "off"
        self._target_temp_away = None
        self._load1 = 0
        self._cycle_length = 0
        self._cycle_length_output2_status = "off"
        self._aux_heat = "off"
        self._aux_cycle_length = 0
        self._code_compensation_sensor = None
        self._code_wire_sensor = None
        self._code_current_overload = None
        self._code_thermal_overload = None
        self._code_end_of_life = None
        self._code_air_sensor = None
        self._code_reference_sensor = None
        self._code_load_error = None
        self._heat_level = 0
        self._temp_display_value = None
        self._display2 = None
        self._keypad = None
        self._backlight = None
        self._time_format = "24h"
        self._temperature_format = UnitOfTemperature.CELSIUS
        self._min_temp = 0
        self._max_temp = 0
        self._rssi = None
        self._is_wifi = device_info["signature"]["model"] in \
                        DEVICE_MODEL_WIFI_FLOOR or device_info["signature"]["model"] in \
                        DEVICE_MODEL_WIFI or device_info["signature"]["model"] in \
                        DEVICE_MODEL_LOW_WIFI
        self._is_double = False
        self._is_wifi_floor = False
        self._is_low_wifi = False
        self._is_low_voltage = False
        self._is_gen2 = False
        self._is_hc = False
        self._is_floor = False
        self._energy_stat_time = time.time() - 1500
        self._snooze = 0
        self._activ = True
        _LOGGER.debug("Setting up %s: %s", self._name, device_info)

    def update(self):
        if self._activ:
            WIFI_ATTRIBUTES = [ATTR_CYCLE, ATTR_FLOOR_OUTPUT1, ATTR_WIFI_WATTAGE, ATTR_WIFI, ATTR_WIFI_KEYPAD,
                               ATTR_DISPLAY2, ATTR_SETPOINT_MODE, ATTR_OCCUPANCY, ATTR_BACKLIGHT_AUTO_DIM,
                               ATTR_EARLY_START, ATTR_ROOM_SETPOINT_AWAY]
            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            _LOGGER.debug("Updated attributes for %s: %s", self._name, UPDATE_ATTRIBUTES + WIFI_ATTRIBUTES)
            device_data = self._client.get_device_attributes(self._id, UPDATE_ATTRIBUTES + WIFI_ATTRIBUTES)
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
                    if ATTR_CYCLE in device_data:
                        self._cycle_length = device_data[ATTR_CYCLE]
                    if ATTR_ROOM_TEMP_DISPLAY in device_data:
                        self._temp_display_status = device_data[ATTR_ROOM_TEMP_DISPLAY]["status"]
                        self._temp_display_value = device_data[ATTR_ROOM_TEMP_DISPLAY]["value"]
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
                     'occupancy': self._occupancy,
                     'temp_display_status': self._temp_display_status,
                     'source_type': self._heat_source_type,
                     'early_start': self._early_start,
                     'setpoint_away': self._target_temp_away,
                     'load_watt_1': self._load1,
                     'cycle_length': self._cycle_length,
                     'status compensation sensor': self._code_compensation_sensor,
                     'status wire sensor': self._code_wire_sensor,
                     'status current sensor': self._code_current_overload,
                     'status thermal sensor': self._code_thermal_overload,
                     'status end of life sensor': self._code_end_of_life,
                     'status air sensor': self._code_air_sensor,
                     'status reference sensor': self._code_reference_sensor,
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