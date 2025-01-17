# Interface object for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from enum import Enum
from Backend.data_logger import DataLogger
from Backend.device import Device
from typing import Dict, Union, List
from abc import ABC, abstractmethod

import can
import cantools
import cantools.database
from smbus2 import SMBus
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

# Exception for device not being active
class InterfaceNotActiveException(Exception):
    """Raised when an operation is attempted on a device that is not active."""
    pass


# ===== Parent class for all interfaces =====
class Interface(ABC):

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

    class InterfaceStatus(Enum):
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
    interfaceProtocol: InterfaceProtocol
    name: str
    log: DataLogger
    __status: InterfaceStatus

    # Device variables
    devices: Dict[str, Device]


    def __init__(self, 
                 name: str,
                 devices: List[Device],
                 interfaceProtocol: InterfaceProtocol, 
                 logger: DataLogger):
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
        self.interfaceProtocol = interfaceProtocol
        self.name = name
        self.log = logger
        self.__status = self.InterfaceStatus.NOT_INITIALIZED

        # Set & Verify that devices have unique names
        device_names = [device.name for device in devices]
        if len(device_names) != len(set(device_names)):
            raise ValueError(f"Duplicate device names found: {device_names}")
        # Convert List (input) into dict (self.devices)
        self.devices = {}
        for device in devices:
            self.devices[device.name] = device


        # Log Interface creation
        self._log(f'Created {self.interfaceProtocol.name} Interface {self.name}.')


    def initialize(self):
        """
        Initializes each device on the interface.

        Must be called before data can be collected by devices.
        """

        for key, device in self.devices.items():
            device.initialize()
        
        # Set status to active
        self.__status = self.InterfaceStatus.ACTIVE

        # Log device initialization
        self._log(f'Initialized {self.interfaceProtocol.name} device {self.name} successfully.')


    def update(self):
        """
        Updates the `cached_values` dictionary 
        with the latest sensor readings.

        Should be called as often as possible.
        """
        if self.__status != self.InterfaceStatus.ACTIVE:
            raise InterfaceNotActiveException(f"Cannot update {self.name}: Device is not active.")
        
        for key, device in self.devices.items():
            device.update()
             

    # ===== ABSTRACT METHODS =====
    @abstractmethod
    def close_connection(self):
        """
        Closes the respective interface
        """


    # ===== MAIN METHODS =====
    def get_data_from_device(self, device_key: str, data_key: str) -> Union[str, float, int, None]:
        """
        Retrieves the most recent cached data associated with the provided key.

        Parameters:
            device_key (str): The key for the device where the data exists.
            data_key (str): The key for the data being retrieved.

        Returns:
            Union[str, float, int, None]: The cached value corresponding to the key if it exists,
                                        otherwise None. The value type can be str, float, or int.
        """

        # Verify device exists
        if device_key not in self.devices:
            self._log(f"No device found for key: {device_key}", self.log.LogSeverity.WARNING)
            return None
        
        # Get the data
        data = self.devices[device_key].get_data(data_key)

        # Return the data
        return data

    def get_all_device_names(self) -> List[str]:
        """
        Retrieves a list of all device names managed by this interface.

        Returns:
            List[str]: A list containing the names of all devices owned by the interface.
        """
        return list(self.devices.keys())
    

    # ===== OTHER METHODS =====
    def _initialize_device(self, device: Device):
        """
        Safely initializes a given device, 
        handling all errors that could possibly be raised during the inialization.
        """

        self._log(f'Initializing {device.name} Device on {self.name} ({self.interfaceProtocol.name})')

        # Initalize Device 
        try:
            # Initialize the device
            device.initialize()

            # Try reading the first peice of data
            device.update()
        except Exception as e:
            # Log the error
            self._log(f'Was unable to intialize device {device.name}: {e}.', DataLogger.LogSeverity.CRITICAL)

            # Change device status to error
            device.__status = Device.DeviceStatus.ERROR
            return

        # ===== FINISHED ===== 
        self._log(f'Finished initializing {device.name}!')


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
    def status(self):                             # Status Getter
        return self.__status
    

    @status.setter
    def status(self, value: InterfaceStatus):     # Status Setter
        self.change_status(value)


    def change_status(self, new_status: InterfaceStatus):
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



