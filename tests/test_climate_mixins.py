"""Unit tests for FloorMixin — Task 3.1 of the climate-refactor bugfix spec.

Validates:
- FloorMixin defines all four floor-specific methods
- Neviweb130FloorThermostat inherits them via FloorMixin
- Neviweb130WifiThermostat does NOT have set_floor_limit (ISP fix)
"""
import pytest

from custom_components.neviweb130.climate import (
    FloorMixin,
    Neviweb130FloorThermostat,
    Neviweb130WifiFloorThermostat,
    Neviweb130WifiThermostat,
)

FLOOR_METHODS = [
    "set_floor_limit",
    "set_air_floor_mode",
    "set_floor_air_limit",
    "set_sensor_type",
]


@pytest.mark.unit
class TestFloorMixinDefinition:
    """FloorMixin must define all four floor-specific methods."""

    def test_floor_mixin_has_set_floor_limit(self):
        assert "set_floor_limit" in FloorMixin.__dict__

    def test_floor_mixin_has_set_air_floor_mode(self):
        assert "set_air_floor_mode" in FloorMixin.__dict__

    def test_floor_mixin_has_set_floor_air_limit(self):
        assert "set_floor_air_limit" in FloorMixin.__dict__

    def test_floor_mixin_has_set_sensor_type(self):
        assert "set_sensor_type" in FloorMixin.__dict__

    def test_floor_mixin_has_all_four_methods(self):
        missing = [m for m in FLOOR_METHODS if m not in FloorMixin.__dict__]
        assert not missing, f"FloorMixin is missing methods: {missing}"


@pytest.mark.unit
class TestFloorThermostatInheritance:
    """Neviweb130FloorThermostat must inherit all four methods from FloorMixin."""

    def test_floor_thermostat_has_set_floor_limit(self):
        assert hasattr(Neviweb130FloorThermostat, "set_floor_limit")

    def test_floor_thermostat_has_set_air_floor_mode(self):
        assert hasattr(Neviweb130FloorThermostat, "set_air_floor_mode")

    def test_floor_thermostat_has_set_floor_air_limit(self):
        assert hasattr(Neviweb130FloorThermostat, "set_floor_air_limit")

    def test_floor_thermostat_has_set_sensor_type(self):
        assert hasattr(Neviweb130FloorThermostat, "set_sensor_type")

    def test_floor_thermostat_uses_floor_mixin(self):
        assert issubclass(Neviweb130FloorThermostat, FloorMixin)

    def test_wifi_floor_thermostat_has_all_floor_methods(self):
        missing = [m for m in FLOOR_METHODS if not hasattr(Neviweb130WifiFloorThermostat, m)]
        assert not missing, f"Neviweb130WifiFloorThermostat missing: {missing}"

    def test_wifi_floor_thermostat_uses_floor_mixin(self):
        assert issubclass(Neviweb130WifiFloorThermostat, FloorMixin)


@pytest.mark.unit
class TestWifiThermostatISP:
    """Neviweb130WifiThermostat must NOT have set_floor_limit (ISP compliance)."""

    def test_wifi_thermostat_no_set_floor_limit_in_dict(self):
        assert "set_floor_limit" not in Neviweb130WifiThermostat.__dict__, (
            "set_floor_limit must not be defined directly on Neviweb130WifiThermostat"
        )

    def test_wifi_thermostat_no_set_floor_limit_via_hasattr(self):
        assert not hasattr(Neviweb130WifiThermostat, "set_floor_limit"), (
            "Neviweb130WifiThermostat must not inherit set_floor_limit from any base class"
        )

    def test_wifi_thermostat_no_set_air_floor_mode(self):
        assert not hasattr(Neviweb130WifiThermostat, "set_air_floor_mode"), (
            "Neviweb130WifiThermostat must not have set_air_floor_mode"
        )

    def test_wifi_thermostat_no_set_floor_air_limit(self):
        assert not hasattr(Neviweb130WifiThermostat, "set_floor_air_limit"), (
            "Neviweb130WifiThermostat must not have set_floor_air_limit"
        )

    def test_wifi_thermostat_no_set_sensor_type(self):
        assert not hasattr(Neviweb130WifiThermostat, "set_sensor_type"), (
            "Neviweb130WifiThermostat must not have set_sensor_type"
        )


