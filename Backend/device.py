# Device Abstract Base Class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from typing import Dict, List, Union
from Backend.data_logger import DataLogger
from abc import ABC, abstractmethod
import time
import threading
from enum import Enum

class Device(ABC):
    '''
    This class provides standard methods which each Device
    object that the DDS uses should override.
    '''

    class DeviceStatus(Enum):
        '''
        This keeps track of the state of the device.
        
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
    name: str
    __status: DeviceStatus

    # Cache variables
    CACHE_TIMEOUT_THRESHOLD = 2      # Cache timeout in seconds
    cached_values: dict              # Dictionary to store cached values
    last_cache_update: float         # Time since last cache update


    def __init__(self, name: str, logger: DataLogger):
        '''
        Initializes a Device object.
        '''

        # Init Class variables
        self.name = name
        self.log = logger
        self.__status = self.DeviceStatus.NOT_INITIALIZED

        # Init cache
        self.cached_values = {}
        self.last_cache_update = time.time()


    # ===== PUBLIC METHODS =====
    @abstractmethod
    def initialize(self, bus):
        '''
        Initializes the device.

        Raises:
            ...
        '''
        # Check if the method is being called on the base class
        if type(self) is Device:
            raise NotImplementedError(
                f"The 'initialize' method for {self.name} must be implemented in a subclass."
            )

        # Start threaded data collection
        self.__start_threaded_data_collection()

        # If called by a subclass, complete initialization
        self._log(f'{self.name} initialized successfully!')
        self.__status = self.DeviceStatus.ACTIVE

    @abstractmethod
    def update(self):
        '''
        Updates the device by reading data from it,
        and storing it into the cached values.

        See example code below:
        '''

        data = self.__get_data_from_thread()

        if data is None:
            # Update the cache with no new data
            self._update_cache(new_data_exists=False)
            return
        self._update_cache(new_data_exists=True)

        self.cached_values["Acceleration"] = data
        self._log_telemetry(f"Acceleration", data, "g")
        


    @abstractmethod
    def _data_collection_worker(self):
        '''
        This function contains the code that will be running on the seperate thread.
        It should be doing all the communication that interfaces with the I/O of the pi.

        See example code below: 
        '''
        
        sensor = None # Imagine this as a sensor

        while self.__status is self.DeviceStatus.ACTIVE:
            try:
                data = sensor.get_data()
                self.data_queue.put(data) # Put data in the queue for the main program
            except Exception as e:
                self._log(f"Error fetching sensor data: {e}", self.log.LogSeverity.ERROR)
        
        # If we ever get here, there was a problem.
        # We should log that the data collection worker stopped working
        self._log('Data collection worker stopped.', self.log.LogSeverity.WARNING)



    def get_all_param_names(self) -> List[str]:
        """
        Returns all parameter names (keys) from the cached values dictionary.

        Returns:
            List[str]: A list of all parameter names in the cached values dictionary.
        """
        return list(self.cached_values.keys())
    

    def get_data(self, data_key: str) -> Union[str, float, int, None]:
        '''
        This method verifies that the data at the specified key exists,
        and if it does, return it.

        If it doesn't exist, log a message and return None.

        Parameters:
            data_key (str): The key of the data being requested.

        Returns:
            Union[str, float, int, None]: The data at the specified key.
        '''

        # Verify data exists, and return it if so
        if not data_key in self.cached_values:
            # This happens if this data has never existed
            return self._log(f"No data found for key: {data_key}", self.log.LogSeverity.WARNING)
        elif self.cached_values[data_key] is None:
            # This happens if the data doesn't currently exist
            return self._log(f"No cached data found for key: {data_key}", self.log.LogSeverity.DEBUG)
        return self.cached_values[data_key]
    

    # ===== PRIVATE METHODS =====
    def _update_cache(self, new_data_exists: bool):
        '''
        Checks if the cache has expired due to lack of new data and clears it if necessary.
        Should be called once every update() frame.

        Parameters:
            new_data_exists (bool): True if the most recent data collected is unique.
        '''
        # Update caching functions
        if new_data_exists:
            self.last_cache_update = time.time()
        else:
            # Return early if the cache is already empty
            if not self.cached_values:
                return

            # Update the current time
            current_time = time.time()

            # Clear the cache if it has expired
            if current_time - self.last_cache_update > self.CACHE_TIMEOUT_THRESHOLD:
                self.__clear_cache()

    
    def __clear_cache(self):
        '''
        Clears the cached values by changing the values to None.
        The keys are left unchanged.
        '''
        # Change all values to None 
        empty_cache = {key: None for key in self.cached_values}
        self.cached_values = empty_cache

        self._log("Cache cleared due to data timeout.", self.log.LogSeverity.WARNING)
    
    
    def __start_threaded_data_collection(self):
        """Start the data collection in a separate thread."""

        # Make thread
        sensor_thread = threading.Thread(target=self._data_collection_worker, daemon=True)

        # Create the thread & start running
        sensor_thread.start()


    def __get_data_from_thread(self) -> List[float]:
        """
        Main program calls this to fetch the latest data from the queue.
        """
        if not self.data_queue.empty():
            return self.data_queue.get_nowait()  # Non-blocking call
        else:
            return None  # No data available yet

    # ===== HELPER METHODS =====
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
    def status(self) -> DeviceStatus:          # Status Getter
        return self.__status
    
    @status.setter
    def status(self, value: DeviceStatus):     # Status Setter

        # Return early if there is no change in status
        if self.__status == value:
            return
        
        # Log the change in status
        self._log(f"{self.name} changed from {self.__status.name} to {value.name}.")

        # Change the status
        self.__status = value


class I2CDevice(Device):
    # TODO: IMPLEMENT
    pass

import can
import cantools.database
class CANDevice(Device):

    db: cantools.database.Database

    def __init__(self, name, dbc_filepath: str, logger: DataLogger):
        self.db = cantools.database.load_file(dbc_filepath)
        super().__init__(name, logger)
    

    def update(self, msg: can.Message):
        '''
        This update function overrides the update function from Device.

        Because CANDevices are a little special, we pass in a can message to the update call.
        '''

        # Return early if no new data.
        if msg is None:
            self._update_cache(new_data_exists=False)
            return

        # Decode message
                # Decoding the message
        decoded_msg: Dict[str, float]
        try:
            # Decode the CAN message using the database
            decoded_msg = self.db.decode_message(msg.arbitration_id, msg.data)
        except KeyError:
            # Log a warning if no database entry matches the arbitration ID
            self._log(f"No database entry found for CAN msg: {msg}", self.log.LogSeverity.ERROR)
            return None
        
        # Logging the message
        for signal_name, value in decoded_msg.items():

            # Get the units for the signal
            cantools_message = self.db.get_message_by_frame_id(msg.arbitration_id)
            cantools_signal = cantools_message.get_signal_by_name(signal_name)
            unit = cantools_signal.unit

            # Write the data to the log file 
            self._log_telemetry(signal_name, value, units=unit)

        # Update or add all decoded values to the cached values dictionary.
        for name, data in decoded_msg.items():
            self.cached_values[name] = data


    def get_all_param_names(self) -> List[str]:
        '''
        Gets all of the signals listed in the device's CAN Database.
        This is overloaded because CAN's parameters are defined by the database, not by the cached values.

        Returns:
            List[str]: The names of every signal in the database.
        '''
        param_names: List[str] = []  # Initialize the list

        # Iterate through all messages in the database
        for message in self.db.messages:
            for signal in message.signals:
                param_names.append(signal.name)  # Add signal names to the list

        return param_names