#!/usr/bin/env python3
"""SE Architecture Enrichment: rename capabilities, add sub-capabilities, enrich use cases, actor goals."""
from pathlib import Path
from architecture_model.core.parser import load_model, save_model
from architecture_model.core.types import (
    Capability, Relationship, RelationType, Status, Priority,
)

MODEL_PATH = Path(".architecture-model.yaml")

# Task 1: Capability renames
CAP_RENAME = {
    "CAP-S1": "CAP-PARSE-VALIDATE",
    "CAP-S2": "CAP-MANIFEST",
    "CAP-S3": "CAP-SLICE-DIFF",
    "CAP-S4": "CAP-CLI",
    "CAP-S5": "CAP-CONFIG",
    "CAP-S6": "CAP-SCHEMA",
    "CAP-S7": "CAP-EXTRACT",
    "CAP-S8": "CAP-PROFILES",
    "CAP-S9": "CAP-UTILS",
    "CAP-S10": "CAP-ENRICH",
}

# Task 2: Sub-capabilities {parent_id: [(id, name, description)]}
SUB_CAPS = {
    "CAP-PARSE-VALIDATE": [
        ("CAP-VALIDATE-STRUCTURAL", "Structural Validation", "ID uniqueness, referential integrity, orphan detection"),
        ("CAP-VALIDATE-SEMANTIC", "Semantic Validation", "Status consistency, v1.1 rules, capability realization"),
        ("CAP-VALIDATE-QUALITY", "Quality Assessment", "Regen readiness scoring, improvement suggestions"),
    ],
    "CAP-MANIFEST": [
        ("CAP-MANIFEST-SCAN", "Source Scanning", "AST parsing, function/class/import extraction"),
        ("CAP-MANIFEST-METRICS", "Metrics Computation", "Line counts, complexity, body hints"),
        ("CAP-MANIFEST-TESTS", "Test Analysis", "Test contract discovery and assertion extraction"),
    ],
    "CAP-SLICE-DIFF": [
        ("CAP-SLICE", "Model Slicing", "Extract sub-models by f-block, layer, status, artifact"),
        ("CAP-DIFF", "Model Diffing", "Compare models, detect entity/relationship changes"),
        ("CAP-MERGE", "Model Merging", "Compose enriched models, compact for generation"),
    ],
    "CAP-CLI": [
        ("CAP-CLI-CORE", "Core CLI Commands", "init, validate, manifest"),
        ("CAP-CLI-ANALYSIS", "Analysis CLI Commands", "slice, diff, stats, impact, coverage"),
        ("CAP-CLI-GENERATION", "Generation CLI Commands", "decompose, visualize, enrich"),
    ],
    "CAP-ENRICH": [
        ("CAP-ENRICH-SIGS", "Signature Enrichment", "Extract function signatures from AST"),
        ("CAP-ENRICH-CONSTS", "Constant Enrichment", "Extract module-level constants"),
        ("CAP-ENRICH-TESTS", "Test Contract Enrichment", "Discover and extract test contracts"),
    ],
}

