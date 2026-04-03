"""Climate mixins, helper functions, and error handlers for neviweb130 thermostats."""
from __future__ import annotations

import logging
import time
from typing import Callable, override

from homeassistant.components.climate.const import HVACMode
from homeassistant.exceptions import ServiceValidationError

from ..const import (
    ATTR_AIR_EX_MIN_TIME_ON,
    ATTR_AUX_HEAT_MIN_TIME_OFF,
    ATTR_AUX_HEAT_MIN_TIME_ON,
    ATTR_AUX_HEAT_SOURCE_TYPE,
    ATTR_COOL_MIN_TIME_OFF,
    ATTR_COOL_MIN_TIME_ON,
    ATTR_HEAT_MIN_TIME_OFF,
    ATTR_HEAT_MIN_TIME_ON,
    ATTR_POLARITY,
    ATTR_TIME,
    ATTR_TYPE,
    DOMAIN,
)
from ..helpers import translated_or_default
from ..schema import AUX_HEATING, CYCLE_LENGTH_VALUES, FAN_SPEED_VALUES, FAN_SPEED_VALUES_5, FULL_SWING_OFF
from .. import NOTIFY

_LOGGER = logging.getLogger(__name__)

def neviweb_to_ha(value: int) -> str:
    last = ""
    for k, v in sorted(CYCLE_LENGTH_VALUES.items(), key=lambda x: x[1]):
        last = k
        if value <= v:
            return k
    return last


def lock_to_ha(lock: str) -> str:
    """Convert keypad lock state to better description."""
    match lock:
        case "locked":
            return "Locked"
        case "lock":
            return "Locked"
        case "partiallyLocked":
            return "Tamper protection"
        case "partialLock":
            return "Tamper protection"
    return "Unlocked"


def neviweb_to_ha_fan(value: int, model: int) -> str:
    """Return fanSpeed value for model 6813 or 6814."""
    if model == 6813:
        mapping = FAN_SPEED_VALUES
    elif model == 6814:
        mapping = FAN_SPEED_VALUES_5
    else:
        raise ValueError(f"model not supported: {model}")

    last = ""
    for k, v in sorted(mapping.items(), key=lambda x: x[1]):
        last = k
        if value <= v:
            return k
    return last


def neviweb_to_ha_mode(mode: str) -> HVACMode:
    """Convert Neviweb mode string to HVACMode for HP6000WF-xx thermostats."""
    hvac = NEVIWEB_TO_HA_MODE.get(mode)
    if hvac is None:
        raise ValueError(f"Unknown Neviweb HVAC mode: {mode}")
    return hvac


def extract_capability_full(cap):
    """Extract swing capability which are True for each HP device and add general capability."""
    value = {i for i in cap if cap[i] is True}
    return FULL_SWING_OFF + sorted(value)


def extract_capability(cap):
    """Extract capability which are True for each HP device."""
    if not cap:
        return []
    value = {i for i in cap if cap[i] is True}
    return sorted(value)


def resolve_fan_speed(speed: str, model: int) -> int:
    normalized = speed.strip().lower()
    source = FAN_SPEED_VALUES if model == 6813 else FAN_SPEED_VALUES_5
    mapping = {k.lower(): v for k, v in source.items()}

    if normalized not in mapping:
        raise ValueError(f"Invalid fan mode '{speed}'")

    value = mapping[normalized]

    if model == 6813 and value == 0:
        raise ValueError("Model 6813 does not support 'off'")

    return value


class _BlockedMethod:
    """Descriptor that blocks an inherited method on a subclass (ISP enforcement).

    When a subclass defines ``attr = _BlockedMethod()``, ``hasattr(SubClass, attr)``
    returns ``False`` and any attempt to call the method raises ``AttributeError``.
    This lets the base class keep a method for classes that need it while
    explicitly excluding subclasses that must not expose it.
    """

    def __set_name__(self, owner, name):
        self._name = name

    def __get__(self, obj, objtype=None):
        raise AttributeError(
            f"'{objtype.__name__ if objtype else type(obj).__name__}' "
            f"has no attribute '{self._name}' (ISP: not applicable to this subclass)"
        )


