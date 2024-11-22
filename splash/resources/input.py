# Input object for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from enum import Enum
import can
import cantools
import cantools.database

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

    def __init__(self, name, sensorProtocol):
        self.sensorProtocol = sensorProtocol
        self.name = name
        pass

    def get_protocol(self):
        return self.sensorProtocol

    def get_data():
        print("get_data not overriden propertly in child class.")
        

class CANDevice(Input):

    '''
    # CAN Input which inherits the Input class
    # Each device can have its own CAN database & physical CAN interface
    # EX: The MC would be one CAN device and the AMS would be another.
    '''

    # Dictionary which contains the most recent values for all the CAN data
    current_values = {}

    def __init__(self, name, can_interface, database_path):
        # Init super (Input class)
        super().__init__(name, SensorProtocol.CAN)

        # Init database path
        self.database_path = database_path

        # Init database & print messages
        self.db = cantools.database.load_file(self.database_path)
        print(self.can_database.messages)

        # Setup CAN Bus 
        # Can_interface is the interface of the device that the code is running on which can is connected to.
        # interface refers to the type of CAN Bus that is running on that physical interface.
        self.can_bus = can.interface.Bus(can_interface, interface='socketcan')

    def update(self):

        '''
        This function will first poll the CAN Bus for messages
        Then it will parse the messages, and add any values to the current_values dictionary
        '''

        new_values = self.get_data()

        # new_values
        pass

    def get_data(self):

        '''
        # Gets data from the CAN Bus and tries to parse it.
        # Returns a dictionary of parameters and values.
        '''

        # Read a single frame of CAN data
        msg = self.can_bus.recv()

        # DEBUG
        # print(f"INCOMING RAW MSG: {msg}\n ID: {msg.arbitration_id}\n DATA: {msg.data} ")

        # Try to parse the data & return it
        try:
            return self.db.decode_message(msg.arbitration_id, msg.data).get
        except KeyError:
            print(f"ERROR: No database entry found for {msg}")
            return None
        

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
        
    



