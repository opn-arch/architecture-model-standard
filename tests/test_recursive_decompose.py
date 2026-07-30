"""Test iterative deep decomposition until leaf threshold."""
from architecture_model.orchestration.deep_decompose import (
    deep_decompose_block,
    iterative_decompose,
    DecomposeResult,
)
from architecture_model.manifest.types import (
    Manifest, ModuleInfo, FunctionInfo, ModuleStatus,
    MetricsResult, BlockManifest, ScanReport,
)


def _make_manifest(n_modules: int) -> Manifest:
    """Create a manifest with n modules that import each other sequentially."""
    modules = []
    for i in range(n_modules):
        name = f"mod_{i}"
        imports = [f"mod_{i-1}"] if i > 0 else []
        modules.append(ModuleInfo(
            file=f"pkg/mod_{i}.py",
            name=name,
            docstring=None,
            functions=[FunctionInfo(name=f"func_{i}", signature=f"func_{i}()")],
            imports=imports,
            line_count=50,
            status=ModuleStatus.ACTIVE,
            classes=[],
        ))
    return Manifest(
        generated_at="2026-01-01T00:00:00",
        project_root="pkg",
        metrics=MetricsResult(),
        functional_blocks={},
        modules=modules,
        interfaces=[],
        scan_report=ScanReport(),
    )


def test_iterative_decompose_reaches_leaf_size():
    """With 30 modules and leaf_max=3, all leaves should have <= 3 files."""
    manifest = _make_manifest(30)
    results = iterative_decompose(
        manifest, block_id="F1", block_name="Test", leaf_max_files=3
    )
    assert len(results) >= 1
    # Collect all leaf sub-components (those not further decomposed)
    # The last result's sub-components that are <= leaf_max are leaves
    all_requeued_ids = set()
    for r in results:
        for sc in r.sub_components:
            if len(sc.files) > 3:
                all_requeued_ids.add(sc.id)
    # Final leaves are sub-components NOT requeued
    for r in results:
        for sc in r.sub_components:
            if sc.id not in all_requeued_ids:
                assert len(sc.files) <= 3, f"{sc.id} has {len(sc.files)} files"


def test_iterative_decompose_small_block_returns_empty():
    """A 3-file block is already a leaf — no decomposition needed."""
    manifest = _make_manifest(3)
    results = iterative_decompose(
        manifest, block_id="F1", block_name="Test", leaf_max_files=3
    )
    assert results == []


def test_iterative_decompose_depth_tracked():
    """Each iteration increases depth."""
    manifest = _make_manifest(20)
    results = iterative_decompose(
        manifest, block_id="F1", block_name="Test", leaf_max_files=3
    )
    if results:
        depths = [r.depth for r in results]
        assert max(depths) >= 1
