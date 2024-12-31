import unittest
import os
import json
import datetime
from unittest.mock import MagicMock, patch, mock_open

# Assuming these classes/functions are defined in value_monitor.py
# Adjust the import path as needed.
from Backend.value_monitor import (
    ParameterMonitor,
    ParameterWarning,
    VALID_RETURN_STR
)

# Mock DataLogger with the same interface as in your code
class MockDataLogger:
    class LogSeverity:
        DEBUG = "DEBUG"
        INFO = "INFO"
        WARNING = "WARNING"
        ERROR = "ERROR"

    def writeLog(self, loggerName, msg, severity):
        # For testing, we'll just store logs in a list
        self.logs.append((loggerName, msg, severity))

    def __init__(self):
        self.logs = []

class TestParameterMonitor(unittest.TestCase):

    def setUp(self):
        """
        Create a mock logger and a sample JSON configuration that covers multiple parameter types.
        This config will be reused in many tests.
        """
        self.mock_logger = MockDataLogger()

        self.sample_config = {
            "hotPressure": {
                "type": "numeric",
                "min": 0.8,
                "max": 2.5
            },
            "isBrakeApplied": {
                "type": "boolean",
                "expected": False
            },
            "gearSelection": {
                "type": "categorical",
                "valid": ["P", "R", "N", "D"]
            },
            "batteryCellTemperatures": {
                "type": "array",
                "min": 20,
                "max": 50
            },
            "lastServiceDate": {
                "type": "timestamp",
                "before": "2025-01-01T00:00:00"
            },
            "deviceErrorCode": {
                "type": "mappedError",
                "typical": "0x0",
                "codes": {
                    "0x1": "Error 1: Overvoltage detected",
                    "0x2": "Error 2: Overcurrent detected",
                    "0x3": "Error 3: Thermal runaway",
                    "0x4": "Error 4: Communication failure"
                }
            }
        }

    # ------------------------------------------------------------------
    #  __init__(value_limits_file_path: str, logger: DataLogger)
    # ------------------------------------------------------------------

    def test_init_using_dict_normal(self):
        """Normal: Provide a valid config dict directly."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        self.assertEqual(monitor.parameter_limits, self.sample_config)
        self.assertIn("Value Monitor Initialized!", str(self.mock_logger.logs))

    def test_init_using_file_path_normal(self):
        """Normal: Provide a valid JSON file path, ensuring it loads without error."""
        test_json_str = json.dumps(self.sample_config)
        with patch("builtins.open", mock_open(read_data=test_json_str)):
            monitor = ParameterMonitor("path/to/config.json", self.mock_logger)
            self.assertEqual(monitor.parameter_limits, self.sample_config)
            self.assertIn("Value Monitor Initialized!", str(self.mock_logger.logs))

    def test_init_with_invalid_input_edge(self):
        """Edge: Provide a non-string, non-dict to trigger a TypeError."""
        with self.assertRaises(TypeError):
            ParameterMonitor(12345, self.mock_logger)  # invalid type

    # ------------------------------------------------------------------
    #  check_value(param_name: str, param_value: Union[float, bool, str, list])
    # ------------------------------------------------------------------

    def test_check_value_normal_in_range(self):
        """Normal: Provide a value that’s within range for a numeric parameter."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        monitor.check_value("hotPressure", 2.0)  # 0.8 <= 2.0 <= 2.5 => valid
        # No warnings should exist
        self.assertEqual(len(monitor.active_warnings), 0)

    def test_check_value_param_not_found_edge(self):
        """Edge: Provide a parameter name not in config."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        monitor.check_value("unknownParam", 1.23)
        # No warnings should exist, but we expect a log about "No Value Limits found"
        self.assertEqual(len(monitor.active_warnings), 0)
        logs_str = str(self.mock_logger.logs)
        self.assertIn("No Value Limits found for param: unknownParam", logs_str)

    def test_check_value_out_of_range_edge(self):
        """Edge: Provide a numeric value outside the allowed range."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        monitor.check_value("hotPressure", 3.0)  # out of range (max=2.5)
        self.assertEqual(len(monitor.active_warnings), 1)
        self.assertIn("out of range", monitor.active_warnings[0].msg)

    def test_check_value_incorrect_type_edge(self):
        """Edge: Provide a incorrect value type"""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        monitor.check_value("hotPressure", True)  # out of range (max=2.5)
        self.assertEqual(len(monitor.active_warnings), 1)
        self.assertIn("not numeric", monitor.active_warnings[0].msg)

    # ------------------------------------------------------------------
    #  _validate_value(...) 
    #     - Indirectly tested by check_value, but we’ll add direct coverage.
    # ------------------------------------------------------------------

    def test__validate_value_normal_numeric_in_range(self):
        """Normal: Direct call to _validate_value with numeric type in range."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = self.sample_config["hotPressure"]
        msg = monitor._validate_value("hotPressure", 2.0, "numeric", rules)
        self.assertEqual(msg, VALID_RETURN_STR)

    def test__validate_value_edge_unknown_type(self):
        """Edge: Unknown 'type' field triggers an error log and returns an error message."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        msg = monitor._validate_value("unknownTypeParam", 2.0, "mysteryType", {})
        self.assertIn("unknown validation type 'mysteryType'", msg)

    def test__validate_value_edge_incorrect_parameter_type(self):
        """
        Edge: Provide a 'numeric' type but supply a non-numeric value.
        Should return an error message from _validate_numeric.
        """
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = self.sample_config["hotPressure"]
        msg = monitor._validate_value("hotPressure", "notANumber", "numeric", rules)
        self.assertIn("which is not numeric", msg)

    # ------------------------------------------------------------------
    #  _validate_numeric(...)
    # ------------------------------------------------------------------

    def test__validate_numeric_normal_in_bounds(self):
        """Normal: Value is within [min, max]."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {"min": 0.8, "max": 2.5}
        msg = monitor._validate_numeric("hotPressure", 2.0, rules)
        self.assertEqual(msg, VALID_RETURN_STR)

    def test__validate_numeric_edge_below_min(self):
        """Edge: Value is below the min bound."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {"min": 0.8, "max": 2.5}
        msg = monitor._validate_numeric("hotPressure", 0.5, rules)
        self.assertIn("out of range", msg)

    def test__validate_numeric_edge_above_max(self):
        """Edge: Value is above the max bound."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {"min": 0.8, "max": 2.5}
        msg = monitor._validate_numeric("hotPressure", 3.0, rules)
        self.assertIn("out of range", msg)

    # ------------------------------------------------------------------
    #  _validate_boolean(...)
    # ------------------------------------------------------------------

    def test__validate_boolean_normal_expected_true(self):
        """Normal: Value matches expected boolean."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {"expected": True}
        msg = monitor._validate_boolean("isDoorOpen", True, rules)
        self.assertEqual(msg, VALID_RETURN_STR)

    def test__validate_boolean_edge_not_a_boolean(self):
        """Edge: Provided value is not a bool type."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {"expected": False}
        msg = monitor._validate_boolean("isDoorOpen", "notBoolean", rules)
        self.assertIn("is not a boolean", msg)

    def test__validate_boolean_edge_mismatch_expected(self):
        """Edge: Provided value is a bool, but not the 'expected' one."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {"expected": False}
        msg = monitor._validate_boolean("isBrakeApplied", True, rules)
        self.assertIn("expected False", msg)

    # ------------------------------------------------------------------
    #  _validate_categorical(...)
    # ------------------------------------------------------------------

    def test__validate_categorical_normal_in_options(self):
        """Normal: The value is indeed in the valid list."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {"valid": ["P", "R", "N", "D"]}
        msg = monitor._validate_categorical("gearSelection", "R", rules)
        self.assertEqual(msg, VALID_RETURN_STR)

    def test__validate_categorical_edge_not_in_list(self):
        """Edge: The value is a string but not in the valid list."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {"valid": ["P", "R", "N", "D"]}
        msg = monitor._validate_categorical("gearSelection", "X", rules)
        self.assertIn("which is not in valid options", msg)

    def test__validate_categorical_edge_non_string_value(self):
        """Edge: The value is not a string (though it might still fail due to not being in the list)."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {"valid": ["P", "R", "N", "D"]}
        # This will fail because 999 is not in the list
        msg = monitor._validate_categorical("gearSelection", 999, rules)
        self.assertIn("999", msg)
        self.assertIn("which is not in valid options", msg)

    # ------------------------------------------------------------------
    #  _validate_array(...)
    # ------------------------------------------------------------------

    def test__validate_array_normal_all_in_range(self):
        """Normal: All elements in array are numeric and within [min, max]."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {"min": 10, "max": 20}
        msg = monitor._validate_array("testArray", [10, 15, 20], rules)
        self.assertEqual(msg, VALID_RETURN_STR)

    def test__validate_array_edge_non_numeric_element(self):
        """Edge: One element is non-numeric."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {"min": 10, "max": 20}
        msg = monitor._validate_array("testArray", [10, "NotANumber", 12], rules)
        self.assertIn("which is not numeric", msg)

    def test__validate_array_edge_value_out_of_range(self):
        """Edge: One element is outside [min, max]."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {"min": 10, "max": 20}
        msg = monitor._validate_array("testArray", [10, 21, 12], rules)
        self.assertIn("out of range", msg)

    # ------------------------------------------------------------------
    #  _validate_timestamp(...)
    # ------------------------------------------------------------------

    def test__validate_timestamp_normal_in_range(self):
        """Normal: Timestamp is valid and before the specified 'before' value."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {"before": "2025-01-01T00:00:00"}
        msg = monitor._validate_timestamp("lastServiceDate", "2024-12-31T23:59:59", rules)
        self.assertEqual(msg, VALID_RETURN_STR)

    def test__validate_timestamp_edge_invalid_format(self):
        """Edge: Timestamp is not in valid ISO 8601 format."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {"before": "2025-01-01T00:00:00"}
        msg = monitor._validate_timestamp("lastServiceDate", "InvalidTimestamp", rules)
        self.assertIn("not a valid ISO timestamp", msg)

    def test__validate_timestamp_edge_not_before(self):
        """Edge: Provided timestamp is not before the 'before' constraint."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {"before": "2025-01-01T00:00:00"}
        # 2025-01-01T10:00:00 is NOT before 2025-01-01T00:00:00
        msg = monitor._validate_timestamp("lastServiceDate", "2025-01-01T10:00:00", rules)
        self.assertIn("which is not before 2025-01-01T00:00:00", msg)

    # ------------------------------------------------------------------
    #  _validate_mapped_error(...)
    # ------------------------------------------------------------------

    def test__validate_mapped_error_normal_typical_value(self):
        """Normal: Provide the typical value, expect VALID_RETURN_STR."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {
            "type": "mappedError",
            "typical": "0x0",
            "codes": {
                "0x1": "Error 1: Overvoltage detected",
                "0x2": "Error 2: Overcurrent detected",
                "0x3": "Error 3: Thermal runaway",
                "0x4": "Error 4: Communication failure"
            }
        }
        msg = monitor._validate_mapped_error("deviceErrorCode", "0x0", rules)
        self.assertEqual(msg, VALID_RETURN_STR)

    def test__validate_mapped_error_edge_value_in_codes(self):
        """Edge: Provide a value not equal to the typical value, expect the associated message."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {
            "type": "mappedError",
            "typical": "0x0",
            "codes": {
                "0x1": "Error 1: Overvoltage detected",
                "0x2": "Error 2: Overcurrent detected",
                "0x3": "Error 3: Thermal runaway",
                "0x4": "Error 4: Communication failure"
            }
        }
        msg = monitor._validate_mapped_error("deviceErrorCode", "0x2", rules)
        self.assertIn("Error 2: Overcurrent detected", msg)
        self.assertIn("deviceErrorCode", msg)

    def test__validate_mapped_error_edge_value_not_in_codes(self):
        """Edge: Provide a value not in the codes list, expect an unknown code warning."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = {
            "type": "mappedError",
            "typical": "0x0",
            "codes": {
                "0x1": "Error 1: Overvoltage detected",
                "0x2": "Error 2: Overcurrent detected",
                "0x3": "Error 3: Thermal runaway",
                "0x4": "Error 4: Communication failure"
            }
        }
        msg = monitor._validate_mapped_error("deviceErrorCode", "0x5", rules)
        self.assertIn("unknown code", msg)
        self.assertIn("deviceErrorCode has unknown code '0x5'", msg)

    def test__validate_mapped_error_unknown_code(self):
        """Test: Provide an unknown code for mappedError, expect an unknown code warning."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        rules = self.sample_config["deviceErrorCode"]
        msg = monitor._validate_mapped_error("deviceErrorCode", "0x5", rules)
        self.assertIn("unknown code", msg)
        self.assertIn("deviceErrorCode has unknown code '0x5'", msg)

    def test_check_value_invalid_data_type_numeric(self):
        """Test: Provide a non-numeric value for a numeric parameter, expect an error."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        monitor.check_value("hotPressure", "invalid")  # non-numeric input
        self.assertEqual(len(monitor.active_warnings), 1)
        self.assertIn("not numeric", monitor.active_warnings[0].msg)

    def test_check_value_invalid_data_type_array(self):
        """Test: Provide a non-array value for an array parameter, expect an error."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        monitor.check_value("batteryCellTemperatures", "invalid")  # non-array input
        self.assertEqual(len(monitor.active_warnings), 1)
        self.assertIn("which is not a list", monitor.active_warnings[0].msg)

    def test_check_value_invalid_data_type_boolean(self):
        """Test: Provide a non-boolean value for a boolean parameter, expect an error."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        monitor.check_value("isBrakeApplied", None)  # non-boolean input
        self.assertEqual(len(monitor.active_warnings), 1)
        self.assertIn("is not a boolean", monitor.active_warnings[0].msg)

    # ------------------------------------------------------------------
    #  create_warning(warning: ParameterWarning)
    # ------------------------------------------------------------------

    def test_create_warning_normal(self):
        """Normal: Create a new warning for a param that has no existing warning."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        warning = ParameterWarning("hotPressure", 3.0, "Out of range")
        monitor.create_warning(warning)
        self.assertEqual(len(monitor.active_warnings), 1)
        self.assertIn("Out of range", monitor.active_warnings[0].msg)

    def test_create_warning_edge_duplicate(self):
        """Edge: Create a warning for a param that already has one should not duplicate."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        warning1 = ParameterWarning("hotPressure", 3.0, "First warning")
        warning2 = ParameterWarning("hotPressure", 4.0, "Second warning")
        monitor.create_warning(warning1)
        monitor.create_warning(warning2)  # same param_name => should skip
        self.assertEqual(len(monitor.active_warnings), 1)
        self.assertIn("First warning", monitor.active_warnings[0].msg)

    def test_create_warning_edge_empty_message(self):
        """Edge: Create a warning with an empty message. Ensure it still stores properly."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        warning = ParameterWarning("hotPressure", 3.0, "")
        monitor.create_warning(warning)
        self.assertEqual(len(monitor.active_warnings), 1)
        self.assertEqual(monitor.active_warnings[0].msg, "")

    # ------------------------------------------------------------------
    #  clear_warning(param_name: str)
    # ------------------------------------------------------------------

    def test_clear_warning_normal(self):
        """Normal: Clear an existing warning by param_name."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        warning = ParameterWarning("hotPressure", 3.0, "Out of range")
        monitor.create_warning(warning)
        monitor.clear_warning("hotPressure")
        self.assertEqual(len(monitor.active_warnings), 0)

    def test_clear_warning_edge_non_existent(self):
        """Edge: Try clearing a parameter that doesn't exist in active_warnings."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        # No warnings yet
        monitor.clear_warning("randomParam")
        self.assertEqual(len(monitor.active_warnings), 0)
        # Nothing should break or fail

    def test_clear_warning_edge_multiple_warnings_different_params(self):
        """Edge: Ensure clearing one param doesn't clear others."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        w1 = ParameterWarning("hotPressure", 3.0, "Out of range")
        w2 = ParameterWarning("isBrakeApplied", True, "Expected false")
        monitor.create_warning(w1)
        monitor.create_warning(w2)
        monitor.clear_warning("hotPressure")
        # Only isBrakeApplied's warning should remain
        self.assertEqual(len(monitor.active_warnings), 1)
        self.assertEqual(monitor.active_warnings[0].param_name, "isBrakeApplied")

    # ------------------------------------------------------------------
    #  get_warnings_as_str()
    # ------------------------------------------------------------------

    def test_get_warnings_as_str_normal(self):
        """Normal: Return a list of warning messages."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        w1 = ParameterWarning("hotPressure", 3.0, "Too high")
        w2 = ParameterWarning("gearSelection", "X", "Invalid gear")
        monitor.create_warning(w1)
        monitor.create_warning(w2)
        warnings_list = monitor.get_warnings_as_str()
        self.assertEqual(len(warnings_list), 2)
        self.assertIn("Too high", warnings_list[0])
        self.assertIn("Invalid gear", warnings_list[1])

    def test_get_warnings_as_str_edge_no_warnings(self):
        """Edge: Return an empty list if there are no warnings."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        warnings_list = monitor.get_warnings_as_str()
        self.assertEqual(warnings_list, [])

    def test_get_warnings_as_str_edge_special_chars(self):
        """Edge: Handle messages with special characters properly."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        w1 = ParameterWarning("hotPressure", 3.0, "Temp>2.5? #@! out-of-range")
        monitor.create_warning(w1)
        warnings_list = monitor.get_warnings_as_str()
        self.assertIn("Temp>2.5? #@! out-of-range", warnings_list[0])

    # ------------------------------------------------------------------
    #  get_warnings()
    # ------------------------------------------------------------------

    def test_get_warnings_normal(self):
        """Normal: Return a list of ParameterWarning objects."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        w = ParameterWarning("hotPressure", 3.0, "Out of range")
        monitor.create_warning(w)
        all_warnings = monitor.get_warnings()
        self.assertEqual(len(all_warnings), 1)
        self.assertIsInstance(all_warnings[0], ParameterWarning)

    def test_get_warnings_edge_empty(self):
        """Edge: Return an empty list if no warnings exist."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        self.assertEqual(monitor.get_warnings(), [])

    def test_get_warnings_edge_multiple_warnings(self):
        """Edge: Confirm multiple warnings are returned in a list."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        w1 = ParameterWarning("p1", 100, "Error 1")
        w2 = ParameterWarning("p2", 200, "Error 2")
        w3 = ParameterWarning("p3", 300, "Error 3")
        monitor.create_warning(w1)
        monitor.create_warning(w2)
        monitor.create_warning(w3)
        all_warnings = monitor.get_warnings()
        self.assertEqual(len(all_warnings), 3)
        self.assertEqual(all_warnings[0].msg, "Error 1")

    # ------------------------------------------------------------------
    #  __load_config(config_path: str) -> dict[str, dict]
    # ------------------------------------------------------------------

    def test___load_config_normal_file(self):
        """Normal: Load a valid JSON file from disk."""
        # Use mock_open to simulate file reading
        test_json_str = json.dumps(self.sample_config)
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        with patch("builtins.open", mock_open(read_data=test_json_str)):
            loaded = monitor._ParameterMonitor__load_config("fake_path.json")
        self.assertEqual(loaded, self.sample_config)

    def test___load_config_edge_invalid_json(self):
        """Edge: Raise JSONDecodeError when the file is invalid JSON."""
        invalid_json = "{someInvalidJson}"
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        with patch("builtins.open", mock_open(read_data=invalid_json)):
            with self.assertRaises(json.JSONDecodeError):
                monitor._ParameterMonitor__load_config("fake_path.json")

    def test___load_config_edge_file_not_found(self):
        """Edge: Raise FileNotFoundError when the file does not exist."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        with self.assertRaises(FileNotFoundError):
            monitor._ParameterMonitor__load_config("non_existent_file.json")

    # ------------------------------------------------------------------
    #  __log(msg: str, severity=DataLogger.LogSeverity.DEBUG)
    # ------------------------------------------------------------------

    def test___log_normal(self):
        """Normal: Logging a simple DEBUG message."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        monitor._ParameterMonitor__log("Test debug log", MockDataLogger.LogSeverity.DEBUG)
        # The mock logger should contain the log
        self.assertIn("Test debug log", str(self.mock_logger.logs))

    def test___log_edge_info(self):
        """Edge: Logging an INFO message."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        monitor._ParameterMonitor__log("Test info log", MockDataLogger.LogSeverity.INFO)
        self.assertIn(("ValueMonitor", "Test info log", "INFO"), self.mock_logger.logs)

    def test___log_edge_error(self):
        """Edge: Logging an ERROR message."""
        monitor = ParameterMonitor(self.sample_config, self.mock_logger)
        monitor._ParameterMonitor__log("Test error log", MockDataLogger.LogSeverity.ERROR)
        self.assertIn(("ValueMonitor", "Test error log", "ERROR"), self.mock_logger.logs)


if __name__ == "__main__":
    unittest.main()