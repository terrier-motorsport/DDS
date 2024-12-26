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



VALID_ADDRESSES = [0x1D, 0x53]

# I2C Registers
TAP_DUR = 0x21              # TAP_DUR is an 8-bit register holding the max time an event must exceed THRESH_TAP to qualify as a tap. Scale: 625 µs/LSB. A value of 0 disables tap functions.
BW_RATE = 0x2C              # A setting of 0 in the LOW_POWER bit selects normal operation, and a setting of 1 selects reduced power operation, which has somewhat higher noise (see the Power Modes section for details).
POWER_CTL = 0x2D            # Bits from [D7 -> D0]: 0 0 Link AUTO_SLEEP Measure Sleep Wakeup
DATA_RATE_SETTINGS = {      # Data rate (Hz) vs. Data Rate Code.
    3200: 0b1111,  # 0xF
    1600: 0b1110,  # 0xE
    800:  0b1101,  # 0xD
    400:  0b1100,  # 0xC
    200:  0b1011,  # 0xB
    100:  0b1010,  # 0xA
    50:   0b1001,  # 0x9
    25:   0b1000,  # 0x8
    12.5: 0b0111,  # 0x7
    6.25: 0b0110,  # 0x6
    3.13: 0b0101,  # 0x5
    1.56: 0b0100,  # 0x4
    0.78: 0b0011,  # 0x3
    0.39: 0b0010,  # 0x2
    0.20: 0b0001,  # 0x1
    0.10: 0b0000,  # 0x0
}
DATA_FORMAT = 0x31          # Bits from [D7 -> D0]: SELF_TEST SPI INT_INVERT 0 FULL_RES Justify (Range)x2
G_RANGE_SETTINGS = {
2: {"bit_depth": 10, "sensitivity": 256, "configuration": 0x00},  # ±2g range
4: {"bit_depth": 11, "sensitivity": 128, "configuration": 0x01},  # ±4g range
8: {"bit_depth": 12, "sensitivity": 64, "configuration": 0x02},   # ±8g range
16: {"bit_depth": 13, "sensitivity": 32, "configuration": 0x03}   # ±16g range
}

