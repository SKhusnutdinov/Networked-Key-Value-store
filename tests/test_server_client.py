import pytest_asyncio

from kvstore.client import KVClient
from kvstore.server import start_server


@pytest_asyncio.fixture
async def running_server(tmp_path):
    server, _store = await start_server("127.0.0.1", 0, tmp_path)
    port = server.sockets[0].getsockname()[1]
    yield "127.0.0.1", port
    server.close()
    await server.wait_closed()


async def test_single_client_runs_several_commands(running_server):
    host, port = running_server
    async with KVClient(host, port) as client:
        await client.set("name", "Player")
        assert await client.get("name") == "Player"
        assert await client.exists("name") is True
        assert await client.delete("name") is True
        assert await client.get("name") is None


async def test_multiple_clients_share_server_state(running_server):
    host, port = running_server
    async with KVClient(host, port) as client_a, KVClient(host, port) as client_b:
        await client_a.set("shared", "value")
        assert await client_b.get("shared") == "value"


async def test_client_disconnecting_mid_session_does_not_affect_server(running_server):
    host, port = running_server
    client = KVClient(host, port)
    await client.connect()
    await client.set("temp", "1")
    await client.close()

    async with KVClient(host, port) as other_client:
        assert await other_client.get("temp") == "1"


async def test_malformed_input_returns_error_and_connection_stays_usable(running_server):
    host, port = running_server
    async with KVClient(host, port) as client:
        raw_response = await client.send_raw("not json at all")
        assert '"status": "error"' in raw_response
        await client.set("name", "Player")
        assert await client.get("name") == "Player"


async def test_one_bad_client_does_not_crash_server_for_others(running_server):
    host, port = running_server
    bad_client = KVClient(host, port)
    await bad_client.connect()
    await bad_client.send_raw("garbage{{{")
    await bad_client.close()

    async with KVClient(host, port) as good_client:
        await good_client.set("still", "alive")
        assert await good_client.get("still") == "alive"