import socket
import time
import csv
import json
import logging
# log = logging.getLogger('Netcode')
"""
The purpose of this file is to transmit telemetry data from the DDS to a Pit Control Center.
"""

# class TCPClient:
    
#     # This class enables a TCP Network connection with a TCP Server

#     connection: socket.socket              # Socket object
#     connection_active = False

#     def __init__(self, server_ip: str, server_port: int):







# class TCPServer:
#     # This class enables functionality as a TCP Server

#     server_socket = None            # Socket object for server
#     server_ip = '192.168.1.2'
#     server_port = 65432

#     connection_active = False
#     connection = None               # Socket object for connection
#     client_address = None           # Address for connection

#     def __init__(self):

#         # Create a TCP/IP socket
#         self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # AF_INET = IPv4, SOCK_STREAM = TCP


#     def start_server(self):
#         # Bind the socket to an IP address and port
#         self.server_address = (self.server_ip, self.server_port)                 # Address & Port of server
#         print(f"attempting to start on {self.server_address}")
#         self.server_socket.bind(self.server_address)                             # Patching the socket object to a port
#         self.server_socket.listen(1)                                             # Accept incoming connections, refuse any more than (1) connection

#         print(f'TCP Server started on {self.server_ip}:{self.server_port}')


#     def run(self):
        # if not self.connection_active:
        #     print("Waiting for a connection...")
        #     self.connection, self.client_address = self.server_socket.accept()
        #     self.connection_active = True
        #     print(f"Connection from {self.client_address}")

        # try:
        #     request = self.connection.recv(1024).decode()
        #     return request  # FIXED: Now returning request data
        # except ConnectionResetError:
        #     print("Client disconnected.")
        #     self.connection_active = False
        #     return None  # Prevents crashing
        
    
    # def send_response(self, response):

    #     # Encode strings before sending them
    #     if isinstance(response, str):
    #         response = response.encode()
    #     else:
    #         response = str(response).encode()
    #         #print(f"this is an int: {response}")

    #     #isinstance(response, float)

    #     # Send the strings
    #     print(f"Sent: {response}")
    #     self.connection.sendall(response)


#     def set_server_address(self, server_ip, server_port):
#         if not self.connection_active:
#             self.server_ip = server_ip
#             self.server_port = server_port
#         else:
#             print("Failed to set server address: Server Already Running.")


#     def close_server(self):
#         self.connection.close()
#         self.connection_active = False
#         self.connection = None
#         self.client_address = None