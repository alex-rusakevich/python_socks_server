import logging
import os
import select
import socket
import struct
import threading
from pathlib import Path
from typing import Tuple

from dotenv import find_dotenv, load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Socks4Server:
    def __init__(
        self,
        host: str = os.getenv("PYTHON_SOCKS_SERVER_HOST", "127.0.0.1"),
        port: int = int(os.getenv("PYTHON_SOCKS_SERVER_PORT", 1080)),
    ):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False

    def start(self):
        """Start the SOCKS4 proxy server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True

        logger.info(f"SOCKS4 proxy server started on {self.host}:{self.port}")

        env_path = Path(find_dotenv()).resolve()
        logger.info(f"The .env file is located at '{env_path}'")

        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                logger.info(
                    f"New connection from {client_address[0]}:{client_address[1]}"
                )
                client_thread = threading.Thread(
                    target=self.handle_client, args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                logger.error(f"Error accepting connection: {e}")
                break

    def stop(self):
        """Stop the SOCKS4 proxy server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()

    def handle_client(
        self, client_socket: socket.socket, client_address: Tuple[str, int]
    ):
        """Handle client connection"""
        try:
            # Handle SOCKS4 request
            if not self.handle_request(client_socket):
                return

        except Exception as e:
            logger.error(f"Error handling client {client_address}: {e}")
        finally:
            client_socket.close()

    def handle_request(self, client_socket: socket.socket) -> bool:
        """Handle SOCKS4 client request"""
        # Read request
        data = client_socket.recv(1024)
        if not data:
            return False

        logger.info(f"Received client request: {data.hex()}")

        # Check SOCKS version
        if data[0] != 0x04:
            logger.error("Invalid SOCKS version")
            return False

        # Get command
        command = data[1]
        if command != 0x01:  # Only support CONNECT command
            response = struct.pack("!BBHI", 0x00, 0x5B, 0, 0)  # Request rejected
            client_socket.send(response)
            return False

        # Get port
        target_port = struct.unpack("!H", data[2:4])[0]

        # Get IP address
        target_ip = socket.inet_ntoa(data[4:8])

        # Check if this is a SOCKS4a request (IP is 0.0.0.x)
        if target_ip.startswith("0.0.0."):
            # This is a SOCKS4a request, read domain name
            # Find the null terminator after the userid
            null_pos = data.find(b"\x00", 8)
            if null_pos == -1:
                return False

            # Domain name starts after the second null terminator
            domain_start = data.find(b"\x00", null_pos + 1)
            if domain_start == -1:
                return False

            target_host = data[domain_start + 1 : -1].decode()
            logger.info(f"SOCKS4a request for domain: {target_host}")
        else:
            target_host = target_ip
            logger.info(f"SOCKS4 request for IP: {target_host}")

        try:
            # Connect to target
            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.connect((target_host, target_port))

            # Send success response
            response = struct.pack("!BBHI", 0x00, 0x5A, 0, 0)  # Request granted
            client_socket.send(response)

            self.forward_data(client_socket, target_socket)
            return True

        except Exception as e:
            logger.error(f"Error connecting to target: {e}")
            response = struct.pack("!BBHI", 0x00, 0x5B, 0, 0)  # Request rejected
            client_socket.send(response)
            return False

    def forward_data(self, client_socket: socket.socket, target_socket: socket.socket):
        """Forward data between client and target"""
        while self.running:
            # Check for data
            readable, _, exceptional = select.select(
                [client_socket, target_socket], [], [client_socket, target_socket], 1
            )

            if exceptional:
                break

            for sock in readable:
                try:
                    data = sock.recv(4096)
                    if not data:
                        return

                    if sock is client_socket:
                        target_socket.send(data)
                    else:
                        client_socket.send(data)
                except Exception as e:
                    logger.error(f"Error forwarding data: {e}")
                    return


if __name__ == "__main__":
    proxy = Socks4Server()

    try:
        proxy.start()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        proxy.stop()
