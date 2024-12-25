# ADXL343 Accelerometer class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)
    # Additional Code by Mohamed Amine Mzoughi (https://github.com/embeddedmz/ADXL343/blob/master/adxl343.py)

from Backend.interface import I2CDevice
from Backend.data_logger import DataLogger
from Backend.resources.analog_in import Analog_In
from Backend.resources.internal_device import InternalDevice
from typing import List
import time
import smbus2
import threading
import queue

class InternalADXL343(InternalDevice):
    '''
    This class handles the low level i2c communication, and seperates it from the higher level
    functionality of the ADXL343 class. 

    Datasheet: https://www.analog.com/media/en/technical-documentation/data-sheets/adxl343.pdf

    Some Code by Mohamed Amine Mzoughi (https://github.com/embeddedmz/ADXL343/blob/master/adxl343.py)
    Modified by Jackson Justus (jackjust@bu.edu)
    '''

    # ===== CONSTANTS FOR DATA DECODING =====

    # Device Address
    DEVICE_ADDR: int            # i2c Address of the device (7 bits)
    VALID_ADDRESSES = [0x1D, 0x53]

    # I2C Registers
    TAP_DUR = 0x21              # TAP_DUR is an 8-bit register holding the max time an event must exceed THRESH_TAP to qualify as a tap. Scale: 625 µs/LSB. A value of 0 disables tap functions.
    BW_RATE = 0x2C              # A setting of 0 in the LOW_POWER bit selects normal operation, and a setting of 1 selects reduced power operation, which has somewhat higher noise (see the Power Modes section for details).
    POWER_CTL = 0x2D            # Bits from [D7 -> D0]: 0 0 Link AUTO_SLEEP Measure Sleep Wakeup
    DATA_FORMAT = 0x31          # Bits from [D7 -> D0]: SELF_TEST SPI INT_INVERT 0 FULL_RES Justify (Range)x2
    G_RANGE_SETTINGS = {
    2: {"bit_depth": 10, "sensitivity": 256, "configuration": 0x00},  # ±2g range
    4: {"bit_depth": 11, "sensitivity": 128, "configuration": 0x01},  # ±4g range
    8: {"bit_depth": 12, "sensitivity": 64, "configuration": 0x02},   # ±8g range
    16: {"bit_depth": 13, "sensitivity": 32, "configuration": 0x03}   # ±16g range
}
    CURRENT_RANGE: int

    DATA_X0 = 0x32
    DATA_X1 = 0x33
    DATA_Y0 = 0x34
    DATA_Y1 = 0x35
    DATA_Z0 = 0x36
    DATA_Z1 = 0x37


    def __init__(self, i2c_bus: smbus2.SMBus, i2c_addr: int):
        self.bus = i2c_bus

        # Set address if it is valid.
        if i2c_addr not in self.VALID_ADDRESSES:
            raise ValueError(f'I2C Address [{i2c_addr}] is not valid for the ADXL343')
        self.DEVICE_ADDR = i2c_addr

        # Read the range of the device
        range_code = self.get_range()
        
        print('Range code (must be 0 otherwise modify this script to update it) : %d\n' % (range_code))
        time.sleep(0.05)

        rate = self.bus.read_byte_data(self.DEVICE_ADDR, self.BW_RATE)
        print('Rate code (must be 10 otherwise modify this script to update it) : %d\n' % (rate & 0x0F))
        time.sleep(0.05)

        # Exit standby mode
        # It is recommended to configure the device in standby mode and then to enable measurement mode.
        self.bus.write_byte_data(self.DEVICE_ADDR, self.POWER_CTL, 0x08)
        time.sleep(0.05)
        pass

    def get_acceleration(self) -> List[float]:
        '''
        Reads the acceleration data from the sensor and returns it as a list of floats.
        Takes into account the g_range of the sensor.

        Returns:
            `[x_accel, y_accel, z_accel]`
        '''

        # Read 6 bytes of data from the accelerometer
        meas_list = self.bus.read_i2c_block_data(self.DEVICE_ADDR, self.DATA_X0, 6)

        # Convert the 6 bytes into 16-bit raw values
        x_raw = (meas_list[1] << 8) + meas_list[0]
        y_raw = (meas_list[3] << 8) + meas_list[2]
        z_raw = (meas_list[5] << 8) + meas_list[4]

        # Handle signed conversion based on bit depth
        # The raw values are unsigned, so they need to be converted to signed values
        # We use the convert_raw_to_g_with_range function to handle the conversion
        x_accel = self.__convert_raw_to_g_with_range(x_raw)
        y_accel = self.__convert_raw_to_g_with_range(y_raw)
        z_accel = self.__convert_raw_to_g_with_range(z_raw)

        # Print the acceleration in g for each axis
        print('Accelerometer : X=%.4f G, Y=%.4f G, Z=%.4f G\n' % (x_accel, y_accel, z_accel))

        # Sleep to avoid flooding the sensor with requests
        time.sleep(0.05)

        return [x_accel, y_accel, z_accel]

    

    def __convert_raw_to_g_with_range(self, lsb_value):
        """
        Converts raw accelerometer data to acceleration in g based on the g range.

        Parameters:
            lsb_value (int): The raw digital value from the accelerometer.
            g_range (int): The current g range (e.g., 2, 4, 8, 16).

        Returns:
            float: The acceleration in g.
        """
        # Check if the g range is valid
        if self.CURRENT_RANGE not in self.G_RANGE_SETTINGS:
            raise ValueError(f"Invalid g range: {self.CURRENT_RANGE}. Valid ranges: {list(self.G_RANGE_SETTINGS.keys())}")

        # Get the settings for the specified range
        bit_depth = self.G_RANGE_SETTINGS[self.CURRENT_RANGE]["bit_depth"]
        sensitivity = self.G_RANGE_SETTINGS[self.CURRENT_RANGE]["sensitivity"]

        # Convert unsigned value to signed value
        signed_value = self.unsigned_byte_to_signed_byte(lsb_value, bit_depth)

        # Convert to g
        g_value = signed_value / sensitivity
        return g_value



    def get_range(self) -> int:
        '''
        Returns the `g` range of the accelerometer from the DATA_FORMAT register.

        These bits determine the `g` range. See table below.

        D1 D0 g Range
        0  0  ±2 g
        0  1  ±4 g
        1  0  ±8 g
        1  1  ±16 g
        '''
        data_format_register = self.bus.read_byte_data(self.DEVICE_ADDR, self.DATA_FORMAT)
        range_bits = data_format_register & 0x03 # Hex mask for last two bits
        for g_range, bits in self.G_RANGE_SETTINGS['configuration'].items():
            if bits == range_bits:
                return g_range
        raise ValueError('Invalid range bits in DATA_FORMAT register')
    

    def set_g_range(self, range: int):
        '''
        Sets the `g` range of the accelerometer.

        Possible ranges: [±2g, ±4g, ±8g, ±16g]
        '''

        # Validate the range given
        if range not in self.G_RANGE_SETTINGS['configuration']:
            raise ValueError(f'{range} is not a valid range for {self.__class__}')
        
        # Set the range
        self.CURRENT_RANGE = range
        
        # Read the current DATA_FORMAT register value
        data_format_register = self.bus.read_byte_data(self.DEVICE_ADDR, self.DATA_FORMAT)
        
        # Clear the D1 and D0 bits (Range bits)
        data_format_register &= ~0x03
        
        # Set the new range
        data_format_register |= self.G_RANGE_SETTINGS['configuration'][self.CURRENT_RANGE]
        
        # Write the new DATA_FORMAT register value
        self.bus.write_byte_data(self.DEVICE_ADDR, self.DATA_FORMAT, data_format_register)
        


