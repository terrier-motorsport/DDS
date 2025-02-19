# Value Monitor for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

"""
Module Overview
---------------

This module defines classes to monitor values from the DDS_IO system. Signals can be given a constraint 
range in the valuelimits.json file. The ParameterMonitor class observes these signals and logs a 
warning if any value falls outside the given constraint.

TODO:
    - Add support for different limits based on different driving modes.

Classes:
    ParameterWarning: Represents a warning for a parameter that is out of range.
    ParameterMonitor: Monitors parameters and raises warnings if values are out of range.

    
Supported Parameter Limits and Validation Types
-----------------------------------------------

This module supports monitoring various types of parameters with different validation rules.
Each parameter in the configuration file must include a "type" field to indicate the type of
parameter being monitored. The supported types and their rules are detailed below:

1. **Numeric** (type: "numeric")
    - Validates parameters with numeric values (int or float).
    - Rules:
        - "min": The minimum acceptable value (default: -infinity).
        - "max": The maximum acceptable value (default: +infinity).

2. **Boolean** (type: "boolean")
    - Validates parameters with boolean values (True/False).
    - Rules:
        - "expected": (Optional) The expected boolean value (e.g., True or False).

3. **Categorical** (type: "categorical")
    - Validates parameters with string values against a predefined set of valid options.
    - Rules:
        - "valid": A list of acceptable string values.

4. **Array** (type: "array")
    - Validates an array (list) of numeric values. Each element in the array must satisfy the
      specified min/max bounds.
    - Rules:
        - "min": The minimum acceptable value for each element (default: -infinity).
        - "max": The maximum acceptable value for each element (default: +infinity).

5. **Timestamp** (type: "timestamp")
    - Validates ISO 8601 formatted timestamps against "before" and "after" constraints.
    - Rules:
        - "before": (Optional) The latest acceptable timestamp (e.g., "2025-01-01T00:00:00").
        - "after": (Optional) The earliest acceptable timestamp (e.g., "2020-01-01T00:00:00").

6. **Mapped Error** (type: "mappedError")
    - Validates parameters with error codes that map to specific error messages.
    - Rules:
        - "codes": A dictionary mapping each error code (key) to a corresponding error message (value).
        - "typical": (Optional) A single "typical" value indicating the normal/expected state. If the parameter
          value matches this typical value, no warning is generated. If it deviates, the mapped error message
          for the current value is returned.

7. **Unknown/Unsupported Types**
    - If a parameter's "type" is not recognized, it will be ignored and a warning may be logged.

    
Configuration Structure
-----------------------
Each parameter in the JSON5 configuration file must define:
    - "type": The type of validation to apply (e.g., "numeric", "boolean", "mappedError").
    - "prefix": A string that prepends the warning message should it be raised (e.g., "MC", "AMS", ...)
    - Rules specific to the type (e.g., "min", "max" for "numeric"; "valid" for "categorical"; "typical" for "mappedError").
    

Example Configuration
----------------------
{
    "hotPressure": {
        "prefix": "CL",
        "type": "numeric",
        "min": 0.8,
        "max": 2.5
    },
    "isBrakeApplied": {
        "type": "boolean",
        "expected": false
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
        "codes": {
            "0x1": "Error 1: Overvoltage detected",
            "0x2": "Error 2: Overcurrent detected",
            "0x3": "Error 3: Thermal runaway",
            "0x4": "Error 4: Communication failure"
        },
        "typical": "0x0"
    }
}
"""

import json5
import datetime
from typing import List, Union
from Backend.data_logger import DataLogger


