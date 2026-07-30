"""Test automated consistency/quality checks."""
from architecture_model.monitoring_checks import (
    check_decompose_idempotency,
    check_cluster_stability,
    check_pattern_indicators,
    ConsistencyResult,
)
from architecture_model.manifest.types import (
    Manifest, ModuleInfo, ModuleStatus, MetricsResult, BlockManifest,
)


def _make_manifest(n: int) -> Manifest:
    modules = []
    for i in range(n):
        modules.append(ModuleInfo(
            file=f"pkg/mod_{i}.py", name=f"mod_{i}", docstring=None,
            classes=[], functions=[],
            imports=[f"mod_{i-1}"] if i > 0 else [], line_count=50,
            status=ModuleStatus.ACTIVE,
        ))
    block = BlockManifest(name="Test", status="active", description_source="test")
    return Manifest(
        generated_at="2026-01-01", project_root="pkg",
        metrics=MetricsResult(), functional_blocks={"F1": block},
        modules=modules, interfaces=[],
    )


def test_decompose_idempotency_pass():
    manifest = _make_manifest(15)
    result = check_decompose_idempotency(manifest, block_id="F1", block_name="Test")
    assert isinstance(result, ConsistencyResult)
    assert result.passed is True
    assert result.metric_name == "decompose_idempotency"


def test_cluster_stability():
    modules = [f"m{i}" for i in range(10)]
    edges = [(f"m{i}", f"m{i+1}") for i in range(9)]
    result = check_cluster_stability(modules, edges)
    assert isinstance(result, ConsistencyResult)
    assert 0.0 <= result.score <= 1.0


def test_pattern_indicators_match():
    """Check that pattern indicators are found in file content."""
    file_contents = {"fan.py": "class MqttFan(MqttEntity):\n    async def async_setup_entry(hass):\n        pass\nPLATFORM_SCHEMA = vol.Schema({})\n"}
    result = check_pattern_indicators("entity-platform", file_contents)
    assert result.passed is True
    assert result.score >= 0.5


def test_pattern_indicators_mismatch():
    file_contents = {"utils.py": "def helper(): pass\n"}
    result = check_pattern_indicators("entity-platform", file_contents)
    assert result.passed is False
    assert result.score < 0.5
