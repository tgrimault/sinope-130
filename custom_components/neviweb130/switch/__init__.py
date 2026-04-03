"""
Support for Neviweb switch connected to GT130 Zigbee.
Multi-Controller connected to GT130
model 2180 = Multi controller for sedna valve MC3100ZB

Load controller connected to GT130 or Wi-Fi
Support for Neviweb switch connected via GT130 Zigbee.
model 2506 = load controller device, RM3250ZB, 50A, Zigbee
model 346 = load controller device, RM3250WF, 50A, Wi-Fi
model 2151 = Calypso load controller for water heater, RM3500ZB 20,8A, Zigbee
model 2152 = Calypso load controller for water heater, RM3500WF 20,8A, Wi-Fi
model 339 = Calypso load controller for water heater, RM3510WF 20,8A, Wi-Fi
model 2610 = wall outlet, SP2610ZB
model 2600 = portable plug, SP2600ZB

Multi controller connected to Sedna valve
model 2181 = Multi controller for sedna valve MC3100ZB-VA connected sedna valve

Load controller connected to Sedna valve
model 25062 = load controller device, RM3250ZB-VA, 50A, Zigbee

Outlet and plug connected to Sedna valve
model 26102 = wall outlet, SP2610ZB-VA
model 26002 = portable plug, SP2600ZB-VA

For more details about this platform, please refer to the documentation at
https://www.sinopetech.com/en/support/#api
"""

from __future__ import annotations

import logging
from threading import Lock
from typing import Any

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import ServiceCall
from homeassistant.exceptions import ServiceValidationError

from .. import NOTIFY
from ..const import (
    ATTR_ACTIVE,
    ATTR_COLD_LOAD_PICKUP_REMAIN_TIME,
    ATTR_DELAY,
    ATTR_DRACTIVE,
    ATTR_INPUT_NUMBER,
    ATTR_KEYPAD,
    ATTR_NAME_1,
    ATTR_NAME_2,
    ATTR_ONOFF,
    ATTR_ONOFF_NUM,
    ATTR_OPTOUT,
    ATTR_OUTPUT_NAME_1,
    ATTR_OUTPUT_NAME_2,
    ATTR_STATUS,
    ATTR_TEMP_ALERT,
    ATTR_TIME,
    ATTR_TIMER,
    ATTR_TIMER2,
    ATTR_VALUE,
    ATTR_WATER_TEMP_MIN,
    DOMAIN,
    SERVICE_SET_ACTIVATION,
    SERVICE_SET_CONTROL_ONOFF,
    SERVICE_SET_CONTROLLED_DEVICE,
    SERVICE_SET_INPUT_OUTPUT_NAMES,
    SERVICE_SET_LOAD_DR_OPTIONS,
    SERVICE_SET_LOW_TEMP_PROTECTION,
    SERVICE_SET_ON_OFF_INPUT_DELAY,
    SERVICE_SET_REMAINING_TIME,
    SERVICE_SET_SWITCH_KEYPAD_LOCK,
    SERVICE_SET_SWITCH_TEMP_ALERT,
    SERVICE_SET_SWITCH_TIMER,
    SERVICE_SET_SWITCH_TIMER_2,
    SERVICE_SET_TANK_SIZE,
)
from ..helpers import translated_or_default
from ..schema import (
    SET_ACTIVATION_SCHEMA,
    SET_CONTROL_ONOFF_SCHEMA,
    SET_CONTROLLED_DEVICE_SCHEMA,
    SET_INPUT_OUTPUT_NAMES_SCHEMA,
    SET_LOAD_DR_OPTIONS_SCHEMA,
    SET_LOW_TEMP_PROTECTION_SCHEMA,
    SET_ON_OFF_INPUT_DELAY_SCHEMA,
    SET_REMAINING_TIME_SCHEMA,
    SET_SWITCH_KEYPAD_LOCK_SCHEMA,
    SET_SWITCH_TEMP_ALERT_SCHEMA,
    SET_SWITCH_TIMER_2_SCHEMA,
    SET_SWITCH_TIMER_SCHEMA,
    SET_TANK_SIZE_SCHEMA,
)

