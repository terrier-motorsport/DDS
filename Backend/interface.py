# Interface object for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from enum import Enum
from Backend.data_logger import DataLogger
from typing import Union, List

import can
import cantools
import cantools.database
import subprocess
import time


"""
The purpose of this file is to provide an abstract base class for creating interfaces to different devices 
in the DDS (Data Display System) for Terrier Motorsport.

This base class outlines the essential functionality required by all interface devices, which is to manage 
device initialization, periodic data updates, data caching, and logging. Specific device classes (e.g., 
I2C pressure/temperature sensors) can inherit from this base class and implement device-specific logic for 
initialization and data updates. These child classes will call the base class methods to manage common behavior 
and focus on implementing the unique features of their respective devices.

This approach allows for easy scalability and maintainability as new types of devices are added to the system, 
ensuring that common functionality (caching, logging, status management) is reused across devices while 
still allowing for device-specific logic.

"""

# Enums for types of protocols
class InterfaceProtocol(Enum):
    CAN = 1     # DONE
    I2C = 3     # DONE



# ===== Parent class for all interfaces =====
class Interface:

    '''
    The Interface class serves as a base class for defining and interacting with various device interfaces, such as CAN, I2C, etc. 

    The core functionality provided by this class is common to all interfaces, including methods for updating and retrieving data, handling cache, 
    managing the status of the device, and logging messages. Child classes representing specific types of interfaces should inherit from this class 
    and implement or override certain methods to tailor the behavior for the specific interface they represent.

    Key Methods to Be Implemented or Overridden by Child Classes:
        - `initialize()`: Child classes must override this method to implement the specific initialization logic for the interface device.
        - `update()`: Child classes should override this method to implement the logic for updating the sensor data or retrieving values specific to the device.
    
    The `update()` method should be called periodically to ensure that the device's data is up-to-date. The `initialize()` method should be called 
    once to set up the interface before it is used. 

    Methods Inherited from the Base Class:
        - `get_name()`: Returns the name of the interface device.
        - `get_protocol()`: Returns the protocol used by the interface (e.g., CAN, I2C).
        - `get_data()`: Retrieves the most recent cached data for the specified key. 
        - `log()`: Logs messages to a provided logger for tracking the status and events related to the device.
        - `map_to_percentage()`: Converts a value within a specified range to a percentage.
        - `percentage_to_map()`: Converts a percentage back to the corresponding value within a specified range.
        - `clamp()`: Clamps a value between a given minimum and maximum.
        
    Device Status:
        The `status` attribute reflects the state of the interface and can be one of the following:
            - `ACTIVE`: The interface is functioning and polling data.
            - `DISABLED`: The interface is inactive and not being polled.
            - `ERROR`: An error occurred, and the interface will attempt to be re-initialized.
            - `NOT_INITIALIZED`: The interface has not been initialized yet.

    Caching:
        The class maintains a `cached_values` dictionary that stores the most recent sensor data.
    '''

    class Status(Enum):
        '''
        This keeps track of the state of the interface.
        
        ACTIVE: Data is being polled constantly.
        DISABLED: The interface is ignored.
        ERROR: There was an error polling data and the interface will attempt to be re-initialized.
        NOT_INITIALIZED: The interface has not been initialized yet.
        '''
        ACTIVE = 1,
        DISABLED = 2,
        ERROR = 3,
        NOT_INITIALIZED = 4


    # Class variables
    CACHE_TIMEOUT_THRESHOLD = 2      # Cache timeout in seconds
    cached_values: dict              # Dictionary to store cached values
    last_cache_update: float         # Time since last cache update


    def __init__(self, name: str, sensorProtocol: InterfaceProtocol, logger: DataLogger):
        '''
        Initializes an interface device with the given parameters.

        This constructor should handle initialization code that is not expected to raise an error.
        Any logic that involves interacting with physical devices should be placed in the `initialize()` 
        method to ensure proper error handling during the initialization process.

        This constructor should be called by child classes to properly initialize the common aspects 
        of the interface device. Child classes must then implement their own `__init__()` and `initialize()` 
        methods to handle device-specific initialization.

        Parameters:
            name (str): The name of the interface device.
            sensorProtocol (InterfaceProtocol): The protocol used by the sensor interface (e.g., I2C, CAN).
            logger (DataLogger): A logger instance for logging device-related messages.

        Attributes:
            sensorProtocol (InterfaceProtocol): The protocol used by the sensor interface.
            name (str): The name of the device.
            log (DataLogger): Logger instance used for logging messages.
            status (Status): The current status of the device, initially set to `NOT_INITIALIZED`.
            cached_values (dict): A dictionary used to store cached sensor readings.
            last_cache_update (float): Timestamp of the last cache update.
        '''
        
        # Class variables
        self.sensorProtocol = sensorProtocol
        self.name = name
        self.log = logger
        self.__status = self.Status.NOT_INITIALIZED

        # Init cache
        self.cached_values = {}

        # Init cache timeout
        self.last_cache_update = time.time()

        # Log device creation
        self._log(f'Created {self.sensorProtocol.name} device {self.name}.')


    def initialize(self):
        """
        Initializes the device by setting its status to active and logging the successful initialization.

        This method is intended to be overridden by child classes to implement the specific initialization 
        logic for different devices. If there is an error with the physical devices, it may raise an error.

        Child classes must provide their own implementation of this method. After completing their specific 
        initialization tasks, child classes should call this method to update the status and log the successful 
        initialization.

        Example:
            class MyDevice(Device):
                def initialize(self):
                    # Perform custom initialization
                    super().initialize()  # Call the parent class method once initialization is complete
        """
        
        # Set status to active
        self.__status = self.Status.ACTIVE

        # Log device initialization
        self._log(f'Initialized {self.sensorProtocol.name} device {self.name} successfully.')


    def update(self):
        """
        Intended to be overridden by child classes to update the `cached_values` dictionary 
        with the latest sensor readings.

        If not overridden, logs an error message.

        Subclasses should implement their own data retrieval and caching logic.
        """
        self._log("The 'update' method has not been properly overridden in the child class.", 
                  self.log.LogSeverity.ERROR)


    # ===== GETTER METHODS =====
    def get_name(self) -> str:
        """
        Retrieves the name of the interface.

        Returns:
            str: The name of the interface.
        """
        return self.name


    def get_protocol(self) -> InterfaceProtocol:
        """
        Retrieves the protocol of the current interface.

        Returns:
            InterfaceProtocol: The protocol associated with the interface (e.g., CAN, I2C, etc.).
        """
        return self.sensorProtocol


    def get_data(self, key: str) -> Union[str, float, int]:
        """
        Retrieves the most recent cached data associated with the provided key.

        Parameters:
            key (str): The key for which the associated cached data is to be retrieved.

        Returns:
            Union[str, float, int, None]: The cached value corresponding to the key if it exists,
                                        otherwise None. The value type can be str, float, or int.
        """

        # Check if the key exists in the cache
        if key in self.cached_values:
            return self.cached_values[key]
        else:
            self._log(f"No cached data found for key: {key}", self.log.LogSeverity.WARNING)
            return None


    def get_all_param_names(self) -> List[str]:
        """
        Returns all parameter names (keys) from the cached values dictionary.

        Returns:
            List[str]: A list of all parameter names in the cached values dictionary.
        """
        return list(self.cached_values.keys())
    

    def change_status(self, new_status: Status):
        """
        Changes the Interface's status to the one specified.
        Logs if there is a change in status.

        Parameters:
            new_status (Status): The status to switch the device to.
        """

        # Return early if there is no change in status
        if self.__status == new_status:
            return
        
        # Log the change in status
        self._log(f"{self.name} changed from {self.__status.name} to {new_status.name}.")

        # Change the status
        self.__status = new_status
        
        

    # ===== CACHING METHODS =====
    def _update_cache_timeout(self):
        """
        Checks if the cache has expired due to lack of new data and clears it if necessary.

        This method should be called when no new data is found. It compares the current 
        time with the time of the last cache update. If the time difference exceeds the 
        cache timeout threshold, the cache is cleared to ensure outdated data is removed.
        """

        # Return early if the cache is already empty
        if not self.cached_values:
            return

        # Update the current time
        current_time = time.time()

        # Check if the cache has expired
        if current_time - self.last_cache_update > self.CACHE_TIMEOUT_THRESHOLD:
            # Clear the cache & log event
            self.cached_values.clear()
            self._log("Cache cleared due to data timeout.", self.log.LogSeverity.WARNING)


    def _reset_last_cache_update_timer(self):
        """
        Resets the timer that tracks the last time the cache was updated.

        This method should be called every time the cache is updated. It updates the 
        `last_cache_update` attribute to the current time (in seconds since the epoch), 
        ensuring that the elapsed time can be tracked accurately for cache validation.

        Notes:
            - The `last_cache_update` attribute is used to monitor the time since the last 
            cache update, and this method must be invoked each time the cache is modified 
            to ensure the timer reflects the most recent update.
        """
        self.last_cache_update = time.time()


    # ===== OTHER METHODS =====
    def _log_telemetry(self, param_name: str, value, units: str):
        """
        Logs telemetry data to the telemetry file.

        Parameters:
            param_name (str): The name of the parameter being logged.
            value (Any): The value of the parameter.
            units (str): The units of the parameter's value.
        """
        self.log.writeTelemetry(
            device_name=self.name, 
            param_name=param_name,
            value=value,
            units=units)


    def _log(self, msg: str, severity=DataLogger.LogSeverity.INFO):
        """Shorthand logging method."""
        self.log.writeLog(loggerName=self.name, msg=msg, severity=severity)


    # ===== GETTER/SETTER METHODS ====
    @property
    def status(self):                    # Status Getter
        return self.__status
    
    @status.setter
    def status(self, value: Status):     # Status Setter
        self.change_status(value)

    # ===== HELPER METHODS ====
    @staticmethod
    def map_to_percentage(value : int, min_value : int, max_value : int) -> float:
        if value < min_value or value > max_value:
            raise ValueError("Value out of range")
        return (value - min_value) / (max_value - min_value)
    
    @staticmethod
    def percentage_to_map(percentage, min_value : int, max_value : int) -> float:
        if percentage < 0.0 or percentage > 1.0:
            raise ValueError("Percentage out of range")
        return percentage * (max_value - min_value) + min_value
    
    @staticmethod
    def clamp(value, min_value, max_value):
        """Clamps a value between a minimum and maximum."""
        return max(min_value, min(value, max_value))



