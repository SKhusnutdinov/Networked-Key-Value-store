import asyncio
import json

import pytest_asyncio

from kvstore.domain import KeyValueStore
from kvstore.server import start_server


@pytest_asyncio.fixture
async def running_server():
    store = KeyValueStore()
    server = await start_server("127.0.0.1", 0, store)
    port = server.sockets[0].getsockname()[1]
    yield "127.0.0.1", port, store
    server.close()
    await server.wait_closed()


async def test_single_client_set_and_get(running_server):
    host, port, _store = running_server
    reader, writer = await asyncio.open_connection(host, port)

    writer.write((json.dumps({"command": "SET", "key": "name", "value": "Player"}) + "\n").encode())
    await writer.drain()
    response = json.loads((await reader.readline()).decode())
    assert response == {"status": "success"}

    writer.write((json.dumps({"command": "GET", "key": "name"}) + "\n").encode())
    await writer.drain()
    response = json.loads((await reader.readline()).decode())
    assert response == {"status": "success", "value": "Player"}

    writer.close()
    await writer.wait_closed()


async def test_malformed_input_returns_error_without_crashing_server(running_server):
    host, port, _store = running_server
    reader, writer = await asyncio.open_connection(host, port)

    writer.write(b"not json at all\n")
    await writer.drain()
    response = json.loads((await reader.readline()).decode())
    assert response["status"] == "error"

    writer.close()
    await writer.wait_closed()