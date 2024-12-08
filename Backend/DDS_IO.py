# Signal Input/Output for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from resources.interface import Interface, CANInterface, I2CDevice, InterfaceProtocol
from resources.data_logger import File
from resources.sensors.ads1015i2c import ADS1015i2c
import smbus2 # type: ignore

"""
The purpose of this class is to handle all the low level data that the DDS Needs
There is functions for the higher level systems to pull data from various sources.
EX. The UI calls functions from here which pulls data from sensor objects.
"""

class DDS_IO:

    # ===== Log File for all sensor data =====
    logFile = File('FullDataLog')

    # ===== Devices that the DDS Talks to =====
    devices = {
        "canInterface" : CANInterface,
        "coolingLoopSensors" : ADS1015i2c
    }

    # ===== Methods =====

    def __init__(self):
        self.__define_devices()
        pass

    
    def update(self):
        '''Updates all sensors. Should be called as often as possible.'''

        # Update all devices
        for device in self.devices:
            device.update()


    def get_device(self, deviceKey : str) -> Interface:
        return self.devices.get(deviceKey)


    def __define_devices(self):

        '''Initializes all sensors & interfaces for the DDS'''

        # Init CAN interface & CAN Devices
        self.devices['canInterface'] = CANInterface('MC & AMS', can_interface='can0', database_path='Backend/candatabase/CANDatabaseDTI500v2.dbc', logFile=self.logFile)
        self.devices['canInterface'].add_database('Backend/candatabase/Orion_CANBUSv4.dbc') # Add the DBC file for the AMS to the CAN interface

        # Init i2c bus
        self.i2c_bus = smbus2.SMBus(1)

        # Init cooling loop ADS
        self.devices['coolingLoopSensors'] = ADS1015i2c("Cooling loop", File, i2c_bus=self.i2c_bus)
        self.devices['coolingLoopSensors'].setChannelNames(
            'hotPressure',
            'coldPressure',
            'hotTemperature',
            'coldTemperature')
        
        # TODO: IMPLEMENT
        # self.devices['coolingLoopSensors'].setChannelMinimums(
        #     0.5,
        #     0.5,
        #     0.5,
        #     0.5
        # )
        # self.devices['coolingLoopSensors'].setChannelMaximums(
        #     4.5,
        #     4.5,
        #     5,
        #     5
        # )


# Example / Testing Code
DEBUG_ENABLED = True

if DEBUG_ENABLED == True:


    io = DDS_IO()


    while True:
        io.update()

        hotpressure = io.get_device('coolingLoopSensors').get_data('hotPressure')
        print(f"hot pressure: {hotpressure}")

        coldpressure = io.get_device('coolingLoopSensors').get_data('coldPressure')
        print(f"cold pressure: {coldpressure}")

        hottemp = io.get_device('coolingLoopSensors').get_data('hotTemperature')
        print(f"hot temp: {hottemp}")

        coldtemp = io.get_device('coolingLoopSensors').get_data('coldTemperature')
        print(f"cold temp: {coldtemp}")





    # logFile = File('MClog')
    # canInterface = CANInterface('MC & AMS', 
    #                             can_interface='can0', 
    #                             database_path='splash/candatabase/CANDatabaseDTI500v2.dbc', 
    #                             logFile=logFile)
    # canInterface.add_database('splash/candatabase/Orion_CANBUSv4.dbc')


    # io = DDS_IO()
    # io.get_data(device=canInterface)


    # print(type(canInterface.can_bus))

    # mode = input("tx or rx1 (MC) or rx2? (AMS)")

    # if (mode == 'tx'):
    #     for i in range(100):
    #         canInterface.update()
    #     print(canInterface.get_data('DigitalIn1'))

    #     canInterface.send_can('SetDigitalOut', {'DigitialOut1' : 1})

    #     for i in range(100):
    #         canInterface.update()
    #     print(canInterface.get_data('DigitalIn1'))

    # elif mode == 'rx1':
    #     while True:
    #         canInterface.update()
    #         print(canInterface.get_data("ERPM"))
    #         # print(motorController.get_data().get("ERPM"))

    # elif mode == 'rx2':
    #     while True:
    #         canInterface.update()

    #         dataToPrint = [
    #             "Input_Supply_Voltage",
    #             "DTC_Flags_1",
    #             "DTC_Flags_2",
    #             "Pack_CCL",
    #             "Pack_DCL"
    #         ]

    #         for key in dataToPrint:
    #             print(f"{key}: {canInterface.get_data(key)}")

            

    # # print(motorspd.get_protocol())

    # canInterface.close_connection()

