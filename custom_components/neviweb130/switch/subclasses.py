"""Neviweb130Switch subclasses."""
from __future__ import annotations

import logging
import time

from ..const import (
    ATTR_AWAY_ACTION,
    ATTR_BATT_INFO,
    ATTR_BATT_PERCENT_NORMAL,
    ATTR_BATT_STATUS_NORMAL,
    ATTR_BATTERY_STATUS,
    ATTR_BATTERY_VOLTAGE,
    ATTR_COLD_LOAD_PICKUP_REMAIN_TIME,
    ATTR_COLD_LOAD_PICKUP_STATUS,
    ATTR_COLD_LOAD_PICKUP_TEMP,
    ATTR_CONTROLLED_DEVICE,
    ATTR_DR_PROTEC_STATUS,
    ATTR_DR_WATER_TEMP_TIME,
    ATTR_DRACTIVE,
    ATTR_DRSTATUS,
    ATTR_ERROR_CODE_SET1,
    ATTR_EXT_TEMP,
    ATTR_INPUT2_STATUS,
    ATTR_INPUT_1_OFF_DELAY,
    ATTR_INPUT_1_ON_DELAY,
    ATTR_INPUT_2_OFF_DELAY,
    ATTR_INPUT_2_ON_DELAY,
    ATTR_INPUT_STATUS,
    ATTR_KEYPAD,
    ATTR_LEAK_CLOSURE_CONFIG,
    ATTR_LEG_PROTEC_STATUS,
    ATTR_LOW_TEMP_STATUS,
    ATTR_MIN_WATER_TEMP,
    ATTR_NAME_1,
    ATTR_NAME_2,
    ATTR_ONOFF,
    ATTR_ONOFF2,
    ATTR_OPTOUT,
    ATTR_OUTPUT_NAME_1,
    ATTR_OUTPUT_NAME_2,
    ATTR_REL_HUMIDITY,
    ATTR_ROOM_TEMPERATURE,
    ATTR_RSSI,
    ATTR_SYSTEM_MODE,
    ATTR_TANK_SIZE,
    ATTR_TEMP_ALERT,
    ATTR_TIMER,
    ATTR_TIMER2,
    ATTR_WATER_LEAK_ALARM_STATUS,
    ATTR_WATER_LEAK_DISCONNECTED_STATUS,
    ATTR_WATER_LEAK_STATUS,
    ATTR_WATER_TANK_ON,
    ATTR_WATER_TEMP_MIN,
    ATTR_WATER_TEMP_PROTECT,
    ATTR_WATER_TEMP_TIME,
    ATTR_WATER_TEMPERATURE,
    ATTR_WATT_TIME_ON,
    ATTR_WATTAGE,
    ATTR_WATTAGE_INSTANT,
    ATTR_WIFI,
    ATTR_WIFI_KEYPAD,
    ATTR_WIFI_WATT_NOW,
    ATTR_WIFI_WATTAGE,
    STATE_KEYPAD_STATUS,
    STATE_WATER_LEAK,
)
from ..helpers import translated_or_default
from .base import (
    Neviweb130Switch,
    UPDATE_ATTRIBUTES,
    lock_to_ha,
    neviweb_to_ha,
    neviweb_to_ha_controlled,
    neviweb_to_ha_delay,
    remaining_time,
    voltage_to_percentage,
)

