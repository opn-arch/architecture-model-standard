"""Regression test: canonical model contains Phase B + user-facing UC entities.

Track 3 introduces 2 layers, 5 components, 3 capabilities, 6 interfaces, and
4 user-facing behaviors that cover SI&L, LLM Provider Layer, Pipeline
Dashboard, Comment System, Feedback Journals, plus the four user-facing use
cases (Slice-scoped context, Learning loop, Development loop, Comment-driven
collaboration).

If this test fails, `.architecture-model.yaml` is missing entities the Track 2
Sitting B review flagged as required.
"""
from __future__ import annotations

from pathlib import Path
import yaml

MODEL_PATH = Path(__file__).resolve().parents[1] / ".architecture-model.yaml"


def _load():
    return yaml.safe_load(MODEL_PATH.read_text())


def _ids(model: dict, kind: str) -> set[str]:
    return {e["id"] for e in (model["entities"].get(kind) or [])}


def _rel_pair(r: dict) -> tuple[str | None, str | None]:
    """Normalize relationship endpoints (schema accepts from/to or from_id/to_id)."""
    return (r.get("from") or r.get("from_id"), r.get("to") or r.get("to_id"))


def test_track3_layers_present() -> None:
    ids = _ids(_load(), "layers")
    assert {"LAY-6", "LAY-7"}.issubset(ids), sorted(ids)


def test_track3_components_present() -> None:
    ids = _ids(_load(), "components")
    assert {"COMP-13", "COMP-14", "COMP-15", "COMP-16", "COMP-17"}.issubset(ids), sorted(ids)


def test_track3_capabilities_present() -> None:
    ids = _ids(_load(), "capabilities")
    assert {"CAP-16", "CAP-17", "CAP-18"}.issubset(ids), sorted(ids)


def test_track3_interfaces_present() -> None:
    ids = _ids(_load(), "interfaces")
    assert {f"IF-{n}" for n in range(17, 23)}.issubset(ids), sorted(ids)


def test_track3_user_facing_behaviors_present() -> None:
    ids = _ids(_load(), "behaviors")
    assert {"BEH-26", "BEH-27", "BEH-28", "BEH-29"}.issubset(ids), sorted(ids)


def test_track3_component_layer_containment() -> None:
    """Each new component must be contained by its declared layer."""
    m = _load()
    rels = m["relationships"]
    expected = {
        ("LAY-6", "COMP-13"),  # SI&L in Observability
        ("LAY-6", "COMP-17"),  # Feedback in Observability
        ("LAY-7", "COMP-14"),  # LLM Provider in AI Integration
        ("LAY-4", "COMP-15"),  # Dashboard in Interface layer
        ("LAY-3", "COMP-16"),  # Comment System in Application
    }
    actual = {_rel_pair(r) for r in rels if r.get("type") == "contains"}
    missing = expected - actual
    assert not missing, f"missing contains edges: {missing}"


def test_track3_component_realizes_capability() -> None:
    m = _load()
    rels = m["relationships"]
    expected = {
        ("COMP-16", "CAP-16"),
        ("COMP-13", "CAP-17"),
        ("COMP-14", "CAP-18"),
    }
    actual = {_rel_pair(r) for r in rels if r.get("type") == "realizes"}
    missing = expected - actual
    assert not missing, f"missing realizes edges: {missing}"


def test_track3_model_validates() -> None:
    """After Track 3 edits the model must still be schema-valid."""
    from architecture_model.core.parser import load_model
    from architecture_model.core.validator import validate_model

    model = load_model(MODEL_PATH)
    result = validate_model(model)
    assert result.is_valid, f"score={result.score} issues={[str(i) for i in result.issues[:10]]}"
