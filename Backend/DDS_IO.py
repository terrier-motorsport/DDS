# Signal Input/Output for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

import random
from Backend.interface import Interface, CANInterface, InterfaceProtocol
from Backend.data_logger import DataLogger
from Backend.value_monitor import ParameterMonitor, ParameterWarning
from Backend.resources.analog_in import Analog_In, ValueMapper, ExponentialValueMapper
from Backend.resources.ads_1015 import ADS_1015
from Backend.resources.adxl343 import ADXL343
from typing import Union, Dict, List
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
    devices: Dict[str, Interface]



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

        self.__log('Starting Dash Display System Backend...')

        self.__initialize_devices()


    def update(self):
        '''Updates all sensors. Should be called as often as possible.'''

        # Update all enabled devices
        for device_name,device_object in self.devices.items():

            status = device_object.status

            if status is Interface.Status.ACTIVE:
                try:
                    device_object.update()
                    self.__monitor_device_parameters(device_object)
                except Exception as e:
                    self.__log(f'Failed to update {device_name}. {e}')
                    device_object.status = Interface.Status.ERROR
            
            elif status is Interface.Status.ERROR:
                try:
                    device_object.initialize()
                except Exception as e:
                    return

            elif device_object.status is Interface.Status.DISABLED:
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
        if device.status is not Interface.Status.ACTIVE:

            # Log the error
            self.__log(f'Device {device_key} is {device.status.name}. Could not get requested data: {parameter}', DataLogger.LogSeverity.WARNING)

            # Return a value that represents the current stat of the device
            if device.status is Interface.Status.DISABLED:
                return 'DIS'
            elif device.status is Interface.Status.ERROR:
                return 'ERR'
            elif device.status is Interface.Status.NOT_INITIALIZED:
                return 'NIN'
        
        # Fetch data from device
        data = device.get_data(parameter)

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
        for device_name, device in self.devices.items():
            device_names.append(device_name)
        return device_names
    

    def get_device_parameters(self, param_name: str) -> List[str]:
        '''
        Returns a list of parameters for a specified device.
        '''
        device_params = []
        for param_name in self.devices[param_name].get_all_param_names():
            device_params.append(param_name)
        return device_params


    def __get_device(self, deviceKey : str) -> Interface:
        ''' Gets a device at a specified key.
        This may return a None value.'''

        return self.devices.get(deviceKey)
    

    def __initialize_devices(self):

        '''Initializes all sensors & interfaces for the DDS'''

        self.__log('Initializing IO Devices')

        # Create empty devices list
        self.devices = {}


        # ===== Init CAN =====
        if self.CAN_ENABLED:
            self.__initialize_CAN()

        else:
            # CANBus Disabled
            self.__log('CAN Disabled: Skipping initialization.', DataLogger.LogSeverity.WARNING)


        # ===== Init i2c ===== 
        if self.I2C_ENABLED:
            self.__initialize_i2c()

        else:
            # i2c Disabled
            self.__log('i2c Disabled: Skipping initialization.', DataLogger.LogSeverity.WARNING)

        # Update the IO one time to wake all interface (like ADS 1015)
        self.update()

        # Add dummy devices if we are in demo mode.
        if self.demo_mode:
            self.devices = {
                "Mike": Interface('Mike', InterfaceProtocol.I2C, self.log),
                "Anna": Interface('Anna', InterfaceProtocol.CAN, self.log)
            }
            for device_name, device in self.devices.items():
                if device_name == "Mike":
                    device.cached_values["sample_data One (1)"] = 203949.1324
                    device.cached_values["Two"] = "i like chocolate chip cookies"
                    device.cached_values["thre three threee"] = "i HATE chocolate chip cookies which dont have chocolate chips"
                if device_name == "Anna":
                    device.cached_values["other signal"] = "yum i love chocolate chip cookies"
                device.change_status(Interface.Status.ACTIVE)

        # Log that initialization has finished
        self.__log('All devices have been initialized. Listing devices.')
        
        for device_name, device_object in self.devices.items():
            self.__log(f'{device_name}: {device_object.status.name}')


    def __initialize_i2c(self):

        '''Initializes the i2c Bus & all the devices on it.'''

        self.__log(f'Starting i2c bus on {self.I2C_BUS}')

        # ===== Initalize i2c Bus ===== 
        try:
            self.i2c_bus = smbus2.SMBus(bus=self.I2C_BUS)
        except Exception as e:
            self.__failed_to_init_protocol(InterfaceProtocol.I2C, e)
            return


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
        fixed_resistor = 1000
        NTC_M12_value_mapper = ExponentialValueMapper(
            resistance_values=resistance_values,
            output_values=temperature_values,
            supply_voltage=supply_voltage,
            fixed_resistor=fixed_resistor
        )

        coolingLoopDeviceName = 'coolingLoopSensors'

        coolingLoopDevice = ADS_1015(coolingLoopDeviceName, logger=self.log, i2c_bus=self.i2c_bus, inputs = [
            Analog_In('hotPressure', 'bar', mapper=M3200_value_mapper, tolerance=0.1),           #ADC1(A0)
            Analog_In('hotTemperature', '°C', mapper=NTC_M12_value_mapper, tolerance=0.1),       #ADC1(A1)
            Analog_In('coldPressure', 'bar', mapper=M3200_value_mapper, tolerance=0.1),          #ADC1(A2)
            Analog_In('coldTemperature', '°C', mapper=NTC_M12_value_mapper, tolerance=0.1)       #ADC1(A3)
        ])

        self.__safe_initialize_device(coolingLoopDevice)

        # ===== Init accelerometer ===== 

        accelerometerDeviceName = 'frontAccelerometer'
        accelerometerI2CAddr = 0x1D

        accelerometer = ADXL343(accelerometerDeviceName, self.log, self.i2c_bus, accelerometerI2CAddr)
        self.__safe_initialize_device(accelerometer)

        # ===== FINISHED ===== 
        self.__log('Finished initializing all i2c devices!')
    

    def __initialize_CAN(self):
        """
        Initializes the CANBus interface and sets up connected devices.
        """

        self.__log(f"Starting CAN bus on {self.CAN_BUS}")

        # Step 1: Attempt to initialize the CAN bus
        
        try:
            self.can_bus = can.interface.Bus(self.CAN_BUS, interface="socketcan")
        except OSError as e:
            # Log failure and disable the CAN interface if network setup fails
            self.__failed_to_init_protocol(InterfaceProtocol.CAN, e)
            return

        # Step 3: Set up the CAN interface with the database
        canDevice = CANInterface(
            name="MC & AMS", 
            can_bus=self.can_bus, 
            database_path="Backend/candatabase/CANDatabaseDTI500v2.dbc", 
            logger=self.log
        )
        # Add the AMS-specific DBC file to the CAN interface
        canDevice.add_database("Backend/candatabase/Orion_CANBUSv4.dbc")

        # Step 4: Initialize the CAN device safely
        self.__safe_initialize_device(canDevice)

        # Step 5: Log completion of CAN initialization
        self.__log("Finished initializing all CAN devices!")

    
    def __safe_initialize_device(self, device: Interface) -> bool:
        """
        Safely initialize an instance of a Interface child class, and add it to the devices dict.
        
        Parameters:
            cls (Type[Interface]): The child class to instantiate.
            *args: Positional arguments for the child class constructor.
            **kwargs: Keyword arguments for the child class constructor.
        
        Returns:
            bool: The result of the device being successfully initialized
        """

        # Add the device to the devices dict:
        self.devices[device.name] = device

        try:
            # Attempt to initalize the device
            device.initialize()

            # Check if the device can read data
            device.update()

        except Exception as e:
            self.__failed_to_init_device(device=device, exception=e)
            return False
        return True      


    def __failed_to_init_device(self, device: Interface, exception: Exception):
        '''
        This logs an error when a device (ex. MC) is unable to be intialized.
        This is usually caused by hardware being configured incorrectly.
        The device is set to the ERROR state and the DDS_IO will continously attempt to inialize the device.
        '''

        # Log the error
        self.__log(f'{device.get_protocol().name} {device.name} Initialization Error: {exception}', DataLogger.LogSeverity.CRITICAL)

        if isinstance(exception, OSError):
            if exception.errno == 121:
                self.__log(f'Make sure {device.name} is properly wired and shows up on i2cdetect!')

        # Mark the device as having an error
        self.devices[device.name].status = Interface.Status.ERROR


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

    
    def __monitor_device_parameters(self, device: Interface):
        """
        Monitors the parameters of a given device and checks if their values are within the defined limits.

        Parameters:
            device (Interface): The device whose parameters are to be monitored.

        This function retrieves all parameter names from the device's cached values and checks each parameter's value
        against the defined limits using the ParameterMonitor. If a parameter value is out of range, a warning is raised.
        """
        param_names = device.get_all_param_names()

        for param_name in param_names:
            self.parameter_monitor.check_value(param_name, self.get_device_data(device.name, param_name))

    
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
