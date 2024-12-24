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

class InternalADXL323(InternalDevice):
    '''
    This class handles the low level i2c communication, and seperates it from the higher level
    functionality of the ADXL343 class. 

    Datasheet: https://www.analog.com/media/en/technical-documentation/data-sheets/adxl343.pdf

    Some Code by Mohamed Amine Mzoughi (https://github.com/embeddedmz/ADXL343/blob/master/adxl343.py)
    Modified by Jackson Justus (jackjust@bu.edu)
    '''

    # ===== CONSTANTS FOR DATA DECODING =====

    DEVICE_ADDR_7_BITS = 0x1D
    BW_RATE = 0x2C
    POWER_CTL = 0x2D
    DATA_FORMAT = 0x31
    DATA_X0 = 0x32
    DATA_X1 = 0x33
    DATA_Y0 = 0x34
    DATA_Y1 = 0x35
    DATA_Z0 = 0x36
    DATA_Z1 = 0x37


    def __init__(self, i2c_bus: smbus2.SMBus, i2c_addr: int):
        self.bus = i2c_bus
        self.addr = i2c_addr

        self.range = self.bus.read_byte_data(self.DEVICE_ADDR_7_BITS, self.DATA_FORMAT)
        print('Range code (must be 0 otherwise modify this script to update it) : %d\n' % (self.range & 0x03))
        time.sleep(0.05)

        self.rate = self.bus.read_byte_data(self.DEVICE_ADDR_7_BITS, self.BW_RATE)
        print('Rate code (must be 10 otherwise modify this script to update it) : %d\n' % (self.rate & 0x0F))
        time.sleep(0.05)

        # Exit standby mode
        # It is recommended to configure the device in standby mode and then to enable measurement mode.
        self.bus.write_byte_data(self.DEVICE_ADDR_7_BITS, self.POWER_CTL, 0x08)
        time.sleep(0.05)
        pass

    def get_acceleration(self) -> List[float]:

        measList = self.bus.read_i2c_block_data(self.DEVICE_ADDR_7_BITS, self.DATA_X0, 6)
        #print(measList)
        
        xAccel = (self.unsigned_byte_to_signed_byte(measList[1]) << 8) + measList[0]
        yAccel = (self.unsigned_byte_to_signed_byte(measList[3]) << 8) + measList[2]
        zAccel = (self.unsigned_byte_to_signed_byte(measList[5]) << 8) + measList[4]
        

        # 4 mG/bit, we need 250 bit to have 1 G
        print('Accelerometer : X=%.4f G, Y=%.4f G, Z=%.4f G\n' % (xAccel / 250, yAccel / 250, zAccel / 250))
        
        time.sleep(0.05)


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
        self.adxl343 = InternalADXL323(self.bus, self.addr)

        # Configure ADXL343

        # WARNING - this must be higher than the max voltage measured in the system. 
        # It is differential, meaning the ADS can measure ±6.144v
        # self.ads.set_programmable_gain(6.144) 
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