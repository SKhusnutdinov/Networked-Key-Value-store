from pathlib import Path

from kvstore.domain import KeyValueStore
from kvstore.expiration import ExpirationRegistry
from kvstore.persistence.append_log import AppendLog
from kvstore.persistence.recovery import recover
from kvstore.store import StatefulStore


class FakeClock:
    def __init__(self, start: float = 1_700_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _build_store(tmp_path: Path, clock: FakeClock) -> StatefulStore:
    snapshot_path = tmp_path / "snapshot.json"
    log = AppendLog(tmp_path / "kvstore.log")
    expirations = ExpirationRegistry(clock=clock)
    engine = KeyValueStore()
    return StatefulStore(engine, log, expirations, snapshot_path)


async def test_key_exists_before_expiry(tmp_path):
    clock = FakeClock()
    store = _build_store(tmp_path, clock)
    await store.set("session:123", "abc")
    await store.expire("session:123", 60)

    assert store.get("session:123") == "abc"


async def test_key_disappears_after_expiry(tmp_path):
    clock = FakeClock()
    store = _build_store(tmp_path, clock)
    await store.set("session:123", "abc")
    await store.expire("session:123", 60)

    clock.advance(61)

    assert store.get("session:123") is None
    assert store.exists("session:123") is False


async def test_changing_ttl_replaces_old_expiration(tmp_path):
    clock = FakeClock()
    store = _build_store(tmp_path, clock)
    await store.set("session:123", "abc")
    await store.expire("session:123", 10)
    await store.expire("session:123", 100)

    clock.advance(50)

    assert store.get("session:123") == "abc"


async def test_deleting_a_key_removes_its_ttl_metadata(tmp_path):
    clock = FakeClock()
    store = _build_store(tmp_path, clock)
    await store.set("session:123", "abc")
    await store.expire("session:123", 60)
    await store.delete("session:123")
    await store.set("session:123", "def")

    clock.advance(61)

    assert store.get("session:123") == "def"


async def test_overwriting_a_key_clears_its_previous_ttl(tmp_path):
    clock = FakeClock()
    store = _build_store(tmp_path, clock)
    await store.set("session:123", "abc")
    await store.expire("session:123", 60)
    await store.set("session:123", "xyz")

    clock.advance(61)

    assert store.get("session:123") == "xyz"


async def test_expired_key_remains_absent_after_recovery(tmp_path):
    clock = FakeClock()
    store = _build_store(tmp_path, clock)
    await store.set("session:123", "abc")
    await store.expire("session:123", 60)
    clock.advance(61)

    engine = KeyValueStore()
    expirations = ExpirationRegistry(clock=clock)
    recover(engine, expirations, tmp_path / "snapshot.json", tmp_path / "kvstore.log")

    assert engine.get("session:123") is None