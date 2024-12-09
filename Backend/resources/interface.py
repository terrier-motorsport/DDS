# Input object for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from enum import Enum
import can
import cantools
import cantools.database
from .data_logger import File
import subprocess
import spidev           # type: ignore # This is the SPI library for the pi
import time

"""
The purpose of these classes is to serve as an abstract outline 
of a single interface/device to be inherited by a more specific class if necessary.
EX: the I2C Pressure/Tempature Sensor for the cooling loop.
Objects from classes in this file are created in the DDS_IO class.
"""

# ===== CONSTANTS =====

CAN_INTERFACE = 'can0'
UART_TX = 2
#...

# Enums for types of protocols
class InterfaceProtocol(Enum):
    CAN = 1     # DONE
    SPI = 2     # TODO
    I2C = 3     # TODO
    UART = 4    # Not Needed?

# ===== Parent class for all interfaces =====
class Interface:

    def __init__(self, name : str, sensorProtocol : InterfaceProtocol, logFile : File):
        '''
        Parent class for all interfaces.
        In case you didn't know, this is the initializer.
        '''

        self.sensorProtocol = sensorProtocol
        self.name = name
        self.logFile = logFile
        pass


    def log_data(self, param_name: str, value):
        '''Takes in a file, parameter name & a value'''
        self.logFile.writeData(
            logger_name=self.name, 
            param_name=param_name,
            parameter=value)
        

    def get_name(self) -> str:
        '''Gets the name of the interface'''
        return self.name


    def get_protocol(self) -> InterfaceProtocol:
        '''Gets the protocol of the interface'''
        return self.sensorProtocol


    def get_data(self, key : str):
        '''Gets the data from the interface'''
        print("get_data not overriden propertly in child class.")

    # ===== HELPER METHODS =====

    @staticmethod
    def map_to_percentage(value : int, min_value : int, max_value : int) -> float:
        if value < min_value or value > max_value:
            raise ValueError("Value out of range")
        return (value - min_value) / (max_value - min_value)
    
    @staticmethod
    def percentage_to_map(percentage, min_value : int, max_value : int) -> float:
        if percentage < 0.0 or percentage > 1.0:
            raise ValueError("Percentage out of range")
        return percentage * (max_value - min_value) + min_value
    


# ===== I2CDevice class for DDS' I2C Backend =====
class I2CDevice(Interface):
    
    """
    I2C Device which inherits the Interface class
    Each device has its own address & commands that it responds too.
    It is most likely that each i2c device will have it's own child class with custom decoding function.
    """

    # I2C address of device
    i2c_address : int

    cached_values: dict = {}  # Dictionary to store cached values
    cached_data_timeout_threshold = 2  # Cache timeout in seconds

    last_retrieval_time = None

    def __init__(self, name : str, logFile : File, i2c_address : int):
        
        # Init super (Input class)
        super().__init__(name, InterfaceProtocol.I2C, logFile=logFile)

        # Init cache timeout
        self.last_retrieval_time = time.time()

        # Set I2C address
        self.i2c_address = i2c_address

    
    def update(self):
        pass


    def close_connection(self):
        pass

    def reset_last_retrival_timer(self):
        self.last_retrieval_time = time.time()

    def log_data(self, param_name, value):
        return super().log_data(param_name, value)

    def _fetch_sensor_data(self):
        print("FETCH SENSOR DATA IN I2CDevice IS BEING CALLED. IT SHOULD NOT BE GETTING CALLED.")
        pass

    def _update_cache_timeout(self):
        """
        Clear the cache if the data has not been updated within the timeout threshold.
        """
        current_time = time.time()
        if current_time - self.last_retrieval_time > self.cached_data_timeout_threshold:
            self.cached_values = {}
            print("Cache cleared due to data timeout.")