# ---------------------------------------------------------------------------
# Task 3.2 — LowVoltageMixin tests
# ---------------------------------------------------------------------------

from custom_components.neviweb130.climate import (
    LowVoltageMixin,
    Neviweb130LowThermostat,
    Neviweb130LowWifiThermostat,
    Neviweb130WifiThermostat,
)

LOW_VOLTAGE_METHODS = [
    "set_pump_protection",
    "set_aux_cycle_output",
    "set_cycle_output",
]


@pytest.mark.unit
class TestLowVoltageMixinDefinition:
    """LowVoltageMixin must define all three low-voltage-specific methods."""

    def test_low_voltage_mixin_has_set_pump_protection(self):
        assert "set_pump_protection" in LowVoltageMixin.__dict__

    def test_low_voltage_mixin_has_set_aux_cycle_output(self):
        assert "set_aux_cycle_output" in LowVoltageMixin.__dict__

    def test_low_voltage_mixin_has_set_cycle_output(self):
        assert "set_cycle_output" in LowVoltageMixin.__dict__

    def test_low_voltage_mixin_has_all_three_methods(self):
        missing = [m for m in LOW_VOLTAGE_METHODS if m not in LowVoltageMixin.__dict__]
        assert not missing, f"LowVoltageMixin is missing methods: {missing}"


@pytest.mark.unit
class TestLowThermostatInheritance:
    """Neviweb130LowThermostat must inherit all three methods from LowVoltageMixin."""

    def test_low_thermostat_has_set_pump_protection(self):
        assert hasattr(Neviweb130LowThermostat, "set_pump_protection")

    def test_low_thermostat_has_set_aux_cycle_output(self):
        assert hasattr(Neviweb130LowThermostat, "set_aux_cycle_output")

    def test_low_thermostat_has_set_cycle_output(self):
        assert hasattr(Neviweb130LowThermostat, "set_cycle_output")

    def test_low_thermostat_uses_low_voltage_mixin(self):
        assert issubclass(Neviweb130LowThermostat, LowVoltageMixin)

    def test_low_wifi_thermostat_has_all_low_voltage_methods(self):
        missing = [m for m in LOW_VOLTAGE_METHODS if not hasattr(Neviweb130LowWifiThermostat, m)]
        assert not missing, f"Neviweb130LowWifiThermostat missing: {missing}"

    def test_low_wifi_thermostat_uses_low_voltage_mixin(self):
        assert issubclass(Neviweb130LowWifiThermostat, LowVoltageMixin)


@pytest.mark.unit
class TestWifiThermostatLowVoltageISP:
    """Neviweb130WifiThermostat must NOT have set_pump_protection (ISP compliance)."""

    def test_wifi_thermostat_no_set_pump_protection_in_dict(self):
        assert "set_pump_protection" not in Neviweb130WifiThermostat.__dict__, (
            "set_pump_protection must not be defined directly on Neviweb130WifiThermostat"
        )

    def test_wifi_thermostat_no_set_pump_protection_via_hasattr(self):
        assert not hasattr(Neviweb130WifiThermostat, "set_pump_protection"), (
            "Neviweb130WifiThermostat must not inherit set_pump_protection from any base class"
        )

    def test_wifi_thermostat_no_set_aux_cycle_output(self):
        assert not hasattr(Neviweb130WifiThermostat, "set_aux_cycle_output"), (
            "Neviweb130WifiThermostat must not have set_aux_cycle_output"
        )

    def test_wifi_thermostat_no_set_cycle_output(self):
        assert not hasattr(Neviweb130WifiThermostat, "set_cycle_output"), (
            "Neviweb130WifiThermostat must not have set_cycle_output"
        )


