import argparse
import asyncio
from pathlib import Path

from .domain import KeyValueStore
from .errors import ProtocolError
from .expiration import ExpirationRegistry
from .handler import handle
from .persistence.append_log import AppendLog
from .persistence.recovery import recover
from .protocol import Response, parse_request
from .store import StatefulStore

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 6379
DEFAULT_DATA_DIR = Path("./data")
EXPIRATION_SWEEP_INTERVAL_SECONDS = 1.0


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    store: StatefulStore
) -> None:
    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                request = parse_request(line.decode("utf-8").strip())
            except ProtocolError as e:
                response = Response(status="error", error=e.code)
            else:
                response = await handle(request=request, store=store)
            writer.write((response.to_json_line() + '\n').encode("utf-8"))
            await writer.drain()
    except (ConnectionResetError, asyncio.IncompleteReadError):
        pass
    finally:
        writer.close()
        await writer.wait_closed()

async def expirations_sweep_loop(store: StatefulStore, interval: float = EXPIRATION_SWEEP_INTERVAL_SECONDS) -> None:
    while True:
        await store.sweep_expired()
        await asyncio.sleep(interval)


async def start_server(host: str, port: int, data_dir: Path = DEFAULT_DATA_DIR) -> tuple[asyncio.AbstractServer, StatefulStore, asyncio.Task]:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    log_path = data_dir / "kvstore.log"    
    
    engine = KeyValueStore()
    expirations = ExpirationRegistry()
    recover(engine, expirations, log_path)
    log = AppendLog(log_path)
    store = StatefulStore(engine, log, expirations)
    
    sweep_task = asyncio.create_task(expirations_sweep_loop(store))
    
    async def _handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await handle_client(reader, writer, store)
    
    server = await asyncio.start_server(_handler, host, port)
    return server, store, sweep_task

async def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, data_dir: Path = DEFAULT_DATA_DIR) -> None:
    server, _store, _sweep_task = await start_server(host, port, data_dir)
    async with server:
        await server.serve_forever()

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the kvstore TCP server.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    args = parser.parse_args()
    asyncio.run(run_server(args.host, args.port, Path(args.data_dir)))


if __name__ == "__main__":
    main()