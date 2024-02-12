

class Neviweb130LowVoltageWifiThermostat(Neviweb130Thermostat):
    """Implementation of Neviweb TH1400WF thermostat."""

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
        self._target_temp_away = None
        self._heat_level = 0
        self._heat_source_type = None
        self._floor_mode = None
        self._floor_sensor_type = None
        self._aux_heat = "off"
        self._aux_cycle_length = 0
        self._cycle_length_output2_status = "off"
        self._early_start = "off"
        self._keypad = None
        self._load1 = 0
        self._load2 = 0
        self._rssi = None
        self._display2 = None
        self._backlight = None
        self._time_format = "24h"
        self._floor_air_limit = None
        self._floor_air_limit_status = None
        self._floor_max = None
        self._floor_max_status = "off"
        self._floor_min = None
        self._floor_min_status = "off"
        self._temperature_format = UnitOfTemperature.CELSIUS
        self._temp_display_status = None
        self._temp_display_value = None
        self._cycle_length = 0
        self._aux_cycle_length = 0
        self._pump_protec_status = None
        self._pump_protec_duration = None
        self._pump_protec_period = None
        self._pump_duration_value = None
        self._code_reference_sensor = None
        self._code_compensation_sensor = None
        self._code_thermal_overload = None
        self._code_air_sensor = None
        self._code_wire_sensor = None
        self._code_current_overload = None
        self._code_load_error = None
        self._code_end_of_life = None
        self._is_wifi = device_info["signature"]["model"] in \
                        DEVICE_MODEL_WIFI_FLOOR or device_info["signature"]["model"] in \
                        DEVICE_MODEL_WIFI or device_info["signature"]["model"] in \
                        DEVICE_MODEL_LOW_WIFI
        self._is_low_wifi = device_info["signature"]["model"] in \
                            DEVICE_MODEL_LOW_WIFI
        self._is_double = False
        self._is_low_voltage = False
        self._is_gen2 = False
        self._is_hc = False
        self._is_floor = False
        self._is_wifi_floor = False
        self._energy_stat_time = time.time() - 1500
        self._snooze = 0
        self._activ = True
        _LOGGER.debug("Setting up %s: %s", self._name, device_info)

    def update(self):
        if self._activ:
            LOW_WIFI_ATTRIBUTES = [ATTR_FLOOR_OUTPUT2, ATTR_FLOOR_AUX, ATTR_ROOM_SETPOINT_AWAY, ATTR_EARLY_START,
                                   ATTR_BACKLIGHT_AUTO_DIM, ATTR_OCCUPANCY, ATTR_SETPOINT_MODE, ATTR_DISPLAY2,
                                   ATTR_WIFI_KEYPAD, ATTR_WIFI, ATTR_WIFI_WATTAGE,
                                   ATTR_FLOOR_OUTPUT1, ATTR_PUMP_PROTEC, ATTR_PUMP_PROTEC_DURATION,
                                   ATTR_FLOOR_AIR_LIMIT, ATTR_FLOOR_MODE, ATTR_FLOOR_SENSOR, ATTR_AUX_CYCLE, ATTR_CYCLE,
                                   ATTR_FLOOR_MAX, ATTR_FLOOR_MIN]
            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            _LOGGER.debug("Updated attributes for %s: %s", self._name, UPDATE_ATTRIBUTES + LOW_WIFI_ATTRIBUTES)
            device_data = self._client.get_device_attributes(self._id, UPDATE_ATTRIBUTES + LOW_WIFI_ATTRIBUTES)
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
                    self._temp_display_value = device_data[ATTR_ROOM_TEMP_DISPLAY]["value"]
                    self._temp_display_status = device_data[ATTR_ROOM_TEMP_DISPLAY]["status"]
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
                    self._wattage = device_data[ATTR_WIFI_WATTAGE]
                    self._backlight = device_data[ATTR_BACKLIGHT_AUTO_DIM]
                    self._early_start = device_data[ATTR_EARLY_START]
                    self._target_temp_away = device_data[ATTR_ROOM_SETPOINT_AWAY]
                    self._load1 = device_data[ATTR_FLOOR_OUTPUT1]
                    self._floor_mode = device_data[ATTR_FLOOR_MODE]
                    self._floor_sensor_type = device_data[ATTR_FLOOR_SENSOR]
                    self._aux_cycle_length = device_data[ATTR_AUX_CYCLE]
                    self._cycle_length = device_data[ATTR_CYCLE]
                    self._floor_max = device_data[ATTR_FLOOR_MAX]["value"]
                    self._floor_max_status = device_data[ATTR_FLOOR_MAX]["status"]
                    self._floor_min = device_data[ATTR_FLOOR_MIN]["value"]
                    self._floor_min_status = device_data[ATTR_FLOOR_MIN]["status"]
                    self._floor_air_limit = device_data[ATTR_FLOOR_AIR_LIMIT]["value"]
                    self._floor_air_limit_status = device_data[ATTR_FLOOR_AIR_LIMIT]["status"]
                    self._pump_protec_status = device_data[ATTR_PUMP_PROTEC]["status"]
                    if device_data[ATTR_PUMP_PROTEC]["status"] == "on":
                        self._pump_protec_period = device_data[ATTR_PUMP_PROTEC]["frequency"]
                        self._pump_protec_duration = device_data[ATTR_PUMP_PROTEC]["duration"]
                    if ATTR_PUMP_PROTEC_DURATION in device_data:
                        self._pump_duration_value = device_data[ATTR_PUMP_PROTEC_DURATION]
                    if ATTR_FLOOR_AUX in device_data:
                        self._aux_heat = device_data[ATTR_FLOOR_AUX]
                    self._load2 = device_data[ATTR_FLOOR_OUTPUT2]
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
        data.update({'sensor_mode': self._floor_mode,
                     'floor_sensor_type': self._floor_sensor_type,
                     'load_watt': self._wattage,
                     'auxiliary_cycle_length': self._aux_cycle_length,
                     'cycle_length': neviweb_to_ha(self._cycle_length),
                     'pump_protection_status': self._pump_protec_status,
                     'pump_protection_duration': self._pump_protec_duration,
                     'pump_protection_frequency': self._pump_protec_period,
                     'pump_duration_value': self._pump_duration_value,
                     'floor_limit_high': self._floor_max,
                     'floor_limit_high_status': self._floor_max_status,
                     'floor_limit_low': self._floor_min,
                     'floor_limit_low_status': self._floor_min_status,
                     'max_air_limit': self._floor_air_limit,
                     'max_air_limit_status': self._floor_air_limit_status,
                     'temp_display_status': self._temp_display_status,
                     'temp_display_value': self._temp_display_value,
                     'source_type': self._heat_source_type,
                     'early_start': self._early_start,
                     'setpoint_away': self._target_temp_away,
                     'load_watt_1': self._load1,
                     'second_display': self._display2,
                     'occupancy': self._occupancy,
                     'operation_mode': self._operation_mode,
                     'auxiliary_heat': self._aux_heat,
                     'auxiliary_load': self._load2,
                     'status compensation sensor': self._code_compensation_sensor,
                     'status thermal overload': self._code_thermal_overload,
                     'status air sensor': self._code_air_sensor,
                     'status reference sensor': self._code_reference_sensor,
                     'status load sensor': self._code_load_error,
                     'status wire sensor': self._code_wire_sensor,
                     'status current sensor': self._code_current_overload,
                     'status end of life sensor': self._code_end_of_life,
                     'heat_level': self._heat_level,
                     'pi_heating_demand': self._heat_level,
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