# ---------------------------------------------------------------------------
# Task 3.3 — HeatPumpMixin tests
# ---------------------------------------------------------------------------

from custom_components.neviweb130.climate import (
    HeatPumpMixin,
    Neviweb130HPThermostat,
    Neviweb130Thermostat,
    Neviweb130WifiHPThermostat,
)

HEAT_PUMP_METHODS = [
    "set_fan_mode",
    "set_swing_mode",
    "set_swing_horizontal_mode",
    "set_display_config",
    "set_sound_config",
    "set_heat_pump_operation_limit",
    "set_heat_installation_type",
    "set_cool_lockout_temperature",
    "set_heat_lockout_temperature",
]


@pytest.mark.unit
class TestHeatPumpMixinDefinition:
    """HeatPumpMixin must define all HP-specific methods."""

    def test_heat_pump_mixin_has_set_fan_mode(self):
        assert "set_fan_mode" in HeatPumpMixin.__dict__

    def test_heat_pump_mixin_has_set_swing_mode(self):
        assert "set_swing_mode" in HeatPumpMixin.__dict__

    def test_heat_pump_mixin_has_set_swing_horizontal_mode(self):
        assert "set_swing_horizontal_mode" in HeatPumpMixin.__dict__

    def test_heat_pump_mixin_has_set_display_config(self):
        assert "set_display_config" in HeatPumpMixin.__dict__

    def test_heat_pump_mixin_has_set_sound_config(self):
        assert "set_sound_config" in HeatPumpMixin.__dict__

    def test_heat_pump_mixin_has_set_heat_pump_operation_limit(self):
        assert "set_heat_pump_operation_limit" in HeatPumpMixin.__dict__

    def test_heat_pump_mixin_has_set_heat_installation_type(self):
        assert "set_heat_installation_type" in HeatPumpMixin.__dict__

    def test_heat_pump_mixin_has_set_cool_lockout_temperature(self):
        assert "set_cool_lockout_temperature" in HeatPumpMixin.__dict__

    def test_heat_pump_mixin_has_set_heat_lockout_temperature(self):
        assert "set_heat_lockout_temperature" in HeatPumpMixin.__dict__

    def test_heat_pump_mixin_has_all_methods(self):
        missing = [m for m in HEAT_PUMP_METHODS if m not in HeatPumpMixin.__dict__]
        assert not missing, f"HeatPumpMixin is missing methods: {missing}"


@pytest.mark.unit
class TestHPThermostatInheritance:
    """Neviweb130HPThermostat must inherit all HP methods from HeatPumpMixin."""

    def test_hp_thermostat_has_set_fan_mode(self):
        assert hasattr(Neviweb130HPThermostat, "set_fan_mode")

    def test_hp_thermostat_has_set_swing_mode(self):
        assert hasattr(Neviweb130HPThermostat, "set_swing_mode")

    def test_hp_thermostat_has_set_swing_horizontal_mode(self):
        assert hasattr(Neviweb130HPThermostat, "set_swing_horizontal_mode")

    def test_hp_thermostat_has_set_display_config(self):
        assert hasattr(Neviweb130HPThermostat, "set_display_config")

    def test_hp_thermostat_has_set_sound_config(self):
        assert hasattr(Neviweb130HPThermostat, "set_sound_config")

    def test_hp_thermostat_uses_heat_pump_mixin(self):
        assert issubclass(Neviweb130HPThermostat, HeatPumpMixin)

    def test_wifi_hp_thermostat_has_all_hp_methods(self):
        missing = [m for m in HEAT_PUMP_METHODS if not hasattr(Neviweb130WifiHPThermostat, m)]
        assert not missing, f"Neviweb130WifiHPThermostat missing: {missing}"

    def test_wifi_hp_thermostat_uses_heat_pump_mixin(self):
        assert issubclass(Neviweb130WifiHPThermostat, HeatPumpMixin)


