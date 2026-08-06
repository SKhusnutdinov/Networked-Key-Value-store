import asyncio
from pathlib import Path

from kvstore.persistence.snapshot import write_snapshot

from .domain import KeyValueStore
from .expiration import ExpirationRegistry
from .persistence.append_log import AppendLog

COMPACTION_THRESHOLD_BYTES = 1_000_000

class StatefulStore:
    def __init__(self, engine: KeyValueStore, log: AppendLog, expirations: ExpirationRegistry, snapshot_path: Path) -> None:
        self._engine = engine
        self._log = log
        self._expirations = expirations
        self._snapshot_path = Path(snapshot_path)
        self._lock = asyncio.Lock()
    
    async def set(self, key: str, value: str) -> None:
        async with self._lock:
            self._log.append_set(key, value)
            self._engine.set(key, value)
            self._expirations.clear_expiry(key)
        await self._try_compact()
    
    def get(self, key: str) -> str | None:
        self._expire_if_needed(key)
        return self._engine.get(key)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            self._expire_if_needed(key)
            existed = self._engine.exists(key)
            if existed:
                self._log.append_delete(key)
                self._engine.delete(key)
                self._expirations.clear_expiry(key)
        if existed:
            await self._try_compact()
        return existed
    
    def exists(self, key: str) -> bool:
        self._expire_if_needed(key)
        return self._engine.exists(key)
    
    async def incr(self, key: str) -> int:
        async with self._lock:
            self._expire_if_needed(key)
            new_value = self._engine.incr(key)
            self._log.append_set(key, str(new_value))
        await self._try_compact()
        return new_value
    
    async def expire(self, key: str, ttl_seconds: int) -> bool:
        async with self._lock:
            self._expire_if_needed(key)
            key_exists = self._engine.exists(key)
            if key_exists:
                expires_at = self._expirations.clock_now() + ttl_seconds
                self._log.append_expire(key, expires_at)
                self._expirations.set_expiry(key, expires_at)
        if key_exists:
            await self._try_compact()
        return key_exists
    
    async def sweep_expired(self) -> None:
        async with self._lock:
            for key in self._expirations.expired_keys():
                self._engine.delete(key)
                self._expirations.clear_expiry(key)

    async def compact(self) -> None:
        async with self._lock:
            write_snapshot(self._snapshot_path, self._engine, self._expirations)
            self._log.reset()
    
    async def _try_compact(self) -> None:
        if self._log.size_bytes >= COMPACTION_THRESHOLD_BYTES:
            await self.compact()
    
    def _expire_if_needed(self, key: str) -> None:
        if self._expirations.is_expired(key):
            self._engine.delete(key)
            self._expirations.clear_expiry(key)
                