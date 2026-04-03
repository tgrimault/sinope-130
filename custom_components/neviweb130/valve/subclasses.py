"""Neviweb130Valve subclasses."""
from __future__ import annotations

import logging
import time

from ..const import (
    ATTR_AWAY_ACTION,
    ATTR_BATTERY_STATUS,
    ATTR_BATTERY_VOLTAGE,
    ATTR_BATT_ACTION_LOW,
    ATTR_BATT_ALERT,
    ATTR_BATT_PERCENT_NORMAL,
    ATTR_BATT_STATUS_NORMAL,
    ATTR_CLOSE_VALVE,
    ATTR_ERROR_CODE_SET1,
    ATTR_FLOW_ALARM1,
    ATTR_FLOW_ALARM1_LENGTH,
    ATTR_FLOW_ALARM1_OPTION,
    ATTR_FLOW_ALARM1_PERIOD,
    ATTR_FLOW_ALARM2,
    ATTR_FLOW_ALARM_TIMER,
    ATTR_FLOW_ENABLED,
    ATTR_FLOW_METER_CONFIG,
    ATTR_FLOW_THRESHOLD,
    ATTR_MOTOR_POS,
    ATTR_MOTOR_TARGET,
    ATTR_OCCUPANCY_SENSOR_DELAY,
    ATTR_ONOFF,
    ATTR_POWER_SUPPLY,
    ATTR_RSSI,
    ATTR_STM8_ERROR,
    ATTR_TEMP_ACTION_LOW,
    ATTR_TEMP_ALARM,
    ATTR_TRIGGER_ALARM,
    ATTR_VALVE_CLOSURE,
    ATTR_VALVE_INFO,
    ATTR_WATER_LEAK_STATUS,
    ATTR_WIFI,
    MODE_OFF,
    STATE_VALVE_STATUS,
)
from ..helpers import translated_or_default
from .base import (
    Neviweb130Valve,
    lock_to_ha,
    L_2_sqm,
    model_to_HA,
    voltage_to_percentage,
    alert_to_text,
    neviweb_to_ha_delay,
    trigger_close,
    SNOOZE_TIME,
    IMPLEMENTED_WIFI_VALVE_MODEL,
    IMPLEMENTED_ZB_VALVE_MODEL,
    IMPLEMENTED_WIFI_MESH_VALVE_MODEL,
    IMPLEMENTED_ZB_MESH_VALVE_MODEL,
    UPDATE_ATTRIBUTES,
)

_LOGGER = logging.getLogger(__name__)

