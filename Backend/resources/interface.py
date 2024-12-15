# Input object for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from enum import Enum
from .data_logger import DataLogger
from typing import Union

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

# ===== CONSTANTS =====

CAN_INTERFACE = 'can0'
UART_TX = 2
#...

# Enums for types of protocols
class InterfaceProtocol(Enum):
    CAN = 1     # DONE
    SPI = 2     # Not Needed?
    I2C = 3     # DONE
    UART = 4    # Not Needed?



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
        ERROR = 3

    CACHE_TIMEOUT_THRESHOLD = 2      # Cache timeout in seconds
    cached_values: dict              # Dictionary to store cached values
    last_cache_update: float         # Time since last cache update


    def __init__(self, name : str, sensorProtocol : InterfaceProtocol, logger : DataLogger):
        '''
        Parent class for all interfaces.
        In case you didn't know, this is the initializer.
        '''

        # Class variables
        self.sensorProtocol = sensorProtocol
        self.name = name
        self.log = logger
        self.status = self.Status.ACTIVE

        # Init cache
        self.cached_values = {}

        # Init cache timeout
        self.last_cache_update = time.time()



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
            self.log.writeLog(self.name, f"No cached data found for key: {key}", self.log.LogSeverity.WARNING)
            return 'ERR'



    # ===== CACHING METHODS =====
    def _update_cache_timeout(self):
        """
        Clear the cache if the data has not been updated within the timeout threshold.
        """
        current_time = time.time()
        if current_time - self.last_cache_update > self.CACHE_TIMEOUT_THRESHOLD:
            self.cached_values = {}
            self.log.writeLog(__class__.__name__, "Cache cleared due to data timeout.", self.log.LogSeverity.WARNING)


    def reset_last_cache_update_timer(self):
        self.last_cache_update = time.time()


    def _log_telemetry(self, param_name: str, value, units: str):
        '''Takes in a file, parameter name & a value'''
        self.log.writeTelemetry(
            device_name=self.name, 
            param_name=param_name,
            value=value,
            units=units)
        


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

    
    def update(self):
        '''Should be overwritten by child class'''
        self.log.writeLog(__class__.__name__, "update not overriden properly in child class.", self.log.LogSeverity.ERROR)
        pass


    def close_connection(self):
        """
        Closing I2C connection if needed.
        """

        # Close the i2c connection.
        self.bus.close()


    def _log_telemetry(self, param_name, value, units):
        return super()._log_telemetry(param_name, value, units)




# ===== CANInterface class for DDS' CAN Backend =====
class CANInterface(Interface):

    '''
    CAN Interface which inherits the Input class.
    Each device on the interface can have its own CAN database, which can be added using add_database().
    EX: The MC & AMS are on one CAN Interface. 
    \nFor UCP, There is only one CAN Interface running on the DDS.
    '''

    # Dictionary which contains the most recent values for all the CAN data
    cached_values : dict = {}

    # If no CAN data is retrieved within x seconds, the class removes cached data.
    cached_data_timeout_threshold = 2

    
    def __init__(self, name : str, can_interface : str, database_path : str, logger : DataLogger):
        '''
        Initializer for a CANInterface
        '''

        # Init super (Input class)
        super().__init__(name, InterfaceProtocol.CAN, logger=logger)

        # Init database path
        self.database_path = database_path

        # Init database & log messages
        self.db = cantools.database.Database()
        self.add_database(self.database_path)

        # Setup CAN Bus 
        # Can_interface is the interface of the device that the code is running on which can is connected to.
        # interface refers to the type of CAN Bus that is running on that physical interface.
        self.can_bus = can.interface.Bus(can_interface, interface='socketcan')

    
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
        if message == None:

            # If no new values are discovered, we check to see if the cache has expired.
            self.__update_cache_timeout()
            return

        # Decode the recieved data
        data = self.__decode_can_msg(message)
        
        # Update the last retrevial time for the timeout threshold
        self.last_retrieval_time = time.time()  # Update retrieval time

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
        

    def add_database(self, filename : str):
        '''Adds additional database info to the CAN interface from a dbc file'''

        # Add dbc file to database
        self.db.add_dbc_file(filename)
        self.log.writeLog(__class__.__name__, f"Loaded Messages from CAN Database: {filename}")


    def get_avail_signals(self, messageName : str):
        '''Returns the avalable CAN signals from the database with the specified message name'''
        return self.db.get_message_by_name(messageName)
    

    def close_connection(self):
        '''Closes the connection to the CAN Bus'''
        self.can_bus.shutdown()
        

    def __fetch_can_message(self) -> can.Message:
        
        '''
        Gets data from the CAN Bus and tries to parse it.
        Returns a dictionary of parameters and values.
        '''

        # Read a single frame of CAN data
        # If this throws an error, its most likely because the CAN Bus Network on the OS isn't open.
        # It will try to open the network and run the command again.
        try:
            # If a message isn't found within .01ms, the function returns None.
            msg = self.can_bus.recv(timeout=.0001)
        except can.exceptions.CanOperationError:
            self.__start_can_bus()
            msg = self.can_bus.recv(timeout=.0001)

        # Return the message
        return msg
        
    
    def __decode_can_msg(self, msg: can.Message) -> dict:
        # Try to parse the data & return it
        try:
            return self.db.decode_message(msg.arbitration_id, msg.data)
        except KeyError:
            self.log.writeLog(__class__.__name__, 
                              f"No database entry found for {msg}",
                              self.log.LogSeverity.WARNING)
            return {'':''}
    

    def __start_can_bus(self):

        '''
        This is the command to start the can0 network
        In a terminal, all these command would be run with spaces inbetween them
        '''
        self.log.writeLog(__class__.__name__, "CAN Bus not found... Attempting to open one.", self.log.LogSeverity.WARNING)
        

        try:
            # Set CAN interface up with a timeout of 3 seconds
            subprocess.run(
                ["sudo", "ip", "link", "set", "can0", "up", "type", "can", "bitrate", "1000000"],
                check=True,
                timeout=3
            )
            # Set txqueuelen with a timeout of 3 seconds
            subprocess.run(
                ["sudo", "ifconfig", "can0", "txqueuelen", "65536"],
                check=True,
                timeout=3
            )
            self.log.writeLog(__class__.__name__, "can0 Successfully started.", self.log.LogSeverity.INFO)

            # Catch common errors
        except subprocess.TimeoutExpired as e:
            # Command couldn't be run
            self.log.writeLog(__class__.__name__, "Timeout: Couldn't start can0. Try rerunning the program with sudo.", self.log.LogSeverity.CRITICAL)
            raise TimeoutError
        except subprocess.CalledProcessError as e:
            # Tbh idk
            self.log.writeLog(__class__.__name__, f"Error: Couldn't start can0. The command '{e.cmd}' failed with exit code {e.returncode}.", self.log.LogSeverity.CRITICAL)
        except Exception as e:
            # I hope this one doesn't happen
            self.log.writeLog(__class__.__name__, f"Couldn't start can0. Unexpected Error: {e}", self.log.LogSeverity.CRITICAL)


        # subprocess.run(["sudo", "ip", "link", "set", "can0", "up", "type", "can", "bitrate", "1000000"])
        # subprocess.run(["sudo", "ifconfig", "can0", "txqueuelen", "65536"])