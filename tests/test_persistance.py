import json

from kvstore.domain import KeyValueStore
from kvstore.persistence.append_log import AppendLog, replay_log
from kvstore.persistence.recovery import recover


def test_values_survive_log_replay(tmp_path):
    log_path = tmp_path / "kvstore.log"
    log = AppendLog(log_path)
    log.append_set("name", "Player")
    log.append_set("score", "50")
    log.close()

    engine = KeyValueStore()
    replay_log(log_path, engine)

    assert engine.get("name") == "Player"
    assert engine.get("score") == "50"


def test_overwritten_values_recover_correctly(tmp_path):
    log_path = tmp_path / "kvstore.log"
    log = AppendLog(log_path)
    log.append_set("name", "Player")
    log.append_set("name", "Player2")
    log.close()

    engine = KeyValueStore()
    replay_log(log_path, engine)

    assert engine.get("name") == "Player2"


def test_deleted_keys_remain_deleted_after_replay(tmp_path):
    log_path = tmp_path / "kvstore.log"
    log = AppendLog(log_path)
    log.append_set("name", "Player")
    log.append_delete("name")
    log.close()

    engine = KeyValueStore()
    replay_log(log_path, engine)

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
    replay_log(log_path, engine)

    assert engine.get("name") == "Player"


def test_recover_rebuilds_expected_state_from_log(tmp_path):
    log_path = tmp_path / "kvstore.log"
    log = AppendLog(log_path)
    log.append_set("a", "1")
    log.append_set("b", "2")
    log.append_delete("a")
    log.close()

    engine = KeyValueStore()
    recover(engine, log_path)

    assert engine.get("a") is None
    assert engine.get("b") == "2"