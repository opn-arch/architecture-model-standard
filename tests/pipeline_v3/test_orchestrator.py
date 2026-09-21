"""Tests for pipeline_v3.orchestrator — T0.14 Phase 6.8.

orchestrator.py wires scan → derive_promises → cluster → link →
containerize → verify → publish into a single end-to-end run. Exposes:

    PipelineRunResult          # dataclass with all stage outputs
    run_pipeline(repo_path, out_path, ...) -> PipelineRunResult

Optional stage-skipping (skip_publish for in-memory-only runs). The
orchestrator's contract: every intermediate artifact is available on
the returned result so downstream callers can inspect any stage
without re-running.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from architecture_model.pipeline_v3.containerize import ContainerizedModel
from architecture_model.pipeline_v3.orchestrator import (
    PipelineRunResult,
    run_pipeline,
)
from architecture_model.quality.chain_closure import ChainClosureReport


def _make_repo(tmp: Path):
    """Build a tiny two-module repo for smoke testing."""
    (tmp / "pkg").mkdir()
    (tmp / "pkg" / "__init__.py").write_text('"""pkg init."""\n')
    (tmp / "pkg" / "a.py").write_text(
        '"""module a."""\ndef alpha():\n    pass\n'
    )
    (tmp / "pkg" / "b.py").write_text(
        '"""module b."""\n'
        "from pkg import a\n"
        "def beta():\n"
        "    return a.alpha()\n"
    )
    return tmp


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------


def test_run_pipeline_returns_pipeline_run_result(tmp_path):
    _make_repo(tmp_path)
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    assert isinstance(result, PipelineRunResult)


def test_result_carries_containerized_model(tmp_path):
    _make_repo(tmp_path)
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    assert isinstance(result.model, ContainerizedModel)


def test_result_carries_chain_closure_report(tmp_path):
    _make_repo(tmp_path)
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    assert isinstance(result.verify_report, ChainClosureReport)


def test_result_carries_per_component_reports(tmp_path):
    _make_repo(tmp_path)
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    assert isinstance(result.per_component_reports, dict)
    assert set(result.per_component_reports) == {c.id for c in result.model.components}


def test_result_carries_publish_output(tmp_path):
    _make_repo(tmp_path)
    out = tmp_path / "arch.yaml"
    result = run_pipeline(tmp_path, out_path=out)
    assert result.published is not None
    assert result.published.model_path == out
    assert out.exists()


# ---------------------------------------------------------------------------
# End-to-end behavior
# ---------------------------------------------------------------------------


def test_pipeline_produces_valid_v3_yaml_on_disk(tmp_path):
    _make_repo(tmp_path)
    out = tmp_path / "arch.yaml"
    run_pipeline(tmp_path, out_path=out, project_name="tinyrepo")
    doc = yaml.safe_load(out.read_text())
    assert doc["meta"]["schema_version"] == "3.0"
    assert doc["meta"]["project"] == "tinyrepo"
    assert len(doc["entities"]["components"]) >= 1


def test_pipeline_infers_depends_on_from_imports(tmp_path):
    """pkg.b imports pkg.a; both fall into the same cluster at default
    depth=3 (pkg is a single segment), so no cross-cluster link. Use
    depth=4 to split them."""
    _make_repo(tmp_path)
    result = run_pipeline(
        tmp_path,
        out_path=tmp_path / "arch.yaml",
        cluster_depth=4,
    )
    # depth=4 → pkg.a, pkg.b as separate clusters
    kinds = {l.kind for l in result.model.relationships}
    assert "depends-on" in kinds or len(result.model.components) < 2


def test_pipeline_produces_typed_gaps_on_empty_signal(tmp_path):
    """Module with no docstring / no functions / no classes → three typed gaps."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "empty.py").write_text("x = 1\n")
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    # Any component containing the empty module should have typed-gap Promises
    gap_types = {
        p.gap_type
        for c in result.model.components
        for p in c.promises
        if p.gap_type is not None
    }
    assert gap_types & {"missing-intent", "no-public-functions", "no-public-classes"}


