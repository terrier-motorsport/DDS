# ADS 1015 class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from .interface import I2CDevice
from .data_logger import DataLogger
from .analog_in import Analog_In

import smbus2
from typing import List
import time
from ads1015 import ADS1015 # This is a helper package. This class cusomizes it functionality.



class ADS_1015(I2CDevice):
    """
    Adafruit Analog -> Digital Converter on an I2C interface with caching functionality.
    """

    # This list represensts the four channels that correspond to the four on the physical ADC pins
    inputs : List[Analog_In]

    # ===== CONSTANTS FOR DATA DECODING =====

    CHANNELS = ["in0/gnd", "in1/gnd", "in2/gnd", "in3/gnd"]

    # ===== METHODS =====

    def __init__(self, name: str, logger: DataLogger, i2c_bus: smbus2.SMBus, inputs : List[Analog_In]):

        # Initialize super class (I2CDevice)
        super().__init__(name, logger=logger, i2c_address=0x00)   # i2c address isn't used, so put 0

        # Init I2C bus
        self.bus = i2c_bus
        self.last_retrieval_time = time.time()  # Time of the last successful data retrieval

        # Init ADC Device
        self.__init_ads()
        
        # Init virtual analog inputs
        self.inputs = inputs


    def update(self):
        """
        Retrieve data from the sensor, log it, and cache it.
        """

        # Fetch the sensor data
        voltages = self._fetch_sensor_data()

        # Check to see if there is null data. If there is, it means that there are no messages to be recieved.
        # Thus, we can end the update poll early.
        if any(value is None for value in voltages):

            # If no new values are discovered, we check to see if the cache has expired.
            self._update_cache_timeout()
            return

        # For each voltage collected & input object
        for input_obj, voltage in zip(self.inputs, voltages):

            # Set the voltage of the analog_in object to the one measured.
            input_obj.voltage = voltage

            # Extract data from object
            key = input_obj.name
            data = input_obj.get_output()
            units = input_obj.units

            # Update cache with new data
            self.cached_values[key] = data

            # Log the data
            self.log_data(key, data, units)

        # Reset the timeout timer
        self.reset_last_retrival_timer() 
            

    def get_data(self, key: str):
        """
        Retrieve the most recent data associated with the key from the cache.
        To be called by some higher power, not by the class itself.
        """

        if key in self.cached_values:
            return self.cached_values[key]
        else:
            self.log.writeLog(self.name, f"No cached data found for key: {key}", self.log.LogSeverity.WARNING)
            return None


    def _fetch_sensor_data(self) -> List[float]:
        """
        Reads voltages from the ADC for each channel, updates the corresponding inputs, 
        and returns a list of voltages.
        """
        voltages = []  # Initialize a list to store the voltages

        # Iterate through each channel and corresponding input
        for channel, input_obj in zip(self.CHANNELS, self.inputs):

            # Read the voltage for the current channel with compensation
            try:
                input_obj.voltage = self.ads.get_voltage(
                    channel=channel
                )
            except OSError:
                # Occasionally this happens over i2c communication. I'm not sure why.
                self.log.writeLog(self.name,f'Failed to get ADC data from {channel}!', severity=self.log.LogSeverity.ERROR)

                # This will cause the value to be discarded
                input_obj.voltage = -1

            # Validate the voltage of the input
            input_obj = self.__validate_voltage(input_obj)

            # Store the voltage in the voltages list
            voltages.append(input_obj.voltage)

        return voltages
    

    def __validate_voltage(self, analog_in: Analog_In):
        '''
        Validates the voltage is within the analog_in's input range. 
        Returns the output with clean data.
        '''

        if not analog_in.voltage_in_tolerange_range():
            # This means the voltage is outside of the tolerable range.
            self.log.writeLog(
                              self.name,
                              msg =f"{analog_in.name} out of tolerable range! Voltage: {analog_in.voltage}v, Value: {analog_in.get_output()}{analog_in.units}",
                              severity=self.log.LogSeverity.WARNING)
            
            # Return an empty value
            return analog_in

        else:
            # The value is in the output range, so we clamp & return it.
            # This prevents things like negative pressures when the loop is unpresurized
            clamped_voltage = self.clamp(analog_in.voltage, analog_in.min_voltage, analog_in.max_voltage)
            analog_in.voltage = clamped_voltage
            return analog_in
        

    

    def __init_ads(self):
        # Make ADS object
        self.ads = ADS1015()

        # Double check chip type (debug)
        self.chip_type = self.ads.detect_chip_type()
        self.log.writeLog(self.name, "Found: {}".format(self.chip_type))

        # Configure ADS
        self.ads.set_mode("single")
        self.ads.set_programmable_gain(6.144) # WARNING - this must be higher than the max voltage measured in the system.
        self.ads.set_sample_rate(1600)

        # Get reference voltage
        self.reference = self.ads.get_reference_voltage()
        self.log.writeLog(self.name, f"Reference: {self.reference}")
    




    # ===== Super Function Calls =====


    def _update_cache_timeout(self):
        return super()._update_cache_timeout()


    def log_data(self, param_name, value, units):
        return super().log_data(param_name, value, units=units)
    

    def reset_last_retrival_timer(self):
        return super().reset_last_retrival_timer()
    

# Example usage
DEBUG_ENABLED = False

if DEBUG_ENABLED:
    
    pass