_LOGGER = logging.getLogger(__name__)
class Neviweb130PowerSwitch(Neviweb130Switch):
    """Implementation of a Neviweb power controller switch, RM3250ZB connected to GT130 or Sedna."""

    def __init__(self, device_info, name, sku, firmware, device_type, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, device_type, client)
        self._error_code = None
        self._rssi = None
        self._wattage = 0

    _POWER_LOAD_ATTRIBUTES = [
        ATTR_WATTAGE,
        ATTR_WATTAGE_INSTANT,
        ATTR_TIMER,
        ATTR_KEYPAD,
        ATTR_DRSTATUS,
        ATTR_RSSI,
        ATTR_CONTROLLED_DEVICE,
        ATTR_ERROR_CODE_SET1,
    ]

    def _parse_common_state(self, data: dict) -> None:
        """Assign state fields from device data for power switch."""
        self._onoff = data[ATTR_ONOFF]
        if self._is_sedna_load:
            return
        self._current_power_w = data[ATTR_WATTAGE_INSTANT]
        self._wattage = data[ATTR_WATTAGE]
        self._keypad = STATE_KEYPAD_STATUS if data[ATTR_KEYPAD] == STATE_KEYPAD_STATUS else "locked"
        self._timer = data[ATTR_TIMER]
        if ATTR_DRSTATUS in data:
            self._drstatus_active = data[ATTR_DRSTATUS][ATTR_DRACTIVE]
            self._drstatus_optout = data[ATTR_DRSTATUS][ATTR_OPTOUT]
            self._drstatus_onoff = data[ATTR_DRSTATUS][ATTR_ONOFF]
        if ATTR_ERROR_CODE_SET1 in data and len(data[ATTR_ERROR_CODE_SET1]) > 0:
            if data[ATTR_ERROR_CODE_SET1]["raw"] != 0:
                self._error_code = data[ATTR_ERROR_CODE_SET1]["raw"]
                code = data[ATTR_ERROR_CODE_SET1]["raw"]
                self.notify_ha(
                    translated_or_default(
                        self.hass, "error_code",
                        f"Warning: Neviweb Device error code detected: {code} for \n"
                        f"device: {self._name}, ID: {self._id}, Sku: {self._sku}.",
                        code=code, message="", name=self._name, id=self._id, sku=self._sku,
                    )
                )
        else:
            self._error_code = 0
        if ATTR_RSSI in data:
            self._rssi = data[ATTR_RSSI]
        self._controlled_device = data[ATTR_CONTROLLED_DEVICE]

    def update(self):
        """Get the latest data from Neviweb and update the state."""
        if not self._active:
            self._handle_snooze()
            return
        load_attrs = self._POWER_LOAD_ATTRIBUTES if self._is_load else []
        start = time.time()
        device_data = self._fetch_attributes(UPDATE_ATTRIBUTES + load_attrs)
        elapsed = round(time.time() - start, 3)
        _LOGGER.debug("Updating %s (%s sec): %s", self._name, elapsed, device_data)
        if not self._handle_error(device_data):
            self._parse_common_state(device_data)
        if self._is_load:
            self.do_stat(start)

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        data = {}
        data.update({"onOff": self._onoff})
        if not self._is_sedna_load:
            data.update(
                {
                    "controlled_device": neviweb_to_ha_controlled(self._controlled_device),
                    "wattage": self._wattage,
                    "wattage_instant": self._current_power_w,
                    "total_kwh_count": self._total_kwh_count,
                    "monthly_kwh_count": self._monthly_kwh_count,
                    "daily_kwh_count": self._daily_kwh_count,
                    "hourly_kwh_count": self._hourly_kwh_count,
                    "hourly_kwh": self._hour_kwh,
                    "daily_kwh": self._today_kwh,
                    "monthly_kwh": self._month_kwh,
                    "last_energy_stat_update": self._mark,
                    "keypad": lock_to_ha(self._keypad),
                    "timer": self._timer,
                    "eco_status": self._drstatus_active,
                    "eco_optOut": self._drstatus_optout,
                    "eco_onoff": self._drstatus_onoff,
                    "error_code": self._error_code,
                    "rssi": self._rssi,
                }
            )
        data.update(
            {
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


class Neviweb130WifiPowerSwitch(Neviweb130Switch):
    """Implementation of a Neviweb power controller switch, RM3250WF."""

    def __init__(self, device_info, name, sku, firmware, device_type, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, device_type, client)
        self._error_code = None
        self._wattage = 0
        self._wifirssi = None

    _WIFI_LOAD_ATTRIBUTES = [
        ATTR_WATTAGE_INSTANT,
        ATTR_WIFI_WATTAGE,
        ATTR_WIFI_KEYPAD,
        ATTR_DRSTATUS,
        ATTR_WIFI,
        ATTR_CONTROLLED_DEVICE,
        ATTR_ERROR_CODE_SET1,
    ]

    def _parse_common_state(self, data: dict) -> None:
        """Assign state fields from device data for Wi-Fi power switch."""
        self._onoff = data[ATTR_ONOFF]
        self._current_power_w = data[ATTR_WATTAGE_INSTANT]
        self._wattage = data[ATTR_WIFI_WATTAGE]
        self._keypad = STATE_KEYPAD_STATUS if data[ATTR_WIFI_KEYPAD] == STATE_KEYPAD_STATUS else "locked"
        if ATTR_DRSTATUS in data:
            self._drstatus_active = data[ATTR_DRSTATUS][ATTR_DRACTIVE]
            self._drstatus_optout = data[ATTR_DRSTATUS][ATTR_OPTOUT]
            self._drstatus_onoff = data[ATTR_DRSTATUS][ATTR_ONOFF]
        if ATTR_ERROR_CODE_SET1 in data and len(data[ATTR_ERROR_CODE_SET1]) > 0:
            if data[ATTR_ERROR_CODE_SET1]["raw"] != 0:
                self._error_code = data[ATTR_ERROR_CODE_SET1]["raw"]
                code = str(data[ATTR_ERROR_CODE_SET1]["raw"])
                self.notify_ha(
                    translated_or_default(
                        self.hass, "error_code",
                        f"Warning: Neviweb Device error code detected: {code} for \n"
                        f"device: {self._name}, ID: {self._id}, Sku: {self._sku}.",
                        code=code, message="", name=self._name, id=self._id, sku=self._sku,
                    )
                )
        else:
            self._error_code = 0
        if ATTR_WIFI in data:
            self._wifirssi = data[ATTR_WIFI]
        self._controlled_device = data[ATTR_CONTROLLED_DEVICE]

    def update(self):
        """Get the latest data from Neviweb and update the state."""
        if not self._active:
            self._handle_snooze()
            return
        start = time.time()
        device_data = self._fetch_attributes(UPDATE_ATTRIBUTES + self._WIFI_LOAD_ATTRIBUTES)
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
                "onOff": self._onoff,
                "controlled_device": neviweb_to_ha_controlled(self._controlled_device),
                "wattage": self._wattage,
                "wattage_instant": self._current_power_w,
                "total_kwh_count": self._total_kwh_count,
                "monthly_kwh_count": self._monthly_kwh_count,
                "daily_kwh_count": self._daily_kwh_count,
                "hourly_kwh_count": self._hourly_kwh_count,
                "hourly_kwh": self._hour_kwh,
                "daily_kwh": self._today_kwh,
                "monthly_kwh": self._month_kwh,
                "last_energy_stat_update": self._mark,
                "keypad": lock_to_ha(self._keypad),
                "timer": self._timer,
                "eco_status": self._drstatus_active,
                "eco_optOut": self._drstatus_optout,
                "eco_onoff": self._drstatus_onoff,
                "error_code": self._error_code,
                "rssi": self._wifirssi,
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


class Neviweb130TankPowerSwitch(Neviweb130Switch):
    """Implementation of a Neviweb water heater power controller switch, RM3500ZB."""

    def __init__(self, device_info, name, sku, firmware, device_type, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, device_type, client)
        self._cold_load_status = None
        self._consumption = None
        self._consumption_time = None
        self._drstatus_optout_reason = "off"
        self._error_code = None
        self._rssi = None
        self._temperature = None
        self._water_leak_status = None
        self._water_temp = None
        self._water_temp_protect = None
        self._water_temp_time = None
        self._watt_time_on = None
        self._wattage = 0

    _TANK_LOAD_ATTRIBUTES = [
        ATTR_WATER_LEAK_STATUS,
        ATTR_ROOM_TEMPERATURE,
        ATTR_ERROR_CODE_SET1,
        ATTR_WATTAGE,
        ATTR_WATTAGE_INSTANT,
        ATTR_COLD_LOAD_PICKUP_STATUS,
        ATTR_TANK_SIZE,
        ATTR_WATER_TEMP_MIN,
        ATTR_WATT_TIME_ON,
        ATTR_DR_WATER_TEMP_TIME,
        ATTR_RSSI,
        ATTR_DRSTATUS,
        ATTR_DR_PROTEC_STATUS,
        ATTR_COLD_LOAD_PICKUP_REMAIN_TIME,
        ATTR_WATER_TEMP_PROTECT,
    ]

    def _parse_common_state(self, data: dict) -> None:
        """Assign state fields from device data for tank power switch."""
        self._onoff = data[ATTR_ONOFF]
        if ATTR_WATER_LEAK_STATUS in data:
            if data[ATTR_WATER_LEAK_STATUS] == "probe":
                code = data[ATTR_WATER_LEAK_STATUS]
                self.notify_ha(
                    translated_or_default(
                        self.hass, "error_code",
                        f"Warning: Neviweb Device error code detected: {code} for \n"
                        f"device: {self._name}, ID: {self._id}, Sku: {self._sku}.",
                        code=code, message="", name=self._name, id=self._id, sku=self._sku,
                    )
                )
                self._water_leak_status = data[ATTR_WATER_LEAK_STATUS]
            else:
                self._water_leak_status = STATE_WATER_LEAK if data[ATTR_WATER_LEAK_STATUS] == STATE_WATER_LEAK else "ok"
        self._water_temp = data[ATTR_ROOM_TEMPERATURE]
        if ATTR_ERROR_CODE_SET1 in data and len(data[ATTR_ERROR_CODE_SET1]) > 0:
            if data[ATTR_ERROR_CODE_SET1]["raw"] != 0:
                self._error_code = data[ATTR_ERROR_CODE_SET1]["raw"]
                message = None
                match self._error_code:
                    case 32:
                        message = "Temperature sensor disconnected"
                    case 64:
                        message = "Leak sensor disconnected"
                code = str(data[ATTR_ERROR_CODE_SET1]["raw"])
                self.notify_ha(
                    translated_or_default(
                        self.hass, "error_code",
                        f"Warning: Neviweb Device error code detected: {code} for \n"
                        f"device: {self._name}, ID: {self._id}, Sku: {self._sku}. {message}",
                        code=code, message=message, name=self._name, id=self._id, sku=self._sku,
                    )
                )
        else:
            self._error_code = 0
        self._wattage = data[ATTR_WATTAGE]
        self._current_power_w = data[ATTR_WATTAGE_INSTANT]
        self._cold_load_status = data[ATTR_COLD_LOAD_PICKUP_STATUS]
        self._cold_load_remaining_time = data[ATTR_COLD_LOAD_PICKUP_REMAIN_TIME]
        self._rssi = data[ATTR_RSSI]
        self._tank_size = data[ATTR_TANK_SIZE]
        if ATTR_DRSTATUS in data:
            self._drstatus_active = data[ATTR_DRSTATUS][ATTR_DRACTIVE]
            self._drstatus_optout = data[ATTR_DRSTATUS][ATTR_OPTOUT]
            self._drstatus_onoff = data[ATTR_DRSTATUS][ATTR_ONOFF]
            self._drstatus_optout_reason = data[ATTR_DRSTATUS]["optOutReason"]
        self._water_temp_min = data[ATTR_WATER_TEMP_MIN]
        self._water_temp_protect = data[ATTR_WATER_TEMP_PROTECT]
        self._watt_time_on = data[ATTR_WATT_TIME_ON]
        self._water_temp_time = data[ATTR_DR_WATER_TEMP_TIME]
        if ATTR_DR_PROTEC_STATUS in data:
            self._temperature = data[ATTR_DR_PROTEC_STATUS]["temperature"]
            self._consumption = data[ATTR_DR_PROTEC_STATUS]["consumption"]
            self._consumption_time = data[ATTR_DR_PROTEC_STATUS]["consumptionOverTime"]

    def update(self):
        """Get the latest data from Neviweb and update the state."""
        if not self._active:
            self._handle_snooze()
            return
        start = time.time()
        device_data = self._fetch_attributes(UPDATE_ATTRIBUTES + self._TANK_LOAD_ATTRIBUTES)
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
                "onOff": self._onoff,
                "wattage": self._wattage,
                "wattage_instant": self._current_power_w,
                "total_kwh_count": self._total_kwh_count,
                "monthly_kwh_count": self._monthly_kwh_count,
                "daily_kwh_count": self._daily_kwh_count,
                "hourly_kwh_count": self._hourly_kwh_count,
                "hourly_kwh": self._hour_kwh,
                "daily_kwh": self._today_kwh,
                "monthly_kwh": self._month_kwh,
                "last_energy_stat_update": self._mark,
                "water_leak_status": self._water_leak_status,
                "water_temperature": self._water_temp,
                "cold_load_pickup_status": self._cold_load_status,
                "cold_load_remaining_time": remaining_time(self._cold_load_remaining_time),
                "tank_size": neviweb_to_ha(self._tank_size),
                "eco_status": self._drstatus_active,
                "eco_optOut": self._drstatus_optout,
                "eco_onoff": self._drstatus_onoff,
                "eco_optout_reason": self._drstatus_optout_reason,
                "water_temp_min": self._water_temp_min,
                "water_time_on": self._watt_time_on,
                "water_temp_time": self._water_temp_time,
                "water_temp_protection_type": self._water_temp_protect,
                "protection_Temperature": self._temperature,
                "protection_Consumption": self._consumption,
                "protection_consumption_overtime": self._consumption_time,
                "error_code": self._error_code,
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


class Neviweb130WifiTankPowerSwitch(Neviweb130Switch):
    """Implementation of a Neviweb Wi-Fi power controller switch, RM3500WF."""

    def __init__(self, device_info, name, sku, firmware, device_type, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, device_type, client)
        self._away_action = None
        self._away_payload = None
        self._cold_load_status = None
        self._cold_load_temp = None
        self._drstatus_power_abs = "off"
        self._drstatus_power_rel = "off"
        self._drstatus_setpoint = "off"
        self._error_code = None
        self._leg_status_consumption = None
        self._leg_status_over_time = None
        self._leg_status_temp = None
        self._mode = None
        self._rssi = None
        self._water_leak_closure_conf = None
        self._water_leak_disconnected_status = None
        self._water_leak_status = None
        self._water_tank_on = None
        self._water_temp = None
        self._water_temp_protect = None
        self._water_temp_time = None
        self._wattage = 0

    _WIFI_TANK_LOAD_ATTRIBUTES = [
        ATTR_WATER_LEAK_ALARM_STATUS,
        ATTR_WATER_TEMPERATURE,
        ATTR_WATER_LEAK_DISCONNECTED_STATUS,
        ATTR_ERROR_CODE_SET1,
        ATTR_WIFI_WATTAGE,
        ATTR_WIFI_WATT_NOW,
        ATTR_COLD_LOAD_PICKUP_STATUS,
        ATTR_TANK_SIZE,
        ATTR_MIN_WATER_TEMP,
        ATTR_WATER_TANK_ON,
        ATTR_WATER_TEMP_TIME,
        ATTR_WIFI,
        ATTR_DRSTATUS,
        ATTR_LEG_PROTEC_STATUS,
        ATTR_COLD_LOAD_PICKUP_REMAIN_TIME,
        ATTR_SYSTEM_MODE,
        ATTR_COLD_LOAD_PICKUP_TEMP,
        ATTR_LEAK_CLOSURE_CONFIG,
        ATTR_AWAY_ACTION,
        ATTR_WATER_TEMP_PROTECT,
    ]

    def _parse_common_state(self, data: dict) -> None:
        """Assign state fields from device data for Wi-Fi tank power switch."""
        self._onoff = data[ATTR_ONOFF]
        self._water_leak_status = data[ATTR_WATER_LEAK_ALARM_STATUS]
        if data[ATTR_WATER_LEAK_DISCONNECTED_STATUS] == "probe":
            code = data[ATTR_WATER_LEAK_DISCONNECTED_STATUS]
            self.notify_ha(
                translated_or_default(
                    self.hass, "error_code",
                    f"Warning: Neviweb Device error code detected: {code} for \n"
                    f"device: {self._name}, ID: {self._id}, Sku: {self._sku}.\n"
                    f"{'Leak sensor disconnected'}",
                    code=code, message="Leak sensor disconnected",
                    name=self._name, id=self._id, sku=self._sku,
                )
            )
        else:
            self._water_leak_disconnected_status = data[ATTR_WATER_LEAK_DISCONNECTED_STATUS]
        self._water_temp = data[ATTR_WATER_TEMPERATURE]
        if ATTR_ERROR_CODE_SET1 in data and len(data[ATTR_ERROR_CODE_SET1]) > 0:
            if data[ATTR_ERROR_CODE_SET1]["raw"] != 0:
                self._error_code = data[ATTR_ERROR_CODE_SET1]["raw"]
                message = None
                match self._error_code:
                    case 32:
                        message = "Temperature sensor disconnected"
                    case 64:
                        message = "Leak sensor disconnected"
                code = str(data[ATTR_ERROR_CODE_SET1]["raw"])
                self.notify_ha(
                    translated_or_default(
                        self.hass, "error_code",
                        f"Warning: Neviweb Device error code detected: {code} for \n"
                        f"device: {self._name}, ID: {self._id}, Sku: {self._sku}.\n{message}",
                        code=code, message=message, name=self._name, id=self._id, sku=self._sku,
                    )
                )
        else:
            self._error_code = 0
        if ATTR_DRSTATUS in data:
            self._drstatus_active = data[ATTR_DRSTATUS][ATTR_DRACTIVE]
            self._drstatus_optout = data[ATTR_DRSTATUS][ATTR_OPTOUT]
            self._drstatus_onoff = data[ATTR_DRSTATUS][ATTR_ONOFF]
            self._drstatus_power_abs = data[ATTR_DRSTATUS]["powerAbsolute"]
            self._drstatus_power_rel = data[ATTR_DRSTATUS]["powerRelative"]
            self._drstatus_setpoint = data[ATTR_DRSTATUS]["setpoint"]
        self._current_power_w = data[ATTR_WIFI_WATT_NOW]["value"]
        self._wattage = data[ATTR_WIFI_WATTAGE]["value"]
        self._cold_load_status = data[ATTR_COLD_LOAD_PICKUP_STATUS]
        self._cold_load_temp = data[ATTR_COLD_LOAD_PICKUP_TEMP]
        self._cold_load_remaining_time = data[ATTR_COLD_LOAD_PICKUP_REMAIN_TIME]
        self._rssi = data[ATTR_WIFI]
        self._mode = data[ATTR_SYSTEM_MODE]
        self._tank_size = data[ATTR_TANK_SIZE]
        self._away_action = data[ATTR_AWAY_ACTION]["action"]
        self._away_payload = data[ATTR_AWAY_ACTION]["actionPayload"]
        self._leg_status_temp = data[ATTR_LEG_PROTEC_STATUS]["temperature"]
        self._leg_status_consumption = data[ATTR_LEG_PROTEC_STATUS]["consumption"]
        self._leg_status_over_time = data[ATTR_LEG_PROTEC_STATUS]["consumptionOverTime"]
        self._water_temp_min = data[ATTR_MIN_WATER_TEMP]
        self._water_tank_on = data[ATTR_WATER_TANK_ON]
        self._water_temp_time = data[ATTR_WATER_TEMP_TIME]
        self._water_temp_protect = data[ATTR_WATER_TEMP_PROTECT]
        self._water_leak_closure_conf = data[ATTR_LEAK_CLOSURE_CONFIG]

    def update(self):
        """Get the latest data from Neviweb and update the state."""
        if not self._active:
            self._handle_snooze()
            return
        start = time.time()
        device_data = self._fetch_attributes(UPDATE_ATTRIBUTES + self._WIFI_TANK_LOAD_ATTRIBUTES)
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
                "onOff": self._onoff,
                "wattage": self._wattage,
                "wattage_instant": self._current_power_w,
                "total_kwh_count": self._total_kwh_count,
                "monthly_kwh_count": self._monthly_kwh_count,
                "daily_kwh_count": self._daily_kwh_count,
                "hourly_kwh_count": self._hourly_kwh_count,
                "hourly_kwh": self._hour_kwh,
                "daily_kwh": self._today_kwh,
                "monthly_kwh": self._month_kwh,
                "last_energy_stat_update": self._mark,
                "water_leak_status": self._water_leak_status,
                "water_leak_disconect_status": self._water_leak_disconnected_status,
                "water_leak_closure_config": self._water_leak_closure_conf,
                "water_temperature": self._water_temp,
                "cold_load_pickup_status": self._cold_load_status,
                "cold_load_remaining_time": remaining_time(self._cold_load_remaining_time),
                "cold_load_temperature": self._cold_load_temp,
                "tank_size": neviweb_to_ha(self._tank_size),
                "eco_status": self._drstatus_active,
                "eco_optOut": self._drstatus_optout,
                "eco_onoff": self._drstatus_onoff,
                "eco_setpoint": self._drstatus_setpoint,
                "eco_power_absolute": self._drstatus_power_abs,
                "eco_power_relative": self._drstatus_power_rel,
                "water_temp_min": self._water_temp_min,
                "water_time_on": self._water_tank_on,
                "water_temp_time": self._water_temp_time,
                "water_temp_protection_type": self._water_temp_protect,
                "away_action": self._away_action,
                "away_action_payload": self._away_payload,
                "mode": self._mode,
                "leg_status_temperature": self._leg_status_temp,
                "leg_status_consumption": self._leg_status_consumption,
                "leg_status_consumption_over_time": self._leg_status_over_time,
                "error_code": self._error_code,
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


class Neviweb130ControlerSwitch(Neviweb130Switch):
    """Implementation of a Neviweb multi controller switch, MC3100ZB connected to GT130 or Sedna."""

    def __init__(self, device_info, name, sku, firmware, device_type, client):
        """Initialize."""
        super().__init__(device_info, name, sku, firmware, device_type, client)
        self._batt_info = None
        self._batt_percent_normal = None
        self._batt_status_normal = None
        self._battery_status = None
        self._ext_temp = None
        self._humidity = None
        self._input2_status = None
        self._input_status = None
        self._low_temp_status = None
        self._rssi = None

    def _build_attributes(self) -> list:
        """Build the attribute list based on device type and firmware."""
        name_attrs = [ATTR_NAME_1, ATTR_NAME_2, ATTR_OUTPUT_NAME_1, ATTR_OUTPUT_NAME_2] if self._is_zb_control else [ATTR_NAME_1, ATTR_OUTPUT_NAME_1]
        if self._is_zb_control:
            if self._firmware == "0.1.1":
                load_attrs = [
                    ATTR_ONOFF2, ATTR_BATTERY_VOLTAGE, ATTR_BATTERY_STATUS, ATTR_EXT_TEMP,
                    ATTR_REL_HUMIDITY, ATTR_INPUT_STATUS, ATTR_INPUT2_STATUS, ATTR_ROOM_TEMPERATURE,
                    ATTR_TIMER, ATTR_TIMER2, ATTR_RSSI, ATTR_BATT_INFO, ATTR_INPUT_1_ON_DELAY,
                    ATTR_INPUT_2_ON_DELAY, ATTR_INPUT_1_OFF_DELAY, ATTR_INPUT_2_OFF_DELAY,
                    ATTR_BATT_PERCENT_NORMAL, ATTR_BATT_STATUS_NORMAL, ATTR_DRSTATUS,
                    ATTR_TEMP_ALERT, ATTR_LOW_TEMP_STATUS,
                ]
            else:
                load_attrs = [
                    ATTR_ONOFF2, ATTR_BATTERY_VOLTAGE, ATTR_BATTERY_STATUS, ATTR_EXT_TEMP,
                    ATTR_REL_HUMIDITY, ATTR_INPUT_STATUS, ATTR_INPUT2_STATUS, ATTR_ROOM_TEMPERATURE,
                    ATTR_TIMER, ATTR_TIMER2, ATTR_RSSI,
                ]
        else:
            load_attrs = [ATTR_INPUT_STATUS, ATTR_BATTERY_VOLTAGE, ATTR_BATT_INFO]
        return UPDATE_ATTRIBUTES + load_attrs + name_attrs

    def _parse_common_state(self, data: dict) -> None:
        """Assign state fields from device data for controller switch."""
        if self._is_zb_control or self._is_sedna_control:
            self._onoff = data[ATTR_ONOFF]
            self._input_status = data[ATTR_INPUT_STATUS]
            self._battery_voltage = data[ATTR_BATTERY_VOLTAGE]
            if ATTR_BATT_INFO in data:
                self._batt_info = data[ATTR_BATT_INFO]
            self._input_name_1 = data[ATTR_NAME_1]
            self._output_name_1 = data[ATTR_OUTPUT_NAME_1]
        if self._is_zb_control:
            self._onoff2 = data[ATTR_ONOFF2]
            self._battery_status = data[ATTR_BATTERY_STATUS]
            self._input2_status = data[ATTR_INPUT2_STATUS]
            self._humidity = data[ATTR_REL_HUMIDITY]
            self._room_temp = data[ATTR_ROOM_TEMPERATURE]
            self._ext_temp = data[ATTR_EXT_TEMP]
            self._timer = data[ATTR_TIMER]
            self._timer2 = data[ATTR_TIMER2]
            if ATTR_INPUT_1_ON_DELAY in data:
                self._input_1_on_delay = data[ATTR_INPUT_1_ON_DELAY]
                self._input_2_on_delay = data[ATTR_INPUT_2_ON_DELAY]
                self._input_1_off_delay = data[ATTR_INPUT_1_OFF_DELAY]
                self._input_2_off_delay = data[ATTR_INPUT_2_OFF_DELAY]
            if ATTR_BATT_PERCENT_NORMAL in data:
                self._batt_percent_normal = data[ATTR_BATT_PERCENT_NORMAL]
            if ATTR_BATT_STATUS_NORMAL in data:
                self._batt_status_normal = data[ATTR_BATT_STATUS_NORMAL]
            if ATTR_RSSI in data:
                self._rssi = data[ATTR_RSSI]
            if ATTR_TEMP_ALERT in data:
                self._temp_alert = data[ATTR_TEMP_ALERT]
            if ATTR_LOW_TEMP_STATUS in data:
                self._low_temp_status = data[ATTR_LOW_TEMP_STATUS]
            self._input_name_2 = data[ATTR_NAME_2]
            self._output_name_2 = data[ATTR_OUTPUT_NAME_2]
            if ATTR_DRSTATUS in data:
                self._drstatus_active = data[ATTR_DRSTATUS][ATTR_DRACTIVE]
                self._drstatus_onoff = data[ATTR_DRSTATUS][ATTR_ONOFF]

    def update(self):
        """Get the latest data from Neviweb and update the state."""
        if not self._active:
            self._handle_snooze()
            return
        start = time.time()
        device_data = self._fetch_attributes(self._build_attributes())
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
                "onOff": self._onoff,
                "input1_status": self._input_status,
                "battery_voltage": self._battery_voltage,
                "battery_display_info": self._batt_info,
                "input1_name": self._input_name_1,
                "output1_name": self._output_name_1,
            }
        )
        if self._is_zb_control:
            data.update(
                {
                    "battery_level": voltage_to_percentage(self._battery_voltage, 2),
                    "battery_status": self._battery_status,
                    "battery_percent_normalized": self._batt_percent_normal,
                    "battery_status_normalized": self._batt_status_normal,
                    "extern_temperature": self._ext_temp,
                    "room_temperature": self._room_temp,
                    "room_humidity": self._humidity,
                    "timer": self._timer,
                    "timer2": self._timer2,
                    "input2_status": self._input2_status,
                    "onOff2": self._onoff2,
                    "eco_status": self._drstatus_active,
                    "eco_onOff": self._drstatus_onoff,
                    "input1_on_delay": neviweb_to_ha_delay(self._input_1_on_delay),
                    "input2_on_delay": neviweb_to_ha_delay(self._input_2_on_delay),
                    "input1_off_delay": neviweb_to_ha_delay(self._input_1_off_delay),
                    "input2_off_delay": neviweb_to_ha_delay(self._input_2_off_delay),
                    "input2_name": self._input_name_2,
                    "output2_name": self._output_name_2,
                    "temp_alert": "active" if self._temp_alert == 5 else "inactive",
                    "low_temp_status": self._low_temp_status,
                    "rssi": self._rssi,
                }
            )
        data.update(
            {
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
