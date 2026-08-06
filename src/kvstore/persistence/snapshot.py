
import json
import os
from pathlib import Path

from ..domain import KeyValueStore
from ..expiration import ExpirationRegistry


def write_snapshot(path: Path, engine: KeyValueStore, expirations: ExpirationRegistry) -> None:
    path = Path(path)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    payload = {"data": engine.items(), "expirations": expirations.all_expirations()}
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)

def load_snapshot(path: Path, engine: KeyValueStore, expirations: ExpirationRegistry) -> None:
    path = Path(path)
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    for key, value in payload.get("data", {}).items():
        engine.set(key, value)
    for key, expires_at in payload.get("expirations", {}).items():
        expirations.set_expiry(key, expires_at)