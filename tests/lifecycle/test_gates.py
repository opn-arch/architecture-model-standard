"""Tests for lifecycle.gates."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from architecture_model.lifecycle.gates import (
    ArtifactGate,
    DEFAULT_GATES,
    EvolutionGate,
    GateFinding,
    GateResult,
    PackageGate,
    SliceGate,
    TreeGateReport,
    ViewGate,
    evaluate_tree,
)
from architecture_model.lifecycle.package import load_package

FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "lifecycle"
    / "sample_package_tree"
)


def _copy_tree(tmp_path: Path) -> Path:
    dst = tmp_path / "pkg_tree"
    shutil.copytree(FIXTURE, dst)
    return dst


# ---------- PackageGate ----------


def test_package_gate_passes_on_sample():
    pkg = load_package(FIXTURE)
    result = PackageGate().evaluate(pkg)
    assert result.kind == "package"
    assert result.package_id == "root-pkg"
    assert result.passed is True
    assert result.blocking is False
    assert any(f.code == "PACKAGE.OK" for f in result.findings)


def test_package_gate_fails_when_model_missing(tmp_path):
    root = _copy_tree(tmp_path)
    (root / ".architecture-model.yaml").unlink()
    pkg = load_package(root)
    result = PackageGate().evaluate(pkg)
    assert result.passed is False
    assert result.blocking is True
    codes = [f.code for f in result.findings]
    assert "PACKAGE.MISSING_MODEL" in codes


def test_package_gate_fails_when_manifest_missing(tmp_path):
    root = _copy_tree(tmp_path)
    (root / "manifest.json").unlink()
    pkg = load_package(root)
    result = PackageGate().evaluate(pkg)
    assert result.passed is False
    assert result.blocking is True
    codes = [f.code for f in result.findings]
    assert "PACKAGE.MISSING_MANIFEST" in codes


# ---------- Phase-1 no-op gates ----------


@pytest.mark.parametrize(
    "gate_cls,expected_code",
    [
        (SliceGate, "SLICE.NONE_DEFINED"),
        (ViewGate, "VIEW.NONE_DEFINED"),
        (ArtifactGate, "ARTIFACT.NONE_DEFINED"),
    ],
)
def test_phase1_noop_gates(gate_cls, expected_code):
    pkg = load_package(FIXTURE)
    result = gate_cls().evaluate(pkg)
    assert result.passed is True
    assert result.blocking is False
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == expected_code
    assert finding.severity == "info"


# ---------- EvolutionGate ----------


def test_evolution_gate_passes_when_schema_version_present():
    pkg = load_package(FIXTURE)
    result = EvolutionGate().evaluate(pkg)
    assert result.passed is True
    assert result.blocking is False
    assert any(f.code == "EVOLUTION.OK" for f in result.findings)


# ---------- evaluate_tree ----------


def test_evaluate_tree_runs_all_gates_for_every_descendant():
    pkg = load_package(FIXTURE)
    report = evaluate_tree(pkg)
    # Expect 4 packages: root + 3 children.
    assert set(report.per_package.keys()) == {
        "root-pkg",
        "core-pkg",
        "config-pkg",
        "manifest-pkg",
    }
    for aid, results in report.per_package.items():
        assert len(results) == len(DEFAULT_GATES)
        kinds = [r.kind for r in results]
        assert kinds == ["package", "slice", "view", "artifact", "evolution"]
        for r in results:
            assert r.package_id == aid
    assert report.overall_passed is True
    assert report.overall_blocking is False
    assert report.breadcrumb_findings == ()


def test_evaluate_tree_child_failure_propagates_with_breadcrumbs(tmp_path):
    root = _copy_tree(tmp_path)
    # Break the core child's model.
    (root / "children" / "core" / ".architecture-model.yaml").unlink()
    pkg = load_package(root)
    report = evaluate_tree(pkg)
    assert report.overall_passed is False
    assert report.overall_blocking is True
    # Root itself should still individually pass its PackageGate.
    root_results = report.per_package["root-pkg"]
    root_pkg_result = next(r for r in root_results if r.kind == "package")
    assert root_pkg_result.passed is True
    # Core failed.
    core_results = report.per_package["core-pkg"]
    core_pkg_result = next(r for r in core_results if r.kind == "package")
    assert core_pkg_result.blocking is True
    # Breadcrumb finding exists tracing root->core.
    assert any(
        f.code == "PACKAGE.MISSING_MODEL"
        and f.breadcrumbs == ("root-pkg", "core-pkg")
        for f in report.breadcrumb_findings
    )


def test_evaluate_tree_overall_passed_false_when_any_blocking(tmp_path):
    root = _copy_tree(tmp_path)
    (root / "children" / "config" / "manifest.json").unlink()
    pkg = load_package(root)
    report = evaluate_tree(pkg)
    assert report.overall_passed is False
    assert report.overall_blocking is True


def test_evaluate_tree_deterministic():
    pkg1 = load_package(FIXTURE)
    pkg2 = load_package(FIXTURE)
    r1 = evaluate_tree(pkg1)
    r2 = evaluate_tree(pkg2)
    assert r1 == r2
    # Key order determinism.
    assert list(r1.per_package.keys()) == list(r2.per_package.keys())


def test_findings_sorted_by_severity_code_path(tmp_path):
    root = _copy_tree(tmp_path)
    (root / ".architecture-model.yaml").unlink()
    (root / "manifest.json").unlink()
    pkg = load_package(root)
    result = PackageGate().evaluate(pkg)
    # Errors first, alphabetical by code.
    codes = [f.code for f in result.findings]
    assert codes == sorted(codes)
    for f in result.findings:
        assert f.severity == "error"


def test_gate_result_and_finding_are_frozen():
    with pytest.raises(Exception):
        GateFinding(code="X", message="m", severity="info").code = "Y"  # type: ignore[misc]
    with pytest.raises(Exception):
        GateResult(
            kind="package", package_id="x", passed=True, blocking=False
        ).passed = False  # type: ignore[misc]


def test_tree_gate_report_is_frozen():
    with pytest.raises(Exception):
        TreeGateReport(
            overall_passed=True, overall_blocking=False
        ).overall_passed = False  # type: ignore[misc]
