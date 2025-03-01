import resources.netcode2 as net
import random

# NETWORK CONSTANTS
pi_IP_ADDRESS = "192.168.0.138"
router_IP_ADRESS = "128.197.50.90"
router_to_PI_PORT = 65432



piServer = net.TCPServer() # Start the server
piServer.set_server_address(pi_IP_ADDRESS, router_to_PI_PORT)
piServer.start_server()

# ---------------RESPONSE TABLE------------------
def get_sensor_data():
    return str(random.randint(0, 100))  # Replace with real sensor reading

response_table = {
    "GET_SENSOR_DATA": get_sensor_data
}

# ---------------SERVER LOOP------------------
class Server():

    def __init__():
        pass

    def run():
        '''
        Starts an infinite loop of recieving & sending requests
        '''
        while True:
            try:
                request = piServer.run()

                if request:
                    print(f"Received Message: {request}")
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
