# CANBUS Decoding for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)

import cantools
import csv
import logging
from datetime import datetime
from typing import Tuple
from cantools.database import Database

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constants for file paths
DBC_FILE_PATHS = [
    # 'Backend/candatabase/Orion_BMS2_CANBUSv7.dbc',
    'Backend/candatabase/evolve_elcon_uhf_charger.dbc',
    # Add more DBC file paths here
]
INPUT_FILE_PATH = 'Backend/analysis/to_decode/charger_test_2_27_25.txt'
OUTPUT_FILE_PREFIX = 'Backend/analysis/output/log_decoded'

# Load CAN database
db = Database()
for dbc_path in DBC_FILE_PATHS:
    print(f'adding {dbc_path} to database')
    db.add_dbc_file(dbc_path)
# print(db.messages)


def is_extended_id_format(msg: str) -> bool:

    if msg[0] == "t":
        return False
    elif msg[0] == "x":
        return True
    else:
        logging.error(f"MSG ID Format not recognized {msg}")
        return False


# def remove_prefix(msg: str) -> str:
#     """
#     Removes the header from a single message
#     """
#     msg = msg.removeprefix('t')
#     msg = msg.removeprefix('x')
#     return msg

def parse_hex(msg: str) -> Tuple[int, bytes]:
    """
    Converts a log file hex string like 't0A8807D00000000000006F7F' into CAN data.
    
    Args:
        input_str (str): The raw CAN message string.

    Returns:
        Tuple[int, bytes]: A tuple containing the CAN message ID and its data bytes.

    Raises:
        ValueError: If the input string format is incorrect.
    """
    msg_is_extended_id = is_extended_id_format(msg)

    if len(msg) < 10:
        raise ValueError(f"Invalid input format: {msg}")

    try:
        # Extract message from string
        if msg_is_extended_id:
            message_id = int(msg[1:9], 16)  # Convert from hex to int for operations
            data_bytes = bytes.fromhex(msg[10:-4])
        else:
            message_id = msg[1:4]
            data_bytes = bytes.fromhex(msg[5:-4])
        return message_id, data_bytes
    except ValueError as e:
        raise ValueError(f"Failed to parse CAN message: {msg} ({e})")
    

def decode_can_msg(input: str) -> dict:
    """
    Decodes a CAN msg given a string

    Returns
        str: Value
        str: Unit
    """

    message_id, data_bytes = parse_hex(input)
    # print(f'ID: {message_id}, DATA: {data_bytes}')
    try:
        decoded = db.decode_message(message_id, data_bytes)
        formatted_decoded = {}

        for signal_name, signal_value in decoded.items():
            unit = db.get_message_by_frame_id(message_id).get_signal_by_name(signal_name).unit
            key_with_unit = f"{signal_name} ({unit})" if unit else signal_name  # Append unit if available
            formatted_decoded[key_with_unit] = signal_value
            
        return formatted_decoded
    except KeyError as e:
        logging.warning(f'No Message found for ID: {message_id}.')
        return ""


def process_file(input_path: str, output_path: str) -> None:
    """
    Reads a CSV file, decodes CAN messages, and writes the output to a text file.

    Args:
        input_path (str): Path to the input CSV file.
        output_path (str): Path to the output text file.
    """
    try:
        with open(input_path, 'r') as csv_file, open(output_path, 'w') as output_file:
            csv_reader = csv.reader(csv_file)

            for row in csv_reader:
                raw_can_msg = row[0]
                try:
                    decoded = decode_can_msg(raw_can_msg)

                    output_file.write(f"{decoded}\n")
                except ValueError as e:
                    output_file.write(f"Skipping invalid line: {raw_can_msg} ({e})\n")
                    # logging.warning(f"Skipping invalid line: {raw_can_msg} ({e})")
                except KeyError as e:
                    output_file.write(f"Skipping invalid line: {raw_can_msg} ({e})\n")
                    # logging.warning(f"Skipping invalid line: {raw_can_msg} ({e})")
                    
    except FileNotFoundError:
        logging.error(f"File not found: {input_path}")
    except Exception as e:
        logging.error(f"Unexpected error while processing file: {e}")

# Get current timestamp for output file naming
timestamp = datetime.now().strftime("%Y_%m_%d_%H:%M:%S")
output_file_path = f"{OUTPUT_FILE_PREFIX}_{timestamp}.txt"

# Run the processing function
process_file(INPUT_FILE_PATH, output_file_path)
# decode_can_msg('x1806E9F4801CE0064000000000BDF')
# print(decode_can_msg('x1806E5F4801CE0064000000000F04'))
# print(decode_can_msg('x18FF50E58017C000008000000315A'))
# print(decode_can_msg('x1806E9F4801CE0064000000007891'))