class FloorMixin:
    """Mixin for floor thermostat-specific methods (ISP: only floor subclasses inherit these)."""

    def set_floor_limit(self, value):
        """Set maximum/minimum floor setpoint temperature."""
        temp = value["level"]
        limit = value["limit"]
        if limit == "low":
            if 0 < temp < 5:
                temp = 5
        else:
            if 0 < temp < 7:
                temp = 7
        self._client.set_floor_limit(value["id"], temp, limit, self._is_wifi_floor)
        if limit == "low":
            self._floor_min = temp if temp != 0 else None
            self._floor_min_status = "on"
        else:
            self._floor_max = temp if temp != 0 else None
            self._floor_max_status = "on"

    def set_air_floor_mode(self, value):
        """Switch temperature control between floor and ambient sensor."""
        self._client.set_air_floor_mode(value["id"], value["mode"])
        self._floor_mode = value["mode"]

    def set_floor_air_limit(self, value):
        """Set maximum temperature air limit for floor thermostat."""
        if value["temp"] == 0:
            status = "off"
        else:
            status = "on"
        self._client.set_floor_air_limit(value["id"], status, value["temp"])
        self._floor_air_limit = value["temp"]

    def set_sensor_type(self, value):
        """Set sensor type."""
        self._client.set_sensor_type(value["id"], value["type"])
        self._floor_sensor_type = value["type"]


class LowVoltageMixin:
    """Mixin for low-voltage thermostat-specific methods (ISP: only low-voltage subclasses inherit these)."""

    def set_aux_cycle_output(self, value):
        """Set low voltage thermostats auxiliary cycle status and length."""
        length: int = CYCLE_LENGTH_VALUES[value["val"]]
        is_wifi = self._is_low_wifi or (self._is_wifi and self._is_HC)
        if is_wifi and length == 0:
            raise ServiceValidationError(
                translated_or_default(
                    self.hass,
                    "no_off_value",
                    f"No off value for entity {self.entity_id}",
                    entity=self.entity_id,
                )
            )
        self._client.set_aux_cycle_output(value["id"], length, is_wifi)
        if is_wifi:
            self._aux_cycle_length = length
        elif length > 0:
            self._cycle_length_output2_status = "on"
            self._cycle_length_output2_value = length
        else:
            # Leaving self._cycle_length_output2_value to the old value on purpose
            self._cycle_length_output2_status = "off"

    def set_cycle_output(self, value):
        """Set low voltage thermostats main cycle output length."""
        length: int = CYCLE_LENGTH_VALUES[value["val"]]
        if length == 0:
            raise ServiceValidationError(
                translated_or_default(
                    self.hass,
                    "no_off_value",
                    f"No off value for entity {self.entity_id}",
                    entity=self.entity_id,
                )
            )
        self._client.set_cycle_output(value["id"], length, self._is_HC)
        self._cycle_length = length

    def set_pump_protection(self, value):
        """Set pump protection value."""
        self._client.set_pump_protection(value["id"], value["status"], self._is_low_wifi)
        self._pump_protec_status = value["status"]
        self._pump_protec_duration = 60
        self._pump_protec_period = 1


