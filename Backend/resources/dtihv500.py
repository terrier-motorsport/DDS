# DTI HV 500 (MC) Class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from Backend.device import CANDevice


class DTI_HV_500(CANDevice):
    '''
    This device contains the logic from the DTI HV 500 Motor Controller
    '''

    def __init__(self, dbc_filepath: str, logger):
        super().__init__('DTI_HV_500', dbc_filepath, logger)

