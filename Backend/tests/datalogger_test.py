import unittest
import os
import shutil
import tempfile
from csv import reader as csvReader
import logging
from Backend.data_logger import DataLogger

class TestDataLogger(unittest.TestCase):
    def setUp(self):
        """
        Create a temporary directory for tests. 
        Each test will run in isolation with its own environment.
        """
        self.test_dir = tempfile.mkdtemp()
        self.original_log_dir = DataLogger.logDirectoryPath
        # Redirect the logger's base directory to our temporary directory
        DataLogger.logDirectoryPath = self.test_dir

    def tearDown(self):
        """
        Remove the temporary directory and restore defaults after each test.
        """
        DataLogger.logDirectoryPath = self.original_log_dir
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # -----------------------------------------------------------------------
    # __validateFileName Tests
    # -----------------------------------------------------------------------

    def test_validate_file_name_success(self):
        """
        Test that a valid file name passes without raising an exception.
        """
        logger = DataLogger("valid_name")
        self.assertTrue(os.path.exists(logger.directoryPath))

    def test_validate_file_name_failure_empty(self):
        """
        Test that an empty file name raises ValueError.
        """
        with self.assertRaises(ValueError):
            DataLogger("")

    def test_validate_file_name_failure_invalid_char(self):
        """
        Test that an invalid character (e.g., ':') raises ValueError.
        """
        with self.assertRaises(ValueError):
            DataLogger("invalid:name")

    # -----------------------------------------------------------------------
    # __make_directory Tests
    # -----------------------------------------------------------------------

    def test_make_directory_success(self):
        """
        Test that the directory is created successfully within the log base.
        """
        logger = DataLogger("directory_test")
        self.assertTrue(os.path.exists(logger.directoryPath))

    # -----------------------------------------------------------------------
    # __createCSVFile Tests
    # -----------------------------------------------------------------------

    def test_create_csv_file_creates_correct_header(self):
        """
        Test that createCSVFile writes the expected header row to the new file.
        """
        logger = DataLogger("csv_test")
        with open(logger.telemetryPath, "r") as file:
            header = file.readline().strip().split(",")
        self.assertEqual(header, ["Time", "Device", "Parameter", "Value", "Units"])

    def test_create_csv_file_overwrites_existing_file(self):
        """
        Ensure that if the CSV file already exists, it is overwritten 
        (header row is reset).
        """
        logger = DataLogger("overwrite_test")

        # Write some dummy data first
        with open(logger.telemetryPath, "a") as file:
            file.write("dummy,data,123\n")

        # Re-initialize DataLogger, which should recreate the file
        logger2 = DataLogger("overwrite_test")
        with open(logger2.telemetryPath, "r") as file:
            lines = file.readlines()

        # Only the header row should remain
        self.assertEqual(len(lines), 1)
        self.assertIn("Device", lines[0])

    # -----------------------------------------------------------------------
    # writeTelemetry & getTelemetry Tests
    # -----------------------------------------------------------------------

    def test_write_telemetry_appends_data(self):
        """
        Test that calling writeTelemetry adds a new row to the telemetry CSV.
        """
        logger = DataLogger("telemetry_test")
        initial_data = logger.getTelemetry()
        initial_len = len(initial_data)

        logger.writeTelemetry("Device1", "Param1", 100, "Units")
        final_data = logger.getTelemetry()
        final_len = len(final_data)

        self.assertEqual(final_len, initial_len + 1)
        self.assertIn("Device1", final_data[-1])
        self.assertIn("Param1", final_data[-1])

    def test_get_telemetry_returns_correct_data(self):
        """
        Test that getTelemetry returns the expected rows in the correct format.
        """
        logger = DataLogger("telemetry_format_test")
        logger.writeTelemetry("TestDevice", "TestParam", 42, "TEST")

        data = logger.getTelemetry()
        # The header + 1 row
        self.assertEqual(len(data), 2, "Should have header row plus one data row.")

        header = data[0]
        self.assertEqual(header, ["Time", "Device", "Parameter", "Value", "Units"])

        row = data[1]
        # row should have 5 columns (Time, Device, Parameter, Value, Units)
        self.assertEqual(len(row), 5)
        self.assertEqual(row[1], "TestDevice")
        self.assertEqual(row[2], "TestParam")
        self.assertEqual(row[3], "42")
        self.assertEqual(row[4], "TEST")

    # -----------------------------------------------------------------------
    # writeLog & __configureLogger Tests
    # -----------------------------------------------------------------------

    def test_write_log_creates_expected_files(self):
        """
        Test that System.log and debug.log files are created and exist.
        """
        logger = DataLogger("log_file_test")
        self.assertTrue(os.path.exists(logger.systemLogPath))
        self.assertTrue(os.path.exists(logger.debugLogPath))

    def test_write_log_logs_message_with_correct_severity(self):
        """
        Test logging a message with a certain severity, then check 
        that the log file contains the message.
        """
        logger = DataLogger("log_severity_test")
        logger.writeLog("TestLogger", "An info message", severity=DataLogger.LogSeverity.INFO)
        logger.writeLog("TestLogger", "A debug message", severity=DataLogger.LogSeverity.DEBUG)

        # The systemLog should contain INFO but not DEBUG
        with open(logger.systemLogPath, "r") as sys_log:
            system_content = sys_log.read()
        self.assertIn("An info message", system_content)
        self.assertNotIn("A debug message", system_content)

        # The debugLog should contain both
        with open(logger.debugLogPath, "r") as dbg_log:
            debug_content = dbg_log.read()
        self.assertIn("An info message", debug_content)
        self.assertIn("A debug message", debug_content)


if __name__ == '__main__':
    unittest.main()