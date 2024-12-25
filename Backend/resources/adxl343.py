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

    TODO: Remove debug print statements
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
    current_g_range: int

    DATA_X0 = 0x32
    DATA_X1 = 0x33
    DATA_Y0 = 0x34
    DATA_Y1 = 0x35
    DATA_Z0 = 0x36
    DATA_Z1 = 0x37


    def __init__(self, i2c_bus: smbus2.SMBus, i2c_addr: int):
        """
        Initialize the ADXL343 accelerometer over I2C.

        Parameters:
            i2c_bus (smbus2.SMBus): The I2C bus to communicate on.
            i2c_address (int): The valid I2C address of the ADXL343 device.
        """
        self.bus = i2c_bus

        # Set address if it is valid.
        if i2c_addr not in self.VALID_ADDRESSES:
            raise ValueError(f'I2C Address [{i2c_addr}] is not valid for the ADXL343')
        self.DEVICE_ADDR = i2c_addr

        # Read the range of the device
        self.current_g_range = self.read_g_range()
        
        print('Range code (must be 0 otherwise modify this script to update it) : %d\n' % (self.current_g_range))
        time.sleep(0.05)

        current_rate_code = self.bus.read_byte_data(self.DEVICE_ADDR, self.BW_RATE)
        print('Rate code (must be 10 otherwise modify this script to update it) : %d\n' % (current_rate_code & 0x0F))
        time.sleep(0.05)

        # Exit standby mode
        # It is recommended to configure the device in standby mode and then to enable measurement mode.
        self.bus.write_byte_data(self.DEVICE_ADDR, self.POWER_CTL, 0x08)
        time.sleep(0.05)


    def read_acceleration_in_g(self) -> List[float]:
        '''
        Reads the raw acceleration data (6 bytes) and converts it to `[X, Y, Z]` in g.
        Respects the CURRENT_RANGE (±2g, ±4g, ±8g, or ±16g).
        '''
        # 1. Read 6 bytes: [X0, X1, Y0, Y1, Z0, Z1]
        meas_list = self.bus.read_i2c_block_data(self.DEVICE_ADDR, self.DATA_X0, 6)

        # 2. Convert each axis pair to acceleration in g
        x_accel = self.__convert_axis_bytes_to_g(meas_list[0], meas_list[1])
        y_accel = self.__convert_axis_bytes_to_g(meas_list[2], meas_list[3])
        z_accel = self.__convert_axis_bytes_to_g(meas_list[4], meas_list[5])

        print('Accelerometer: X={:.4f} G, Y={:.4f} G, Z={:.4f} G'.format(x_accel, y_accel, z_accel))
        time.sleep(0.05)

        return [x_accel, y_accel, z_accel]

    
    def __convert_axis_bytes_to_g(self, lsb: int, msb: int) -> float:
        '''
        Given two bytes from the sensor for a single axis:
          - LSB: always uses 8 bits
          - MSB: uses (bit_depth - 8) bits
        Combine them into a signed integer, then convert to g using the sensor’s sensitivity.

        Parameters:
            lsb (int): Lower byte for an axis
            msb (int): Upper byte for the same axis
        Returns:
            float: Acceleration in g

        NOTE: LSB = Least Significant Bit
        NOTE: MSB = Most Significant Bit
        '''
        # Lookup bit_depth & sensitivity for current range
        settings = self.G_RANGE_SETTINGS[self.current_g_range]
        bit_depth = settings["bit_depth"]
        sensitivity = settings["sensitivity"]

        # Number of bits in the MSB that are actually used
        num_msb_bits = bit_depth - 8  # e.g., 10-bit range => 2 bits from MSB

        # Mask out the unused bits in msb
        msb_mask = (1 << num_msb_bits) - 1
        msb_value = (msb & msb_mask) << 8  # place them above the LSB

        # Combine with the LSB
        combined_value = msb_value | lsb  # 0b[MSB_bits][LSB bits]

        # If above the signed threshold, convert using two's complement
        signed_value = self.unsigned_byte_to_signed_byte(combined_value, bit_depth)
        # TODO: REMOVE THIS COMMENT
        # if combined_value >= (1 << (bit_depth - 1)):
        #     combined_value -= (1 << bit_depth)

        # Convert to float in g
        return signed_value / sensitivity


    def read_g_range(self) -> int:
        '''
        Reads the `DATA_FORMAT` register to determine which ±g range is in use.

        The last two bits [D1:D0] define the g-range:
            00 => ±2g
            01 => ±4g
            10 => ±8g
            11 => ±16g
        '''
        data_format_register = self.bus.read_byte_data(self.DEVICE_ADDR, self.DATA_FORMAT)
        range_bits = data_format_register & 0x03  # mask the last two bits

        # Reverse lookup: find which of our G_RANGE_SETTINGS has this 'configuration'
        for possible_range, config_dict in self.G_RANGE_SETTINGS.items():
            if config_dict["configuration"] == range_bits:
                return possible_range

        raise ValueError(f"Unrecognized g-range bits: 0x{range_bits:X}")
    

    def write_g_range(self, new_range: int):
        """
        Sets the g range of the ADXL343 by updating the DATA_FORMAT register,
        then uses get_range() to verify the hardware actually reflects that change.

        Possible ranges: [±2g, ±4g, ±8g, ±16g]
        """

        # 1. Validate the range
        if new_range not in self.G_RANGE_SETTINGS:
            raise ValueError(f"Invalid range: ±{new_range}g not supported.")

        # 2. Read the current DATA_FORMAT register
        data_format_value = self.bus.read_byte_data(self.DEVICE_ADDR, self.DATA_FORMAT)

        # 3. Clear bits D1:D0 (the range bits)
        data_format_value &= ~0x03

        # 4. Set bits for the requested range
        data_format_value |= self.G_RANGE_SETTINGS[new_range]["configuration"]

        # 5. Write the updated DATA_FORMAT register value
        self.bus.write_byte_data(self.DEVICE_ADDR, self.DATA_FORMAT, data_format_value)
        time.sleep(0.01)

        # 6. Update self.CURRENT_RANGE immediately
        self.current_g_range = new_range

        # 7. **Verify** that the hardware really changed to new_range
        verified_range = self.read_g_range()
        if verified_range != new_range:
            raise RuntimeError(
                f"Set range to ±{new_range}g, but device reports ±{verified_range}g "
                "after re-reading DATA_FORMAT."
            )
        else:
            print(f"Successfully set and verified range to ±{new_range}g.")
        

    # def __convert_raw_to_g_with_range(self, lsb_value):
    #     """
    #     Converts raw accelerometer data to acceleration in g based on the g range.

    #     Parameters:
    #         lsb_value (int): The raw digital value from the accelerometer.
    #         g_range (int): The current g range (e.g., 2, 4, 8, 16).

    #     Returns:
    #         float: The acceleration in g.
    #     """
    #     # Check if the g range is valid
    #     if self.CURRENT_RANGE not in self.G_RANGE_SETTINGS:
    #         raise ValueError(f"Invalid g range: {self.CURRENT_RANGE}. Valid ranges: {list(self.G_RANGE_SETTINGS.keys())}")

    #     # Get the settings for the specified range
    #     bit_depth = self.G_RANGE_SETTINGS[self.CURRENT_RANGE]["bit_depth"]
    #     sensitivity = self.G_RANGE_SETTINGS[self.CURRENT_RANGE]["sensitivity"]

    #     # Convert unsigned value to signed value
    #     signed_value = self.unsigned_byte_to_signed_byte(lsb_value, bit_depth)

    #     # Convert to g
    #     g_value = signed_value / sensitivity
    #     return g_value



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
        self.adxl343.write_g_range(8)


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