class HeatPumpMixin:
    """Mixin for heat-pump thermostat-specific methods (ISP: only HP subclasses inherit these)."""

    @override
    def set_fan_mode(self, speed: str) -> None:
        """Set new fan mode."""
        if speed is None:
            return

        speed_val = speed
        if self._is_WHP:
            try:
                speed_val = str(resolve_fan_speed(speed, self._device_model))
            except ValueError:
                raise ServiceValidationError(
                    translated_or_default(
                        self.hass,
                        "fan_mode_not_supported",
                        f"Fan mode not supported for model {self._device_model} (off)",
                        model=self._device_model,
                        mode="off",
                    )
                )

        self._client.set_fan_mode(self._id, speed_val)
        self._fan_speed = speed

    @override
    def set_swing_mode(self, swing: str) -> None:
        """Set new vertical swing mode."""
        if swing is None:
            return
        else:
            self._client.set_swing_vertical(self._id, swing)
            self._fan_swing_vert = swing

    @override
    def set_swing_horizontal_mode(self, swing: str) -> None:
        """Set new horizontal swing mode."""
        if swing is None:
            return
        else:
            self._client.set_swing_horizontal(self._id, swing)
            self._fan_swing_horiz = swing

    def set_display_config(self, value):
        """Set display on/off for heat pump."""
        self._client.set_hp_display(value["id"], value["display"])
        self._display_conf = value["display"]

    def set_sound_config(self, value):
        """Set sound on/off for heat pump."""
        self._client.set_hp_sound(value["id"], value["sound"])
        self._sound_conf = value["sound"]

    def set_heat_pump_operation_limit(self, value):
        """Set minimum temperature for heat pump operation."""
        temp = value["temp"]
        if temp < self._balance_pt_low:
            temp = self._balance_pt_low
        self._client.set_heat_pump_limit(value["id"], temp)
        self._balance_pt = temp

    def set_heat_installation_type(self, value):
        """Set heat installation type for heat pump."""
        type_val = value[ATTR_TYPE]
        self._client.set_heat_installation_type(self.unique_id, type_val)
        self._heat_installation_type = type_val

    def set_cool_lockout_temperature(self, value):
        """Set minimum outside temperature limit to allow cooling device operation."""
        self._client.set_cool_lockout(value["id"], value["temp"])
        self._cool_lockout_temp = value["temp"]

    def set_heat_lockout_temperature(self, value):
        """Set maximum outside temperature limit to allow heating device operation."""
        self._client.set_heat_lockout(value["id"], value["temp"], self._is_gen2)
        self._heat_lockout_temp = value["temp"]


