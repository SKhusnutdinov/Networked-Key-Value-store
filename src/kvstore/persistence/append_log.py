

import json
import os
from pathlib import Path


class AppendLog:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._file = open(self.path, "a", encoding="utf-8")
    
    def append_set(self, key: str, value: str) -> None:
        self._write({"operation": "SET", "key": key, "value": value})
    
    def append_delete(self, key: str) -> None:
        self._write({"operation": "DELETE", "key": key})
    
    def _write(self, record: dict) -> None:
        self._file.write(json.dumps(record) + "\n")
        self._file.flush()
        os.fsync(self._file.fileno())
    
    def reset(self) -> None:
        self._file.close()
        self.path.write_text("", encoding="utf-8")
        self._file = open(self.path, "a", encoding="utf-8")
    
    def close(self) -> None:
        self._file.close()

def replay_log(path: Path, engine) -> None:
    path = Path(path)
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                break
            operation = record.get("operation")
            if operation == "SET":
                engine.set(record["key"], record["value"])
            elif operation == "DELETE":
                engine.delete(record["key"])