# Code orignially by ryker1990 on github.
    # https://github.com/ControlEverythingCommunity/MPU-6000/tree/master
# Adapted by Jackson Justus (jackjust@bu.edu) for Terrier Motorsport's DDS.

# Distributed with a free-will license.
# Use it any way you want, profit or free, provided it fits in the licenses of its associated works.
# MPU-6000
# This code is designed to work with the MPU-6000_I2CS I2C Mini Module available from ControlEverything.com.
# https://www.controleverything.com/content/Accelorometer?sku=MPU-6000_I2CS#tabs-0-product_tabset-2


from Backend.device import I2CDevice
from Backend.resources.internal_device import InternalDevice
from smbus2 import SMBus
from gpiozero.pins.lgpio import LGPIOFactory
from gpiozero import Device, LED
import time

class Internal_MPU_6050(InternalDevice):
    """
    Internal class for low-level communication with the MPU6050 sensor.

    This class abstracts the raw communication with the MPU6050 using I2C.
    It provides methods for configuring registers, reading raw data, and converting data to signed values.
    """

    # MPU6050 I2C Address
    MPU6050_I2C_ADDRESS = 0x69

    # Register addresses
    REG_PWR_MGMT_1 = 0x6B
    REG_ACCEL_CONFIG = 0x1C
    REG_GYRO_CONFIG = 0x1B
    REG_ACCEL_XOUT_H = 0x3B
    REG_GYRO_XOUT_H = 0x43

    # Sensitivity scale factors
    ACCEL_SCALE_MODES = {0: 16384.0, 1: 8192.0, 2: 4096.0, 3: 2048.0}  # ±2g, ±4g, ±8g, ±16g
    GYRO_SCALE_MODES = {0: 131.0, 1: 65.5, 2: 32.8, 3: 16.4}  # ±250dps, ±500dps, ±1000dps, ±2000dps

    def __init__(self, bus: SMBus):
        """
        Initializes the MPU6050 internal device.

        Args:
            bus (SMBus): The I2C bus instance to communicate with the MPU6050.
        """
        super().__init__()
        self.bus = bus
        self.accel_scale_factor = self.ACCEL_SCALE_MODES[3]  # Default to ±16g
        self.gyro_scale_factor = self.GYRO_SCALE_MODES[3]  # Default to ±2000dps

    def initialize(self):
        """
        Initializes the MPU6050 sensor by configuring power management and default settings.
        """
        # Wake up the MPU6050
        self.bus.write_byte_data(self.MPU6050_I2C_ADDRESS, self.REG_PWR_MGMT_1, 0x01)  # Set PLL with X-axis gyroscope

        # Configure accelerometer: Set full-scale range to ±16g
        self._write_accel_config(3)

        # Configure gyroscope: Set full-scale range to ±2000dps
        self._write_gyro_config(3)

    def _write_accel_config(self, scale_mode: int):
        """
        Configures the accelerometer full-scale range.

        Args:
            scale_mode (int): Accelerometer scale mode (0=±2g, 1=±4g, 2=±8g, 3=±16g).
        """
        if scale_mode not in self.ACCEL_SCALE_MODES:
            raise ValueError("Invalid accelerometer scale mode.")
        self.accel_scale_factor = self.ACCEL_SCALE_MODES[scale_mode]
        self.bus.write_byte_data(self.MPU6050_I2C_ADDRESS, self.REG_ACCEL_CONFIG, scale_mode << 3)

    def _write_gyro_config(self, scale_mode: int):
        """
        Configures the gyroscope full-scale range.

        Args:
            scale_mode (int): Gyroscope scale mode (0=±250dps, 1=±500dps, 2=±1000dps, 3=±2000dps).
        """
        if scale_mode not in self.GYRO_SCALE_MODES:
            raise ValueError("Invalid gyroscope scale mode.")
        self.gyro_scale_factor = self.GYRO_SCALE_MODES[scale_mode]
        self.bus.write_byte_data(self.MPU6050_I2C_ADDRESS, self.REG_GYRO_CONFIG, scale_mode << 3)

    def read_acceleration(self):
        """
        Reads raw accelerometer data and converts it to g.

        Returns:
            dict: A dictionary containing acceleration data in g for x, y, and z axes.
        """
        raw_data = self._read_raw_data(self.REG_ACCEL_XOUT_H, 6)
        return {
            "x": raw_data[0] / self.accel_scale_factor,
            "y": raw_data[1] / self.accel_scale_factor,
            "z": raw_data[2] / self.accel_scale_factor,
        }

    def read_gyroscope(self):
        """
        Reads raw gyroscope data and converts it to dps.

        Returns:
            dict: A dictionary containing gyroscope data in dps for x, y, and z axes.
        """
        raw_data = self._read_raw_data(self.REG_GYRO_XOUT_H, 6)
        return {
            "x": raw_data[0] / self.gyro_scale_factor,
            "y": raw_data[1] / self.gyro_scale_factor,
            "z": raw_data[2] / self.gyro_scale_factor,
        }

    def _read_raw_data(self, start_register: int, length: int):
        """
        Reads raw data from the MPU6050 starting at the specified register.

        Args:
            start_register (int): The starting register address.
            length (int): The number of bytes to read.

        Returns:
            list: A list of signed integers representing the raw data.
        """
        raw_data = self.bus.read_i2c_block_data(self.MPU6050_I2C_ADDRESS, start_register, length)
        return [
            self._unsigned_byte_to_signed_byte((raw_data[i] << 8) | raw_data[i + 1], 16)
            for i in range(0, length, 2)
        ]

    def set_power_mode(self, mode: int):
        """
        Sets the power mode of the MPU6050.

        Args:
            mode (int): The power mode to set.
                0 = Sleep mode
                1 = Normal mode
        """
        if mode == 0:
            self.bus.write_byte_data(self.MPU6050_I2C_ADDRESS, self.REG_PWR_MGMT_1, 0x40)  # Sleep mode
        elif mode == 1:
            self.bus.write_byte_data(self.MPU6050_I2C_ADDRESS, self.REG_PWR_MGMT_1, 0x01)  # Normal mode
        else:
            raise ValueError("Invalid power mode. Use 0 (sleep) or 1 (normal).")


