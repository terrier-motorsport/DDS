# Input object for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from enum import Enum
import can
import cantools
import cantools.database
from data_logger import File
import subprocess

"""
The purpose of this class is to handle data interpreting of a single sensor/input
Input objects are created by the DDS_IO class.
"""

# ===== CONSTANTS =====

CAN_INTERFACE = 'can0'
UART_TX = 2
#...

class SensorProtocol(Enum):
    CAN = 1
    SPI = 2
    I2C = 3
    UART = 4

# ===== Parent class for all inputs =====
class Input:

    def __init__(self, name : str, sensorProtocol : SensorProtocol, logFile : File):
        self.sensorProtocol = sensorProtocol
        self.name = name
        self.logFile = logFile
        pass

    def log_data(self, param_name: str, value):
        # Takes in a file, parameter name & a value
        self.logFile.writeData(param_name, value)
        

    def get_name(self) -> str:
        return self.name

    def get_protocol(self) -> SensorProtocol:
        return self.sensorProtocol

    def get_data():
        print("get_data not overriden propertly in child class.")
        


# This is the i2c library for the pi
import spidev #type: ignore
import time

class SPIDevice(Input):
    
    """
    SPI Input which inherits the Input class
    Each device has its own address & commands that it responds too.
    """

    def __init__(self, name, address, logFile : File):
        
        # Init super (Input class)
        super().__init__(name, SensorProtocol.SPI, logFile=logFile)

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

class CANInterface(Input):

    '''
    CAN Interface which inherits the Input class.
    Each device on the interface can have its own CAN database, which can be added using add_database().
    EX: The MC & AMS are on one CAN Interface. 
    The values from the network are constantly updated into the current_values dictionary
    and can be retrieved by using the .get_data() function
    \nFor UCP, There is only one CAN Interface running on the DDS.
    '''

    # Dictionary which contains the most recent values for all the CAN data
    current_values : dict = {}

    


    def __init__(self, name : str, can_interface : str, database_path : str, logFile : File):
        '''
        Initializer for a CANInterface
        '''

        # Init super (Input class)
        super().__init__(name, SensorProtocol.CAN, logFile=logFile)

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
        This function will first get data from the input assigned to it.
        It will then log it and stuff
        Then it will parse the messages, and add any values to the current_values dictionary
        '''

        # Get data from the CAN Bus
        new_values = self.__fetch_can_data()

        # Log the data that was read
        for key,value in new_values.items():

            # Validating that the object returned actually contains data
            if key == None or value == None:
                key, value = "Error"

            # Write the data to the log file
            super().log_data(key, value)

        # Updates / Adds all the read values to the current_values dict
        for key, value in new_values.items():
            self.current_values[key] = value


    def get_data(self, key):
        '''
        Returns the most recent piece of CAN data associated with the key passed in.
        '''

        # Get the data by querying the current_values dictionary
        reqData = self.current_values.get(key)
        
        # Validating & returning the data
        if reqData != None:
            return reqData
        else:
            print(f"No current valeus found for parameter: {key}")
        

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


    def send_can(self, messageName, signal : dict):
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
            msg = self.can_bus.recv()
        except can.exceptions.CanOperationError:
            self.__start_can_bus()
            msg = self.can_bus.recv()

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

# Example / Testing Code
DEBUG_ENABLED = True

if DEBUG_ENABLED == True:

    logFile = File('MClog')
    canInterface = CANInterface('MC & AMS', 
                                can_interface='can0', 
                                database_path='splash/candatabase/CANDatabaseDTI500v2.dbc', 
                                logFile=logFile)
    canInterface.add_database('splash/candatabase/Orion_CANBUSv4.dbc')

    print(type(canInterface.can_bus))

    mode = input("tx or rx1 (MC) or rx2? (AMS)")

    if (mode == 'tx'):
        for i in range(100):
            canInterface.update()
        print(canInterface.get_data('DigitalIn1'))

        canInterface.send_can('SetDigitalOut', {'DigitialOut1' : 1})

        for i in range(100):
            canInterface.update()
        print(canInterface.get_data('DigitalIn1'))

    elif mode == 'rx1':
        while True:
            canInterface.update()
            print(canInterface.get_data("ERPM"))
            # print(motorController.get_data().get("ERPM"))

    elif mode == 'rx2':
        while True:
            canInterface.update()

            dataToPrint = [
                "Input_Supply_Voltage",
                "DTC_Flags_1",
                "DTC_Flags_2",
                "Pack_CCL",
                "Pack_DCL"
            ]

            for key in dataToPrint:
                print(f"{key}: {canInterface.get_data(key)}")

            

    # print(motorspd.get_protocol())

    canInterface.close_connection()