class HeatCoolMixin:
    """Mixin for heat/cool thermostat-specific methods (ISP: only TH6xxx subclasses inherit these)."""

    def set_schedule_mode(self, value):
        """Set schedule mode, manual or auto."""
        self._client.set_schedule_mode(value["id"], value["mode"], self._is_HC)
        self._operation_mode = value["mode"]

    def set_heatcool_setpoint_delta(self, value):
        """Set delta temperature between heating and cooling setpoint from 1 to 5°C."""
        self._client.set_heatcool_delta(value["id"], value["level"], self._is_HC)
        self._heatcool_setpoint_delta = value["level"]

    def set_fan_filter_reminder(self, value):
        """Set fan filter reminder period from 1 to 12 month."""
        self._client.set_fan_filter_reminder(value["id"], value["month"], self._is_HC)
        self._fan_filter_remain = value["month"]

    def set_temperature_offset(self, value):
        """Set thermostat sensor offset from -2 to 2°C with a 0.5°C increment."""
        self._client.set_temperature_offset(value["id"], value["temp"], self._is_HC)
        self._temp_offset_heat = value["temp"]

    def set_aux_heating_source(self, value):
        """Set auxiliary heating device."""
        equip = AUX_HEATING.get(value[ATTR_AUX_HEAT_SOURCE_TYPE])
        if equip is None:
            raise ServiceValidationError(
                translated_or_default(
                    self.hass,
                    "invalid_value",
                    f"Invalid value for {ATTR_AUX_HEAT_SOURCE_TYPE}, must be one of {AUX_HEATING.keys()}.",
                    param=ATTR_AUX_HEAT_SOURCE_TYPE,
                    value=AUX_HEATING.keys(),
                )
            )

        self._client.set_aux_heating_source(value["id"], equip)
        self._aux_heat_source_type = equip

    def set_fan_speed(self, value):
        """Set fan speed On or Auto."""
        self._client.set_fan_mode(value["id"], value["speed"])
        self._fan_speed = value["speed"]

    def set_humidity_mode(self, value):
        """Set thermostat humidity setpoint mode, defog or manual"""
        self._client.set_humidity_mode(value["id"], value["mode"], self._is_HC)
        self._humidity_setpoint_mode = value["mode"]

    def set_heat_dissipation_time(self, value):
        """Set device heat dissipation time."""
        self._client.set_heat_dissipation_time(value["id"], value[ATTR_TIME], self._is_HC)
        self._cool_purge_time = value[ATTR_TIME]

    def set_cool_dissipation_time(self, value):
        """Set device cool dissipation time."""
        self._client.set_cool_dissipation_time(value["id"], value[ATTR_TIME], self._is_HC)
        self._heat_purge_time = value[ATTR_TIME]

    def set_reversing_valve_polarity(self, value):
        """Set reversing valve polarity."""
        polarity = value[ATTR_POLARITY]
        self._client.set_reversing_valve_polarity(self.unique_id, polarity)
        self._reversing_valve_polarity = polarity

    def set_min_time_on(self, value):
        """Set minimum time the device is on before letting be off again (run-on time)"""
        heat_min_time_on = value.get(ATTR_HEAT_MIN_TIME_ON)
        cool_min_time_on = value.get(ATTR_COOL_MIN_TIME_ON)
        aux_heat_min_time_on = value.get(ATTR_AUX_HEAT_MIN_TIME_ON)
        air_ex_min_time_on = value.get(ATTR_AIR_EX_MIN_TIME_ON)

        if heat_min_time_on is not None:
            self._client.set_heat_min_time_on(self.unique_id, heat_min_time_on)
            self._heat_min_time_on = heat_min_time_on
        if cool_min_time_on is not None:
            self._client.set_cool_min_time_on(self.unique_id, cool_min_time_on)
            self._cool_min_time_on = cool_min_time_on
        if aux_heat_min_time_on is not None:
            self._client.set_aux_heat_min_time_on(self.unique_id, aux_heat_min_time_on)
            self._aux_heat_min_time_on = aux_heat_min_time_on
        if air_ex_min_time_on is not None:
            self._client.set_air_ex_min_time_on(self.unique_id, air_ex_min_time_on)
            self._air_ex_min_time_on = air_ex_min_time_on

    def set_min_time_off(self, value):
        """Set minimum time the device is off before letting it be on again (cooldown time)"""
        heat_min_time_off = value.get(ATTR_HEAT_MIN_TIME_OFF)
        cool_min_time_off = value.get(ATTR_COOL_MIN_TIME_OFF)
        aux_heat_min_time_off = value.get(ATTR_AUX_HEAT_MIN_TIME_OFF)

        if heat_min_time_off is not None:
            self._client.set_heat_min_time_off(self.unique_id, heat_min_time_off)
            self._heat_min_time_off = heat_min_time_off
        if cool_min_time_off is not None:
            self._client.set_cool_min_time_off(self.unique_id, cool_min_time_off)
            self._cool_min_time_off = cool_min_time_off
        if aux_heat_min_time_off is not None:
            self._client.set_aux_heat_min_time_off(self.unique_id, aux_heat_min_time_off)
            self._aux_heat_min_time_off = aux_heat_min_time_off

    def set_heat_interstage_delay(self, value):
        try:
            time_val = int(value[ATTR_TIME])
        except KeyError:
            raise ServiceValidationError(
                translated_or_default(
                    self.hass,
                    "missing_parameter",
                    f"Missing parameter {ATTR_TIME}.",
                    param=ATTR_TIME,
                )
            )
        except ValueError:
            raise ServiceValidationError(
                translated_or_default(
                    self.hass,
                    "integer_needed",
                    f"Invalid value for {ATTR_TIME}, must be an integer.",
                    param=ATTR_TIME,
                )
            )

        outputs = self._output_connect_state
        hp_can_heat = self._reversing_valve_polarity == "cooling" or outputs["OB"]
        has_multiple_hp_heat_stages = outputs["Y1"] and outputs["Y2"] and hp_can_heat
        has_multiple_aux_stages = outputs["W"] and outputs["W2"]
        if not has_multiple_hp_heat_stages and not has_multiple_aux_stages:
            raise ServiceValidationError(
                translated_or_default(
                    self.hass,
                    "multiple_heating_level",
                    f"Entity {self.entity_id} does not support multiple levels of heating with current configuration.",
                    entity=self.entity_id,
                )
            )

        if has_multiple_hp_heat_stages:
            self._client.set_heat_interstage_min_delay(self.unique_id, time_val * 60)
            self._client.set_heat_interstage_delay(self.unique_id, time_val * 60 * 2)
        if has_multiple_aux_stages:
            self._client.set_aux_interstage_min_delay(self.unique_id, time_val * 60)
            self._client.set_aux_interstage_delay(self.unique_id, time_val * 60 * 2)

    def set_cool_interstage_delay(self, value):
        try:
            time_val = int(value[ATTR_TIME])
        except KeyError:
            raise ServiceValidationError(
                translated_or_default(
                    self.hass,
                    "missing_parameter",
                    f"Missing required parameter: {ATTR_TIME}.",
                    param=ATTR_TIME,
                )
            )
        except ValueError:
            raise ServiceValidationError(
                translated_or_default(
                    self.hass,
                    "integer_needed",
                    f"Invalid value for {ATTR_TIME}, must be an integer.",
                    param=ATTR_TIME,
                )
            )

        outputs = self._output_connect_state
        hp_can_cool = self._reversing_valve_polarity == "heating" or outputs["OB"]
        has_multiple_cooling_stages = outputs["Y1"] and outputs["Y2"] and hp_can_cool
        if not has_multiple_cooling_stages:
            raise ServiceValidationError(
                translated_or_default(
                    self.hass,
                    "multiple_cooling_level",
                    f"Entity {self.entity_id} does not support multiple levels of cooling with current configuration.",
                    entity=self.entity_id,
                )
            )

        self._client.set_cool_interstage_min_delay(self.unique_id, time_val * 60)
        self._client.set_cool_interstage_delay(self.unique_id, time_val * 60 * 2)

    def set_aux_heat_start_delay(self, value):
        try:
            time_val = float(value[ATTR_TIME])
        except KeyError:
            raise ServiceValidationError(
                translated_or_default(
                    self.hass,
                    "missing_parameter",
                    f"Missing required parameter: {ATTR_TIME}.",
                    param=ATTR_TIME,
                )
            )
        except ValueError:
            raise ServiceValidationError(
                translated_or_default(
                    self.hass,
                    "float_needed",
                    f"Invalid value for {ATTR_TIME}, must be a float.",
                    param=ATTR_TIME,
                )
            )

        outputs = self._output_connect_state
        hp_can_heat = (outputs["Y1"] or outputs["Y2"]) and (
            self._reversing_valve_polarity == "cooling" or outputs["OB"]
        )
        has_aux_heating = outputs["W"] or outputs["W2"]
        if not hp_can_heat or not has_aux_heating:
            raise ServiceValidationError(
                translated_or_default(
                    self.hass,
                    "missing_functionality",
                    f"Entity {self.entity_id} does not have both a heat pump and an auxiliary heater.",
                    entity=self.entity_id,
                )
            )

        self._client.set_aux_heat_start_delay(self.unique_id, time_val)

    def set_accessory_type(self, value):
        """Set accessory (humidifier, dehumidifier, air exchanger, heat accumulator) type for TH6500WF."""
        self._client.set_accessory_type(value["id"], value["type"])
        self._accessory_type = value["type"]

    def set_cool_setpoint_away(self, value):
        """Set device away cooling setpoint."""
        self._client.set_cool_setpoint_away(value["id"], value["temp"], self._is_HC)
        self._cool_target_temp_away = value["temp"]

    def set_cool_setpoint_max(self, value):
        """Set maximum cooling setpoint temperature."""
        self._client.set_cool_setpoint_max(value["id"], value["temp"])
        self._cool_max = value["temp"]

    def set_cool_setpoint_min(self, value):
        """Set minimum cooling setpoint temperature."""
        self._client.set_cool_setpoint_min(value["id"], value["temp"])
        self._cool_min = value["temp"]

    def set_heat_installation_type(self, value):
        """Set heat installation type for heat/cool thermostat."""
        type_val = value[ATTR_TYPE]
        self._client.set_heat_installation_type(self.unique_id, type_val)
        self._heat_installation_type = type_val

    @override
    def set_fan_mode(self, speed: str) -> None:
        """Set new fan mode for heat/cool thermostat."""
        if speed is None:
            return
        self._client.set_fan_mode(self._id, speed)
        self._fan_speed = speed


