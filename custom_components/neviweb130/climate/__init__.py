"""
Support for Neviweb thermostat connected to GT130 Zigbee.
model 1123 = thermostat TH1123ZB 3000W
model 300 = thermostat TH1123ZB-G2 3000W
model 1124 = thermostat TH1124ZB 4000W
model 300 = thermostat TH1124ZB-G2 4000W
model 737 = thermostat TH1300ZB 3600W (floor)
model 737 = thermostat TH1320ZB-04 (floor)
model 7373 = thermostat TH1500ZB double pole thermostat
model 7372 = thermostat TH1400ZB low voltage
model 7372 = thermostat TH1420ZB-01 Nordik low voltage radiant hydroponic floor thermostat
model 1124 = thermostat OTH4000-ZB Ouellet
model 737 = thermostat OTH3600-GA-ZB Ouellet
model 1512 = Thermostat TH1134ZB-HC for heating/cooling interlocking

Support for Neviweb Wi-Fi thermostats
model 1510 = thermostat TH1123WF 3000W (Wi-Fi)
model 1510 = thermostat TH1124WF 4000W (Wi-Fi)
model 336 = thermostat TH1133WF 3000W (Wi-Fi lite) Three wires connection
model 348 = thermostat TH1133CR Sinopé Evo 3000W (Wi-Fi lite)
model 336 = thermostat TH1134WF 4000W (Wi-Fi lite) three wires connection
model 348 = thermostat TH1134CR Sinopé Evo 4000W (Wi-Fi lite)
model 343 = thermostat THEWF01 (Wi-Fi lite)
model 350 = thermostat TH1143WF 3000W (Wi-Fi) two wires connection, color screen
model 350 = thermostat TH1144WF 4000W (Wi-Fi) two wires connection, color screen
model 350 = thermostat TH1145WF ?  (Wi-Fi) two wires connection, color screen
model 738 = thermostat TH1300WF 3600W, TH1325WF, TH1310WF, SRM40, True Comfort (sku: PS120_240WF)
    (wifi floor), no energy stat for True Comfort
model 739 = thermostat TH1400WF low voltage (Wi-Fi)
model 742 = thermostat TH1500WF double pole thermostat (Wi-Fi)
model 6727 = thermostat TH6500WF heat/cool (Wi-Fi)
model 6727 = thermostat TH6510WF heat/cool (Wi-Fi)
model 6730 = thermostat TH6250WF heat/cool (Wi-Fi)
model 6731 = thermostat TH6250WF-PRO heat/cool (Wi-Fi)

Support for Flextherm Wi-Fi thermostat
model 738 = Thermostat Flextherm concerto connect FLP55 (wifi floor),
    (sku: FLP55), no energy stats

Support for heat pump interfaces
model 6810 = HP6000ZB-GE for Ouellet heat pump with Gree connector
model 6811 = HP6000ZB-MA for Ouellet Convectair heat pump with Midea connector
model 6812 = HP6000ZB-HS for Hisense, Haxxair and Zephyr heat pump

Support for Wi-Fi heat pump interfaces
model 6813 = HP6000WF-MA for Ouellet Convectair heat pump with Midea connector
model 6814 = HP6000WF-TCL for Runtru/Ameristar heat pump
model xxxx = HP6000WF-XX for Hisense, Haxxair and Zephyr heat pump
model xxxx = HP6000WF-XX for Ouellet heat pump with Gree connector

For more details about this platform, please refer to the documentation at
https://www.sinopetech.com/en/support/#api
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone
from threading import Lock
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
    SERVICE_SET_ACCESSORY_TYPE,
    SERVICE_SET_ACTIVATION,
    SERVICE_SET_AIR_FLOOR_MODE,
    SERVICE_SET_AUX_CYCLE_OUTPUT,
    SERVICE_SET_AUX_HEAT_START_DELAY,
    SERVICE_SET_AUX_HEATING_SOURCE,
    SERVICE_SET_AUXILIARY_LOAD,
    SERVICE_SET_BACKLIGHT,
    SERVICE_SET_CLIMATE_KEYPAD_LOCK,
    SERVICE_SET_CLIMATE_NEVIWEB_STATUS,
    SERVICE_SET_COOL_DISSIPATION_TIME,
    SERVICE_SET_COOL_INTERSTAGE_DELAY,
    SERVICE_SET_COOL_LOCKOUT_TEMPERATURE,
    SERVICE_SET_COOL_SETPOINT_AWAY,
    SERVICE_SET_COOL_SETPOINT_MAX,
    SERVICE_SET_COOL_SETPOINT_MIN,
    SERVICE_SET_CYCLE_OUTPUT,
    SERVICE_SET_DISPLAY_CONFIG,
    SERVICE_SET_EARLY_START,
    SERVICE_SET_EM_HEAT,
    SERVICE_SET_FAN_FILTER_REMINDER,
    SERVICE_SET_FAN_SPEED,
    SERVICE_SET_FLOOR_AIR_LIMIT,
    SERVICE_SET_FLOOR_LIMIT_HIGH,
    SERVICE_SET_FLOOR_LIMIT_LOW,
    SERVICE_SET_HC_SECOND_DISPLAY,
    SERVICE_SET_HEAT_DISSIPATION_TIME,
    SERVICE_SET_HEAT_INSTALLATION_TYPE,
    SERVICE_SET_HEAT_INTERSTAGE_DELAY,
    SERVICE_SET_HEAT_LOCKOUT_TEMPERATURE,
    SERVICE_SET_HEAT_PUMP_OPERATION_LIMIT,
    SERVICE_SET_HEATCOOL_SETPOINT_DELTA,
    SERVICE_SET_HUMIDITY_SETPOINT_MODE,
    SERVICE_SET_HVAC_DR_OPTIONS,
    SERVICE_SET_HVAC_DR_SETPOINT,
    SERVICE_SET_LANGUAGE,
    SERVICE_SET_MIN_TIME_OFF,
    SERVICE_SET_MIN_TIME_ON,
    SERVICE_SET_PUMP_PROTECTION,
    SERVICE_SET_REVERSING_VALVE_POLARITY,
    SERVICE_SET_ROOM_SETPOINT_AWAY,
    SERVICE_SET_SCHEDULE_MODE,
    SERVICE_SET_SECOND_DISPLAY,
    SERVICE_SET_SENSOR_TYPE,
    SERVICE_SET_SETPOINT_MAX,
    SERVICE_SET_SETPOINT_MIN,
    SERVICE_SET_SOUND_CONFIG,
    SERVICE_SET_TEMPERATURE_FORMAT,
    SERVICE_SET_TEMPERATURE_OFFSET,
    SERVICE_SET_TIME_FORMAT,
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
    SET_ACCESSORY_TYPE_SCHEMA,
    SET_ACTIVATION_SCHEMA,
    SET_AIR_FLOOR_MODE_SCHEMA,
    SET_AUX_CYCLE_OUTPUT_SCHEMA,
    SET_AUX_HEAT_START_DELAY_SCHEMA,
    SET_AUX_HEATING_SOURCE_SCHEMA,
    SET_AUXILIARY_LOAD_SCHEMA,
    SET_BACKLIGHT_SCHEMA,
    SET_CLIMATE_KEYPAD_LOCK_SCHEMA,
    SET_CLIMATE_NEVIWEB_STATUS_SCHEMA,
    SET_COOL_DISSIPATION_TIME_SCHEMA,
    SET_COOL_INTERSTAGE_DELAY_SCHEMA,
    SET_COOL_LOCKOUT_TEMPERATURE_SCHEMA,
    SET_COOL_SETPOINT_AWAY_SCHEMA,
    SET_COOL_SETPOINT_MAX_SCHEMA,
    SET_COOL_SETPOINT_MIN_SCHEMA,
    SET_CYCLE_OUTPUT_SCHEMA,
    SET_DISPLAY_CONFIG_SCHEMA,
    SET_EARLY_START_SCHEMA,
    SET_EM_HEAT_SCHEMA,
    SET_FAN_FILTER_REMINDER_SCHEMA,
    SET_FAN_SPEED_SCHEMA,
    SET_FLOOR_AIR_LIMIT_SCHEMA,
    SET_FLOOR_LIMIT_HIGH_SCHEMA,
    SET_FLOOR_LIMIT_LOW_SCHEMA,
    SET_HC_SECOND_DISPLAY_SCHEMA,
    SET_HEAT_DISSIPATION_TIME_SCHEMA,
    SET_HEAT_INSTALLATION_TYPE_SCHEMA,
    SET_HEAT_INTERSTAGE_DELAY_SCHEMA,
    SET_HEAT_LOCKOUT_TEMPERATURE_SCHEMA,
    SET_HEAT_PUMP_OPERATION_LIMIT_SCHEMA,
    SET_HEATCOOL_SETPOINT_DELTA_SCHEMA,
    SET_HUMIDITY_SETPOINT_MODE_SCHEMA,
    SET_HVAC_DR_OPTIONS_SCHEMA,
    SET_HVAC_DR_SETPOINT_SCHEMA,
    SET_LANGUAGE_SCHEMA,
    SET_MIN_TIME_OFF_SCHEMA,
    SET_MIN_TIME_ON_SCHEMA,
    SET_PUMP_PROTECTION_SCHEMA,
    SET_REVERSING_VALVE_POLARITY_SCHEMA,
    SET_ROOM_SETPOINT_AWAY_SCHEMA,
    SET_SCHEDULE_MODE_SCHEMA,
    SET_SECOND_DISPLAY_SCHEMA,
    SET_SENSOR_TYPE_SCHEMA,
    SET_SETPOINT_MAX_SCHEMA,
    SET_SETPOINT_MIN_SCHEMA,
    SET_SOUND_CONFIG_SCHEMA,
    SET_TEMPERATURE_FORMAT_SCHEMA,
    SET_TEMPERATURE_OFFSET_SCHEMA,
    SET_TIME_FORMAT_SCHEMA,
    TH6_MODES_VALUES,
    WIFI_FAN_SPEED,
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


def _build_climate_entities(
    gateway_data: list, group_name: str, client: Any
) -> list:
    """Instantiate thermostat entities for one gateway data list."""
    result = []
    for device_info in gateway_data:
        if not (
            "signature" in device_info
            and "model" in device_info["signature"]
            and device_info["signature"]["model"] in IMPLEMENTED_DEVICE_MODEL
        ):
            continue
        device_name = "{} {}".format(group_name, device_info["name"])
        device_sku = device_info["sku"]
        location_id = device_info["location$id"]
        sv = device_info["signature"]["softVersion"]
        device_firmware = "{}.{}.{}".format(sv["major"], sv["middle"], sv["minor"])
        model = device_info["signature"]["model"]
        args = (device_info, device_name, device_sku, device_firmware, location_id, client)
        if model in DEVICE_MODEL_HEAT:
            result.append(Neviweb130Thermostat(*args))
        elif model in DEVICE_MODEL_HEAT_G2:
            result.append(Neviweb130G2Thermostat(*args))
        elif model in DEVICE_MODEL_FLOOR:
            result.append(Neviweb130FloorThermostat(*args))
        elif model in DEVICE_MODEL_LOW:
            result.append(Neviweb130LowThermostat(*args))
        elif model in DEVICE_MODEL_DOUBLE:
            result.append(Neviweb130DoubleThermostat(*args))
        elif model in DEVICE_MODEL_WIFI:
            result.append(Neviweb130WifiThermostat(*args))
        elif model in DEVICE_MODEL_WIFI_LITE:
            result.append(Neviweb130WifiLiteThermostat(*args))
        elif model in DEVICE_MODEL_COLOR_WIFI:
            result.append(Neviweb130ColorWifiThermostat(*args))
        elif model in DEVICE_MODEL_LOW_WIFI:
            result.append(Neviweb130LowWifiThermostat(*args))
        elif model in DEVICE_MODEL_WIFI_FLOOR:
            result.append(Neviweb130WifiFloorThermostat(*args))
        elif model in DEVICE_MODEL_HC:
            result.append(Neviweb130HcThermostat(*args))
        elif model in DEVICE_MODEL_HEAT_PUMP:
            result.append(Neviweb130HPThermostat(*args))
        elif model in DEVICE_MODEL_WIFI_HEAT_PUMP:
            result.append(Neviweb130WifiHPThermostat(*args))
        else:
            result.append(Neviweb130HeatCoolThermostat(*args))  # DEVICE_MODEL_HEAT_COOL
    return result


async def async_setup_platform(
    hass,
    config,
    async_add_entities,
    discovery_info=None,
) -> None:
    """Set up the neviweb130 thermostats."""
    data = hass.data[DOMAIN]["data"]
    await data.migration_done.wait()

    entities: list[Neviweb130Thermostat] = []
    for client in data.neviweb130_clients:
        entities.extend(_build_climate_entities(
            client.gateway_data, client.default_group_name("climate"), client
        ))
        entities.extend(_build_climate_entities(
            client.gateway_data2, client.default_group_name("climate", 2), client
        ))
        entities.extend(_build_climate_entities(
            client.gateway_data3, client.default_group_name("climate", 3), client
        ))

    async_add_entities(entities, True)
    _register_climate_services(hass, entities)


def _register_climate_services(hass: Any, entities: list) -> None:
    """Register all climate services with Home Assistant."""

    entity_map: dict[str, Neviweb130Thermostat] | None = None
    _entity_map_lock = Lock()

    def get_thermostat(service: ServiceCall) -> Neviweb130Thermostat:
        entity_id = service.data.get(ATTR_ENTITY_ID)
        if entity_id is None:
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "missing_parameter",
                    f"Missing required parameter: {ATTR_ENTITY_ID}",
                    param=ATTR_ENTITY_ID,
                )
            )

        nonlocal entity_map
        if entity_map is None:
            with _entity_map_lock:
                if entity_map is None:
                    entity_map = {entity.entity_id: entity for entity in entities if entity.entity_id is not None}
                    if len(entity_map) != len(entities):
                        entity_map = None
                        raise ServiceValidationError(
                            translated_or_default(
                                hass,
                                "entities_not_ready",
                                "Entities are not ready",
                            )
                        )

        thermostat = entity_map.get(entity_id)
        if thermostat is None:
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "entity_must_be_domain",
                    f"Entity '{entity_id}' must be a neviweb130 thermostat",
                    entity=entity_id,
                    domain=DOMAIN,
                    platform="thermostat",
                )
            )
        return thermostat

    def set_second_display_service(service: ServiceCall) -> None:
        """Set to outside or setpoint temperature display for Wi-Fi thermostats."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "display": service.data[ATTR_DISPLAY2],
        }
        thermostat.set_second_display(value)
        thermostat.schedule_update_ha_state(True)

    def set_backlight_service(service: ServiceCall) -> None:
        """Set backlight always on or auto."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "level": service.data[ATTR_BACKLIGHT],
        }
        thermostat.set_backlight(value)
        thermostat.schedule_update_ha_state(True)

    def set_climate_keypad_lock_service(service: ServiceCall) -> None:
        """Lock/unlock keypad device."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "lock": service.data[ATTR_KEYPAD],
        }
        thermostat.set_keypad_lock(value)
        thermostat.schedule_update_ha_state(True)

    def set_time_format_service(service: ServiceCall) -> None:
        """Set time format 12h or 24h."""
        thermostat = get_thermostat(service)
        if isinstance(thermostat, Neviweb130WifiLiteThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "does_not_support",
                    f"Entity '{thermostat.entity_id}' does not support time format (Wi-Fi lite model)",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                    model="Wi-Fi (lite)",
                )
            )
        if isinstance(thermostat, Neviweb130HPThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "does_not_support",
                    f"Entity '{thermostat.entity_id}' does not support time format (Heat-Pump model)",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                    model="Heat-Pump",
                )
            )
        if isinstance(thermostat, Neviweb130WifiHPThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "does_not_support",
                    f"Entity '{thermostat.entity_id}' does not support time format (Wi-Fi Heat-Pump model)",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                    model="Wi-Fi Heat-Pump",
                )
            )

        value = {
            "id": thermostat.unique_id,
            ATTR_TIME: service.data[ATTR_TIME_FORMAT],
        }
        thermostat.set_time_format(value)
        thermostat.schedule_update_ha_state(True)

    def set_temperature_format_service(service: ServiceCall) -> None:
        """Set temperature format, celsius or fahrenheit."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "temp": service.data[ATTR_TEMP],
        }
        thermostat.set_temperature_format(value)
        thermostat.schedule_update_ha_state(True)

    def set_setpoint_max_service(service: ServiceCall) -> None:
        """Set maximum setpoint for device."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "temp": service.data[ATTR_ROOM_SETPOINT_MAX],
        }
        thermostat.set_setpoint_max(value)
        thermostat.schedule_update_ha_state(True)

    def set_setpoint_min_service(service: ServiceCall) -> None:
        """Set minimum setpoint for device."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "temp": service.data[ATTR_ROOM_SETPOINT_MIN],
        }
        thermostat.set_setpoint_min(value)
        thermostat.schedule_update_ha_state(True)

    def set_floor_air_limit_service(service: ServiceCall) -> None:
        """Set minimum setpoint for device."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "temp": service.data[ATTR_FLOOR_AIR_LIMIT],
        }
        thermostat.set_floor_air_limit(value)
        thermostat.schedule_update_ha_state(True)

    def set_early_start_service(service: ServiceCall) -> None:
        """Set early heating on/off for Wi-Fi thermostat."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "start": service.data[ATTR_EARLY_START],
        }
        thermostat.set_early_start(value)
        thermostat.schedule_update_ha_state(True)

    def set_air_floor_mode_service(service: ServiceCall) -> None:
        """Switch between ambient or floor temperature sensor."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "mode": service.data[ATTR_FLOOR_MODE],
        }
        thermostat.set_air_floor_mode(value)
        thermostat.schedule_update_ha_state(True)

    def set_hvac_dr_options_service(service: ServiceCall) -> None:
        """Set options for hvac dr in Eco Sinope."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            value = {
                "id": thermostat.unique_id,
                "dractive": service.data(ATTR_DRACTIVE),
                "optout": service.data(ATTR_OPTOUT),
                "setpoint": service.data(ATTR_SETPOINT),
            }
        else:
            value = {
                "id": thermostat.unique_id,
                ATTR_AUX_OPTIM: service.data.get(ATTR_AUX_OPTIM),
                ATTR_FAN_SPEED_OPTIM: service.data.get(ATTR_FAN_SPEED_OPTIM),
            }
        thermostat.set_hvac_dr_options(value)
        thermostat.schedule_update_ha_state(True)

    def set_hvac_dr_setpoint_service(service: ServiceCall) -> None:
        """Set options for hvac dr setpoint in Eco Sinope."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "status": service.data[ATTR_STATUS],
            "val": service.data[ATTR_VALUE],
        }
        thermostat.set_hvac_dr_setpoint(value)
        thermostat.schedule_update_ha_state(True)

    def set_auxiliary_load_service(service: ServiceCall) -> None:
        """Set options for auxiliary heating."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "status": service.data[ATTR_STATUS],
            "val": service.data[ATTR_VALUE],
        }
        thermostat.set_auxiliary_load(value)
        thermostat.schedule_update_ha_state(True)

    def set_aux_cycle_output_service(service: ServiceCall) -> None:
        """Set options for auxiliary cycle length for low voltage thermostats."""
        thermostat = get_thermostat(service)
        val = service.data.get(ATTR_VALUE)
        if val is None:
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "missing_parameter",
                    f"missing_parameter '{ATTR_VALUE}'",
                    param=ATTR_VALUE,
                )
            )
        value = {
            "id": thermostat.unique_id,
            "val": val,
        }
        thermostat.set_aux_cycle_output(value)
        thermostat.schedule_update_ha_state(True)

    def set_cycle_output_service(service: ServiceCall) -> None:
        """Set options for main cycle length for low voltage thermostats."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "val": service.data[ATTR_VALUE],
        }
        thermostat.set_cycle_output(value)
        thermostat.schedule_update_ha_state(True)

    def set_pump_protection_service(service: ServiceCall) -> None:
        """Set status of pump protection for low voltage thermostats."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "status": service.data[ATTR_STATUS],
        }
        thermostat.set_pump_protection(value)
        thermostat.schedule_update_ha_state(True)

    def set_cool_setpoint_max_service(service: ServiceCall) -> None:
        """Set maximum cooling setpoint for device."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "temp": service.data[ATTR_COOL_SETPOINT_MAX],
        }
        thermostat.set_cool_setpoint_max(value)
        thermostat.schedule_update_ha_state(True)

    def set_cool_setpoint_min_service(service: ServiceCall) -> None:
        """Set minimum cooling setpoint for device."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "temp": service.data[ATTR_COOL_SETPOINT_MIN],
        }
        thermostat.set_cool_setpoint_min(value)
        thermostat.schedule_update_ha_state(True)

    def set_room_setpoint_away_service(service: ServiceCall) -> None:
        """Set away heating setpoint."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "temp": service.data[ATTR_ROOM_SETPOINT_AWAY],
        }
        thermostat.set_room_setpoint_away(value)
        thermostat.schedule_update_ha_state(True)

    def set_cool_setpoint_away_service(service: ServiceCall) -> None:
        """Set away cooling setpoint."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        value = {
            "id": thermostat.unique_id,
            "temp": service.data[ATTR_COOL_SETPOINT_AWAY],
        }
        thermostat.set_cool_setpoint_away(value)
        thermostat.schedule_update_ha_state(True)

    def set_floor_limit_high_service(service: ServiceCall) -> None:
        """Set maximum floor heating limit for floor device."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "level": service.data[ATTR_FLOOR_MAX],
            "limit": "high",
        }
        thermostat.set_floor_limit(value)
        thermostat.schedule_update_ha_state(True)

    def set_floor_limit_low_service(service: ServiceCall) -> None:
        """Set minimum floor heating limit for floor device."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "level": service.data[ATTR_FLOOR_MIN],
            "limit": "low",
        }
        thermostat.set_floor_limit(value)
        thermostat.schedule_update_ha_state(True)

    def set_activation_service(service: ServiceCall) -> None:
        """Activate or deactivate Neviweb polling for missing device."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "active": service.data[ATTR_ACTIVE],
        }
        thermostat.set_activation(value)
        thermostat.schedule_update_ha_state(True)

    def set_sensor_type_service(service: ServiceCall) -> None:
        """Set floor sensor type."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "type": service.data[ATTR_FLOOR_SENSOR],
        }
        thermostat.set_sensor_type(value)
        thermostat.schedule_update_ha_state(True)

    def set_em_heat_service(service: ServiceCall) -> None:
        """Set emergency heat on/off for thermostats."""
        thermostat = get_thermostat(service)
        if service.data[ATTR_VALUE] == "on":
            thermostat.turn_em_heat_on()
        else:
            thermostat.turn_em_heat_off()
        thermostat.schedule_update_ha_state(True)

    def set_heat_pump_operation_limit_service(service: ServiceCall) -> None:
        """Set minimum temperature for heat pump device operation."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "temp": service.data[ATTR_BALANCE_PT],
        }
        thermostat.set_heat_pump_operation_limit(value)
        thermostat.schedule_update_ha_state(True)

    def set_heat_installation_type_service(service: ServiceCall) -> None:
        """Set minimum temperature for heat pump device operation."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        value = {
            "id": thermostat.unique_id,
            ATTR_TYPE: service.data[ATTR_TYPE],
        }
        thermostat.set_heat_installation_type(value)
        thermostat.schedule_update_ha_state(True)

    def set_heat_lockout_temperature_service(service: ServiceCall) -> None:
        """Set maximum outside temperature limit to allow heating device operation."""
        # Work differently for G2 thermostats
        thermostat = get_thermostat(service)
        temp = service.data.get(ATTR_HEAT_LOCK_TEMP) or service.data.get(ATTR_HEAT_LOCKOUT_TEMP)
        value = {
            "id": thermostat.unique_id,
            "temp": temp,
        }
        thermostat.set_heat_lockout_temperature(value)
        thermostat.schedule_update_ha_state(True)

    def set_cool_lockout_temperature_service(service: ServiceCall) -> None:
        """Set minimum outside temperature limit to allow cooling device operation."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "temp": service.data[ATTR_COOL_LOCK_TEMP],
        }
        thermostat.set_cool_lockout_temperature(value)
        thermostat.schedule_update_ha_state(True)

    def set_display_config_service(service: ServiceCall) -> None:
        """Set display on/off for heat pump."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "display": service.data[ATTR_DISPLAY_CONF],
        }
        thermostat.set_display_config(value)
        thermostat.schedule_update_ha_state(True)

    def set_sound_config_service(service: ServiceCall) -> None:
        """Set sound on/off for heat pump."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "sound": service.data[ATTR_SOUND_CONF],
        }
        thermostat.set_sound_config(value)
        thermostat.schedule_update_ha_state(True)

    def set_hc_second_display_service(service: ServiceCall) -> None:
        """Set second display for TH1134ZB-HC thermostat."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "display": service.data[ATTR_DISPLAY2],
        }
        thermostat.set_hc_second_display(value)
        thermostat.schedule_update_ha_state(True)

    def set_language_service(service: ServiceCall) -> None:
        """Set display language for TH1134ZB-HC thermostat."""
        thermostat = get_thermostat(service)
        value = {
            "id": thermostat.unique_id,
            "lang": service.data[ATTR_LANGUAGE],
        }
        thermostat.set_language(value)
        thermostat.schedule_update_ha_state(True)

    def set_reversing_valve_polarity(service: ServiceCall) -> None:
        """Set minimum time the device is on before letting be off again (run-on time)
        for TH6500WF and TH6250WF thermostats."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        thermostat.set_reversing_valve_polarity(service.data)
        thermostat.schedule_update_ha_state(True)

    def set_min_time_on_service(service: ServiceCall) -> None:
        """Set minimum time the device is on before letting be off again (run-on time)
        for TH6500WF and TH6250WF thermostats."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        thermostat.set_min_time_on(service.data)
        thermostat.schedule_update_ha_state(True)

    def set_min_time_off_service(service: ServiceCall) -> None:
        """Set minimum time the device is off before letting it be on again (cooldown time)
        for TH6500WF and TH6250WF thermostats."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        thermostat.set_min_time_off(service.data)
        thermostat.schedule_update_ha_state(True)

    def set_heat_interstage_delay(service: ServiceCall) -> None:
        """Set minimum time the device is heating before letting it increment the heater stage
        for TH6500WF and TH6250WF thermostats."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        thermostat.set_heat_interstage_delay(service.data)
        thermostat.schedule_update_ha_state(True)

    def set_cool_interstage_delay(service: ServiceCall) -> None:
        """Set minimum time the device is cooling before letting it increment the cooler stage
        for TH6500WF and TH6250WF thermostats."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        thermostat.set_cool_interstage_delay(service.data)
        thermostat.schedule_update_ha_state(True)

    def set_aux_heat_start_delay(service: ServiceCall) -> None:
        """Set minimum time the device is cooling before letting it increment the cooler stage
        for TH6500WF and TH6250WF thermostats."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        thermostat.set_aux_heat_start_delay(service.data)
        thermostat.schedule_update_ha_state(True)

    def set_accessory_type_service(service: ServiceCall) -> None:
        """Set TH6500WF accessory (humidifier, dehumidifier, air exchanger) type."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        value = {
            "id": thermostat.unique_id,
            "type": service.data[ATTR_ACCESSORY_TYPE],
        }
        thermostat.set_accessory_type(value)
        thermostat.schedule_update_ha_state(True)

    def set_schedule_mode_service(service: ServiceCall) -> None:
        """Set TH6500WF, TH6250WF schedule mode, manual or auto."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        value = {
            "id": thermostat.unique_id,
            "mode": service.data[ATTR_SETPOINT_MODE],
        }
        thermostat.set_schedule_mode(value)
        thermostat.schedule_update_ha_state(True)

    def set_heatcool_setpoint_delta_service(service: ServiceCall) -> None:
        """Set TH6500WF, TH6250WF delta temperature between heating and cooling setpoint."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        value = {
            "id": thermostat.unique_id,
            "level": service.data[ATTR_HEATCOOL_SETPOINT_MIN_DELTA],
        }
        thermostat.set_heatcool_setpoint_delta(value)
        thermostat.schedule_update_ha_state(True)

    def set_fan_filter_reminder_service(service: ServiceCall) -> None:
        """Set TH6500WF, TH6250WF fan filter reminder period from 1 to 12 month."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        value = {
            "id": thermostat.unique_id,
            "month": service.data[ATTR_FAN_FILTER_REMAIN],
        }
        thermostat.set_fan_filter_reminder(value)
        thermostat.schedule_update_ha_state(True)

    def set_temperature_offset_service(service: ServiceCall) -> None:
        """Set TH6500WF, TH6250WF temperature sensor offset from -2 to 2°C with a 0.5°C increment."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        value = {
            "id": thermostat.unique_id,
            "temp": service.data[ATTR_TEMP_OFFSET_HEAT],
        }
        thermostat.set_temperature_offset(value)
        thermostat.schedule_update_ha_state(True)

    def set_aux_heating_source_service(service: ServiceCall) -> None:
        """Set TH6500WF, TH6250WF auxiliary heating device."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        value = {
            "id": thermostat.unique_id,
            ATTR_AUX_HEAT_SOURCE_TYPE: service.data[ATTR_AUX_HEAT_SOURCE_TYPE],
        }
        thermostat.set_aux_heating_source(value)
        thermostat.schedule_update_ha_state(True)

    def set_fan_speed_service(service: ServiceCall) -> None:
        """Set TH6500WF, TH6250WF fan speed, On or Auto."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        value = {
            "id": thermostat.unique_id,
            "speed": service.data[ATTR_FAN_SPEED],
        }
        thermostat.set_fan_speed(value)
        thermostat.schedule_update_ha_state(True)

    def set_humidity_mode_service(service: ServiceCall) -> None:
        """Set TH6500WF, TH6250WF fan speed, On or Auto."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        value = {
            "id": thermostat.unique_id,
            "mode": service.data[ATTR_HUMIDITY_SETPOINT_MODE],
        }
        thermostat.set_humidity_mode(value)
        thermostat.schedule_update_ha_state(True)

    def set_heat_dissipation_time_service(service: ServiceCall) -> None:
        """Set TH6500WF, TH6250WF fan speed, On or Auto."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        value = {
            "id": thermostat.unique_id,
            ATTR_TIME: service.data[ATTR_TIME] * 60,
        }
        thermostat.set_heat_dissipation_time(value)
        thermostat.schedule_update_ha_state(True)

    def set_cool_dissipation_time_service(service: ServiceCall) -> None:
        """Set TH6500WF, TH6250WF fan speed, On or Auto."""
        thermostat = get_thermostat(service)
        if not isinstance(thermostat, Neviweb130HeatCoolThermostat):
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "must_be_heat_cool",
                    f"Entity '{thermostat.entity_id}' must be a heat cool {DOMAIN} integration",
                    entity=thermostat.entity_id,
                    domain=DOMAIN,
                )
            )
        value = {
            "id": thermostat.unique_id,
            ATTR_TIME: service.data[ATTR_TIME] * 60,
        }
        thermostat.set_cool_dissipation_time(value)
        thermostat.schedule_update_ha_state(True)

    def set_climate_neviweb_status_service(service):
        """Set Neviweb global status per location, home or away."""
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "mode": service.data[ATTR_MODE]}
                thermostat.set_climate_neviweb_status(value)
                thermostat.schedule_update_ha_state(True)
                break

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SECOND_DISPLAY,
        set_second_display_service,
        schema=SET_SECOND_DISPLAY_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_BACKLIGHT,
        set_backlight_service,
        schema=SET_BACKLIGHT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CLIMATE_KEYPAD_LOCK,
        set_climate_keypad_lock_service,
        schema=SET_CLIMATE_KEYPAD_LOCK_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TIME_FORMAT,
        set_time_format_service,
        schema=SET_TIME_FORMAT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TEMPERATURE_FORMAT,
        set_temperature_format_service,
        schema=SET_TEMPERATURE_FORMAT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SETPOINT_MAX,
        set_setpoint_max_service,
        schema=SET_SETPOINT_MAX_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SETPOINT_MIN,
        set_setpoint_min_service,
        schema=SET_SETPOINT_MIN_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FLOOR_AIR_LIMIT,
        set_floor_air_limit_service,
        schema=SET_FLOOR_AIR_LIMIT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_EARLY_START,
        set_early_start_service,
        schema=SET_EARLY_START_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_AIR_FLOOR_MODE,
        set_air_floor_mode_service,
        schema=SET_AIR_FLOOR_MODE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_HVAC_DR_OPTIONS,
        set_hvac_dr_options_service,
        schema=SET_HVAC_DR_OPTIONS_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_HVAC_DR_SETPOINT,
        set_hvac_dr_setpoint_service,
        schema=SET_HVAC_DR_SETPOINT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_AUXILIARY_LOAD,
        set_auxiliary_load_service,
        schema=SET_AUXILIARY_LOAD_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_AUX_CYCLE_OUTPUT,
        set_aux_cycle_output_service,
        schema=SET_AUX_CYCLE_OUTPUT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CYCLE_OUTPUT,
        set_cycle_output_service,
        schema=SET_CYCLE_OUTPUT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PUMP_PROTECTION,
        set_pump_protection_service,
        schema=SET_PUMP_PROTECTION_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_COOL_SETPOINT_MAX,
        set_cool_setpoint_max_service,
        schema=SET_COOL_SETPOINT_MAX_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_COOL_SETPOINT_MIN,
        set_cool_setpoint_min_service,
        schema=SET_COOL_SETPOINT_MIN_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ROOM_SETPOINT_AWAY,
        set_room_setpoint_away_service,
        schema=SET_ROOM_SETPOINT_AWAY_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_COOL_SETPOINT_AWAY,
        set_cool_setpoint_away_service,
        schema=SET_COOL_SETPOINT_AWAY_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FLOOR_LIMIT_HIGH,
        set_floor_limit_high_service,
        schema=SET_FLOOR_LIMIT_HIGH_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FLOOR_LIMIT_LOW,
        set_floor_limit_low_service,
        schema=SET_FLOOR_LIMIT_LOW_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ACTIVATION,
        set_activation_service,
        schema=SET_ACTIVATION_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SENSOR_TYPE,
        set_sensor_type_service,
        schema=SET_SENSOR_TYPE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_EM_HEAT,
        set_em_heat_service,
        schema=SET_EM_HEAT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_HEAT_PUMP_OPERATION_LIMIT,
        set_heat_pump_operation_limit_service,
        schema=SET_HEAT_PUMP_OPERATION_LIMIT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_HEAT_INSTALLATION_TYPE,
        set_heat_installation_type_service,
        schema=SET_HEAT_INSTALLATION_TYPE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_COOL_LOCKOUT_TEMPERATURE,
        set_cool_lockout_temperature_service,
        schema=SET_COOL_LOCKOUT_TEMPERATURE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_HEAT_LOCKOUT_TEMPERATURE,
        set_heat_lockout_temperature_service,
        schema=SET_HEAT_LOCKOUT_TEMPERATURE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_DISPLAY_CONFIG,
        set_display_config_service,
        schema=SET_DISPLAY_CONFIG_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SOUND_CONFIG,
        set_sound_config_service,
        schema=SET_SOUND_CONFIG_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_HC_SECOND_DISPLAY,
        set_hc_second_display_service,
        schema=SET_HC_SECOND_DISPLAY_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_LANGUAGE,
        set_language_service,
        schema=SET_LANGUAGE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_REVERSING_VALVE_POLARITY,
        set_reversing_valve_polarity,
        schema=SET_REVERSING_VALVE_POLARITY_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_MIN_TIME_ON,
        set_min_time_on_service,
        schema=SET_MIN_TIME_ON_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_MIN_TIME_OFF,
        set_min_time_off_service,
        schema=SET_MIN_TIME_OFF_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_HEAT_INTERSTAGE_DELAY,
        set_heat_interstage_delay,
        schema=SET_HEAT_INTERSTAGE_DELAY_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_COOL_INTERSTAGE_DELAY,
        set_cool_interstage_delay,
        schema=SET_COOL_INTERSTAGE_DELAY_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_AUX_HEAT_START_DELAY,
        set_aux_heat_start_delay,
        schema=SET_AUX_HEAT_START_DELAY_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ACCESSORY_TYPE,
        set_accessory_type_service,
        schema=SET_ACCESSORY_TYPE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCHEDULE_MODE,
        set_schedule_mode_service,
        schema=SET_SCHEDULE_MODE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_HEATCOOL_SETPOINT_DELTA,
        set_heatcool_setpoint_delta_service,
        schema=SET_HEATCOOL_SETPOINT_DELTA_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FAN_FILTER_REMINDER,
        set_fan_filter_reminder_service,
        schema=SET_FAN_FILTER_REMINDER_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TEMPERATURE_OFFSET,
        set_temperature_offset_service,
        schema=SET_TEMPERATURE_OFFSET_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_AUX_HEATING_SOURCE,
        set_aux_heating_source_service,
        schema=SET_AUX_HEATING_SOURCE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_FAN_SPEED,
        set_fan_speed_service,
        schema=SET_FAN_SPEED_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_HUMIDITY_SETPOINT_MODE,
        set_humidity_mode_service,
        schema=SET_HUMIDITY_SETPOINT_MODE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_HEAT_DISSIPATION_TIME,
        set_heat_dissipation_time_service,
        schema=SET_HEAT_DISSIPATION_TIME_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_COOL_DISSIPATION_TIME,
        set_cool_dissipation_time_service,
        schema=SET_COOL_DISSIPATION_TIME_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CLIMATE_NEVIWEB_STATUS,
        set_climate_neviweb_status_service,
        schema=SET_CLIMATE_NEVIWEB_STATUS_SCHEMA,
    )



