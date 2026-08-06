"""Full end-to-end architecture extraction pipeline."""
from __future__ import annotations

from dataclasses import replace as dc_replace
from pathlib import Path

from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, RelationType, System
)


def _has_non_python_sources(repo_path: Path) -> bool:
    """Check if repo contains non-Python source files worth scanning."""
    jvm_exclude = {"build", ".gradle", "generated", "ksp", "kspCaches", ".git"}
    for ext in ("*.kt", "*.java"):
        for f in repo_path.rglob(ext):
            if not any(part in jvm_exclude for part in f.parts):
                return True
    return False


def _components_from_config(config, manifest, source_graph=None):
    """Create components from config functional blocks, auto-group remainders.

    Each FunctionalBlockConfig becomes a Component. Files are assigned by
    explicit block.files + files under block.dirs. Remaining unassigned
    files get auto-grouped using group_modules().
    """
    from architecture_model.core.types import Component
    from architecture_model.manifest.grouping import group_modules
    from architecture_model.manifest.generator import generate_manifest as _gen_manifest
    from architecture_model.config.loader import discover_config as _discover

    repo_path = config.root
    components = []
    assigned_files: set[str] = set()

    for i, block in enumerate(config.functional_blocks, 1):
        # Collect files: explicit files + files under dirs
        block_files: list[str] = list(block.files)
        for d in block.dirs:
            dir_path = repo_path / d
            if dir_path.is_dir():
                for f in dir_path.rglob("*.py"):
                    rel = str(f.relative_to(repo_path))
                    if rel not in block_files:
                        block_files.append(rel)

        assigned_files.update(block_files)
        components.append(Component(
            id=f"COMP-{i}",
            name=block.name,
            status="ACTIVE",
            source_block=block.id,
            files=sorted(block_files),
        ))

    # Generate a full manifest (auto-discovered config scans all dirs) for remainders
    discovered_cfg, _ = _discover(repo_path)
    full_manifest = _gen_manifest(repo_path, config=discovered_cfg)
    remaining_modules = [
        m for m in full_manifest.modules if m.file not in assigned_files
    ]
    if remaining_modules:
        remaining_interfaces = [
            e for e in (manifest.interfaces if hasattr(manifest, "interfaces") else [])
            if e.source in {m.file for m in remaining_modules}
        ]
        groups = group_modules(remaining_modules, remaining_interfaces)
        offset = len(components) + 1
        for j, g in enumerate(groups):
            components.append(Component(
                id=f"COMP-{offset + j}",
                name=g.name,
                status="ACTIVE",
                files=list(g.modules),
            ))

    return components


def _derive_component_dependencies(components, manifest):
    """Create depends-on relationships between components based on import edges."""
    from architecture_model.core.types import Relationship, RelationType

    file_to_comp = {}
    for comp in components:
        for f in (comp.files or []):
            file_to_comp[f] = comp.id

    # Build dotted module path → file mapping from file paths
    name_to_file = {}
    for mod in manifest.modules:
        # Convert file path to dotted module name: "app/services/user_service.py" → "app.services.user_service"
        dotted = mod.file.replace("/", ".").replace("\\", ".")
        if dotted.endswith(".py"):
            dotted = dotted[:-3]
        if dotted.endswith(".__init__"):
            dotted = dotted[:-9]
        name_to_file[dotted] = mod.file

    edges = set()
    for mod in manifest.modules:
        src_comp = file_to_comp.get(mod.file)
        if not src_comp:
            continue
        for imp in (mod.imports or []):
            target_file = name_to_file.get(imp)
            if not target_file:
                for mname, mfile in name_to_file.items():
                    if imp.startswith(mname + ".") or mname.startswith(imp + "."):
                        target_file = mfile
                        break
            if target_file:
                tgt_comp = file_to_comp.get(target_file)
                if tgt_comp and tgt_comp != src_comp:
                    edges.add((src_comp, tgt_comp))

    return [
        Relationship(type=RelationType.DEPENDS_ON, from_id=src, to_id=tgt)
        for src, tgt in sorted(edges)
    ]


