# Adafruit ADS 1015 class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)
from ..interface import I2CDevice, InterfaceProtocol, Interface
from ..data_logger import File
import smbus # type: ignore
import time
import adafruit_ads1x15.ads1015 as ADS # type: ignore
from adafruit_ads1x15.analog_in import AnalogIn # type: ignore
from typing import List


class ADS1015(I2CDevice):
    """
    Adafruit Analog -> Digital Converter on an I2C interface with caching functionality.
    """

    # These are the four channels that correspond to the four on the physical ADC pins
    hotPressure : AnalogIn            #ADC(A0)
    hotTemperature : AnalogIn         #ADC(A1)
    coldPressure : AnalogIn           #ADC(A2)
    coldTemperature : AnalogIn        #ADC(A3)

    # ===== CONSTANTS FOR DATA DECODING =====



    # ===== METHODS =====

    def __init__(self, name: str, logFile: File, i2c_bus: smbus.SMBus):

        # Initialize super class (I2CDevice)
        super().__init__(name, logFile=logFile, i2c_address=0x00)   # i2c address isn't used, so I put 0

        # Init I2C bus
        self.bus = i2c_bus
        self.last_retrieval_time = time.time()  # Time of the last successful data retrieval

        # Init ADC Device
        self.ads = ADS.ADS1015(self.bus)

        # Init virtual analog pins
        # These are the four channels that correspond to the four on the physical ADC pins
        self.hotPressure = AnalogIn(self.bus, ADS.P0)        #ADC(A0)
        self.hotTemperature = AnalogIn(self.bus, ADS.P1)     #ADC(A1)
        self.coldPressure = AnalogIn(self.bus, ADS.P2)       #ADC(A2)
        self.coldTemperature = AnalogIn(self.bus, ADS.P3)    #ADC(A3)


        


    def update(self):
        """
        Retrieve data from the sensor, log it, and cache it.
        """

        # Fetch the sensor data
        hotPressure, hotTemp, coldPressure, coldTemp = self._fetch_sensor_data()

        # Check to see if there is null data. If there is, it means that there are no messages to be recieved.
        # Thus, we can end the update poll early.
        if any(value is None for value in [hotPressure, hotTemp, coldPressure, coldTemp]):

            # If no new values are discovered, we check to see if the cache has expired.
            self._update_cache_timeout()
            return

        # Update cache with new data
        self.cached_values["hotPressure"] = hotPressure
        self.cached_values["hotTemperature"] = hotTemp
        self.cached_values["coldPressure"] = coldPressure
        self.cached_values["coldTemperature"] = coldTemp

        # Reset the timeout timer
        self.reset_last_retrival_timer() 

        # Log the data
        self.log_data("hotPressure", hotPressure)
        self.log_data("hotTemperature", hotTemp)
        self.log_data("coldPressure", coldPressure)
        self.log_data("coldTemperature", coldTemp)


    def get_data(self, key: str):
        """
        Retrieve the most recent data associated with the key from the cache.
        """
        if key in self.cached_values:
            return self.cached_values[key]
        else:
            print(f"No cached data found for key: {key}")
            return None


    def close_connection(self):
        """
        Placeholder for closing I2C connection if needed.
        """
        pass


    def _fetch_sensor_data(self) -> List[float]:
        """
        Internal method to encapsulate sensor read logic
        """

        v1 = self.hotPressure.voltage
        v2 = self.hotTemperature.voltage
        v3 = self.coldPressure.voltage
        v4 = self.coldTemperature.voltage
        
        return [v1, v2, v3, v4]
    

    # ===== Super Function Calls =====


    def _update_cache_timeout(self):
        return super()._update_cache_timeout()


    def log_data(self, param_name, value):
        return super().log_data(param_name, value)
    

    def reset_last_retrival_timer():
        return super().reset_last_retrival_timer()
    

