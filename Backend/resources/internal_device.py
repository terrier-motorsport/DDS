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

    
    def eight_bit_unsigned_byte_to_signed_byte(self, unsigned_byte):
        return unsigned_byte - 256 if unsigned_byte > 127 else unsigned_byte
    
        # Example unsigned to signed byte conversion function
    def unsigned_byte_to_signed_byte(self, unsigned_byte, bit_depth=8):
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
    

if __name__ == '__main__':
    dev = InternalDevice()

    print(dev.eight_bit_unsigned_byte_to_signed_byte(1024))
    print(dev.unsigned_byte_to_signed_byte(1024))