# ---------------------------------------------------------------------------
# Module-level error handler functions (one per API error code)
# ---------------------------------------------------------------------------

def _handle_session_expired(entity) -> None:
    """Handle USRSESSEXP — session expired, reconnect."""
    _LOGGER.warning("Session expired... Reconnecting...")
    if NOTIFY == "notification" or NOTIFY == "both":
        entity.notify_ha(
            translated_or_default(
                entity.hass,
                "usr_session",
                (
                    "Warning: Got USRSESSEXP error, Neviweb session expired.\n"
                    "Set your scan_interval parameter to less than 10 minutes to avoid this...\n"
                    "Reconnecting..."
                ),
            )
        )
    entity._client.reconnect()


def _handle_day_req_max(entity) -> None:
    """Handle ACCDAYREQMAX — daily request limit reached."""
    _LOGGER.warning("Maximum daily request reached... Reduce polling frequency")


def _handle_timeout_error(entity) -> None:
    """Handle TimeoutError — transient timeout."""
    _LOGGER.warning("Timeout error detected... Retry later")


def _handle_maintenance(entity) -> None:
    """Handle MAINTENANCE — Neviweb blocked for maintenance."""
    _LOGGER.warning("Access blocked for maintenance... Retry later")
    entity.notify_ha(
        translated_or_default(
            entity.hass,
            "maintenance",
            "Warning: Neviweb access temporary blocked for maintenance... Retry later.",
        )
    )
    entity._client.reconnect()