# Task 3: Use case enrichment
USE_CASES = {
    "BEH-INIT": {
        "actor": "ACT-DEV",
        "trigger": "CLI: architecture-model init <path>",
        "preconditions": ["Project directory exists", "Directory contains Python source files"],
        "steps": [
            "Scan directory structure for source root (src-layout, flat-layout, lib-layout)",
            "Discover subpackages as functional blocks",
            "Enumerate files per block",
            "Write .architecture-model.yaml with layers, F-blocks, and metrics",
        ],
        "postconditions": [".architecture-model.yaml created", "Each subpackage mapped to an F-block"],
    },
    "BEH-VALIDATE": {
        "actor": "ACT-DEV",
        "trigger": "CLI: architecture-model validate <path>",
        "preconditions": [".architecture-model.yaml exists", "File is valid YAML"],
        "steps": [
            "Parse YAML into ArchitectureModel (S3: parser)",
            "Check ID uniqueness across all entity types",
            "Verify referential integrity of all relationship endpoints",
            "Detect orphaned entities with no relationships",
            "Check status consistency on all entities",
            "Verify all capabilities are realized by components",
            "Validate meta section completeness",
            "Apply v1.1 semantic rules",
            "Score regen readiness per component",
            "Apply domain profile rules if set (S7: profiles)",
            "Aggregate issues by severity, compute score 0-100",
            "Display results to developer (S1: CLI)",
        ],
        "postconditions": ["Validation score 0-100 reported", "Issues listed by severity (ERROR, WARNING, INFO)"],
    },
    "BEH-MANIFEST": {
        "actor": "ACT-DEV",
        "trigger": "CLI: architecture-model manifest <path>",
        "preconditions": ["Project directory exists", "Configuration available (auto-discovered or .architecture-model.yaml)"],
        "steps": [
            "Load or discover project configuration (S2: config)",
            "Compute project-wide metrics (total lines, file counts)",
            "Assemble functional blocks from config",
            "Scan all source files via AST (S5: scanner)",
            "Extract functions, classes, imports, constants per file",
            "Classify function complexity and generate body hints (S5: body_hints)",
            "Discover inter-block interfaces from import analysis (S5: interfaces)",
            "Assemble final manifest with blocks, interfaces, metrics",
        ],
        "postconditions": ["Manifest JSON written with all blocks and metrics", "Each file scanned with function signatures and body hints"],
    },
    "BEH-ENRICH": {
        "actor": "ACT-DEV",
        "trigger": "CLI: architecture-model enrich <path>",
        "preconditions": [".architecture-model.yaml exists", "Source files accessible"],
        "steps": [
            "Load architecture model",
            "For each component with source files, extract function signatures from AST",
            "Extract module-level constants and enum members",
            "Discover test files via 7 naming conventions",
            "Extract test contracts (assertions, expected values) from test AST",
            "Update component signatures, constants, and test_contracts fields",
            "Save enriched model",
        ],
        "postconditions": ["Components enriched with signatures, constants, test_contracts", "Model regen-readiness score improved"],
    },
    "BEH-EXTRACT": {
        "actor": "ACT-LLM",
        "trigger": "MCP tool: architect_extract",
        "preconditions": ["Source code accessible", "Manifest generated"],
        "steps": [
            "Analyze source structure to derive capabilities",
            "Identify external actors from usage patterns",
            "Map source modules to architecture components",
            "Derive interfaces from import/export analysis",
            "Infer relationships between entities",
            "Assemble and validate architecture model",
        ],
        "postconditions": ["Architecture model extracted from code", "Model validates at score >= 90"],
    },
    "BEH-SLICE": {
        "actor": "ACT-LLM",
        "trigger": "MCP tool: architect_slice / CLI: architecture-model slice",
        "preconditions": ["Architecture model loaded"],
        "steps": [
            "Select slicing strategy (f-block, layer, status, artifact, component)",
            "Trace relationships from seed entities to find connected entities",
            "Build filtered model with selected entities and relevant relationships",
            "Preserve cross-boundary dependency edges",
        ],
        "postconditions": ["Sub-model returned with only relevant entities", "All internal relationships preserved"],
    },
    "BEH-DIFF": {
        "actor": "ACT-DEV",
        "trigger": "CLI: architecture-model diff <model1> <model2>",
        "preconditions": ["Two valid architecture models provided"],
        "steps": [
            "Load both models",
            "Compare entities: detect added, removed, modified per entity type",
            "Compare relationships: detect added, removed",
            "Format diff report",
        ],
        "postconditions": ["Diff report showing all changes between models"],
    },
    "BEH-MERGE": {
        "actor": "ACT-LLM",
        "trigger": "Programmatic API call",
        "preconditions": ["Base model and manifest both available"],
        "steps": [
            "Load base architecture model",
            "Load reality manifest with AST data",
            "Merge manifest modules into component file lists",
            "Enrich components with manifest-derived signatures and metrics",
            "Resolve conflicts (model takes precedence over manifest)",
            "Compact model for generation context if needed",
        ],
        "postconditions": ["Enriched model with manifest data merged", "Component file lists updated from manifest"],
    },
    "BEH-DECOMPOSE": {
        "actor": "ACT-DEV",
        "trigger": "CLI: architecture-model decompose <path>",
        "preconditions": [".architecture-model.yaml exists", "Components have source_block assignments"],
        "steps": [
            "Load parent architecture model",
            "For each F-block, find all components with matching source_block",
            "Find parent component for each block's component hierarchy",
            "Trace relationships to find connected capabilities, interfaces, behaviors, constraints",
            "Collect internal and boundary relationships",
            "Inject sub-behaviors from sub-behaviors.yaml for matched components",
            "Build and save sub-model YAML per F-block",
        ],
        "postconditions": ["One sub-model per F-block in .architecture-models/", "Sub-models contain unique sub-behaviors not in parent"],
    },
}

# Task 5: Actor goals
ACTOR_GOALS = {
    "ACT-DEV": [
        "Validate architecture model correctness",
        "Generate manifest from source code",
        "Slice model for focused analysis",
        "Track model changes over time",
        "Enrich model with AST-derived data",
        "Decompose model into per-block sub-models",
    ],
    "ACT-LLM": [
        "Load compressed architecture context",
        "Generate code from architecture model",
        "Update model based on code changes",
        "Extract architecture from unfamiliar codebases",
    ],
}

NEW_ACTOR_RELS = [
    ("consumes", "ACT-DEV", "IF-VALIDATE-API"),
    ("consumes", "ACT-DEV", "IF-ENRICH-API"),
    ("consumes", "ACT-DEV", "IF-PROFILE-API"),
    ("consumes", "ACT-LLM", "IF-VALIDATE-API"),
]


