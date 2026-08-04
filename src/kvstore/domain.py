

from .errors import (
    InvalidKeyError,
    KeyTooLongError,
    NotAnIntegerError,
    UnsupportedValueTypeError,
    ValueTooLongError,
)

MAX_KEY_LENGTH = 256
MAX_VALUE_LENGTH = 4096


class KeyValueStore:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}
    
    def set(self, key: str, value: str) -> None:
        self._validate_key(key)
        self._validate_value(value)
        self._data[key] = value
    
    def get(self, key: str) -> None:
        self._validate_key(key)
        return self._data.get(key)

    def delete(self, key: str) -> bool:
        self._validate_key(key)
        return self._data.pop(key, None) is not None

    def exists(self, key: str) -> bool:
        self._validate_key(key)
        return key in self._data

    def items(self) -> dict[str, str]:
        return dict(self._data)
    
    def incr(self, key: str) -> int:
        self._validate_key(key)
        current = self._data.get(key, "0")
        try:
            new_value = int(current) + 1
        except ValueError as e:
            raise NotAnIntegerError(f"value for key {key} is not an integer") from e
        self._data[key] = str(new_value)
        return new_value
    
    def _validate_key(self, key: str) -> None:
        if not isinstance(key, str) or key == "":
            raise InvalidKeyError("key must be non-empty string")
        if len(key) > MAX_KEY_LENGTH:
            raise KeyTooLongError(f"key exceeds {MAX_KEY_LENGTH} characters")
    
    def _validate_value(self, value: str) -> None:
        if not isinstance(value, str):
            raise UnsupportedValueTypeError("value must be string")
        if len(value) > MAX_VALUE_LENGTH:
            raise ValueTooLongError(f"value exceeds {MAX_VALUE_LENGTH} characters")
            
        