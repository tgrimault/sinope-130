"""
Support for Neviweb thermostat connected to GT130 ZigBee.
model 1123 = thermostat TH1123ZB 3000W
model 300 = thermostat TH1123ZB-G2 3000W
model 1124 = thermostat TH1124ZB 4000W
model 300 = thermostat TH1124ZB-G2 4000W
model 737 = thermostat TH1300ZB 3600W (floor)
model 7373 = thermostat TH1500ZB double pole thermostat
model 7372 = thermostat TH1400ZB low voltage
model 1124 = thermostat OTH4000-ZB Ouellet
model 737 = thermostat OTH3600-GA-ZB Ouellet
model 1134 = Thermostat TH1134ZB-HC for heating/cooling interlocking

Support for Neviweb wifi thermostats
model 1510 = thermostat TH1123WF 3000W (wifi)
model 1510 = thermostat TH1124WF 4000W (wifi)
model 738 = thermostat TH1300WF 3600W, TH1325WF, TH1310WF and SRM40 (wifi floor)
model 739 = thermostat TH1400WF low voltage (wifi)
model 742 = thermostat TH1500WF double pole thermostat (wifi)

Support for Flextherm wifi thermostat
model 738 = Thermostat concerto connect FLP55 (wifi floor), (sku: FLP55), no energy stats

For more details about this platform, please refer to the documentation at
https://www.sinopetech.com/en/support/#api
"""

from __future__ import annotations

import logging

from homeassistant.const import ATTR_ENTITY_ID

from .thermostats.base_thermostat import Neviweb130Thermostat
from .thermostats.double_thermostat import Neviweb130DoubleThermostat
from .thermostats.floor_thermostat import Neviweb130FloorThermostat
from .thermostats.g2_thermostat import Neviweb130G2Thermostat
from .thermostats.hc_thermostat import Neviweb130HcThermostat
from .thermostats.low_voltage_thermostat import Neviweb130LowVoltageThermostat
from .thermostats.low_voltage_wifi_thermostat import Neviweb130LowVoltageWifiThermostat
from .thermostats.wifi_floor_thermostat import Neviweb130WifiFloorThermostat
from .thermostats.wifi_thermostat import Neviweb130WifiThermostat

from .const import (
    DOMAIN,
    ATTR_ACTIVE,
    ATTR_BACKLIGHT,
    ATTR_COOL_SETPOINT_MAX,
    ATTR_COOL_SETPOINT_MIN,
    ATTR_DISPLAY2,
    ATTR_DRACTIVE,
    ATTR_EARLY_START,
    ATTR_FLOOR_AIR_LIMIT,
    ATTR_FLOOR_MAX,
    ATTR_FLOOR_MIN,
    ATTR_FLOOR_MODE,
    ATTR_FLOOR_SENSOR,
    ATTR_KEYPAD,
    ATTR_OPTOUT,
    ATTR_ROOM_SETPOINT_MAX,
    ATTR_ROOM_SETPOINT_MIN,
    ATTR_SETPOINT,
    ATTR_STATUS,
    ATTR_TEMP,
    ATTR_TIME,
    ATTR_TYPE,
    ATTR_VALUE,
    SERVICE_SET_ACTIVATION,
    SERVICE_SET_AIR_FLOOR_MODE,
    SERVICE_SET_AUX_CYCLE_OUTPUT,
    SERVICE_SET_AUXILIARY_LOAD,
    SERVICE_SET_BACKLIGHT,
    SERVICE_SET_CLIMATE_KEYPAD_LOCK,
    SERVICE_SET_COOL_SETPOINT_MAX,
    SERVICE_SET_COOL_SETPOINT_MIN,
    SERVICE_SET_CYCLE_OUTPUT,
    SERVICE_SET_EARLY_START,
    SERVICE_SET_FLOOR_AIR_LIMIT,
    SERVICE_SET_FLOOR_LIMIT_HIGH,
    SERVICE_SET_FLOOR_LIMIT_LOW,
    SERVICE_SET_HVAC_DR_OPTIONS,
    SERVICE_SET_HVAC_DR_SETPOINT,
    SERVICE_SET_PUMP_PROTECTION,
    SERVICE_SET_SECOND_DISPLAY,
    SERVICE_SET_SENSOR_TYPE,
    SERVICE_SET_SETPOINT_MAX,
    SERVICE_SET_SETPOINT_MIN,
    SERVICE_SET_TEMPERATURE_FORMAT,
    SERVICE_SET_TIME_FORMAT,
)

