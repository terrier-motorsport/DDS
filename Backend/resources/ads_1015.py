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
    This class takes advantage of multithreading to collect data asyncronously, and transfers it to the main thread.
    This process significantly reduces the amount of time it takes to run the DDS_IO.update() function.
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

        # Init virtual analog inputs
        self.inputs = inputs

        # Init threading things
        self.data_queue = queue.Queue()  # Queue to hold sensor data


    def initialize(self):

        print('init adc')

        # Init ADC Device
        self.__init_ads(self.bus)

        # Start data collection thread
        self.__start_threaded_data_collection()

        # Wait for thread to collect data
        time.sleep(0.5)

        # Complete the initialization
        super().initialize()


    def update(self):
        """
        Retrieve data from the sensor, log it, and cache it.
        """

        # If the device is ERROR, we can attempt to reinit it.
        if self.status is self.Status.ERROR:
            self.__init_ads(self.bus)

        # Fetch the sensor data
        voltages = self.__get_data_from_thread()

        # Check to see if there is null data. If there is, it means that there are no messages to be recieved.
        # Thus, we can end the update poll early.
        if voltages is None or any(value is None for value in voltages):

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


    def __init_ads(self, bus: smbus2.SMBus):
        # Make ADS object
        self.ads = ADS1015(i2c_dev=bus)

        # Configure ADS
        self.ads.set_mode("continuous")

        # WARNING - this must be higher than the max voltage measured in the system. 
        # It is differential, meaning the ADS can measure ±6.144v
        self.ads.set_programmable_gain(6.144) 
        self.ads.set_sample_rate(3300)

        # Those commands run in real time, so we need to sleep to make sure that the physical i2c commands are recieved
        time.sleep(0.5)

        # Double check chip type (debug)
        self.chip_type = self.ads.detect_chip_type()
        self.log.writeLog(self.name, f"Found: {self.chip_type}")


    def __get_data_from_thread(self) -> List[float]:
        """
        Main program calls this to fetch the latest data from the queue.
        """
        if not self.data_queue.empty():
            return self.data_queue.get_nowait()  # Non-blocking call
        else:
            return None  # No data available yet


    # This is the main thread function
    def __data_collection_worker(self):
        """
        # This is the function that the thread runs continously
        Thread function to continuously fetch sensor data.
        """
        print('getting data')
        while self.status is self.Status.ACTIVE:
            try:
                voltages = self.__fetch_sensor_data()
                self.data_queue.put(voltages)  # Put data in the queue for the main program
                self.reset_last_cache_update_timer()
            except Exception as e:
                print(f"Error in fetching sensor data: {e}")
            # time.sleep(0.1)  # Adjust the sleep time based on how often you want to read data
    

    def __fetch_sensor_data(self) -> List[float]:
        """
        Reads voltages from the ADC for each channel, updates the corresponding inputs, 
        and returns a list of voltages.
        This is used to run the data collection thread, and should not be called from the main thread.
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
      

    def __start_threaded_data_collection(self):
        """Start the data collection in a separate thread."""

        # Make thread
        sensor_thread = threading.Thread(target=self.__data_collection_worker, daemon=True)

        # Create the thread & start running
        sensor_thread.start()


# Example usage
if __name__ == '__main__':

    pass