def _handle_session_exceeded(entity) -> None:
    """Handle ACCSESSEXC — maximum session count reached."""
    _LOGGER.warning("Maximum session number reached... Close other connections and try again")
    entity.notify_ha(
        translated_or_default(
            entity.hass,
            "access_limit",
            (
                "Warning: ACCSESSEXC maximum Neviweb session number reached... \n"
                "Close other connections and try again."
            ),
        )
    )
    entity._client.reconnect()


def _handle_attr_not_supported(entity) -> None:
    """Handle DVCATTRNSPTD — device attribute not supported."""
    _LOGGER.warning(
        "Device attribute not supported for %s (id: %s): DVCATTRNSPTD... (SKU: %s)",
        entity._name,
        str(entity._id),
        entity._sku,
    )
    safe_mode = entity.hass.data[DOMAIN]["safe_mode"]
    if safe_mode == "-":
        _LOGGER.warning(
            translated_or_default(
                entity.hass,
                "safe_mode_enabled",
                (
                    f"Auto-enabling safe mode for device {entity._name} (id: {entity._id}) "
                    "due to unsupported action."
                ),
                name=entity._name,
                id=entity._id,
            )
        )
        entity.hass.data[DOMAIN]["safe_mode"] = entity._id


def _handle_action_not_supported(entity) -> None:
    """Handle DVCACTNSPTD — device action not supported."""
    _LOGGER.warning(
        "Device action not supported for %s... (id: %s, SKU: %s), (Model: %s). Report to maintainer",
        entity._name,
        str(entity._id),
        entity._sku,
        str(entity._device_model),
    )
    safe_mode = entity.hass.data[DOMAIN]["safe_mode"]
    if safe_mode == "-":
        _LOGGER.warning(
            translated_or_default(
                entity.hass,
                "safe_mode_enabled",
                (
                    f"Auto-enabling safe mode for device {entity._name} (id: {entity._id}) "
                    "due to unsupported action."
                ),
                name=entity._name,
                id=entity._id,
            )
        )
        entity.hass.data[DOMAIN]["safe_mode"] = entity._id


