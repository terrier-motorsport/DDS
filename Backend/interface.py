# Interface object for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from enum import Enum
from Backend.data_logger import DataLogger
from Backend.device import Device, CANDevice, I2CDevice
from Backend.value_monitor import ParameterMonitor, ParameterWarning
from typing import Any, Dict, Union, List
from abc import ABC, abstractmethod

import can
import cantools
import cantools.database
from smbus2 import SMBus
import subprocess
import time


"""
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
    CAN = 1
    I2C = 3

# Exception for device not being active
class InterfaceNotActiveException(Exception):
    """Raised when an operation is attempted on a device that is not active."""
    pass


# ===== Parent class for all interfaces =====
class Interface(ABC):

    '''
    The purpose of this file is to provide an abstract base class for creating interfaces.
    An interface as defined as an object which interfaces with a data transmission protocol (Ex. CAN)
    and contains devices on that protocol.

    Abstract Description:
        The core functionality provided by this class is common to all interfaces, including methods for updating and retrieving data, handling cache, 
        managing the status of the device, and logging messages. Child classes representing specific types of interfaces should inherit from this class 
        and implement or override certain methods to tailor the behavior for the specific interface they represent.

    Using the Interface Class:
        The `initialize()` method should be called once to set up the interface before it is used. 
        The `update()` method should be called as often as possible to update the device's data.

    Methods Inherited from the Base Class:
        - `get_name()`: Returns the name of the interface device.
        - `get_protocol()`: Returns the protocol used by the interface (e.g., CAN, I2C).
        - `get_data()`: Retrieves the most recent cached data for the specified key. 
        - `log()`: Logs messages to a provided logger for tracking the status and events related to the device.
        
    Device Status:
        The `status` attribute reflects the state of the interface and can be one of the following:
            - `ACTIVE`: The interface is functioning and polling data.
            - `DISABLED`: The interface is inactive and not being polled.
            - `ERROR`: An error occurred, and the interface will attempt to be re-initialized.
            - `NOT_INITIALIZED`: The interface has not been initialized yet.
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
    bus: Any             # To be implemented by subclass

    # Device variables
    devices: Dict[str, Device]


    def __init__(self, 
                 name: str,
                 devices: List[Device],
                 interfaceProtocol: InterfaceProtocol, 
                 logger: DataLogger,
                 parameter_monitor: ParameterMonitor):
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
        self.parameter_monitor = parameter_monitor
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


    # ===== PUBLIC METHODS =====
    def initialize(self, bus):
        """
        Initializes each device on the interface.

        Must be called before data can be collected by devices.

        Parameters:
            bus: The bus on which devices on this interface should use.
        """

        # Initialize devices
        for key, device in self.devices.items():
            self._initialize_device(device, bus)

        # Set status to active
        self.status = self.InterfaceStatus.ACTIVE

        # Make everything is working
        self.update()

        # Log Interface initialization
        self._log(f'Finish initializing {self.interfaceProtocol.name} interface {self.name} successfully.')


    def update(self):
        """
        Updates each device on the interface and monitors the parameters of the device.
        """

        if self.__status != self.InterfaceStatus.ACTIVE:
            raise InterfaceNotActiveException(f"Cannot update {self.name}: Device is not active.")
        
        for key, device in self.devices.items():
            if device.status == Device.DeviceStatus.ACTIVE:
                device.update()
                self.__monitor_device_parameters()
            elif device.status == Device.DeviceStatus.ERROR:
                # Create warning for device
                self.parameter_monitor.create_warning(ParameterWarning(
                    f'{device.name}',
                    f'Error',
                    'ERROR'
                ))
                try:
                    device.initialize(self.bus)
                except Exception as e:
                    self._log(f'Couldn\'t init {device.name}, {e}', DataLogger.LogSeverity.DEBUG)
                    # print(f'Err init dev {device.name}, {e}')
                pass
             

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
    

    # ===== PRIVATE METHODS =====
    def _initialize_device(self, device: Device, bus):
        """
        Safely initializes a given device, 
        handling all errors that could possibly be raised during the inialization.
        """

        self._log(f'Initializing {device.name} Device on {self.name} ({self.interfaceProtocol.name})')

        # Initalize Device 
        try:
            # Initialize the device
            device.initialize(bus)

        except Exception as e:
            # Log the error
            self._log(f'Was unable to intialize device {device.name}: {e}.', DataLogger.LogSeverity.CRITICAL)
            self._log(f'{device.name} will be disabled since it failed at runtime.', DataLogger.LogSeverity.CRITICAL)

            # If the device throws an error at runtime, it will be disabled for the rest of the session.
            device.status = Device.DeviceStatus.DISABLED

            # Create warning for device
            self.parameter_monitor.create_warning(ParameterWarning.standardMsg(
                'DeviceStatusWarning',
                dev_name=f"{device.name}",
                dev_status=f"{device.status.name}"
            ))
            return
            

        # ===== FINISHED ===== 
        self._log(f'Finished initializing {device.name}!')


    def __monitor_device_parameters(self):
        """
        Monitors the parameters of all devices on this interface, according to the valuelimits config file.

        This function retrieves all parameter names from the device's cached values and checks each parameter's value
        against the defined limits using the ParameterMonitor. If a parameter value is out of range, a warning is raised.
        """

        # Checks every parameter for every device on the interface
        for name, device in self.devices.items():
            param_names = device.get_all_param_names()
            for param_name in param_names:
                self.parameter_monitor.check_value(param_name, device.get_data(param_name))


    # ===== ABSTRACT METHODS =====
    @abstractmethod
    def close_connection(self):
        """
        Closes the respective interface
        """


    # ===== MISC METHODS =====
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

    @property
    def status(self):                             # Status Getter
        return self.__status
    
    @status.setter
    def status(self, value: InterfaceStatus):     # Status Setter
        # Return early if there is no change in status
        if self.__status == value:
            return
        
        # Log the change in status
        self._log(f"{self.name} changed from {self.__status.name} to {value.name}.")

        # Change the status
        self.__status = value



# ===== I2CInterface class for DDS' I2C Backend =====
class I2CInterface(Interface):
    """
    Manages the I2C interface for communication with I2C devices.

    This class serves as a base for I2C devices, providing fundamental functionality 
    for I2C communication. Each device communicates through a unique address and 
    responds to specific commands. It is likely that each I2C device will have a 
    dedicated device class that implements device-specific behavior, including custom 
    decoding functions.
    """
    

    def __init__(self, 
                 name: str, 
                 i2c_channel: str, 
                 devices: List[I2CDevice], 
                 logger: DataLogger,
                 parameter_monitor: ParameterMonitor):
        super().__init__(name, devices, InterfaceProtocol.I2C, logger, parameter_monitor)
        self.channel = i2c_channel


    def initialize(self):
        '''
        Starts the I2C bus on the channel given during __init__(),
        and initializes all devices on the interface.
        '''
        # Start the bus
        self.bus = SMBus(self.channel)

        # Initialize all devices on interface.
        super().initialize(self.bus)


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
    CAN database (DBC file) This allows the interface to decode CAN messages and manage communication.
    """

    # 0.1 ms timeout for reading CAN Bus
    TIMEOUT = 0.0001  

    devices: Dict[str, CANDevice]
    
    def __init__(self, 
                 name: str, 
                 can_channel: str, 
                 devices: List[CANDevice], 
                 logger: DataLogger, 
                 parameter_monitor: ParameterMonitor):
        """
        Initializes a CANInterface instance.

        Parameters:
            name (str): The name of the interface.
            can_bus (can.BusABC): The CAN bus interface object.
            database_path (str): Path to the DBC file for CAN database.
            logger (DataLogger): Logger for logging messages.
        """
        
        # Initialize the parent class (Interface)
        super().__init__(name, devices, InterfaceProtocol.CAN, logger, parameter_monitor)

        # Initialize the database
        self.db = cantools.database.Database()

        self.channel = can_channel

        
    def initialize(self):
        """
        Starts the CANBUS on the channel given during __init__(),
        and initializes all devices on the interface.
        """
        
        try:
            # Init the CAN Bus
            self.bus = can.interface.Bus(self.channel, interface='socketcan')

            # Attempt to fetch a CAN message to verify connection
            self.__fetch_can_message()
        except can.CanOperationError:
            # If fetching the message fails, try to initialize the CAN network
            self.__start_can_network(self.channel)

            # Try to restart the bus. If this fails, then that is an interface-level error
            # and will be handled by DDS_IO.
            self.bus = can.interface.Bus(self.channel, interface='socketcan')
        
        # Finish the initialization process
        super().initialize(self.bus)

    
    def update(self):
        """
        Reads data from the CAN bus, logs telemetry, decodes messages, and updates the cached values.
        """
        # The CAN Interface differs from other interfaces, because the interface itself reads the message,
        # not the devices. As a result, we kinda have to some strange things, and we dont use the parent update() method.

        # Get data from the CAN Bus
        # This can raise a CanOperationError, but because this is a interface-level failure,
        # we can let it propogate through to the DDS_IO which will handle it.
        message = self.__fetch_can_message()

        # Check if the message is valid; if not, update cache timeout and return early.
        # This means no messages were received, and we don't need to continue the update process.
        if not message:
            # Update the cache timeout of devices.
            for name, device in self.devices.items():
                device.update(message)
            return

        # Decode the received CAN message to extract relevant data.
        updated_device = None  # Flag to track if device.update() was called
        for name, device in self.devices.items():
            try: 
                # Check if the message corresponds to the device's database
                device.db.get_message_by_frame_id(message.arbitration_id)
            except KeyError as e:
                # This is raised if the message doens't exist in the database.
                # If it this does happen, then the device that is being iterated 
                # doesn't have an database for the message.
                continue

            # If we get to this point, the device has a database for the received message.
            # Call update on the device and mark it as updated
            device.update(message)
            updated_device = device.name  # Save the name of the updated device
            break  # Exit the loop since the device has been updated

        # Check the final condition
        if not updated_device:
            self._log(f"No device found for message ID {message.arbitration_id}.", DataLogger.LogSeverity.WARNING)
            self._log_telemetry('UnknownCanMessage',f'{message.arbitration_id} {message.bitrate_switch} {message.channel} {message.data} {message.dlc}')


    def get_avail_signals(self, messageName : str) -> can.Message:
        '''Returns the avalable CAN signals from the database with the specified message name'''
        return self.db.get_message_by_name(messageName)
    

    def close_connection(self):
        '''Closes the connection to the CAN Bus'''
        self.bus.shutdown()
        

    # ===== CAN Specific Stuff =====
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
            - The `CAN_TIMEOUT` is the maximum time allowed to wait for a message before returning `None`.
        """

        # Read a single frame of CAN data
        # If a CanOperationError is raised, that is an interface-level error.
        # Therefore, it will be handled by the DDS_IO
        msg = self.bus.recv(self.TIMEOUT)

        if msg is None:
            # If there is no message recieved, we need to let the devices know that,
            # so they need to know to clear the cache if it's expired.
            for name, device in self.devices.items():
                super()

        return msg


    def __start_can_network(self, can_channel: str):
        """
        Initializes the CAN network on the OS level.

        Configures the CAN interface by setting its bitrate and transmit queue length at the OS level.

        
        Parameters:
            can_interface (str): The name of the CAN interface (e.g., "can0").
        """

        # Log a warning to indicate the initialization attempt
        self._log(f"CAN Network not found... Attempting to open one on {can_channel}.", DataLogger.LogSeverity.WARNING)

        # Bring up the CAN interface with the specified bitrate
        subprocess.run(
            ["sudo", "ip", "link", "set", can_channel, "up", "type", "can", "bitrate", "250000"],
            check=True,
            timeout=3
        )

        # Set the transmit queue length for the CAN interface
        subprocess.run(
            ["sudo", "ifconfig", can_channel, "txqueuelen", "65536"],
            check=True,
            timeout=3
        )


from Backend.resources.ads_1015 import ADS_1015
from Backend.resources.dtihv500 import DTI_HV_500
from Backend.resources.analog_in import Analog_In, ValueMapper
import smbus2

if __name__ == "__main__":

    logger = DataLogger('InterfaceTest')
    i2c_channel = 2
    can_channel = 'can0'


    # Setting up a test i2c interface
    m3200_pressure_mapper = ValueMapper(
        voltage_range=[0.5, 4.5], 
        output_range=[0, 17])
    i2cinterface = I2CInterface(
        'I2C Interface',
        i2c_channel=i2c_channel,
        devices=[
            ADS_1015('ADC1',logger,[
                Analog_In('hotPressure', 'bar', mapper=m3200_pressure_mapper, tolerance=0.1),         #ADC1(A0)
                Analog_In('hotTemperature', '°C', mapper=m3200_pressure_mapper, tolerance=0.1),       #ADC1(A1)
                Analog_In('coldPressure', 'bar', mapper=m3200_pressure_mapper, tolerance=0.1),        #ADC1(A2)
                Analog_In('coldTemperature', '°C', mapper=m3200_pressure_mapper, tolerance=0.1)       #ADC1(A3)
            ]),
            ADS_1015('ADC2',logger,[
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
        can_channel=can_channel,
        devices=[
            DTI_HV_500("Backend/candatabase/CANDatabaseDTI500v2.dbc", logger)
        ],
        logger=logger

    )

    i2cinterface.initialize()
    i2cinterface.update()

    caninterface.initialize()
    caninterface.update()

    print(i2cinterface.get_data_from_device("ADC1", "hotPressure"))
    
    

