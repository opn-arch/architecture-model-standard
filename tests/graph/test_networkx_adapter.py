"""Tests for the NetworkX graph export adapter (Stage 1)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("networkx")
import networkx as nx  # noqa: E402

from architecture_model.graph import (  # noqa: E402
    BUCKET_ORDER,
    EDGE_TYPES,
    SEMANTIC_FIELDS,
    to_networkx,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _empty_model() -> dict:
    return {"meta": {}, "entities": {}, "relationships": []}


def _tiny_model() -> dict:
    """Small model exercising all 7 core kinds + parallel typed edges +
    promises + evidence."""
    return {
        "meta": {"project": "tiny"},
        "entities": {
            "capabilities": [
                {
                    "id": "CAP-A",
                    "name": "Cap A",
                    "status": "ACTIVE",
                    "intent": "test cap",
                    "owner": "alice",
                    "promises": [
                        {
                            "id": "P1",
                            "attribute": "throughput",
                            "content": "1000rps",
                            "status": "promised",
                            "confidence": 0.9,
                            "verified_by": ["evidence://bench/2026-01"],
                        },
                        {
                            "id": "P2",
                            "attribute": "latency",
                            "content": "10ms",
                            "status": "unverified",
                            "verified_by": [
                                {"uri": "evidence://bench/2026-02", "kind": "sil"},
                                "evidence://bench/2026-01",  # dedup target
                            ],
                        },
                    ],
                },
                {"id": "CAP-B", "name": "Cap B", "status": "ACTIVE"},
            ],
            "components": [
                {"id": "COMP-1", "name": "Comp1", "status": "ACTIVE"},
                {"id": "COMP-2", "name": "Comp2", "status": "ACTIVE"},
            ],
            "behaviors": [{"id": "BEH-1", "name": "Beh1", "status": "ACTIVE"}],
            "interfaces": [{"id": "IF-1", "name": "If1", "status": "ACTIVE"}],
            "actors": [{"id": "ACT-1", "name": "User", "status": "ACTIVE"}],
            "constraints": [{"id": "CON-1", "name": "Con1", "status": "ACTIVE"}],
            "layers": [{"id": "L-1", "name": "Layer1", "status": "ACTIVE"}],
        },
        "relationships": [
            {"from": "COMP-1", "to": "CAP-A", "type": "realizes", "weight": 3},
            {"from": "COMP-1", "to": "COMP-2", "type": "depends-on",
             "weight": 2, "note": "runtime"},
            # Parallel typed edges (browse regression):
            {"from": "CAP-A", "to": "CAP-B", "type": "contains"},
            {"from": "CAP-A", "to": "CAP-B", "type": "triggers"},
            {"from": "ACT-1", "to": "BEH-1", "type": "consumes"},
            {"from": "COMP-1", "to": "CON-1", "type": "constrained-by"},
        ],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_empty_model_produces_empty_graph():
    G = to_networkx(_empty_model())
    assert isinstance(G, nx.MultiDiGraph)
    assert G.number_of_nodes() == 0
    assert G.number_of_edges() == 0


def test_all_seven_kinds_become_nodes():
    G = to_networkx(_tiny_model(), promises_as_nodes=False)
    entity_kinds = {
        d["kind"] for _, d in G.nodes(data=True)
        if d.get("kind") not in ("promise", "evidence")
    }
    expected = {
        "capability", "component", "behavior", "interface",
        "actor", "constraint", "layer",
    }
    assert expected.issubset(entity_kinds)


def test_relationships_survive_as_typed_edges():
    G = to_networkx(_tiny_model(), promises_as_nodes=False)
    types_seen = {d.get("type") for _, _, d in G.edges(data=True)}
    assert {
        "realizes", "depends-on", "contains", "triggers",
        "consumes", "constrained-by",
    }.issubset(types_seen)


def test_parallel_typed_edges_preserved_browse_regression():
    """CAP-A → CAP-B has BOTH 'contains' and 'triggers'. Both must survive."""
    G = to_networkx(_tiny_model(), promises_as_nodes=False)
    keys = set(G.get_edge_data("CAP-A", "CAP-B").keys())
    assert keys == {"contains", "triggers"}


def test_promises_promoted_to_sub_nodes():
    G = to_networkx(_tiny_model(), promises_as_nodes=True)
    assert "CAP-A#p0" in G.nodes
    assert "CAP-A#p1" in G.nodes
    assert G.nodes["CAP-A#p0"]["kind"] == "promise"
    assert G.nodes["CAP-A#p0"]["attr"] == "throughput"
    assert G.nodes["CAP-A#p0"]["owner_id"] == "CAP-A"


def test_has_promise_edges_created():
    G = to_networkx(_tiny_model(), promises_as_nodes=True)
    data = G.get_edge_data("CAP-A", "CAP-A#p0")
    assert "has-promise" in data
    assert data["has-promise"]["type"] == "has-promise"


def test_evidence_deduped_by_uri():
    """P1 references evidence://bench/2026-01; P2 references it AGAIN plus a
    new one. Should get exactly 2 evidence nodes."""
    G = to_networkx(_tiny_model(), promises_as_nodes=True)
    ev_nodes = [n for n, d in G.nodes(data=True) if d.get("kind") == "evidence"]
    assert len(ev_nodes) == 2
    uris = {G.nodes[n]["uri"] for n in ev_nodes}
    assert uris == {"evidence://bench/2026-01", "evidence://bench/2026-02"}


def test_verified_by_edges_created():
    G = to_networkx(_tiny_model(), promises_as_nodes=True)
    # P1 → 1 evidence; P2 → 2 evidence refs (one deduped)
    p1_edges = [
        (u, v) for u, v, k in G.out_edges("CAP-A#p0", keys=True)
        if k == "verified-by"
    ]
    p2_edges = [
        (u, v) for u, v, k in G.out_edges("CAP-A#p1", keys=True)
        if k == "verified-by"
    ]
    assert len(p1_edges) == 1
    assert len(p2_edges) == 2


def test_no_promises_flag_omits_promotion():
    G = to_networkx(_tiny_model(), promises_as_nodes=False)
    assert "CAP-A#p0" not in G.nodes
    types = {d.get("type") for _, _, d in G.edges(data=True)}
    assert "has-promise" not in types
    assert "verified-by" not in types


def test_semantic_fields_carried_on_nodes():
    G = to_networkx(_tiny_model(), include_semantic_fields=True)
    assert G.nodes["CAP-A"]["intent"] == "test cap"
    assert G.nodes["CAP-A"]["owner"] == "alice"


def test_no_semantic_flag_omits_bag():
    G = to_networkx(_tiny_model(), include_semantic_fields=False)
    for field in SEMANTIC_FIELDS:
        assert field not in G.nodes["CAP-A"]


def test_edge_extras_propagated():
    """weight, note, and any other relationship-level attrs land on edges."""
    G = to_networkx(_tiny_model(), promises_as_nodes=False)
    e = G.get_edge_data("COMP-1", "COMP-2")["depends-on"]
    assert e["weight"] == 2
    assert e["note"] == "runtime"
    e2 = G.get_edge_data("COMP-1", "CAP-A")["realizes"]
    assert e2["weight"] == 3


def test_determinism_two_builds_identical_ordering():
    m = _tiny_model()
    G1 = to_networkx(m)
    G2 = to_networkx(m)
    assert list(G1.nodes) == list(G2.nodes)
    assert list(G1.edges(keys=True)) == list(G2.edges(keys=True))


def test_missing_networkx_raises_actionable_error(monkeypatch):
    """Simulate networkx absence via import hook."""
    import architecture_model.graph.networkx_adapter as adapter

    def _boom():
        raise ImportError(
            "networkx is required for graph export. Install with:\n"
            "  pip install 'architecture-model-standard[graph]'"
        )

    monkeypatch.setattr(adapter, "_import_networkx", _boom)
    with pytest.raises(ImportError, match="architecture-model-standard\\[graph\\]"):
        adapter.to_networkx(_tiny_model())


def test_edge_types_frozenset_covers_synthetic():
    assert "has-promise" in EDGE_TYPES
    assert "verified-by" in EDGE_TYPES
    assert "realizes" in EDGE_TYPES
    assert "contains" in EDGE_TYPES


def test_bucket_order_stable():
    assert BUCKET_ORDER[0] == "capabilities"
    assert "environments" in BUCKET_ORDER
    assert "resources" in BUCKET_ORDER


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------


def _write_model_yaml(path: Path, model: dict) -> None:
    import yaml
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(model, fh, sort_keys=False)


def test_cli_export_graphml_writes_file(tmp_path):
    model_path = tmp_path / ".architecture-model.v3.yaml"
    _write_model_yaml(model_path, _tiny_model())
    out = tmp_path / "out.graphml"
    result = subprocess.run(
        [
            sys.executable, "-m", "architecture_model",
            "export-graph", str(model_path),
            "-f", "graphml", "-o", str(out),
        ],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()
    # Round-trip via networkx to verify readability.
    G = nx.read_graphml(str(out))
    assert G.number_of_nodes() > 0
    assert G.number_of_edges() > 0


def test_cli_stats_prints_counts(tmp_path):
    model_path = tmp_path / ".architecture-model.v3.yaml"
    _write_model_yaml(model_path, _tiny_model())
    result = subprocess.run(
        [
            sys.executable, "-m", "architecture_model",
            "export-graph", str(model_path), "--stats",
        ],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert "nodes:" in result.stdout
    assert "edges:" in result.stdout
    assert "by-node-kind:" in result.stdout
    assert "by-edge-type:" in result.stdout
