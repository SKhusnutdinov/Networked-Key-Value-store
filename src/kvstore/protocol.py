

import json
from dataclasses import dataclass

from .commands import Command
from .errors import ProtocolError

MAX_REQUEST_BYTES = 8192


@dataclass(frozen=True)
class Request:
    command: Command
    key: str | None = None
    value: str | None = None
    ttl: int | None = None

@dataclass(frozen=True)
class Response:
    status: str
    value: str | None = None
    error: str | None = None
    exists: bool | None = None
    deleted: bool | None = None

    def to_json_line(self) -> str:
        payload = {"status": self.status}
        if self.value is not None:
            payload["value"] = self.value
        if self.error is not None:
            payload["error"] = self.error
        if self.exists is not None:
            payload["exists"] = self.exists
        if self.deleted is not None:
            payload["deleted"] = self.deleted
        return json.dumps(payload)


_REQUIRED_FIELDS_BY_COMMAND = {
    Command.SET: ("key", "value"),
    Command.GET: ("key",),
    Command.DELETE: ("key",),
    Command.EXISTS: ("key",),
    Command.INCR: ("key",),
    Command.EXPIRE: ("key", "ttl",),
}

def parse_request(line: str) -> Request:
    if len(line.encode("utf-8")) > MAX_REQUEST_BYTES:
        raise ProtocolError("request_too_large")
    try:
        raw = json.loads(line)
    except json.JSONDecodeError as e:
        raise ProtocolError("malformed_json") from e
    if not isinstance(raw, dict):
        raise ProtocolError("malformed_json")

    command_raw = raw.get("command")
    if command_raw is None:
        raise ProtocolError("missing_field:command")
    try:
        command = Command(command_raw)
    except ValueError:
        raise ProtocolError("unknown_command")
    
    for field in _REQUIRED_FIELDS_BY_COMMAND[command]:
        if field not in raw or raw[field] is None:
            raise ProtocolError(f"missing_field:{field}")
    
    key = raw.get("key")
    if key is not None and not isinstance(key, str):
        raise ProtocolError("invalid_field_type:key")
    
    value = raw.get("value")
    if value is not None and not isinstance(value, str):
        raise ProtocolError("invalid_field_type:value")
    
    ttl = raw.get("ttl")
    if ttl is not None and not isinstance(ttl, int):
        raise ProtocolError("invalid_field_type:ttl")
    
    return Request(command=command, key=key, value=value, ttl=ttl)
    
    