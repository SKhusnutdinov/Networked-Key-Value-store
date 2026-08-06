

from pathlib import Path

from kvstore.domain import KeyValueStore
from kvstore.persistence.append_log import replay_log


def recover(engine: KeyValueStore, log_path: Path) -> None:
    replay_log(log_path, engine)