# ===== I2CDevice class for DDS' I2C Backend =====
class I2CDevice(Interface):
    """
    Represents an I2C device in the DDS (Data Display System) backend.

    This class serves as a base for I2C devices, providing fundamental functionality 
    for I2C communication. Each device communicates through a unique address and 
    responds to specific commands. It is likely that each I2C device will have a 
    dedicated subclass that implements device-specific behavior, including custom 
    decoding functions.

    Attributes:
        name (str): The name of the I2C device.
        logger (DataLogger): Logger used for logging messages and events.
    """
    
    def __init__(self, name: str, logger: DataLogger):
        """
        Initializes an I2CDevice instance.

        Parameters:
            name (str): The name of the I2C device.
            logger (DataLogger): Logger for logging device events and messages.
        """
        # Initialize the parent class (Interface)
        super().__init__(name, InterfaceProtocol.I2C, logger=logger)


    def close_connection(self):
        """
        Closes the I2C connection.
        """
        # Close the I2C bus connection
        self.bus.close()



# ===== CANInterface class for DDS' CAN Backend =====
class CANInterface(Interface):

    """
    Manages the CAN interface for communication with CAN bus devices.

    This class extends the Interface class and provides functionality for initializing 
    and interacting with a CAN bus. Each device connected via CAN can have its own 
    CAN database (DBC file), which can be loaded using the `add_database()` method. 
    This allows the interface to decode CAN messages and manage communication.
    Additional databases can be added to the CANInterface with the add_database() function.

    Attributes:
        CAN_TIMEOUT (float): Timeout value for reading CAN messages (default 0.0001s).
        can_bus (can.BusABC): The CAN bus object that facilitates communication.
        db (cantools.database.Database): The database containing CAN message definitions.
        cached_values (dict): A dictionary storing the decoded signal values.
        database_path (str): The path to the CAN DBC file.
    """

    # 0.1 ms timeout for reading CAN Bus
    TIMEOUT = 0.0001  
    

    def __init__(self, name: str, can_bus: can.BusABC, database_path: str, logger: DataLogger):
        """
        Initializes a CANInterface instance.

        Parameters:
            name (str): The name of the interface.
            can_bus (can.BusABC): The CAN bus interface object.
            database_path (str): Path to the DBC file for CAN database.
            logger (DataLogger): Logger for logging messages.
        """
        
        # Initialize the parent class (Interface)
        super().__init__(name, InterfaceProtocol.CAN, logger=logger)

        # Set up the database path and load the CAN database
        self.database_path = database_path
        self.db = cantools.database.Database()
        self.add_database(self.database_path)

        # Set up the CAN bus interface
        self.can_bus = can_bus

        
    def initialize(self):
        """
        Initializes the interface by communicating with physical devices.
        
        This method interacts with the CAN bus and ensures the connection is functional.
        If communication with the physical device fails, it attempts to initialize the CAN network.
        Any failure in this process may raise an error.
        """
        
        # Extract the CAN interface name from the channel info (e.g., "socketcan channel 'can0'")
        channel_info = self.can_bus.channel_info
        start = channel_info.find("'") + 1
        end = channel_info.find("'", start)

        # Get the interface name (e.g., 'can0')
        interface_name = channel_info[start:end]

        try:
            # Attempt to fetch a CAN message to verify connection
            self.__fetch_can_message()
        except can.CanOperationError:
            # If fetching the message fails, try to initialize the CAN network
            self.__init_can_network(interface_name)
            
        # Finish the initialization process
        super().initialize()

    
    def update(self):
        """
        Reads data from the CAN bus, logs telemetry, decodes messages, and updates the cached values.
        """
        # Get data from the CAN Bus
        message = self.__fetch_can_message()

        # Check if the message is valid; if not, update cache timeout and return early.
        # This means no messages were received, and we don't need to continue the update process.
        if not self.__is_valid_message(message):
            return

        # Decode the received CAN message to extract relevant data.
        data = self.__decode_can_msg(message)
        if not data:
            return

        # Reset the last cache update timer 
        self._reset_last_cache_update_timer()

        # Log the decoded data
        self.__log_decoded_data(message, data)

        # Update or add all decoded values to the cached values dictionary.
        for signal_name, value in data.items():
            self.cached_values[signal_name] = value
        

    def add_database(self, filename: str):
        """
        Adds a DBC file to the CAN database.

        Parameters:
            filename (str): Path to the DBC file to be added.
        """
        try:
            self.db.add_dbc_file(filename)
            self._log(severity=self.log.LogSeverity.INFO, msg=f"Loaded DBC file: {filename}")
        except Exception as e:
            self._log(severity=self.log.LogSeverity.ERROR, msg=f"Failed to load DBC file {filename}: {e}")
            raise


    def get_avail_signals(self, messageName : str) -> can.Message:
        '''Returns the avalable CAN signals from the database with the specified message name'''
        return self.db.get_message_by_name(messageName)
    

    def close_connection(self):
        '''Closes the connection to the CAN Bus'''
        self.can_bus.shutdown()
        

    def __log_decoded_data(self, message: can.Message, data: dict):
        """
        Logs the decoded CAN data along with their respective units.
        """
        for signal_name, value in data.items():

            # Get the units for the signal
            cantools_message = self.db.get_message_by_frame_id(message.arbitration_id)
            cantools_signal = cantools_message.get_signal_by_name(signal_name)
            unit = cantools_signal.unit

            # Write the data to the log file 
            super()._log_telemetry(signal_name, value, units=unit)
        

    def __is_valid_message(self, message):
        """
        Checks if the message is valid; updates the cache timeout and returns False if not.
        """
        if not message:
            self._update_cache_timeout()
            return False
        return True


    def __fetch_can_message(self) -> can.Message:
        """
        Fetches a single CAN message from the CAN Bus.

        Returns:
            can.Message: A CAN message object containing the received message data, or `None` 
                        if no message was received within the specified timeout.

        Raises:
            can.exceptions.CanOperationError: If the CAN Bus interface encounters an error 
                                            during the operation (e.g., network not open).
        
        Notes:
            - This function relies on the `self.can_bus.recv` method to receive the CAN message.
            - The `CAN_TIMEOUT` is the maximum time allowed to wait for a message before returning `None`.
        """

        # Read a single frame of CAN data
        return self.can_bus.recv(self.TIMEOUT)
        
    
    def __decode_can_msg(self, msg: can.Message) -> dict:
        """
        Decodes the given CAN message using the stored CAN Databases.

        Parameters:
            msg (can.Message): The CAN message to decode.

        Returns:
            dict: A dictionary with the decoded message data, or `None` if no database entry is found.
        """

        try:
            # Decode the CAN message using the database
            return self.db.decode_message(msg.arbitration_id, msg.data)
        except KeyError:
            # Log a warning if no database entry matches the arbitration ID
            self._log(f"No database entry found for {msg}", self.log.LogSeverity.WARNING)
            return None


    def __init_can_network(self, can_interface: str):
        """
        Initializes the specified CAN network interface.

        Configures the CAN interface by setting its bitrate and transmit queue length at the OS level.

        Parameters:
            can_interface (str): The name of the CAN interface (e.g., "can0").
        """

        # Log a warning to indicate the initialization attempt
        self._log(f"CAN Bus not found... Attempting to open one on {can_interface}.", DataLogger.LogSeverity.WARNING)


        # Bring up the CAN interface with the specified bitrate
        subprocess.run(
            ["sudo", "ip", "link", "set", can_interface, "up", "type", "can", "bitrate", "1000000"],
            check=True,
            timeout=3
        )

        # Set the transmit queue length for the CAN interface
        subprocess.run(
            ["sudo", "ifconfig", can_interface, "txqueuelen", "65536"],
            check=True,
            timeout=3
        )


if __name__ == "__main__":

    logger = DataLogger('InterfaceTest')

    test = Interface('testInterface', InterfaceProtocol.I2C, logger)

    print(test.status)
    test.status = test.Status.DISABLED
    print(test.status)