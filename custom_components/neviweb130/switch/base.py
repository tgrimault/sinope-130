"""Neviweb130Switch base class."""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone
from typing import Any, override

from homeassistant.components.persistent_notification import DOMAIN as PN_DOMAIN
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.sensor import SensorStateClass
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity

from .. import NOTIFY
from .. import SCAN_INTERVAL as scan_interval
from .. import STAT_INTERVAL
from ..const import (
    ATTR_ACTIVE,
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
    ATTR_DELAY,
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
    ATTR_INPUT_NUMBER,
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
    ATTR_ONOFF_NUM,
    ATTR_OPTOUT,
    ATTR_OUTPUT_NAME_1,
    ATTR_OUTPUT_NAME_2,
    ATTR_REL_HUMIDITY,
    ATTR_ROOM_TEMPERATURE,
    ATTR_RSSI,
    ATTR_STATUS,
    ATTR_SYSTEM_MODE,
    ATTR_TANK_SIZE,
    ATTR_TEMP_ALERT,
    ATTR_TIME,
    ATTR_TIMER,
    ATTR_TIMER2,
    ATTR_VALUE,
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
    DOMAIN,
    MODE_OFF,
    STATE_KEYPAD_STATUS,
    STATE_WATER_LEAK,
    VERSION,
)
from ..helpers import safe_get_device_attributes, translated_or_default

_LOGGER = logging.getLogger(__name__)

SNOOZE_TIME = 1200
SCAN_INTERVAL = scan_interval

UPDATE_ATTRIBUTES = [ATTR_ONOFF]

HA_TO_NEVIWEB_SIZE = {"40 gal": 40, "50 gal": 50, "60 gal": 60, "80 gal": 80}

HA_TO_NEVIWEB_DELAY = {
    "off": 0,
    "1 min": 60,
    "2 min": 120,
    "5 min": 300,
    "10 min": 600,
    "15 min": 900,
    "30 min": 1800,
    "45 min": 2700,
    "60 min": 3600,
    "75 min": 4500,
    "90 min": 5400,
    "1 h": 3600,
    "2 h": 7200,
    "3 h": 10800,
    "6 h": 21600,
    "12 h": 43200,
    "24 h": 86400,
}

HA_TO_NEVIWEB_CONTROLLED = {
    "Hot water heater": "hotWaterHeater",
    "Pool pump": "poolPump",
    "Electric vehicle charger": "electricVehicleCharger",
    "Other": "other",
}

SWITCH_TYPES: dict[str, tuple[str, SwitchDeviceClass]] = {
    "power": ("mdi:switch", SwitchDeviceClass.SWITCH),
    "outlet": ("mdi:power-plug", SwitchDeviceClass.OUTLET),
    "control": ("mdi:alarm", SwitchDeviceClass.SWITCH),
}

IMPLEMENTED_WIFI_WATER_HEATER_LOAD_MODEL = [2152, 339]
IMPLEMENTED_WATER_HEATER_LOAD_MODEL = [2151]
IMPLEMENTED_ZB_DEVICE_CONTROL = [2180]
IMPLEMENTED_SED_DEVICE_CONTROL = [2181]
IMPLEMENTED_WALL_DEVICES = [2600, 2610]
IMPLEMENTED_SED_WALL_DEVICES = [26002, 26102]
IMPLEMENTED_LOAD_DEVICES = [2506]
IMPLEMENTED_SED_LOAD_DEVICES = [25062]
IMPLEMENTED_WIFI_LOAD_DEVICES = [346]
IMPLEMENTED_DEVICE_MODEL = (
    IMPLEMENTED_LOAD_DEVICES
    + IMPLEMENTED_SED_LOAD_DEVICES
    + IMPLEMENTED_WALL_DEVICES
    + IMPLEMENTED_SED_WALL_DEVICES
    + IMPLEMENTED_ZB_DEVICE_CONTROL
    + IMPLEMENTED_SED_DEVICE_CONTROL
    + IMPLEMENTED_WATER_HEATER_LOAD_MODEL
    + IMPLEMENTED_WIFI_WATER_HEATER_LOAD_MODEL
    + IMPLEMENTED_WIFI_LOAD_DEVICES
)


