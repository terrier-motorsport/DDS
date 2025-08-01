# Device Abstract Base Class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from typing import Dict, List, Union
from Backend.data_logger import DataLogger
from Backend.value_monitor import ParameterMonitor, ParameterWarning
from abc import ABC, abstractmethod
import time
import threading
from enum import Enum
import threading
import queue

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


    def __init__(self, name: str, logger: DataLogger):
        '''
        Initializes a Device object.
        '''
        self.name = name
        self.log = logger
        self.cached_values = {}
        self.lock = threading.Lock()
        self.__status = self.DeviceStatus.NOT_INITIALIZED
        self.last_cache_update = time.time()
        self.thread = None  # Worker thread for data collection
        self.CACHE_TIMEOUT_THRESHOLD = 2  # Cache timeout in seconds


    # ===== PUBLIC METHODS =====
    @abstractmethod
    def initialize(self, bus):
        '''
        Initialize the device. Must be implemented by subclasses.

        At the bare minimum, must set status to active.
        '''
        pass

        # # Check if the method is being called on the base class
        # if type(self) is Device:
        #     raise NotImplementedError(
        #         f"The 'initialize' method for {self.name} must be implemented in a subclass."
        #     )

        # # Start threaded data collection
        # self.status = self.DeviceStatus.ACTIVE
        # self.__start_threaded_data_collection()

        # # If called by a subclass, complete initialization
        # self._log(f'{self.name} initialized successfully!')
        # self.__status = self.DeviceStatus.ACTIVE

    @abstractmethod
    def update(self):
        '''
        Updates cached values with new data.
        '''
        pass

        # data = self._get_data_from_thread()

        # if data is None:
        #     # Update the cache with no new data
        #     self._update_cache(new_data_exists=False)
        #     return
        # self._update_cache(new_data_exists=True)

        # self.cached_values["Acceleration"] = data
        # self._log_telemetry(f"Acceleration", data, "g")
        


    @abstractmethod
    def _data_collection_worker(self):
        '''
        This function contains the code that will be running on the seperate thread.
        It should be doing all the communication that interfaces with the I/O of the pi.

        See example code below: 
        '''
        pass
        
        # sensor = None # Imagine this as a sensor

        # while self.status is self.DeviceStatus.ACTIVE:
        #     try:
        #         data = sensor.get_data()
        #         self.data_queue.put(data) # Put data in the queue for the main program
        #     except Exception as e:
        #         self._log(f"Error fetching sensor data: {e}", self.log.LogSeverity.ERROR)
        
        # # If we ever get here, there was a problem.
        # # We should log that the data collection worker stopped working
        # self._log('Data collection worker stopped.', self.log.LogSeverity.ERROR)
        # self.status = self.DeviceStatus.ERROR


    def start_worker(self):
        '''
        Start the worker thread for data collection.
        '''
        self.thread = threading.Thread(target=self._data_collection_worker, daemon=True)
        self.thread.start()


    def stop_worker(self):
        '''
        Stop the worker thread gracefully.
        '''
        self.status = self.DeviceStatus.DISABLED
        if self.thread and self.thread.is_alive():
            self.thread.join()


    def get_all_param_names(self) -> List[str]:
        """
        Returns all parameter names (keys) from the cached values dictionary.

        Returns:
            List[str]: A list of all parameter names in the cached values dictionary.
        """
        return list(self.cached_values.keys())
    

    def get_data(self, param_name: str):
        '''
        Thread-safe access to cached data.
        '''
        with self.lock:
            return self.cached_values.get(param_name, None)


    def _update_cache(self, new_data: dict):
        '''
        Thread-safe update of the cache.
        Writes telemetry based on new data
        '''
        # self._log_telemetry(new_data)
        with self.lock:
            self.cached_values.update(new_data)
            self.last_cache_update = time.time()


    # def _log_telemetry(self, data: dict):
    #     for key,value in data.items():
    #         self.log.writeTelemetry(self.name,key,value,"")

    def _check_cache_timeout(self):
        '''
        Clears the cache if the timeout threshold is exceeded.
        '''
        with self.lock:
            if self.cached_values and time.time() - self.last_cache_update > self.CACHE_TIMEOUT_THRESHOLD:
                self.cached_values = {key: None for key in self.cached_values}
                self._log("Cache cleared due to timeout.", self.log.LogSeverity.WARNING)


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
    

    def initialize(self, bus):
        self.bus = bus
        self.status = self.DeviceStatus.ACTIVE
    

    def update(self, msg: can.Message):
        '''
        This update function overrides the update function from Device.

        Because CANDevices are a little special, we pass in a can message to the update call.
        '''

        # Return early if no new data.
        if msg is None:
            self._check_cache_timeout()
            return

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
        self._update_cache(decoded_msg)

    
    def _data_collection_worker(self):
        '''
        CANDevice doesn't use threaded data collection.
        '''
        return

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