class ParameterWarning:
    """
    Represents a warning for a parameter that is out of range or otherwise invalid.

    Attributes:
        param_name (str): The name of the parameter.
        param_value (Union[float, bool, str, list]): The current value of the parameter.
        msg (str): A message describing the warning.
        priority (int): The priority level of the warning (default is 100).
    """

    def __init__(
        self, 
        param_name: str, 
        param_value: Union[float, bool, str, list], 
        msg: str,
        priority: int = 100
    ):
        self.param_name = param_name
        self.param_value = param_value
        self.msg = msg
        self.priority = priority

    def getMsg(self) -> str:
        return self.msg

    def __str__(self) -> str:
        return self.msg
    
    @staticmethod
    def standardMsg(type: str, **kwargs) -> 'ParameterWarning':
        """
        Returns a ParameterWarning instance with a standard message.
        This is a way to ensure consistency across different places creating warnings.

        Params:
            type (str): The type of standard message wanted
            **kwargs: The keywords required to form the message

        Returns:
            ParameterWarning: name, status

        Types of msg w/ required params:
            StatusWarning: name, status
        """
        # Set defaults using .get() to prevent KeyError
        param_name = kwargs.get("param_name", "WarningTemplate")
        param_value = kwargs.get("param_value", "DummyValue")
        name = kwargs.get("name", "DummyName")
        status = kwargs.get("status", "DummyStatus")

        if type == 'StatusWarning':
            return ParameterWarning(
                param_name=name,
                param_value=status,
                msg=f"{name} has status {status}",
                priority=100
            )


VALID_RETURN_STR = ""