def test_pipeline_skip_publish_leaves_no_file(tmp_path):
    _make_repo(tmp_path)
    out = tmp_path / "arch.yaml"
    result = run_pipeline(tmp_path, out_path=out, skip_publish=True)
    assert result.published is None
    assert not out.exists()
    # But model + reports still populated
    assert result.model is not None
    assert result.verify_report is not None


def test_pipeline_is_deterministic_with_pinned_now(tmp_path, monkeypatch):
    monkeypatch.setenv("AMS_DETERMINISTIC_NOW", "2026-09-14T00:00:00Z")
    _make_repo(tmp_path)
    r1 = run_pipeline(tmp_path, out_path=tmp_path / "a.yaml")
    r2 = run_pipeline(tmp_path, out_path=tmp_path / "b.yaml")
    assert r1.published.model_yaml == r2.published.model_yaml


def test_pipeline_accepts_string_repo_path(tmp_path):
    _make_repo(tmp_path)
    result = run_pipeline(str(tmp_path), out_path=tmp_path / "arch.yaml")
    assert isinstance(result, PipelineRunResult)


def test_pipeline_empty_repo(tmp_path):
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    assert result.model.components == []
    assert result.verify_report.total_promises == 0
    assert (tmp_path / "arch.yaml").exists()


# ---------------------------------------------------------------------------
# Part 17a1: behaviors flow through end-to-end
# ---------------------------------------------------------------------------


def _make_documented_repo(tmp: Path) -> Path:
    """Repo with a single documented public function → 1 behavior."""
    (tmp / "pkg").mkdir()
    (tmp / "pkg" / "__init__.py").write_text('"""pkg init."""\n')
    (tmp / "pkg" / "a.py").write_text(
        '"""module a."""\n'
        "def scan_repo():\n"
        '    """Scan a repository and emit modules."""\n'
        "    pass\n"
    )
    return tmp


def test_result_carries_behavior_candidates(tmp_path):
    _make_documented_repo(tmp_path)
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    assert any(c.function_name == "scan_repo" for c in result.behavior_candidates)


def test_pipeline_containerizes_behaviors_with_owner_component(tmp_path):
    _make_documented_repo(tmp_path)
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    assert result.model.behaviors, "expected at least one containerized behavior"
    b = result.model.behaviors[0]
    assert b.owner_component  # non-empty component id
    assert any(
        c.id == b.owner_component for c in result.model.components
    )


def test_pipeline_emits_traces_to_edge_for_each_behavior(tmp_path):
    _make_documented_repo(tmp_path)
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    traces = [r for r in result.model.relationships if r.kind == "traces-to"]
    assert len(traces) == len(result.model.behaviors)
    beh_ids = {b.id for b in result.model.behaviors}
    for r in traces:
        assert r.to_cluster in beh_ids


def test_published_yaml_includes_behaviors_when_present(tmp_path):
    _make_documented_repo(tmp_path)
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    doc = yaml.safe_load(result.published.model_yaml)
    assert "behaviors" in doc["entities"]
    assert doc["entities"]["behaviors"]


def test_published_yaml_omits_behaviors_when_absent(tmp_path):
    _make_repo(tmp_path)  # functions without docstrings
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    doc = yaml.safe_load(result.published.model_yaml)
    assert "behaviors" not in doc["entities"]


# ---------------------------------------------------------------------------
# Part 17a2: trigger edges flow through end-to-end
# ---------------------------------------------------------------------------


def _make_triggering_repo(tmp: Path) -> Path:
    """Repo where ``caller`` calls ``callee`` in the same module."""
    (tmp / "pkg").mkdir()
    (tmp / "pkg" / "__init__.py").write_text('"""pkg init."""\n')
    (tmp / "pkg" / "a.py").write_text(
        '"""module a."""\n'
        "def callee():\n"
        '    """Do the work."""\n'
        "    return 1\n"
        "\n"
        "def caller():\n"
        '    """Orchestrate work."""\n'
        "    return callee()\n"
    )
    return tmp


