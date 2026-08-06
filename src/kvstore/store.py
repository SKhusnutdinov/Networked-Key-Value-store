import asyncio

from .domain import KeyValueStore
from .persistence.append_log import AppendLog


class StatefulStore:
    def __init__(self, engine: KeyValueStore, log: AppendLog) -> None:
        self._engine = engine
        self._log = log
        self._lock = asyncio.Lock()
    
    async def set(self, key: str, value: str) -> None:
        async with self._lock:
            self._log.append_set(key, value)
            self._engine.set(key, value)
    
    def get(self, key: str) -> str | None:
        return self._engine.get(key)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            existed = self._engine.exists(key)
            if existed:
                self._log.append_delete(key)
                self._engine.delete(key)
            return existed
    
    def exists(self, key: str) -> bool:
        return self._engine.exists(key)
    
    async def incr(self, key: str) -> int:
        async with self._lock:
            new_value = self._engine.incr(key)
            self._log.append_set(key, str(new_value))
            return new_value