"""Tests for SI&L Run History panel in the viewer."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

import pytest

from architecture_model.core.parser import _parse_raw
from architecture_model.core.visualize import _load_sil_data, generate_html_viewer


class _ScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self._current = None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self._current = {"type": dict(attrs).get("type"), "text": ""}

    def handle_data(self, data):
        if self._current is not None:
            self._current["text"] += data

    def handle_endtag(self, tag):
        if tag == "script" and self._current is not None:
            self.scripts.append(self._current)
            self._current = None


def _viewer_data(html: str) -> dict:
    parser = _ScriptParser()
    parser.feed(html)
    return json.loads(
        next(s["text"] for s in parser.scripts if s["type"] == "application/json")
    )


def _minimal_model():
    return _parse_raw(
        {
            "meta": {"project": "sil-test", "schema_version": "1.3"},
            "entities": {
                "components": [
                    {"id": "COMP-1", "name": "Alpha", "status": "ACTIVE"},
                    {"id": "COMP-2", "name": "Beta", "status": "ACTIVE"},
                ],
            },
            "relationships": [],
        }
    )


def _seed_sil(db_path: Path, events: list[tuple[str, str, str, int, str, str]]) -> None:
    """Seed sqlite with rows: (component_id, ts, kind, duration_ms, outcome, ref)."""
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE sil_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            kind TEXT NOT NULL,
            outcome TEXT NOT NULL,
            duration_ms INTEGER NOT NULL,
            ref TEXT
        );
        """
    )
    conn.executemany(
        "INSERT INTO sil_events (component_id, ts, kind, outcome, duration_ms, ref) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [(cid, ts, kind, outcome, dur, ref) for cid, ts, kind, dur, outcome, ref in events],
    )
    conn.commit()
    conn.close()


def test_load_sil_data_returns_empty_when_missing(tmp_path):
    assert _load_sil_data(None) == {}
    assert _load_sil_data(tmp_path / "does_not_exist.sqlite") == {}


def test_load_sil_data_ignores_wrong_schema(tmp_path):
    db = tmp_path / "sil.sqlite"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE unrelated (x TEXT)")
    conn.commit()
    conn.close()
    assert _load_sil_data(db) == {}


def test_load_sil_data_aggregates_and_computes_trend(tmp_path):
    db = tmp_path / "sil.sqlite"
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(days=1)).isoformat()
    older = (now - timedelta(days=10)).isoformat()
    _seed_sil(
        db,
        [
            ("COMP-1", recent, "stage", 100, "ok", "run-1"),
            ("COMP-1", recent, "stage", 200, "ok", "run-2"),
            ("COMP-1", recent, "stage", 300, "error", "run-3"),
            ("COMP-1", older, "stage", 100, "ok", "run-old"),
        ],
    )
    result = _load_sil_data(db)
    assert set(result) == {"COMP-1"}
    m = result["COMP-1"]["metrics"]
    assert m["invocations_7d"] == 3
    assert m["failure_rate_7d"] == pytest.approx(1 / 3, rel=1e-3)
    assert m["avg_duration_ms"] == pytest.approx(200.0)
    assert result["COMP-1"]["trend"] == "up"  # 3 recent vs 1 prior
    assert len(result["COMP-1"]["recent_events"]) == 4


def test_viewer_omits_sil_section_when_no_data(tmp_path):
    out = tmp_path / "viewer.html"
    generate_html_viewer(_minimal_model(), out, repo_path=tmp_path)
    data = _viewer_data(out.read_text())
    assert data.get("sil_by_component") == {}


def test_viewer_embeds_sil_data_when_present(tmp_path):
    arch_dir = tmp_path / ".architecture"
    arch_dir.mkdir()
    db = arch_dir / "sil.sqlite"
    now = datetime.now(timezone.utc)
    ts = (now - timedelta(hours=1)).isoformat()
    _seed_sil(
        db,
        [
            ("COMP-1", ts, "stage", 50, "ok", "run-a"),
            ("COMP-1", ts, "stage", 60, "ok", "run-b"),
        ],
    )
    out = tmp_path / "viewer.html"
    generate_html_viewer(_minimal_model(), out, repo_path=tmp_path, sil_store_path=db)
    html = out.read_text()
    data = _viewer_data(html)
    assert "COMP-1" in data["sil_by_component"]
    assert data["sil_by_component"]["COMP-1"]["metrics"]["invocations_7d"] == 2
    # JS-side markers rendered
    assert "silRunHistoryHtml" in html
    assert "sil-badge" in html
    assert "Run History" in html


def test_viewer_component_without_sil_events_has_no_entry(tmp_path):
    arch_dir = tmp_path / ".architecture"
    arch_dir.mkdir()
    db = arch_dir / "sil.sqlite"
    now = datetime.now(timezone.utc)
    ts = (now - timedelta(hours=1)).isoformat()
    _seed_sil(db, [("COMP-1", ts, "stage", 50, "ok", "run-a")])
    out = tmp_path / "viewer.html"
    generate_html_viewer(_minimal_model(), out, repo_path=tmp_path, sil_store_path=db)
    data = _viewer_data(out.read_text())
    assert "COMP-1" in data["sil_by_component"]
    assert "COMP-2" not in data["sil_by_component"]
