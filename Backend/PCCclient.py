import time
import threading
import logging
import socket
import json
from typing import Callable, Dict, Any, Optional, Tuple
from Backend.config.config_loader import CONFIG


class NotConnectedException(Exception):
    pass


class PCCClient:
    def __init__(self, get_data_callable: Callable[[str, str], Any]) -> None:
        """
        Initializes the PCCClient by setting up the TCP client connection to the server.
        The server address and port are retrieved from the configuration file.
        """
        self.log = logging.getLogger("PCC_Client")
        self.get_data_callable = get_data_callable
        self.server_ip = CONFIG["network_settings"]["ip"]
        self.server_port = CONFIG["network_settings"]["port"]
        self.socket: Optional[socket.socket] = None
        self.connected_to_server = False
        socket.setdefaulttimeout(5)
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Starts the client loop in a separate daemon thread."""
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stops the client loop and closes the connection."""
        self._stop_event.set()
        self.close_connection()
        if hasattr(self, "thread"):
            self.thread.join()

    def _run(self) -> None:
        """
        Background thread that continuously manages connection,
        receives requests from the server, and sends sensor data responses.
        """
        while not self._stop_event.is_set():
            if not self.connected_to_server:
                time.sleep(1)
                self.connected_to_server = self._connect_to_server(self.server_ip, self.server_port)
                continue

            request_message = self._receive_message()
            if request_message is None:
                self.log.warning("Lost connection to server")
                self.connected_to_server = False
                continue

            request_parsed = self._parse_request(request_message)
            if not request_parsed:
                self.log.error(f"Failed to parse request: {request_message}")
                self.connected_to_server = False
                continue

            device, parameter = request_parsed
            sensor_data = self.get_data_callable(device, parameter)
            self.log.debug(f"Sending response {sensor_data} for request {request_parsed}")
            self._send_message(sensor_data)

        self.log.critical("Client thread stopped running.")

    def _connect_to_server(self, ip: str, port: int) -> bool:
        """
        Attempts to establish a connection with the server and perform handshake.
        Returns True if connection and handshake are successful, False otherwise.
        """
        self.log.debug(f"Attempting to connect to PCC at {ip}:{port}")
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(1)
            self.socket.connect((ip, port))
            self.socket.sendall("START_COMMUNICATION_DDS".encode())

            handshake = self.socket.recv(1024).decode()
            if handshake == "GOOD_TO_START_COMMUNICATION_PCC":
                self.log.info(f"Connected to PCC at {ip}:{port}")
                return True
            else:
                self.log.warning(f"Handshake failed. Received: {handshake}")
                self.close_connection()
                return False
        except (ConnectionRefusedError, ConnectionResetError, TimeoutError, OSError) as e:
            self.log.warning(f"Connection attempt failed: {e}")
            self.close_connection()
            return False

    def _send_message(self, message: Dict[str, Any]) -> None:
        """Encodes and sends a message to the server."""
        try:
            encoded_message = json.dumps(message).encode()
            self.socket.sendall(encoded_message)
        except (BrokenPipeError, OSError) as e:
            self.log.warning(f"Error sending message: {e}")
            self.connected_to_server = False
            self.close_connection()

    def _receive_message(self) -> Optional[str]:
        """
        Receives a message from the server.
        Returns the message string if successful, or None if there is an error.
        """
        try:
            message = self.socket.recv(1024).decode()
            self.log.debug(f"Received message: {message}")
            return message
        except (ConnectionResetError, TimeoutError, OSError) as e:
            self.log.error(f"Error receiving message: {e}")
            self.connected_to_server = False
            self.close_connection()
            return None

    def _parse_request(self, data: str) -> Optional[Tuple[str, str]]:
        """
        Parses the incoming request string into a tuple of (device, parameter).
        Expected format: "device|parameter".
        Returns a tuple if successful, or None if parsing fails.
        """
        try:
            data = data.strip()
            if '|' not in data:
                raise ValueError("Missing '|' separator in request")
            parts = data.split('|')
            if len(parts) != 2:
                raise ValueError("Expected exactly one '|' separator")
            device, parameter = parts[0].strip(), parts[1].strip()
            if not device or not parameter:
                raise ValueError("Device or parameter is empty")
            return device, parameter
        except Exception as e:
            self.log.error(f"Error parsing request: {e}")
            return None

    def close_connection(self) -> None:
        """Closes the socket connection if it exists."""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                self.log.error(f"Error closing socket: {e}")
            finally:
                self.socket = None
                self.connected_to_server = False


if __name__ == "__main__":
    def fetch_device_data(device: str, parameter: str) -> Dict[str, Any]:
        # Replace with actual data retrieval logic.
        return {"device": device, "parameter": parameter, "value": 42}

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(name)s]: %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    client = PCCClient(fetch_device_data)
    client.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client.log.info("KeyboardInterrupt received, shutting down.")
        client.stop()