# ---------------------------------------------------------------------------
# Import all thermostat classes from sub-modules.
# The class definitions have been moved there; this file keeps only the
# HA entry-point functions (async_setup_platform, _register_climate_services).
# ---------------------------------------------------------------------------
from .base import Neviweb130Thermostat  # noqa: E402
from .zigbee import (  # noqa: E402
    Neviweb130G2Thermostat,
    Neviweb130FloorThermostat,
    Neviweb130LowThermostat,
    Neviweb130DoubleThermostat,
)
from .wifi import (  # noqa: E402
    Neviweb130WifiThermostat,
    Neviweb130WifiLiteThermostat,
    Neviweb130ColorWifiThermostat,
    Neviweb130LowWifiThermostat,
    Neviweb130WifiFloorThermostat,
)
from .heatcool import Neviweb130HcThermostat, Neviweb130HeatCoolThermostat  # noqa: E402
from .heatpump import Neviweb130HPThermostat, Neviweb130WifiHPThermostat  # noqa: E402
from .mixins import (  # noqa: E402
    _BlockedMethod,
    FloorMixin,
    LowVoltageMixin,
    HeatPumpMixin,
    HeatCoolMixin,
    ERROR_HANDLERS,
    _handle_action_not_supported,
    _handle_attr_not_supported,
    _handle_comm_timeout,
    _handle_day_req_max,
    _handle_device_busy,
    _handle_device_error,
    _handle_device_unavailable,
    _handle_maintenance,
    _handle_service_error,
    _handle_service_unauthorized,
    _handle_session_exceeded,
    _handle_session_expired,
    _handle_timeout_error,
)
