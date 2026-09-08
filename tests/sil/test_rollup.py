"""B2.1.3 — rollup_component merges runtime records for an arch component."""

from architecture_model.sil.record import SILRecord, Metrics
from architecture_model.sil.rollup import rollup_component


def test_rollup_merges_runtime_records_for_arch_component(tmp_path):
    """COMP-2.1 owns modules pipeline/coordinator.py + protocol.py + cache.py.
    Two runtime records (stage:observe scoped to those modules, mcp_tool:pipeline)
    are aggregated: invocations summed, avg_duration_ms weighted."""
    manifest_allocation = {
        "COMP-2.1": [
            "src/architecture_model/pipeline/coordinator.py",
            "src/architecture_model/pipeline/protocol.py",
        ]
    }
    runtime_records = [
        SILRecord(
            component_id="stage:observe",
            kind="runtime-component",
            name="ObserveStage",
            metrics=Metrics(
                invocations_7d=10, avg_duration_ms=100, failure_rate_7d=0.1
            ),
        ),
        SILRecord(
            component_id="mcp_tool:pipeline",
            kind="runtime-component",
            name="pipeline",
            metrics=Metrics(
                invocations_7d=30, avg_duration_ms=200, failure_rate_7d=0.0
            ),
        ),
    ]
    arch_record = SILRecord(
        component_id="COMP-2.1",
        kind="architecture-component",
        name="Pipeline Coordination",
        metrics=Metrics(validation_score=88),
    )
    merged = rollup_component(
        arch_record,
        runtime_records,
        allocation_map=manifest_allocation,
        module_to_runtime={
            "src/architecture_model/pipeline/coordinator.py": [
                "stage:observe",
                "mcp_tool:pipeline",
            ]
        },
    )
    assert merged.rollup.runtime_components == ["stage:observe", "mcp_tool:pipeline"]
    assert merged.metrics.invocations_7d == 40  # 10 + 30
    assert merged.metrics.avg_duration_ms == 175  # (10·100 + 30·200) / 40
    assert 0.024 < merged.metrics.failure_rate_7d < 0.026  # weighted
    # arch record not mutated, and validation_score preserved on merged copy
    assert arch_record.rollup is None
    assert arch_record.metrics.invocations_7d == 0
    assert merged.metrics.validation_score == 88
