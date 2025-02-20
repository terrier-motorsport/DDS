import socket
import DDS.DDS.Backend.resources.constants as constants
import time
import csv
import random

class TCPClient:
    # This class enables a TCP Network connection with a TCP Server

    connection = None               # Socket object
    server_ip = constants.pi_IP_ADDRESS
    server_port = constants.router_to_PI_PORT

    connection_active = False

    def __init__(self):
        # Create a TCP/IP Socket
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # AF_INET = IPv4, SOCK_STREAM = TCP

        # Create CSV file and write header if it doesn't exist
        self.csv_file = "sensor_data.csv"
        with open(self.csv_file, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Data"])

    def connect_to_server(self):
        while not self.connection_active:
            try:
                print(f"Attempting to connect to {self.server_ip}:{self.server_port}...")
                server_address = (self.server_ip, self.server_port)

                # Establish a connection with the TCP server at server_address
                self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #creates new socket for each attempt of connection
                self.connection.connect(server_address)
                self.connection_active = True
                print("Connected successfully!")


            except ConnectionRefusedError:
                # If there is no TCP Server at the address, this will run.
                print("Connection failed. Retrying in 5 seconds...")
                time.sleep(5) #Wait 5 seconds before retrying connection

    def send_request(self, request):
        try:
            # Encode the request
            request = request.encode()

            # Send the request to the server
            self.connection.send(request)

            # Wait for the response
            response = self.connection.recv(1024).decode()

            print(f'Data received: {response}') #comment out?
            self.save_to_csv(response)
            return response

        except BrokenPipeError:
            print("Connection lost. Attempting to reconnect...")
            self.connection_active = False
            self.connect_to_server()

    def save_to_csv(self, data):
        try:
            with open(self.csv_file, mode="a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([data])
        except Exception as e:
            print(f"Error saving to CSV: {e}")

    def set_server_address(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port

    def close_connection(self):
        self.connection.close()

class TCPServer:
    # This class enables functionality as a TCP Server

    server_socket = None            # Socket object for server
    server_ip = '192.168.1.2'
    server_port = 65432

    connection_active = False
    connection = None               # Socket object for connection
    client_address = None           # Address for connection

    def __init__(self):

        # Create a TCP/IP socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # AF_INET = IPv4, SOCK_STREAM = TCP


    def start_server(self):
        # Bind the socket to an IP address and port
        self.server_address = (self.server_ip, self.server_port)                 # Address & Port of server
        print(f"attempting to start on {self.server_address}")
        self.server_socket.bind(self.server_address)                             # Patching the socket object to a port
        self.server_socket.listen(1)                                             # Accept incoming connections, refuse any more than (1) connection

        print(f'TCP Server started on {self.server_ip}:{self.server_port}')


    def run(self):
        if not self.connection_active:
            print("Waiting for a connection...")
            self.connection, self.client_address = self.server_socket.accept()
            self.connection_active = True
            print(f"Connection from {self.client_address}")

        try:
            request = self.connection.recv(1024).decode()
            return request  # FIXED: Now returning request data
        except ConnectionResetError:
            print("Client disconnected.")
            self.connection_active = False
            return None  # Prevents crashing

    def read_data(self):
        # Recieves data from socket (up to 1024 bytes).
        #replace with sensor data
        return random.randint(0,100)
    
    def send_response(self, response):

        # Encode strings before sending them
        if isinstance(response, str):
            response = response.encode()
        else:
            response = str(response).encode()
            #print(f"this is an int: {response}")

        #isinstance(response, float)

        # Send the strings
        print(f"Sent: {response}")
        self.connection.sendall(response)


    def set_server_address(self, server_ip, server_port):
        if not self.connection_active:
            self.server_ip = server_ip
            self.server_port = server_port
        else:
            print("Failed to set server address: Server Already Running.")


    def close_server(self):
        self.connection.close()
        self.connection_active = False
        self.connection = None
        self.client_address = None