def full_extraction(repo_path: Path, target_systems: int = 0) -> ArchitectureModel:
    """Run complete architecture extraction pipeline.
    
    Pipeline steps:
    1. Generate manifest (AST scan) + optionally scan non-Python languages
    2. Build call graph from manifest
    3. Group modules into components (uses SourceGraph path if multi-language)
    4. Create initial model with components
    5. Detect system boundaries (multi-signal)
    6. Create behaviors from manifest (router/service functions)
    7. Detect behavior triggers from call graph
    8. Infer composite behaviors (use cases from trigger chains)
    9. Decompose behaviors (raw steps → structured Steps)
    10. Infer capabilities from behavior trigger patterns
    11. Build capability hierarchy from URL nesting
    12. Return enriched model
    
    Args:
        repo_path: Path to repository root
        target_systems: Number of systems to detect (0 = auto)
    
    Returns:
        Fully enriched ArchitectureModel
    """
    from architecture_model.manifest.generator import generate_manifest
    from architecture_model.manifest.call_graph import build_call_graph
    from architecture_model.manifest.grouping import (
        create_components_from_manifest, group_source_graph
    )
    from architecture_model.core.decomposer import detect_systems
    from architecture_model.orchestration.auto_enrich import create_behaviors_from_manifest
    from architecture_model.orchestration.trigger_detection import (
        detect_behavior_triggers, build_behavior_entry_map
    )
    from architecture_model.orchestration.use_case_inference import infer_composite_behaviors
    from architecture_model.orchestration.behavior_decompose import decompose_all_behaviors
    from architecture_model.orchestration.capability_inference import (
        infer_capabilities, build_capability_hierarchy
    )
    from architecture_model.core.types import Relationship, Component
    
    # Step 1: Generate Python manifest (always needed for call graph + behaviors)
    manifest = generate_manifest(repo_path)
    
    # Step 1b: Check for non-Python sources
    multi_language = _has_non_python_sources(repo_path)
    source_graph = None
    
    if multi_language:
        try:
            from architecture_model.manifest.multi_scanner import scan_all_languages
            from architecture_model.manifest.protocol import SourceGraph
            source_graph = scan_all_languages(repo_path)
        except Exception:
            multi_language = False  # fallback to Python-only
    
    # Step 2: Build call graph (Python only — JVM call graph not supported yet)
    call_graph = build_call_graph(manifest)
    
    # Step 3: Group modules into components
    # Try config-driven grouping first
    config_components = None
    try:
        from architecture_model.config.loader import load_config
        config = load_config(repo_path)
        if config.functional_blocks:
            config_components = _components_from_config(config, manifest, source_graph)
    except Exception:
        pass  # Fall through to auto-grouping

    if config_components is not None:
        components = config_components
    elif multi_language and source_graph and len(source_graph.units) > len(manifest.modules):
        # Multi-language path: use SourceGraph grouping
        groups = group_source_graph(source_graph)
        components = []
        for i, g in enumerate(groups, 1):
            components.append(Component(
                id=f"COMP-{i}",
                name=g.name,
                status="ACTIVE",
                files=list(g.modules),  # file paths from group
            ))
    else:
        # Python-only path: use manifest grouping
        components = create_components_from_manifest(manifest)
    
    # Step 4: Create initial model
    project_name = repo_path.name
    model = ArchitectureModel(
        meta=ModelMeta(project=project_name, schema_version="1.3"),
        entities=Entities(components=components),
        relationships=[]
    )
    
    # Step 5: Detect system boundaries
    system_scores = detect_systems(model, manifest, target_systems=target_systems)
    systems = []
    for i, ss in enumerate(system_scores, 1):
        systems.append(System(
            id=f"SYS-{i}",
            name=ss.name,
            status="ACTIVE",
            component_ids=ss.component_ids,
            complexity_score=ss.independence,
        ))
    model = dc_replace(model, entities=dc_replace(model.entities, systems=systems))
    
    # Step 6: Create behaviors from manifest
    behaviors, beh_rels = create_behaviors_from_manifest(model, manifest)
    model = dc_replace(
        model,
        entities=dc_replace(model.entities, behaviors=behaviors),
        relationships=list(model.relationships) + beh_rels
    )
    
    # Step 6b: Derive component-to-component dependencies from imports
    comp_rels = _derive_component_dependencies(components, manifest)
    model = dc_replace(model, relationships=list(model.relationships) + comp_rels)

    # Step 7: Detect behavior triggers
    entry_map = build_behavior_entry_map(behaviors, call_graph)
    trigger_rels = detect_behavior_triggers(behaviors, call_graph, entry_map)
    model = dc_replace(model, relationships=list(model.relationships) + trigger_rels)
    
    # Step 8: Infer composite behaviors (use cases)
    model = infer_composite_behaviors(model)
    
    # Step 9: Decompose behaviors (structured steps)
    model = decompose_all_behaviors(model, manifest)
    
    # Step 10: Infer capabilities
    model = infer_capabilities(model)
    
    # Step 11: Build capability hierarchy
    model = build_capability_hierarchy(model)
    
    # Normalize relationship types to enums for save_model() compatibility
    normalized_rels = []
    for r in model.relationships:
        if isinstance(r.type, str):
            try:
                r = dc_replace(r, type=RelationType(r.type))
            except ValueError:
                pass
        normalized_rels.append(r)
    model = dc_replace(model, relationships=normalized_rels)

    return model