@pytest.mark.unit
class TestBaseThermostatHeatPumpISP:
    """Neviweb130Thermostat base class must NOT have HP-specific methods (ISP compliance)."""

    def test_base_thermostat_no_set_fan_mode(self):
        assert "set_fan_mode" not in Neviweb130Thermostat.__dict__, (
            "set_fan_mode must not be defined on Neviweb130Thermostat base class"
        )

    def test_base_thermostat_no_set_fan_mode_via_hasattr(self):
        # set_fan_mode is an HA ClimateEntity interface method — check it's not overridden in the base class
        assert "set_fan_mode" not in Neviweb130Thermostat.__dict__, (
            "Neviweb130Thermostat must not override set_fan_mode (HP-only method)"
        )

    def test_base_thermostat_no_set_swing_mode(self):
        # set_swing_mode is an HA ClimateEntity interface method — check it's not overridden in the base class
        assert "set_swing_mode" not in Neviweb130Thermostat.__dict__, (
            "Neviweb130Thermostat must not override set_swing_mode (HP-only method)"
        )

    def test_base_thermostat_no_set_swing_horizontal_mode(self):
        # set_swing_horizontal_mode is an HA ClimateEntity interface method — check it's not overridden in the base class
        assert "set_swing_horizontal_mode" not in Neviweb130Thermostat.__dict__, (
            "Neviweb130Thermostat must not override set_swing_horizontal_mode (HP-only method)"
        )

    def test_base_thermostat_no_set_display_config(self):
        assert not hasattr(Neviweb130Thermostat, "set_display_config"), (
            "Neviweb130Thermostat must not have set_display_config"
        )

    def test_base_thermostat_no_set_sound_config(self):
        assert not hasattr(Neviweb130Thermostat, "set_sound_config"), (
            "Neviweb130Thermostat must not have set_sound_config"
        )


# ---------------------------------------------------------------------------
# Task 3.4 — HeatCoolMixin tests
# ---------------------------------------------------------------------------

from custom_components.neviweb130.climate import (
    HeatCoolMixin,
    Neviweb130HeatCoolThermostat,
    Neviweb130Thermostat,
)

HEAT_COOL_METHODS = [
    "set_schedule_mode",
    "set_heatcool_setpoint_delta",
    "set_fan_filter_reminder",
    "set_temperature_offset",
    "set_aux_heating_source",
    "set_fan_speed",
    "set_humidity_mode",
    "set_heat_dissipation_time",
    "set_cool_dissipation_time",
    "set_reversing_valve_polarity",
    "set_min_time_on",
    "set_min_time_off",
    "set_heat_interstage_delay",
    "set_cool_interstage_delay",
    "set_aux_heat_start_delay",
    "set_accessory_type",
    "set_cool_setpoint_away",
    "set_cool_setpoint_max",
    "set_cool_setpoint_min",
]


@pytest.mark.unit
class TestHeatCoolMixinDefinition:
    """HeatCoolMixin must define all heat/cool-specific methods."""

    def test_heat_cool_mixin_has_set_schedule_mode(self):
        assert "set_schedule_mode" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_heatcool_setpoint_delta(self):
        assert "set_heatcool_setpoint_delta" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_fan_filter_reminder(self):
        assert "set_fan_filter_reminder" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_temperature_offset(self):
        assert "set_temperature_offset" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_aux_heating_source(self):
        assert "set_aux_heating_source" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_fan_speed(self):
        assert "set_fan_speed" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_humidity_mode(self):
        assert "set_humidity_mode" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_heat_dissipation_time(self):
        assert "set_heat_dissipation_time" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_cool_dissipation_time(self):
        assert "set_cool_dissipation_time" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_reversing_valve_polarity(self):
        assert "set_reversing_valve_polarity" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_min_time_on(self):
        assert "set_min_time_on" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_min_time_off(self):
        assert "set_min_time_off" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_heat_interstage_delay(self):
        assert "set_heat_interstage_delay" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_cool_interstage_delay(self):
        assert "set_cool_interstage_delay" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_aux_heat_start_delay(self):
        assert "set_aux_heat_start_delay" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_accessory_type(self):
        assert "set_accessory_type" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_cool_setpoint_away(self):
        assert "set_cool_setpoint_away" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_cool_setpoint_max(self):
        assert "set_cool_setpoint_max" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_set_cool_setpoint_min(self):
        assert "set_cool_setpoint_min" in HeatCoolMixin.__dict__

    def test_heat_cool_mixin_has_all_methods(self):
        missing = [m for m in HEAT_COOL_METHODS if m not in HeatCoolMixin.__dict__]
        assert not missing, f"HeatCoolMixin is missing methods: {missing}"


