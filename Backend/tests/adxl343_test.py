# ADXL343 Accelerometer Tests for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)


import unittest
from unittest.mock import MagicMock, patch
import smbus2
import time

from Backend.resources.adxl343 import InternalADXL343, DATA_FORMAT, POWER_CTL, BW_RATE  # Adjust import to match your file/module structure

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
        self.mock_bus.read_byte_data.assert_any_call(self.valid_address, DATA_FORMAT)
        # Ensure it wrote to POWER_CTL to exit standby mode
        self.mock_bus.write_byte_data.assert_any_call(self.valid_address, POWER_CTL, 0x08)
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
            if register == DATA_FORMAT:
                return 0x01  # ±4g
            return 0x00

        self.mock_bus.read_byte_data.side_effect = mock_read_byte_data

        device.write_g_range(4)
        self.assertEqual(device.current_g_range, 4, "Expected class property to update to ±4g.")
        # Confirm the device re-read the DATA_FORMAT register
        self.assertIn(
            (device.device_addr, DATA_FORMAT),
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
                result = device._unsigned_byte_to_signed_byte(unsigned_value, bit_depth)
                self.assertEqual(
                    result,
                    expected_signed,
                    msg=(
                        f"For unsigned_value={unsigned_value} at {bit_depth} bits, "
                        f"expected {expected_signed}, got {result}"
                    )
                )

    
    def test_write_bit_to_byte_fifth_bit(self):
        """
        Tests writing 1 and 0 to the fifth bit in a byte using write_bit_to_byte.
        """

        device = self.InternalADXL343(self.mock_bus, self.valid_address)


        original_byte = 0b00000000  # Start with all bits 0
        modified_byte = device._write_bit_to_byte(original_byte, 5, 1)
        self.assertEqual(modified_byte, 0b00100000,
                         f"Failed to set the 5th bit. Expected 0b00100000, got {modified_byte:08b}")

        # Now clear the 5th bit
        modified_byte = device._write_bit_to_byte(modified_byte, 5, 0)
        self.assertEqual(modified_byte, 0b00000000,
                         f"Failed to clear the 5th bit. Expected 0b00000000, got {modified_byte:08b}")

        # Test setting the 5th bit in a byte that already has other bits set
        original_byte = 0b11011010
        modified_byte = device._write_bit_to_byte(original_byte, 5, 1)
        # This should produce 0b11111010 because bit 5 is now set (1)
        self.assertEqual(modified_byte, 0b11111010,
                         f"Failed to set the 5th bit in a mixed byte. Expected 0b11111010, got {modified_byte:08b}")

        # Clearing the 5th bit of that same mixed byte
        modified_byte = device._write_bit_to_byte(modified_byte, 5, 0)
        # Now it should go back to 0b11011010
        self.assertEqual(modified_byte, 0b11011010,
                         f"Failed to clear the 5th bit in a mixed byte. Expected 0b11011010, got {modified_byte:08b}")


    def test_write_bits_to_byte_example(self):
        """
        Tests writing multiple consecutive bits in a byte using write_bits_to_byte.
        """
        device = self.InternalADXL343(self.mock_bus, self.valid_address)

        # 1) Start with an all-zero byte, set 3 bits (bits 1, 2, 3) to 0b101 (5 decimal).
        #    That means bits 1..3 in the result should be: 0b101 => positions 1..3 => 0b1010 => 0xA
        original_byte = 0b00000000
        modified_byte = device._write_bits_to_byte(original_byte, start_bit=1, bit_count=3, new_value=0b101)
        self.assertEqual(modified_byte, 0b00001010,
                        f"Failed to set bits 1..3 to 0b101. Expected 0b00001010, got {modified_byte:08b}")

        # 2) Clear those same 3 bits by writing 0b000 into bits 1..3.
        modified_byte = device._write_bits_to_byte(modified_byte, start_bit=1, bit_count=3, new_value=0b000)
        self.assertEqual(modified_byte, 0b00000000,
                        f"Failed to clear bits 1..3. Expected 0b00000000, got {modified_byte:08b}")

        # 3) Test writing bits in a byte that already has some bits set outside the target region.
        #    For instance, set bits 4..6 to 0b111, while bit 7 remains set.
        original_byte = 0b10000000  # bit 7 is set
        modified_byte = device._write_bits_to_byte(original_byte, start_bit=4, bit_count=3, new_value=0b111)
        # This sets bits [4..6] to 0b111 => positions 4,5,6 => 0b01110000 (0x70) plus the existing bit 7 => 0xF0
        self.assertEqual(modified_byte, 0b11110000,
                        f"Failed to set bits 4..6 to 0b111. Expected 0b11110000, got {modified_byte:08b}")

        # 4) Now clear bits 5..6 in that same byte by writing 0b00 into them, leaving bit 4 = 1 and bit 7 = 1.
        #    So we should end up with 0b10010000 => 0x90
        modified_byte = device._write_bits_to_byte(modified_byte, start_bit=5, bit_count=2, new_value=0b00)
        self.assertEqual(modified_byte, 0b10010000,
                        f"Failed to clear bits 5..6. Expected 0b10010000, got {modified_byte:08b}")
        

    def test_write_rate(self):
        """
        Tests that write_rate correctly updates the BW_RATE register for a valid rate.
        """
        device = self.InternalADXL343(self.mock_bus, self.valid_address)

        # Mock the current register value and the desired rate
        self.mock_bus.read_byte_data.return_value = 0b00011111  # Example initial value

        # Set a valid rate (e.g., 100 Hz)
        valid_rate = 100  # Corresponds to 0b1010 in DATA_RATE_SETTINGS
        device.write_sample_rate(valid_rate)

        # Confirm the register was updated
        self.mock_bus.write_byte_data.assert_called_with(
            device.device_addr,
            BW_RATE,
            0b00011010  # Updated value: original upper bits unchanged, lower bits set to 0b1010
        )


    def test_write_rate_1_56_hz(self):
        """
        Tests that write_rate correctly updates the BW_RATE register for a rate of 1.56 Hz.
        """
        device = self.InternalADXL343(self.mock_bus, self.valid_address)

        # Mock the current register value before writing
        self.mock_bus.read_byte_data.return_value = 0b10110000  # Example current value

        # 1.56 Hz should correspond to 0b0100 in DATA_RATE_SETTINGS
        DATA_RATE_SETTINGS = {1.56: 0b0100}
        expected_bits = DATA_RATE_SETTINGS[1.56]

        # Call write_rate to set 1.56 Hz
        device.write_sample_rate(1.56)

        # Expected value: Keep the upper bits of the original register (0b1011xxxx) unchanged,
        # and replace the lower 4 bits with 0b0100 (for 1.56 Hz).
        expected_register_value = (0b10110000 & 0xF0) | expected_bits  # Upper bits unchanged, lower updated

        # Verify the correct value was written to the BW_RATE register
        self.mock_bus.write_byte_data.assert_called_with(
            device.device_addr,
            BW_RATE,
            expected_register_value
        )


    def test_write_rate_invalid_rate(self):
        """
        Tests that write_rate raises a ValueError for an invalid rate.
        """
        device = self.InternalADXL343(self.mock_bus, self.valid_address)

        # An invalid rate (not in DATA_RATE_SETTINGS)
        invalid_rate = 123.45  # Example invalid rate

        # Ensure that calling write_rate with an invalid rate raises a ValueError
        with self.assertRaises(ValueError) as context:
            device.write_sample_rate(invalid_rate)

        # Verify the error message is descriptive
        self.assertIn(
            f'Rate {invalid_rate} is not valid.',
            str(context.exception),
            "Error message should include the invalid rate."
        )

if __name__ == "__main__":
    unittest.main()