def full_extraction_with_docs(
    repo_path: Path,
    target_systems: int = 0,
    output_dir: str = ".architecture-models",
) -> tuple[ArchitectureModel, dict]:
    """Full extraction + docs + compaction + hierarchical output.

    Produces:
    - Compact .architecture-model.yaml (use cases + summaries only)
    - .architecture-models/full-model.yaml (complete reference)
    - .architecture-models/docs/ (component specs, behavior specs, diagrams, etc.)
    - .architecture-models/COMP-*/ (per-component sub-models with full behaviors)

    Args:
        repo_path: Path to repository root
        target_systems: Number of systems to detect (0 = auto)
        output_dir: Output directory name (default: .architecture-models)

    Returns:
        (compact_model, artifacts) where artifacts describes what was written.
    """
    from architecture_model.core.parser import save_model
    from architecture_model.orchestration.compaction import compact_for_storage

    artifacts: dict = {"errors": []}
    out = repo_path / output_dir

    # Step 1: Run full extraction
    model = full_extraction(repo_path, target_systems=target_systems)
    artifacts["full_model"] = {
        "components": len(model.entities.components),
        "systems": len(model.entities.systems or []),
        "behaviors": len(model.entities.behaviors or []),
        "capabilities": len(model.entities.capabilities or []),
        "relationships": len(model.relationships),
    }

    # Step 2: Save full model as reference
    full_model_path = out / "full-model.yaml"
    full_model_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        save_model(model, full_model_path)
        artifacts["full_model_path"] = str(full_model_path)
    except Exception as e:
        artifacts["errors"].append(f"full model save: {e}")

    # Step 3: Generate manifest for doc generation
    manifest = None
    try:
        from architecture_model.manifest.generator import generate_manifest
        manifest = generate_manifest(repo_path)
    except Exception as e:
        artifacts["errors"].append(f"manifest: {e}")

    # Step 4: Generate docs
    docs_dir = out / "docs"
    try:
        from architecture_model.docs.generator import generate_docs
        doc_result = generate_docs(model, docs_dir, manifest=manifest)
        artifacts["docs"] = {k: len(v) for k, v in doc_result.items()}
    except Exception as e:
        artifacts["errors"].append(f"docs: {e}")

    # Step 5: Generate diagrams
    try:
        from architecture_model.docs.diagrams import generate_all_diagrams
        diag_dir = docs_dir / "diagrams"
        diagram_paths = generate_all_diagrams(model, diag_dir)
        artifacts["diagrams"] = len(diagram_paths)
    except Exception as e:
        artifacts["errors"].append(f"diagrams: {e}")

    # Step 6: Generate behavior specs + index
    try:
        from architecture_model.manifest.call_graph import build_call_graph
        from architecture_model.orchestration.behavior_flows import (
            classify_behaviors, summarize_crud_group, build_behavior_manifest,
            build_file_to_comp,
        )
        from architecture_model.docs.behavior_spec import (
            generate_behavior_spec, generate_behavior_index,
        )

        if manifest and (model.entities.behaviors or []):
            call_graph = build_call_graph(manifest)
            file_to_comp = build_file_to_comp(model, manifest)
            classification = classify_behaviors(
                model.entities.behaviors, model.relationships,
                call_graph, file_to_comp,
            )

            beh_dir = docs_dir / "behaviors"
            beh_dir.mkdir(parents=True, exist_ok=True)

            for behavior, flow_trace in classification.cross_component:
                try:
                    scoped = build_behavior_manifest(behavior, flow_trace, manifest)
                    spec_md = generate_behavior_spec(
                        behavior, flow_trace, scoped, file_to_comp,
                    )
                    (beh_dir / f"{behavior.id}.md").write_text(spec_md)
                except Exception:
                    continue

            crud_summaries = {
                comp_id: summarize_crud_group(comp_id, behs)
                for comp_id, behs in classification.crud_groups.items()
            }
            index_md = generate_behavior_index(classification, crud_summaries)
            (beh_dir / "index.md").write_text(index_md)
            artifacts["behavior_specs"] = {
                "cross_component": len(classification.cross_component),
                "crud_groups": len(classification.crud_groups),
            }
    except Exception as e:
        artifacts["errors"].append(f"behavior specs: {e}")

    # Step 7: Compact model for storage
    compact, offloaded = compact_for_storage(model)
    artifacts["compaction"] = {
        "original_behaviors": len(model.entities.behaviors or []),
        "compact_behaviors": len(compact.entities.behaviors or []),
        "offloaded_components": len(offloaded),
    }

    # Step 8: Write per-component sub-models with full behaviors
    for comp_id, comp_behaviors in offloaded.items():
        comp_dir = out / comp_id
        comp_dir.mkdir(parents=True, exist_ok=True)
        # Build sub-model: component + its behaviors + relevant relationships
        comp = next(
            (c for c in model.entities.components if c.id == comp_id), None,
        )
        if not comp:
            continue
        comp_beh_ids = {b.id for b in comp_behaviors}
        comp_rels = [
            r for r in model.relationships
            if r.from_id == comp_id or r.to_id in comp_beh_ids
        ]
        sub_model = ArchitectureModel(
            meta=ModelMeta(
                project=f"{model.meta.project}/{comp.name}",
                schema_version="1.3",
            ),
            entities=Entities(
                components=[comp],
                behaviors=comp_behaviors,
            ),
            relationships=comp_rels,
        )
        try:
            save_model(sub_model, comp_dir / ".architecture-model.yaml")
        except Exception as e:
            artifacts["errors"].append(f"sub-model {comp_id}: {e}")

    # Step 9: Save compact model as the main model
    try:
        save_model(compact, repo_path / ".architecture-model.yaml")
        artifacts["compact_model_path"] = str(
            repo_path / ".architecture-model.yaml"
        )
    except Exception as e:
        artifacts["errors"].append(f"compact model save: {e}")

    return compact, artifacts
