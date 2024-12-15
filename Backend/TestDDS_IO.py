# FILE: Backend/TestDDS_IO.py

import unittest
from unittest.mock import patch, MagicMock
from Backend.resources.data_logger import DataLogger
from Backend.resources.interface import Interface
from Backend.resources.ads_1015 import ADS_1015
from Backend.DDS_IO import DDS_IO

class TestDDS_IO(unittest.TestCase):

    def setUp(self):
        self.dds_io = DDS_IO()

    def tearDown(self):
        del self.dds_io

    @patch.object(DDS_IO, '_DDS_IO__initialize_CAN')
    @patch.object(DDS_IO, '_DDS_IO__initialize_i2c')
    def test_initialize_devices(self, mock_initialize_i2c, mock_initialize_CAN):
        self.dds_io.__initialize_devices()
        mock_initialize_CAN.assert_called_once()
        mock_initialize_i2c.assert_called_once()

    @patch.object(Interface, 'update')
    def test_update(self, mock_update):
        self.dds_io.devices = {'test_device': MagicMock(status=Interface.Status.ACTIVE)}
        self.dds_io.update()
        mock_update.assert_called_once()

    @patch.object(Interface, 'get_data', return_value=42)
    def test_get_device_data(self, mock_get_data):
        self.dds_io.devices = {'test_device': MagicMock(status=Interface.Status.ACTIVE)}
        result = self.dds_io.get_device_data('test_device', 'parameter')
        self.assertEqual(result, 42)
        mock_get_data.assert_called_once_with('parameter')

    @patch.object(DataLogger, 'writeLog')
    def test_get_device_data_device_not_found(self, mock_writeLog):
        result = self.dds_io.get_device_data('non_existent_device', 'parameter')
        self.assertIsNone(result)
        mock_writeLog.assert_called_once()

    @patch.object(DataLogger, 'writeLog')
    def test_get_device_data_device_disabled(self, mock_writeLog):
        self.dds_io.devices = {'test_device': MagicMock(status=Interface.Status.DISABLED)}
        result = self.dds_io.get_device_data('test_device', 'parameter')
        self.assertEqual(result, 'DIS')
        mock_writeLog.assert_called_once()

    @patch.object(DataLogger, 'writeLog')
    def test_failed_to_init(self, mock_writeLog):
        self.dds_io.devices = {'test_device': MagicMock()}
        self.dds_io.__failed_to_init('i2c', Exception('Test Exception'), ['test_device'])
        self.assertEqual(self.dds_io.devices['test_device'].status, Interface.Status.ERROR)
        mock_writeLog.assert_called_once()

if __name__ == '__main__':
    unittest.main()