class ParameterMonitor:
    """
    Monitors parameters and raises warnings if values are out of range.

    Attributes:
        active_warnings (list[ParameterWarning]): A list to store active warnings.
        parameter_limits (dict): A dictionary containing the limits and validation rules for each parameter.

    Supported Parameter Types:
        - Numeric ("numeric"): Parameters with numerical values and optional min/max bounds.
        - Boolean ("boolean"): Parameters with boolean values and an optional expected value.
        - Categorical ("categorical"): Parameters with string values validated against a predefined list.
        - Array ("array"): Parameters containing lists of numerical values validated against min/max bounds.
        - Timestamp ("timestamp"): Parameters with ISO 8601 timestamps validated against "before" or "after" constraints.
        - Mapped Error ("mappedError"): Parameters with error codes mapping to specific error messages. Includes optional
        support for a "typical" value that represents the normal/expected state.
    """

    active_warnings: list[ParameterWarning]

    def __init__(self, value_limits: Union[str, dict], logger: DataLogger):
        """
        Initializes the ParameterMonitor with a configuration.

        Args:
            value_limits (Union[str, dict]): The path to the configuration file or a dictionary containing the value limits.
            logger (DataLogger): The logger instance for logging messages.
        """
        self.logger = logger
        self.active_warnings = []

        # Load the configuration based on the type of value_limits
        if isinstance(value_limits, str):
            self.parameter_limits = self.__load_config(value_limits)
        elif isinstance(value_limits, dict):
            self.parameter_limits = value_limits
        else:
            raise TypeError("value_limits must be a file path (str) or a configuration dictionary (dict)")

        # Log the initialization
        self.__log('Value Monitor Initialized!', DataLogger.LogSeverity.INFO)


    def check_value(self, param_name: str, param_value: Union[float, bool, str, list]):
        """
        Checks if a parameter value is within the defined constraint
        and raises a warning if it is not.

        Args:
            param_name (str): The name of the parameter to check.
            param_value (Union[float, bool, str, list]): The value of the parameter to check.
        """
        if param_name not in self.parameter_limits:
            # If there's no config for this parameter, log & return
            return self.__log(f'No Value Limits found for param: {param_name} ({param_value})')
        
        rules = self.parameter_limits[param_name]
        param_type = rules.get('type', 'numeric')  # fallback to numeric if unspecified

        # Make warning text
        warning_text = self._validate_value(param_name, param_value, param_type, rules)
        prefix = self.__get_prefix(rules)

        # Check to see if there was a warning returned
        if warning_text == VALID_RETURN_STR:
            # If it's valid, clear any existing warning
            self.clear_warning(param_name)
            return

        # Add the prefix to warning_msg
        warning_msg = prefix + warning_text

        # A warning message indicates the value is invalid or out of range
        parameter_warning = ParameterWarning(param_name, param_value, warning_msg)
        self.create_warning(parameter_warning)



    def _validate_value(
        self, 
        param_name: str, 
        param_value: Union[float, bool, str, list], 
        param_type: str, 
        rules: dict
    ) -> str:
        """
        Dispatch function to validate a parameter value based on its type.
        Returns an error string if validation fails, or an empty string if valid.

        Parameters:
            See `check_value()`

        Returns:
            `str`: A string containing a warning message. If the value is valid, `None` is returned
        """
        if param_type == 'numeric':
            return self._validate_numeric(param_name, param_value, rules)
        elif param_type == 'boolean':
            return self._validate_boolean(param_name, param_value, rules)
        elif param_type == 'categorical':
            return self._validate_categorical(param_name, param_value, rules)
        elif param_type == 'array':
            return self._validate_array(param_name, param_value, rules)
        elif param_type == 'timestamp':
            return self._validate_timestamp(param_name, param_value, rules)
        elif param_type == 'mappedError':
            return self._validate_mapped_error(param_name, param_value, rules)
        else:
            # Unknown type => treat it as an Error
            return self.__log_and_return_err(f"Parameter '{param_name}' has unknown validation type '{param_type}'.")


    def _validate_numeric(self, param_name: str, param_value: Union[float, int], rules: dict) -> str:
        """
        Validates a numeric parameter against min/max bounds.
        
        Returns:
            `str`: An error message if invalid, else empty string.
        """
        # Check correct type (must be a int/float & not a bool)
        if not (isinstance(param_value, (int, float)) and not isinstance(param_value, bool)):
            return (f"{param_name} has value '{param_value}' which is not numeric.")

        min_val = rules.get('min', float('-inf'))
        max_val = rules.get('max', float('inf'))

        if param_value < min_val or param_value > max_val:
            return (f"{param_name} ({param_value}) is out of range: [{min_val}, {max_val}]")
        return VALID_RETURN_STR
    

    def _validate_boolean(self, param_name: str, param_value: bool, rules: dict) -> str:
        """
        Validates a boolean parameter. If 'expected' is given, checks that the value matches it.

        Returns:
            `str`: An error message if invalid, else empty string.
        """
        if not isinstance(param_value, bool):
            return self.__log_and_return_err(f"{param_name} has value '{param_value}' which is not a boolean.")

        expected_val = rules.get('expected')
        if expected_val is not None and param_value != expected_val:
            return (f"{param_name} = {param_value}, but expected {expected_val}.")
        return VALID_RETURN_STR
    

    def _validate_categorical(self, param_name: str, param_value: str, rules: dict) -> str:
        """
        Validates a string parameter against a list of valid categorical options.

        Returns:
            `str`: An error message if invalid, else empty string.
        """
        valid_options = rules.get('valid', [])
        if param_value not in valid_options:
            return (f"{param_name} has value '{param_value}', "
                    f"which is not in valid options: {valid_options}.")
        return VALID_RETURN_STR
    

    def _validate_array(self, param_name: str, param_value: list, rules: dict) -> str:
        """
        Validates an array of numeric values against min/max.

        Returns:
            `str`: An error message if invalid, else empty string.
        """
        if not isinstance(param_value, list):
            return self.__log_and_return_err(f"{param_name} has value '{param_value}' which is not a list.")

        min_val = rules.get('min', float('-inf'))
        max_val = rules.get('max', float('inf'))

        for i, val in enumerate(param_value):
            if not isinstance(val, (int, float)):
                return (f"{param_name}[{i}] = '{val}', which is not numeric.")
            if val < min_val or val > max_val:
                return (f"{param_name}[{i}] = {val} is out of range: [{min_val}, {max_val}].")
        return VALID_RETURN_STR


    def _validate_timestamp(self, param_name: str, param_value: str, rules: dict) -> str:
        """
        Validates the current time against a predetermined timestamp.

        Returns:
            `str`: An error message if invalid, else empty string.
        """
        try:
            dt_value = datetime.datetime.fromisoformat(param_value)
        except ValueError:
            return self.__log_and_return_err(f"{param_name} has value '{param_value}' which is not a valid ISO timestamp.")

        before_str = rules.get('before')
        after_str = rules.get('after')

        # Check 'before'
        if before_str:
            try:
                before_dt = datetime.datetime.fromisoformat(before_str)
                if dt_value >= before_dt:
                    return (f"{param_name} = {param_value}, which is not before {before_str}.")
            except ValueError:
                return self.__log_and_return_err(
                    f"{param_name} has invalid 'before' constraint '{before_str}'.", DataLogger.LogSeverity.ERROR)

        # Check 'after'
        if after_str:
            try:
                after_dt = datetime.datetime.fromisoformat(after_str)
                if dt_value <= after_dt:
                    return (f"{param_name} = {param_value}, which is not after {after_str}.")
            except ValueError:
                return self.__log_and_return_err(
                    f"{param_name} has invalid 'after' constraint '{after_str}'.", DataLogger.LogSeverity.ERROR)

        return VALID_RETURN_STR
    
    def _validate_mapped_error(
        self, 
        param_name: str, 
        param_value: Union[str, int], 
        rules: dict
    ) -> str:
        """
        Validates an error-code parameter where each code maps to a message.

        For "mappedError" parameters:
            - If the current value matches the "typical" value, VALID_RETURN_STR is returned.
            - If the current value deviates from the "typical" value, the corresponding message from the "codes" field
            is returned.
            - If the current value is not in the "codes" field, a warning for an unknown code is generated.

        Returns:
            str: An error message if invalid, or VALID_RETURN_STR if valid.
        """
        codes_map = rules.get("codes", {})
        param_str = str(param_value)  # Convert param_value to string for comparison
        typical_value = str(rules.get("typical", ""))  # Ensure typical value is a string

        # If the current value matches the typical value, return VALID_RETURN_STR
        if param_str == typical_value:
            return VALID_RETURN_STR

        # If the current value is in the codes map, return the associated message
        if param_str in codes_map:
            return f"{param_name} {codes_map[param_str]}"

        # If the value is not recognized, return a error
        return self.__log_and_return_err(f"{param_name} has unknown code '{param_value}'.")

    def create_warning(self, warning: ParameterWarning):
        """
        Adds a warning to the warning list if it does not already exist.

        Args:
            warning (ParameterWarning): The warning to add.
        """
        for existing_warning in self.active_warnings:
            if existing_warning.param_name == warning.param_name:
                # If the warning already exists, return early
                return
        self.active_warnings.append(warning)

        # Log creation of warning
        self.__log(f'{warning.getMsg()}', DataLogger.LogSeverity.WARNING)

    def clear_warning(self, param_name: str):
        """
        Clears the warning for a specific parameter and logs the action.

        Args:
            param_name (str): The name of the parameter to clear the warning for.
        """
        initial_warning_count = len(self.active_warnings)

        # Remove the warning for the specified parameter
        self.active_warnings = [
            warning for warning in self.active_warnings
            if warning.param_name != param_name
        ]

        # Check if a warning was cleared and log the action
        if len(self.active_warnings) < initial_warning_count:
            self.__log(f"Warning cleared for parameter '{param_name}'.", DataLogger.LogSeverity.INFO)


    def get_warnings_as_str(self) -> List[str]:
        """
        Returns a list of active warnings as strings.

        Returns:
            `List[str]`: A list of active warnings.
        """
        warnings = []
        for warning in self.active_warnings:
            warnings.append(str(warning))
        return warnings

    
    def get_warnings(self) -> List[ParameterWarning]:
        """
        Returns a list of active warnings as ParameterWarning objects.

        Returns:
            `List[ParameterWarning]`: A list of active warnings.
        """
        return self.active_warnings
    
    def __log_and_return_err(self, err_msg: str) -> str:
        '''
        Shorthand for logging an error & returning it on the same line.

        Returns:
            `err_msg`
        '''

        self.__log(err_msg, DataLogger.LogSeverity.ERROR)
        return err_msg


    def __load_config(self, config_path: str) -> dict[str, dict]:
        """
        Loads the value limits configuration from a file.

        Args:
            config_path (str): The path to the configuration file.

        Returns:
            dict: A dictionary containing the value limits.
        """
        config: dict[str, dict]

        # Read JSON File
        with open(config_path, 'r') as file:
            config = json5.load(file)

        # Validate mappedError configurations
        for param_name, param_rules in config.items():
            if param_rules.get("type") == "mappedError":
                typical = param_rules.get("typical")
                if typical is not None and str(typical) in param_rules.get("codes", {}):
                    msg = (f"Parameter '{param_name}' has a 'typical' value '{typical}' "
                        f"that exists in its 'codes' dictionary. This is not allowed.")
                    self.__log(msg, DataLogger.LogSeverity.ERROR)
                    raise ValueError(msg)
                if typical is None:
                    msg = (f"Parameter '{param_name}' has no 'typical' value")
                    self.__log(msg, DataLogger.LogSeverity.ERROR)
                    raise ValueError(msg)
                
        # Log File Read
        self.__log('Successfully loaded valuelimits.json.')
        return config
        
    def __get_prefix(self, rules: dict) -> str:
        """"Returns the prefix for a given parameter limit (if it exists)"""
        prefix = rules.get("prefix")

        if prefix is not None:
            return prefix + " "
        else:
            return ""


    def __log(self, msg: str, severity=DataLogger.LogSeverity.DEBUG):
        """Shorthand logging method."""
        self.logger.writeLog(loggerName='ValueMonitor', msg=msg, severity=severity)
        


