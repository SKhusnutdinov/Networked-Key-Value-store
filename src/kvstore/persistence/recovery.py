

from pathlib import Path

from kvstore.domain import KeyValueStore
from kvstore.expiration import ExpirationRegistry
from kvstore.persistence.append_log import replay_log


def recover(engine: KeyValueStore, expirations: ExpirationRegistry, log_path: Path) -> None:
    replay_log(log_path, engine, expirations)
    for key in expirations.expired_keys():
        engine.delete(key)
        expirations.clear_expiry(key)