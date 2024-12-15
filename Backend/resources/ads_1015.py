# ADS 1015 class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from .interface import I2CDevice
from .data_logger import DataLogger
from .analog_in import Analog_In
from typing import List
from ads1015 import ADS1015 # This is a helper package. This class cusomizes it functionality.
import time
import smbus2
import threading
import queue



class ADS_1015(I2CDevice):
    """
    # DDS ADS 1015 CLASS
    Analog -> Digital Converter on an I2C interface with caching functionality.
    """

    # This list represensts the four channels that correspond to the four on the physical ADC pins
    inputs : List[Analog_In]

    # ===== CONSTANTS FOR DATA DECODING =====

    CHANNELS = ["in0/gnd", "in1/gnd", "in2/gnd", "in3/gnd"]

    # ===== METHODS =====

    def __init__(self, name: str, logger: DataLogger, i2c_bus: smbus2.SMBus, inputs : List[Analog_In]):

        # Initialize super class (I2CDevice)
        super().__init__(name, logger=logger)

        # Init I2C bus
        self.bus = i2c_bus
        self.last_retrieval_time = time.time()  # Time of the last successful data retrieval

        # Init ADC Device
        self.__init_ads(self.bus)
        
        # Init virtual analog inputs
        self.inputs = inputs

        # Init threading things
        self.data_queue = queue.Queue()  # Queue to hold sensor data
        self.thread_running = True  # Flag to control the thread's execution


    def update(self):
        """
        Retrieve data from the sensor, log it, and cache it.
        """

        # Fetch the sensor data
        voltages = self.__fetch_sensor_data()

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
            self._log_telemetry(key, data, units)

        # Reset the timeout timer
        self.reset_last_cache_update_timer() 


    def __fetch_sensor_data(self) -> List[float]:
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

            except:
                # This will cause the value to be discarded
                input_obj.voltage = -1

                # Try to restart sensor
                try:
                    self.__init_ads()
                except:
                    pass
                

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
        

    def __init_ads(self, bus: smbus2.SMBus):
        # Make ADS object
        self.ads = ADS1015(i2c_dev=bus)

        # Configure ADS
        self.ads.set_mode("continuous")

        # WARNING - this must be higher than the max voltage measured in the system. 
        # It is differential, meaning the ADS can measure ±6.144v
        self.ads.set_programmable_gain(6.144) 
        self.ads.set_sample_rate(3300)

        # Double check chip type (debug)
        self.chip_type = self.ads.detect_chip_type()
        self.log.writeLog(self.name, f"Found: {self.chip_type}")


    def get_latest_data(self):
        """Main program calls this to fetch the latest data from the queue."""
        if not self.data_queue.empty():
            return self.data_queue.get_nowait()  # Non-blocking call
        else:
            return None  # No data available yet

    def _sensor_data_thread(self):
        """Thread function to continuously fetch sensor data."""
        while self.thread_running:
            try:
                voltages = self.__fetch_sensor_data()
                self.data_queue.put(voltages)  # Put data in the queue for the main program
            except Exception as e:
                print(f"Error in fetching sensor data: {e}")
            time.sleep(0.1)  # Adjust the sleep time based on how often you want to read data
    
    def start_sensor_data_collection(self):
        """Start the data collection in a separate thread."""
        sensor_thread = threading.Thread(target=self._sensor_data_thread, daemon=True)
        sensor_thread.start()

    def stop_thread(self):
        self.thread_running = False


# Example usage
if __name__ == '__main__':

    pass