class Neviweb130WifiValve(Neviweb130Valve):
    """Implementation of a Neviweb Wi-Fi valve, VA4200WZ, VA4201WZ, VA4220WZ, VA4221WZ, VA4220WF, VA4221WF."""

    def __init__(self, device_info, name, sku, firmware, device_type, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, device_type, client)
        self._away_action = None
        self._batt_action_low = None
        self._flowmeter_divisor = 1
        self._flowmeter_offset = 0
        self._flowmeter_opt_action_1 = None
        self._flowmeter_opt_action_2 = None
        self._flowmeter_opt_alarm_1 = None
        self._flowmeter_opt_alarm_2 = None
        self._flowmeter_opt_duration_1 = 0
        self._flowmeter_opt_duration_2 = 0
        self._flowmeter_opt_flow_min_1 = 1
        self._flowmeter_opt_flow_min_2 = 1
        self._flowmeter_opt_observationPeriod_1 = 0
        self._flowmeter_opt_observationPeriod_2 = 0
        self._motor_target = None
        self._occupancy_delay = None
        self._stm8Error_motorJam = None
        self._stm8Error_motorLimit = None
        self._stm8Error_motorPosition = None
        self._temp_action_low = None
        self._valve_closure = None
        self._valve_info_cause = None
        self._valve_info_id = None
        self._valve_info_status = None
        self._water_leak_status = None

    def _load_attributes(self) -> list:
        return [
            ATTR_WIFI,
            ATTR_MOTOR_POS,
            ATTR_MOTOR_TARGET,
            ATTR_TEMP_ALARM,
            ATTR_VALVE_INFO,
            ATTR_BATTERY_VOLTAGE,
            ATTR_BATTERY_STATUS,
            ATTR_POWER_SUPPLY,
            ATTR_VALVE_CLOSURE,
            ATTR_BATT_ALERT,
            ATTR_STM8_ERROR,
            ATTR_FLOW_METER_CONFIG,
            ATTR_FLOW_ALARM1,
            ATTR_FLOW_ALARM2,
            ATTR_TEMP_ACTION_LOW,
            ATTR_BATT_ACTION_LOW,
            ATTR_OCCUPANCY_SENSOR_DELAY,
            ATTR_BATT_STATUS_NORMAL,
            ATTR_BATT_PERCENT_NORMAL,
            ATTR_WATER_LEAK_STATUS,
            ATTR_AWAY_ACTION,
        ]

    def _parse_common_state(self, data: dict, device_alert: dict | None = None) -> None:
        """Assign state fields from Wi-Fi valve device data."""
        self._valve_status = STATE_VALVE_STATUS if data[ATTR_MOTOR_POS] == 100 else "closed"
        self._onoff = "on" if self._valve_status == STATE_VALVE_STATUS else MODE_OFF
        self._temp_alert = data[ATTR_TEMP_ALARM]
        self._battery_voltage = data[ATTR_BATTERY_VOLTAGE] if data[ATTR_BATTERY_VOLTAGE] is not None else 0
        self._battery_status = data[ATTR_BATTERY_STATUS]
        self._power_supply = data[ATTR_POWER_SUPPLY]
        self._battery_alert = data[ATTR_BATT_ALERT]
        if ATTR_WATER_LEAK_STATUS in data:
            self._water_leak_status = data[ATTR_WATER_LEAK_STATUS]
            if self._water_leak_status == "flowMeter" and data[ATTR_FLOW_METER_CONFIG]["offset"] != 0:
                code = data[ATTR_WATER_LEAK_STATUS]
                self.notify_ha(
                    translated_or_default(
                        self.hass, "error_code",
                        f"Warning: Neviweb Device error code detected: {code} for \ndevice: {self._name}, ID: {self._id}, Sku: {self._sku}.",
                        code=code, message="", name=self._name, id=self._id, sku=self._sku,
                    )
                )
        if ATTR_MOTOR_TARGET in data:
            self._motor_target = data[ATTR_MOTOR_TARGET]
        if ATTR_VALVE_CLOSURE in data:
            self._valve_closure = data[ATTR_VALVE_CLOSURE]["source"]
        if ATTR_VALVE_INFO in data:
            self._valve_info_status = data[ATTR_VALVE_INFO]["status"]
            self._valve_info_cause = data[ATTR_VALVE_INFO]["cause"]
            self._valve_info_id = data[ATTR_VALVE_INFO]["identifier"]
        if ATTR_STM8_ERROR in data:
            self._stm8Error_motorJam = data[ATTR_STM8_ERROR]["motorJam"]
            if "motorPosition" in data[ATTR_STM8_ERROR]:
                self._stm8Error_motorPosition = data[ATTR_STM8_ERROR]["motorPosition"]
            if "motorLimit" in data[ATTR_STM8_ERROR]:
                self._stm8Error_motorLimit = data[ATTR_STM8_ERROR]["motorLimit"]
        if ATTR_FLOW_METER_CONFIG in data:
            self._flowmeter_multiplier = data[ATTR_FLOW_METER_CONFIG]["multiplier"]
            self._flowmeter_offset = data[ATTR_FLOW_METER_CONFIG]["offset"]
            self._flowmeter_divisor = data[ATTR_FLOW_METER_CONFIG]["divisor"]
        if ATTR_FLOW_ALARM1 in data:
            self._flowmeter_opt_alarm_1 = data[ATTR_FLOW_ALARM1]["actions"][ATTR_TRIGGER_ALARM]
            self._flowmeter_opt_action_1 = data[ATTR_FLOW_ALARM1]["actions"][ATTR_CLOSE_VALVE]
            self._flowmeter_opt_flow_min_1 = data[ATTR_FLOW_ALARM1]["flowMin"]
            self._flowmeter_opt_duration_1 = data[ATTR_FLOW_ALARM1]["duration"]
            self._flowmeter_opt_observationPeriod_1 = data[ATTR_FLOW_ALARM1]["observationPeriod"]
        if ATTR_FLOW_ALARM2 in data:
            self._flowmeter_opt_alarm_2 = data[ATTR_FLOW_ALARM2]["actions"][ATTR_TRIGGER_ALARM]
            self._flowmeter_opt_action_2 = data[ATTR_FLOW_ALARM2]["actions"][ATTR_CLOSE_VALVE]
            self._flowmeter_opt_flow_min_2 = data[ATTR_FLOW_ALARM2]["flowMin"]
            self._flowmeter_opt_duration_2 = data[ATTR_FLOW_ALARM2]["duration"]
            self._flowmeter_opt_observationPeriod_2 = data[ATTR_FLOW_ALARM2]["observationPeriod"]
        if ATTR_TEMP_ACTION_LOW in data:
            self._temp_action_low = data[ATTR_TEMP_ACTION_LOW]
        if ATTR_BATT_ACTION_LOW in data:
            self._batt_action_low = data[ATTR_BATT_ACTION_LOW]
        if ATTR_OCCUPANCY_SENSOR_DELAY in data:
            self._occupancy_delay = data[ATTR_OCCUPANCY_SENSOR_DELAY]
        if ATTR_WIFI in data:
            self._rssi = data[ATTR_WIFI]
        if ATTR_BATT_PERCENT_NORMAL in data:
            self._batt_percent_normal = data[ATTR_BATT_PERCENT_NORMAL]
        if ATTR_BATT_STATUS_NORMAL in data:
            self._batt_status_normal = data[ATTR_BATT_STATUS_NORMAL]
        if ATTR_AWAY_ACTION in data:
            self._away_action = data[ATTR_AWAY_ACTION]

    def update(self):
        """Get the latest data from Neviweb and update the state."""
        if not self._active:
            self._handle_snooze()
            return
        start = time.time()
        attributes = UPDATE_ATTRIBUTES + self._load_attributes()
        _LOGGER.debug("Updated attributes for %s (firmware %s): %s", self._name, self._firmware, attributes)
        device_data = self._fetch_attributes(attributes)
        elapsed = round(time.time() - start, 3)
        _LOGGER.debug("Updating %s (%s sec): %s", self._name, elapsed, device_data)
        if not self._handle_error(device_data):
            self._parse_common_state(device_data)
        self.do_stat(start)

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        data = {}
        data.update(
            {
                "valve_status": self._valve_status,
                "temperature_alert": self._temp_alert,
                "leak_icon": self.leak_icon,
                "icon_type": self.icon_type,
                "battery_level": voltage_to_percentage(self._battery_voltage, 4),
                "battery_voltage": self._battery_voltage,
                "battery_status": self._battery_status,
                "battery_icon": self.battery_icon,
                "power_supply": self._power_supply,
                "valve_closure_source": self._valve_closure,
                "battery_alert": self._battery_alert,
                "motor_target_position": self._motor_target,
                "water_leak_status": self._water_leak_status,
                "valve_info_status": self._valve_info_status,
                "valve_cause": self._valve_info_cause,
                "valve_info_id": self._valve_info_id,
                "alert_motor_jam": self._stm8Error_motorJam,
                "alert_motor_position": self._stm8Error_motorPosition,
                "alert_motor_limit": self._stm8Error_motorLimit,
                "away_action": self._away_action,
                "flow_meter_alarm_delay_1": neviweb_to_ha_delay(self._flowmeter_opt_observationPeriod_1),
                "flow_meter_alarm_duration_1": neviweb_to_ha_delay(self._flowmeter_opt_duration_1),
                "flow_meter_alarm_flowMin_1": self._flowmeter_opt_flow_min_1,
                "flowmeter_options_1": trigger_close(self._flowmeter_opt_action_1, self._flowmeter_opt_alarm_1),
                "flow_meter_alarm_delay_2": neviweb_to_ha_delay(self._flowmeter_opt_observationPeriod_2),
                "flow_meter_alarm_duration_2": neviweb_to_ha_delay(self._flowmeter_opt_duration_2),
                "flow_meter_alarm_flowMin_2": self._flowmeter_opt_flow_min_2,
                "flowmeter_options_2": trigger_close(self._flowmeter_opt_action_2, self._flowmeter_opt_alarm_2),
                "temp_action_low": self._temp_action_low,
                "batt_action_low": self._batt_action_low,
                "battery_percent_normalized": self._batt_percent_normal,
                "battery_status_normalized": self._batt_status_normal,
                "flow_meter_multiplier": self._flowmeter_multiplier,
                "flow_meter_offset": self._flowmeter_offset,
                "flow_meter_divisor": self._flowmeter_divisor,
                "occupancy_sensor_delay": neviweb_to_ha_delay(self._occupancy_delay),
                "total_flow_count": L_2_sqm(self._total_kwh_count),
                "monthly_flow_count": L_2_sqm(self._monthly_kwh_count),
                "daily_flow_count": L_2_sqm(self._daily_kwh_count),
                "hourly_flow_count": L_2_sqm(self._hourly_kwh_count),
                "hourly_flow": L_2_sqm(self._hour_kwh),
                "daily_flow": L_2_sqm(self._today_kwh),
                "monthly_flow": L_2_sqm(self._month_kwh),
                "last_flow_stat_update": self._mark,
                "rssi": self._rssi,
                "sku": self._sku,
                "device_model": str(self._device_model),
                "device_model_cfg": self._device_model_cfg,
                "firmware": self._firmware,
                "activation": self._active,
                "device_type": self._device_type,
                "id": self._id,
            }
        )
        return data


