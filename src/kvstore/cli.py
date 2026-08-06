

import asyncio
import sys

from .client import KVClient, KVClientError

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 6379

async def run_cli(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    try:
        async with KVClient(host, port) as client:
            print(f"Connected to {host}:{port}")
            while True:
                try:
                    line = await asyncio.to_thread(input, "kv> ")
                except EOFError:
                    break
                line = line.strip()
                if not line:
                    continue
                if line.lower() in ("quit", "exit"):
                    break
                await _dispatch(client, line)
    except OSError as e:
        print(f"error could not connect to {host}:{port}: {e}")

async def _dispatch(client: KVClient, line: str) -> None:
    parts = line.split(maxsplit=2)
    command = parts[0].upper()
    try:
        if command == "SET" and len(parts) == 3:
            await client.set(parts[1], parts[2])
            print("success")
        elif command == "GET" and len(parts) == 2:
            value = await client.get(parts[1])
            print(value if value is not None else "value not found")
        elif command == "DELETE" and len(parts) == 2:
            deleted = await client.delete(parts[1])
            print("success" if deleted else "value not found")
        elif command == "EXISTS" and len(parts) == 2:
            exists = await client.exists(parts[1])
            print("true" if exists else "false")
        elif command == "INCR" and len(parts) == 2:
            value = await client.incr(parts[1])
            print(value)
        elif command == "EXPIRE" and len(parts) == 3:
            success = await client.expire(parts[1], int(parts[2]))
            print("success" if success else "value not found")
        else:
            print("error: unrecognized command")
    except KVClientError as e:
        print(f"error: {e}")

def main() -> None:
    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOST
    port = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PORT
    try:
        asyncio.run(run_cli(host, port))
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()