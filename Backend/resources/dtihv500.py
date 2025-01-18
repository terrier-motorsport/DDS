# DTI HV 500 (MC) Class for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from Backend.device import CANDevice


class DTI_HV_500(CANDevice):
    '''
    This device contains the logic from the DTI HV 500 Motor Controller
    '''

    def __init__(self, logger):
        super().__init__('DTI HV 500', logger)

    def initialize(self, bus):
        return super().initialize(bus)
    
    def update(self):
        return super().update()