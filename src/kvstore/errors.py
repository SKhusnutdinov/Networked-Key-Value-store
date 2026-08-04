

class KVStoreError(Exception):
    code: str = "internal_error"

class InvalidKeyError(KVStoreError):
    code = "invalid_key"

class KeyTooLongError(KVStoreError):
    code = "key_too_long"

class ValueTooLongError(KVStoreError):
    code = "value_too_long"

class UnsupportedValueTypeError(KVStoreError):
    code = "unsupported_value_type"

class NotAnIntegerError(KVStoreError):
    code = "not_an_integer"

class ProtocolError(KVStoreError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code