def test_result_carries_trigger_edges(tmp_path):
    _make_triggering_repo(tmp_path)
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    assert result.trigger_edges, "expected at least one trigger edge"


def test_pipeline_emits_triggers_relationship_beh_to_beh(tmp_path):
    _make_triggering_repo(tmp_path)
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    triggers = [r for r in result.model.relationships if r.kind == "triggers"]
    assert triggers, "expected triggers relationship in containerized model"
    beh_ids = {b.id for b in result.model.behaviors}
    for r in triggers:
        assert r.from_cluster in beh_ids
        assert r.to_cluster in beh_ids


def test_published_yaml_includes_triggers_relationship(tmp_path):
    _make_triggering_repo(tmp_path)
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    doc = yaml.safe_load(result.published.model_yaml)
    kinds = {r["type"] for r in doc["relationships"]}
    assert "triggers" in kinds


# ---------------------------------------------------------------------------
# Part 17a4: call_chain flows end-to-end on composite traces-to edges
# ---------------------------------------------------------------------------


def _make_composite_repo(tmp: Path) -> Path:
    """Repo where ``orch`` calls three callees — enough to be composite
    (>= COMPOSITE_MIN_TRIGGERS = 3)."""
    (tmp / "pkg").mkdir()
    (tmp / "pkg" / "__init__.py").write_text('"""pkg init."""\n')
    (tmp / "pkg" / "a.py").write_text(
        '"""module a."""\n'
        "def step_a():\n"
        '    """Step A."""\n'
        "    return 1\n"
        "\n"
        "def step_b():\n"
        '    """Step B."""\n'
        "    return 2\n"
        "\n"
        "def step_c():\n"
        '    """Step C."""\n'
        "    return 3\n"
        "\n"
        "def orch():\n"
        '    """Orchestrate steps."""\n'
        "    step_a()\n"
        "    step_b()\n"
        "    step_c()\n"
        "    return None\n"
    )
    return tmp


def test_pipeline_composite_traces_to_carries_call_chain(tmp_path):
    _make_composite_repo(tmp_path)
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    # Find the composite (orch) behavior id
    orch = next(b for b in result.model.behaviors if b.function_name == "orch")
    step_ids_by_name = {
        b.function_name: b.id for b in result.model.behaviors
    }
    # Its traces-to edge should carry call_chain in call-site order
    traces = [
        r for r in result.model.relationships
        if r.kind == "traces-to" and r.to_cluster == orch.id
    ]
    assert len(traces) == 1
    assert traces[0].call_chain == (
        step_ids_by_name["step_a"],
        step_ids_by_name["step_b"],
        step_ids_by_name["step_c"],
    )


def test_pipeline_non_composite_traces_to_has_no_call_chain(tmp_path):
    # The two-function triggering repo has only 1 outgoing trigger from
    # caller — below the composite threshold — so its traces-to edge
    # must not carry a call_chain.
    _make_triggering_repo(tmp_path)
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    caller = next(b for b in result.model.behaviors if b.function_name == "caller")
    traces = [
        r for r in result.model.relationships
        if r.kind == "traces-to" and r.to_cluster == caller.id
    ]
    assert len(traces) == 1
    assert traces[0].call_chain is None


def test_published_yaml_call_chain_is_list_in_order(tmp_path):
    _make_composite_repo(tmp_path)
    result = run_pipeline(tmp_path, out_path=tmp_path / "arch.yaml")
    doc = yaml.safe_load(result.published.model_yaml)
    orch = next(b for b in result.model.behaviors if b.function_name == "orch")
    trace_rels = [
        r for r in doc["relationships"]
        if r["type"] == "traces-to" and r["to"] == orch.id
    ]
    assert len(trace_rels) == 1
    chain = trace_rels[0]["call_chain"]
    assert isinstance(chain, list)
    assert len(chain) == 3
    # All entries are BEH-<hash> ids
    assert all(c.startswith("BEH-") for c in chain)
