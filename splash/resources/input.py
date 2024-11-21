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
        

# CAN Input which inherits the Input class
class CANInput(Input):

    can_id = ''
    can_database = ''

    def __init__(self, name, id, database_path):
        # Init super (Input class)
        super().__init__(name, SensorProtocol.CAN)

        # Assign ID of CAN signal
        self.can_id = id

        # Init database & print messages
        self.can_database = cantools.database.load_file(database_path)
        print(self.can_database.messages)

        # Setup CANBus interface
        self.can_bus = can.interface.Bus(CAN_INTERFACE, bustype='socketcan')



    def get_data(self):
        # This is where the pi would fetch data

        # Read CAN data
        message = self.can_bus.recv()

        print(message.arbitration_id, message.data, message.timestamp)
    
        for msg in self.can_bus:
            print(self.can_database.decode_message(msg.arbitration_id, msg.data))
        
    
    


motorspd = CANInput('motor speed', '0x2a', 'splash/candatabase/file.dbc')

print(motorspd.get_protocol())

motorspd.get_data()