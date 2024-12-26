# Internal Device base class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)
    # Additional Code by Mohamed Amine Mzoughi (https://github.com/embeddedmz/ADXL343/blob/master/adxl343.py)


class InternalDevice():
    '''
    This class outlines low level communication objects, which are used to
    seperate functionality from the higher level class that the DDS interacts with. 

    Some Code by Mohamed Amine Mzoughi (https://github.com/embeddedmz/ADXL343/blob/master/adxl343.py)
    Modified by Jackson Justus (jackjust@bu.edu)
    '''

    def __init__(self):
        pass


        # Example unsigned to signed byte conversion function
    def _unsigned_byte_to_signed_byte(self, unsigned_byte, bit_depth=8):
        """
        Converts an unsigned raw value to a signed value using two's complement.
        
        Parameters:
            unsigned_value (int): The raw unsigned value.
            bit_depth (int): The resolution in bits.

        Returns:
            int: The signed value.
        """
        max_digital_value = 2**bit_depth
        half_scale = max_digital_value // 2

        if unsigned_byte >= half_scale:
            return unsigned_byte - max_digital_value
        return unsigned_byte
    

    def _write_bit_to_byte(self, original_byte: int, bit_position: int, value: int) -> int:
        """
        Sets or clears the bit at `bit_position` in `original_byte`.
        value: 1 to set, 0 to clear.
        """
        if value not in (0, 1):
            raise ValueError("value must be 0 or 1.")
        
        if value == 1:
            # Set the bit
            return original_byte | (1 << bit_position)
        else:
            # Clear the bit
            return original_byte & ~(1 << bit_position)
    

    def _write_bits_to_byte(self, original_byte: int, start_bit: int, bit_count: int, new_value: int) -> int:
        """
        Replaces a range of bits in 'original_byte' (starting at 'start_bit', 
        spanning 'bit_count' bits) with 'new_value'.

        Args:
            original_byte (int): The original byte to modify.
            start_bit (int): The index (0-based from the least significant bit) 
                where the replacement should begin.
            bit_count (int): How many consecutive bits to replace.
            new_value (int): The value to store in that range of bits. 
                (Should fit within 'bit_count' bits.)

        Returns:
            int: A modified byte (0–255 if bit_count <= 8) 
            with 'bit_count' bits replaced starting at 'start_bit'.
        """
        # Create a mask for the specified number of bits, e.g. for bit_count=3 => 0b111
        mask = (1 << bit_count) - 1

        # Ensure new_value fits into the specified bit_count
        new_value = new_value & mask

        # Shift new_value to align it with the start_bit
        shifted_value = new_value << start_bit

        # Shift the mask to the correct region
        shifted_mask = mask << start_bit

        # Clear out the bits in the original_byte for the target region
        cleared_original = original_byte & ~shifted_mask

        # OR in the new bits
        return cleared_original | shifted_value


if __name__ == '__main__':
    dev = InternalDevice()

    print(dev._unsigned_byte_to_signed_byte(512))