class MPU_6050_x3(I2CDevice):

    '''
    This handles the communication for all three MPU 6050 accel/gyro sensors.
    '''

    def __init__(self, name, logger):
        super().__init__(name, logger)
        self.dev_pins = [17, 27, 22]  # GPIO pins for device selection
        self.bus = None
        self.internal_devices = []  # Holds Internal_MPU_6050 instances
        self.device_selectors = []  # GPIO selectors for each device


    def initialize(self, bus):
        '''
        Initialize the MPU6050 sensors and configure GPIO.
        '''
        self.bus = bus

        # Setup GPIO for device selection
        Device.pin_factory = LGPIOFactory()
        self.device_selectors = [LED(pin) for pin in self.dev_pins]

        # Configure each MPU6050 device
        for dev_id in range(3):
            self._select_device(dev_id)
            time.sleep(0.1)  # Allow time for device switching

            # Create an Internal_MPU_6050 instance for this sensor
            internal_device = Internal_MPU_6050(bus)
            internal_device.initialize()
            self.internal_devices.append(internal_device)

        self.status = self.DeviceStatus.ACTIVE
        self.start_worker()  # Start the data collection thread
        self._log(f"{self.name} Finished Initializing.")

    
    def _select_device(self, dev_id):
        '''
        Activates the GPIO pin corresponding to the selected device.
        '''
        for i, selector in enumerate(self.device_selectors):
            if i == dev_id:
                selector.on()
            else:
                selector.off()


    def update(self):
        '''
        Updates cached values from the data collection thread.
        '''
            
        # No additional logic needed if data collection worker is running
        self._check_cache_timeout()


    def _data_collection_worker(self):
        """
        This function contains the code that will be running on the separate thread.
        It should handle communication with the sensors and update the cache.
        """
        while self.status == self.DeviceStatus.ACTIVE:
            for dev_id in range(3):
                self._select_device(dev_id)
                time.sleep(0.05)

                # Get data from the internal MPU6050 device
                internal_device = self.internal_devices[dev_id]

                # Read acceleration and gyroscope data
                try:
                    acceleration = internal_device.read_acceleration()
                    gyroscope = internal_device.read_gyroscope()
                except Exception as e:
                    self.status = self.DeviceStatus.ERROR
                    break


                # Create parameterized data entries
                data = {
                    f"MPU{dev_id + 1}_xAccl": acceleration["x"],
                    f"MPU{dev_id + 1}_yAccl": acceleration["y"],
                    f"MPU{dev_id + 1}_zAccl": acceleration["z"],
                    f"MPU{dev_id + 1}_xGyro": gyroscope["x"],
                    f"MPU{dev_id + 1}_yGyro": gyroscope["y"],
                    f"MPU{dev_id + 1}_zGyro": gyroscope["z"],
                }

                # Update the shared cache
                self._update_cache(data)

        # Log error if the data collection worker stops unexpectedly
        self._log("Data collection worker stopped.", self.log.LogSeverity.ERROR)
        self.status = self.DeviceStatus.ERROR

            










from Backend.data_logger import DataLogger
import time  # Import the time module for delta time calculation

if __name__ == '__main__':
    
    # Get I2C bus
    bus = SMBus(2)
    mpu = MPU_6050_x3('MPU', DataLogger('MPUTest'))

    mpu.initialize(bus)

    # Initialize prev_time to calculate delta time
    prev_time = time.time()

    while True:
        # Calculate delta time
        current_time = time.time()
        delta_time = current_time - prev_time
        prev_time = current_time  # Update prev_time for the next iteration

        # Update MPU data
        mpu.update()

        # Display MPU parameter names and their data
        print(f"Delta Time (s): {delta_time:.6f}")  # Print delta time
        print(f"mpu param names: {mpu.get_all_param_names()}")

        for param_name in mpu.get_all_param_names():
            print(f"{param_name}: {mpu.get_data(param_name)}")

        time.sleep(0.1)
