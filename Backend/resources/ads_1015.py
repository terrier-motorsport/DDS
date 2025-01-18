# ADS 1015 class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from Backend.data_logger import DataLogger
from Backend.resources.analog_in import Analog_In
from Backend.device import Device
from typing import List
from ads1015 import ADS1015 # This is a helper package. This class cusomizes it functionality.
from smbus2 import SMBus
import time
import threading
import queue



class ADS_1015(Device):
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

    def __init__(self, name: str, logger: DataLogger, inputs : List[Analog_In]):

        # Initialize super class (Device)
        super().__init__(name, logger)

        # Init class variables
        self.inputs = inputs
        self.data_queue = queue.Queue()  # Queue to hold sensor data


    def initialize(self, bus: SMBus):

        # Save bus
        self.bus = bus

        # Make ADS object
        self.ads = ADS1015(i2c_dev=self.bus)

        # Configure ADS
        self.ads.set_mode("continuous")

        # WARNING - this must be higher than the max voltage measured in the system. 
        # It is differential, meaning the ADS can measure ±6.144v
        self.ads.set_programmable_gain(6.144) 
        self.ads.set_sample_rate(250)

        # Those commands run in real time, so we need to sleep to make sure that the physical i2c commands are recieved
        time.sleep(0.5)

        # Double check chip type (debug)
        self.chip_type = self.ads.detect_chip_type()
        self._log(f"Found: {self.chip_type}")

        # Start data collection thread
        # NOTE: The status of the device must be set to ACTIVE for the data collector to run.
        self.__status = self.DeviceStatus.ACTIVE
        self.__start_threaded_data_collection()

        # Wait for thread to collect data
        time.sleep(0.5)

        # Complete the initialization
        super().initialize(bus)


    def update(self):
        """
        Retrieve data from the sensor, log it, and cache it.
        """

        # Fetch the sensor data
        voltages = self.__get_data_from_thread()

        # Check to see if there is null data. If there is, it means that there are no messages to be recieved.
        # Thus, we can end the update poll early.
        if voltages is None or any(value is None for value in voltages):
            # Update the cache with no new data
            self._update_cache(new_data_exists=False)
            return
        self._update_cache(new_data_exists=True)

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

        while self.__status is self.DeviceStatus.ACTIVE:
            try:
                voltages = self.__fetch_sensor_data()
                self.data_queue.put(voltages)  # Put data in the queue for the main program
                self.__reset_last_cache_update_timer()
            except Exception as e:
                self._log(f"Error fetching sensor data: {e}", self.log.LogSeverity.ERROR)

        # If we ever get here, there was a problem.
        # We should log that the data collection worker stopped working
        self._log('Data collection worker stopped.', self.log.LogSeverity.WARNING)
    

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
                self._log(f'Failed to get ADC data from {channel}!', severity=self.log.LogSeverity.ERROR)

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
            self._log(f"{analog_in.name} out of tolerable range! Voltage: {analog_in.voltage}v, Value: {analog_in.get_output()}{analog_in.units}", severity=self.log.LogSeverity.WARNING)
            
            # Return an empty value
            return analog_in

        else:
            # The value is in the output range, so we clamp & return it.
            # This prevents things like negative pressures when the loop is unpresurized
            clamped_voltage = self.__clamp(analog_in.voltage, analog_in.min_voltage, analog_in.max_voltage)
            analog_in.voltage = clamped_voltage
            return analog_in
      

    def __start_threaded_data_collection(self):
        """Start the data collection in a separate thread."""

        # Make thread
        sensor_thread = threading.Thread(target=self.__data_collection_worker, daemon=True)

        # Create the thread & start running
        sensor_thread.start()


    def __clamp(self, value, min_value, max_value):
        """Clamps a value between a minimum and maximum."""
        return max(min_value, min(value, max_value))


# Example usage
if __name__ == '__main__':
    pass