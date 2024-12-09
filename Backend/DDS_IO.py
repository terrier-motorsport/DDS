# Signal Input/Output for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from resources.interface import Interface, CANInterface
from resources.data_logger import File
from resources.analog_in import Analog_In, ValueMapper, ExponentialValueMapper
from resources.ads_1015 import ADS_1015
import smbus2

"""
The purpose of this class is to handle all the low level data that the DDS Needs
There is functions for the higher level systems to pull data from various sources.
EX. The UI calls functions from here which pulls data from sensor objects.
"""



class DDS_IO:

    # ===== Debugging Variables =====
    CAN_ENABLED = False
    I2C_ENABLED = True


    
    logFile = File('FullDataLog')

    # ===== Devices that the DDS Talks to =====
    devices = {
        "canInterface" : CANInterface,
        "coolingLoopSensors" : ADS_1015
    }

    # ===== Methods =====

    def __init__(self):
        self.__define_devices()
        pass

    
    def update(self):
        '''Updates all sensors. Should be called as often as possible.'''

        # Update all devices
        for device in self.devices:
            if device is not None:
                device.update()


    def get_device(self, deviceKey : str) -> Interface:
        return self.devices.get(deviceKey)


    def __define_devices(self):

        '''Initializes all sensors & interfaces for the DDS'''

        # ===== Init CAN interface & CAN Devices =====
        if self.CAN_ENABLED:
            self.devices['canInterface'] = CANInterface('MC & AMS', can_interface='can0', database_path='Backend/candatabase/CANDatabaseDTI500v2.dbc', logFile=self.logFile)
            self.devices['canInterface'].add_database('Backend/candatabase/Orion_CANBUSv4.dbc') # Add the DBC file for the AMS to the CAN interface


        # ===== Init i2c bus ===== 
        if self.I2C_ENABLED:
            self.i2c_bus = smbus2.SMBus(1)


            # ===== Init cooling loop inputs & ADS ===== 
            M3200_value_mapper = ValueMapper(voltage_range=[0.5, 4.5], output_range=[0, 17])

            # Define constants for NTC_M12 value mapping
            resistance_values = [
                45313, 26114, 15462, 9397, 5896, 3792, 2500,
                1707, 1175, 834, 596, 436, 323, 243, 187, 144, 113, 89
            ]
            temperature_values = [
                -40, -30, -20, -10, 0, 10, 20, 30, 40, 50,
                60, 70, 80, 90, 100, 110, 120, 130
            ]
            # Refer to the voltage divider circuit for the NTC_M12s
            supply_voltage = 5
            fixed_resistor = 10000
            NTC_M12_value_mapper = ExponentialValueMapper(
                resistance_values=resistance_values,
                output_values=temperature_values,
                supply_voltage=supply_voltage,
                fixed_resistor=fixed_resistor
            )

            self.devices['coolingLoopSensors'] = ADS_1015("Cooling loop", File, i2c_bus=self.i2c_bus, inputs = [
                Analog_In('hotPressure', 'bar', mapper=M3200_value_mapper),           #ADC1(A0)
                Analog_In('coldPressure', 'bar', mapper=M3200_value_mapper),          #ADC1(A1)
                Analog_In('hotTemperature', '°C', mapper=NTC_M12_value_mapper),       #ADC1(A2)
                Analog_In('coldTemperature', '°C', mapper=NTC_M12_value_mapper)       #ADC1(A3)
            ])
            # TODO: Init second ADC w/ other sensors


        # ===== TODO: Init Accelerometers ===== 


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

