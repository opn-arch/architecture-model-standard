"""
CLI for the Architecture Model Standard.

Usage:
    architecture-model validate <model.yaml> [--strict]
    architecture-model slice <model.yaml> --fblock F3
    architecture-model slice <model.yaml> --artifact use-cases
    architecture-model diff <old.yaml> <new.yaml>
    architecture-model stats <model.yaml>
    architecture-model init <path>
    architecture-model manifest <path>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="architecture-model",
        description="Architecture Model Standard — CLI tools",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- validate ---
    p_validate = subparsers.add_parser("validate", help="Validate model invariants")
    p_validate.add_argument("model", help="Path to architecture-model.yaml")
    p_validate.add_argument("--strict", action="store_true", help="Promote warnings to errors")

    # --- slice ---
    p_slice = subparsers.add_parser("slice", help="Extract model subset")
    p_slice.add_argument("model", help="Path to architecture-model.yaml")
    p_slice.add_argument("--fblock", help="Filter by F-block (e.g., F3)")
    p_slice.add_argument("--layer", help="Filter by layer (e.g., web-layer)")
    p_slice.add_argument("--artifact", help="Slice for artifact regeneration")
    p_slice.add_argument("--status", help="Filter by status (ACTIVE, PLANNED)")
    p_slice.add_argument("-o", "--output", help="Output YAML path (default: stdout summary)")

    # --- diff ---
    p_diff = subparsers.add_parser("diff", help="Compare two model versions")
    p_diff.add_argument("old_model", help="Path to old/baseline model")
    p_diff.add_argument("new_model", help="Path to new/current model")

    # --- stats ---
    p_stats = subparsers.add_parser("stats", help="Show model statistics")
    p_stats.add_argument("model", help="Path to architecture-model.yaml")

    # --- init ---
    p_init = subparsers.add_parser(
        "init", help="Auto-generate .architecture-model.yaml for a project"
    )
    p_init.add_argument(
        "path", nargs="?", default=".", help="Project root directory (default: cwd)"
    )
    p_init.add_argument("--force", action="store_true", help="Overwrite existing config file")

    # --- impact ---
    p_impact = subparsers.add_parser("impact", help="Impact analysis for an entity")
    p_impact.add_argument("model", help="Path to architecture-model.yaml")
    p_impact.add_argument("entity_id", help="Entity ID to analyze")
    p_impact.add_argument("--depth", type=int, default=2, help="Traversal depth")

    # --- manifest ---
    p_manifest = subparsers.add_parser("manifest", help="Generate reality-manifest.json from source code")
    p_manifest.add_argument("path", nargs="?", default=".", help="Project root directory (default: cwd)")
    p_manifest.add_argument("-o", "--output", help="Output JSON path")

    # --- enrich ---
    p_enrich = subparsers.add_parser("enrich", help="Auto-enrich model with signatures, constants, test contracts")
    p_enrich.add_argument("model", help="Path to architecture-model.yaml")
    p_enrich.add_argument("--root", default=".", help="Project root directory")

    # --- coverage ---
    p_coverage = subparsers.add_parser("coverage", help="Analyze model coverage against code reality")
    p_coverage.add_argument("model", help="Path to .architecture-model.yaml")
    p_coverage.add_argument("--project", "-p", help="Project path for manifest generation (default: model directory)")
    p_coverage.add_argument("--manifest", help="Path to pre-generated manifest JSON")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch
    handlers = {
        "init": _cmd_init,
        "validate": _cmd_validate,
        "slice": _cmd_slice,
        "diff": _cmd_diff,
        "stats": _cmd_stats,
        "impact": _cmd_impact,
        "manifest": _cmd_manifest,
        "coverage": _cmd_coverage,
        "enrich": _cmd_enrich,
    }
    return handlers[args.command](args)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _cmd_init(args) -> int:
    from ..config.loader import discover_config, write_config, CONFIG_FILENAME

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory")
        return 1

    config_path = root / CONFIG_FILENAME
    if config_path.exists() and not args.force:
        print(f"Config already exists: {config_path}")
        print("Use --force to overwrite.")
        return 1

    print(f"Scanning: {root}")
    config, _report = discover_config(root)

    # Summary
    print(f"\nProject: {config.name}")
    print(f"System:  {config.system}")
    print(f"Layers:  {len(config.layers)}")
    for layer in config.layers:
        print(f"  - {layer.id}: {layer.dirs}")
    print(f"Functional Blocks: {len(config.functional_blocks)}")
    for fb in config.functional_blocks:
        print(f"  - [{fb.id}] {fb.name} ({len(fb.files)} files)")
        if fb.description_source:
            print(f"    {fb.description_source}")
    print(f"Metrics: {len(config.metrics)}")
    for m in config.metrics:
        print(f"  - {m.label}: {m.path} ({m.pattern})")

    # Write
    out_path = write_config(config, root)
    print(f"\nWritten: {out_path}")
    return 0


def _cmd_validate(args) -> int:
    from ..core.parser import load_model
    from ..core.validator import validate_model

    model = load_model(args.model)
    result = validate_model(model, strict=args.strict)

    print(result.summary())
    if result.issues:
        print()
        for issue in result.issues:
            print(f"  {issue}")

    return 0 if result.is_valid else 1


def _cmd_slice(args) -> int:
    from ..core.parser import load_model, save_model
    from ..core.slicer import slice_by_fblock, slice_by_layer, slice_by_status, slice_for_artifact
    from ..core.types import Status

    model = load_model(args.model)

    if args.fblock:
        sliced = slice_by_fblock(model, args.fblock)
        label = f"F-block: {args.fblock}"
    elif args.layer:
        sliced = slice_by_layer(model, args.layer)
        label = f"Layer: {args.layer}"
    elif args.artifact:
        sliced = slice_for_artifact(model, args.artifact)
        label = f"Artifact: {args.artifact}"
    elif args.status:
        sliced = slice_by_status(model, Status(args.status.upper()))
        label = f"Status: {args.status}"
    else:
        print("ERROR: Provide --fblock, --layer, --artifact, or --status")
        return 1

    print(
        f"Slice [{label}]: {sliced.entity_count} entities, {sliced.relationship_count} relationships"
    )

    if args.output:
        save_model(sliced, args.output)
        print(f"Saved to: {args.output}")

    return 0


def _cmd_diff(args) -> int:
    from ..core.parser import load_model
    from ..core.differ import diff_models

    old_model = load_model(args.old_model)
    new_model = load_model(args.new_model)

    diff = diff_models(old_model, new_model)
    print(diff.format_report())

    if diff.has_changes:
        print(f"\nAffected artifacts: {', '.join(sorted(diff.affected_artifacts()))}")

    return 0


def _cmd_stats(args) -> int:
    from ..core.parser import load_model
    from ..core.validator import validate_model
    from collections import Counter
    from ..core.types import Status

    model = load_model(args.model)

    print(f"Architecture Model: {model.meta.project}")
    print(f"System: {model.meta.system}")
    print(f"Schema version: {model.meta.schema_version}")
    print(f"Generated: {model.meta.generated_at}")
    print(f"Sources: {', '.join(model.meta.source_artifacts)}")
    if model.meta.manifest_hash:
        print(f"Manifest hash: {model.meta.manifest_hash}")
    print()
    print(f"Total entities: {model.entity_count}")
    print(f"  Actors:        {len(model.entities.actors)}")
    print(f"  Capabilities:  {len(model.entities.capabilities)}")
    print(f"  Behaviors:     {len(model.entities.behaviors)}")
    print(f"  Interfaces:    {len(model.entities.interfaces)}")
    print(f"  Constraints:   {len(model.entities.constraints)}")
    print(f"  Layers:        {len(model.entities.layers)}")
    print(f"  Components:    {len(model.entities.components)}")
    print()
    print(f"Total relationships: {model.relationship_count}")

    # Relationship type breakdown
    from ..core.types import RelationType

    rel_counts = Counter(r.type.value for r in model.relationships)
    for rtype, count in rel_counts.most_common():
        print(f"  {rtype}: {count}")

    # Status breakdown
    print()
    statuses = Counter()
    for lst in [
        model.entities.actors,
        model.entities.capabilities,
        model.entities.behaviors,
        model.entities.interfaces,
        model.entities.constraints,
        model.entities.layers,
        model.entities.components,
    ]:
        for e in lst:
            statuses[e.status.value] += 1
    for status, count in statuses.most_common():
        print(f"  [{status}]: {count}")

    # Validation
    print()
    result = validate_model(model)
    print(f"Validation: {result.summary()}")

    return 0


def _cmd_impact(args) -> int:
    """Impact analysis using BFS through relationships."""
    from ..core.parser import load_model

    model = load_model(args.model)

    # Simple BFS impact analysis (moved from integrations)
    entity_id = args.entity_id
    depth = args.depth

    # Verify entity exists
    all_ids = set()
    for lst in [
        model.entities.actors, model.entities.capabilities,
        model.entities.behaviors, model.entities.interfaces,
        model.entities.constraints, model.entities.layers,
        model.entities.components,
    ]:
        for e in lst:
            all_ids.add(e.id)

    if entity_id not in all_ids:
        print(f"ERROR: Entity '{entity_id}' not found in model")
        return 1

    # BFS
    adjacency: dict[str, set[str]] = {eid: set() for eid in all_ids}
    for rel in model.relationships:
        if rel.from_id in adjacency:
            adjacency[rel.from_id].add(rel.to_id)
        if rel.to_id in adjacency:
            adjacency[rel.to_id].add(rel.from_id)

    visited: dict[str, int] = {entity_id: 0}
    queue = [(entity_id, 0)]
    while queue:
        current, d = queue.pop(0)
        if d >= depth:
            continue
        for neighbor in adjacency.get(current, set()):
            if neighbor not in visited:
                visited[neighbor] = d + 1
                queue.append((neighbor, d + 1))

    print(f"Impact analysis: {entity_id} (depth={depth})")
    print(f"Affected entities: {len(visited) - 1}")
    for eid, d in sorted(visited.items(), key=lambda x: (x[1], x[0])):
        if eid == entity_id:
            continue
        print(f"  [depth {d}] {eid}")

    return 0


def _cmd_manifest(args) -> int:
    from ..manifest import generate_manifest
    from ..config.loader import get_config
    import json

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory")
        return 1

    print(f"Scanning: {root}")
    manifest = generate_manifest(root)
    manifest_dict = manifest.to_dict()

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        config = get_config(root)
        resolved = config.resolved_output()
        out_path = resolved.manifest

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest_dict, indent=2, default=str), encoding="utf-8")

    # Print summary
    modules = manifest_dict.get("modules", [])
    interfaces = manifest_dict.get("interfaces", [])
    blocks = manifest_dict.get("functional_blocks", {})
    metrics = manifest_dict.get("metrics", {})

    print(f"\n  Modules: {len(modules)}")
    print(f"  Interfaces: {len(interfaces)}")
    print(f"  F-blocks: {len(blocks)}")
    print(f"  Metrics: {metrics}")
    print(f"\nSaved: {out_path}")
    return 0


def _cmd_enrich(args) -> int:
    """Auto-enrich model with signatures, constants, and test contracts."""
    from ..core.parser import load_model, save_model
    from ..enrich import enrich_model

    model_path = Path(args.model)
    root = Path(args.root).resolve()

    model = load_model(model_path)

    # Count before
    comps = model.entities.get("components", []) if isinstance(model.entities, dict) else model.entities.components
    before_sigs = sum(len(c.signatures) for c in comps)
    before_consts = sum(len(c.constants) for c in comps)
    before_tests = sum(len(c.test_contracts) for c in comps)

    enriched = enrich_model(model, root)
    save_model(enriched, model_path)

    # Count after
    comps_after = enriched.entities.get("components", []) if isinstance(enriched.entities, dict) else enriched.entities.components
    after_sigs = sum(len(c.signatures) for c in comps_after)
    after_consts = sum(len(c.constants) for c in comps_after)
    after_tests = sum(len(c.test_contracts) for c in comps_after)

    print(f"Enriched {model_path}")
    print(f"  Signatures:     {before_sigs} -> {after_sigs} (+{after_sigs - before_sigs})")
    print(f"  Constants:      {before_consts} -> {after_consts} (+{after_consts - before_consts})")
    print(f"  Test contracts: {before_tests} -> {after_tests} (+{after_tests - before_tests})")
    return 0


def _cmd_coverage(args) -> int:
    """Run coverage analysis: model vs manifest."""
    import json as json_mod

    from ..core.coverage import coverage_report
    from ..core.parser import load_model

    model = load_model(args.model)
    model_dir = Path(args.model).parent.resolve()

    if args.manifest:
        with open(args.manifest) as f:
            manifest = json_mod.load(f)
    else:
        project = Path(args.project) if args.project else model_dir
        from ..config.loader import discover_config
        from ..manifest.generator import generate_manifest

        config = discover_config(project)
        manifest = generate_manifest(project, config=config)

    result = coverage_report(model, manifest)
    print(result.summary())
    return 0 if result.overall_score >= 80 else 1


if __name__ == "__main__":
    sys.exit(main())
