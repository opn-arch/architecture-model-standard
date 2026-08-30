"""
CLI for the Architecture Model Standard.

Usage:
    architecture-model validate <model.yaml> [--strict]
    architecture-model slice <model.yaml> --source_block F3
    architecture-model slice <model.yaml> --artifact use-cases
    architecture-model diff <old.yaml> <new.yaml>
    architecture-model stats <model.yaml>
    architecture-model pipeline <path> [--stage observe]
    architecture-model manifest <path>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

GLOBAL_LEARNING_PATH = Path.home() / ".config" / "opencode" / "arch-learning"


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
    p_slice.add_argument("--source_block", help="Filter by F-block (e.g., F3)")
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

    # --- impact ---
    p_impact = subparsers.add_parser("impact", help="Impact analysis for an entity")
    p_impact.add_argument("model", help="Path to architecture-model.yaml")
    p_impact.add_argument("entity_id", help="Entity ID to analyze")
    p_impact.add_argument("--depth", type=int, default=2, help="Traversal depth")

    # --- manifest ---
    p_manifest = subparsers.add_parser("manifest", help="Generate reality-manifest.json from source code")
    p_manifest.add_argument("path", nargs="?", default=".", help="Project root directory (default: cwd)")
    p_manifest.add_argument("-o", "--output", help="Output JSON path")
    p_manifest.add_argument("--recursive", action="store_true", help="Generate per-F-block recursive manifests")

    # --- enrich ---
    p_enrich = subparsers.add_parser("enrich", help="Auto-enrich model with signatures, constants, test contracts")
    p_enrich.add_argument("model", help="Path to architecture-model.yaml")
    p_enrich.add_argument("--root", default=".", help="Project root directory")

    # --- decompose ---
    p_decompose = subparsers.add_parser("decompose", help="Generate per-F-block sub-models from parent model")
    p_decompose.add_argument("path", nargs="?", default=".", help="Project root directory (default: cwd)")
    p_decompose.add_argument("-o", "--output", help="Output directory (default: .architecture-models/)")

    # --- coverage ---
    p_coverage = subparsers.add_parser("coverage", help="Analyze model coverage against code reality")
    p_coverage.add_argument("model", help="Path to .architecture-model.yaml")
    p_coverage.add_argument("--project", "-p", help="Project path for manifest generation (default: model directory)")
    p_coverage.add_argument("--manifest", help="Path to pre-generated manifest JSON")

    # --- docs ---
    p_docs = subparsers.add_parser("docs", help="Generate architecture documentation site")
    p_docs.add_argument("repo", help="Repository root path")
    p_docs.add_argument("-o", "--output", help="Output directory (default: {repo}/.architecture-models/docs)")
    p_docs.add_argument("--se", action="store_true", help="Generate SE documents (ConOps, V&V, etc.)")
    p_docs.add_argument("--se-only", action="store_true", help="Generate only SE documents")
    p_docs.add_argument("--formats", help="Comma-separated doc types (e.g. conops,use_cases,se_all)")
    p_docs.add_argument("--pdf", action="store_true", help="Also generate PDF output from markdown docs")

    # --- visualize ---
    p_visualize = subparsers.add_parser("visualize", help="Generate Mermaid diagrams from architecture model")
    p_visualize.add_argument("path", nargs="?", default=".", help="Project root directory (default: cwd)")
    p_visualize.add_argument("-o", "--output", default="output/diagrams", help="Output directory (default: output/diagrams)")

    # --- author ---
    p_author = subparsers.add_parser("author", help="Generate model from requirements document")
    p_author.add_argument("requirements", help="Path to requirements markdown file")
    p_author.add_argument("-o", "--output", default=".architecture-model.yaml", help="Output YAML path")

    # --- regen-score ---
    p_regen = subparsers.add_parser("regen-score", help="Show regen readiness score for enriched model")
    p_regen.add_argument("path", nargs="?", default=".", help="Project root directory (default: cwd)")
    p_regen.add_argument("--component", help="Show detail for a specific component ID")
    p_regen.add_argument("--verbose", action="store_true", help="Show per-function readiness")

    # --- pipeline ---
    p_pipeline = subparsers.add_parser("pipeline", help="Run modular extraction pipeline")
    p_pipeline.add_argument("path", nargs="?", default=".", help="Project root directory (default: cwd)")
    p_pipeline.add_argument("--stage", help="Run up to this stage (default: all)")
    p_pipeline.add_argument("--recursive", action="store_true", help="Recurse into large components")
    p_pipeline.add_argument("--max-depth", type=int, default=3, help="Max recursion depth")
    p_pipeline.add_argument("-o", "--output", help="Output directory (default: .architecture/)")
    p_pipeline.add_argument("--llm-review", action="store_true", help="Enable LLM review of stage outputs")
    p_pipeline.add_argument("--gap-analysis", action="store_true", help="Run gap analysis after pipeline")

    # --- gap-analysis ---
    p_gap = subparsers.add_parser("gap-analysis", help="Run gap analysis: deterministic vs LLM pipeline comparison")
    p_gap.add_argument("path", nargs="?", default=".", help="Project root directory")
    p_gap.add_argument("-o", "--output", help="Output directory for report")

    subparsers.add_parser("learnings", help="Show global learnings (heuristics, archetypes, workflows)")

    # --- quality ---
    p_quality = subparsers.add_parser("quality", help="Generate unified quality report")
    p_quality.add_argument("repo", help="Repository root path")
    p_quality.add_argument("--markdown", action="store_true", help="Output as markdown")

    # --- review ---
    p_review = subparsers.add_parser("review", help="Analyze and improve code quality")
    p_review.add_argument("path", help="File or directory to review")
    p_review.add_argument("--auto", action="store_true", help="Auto-apply safe changes")
    p_review.add_argument("--target-score", type=int, default=80, help="Target quality score")
    p_review.add_argument("--compare", nargs=2, metavar=("FILE_A", "FILE_B"),
                           help="Compare two implementations")
    p_review.add_argument("--feedback", action="store_true",
                           help="Generate model feedback from code analysis")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch
    handlers = {
        "validate": _cmd_validate,
        "slice": _cmd_slice,
        "diff": _cmd_diff,
        "stats": _cmd_stats,
        "impact": _cmd_impact,
        "manifest": _cmd_manifest,
        "coverage": _cmd_coverage,
        "enrich": _cmd_enrich,
        "decompose": _cmd_decompose,
        "visualize": _cmd_visualize,
        "docs": _cmd_docs,
        "author": _cmd_author,
        "regen-score": _cmd_regen_score,
        "pipeline": _cmd_pipeline,
        "learnings": _cmd_learnings,
        "quality": _cmd_quality,
        "review": _cmd_review,
        "gap-analysis": _cmd_gap_analysis,
    }
    return handlers[args.command](args)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


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
    from ..core.slicer import slice_by_source_block, slice_by_layer, slice_by_status, slice_for_artifact
    from ..core.types import Status

    model = load_model(args.model)

    if args.source_block:
        sliced = slice_by_source_block(model, args.source_block)
        label = f"F-block: {args.source_block}"
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
        print("ERROR: Provide --source_block, --layer, --artifact, or --status")
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

    # Compression stats
    try:
        from ..core.compression import compute_compression_stats, format_compression_summary
        model_path = Path(args.model)
        project_root = model_path.parent if model_path.is_file() else model_path
        stats = compute_compression_stats(project_root)
        if stats["source_bytes"] > 0:
            print()
            print(format_compression_summary(stats))
    except Exception:
        pass

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

    if args.recursive:
        from ..manifest.recursive import generate_recursive_manifests, write_recursive_manifests
        manifests = generate_recursive_manifests(root)
        out_dir = Path(args.output) if args.output else root / "output" / "manifests"
        written = write_recursive_manifests(manifests, out_dir)
        print(f"Generated {len(written)} recursive manifests in {out_dir}")
        return 0

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
    from ..orchestration.enrich import enrich_model

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


def _cmd_decompose(args) -> int:
    """Generate per-F-block sub-models from parent model + recursive manifests."""
    from ..orchestration.decompose import decompose_model, write_sub_models

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory")
        return 1

    model_path = root / ".architecture-model.yaml"
    if not model_path.exists():
        print(f"ERROR: No .architecture-model.yaml in {root}")
        return 1

    print(f"Decomposing: {root}")
    sub_models = decompose_model(root)

    if not sub_models:
        print("No sub-models generated (no F-blocks with matching components)")
        return 1

    out_dir = Path(args.output) if args.output else root / ".architecture-models"
    written = write_sub_models(sub_models, out_dir)

    print(f"\nGenerated {len(written)} sub-models in {out_dir}")
    for p in written:
        block_id = p.parent.name
        m = sub_models[block_id]
        print(f"  {block_id}: {m.entity_count} entities, {m.relationship_count} relationships")

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
        from ..config.loader import get_config
        from ..manifest.generator import generate_manifest

        config = get_config(project)
        manifest = generate_manifest(project, config=config)

    # Convert Manifest dataclass to dict if needed
    if not isinstance(manifest, dict):
        manifest = manifest.to_dict() if hasattr(manifest, 'to_dict') else manifest

    result = coverage_report(model, manifest)
    print(result.summary())
    return 0 if result.overall_score >= 80 else 1


def _cmd_visualize(args) -> int:
    """Generate Mermaid diagrams from architecture model."""
    from ..core.parser import load_model
    from ..core.visualize import generate_all_diagrams

    root = Path(args.path).resolve()
    model_path = root / ".architecture-model.yaml"
    if not model_path.exists():
        print(f"ERROR: No .architecture-model.yaml in {root}")
        return 1

    model = load_model(model_path)
    out_dir = Path(args.output)
    if not out_dir.is_absolute():
        out_dir = root / out_dir

    paths = generate_all_diagrams(model, out_dir)
    print(f"Generated {len(paths)} diagrams in {out_dir}/")
    for name in sorted(paths):
        print(f"  {paths[name].name}")
    return 0


def _cmd_docs(args) -> int:
    """Generate architecture documentation."""
    from ..core.parser import load_model
    from ..docs import generate_docs

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"ERROR: {repo} is not a directory")
        return 1

    # Find model file
    model_path = repo / ".architecture-model-extracted.yaml"
    if not model_path.exists():
        model_path = repo / ".architecture-model.yaml"
    if not model_path.exists():
        print(f"ERROR: No architecture model found in {repo}")
        return 1

    model = load_model(model_path)

    # Optionally generate manifest for health report
    manifest = None
    try:
        from ..manifest import generate_manifest
        manifest = generate_manifest(repo)
    except Exception:
        pass

    output_dir = Path(args.output) if args.output else repo / ".architecture-models" / "docs"

    # SE document generation
    se_mode = getattr(args, "se", False) or getattr(args, "se_only", False)
    se_only = getattr(args, "se_only", False)
    formats_arg = getattr(args, "formats", None)

    if not se_only:
        result = generate_docs(model, output_dir=output_dir, manifest=manifest)

    if se_mode or se_only or (formats_arg and any(f.strip() in (
        "se_all", "conops", "functional_analysis", "logical_architecture",
        "requirements_analysis", "verification_validation", "operations_manual",
        "maintenance_manual", "use_cases", "risk_assessment", "interface_spec",
    ) for f in formats_arg.split(","))):
        try:
            from ..docs.se.generator import generate_se_docs
            se_dir = output_dir / "se"
            doc_filter = None
            if formats_arg:
                doc_filter = [f.strip() for f in formats_arg.split(",") if f.strip() != "se_all"]
                if not doc_filter:
                    doc_filter = None
            se_result = generate_se_docs(model, se_dir, manifest, doc_filter=doc_filter)
            se_count = len(se_result.get("generated", []))
            print(f"Generated {se_count} SE documents in {se_dir}/")
        except Exception as e:
            print(f"SE doc generation failed: {e}")

    print(f"Generated docs in {output_dir}/")
    for f in sorted(output_dir.rglob("*.md")):
        print(f"  {f.relative_to(output_dir)}")

    if getattr(args, "pdf", False):
        try:
            import subprocess
            md_files = sorted(output_dir.rglob("*.md"))
            if md_files:
                pdf_path = output_dir / "architecture-docs.pdf"
                # Try pandoc first, fall back to simple concatenation message
                try:
                    cmd = ["pandoc", "-o", str(pdf_path)] + [str(f) for f in md_files]
                    subprocess.run(cmd, check=True, capture_output=True)
                    print(f"Generated PDF: {pdf_path}")
                except FileNotFoundError:
                    print("WARNING: pandoc not found. Install pandoc to generate PDF output.")
                    print("  brew install pandoc  # or apt-get install pandoc")
                    return 1
        except Exception as e:
            print(f"PDF generation failed: {e}")
            return 1

    return 0


def _cmd_author(args) -> int:
    from ..authoring.parser import parse_requirements_doc

    req_path = Path(args.requirements)
    if not req_path.exists():
        print(f"ERROR: {req_path} does not exist")
        return 1

    text = req_path.read_text()
    model = parse_requirements_doc(text)
    yaml_str = model.to_yaml()

    output_path = Path(args.output)
    output_path.write_text(yaml_str)

    print(f"Model written to {output_path}")
    print(f"  Actors: {len(model.entities.actors)}")
    print(f"  Capabilities: {len(model.entities.capabilities)}")
    print(f"  Constraints: {len(model.entities.constraints)}")
    print(f"  Relationships: {len(model.relationships)}")
    return 0


def _cmd_regen_score(args) -> int:
    """Show regen readiness score for an enriched architecture model."""
    from ..core.parser import load_model
    from ..core.regen_readiness import compute_regen_readiness

    root = Path(args.path).resolve()
    model_path = root / ".architecture-model.yaml" if root.is_dir() else root
    if not model_path.exists():
        print(f"ERROR: No .architecture-model.yaml found in {root}")
        return 1

    model = load_model(model_path)
    result = compute_regen_readiness(model)

    # Single component detail
    if args.component:
        comp = next((c for c in result.components if c.id == args.component), None)
        if not comp:
            print(f"ERROR: Component '{args.component}' not found")
            return 1
        _print_component_verbose(comp)
        return 0

    # Verbose: all components with function detail
    if args.verbose:
        print(f"Regen Readiness: {result.overall:.0f}/100 ({result.grade})\n")
        for comp in result.components:
            _print_component_verbose(comp)
            print()
        return 0

    # Default summary
    print(f"Regen Readiness: {result.overall:.0f}/100 ({result.grade})\n")
    if result.components:
        print("Components:")
        for comp in result.components:
            sigs = len(comp.functions)
            hints = sum(1 for f in comp.functions if f.has_body_hint)
            contracts = comp.test_contract_count
            blocker_str = f"  \u26a0 {len(comp.blockers)} blockers" if comp.blockers else ""
            print(f"  {comp.id:<8s} {comp.name:<14s} {comp.score:3.0f}/100 {_grade(comp.score)}  [{sigs} sigs, {hints} hints, {contracts} contracts]{blocker_str}")
    else:
        print("No enriched components found.")

    if result.blockers:
        print(f"\nBlockers ({len(result.blockers)}):")
        for b in result.blockers:
            print(f"  \u26a0 {b}")

    # Recommendation: find worst component
    if result.components:
        worst = min(result.components, key=lambda c: c.score)
        if worst.score < 80:
            print(f"\nRecommendation: Enrich {worst.id}: add body_hints and test contracts")

    return 0


def _print_component_verbose(comp) -> None:
    """Print verbose detail for a single component."""
    print(f"{comp.id} {comp.name} ({comp.score:.0f}/100 {_grade(comp.score)}):")
    print(f"  body_hint_coverage: {comp.body_hint_coverage:.0f}%  trivial_ratio: {comp.body_hint_trivial_ratio:.0f}%")
    print(f"  test_contracts: {comp.test_contract_count}  constant_coverage: {comp.constant_coverage:.0f}%  sig_coverage: {comp.signature_coverage:.0f}%")
    if comp.functions:
        print("  Functions:")
        for fn in comp.functions:
            tests_str = f"[{fn.called_in_tests} tests]"
            print(f"    {fn.name:<20s} {fn.score:3.0f}  {fn.body_hint_quality:<8s} {tests_str}")


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    return "F"


def _cmd_pipeline(args) -> int:
    """Run the modular extraction pipeline."""
    from ..pipeline.observe import ObserveStage
    from ..pipeline.infer import InferStage
    from ..pipeline.allocate import AllocateStage
    from ..pipeline.relate import RelateStage
    from ..pipeline.specify import SpecifyStage
    from ..pipeline.contract import ContractStage
    from ..pipeline.validate import ValidateStage
    from ..pipeline.decompose import DecomposeStage
    from ..pipeline.synthesize import SynthesizeStage
    from ..pipeline.emit import EmitStage
    from ..pipeline.coordinator import PipelineCoordinator
    from ..pipeline.learning import LearningStore
    from ..pipeline.protocol import PipelineContext
    from ..pipeline.artifacts import write_artifacts
    from ..pipeline.context_gen import write_context

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory")
        return 1

    output_dir = Path(args.output).resolve() if args.output else root / ".architecture"
    learning_path = output_dir / "learning"

    stages = {
        "observe": ObserveStage(),
        "infer": InferStage(),
        "allocate": AllocateStage(),
        "relate": RelateStage(),
        "specify": SpecifyStage(),
        "contract": ContractStage(),
        "validate": ValidateStage(),
        "decompose": DecomposeStage(),
        "synthesize": SynthesizeStage(),
        "emit": EmitStage(),
    }

    store = LearningStore(learning_path)
    coord = PipelineCoordinator(stages, learning_store=store)
    ctx = PipelineContext(repo_path=root, output_dir=output_dir)
    ctx.config["coordinator"] = coord  # synthesize stage needs this

    if getattr(args, "llm_review", False):
        from ..pipeline.llm_provider import create_llm_callback
        callback = create_llm_callback()
        if callback:
            ctx.llm_callback = callback
            print("LLM review enabled")
        else:
            print("WARNING: --llm-review specified but no LLM provider available")

    if args.stage:
        print(f"Running pipeline to stage: {args.stage}")
        results = coord.run_to(args.stage, ctx)
    elif args.recursive:
        print(f"Running recursive pipeline (max_depth={args.max_depth})")
        result = coord.run_recursive(ctx, max_depth=args.max_depth)
        results = result["results"]
    else:
        print("Running full pipeline")
        results = coord.run_all(ctx)

    # Write artifacts
    write_artifacts(ctx)
    write_context(ctx)

    # Print summary
    print(f"\nResults ({len(results)} stages):")
    for name, result in results.items():
        score = result.quality.score
        uncertainties = len(result.uncertainties)
        duration = result.duration_ms
        status = "PASS" if score >= 50 else "WARN"
        print(f"  {name:12s} score={int(score):3d}  uncertainties={uncertainties}  {duration}ms  [{status}]")

    print(f"\nArtifacts written to: {output_dir}")

    # Save reviews if any
    if ctx.review_log:
        from ..pipeline.review_store import save_reviews
        review_path = save_reviews(output_dir / "reviews", ctx.review_log)
        print(f"Reviews saved to: {review_path}")
        for review in ctx.review_log:
            if review.suggestions:
                print(f"\n  {review.stage} suggestions:")
                for s in review.suggestions[:3]:
                    print(f"    - {s}")

    if getattr(args, "gap_analysis", False):
        from ..pipeline.gap_analysis import extract_stage_data, diff_stage_outputs, build_naming_chains, trace_propagation, GapAnalysisResult
        from ..pipeline.gap_report import render_gap_report, render_deep_gap_report
        from ..pipeline.gap_prompts import build_reinfer_prompt, parse_reinfer_response

        print("\nRunning gap analysis...")
        if ctx.llm_callback is None:
            from ..pipeline.llm_provider import create_llm_callback
            callback = create_llm_callback()
            if callback:
                ctx.llm_callback = callback

        if ctx.llm_callback is not None:
            import asyncio
            stage_gaps = []
            det_data = {}
            llm_data = {}
            reviewable = ["infer", "allocate", "relate", "specify", "contract", "validate"]
            for stage_name in reviewable:
                if stage_name not in results:
                    continue
                stage_result = results[stage_name]
                det = extract_stage_data(stage_name, stage_result.output)
                det_data[stage_name] = det

                prompt = build_reinfer_prompt(stage_name, **det)
                try:
                    loop = asyncio.get_event_loop()
                    response = loop.run_until_complete(ctx.llm_callback(stage_name, prompt, {}))
                    llm = parse_reinfer_response(stage_name, response)
                except Exception:
                    llm = {}
                llm_data[stage_name] = llm
                gap = diff_stage_outputs(stage_name, det, llm)
                stage_gaps.append(gap)

            chains = build_naming_chains(det_data, llm_data)
            propagation = trace_propagation(det_data)

            # Build stage traces
            from ..pipeline.stage_tracer import trace_stage as _trace_stage
            inventory = results["observe"].output if "observe" in results else None
            traces = {}
            for sn in reviewable:
                if sn in det_data:
                    prior = {k: v for k, v in det_data.items() if k != sn}
                    traces[sn] = _trace_stage(sn, inventory, det_data[sn], prior, llm_data.get(sn, {}))

            gap_result = GapAnalysisResult(
                repo_path=str(root),
                stage_gaps=stage_gaps,
                naming_chains=chains,
                propagation_traces=propagation,
                summary={"stages_analyzed": len(stage_gaps)},
                traces=traces,
            )
            report = render_deep_gap_report(gap_result, traces)
            gap_path = output_dir / "gap-analysis-report.md"
            gap_path.write_text(report)
            print(f"Gap analysis report: {gap_path}")
        else:
            print("WARNING: --gap-analysis requires LLM provider (use --llm-review or set API key)")

    return 0


def _cmd_gap_analysis(args) -> int:
    """Run gap analysis comparing deterministic pipeline vs LLM alternatives."""
    from ..pipeline.gap_analysis import run_gap_analysis, GapAnalysisResult
    from ..pipeline.gap_report import render_gap_report, render_deep_gap_report
    from ..pipeline.llm_provider import create_llm_callback
    import asyncio

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory")
        return 1

    callback = create_llm_callback()
    if callback is None:
        print("ERROR: No LLM provider available. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or start copilot-relay.")
        return 1

    print(f"Running gap analysis on {root}...")
    try:
        result = asyncio.run(run_gap_analysis(root, callback))
    except Exception as e:
        print(f"ERROR: Gap analysis failed: {e}")
        return 1

    if result.traces:
        report = render_deep_gap_report(result, result.traces)
    else:
        report = render_gap_report(result)

    output_dir = Path(args.output).resolve() if args.output else root / ".architecture"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "gap-analysis-report.md"
    report_path.write_text(report)
    print(f"Report written to: {report_path}")

    # Print summary
    total_gaps = sum(len(g.added) + len(g.removed) + len(g.renamed) for g in result.stage_gaps)
    print(f"Stages analyzed: {len(result.stage_gaps)}")
    print(f"Total gaps: {total_gaps}")
    print(f"Naming chains: {len(result.naming_chains)}")
    print(f"Propagation traces: {len(result.propagation_traces)}")

    return 0


def _cmd_learnings(args) -> int:
    """Show global learnings (heuristics, archetypes, workflows)."""
    from architecture_model.pipeline.global_learning import GlobalLearningStore

    store = GlobalLearningStore(GLOBAL_LEARNING_PATH)
    rules = store.get_heuristics()
    archetypes = store.get_archetypes()
    workflows = store.get_workflows()

    if not rules and not archetypes and not workflows:
        print("No learnings recorded yet. Use architect_learn MCP tool to add.")
        return 0

    if rules:
        print(f"\n## Heuristic Rules ({len(rules)})\n")
        for r in rules:
            print(f"  {r.id} [{r.stage}]: {r.condition} → {r.action}")
            if r.validated_on:
                print(f"         validated on: {', '.join(r.validated_on)}")

    if archetypes:
        print(f"\n## Archetype Patterns ({len(archetypes)})\n")
        for a in archetypes:
            print(f"  {a.id} {a.name}: {a.problem}")
            print(f"         solution: {a.solution}")

    if workflows:
        print(f"\n## Workflow Lessons ({len(workflows)})\n")
        for w in workflows:
            print(f"  {w.id}: {w.trigger}")
            print(f"         fix: {w.fix_applied}")
            print(f"         result: {w.validation}")

    return 0


def _cmd_quality(args) -> int:
    """Generate unified quality report."""
    from ..core.parser import load_model
    from ..quality.dashboard import quality_report

    repo = Path(args.repo).resolve()
    model_path = repo / ".architecture-model.yaml"
    if not model_path.exists():
        print(f"ERROR: No architecture model found in {repo}")
        return 1

    model = load_model(model_path)
    report = quality_report(model)

    if getattr(args, "markdown", False):
        print(report.to_markdown())
    else:
        print(f"Quality Report: {report.project}")
        print(f"  Grade: {report.grade} ({report.overall_score}/100)")
        print(f"  Validation: {report.validation_score}/100 ({report.validation_issues} issues)")
        print(f"  Regen Readiness: {report.regen_readiness_score:.0f}/100")
        print(f"  Semantic Completeness:")
        for k, v in report.semantic_completeness.items():
            print(f"    {k}: {v}")
    return 0


def _cmd_review(args) -> int:
    """Analyze and improve code quality."""
    from ..quality.code_review import analyze_file, analyze_component
    from ..quality.code_prompts import compare_prompt

    path = Path(args.path).resolve()

    if args.compare:
        file_a, file_b = args.compare
        with open(file_a) as f:
            src_a = f.read()
        with open(file_b) as f:
            src_b = f.read()
        prompt = compare_prompt(src_a, src_b)
        print("Comparison prompt generated. Send to LLM:")
        print(prompt)
        return 0

    if path.is_file():
        analysis = analyze_file(str(path))
        print(f"File: {analysis.filename}")
        print(f"Score: {analysis.score}/100")
        print(f"Functions: {len(analysis.functions)}")
        print(f"Issues: {len(analysis.issues)}")
        for issue in analysis.issues:
            fixable = " [FIXABLE]" if issue.fixable else ""
            print(f"  [{issue.severity.value}] {issue.code}: {issue.message}{fixable}")

        if getattr(args, "feedback", False):
            from ..quality.model_feedback import code_to_model_feedback
            from ..core.types import Component, Status
            comp = Component(id="REVIEW", name=path.stem, status=Status.ACTIVE,
                             files=[str(path)])
            feedback = code_to_model_feedback(comp, [analysis])
            if feedback.suggested_failure_modes:
                print("\nSuggested failure_modes:")
                for fm in feedback.suggested_failure_modes:
                    print(f"  - {fm}")
            if feedback.suggested_trade_offs:
                print("\nSuggested trade_offs:")
                for to in feedback.suggested_trade_offs:
                    print(f"  - {to}")
        return 0

    elif path.is_dir():
        files = [str(f) for f in path.rglob("*.py") if not f.name.startswith("test_")]
        results = analyze_component(files)
        total_score = sum(r.score for r in results) // max(len(results), 1)
        total_issues = sum(len(r.issues) for r in results)
        print(f"Directory: {path}")
        print(f"Files: {len(results)}")
        print(f"Average Score: {total_score}/100")
        print(f"Total Issues: {total_issues}")
        for r in sorted(results, key=lambda x: x.score):
            print(f"  {r.filename}: {r.score}/100 ({len(r.issues)} issues)")
        return 0

    print(f"ERROR: {path} not found")
    return 1


if __name__ == "__main__":
    sys.exit(main())
