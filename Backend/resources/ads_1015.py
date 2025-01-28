# ADS 1015 class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from Backend.data_logger import DataLogger
from Backend.resources.analog_in import Analog_In
from Backend.device import I2CDevice
from typing import Dict, List
from ads1015 import ADS1015 # This is a helper package. This class cusomizes it functionality.
from smbus2 import SMBus
import time




class ADS_1015(I2CDevice):
    """
    # DDS ADS 1015 CLASS
    Analog -> Digital Converter on an I2C interface with caching functionality.
    This class takes advantage of multithreading to collect data asynchronously, 
    and transfers it to the main thread using a thread-safe cache.
    """

	# This list represents the four channels that correspond to the four physical ADC pins
    inputs: List[Analog_In]

	# ===== CONSTANTS FOR DATA DECODING =====
    CHANNELS = ["in0/gnd", "in1/gnd", "in2/gnd", "in3/gnd"]


    def __init__(self, name: str, logger: DataLogger, inputs : List[Analog_In], i2c_addr: int=0x48):
        """
        Initializes the ADS_1015 device.
        Args:
            name (str): Name of the device.
            logger (DataLogger): Logger instance.
            inputs (List[Analog_In]): List of Analog_In objects corresponding to ADC channels.
            i2c_addr (int): I2C address of the ADS1015 device (default: 0x48).
        """
        super().__init__(name, logger)
        self.inputs = inputs
        self.addr = i2c_addr


    def initialize(self, bus: SMBus):
        """
        Initializes the ADS1015 sensor by configuring its I2C communication.
        """
        # Save bus
        self.bus = bus

        # Create ADS object
        self.ads = ADS1015(i2c_addr=self.addr, i2c_dev=self.bus)

        # Configure ADS
        self.ads.set_mode("continuous")
        self.ads.set_programmable_gain(6.144)  # ±6.144V range
        self.ads.set_sample_rate(250)

        # Allow time for hardware to configure
        time.sleep(0.5)

        # Double-check chip type (debug)
        self.chip_type = self.ads.detect_chip_type()
        self._log(f"Found: {self.chip_type}")

        # Complete the initialization
        self.status = self.DeviceStatus.ACTIVE
        self.start_worker()


    def update(self):
        """
        Retrieves data from the cache and ensures it is up-to-date.
        """
        # Check if the cache has timed out
        self._check_cache_timeout()


    def _data_collection_worker(self):
        """
        Continuously collects data from the ADS1015 sensor in a separate thread.
        Handles slower I/O-dependent communication with the device.
        """
        while self.status == self.DeviceStatus.ACTIVE:
            print('yay')

            # Fetch voltages from the sensor
            voltages = self.__fetch_sensor_data()

            # Process the voltages
            outputs: Dict[str, float] = {}
            for input_obj, voltage in zip(self.inputs, voltages):
                # Get the output value
                output = input_obj.voltage_to_output(voltage)

                # Log it
                self._log_telemetry(input_obj.name, output, input_obj.units)

                # Add it to list of outputs
                outputs[input_obj.name] = output

            print('updating cache')
            # Update the cache in a thread-safe manner
            self._update_cache(outputs)

        # Log error if the data collection worker stops unexpectedly
        self._log('Data collection worker stopped.', self.log.LogSeverity.ERROR)
        self.status = self.DeviceStatus.ERROR
    

    def __fetch_sensor_data(self) -> List[float]:
        """
        Reads voltages from the ADC for each channel and returns a list of voltages.
        Returns:
            List[float]: A list of voltages read from each channel.
        """
        voltages = []

        for channel, input_obj in zip(self.CHANNELS, self.inputs):
            try:
                # Read voltage from the current channel
                voltage = self.ads.get_voltage(channel=channel)
            except OSError as e:
                # Handle occasional I2C errors
                self._log(f"Failed to get ADC data from {channel}: {e}", self.log.LogSeverity.ERROR)
                voltage = None

            # Validate and clamp the voltage
            voltage = self.__validate_voltage(input_obj, voltage)

            # Store the validated voltage
            voltages.append(voltage)

        return voltages


    def __validate_voltage(self, analog_in: Analog_In, voltage: float) -> float:
        """
        Validates and clamps the voltage within the Analog_In's valid range.
        Args:
            analog_in (Analog_In): The Analog_In object associated with the voltage.
            voltage (float): The voltage to validate.
        Returns:
            float: The clamped voltage.
        """
        # Clamp the voltage to the valid range
        return self.__clamp(voltage, analog_in.min_voltage, analog_in.max_voltage)



    def __clamp(self, value, min_value, max_value) -> float:
        """
        Clamps a value between a minimum and maximum.
        Args:
            value (float): The value to clamp.
            min_value (float): The minimum allowable value.
            max_value (float): The maximum allowable value.
        Returns:
            float: The clamped value.
        """
        return max(min_value, min(value, max_value))

# Example usage
from Backend.resources.analog_in import ValueMapper
if __name__ == '__main__':
    testValueMapper = ValueMapper(
        voltage_range=[0.5, 4.5], 
        output_range=[0, 17]
    )

    ads = ADS_1015('ADS', DataLogger('ADSTest'), inputs=[
        Analog_In('Testinput1', 'Units', testValueMapper),
        Analog_In('Testinput2', 'Units', testValueMapper),
        Analog_In('Testinput3', 'Units', testValueMapper),
        Analog_In('Testinput4', 'Units', testValueMapper)
    ])
    
    # Initialize the ADS_1015 with the I2C bus
    ads.initialize(SMBus(2))

    print("Starting ADS1015 data collection... Press Ctrl+C to exit.")

    prev_time = time.time()  # Initialize the previous time for delta time tracking

    try:
        while True:
            current_time = time.time()  # Capture the current time
            delta_time = current_time - prev_time  # Calculate delta time
            prev_time = current_time  # Update previous time

            # Update the ADS object (fetch data from the device and update cache)
            ads.update()

            # Print the data for all parameters (voltages for each input)
            param_names = ads.get_all_param_names()
            print(f"Delta Time: {delta_time:.6f} seconds")
            for param in param_names:
                print(f"{param}: {ads.get_data(param)}")

            # Wait before the next update (adjust as needed)
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nExiting ADS1015 test...")