# ===== SPIDevice class for DDS' SPI Backend =====
class SPIDevice(Interface):
    
    """
    SPI Input which inherits the Input class
    Each device has its own address & commands that it responds too.
    """

    def __init__(self, name, address, logFile : File):
        
        # Init super (Input class)
        super().__init__(name, InterfaceProtocol.SPI, logFile=logFile)

        # Initialize SPI
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)  # (bus 0, device 0)
        self.spi.max_speed_hz = 50000  # Adjust speed as needed

    def _read_sensor(self):
        # Send and receive data
        adc_response = self.spi.xfer2([0x00, 0x00])  # Example request
        return adc_response
    
    def update(self):
        data = self.read_sensor()
        print("Sensor Data:", data)
        time.sleep(1)

    def close_connection(self):
        self.spi.close()

# ===== CANInterface class for DDS' CAN Backend =====
class CANInterface(Interface):

    '''
    CAN Interface which inherits the Input class.
    Each device on the interface can have its own CAN database, which can be added using add_database().
    EX: The MC & AMS are on one CAN Interface. 
    In order for this to function properly, the update() function must be called as often as possible.
    /The values from the network are constantly updated into the current_values dictionary
    and can be retrieved by using the .get_data() function
    \nFor UCP, There is only one CAN Interface running on the DDS.
    '''

    # Dictionary which contains the most recent values for all the CAN data
    cached_values : dict = {}

    # If no CAN data is retrieved within x seconds, the class removes cached data.
    cached_data_timeout_threshold = 2

    
    def __init__(self, name : str, can_interface : str, database_path : str, logFile : File):
        '''
        Initializer for a CANInterface
        '''

        # Init super (Input class)
        super().__init__(name, InterfaceProtocol.CAN, logFile=logFile)

        # Init database path
        self.database_path = database_path

        # Init database & print messages
        self.db = cantools.database.load_file(self.database_path)
        print(f"\n\n\nLOADED THE FOLLOWING CAN MESSAGES: {self.db.messages}")

        # Setup CAN Bus 
        # Can_interface is the interface of the device that the code is running on which can is connected to.
        # interface refers to the type of CAN Bus that is running on that physical interface.
        self.can_bus = can.interface.Bus(can_interface, interface='socketcan')

    
    def update(self):

        '''
        This function will first get data from the interface assigned to it.
        It will then log it and stuff
        Then it will parse the messages, and cache all values
        '''

        # Get data from the CAN Bus
        new_values = self.__fetch_can_data()

        # Check to see if there is null data. If there is, it means that there are no messages to be recieved.
        # Thus, we can end the update poll early.
        if new_values == None:

            # If no new values are discovered, we check to see if the cache has expired.
            self.__update_cache_timeout()
            return
        
        # Update the last retrevial time for the timeout threshold
        self.last_retrieval_time = time.time()  # Update retrieval time

        # Log the data that was read
        for key,value in new_values.items():

            # Write the data to the log file
            super().log_data(key, value)

        # Updates / Adds all the read values to the current_values dict
        for key, value in new_values.items():
            self.cached_values[key] = value


    def get_data(self, key : str):
        '''
        Returns the most recent piece of CAN data associated with the key passed in.
        '''

        # Get the data by querying the current_values dictionary
        reqData = self.cached_values.get(key)
        
        # Validating & returning the data
        if reqData != None:
            return reqData
        else:
            print(f"No current values found for parameter: {key}")
        

    def get_data_raw(self):

        '''
        # This is the same as get_data(), however it doesn't parse the data with a database.
        # Good for troubleshooting CAN messages.
        # Resturns a CAN Message object
        '''

        # Read CAN data
        msg = self.can_bus.recv()

        # Return message
        return msg

        # DEBUG - Ignore. To be removed in future.
        # print(f"{msg}\n ID: {msg.arbitration_id}\n DATA: {msg.data} ")
        # with self.can_bus as bus:
        # for msg in bus: 
        # print(f"{msg}\n{hex(msg.arbitration_id)}")


    def send_can(self, messageName : str, signal : dict):
        """
        # NOTE: THIS CURRENTLY DOESN'T WORK. TO BE IMPLEMENTED WHEN NEEDED.

        Fetches the parameters of the message with the provided name.
        Then fetches the signal of the message with the provided name.
        If you are unsure of signal names, use git_avail_signals(msgName)

        Each message in the database contains up to 64 signals. Look at the database for more info.
        You must encode every signal in a message to send it successfully.
        """

        # Getting the message from the database using name provided
        msg = self.db.get_message_by_name(messageName)
        data = msg.encode({'DigitalOut1' : 1,'DigitalOut2' : 1,'DigitalOut3' : 1,'DigitalOut4' : 1})

        self.can_bus.send(can.Message(arbitration_id=0x0000073a, data=[255,255,255,255,255,255,255,255,]))
        new_msg = can.Message(arbitration_id=msg.frame_id, data=data)
        print(new_msg)
        # self.can_bus.send(new_msg)
        

    def get_avail_signals(self, messageName : str):
        '''Returns the avalable CAN signals from the database with the specified message name'''
        return self.db.get_message_by_name(messageName)


    def old_send_can(self, hex_id, data):

        '''   
        # DEPRICATED - ONLY USE FOR DEBUGGING 
        This sends a CAN message with the extended id format
        Code from https://python-can.readthedocs.io/en/stable/
        '''


        # Create Message object
        msg = can.Message(
            arbitration_id=hex_id, data=data, is_extended_id=True
        )

        # Attempt to send the message & log it
        try:
            self.can_bus.send(msg)
            print(f"Message sent on {self.can_bus.channel_info}: {msg}")
        except can.CanError:
            print("Message NOT sent")


    def close_connection(self):
        '''Closes the connection to the CAN Bus'''
        self.can_bus.shutdown()
        

    def add_database(self, filename : str):
        '''Adds additional database info to the CAN interface from a dbc file'''

        # Add dbc file to database
        self.db.add_dbc_file(filename)
        print(f"\n\n\nLOADED THE FOLLOWING CAN MESSAGES: {self.db.messages}")
        

    def __fetch_can_data(self):
        
        '''
        Gets data from the CAN Bus and tries to parse it.
        Returns a dictionary of parameters and values.
        '''

        # Read a single frame of CAN data
        # If this throws an error, its most likely because the CAN Bus Network on the OS isn't open.
        # It will try to open the network and run the command again.
        try:
            # If a message isn't found within 10ms, the function returns None.
            msg = self.can_bus.recv(timeout=.01)
        except can.exceptions.CanOperationError:
            self.__start_can_bus()
            msg = self.can_bus.recv()

        # Check to see if the request timed out
        if msg == None:
            return None

        # Try to parse the data & return it
        try:
            return self.db.decode_message(msg.arbitration_id, msg.data)
        except KeyError:
            print(f"ERROR: No database entry found for {msg}")
            return {'':''}
    

    def __start_can_bus(self):

        '''
        This is the command to start the can0 network
        In a terminal, all these command would be run with spaces inbetween them
        '''
        print("CAN Bus not found... Attempting to open one.")

        subprocess.run(["sudo", "ip", "link", "set", "can0", "up", "type", "can", "bitrate", "1000000"])
        subprocess.run(["sudo", "ifconfig", "can0", "txqueuelen", "65536"])


    def __update_cache_timeout(self):
        """
        Checks if cached data should be cleared due to timeout, and clears it if it does
        """

        # If the cache is already empty, skip this function
        if self.cached_values == {}:
            return
        
        # Get current time
        current_time = time.time()

        # DEBUG Print statement
        # print(f"Current time: {current_time}\nLast Retrieval: {self.last_retrieval_time}\nCalc Value: {current_time - self.last_retrieval_time}\nCache Threshold: {self.cached_data_timeout_threshold}")

        if current_time - self.last_retrieval_time > self.cached_data_timeout_threshold:
            self.cached_values = {}  # Clear the cache if timeout is exceeded
            print("Cache cleared due to CAN timeout.")
