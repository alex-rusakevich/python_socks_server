Python SOCKS 4 server
===

This program is a SOCKS 4 server which does not require `sudo`, `glibc`, `ssh` etc.
The only requirements are Python and `pip`.

## Development setup

```sh
pip install poetry
poetry install

poetry run python python_socks_server.py
```

## Production setup

```sh
pip install poetry
poetry install --no-dev --no-root

poetry run python python_socks_server.py
```