def main():
    model = load_model(MODEL_PATH)

    # --- Task 1: Rename capabilities ---
    for cap in model.entities.capabilities:
        if cap.id in CAP_RENAME:
            cap.id = CAP_RENAME[cap.id]

    for rel in model.relationships:
        if rel.from_id in CAP_RENAME:
            rel.from_id = CAP_RENAME[rel.from_id]
        if rel.to_id in CAP_RENAME:
            rel.to_id = CAP_RENAME[rel.to_id]

    # --- Task 2: Add sub-capabilities ---
    existing_cap_ids = {c.id for c in model.entities.capabilities}
    existing_rels = {(r.type.value if hasattr(r.type, 'value') else r.type, r.from_id, r.to_id) for r in model.relationships}

    # Build parent source_block lookup
    parent_source_block = {c.id: c.source_block for c in model.entities.capabilities}

    for parent_id, subs in SUB_CAPS.items():
        source_block = parent_source_block.get(parent_id, "")
        for sub_id, sub_name, sub_desc in subs:
            if sub_id not in existing_cap_ids:
                model.entities.capabilities.append(Capability(
                    id=sub_id,
                    name=sub_name,
                    status=Status.ACTIVE,
                    description=sub_desc,
                    source_block=source_block,
                    priority=Priority.HIGH,
                ))
                existing_cap_ids.add(sub_id)
            # Add contains relationship
            rel_key = ("contains", parent_id, sub_id)
            if rel_key not in existing_rels:
                model.relationships.append(Relationship(
                    from_id=parent_id,
                    to_id=sub_id,
                    type=RelationType.CONTAINS,
                ))
                existing_rels.add(rel_key)

    # --- Task 3: Enrich parent behaviors ---
    beh_map = {b.id: b for b in model.entities.behaviors}
    for beh_id, uc in USE_CASES.items():
        beh = beh_map.get(beh_id)
        if beh is None:
            continue
        beh.actor = uc["actor"]
        beh.trigger = uc["trigger"]
        beh.preconditions = uc["preconditions"]
        beh.postconditions = uc["postconditions"]
        beh.steps = uc["steps"]

    # --- Task 5: Actor goals + relationships ---
    for actor in model.entities.actors:
        if actor.id in ACTOR_GOALS:
            actor.goals = ACTOR_GOALS[actor.id]

    for rel_type_str, from_id, to_id in NEW_ACTOR_RELS:
        rel_key = (rel_type_str, from_id, to_id)
        if rel_key not in existing_rels:
            model.relationships.append(Relationship(
                from_id=from_id,
                to_id=to_id,
                type=RelationType(rel_type_str),
            ))
            existing_rels.add(rel_key)

    # --- Add realizes relationships for sub-capabilities ---
    # Map sub-caps to the components that should realize them
    SUB_CAP_REALIZERS = {
        # CAP-PARSE-VALIDATE subs -> COMP-CORE sub-components
        "CAP-VALIDATE-STRUCTURAL": "COMP-CORE-VALIDATOR",
        "CAP-VALIDATE-SEMANTIC": "COMP-CORE-VALIDATOR",
        "CAP-VALIDATE-QUALITY": "COMP-CORE-VALIDATOR",
        # CAP-MANIFEST subs
        "CAP-MANIFEST-SCAN": "COMP-MANIFEST-SCANNER",
        "CAP-MANIFEST-METRICS": "COMP-MANIFEST-METRICS",
        "CAP-MANIFEST-TESTS": "COMP-MANIFEST-TEST-ANALYZER",
        # CAP-SLICE-DIFF subs
        "CAP-SLICE": "COMP-CORE-SLICER",
        "CAP-DIFF": "COMP-CORE-DIFFER",
        "CAP-MERGE": "COMP-CORE-MERGER",
        # CAP-CLI subs -> COMP-CLI
        "CAP-CLI-CORE": "COMP-CLI",
        "CAP-CLI-ANALYSIS": "COMP-CLI",
        "CAP-CLI-GENERATION": "COMP-CLI",
        # CAP-ENRICH subs -> COMP-ENRICH
        "CAP-ENRICH-SIGS": "COMP-ENRICH",
        "CAP-ENRICH-CONSTS": "COMP-ENRICH",
        "CAP-ENRICH-TESTS": "COMP-ENRICH",
    }
    for cap_id, comp_id in SUB_CAP_REALIZERS.items():
        rel_key = ("realizes", comp_id, cap_id)
        if rel_key not in existing_rels:
            model.relationships.append(Relationship(
                from_id=comp_id,
                to_id=cap_id,
                type=RelationType.REALIZES,
            ))
            existing_rels.add(rel_key)

    save_model(model, MODEL_PATH)
    print(f"Done. {len(model.entities.capabilities)} capabilities, "
          f"{len(model.relationships)} relationships, "
          f"{len(model.entities.behaviors)} behaviors.")


if __name__ == "__main__":
    main()
