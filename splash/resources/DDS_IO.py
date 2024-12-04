# Signal Input/Output for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from input import Input, CANInterface, SPIDevice, SensorProtocol
from data_logger import File

"""
The purpose of this class is to handle all the low level data that the DDS Needs
There is functions for the higher level systems to pull data from various sources.
EX. The UI calls functions from here which pulls data from sensor objects.
"""

class DDS_IO:

    logFile = File('FullDataLog')

    motorController = CANInterface('DTI HV 500 (MC)', can_interface='can0', database_path='splash/candatabase/CANDatabaseDTI500.dbc', logFile=logFile)

    # TODO: Implement 
    # AcumulatorManagementSystem = CANDevice('Orion BMS 2', can_interface='can0', database_path='')

    accelerometer = SPIDevice('accelerometer', 0x3c, logFile=logFile)
    

    def __init__(self):
        pass

    
    def define_sensors(self):

        accelerometer = Input(SensorProtocol.SPI)

        self.sensors.append()