class ADXL343(I2CDevice):
    """
    # DDS ADXL 343 CLASS
    Accelerometer on an I2C interface with caching functionality.
    This class takes advantage of multithreading to collect data asyncronously, and transfers it to the main thread.
    This process significantly reduces the amount of time it takes to run the DDS_IO.update() function.
    """

    # This list represensts the four channels that correspond to the four on the physical ADC pins
    inputs : List[Analog_In]



    # ===== METHODS =====

    def __init__(self, name: str, logger: DataLogger, i2c_bus: smbus2.SMBus, i2c_addr: int):

        # Initialize super class (I2CDevice)
        super().__init__(name, logger=logger)

        # Init I2C bus
        self.bus = i2c_bus
        self.addr = i2c_addr
        self.last_retrieval_time = time.time()  # Time of the last successful data retrieval

        # Init threading things
        self.data_queue = queue.Queue()  # Queue to hold sensor data


    def initialize(self):

        # Make ADXL343 object
        self.adxl343 = InternalADXL343(self.bus, self.addr)

        # Configure ADXL343
        self.adxl343.set_g_range(8)


        # self.ads.set_sample_rate(3300)

        # Those commands run in real time, so we need to sleep to make sure that the physical i2c commands are recieved
        time.sleep(0.5)

        # Double check chip type (debug)
        # self.chip_type = self.ads.detect_chip_type()
        # self._log(f"Found: {self.chip_type}")

        # Start data collection thread
        # NOTE: The status of the device must be set to ACTIVE for the data collector to run.
        self.__start_threaded_data_collection()

        # Wait for thread to collect data
        time.sleep(0.5)

        # Complete the initialization
        super().initialize()


    def update(self):
        """
        Retrieve data from the sensor, log it, and cache it.
        """

        # Fetch the sensor data
        accelerations = self.__get_data_from_thread()

        # Check to see if there is null data. If there is, it means that there are no messages to be recieved.
        # Thus, we can end the update poll early.
        if accelerations is None or any(value is None for value in accelerations):

            # If no new values are discovered, we check to see if the cache has expired.
            self._update_cache_timeout()
            return

        # Parse / reformat data

        # Expand data from object
        key = self.name
        accelerations = accelerations
        units = 'g'

        # Update cache with new data
        self.cached_values[key] = accelerations

        # Log the data
        self._log_telemetry(key, accelerations, units)

        # Reset the timeout timer
        self._reset_last_cache_update_timer() 


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

        while self.status is self.Status.ACTIVE:
            try:
                accelerations = self.__fetch_sensor_data()
                self.data_queue.put(accelerations)  # Put data in the queue for the main program
                self._reset_last_cache_update_timer()
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
        accelerations = []  # Initialize a list to store the voltages

        # Iterate through each channel and corresponding input
        for channel in self.CHANNELS:

            # Read the voltage for the current channel with compensation
            try:
                # TODO: Get data & add it to accelerations list
                acceleration = 1
                pass
            except OSError:
                # Occasionally this happens over i2c communication. I'm not sure why.
                self._log(f'Failed to get ADC data from {channel}!', severity=self.log.LogSeverity.ERROR)

            # Store the voltage in the voltages list
            accelerations.append(acceleration)

        return accelerations
      

    def __start_threaded_data_collection(self):
        """Start the data collection in a separate thread."""

        # Make thread
        sensor_thread = threading.Thread(target=self.__data_collection_worker, daemon=True)

        # Create the thread & start running
        sensor_thread.start()


# Example usage
if __name__ == '__main__':
    pass