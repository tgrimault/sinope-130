"""
Need to be changed
Support for Neviweb switch connected via GT130 ZigBee.
type 120 = load controller device, RM3250ZB, 50A
type xxx =  wall plug, SP2610ZB
type xxx =  portable plug, SP2600ZB
For more details about this platform, please refer to the documentation at  
https://www.sinopetech.com/en/support/#api
"""
import logging

import voluptuous as vol
import time

import custom_components.neviweb130 as neviweb130
from . import (SCAN_INTERVAL)
from homeassistant.components.switch import (SwitchDevice, 
    ATTR_TODAY_ENERGY_KWH, ATTR_CURRENT_POWER_W)
from datetime import timedelta
from homeassistant.helpers.event import track_time_interval
from .const import (DOMAIN, ATTR_POWER_MODE, ATTR_INTENSITY, ATTR_RSSI,
    ATTR_WATTAGE, ATTR_WATTAGE_INSTANT, MODE_AUTO, MODE_MANUAL)

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'neviweb130 switch'

UPDATE_ATTRIBUTES = [ATTR_POWER_MODE, ATTR_INTENSITY, ATTR_RSSI, 
    ATTR_WATTAGE, ATTR_WATTAGE_INSTANT]

IMPLEMENTED_DEVICE_TYPES = [120] #power control device

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Neviweb switch."""
    data = hass.data[DOMAIN]
    
    devices = []
    for device_info in data.neviweb130_client.gateway_data:
        if "signature" in device_info and \
            "type" in device_info["signature"] and \
            device_info["signature"]["type"] in IMPLEMENTED_DEVICE_TYPES:
            device_name = '{} {}'.format(DEFAULT_NAME, device_info["name"])
            devices.append(Neviweb130Switch(data, device_info, device_name))

    async_add_entities(devices, True)

class Neviweb130Switch(SwitchDevice):
    """Implementation of a Neviweb switch."""

    def __init__(self, data, device_info, name):
        """Initialize."""
        self._name = name
        self._client = data.neviweb130_client
        self._id = device_info["id"]
        self._wattage = 0 # keyCheck("wattage", device_info, 0, name)
        self._brightness = 0
        self._operation_mode = 1
        #self._alarm = None
        self._current_power_w = None
        self._today_energy_kwh = None
        self._rssi = None
        _LOGGER.debug("Setting up %s: %s", self._name, device_info)

    def update(self):
        """Get the latest data from Neviweb and update the state."""
        start = time.time()
        device_data = self._client.get_device_attributes(self._id,
            UPDATE_ATTRIBUTES)
        device_daily_stats = self._client.get_device_daily_stats(self._id)
        end = time.time()
        elapsed = round(end - start, 3)
        _LOGGER.debug("Updating %s (%s sec): %s",
            self._name, elapsed, device_data)
        if "error" not in device_data:
            if "errorCode" not in device_data:
                self._brightness = device_data[ATTR_INTENSITY] if \
                    device_data[ATTR_INTENSITY] is not None else 0.0
                self._operation_mode = device_data[ATTR_POWER_MODE] if \
                    device_data[ATTR_POWER_MODE] is not None else MODE_MANUAL
                #self._alarm = device_data["alarm"]
                self._current_power_w = device_data[ATTR_WATTAGE_INSTANT]["value"]
                self._wattage = device_data[ATTR_WATTAGE]["value"]
                self._rssi = device_data[ATTR_RSSI]
                self._today_energy_kwh = device_daily_stats[0] / 1000
                return
            _LOGGER.warning("Error in reading device %s: (%s)", self._name, device_data)
            return
        _LOGGER.warning("Cannot update %s: %s", self._name, device_data)     

    @property
    def unique_id(self):
        """Return unique ID based on Neviweb device ID."""
        return self._id

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property  
    def is_on(self):
        """Return current operation i.e. ON, OFF """
        return self._brightness != 0

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self._client.set_brightness(self._id, 100)
        
    def turn_off(self, **kwargs):
        """Turn the device off."""
        self._client.set_brightness(self._id, 0)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {#'alarm': self._alarm,
                'operation_mode': self.operation_mode,
                'rssi': self._rssi,
                'wattage': self._wattage,
                'id': self._id}
       
    @property
    def operation_mode(self):
        return self._operation_mode

    @property
    def current_power_w(self):
        """Return the current power usage in W."""
        return self._current_power_w

    @property
    def today_energy_kwh(self):
        """Return the today total energy usage in kWh."""
        return self._today_energy_kwh
    
    @property
    def is_standby(self):
        """Return true if device is in standby."""
        return self._current_power_w == 0