def _handle_comm_timeout(entity) -> None:
    """Handle DVCCOMMTO — device communication timeout."""
    _LOGGER.warning(
        "Device Communication Timeout... The device %s (id: %s) "
        "did not respond to the server within the prescribed delay (SKU: %s)",
        entity._name,
        str(entity._id),
        entity._sku,
    )


def _handle_service_error(entity) -> None:
    """Handle SVCERR — service error, device temporarily unavailable."""
    _LOGGER.warning(
        "Service error, device not available retry later %s: SVCERR... (id: %s, SKU: %s)",
        entity._name,
        str(entity._id),
        entity._sku,
    )


def _handle_device_busy(entity) -> None:
    """Handle DVCBUSY — device busy (e.g. Neviweb update in progress)."""
    _LOGGER.warning(
        "Device busy can't reach (neviweb update ?), retry later %s (id: %s): DVCBUSY... (SKU: %s)",
        entity._name,
        str(entity._id),
        entity._sku,
    )


def _handle_device_unavailable(entity) -> None:
    """Handle DVCUNVLB — device disconnected from Neviweb."""
    _LOGGER.warning("NOTIFY value: %s, (SKU: %s)", NOTIFY, entity._sku)
    if NOTIFY == "logging" or NOTIFY == "both":
        _LOGGER.warning(
            "Device %s (id: %s) is disconnected from Neviweb: DVCUNVLB... (SKU: %s)",
            entity._name,
            str(entity._id),
            entity._sku,
        )
        _LOGGER.warning(
            "This device %s is de-activated and won't be updated for 20 minutes",
            entity._name,
        )
        _LOGGER.warning(
            "You can re-activate device %s with "
            "service.neviweb130_set_activation or wait 20 minutes "
            "for update to restart or just restart HA",
            entity._name,
        )
    if NOTIFY == "notification" or NOTIFY == "both":
        entity.notify_ha(
            translated_or_default(
                entity.hass,
                "update_stopped",
                f"Update for {entity._name}, {entity._id} ({entity._sku}), is stopped for 20 minutes",
                name=entity._name,
                id=entity._id,
                sku=entity._sku,
            )
        )
    entity._active = False
    entity._snooze = time.time()


def _handle_device_error(entity) -> None:
    """Handle DVCERR — device error (service already active)."""
    _LOGGER.warning(
        "Device error for %s (id: %s), service already active: DVCERR... (SKU: %s)",
        entity._name,
        str(entity._id),
        entity._sku,
    )


def _handle_service_unauthorized(entity) -> None:
    """Handle SVCUNAUTH — service not authorised for this device."""
    _LOGGER.warning(
        "Service not authorised for device %s (id: %s): SVCUNAUTH... (SKU: %s)",
        entity._name,
        str(entity._id),
        entity._sku,
    )


# Lookup table mapping API error codes to their handler functions.
# Add new error codes here without modifying log_error() (OCP).
ERROR_HANDLERS: dict[str, Callable] = {
    "USRSESSEXP": _handle_session_expired,
    "ACCDAYREQMAX": _handle_day_req_max,
    "TimeoutError": _handle_timeout_error,
    "MAINTENANCE": _handle_maintenance,
    "ACCSESSEXC": _handle_session_exceeded,
    "DVCATTRNSPTD": _handle_attr_not_supported,
    "DVCACTNSPTD": _handle_action_not_supported,
    "DVCCOMMTO": _handle_comm_timeout,
    "SVCERR": _handle_service_error,
    "DVCBUSY": _handle_device_busy,
    "DVCUNVLB": _handle_device_unavailable,
    "DVCERR": _handle_device_error,
    "SVCUNAUTH": _handle_service_unauthorized,
}


