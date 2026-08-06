from pathlib import Path

from kvstore.client import KVClient
from kvstore.server import start_server


async def _run_server_and_get_address(data_dir: Path):
    server, store, sweep_task = await start_server("127.0.0.1", 0, data_dir)
    port = server.sockets[0].getsockname()[1]
    return server, store, sweep_task, ("127.0.0.1", port)


async def test_values_survive_server_restart(tmp_path):
    server, _store, sweep_task, (host, port) = await _run_server_and_get_address(tmp_path)
    async with KVClient(host, port) as client:
        await client.set("name", "Alice")
    sweep_task.cancel()
    server.close()
    await server.wait_closed()

    server, _store, sweep_task, (host, port) = await _run_server_and_get_address(tmp_path)
    async with KVClient(host, port) as client:
        assert await client.get("name") == "Alice"
    sweep_task.cancel()
    server.close()
    await server.wait_closed()


async def test_deleted_key_stays_deleted_after_restart(tmp_path):
    server, _store, sweep_task, (host, port) = await _run_server_and_get_address(tmp_path)
    async with KVClient(host, port) as client:
        await client.set("name", "Alice")
        await client.delete("name")
    sweep_task.cancel()
    server.close()
    await server.wait_closed()

    server, _store, sweep_task, (host, port) = await _run_server_and_get_address(tmp_path)
    async with KVClient(host, port) as client:
        assert await client.get("name") is None
    sweep_task.cancel()
    server.close()
    await server.wait_closed()