if __name__ == "__main__":
    # Example JSON configuration as a string
    json_config = """
    {
        "hotPressure": {
            "type": "numeric",
            "min": 0.8,
            "max": 2.5
        },
        "isBrakeApplied": {
            "type": "boolean",
            "expected": false
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
            "before": "2025-05-01T00:00:00"
        },
        "deviceErrorCode": {
            "type": "mappedError",
            "codes": {
                "1": "Error 1: Overvoltage detected",
                "2": "Error 2: Overcurrent detected",
                "3": "Error 3: Thermal runaway",
                "4": "Error 4: Communication failure"
            },
            "typical": "0"
        }
    }
    """
    # Parse JSON into a dictionary
    # value_limits = json5.loads(json_config)

    # Initialize the ParameterMonitor
    logger = DataLogger('ValueMonitor_Test')
    value_monitor = ParameterMonitor('Backend/config/valuelimits.json5', logger)

    # print("Loaded parameter limits:")
    # print(json5.dumps(value_monitor.parameter_limits, indent=4))

    # Example test data (MC)
    # test_data = {
    #     "FAULT" : 7,
    #     "BrakeSignal": 100.001,
    #     "DriveEnable": False,
    #     "CANMapVersion": 24,
    #     "FOC_Id": -1
    # }

    # Example test data (AMS)
    test_data = {
        "Pack_Current": 520,               # numeric, out of range (exceeds max of 500)
        "Pack_Inst_Voltage": 450,          # numeric, within range (0-500)
        "Pack_SOC": -5,                    # numeric, out of range (below min of 0)
        "Relay_State": False,              # boolean, matches the expected value (False)
        "Pack_DCL": 480,                   # numeric, within range (0-500)
        "High_Temperature": 85,            # numeric, out of range (exceeds max of 80)
        "Low_Temperature": -50,            # numeric, out of range (below min of -40)
    }

    # Validate each parameter
    print("\nValidating parameters...")
    for param_name, param_value in test_data.items():
        value_monitor.check_value(param_name, param_value)
