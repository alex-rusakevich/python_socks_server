#!/usr/bin/env python3

import logging
from pathlib import Path

import click
from dotenv import find_dotenv, load_dotenv

from .socks4 import Socks4Server
from .socks5 import Socks5Server

load_dotenv()
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


@click.command()
@click.option('-s', '--socks-version', type=click.Choice(['4', '5']), default='5',
              help='SOCKS protocol version')
@click.option('-h', '--host', default='0.0.0.0', help='Bind address')
@click.option('-p', '--port', default=1080, help='Bind port')
def main(socks_version, host, port):
    env_path = Path(find_dotenv(), ".env").resolve()
    logger.info(f"The .env file is located at '{env_path}'")

    server = Socks4Server(host, port) if socks_version == '4' else Socks5Server(host, port)
    logger.info(f"Starting SOCKS{socks_version} server on {host}:{port}")
    server.start()


if __name__ == '__main__':
    main()
