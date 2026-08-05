import asyncio

from .domain import KeyValueStore
from .errors import ProtocolError
from .handler import handle
from .protocol import Response, parse_request

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 6379


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    store: KeyValueStore
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


async def start_server(host: str, port: int, store: KeyValueStore) -> asyncio.AbstractServer:
    async def _handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await handle_client(reader, writer, store)
    
    return await asyncio.start_server(_handler, host, port)

async def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    store = KeyValueStore()
    server = await start_server(host, port, store)
    async with server:
        await server.serve_forever()

def main() -> None:
    asyncio.run(run_server())

if __name__ == "__main__":
    main()