"""Artifact writer — produces uniform file structure from pipeline results.

Writes:
  .architecture/
  ├── inventory.json       (observe output)
  ├── functional.yaml      (capabilities, actors, behaviors)
  ├── structure.yaml       (components, layers, allocation)
  ├── relationships.yaml   (all derived relationships)
  ├── validation.json      (validation score + issues)
  ├── context.md           (LLM-readable summary)
  ├── specs/{comp}.yaml    (interface specs per component)
  └── contracts/{comp}.yaml (test contracts per component)
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .allocate_types import AllocationResult
from .contract_types import ContractResult
from .infer_types import InferenceResult
from .observe_types import Inventory
from .protocol import PipelineContext, StageResult
from .relate_types import RelateResult
from .specify_types import SpecifyResult
from .validate_types import ValidateResult


def write_artifacts(ctx: PipelineContext) -> Path:
    """Write all pipeline artifacts to output_dir.

    Returns the output directory path.
    """
    out = ctx.output_dir
    out.mkdir(parents=True, exist_ok=True)

    # inventory.json (observe)
    observe = ctx.get("observe")
    if observe:
        _write_inventory(out / "inventory.json", observe.output)

    # functional.yaml (infer)
    infer = ctx.get("infer")
    if infer:
        _write_functional(out / "functional.yaml", infer.output)

    # structure.yaml (allocate)
    allocate = ctx.get("allocate")
    if allocate:
        _write_structure(out / "structure.yaml", allocate.output)

    # relationships.yaml (relate)
    relate = ctx.get("relate")
    if relate:
        _write_relationships(out / "relationships.yaml", relate.output)

    # validation.json (validate)
    validate = ctx.get("validate")
    if validate:
        _write_validation(out / "validation.json", validate.output)

    # specs/ (specify)
    specify = ctx.get("specify")
    if specify:
        _write_specs(out / "specs", specify.output, allocate.output if allocate else None)

    # contracts/ (contract)
    contract = ctx.get("contract")
    if contract:
        _write_contracts(out / "contracts", contract.output, allocate.output if allocate else None)

    return out


def _write_inventory(path: Path, inventory: Inventory) -> None:
    """Write observe inventory as JSON."""
    data = {
        "modules": [
            {
                "path": str(m.path),
                "language": m.language,
                "functions": [{"name": f.name, "signature": f.signature, "body_hint": f.body_hint} for f in m.functions],
                "classes": [{"name": c.name, "bases": c.bases, "methods": c.methods} for c in m.classes],
                "constants": [{"name": c.name, "value": c.value} for c in m.constants],
                "imports": m.imports,
                "line_count": m.line_count,
            }
            for m in inventory.modules
        ],
        "routes": [
            {"method": r.method, "path": r.path, "function": r.function_name, "file": str(r.file)}
            for r in inventory.routes
        ],
        "constraints": [
            {"name": c.name, "value": c.value, "type": c.constraint_type}
            for c in inventory.constraints
        ],
        "test_files": [{"path": str(t.path), "targets": t.targets} for t in inventory.test_files],
        "docs": [{"path": str(d.path), "title": d.title} for d in inventory.docs],
        "metrics": {
            "total_modules": len(inventory.modules),
            "total_routes": len(inventory.routes),
            "total_tests": len(inventory.test_files),
        },
    }
    path.write_text(json.dumps(data, indent=2))


def _write_functional(path: Path, inference: InferenceResult) -> None:
    """Write capabilities, actors, behaviors as YAML."""
    import yaml  # noqa: delayed import for optional dep

    data = {
        "capabilities": [
            {"id": c.id, "name": c.name, "description": c.description, "evidence": c.evidence_source}
            for c in inference.capabilities
        ],
        "actors": [
            {"id": a.id, "name": a.name, "type": a.actor_type, "evidence": a.evidence_source}
            for a in inference.actors
        ],
        "behaviors": [
            {"id": b.id, "name": b.name, "actor": b.actor_id, "capability": b.capability_id}
            for b in inference.behaviors
        ],
    }
    path.write_text(_yaml_dump(data))


def _write_structure(path: Path, allocation: AllocationResult) -> None:
    """Write component allocation as YAML."""
    data = {
        "components": [
            {
                "id": c.id,
                "name": c.name,
                "capability_id": c.capability_id,
                "layer": c.layer,
                "files": [str(f) for f in c.files],
            }
            for c in allocation.components
        ],
        "metrics": {
            "file_coverage": round(allocation.file_coverage, 1),
            "boundary_coherence": round(allocation.boundary_coherence, 1),
        },
    }
    path.write_text(_yaml_dump(data))


def _write_relationships(path: Path, relate: RelateResult) -> None:
    """Write relationships as YAML."""
    data = {
        "relationships": [
            {
                "from": r.from_id,
                "to": r.to_id,
                "type": r.rel_type,
                "evidence": r.evidence_source,
            }
            for r in relate.relationships
        ],
    }
    path.write_text(_yaml_dump(data))


def _write_validation(path: Path, validate: ValidateResult) -> None:
    """Write validation results as JSON."""
    data = {
        "score": validate.score,
        "is_valid": validate.is_valid,
        "issues": [
            {"severity": i.severity, "message": i.message, "entity_id": i.entity_id, "rule": i.rule}
            for i in validate.issues
        ],
    }
    path.write_text(json.dumps(data, indent=2))


def _write_specs(specs_dir: Path, specify: SpecifyResult, allocation: AllocationResult | None) -> None:
    """Write per-component interface specs."""
    if not specify.interfaces:
        return
    specs_dir.mkdir(parents=True, exist_ok=True)
    # Group by component
    from collections import defaultdict
    by_comp: dict[str, list] = defaultdict(list)
    for iface in specify.interfaces:
        by_comp[iface.component_id].append(iface)

    for comp_id, ifaces in by_comp.items():
        data = {
            "component": comp_id,
            "interfaces": [
                {"id": i.id, "name": i.name, "type": i.interface_type, "methods": i.methods}
                for i in ifaces
            ],
        }
        safe_name = comp_id.lower().replace(" ", "-")
        (specs_dir / f"{safe_name}.yaml").write_text(_yaml_dump(data))


def _write_contracts(contracts_dir: Path, contract: ContractResult, allocation: AllocationResult | None) -> None:
    """Write per-component test contracts."""
    if not contract.contracts:
        return
    contracts_dir.mkdir(parents=True, exist_ok=True)
    from collections import defaultdict
    by_comp: dict[str, list] = defaultdict(list)
    for c in contract.contracts:
        by_comp[c.target_component].append(c)

    for comp_id, contracts in by_comp.items():
        data = {
            "component": comp_id,
            "contracts": [
                {"test_file": c.test_file, "assertions": c.assertions}
                for c in contracts
            ],
        }
        safe_name = comp_id.lower().replace(" ", "-")
        (contracts_dir / f"{safe_name}.yaml").write_text(_yaml_dump(data))


def _yaml_dump(data: Any) -> str:
    """YAML dump with fallback to JSON if ruamel not available."""
    try:
        import yaml
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
    except ImportError:
        return json.dumps(data, indent=2)
