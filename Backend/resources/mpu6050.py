# Code orignially by ryker1990 on github.
	# https://github.com/ControlEverythingCommunity/MPU-6000/tree/master
# Adapted by Jackson Justus (jackjust@bu.edu) for Terrier Motorsport's DDS.

# Distributed with a free-will license.
# Use it any way you want, profit or free, provided it fits in the licenses of its associated works.
# MPU-6000
# This code is designed to work with the MPU-6000_I2CS I2C Mini Module available from ControlEverything.com.
# https://www.controleverything.com/content/Accelorometer?sku=MPU-6000_I2CS#tabs-0-product_tabset-2


from Backend.device import I2CDevice
from smbus2 import SMBus
from gpiozero.pins.lgpio import LGPIOFactory
from gpiozero import Device, LED
import time


class MPU_6050_x3(I2CDevice):

	'''
	This handles the communication for all three MPU 6050 accel/gyro sensors.
	'''


	def initialize(self, bus):
		self.bus = bus

		# Initialize the gpiozero lib with lgpio
		Device.pin_factory = LGPIOFactory()

		ACC_1_SEL = 17
		ACC_2_SEL = 27
		ACC_3_SEL = 22


		# SETUP GPIO
		# These are setup as LEDs bc its easy to handle
		self.dev_1_sel = LED(ACC_1_SEL)
		self.dev_2_sel = LED(ACC_2_SEL)
		self.dev_3_sel = LED(ACC_3_SEL)

		# Iterate through each device
		for dev_id in range(3):

			if dev_id == 0:
				self.dev_1_sel.on()
				self.dev_2_sel.off()
				self.dev_3_sel.off()
			elif dev_id == 1:
				self.dev_1_sel.off()
				self.dev_2_sel.on()
				self.dev_3_sel.off()
			elif dev_id == 2:
				self.dev_1_sel.off()
				self.dev_2_sel.off()
				self.dev_3_sel.on()
			time.sleep(0.01)

			# Configure each device
			# MPU-6050 address, 0x68(104)
			# Select gyroscope configuration register, 0x1B(27)
			#		0x18(24)	Full scale range = 2000 dps
			bus.write_byte_data(0x69, 0x1B, 0x18)
			# MPU-6050 address, 0x68(104)
			# Select accelerometer configuration register, 0x1C(28)
			#		0x18(24)	Full scale range = +/-16g
			bus.write_byte_data(0x69, 0x1C, 0x18)
			# MPU-6050 address, 0x68(104)
			# Select power management register1, 0x6B(107)
			#		0x01(01)	PLL with xGyro reference
			bus.write_byte_data(0x69, 0x6B, 0x01)

		# Finish initialization & start threaded data collection
		super().initialize(bus)

	
	def update(self):

		data = self._get_data_from_thread()
		print(data)

		if data is None:
			self._update_cache(new_data_exists=False)
			return
		self._update_cache(new_data_exists=True)

		# This is kinda bad code
		param_name = f"{data[0]}{data[1][0]}"
		self.cached_values[param_name] = data[2]
		self._log_telemetry(param_name, data, data[1][1])
		pass

	def _data_collection_worker(self):
		'''
        This function contains the code that will be running on the seperate thread.
        It should be doing all the communication that interfaces with the I/O of the pi.
		'''

		while self.status is self.DeviceStatus.ACTIVE:

			# Iterate through each device
			for dev_id in range(3):

				if dev_id == 0:
					self.dev_1_sel.on()
					self.dev_2_sel.off()
					self.dev_3_sel.off()
				elif dev_id == 1:
					self.dev_1_sel.off()
					self.dev_2_sel.on()
					self.dev_3_sel.off()
				elif dev_id == 2:
					self.dev_1_sel.off()
					self.dev_2_sel.off()
					self.dev_3_sel.on()
				time.sleep(0.01)

				# MPU-6000 address, 0x68(104)
				# Read data back from 0x3B(59), 6 bytes
				# Accelerometer X-Axis MSB, X-Axis LSB, Y-Axis MSB, Y-Axis LSB, Z-Axis MSB, Z-Axis LSB
				data = bus.read_i2c_block_data(0x69, 0x3B, 6)

				# Convert the data
				xAccl = data[0] * 256 + data[1]
				if xAccl > 32767 :
					xAccl -= 65536

				yAccl = data[2] * 256 + data[3]
				if yAccl > 32767 :
					yAccl -= 65536

				zAccl = data[4] * 256 + data[5]
				if zAccl > 32767 :
					zAccl -= 65536

				# MPU-6000 address, 0x68(104)
				# Read data back from 0x43(67), 6 bytes
				# Gyrometer X-Axis MSB, X-Axis LSB, Y-Axis MSB, Y-Axis LSB, Z-Axis MSB, Z-Axis LSB
				data = bus.read_i2c_block_data(0x69, 0x43, 6)

				# Convert the data
				xGyro = data[0] * 256 + data[1]
				if xGyro > 32767 :
					xGyro -= 65536

				yGyro = data[2] * 256 + data[3]
				if yGyro > 32767 :
					yGyro -= 65536

				zGyro = data[4] * 256 + data[5]
				if zGyro > 32767 :
					zGyro -= 65536


				# Convert the raw acceleration data to 'g'
				# Sensitivity scale factor for ±16g is 2048 LSB/g
				SCALE_FACTOR = 2048.0

				xAccl_g = xAccl / SCALE_FACTOR
				yAccl_g = yAccl / SCALE_FACTOR
				zAccl_g = zAccl / SCALE_FACTOR

				# Output the acceleration in g to the screen
				# print("Acceleration in X-Axis (g): %.3f" % xAccl_g)
				# print("Acceleration in Y-Axis (g): %.3f" % yAccl_g)
				# print("Acceleration in Z-Axis (g): %.3f" % zAccl_g)

				# Sensitivity scale factor for ±2000 dps is 16.4 LSB/dps
				GYRO_SCALE_FACTOR = 16.4

				xGyro_dps = xGyro / GYRO_SCALE_FACTOR
				yGyro_dps = yGyro / GYRO_SCALE_FACTOR
				zGyro_dps = zGyro / GYRO_SCALE_FACTOR

				# Output the gyroscope data in dps to the screen
				# print("Rotation in X-Axis (dps): %.3f" % xGyro_dps)
				# print("Rotation in Y-Axis (dps): %.3f" % yGyro_dps)
				# print("Rotation in Z-Axis (dps): %.3f" % zGyro_dps)


				# Identify the selected device
				dev_str: str
				if dev_id == 0:
					dev_str = "MPU1"
				if dev_id == 1:
					dev_str = "MPU2"
				if dev_id == 2:
					dev_str = "MPU3"

				# Add the data to the queue
				self.data_queue.put((dev_str, ("xAccl","g"), xAccl_g))
				self.data_queue.put((dev_str, ("yAccl","g"), yAccl_g))
				self.data_queue.put((dev_str, ("zAccl","g"), zAccl_g))

				self.data_queue.put((dev_str, ("xGyro","dps"), xGyro_dps))
				self.data_queue.put((dev_str, ("yGyro","dps"), yGyro_dps))
				self.data_queue.put((dev_str, ("zGyro","dps"), zGyro_dps))

		# If we ever get here, there was a problem.
		# We should log that the data collection worker stopped working
		self._log('Data collection worker stopped.', self.log.LogSeverity.ERROR)
		self.status = self.DeviceStatus.ERROR

			











