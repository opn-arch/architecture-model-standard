"""Tests for the WalkSpec YAML loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from architecture_model.walks.spec.loader import (
    WalkSpecError,
    load_walk_specs_from_dir,
    parse_walk_spec,
)


def test_parse_minimal_spec() -> None:
    raw = {
        "walk": {
            "id": "WALK-x",
            "audits": ["CAP-A"],
            "scope": {"kind": "capability"},
        }
    }
    spec = parse_walk_spec(raw)
    assert spec.id == "WALK-x"
    assert spec.audits == ("CAP-A",)
    assert spec.scope.kind == "capability"
    assert spec.rollup is None


def test_parse_full_spec() -> None:
    raw = {
        "walk": {
            "id": "WALK-full",
            "audits": ["CAP-A", "CAP-B"],
            "scope": {"kind": "component", "predicate": "has:intent"},
            "traverse": {"edges": ["contains"], "direction": "outbound", "depth": 2},
            "classify": {
                "verdicts": [
                    {"name": "ready-to-code", "when": "has:promises and has:intent"},
                    {"name": "needs-enrichment", "when": "missing:intent"},
                ],
                "on_missing_attributes": "needs-enrichment",
            },
            "rollup": {"via": "contains", "category": "C", "strategy": "any-child-ok"},
            "evidence": {"tier": "semantic", "sources": ["model", "tests"]},
            "emit": {"card_template": "custom", "severity_from": "verdict"},
        }
    }
    spec = parse_walk_spec(raw)
    assert spec.audits == ("CAP-A", "CAP-B")
    assert spec.traverse.edges == ("contains",)
    assert spec.traverse.depth == 2
    assert len(spec.classify.verdicts) == 2
    assert spec.classify.verdicts[0].name == "ready-to-code"
    assert spec.rollup is not None
    assert spec.rollup.strategy == "any-child-ok"
    assert spec.evidence.tier == "semantic"


def test_parse_missing_id_raises() -> None:
    with pytest.raises(WalkSpecError):
        parse_walk_spec({"walk": {"scope": {"kind": "capability"}}})


def test_parse_bad_id_prefix_raises() -> None:
    with pytest.raises(WalkSpecError):
        parse_walk_spec(
            {"walk": {"id": "BAD-x", "scope": {"kind": "capability"}}}
        )


def test_parse_missing_scope_raises() -> None:
    with pytest.raises(WalkSpecError):
        parse_walk_spec({"walk": {"id": "WALK-x"}})


def test_parse_audits_scalar_wrapped() -> None:
    spec = parse_walk_spec(
        {"walk": {"id": "WALK-x", "audits": "CAP-A", "scope": {"kind": "capability"}}}
    )
    assert spec.audits == ("CAP-A",)


def test_parse_unbounded_depth() -> None:
    spec = parse_walk_spec(
        {
            "walk": {
                "id": "WALK-x",
                "scope": {"kind": "capability"},
                "traverse": {"depth": "unbounded"},
            }
        }
    )
    assert spec.traverse.depth is None


def test_load_from_dir_cycle_detected(tmp_path: Path) -> None:
    (tmp_path / "a.v3.yaml").write_text(
        """
walk:
  id: WALK-a
  scope: {kind: capability, from_walk: WALK-b}
""".strip()
    )
    (tmp_path / "b.v3.yaml").write_text(
        """
walk:
  id: WALK-b
  scope: {kind: capability, from_walk: WALK-a}
""".strip()
    )
    with pytest.raises(WalkSpecError, match="composition cycle"):
        load_walk_specs_from_dir(tmp_path)


def test_load_from_dir_no_cycle(tmp_path: Path) -> None:
    (tmp_path / "a.v3.yaml").write_text(
        """
walk:
  id: WALK-a
  scope: {kind: capability}
""".strip()
    )
    (tmp_path / "b.v3.yaml").write_text(
        """
walk:
  id: WALK-b
  scope: {kind: capability, from_walk: WALK-a}
""".strip()
    )
    specs = load_walk_specs_from_dir(tmp_path)
    assert len(specs) == 2
    assert {s.id for s in specs} == {"WALK-a", "WALK-b"}