# ===== I2CInterface class for DDS' I2C Backend =====
class I2CInterface(Interface):
    """
    Represents an I2C Interface in the DDS (Data Display System) backend.

    Each I2C Interface contains at least one device, 
    which it will collect data from periodically and add the data to the cached_values.

    This class serves as a base for I2C devices, providing fundamental functionality 
    for I2C communication. Each device communicates through a unique address and 
    responds to specific commands. It is likely that each I2C device will have a 
    dedicated device class that implements device-specific behavior, including custom 
    decoding functions.

    Attributes:
        name (str): The name of the I2C device.
        logger (DataLogger): Logger used for logging messages and events.
    """
    

    def __init__(self, name: str, i2c_bus: SMBus, devices: List[Device], logger: DataLogger):
        super().__init__(name, devices, InterfaceProtocol.I2C, logger)
        self.bus = i2c_bus


    def initialize(self):
        return super().initialize()


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
    

    def __init__(self, name: str, can_bus: can.BusABC, devices: List[Device], logger: DataLogger):
        """
        Initializes a CANInterface instance.

        Parameters:
            name (str): The name of the interface.
            can_bus (can.BusABC): The CAN bus interface object.
            database_path (str): Path to the DBC file for CAN database.
            logger (DataLogger): Logger for logging messages.
        """
        
        # Initialize the parent class (Interface)
        super().__init__(name, devices, InterfaceProtocol.CAN, logger=logger)

        # Initialize the database
        self.db = cantools.database.Database()

        # Set up the CAN bus interface
        self.bus = can_bus

        
    def initialize(self):
        """
        Initializes the interface by communicating with physical devices.
        
        This method interacts with the CAN bus and ensures the connection is functional.
        If communication with the physical device fails, it attempts to initialize the CAN network.
        Any failure in this process may raise an error.
        """
        
        # Extract the CAN interface name from the channel info (e.g., "socketcan channel 'can0'")
        channel_info = self.bus.channel_info
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
        self.bus.shutdown()
        

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
        return self.bus.recv(self.TIMEOUT)
        
    
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


    @staticmethod
    def __init_can_network(can_interface: str, logger: DataLogger):
        """
        Initializes the specified CAN network interface.

        Configures the CAN interface by setting its bitrate and transmit queue length at the OS level.

        Parameters:
            can_interface (str): The name of the CAN interface (e.g., "can0").
        """

        # Log a warning to indicate the initialization attempt
        logger.writeLog('CAN', f"CAN Bus not found... Attempting to open one on {can_interface}.", DataLogger.LogSeverity.WARNING)


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


from Backend.resources.ads_1015 import ADS_1015
from Backend.resources.dtihv500 import DTI_HV_500
from Backend.resources.analog_in import Analog_In, ValueMapper
import smbus2

if __name__ == "__main__":

    logger = DataLogger('InterfaceTest')
    i2cBus = smbus2.SMBus(2)
    canBus = can.interface.Bus('can0', interface="socketcan")


    # Setting up a test i2c interface
    m3200_pressure_mapper = ValueMapper(
        voltage_range=[0.5, 4.5], 
        output_range=[0, 17])
    i2cinterface = I2CInterface(
        'I2C Interface',
        devices=[
            ADS_1015('ADC1',logger,i2cBus,[
                Analog_In('hotPressure', 'bar', mapper=m3200_pressure_mapper, tolerance=0.1),         #ADC1(A0)
                Analog_In('hotTemperature', '°C', mapper=m3200_pressure_mapper, tolerance=0.1),       #ADC1(A1)
                Analog_In('coldPressure', 'bar', mapper=m3200_pressure_mapper, tolerance=0.1),        #ADC1(A2)
                Analog_In('coldTemperature', '°C', mapper=m3200_pressure_mapper, tolerance=0.1)       #ADC1(A3)
            ]),
            ADS_1015('ADC2',logger,i2cBus,[
                Analog_In('hotPressure', 'bar', mapper=m3200_pressure_mapper, tolerance=0.1),         #ADC2(A0)
                Analog_In('hotTemperature', '°C', mapper=m3200_pressure_mapper, tolerance=0.1),       #ADC2(A1)
                Analog_In('coldPressure', 'bar', mapper=m3200_pressure_mapper, tolerance=0.1),        #ADC2(A2)
                Analog_In('coldTemperature', '°C', mapper=m3200_pressure_mapper, tolerance=0.1)       #ADC2(A3)
            ]),
        ],
        logger=logger)
    
    # Make a test CAN interface
    caninterface = CANInterface(
        name='CAN Interface',
        can_bus=canBus,
        devices=[
            DTI_HV_500(logger)

        ],
        logger=logger

    )

    i2cinterface.initialize()
    i2cinterface.update()

    caninterface.initialize()
    caninterface.update()

    print(i2cinterface.get_data_from_device("ADC1", "hotPressure"))
    
    

