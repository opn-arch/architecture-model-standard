"""Coverage analysis: compare architecture model against code reality (manifest)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import ArchitectureModel

from architecture_model.monitoring import monitored

from .types import RelationType


@dataclass
class CoverageCheck:
    """Result of a single coverage check."""
    name: str
    score: float  # 0-100
    matched: int
    total: int
    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    details: str = ""


@dataclass
class CoverageResult:
    """Aggregate coverage report."""
    checks: list[CoverageCheck] = field(default_factory=list)
    overall_score: float = 0.0

    def summary(self) -> str:
        lines = ["Model Coverage Report", "=" * 40]
        for c in self.checks:
            status = "✓" if c.score == 100 else "△" if c.score >= 80 else "✗"
            lines.append(f"  {status} {c.name}: {c.matched}/{c.total} ({c.score:.0f}%)")
            for m in c.missing:
                lines.append(f"      ⚠ Missing: {m}")
            for e in c.extra:
                lines.append(f"      ⊕ Extra (not in code): {e}")
        lines.append(f"\nOverall accuracy: {self.overall_score:.0f}%")
        return "\n".join(lines)


def _check_component_coverage(model: "ArchitectureModel", manifest: dict) -> CoverageCheck:
    """Check model components against manifest modules.

    Matching strategy: a manifest module is "covered" if its file stem matches
    a component name OR any directory segment in its path matches a component name.
    Score = % of manifest modules covered by at least one model component.
    """
    # Collect module paths (skip __init__)
    module_files: list[str] = []
    for mod in manifest.get("modules", []):
        f = mod if isinstance(mod, str) else mod.get("file", "")
        if f and Path(f).stem != "__init__":
            module_files.append(f)

    model_names = {c.name.lower() for c in model.entities.components}

    # Check which modules are covered
    covered_modules: set[str] = set()
    for mf in module_files:
        stem = Path(mf).stem.lower()
        parts = [p.lower() for p in Path(mf).parts]
        if stem in model_names or any(p in model_names for p in parts[:-1]):
            covered_modules.add(mf)

    uncovered = sorted(Path(mf).stem for mf in module_files if mf not in covered_modules)
    # Extra: model components that don't match any module
    matched_components = set()
    for comp_name in model_names:
        for mf in module_files:
            stem = Path(mf).stem.lower()
            parts = [p.lower() for p in Path(mf).parts]
            if stem == comp_name or comp_name in parts:
                matched_components.add(comp_name)
                break
    extra = sorted(model_names - matched_components)

    total = len(module_files) if module_files else 1
    matched_count = len(covered_modules)

    return CoverageCheck(
        name="Component Coverage",
        score=matched_count / total * 100 if total else 100.0,
        matched=matched_count,
        total=total,
        missing=uncovered[:10],
        extra=extra,
    )


def _check_relationship_accuracy(model: "ArchitectureModel", manifest: dict) -> CoverageCheck:
    """Legacy alias — delegates to _check_relationship_accuracy_legacy."""
    return _check_relationship_accuracy_legacy(model, manifest)


def _check_relationship_accuracy_legacy(model: "ArchitectureModel", manifest: dict) -> CoverageCheck:
    """Check model relationships against manifest import graph.

    Aggregates file-level imports to package-level edges for comparison
    with model depends-on relationships.
    """
    # Build manifest import edges at package level
    # Determine package for each file by finding the deepest model-component directory
    id_to_name = {c.id: c.name.lower() for c in model.entities.components}
    model_comp_names = set(id_to_name.values())

    def _file_to_package(filepath: str) -> str | None:
        """Map a file path to its owning model component (package name)."""
        parts = [p.lower() for p in Path(filepath).parts]
        # Find the deepest directory that matches a component name
        for part in reversed(parts[:-1]):  # exclude filename
            if part in model_comp_names:
                return part
        # Fallback: file stem
        stem = Path(filepath).stem.lower()
        if stem in model_comp_names:
            return stem
        return None

    manifest_pkg_edges: set[tuple[str, str]] = set()
    for iface in manifest.get("interfaces", []):
        src_pkg = _file_to_package(iface.get("source", ""))
        tgt_pkg = _file_to_package(iface.get("target", ""))
        if src_pkg and tgt_pkg and src_pkg != tgt_pkg:
            manifest_pkg_edges.add((src_pkg, tgt_pkg))

    # Build model depends-on edges
    model_edges: set[tuple[str, str]] = set()
    for rel in model.relationships:
        if rel.type == RelationType.DEPENDS_ON:
            from_name = id_to_name.get(rel.from_id)
            to_name = id_to_name.get(rel.to_id)
            if from_name and to_name:
                model_edges.add((from_name, to_name))

    matched = manifest_pkg_edges & model_edges
    missing = sorted(manifest_pkg_edges - model_edges)
    extra = sorted(model_edges - manifest_pkg_edges)
    total = len(manifest_pkg_edges) if manifest_pkg_edges else 1

    return CoverageCheck(
        name="Relationship Accuracy",
        score=len(matched) / total * 100 if total else 100.0,
        matched=len(matched),
        total=total,
        missing=[f"{a} → {b}" for a, b in missing],
        extra=[f"{a} → {b}" for a, b in extra],
    )


def _check_dependency_accuracy(
    model: "ArchitectureModel",
    import_deps: dict[str, set[str]] | None = None,
    manifest: dict | None = None,
) -> CoverageCheck:
    """Check model depends-on relationships against import-derived F-block dependencies.

    If import_deps not provided, falls back to legacy interface-based check.
    """
    if import_deps is None and manifest is not None:
        return _check_relationship_accuracy_legacy(model, manifest)

    if import_deps is None:
        import_deps = {}

    # Build model edges as F-block pairs
    comp_to_fb = {c.id: c.source_block for c in model.entities.components if c.source_block}
    model_edges: set[tuple[str, str]] = set()
    for rel in model.relationships:
        if rel.type == RelationType.DEPENDS_ON:
            src_fb = comp_to_fb.get(rel.from_id)
            tgt_fb = comp_to_fb.get(rel.to_id)
            if src_fb and tgt_fb:
                model_edges.add((src_fb, tgt_fb))

    # Build import edges
    import_edges: set[tuple[str, str]] = set()
    for src_fb, targets in import_deps.items():
        for tgt_fb in targets:
            import_edges.add((src_fb, tgt_fb))

    all_edges = model_edges | import_edges
    if not all_edges:
        return CoverageCheck(name="Dependency Accuracy", score=100.0, matched=0, total=0)

    matched = model_edges & import_edges
    missing = sorted(import_edges - model_edges)  # in imports but not model
    extra = sorted(model_edges - import_edges)    # in model but not imports

    score = len(matched) / len(all_edges) * 100

    return CoverageCheck(
        name="Dependency Accuracy",
        score=score,
        matched=len(matched),
        total=len(all_edges),
        missing=[f"{a} → {b}" for a, b in missing],
        extra=[f"{a} → {b}" for a, b in extra],
    )


def _check_capability_coverage(model: "ArchitectureModel", manifest: dict) -> CoverageCheck:
    """Check model capabilities against manifest functional blocks."""
    manifest_source_blocks = set(manifest.get("functional_blocks", {}).keys())
    model_source_blocks = {c.source_block for c in model.entities.capabilities if c.source_block}

    # Case-insensitive comparison
    manifest_lower = {f.lower() for f in manifest_source_blocks}
    model_lower = {f.lower() for f in model_source_blocks}

    matched = manifest_lower & model_lower
    missing = sorted(manifest_lower - model_lower)
    extra = sorted(model_lower - manifest_lower)
    total = len(manifest_lower) if manifest_lower else 1

    return CoverageCheck(
        name="Capability Coverage",
        score=len(matched) / total * 100 if total else 100.0,
        matched=len(matched),
        total=total,
        missing=missing,
        extra=extra,
    )


def _check_interface_coverage(model: "ArchitectureModel", manifest: dict) -> CoverageCheck:
    """Check model interfaces against manifest module exports.

    A model component with an EXPOSES relationship should correspond to
    manifest modules (in that component's package) that have exports.
    """
    # Find packages that contain modules with exports
    model_comp_names = {c.name.lower() for c in model.entities.components}
    packages_with_exports: set[str] = set()
    for mod in manifest.get("modules", []):
        if isinstance(mod, dict) and mod.get("exports"):
            filepath = mod.get("file", "")
            stem = Path(filepath).stem.lower()
            parts = [p.lower() for p in Path(filepath).parts]
            # Match by directory segment or by file stem
            matched = False
            for part in reversed(parts[:-1]):
                if part in model_comp_names:
                    packages_with_exports.add(part)
                    matched = True
                    break
            if not matched and stem in model_comp_names:
                packages_with_exports.add(stem)

    # Find model components that have EXPOSES relationships
    comp_id_to_name = {c.id: c.name.lower() for c in model.entities.components}
    components_with_interfaces: set[str] = set()
    for rel in model.relationships:
        if rel.type == RelationType.EXPOSES and rel.from_id in comp_id_to_name:
            components_with_interfaces.add(comp_id_to_name[rel.from_id])

    matched = packages_with_exports & components_with_interfaces
    missing = sorted(packages_with_exports - components_with_interfaces)
    extra = sorted(components_with_interfaces - packages_with_exports)
    total = len(packages_with_exports) if packages_with_exports else 1

    return CoverageCheck(
        name="Interface Coverage",
        score=len(matched) / total * 100 if total else 100.0,
        matched=len(matched),
        total=total,
        missing=missing,
        extra=extra,
    )


def _check_staleness(model: "ArchitectureModel", manifest: dict) -> CoverageCheck:
    """Check if model is up-to-date with manifest hash."""
    # Exclude volatile fields (e.g. generated_at timestamp) for deterministic hashing
    stable_manifest = {k: v for k, v in manifest.items() if k != "generated_at"}
    current_hash = hashlib.sha256(
        json.dumps(stable_manifest, sort_keys=True).encode()
    ).hexdigest()[:16]

    model_hash = model.meta.manifest_hash

    if not model_hash:
        return CoverageCheck(
            name="Staleness",
            score=0.0,
            matched=0,
            total=1,
            missing=["manifest_hash not set in model meta"],
            details=f"Current manifest hash: {current_hash}",
        )

    if model_hash == current_hash:
        return CoverageCheck(
            name="Staleness",
            score=100.0,
            matched=1,
            total=1,
            details=f"Hash matches: {current_hash}",
        )

    return CoverageCheck(
        name="Staleness",
        score=0.0,
        matched=0,
        total=1,
        missing=[f"Hash mismatch: model={model_hash}, manifest={current_hash}"],
        details=f"Model is stale",
    )


def _check_source_block_quality(model: "ArchitectureModel") -> CoverageCheck:
    """Check F-block quality metrics (dimension 6)."""
    from .source_block_quality import compute_source_block_quality

    quality = compute_source_block_quality(model)

    # Score: weighted combination of metrics (0-100)
    # modularity (capped at 0.5 = perfect), low orphan rate, low cycle ratio, balance
    mod_score = min(quality.modularity / 0.5, 1.0) * 100 if quality.modularity > 0 else 0.0
    orphan_score = (1 - quality.orphan_rate) * 100
    cycle_score = (1 - quality.cross_block_cycle_ratio) * 100
    balance_score = (1 - quality.cluster_balance) * 100

    score = 0.4 * mod_score + 0.2 * orphan_score + 0.2 * cycle_score + 0.2 * balance_score

    details_parts = [
        f"modularity={quality.modularity:.3f}",
        f"orphan_rate={quality.orphan_rate:.2f}",
        f"cycle_ratio={quality.cross_block_cycle_ratio:.2f}",
        f"cluster_balance={quality.cluster_balance:.2f}",
    ]
    if quality.agreement_rate is not None:
        details_parts.append(f"agreement={quality.agreement_rate:.2f}")

    return CoverageCheck(
        name="F-Block Quality",
        score=round(score, 1),
        matched=int(score),
        total=100,
        details=", ".join(details_parts),
    )


def _check_requirement_traceability(model: "ArchitectureModel") -> CoverageCheck:
    """Check requirement traceability coverage (dimension 8).

    Reports orphan requirements (no incoming 'satisfies' edges).
    Returns not_run result if no requirements exist (opt-in feature).
    """
    requirements = getattr(getattr(model, "entities", None), "requirements", None) or []

    # Only count ACTIVE requirements
    active_reqs = {r.id for r in requirements if r.status in ("ACTIVE", "active")}

    if not active_reqs:
        return CoverageCheck(
            name="requirement_traceability",
            score=100,
            matched=0,
            total=0,
            details="not_run: no requirements configured",
        )

    # Find requirements with satisfies edges
    satisfied_ids: set[str] = set()
    for rel in model.relationships:
        rel_type = rel.type if isinstance(rel.type, str) else rel.type.value
        if rel_type == "satisfies":
            satisfied_ids.add(rel.to_id)

    orphan_reqs = sorted(active_reqs - satisfied_ids)
    covered = len(active_reqs) - len(orphan_reqs)
    score = int(100 * covered / len(active_reqs))

    return CoverageCheck(
        name="requirement_traceability",
        score=score,
        matched=covered,
        total=len(active_reqs),
        missing=[f"Orphan requirement (no satisfies edge): {rid}" for rid in orphan_reqs],
        details=f"{covered}/{len(active_reqs)} requirements covered",
    )


@monitored(
    module="core.coverage",
    quality=lambda r: {"overall_score": r.overall_score},
)
def coverage_report(
    model: "ArchitectureModel",
    manifest: dict,
    import_deps: dict[str, set[str]] | None = None,
) -> CoverageResult:
    """Run all coverage checks and return aggregate result."""
    if import_deps is not None:
        rel_check = _check_dependency_accuracy(model, import_deps)
    else:
        rel_check = _check_relationship_accuracy_legacy(model, manifest)
    checks = [
        _check_component_coverage(model, manifest),
        rel_check,
        _check_capability_coverage(model, manifest),
        _check_interface_coverage(model, manifest),
        _check_staleness(model, manifest),
        _check_source_block_quality(model),
        _check_requirement_traceability(model),
    ]
    overall = sum(c.score for c in checks) / len(checks) if checks else 0.0
    return CoverageResult(checks=checks, overall_score=overall)
