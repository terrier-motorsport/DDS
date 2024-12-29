# Value Monitor for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

import json
from typing import List

"""
This module defines classes to monitor values from the DDS_IO system. Signals can be given a max/min 
range in the valuelimits.json file. The ParameterMonitor class observes these signals and logs a 
warning if any value falls outside the given range.

Classes:
    ParameterWarning: Represents a warning for a parameter that is out of range.
    ParameterMonitor: Monitors parameters and raises warnings if values are out of range.

TODO:
    - Add support for different limits based on different driving modes.
"""


class ParameterWarning:
    """
    Represents a warning for a parameter that is out of range.

    Attributes:
        param_name (str): The name of the parameter.
        param_value (float): The current value of the parameter.
        min (float): The minimum acceptable value for the parameter.
        max (float): The maximum acceptable value for the parameter.
        priority (int): The priority level of the warning (default is 100).

    Methods:
        __str__(): Returns a string representation of the warning.
    """

    msg: str
    param_name: str
    param_value: float
    min: float
    max: float
    priority: int

    def __init__(self, param_name: str, param_value: float, min: float, max: float, priority: int = 100):
        self.param_name = param_name
        self.param_value = param_value
        self.min = min
        self.max = max
        self.priority = priority
        self.msg = f'{self.param_name} ({self.param_value:.2f}) is out of range: [{self.min}, {self.max}]'

    def getMsg(self) -> str:
        return self.msg

    def __str__(self) -> str:
        return self.msg


class ParameterMonitor:
    """
    Monitors parameters and raises warnings if values are out of range.

    Attributes:
        active_warnings (list[ParameterWarning]): A list to store active warnings.
        parameter_limits (dict): A dictionary containing the min and max limits for each parameter.

    Methods:
        __init__(value_limits_file_path: str): Initializes the ParameterMonitor with a configuration file.
        check_value(param_name: str, param_value: float): Checks if a parameter value is within the defined limits and raises a warning if it is not.
        create_warning(warning: ParameterWarning): Adds a warning to the warning list if it does not already exist.
        clear_warning(param_name: str): Clears the warning for a specific parameter.
        get_warnings() -> List[str]: Returns a list of active warnings as strings.
        __load_config(config_path: str) -> dict: Loads the value limits configuration from a file.
    """

    active_warnings: list[ParameterWarning]

    def __init__(self, value_limits_file_path: str):
        """
        Initializes the ParameterMonitor with a configuration file.

        Args:
            value_limits_file_path (str): The path to the configuration file containing value limits.
        """
        self.active_warnings = []
        self.parameter_limits = self.__load_config(value_limits_file_path)


    def check_value(self, param_name: str, param_value: float):
        """
        Checks if a parameter value is within the defined limits and raises a warning if it is not.

        Args:
            param_name (str): The name of the parameter to check.
            param_value (float): The value of the parameter to check.
        """
        try:
            min_value = self.parameter_limits[param_name]['min']
            max_value = self.parameter_limits[param_name]['max']
        except KeyError:
            # This happens if there is no database entry for the parameter.
            # In this case, we can ignore it and return early.
            return

        if not min_value <= param_value <= max_value:
            # Raise a warning for the parameter
            parameter_warning = ParameterWarning(param_name, param_value, min_value, max_value)
            self.create_warning(parameter_warning)
        else:
            self.clear_warning(param_name)


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


    def clear_warning(self, param_name: str):
        """
        Clears the warning for a specific parameter.

        Args:
            param_name (str): The name of the parameter to clear the warning for.
        """
        self.active_warnings = [
            warning for warning in self.active_warnings 
            if warning.param_name != param_name
        ]


    def get_warnings(self) -> List[str]:
        """
        Returns a list of active warnings as strings.

        Returns:
            List[str]: A list of active warnings.
        """
        warnings = []
        for warning in self.active_warnings:
            warnings.append(str(warning))
        return warnings


    def __load_config(self, config_path: str) -> dict:
        """
        Loads the value limits configuration from a file.

        Args:
            config_path (str): The path to the configuration file.

        Returns:
            dict: A dictionary containing the value limits.
        """
        with open(config_path, 'r') as file:
            return json.load(file)
        

if __name__ == '__main__':

    value_monitor = ParameterMonitor('Backend/config/valuelimits.json')

    # Print the loaded parameter limits
    print("Loaded parameter limits:")
    print(value_monitor.parameter_limits)

    # Test 1: Check if the parameter limits are loaded correctly
    print("\nTest 1: Check if the parameter limits are loaded correctly")
    try:
        assert value_monitor.parameter_limits['hotTemperature']['max'] == 110
        print("Test 1 Passed")
    except AssertionError:
        print("Test 1 Failed")

    # Test 2: Check a value within the range
    print("\nTest 2: Check a value within the range")
    value_monitor.check_value('hotTemperature', 30)
    try:
        assert len(value_monitor.active_warnings) == 0
        print("Test 2 Passed")
    except AssertionError:
        print("Test 2 Failed")

    # Test 3: Check a value outside the range
    print("\nTest 3: Check a value outside the range")
    value_monitor.check_value('hotTemperature', 150)
    try:
        assert len(value_monitor.active_warnings) == 1
        assert value_monitor.active_warnings[0].param_name == 'hotTemperature'
        print("Test 3 Passed")
    except AssertionError:
        print("Test 3 Failed")

    # Test 4: Clear a warning
    print("\nTest 4: Clear a warning")
    value_monitor.clear_warning('hotTemperature')
    try:
        assert len(value_monitor.active_warnings) == 0
        print("Test 4 Passed")
    except AssertionError:
        print("Test 4 Failed")

    # Test 5: Get warnings as strings
    print("\nTest 5: Get warnings as strings")
    value_monitor.check_value('hotTemperature', 150)
    warnings = value_monitor.get_warnings()
    try:
        assert len(warnings) == 1
        assert warnings[0] == "hotTemperature (150) is out of range: [-40, 130]"
        print("Test 5 Passed")
    except AssertionError:
        print("Test 5 Failed")

    # Test 6: Check a parameter not in the config file
    print("\nTest 6: Check a parameter not in the config file")
    value_monitor.check_value('unknownParameter', 50)
    try:
        assert len(value_monitor.active_warnings) == 1  # Should still be 1 from the previous test
        print("Test 6 Passed")
    except AssertionError:
        print("Test 6 Failed")

    # Test 7: Clear a warning for a parameter not in the config file
    print("\nTest 7: Clear a warning for a parameter not in the config file")
    value_monitor.clear_warning('unknownParameter')
    try:
        assert len(value_monitor.active_warnings) == 1  # Should still be 1 from the previous test
        print("Test 7 Passed")
    except AssertionError:
        print("Test 7 Failed")