@pytest.mark.unit
class TestHeatCoolThermostatInheritance:
    """Neviweb130HeatCoolThermostat must inherit all methods from HeatCoolMixin."""

    def test_heat_cool_thermostat_has_set_schedule_mode(self):
        assert hasattr(Neviweb130HeatCoolThermostat, "set_schedule_mode")

    def test_heat_cool_thermostat_uses_heat_cool_mixin(self):
        assert issubclass(Neviweb130HeatCoolThermostat, HeatCoolMixin)

    def test_heat_cool_thermostat_has_all_heat_cool_methods(self):
        missing = [m for m in HEAT_COOL_METHODS if not hasattr(Neviweb130HeatCoolThermostat, m)]
        assert not missing, f"Neviweb130HeatCoolThermostat missing: {missing}"

    def test_heat_cool_thermostat_set_schedule_mode_from_mixin(self):
        """set_schedule_mode must come from HeatCoolMixin, not defined directly on the subclass."""
        assert "set_schedule_mode" not in Neviweb130HeatCoolThermostat.__dict__, (
            "set_schedule_mode should be inherited from HeatCoolMixin, not redefined on the subclass"
        )


@pytest.mark.unit
class TestBaseThermostatHeatCoolISP:
    """Neviweb130Thermostat base class must NOT have heat/cool-specific methods (ISP compliance)."""

    def test_base_thermostat_no_set_schedule_mode(self):
        assert "set_schedule_mode" not in Neviweb130Thermostat.__dict__, (
            "set_schedule_mode must not be defined on Neviweb130Thermostat base class"
        )

    def test_base_thermostat_no_set_schedule_mode_via_hasattr(self):
        assert not hasattr(Neviweb130Thermostat, "set_schedule_mode"), (
            "Neviweb130Thermostat must not inherit set_schedule_mode from any base class"
        )

    def test_base_thermostat_no_set_cool_setpoint_max(self):
        assert "set_cool_setpoint_max" not in Neviweb130Thermostat.__dict__, (
            "set_cool_setpoint_max must not be defined on Neviweb130Thermostat base class"
        )

    def test_base_thermostat_no_set_cool_setpoint_max_via_hasattr(self):
        assert not hasattr(Neviweb130Thermostat, "set_cool_setpoint_max"), (
            "Neviweb130Thermostat must not have set_cool_setpoint_max"
        )

    def test_base_thermostat_no_set_cool_setpoint_min(self):
        assert "set_cool_setpoint_min" not in Neviweb130Thermostat.__dict__, (
            "set_cool_setpoint_min must not be defined on Neviweb130Thermostat base class"
        )

    def test_base_thermostat_no_set_cool_setpoint_min_via_hasattr(self):
        assert not hasattr(Neviweb130Thermostat, "set_cool_setpoint_min"), (
            "Neviweb130Thermostat must not have set_cool_setpoint_min"
        )

    def test_base_thermostat_no_set_cool_setpoint_away(self):
        assert "set_cool_setpoint_away" not in Neviweb130Thermostat.__dict__, (
            "set_cool_setpoint_away must not be defined on Neviweb130Thermostat base class"
        )

    def test_base_thermostat_no_set_cool_setpoint_away_via_hasattr(self):
        assert not hasattr(Neviweb130Thermostat, "set_cool_setpoint_away"), (
            "Neviweb130Thermostat must not have set_cool_setpoint_away"
        )
