# M3200 Pressure Transducer class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)
    # NOTE: This code is for i2c communication with the M3200. 
        # With the 2024-2025 season, we have no i2c M3200.
        # (This page was a mistake, but probably still works)

from Backend.interface import I2CInterface, InterfaceProtocol, Interface
from Backend.data_logger import DataLogger
import smbus # type: ignore
import time



class M3200PressureSensorI2C(I2CInterface):
    """
    M3200 Pressure Sensor on an I2C interface with caching functionality.
    """

    # ===== CONSTANTS FOR DATA DECODING =====

    # Status
    status_map = {
        0: "Normal Operation. Good Data Packet",
        1: "Reserved",
        2: "Stale Data. Data has been fetched since last measurement cycle.",
        3: "Fault Detected"
    }

    # Pressure
    # These values corralate to the 'count' that the sensor sends on the i2c bus
    Pres_raw_max = 15000   # This value (15000) is defined in the manual and shouldn't change
    Pres_raw_min = 1000    # This value (1000) is defined in the manual and shouldn't change

    # These values corralate to the output pressure that is given by the part number of the sensor
    # They are given in PSI
    Pres_max = 100         # This value (100) is defined in the manual and shouldn't change
    Pres_min = 0           # This value (0) is defined in the manual and shouldn't change
    # Pres_offset = 1000


    # Temperature
    Temp_range = 200       # Temperature range from -50°C to 150°C
    Temp_multiplier = 2048 # Arbitrary number specified in manual (2048)
    Temp_offset = 50       # Arbitrary number specified in manual (50)



    def __init__(self, name: str, logger: DataLogger, i2c_address: int, i2c_bus: smbus.SMBus):

        # Initialize super class (I2CDevice)
        super().__init__(name, logger=logger, i2c_address=i2c_address)

        # Init I2C bus
        self.bus = i2c_bus
        self.last_retrieval_time = time.time()  # Time of the last successful data retrieval


    def update(self):
        """
        Retrieve data from the sensor, log it, and cache it.
        """
        
        # Fetch the sensor data
        status, pressure, temperature = self.__fetch_sensor_data()

        # Check to see if there is null data. If there is, it means that there are no messages to be recieved.
        # Thus, we can end the update poll early.
        if any(value is None for value in (status, pressure, temperature)):

            # If no new values are discovered, we check to see if the cache has expired.
            self._update_cache_timeout()
            return
        

        # Update cache with new data
        self.cached_values["status"] = status
        self.cached_values["pressure"] = pressure
        self.cached_values["temperature"] = temperature
        self._reset_last_cache_update_timer() # Reset the timeout timer

        # Log the data
        self._log_telemetry("status", status)
        self._log_telemetry("pressure", pressure)
        self._log_telemetry("temperature", temperature)


    def get_data(self, key: str):
        """
        Retrieve the most recent data associated with the key from the cache.
        """
        if key in self.cached_values:
            return self.cached_values[key]
        else:
            self.log.writeLog(__class__.__name__, f"No cached data found for key: {key}", self.log.LogSeverity.WARNING)
            return None


    def close_connection(self):
        """
        Placeholder for closing I2C connection if needed.
        """
        pass


    def __fetch_sensor_data(self) -> tuple[str, float, float]:
        """
        Internal method to encapsulate sensor read logic
        """
        data = self.bus.read_i2c_block_data(self.i2c_address, 0x00, 4)

        # Extract status
        status_raw = (data[0] & 0xC0) >> 6
        status = self._decode_status(status_raw)

        # Extract bridge data (pressure)
        bridge_raw = ((data[0] & 0x3F) << 8) | data[1]
        pressure = self._decode_pressure(bridge_raw)

        # Extract temperature data
        temp_raw = (data[2] << 3) | ((data[3] & 0xE0) >> 5)
        temperature = self._decode_temp(temp_raw) 
        
        return status, pressure, temperature
    

    def _decode_status(self, status_int: int) -> str:
        """
        Decode the status bits (2 MSB) from the sensor data.).

        Returns:
        str: A human-readable status message.
        """

        # Return the corresponding status or 'Unknown Status' if not found
        return self.status_map.get(status_int, "Unknown Status")


    def _decode_temp(self, temp_raw: int) -> float:
        """
        Decode the output (decimal) to temperature in Celcius.
        """
        
        # Calculate the output decimal counts
        degrees_celcius = ((temp_raw * self.Temp_range) / self.Temp_multiplier) - self.Temp_offset
        
        return int(degrees_celcius)
    
    def _decode_pressure(self, pres_raw: int) -> float:
        """
        Decode the output (decimal) to pressure (PSI)
        """
        
        sensor_max = self.Pres_raw_max  # This is the highest value that the sensor can output
        sensor_min = self.Pres_raw_min  # This is the lowest value that the sensor can output

        # This float is a value from 0 to 1 representing the pressure sensor's value
        percentage = Interface.map_to_percentage(pres_raw, sensor_min, sensor_max)

        max = self.Pres_max     # This is measured in PSI
        min = self.Pres_min     # This is measured in PSI

        # This gives us the actual pressure in PSI
        pressure = Interface.percentage_to_map(percentage, min, max)
        
        return int(pressure)


    # ===== Super Function Calls =====


    def _update_cache_timeout(self):
        return super()._update_cache_timeout()


    def _log_telemetry(self, param_name, value):
        return super()._log_telemetry(param_name, value)
    

    def _reset_last_cache_update_timer():
        return super()._reset_last_cache_update_timer()
    

