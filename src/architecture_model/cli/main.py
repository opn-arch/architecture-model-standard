"""
CLI for the Architecture Model Standard.

Usage:
    python -m architecture_model extract <artifact_dir> [-o output.yaml]
    python -m architecture_model validate <model.yaml> [--strict]
    python -m architecture_model slice <model.yaml> --fblock F3
    python -m architecture_model slice <model.yaml> --artifact use-cases
    python -m architecture_model diff <old.yaml> <new.yaml>
    python -m architecture_model query <model.yaml> "what realizes F3?"
    python -m architecture_model context <model.yaml> [--artifact icd] [--tokens 3000]
    python -m architecture_model stats <model.yaml>
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

    # --- extract ---
    p_extract = subparsers.add_parser("extract", help="Extract model from Tier 1 artifacts")
    p_extract.add_argument("artifact_dir", nargs="?", help="Path to stage2 artifact directory")
    p_extract.add_argument(
        "--from-code", metavar="PATH",
        help="Extract model directly from source code (bypasses stage2 artifacts)",
    )
    p_extract.add_argument("-o", "--output", help="Output YAML path")
    p_extract.add_argument("--project", default="", help="Project name override")
    p_extract.add_argument("--system", default="", help="System identifier override")
    p_extract.add_argument("--manifest", help="Path to reality-manifest.json for merger")

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

    # --- query ---
    p_query = subparsers.add_parser("query", help="Query model structure")
    p_query.add_argument("model", help="Path to architecture-model.yaml")
    p_query.add_argument("question", help="Structural question")

    # --- context ---
    p_context = subparsers.add_parser("context", help="Generate LLM context from model")
    p_context.add_argument("model", help="Path to architecture-model.yaml")
    p_context.add_argument("--artifact", help="Generate artifact-specific context")
    p_context.add_argument("--fblock", help="Generate F-block-specific context")
    p_context.add_argument("--tokens", type=int, default=3000, help="Token budget")
    p_context.add_argument("--detail", choices=["minimal", "standard", "full"], default="standard")

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

    # --- train (subcommand group) ---
    from .train import register_train_commands
    register_train_commands(subparsers)

    # --- generate ---
    from .generate import register_generate_command
    register_generate_command(subparsers)

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch
    from .train import _train_stub
    from .generate import _cmd_generate
    handlers = {
        "init": _cmd_init,
        "extract": _cmd_extract,
        "validate": _cmd_validate,
        "slice": _cmd_slice,
        "diff": _cmd_diff,
        "query": _cmd_query,
        "context": _cmd_context,
        "stats": _cmd_stats,
        "impact": _cmd_impact,
        "manifest": _cmd_manifest,
        "train": _train_stub,
        "generate": _cmd_generate,
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
    config = discover_config(root)

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


def _cmd_extract(args) -> int:
    from ..extract.from_artifacts import extract_from_artifacts
    from ..extract.from_code import extract_from_code
    from ..core.parser import save_model
    from ..core.merger import merge_manifest

    if args.from_code:
        code_path = Path(args.from_code)
        output = Path(args.output) if args.output else code_path / "architecture-model.yaml"
        print(f"Extracting architecture model from code: {code_path}")
        model = extract_from_code(code_path)
    elif args.artifact_dir:
        artifact_dir = Path(args.artifact_dir)
        output = Path(args.output) if args.output else artifact_dir.parent / "architecture-model.yaml"
        print(f"Extracting architecture model from: {artifact_dir}")
        model = extract_from_artifacts(artifact_dir, project=args.project, system=args.system)
    else:
        print("ERROR: Provide either <artifact_dir> or --from-code PATH")
        return 1

    if args.manifest:
        manifest_path = Path(args.manifest)
        if manifest_path.exists():
            merge_manifest(model, manifest_path)
            print(f"  Merged manifest: {manifest_path}")

    print(f"  Entities: {model.entity_count}")
    print(f"    Actors: {len(model.entities.actors)}")
    print(f"    Capabilities: {len(model.entities.capabilities)}")
    print(f"    Behaviors: {len(model.entities.behaviors)}")
    print(f"    Interfaces: {len(model.entities.interfaces)}")
    print(f"    Constraints: {len(model.entities.constraints)}")
    print(f"    Layers: {len(model.entities.layers)}")
    print(f"    Components: {len(model.entities.components)}")
    print(f"  Relationships: {model.relationship_count}")

    save_model(model, output)
    print(f"\nSaved: {output}")
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


def _cmd_query(args) -> int:
    from ..core.parser import load_model
    from ..integrations.llm_context import query_model

    model = load_model(args.model)
    print(query_model(model, args.question))
    return 0


def _cmd_context(args) -> int:
    from ..core.parser import load_model
    from ..integrations.llm_context import (
        format_model_context,
        format_fblock_context,
        format_artifact_context,
    )

    model = load_model(args.model)

    if args.artifact:
        ctx = format_artifact_context(model, args.artifact, max_tokens=args.tokens)
    elif args.fblock:
        ctx = format_fblock_context(model, args.fblock, max_tokens=args.tokens)
    else:
        ctx = format_model_context(model, max_tokens=args.tokens, detail_level=args.detail)

    print(ctx)
    print(f"\n---\n[{len(ctx)} chars, ~{len(ctx) // 4} tokens]")
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
    from ..core.parser import load_model
    from ..integrations.llm_context import impact_analysis

    model = load_model(args.model)
    print(impact_analysis(model, args.entity_id, depth=args.depth))
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


if __name__ == "__main__":
    sys.exit(main())