def voltage_to_percentage(voltage, num):
    """Convert voltage level from volt to percentage."""
    if num == 2:
        return int((min(voltage, 2.7) - 2.3) / (2.7 - 2.3) * 100)
    else:
        return int((min(voltage, 6.0) - 3.0) / (6.0 - 3.0) * 100)


def neviweb_to_ha(value):
    keys = [k for k, v in HA_TO_NEVIWEB_SIZE.items() if v == value]
    if keys:
        return keys[0]
    return None


def neviweb_to_ha_controlled(value):
    keys = [k for k, v in HA_TO_NEVIWEB_CONTROLLED.items() if v == value]
    if keys:
        return keys[0]
    return None


def neviweb_to_ha_delay(value):
    keys = [k for k, v in HA_TO_NEVIWEB_DELAY.items() if v == value]
    if keys:
        return keys[0]
    return None


def trigger_close(action, alarm):
    """ "No action", "Close and send", "Close only", "Send only." """
    if action:
        if alarm:
            return "Close and send"
        else:
            return "Close only"
    else:
        if alarm:
            return "Send only"
        else:
            return "No action"


def L_2_sqm(value):
    """Convert liters valuer to cubic meter for water flow stat."""
    if value is not None:
        return value / 1000
    else:
        return None


def model_to_HA(value):
    if value == 9887:
        return "FS4221"
    elif value == 4546:
        return "FS4220"
    else:
        return "No flow meter"


def lock_to_ha(lock):
    """Convert keypad lock state to better description."""
    match lock:
        case "locked":
            return "Locked"
        case "lock":
            return "Locked"
        case "unlocked":
            return "Unlocked"
        case "unlock":
            return "Unlocked"
        case "partiallyLocked":
            return "Tamper protection"
        case "partialLock":
            return "Tamper protection"
    return None


def remaining_time(time_val):
    """Convert time countdown for RM3500ZB."""
    if time_val == 65535:
        return "off"
    return time_val