from .schema import (
    SET_SECOND_DISPLAY_SCHEMA,
    SET_BACKLIGHT_SCHEMA,
    SET_CLIMATE_KEYPAD_LOCK_SCHEMA,
    SET_TIME_FORMAT_SCHEMA,
    SET_TEMPERATURE_FORMAT_SCHEMA,
    SET_SETPOINT_MAX_SCHEMA,
    SET_SETPOINT_MIN_SCHEMA,
    SET_FLOOR_AIR_LIMIT_SCHEMA,
    SET_EARLY_START_SCHEMA,
    SET_AIR_FLOOR_MODE_SCHEMA,
    SET_HVAC_DR_OPTIONS_SCHEMA,
    SET_HVAC_DR_SETPOINT_SCHEMA,
    SET_COOL_SETPOINT_MAX_SCHEMA,
    SET_COOL_SETPOINT_MIN_SCHEMA,
    SET_AUXILIARY_LOAD_SCHEMA,
    SET_AUX_CYCLE_OUTPUT_SCHEMA,
    SET_CYCLE_OUTPUT_SCHEMA,
    SET_PUMP_PROTECTION_SCHEMA,
    SET_FLOOR_LIMIT_LOW_SCHEMA,
    SET_FLOOR_LIMIT_HIGH_SCHEMA,
    SET_ACTIVATION_SCHEMA,
    SET_SENSOR_TYPE_SCHEMA,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "neviweb130 climate"
DEFAULT_NAME_2 = "neviweb130 climate 2"

DEVICE_MODEL_LOW = [7372]
DEVICE_MODEL_LOW_WIFI = [739]
DEVICE_MODEL_FLOOR = [737]
DEVICE_MODEL_WIFI_FLOOR = [738]
DEVICE_MODEL_WIFI = [1510, 742]
DEVICE_MODEL_HEAT = [1123, 1124]
DEVICE_MODEL_DOUBLE = [7373]
DEVICE_MODEL_HEAT_G2 = [300]
DEVICE_MODEL_HC = [1134]
IMPLEMENTED_DEVICE_MODEL = DEVICE_MODEL_HEAT + DEVICE_MODEL_FLOOR + DEVICE_MODEL_LOW + DEVICE_MODEL_WIFI_FLOOR + DEVICE_MODEL_WIFI + DEVICE_MODEL_LOW_WIFI + DEVICE_MODEL_HEAT_G2 + DEVICE_MODEL_HC + DEVICE_MODEL_DOUBLE


async def async_setup_platform(
        hass,
        config,
        async_add_entities,
        discovery_info=None,
):
    """Set up the neviweb130 thermostats."""
    data = hass.data[DOMAIN]

    entities = []
    for device_info in data.neviweb130_client.gateway_data:
        if "signature" in device_info and \
                "model" in device_info["signature"] and \
                device_info["signature"]["model"] in IMPLEMENTED_DEVICE_MODEL:
            device_name = "{} {}".format(DEFAULT_NAME, device_info["name"])
            device_sku = device_info["sku"]
            device_firmware = "{}.{}.{}".format(device_info["signature"]["softVersion"]["major"],
                                                device_info["signature"]["softVersion"]["middle"],
                                                device_info["signature"]["softVersion"]["minor"])
            if device_info["signature"]["model"] in DEVICE_MODEL_HEAT:
                entities.append(Neviweb130Thermostat(data, device_info, device_name, device_sku, device_firmware))
            elif device_info["signature"]["model"] in DEVICE_MODEL_HEAT_G2:
                entities.append(Neviweb130G2Thermostat(data, device_info, device_name, device_sku, device_firmware))
            elif device_info["signature"]["model"] in DEVICE_MODEL_FLOOR:
                entities.append(Neviweb130FloorThermostat(data, device_info, device_name, device_sku, device_firmware))
            elif device_info["signature"]["model"] in DEVICE_MODEL_LOW:
                entities.append(Neviweb130LowVoltageThermostat(data, device_info, device_name, device_sku, device_firmware))
            elif device_info["signature"]["model"] in DEVICE_MODEL_DOUBLE:
                entities.append(Neviweb130DoubleThermostat(data, device_info, device_name, device_sku, device_firmware))
            elif device_info["signature"]["model"] in DEVICE_MODEL_WIFI:
                entities.append(Neviweb130WifiThermostat(data, device_info, device_name, device_sku, device_firmware))
            elif device_info["signature"]["model"] in DEVICE_MODEL_LOW_WIFI:
                entities.append(
                    Neviweb130LowVoltageWifiThermostat(data, device_info, device_name, device_sku, device_firmware))
            elif device_info["signature"]["model"] in DEVICE_MODEL_WIFI_FLOOR:
                entities.append(
                    Neviweb130WifiFloorThermostat(data, device_info, device_name, device_sku, device_firmware))
            elif device_info["signature"]["model"] in DEVICE_MODEL_HC:
                entities.append(Neviweb130HcThermostat(data, device_info, device_name, device_sku, device_firmware))
    for device_info in data.neviweb130_client.gateway_data2:
        if "signature" in device_info and \
                "model" in device_info["signature"] and \
                device_info["signature"]["model"] in IMPLEMENTED_DEVICE_MODEL:
            device_name = "{} {}".format(DEFAULT_NAME_2, device_info["name"])
            device_sku = device_info["sku"]
            device_firmware = "{}.{}.{}".format(device_info["signature"]["softVersion"]["major"],
                                                device_info["signature"]["softVersion"]["middle"],
                                                device_info["signature"]["softVersion"]["minor"])
            if device_info["signature"]["model"] in DEVICE_MODEL_HEAT:
                entities.append(Neviweb130Thermostat(data, device_info, device_name, device_sku, device_firmware))
            elif device_info["signature"]["model"] in DEVICE_MODEL_HEAT_G2:
                entities.append(Neviweb130G2Thermostat(data, device_info, device_name, device_sku, device_firmware))
            elif device_info["signature"]["model"] in DEVICE_MODEL_FLOOR:
                entities.append(Neviweb130FloorThermostat(data, device_info, device_name, device_sku, device_firmware))
            elif device_info["signature"]["model"] in DEVICE_MODEL_LOW:
                entities.append(Neviweb130LowVoltageThermostat(data, device_info, device_name, device_sku, device_firmware))
            elif device_info["signature"]["model"] in DEVICE_MODEL_DOUBLE:
                entities.append(Neviweb130DoubleThermostat(data, device_info, device_name, device_sku, device_firmware))
            elif device_info["signature"]["model"] in DEVICE_MODEL_WIFI:
                entities.append(Neviweb130WifiThermostat(data, device_info, device_name, device_sku, device_firmware))
            elif device_info["signature"]["model"] in DEVICE_MODEL_LOW_WIFI:
                entities.append(
                    Neviweb130LowVoltageWifiThermostat(data, device_info, device_name, device_sku, device_firmware))
            elif device_info["signature"]["model"] in DEVICE_MODEL_WIFI_FLOOR:
                entities.append(
                    Neviweb130WifiFloorThermostat(data, device_info, device_name, device_sku, device_firmware))
            elif device_info["signature"]["model"] in DEVICE_MODEL_HC:
                entities.append(Neviweb130HcThermostat(data, device_info, device_name, device_sku, device_firmware))

    async_add_entities(entities, True)

    def set_second_display_service(service):
        """Set to outside or setpoint temperature display for wifi thermostats"""
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "display": service.data[ATTR_DISPLAY2]}
                thermostat.set_second_display(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_backlight_service(service):
        """Set backlight always on or auto"""
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "type": service.data[ATTR_TYPE],
                         "level": service.data[ATTR_BACKLIGHT]}
                thermostat.set_backlight(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_climate_keypad_lock_service(service):
        """ lock/unlock keypad device"""
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "lock": service.data[ATTR_KEYPAD]}
                thermostat.set_keypad_lock(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_time_format_service(service):
        """ set time format 12h or 24h"""
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "time": service.data[ATTR_TIME]}
                thermostat.set_time_format(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_temperature_format_service(service):
        """ set temperature format, celsius or fahrenheit"""
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "temp": service.data[ATTR_TEMP]}
                thermostat.set_temperature_format(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_setpoint_max_service(service):
        """ set maximum setpoint for device"""
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "temp": service.data[ATTR_ROOM_SETPOINT_MAX]}
                thermostat.set_setpoint_max(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_setpoint_min_service(service):
        """ set minimum setpoint for device"""
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "temp": service.data[ATTR_ROOM_SETPOINT_MIN]}
                thermostat.set_setpoint_min(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_floor_air_limit_service(service):
        """ set minimum setpoint for device"""
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "temp": service.data[ATTR_FLOOR_AIR_LIMIT]}
                thermostat.set_floor_air_limit(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_early_start_service(service):
        """ set early heating on/off for wifi thermostat """
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "start": service.data[ATTR_EARLY_START]}
                thermostat.set_early_start(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_air_floor_mode_service(service):
        """ switch between ambiant or floor temperature sensor """
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "mode": service.data[ATTR_FLOOR_MODE]}
                thermostat.set_air_floor_mode(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_hvac_dr_options_service(service):
        """ Set options for hvac dr in Eco Sinope """
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "dractive": service.data[ATTR_DRACTIVE],
                         "optout": service.data[ATTR_OPTOUT], "setpoint": service.data[ATTR_SETPOINT]}
                thermostat.set_hvac_dr_options(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_hvac_dr_setpoint_service(service):
        """ Set options for hvac dr setpoint in Eco Sinope """
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "status": service.data[ATTR_STATUS],
                         "val": service.data[ATTR_VALUE]}
                thermostat.set_hvac_dr_setpoint(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_auxiliary_load_service(service):
        """ Set options for auxilary heating """
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "status": service.data[ATTR_STATUS],
                         "val": service.data[ATTR_VALUE]}
                thermostat.set_auxiliary_load(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_aux_cycle_output_service(service):
        """ Set options for auxilary cycle length for low voltage thermostats """
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "status": service.data[ATTR_STATUS],
                         "val": service.data[ATTR_VALUE][0]}
                thermostat.set_aux_cycle_output(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_cycle_output_service(service):
        """ Set options for main cycle length for low voltage thermostats """
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "val": service.data[ATTR_VALUE][0]}
                thermostat.set_cycle_output(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_pump_protection_service(service):
        """ Set status of pump protection for low voltage thermostats """
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "status": service.data[ATTR_STATUS]}
                thermostat.set_pump_protection(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_cool_setpoint_max_service(service):
        """ set maximum cooling setpoint for device"""
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "temp": service.data[ATTR_COOL_SETPOINT_MAX]}
                thermostat.set_cool_setpoint_max(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_cool_setpoint_min_service(service):
        """ set minimum cooling setpoint for device"""
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "temp": service.data[ATTR_COOL_SETPOINT_MIN]}
                thermostat.set_cool_setpoint_min(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_floor_limit_high_service(service):
        """ set maximum floor heating limit for floor device"""
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "level": service.data[ATTR_FLOOR_MAX], "limit": "high"}
                thermostat.set_floor_limit(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_floor_limit_low_service(service):
        """ set minimum floor heating limit for floor device"""
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "level": service.data[ATTR_FLOOR_MIN], "limit": "low"}
                thermostat.set_floor_limit(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_activation_service(service):
        """ Activate or deactivate Neviweb polling for missing device """
        entity_id = service.data[ATTR_ENTITY_ID]
        for switch in entities:
            if switch.entity_id == entity_id:
                value = {"id": switch.unique_id, "active": service.data[ATTR_ACTIVE]}
                switch.set_activation(value)
                switch.schedule_update_ha_state(True)
                break

    def set_sensor_type_service(service):
        """ Set floor sensor type """
        entity_id = service.data[ATTR_ENTITY_ID]
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "type": service.data[ATTR_FLOOR_SENSOR]}
                thermostat.set_sensor_type(value)
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
