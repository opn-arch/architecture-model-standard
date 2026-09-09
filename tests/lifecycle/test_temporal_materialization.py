"""Tests for materializer wiring of temporal fields (Phase 2 Task 12)."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from textwrap import dedent

import pytest

from architecture_model.lifecycle.model_slice import (
    Curation,
    ModelSlice,
    RevisionRange,
    Selectors,
    SupplementaryRef,
    TimeWindow,
)
from architecture_model.lifecycle.model_slice_materializer import (
    ModelRevisionFragment,
    materialize,
)
from architecture_model.lifecycle.package import load_package


PKG_YAML = dedent(
    """\
    architecture_id: root-pkg
    name: Root
    slug: root-pkg
    contract_version: "1.0.0"
    model_ref: .architecture-model.yaml
    manifest_ref: manifest.json
    """
)


def _model_yaml(components: list[tuple[str, str]]) -> str:
    """Compose a minimal model YAML with the given (id, name) components."""
    header = dedent(
        """\
        meta:
          schema_version: '2.1.0'
          project: root
        entities:
          components:
        """
    )
    body = "".join(
        f"    - id: {cid}\n      name: {cname}\n      status: ACTIVE\n"
        for cid, cname in components
    )
    return header + body + "relationships: []\n"


def _write_generation(root: Path, n: int, components: list[tuple[str, str]]):
    gen_dir = root / "generations" / f"{n:07d}" / "model"
    gen_dir.mkdir(parents=True, exist_ok=True)
    (gen_dir / ".architecture-model.yaml").write_text(_model_yaml(components))


def _seed_sil(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE sil_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            kind TEXT, outcome TEXT, duration_ms REAL, ref TEXT
        )
        """
    )
    rows = [
        ("COMP-A", "2026-07-01T00:00:00Z", "s", "ok", 1.0, ""),  # before window
        ("COMP-A", "2026-08-05T00:00:00Z", "s", "ok", 2.0, ""),  # inside
        ("COMP-A", "2026-08-06T00:00:00Z", "s", "error", 3.0, ""),  # inside
        ("COMP-A", "2026-09-01T00:00:00Z", "s", "ok", 4.0, ""),  # after window
    ]
    conn.executemany(
        "INSERT INTO sil_events (component_id, ts, kind, outcome, duration_ms, ref) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


@pytest.fixture
def pkg_with_history(tmp_path: Path):
    """Package with three published generations."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "package.yaml").write_text(PKG_YAML)
    # Current model = last generation contents (COMP-A + COMP-B + COMP-C)
    (root / ".architecture-model.yaml").write_text(
        _model_yaml([("COMP-A", "Alpha"), ("COMP-B", "Bravo"), ("COMP-C", "Charlie")])
    )
    (root / "manifest.json").write_text("{}")

    _write_generation(root, 1, [("COMP-A", "Alpha")])
    _write_generation(root, 2, [("COMP-A", "Alpha"), ("COMP-B", "Bravo")])
    _write_generation(
        root, 3, [("COMP-A", "Alpha"), ("COMP-B", "Bravo"), ("COMP-C", "Charlie")]
    )
    _seed_sil(root / ".architecture" / "sil.sqlite")
    return load_package(root)


@pytest.fixture
def pkg_no_history(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "package.yaml").write_text(PKG_YAML)
    (root / ".architecture-model.yaml").write_text(
        _model_yaml([("COMP-A", "Alpha")])
    )
    (root / "manifest.json").write_text("{}")
    return load_package(root)


def _slice(**overrides):
    kwargs = dict(
        id="s1",
        architecture_id="root-pkg",
        model_revision="rev-1",
        scope="local",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_kinds=["component"]),
        curation=Curation(),
    )
    kwargs.update(overrides)
    return ModelSlice(**kwargs)


# ---------------------------------------------------------------------------
# revision_range → revision_series
# ---------------------------------------------------------------------------

def test_no_revision_range_leaves_series_empty(pkg_with_history):
    ms = materialize(_slice(), pkg_with_history)
    assert ms.revision_series == ()


def test_revision_range_loads_each_generation(pkg_with_history):
    slc = _slice(revision_range=RevisionRange(from_="0000001", to="0000003"))
    ms = materialize(slc, pkg_with_history)
    assert len(ms.revision_series) == 3
    assert [f.revision for f in ms.revision_series] == [
        "0000001",
        "0000002",
        "0000003",
    ]
    # Component growth is visible across revisions.
    counts = [len(f.model_fragment.entities.components) for f in ms.revision_series]
    assert counts == [1, 2, 3]


def test_revision_range_applies_selectors(pkg_with_history):
    slc = _slice(
        selectors=Selectors(entity_ids=["COMP-A"]),
        revision_range=RevisionRange(from_="0000001", to="0000003"),
    )
    ms = materialize(slc, pkg_with_history)
    for frag in ms.revision_series:
        ids = {c.id for c in frag.model_fragment.entities.components}
        assert ids == {"COMP-A"}


def test_revision_range_narrow_window(pkg_with_history):
    slc = _slice(revision_range=RevisionRange(from_="0000002", to="0000002"))
    ms = materialize(slc, pkg_with_history)
    assert len(ms.revision_series) == 1
    assert ms.revision_series[0].revision == "0000002"


def test_missing_generation_emits_warning(pkg_no_history):
    """Range 1..2 with no publications yields two REVISION_MISSING warnings."""
    slc = _slice(revision_range=RevisionRange(from_="0000001", to="0000002"))
    ms = materialize(slc, pkg_no_history)
    assert ms.revision_series == ()
    codes = [w.code for w in ms.warnings]
    assert codes.count("SLICE.REVISION_MISSING") == 2


def test_partial_missing_range_returns_what_exists(pkg_with_history):
    """Range 2..5 with only 2 & 3 present returns those two and warns for 4, 5."""
    slc = _slice(revision_range=RevisionRange(from_="0000002", to="0000005"))
    ms = materialize(slc, pkg_with_history)
    assert [f.revision for f in ms.revision_series] == ["0000002", "0000003"]
    missing_msgs = [
        w.message for w in ms.warnings if w.code == "SLICE.REVISION_MISSING"
    ]
    assert len(missing_msgs) == 2  # 0000004, 0000005


def test_revision_series_is_deterministic(pkg_with_history):
    slc = _slice(revision_range=RevisionRange(from_="0000001", to="0000003"))
    a = materialize(slc, pkg_with_history)
    b = materialize(slc, pkg_with_history)
    assert [f.revision for f in a.revision_series] == [
        f.revision for f in b.revision_series
    ]


# ---------------------------------------------------------------------------
# time_window → sil filter injection
# ---------------------------------------------------------------------------

def test_time_window_filters_sil_events(pkg_with_history):
    slc = _slice(
        supplementary_refs=(SupplementaryRef(kind="sil"),),
        time_window=TimeWindow(
            from_="2026-08-01T00:00:00Z", to="2026-08-15T00:00:00Z"
        ),
    )
    ms = materialize(slc, pkg_with_history)
    sil = ms.supplementary_fragments["sil"]
    # Only the two events inside the window survive.
    assert len(sil.events) == 2
    assert all(
        "2026-08-01T00:00:00Z" <= ev.ts < "2026-08-15T00:00:00Z"
        for ev in sil.events
    )


def test_explicit_ref_filter_wins_over_time_window(pkg_with_history):
    """SupplementaryRef.filter.since takes precedence over slice.time_window.from_."""
    slc = _slice(
        supplementary_refs=(
            SupplementaryRef(kind="sil", filter={"since": "2026-08-06T00:00:00Z"}),
        ),
        time_window=TimeWindow(
            from_="2026-08-01T00:00:00Z", to="2026-09-15T00:00:00Z"
        ),
    )
    ms = materialize(slc, pkg_with_history)
    sil = ms.supplementary_fragments["sil"]
    # Explicit since='2026-08-06' + inherited until='2026-09-15' → only 1 event (2026-08-06)
    assert all(ev.ts >= "2026-08-06T00:00:00Z" for ev in sil.events)
    assert all(ev.ts < "2026-09-15T00:00:00Z" for ev in sil.events)


def test_time_window_without_sil_ref_is_noop(pkg_with_history):
    """time_window alone (no supplementary refs) doesn't crash and produces no fragments."""
    slc = _slice(
        time_window=TimeWindow(
            from_="2026-08-01T00:00:00Z", to="2026-08-15T00:00:00Z"
        ),
    )
    ms = materialize(slc, pkg_with_history)
    assert ms.supplementary_fragments == {}
    assert ms.revision_series == ()
