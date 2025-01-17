# Device Abstract Base Class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from Backend.data_logger import DataLogger
from abc import ABC, abstractmethod
import time
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
    status: DeviceStatus

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
        self.status = self.DeviceStatus.NOT_INITIALIZED

        # Init cache
        self.cached_values = {}
        self.last_cache_update = time.time()



    @abstractmethod
    def initialize(self):
        '''
        Initializes the device.

        Raises:
            ...
        '''
        pass


    def update(self):
        '''
        Updates the device by reading data from it,
        and storing it into the cached values.
        '''
        pass


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

        # Clear the cache if it has expired
        if current_time - self.last_cache_update > self.CACHE_TIMEOUT_THRESHOLD:
            self._clear_cache()
            

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
    
    
    def _clear_cache(self):
        '''
        Clears the cached values by changing the values to None.
        The keys are left unchanged.
        '''
        # Change all values to None 
        empty_cache = {key: None for key in self.cached_values}
        self.cached_values = empty_cache

        self._log("Cache cleared due to data timeout.", self.log.LogSeverity.WARNING)


    # ===== HELPER METHODS =====
    def _log(self, msg: str, severity=DataLogger.LogSeverity.INFO):
        """Shorthand logging method."""
        self.log.writeLog(loggerName=self.name, msg=msg, severity=severity)
    

    # ===== GETTER/SETTER METHODS ====
    @property
    def status(self) -> DeviceStatus:          # Status Getter
        return self.status
    
    @status.setter
    def status(self, value: DeviceStatus):     # Status Setter

        # Return early if there is no change in status
        if self.status == value:
            return
        
        # Log the change in status
        self._log(f"{self.name} changed from {self.status.name} to {value.name}.")

        # Change the status
        self.status = value




# class testThing(Device):
#     pass

# if __name__ == "__main__":
#     thing = testThing()
#     # thing.testMethod()
