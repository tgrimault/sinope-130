"""Constants for neviweb130 component."""

DOMAIN = "neviweb130"
CONF_NETWORK = 'network'
CONF_HOMEKIT_MODE = 'homekit_mode'

ATTR_ALERT = "alert"
ATTR_SIGNATURE = "signature"
ATTR_POWER_MODE = "powerMode"
ATTR_ONOFF = "onOff"
ATTR_ONOFF2 = "onOff2"
ATTR_INTENSITY = "intensity"
ATTR_INTENSITY_MIN = "intensityMin"
ATTR_WATTAGE = "loadConnected"
ATTR_WATTAGE_INSTANT = "wattageInstant"
ATTR_WATTAGE_OVERRIDE = "wattageOverride"
ATTR_SETPOINT_MODE = "setpointMode"
ATTR_ROOM_SETPOINT = "roomSetpoint"
ATTR_ROOM_SETPOINT_AWAY = "roomSetpointAway"
ATTR_ROOM_TEMPERATURE = "roomTemperature"
ATTR_OUTPUT_PERCENT_DISPLAY = "outputPercentDisplay"
ATTR_ROOM_SETPOINT_MIN = "roomSetpointMin"
ATTR_ROOM_SETPOINT_MAX = "roomSetpointMax"
ATTR_GFCI_STATUS = "gfciStatus"
ATTR_GFCI_ALERT = "alertGfci"
ATTR_WATER_LEAK_STATUS = "waterLeakStatus"
ATTR_BATTERY_VOLTAGE = "batteryVoltage"
ATTR_BATTERY_STATUS = "batteryStatus"
ATTR_BATTERY_TYPE = "batteryType"
ATTR_LEVEL_STATUS = "tankLevelPercent"
ATTR_FLOOR_MODE = "airFloorMode"
ATTR_FLOOR_OUTPUT2 = "loadWattOutput2" #status on/off, value=xx
ATTR_FLOOR_AUX = "auxHeatConfig"
ATTR_KEYPAD = "lockKeypad"
ATTR_OCCUPANCY = "occupancyMode"
ATTR_FLOOR_OUTPUT1 = "loadWattOutput1" #status on/off, value=xx
ATTR_LIGHT_WATTAGE = "loadWattOutput1" #status on/off, value=xx
ATTR_WIFI_WATTAGE = "loadWatt"
ATTR_WIFI = "wifiRssi"
ATTR_RSSI = "rssi"
ATTR_DISPLAY2 = "config2ndDisplay"
ATTR_WIFI_KEYPAD = "keyboardLock"
ATTR_TIMER = "powerTimer"
ATTR_TIMER2 = "powerTimer2"
ATTR_DRSTATUS = "drStatus"
ATTR_BACKLIGHT = "backlightAdaptive"
ATTR_BACKLIGHT_AUTO_DIM = "backlightAutoDim"
ATTR_LED_ON_INTENSITY = "statusLedOnIntensity"
ATTR_LED_OFF_INTENSITY = "statusLedOffIntensity"
ATTR_LED_ON_COLOR = "statusLedOnColor"
ATTR_LED_OFF_COLOR = "statusLedOffColor"
ATTR_STATE = "state"
ATTR_RED = "red"
ATTR_GREEN = "green"
ATTR_BLUE = "blue"
ATTR_TIME = "timeFormat"
ATTR_TEMP = "temperatureFormat"
ATTR_MOTOR_POS = "motorPosition"
ATTR_TEMP_ALARM = "temperatureAlarmStatus"
ATTR_ROOM_TEMP_ALARM = "roomTemperatureAlarmStatus"
ATTR_VALVE_CLOSURE = "valveClosureSource" #source
ATTR_LEAK_ALERT = "alertWaterLeak"
ATTR_BATT_ALERT = "alertLowBatt"
ATTR_TEMP_ALERT = "alertLowTemp"
ATTR_CONF_CLOSURE = "cfgValveClosure"
ATTR_MOTOR_TARGET = "motorTargetPosition"
ATTR_FLOOR_AIR_LIMIT = "floorMaxAirTemperature"
ATTR_FLOOR_MAX = "floorLimitHigh"
ATTR_FLOOR_MIN = "floorLimitLow"
ATTR_ROOM_TEMP_DISPLAY = "roomTemperatureDisplay"
ATTR_EARLY_START = "earlyStartCfg"
ATTR_FLOOR_SENSOR = "floorSensorType"
ATTR_AUX_CYCLE = "auxCycleLength"
ATTR_CYCLE = "cycleLength"
ATTR_CYCLE_OUTPUT2= "cycleLengthOutput2" #status on/off, value (second)
ATTR_PUMP_PROTEC = "pumpProtection" #status on/off, duration, frequency
ATTR_PUMP_PROTEC_DURATION = "pumpProtectDuration" #status on/off, value
ATTR_PUMP_PROTEC_PERIOD = "pumpProtectPeriod" #status on/off, value
ATTR_TYPE = "type"
ATTR_PHASE_CONTROL = "phaseControl"
ATTR_SYSTEM_MODE = "systemMode"
ATTR_DRSETPOINT = "drSetpoint"
ATTR_DRACTIVE = "drActive"
ATTR_OPTOUT = "optOut"
ATTR_SETPOINT = "setpoint"
ATTR_INPUT_STATUS = "inputStatus"
ATTR_INPUT2_STATUS = "input2Status"
ATTR_EXT_TEMP = "externalTemperature"
ATTR_REL_HUMIDITY = "relativeHumidity"
ATTR_STATUS = "status"
ATTR_ERROR_CODE_SET1 = "errorCodeSet1"
ATTR_FLOW_METER_CONFIG = "flowMeterMeasurementConfig"
ATTR_VALVE_INFO = "valveInfo"
ATTR_STM8_ERROR = "stm8Error"
ATTR_TANK_SIZE = "tankSize"
ATTR_CONTROLED_DEVICE = "controlledDevice"
ATTR_COLD_LOAD_PICKUP = "coldLoadPickupStatus"
ATTR_KEY_DOUBLE_UP = "configKeyDoubleUp"
ATTR_ANGLE = "angle"
ATTR_TANK_TYPE = "tankType"
ATTR_TANK_HEIGHT = "tankHeight"

