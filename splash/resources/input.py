# Input object for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

from enum import Enum
import can # type: ignore
import time
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
    database_path = 'splash/candatabase/file.dbc'

    def __init__(self, name, id):
        # Init super (Input class)
        super().__init__(name, SensorProtocol.CAN)

        # Assign ID of CAN signal
        self.can_id = id

        # Init database & print messages
        self.db = cantools.database.load_file(self.database_path)
        # print(self.can_database.messages)

        # Setup CANBus interface
        self.can_bus = can.interface.Bus(CAN_INTERFACE, interface='socketcan')



    def get_data(self):
        # This is where the pi would fetch data

        # Read CAN data
        msg = self.can_bus.recv()

        # DEBUG
        print(f"{msg}\n ID: {msg.arbitration_id}\n DATA: {msg.data} ")


        # Note: msg.arbitration_id contains the integer value of the hex ID
        # Thats all good and fun, but for some reason when converted to a hex ID
        # Which is needed in order to parse the data, there is a 3a appended to every message.
        # EX: a message that should be coming from 0x21 is recieved as 0x213a
        # My current solution is to just ignore the first and last two characters then
        # pass that into the database. This may require more work in the future.

        # hex_id = (hex(msg.arbitration_id))
        # real_id = hex_id[2:4]

        # #D  EBUG
        # print(real_id)

        # Get the decoded message
        print(self.db.decode_message(msg.arbitration_id, msg.data))

        # print(message.arbitration_id, message.data, message.timestamp)
    
        # with self.can_bus as bus:
        #     for msg in bus: 
        #         print(msg)
        #         print(self.db.decode_message(msg.arbitration_id, msg.data))



    def get_data_raw(self):
        # This is where the pi would fetch data

        # Read CAN data
        # msg = self.can_bus.recv()

        # print(f"{msg}\n ID: {msg.arbitration_id}\n DATA: {msg.data} ")

        # print(msg)

        # print(message.arbitration_id, message.data, message.timestamp)
    
        with self.can_bus as bus:
            for msg in bus: 
                print(f"{msg}\n{hex(msg.arbitration_id)}")
        #         print(self.db.decode_message(msg.arbitration_id, msg.data))

    
    def send_can(self):
        # Code from https://python-can.readthedocs.io/en/stable/
        """Sends a single message."""

        # this uses the default configuration (for example from the config file)
        # see https://python-can.readthedocs.io/en/stable/configuration.html
        # with self.can_bus as bus:
            # Using specific buses works similar:
            # bus = can.interface.Bus(interface='socketcan', channel='can0', bitrate=1000000)
            # bus = can.Bus(interface='pcan', channel='PCAN_USBBUS1', bitrate=250000)
            # bus = can.Bus(interface='ixxat', channel=0, bitrate=250000)
            # bus = can.Bus(interface='vector', app_name='CANalyzer', channel=0, bitrate=250000)
            # ...

        msg = can.Message(
            arbitration_id=0xC0FFEE, data=[0, 25, 0, 1, 3, 1, 4, 1], is_extended_id=True
        )

        try:
            self.can_bus.send(msg)
            print(f"Message sent on {self.can_bus.channel_info}: {msg}")
        except can.CanError:
            print("Message NOT sent")
        
        
    



motorspd = CANInput('motor speed', '0x2a')

mode = input("tx or rx1 or rx2?")

if (mode == 'tx'):
    while True:
        motorspd.send_can() 
        time.sleep(0.001)
elif mode == 'rx1':
    motorspd.get_data()

elif mode == 'rx2':
    motorspd.get_data_raw()

# print(motorspd.get_protocol())