import pytest_asyncio

from kvstore.commands import Command
from kvstore.domain import KeyValueStore
from kvstore.expiration import ExpirationRegistry
from kvstore.handler import handle
from kvstore.persistence.append_log import AppendLog
from kvstore.protocol import Request
from kvstore.store import StatefulStore


@pytest_asyncio.fixture
async def store(tmp_path):
    engine = KeyValueStore()
    snapshot_path = tmp_path / "snapshot.json"
    log = AppendLog(tmp_path / "kvstore.log")
    expirations = ExpirationRegistry()
    stateful_store = StatefulStore(engine, log, expirations, snapshot_path)

    yield stateful_store

    log.close()

async def test_set_returns_success_and_mutates_store(store):
    response = await handle(Request(command=Command.SET, key="name", value="Player"), store)
    assert response.status == "success"
    assert store.get("name") == "Player"


async def test_get_existing_key(store):
    await store.set("name", "Player")
    response = await handle(Request(command=Command.GET, key="name"), store)
    assert response.status == "success"
    assert response.value == "Player"


async def test_get_missing_key_returns_not_found_error(store):
    response = await handle(Request(command=Command.GET, key="missing"), store)
    assert response.status == "error"
    assert response.error == "not_found"


async def test_delete_existing_key(store):
    await store.set("name", "Player")
    response = await handle(Request(command=Command.DELETE, key="name"), store)
    assert response.status == "success"
    assert response.deleted is True
    assert not store.exists("name")


async def test_delete_missing_key(store):
    response = await handle(Request(command=Command.DELETE, key="missing"), store)
    assert response.status == "success"
    assert response.deleted is False


async def test_exists_true_and_false(store):
    await store.set("name", "Player")
    present = await handle(Request(command=Command.EXISTS, key="name"), store)
    absent = await handle(Request(command=Command.EXISTS, key="missing"), store)
    assert present.exists is True
    assert absent.exists is False


async def test_domain_error_becomes_error_response(store):
    response = await handle(Request(command=Command.SET, key="", value="x"), store)
    assert response.status == "error"
    assert response.error == "invalid_key"

async def test_incr_existing_integer_value(store):
    await store.set("counter", "5")

    response = await handle(
        Request(command=Command.INCR, key="counter"),
        store,
    )

    assert response.status == "success"
    assert response.value == "6"
    assert store.get("counter") == "6"
    
async def test_incr_missing_key_starts_from_zero(store):

    response = await handle(
        Request(command=Command.INCR, key="counter"),
        store,
    )

    assert response.status == "success"
    assert response.value == "1"
    assert store.get("counter") == "1"

async def test_incr_non_integer_value_returns_error(store):
    await store.set("counter", "Player")

    response = await handle(
        Request(command=Command.INCR, key="counter"),
        store,
    )

    assert response.status == "error"
    assert response.error == "not_an_integer"
    assert store.get("counter") == "Player"
