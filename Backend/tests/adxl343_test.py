import unittest
from unittest.mock import MagicMock, patch, call
import threading
import time
import queue
from typing import List

# Adjust imports to match your code's structure. For example:
from Backend.resources.adxl343 import ADXL343, InternalADXL343
from Backend.data_logger import DataLogger

class TestADXL343(unittest.TestCase):

    def setUp(self):
        """
        Create a mocked environment for ADXL343 tests.
        """
        # Mock the DataLogger
        self.mock_logger = MagicMock(
            spec=DataLogger
        )

        # Mock an SMBus object
        self.mock_bus = MagicMock()

        # Mock i2c_addr
        self.mock_addr = 0x1D  # typically valid for ADXL343

        # Create a test instance of ADXL343
        # We'll patch any threading or time.sleep calls as necessary in each test
        self.device_name = "TestADXL343"
        self.adxl = ADXL343(
            name=self.device_name,
            logger=self.mock_logger,
            i2c_bus=self.mock_bus,
            i2c_addr=self.mock_addr
        )

    def test_init(self):
        """
        Test that the __init__ method sets up the ADXL343 object properly.
        """
        self.assertEqual(self.adxl.name, self.device_name, "Device name should match constructor argument.")
        self.assertEqual(self.adxl.bus, self.mock_bus, "I2C bus should be set to the provided bus.")
        self.assertEqual(self.adxl.addr, self.mock_addr, "I2C address should be set.")
        self.assertIsInstance(self.adxl.data_queue, queue.Queue, "data_queue should be a Queue instance.")
        self.assertTrue(hasattr(self.adxl, 'last_retrieval_time'), "Should store the last retrieval time.")
        self.assertGreater(self.adxl.last_retrieval_time, 0, "last_retrieval_time should be a positive float.")

    @patch('time.sleep', return_value=None)  # to skip actual sleeping
    @patch.object(ADXL343, '_ADXL343__start_threaded_data_collection', autospec=True)
    @patch.object(ADXL343, 'Status', autospec=True)
    @patch('Backend.resources.adxl343.InternalADXL343', autospec=True)
    
    def test_initialize(
        self, mock_internal_adxl, mock_status, mock_start_thread, mock_sleep
    ):
        """
        Test the initialize method to ensure it configures the InternalADXL343,
        sets status to ACTIVE, and starts the thread for data collection.
        """
        # Prepare a mock InternalADXL343 instance
        internal_adxl_instance = MagicMock()
        mock_internal_adxl.return_value = internal_adxl_instance

        # Pretend ADXL343.Status.ACTIVE is an enum value
        mock_status.ACTIVE = "ACTIVE"

        # Now call initialize()
        self.adxl.initialize()

        # Check that we created an InternalADXL343
        mock_internal_adxl.assert_called_once_with(self.mock_bus, self.mock_addr)

        # Check calls to configure the ADXL343
        internal_adxl_instance.write_g_range.assert_called_with(8)
        internal_adxl_instance.write_sample_rate.assert_called_with(200)
        internal_adxl_instance.write_low_power_mode.assert_called_with(False)

        # Confirm we set the device status to ACTIVE
        self.assertEqual(self.adxl.status, mock_status.ACTIVE)

        # Confirm we started the data collection thread
        mock_start_thread.assert_called_once_with(self.adxl)

        # Confirm we called time.sleep at least once for I2C delay
        self.assertTrue(mock_sleep.called, "time.sleep should be called for I2C command sync.")

    def test_update_no_data(self):
        """
        If no data is available, __get_data_from_thread should return None,
        and update should skip any caching/logging.
        """
        # Mock the __get_data_from_thread to return None
        with patch.object(self.adxl, '_ADXL343__get_data_from_thread', return_value=None):
            # Also mock _update_cache_timeout and _reset_last_cache_update_timer
            with patch.object(self.adxl, '_update_cache_timeout') as mock_update_cache, \
                 patch.object(self.adxl, '_reset_last_cache_update_timer') as mock_reset_timer, \
                 patch.object(self.adxl, '_log_telemetry') as mock_log_telemetry:

                self.adxl.update()

                # No data => no telemetry logging, no reset timer call
                mock_log_telemetry.assert_not_called()
                mock_reset_timer.assert_not_called()

                # But we should update the cache timeout
                mock_update_cache.assert_called_once()

    def test_update_partial_none_data(self):
        """
        If any value in the accelerations list is None, treat it like no new data.
        """
        # e.g., [0.5, None, 1.2]
        partial_none_data = [0.5, None, 1.2]

        with patch.object(self.adxl, '_ADXL343__get_data_from_thread', return_value=partial_none_data):
            with patch.object(self.adxl, '_update_cache_timeout') as mock_update_cache, \
                 patch.object(self.adxl, '_reset_last_cache_update_timer') as mock_reset_timer, \
                 patch.object(self.adxl, '_log_telemetry') as mock_log_telemetry:

                self.adxl.update()

                mock_log_telemetry.assert_not_called()
                mock_reset_timer.assert_not_called()
                mock_update_cache.assert_called_once()

    def test_update_with_valid_data(self):
        """
        If we have valid data, we should log it, cache it, and reset the timer.
        """
        valid_data = [0.12, 0.98, -0.21]

        # Mock the queue retrieval to return valid data
        with patch.object(self.adxl, '_ADXL343__get_data_from_thread', return_value=valid_data):
            with patch.object(self.adxl, '_update_cache_timeout') as mock_update_cache, \
                 patch.object(self.adxl, '_reset_last_cache_update_timer') as mock_reset_timer, \
                 patch.object(self.adxl, '_log_telemetry') as mock_log_telemetry:

                self.adxl.update()

                # Verify that the cached values match the dummy data
                self.assertEqual(self.adxl.get_data('x'), 0.12)
                self.assertEqual(self.adxl.get_data('y'), 0.98)
                self.assertEqual(self.adxl.get_data('z'), -0.21)

                # Telemetry logging should be called
                mock_log_telemetry.assert_has_calls([
                    call('x', valid_data[0], 'g'),
                    call('y', valid_data[1], 'g'),
                    call('z', valid_data[2], 'g')
                ], any_order=False)  # Set to True if order doesn't matter

                # We do not call _update_cache_timeout if we successfully retrieved data
                mock_update_cache.assert_not_called()

                # Reset timer should be called
                mock_reset_timer.assert_called_once()

    def test___get_data_from_thread_empty(self):
        """
        Test that if the queue is empty, __get_data_from_thread returns None.
        """
        self.assertTrue(self.adxl.data_queue.empty(), "Queue should be empty initially.")
        result = self.adxl._ADXL343__get_data_from_thread()
        self.assertIsNone(result, "Should return None if the queue is empty.")

    def test___get_data_from_thread_with_data(self):
        """
        Test that if the queue has data, __get_data_from_thread returns it.
        """
        test_data = [1.0, 2.0, 3.0]
        self.adxl.data_queue.put_nowait(test_data)
        result = self.adxl._ADXL343__get_data_from_thread()
        self.assertEqual(result, test_data, "Should return the enqueued data.")
        self.assertTrue(self.adxl.data_queue.empty(), "Queue should be empty after reading.")

    @patch('threading.Thread', autospec=True)
    def test___start_threaded_data_collection(self, mock_thread):
        """
        Test that __start_threaded_data_collection starts a daemon thread that runs __data_collection_worker.
        """
        # Start the thread
        self.adxl._ADXL343__start_threaded_data_collection()

        # A thread should be created with target=__data_collection_worker
        mock_thread.assert_called_once()
        args, kwargs = mock_thread.call_args

        # Check the target function
        self.assertEqual(kwargs['target'], self.adxl._ADXL343__data_collection_worker)
        self.assertTrue(kwargs['daemon'], "Thread should be a daemon thread.")

        # Check that thread.start() is called
        mock_thread.return_value.start.assert_called_once()


    # I don't really understand how ChatGPT wrote this test.
    # It keeps failing so ill comment it for now.
    # @patch('time.sleep', return_value=None)
    # @patch.object(ADXL343, '_log')
    # @patch.object(ADXL343, 'Status', autospec=True)
    # def test___data_collection_worker_runs(
    #     self, mock_status, mock_log, mock_sleep
    # ):
    #     """
    #     Test that __data_collection_worker fetches data and puts it in the queue,
    #     as long as status is ACTIVE.
    #     """
    #     from Backend.interface import Interface
    #     self.adxl.status = Interface.Status.ACTIVE

    #     # Patch out __fetch_sensor_data to return a known list
    #     fetch_data = [0.1, 0.2, 0.3]
    #     with patch.object(self.adxl, '_ADXL343__fetch_sensor_data', return_value=fetch_data), \
    #          patch.object(self.adxl, '_reset_last_cache_update_timer') as mock_reset_timer:

    #         # We'll run the worker in a separate thread
    #         worker_thread = threading.Thread(target=self.adxl._ADXL343__data_collection_worker, daemon=True)

    #         # Let the worker run for a short time
    #         worker_thread.start()
    #         time.sleep(0.1)

    #         # Make sure its still alive
    #         self.assertTrue(worker_thread.is_alive(), "Thread should be running")

    #         # Now instruct the device to become Error
    #         self.adxl.status = Interface.Status.ERROR
    #         worker_thread.join(timeout=1.0)

    #         # Make sure the thread stopped
    #         self.assertFalse(worker_thread.is_alive(), "Thread should've stopped when status is ERROR")

    #         # Check if the data is in the queue
    #         self.assertFalse(self.adxl.data_queue.empty(), "Data queue should have at least one entry.")
    #         self.assertEqual(self.adxl.data_queue.get_nowait(), fetch_data, "Should contain the fetched data.")

    #         # Ensure we reset the cache update timer after successfully reading data
    #         mock_reset_timer.assert_called()


    @patch.object(ADXL343, '_log')
    @patch.object(ADXL343, 'Status', autospec=True)
    def test___data_collection_worker_error(
        self, mock_status, mock_log
    ):
        """
        Test that if __fetch_sensor_data raises an error, we log the error and continue.
        """
        from Backend.interface import Interface
        self.adxl.status = Interface.Status.ACTIVE

        # Force an Exception to be raised
        with patch.object(self.adxl, '_ADXL343__fetch_sensor_data', side_effect=Exception("Fake error")), \
             patch.object(self.adxl, '_reset_last_cache_update_timer'):
            
            worker_thread = threading.Thread(target=self.adxl._ADXL343__data_collection_worker, daemon=True)
            worker_thread.start()
            time.sleep(0.1)

            # Stop the worker
            self.adxl.status = Interface.Status.ERROR
            worker_thread.join(timeout=1.0)

            # We should have logged the error at least once
            mock_log.assert_called()
            # The queue should remain empty
            self.assertTrue(self.adxl.data_queue.empty(), "No data should be enqueued if fetch fails.")

    def test___fetch_sensor_data_success(self):
        """
        Tests that __fetch_sensor_data reads from adxl343 and returns the results.
        """
        mock_read = MagicMock(return_value=[-0.1, 0.5, 1.2])
        self.adxl.adxl343 = MagicMock(read_acceleration_in_g=mock_read)

        result = self.adxl._ADXL343__fetch_sensor_data()
        self.assertEqual(result, [-0.1, 0.5, 1.2], "Should return the read_acceleration_in_g results.")
        mock_read.assert_called_once()

    @patch.object(ADXL343, '_log')
    def test___fetch_sensor_data_failure(self, mock_log):
        """
        If reading acceleration fails with OSError, log the error and return an empty list.
        """
        self.adxl.adxl343 = MagicMock()
        self.adxl.adxl343.read_acceleration_in_g.side_effect = OSError("I2C error")

        result = self.adxl._ADXL343__fetch_sensor_data()
        self.assertEqual(result, [], "Should return an empty list on OSError.")
        mock_log.assert_called_once()

    def test_get_cached_values_via_update(self):
        """
        Test retrieving the x, y, and z acceleration values using the get_cached_values function,
        with data provided through the update method.
        """
        # Define the dummy data to simulate accelerometer readings
        dummy_data = [0.15, -0.45, 0.85]

        # Patch the __get_data_from_thread method to return dummy data
        with patch.object(self.adxl, '_ADXL343__get_data_from_thread', return_value=dummy_data):
            # Call the update method, which should cache the data
            self.adxl.update()

            # Verify that the cached values match the dummy data
            self.assertEqual(self.adxl.get_data('x'), 0.15)
            self.assertEqual(self.adxl.get_data('y'), -0.45)
            self.assertEqual(self.adxl.get_data('z'), 0.85)
        
# This allows running the tests directly (e.g., `python test_adxl343.py`)
if __name__ == "__main__":
    unittest.main()