

from pathlib import Path

from kvstore.persistence.snapshot import load_snapshot

from ..domain import KeyValueStore
from ..expiration import ExpirationRegistry
from ..persistence.append_log import replay_log


def recover(engine: KeyValueStore, expirations: ExpirationRegistry, snapshot_path: Path, log_path: Path) -> None:
    load_snapshot(snapshot_path, engine, expirations)
    replay_log(log_path, engine, expirations)
    for key in expirations.expired_keys():
        engine.delete(key)
        expirations.clear_expiry(key)