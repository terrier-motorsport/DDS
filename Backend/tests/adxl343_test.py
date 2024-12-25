# ADXL343 Accelerometer Tests for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)


import unittest
from unittest.mock import MagicMock, patch
import smbus2
import time

from Backend.resources.adxl343 import InternalADXL343  # Adjust import to match your file/module structure

class TestInternalADXL343(unittest.TestCase):

    def setUp(self):
        """
        Creates a mock SMBus and an InternalADXL343 instance.
        By default, mock the read_byte_data so that it returns 0x00 for the DATA_FORMAT register
        (indicating ±2g range bits 00).
        """
        self.mock_bus = MagicMock(spec=smbus2.SMBus)
        
        # By default, read_byte_data returns 0 => ±2g in the last two bits
        self.mock_bus.read_byte_data.return_value = 0x00
        # read_i2c_block_data returns 6 bytes of zeros
        self.mock_bus.read_i2c_block_data.return_value = [0, 0, 0, 0, 0, 0]

        self.valid_address = 0x1D
        self.invalid_address = 0x33  # Not in VALID_ADDRESSES
        self.InternalADXL343 = InternalADXL343

    def test_init_with_valid_address(self):
        """
        Test that initialization succeeds with a valid address.
        """
        try:
            device = self.InternalADXL343(self.mock_bus, self.valid_address)
        except ValueError as e:
            self.fail(f"Initialization with valid address raised ValueError unexpectedly: {e}")

        # Ensure the device actually read the g-range register
        self.mock_bus.read_byte_data.assert_any_call(self.valid_address, device.DATA_FORMAT)
        # Ensure it wrote to POWER_CTL to exit standby mode
        self.mock_bus.write_byte_data.assert_any_call(self.valid_address, device.POWER_CTL, 0x08)
        # The device’s current_g_range should be 2 (±2g) by default
        self.assertEqual(device.current_g_range, 2, "Expected default ±2g upon reading 0x00 from DATA_FORMAT.")

    def test_init_with_invalid_address(self):
        """
        Test that initialization raises a ValueError if the address is invalid.
        """
        with self.assertRaises(ValueError):
            _ = self.InternalADXL343(self.mock_bus, self.invalid_address)

    def test_read_g_range(self):
        """
        If read_byte_data returns 0x02 in the last two bits => 10 => ±8g.
        """
        from Backend.resources.adxl343 import InternalADXL343
        device = InternalADXL343(self.mock_bus, self.valid_address)

        # Now fake read_byte_data to return 0x02 => last two bits are 10 => ±8g
        self.mock_bus.read_byte_data.return_value = 0x02
        read_range = device.read_g_range()
        self.assertEqual(read_range, 8, "Expected ±8g if the last two bits are '10' (0x02).")

    def test_write_g_range_valid(self):
        """
        Test writing a new range. Mocks the re-read so that the device confirms the correct range bits.
        """
        device = InternalADXL343(self.mock_bus, self.valid_address)

        # Suppose we want to set ±4g => bits 01 => 0x01
        # We'll mock read_byte_data so after writing 0x01, read_g_range sees it in the register
        def mock_read_byte_data(addr, register):
            if register == device.DATA_FORMAT:
                return 0x01  # ±4g
            return 0x00

        self.mock_bus.read_byte_data.side_effect = mock_read_byte_data

        device.write_g_range(4)
        self.assertEqual(device.current_g_range, 4, "Expected class property to update to ±4g.")
        # Confirm the device re-read the DATA_FORMAT register
        self.assertIn(
            (device.DEVICE_ADDR, device.DATA_FORMAT),
            [(args[0], args[1]) for args, _ in self.mock_bus.read_byte_data.call_args_list],
            "Expected a re-read of DATA_FORMAT to verify ±4g setting."
        )

    def test_write_g_range_invalid(self):
        """
        Setting an unsupported range (e.g., ±3g) should raise ValueError.
        """
        device = self.InternalADXL343(self.mock_bus, self.valid_address)
        with self.assertRaises(ValueError):
            device.write_g_range(3)  # Not in [2, 4, 8, 16]

    def test_read_acceleration_in_g_default_zero(self):
        """
        If read_i2c_block_data returns all zeros, expect read_acceleration_in_g => [0.0, 0.0, 0.0].
        """
        device = self.InternalADXL343(self.mock_bus, self.valid_address)
        self.mock_bus.read_i2c_block_data.return_value = [0]*6

        result = device.read_acceleration_in_g()
        self.assertEqual(result, [0.0, 0.0, 0.0], "Expected zero acceleration if all raw bytes are zero.")

    def test_read_acceleration_in_g_mock_data(self):
        """
        Provide mock data for X, Y, Z, then ensure read_acceleration_in_g calls __convert_axis_bytes_to_g
        for each axis, producing consistent results.
        """
        device = self.InternalADXL343(self.mock_bus, self.valid_address)

        # Fake data for each axis: [X0, X1, Y0, Y1, Z0, Z1].
        # Example: X0=0x12, X1=0x00 => 18 decimal => ~0.0703g if ±2g
        self.mock_bus.read_i2c_block_data.return_value = [0x12, 0x00, 0x13, 0x00, 0x14, 0x00]

        # We'll just check that the result is consistent with the private method logic.
        # ±2g => bit_depth=10 => combined_value <512 => no sign flip => e.g., 0x12 => 18/256 => 0.0703g
        result = device.read_acceleration_in_g()
        self.assertEqual(len(result), 3, "Should return [x, y, z].")
        self.assertTrue(all(isinstance(r, float) for r in result), "All results should be floats.")

    def test_convert_axis_bytes_to_g_positive(self):
        """
        Direct test of the private __convert_axis_bytes_to_g for a positive reading scenario.
        """
        device = self.InternalADXL343(self.mock_bus, self.valid_address)
        device.current_g_range = 2  # ±2g => bit_depth=10 => sensitivity=256

        # LSB=0x34, MSB=0x01 => same logic as earlier example
        result = device._InternalADXL343__convert_axis_bytes_to_g(0x34, 0x01)
        self.assertAlmostEqual(result, 1.203125, places=5,
            msg="Expected ~1.203125g for (LSB=0x34, MSB=0x01) in ±2g mode.")

    def test_convert_axis_bytes_to_g_negative(self):
        """
        Direct test of the private __convert_axis_bytes_to_g for a negative reading scenario.
        """
        device = self.InternalADXL343(self.mock_bus, self.valid_address)
        device.current_g_range = 2  # ±2g => bit_depth=10 => sensitivity=256

        # LSB=0xFF, MSB=0x03 => from the earlier example, ~-0.00390625g
        result = device._InternalADXL343__convert_axis_bytes_to_g(0xFF, 0x03)
        self.assertAlmostEqual(result, -0.00390625, places=7,
            msg="Expected ~-0.00390625g for LSB=0xFF, MSB=0x03 in ±2g mode.")

    def test_i2c_read_error_handling(self):
        """
        OPTIONAL: Demonstrate how you might handle or assert an OSError is raised
        if the I2C read fails. This depends on your production code's error-handling behavior.
        """
        device = self.InternalADXL343(self.mock_bus, self.valid_address)

        # Suppose the read_i2c_block_data raises an OSError
        self.mock_bus.read_i2c_block_data.side_effect = OSError("I2C bus error")

        with self.assertRaises(OSError):
            _ = device.read_acceleration_in_g()

    def test_i2c_write_error_handling(self):
        """
        OPTIONAL: Show how you might handle or test for an OSError if the I2C write fails.
        """
        device = self.InternalADXL343(self.mock_bus, self.valid_address)

        # Suppose the write_byte_data raises an OSError
        self.mock_bus.write_byte_data.side_effect = OSError("I2C bus error")

        with self.assertRaises(OSError):
            device.write_g_range(4)  # This triggers a write

    def test_unsigned_byte_to_signed_byte(self):
        """
        Tests the 'unsigned_byte_to_signed_byte' function for various bit depths and values.
        """

        device = self.InternalADXL343(self.mock_bus, self.valid_address)

        # Each tuple: (unsigned_value, bit_depth, expected_signed_value)
        test_cases = [
            # 8-bit examples
            (0,    8,   0),      # Min unsigned => 0
            (127,  8,   127),    # Just below half-scale => positive
            (128,  8,  -128),    # Exactly half-scale => negative boundary
            (255,  8,  -1),      # Max unsigned => -1 in two's complement 8-bit

            # 10-bit examples
            (0,    10,  0),
            (511,  10,  511),    # Just below half-scale => positive
            (512,  10,  -512),   # Exactly half-scale => boundary
            (1023, 10,  -1),     # Max in 10 bits => -1 in two's complement

            # 12-bit examples
            (0,      12,   0),
            (2047,   12,   2047),  # Just below half-scale => positive
            (2048,   12,  -2048),  # Boundary => half-scale
            (4095,   12,  -1),     # Max => -1

            # 13-bit examples
            (0,      13,   0),
            (4095,   13,  4095),   # Just below half-scale => positive
            (4096,   13, -4096),   # Boundary => half-scale
            (8191,   13,   -1),    # Max => -1
        ]

        for unsigned_value, bit_depth, expected_signed in test_cases:
            with self.subTest(unsigned_value=unsigned_value, bit_depth=bit_depth):
                result = device.unsigned_byte_to_signed_byte(unsigned_value, bit_depth)
                self.assertEqual(
                    result,
                    expected_signed,
                    msg=(
                        f"For unsigned_value={unsigned_value} at {bit_depth} bits, "
                        f"expected {expected_signed}, got {result}"
                    )
                )

if __name__ == "__main__":
    unittest.main()