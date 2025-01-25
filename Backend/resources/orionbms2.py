# DTI HV 500 (MC) Class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from Backend.device import CANDevice


class Orion_BMS_2(CANDevice):
    '''
    This device contains the logic from the Orion BMS 2 Accumulator Management System
    '''

    def __init__(self, dbc_filepath: str, logger):
        super().__init__('OrionBMS2', dbc_filepath, logger)

    def initialize(self, bus):
        return super().initialize(bus)