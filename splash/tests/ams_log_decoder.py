# CANBUS Decoding for the Orion BMS2 (AMS) for Terrier Motorsport's DDS
    # Code by Jackson Justus (jackjust@bu.edu)


import cantools
import cantools.database
import csv
from datetime import datetime

db = cantools.database.load_file('splash/candatabase/Orion_CANBUSv3.dbc')


def parse_string(input_str):
    '''
    Takes a string from a log file that looks like t0A8807D00000000000006F7F
    and turns it into readable CAN data such as ('0x0A8', b'\x07\xd0\x00\x00\x00\x00\x00\x00')
    '''

    # Ensure input starts with 't' and is the correct length
    if not input_str.startswith('t') or len(input_str) < 10:
        raise ValueError("Invalid input format")

    # Extract ID (characters 1-4) and Data (characters 4 to the second-to-last)
    message_id = input_str[1:4]
    data_part = input_str[5:-4]  # Excluding the last two checksum characters

    # Convert the message ID to decimal
    message_id_hex = f"0x{message_id}"
    message_id_decimal = int(message_id_hex, 16)

    # Convert the data part to bytes
    data_bytes = bytes.fromhex(data_part)

    # Format the output as a tuple
    result = (message_id_decimal, data_bytes)
    return result


def process_csv(file_path, output_file_path):
    with open(file_path, 'r') as csv_file, open(output_file_path, 'w') as output_file:
        csv_reader = csv.reader(csv_file)
        for row in csv_reader:
            input_str = row[0]
            try:
                result = parse_string(input_str)
                decoded = db.decode_message(result[0], result[1])
                # Write the result to the output file
                output_file.write(f"{decoded}\n")
            except ValueError as e:
                output_file.write(f"Skipping invalid line: {input_str} ({e})\n")


# Get current date and time
now = datetime.now()

# Format it as a string
formatted_now = now.strftime("%Y_%m_%d_%H:%M:%S")

# Example usage
csv_file_path = 'splash/tests/data.csv'  # Replace with your CSV file path
output_file_path = 'splash/tests/output/AMS_LOG_DECODED' + formatted_now + '.txt'  # Replace with your desired output TXT file path
process_csv(csv_file_path, output_file_path)


# input_str = "t0A8807D00000000000006F7F"
# result = parse_string(input_str)
# print(result)
# print(db.decode_message(result[0],result[1]))

# print(db.decode_message(0x0A8, b'\x07\xD0\x00\x00\x00\x00\x00\x00'))
# print(db.decode_message(0x6B1, b'\x00\xC8\x00\x07\x18\x18\x00\xB8'))
# print(db)