class Neviweb130Switch(SwitchEntity):
    """Implementation of a Neviweb switch, SP2600ZB and SP2610ZB."""

    def __init__(self, device_info, name, sku, firmware, device_type, client):
        """Initialize."""
        _LOGGER.debug("Setting up %s: %s", name, device_info)
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_unit_class = "energy"
        self._attr_statistic_mean_type = StatisticMeanType.ARITHMETIC

        self._name = name
        self._sku = sku
        self._firmware = firmware
        self._client = client
        self._id = str(device_info["id"])
        self._device_model = device_info["signature"]["model"]
        self._device_model_cfg = device_info["signature"]["modelCfg"]
        self._device_type = device_type
        self._is_wall = device_info["signature"]["model"] in IMPLEMENTED_WALL_DEVICES
        self._is_sedna_wall = device_info["signature"]["model"] in IMPLEMENTED_SED_WALL_DEVICES
        self._is_load = device_info["signature"]["model"] in IMPLEMENTED_LOAD_DEVICES
        self._is_wifi_load = device_info["signature"]["model"] in IMPLEMENTED_WIFI_LOAD_DEVICES
        self._is_sedna_load = device_info["signature"]["model"] in IMPLEMENTED_SED_LOAD_DEVICES
        self._is_tank_load = device_info["signature"]["model"] in IMPLEMENTED_WATER_HEATER_LOAD_MODEL
        self._is_wifi_tank_load = device_info["signature"]["model"] in IMPLEMENTED_WIFI_WATER_HEATER_LOAD_MODEL
        self._is_zb_control = device_info["signature"]["model"] in IMPLEMENTED_ZB_DEVICE_CONTROL
        self._is_sedna_control = device_info["signature"]["model"] in IMPLEMENTED_SED_DEVICE_CONTROL
        self._active = True
        self._battery_voltage = 0
        self._cold_load_remaining_time = 0
        self._controlled_device = None
        self._cur_temp = None
        self._current_power_w = 0
        self._daily_kwh_count = 0
        self._drstatus_active = "off"
        self._drstatus_onoff = "off"
        self._drstatus_optout = "off"
        self._energy_stat_time = time.time() - 1500
        self._hour_kwh = 0
        self._hourly_kwh_count = 0
        self._input_1_off_delay = 0
        self._input_1_on_delay = 0
        self._input_2_off_delay = 0
        self._input_2_on_delay = 0
        self._input_name_1 = "Not set"
        self._input_name_2 = "Not set"
        self._keypad = None
        self._mark = 0
        self._marker: int | None = None
        self._month_kwh = 0
        self._monthly_kwh_count = 0
        self._onoff = None
        self._onoff2 = None
        self._output_name_1 = "Not set"
        self._output_name_2 = "Not set"
        self._room_temp = None
        self._snooze = 0.0
        self._tank_size = None
        self._temp_alert = None
        self._timer = 0
        self._timer2 = 0
        self._today_kwh = 0
        self._total_kwh_count = 0
        self._water_temp_min = None

    # ------------------------------------------------------------------
    # Private helpers — update() decomposition
    # ------------------------------------------------------------------

    def _fetch_attributes(self, attributes: list) -> dict:
        """Fetch device attributes, using safe mode when configured."""
        from custom_components.neviweb130.switch import safe_get_device_attributes as _safe_get
        safe_mode = self.hass.data[DOMAIN]["safe_mode"]
        if safe_mode == self._id:
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

    def _parse_common_state(self, data: dict) -> None:
        """Assign common state fields from device data."""
        self._onoff = data[ATTR_ONOFF]
        if self._is_wall:
            self._current_power_w = data[ATTR_WATTAGE_INSTANT]

    def _handle_error(self, device_data: dict) -> bool:
        """Handle API error in device_data. Returns True if an error was found."""
        if "error" in device_data:
            self.log_error(device_data["error"]["code"])
            return True
        if "errorCode" in device_data:
            _LOGGER.warning("Error reading device %s: (%s)", self._name, device_data)
            return True
        return False

    def _handle_snooze(self) -> None:
        """Re-activate polling after snooze period expires."""
        if time.time() - self._snooze > SNOOZE_TIME:
            self._active = True
            if NOTIFY == "notification" or NOTIFY == "both":
                self.notify_ha(
                    translated_or_default(
                        self.hass,
                        "update_restarted",
                        f"Warning: Neviweb Device update restarted for {self._name}, Sku: {self._sku}.",
                        name=self._name,
                        sku=self._sku,
                    )
                )

    def update(self):
        """Get the latest data from Neviweb and update the state."""
        if not self._active:
            self._handle_snooze()
            return
        load_attributes = [ATTR_WATTAGE_INSTANT] if self._is_wall else []
        start = time.time()
        device_data = self._fetch_attributes(UPDATE_ATTRIBUTES + load_attributes)
        elapsed = round(time.time() - start, 3)
        _LOGGER.debug("Updating %s (%s sec): %s", self._name, elapsed, device_data)
        if not self._handle_error(device_data):
            self._parse_common_state(device_data)
        if self._is_wall:
            self.do_stat(start)

    @property
    @override
    def unique_id(self) -> str:
        """Return unique ID based on Neviweb device ID."""
        return self._client.scoped_unique_id(self._id)

    @property
    @override
    def name(self) -> str:
        """Return the name of the switch."""
        return self._name

    @property
    @override
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        device_info = SWITCH_TYPES.get(self._device_type)
        if device_info is None:
            return None
        return device_info[0]

    @property
    @override
    def device_class(self) -> SwitchDeviceClass | None:
        """Return the device class of this entity."""
        device_info = SWITCH_TYPES.get(self._device_type)
        if device_info is None:
            return None
        return device_info[1]

    @property
    def is_on(self):
        """Return current operation i.e. ON, OFF."""
        return self._onoff != MODE_OFF

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self._client.set_onoff(self._id, "on")
        self._onoff = "on"

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self._client.set_onoff(self._id, "off")
        self._onoff = MODE_OFF

    @property
    def keypad_status(self):
        """Return current keypad status."""
        if self._keypad is not None:
            return lock_to_ha(self._keypad)
        return False

    @property
    def current_temperature(self):
        """Return the current controller temperature."""
        if self._is_zb_control or self._is_sedna_control or self._is_tank_load:
            return self._room_temp
        else:
            return self._cur_temp

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes."""
        data = {}
        data.update({"onOff": self._onoff})
        if self._is_wall:
            data.update(
                {
                    "wattage_instant": self._current_power_w,
                    "total_kwh_count": self._total_kwh_count,
                    "monthly_kwh_count": self._monthly_kwh_count,
                    "daily_kwh_count": self._daily_kwh_count,
                    "hourly_kwh_count": self._hourly_kwh_count,
                    "hourly_kwh": self._hour_kwh,
                    "daily_kwh": self._today_kwh,
                    "monthly_kwh": self._month_kwh,
                    "last_energy_stat_update": self._mark,
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

    @property
    def battery_voltage(self):
        """Return the current battery voltage of the controller in %."""
        return voltage_to_percentage(self._battery_voltage, 2 if self._is_zb_control or self._is_sedna_control else 4)

    @property
    def is_standby(self):
        """Return true if device is in standby."""
        return self._current_power_w == 0

    def set_control_onoff(self, value):
        """Set onOff or onOff2 to on or off."""
        self._client.set_control_onoff(value["id"], value["onoff_num"], value["status"])
        if value["onoff_num"] == 1:
            self._onoff = value["status"]
        else:
            self._onoff2 = value["status"]

    def set_keypad_lock(self, value):
        """Lock or unlock device's keypad."""
        if self._is_wifi_load or self._is_wifi_tank_load:
            self._client.set_keypad_lock(value["id"], value["lock"], True)
        else:
            self._client.set_keypad_lock(value["id"], value["lock"], False)
        self._keypad = value["lock"]

    def set_timer(self, value):
        """Set device timer, 0 = off, 1 to 255 = timer length."""
        self._client.set_timer(value["id"], value[ATTR_TIME])
        self._timer = value[ATTR_TIME]

    def set_timer2(self, value):
        """Set device timer 2 for Multi controller."""
        self._client.set_timer2(value["id"], value[ATTR_TIME])
        self._timer2 = value[ATTR_TIME]

    def set_temp_alert(self, value):
        """Set low temperature alert on/off for MC3100ZB."""
        self._client.set_switch_temp_alert(value["id"], value["alert"])
        self._temp_alert = value["alert"]

    def set_load_dr_options(self, value):
        """Set load controller Éco Sinopé attributes."""
        self._client.set_load_dr_options(value["id"], value["onoff"], value["droptout"], value["dractive"])
        self._drstatus_active = value["dractive"]
        self._drstatus_optout = value["droptout"]
        self._drstatus_onoff = value["onoff"]

    def set_tank_size(self, value):
        """Set water tank size for RM3500ZB Calypso controller."""
        val = value["val"]
        size = [v for k, v in HA_TO_NEVIWEB_SIZE.items() if k == val][0]
        self._client.set_tank_size(value["id"], size)
        self._tank_size = size

    def set_controlled_device(self, value):
        """Set device name controlled by RM3250ZB load controller."""
        val = value["val"]
        type_val = [v for k, v in HA_TO_NEVIWEB_CONTROLLED.items() if k == val][0]
        self._client.set_controlled_device(value["id"], type_val)
        self._controlled_device = type_val

    def set_low_temp_protection(self, value):
        """Set water temperature protection for Calypso."""
        self._client.set_low_temp_protection(value["id"], value["val"])
        self._water_temp_min = value["val"]

    def set_activation(self, value):
        """Activate or deactivate neviweb polling for a missing device."""
        self._active = value["active"]

    def set_remaining_time(self, value):
        """Set coldLoadPickupRemainingTime value."""
        self._client.set_remaining_time(value["id"], value[ATTR_TIME])
        self._cold_load_remaining_time = value[ATTR_TIME]

    def set_on_off_input_delay(self, value):
        """Set input 1 or 2 on/off delay in seconds."""
        val = value["delay"]
        delay = [v for k, v in HA_TO_NEVIWEB_DELAY.items() if k == val][0]
        self._client.set_on_off_input_delay(value["id"], delay, value["onoff"], value["input_number"])
        if value["input_number"] == 1:
            match value["onoff"]:
                case "on":
                    self._input_1_on_delay = delay
                case _:
                    self._input_1_off_delay = delay
        else:
            match value["onoff"]:
                case "on":
                    self._input_2_on_delay = delay
                case _:
                    self._input_2_off_delay = delay

    def set_input_output_names(self, value):
        """Set names for input 1 and 2, output 1 and 2 for MC3100ZB device."""
        in_1 = value["input1"] if len(value["input1"]) > 0 else ""
        in_2 = value["input2"] if len(value["input2"]) > 0 else ""
        out_1 = value["output1"] if len(value["output1"]) > 0 else ""
        out_2 = value["output2"] if len(value["output2"]) > 0 else ""
        self._client.set_input_output_names(value["id"], in_1, in_2, out_1, out_2)
        self._input_name_1 = in_1
        self._input_name_2 = in_2
        self._output_name_1 = out_1
        self._output_name_2 = out_2

    def do_stat(self, start):
        """Get device energy statistic."""
        if start - self._energy_stat_time > STAT_INTERVAL and self._energy_stat_time != 0:
            today = date.today()
            current_month = today.month
            current_day = today.day
            device_monthly_stats = self._client.get_device_monthly_stats(self._id, False)
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
                        f"Got None for device monthly stats for device {self._name}.",
                        param="monthly",
                        name=self._name,
                    )
                )
            device_daily_stats = self._client.get_device_daily_stats(self._id, False)
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
                        f"Got None for device daily stats for device {self._name}.",
                        param="daily",
                        name=self._name,
                    )
                )
            device_hourly_stats = self._client.get_device_hourly_stats(self._id, False)
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
                        f"Got None for device hourly stats for device {self._name}.",
                        param="hourly",
                        name=self._name,
                    )
                )
            if self._total_kwh_count == 0:
                self._total_kwh_count = round(
                    self._monthly_kwh_count + self._daily_kwh_count + self._hourly_kwh_count,
                    3,
                )
                self._mark = self._marker if self._marker is not None else 0
            else:
                if self._marker != self._mark:
                    self._total_kwh_count += round(self._hour_kwh, 3)
                    self._mark = self._marker if self._marker is not None else 0
            self._energy_stat_time = time.time()
        if self._energy_stat_time == 0:
            self._energy_stat_time = start

    def log_error(self, error_data):
        """Send error message to LOG."""
        if error_data == "USRSESSEXP":
            _LOGGER.warning("Session expired... Reconnecting...")
            if NOTIFY == "notification" or NOTIFY == "both":
                self.notify_ha(
                    "Warning: Got USRSESSEXP error, Neviweb session expired. "
                    "Set your scan_interval parameter to less than 10 minutes to avoid this... Reconnecting..."
                )
            self._client.reconnect()
        elif error_data == "ACCDAYREQMAX":
            _LOGGER.warning("Maximum daily request reached... Reduce polling frequency")
        elif error_data == "TimeoutError":
            _LOGGER.warning("Timeout error detected... Retry later")
        elif error_data == "MAINTENANCE":
            _LOGGER.warning("Access blocked for maintenance... Retry later")
            self.notify_ha("Warning: Neviweb access temporary blocked for maintenance... Retry later")
            self._client.reconnect()
        elif error_data == "ACCSESSEXC":
            _LOGGER.warning("Maximum session number reached... Close other connections and try again")
            self.notify_ha("Warning: Maximum Neviweb session number reached... Close other connections and try again")
            self._client.reconnect()
        elif error_data == "DVCATTRNSPTD":
            _LOGGER.warning(
                "Device attribute not supported for %s (id: %s): %s... (SKU: %s)",
                self._name, str(self._id), error_data, self._sku,
            )
            safe_mode = self.hass.data[DOMAIN]["safe_mode"]
            if safe_mode == "-":
                _LOGGER.warning(
                    translated_or_default(
                        self.hass,
                        "safe_mode_enabled",
                        (
                            f"Auto-enabling safe mode for device {self._name} (id: {self._id}) "
                            "due to unsupported action."
                        ),
                        name=self._name,
                        id=self._id,
                    )
                )
                self.hass.data[DOMAIN]["safe_mode"] = self._id
        elif error_data == "DVCACTNSPTD":
            _LOGGER.warning(
                "Device action not supported for %s (id: %s)... (SKU: %s), (Model: %s). Report to maintainer",
                self._name, str(self._id), self._sku, str(self._device_model),
            )
        elif error_data == "DVCCOMMTO":
            _LOGGER.warning(
                "Device Communication Timeout for %s (id: %s)... The device "
                "did not respond to the server within the prescribed delay (SKU: %s)",
                self._name, str(self._id), self._sku,
            )
        elif error_data == "SVCERR":
            _LOGGER.warning(
                "Service error, device not available retry later %s (id: %s): %s... (SKU: %s)",
                self._name, str(self._id), error_data, self._sku,
            )
        elif error_data == "DVCBUSY":
            _LOGGER.warning(
                "Device busy can't reach (neviweb update ?), retry later %s (id: %s): %s... (SKU: %s)",
                self._name, str(self._id), error_data, self._sku,
            )
        elif error_data == "DVCUNVLB":
            if NOTIFY == "logging" or NOTIFY == "both":
                _LOGGER.warning(
                    "Device %s (id: %s) is disconnected from Neviweb: %s... (SKU: %s)",
                    self._name, str(self._id), error_data, self._sku,
                )
                _LOGGER.warning("This device %s is de-activated and won't be updated for 20 minutes", self._name)
                _LOGGER.warning(
                    "You can re-activate device %s with service.neviweb130_set_activation or wait 20 minutes "
                    "for update to restart or just restart HA",
                    self._name,
                )
            if NOTIFY == "notification" or NOTIFY == "both":
                self.notify_ha(
                    translated_or_default(
                        self.hass,
                        "update_stopped",
                        (
                            f"Warning: Received message from Neviweb, device disconnected... Check your log...\n"
                            f"Neviweb update will be halted for 20 minutes for {self._name},\n"
                            f"id: {self._id}, Sku: {self._sku}."
                        ),
                        name=self._name,
                        id=self._id,
                        sku=self._sku,
                    )
                )
            self._active = False
            self._snooze = time.time()
        else:
            _LOGGER.warning(
                translated_or_default(
                    self.hass,
                    "unknown_error",
                    (
                        f"Unknown error for {self._name} (id: {self._id}) (SKU: {self._sku}),\n"
                        f"(Model: {self._device_model}). Report to maintainer. Data received: {error_data}."
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
            service_data={"title": title, "message": msg},
            blocking=False,
        )
        return True