class Neviweb130MeshValve(Neviweb130Valve):
    """Implementation of a Neviweb mesh valve VA4220ZB and ACT4220ZB-M."""

    def __init__(self, device_info, name, sku, firmware, device_type, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, device_type, client)
        self._error_code = 0
        self._flowmeter_divisor = 1
        self._flowmeter_enabled = None
        self._flowmeter_offset = 0
        self._flowmeter_opt_action = None
        self._stm8Error_motorJam = None
        self._stm8Error_motorLimit = None
        self._stm8Error_motorPosition = None
        self._water_leak_status = None

    def _load_attributes(self) -> list:
        return [
            ATTR_RSSI,
            ATTR_BATTERY_VOLTAGE,
            ATTR_BATTERY_STATUS,
            ATTR_POWER_SUPPLY,
            ATTR_STM8_ERROR,
            ATTR_WATER_LEAK_STATUS,
            ATTR_FLOW_METER_CONFIG,
            ATTR_FLOW_ALARM_TIMER,
            ATTR_FLOW_THRESHOLD,
            ATTR_FLOW_ALARM1_PERIOD,
            ATTR_FLOW_ALARM1_LENGTH,
            ATTR_FLOW_ALARM1_OPTION,
            ATTR_FLOW_ENABLED,
            ATTR_BATT_STATUS_NORMAL,
            ATTR_BATT_PERCENT_NORMAL,
            ATTR_ERROR_CODE_SET1,
        ]

    def _parse_common_state(self, data: dict, device_alert: dict | None = None) -> None:
        """Assign state fields from mesh valve device data."""
        self._valve_status = STATE_VALVE_STATUS if data[ATTR_ONOFF] == "on" else "closed"
        self._onoff = data[ATTR_ONOFF]
        self._battery_voltage = data[ATTR_BATTERY_VOLTAGE] if data[ATTR_BATTERY_VOLTAGE] is not None else 0
        self._battery_status = data[ATTR_BATTERY_STATUS]
        self._power_supply = data[ATTR_POWER_SUPPLY]
        if device_alert is not None and ATTR_BATT_ALERT in device_alert:
            self._battery_alert = device_alert[ATTR_BATT_ALERT]
        if ATTR_STM8_ERROR in data:
            self._stm8Error_motorJam = data[ATTR_STM8_ERROR]["motorJam"]
            self._stm8Error_motorLimit = data[ATTR_STM8_ERROR]["motorLimit"]
            self._stm8Error_motorPosition = data[ATTR_STM8_ERROR]["motorPosition"]
        if ATTR_FLOW_METER_CONFIG in data:
            self._flowmeter_multiplier = data[ATTR_FLOW_METER_CONFIG]["multiplier"]
            self._flowmeter_offset = data[ATTR_FLOW_METER_CONFIG]["offset"]
            self._flowmeter_divisor = data[ATTR_FLOW_METER_CONFIG]["divisor"]
            self._flowmeter_model = model_to_HA(self._flowmeter_multiplier)
        self._water_leak_status = data[ATTR_WATER_LEAK_STATUS]
        if self._water_leak_status == "flowMeter" and data[ATTR_FLOW_METER_CONFIG]["offset"] != 0:
            code = data[ATTR_WATER_LEAK_STATUS]
            self.notify_ha(
                translated_or_default(
                    self.hass, "error_code",
                    f"Warning: Neviweb Device error code detected: {code} for \ndevice: {self._name}, ID: {self._id}, Sku: {self._sku}. {''}",
                    code=code, message="", name=self._name, id=self._id, sku=self._sku,
                )
            )
        if ATTR_FLOW_ALARM_TIMER in data:
            self._flowmeter_timer = data[ATTR_FLOW_ALARM_TIMER]
            if self._flowmeter_timer == 0 and ATTR_FLOW_THRESHOLD in data:
                self._flowmeter_threshold = data[ATTR_FLOW_THRESHOLD]
                self._flowmeter_alert_delay = data[ATTR_FLOW_ALARM1_PERIOD]
                self._flowmeter_alarm_length = data[ATTR_FLOW_ALARM1_LENGTH]
                self._flowmeter_opt_alarm = data[ATTR_FLOW_ALARM1_OPTION][ATTR_TRIGGER_ALARM]
                self._flowmeter_opt_action = data[ATTR_FLOW_ALARM1_OPTION][ATTR_CLOSE_VALVE]
        if ATTR_BATT_PERCENT_NORMAL in data:
            self._batt_percent_normal = data[ATTR_BATT_PERCENT_NORMAL]
        if ATTR_BATT_STATUS_NORMAL in data:
            self._batt_status_normal = data[ATTR_BATT_STATUS_NORMAL]
        if ATTR_RSSI in data:
            self._rssi = data[ATTR_RSSI]
        if ATTR_FLOW_ENABLED in data:
            self._flowmeter_enabled = data[ATTR_FLOW_ENABLED]
        if ATTR_ERROR_CODE_SET1 in data and len(data[ATTR_ERROR_CODE_SET1]) > 0:
            if data[ATTR_ERROR_CODE_SET1]["raw"] != 0:
                self._error_code = data[ATTR_ERROR_CODE_SET1]["raw"]
                code = str(data[ATTR_ERROR_CODE_SET1]["raw"])
                self.notify_ha(
                    translated_or_default(
                        self.hass, "error_code",
                        f"Warning: Neviweb Device error code detected: {code} for \ndevice: {self._name}, ID: {self._id}, Sku: {self._sku}.",
                        code=code, message="", name=self._name, id=self._id, sku=self._sku,
                    )
                )
                _LOGGER.warning("Error code set1 updated: %s", str(data[ATTR_ERROR_CODE_SET1]["raw"]))
        else:
            self._error_code = 0

    def update(self):
        """Get the latest data from Neviweb and update the state."""
        if not self._active:
            self._handle_snooze()
            return
        start = time.time()
        attributes = UPDATE_ATTRIBUTES + self._load_attributes()
        _LOGGER.debug("Updated attributes for %s (firmware %s): %s", self._name, self._firmware, attributes)
        device_data = self._fetch_attributes(attributes)
        elapsed = round(time.time() - start, 3)
        device_alert = self._client.get_device_alert(self._id)
        _LOGGER.debug("Updating alert for %s (%s sec): %s", self._name, elapsed, device_alert)
        _LOGGER.debug("Updating %s (%s sec): %s", self._name, elapsed, device_data)
        if not self._handle_error(device_data):
            self._parse_common_state(device_data, device_alert)
        self.do_stat(start)

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        data = {}
        data.update(
            {
                "battery_level": voltage_to_percentage(self._battery_voltage, 4),
                "battery_voltage": self._battery_voltage,
                "battery_status": self._battery_status,
                "battery_icon": self.battery_icon,
                "battery_percent_normalized": self._batt_percent_normal,
                "battery_status_normalized": self._batt_status_normal,
                "leak_icon": self.leak_icon,
                "icon_type": self.icon_type,
                "power_supply": self._power_supply,
                "alert_motor_jam": self._stm8Error_motorJam,
                "alert_motor_position": self._stm8Error_motorPosition,
                "alert_motor_limit": self._stm8Error_motorLimit,
                "error_code": self._error_code,
                "flow_meter_multiplier": self._flowmeter_multiplier,
                "flow_meter_offset": self._flowmeter_offset,
                "flow_meter_divisor": self._flowmeter_divisor,
                "flow_meter_model": self._flowmeter_model,
                "flow_meter_disable_timer": self._flowmeter_timer,
                "flow_meter_alert_delay": neviweb_to_ha_delay(self._flowmeter_alert_delay),
                "flow_meter_alarm_length": self._flowmeter_alarm_length,
                "flowmeter_options": trigger_close(self._flowmeter_opt_action, self._flowmeter_opt_alarm),
                "flowmeter_enabled": self._flowmeter_enabled,
                "water_leak_status": self._water_leak_status,
                "battery_alert": alert_to_text(self._battery_alert, "bat"),
                "total_flow_count": L_2_sqm(self._total_kwh_count),
                "monthly_flow_count": L_2_sqm(self._monthly_kwh_count),
                "daily_flow_count": L_2_sqm(self._daily_kwh_count),
                "hourly_flow_count": L_2_sqm(self._hourly_kwh_count),
                "hourly_flow": L_2_sqm(self._hour_kwh),
                "daily_flow": L_2_sqm(self._today_kwh),
                "monthly_flow": L_2_sqm(self._month_kwh),
                "last_flow_stat_update": self._mark,
                "rssi": self._rssi,
                "sku": self._sku,
                "device_model": str(self._device_model),
                "device_model_cfg": self._device_model_cfg,
                "firmware": self._firmware,
                "activation": self._active,
                "device_type": self._device_type,
                "id": self._id,
            }
        )
        return data


