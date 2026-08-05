

import asyncio
import json
from typing import Self

from .commands import Command
from .errors import KVStoreError


class KVClientError(KVStoreError):
    pass
    


class KVClient:
    def __init__(self, host: str, port: str) -> None:
        self._host = host
        self._port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
    
    async def connect(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(self._host, self._port)
    
    async def close(self) -> None:
        if self._writer is not None:
            self._writer.close()
            await self._writer.wait_closed()

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()
    
    async def set(self, key: str, value: str) -> None:
        await self._request({"command": Command.SET.value, "key": key, "value": value})
    
    async def get(self, key: str) -> str | None:
        response = await self._request({"command": Command.GET.value, "key": key})
        if response["status"] == "error":
            if response.get("error") == "not_found":
                return None
            raise KVClientError(response.get("error", "unknown_error")) 
        return response.get("value")

    async def delete(self, key: str) -> bool:
        response = await self._request({"command": Command.DELETE.value, "key": key})
        return bool(response.get("deleted", False))
    
    async def exists(self, key: str) -> bool:
        response = await self._request({"command": Command.EXISTS.value, "key": key})
        return bool(response.get("exists", False))

    async def send_raw(self, raw_line: str) -> str:
        assert self._writer is not None and self._reader is not None
        self._writer.write((raw_line + '\n').encode("utf-8"))
        await self._writer.drain()
        line = await self._reader.readline()
        return line.decode("utf-8").strip()
    
    async def _request(self, payload: dict) -> dict:
        raw_response = await self.send_raw(json.dumps(payload))
        return json.loads(raw_response)