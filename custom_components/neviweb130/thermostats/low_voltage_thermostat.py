


class Neviweb130LowVoltageThermostat(Neviweb130Thermostat):
    """Implementation of Neviweb TH1400ZB thermostat."""

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
        self._min_temp = 0
        self._max_temp = 0
        self._temperature_format = UnitOfTemperature.CELSIUS
        self._time_format = "24h"
        self._backlight = None
        self._keypad = None
        self._display2 = None
        self._temp_display_value = None
        self._heat_level = 0
        self._pump_protec_status = None
        self._pump_protec_duration = None
        self._pump_protec_period = None
        self._pump_protec_period_status = None
        self._floor_sensor_type = None
        self._floor_air_limit = None
        self._floor_air_limit_status = None
        self._floor_max = None
        self._floor_max_status = "off"
        self._floor_min = None
        self._floor_min_status = "off"
        self._cycle_length_output2_value = 0
        self._cycle_length_output2_status = "off"
        self._aux_heat = "off"
        self._aux_cycle_length = 0
        self._cycle_length = 0
        self._floor_mode = None
        self._code_compensation_sensor = None
        self._code_thermal_overload = None
        self._code_air_sensor = None
        self._code_floor_sensor = None
        self._load1 = 0
        self._load2 = 0
        self._load2_status = None
        self._rssi = None
        self._is_low_voltage = device_info["signature"]["model"] in \
                               DEVICE_MODEL_LOW
        self._is_wifi = False
        self._is_wifi_floor = False
        self._is_low_wifi = False
        self._is_double = False
        self._is_gen2 = False
        self._is_hc = False
        self._is_floor = False
        self._energy_stat_time = time.time() - 1500
        self._snooze = 0
        self._activ = True
        _LOGGER.debug("Setting up %s: %s", self._name, device_info)

    def update(self):
        if self._activ:
            LOW_VOLTAGE_ATTRIBUTES = [ATTR_KEYPAD, ATTR_BACKLIGHT, ATTR_SYSTEM_MODE, ATTR_CYCLE, ATTR_DISPLAY2,
                                      ATTR_RSSI, ATTR_PUMP_PROTEC_DURATION, ATTR_PUMP_PROTEC_PERIOD,
                                      ATTR_FLOOR_AIR_LIMIT, ATTR_FLOOR_MODE,
                                      ATTR_FLOOR_SENSOR, ATTR_FLOOR_MAX, ATTR_FLOOR_MIN, ATTR_CYCLE_OUTPUT2,
                                      ATTR_FLOOR_OUTPUT1, ATTR_FLOOR_OUTPUT2]
            """Get the latest data from Neviweb and update the state."""
            start = time.time()
            _LOGGER.debug("Updated attributes for %s: %s", self._name, UPDATE_ATTRIBUTES + LOW_VOLTAGE_ATTRIBUTES)
            device_data = self._client.get_device_attributes(self._id, UPDATE_ATTRIBUTES + LOW_VOLTAGE_ATTRIBUTES)
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
                    self._heat_level = device_data[ATTR_OUTPUT_PERCENT_DISPLAY]
                    self._keypad = device_data[ATTR_KEYPAD]
                    self._backlight = device_data[ATTR_BACKLIGHT]
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
                    if ATTR_CYCLE in device_data:
                        self._cycle_length = device_data[ATTR_CYCLE]
                    if ATTR_RSSI in device_data:
                        self._rssi = device_data[ATTR_RSSI]
                    self._operation_mode = device_data[ATTR_SYSTEM_MODE]
                    self._floor_mode = device_data[ATTR_FLOOR_MODE]
                    self._floor_air_limit = device_data[ATTR_FLOOR_AIR_LIMIT]["value"]
                    self._floor_air_limit_status = device_data[ATTR_FLOOR_AIR_LIMIT]["status"]
                    self._cycle_length_output2_status = device_data[ATTR_CYCLE_OUTPUT2]["status"]
                    self._cycle_length_output2_value = device_data[ATTR_CYCLE_OUTPUT2]["value"]
                    self._floor_max = device_data[ATTR_FLOOR_MAX]["value"]
                    self._floor_max_status = device_data[ATTR_FLOOR_MAX]["status"]
                    self._floor_min = device_data[ATTR_FLOOR_MIN]["value"]
                    self._floor_min_status = device_data[ATTR_FLOOR_MIN]["status"]
                    self._pump_protec_status = device_data[ATTR_PUMP_PROTEC_DURATION]["status"]
                    if device_data[ATTR_PUMP_PROTEC_DURATION]["status"] == "on":
                        self._pump_protec_duration = device_data[ATTR_PUMP_PROTEC_DURATION]["value"]
                        self._pump_protec_period = device_data[ATTR_PUMP_PROTEC_PERIOD]["value"]
                        self._pump_protec_period_status = device_data[ATTR_PUMP_PROTEC_PERIOD]["status"]
                    self._floor_sensor_type = device_data[ATTR_FLOOR_SENSOR]
                    if ATTR_FLOOR_OUTPUT1 in device_data:
                        self._load1 = device_data[ATTR_FLOOR_OUTPUT1]
                    if ATTR_FLOOR_OUTPUT2 in device_data:
                        self._load2_status = device_data[ATTR_FLOOR_OUTPUT2]["status"]
                        if device_data[ATTR_FLOOR_OUTPUT2]["status"] == "on":
                            self._load2 = device_data[ATTR_FLOOR_OUTPUT2]["value"]
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
                     'cycle_length': neviweb_to_ha(self._cycle_length),
                     'auxiliary_cycle_status': self._cycle_length_output2_status,
                     'auxiliary_cycle_value': neviweb_to_ha(self._cycle_length_output2_value),
                     'floor_limit_high': self._floor_max,
                     'floor_limit_high_status': self._floor_max_status,
                     'floor_limit_low': self._floor_min,
                     'floor_limit_low_status': self._floor_min_status,
                     'max_air_limit': self._floor_air_limit,
                     'max_air_limit_status': self._floor_air_limit_status,
                     'floor_sensor_type': self._floor_sensor_type,
                     'pump_protection_status': self._pump_protec_status,
                     'pump_protection_duration': self._pump_protec_duration,
                     'pump_protection_frequency': self._pump_protec_period,
                     'pump_protection_frequency_status': self._pump_protec_period_status,
                     'status compensation sensor': self._code_compensation_sensor,
                     'status thermal overload': self._code_thermal_overload,
                     'status air sensor': self._code_air_sensor,
                     'status floor sensor': self._code_floor_sensor,
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
                     'cycle_length_output': self._load1,
                     'cycle_length_output_2': self._load2,
                     'cycle_length_output_2_status': self._load2_status,
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