class Neviweb130WifiMeshValve(Neviweb130Valve):
    """Implementation of a Neviweb Wi-Fi mesh valve, ACT4220WF-M, ACT4221WF-M."""

    def __init__(self, device_info, name, sku, firmware, device_type, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, device_type, client)
        self._batt_action_low = None
        self._flow_alarm_1 = None
        self._flow_alarm_2 = None
        self._flowmeter_divisor = 1
        self._flowmeter_offset = None
        self._motor_target = None
        self._stm8Error_motorJam = None
        self._stm8Error_motorLimit = None
        self._stm8Error_motorPosition = None
        self._temp_action_low = None
        self._valve_info_cause = None
        self._valve_info_id = None
        self._valve_info_status = None
        self._water_leak_status = None

    def _load_attributes(self) -> list:
        return [
            ATTR_MOTOR_POS,
            ATTR_MOTOR_TARGET,
            ATTR_TEMP_ALARM,
            ATTR_VALVE_INFO,
            ATTR_BATTERY_STATUS,
            ATTR_POWER_SUPPLY,
            ATTR_BATTERY_VOLTAGE,
            ATTR_STM8_ERROR,
            ATTR_FLOW_METER_CONFIG,
            ATTR_WATER_LEAK_STATUS,
            ATTR_FLOW_ALARM_TIMER,
            ATTR_FLOW_THRESHOLD,
            ATTR_FLOW_ALARM1_PERIOD,
            ATTR_FLOW_ALARM1_LENGTH,
            ATTR_FLOW_ALARM1_OPTION,
            ATTR_FLOW_ALARM1,
            ATTR_FLOW_ALARM2,
            ATTR_TEMP_ACTION_LOW,
            ATTR_BATT_ACTION_LOW,
        ]

    def _parse_common_state(self, data: dict, device_alert: dict | None = None) -> None:
        """Assign state fields from Wi-Fi mesh valve device data."""
        self._valve_status = STATE_VALVE_STATUS if data[ATTR_MOTOR_POS] == 100 else "closed"
        self._onoff = "on" if self._valve_status == STATE_VALVE_STATUS else MODE_OFF
        self._motor_target = data[ATTR_MOTOR_TARGET]
        self._temp_alert = data[ATTR_TEMP_ALARM]
        if ATTR_VALVE_INFO in data:
            self._valve_info_status = data[ATTR_VALVE_INFO]["status"]
            self._valve_info_cause = data[ATTR_VALVE_INFO]["cause"]
            self._valve_info_id = data[ATTR_VALVE_INFO]["identifier"]
        self._battery_status = data[ATTR_BATTERY_STATUS]
        self._power_supply = data[ATTR_POWER_SUPPLY]
        self._battery_voltage = data[ATTR_BATTERY_VOLTAGE] if data[ATTR_BATTERY_VOLTAGE] is not None else 0
        if ATTR_STM8_ERROR in data:
            self._stm8Error_motorJam = data[ATTR_STM8_ERROR]["motorJam"]
            self._stm8Error_motorLimit = data[ATTR_STM8_ERROR]["motorLimit"]
            self._stm8Error_motorPosition = data[ATTR_STM8_ERROR]["motorPosition"]
        if ATTR_FLOW_METER_CONFIG in data:
            self._flowmeter_multiplier = data[ATTR_FLOW_METER_CONFIG]["multiplier"]
            self._flowmeter_offset = data[ATTR_FLOW_METER_CONFIG]["offset"]
            self._flowmeter_divisor = data[ATTR_FLOW_METER_CONFIG]["divisor"]
            self._flowmeter_model = model_to_HA(self._flowmeter_multiplier)
        self._water_leak_status = data[ATTR_WATER_LEAK_STATUS]
        if self._water_leak_status == "flowMeter" and data[ATTR_FLOW_METER_CONFIG]["offset"] != 0:
            code = data[ATTR_WATER_LEAK_STATUS]
            self.notify_ha(
                translated_or_default(
                    self.hass, "error_code",
                    f"Warning: Neviweb Device error code detected: {code} for \ndevice: {self._name}, ID: {self._id}, Sku: {self._sku}.",
                    code=code, message="", name=self._name, id=self._id, sku=self._sku,
                )
            )
        if ATTR_FLOW_ALARM_TIMER in data:
            self._flowmeter_timer = data[ATTR_FLOW_ALARM_TIMER]
            if self._flowmeter_timer == 0 and ATTR_FLOW_THRESHOLD in data:
                self._flowmeter_threshold = data[ATTR_FLOW_THRESHOLD]
                self._flowmeter_alert_delay = data[ATTR_FLOW_ALARM1_PERIOD]
                self._flowmeter_alarm_length = data[ATTR_FLOW_ALARM1_LENGTH]
                self._flowmeter_opt_alarm = data[ATTR_FLOW_ALARM1_OPTION][ATTR_TRIGGER_ALARM]
                self._flowmeter_opt_action = data[ATTR_FLOW_ALARM1_OPTION][ATTR_CLOSE_VALVE]
        if ATTR_FLOW_ALARM1 in data:
            self._flow_alarm_1 = data[ATTR_FLOW_ALARM1]
        if ATTR_FLOW_ALARM2 in data:
            self._flow_alarm_2 = data[ATTR_FLOW_ALARM2]
        if ATTR_TEMP_ACTION_LOW in data:
            self._temp_action_low = data[ATTR_TEMP_ACTION_LOW]
        if ATTR_BATT_ACTION_LOW in data:
            self._batt_action_low = data[ATTR_BATT_ACTION_LOW]

    def update(self):
        """Get the latest data from Neviweb and update the state."""
        if not self._active:
            self._handle_snooze()
            return
        start = time.time()
        attributes = UPDATE_ATTRIBUTES + self._load_attributes()
        _LOGGER.debug("Updated attributes for %s (firmware %s): %s", self._name, self._firmware, attributes)
        device_data = self._fetch_attributes(attributes)
        elapsed = round(time.time() - start, 3)
        _LOGGER.debug("Updating %s (%s sec): %s", self._name, elapsed, device_data)
        if not self._handle_error(device_data):
            self._parse_common_state(device_data)

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        data = {}
        data.update(
            {
                "motor_target_position": self._motor_target,
                "temperature_alert": self._temp_alert,
                "valve_status": self._valve_info_status,
                "valve_cause": self._valve_info_cause,
                "valve_info_id": self._valve_info_id,
                "leak_icon": self.leak_icon,
                "icon_type": self.icon_type,
                "battery_level": voltage_to_percentage(self._battery_voltage, 4),
                "battery_voltage": self._battery_voltage,
                "battery_status": self._battery_status,
                "battery_icon": self.battery_icon,
                "power_supply": self._power_supply,
                "alert_motor_jam": self._stm8Error_motorJam,
                "alert_motor_position": self._stm8Error_motorPosition,
                "alert_motor_limit": self._stm8Error_motorLimit,
                "flow_alarm1": self._flow_alarm_1,
                "flow_alarm2": self._flow_alarm_2,
                "temp_action_low": self._temp_action_low,
                "batt_action_low": self._batt_action_low,
                "flow_meter_multiplier": self._flowmeter_multiplier,
                "flow_meter_offset": self._flowmeter_offset,
                "flow_meter_divisor": self._flowmeter_divisor,
                "flow_meter_model": self._flowmeter_model,
                "flow_meter_disable_timer": self._flowmeter_timer,
                "flow_meter_alert_delay": neviweb_to_ha_delay(self._flowmeter_alert_delay),
                "flow_meter_alarm_length": self._flowmeter_alarm_length,
                "flowmeter_options": trigger_close(self._flowmeter_opt_action, self._flowmeter_opt_alarm),
                "water_leak_status": self._water_leak_status,
                "total_flow_count": L_2_sqm(self._total_kwh_count),
                "monthly_flow_count": L_2_sqm(self._monthly_kwh_count),
                "daily_flow_count": L_2_sqm(self._daily_kwh_count),
                "hourly_flow_count": L_2_sqm(self._hourly_kwh_count),
                "hourly_flow": L_2_sqm(self._hour_kwh),
                "daily_flow": L_2_sqm(self._today_kwh),
                "monthly_flow": L_2_sqm(self._month_kwh),
                "last_flow_stat_update": self._mark,
                "sku": self._sku,
                "device_model": str(self._device_model),
                "device_model_cfg": self._device_model_cfg,
                "firmware": self._firmware,
                "activation": self._active,
                "device_type": self._device_type,
                "id": self._id,
            }
        )
        return data
