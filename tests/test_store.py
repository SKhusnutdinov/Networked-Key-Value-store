import pytest

from kvstore.domain import MAX_KEY_LENGTH, MAX_VALUE_LENGTH, KeyValueStore
from kvstore.errors import (
    InvalidKeyError,
    KeyTooLongError,
    NotAnIntegerError,
    UnsupportedValueTypeError,
    ValueTooLongError,
)


def test_set_and_get():
    store = KeyValueStore()
    store.set("name", "Player")
    assert store.get("name") == "Player"


def test_overwrite_existing_value():
    store = KeyValueStore()
    store.set("name", "Player")
    store.set("name", "Player2")
    assert store.get("name") == "Player2"


def test_get_missing_key_returns_none():
    store = KeyValueStore()
    assert store.get("missing") is None


def test_delete_existing_key():
    store = KeyValueStore()
    store.set("name", "Player")
    assert store.delete("name") is True
    assert store.get("name") is None


def test_delete_missing_key_returns_false():
    store = KeyValueStore()
    assert store.delete("missing") is False


def test_exists_true_and_false():
    store = KeyValueStore()
    store.set("name", "Player")
    assert store.exists("name") is True
    assert store.exists("missing") is False


def test_empty_key_is_rejected():
    store = KeyValueStore()
    with pytest.raises(InvalidKeyError):
        store.set("", "value")


def test_key_over_max_length_is_rejected():
    store = KeyValueStore()
    with pytest.raises(KeyTooLongError):
        store.set("k" * (MAX_KEY_LENGTH + 1), "value")


def test_value_over_max_length_is_rejected():
    store = KeyValueStore()
    with pytest.raises(ValueTooLongError):
        store.set("key", "v" * (MAX_VALUE_LENGTH + 1))


def test_non_string_value_is_rejected():
    store = KeyValueStore()
    with pytest.raises(UnsupportedValueTypeError):
        store.set("key", 123)


def test_incr_creates_counter_starting_at_zero():
    store = KeyValueStore()
    assert store.incr("counter") == 1


def test_incr_increments_existing_integer_value():
    store = KeyValueStore()
    store.set("counter", "5")
    assert store.incr("counter") == 6
    assert store.get("counter") == "6"


def test_incr_on_non_integer_value_raises():
    store = KeyValueStore()
    store.set("counter", "not-a-number")
    with pytest.raises(NotAnIntegerError):
        store.incr("counter")