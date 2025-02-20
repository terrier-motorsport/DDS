import resources.netcode2 as net
import time
import random
import DDS.DDS.Backend.resources.constants as constants

piServer = net.TCPServer() # Start the server
piServer.set_server_address(constants.pi_IP_ADDRESS, constants.router_to_PI_PORT)
piServer.start_server()

def get_sensor_data():
    return str(random.randint(0, 100))  # Replace with real sensor reading

response_table = {
    "GET_SENSOR_DATA": get_sensor_data
}

# ---------------SERVER LOOP------------------
while True:
    try:
        request = piServer.run()

        if request:
            print(f"Received request: {request}")
            response = response_table.get(request, lambda: "Invalid request")()
            piServer.send_response(response)

        else:
            print("No request received.")

    except KeyboardInterrupt:
        print("Shutting down server")
        piServer.close_server()
        break
    
    except Exception as e:
        print(f"Server error: {e}. Continuing")

print("Server Closed")
