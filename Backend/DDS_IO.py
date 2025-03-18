# Signal Input/Output for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

import random
import Backend.config.device_config
from Backend.config.config_loader import CONFIG
from Backend.interface import Interface, CANInterface, I2CInterface, InterfaceProtocol
from Backend.device import Device
from Backend.data_logger import DataLogger
from Backend.value_monitor import ParameterMonitor, ParameterWarning
from Backend.PCCclient import PCCClient
from Backend.resources.analog_in import Analog_In, ValueMapper, ExponentialValueMapper
from Backend.resources.ads_1015 import ADS_1015
from Backend.resources.mpu6050 import MPU_6050_x3
from Backend.resources.dtihv500 import DTI_HV_500
from Backend.resources.orionbms2 import Orion_BMS_2
from Backend.resources.elconuhf import Elcon_UHF
from typing import Union, Dict, List



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
        # Set up fancy things
        self.log = DataLogger('DDS_Log', baseDirectoryPath=CONFIG["log_settings"]["external_storage_path"])
        self.parameter_monitor = ParameterMonitor('Backend/config/valuelimits.json5', self.log)
        self.pcc = PCCClient(get_data_callable=lambda device, param: self.get_device_data(device, param, caller="PCC Client"))
        self.pcc.run()
        
        # Set up not fancy things
        self.debug = debug
        self.demo_mode = demo_mode
        self.interfaces = {}

        self.__log('Starting Dash Display System Backend...')
        self.__initialize_io()


    def update(self):
        '''Updates all Interfaces. Should be called as often as possible.'''

        # Update all enabled devices
        for interface_name, interface_object in self.interfaces.items():

            status = interface_object.status

            if status is Interface.InterfaceStatus.ACTIVE:
                try:
                    interface_object.update()
                except Exception as e:
                    self.__log(f'Failed to update {interface_name}. {e}')
                    interface_object.status = Interface.InterfaceStatus.ERROR
            
            elif status is Interface.InterfaceStatus.ERROR:
                # TEMPORARILY DISABLED FOR TESTING PURPOSES.
                # try:
                #     interface_object.initialize()
                # except Exception as e:
                #     return
                pass

            elif interface_object.status is Interface.InterfaceStatus.DISABLED:
                return


    def get_device_data(self, device_key: str, param_key: str, caller: str="DDS_IO") -> Union[str, float, int, None]:
        '''
        Gets a single parameter from a specified device.

        Parameters:
            device_key `(str)`: The key of the device with the requested parameter
            param_key `(str)`: The key of the parameter that you are requesting
            caller `(str)`: The name of the entity calling this function. Used for logging purposes.
        '''

        # Return a random value if we are in demo mode.
        if self.demo_mode:
            return random.random() * 100
        
        # 1) Get the device at the specified key by checking each interface for it.
        device: Device = None
        for name, interface in self.interfaces.items():
            if interface.devices.get(device_key) is not None:
                device = interface.devices.get(device_key)
                break
            # If the device is None, we can return early
        if device is None:
            # Log the mistake and return.
            self.__log(f'Device {device_key} not found. (Data Req: {param_key})', DataLogger.LogSeverity.DEBUG, caller)
            return "UKNDEV"
        

        # 2) If the device is not active, we can return early
        if device.status is not Device.DeviceStatus.ACTIVE:

            # Log the warning
            self.__log(f'Device {device_key} is {device.status.name}. Could not get requested data: {param_key}', DataLogger.LogSeverity.DEBUG)

            # Return a value that represents the current state of the device
            if device.status is Device.DeviceStatus.DISABLED:
                return 'DISBLD'
            elif device.status is Device.DeviceStatus.ERROR:
                return 'ERROR'
            elif device.status is Device.DeviceStatus.NOT_INITIALIZED:
                return 'NO_INIT'
              
        # 3) Fetch data from device
        data = device.get_data(param_key)

        
        # 4) If the data is None, we can return early
        if data is None:
            return "NO_DATA"

        
        # 5) Return the data
        return data
    

    def get_warnings(self) -> List[str]:
        '''Returns a list of active warnings''' 
        warnings = self.parameter_monitor.get_warnings_as_str()
        # print(f'{warnings}, {self.demo_mode}')

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
        for interface_name, interface in self.interfaces.items():
            for device_name, device in interface.devices.items():
                device_names.append(device_name)
        return device_names
    

    def get_device_parameters(self, device_name: str) -> List[str]:
        """
        Returns a list of parameters for a specified device.

        Args:
            device_name (str): The name of the device for which parameters are requested.

        Returns:
            List[str]: A list of parameter names for the specified device. 
                    If the device is not found, an empty list is returned.
        """
        for interface_name, interface in self.interfaces.items():
            if device_name in interface.devices:
                device = interface.devices[device_name]
                return device.get_all_param_names()
        
        # If no matching device is found, return an empty list
        self.__log(f"Device '{device_name}' not found when fetching parameters.", DataLogger.LogSeverity.DEBUG)
        return []
    

    def __initialize_io(self):

        '''Initializes all sensors & interfaces for the DDS'''
        self.__log('Initializing IO Devices')


        # ===== Init CAN =====
        if self.CAN_ENABLED:
            self.__log(f"Starting CANInterface on {self.CAN_BUS}")
            canInterface = CANInterface(
                name='CANInterface',
                can_channel=self.CAN_BUS,
                devices=[
                    Orion_BMS_2('Backend/candatabase/Orion_BMS2_CANBUSv7.dbc', self.log),
                    DTI_HV_500('Backend/candatabase/DTI_HV_500_CANBUSv3.dbc', self.log),
                    Elcon_UHF('Backend/candatabase/evolve_elcon_uhf_charger.dbc', self.log)
                ],
                logger=self.log,
                parameter_monitor=self.parameter_monitor
            )
            self.__safe_initialize_interface(canInterface)
            self.__log("Finished initializing all CAN devices!")
        else:
            # CAN Disabled
            self.__log('CAN Disabled: Skipping initialization.', DataLogger.LogSeverity.WARNING)


        # ===== Init i2c ===== 
        if self.I2C_ENABLED:
            self.__log(f'Starting I2CInterface bus on {self.I2C_BUS}')
            i2cInterface = I2CInterface(
                'I2CInterface',
                i2c_channel=self.I2C_BUS,
                devices=[
                    # See the referenced package for details about devices.
                    Backend.config.device_config.define_ADC1(self.log),
                    Backend.config.device_config.define_ADC2(self.log),
                    # TODO: Implement
                    Backend.config.device_config.define_MPU_6050(self.log),
                    # Backend.config.device_config.define_top_MPU_6050(self.log),
                    # Backend.config.device_config.define_wheel_MPU_6050(self.log),
                ],
                logger=self.log,
                parameter_monitor=self.parameter_monitor
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
            # THIS IS ALL GARBO. NEED TO FIX
            pass
            # self.interfaces = {
            #     "Mike": Interface('Mike', InterfaceProtocol.I2C, self.log, self.parameter_monitor),
            #     "Anna": Interface('Anna', InterfaceProtocol.CAN, self.log)
            # }
            # for device_name, device in self.interfaces.items():
            #     if device_name == "Mike":
            #         device.cached_values["sample_data One (1)"] = 203949.1324
            #         device.cached_values["Two"] = "i like chocolate chip cookies"
            #         device.cached_values["thre three threee"] = "i HATE chocolate chip cookies which dont have chocolate chips"
            #     if device_name == "Anna":
            #         device.cached_values["other signal"] = "yum i love chocolate chip cookies"
            #     device.change_status(Interface.InterfaceStatus.ACTIVE)


        # Log that initialization has finished
        self.__log('All devices have been initialized. Listing devices.')
        
        for interface_name, interface_object in self.interfaces.items():
            self.__log(f'{interface_name}: {interface_object.status.name}')
            for device_name, device_object in interface_object.devices.items():
                self.__log(f'   {device_name}: {device_object.status.name}')


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
        It also creates a warning that the device has failed.

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

        # Create warning
        self.parameter_monitor.create_warning(ParameterWarning.standardMsg(
            'StatusWarning',
            name=f"{interface.name}",
            status=f"{interface.status.name}"
        ))

    
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

            # Print every parameter
            for interface_name, interface_obj in io.interfaces.items():
                for device_name, device_obj in interface_obj.devices.items():
                    param_names = device_obj.get_all_param_names()
                    for param in param_names:
                        data = io.get_device_data(device_name, param, "TestCode")
                        if data != "NO_DATA":
                            print(f'{device_name}.{param}: {data}')

            # Get and print the data
            # hotpressure = io.get_device_data('coolingLoopSensors1', 'hotPressure')
            # print(f"hot pressure: {hotpressure}")

            # coldpressure = io.get_device_data('coolingLoopSensors1', 'coldPressure')
            # print(f"cold pressure: {coldpressure}")

            # hottemp = io.get_device_data('coolingLoopSensors1', 'hotTemperature')
            # print(f"hot temp: {hottemp}")

            # coldtemp = io.get_device_data('coolingLoopSensors1', 'coldTemperature')
            # print(f"cold temp: {coldtemp}")

            # for warning in io.get_warnings():
            #     print(f'{warning}')

            # Calculate and print the average delta time
            if delta_times:
                avg_delta_time = sum(delta_times) / len(delta_times)
                print(f"Average delta time: {avg_delta_time:.6f} seconds")
                delta_times.clear()  # Clear the list after printing the average