MODE_AUTO = "auto"
MODE_AUTO_BYPASS = "autoBypass"
MODE_MANUAL = "manual"
MODE_AWAY = "away"
MODE_HOME = "home"
MODE_OFF = "off"

STATE_WATER_LEAK = "water"
STATE_VALVE_STATUS = "open"
STATE_KEYPAD_STATUS = "unlocked"

SERVICE_SET_LED_INDICATOR = "set_led_indicator"
SERVICE_SET_CLIMATE_KEYPAD_LOCK = "set_climate_keypad_lock"
SERVICE_SET_LIGHT_KEYPAD_LOCK = "set_light_keypad_lock"
SERVICE_SET_SWITCH_KEYPAD_LOCK = "set_switch_keypad_lock"
SERVICE_SET_LIGHT_TIMER = "set_light_timer"
SERVICE_SET_SWITCH_TIMER = "set_switch_timer"
SERVICE_SET_SWITCH_TIMER_2 = "set_switch_timer2"
SERVICE_SET_SECOND_DISPLAY = "set_second_display"
SERVICE_SET_BACKLIGHT = "set_backlight"
SERVICE_SET_EARLY_START = "set_early_start"
SERVICE_SET_TIME_FORMAT = "set_time_format"
SERVICE_SET_TEMPERATURE_FORMAT = "set_temperature_format"
SERVICE_SET_WATTAGE = "set_wattage"
SERVICE_SET_SETPOINT_MAX = "set_setpoint_max"
SERVICE_SET_SETPOINT_MIN = "set_setpoint_min"
SERVICE_SET_SENSOR_ALERT = "set_sensor_alert"
SERVICE_SET_VALVE_ALERT = "set_valve_alert"
SERVICE_SET_VALVE_TEMP_ALERT = "set_valve_temp_alert"
SERVICE_SET_FLOOR_AIR_LIMIT = "set_floor_air_limit"
SERVICE_SET_AIR_FLOOR_MODE = "set_air_floor_mode"
SERVICE_SET_PHASE_CONTROL = "set_phase_control"
SERVICE_SET_HVAC_DR_OPTIONS = "set_hvac_dr_options"
SERVICE_SET_HVAC_DR_SETPOINT = "set_hvac_dr_setpoint"
SERVICE_SET_LOAD_DR_OPTIONS = "set_load_dr_options"
SERVICE_SET_CONTROL_ONOFF = "set_control_onOff"
SERVICE_SET_AUXILIARY_LOAD = "set_auxiliary_load"
SERVICE_SET_AUX_CYCLE_OUTPUT = "set_aux_cycle_output"
SERVICE_SET_CYCLE_OUTPUT = "set_cycle_output"
SERVICE_SET_BATTERY_TYPE = "set_battery_type"
SERVICE_SET_PUMP_PROTECTION = "set_pump_protection"
SERVICE_SET_TANK_SIZE = "set_tank_size"
SERVICE_SET_CONTROLED_DEVICE = "set_controled_device"
