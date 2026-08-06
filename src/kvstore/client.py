

import asyncio
import json
from typing import Self

from .commands import Command
from .errors import KVStoreError


class KVClientError(KVStoreError):
    pass
    


class KVClient:
    def __init__(self, host: str, port: int) -> None:
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
        
        self._writer = None
        self._reader = None

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
    
    async def incr(self, key: str) -> int:
        response = await self._request({"command": Command.INCR.value, "key": key})
        if response["status"] == "error":
            raise KVClientError(response.get("error", "unknown_error"))
        return int(response["value"])
    
    async def expire(self, key: str, ttl_seconds: int) -> bool:
        response = await self._request({"command": Command.EXPIRE.value, "key": key, "expires_at": ttl_seconds})
        return response["status"] == "success"

    async def send_raw(self, raw_line: str) -> str:
        if self._writer is None or self._reader is None:
            raise KVClientError("not_connected")
        self._writer.write((raw_line + '\n').encode("utf-8"))
        await self._writer.drain()
        line = await self._reader.readline()
        return line.decode("utf-8").strip()
    
    async def _request(self, payload: dict) -> dict:
        raw_response = await self.send_raw(json.dumps(payload))
        return json.loads(raw_response)