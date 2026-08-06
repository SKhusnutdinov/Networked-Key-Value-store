from kvstore.client import KVClient
from kvstore.server import start_server


async def _start(tmp_path):
    server, store, sweep_task = await start_server("127.0.0.1", 0, tmp_path)
    port = server.sockets[0].getsockname()[1]
    return server, store, sweep_task, ("127.0.0.1", port)


async def _stop(server, sweep_task):
    sweep_task.cancel()
    server.close()
    await server.wait_closed()


async def test_compaction_then_restart_recovers_full_state(tmp_path):
    server, store, sweep_task, (host, port) = await _start(tmp_path)
    async with KVClient(host, port) as client:
        await client.set("name", "Player")
        await client.set("score", "1")
        await client.set("score", "2")
    await store.compact()
    async with KVClient(host, port) as client:
        await client.set("extra", "after-compaction")
    await _stop(server, sweep_task)

    server, store, sweep_task, (host, port) = await _start(tmp_path)
    async with KVClient(host, port) as client:
        assert await client.get("name") == "Player"
        assert await client.get("score") == "2"
        assert await client.get("extra") == "after-compaction"
    await _stop(server, sweep_task)


async def test_log_is_reset_after_compaction(tmp_path):
    server, store, sweep_task, (host, port) = await _start(tmp_path)
    async with KVClient(host, port) as client:
        await client.set("name", "Player")
    await store.compact()

    log_path = tmp_path / "kvstore.log"
    assert log_path.read_text() == ""

    await _stop(server, sweep_task)