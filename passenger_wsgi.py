import os
import socket
import sys
from pathlib import Path
from threading import Thread

from dotenv import load_dotenv

from python_socks_server.logging import setup_logger

load_dotenv(dotenv_path=Path(__file__).parent / '.env', verbose=True)
setup_logger()


def is_socks_running():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.bind((
                os.environ.get("SOCKS_HOST", "127.0.0.1"),
                int(os.environ.get("SOCKS_PORT", 1080))
            ))
        return False
    except OSError:
        return True


class SocksProxyManager:
    def __init__(self):
        self.running = False

    def run_socks_server(self):
        if self.running:
            return

        self.running = True
        try:
            from python_socks_server.socks5 import Socks5Server
            
            server = Socks5Server()
            server.start()
        except ImportError:
            print("Error: Could not import python_socks_server", file=sys.stderr)
        finally:
            self.running = False


proxy_manager = SocksProxyManager()


def application(environ, start_response):
    if not is_socks_running() and not proxy_manager.running:
        Thread(target=proxy_manager.run_socks_server, daemon=True).start()

    start_response('200 OK', [
        ('Content-Type', 'text/plain'),
        ('Cache-Control', 'no-store')
    ])
    return [b"SOCKS5 proxy manager is active"]