_LOGGER = logging.getLogger(__name__)

# Re-export everything from sub-modules for backward compatibility
from ..helpers import safe_get_device_attributes  # noqa: E402 — re-export for test patching
from .base import (  # noqa: E402
    Neviweb130Switch,
    SNOOZE_TIME,
    SCAN_INTERVAL,
    UPDATE_ATTRIBUTES,
    HA_TO_NEVIWEB_SIZE,
    HA_TO_NEVIWEB_DELAY,
    HA_TO_NEVIWEB_CONTROLLED,
    SWITCH_TYPES,
    IMPLEMENTED_WIFI_WATER_HEATER_LOAD_MODEL,
    IMPLEMENTED_WATER_HEATER_LOAD_MODEL,
    IMPLEMENTED_ZB_DEVICE_CONTROL,
    IMPLEMENTED_SED_DEVICE_CONTROL,
    IMPLEMENTED_WALL_DEVICES,
    IMPLEMENTED_SED_WALL_DEVICES,
    IMPLEMENTED_LOAD_DEVICES,
    IMPLEMENTED_SED_LOAD_DEVICES,
    IMPLEMENTED_WIFI_LOAD_DEVICES,
    IMPLEMENTED_DEVICE_MODEL,
    voltage_to_percentage,
    neviweb_to_ha,
    neviweb_to_ha_controlled,
    neviweb_to_ha_delay,
    trigger_close,
    L_2_sqm,
    model_to_HA,
    lock_to_ha,
    remaining_time,
)
from .subclasses import (  # noqa: E402
    Neviweb130PowerSwitch,
    Neviweb130WifiPowerSwitch,
    Neviweb130TankPowerSwitch,
    Neviweb130WifiTankPowerSwitch,
    Neviweb130ControlerSwitch,
)


def _build_switch_entities(
    gateway_data: list, group_name: str, client: Any
) -> list:
    """Instantiate switch entities for one gateway data list."""
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
        sv = device_info["signature"]["softVersion"]
        device_firmware = "{}.{}.{}".format(sv["major"], sv["middle"], sv["minor"])
        model = device_info["signature"]["model"]
        if model in IMPLEMENTED_WALL_DEVICES or model in IMPLEMENTED_SED_WALL_DEVICES:
            result.append(Neviweb130Switch(device_info, device_name, device_sku, device_firmware, "outlet", client))
        elif model in IMPLEMENTED_LOAD_DEVICES or model in IMPLEMENTED_SED_LOAD_DEVICES:
            result.append(Neviweb130PowerSwitch(device_info, device_name, device_sku, device_firmware, "power", client))
        elif model in IMPLEMENTED_WIFI_LOAD_DEVICES:
            result.append(Neviweb130WifiPowerSwitch(device_info, device_name, device_sku, device_firmware, "power", client))
        elif model in IMPLEMENTED_WATER_HEATER_LOAD_MODEL:
            result.append(Neviweb130TankPowerSwitch(device_info, device_name, device_sku, device_firmware, "power", client))
        elif model in IMPLEMENTED_WIFI_WATER_HEATER_LOAD_MODEL:
            result.append(Neviweb130WifiTankPowerSwitch(device_info, device_name, device_sku, device_firmware, "power", client))
        else:  # IMPLEMENTED_ZB_DEVICE_CONTROL or IMPLEMENTED_SED_DEVICE_CONTROL
            result.append(Neviweb130ControlerSwitch(device_info, device_name, device_sku, device_firmware, "control", client))
    return result


