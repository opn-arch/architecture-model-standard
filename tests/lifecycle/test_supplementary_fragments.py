"""Tests for supplementary_fragments wiring (Phase 2 Task 10).

Covers ``sil`` end-to-end against a real SQLite fixture, plus stub
behaviour for ``gates`` / ``drift`` / ``test_results`` / ``learning``.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from textwrap import dedent

import pytest

from architecture_model.lifecycle.model_slice import (
    Curation,
    ModelSlice,
    Selectors,
    SupplementaryRef,
)
from architecture_model.lifecycle.model_slice_materializer import materialize
from architecture_model.lifecycle.package import load_package
from architecture_model.lifecycle.supplementary_loaders import (
    SILEvent,
    SILFragment,
    load_sil,
)


MODEL_YAML = dedent(
    """\
    meta:
      schema_version: '2.1.0'
      project: root
    entities:
      components:
        - id: COMP-A
          name: Alpha
          status: ACTIVE
        - id: COMP-B
          name: Bravo
          status: ACTIVE
    relationships: []
    """
)

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


def _seed_sil(db_path: Path) -> None:
    """Create a minimal ``sil_events`` table with a handful of rows."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE sil_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            kind TEXT,
            outcome TEXT,
            duration_ms REAL,
            ref TEXT
        )
        """
    )
    rows = [
        ("COMP-A", "2026-08-01T00:00:00Z", "stage:observe", "ok", 12.5, ""),
        ("COMP-A", "2026-08-02T00:00:00Z", "stage:observe", "ok", 15.0, ""),
        ("COMP-A", "2026-08-03T00:00:00Z", "stage:observe", "error", 999.0, "boom"),
        ("COMP-B", "2026-08-01T00:00:00Z", "stage:emit", "ok", 5.0, ""),
        ("COMP-B", "2026-08-04T00:00:00Z", "stage:emit", "ok", 7.0, ""),
    ]
    conn.executemany(
        "INSERT INTO sil_events (component_id, ts, kind, outcome, duration_ms, ref) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


@pytest.fixture
def pkg_with_sil(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "package.yaml").write_text(PKG_YAML)
    (root / ".architecture-model.yaml").write_text(MODEL_YAML)
    (root / "manifest.json").write_text("{}")
    _seed_sil(root / ".architecture" / "sil.sqlite")
    return load_package(root)


@pytest.fixture
def pkg_no_sil(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "package.yaml").write_text(PKG_YAML)
    (root / ".architecture-model.yaml").write_text(MODEL_YAML)
    (root / "manifest.json").write_text("{}")
    return load_package(root)


def _slice(**overrides) -> ModelSlice:
    kwargs = dict(
        id="s1",
        architecture_id="root-pkg",
        model_revision="rev-1",
        scope="local",
        closure="strict",
        shared_refs="none",
        selectors=Selectors(entity_ids=["COMP-A", "COMP-B"]),
        curation=Curation(),
    )
    kwargs.update(overrides)
    return ModelSlice(**kwargs)


# ---------------------------------------------------------------------------
# Direct loader tests
# ---------------------------------------------------------------------------

def test_load_sil_missing_db_returns_none(tmp_path):
    assert load_sil(tmp_path) is None


def test_load_sil_reads_all_events(pkg_with_sil):
    frag = load_sil(pkg_with_sil.root)
    assert isinstance(frag, SILFragment)
    assert len(frag.events) == 5
    assert all(isinstance(e, SILEvent) for e in frag.events)


def test_load_sil_filter_by_component_id(pkg_with_sil):
    frag = load_sil(pkg_with_sil.root, filter={"component_id": "COMP-A"})
    assert len(frag.events) == 3
    assert {e.component_id for e in frag.events} == {"COMP-A"}


def test_load_sil_filter_by_since(pkg_with_sil):
    frag = load_sil(pkg_with_sil.root, filter={"since": "2026-08-03T00:00:00Z"})
    assert all(e.ts >= "2026-08-03T00:00:00Z" for e in frag.events)
    assert len(frag.events) == 2


def test_load_sil_summary_counts_and_failures(pkg_with_sil):
    frag = load_sil(pkg_with_sil.root)
    a = frag.summary["COMP-A"]
    b = frag.summary["COMP-B"]
    assert a["invocations"] == 3
    assert a["failures"] == 1
    assert b["invocations"] == 2
    assert b["failures"] == 0


def test_load_sil_rejects_conflicting_filters(pkg_with_sil):
    with pytest.raises(ValueError):
        load_sil(
            pkg_with_sil.root,
            filter={"component_id": "COMP-A", "component_ids": ["COMP-B"]},
        )


# ---------------------------------------------------------------------------
# Materializer integration — sil
# ---------------------------------------------------------------------------

def test_materialize_attaches_sil_fragment(pkg_with_sil):
    slc = _slice(supplementary_refs=(SupplementaryRef(kind="sil"),))
    ms = materialize(slc, pkg_with_sil)
    assert "sil" in ms.supplementary_fragments
    frag = ms.supplementary_fragments["sil"]
    assert isinstance(frag, SILFragment)
    assert len(frag.events) == 5


def test_materialize_sil_with_filter(pkg_with_sil):
    slc = _slice(
        supplementary_refs=(
            SupplementaryRef(kind="sil", filter={"component_id": "COMP-B"}),
        )
    )
    ms = materialize(slc, pkg_with_sil)
    frag = ms.supplementary_fragments["sil"]
    assert {e.component_id for e in frag.events} == {"COMP-B"}


def test_materialize_sil_missing_db_emits_warning(pkg_no_sil):
    slc = _slice(supplementary_refs=(SupplementaryRef(kind="sil"),))
    ms = materialize(slc, pkg_no_sil)
    assert "sil" not in ms.supplementary_fragments
    codes = {w.code for w in ms.warnings}
    assert "SLICE.SUPPLEMENTARY_NOT_AVAILABLE" in codes


def test_materialize_no_supplementary_refs_leaves_dict_empty(pkg_with_sil):
    ms = materialize(_slice(), pkg_with_sil)
    assert ms.supplementary_fragments == {}


# ---------------------------------------------------------------------------
# Stubbed kinds (gates / drift / test_results / learning)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "kind", ["gates", "drift", "test_results", "learning"],
)
def test_stub_kinds_emit_unavailable_warning(pkg_with_sil, kind):
    slc = _slice(supplementary_refs=(SupplementaryRef(kind=kind),))
    ms = materialize(slc, pkg_with_sil)
    assert kind not in ms.supplementary_fragments
    codes = {w.code for w in ms.warnings}
    assert "SLICE.SUPPLEMENTARY_NOT_AVAILABLE" in codes


def test_multiple_refs_partially_resolve(pkg_with_sil):
    """sil resolves; gates emits a warning; both are handled in one pass."""
    slc = _slice(
        supplementary_refs=(
            SupplementaryRef(kind="sil"),
            SupplementaryRef(kind="gates"),
        )
    )
    ms = materialize(slc, pkg_with_sil)
    assert set(ms.supplementary_fragments) == {"sil"}
    assert any(
        w.code == "SLICE.SUPPLEMENTARY_NOT_AVAILABLE" and "gates" in w.message
        for w in ms.warnings
    )
