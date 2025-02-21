import DDS.DDS.Backend.resources.netcode2 as net
import time


# ---------------CLIENT SETUP------------------
client = net.TCPClient()
client.set_server_address('128.197.50.90', 65432)
client.connect_to_server()

# ---------------RECEIVE DATA------------------
while True:
    try:
        response = client.send_message("GET_SENSOR_DATA")
        
        if response is None:
            print("No response received. Retrying connection...")
            client.connection_active = False  # Force reconnect in next loop iteration
            client.connect_to_server()
        else:
            print(f"Received Sensor Data: {response}") # comment out?
        
        time.sleep(1)  # Request data every second

    except (KeyboardInterrupt, SystemExit):
        print("Closing connection...")
        client.close_connection()
        break
    except Exception as e:
        print(f"Unexpected error: {e}. Retrying in 5 seconds...")
        time.sleep(5)
        client.connection_active = False
        client.connect_to_server()

print("App Closed")