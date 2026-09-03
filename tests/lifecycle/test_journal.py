"""Tests for lifecycle.journal."""

from __future__ import annotations

import json
from pathlib import Path

from architecture_model.lifecycle import journal as jmod


def test_record_returns_id_and_appends_line(tmp_path: Path) -> None:
    j = jmod.Journal(tmp_path / "j.jsonl")
    eid = j.record("evt.one", {"k": 1})
    assert isinstance(eid, str) and len(eid) == 32
    lines = (tmp_path / "j.jsonl").read_text().splitlines()
    assert len(lines) == 1
    j.record("evt.two", {"k": 2})
    lines = (tmp_path / "j.jsonl").read_text().splitlines()
    assert len(lines) == 2


def test_record_json_line_shape(tmp_path: Path) -> None:
    j = jmod.Journal(tmp_path / "j.jsonl")
    j.record("evt.shape", {"a": 1})
    line = (tmp_path / "j.jsonl").read_text().splitlines()[0]
    obj = json.loads(line)
    assert set(obj.keys()) == {"id", "ts", "event", "payload"}
    assert obj["event"] == "evt.shape"
    assert obj["payload"] == {"a": 1}
    assert obj["ts"].endswith("Z") or "+" in obj["ts"]


def test_replay_yields_in_order(tmp_path: Path) -> None:
    j = jmod.Journal(tmp_path / "j.jsonl")
    ids = [j.record(f"e.{i}", {"i": i}) for i in range(3)]
    got = list(j.replay())
    assert [e["id"] for e in got] == ids


def test_replay_since_filter(tmp_path: Path) -> None:
    j = jmod.Journal(tmp_path / "j.jsonl")
    a = j.record("a", {})
    b = j.record("b", {})
    c = j.record("c", {})
    got = list(j.replay(since=a))
    assert [e["id"] for e in got] == [b, c]


def test_replay_missing_file_yields_empty(tmp_path: Path) -> None:
    j = jmod.Journal(tmp_path / "missing.jsonl")
    assert list(j.replay()) == []


def test_standard_event_kinds_are_strings() -> None:
    assert jmod.PACKAGE_PUBLISH_BEGIN == "package.publish.begin"
    assert jmod.PACKAGE_PUBLISH_COMMIT == "package.publish.commit"
    assert jmod.PACKAGE_PUBLISH_ABORT == "package.publish.abort"
    assert jmod.STORE_WRITE_BEGIN == "store.write.begin"
    assert jmod.STORE_WRITE_COMMIT == "store.write.commit"
    assert jmod.INDEX_REBUILD_COMMIT == "index.rebuild.commit"