DATA_X0 = 0x32
DATA_X1 = 0x33
DATA_Y0 = 0x34
DATA_Y1 = 0x35
DATA_Z0 = 0x36
DATA_Z1 = 0x37

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
    device_addr: int            # i2c Address of the device (7 bits)

    current_g_range: int




    def __init__(self, i2c_bus: smbus2.SMBus, i2c_addr: int):
        """
        Initializes the ADXL343 accelerometer over I2C.

        Parameters:
            i2c_bus (smbus2.SMBus): 
                The I2C bus object used for communication with the device.
            i2c_addr (int): 
                The I2C address of the ADXL343. Must be a valid address in `[0x1D, 0x53]`.

        Description:
            - Validates the provided I2C address to ensure compatibility with the ADXL343.
            - Reads the current g range from the device and stores it in `self.current_g_range`.
            - Sets the device to measurement mode by writing to the POWER_CTL register.

        Raises:
            ValueError: If the provided I2C address is not valid for the ADXL343.

        Example:
            ```
            # Assuming SMBus is set up and 0x1D is a valid I2C address for the ADXL343
            bus = smbus2.SMBus(1)
            adxl343 = InternalADXL343(bus, 0x1D)
            ```
        """
        self.bus = i2c_bus

        # Set address if it is valid.
        if i2c_addr not in VALID_ADDRESSES:
            raise ValueError(f'I2C Address [{i2c_addr}] is not valid for the ADXL343')
        self.device_addr = i2c_addr

        # Read the range of the device
        self.current_g_range = self.read_g_range()
        
        print('Range : %d\n' % (self.current_g_range))
        time.sleep(0.05)

        current_rate_code = self.bus.read_byte_data(self.device_addr, BW_RATE)
        print('Rate code (must be 10 otherwise modify this script to update it) : %d\n' % (current_rate_code & 0x0F))
        time.sleep(0.05)

        # Exit standby mode
        # It is recommended to configure the device in standby mode and then to enable measurement mode.
        self.bus.write_byte_data(self.device_addr, POWER_CTL, 0x08)
        time.sleep(0.05)


    def read_acceleration_in_g(self) -> List[float]:
        """
        Reads the current acceleration values from the sensor and converts them to g.

        The function reads 6 bytes of raw data from the accelerometer, corresponding to 
        the X, Y, and Z axes. Each axis's raw data is converted into acceleration in g 
        based on the current g range (±2g, ±4g, ±8g, or ±16g).

        Returns:
            List[float]: A list of acceleration values in g for the X, Y, and Z axes, 
                        formatted as `[x_accel, y_accel, z_accel]`.
        """
        # 1. Read 6 bytes: [X0, X1, Y0, Y1, Z0, Z1]
        meas_list = self.bus.read_i2c_block_data(self.device_addr, DATA_X0, 6)

        # 2. Convert each axis pair to acceleration in g
        x_accel = self.__convert_axis_bytes_to_g(meas_list[0], meas_list[1])
        y_accel = self.__convert_axis_bytes_to_g(meas_list[2], meas_list[3])
        z_accel = self.__convert_axis_bytes_to_g(meas_list[4], meas_list[5])

        print('Accelerometer: X={:.4f} G, Y={:.4f} G, Z={:.4f} G'.format(x_accel, y_accel, z_accel))
        time.sleep(0.05)

        return [x_accel, y_accel, z_accel]



    def read_g_range(self) -> int:
        """
        Reads the current g range of the accelerometer from the DATA_FORMAT register.

        The g range is determined by the last two bits (D1:D0) of the DATA_FORMAT register:
            - 00: ±2g
            - 01: ±4g
            - 10: ±8g
            - 11: ±16g

        Returns:
            int: The current g range (2, 4, 8, or 16).

        Raises:
            ValueError: If the g-range bits in the register are unrecognized.

        Description:
            - Reads the DATA_FORMAT register to extract the last two bits.
            - Performs a reverse lookup in `G_RANGE_SETTINGS` to match the bits with a valid g range.
            - Returns the corresponding g range.

        Example:
            If the DATA_FORMAT register contains 0b00000010, the last two bits are `10`, 
            indicating a g range of ±8g.
        """
        data_format_register = self.bus.read_byte_data(self.device_addr, DATA_FORMAT)
        range_bits = data_format_register & 0x03  # mask the last two bits

        # Reverse lookup: find which of our G_RANGE_SETTINGS has this 'configuration'
        for possible_range, config_dict in G_RANGE_SETTINGS.items():
            if config_dict["configuration"] == range_bits:
                return possible_range

        raise ValueError(f"Unrecognized g-range bits: 0x{range_bits:X}")
    

    def write_g_range(self, new_range: int):
        """
        Configures the accelerometer's g range by updating the DATA_FORMAT register. 

        Parameters:
            new_range (int): Desired g range. Must be one of [2, 4, 8, 16], representing ±2g, ±4g, ±8g, or ±16g.

        Description:
            - Validates the requested range and updates the last two bits (D1:D0) of the DATA_FORMAT register.
            - Writes the updated value back to the register.
            - Verifies the change by re-reading the register and comparing the result to the requested range.
            - Updates the class's `current_g_range` property if the operation is successful.

        Raises:
            ValueError: If `new_range` is not supported.
            RuntimeError: If the hardware does not reflect the updated range after writing.

        Example:
            If `new_range = 4`, this function sets the DATA_FORMAT register bits D1:D0 to `01` for ±4g.
            After successful verification, `current_g_range` is updated to `4`.
        """

        # 1. Validate the range
        if new_range not in G_RANGE_SETTINGS:
            raise ValueError(f"Invalid range: ±{new_range}g not supported.")

        # 2. Read the current DATA_FORMAT register
        data_format_value = self.bus.read_byte_data(self.device_addr, DATA_FORMAT)

        # 3. Clear bits D1:D0 (the range bits)
        data_format_value &= ~0x03

        # 4. Set bits for the requested range
        data_format_value |= G_RANGE_SETTINGS[new_range]["configuration"]

        # 5. Write the updated DATA_FORMAT register value
        self.bus.write_byte_data(self.device_addr, DATA_FORMAT, data_format_value)
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


    def write_low_power_mode(self, enabled: bool):
        """
        Configures the accelerometer's power mode by setting or clearing the LOW_POWER bit (bit 4) 
        in the BW_RATE register.

        Parameters:
            enabled (bool): True to enable low-power mode (reduces power usage but increases noise), 
                            False to use normal operation (lower noise, higher power).

        Description:
            - Reads the current BW_RATE register value to preserve unrelated bits.
            - Updates bit 4 (LOW_POWER) based on the `enabled` argument.
            - Writes the updated value back to the BW_RATE register.

        Example:
            If the current BW_RATE value is 0b11001010, calling `write_low_power_mode(False)` 
            clears bit 4, resulting in 0b11000010, which is written back to the register.
        """
        # Read the current BW_RATE register value
        current_register_value = self.bus.read_byte_data(self.device_addr, BW_RATE)

        # Convert boolean 'enabled' to the bit we need to set: 0 or 1
        desired_bit = int(enabled)

        # Update bit 4 of the register
        updated_register_value = self._write_bit_to_byte(current_register_value, 4, desired_bit)

        # Write back the modified value to the BW_RATE register
        self.bus.write_byte_data(self.device_addr, BW_RATE, updated_register_value)


    def write_sample_rate(self, rate: float):
        """
        Sets the accelerometer's data output rate by updating the BW_RATE register.

        The data rate determines how often acceleration data is sampled and 
        output by the device. Higher data rates provide more frequent updates 
        but increase power consumption, while lower rates save power but provide 
        less frequent updates.

        Parameters:
            rate (float): The desired data rate in Hz. Must be one of the valid 
                        rates defined in DATA_RATE_SETTINGS.

        Raises:
            ValueError: If the provided rate is not supported (not in DATA_RATE_SETTINGS).

        Description:
            - Reads the current value of the BW_RATE register to ensure other bits 
            (besides the data rate bits) are not modified.
            - Updates only the least significant 4 bits (0–3) of the register 
            to set the desired data rate while preserving other register values.
            - Writes the updated value back to the BW_RATE register.

        Example:
            If DATA_RATE_SETTINGS = {100: 0b1010}, calling `write_sample_rate(100)` will:
            - Read the current BW_RATE value (e.g., 0b11010000).
            - Update the 4 least significant bits to 0b1010.
            - Write back the new value (e.g., 0b11011010) to the BW_RATE register.
        """

        if rate not in DATA_RATE_SETTINGS:
            raise ValueError(f'Rate {rate} is not valid.')
        
        current_register_value = self.bus.read_byte_data(self.device_addr, BW_RATE)

        desired_bits = DATA_RATE_SETTINGS[rate]

        updated_register_value = self._write_bits_to_byte(current_register_value, 0, 4, desired_bits)

        self.bus.write_byte_data(self.device_addr, BW_RATE, updated_register_value)


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
        settings = G_RANGE_SETTINGS[self.current_g_range]
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
        signed_value = self._unsigned_byte_to_signed_byte(combined_value, bit_depth)
        # TODO: REMOVE THIS COMMENT
        # if combined_value >= (1 << (bit_depth - 1)):
        #     combined_value -= (1 << bit_depth)

        # Convert to float in g
        return signed_value / sensitivity
    

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


    # ===== METHODS =====

    def __init__(self, name: str, logger: DataLogger, i2c_bus: smbus2.SMBus, i2c_addr: int):
        """
        Initializes the device, setting up I2C communication, logging, and threading infrastructure.

        Parameters:
            name (str): 
                The name of the device, used for identification and logging purposes.
            logger (DataLogger): 
                An instance of `DataLogger` to log events, errors, and sensor data.
            i2c_bus (smbus2.SMBus): 
                The I2C bus object for communication with the sensor.
            i2c_addr (int): 
                The I2C address of the sensor.

        Notes:
            - This initialization supports multithreaded environments by using a `queue.Queue` 
            for storing and processing sensor data asynchronously.
        """
        # Initialize superclass
        super().__init__(name, logger=logger)

        # Init I2C bus
        self.bus = i2c_bus
        self.addr = i2c_addr
        self.last_retrieval_time = time.time()  # Time of the last successful data retrieval

        # Init threading resources
        self.data_queue = queue.Queue()  # Queue to hold sensor data


    def initialize(self):
        """
        Initializes the sensor and starts data collection.
        """

        # Make ADXL343 object
        self.adxl343 = InternalADXL343(self.bus, self.addr)

        # Configure ADXL343
        self.adxl343.write_g_range(8)
        self.adxl343.write_sample_rate(200)
        self.adxl343.write_low_power_mode(False)

        # Ensure I2C commands are received
        time.sleep(0.5)

        # Start data collection thread
        # NOTE: The status of the device must be set to ACTIVE for the data collector to run.
        self.status = self.Status.ACTIVE
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
        Reads acceleration values and returns a list of accelerations.
        This is used to run the data collection thread, and should not be called from the main thread.
        """
        accelerations = []  # Initialize a list to store the data

        # Read the data
        try:
            accelerations = self.adxl343.read_acceleration_in_g()
        except OSError:
            # Occasionally this happens over i2c communication. I'm not sure why.
            self._log(f'Failed to get acceleration data from {self.name}!', severity=self.log.LogSeverity.ERROR)

        return accelerations
      

    def __start_threaded_data_collection(self):
        """
        Start the data collection in a separate thread.
        """

        # Make thread
        sensor_thread = threading.Thread(target=self.__data_collection_worker, daemon=True)

        # Create the thread & start running
        sensor_thread.start()


# Example usage
if __name__ == '__main__':

    bus = smbus2.SMBus(1)
    log = DataLogger('testing')
    accel = ADXL343('testSensor', log, bus, 0x1D)