async def async_setup_platform(
    hass,
    config,
    async_add_entities,
    discovery_info=None,
) -> None:
    """Set up the Neviweb130 switch."""
    data = hass.data[DOMAIN]["data"]

    # Wait for async migration to be done
    await data.migration_done.wait()

    entities: list[Neviweb130Switch] = []

    # Loop through all clients (supports multi-account)
    for client in data.neviweb130_clients:
        entities.extend(_build_switch_entities(
            client.gateway_data, client.default_group_name("switch"), client
        ))
        entities.extend(_build_switch_entities(
            client.gateway_data2, client.default_group_name("switch", 2), client
        ))
        entities.extend(_build_switch_entities(
            client.gateway_data3, client.default_group_name("switch", 3), client
        ))

    async_add_entities(entities, True)
    _register_switch_services(hass, entities)


def _register_switch_services(hass: Any, entities: list) -> None:
    """Register all switch services with Home Assistant."""
    entity_map: dict[str, Neviweb130Switch] | None = None
    _entity_map_lock = Lock()

    def get_switch(service: ServiceCall) -> Neviweb130Switch:
        entity_id = service.data.get(ATTR_ENTITY_ID)
        if entity_id is None:
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "missing_parameter",
                    f"Missing required parameter: {ATTR_ENTITY_ID}.",
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
                                "Entities not finished loading, try again shortly.",
                            )
                        )

        switch = entity_map.get(entity_id)
        if switch is None:
            raise ServiceValidationError(
                translated_or_default(
                    hass,
                    "entity_must_be_domain",
                    f"Entity {entity_id} must be a {DOMAIN} switch.",
                    entity=entity_id,
                    domain=DOMAIN,
                    platform="switch",
                )
            )
        return switch

    def set_switch_keypad_lock_service(service: ServiceCall) -> None:
        """Lock/unlock keypad device."""
        switch = get_switch(service)
        value = {"id": switch.unique_id, "lock": service.data[ATTR_KEYPAD]}
        switch.set_keypad_lock(value)
        switch.schedule_update_ha_state(True)

    def set_switch_timer_service(service: ServiceCall) -> None:
        """Set timer for switch device."""
        switch = get_switch(service)
        value = {"id": switch.unique_id, ATTR_TIME: service.data[ATTR_TIMER]}
        switch.set_timer(value)
        switch.schedule_update_ha_state(True)

    def set_switch_timer2_service(service: ServiceCall) -> None:
        """Set timer for switch device."""
        switch = get_switch(service)
        value = {"id": switch.unique_id, ATTR_TIME: service.data[ATTR_TIMER2]}
        switch.set_timer2(value)
        switch.schedule_update_ha_state(True)

    def set_switch_temp_alert_service(service: ServiceCall) -> None:
        """Set low temperature alert for switch device MC3100ZB."""
        switch = get_switch(service)
        value = {"id": switch.unique_id, "alert": service.data[ATTR_TEMP_ALERT]}
        switch.set_temp_alert(value)
        switch.schedule_update_ha_state(True)

    def set_load_dr_options_service(service: ServiceCall) -> None:
        """Set dr mode options for load controller."""
        switch = get_switch(service)
        value = {
            "id": switch.unique_id,
            "dractive": service.data[ATTR_DRACTIVE],
            "droptout": service.data[ATTR_OPTOUT],
            "onoff": service.data[ATTR_ONOFF],
        }
        switch.set_load_dr_options(value)
        switch.schedule_update_ha_state(True)

    def set_control_onoff_service(service: ServiceCall) -> None:
        """Set status of both onoff controller."""
        switch = get_switch(service)
        value = {
            "id": switch.unique_id,
            "onoff_num": service.data[ATTR_ONOFF_NUM],
            "status": service.data[ATTR_STATUS],
        }
        switch.set_control_onoff(value)
        switch.schedule_update_ha_state(True)

    def set_tank_size_service(service: ServiceCall) -> None:
        """Set water tank size for RM3500ZB."""
        switch = get_switch(service)
        value = {"id": switch.unique_id, "val": service.data[ATTR_VALUE][0]}
        switch.set_tank_size(value)
        switch.schedule_update_ha_state(True)

    def set_controlled_device_service(service: ServiceCall) -> None:
        """Set controlled device type for RM3250ZB."""
        switch = get_switch(service)
        value = {"id": switch.unique_id, "val": service.data[ATTR_VALUE][0]}
        switch.set_controlled_device(value)
        switch.schedule_update_ha_state(True)

    def set_low_temp_protection_service(service: ServiceCall) -> None:
        """Set water tank temperature protection for RM3500ZB."""
        switch = get_switch(service)
        value = {
            "id": switch.unique_id,
            "val": service.data[ATTR_WATER_TEMP_MIN],
        }
        switch.set_low_temp_protection(value)
        switch.schedule_update_ha_state(True)

    def set_input_output_names_service(service: ServiceCall) -> None:
        """Set names for input 1 and 2, output 1 and 2 for MC3100ZB device."""
        switch = get_switch(service)
        value = {
            "id": switch.unique_id,
            "input1": service.data[ATTR_NAME_1],
            "input2": service.data[ATTR_NAME_2],
            "output1": service.data[ATTR_OUTPUT_NAME_1],
            "output2": service.data[ATTR_OUTPUT_NAME_2],
        }
        switch.set_input_output_names(value)
        switch.schedule_update_ha_state(True)

    def set_activation_service(service: ServiceCall) -> None:
        """Activate or deactivate Neviweb polling for missing device."""
        switch = get_switch(service)
        value = {"id": switch.unique_id, "active": service.data[ATTR_ACTIVE]}
        switch.set_activation(value)
        switch.schedule_update_ha_state(True)

    def set_remaining_time_service(service: ServiceCall) -> None:
        """Set coldLoadPickupRemainingTime value."""
        switch = get_switch(service)
        value = {
            "id": switch.unique_id,
            ATTR_TIME: service.data[ATTR_COLD_LOAD_PICKUP_REMAIN_TIME],
        }
        switch.set_remaining_time(value)
        switch.schedule_update_ha_state(True)

    def set_on_off_input_delay_service(service: ServiceCall) -> None:
        """Set input 1 or 2 on/off delay for MC3100ZB device."""
        switch = get_switch(service)
        value = {
            "id": switch.unique_id,
            "input_number": service.data[ATTR_INPUT_NUMBER],
            "onoff": service.data[ATTR_ONOFF],
            "delay": service.data[ATTR_DELAY][0],
        }
        switch.set_on_off_input_delay(value)
        switch.schedule_update_ha_state(True)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SWITCH_KEYPAD_LOCK,
        set_switch_keypad_lock_service,
        schema=SET_SWITCH_KEYPAD_LOCK_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SWITCH_TIMER,
        set_switch_timer_service,
        schema=SET_SWITCH_TIMER_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SWITCH_TIMER_2,
        set_switch_timer2_service,
        schema=SET_SWITCH_TIMER_2_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SWITCH_TEMP_ALERT,
        set_switch_temp_alert_service,
        schema=SET_SWITCH_TEMP_ALERT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_LOAD_DR_OPTIONS,
        set_load_dr_options_service,
        schema=SET_LOAD_DR_OPTIONS_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CONTROL_ONOFF,
        set_control_onoff_service,
        schema=SET_CONTROL_ONOFF_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TANK_SIZE,
        set_tank_size_service,
        schema=SET_TANK_SIZE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CONTROLLED_DEVICE,
        set_controlled_device_service,
        schema=SET_CONTROLLED_DEVICE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_LOW_TEMP_PROTECTION,
        set_low_temp_protection_service,
        schema=SET_LOW_TEMP_PROTECTION_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_INPUT_OUTPUT_NAMES,
        set_input_output_names_service,
        schema=SET_INPUT_OUTPUT_NAMES_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ACTIVATION,
        set_activation_service,
        schema=SET_ACTIVATION_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_REMAINING_TIME,
        set_remaining_time_service,
        schema=SET_REMAINING_TIME_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ON_OFF_INPUT_DELAY,
        set_on_off_input_delay_service,
        schema=SET_ON_OFF_INPUT_DELAY_SCHEMA,
    )
