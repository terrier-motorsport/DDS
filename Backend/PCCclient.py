import time
import threading
import logging
import socket
import json
from typing import Callable, Dict, Any
from Backend.config.config_loader import CONFIG


NotConnectedException = Exception()

"""
PCCClient continuously attempts to establish and maintain a connection to the PCC Server.
It periodically sends requests for sensor data and handles reconnections in case of failure.
"""

class PCCClient:

    def __init__(self, get_data_callable: Callable[[str, str], Any]):
        """
        Initializes the PCCClient by setting up the TCP client connection to the server.
        The server address and port are retrieved from the configuration file.
        """
        self.log = logging.getLogger("PCC_Client")
        self.get_data_callable = get_data_callable  # Function to get parameter data from the DDS_IO
        self.server_ip = CONFIG["network_settings"]["ip"]
        self.server_port = CONFIG["network_settings"]["port"]
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected_to_server = False

    def run(self):
        """
        Starts the client loop in a separate thread.
        This function is responsible for initiating the background process 
        that handles communication with the PCC Server.
        """
        # Start the client loop in a separate thread
        self.thread = threading.Thread(target=self.__run, daemon=True)
        self.thread.start()

    def __run(self):
        """
        Runs in a background thread, continuously requesting sensor data 
        and handling reconnections if the connection is lost.
        """
        
        while True:
            if not self.connected_to_server:
                time.sleep(1)
                self.connected_to_server = self.connect_to_server(self.server_ip, self.server_port)
                continue

            # Get requested device data from server
            requested_device_data = self.get_message_from_server()
            if requested_device_data is None:
                self.connected_to_server = False
                self.log.warning(f"Lost connection to server")
                continue
            
            # Parse the data 
            request_parsed = self.parse_requested_data_from_server(requested_device_data)
            if not isinstance(request_parsed, tuple):
                self.log.error(f"Failed to parse requested data: {requested_device_data}")
                continue
            requested_device, requested_param = request_parsed

            # Fetch device data from DDS_IO
            requested_data = self.get_data_callable(requested_device, requested_data)

            # Send device data back to server
            self.send_message_to_server({"device": requested_device, "parameter": requested_param, "value": requested_data})
        #     except (KeyboardInterrupt, SystemExit):
        #         self.log.info("Closing connection...")
        #         self.close_connection()
        #         break
        #     except Exception as e:
        #         self.log.info(f"Unexpected error: {e}. Retrying in 5 seconds...")
        #         time.sleep(5)
        #         self.connected_to_server = False
        #         self.connect_to_server()

        self.log.critical("Thread stopped running.")


    def send_message_to_server(self, message:dict):
        """
        Sends a message to the TCP server
        """
        try:
            # Encode the request
            message = json.dumps(message).encode()

            # Send the request to the server
            self.socket.send(message)

        except BrokenPipeError:
            self.log.info("Connection lost. Attempting to reconnect...")
            self.connected_to_server = False
            self.connect_to_server()

    def get_message_from_server(self) -> str | None:
        """
        Gets a message from the TCP Server
        """
        try:
            # Gets a message from the TCP Buffer
            message = self.socket.recv(1024).decode() # Valid format for requested data is device|parameter
            self.log.debug(f'Recv msg from PCC: {message}')
            return message
        except ConnectionResetError:
            self.log.error("Client disconnected.")
            self.connected_to_server = False
            return None
        
    def connect_to_server(self, server_ip, server_port) -> bool:
        """
        Tries to connect to the TCP Server.

        Returns:
            bool: whether the connection was successful or not.
        """
        # while not self.connected_to_server:
        #     try:
        #         self.log.info(f"Attempting to connect to {server_ip}:{server_port}...")
        #         # print(f"Attempting to connect to {self.server_ip}:{self.server_port}...")
        #         server_address = (server_ip, server_port)

        #         # Establish a connection with the TCP server at server_address
        #         self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #creates new socket for each attempt of connection
        #         self.connection.connect(server_address)
        #         self.connected_to_server = True
        #         return True

        #     except ConnectionRefusedError:
        #         # If there is no TCP Server at the address, this will run.
        #         return False

        # HOST = 'daring.cwi.nl'    # The remote host
        # PORT = 50007              # The same port as used by the server
        self.log.debug(f"Attempting to connect to PCC on {server_ip}:{server_port}")

        # Establish socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((server_ip, server_port))
        except ConnectionRefusedError as e:
            self.log.debug(f"Attempt Failed: {e}")
            return False
        except ConnectionResetError as e:
            self.log.debug(f"Attempt Failed: {e}")
            return False
        
        self.socket.sendall('START_COMMUNICATION_DDS'.encode())
        data = self.socket.recv(1024).decode()
        if data == "GOOD_TO_START_COMMUNICATION_PCC":
            self.log.info(f"Successfully established connection with PCC on {server_ip}:{server_port}")
            return True
        else:
            self.log.warning(f"PCC Failed Handshake - Received: {data}")
            return False
            
    
    def parse_requested_data_from_server(self, data: str) -> tuple[str, str] | None:
        """
        Parse the requested data string into its device and parameter parts.
        
        Expected format: "device|parameter"
        
        Args:
            data (str): The input string containing the requested data.
            
        Returns:
            tuple[str, str] | None: A tuple (device, parameter) if parsing is successful,
                                    or None if an error occurs.
        
        Error Handling:
            - Raises a ValueError if the string does not contain exactly one '|' character.
            - Raises a ValueError if either the device or parameter is empty.
            - Catches any exceptions, logs an error, and returns None.
        """
        try:
            # Remove leading/trailing whitespace
            data = data.strip()
            
            # Ensure the separator exists
            if '|' not in data:
                raise ValueError("Invalid format: Missing '|' separator.")
            
            # Split the string into parts
            parts = data.split('|')
            
            if len(parts) != 2:
                raise ValueError("Invalid format: Expected exactly one '|' separator.")
            
            device, parameter = parts[0].strip(), parts[1].strip()
            
            if not device or not parameter:
                raise ValueError("Invalid format: Device or parameter is empty.")
            
            return device, parameter

        except Exception as e:
            logging.error(f"Error parsing data from server: {e}")
            return None
            
    def close_connection(self):
        self.socket.close()




if __name__ == '__main__':

    def fetch_device_data(device: str, parameter: str):
        # Replace the following logic with actual data retrieval code
        return {"device": device, "parameter": parameter, "value": 42}
    
    
    # Configure logging for the main process
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(name)s]: %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    # Instantiate and run the PCCClient
    client = PCCClient(fetch_device_data)
    client.run()

    # Keep the main thread alive to allow the client thread to run
    # try:
    while True:
        time.sleep(1)
    # except KeyboardInterrupt:
    #     client.log.info("KeyboardInterrupt received, shutting down.")