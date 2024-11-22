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

    def __init__(self, name, sensorProtocol, logFile : File):
        self.sensorProtocol = sensorProtocol
        self.name = name
        self.logFile = logFile
        pass

    def log_data(self, param_name: str, value):
        # Takes in a file, parameter name & a value
        self.logFile.writeData(param_name, value)
        



    def get_protocol(self):
        return self.sensorProtocol

    def _fetch_can_data():
        print("get_data not overriden propertly in child class.")
        

class CANDevice(Input):

    '''
    # CAN Input which inherits the Input class
    # Each device can have its own CAN database & physical CAN interface
    # EX: The MC would be one CAN device and the AMS would be another.
    '''

    # Dictionary which contains the most recent values for all the CAN data
    current_values = {}

    def __init__(self, name, can_interface, database_path, logFile : File):
        # Init super (Input class)
        super().__init__(name, SensorProtocol.CAN, logFile=logFile)

        # Init database path
        self.database_path = database_path

        # Init database & print messages
        self.db = cantools.database.load_file(self.database_path)
        print(self.db.messages)

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
        new_values = self._fetch_can_data()

        print(new_values)

        # Log the data that was read
        for key,value in new_values.items():
            super().log_data(key, value)

        # Updates / Adds all the read values to the current_values dict
        for key, value in new_values:
            self.current_values[key] = value

    def get_data(self, key):
        return self.current_values.get(key)
        
        

    def _fetch_can_data(self):

        '''
        # Gets data from the CAN Bus and tries to parse it.
        # Returns a dictionary of parameters and values.
        '''

        # Read a single frame of CAN data
        # If this throws an error, its most likely because the CAN Bus Network on the OS isn't open.
        # It will try to open the network and run the command again.
        try:
            msg = self.can_bus.recv()
        except can.exceptions.CanOperationError:
            self.start_can_bus()
            msg = self.can_bus.recv()

        # DEBUG
        # print(f"INCOMING RAW MSG: {msg}\n ID: {msg.arbitration_id}\n DATA: {msg.data} ")

        # Try to parse the data & return it
        try:
            return self.db.decode_message(msg.arbitration_id, msg.data)
        except KeyError:
            print(f"ERROR: No database entry found for {msg}")
            return {'':''}
        

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


    def send_can(self, hex_id, data):

        '''    
        # This sends a CAN message with the extended id format
        # Code from https://python-can.readthedocs.io/en/stable/
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
        # This closes the connection to the CAN Bus
        self.can_bus.shutdown()
        
    
    def start_can_bus(self):
        # This is the command to start the can0 network
        # In a terminal, all these command would be run with spaces inbetween them
        subprocess.run(["sudo", "ip", "link", "set", "can0", "up", "type", "can", "bitrate", "1000000"])
        subprocess.run(["sudo", "ifconfig", "can0", "txqueuelen", "65536"])






import time


logFile = File('MClog')
motorController = CANDevice('DTI HV 500 (MC)', can_interface='can0', database_path='splash/candatabase/CANDatabaseDTI500.dbc', logFile=logFile)


mode = input("tx or rx1 or rx2?")

if (mode == 'tx'):
    while True:
        motorController.send_can() 
        time.sleep(0.001)
elif mode == 'rx1':
    while True:
        motorController.update()
        print(motorController.get_data("ERPM"))
        # print(motorController.get_data().get("ERPM"))

elif mode == 'rx2':
    motorController.get_data_raw()

# print(motorspd.get_protocol())

motorController.close_connection()