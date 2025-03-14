# Elcon UHF 3.3kW (Charger) Class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from Backend.device import CANDevice


class Elcon_UHF(CANDevice):
    '''
    This device contains the logic from the ELCON UHF Motor Controller
    '''

    def __init__(self, dbc_filepath: str, logger):
        super().__init__('ELCON_UHF', dbc_filepath, logger)

    