import json

import pytest

from kvstore.domain import KeyValueStore
from kvstore.expiration import ExpirationRegistry
from kvstore.persistence.append_log import AppendLog, replay_log
from kvstore.persistence.recovery import recover
from kvstore.persistence.snapshot import write_snapshot


def test_values_survive_log_replay(tmp_path):
    log_path = tmp_path / "kvstore.log"
    log = AppendLog(log_path)
    log.append_set("name", "Player")
    log.append_set("score", "50")
    log.close()

    engine = KeyValueStore()
    replay_log(log_path, engine, ExpirationRegistry())

    assert engine.get("name") == "Player"
    assert engine.get("score") == "50"


def test_overwritten_values_recover_correctly(tmp_path):
    log_path = tmp_path / "kvstore.log"
    log = AppendLog(log_path)
    log.append_set("name", "Player")
    log.append_set("name", "Player2")
    log.close()

    engine = KeyValueStore()
    replay_log(log_path, engine, ExpirationRegistry())

    assert engine.get("name") == "Player2"


def test_deleted_keys_remain_deleted_after_replay(tmp_path):
    log_path = tmp_path / "kvstore.log"
    log = AppendLog(log_path)
    log.append_set("name", "Player")
    log.append_delete("name")
    log.close()

    engine = KeyValueStore()
    replay_log(log_path, engine, ExpirationRegistry())

    assert engine.get("name") is None


def test_read_commands_are_never_written_to_log(tmp_path):
    log_path = tmp_path / "kvstore.log"
    log = AppendLog(log_path)
    log.append_set("name", "Player")
    log.close()

    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["operation"] == "SET"


def test_incomplete_final_log_record_does_not_destroy_earlier_data(tmp_path):
    log_path = tmp_path / "kvstore.log"
    log = AppendLog(log_path)
    log.append_set("name", "Player")
    log.close()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write('{"operation":"SET","key":"broke')

    engine = KeyValueStore()
    replay_log(log_path, engine, ExpirationRegistry())

    assert engine.get("name") == "Player"


def test_recover_rebuilds_expected_state_from_log(tmp_path):
    log_path = tmp_path / "kvstore.log"
    snapshot_path = tmp_path / "snapshot.json"
    log = AppendLog(log_path)
    log.append_set("a", "1")
    log.append_set("b", "2")
    log.append_delete("a")
    log.close()

    engine = KeyValueStore()
    expirations = ExpirationRegistry()
    recover(engine, expirations, snapshot_path, log_path)

    assert engine.get("a") is None
    assert engine.get("b") == "2"

def test_snapshot_contains_correct_state(tmp_path):
    engine = KeyValueStore()
    engine.set("name", "Player")
    engine.set("score", "100")
    expirations = ExpirationRegistry()
    expirations.set_expiry("session:123", 1_785_866_400.0)

    snapshot_path = tmp_path / "snapshot.json"
    write_snapshot(snapshot_path, engine, expirations)

    payload = json.loads(snapshot_path.read_text())
    assert payload["data"] == {"name": "Player", "score": "100"}
    assert payload["expirations"] == {"session:123": 1_785_866_400.0}


def test_recovery_works_from_snapshot_alone(tmp_path):
    engine = KeyValueStore()
    engine.set("name", "Player")
    expirations = ExpirationRegistry()
    snapshot_path = tmp_path / "snapshot.json"
    write_snapshot(snapshot_path, engine, expirations)

    recovered_engine = KeyValueStore()
    recovered_expirations = ExpirationRegistry()
    recover(recovered_engine, recovered_expirations, snapshot_path, tmp_path / "kvstore.log")

    assert recovered_engine.get("name") == "Player"


def test_recovery_works_from_snapshot_plus_newer_log_entries(tmp_path):
    engine = KeyValueStore()
    engine.set("name", "Player")
    expirations = ExpirationRegistry()
    snapshot_path = tmp_path / "snapshot.json"
    write_snapshot(snapshot_path, engine, expirations)

    log_path = tmp_path / "kvstore.log"
    log = AppendLog(log_path)
    log.append_set("score", "50")
    log.close()

    recovered_engine = KeyValueStore()
    recovered_expirations = ExpirationRegistry()
    recover(recovered_engine, recovered_expirations, snapshot_path, log_path)

    assert recovered_engine.get("name") == "Player"
    assert recovered_engine.get("score") == "50"


def test_expired_keys_are_not_restored_from_snapshot(tmp_path):
    def clock() -> float:
        return 1_700_000_100.0

    engine = KeyValueStore()
    engine.set("session:123", "abc")
    expirations = ExpirationRegistry(clock=clock)
    expirations.set_expiry("session:123", 1_700_000_000.0)  # already in the past
    snapshot_path = tmp_path / "snapshot.json"
    write_snapshot(snapshot_path, engine, expirations)

    recovered_engine = KeyValueStore()
    recovered_expirations = ExpirationRegistry(clock=clock)
    recover(recovered_engine, recovered_expirations, snapshot_path, tmp_path / "kvstore.log")

    assert recovered_engine.get("session:123") is None


def test_failed_temporary_snapshot_does_not_replace_valid_snapshot(tmp_path, monkeypatch):
    engine = KeyValueStore()
    engine.set("name", "Player")
    expirations = ExpirationRegistry()
    snapshot_path = tmp_path / "snapshot.json"
    write_snapshot(snapshot_path, engine, expirations)
    original_contents = snapshot_path.read_text()

    def _boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("kvstore.persistence.snapshot.os.fsync", _boom)

    engine.set("name", "Player2")
    with pytest.raises(OSError):
        write_snapshot(snapshot_path, engine, expirations)

    assert snapshot_path.read_text() == original_contents


def test_compacted_log_produces_identical_recovered_state(tmp_path):
    log_path = tmp_path / "kvstore.log"
    snapshot_path = tmp_path / "snapshot.json"

    engine = KeyValueStore()
    expirations = ExpirationRegistry()
    log = AppendLog(log_path)
    log.append_set("a", "1")
    log.append_set("b", "2")
    log.append_set("a", "3")

    engine.set("a", "3")
    engine.set("b", "2")
    write_snapshot(snapshot_path, engine, expirations)
    log.reset()
    log.close()

    recovered_engine = KeyValueStore()
    recovered_expirations = ExpirationRegistry()
    recover(recovered_engine, recovered_expirations, snapshot_path, log_path)

    assert recovered_engine.get("a") == "3"
    assert recovered_engine.get("b") == "2"