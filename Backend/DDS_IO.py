# Signal Input/Output for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from resources.interface import Interface, CANInterface, InterfaceProtocol
from resources.data_logger import DataLogger
from resources.analog_in import Analog_In, ValueMapper, ExponentialValueMapper
from resources.ads_1015 import ADS_1015
from typing import Union, List, Dict
import smbus2

"""
The purpose of this class is to handle all the low level data that the DDS Needs
There is functions for the higher level systems to pull data from various sources.
EX. The UI calls functions from here which pulls data from sensor objects.
"""



class DDS_IO:

    # ===== Debugging Variables =====
    CAN_ENABLED = True
    I2C_ENABLED = True


    # ===== Device Constants=====
    I2C_BUS = '/dev/i2c-2'


    # ===== Devices that the DDS Talks to =====
    devices: Dict[str, Interface] = {
        "canInterface" : CANInterface,
        "coolingLoopSensors" : ADS_1015
    }



    # ===== Class Variables =====
    log : DataLogger
    

    # ===== Methods =====

    def __init__(self):
        self.log = DataLogger('DDS_Log')

        self.__log('Starting Dash Display System Backend...')

        self.__log('Initializing IO Devices')
        self.__initialize_devices()
        pass

    
    def update(self):
        '''Updates all sensors. Should be called as often as possible.'''

        # Update all enabled devices
        for key,interface in self.devices.items():
            if interface.status is not Interface.Status.DISABLED:
                interface.update()


    def get_device_data(self, device_key: str, parameter: str) -> Union[str, float, int, None]:
        ''' Gets a single parameter from a specified device.'''

        device = self.__get_device(device_key)

        # If the device is None, we can return early
        if device is None:
            self.__log(f'Device {device_key} not found.', DataLogger.LogSeverity.WARNING)
            return
        
        # If the device is not active, we can return early
        if device.status is not Interface.Status.ACTIVE:

            # Log the error
            self.__log(f'Device {device_key} is {device.status.name}. Could not get requested data: {parameter}', DataLogger.LogSeverity.WARNING)

            # Return a value that represents the current stat of the device
            if device.status is Interface.Status.DISABLED:
                return 'DIS'
            elif device.status is Interface.Status.ERROR:
                return 'ERR'
        
        # Fetch data from device
        data = device.get_data(parameter)

        # If the data is None, we can return early
        if data is None:
            self.__log(f'Data {device_key} not found for device {device_key}', DataLogger.LogSeverity.WARNING)
            return
        
        # Return the data
        return data


    def __get_device(self, deviceKey : str) -> Interface:
        ''' Gets a device at a specified key.
        This may return a None value.'''

        return self.devices.get(deviceKey)


    def __initialize_devices(self):

        '''Initializes all sensors & interfaces for the DDS'''

        self.devices = {}


        # ===== Init CAN =====
        if self.CAN_ENABLED:
            self.__initialize_CAN()

        else:
            # CANBus Disabled
            self.__log('CAN Disabled: Skipping initialization.', DataLogger.LogSeverity.WARNING)
            del self.devices['canInterface']


        # ===== Init i2c ===== 
        if self.I2C_ENABLED:
            self.__initialize_i2c()

        else:
            # i2c Disabled
            self.__log('i2c Disabled: Skipping initialization.', DataLogger.LogSeverity.WARNING)
            del self.devices['coolingLoopSensors']


        # ===== TODO: Init Accelerometers ===== 


    def __initialize_i2c(self):

        '''Initializes the i2c Interface'''

        self.__log('Initializing i2c...')

        try:
            self.log(f'Starting i2c bus on {self.I2C_BUS}')

            # Define i2c bus
            self.i2c_bus = smbus2.SMBus(bus=self.I2C_BUS)
        
            # ===== Init cooling loop inputs & ADS ===== 
            M3200_value_mapper = ValueMapper(
                voltage_range=[0.5, 4.5], 
                output_range=[0, 17])

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
            fixed_resistor = 3200
            NTC_M12_value_mapper = ExponentialValueMapper(
                resistance_values=resistance_values,
                output_values=temperature_values,
                supply_voltage=supply_voltage,
                fixed_resistor=fixed_resistor
            )

            self.devices['coolingLoopSensors'] = ADS_1015("Cooling loop", logger=self.log, i2c_bus=self.i2c_bus, inputs = [
                Analog_In('hotPressure', 'bar', mapper=M3200_value_mapper, tolerance=0.1),           #ADC1(A0)
                Analog_In('hotTemperature', '°C', mapper=NTC_M12_value_mapper, tolerance=0.1),       #ADC1(A1)
                Analog_In('coldPressure', 'bar', mapper=M3200_value_mapper, tolerance=0.1),          #ADC1(A2)
                Analog_In('coldTemperature', '°C', mapper=NTC_M12_value_mapper, tolerance=0.1)       #ADC1(A3)
            ])
            # TODO: Init second ADC w/ other sensors

            self.__log('Successfully Initialized i2c!')
        
        except Exception as e:
            # Failed to initialize
            self.__failed_to_init('i2c', exception=e, device_keys='coolingLoopSensors')

            # Disable the i2c devices
            self.devices['coolingLoopSensors'].status = Interface.Status.DISABLED
    

    def __initialize_CAN(self):
            
        '''Initializes the CANBus Interface'''

        self.__log('Initializing CANBus...')

        try:
            # Init canInterface
            self.devices['canInterface'] = CANInterface('MC & AMS', 
                                                        can_interface='can0', 
                                                        database_path='Backend/candatabase/CANDatabaseDTI500v2.dbc', 
                                                        logger=self.log)
            self.devices['canInterface'].add_database('Backend/candatabase/Orion_CANBUSv4.dbc') # Add the DBC file for the AMS to the CAN interface

            # Log completion
            self.__log('Successfully Initialized CANBus!')

        except Exception as e:
            # Failed to initialize
            self.__failed_to_init('CAN', exception=e, device_keys=
                                  'canInterface')


    def __failed_to_init(self, protocol_name: str, exception: Exception, device_keys: List[str]):
        # Log the error
        self.__log(f'{protocol_name} Initialization Error: {exception}, continuing', DataLogger.LogSeverity.CRITICAL)

        # Mark the devices as having an error
        for device_key in device_keys:
            self.devices[device_key].status = Interface.Status.ERROR


    
    def __log(self, msg: str, severity=DataLogger.LogSeverity.INFO):
        self.log.writeLog(
            logger_name='DDS_IO',
            msg=msg,
            severity=severity)

