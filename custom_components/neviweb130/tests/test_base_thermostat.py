import unittest
from unittest.mock import MagicMock, patch
from ..thermostats.base_thermostat import Neviweb130Thermostat


class TestNeviweb130Thermostat(unittest.TestCase):
    def setUp(self):
        self.data = MagicMock()
        self.device_info = {
            "id": "test_id",
            "signature": {
                "model": "test_model",
                "modelCfg": "test_model_cfg"
            }
        }
        self.name = "Test Thermostat"
        self.sku = "Test SKU"
        self.firmware = "Test Firmware"
        self.thermostat = Neviweb130Thermostat(self.data, self.device_info, self.name, self.sku, self.firmware)

    @patch("neviweb130.thermostats.base_thermostat.Neviweb130Thermostat.get_sensor_error_code")
    @patch("neviweb130.thermostats.base_thermostat._LOGGER")
    def test_update(self, mock_logger, mock_get_sensor_error_code):
        mock_device_data = {
            "roomTemperature": {"value": 25.0},
            "roomSetpoint": 22.0,
            "roomSetpointMin": 18.0,
            "roomSetpointMax": 30.0,
            "temperatureFormat": "CELSIUS",
            "timeFormat": "24h",
            "roomTemperatureDisplay": "display_value",
            "config2ndDisplay": "display2_value",
            "drsetpoint": {"status": "off", "value": None},
            "drstatus": {"drActive": "off", "optOut": "off", "setpoint": "off", "powerAbsolute": "off",
                         "powerRelative": "off"},
            "outputPercentDisplay": 50,
            "lockKeypad": "keypad_value",
            "backlightAdaptive": "backlight_value",
            "cycleLength": 10,
            "rssi": "rssi_value",
            "systemMode": "mode_value",
            "loadConnected": 1000
        }
        self.thermostat._client.get_device_attributes.return_value = mock_device_data

        self.thermostat.update()

        self.assertEqual(self.thermostat._cur_temp, 25.0)
        self.assertEqual(self.thermostat._cur_temp_before, None)  # Assuming it's the first update
        self.assertEqual(self.thermostat._target_temp, 22.0)
        self.assertEqual(self.thermostat._min_temp, 18.0)
        self.assertEqual(self.thermostat._max_temp, 30.0)
        self.assertEqual(self.thermostat._temperature_format, "CELSIUS")
        self.assertEqual(self.thermostat._time_format, "24h")
        self.assertEqual(self.thermostat._temp_display_value, "display_value")
        self.assertEqual(self.thermostat._display2, "display2_value")
        self.assertEqual(self.thermostat._drsetpoint_status, "off")
        self.assertEqual(self.thermostat._drsetpoint_value, 0)
        self.assertEqual(self.thermostat._drstatus_active, "off")
        self.assertEqual(self.thermostat._drstatus_optout, "off")
        self.assertEqual(self.thermostat._drstatus_setpoint, "off")
        self.assertEqual(self.thermostat._drstatus_abs, "off")
        self.assertEqual(self.thermostat._drstatus_rel, "off")
        self.assertEqual(self.thermostat._heat_level, 50)
        self.assertEqual(self.thermostat._keypad, "keypad_value")
        self.assertEqual(self.thermostat._backlight, "backlight_value")
        self.assertEqual(self.thermostat._cycle_length, 10)
        self.assertEqual(self.thermostat._rssi, "rssi_value")
        self.assertEqual(self.thermostat._operation_mode, "mode_value")
        self.assertEqual(self.thermostat._wattage, 1000)
        self.assertTrue(self.thermostat._client.get_device_attributes.called)
        self.assertTrue(mock_get_sensor_error_code.called)
        self.assertTrue(mock_logger.debug.called)


if __name__ == '__main__':
    unittest.main()
