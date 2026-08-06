"""Full end-to-end architecture extraction pipeline."""
from __future__ import annotations

from dataclasses import replace as dc_replace
from pathlib import Path

from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, System
)


def full_extraction(repo_path: Path, target_systems: int = 0) -> ArchitectureModel:
    """Run complete architecture extraction pipeline.
    
    Pipeline steps:
    1. Generate manifest (AST scan)
    2. Build call graph from manifest
    3. Group modules into components
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
    from architecture_model.manifest.grouping import create_components_from_manifest
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
    from architecture_model.core.types import Relationship
    
    # Step 1: Generate manifest
    manifest = generate_manifest(repo_path)
    
    # Step 2: Build call graph
    call_graph = build_call_graph(manifest)
    
    # Step 3: Group modules into components
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
    
    return model