from Backend.data_logger import DataLogger

# Get I2C bus
bus = SMBus(2)
mpu = MPU_6050_x3('MPU', DataLogger('MPUTest'))

mpu.initialize(bus)

while True:
	mpu.update()


'''
ACC_1_SEL = 17
ACC_2_SEL = 27
ACC_3_SEL = 22


# SETUP GPIO
# These are setup as LEDs bc its easy to handle
dev_1_sel = LED(ACC_1_SEL)
dev_2_sel = LED(ACC_2_SEL)
dev_3_sel = LED(ACC_3_SEL)

prev_time = time.time()  # Initialize prev_time with the current time


while True:
	for dev_id in range(3):

		if dev_id == 0:
			# GPIO.output(ACC_1_SEL, 1)
			# GPIO.output(ACC_2_SEL, 0)
			# GPIO.output(ACC_3_SEL, 0)
			dev_1_sel.on()
			dev_2_sel.off()
			dev_3_sel.off()
			time.sleep(0.01)
		elif dev_id == 1:
			# GPIO.output(ACC_1_SEL, 0)
			# GPIO.output(ACC_2_SEL, 1)
			# GPIO.output(ACC_3_SEL, 0)
			dev_1_sel.off()
			dev_2_sel.on()
			dev_3_sel.off()
			time.sleep(0.01)
		elif dev_id == 2:
			# GPIO.output(ACC_1_SEL, 0)
			# GPIO.output(ACC_2_SEL, 0)
			# GPIO.output(ACC_3_SEL, 1)
			dev_1_sel.off()
			dev_2_sel.off()
			dev_3_sel.on()
			time.sleep(0.01)


		# MPU-6000 address, 0x68(104)
		# Select gyroscope configuration register, 0x1B(27)
		#		0x18(24)	Full scale range = 2000 dps
		bus.write_byte_data(0x69, 0x1B, 0x18)
		# MPU-6000 address, 0x68(104)
		# Select accelerometer configuration register, 0x1C(28)
		#		0x18(24)	Full scale range = +/-16g
		bus.write_byte_data(0x69, 0x1C, 0x18)
		# MPU-6000 address, 0x68(104)
		# Select power management register1, 0x6B(107)
		#		0x01(01)	PLL with xGyro reference
		bus.write_byte_data(0x69, 0x6B, 0x01)


		# MPU-6000 address, 0x68(104)
		# Read data back from 0x3B(59), 6 bytes
		# Accelerometer X-Axis MSB, X-Axis LSB, Y-Axis MSB, Y-Axis LSB, Z-Axis MSB, Z-Axis LSB
		data = bus.read_i2c_block_data(0x69, 0x3B, 6)

		# Convert the data
		xAccl = data[0] * 256 + data[1]
		if xAccl > 32767 :
			xAccl -= 65536

		yAccl = data[2] * 256 + data[3]
		if yAccl > 32767 :
			yAccl -= 65536

		zAccl = data[4] * 256 + data[5]
		if zAccl > 32767 :
			zAccl -= 65536

		# MPU-6000 address, 0x68(104)
		# Read data back from 0x43(67), 6 bytes
		# Gyrometer X-Axis MSB, X-Axis LSB, Y-Axis MSB, Y-Axis LSB, Z-Axis MSB, Z-Axis LSB
		data = bus.read_i2c_block_data(0x69, 0x43, 6)

		# Convert the data
		xGyro = data[0] * 256 + data[1]
		if xGyro > 32767 :
			xGyro -= 65536

		yGyro = data[2] * 256 + data[3]
		if yGyro > 32767 :
			yGyro -= 65536

		zGyro = data[4] * 256 + data[5]
		if zGyro > 32767 :
			zGyro -= 65536


		# Convert the raw acceleration data to 'g'
		# Sensitivity scale factor for ±16g is 2048 LSB/g
		SCALE_FACTOR = 2048.0

		xAccl_g = xAccl / SCALE_FACTOR
		yAccl_g = yAccl / SCALE_FACTOR
		zAccl_g = zAccl / SCALE_FACTOR

		# Output the acceleration in g to the screen
		print("Acceleration in X-Axis (g): %.3f" % xAccl_g)
		print("Acceleration in Y-Axis (g): %.3f" % yAccl_g)
		print("Acceleration in Z-Axis (g): %.3f" % zAccl_g)

		# Sensitivity scale factor for ±2000 dps is 16.4 LSB/dps
		GYRO_SCALE_FACTOR = 16.4

		xGyro_dps = xGyro / GYRO_SCALE_FACTOR
		yGyro_dps = yGyro / GYRO_SCALE_FACTOR
		zGyro_dps = zGyro / GYRO_SCALE_FACTOR

		# Output the gyroscope data in dps to the screen
		print("Rotation in X-Axis (dps): %.3f" % xGyro_dps)
		print("Rotation in Y-Axis (dps): %.3f" % yGyro_dps)
		print("Rotation in Z-Axis (dps): %.3f" % zGyro_dps)


		# Calculate and print delta time
		current_time = time.time()
		delta_time = current_time - prev_time
		prev_time = current_time
		print("Delta Time (s): %.6f" % delta_time)

		print()
		print()
'''