# Example / Testing Code

DEBUG_ENABLED = True

import time

if DEBUG_ENABLED:

    io = DDS_IO()
    last_print_time = 0  # Tracks the last time the print statements were executed
    PRINT_INTERVAL = 1   # Time interval in seconds between prints

    delta_times = []  # List to store delta times
    last_loop_time = time.time()  # Tracks the time of the last loop iteration

    while True:
        io.update()

        # Measure the current time and calculate the delta time for this loop iteration
        current_time = time.time()
        delta_time = current_time - last_loop_time
        delta_times.append(delta_time)
        last_loop_time = current_time

        # Calculate and print average delta time every PRINT_INTERVAL
        if current_time - last_print_time >= PRINT_INTERVAL:
            # Update the last print time
            last_print_time = current_time

            # Get and print the data
            hotpressure = io.__get_device('coolingLoopSensors').get_data('hotPressure')
            print(f"hot pressure: {hotpressure}")

            coldpressure = io.__get_device('coolingLoopSensors').get_data('coldPressure')
            print(f"cold pressure: {coldpressure}")

            hottemp = io.__get_device('coolingLoopSensors').get_data('hotTemperature')
            print(f"hot temp: {hottemp}")

            coldtemp = io.__get_device('coolingLoopSensors').get_data('coldTemperature')
            print(f"cold temp: {coldtemp}")

            # Calculate and print the average delta time
            if delta_times:
                avg_delta_time = sum(delta_times) / len(delta_times)
                print(f"Average delta time: {avg_delta_time:.6f} seconds")
                delta_times.clear()  # Clear the list after printing the average
