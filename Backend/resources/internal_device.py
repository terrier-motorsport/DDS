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

    
    def unsigned_byte_to_signed_byte(unsigned_byte):
        return unsigned_byte - 256 if unsigned_byte > 127 else unsigned_byte
