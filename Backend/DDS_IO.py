# Signal Input/Output for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from Backend.resources.interface import Interface, CANInterface, I2CDevice, InterfaceProtocol
from resources.data_logger import File
from resources.sensors.ADS1015 import ADS1015

"""
The purpose of this class is to handle all the low level data that the DDS Needs
There is functions for the higher level systems to pull data from various sources.
EX. The UI calls functions from here which pulls data from sensor objects.
"""

class DDS_IO:

    # ===== Log File for all sensor data =====
    logFile = File('FullDataLog')

    devices = {
        "canInterface" : CANInterface,
        "digitalAnalogConverter" : ADS1015
    }

    # ===== Devices that the DDS Talks to =====

    def __init__(self):
        self.__define_sensors()
        pass

    
    def __define_sensors(self):
        '''Initializes all sensors for the DDS'''

        # Add the DBC file for the AMS to the CAN interface
        self.canInterface.add_database('Backend/candatabase/Orion_CANBUSv4.dbc')

        self.devices['canInterface'] = CANInterface('MC & AMS', can_interface='can0', database_path='Backend/candatabase/CANDatabaseDTI500v2.dbc', logFile=self.logFile)
        self.devices['canInterface'].add_database('Backend/candatabase/Orion_CANBUSv4.dbc')

        self.devices['digitalAnalogConverter'] = ADS1015("Cooling loop", File)

    def get_data(self, device : Interface, parameter : str):
        '''Gets a single parameter from a device'''
        return device.get_data(parameter)
    
    def update(self):
        '''Updates all sensors. Should be called as often as possible.'''

        # Update all devices
        for device in self.devices:
            device.update()


# Example / Testing Code
DEBUG_ENABLED = True

if DEBUG_ENABLED == True:


    io = DDS_IO()


    while True:
        io.update()

        hotpressure = io.canInterface.get_data("hotPressure")
        print(f"hot pressure: {hotpressure}")

        coldpressure = io.canInterface.get_data("coldPressure")
        print(f"cold pressure: {coldpressure}")

        hottemp = io.canInterface.get_data("hotTemperature")
        print(f"hot temp: {hottemp}")

        coldtemp = io.canInterface.get_data("coldTemperature")
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

