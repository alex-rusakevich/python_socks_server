import logging
import os
import select
import socket
import struct
import threading
from typing import Tuple

from python_socks_server.server import SocksServer

logger = logging.getLogger(__name__)


class Socks5Server(SocksServer):
    def __init__(
            self,
            host: str = os.environ.get("SOCKS_HOST", "127.0.0.1"),
            port: int = int(os.environ.get("SOCKS_PORT", 1080)),
            username: str = os.environ.get("SOCKS_USER", "user"),
            password: str = os.environ.get("SOCKS_PASSWORD", "password")
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.server_socket = None
        self.running = False

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True

        logger.info(f"SOCKS5 proxy server started on {self.host}:{self.port}")

        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                logger.info(f"New connection from {client_address[0]}:{client_address[1]}")
                client_thread = threading.Thread(
                    target=self.handle_client, args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                logger.error(f"Error accepting connection: {e}")
                break

    def stop(self):
        self.running = False

        if self.server_socket:
            self.server_socket.close()

    def handle_client(
            self, client_socket: socket.socket, client_address: Tuple[str, int]
    ):
        """Handle client connection"""
        try:
            if not self.handle_handshake(client_socket):
                return

            if not self.handle_request(client_socket):
                return

        except Exception as e:
            logger.error(f"Error handling client {client_address}: {e}")
        finally:
            client_socket.close()

    def handle_handshake(self, client_socket: socket.socket) -> bool:
        """Handle SOCKS5 handshake with authentication"""
        # Read client greeting
        data = client_socket.recv(1024)
        if not data:
            return False

        logger.debug(f"Received client greeting: {data.hex()}")

        # Check SOCKS version
        if data[0] != 0x05:
            logger.error("Invalid SOCKS version")
            return False

        # Get number of auth methods
        nmethods = data[1]
        methods = data[2: 2 + nmethods]

        logger.debug(f"Client auth methods: {methods.hex()}")

        # Check if username/password auth is supported by client
        if 0x02 in methods:  # Username/password auth
            # Send auth method choice
            client_socket.send(b"\x05\x02")  # SOCKS5, username/password auth
            logger.debug("Sent auth method choice: 0x05 0x02")

            # Read username/password
            auth_data = client_socket.recv(1024)
            if not auth_data:
                return False

            logger.debug(f"Received auth data: {auth_data.hex()}")

            # Parse username and password
            if auth_data[0] != 0x01:  # Check auth version
                logger.error("Invalid auth version")
                return False

            ulen = auth_data[1]
            username = auth_data[2: 2 + ulen].decode()
            plen = auth_data[2 + ulen]
            password = auth_data[3 + ulen: 3 + ulen + plen].decode()

            # logger.info(f"Received username: {username}, password: {password}")

            # Verify credentials
            if username == self.username and password == self.password:
                client_socket.send(b"\x01\x00")  # Authentication successful
                logger.info("Authentication successful")
            else:
                client_socket.send(b"\x01\x01")  # Authentication failed
                logger.error("Authentication failed")
                return False
        else:
            client_socket.send(b"\x05\xff")  # No acceptable methods
            logger.error("Client doesn't support username/password auth")
            return False

        return True

    def handle_request(self, client_socket: socket.socket) -> bool:
        """Handle SOCKS5 client request"""
        # Read request
        data = client_socket.recv(1024)
        if not data:
            return False

        # Check SOCKS version
        if data[0] != 0x05:
            return False

        # Get command
        command = data[1]
        if command != 0x01:  # Only support CONNECT command
            client_socket.send(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
            return False

        # Get address type
        addr_type = data[3]
        if addr_type == 0x01:  # IPv4
            target_host = socket.inet_ntoa(data[4:8])
            target_port = struct.unpack(">H", data[8:10])[0]
        elif addr_type == 0x03:  # Domain name
            domain_len = data[4]
            target_host = data[5: 5 + domain_len].decode()
            target_port = struct.unpack(">H", data[5 + domain_len: 7 + domain_len])[0]
        else:
            client_socket.send(b"\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00")
            return False

        try:
            # Connect to target
            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.connect((target_host, target_port))

            # Send success response
            bind_addr = target_socket.getsockname()
            response = b"\x05\x00\x00\x01"
            response += socket.inet_aton(bind_addr[0])
            response += struct.pack(">H", bind_addr[1])
            client_socket.send(response)

            # Start forwarding data
            self.forward_data(client_socket, target_socket)
            return True

        except Exception as e:
            logger.error(f"Error connecting to target: {e}")
            client_socket.send(b"\x05\x04\x00\x01\x00\x00\x00\x00\x00\x00")
            return False

    def forward_data(self, client_socket: socket.socket, target_socket: socket.socket):
        """Forward data between client and target"""
        while self.running:
            # Use select to check for data
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
