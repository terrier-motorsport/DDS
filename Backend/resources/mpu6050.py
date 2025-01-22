# Code orignially by ryker1990 on github.
	# https://github.com/ControlEverythingCommunity/MPU-6000/tree/master
# Adapted by Jackson Justus (jackjust@bu.edu) for Terrier Motorsport's DDS.

# Distributed with a free-will license.
# Use it any way you want, profit or free, provided it fits in the licenses of its associated works.
# MPU-6000
# This code is designed to work with the MPU-6000_I2CS I2C Mini Module available from ControlEverything.com.
# https://www.controleverything.com/content/Accelorometer?sku=MPU-6000_I2CS#tabs-0-product_tabset-2

import smbus2
import time

# Get I2C bus
bus = smbus2.SMBus(2)

# MPU-6000 address, 0x68(104)
# Select gyroscope configuration register, 0x1B(27)
#		0x18(24)	Full scale range = 2000 dps
bus.write_byte_data(0x68, 0x1B, 0x18)
# MPU-6000 address, 0x68(104)
# Select accelerometer configuration register, 0x1C(28)
#		0x18(24)	Full scale range = +/-16g
bus.write_byte_data(0x68, 0x1C, 0x18)
# MPU-6000 address, 0x68(104)
# Select power management register1, 0x6B(107)
#		0x01(01)	PLL with xGyro reference
bus.write_byte_data(0x68, 0x6B, 0x01)

time.sleep(0.8)

# MPU-6000 address, 0x68(104)
# Read data back from 0x3B(59), 6 bytes
# Accelerometer X-Axis MSB, X-Axis LSB, Y-Axis MSB, Y-Axis LSB, Z-Axis MSB, Z-Axis LSB
data = bus.read_i2c_block_data(0x68, 0x3B, 6)

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
data = bus.read_i2c_block_data(0x68, 0x43, 6)

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

# Output data to screen
print("Acceleration in X-Axis : %d" %xAccl)
print("Acceleration in Y-Axis : %d" %yAccl)
print("Acceleration in Z-Axis : %d" %zAccl)
print("X-Axis of Rotation : %d" %xGyro)
print("Y-Axis of Rotation : %d" %yGyro)
print("Z-Axis of Rotation : %d" %zGyro)