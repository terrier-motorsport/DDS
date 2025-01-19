# Signal Input/Output for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

import random
from Backend.interface import Interface, CANInterface, I2CInterface, InterfaceProtocol
from Backend.data_logger import DataLogger
from Backend.value_monitor import ParameterMonitor, ParameterWarning
from Backend.resources.analog_in import Analog_In, ValueMapper, ExponentialValueMapper
from Backend.resources.ads_1015 import ADS_1015
from Backend.resources.adxl343 import ADXL343
from Backend.resources.dtihv500 import DTI_HV_500
from Backend.resources.orionbms2 import Orion_BMS_2
from typing import Union, Dict, List
import Backend.config.device_config
import smbus2
import can

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
    CAN_BUS = 'can0'


    # ===== Devices that the DDS Talks to =====
    interfaces: Dict[str, Interface]


    # ===== Class Variables =====
    log : DataLogger
    parameter_monitor: ParameterMonitor
    

    # ===== Methods =====
    def __init__(self, debug=False, demo_mode=False):
        '''
        Starts the Backend of the DDS.

        Parameters:
            debug (bool): Puts the DataLogger into debug mode
            demo_mode (bool): If a parameter is requested which isn't avaliable, a random value is returned instead.

        '''
        self.log = DataLogger('DDS_Log')
        self.debug = debug
        self.demo_mode = demo_mode
        self.parameter_monitor = ParameterMonitor('Backend/config/valuelimits.json5', self.log)
        self.interfaces = {}

        self.__log('Starting Dash Display System Backend...')

        self.__initialize_io()


    def update(self):
        '''Updates all sensors. Should be called as often as possible.'''

        # Update all enabled devices
        for interface_name, interface_object in self.interfaces.items():

            status = interface_object.status

            if status is Interface.InterfaceStatus.ACTIVE:
                try:
                    interface_object.update()
                    self.__monitor_device_parameters(interface_object)
                except Exception as e:
                    self.__log(f'Failed to update {interface_name}. {e}')
                    interface_object.status = Interface.InterfaceStatus.ERROR
            
            elif status is Interface.InterfaceStatus.ERROR:
                try:
                    interface_object.initialize()
                except Exception as e:
                    return

            elif interface_object.status is Interface.InterfaceStatus.DISABLED:
                return


    def get_device_data(self, device_key: str, parameter: str, caller: str="DDS_IO") -> Union[str, float, int, None]:
        '''
        Gets a single parameter from a specified device.

        Parameters:
            device_key `(str)`: The key of the device in the device list
            parameter `(str)`: The key of the parameter that you are requesting
            caller `(str)`: The name of the entity calling this function. Used for logging purposes.
        '''

        device = self.__get_device(device_key)

        # If the device is None, we can return early
        if device is None:
            self.__log(f'Device {device_key} not found. (Data Req: {parameter})', DataLogger.LogSeverity.DEBUG, caller)

            if self.demo_mode:
                return random.random() * 100
            return
        
        # If the device is not active, we can return early
        if device.status is not Interface.InterfaceStatus.ACTIVE:

            # Log the error
            self.__log(f'Device {device_key} is {device.status.name}. Could not get requested data: {parameter}', DataLogger.LogSeverity.WARNING)

            # Return a value that represents the current stat of the device
            if device.status is Interface.InterfaceStatus.DISABLED:
                return 'DIS'
            elif device.status is Interface.InterfaceStatus.ERROR:
                return 'ERR'
            elif device.status is Interface.InterfaceStatus.NOT_INITIALIZED:
                return 'NIN'
        
        # Fetch data from device
        data = device.get_data_from_device(parameter)

        # If the data is None, we can return early
        if data is None:
            self.__log(f'Data {device_key} not found for device {device_key}', DataLogger.LogSeverity.WARNING)

            # if self.demo_mode:
            #     return random.random()
            return None
        
        # Return the data
        return data
    

    def get_warnings(self) -> List[str]:
        '''Returns a list of active warnings'''
        warnings = self.parameter_monitor.get_warnings_as_str()
        print(f'{warnings}, {self.demo_mode}')

        if not self.demo_mode:
            return warnings
        else:
            warnings = [
                ParameterWarning('RPM', 9324, 'RPM is out of range').getMsg(),
                ParameterWarning('Mike', 1, 'THIS IS A SUPER DUPER LOOPER LONG MESSAGE').getMsg(),
                ParameterWarning('Anna', 2398, 'Anna is out of range').getMsg(),
            ]
            return warnings
        

    def get_device_names(self) -> List[str]:
        '''
        Returns a list of devices.
        If there are no devices, returns a single string with an error message.
        '''

        # if len(self.devices) == 0:
        #     return ['There are no available devices']
        device_names = []
        for device_name, device in self.interfaces.items():
            device_names.append(device_name)
        return device_names
    

    def get_device_parameters(self, param_name: str) -> List[str]:
        '''
        Returns a list of parameters for a specified device.
        '''
        device_params = []
        for param_name in self.interfaces[param_name].get_all_param_names_for_device():
            device_params.append(param_name)
        return device_params


    def __get_device(self, deviceKey : str) -> Interface:
        ''' Gets a device at a specified key.
        This may return a None value.'''

        return self.interfaces.get(deviceKey)
    

    def __initialize_io(self):

        '''Initializes all sensors & interfaces for the DDS'''
        self.__log('Initializing IO Devices')


        # ===== Init CAN =====
        if self.CAN_ENABLED:
            self.__log(f"Starting CAN bus on {self.CAN_BUS}")
            canInterface = CANInterface(
                name='CANInterface',
                can_channel=self.CAN_BUS,
                devices=[
                    Orion_BMS_2('Backend/candatabase/Orion_BMS2_CANBUSv7.dbc', self.log),
                    DTI_HV_500('Backend/candatabase/DTI_HV_500_CANBUSv3.dbc', self.log)
                ],
                logger=self.log
            )
            self.__safe_initialize_interface(canInterface)
            self.__log("Finished initializing all CAN devices!")
        else:
            # CAN Disabled
            self.__log('CAN Disabled: Skipping initialization.', DataLogger.LogSeverity.WARNING)


        # ===== Init i2c ===== 
        if self.I2C_ENABLED:
            self.__log(f'Starting i2c bus on {self.I2C_BUS}')
            i2cInterface = I2CInterface(
                'I2CInterface',
                i2c_channel=self.I2C_BUS,
                devices=[
                    # See the referenced package for details about devices.
                    Backend.config.device_config.define_ADC1(self.log),
                    Backend.config.device_config.define_ADC2(self.log),
                    # TODO: Implement
                    # Backend.config.device_config.define_chassis_MPU_6050(self.log),
                    # Backend.config.device_config.define_top_MPU_6050(self.log),
                    # Backend.config.device_config.define_wheel_MPU_6050(self.log),
                ],
                logger=self.log
            )
            self.__safe_initialize_interface(i2cInterface)
            self.__log('Finished initializing all i2c devices!')
        else:
            # i2c Disabled
            self.__log('i2c Disabled: Skipping initialization.', DataLogger.LogSeverity.WARNING)

        # ===== FIN INIT =====
        # Update the IO one time to wake all interface
        self.update()

        # Add dummy devices if we are in demo mode.
        if self.demo_mode:
            self.interfaces = {
                "Mike": Interface('Mike', InterfaceProtocol.I2C, self.log),
                "Anna": Interface('Anna', InterfaceProtocol.CAN, self.log)
            }
            for device_name, device in self.interfaces.items():
                if device_name == "Mike":
                    device.cached_values["sample_data One (1)"] = 203949.1324
                    device.cached_values["Two"] = "i like chocolate chip cookies"
                    device.cached_values["thre three threee"] = "i HATE chocolate chip cookies which dont have chocolate chips"
                if device_name == "Anna":
                    device.cached_values["other signal"] = "yum i love chocolate chip cookies"
                device.change_status(Interface.InterfaceStatus.ACTIVE)

        # Log that initialization has finished
        self.__log('All devices have been initialized. Listing devices.')
        
        for device_name, device_object in self.interfaces.items():
            self.__log(f'{device_name}: {device_object.status.name}')


    def __safe_initialize_interface(self, interface: Interface) -> bool:
        """
        This method takes care of initializing the given interface, with error handling.
        
        Parameters:
            interface (Interface): The child class to instantiate.
        
        Returns:
            bool: The result of the device being successfully initialized
        """

        # Add the interface to the interfaces dict:
        self.interfaces[interface.name] = interface

        try:
            # Attempt to initalize the interface
            interface.initialize()

            # Check if the interface can read data
            interface.update()

        except Exception as e:
            self.__failed_to_init_interface(interface=interface, e=e)
            return False
        return True      


    def __failed_to_init_interface(self, interface: Interface, e: Exception):
        '''
        This method takes care of handling the failed initialization
        The interface is set to the ERROR state and the DDS_IO will 
        continously attempt to inialize the interface.

        Parameters:
            interface (Interface): The interface that failed being initialized.
            e (Exception): The exception raised during initialization.


        '''

        # Log the error
        self.__log(f'{interface.interfaceProtocol.name} {interface.name} Initialization Error: {e}', 
                   DataLogger.LogSeverity.CRITICAL)

        if isinstance(e, OSError):
            if e.errno == 121:
                self.__log(f'Make sure {interface.name} is properly wired and shows up on i2cdetect!')

        # Mark the device as having an error
        self.interfaces[interface.name].status = Interface.InterfaceStatus.ERROR


    def __failed_to_init_protocol(self, protocol: InterfaceProtocol, exception: Exception):
        '''
        This logs an error when a protocol (ex. i2c) is unable to be intialized.
        This is usually caused by hardware being configured incorrectly, or running the program on an OS which doesn't support the protocol.
        If a protocol can't start, it is impossible to restart the devices on the protocol.
        '''

        # Log the error
        self.__log(f'Was unable to intialize {protocol.name}: {exception}. Interfaces on this protocol will be disabled.', DataLogger.LogSeverity.CRITICAL)

        # Disable protocol
        if protocol is InterfaceProtocol.I2C:
            self.I2C_ENABLED = False
        elif protocol is InterfaceProtocol.CAN:
            self.CAN_ENABLED = False
            self.__log('Make sure you are running the DDS w/ sudo to init CAN Correctly.')

    
    def __log(self, msg: str, severity=DataLogger.LogSeverity.INFO, name="DDS_IO"):
        self.log.writeLog(
            loggerName=name,
            msg=msg,
            severity=severity)

# Example / Testing Code

import time

if __name__ == '__main__':

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
            hotpressure = io.get_device_data('coolingLoopSensors', 'hotPressure')
            print(f"hot pressure: {hotpressure}")

            coldpressure = io.get_device_data('coolingLoopSensors', 'coldPressure')
            print(f"cold pressure: {coldpressure}")

            hottemp = io.get_device_data('coolingLoopSensors', 'hotTemperature')
            print(f"hot temp: {hottemp}")

            coldtemp = io.get_device_data('coolingLoopSensors', 'coldTemperature')
            print(f"cold temp: {coldtemp}")

            for warning in io.get_warnings():
                print(f'{warning}')

            # Calculate and print the average delta time
            if delta_times:
                avg_delta_time = sum(delta_times) / len(delta_times)
                print(f"Average delta time: {avg_delta_time:.6f} seconds")
                delta_times.clear()  # Clear the list after printing the average
