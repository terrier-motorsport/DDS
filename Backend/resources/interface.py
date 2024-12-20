# Interface object for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from enum import Enum
from .data_logger import DataLogger
from typing import Union, Callable

import can
import cantools
import cantools.database
import subprocess
import time


"""
The purpose of these classes is to serve as an abstract outline 
of a single interface/device to be inherited by a more specific class if necessary.
EX: the I2C Pressure/Tempature Sensor for the cooling loop.
Objects from classes in this file are created in the DDS_IO class.
"""


# Enums for types of protocols
class InterfaceProtocol(Enum):
    CAN = 1     # DONE
    I2C = 3     # DONE


# ===== Parent class for all interfaces =====
class Interface:

    '''
    This class contains the base functionality for all interfaces. 
    In order for this to function properly, the update() function must be called as often as possible.
    The values from the interface are constantly updated into the current_values dictionary
    and can be retrieved by using the .get_data() function
    '''

    class Status(Enum):
        '''
        This keeps track of the state of the interface.
        ACTIVE: Data is being polled constantly.
        DISABLED: The interface is ignored.
        ERROR: There was an error polling data and the interface will attempt to be re-initialized.
        '''
        ACTIVE = 1,
        DISABLED = 2,
        ERROR = 3,
        NOT_INITIALIZED = 4


    # Class variables
    CACHE_TIMEOUT_THRESHOLD = 2      # Cache timeout in seconds
    cached_values: dict              # Dictionary to store cached values
    last_cache_update: float         # Time since last cache update


    def __init__(self, name : str, sensorProtocol : InterfaceProtocol, logger : DataLogger):
        '''
        This initalizer should contain code which is not expected to raise an error.
        Code which initializes the physical aspect of interfaces should be put in initalize()
        '''

        # Class variables
        self.sensorProtocol = sensorProtocol
        self.name = name
        self.log = logger
        self.status = self.Status.NOT_INITIALIZED

        # Init cache
        self.cached_values = {}

        # Init cache timeout
        self.last_cache_update = time.time()

        # Log device creation
        self._log(f'Created {self.sensorProtocol.name} device {self.name}.')


    def initialize(self):
        '''
        This method encapsulates the part of the initalization which talks to the physical devices.
        If there is an error with the physical devices, this may raise an error.
        '''
        
        # Set status to active
        self.status = self.Status.ACTIVE

        # Log device initilization
        self._log(f'Initalized {self.sensorProtocol.name} device {self.name} Successfully.')


    def update(self):
        """
        Method intended to be overridden by child classes.

        The purpose of this method is to receive data from sensors 
        and update the `cached_values` dictionary with the latest readings.

        Logs an error if the method is not properly overridden.
        """
        self._log(
            self.name,
            "The 'update' method has not been properly overridden in the child class.",
            self.log.LogSeverity.ERROR
        )
        pass



    # ===== GETTER METHODS =====
    def get_name(self) -> str:
        '''Gets the name of the interface'''
        return self.name


    def get_protocol(self) -> InterfaceProtocol:
        '''Gets the protocol of the interface'''
        return self.sensorProtocol


    def get_data(self, key: str) -> Union[str, float, int]:
        """
        Retrieve the most recent data associated with the key given from the cache.
        """

        if key in self.cached_values:
            return self.cached_values[key]
        else:
            self._log(f"No cached data found for key: {key}", self.log.LogSeverity.WARNING)
            return None


    # ===== CACHING METHODS =====
    def _update_cache_timeout(self):
        """
        To be called when no new data is found.
        This checks to see if the cache has expired. If it has, the cache is cleared.
        """

        # Checks if the cache is already empty
        if not self.cached_values:
            return

        # Update the current time
        current_time = time.time()

        # See if the cache has expired
        if current_time - self.last_cache_update > self.CACHE_TIMEOUT_THRESHOLD:

            # Clear the cache
            self.cached_values.clear()
            self._log("Cache cleared due to data timeout.", self.log.LogSeverity.WARNING)


    def _reset_last_cache_update_timer(self):
        '''
        Resets the timer which keeps track of the last time the cache was updated.
        Should be called every time the cache is updated.
        '''
        self.last_cache_update = time.time()


    # ===== OTHER METHODS =====
    def _log_telemetry(self, param_name: str, value, units: str):
        '''Takes in a file, parameter name & a value'''
        self.log.writeTelemetry(
            device_name=self.name, 
            param_name=param_name,
            value=value,
            units=units)


    def _log(self, msg: str, severity=DataLogger.LogSeverity.INFO):
        """Centralized logging helper."""
        self.log.writeLog(
            logger_name=self.name,
            msg=msg,
            severity=severity)

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
    I2C Device which inherits the Interface class
    Each device has its own address & commands that it responds too.
    It is most likely that each i2c device will have it's own child class with custom decoding function.
    """


    def __init__(self, name : str, logger : DataLogger):
        
        # Init super (Input class)
        super().__init__(name, InterfaceProtocol.I2C, logger=logger)


    def close_connection(self):
        """
        Closing I2C connection if needed.
        """

        # Close the i2c connection.
        self.bus.close()





# ===== CANInterface class for DDS' CAN Backend =====
class CANInterface(Interface):

    '''
    CAN Interface which inherits the Interface class.
    Each device on the interface can have its own CAN database, which can be added using add_database().
    EX: The MC & AMS are on one CAN Interface. 
    \nFor UCP, There is only one CAN Interface running on the DDS.
    '''

    # 0.1 ms timeout for reading CAN Bus
    CAN_TIMEOUT = 0.0001  
    

    def __init__(self, name : str, can_bus: can.BusABC, database_path : str, logger : DataLogger):
        '''
        Initializer for a CANInterface
        '''

        # Init super (Interface class)
        super().__init__(name, InterfaceProtocol.CAN, logger=logger)

        # Init database path
        self.database_path = database_path

        # Init database & log messages
        self.db = cantools.database.Database()
        self.add_database(self.database_path)

        # Setup CAN Bus 
        # Can_interface is the interface of the device that the code is running on which can is connected to.
        # interface refers to the type of CAN Bus that is running on that physical interface.
        self.can_bus = can_bus

    
    def initialize(self):
        """
        Initializes the interface by communicating with physical devices.
        This method encapsulates the part of the initialization process that involves
        communication with physical devices. If there is an error with the physical
        devices, this method may raise an error.
        """
        
        # Finish initializaiton 
        super().initialize()

    
    def update(self):

        '''
        This function will first get data from the interface assigned to it.
        It will then log it and stuff
        Then it will parse the messages, and cache all values
        '''

        # Get data from the CAN Bus
        message = self.__fetch_can_message()

        # Check to see if there is null data. If there is, it means that there are no messages to be recieved.
        # Thus, we can end the update poll early.
        if not message:
            self._update_cache_timeout()
            return

        # Decode the recieved data
        data = self.__decode_can_msg(message)

        # See if data decoding was successful. If not, return
        if not data:
            return

        # Update the last retrevial time for the timeout threshold
        self._reset_last_cache_update_timer()

        # Log the data that was read
        for signal_name,value in data.items():
            
            # Get the units for the signal
            cantools_message = self.db.get_message_by_frame_id(message.arbitration_id)
            cantools_signal = cantools_message.get_signal_by_name(signal_name)
            unit = cantools_signal.unit

            # Write the data to the log file 
            self.db.get_message_by_name()
            super()._log_telemetry(signal_name, value, units=unit)

        # Updates / Adds all the read values to the current_values dict
        for signal_name, value in data.items():
            self.cached_values[signal_name] = value
        

    def add_database(self, filename: str):
        """Loads a DBC file into the CAN database."""
        try:
            self.db.add_dbc_file(filename)
            self._log(severity=self.log.LogSeverity.INFO, msg=f"Loaded DBC file: {filename}")
        except Exception as e:
            self._log(severity=self.log.LogSeverity.ERROR, msg=f"Failed to load DBC file {filename}: {e}")
            raise



    def get_avail_signals(self, messageName : str):
        '''Returns the avalable CAN signals from the database with the specified message name'''
        return self.db.get_message_by_name(messageName)
    

    def close_connection(self):
        '''Closes the connection to the CAN Bus'''
        self.can_bus.shutdown()
        

    def __fetch_can_message(self) -> can.Message:
        """
        Fetches a single CAN message from the CAN Bus.

        This method reads a single CAN message frame from the CAN Bus. If the message is not
        received within the specified timeout, the function will return `None`. 

        Returns:
            can.Message: A CAN message object containing the received message data, or `None` 
                        if no message was received within the specified timeout.

        Raises:
            can.exceptions.CanOperationError: If the CAN Bus interface encounters an error 
                                            during the operation (e.g., network not open).
        
        Notes:
            - This function relies on the `self.can_bus.recv` method to receive the CAN message.
            - The `CAN_TIMEOUT` is the maximum time allowed to wait for a message before returning `None`.
            - If the CAN Bus interface is not operational, the function attempts to start it again.

        """

        # Read a single frame of CAN data
        return self.can_bus.recv(self.CAN_TIMEOUT)


        
    
    def __decode_can_msg(self, msg: can.Message) -> dict:
        """
        Decodes the given CAN message using a predefined message database.

        This method attempts to parse the CAN message by matching its arbitration ID 
        and data against a database of predefined message formats. If no match is found, 
        a warning is logged, and `None` is returned.

        Args:
            msg (can.Message): The CAN message to decode. It must contain an arbitration 
                            ID and data, which are used for decoding.

        Returns:
            dict: A dictionary with the decoded message data, or `None` if decoding fails.
        """

        try:
            # Decode the CAN message using the database
            return self.db.decode_message(msg.arbitration_id, msg.data)
        except KeyError:
            # Log a warning if no database entry matches the arbitration ID
            self._log(f"No database entry found for {msg}", self.log.LogSeverity.WARNING)
            return None




    @staticmethod
    def init_can_network(log_func: Callable[[str, DataLogger.LogSeverity], None], can_interface: str) -> bool:
        """
        Brings up and configures a CAN network interface at the OS level.

        This method executes system commands to initialize the specified CAN interface, 
        set its bitrate, and configure its transmit queue length. Logs messages for 
        success, warnings, and errors. Returns a boolean indicating the success of the operation.

        Args:
            log_func (Callable[[str, str], None]): A logging function that accepts a message 
                string and a severity level string as arguments.
            can_interface (str): The name of the CAN interface to initialize (e.g., "can0").

        Returns:
            bool: True if the CAN interface was successfully initialized, False otherwise.
        """
        # Log a warning to indicate the initialization attempt
        log_func(f"CAN Bus not found... Attempting to open one on {can_interface}.", DataLogger.LogSeverity.WARNING)

        try:
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

            # Log success and return True
            log_func(f"{can_interface} successfully started.", DataLogger.LogSeverity.INFO)
            return True

        except subprocess.TimeoutExpired:
            # Handle timeout errors and log a critical message
            log_func(f"Timeout: Couldn't start {can_interface}. Try rerunning the program with sudo.", DataLogger.LogSeverity.CRITICAL)
            raise TimeoutError

        except subprocess.CalledProcessError as e:
            # Handle shell command errors and log details about the failure
            log_func(f"Error: Couldn't start {can_interface}. The command '{e.cmd}' failed", DataLogger.LogSeverity.INFO)
