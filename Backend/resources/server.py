"""
THIS EXISTS FOR REFERENCE ONLY; SHOULD NOT BE RUN.
"""

# raise NotImplementedError()
# import Backend.resources.netcode as net
# import random

# socket.socket()


import socket
import time

HOST = ''                 # Symbolic name meaning all available interfaces
PORT = 8765              # Arbitrary non-privileged port

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    try:
        s.bind((HOST, PORT))
        s.listen(1)
        conn, addr = s.accept()
        with conn:
            print('Connected by', addr)
            conn.sendall("GOOD_TO_START_COMMUNICATION_PCC".encode())
            while True:
                data = conn.recv(1024)
                if not data: break
                conn.sendall("coolingLoopSensors1|hotTemp".encode())
                time.sleep(0.1)
    except KeyboardInterrupt:
        s.close()


# NETWORK CONSTANTS
# pi_IP_ADDRESS = "192.168.0.4"
# # router_IP_ADRESS = "128.197.50.90"
# router_to_PI_PORT = 8765



# piServer = net.TCPServer() # Start the server

# piServer.set_server_address(pi_IP_ADDRESS, router_to_PI_PORT)
# piServer.start_server()

# # ---------------RESPONSE TABLE------------------
# def get_sensor_data():
#     return str(random.randint(0, 100))  # Replace with real sensor reading

# response_table = {
#     "GET_SENSOR_DATA": get_sensor_data
# }

# # ---------------SERVER LOOP------------------
# class Server():

#     def __init__():
#         pass

#     def run():
#         '''
#         Starts an infinite loop of recieving & sending requests
#         '''
#         while True:
#             try:
#                 request = piServer.run()

#                 if request:
#                     print(f"Received Message: {request}")
#                     response = response_table.get(request, lambda: "Invalid request")()
#                     piServer.send_response(response)

#                 else:
#                     print("No request received.")

#             except KeyboardInterrupt:
#                 print("Shutting down server")
#                 piServer.close_server()
#                 break
            
#             except Exception as e:
#                 print(f"Server error: {e}. Continuing")

#         print("Server Closed")
