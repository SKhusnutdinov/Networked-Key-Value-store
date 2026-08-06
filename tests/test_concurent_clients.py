import asyncio

from kvstore.client import KVClient
from kvstore.server import start_server


async def test_concurrent_increments_are_not_lost(tmp_path):
    server, _store, sweep_task = await start_server("127.0.0.1", 0, tmp_path)
    port = server.sockets[0].getsockname()[1]
    host = "127.0.0.1"

    async with KVClient(host, port) as setup_client:
        await setup_client.set("counter", "0")

    async def one_client_100_incrs() -> None:
        async with KVClient(host, port) as client:
            for _ in range(100):
                await client.incr("counter")

    await asyncio.gather(*(one_client_100_incrs() for _ in range(100)))

    async with KVClient(host, port) as client:
        assert await client.get("counter") == "10000"

    sweep_task.cancel()
    server.close()
    await server.wait_closed()