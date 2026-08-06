#!/usr/bin/env python3
"""Add function-level sub-behaviors to the architecture model."""
from pathlib import Path
from architecture_model.core.parser import load_model, save_model
from architecture_model.core.types import (
    Behavior, BehaviorPattern, Relationship, RelationType, Status, Priority,
)

MODEL_PATH = Path(".architecture-model.yaml")

# New parent behaviors: (id, name, desc, primary_component_for_traces_to)
NEW_PARENTS = [
    ("BEH-SLICE", "Model Slicing", "Extract sub-models by various criteria", "COMP-CLI"),
    ("BEH-DIFF", "Model Diffing", "Compare two architecture models", "COMP-CLI"),
    ("BEH-MERGE", "Model Merging", "Merge and compose architecture models", "COMP-CORE-MERGER"),
    ("BEH-DECOMPOSE", "Model Decomposition", "Decompose model into subsystems", "COMP-CLI"),
]

# Sub-behaviors: (id, name, desc, parent_id, component_id)
SUB_BEHAVIORS = [
    # S3 Core — Validator
    ("BEH-VALIDATE-IDS", "ID Uniqueness Check", "Check all entity IDs are unique across entity types", "BEH-VALIDATE", "COMP-CORE-VALIDATOR"),
    ("BEH-VALIDATE-REFS", "Referential Integrity Check", "Verify all relationship endpoints reference existing entities", "BEH-VALIDATE", "COMP-CORE-VALIDATOR"),
    ("BEH-VALIDATE-ORPHANS", "Orphan Entity Detection", "Find entities with no relationships", "BEH-VALIDATE", "COMP-CORE-VALIDATOR"),
    ("BEH-VALIDATE-STATUS", "Status Consistency Check", "Verify status field values are valid", "BEH-VALIDATE", "COMP-CORE-VALIDATOR"),
    ("BEH-VALIDATE-CAPS", "Capability Realization Check", "Ensure every capability is realized by at least one component", "BEH-VALIDATE", "COMP-CORE-VALIDATOR"),
    ("BEH-VALIDATE-META", "Meta Completeness Check", "Validate model meta section has required fields", "BEH-VALIDATE", "COMP-CORE-VALIDATOR"),
    ("BEH-VALIDATE-V11", "V1.1 Semantics Check", "Validate schema v1.1+ semantic rules", "BEH-VALIDATE", "COMP-CORE-VALIDATOR"),
    ("BEH-VALIDATE-REGEN", "Regen Readiness Check", "Score components for code regeneration readiness", "BEH-VALIDATE", "COMP-CORE-VALIDATOR"),
    ("BEH-VALIDATE-PROFILE", "Domain Profile Validation", "Validate domain-profile-specific rules", "BEH-VALIDATE", "COMP-CORE-VALIDATOR"),
    ("BEH-VALIDATE-IMPROVE", "Improvement Opportunities", "Detect non-critical improvements", "BEH-VALIDATE", "COMP-CORE-VALIDATOR"),
    # S3 Core — Parser
    ("BEH-PARSE-LOAD", "Model Loading", "Load YAML file, parse into ArchitectureModel dataclass", "BEH-VALIDATE", "COMP-CORE-PARSER"),
    ("BEH-PARSE-SAVE", "Model Saving", "Serialize ArchitectureModel to YAML via to_dict()", "BEH-VALIDATE", "COMP-CORE-PARSER"),
    ("BEH-PARSE-DUMP", "Model Dumping", "Dump model to string format for display", "BEH-VALIDATE", "COMP-CORE-PARSER"),
    # S3 Core — Slicer
    ("BEH-SLICE-FBLOCK", "Slice by F-Block", "Extract sub-model for a functional block by tracing relationships", "BEH-SLICE", "COMP-CORE-SLICER"),
    ("BEH-SLICE-LAYER", "Slice by Layer", "Extract sub-model for an architectural layer", "BEH-SLICE", "COMP-CORE-SLICER"),
    ("BEH-SLICE-STATUS", "Slice by Status", "Filter model entities by status value", "BEH-SLICE", "COMP-CORE-SLICER"),
    ("BEH-SLICE-ARTIFACT", "Slice by Artifact", "Extract sub-model relevant to a specific artifact type", "BEH-SLICE", "COMP-CORE-SLICER"),
    ("BEH-SLICE-COMPONENT", "Slice by Component", "Extract sub-model for a single component with dependencies", "BEH-SLICE", "COMP-CORE-SLICER"),
    # S3 Core — Differ
    ("BEH-DIFF-ENTITIES", "Entity Diff", "Compare entities between two models, detect added/removed/modified", "BEH-DIFF", "COMP-CORE-DIFFER"),
    ("BEH-DIFF-RELS", "Relationship Diff", "Compare relationships between two models", "BEH-DIFF", "COMP-CORE-DIFFER"),
    # S3 Core — Merger
    ("BEH-MERGE-MANIFEST", "Merge Manifest", "Merge reality manifest data into architecture model", "BEH-MERGE", "COMP-CORE-MERGER"),
    ("BEH-MERGE-ENRICH", "Enrich from Manifest", "Enrich model components with manifest-derived data", "BEH-MERGE", "COMP-CORE-MERGER"),
    ("BEH-MERGE-COMPACT", "Compact for Generation", "Compact model for code generation context", "BEH-MERGE", "COMP-CORE-MERGER"),
    ("BEH-MERGE-COMPOSE", "Compose Enriched Model", "Compose a fully enriched model from multiple sources", "BEH-MERGE", "COMP-CORE-MERGER"),
    # S3 Core — Decomposer
    ("BEH-DECOMPOSE-IDENTIFY", "Identify Systems", "Discover functional subsystems from component graph", "BEH-DECOMPOSE", "COMP-CORE-DECOMPOSER"),
    ("BEH-DECOMPOSE-COMPLEXITY", "Compute Complexity", "Calculate complexity metrics for subsystem partitioning", "BEH-DECOMPOSE", "COMP-CORE-DECOMPOSER"),
    ("BEH-DECOMPOSE-PARTITION", "Partition Subsystems", "Partition components into subsystems by affinity", "BEH-DECOMPOSE", "COMP-CORE-DECOMPOSER"),
    # S5 Manifest — Scanner
    ("BEH-SCAN-PARSE", "AST Parsing", "Parse Python source file into AST", "BEH-MANIFEST", "COMP-MANIFEST-SCANNER"),
    ("BEH-SCAN-FUNCTIONS", "Function Extraction", "Extract function definitions with signatures, decorators, docstrings", "BEH-MANIFEST", "COMP-MANIFEST-SCANNER"),
    ("BEH-SCAN-CLASSES", "Class Extraction", "Extract class definitions with methods and attributes", "BEH-MANIFEST", "COMP-MANIFEST-SCANNER"),
    ("BEH-SCAN-IMPORTS", "Import Extraction", "Extract import statements with aliases and relative resolution", "BEH-MANIFEST", "COMP-MANIFEST-SCANNER"),
    ("BEH-SCAN-CONSTANTS", "Constant Extraction", "Extract module-level constants and assignments", "BEH-MANIFEST", "COMP-MANIFEST-SCANNER"),
    ("BEH-SCAN-METRICS", "Metrics Computation", "Compute line count, status, exports for scanned file", "BEH-MANIFEST", "COMP-MANIFEST-SCANNER"),
    # S5 Manifest — Generator
    ("BEH-MANIFEST-CONFIG", "Config Loading", "Load or discover project configuration for manifest generation", "BEH-MANIFEST", "COMP-MANIFEST-GENERATOR"),
    ("BEH-MANIFEST-METRICS", "Project Metrics", "Compute project-wide metrics (total lines, file counts)", "BEH-MANIFEST", "COMP-MANIFEST-GENERATOR"),
    ("BEH-MANIFEST-BLOCKS", "Block Assembly", "Assemble functional blocks from config with file enumeration", "BEH-MANIFEST", "COMP-MANIFEST-GENERATOR"),
    ("BEH-MANIFEST-SCAN", "Block Scanning", "Scan all files within each block for AST data", "BEH-MANIFEST", "COMP-MANIFEST-GENERATOR"),
    ("BEH-MANIFEST-IFACE", "Interface Discovery", "Discover inter-block interfaces from import analysis", "BEH-MANIFEST", "COMP-MANIFEST-GENERATOR"),
    ("BEH-MANIFEST-ASSEMBLE", "Manifest Assembly", "Assemble final manifest from blocks, interfaces, metrics", "BEH-MANIFEST", "COMP-MANIFEST-GENERATOR"),
    # S5 Manifest — Body Hints
    ("BEH-BODYHINT-CLASSIFY", "Complexity Classification", "Classify function complexity as TRIVIAL/SHORT/COMPLEX", "BEH-MANIFEST", "COMP-MANIFEST-BODY-HINTS"),
    ("BEH-BODYHINT-SUMMARIZE", "Body Summarization", "Generate body_hint text summarizing function implementation", "BEH-MANIFEST", "COMP-MANIFEST-BODY-HINTS"),
    # S5 Manifest — Test Analyzer
    ("BEH-TEST-DISCOVER", "Test Method Discovery", "Find test methods/functions in test files", "BEH-MANIFEST", "COMP-MANIFEST-TEST-ANALYZER"),
    ("BEH-TEST-ASSERTIONS", "Assertion Pattern Matching", "Extract assertion patterns from test methods (unittest + pytest)", "BEH-MANIFEST", "COMP-MANIFEST-TEST-ANALYZER"),
    # S5 Manifest — Interfaces
    ("BEH-IFACE-RESOLVE", "Import Resolution", "Resolve relative and absolute imports to interface edges", "BEH-MANIFEST", "COMP-MANIFEST-INTERFACES"),
    ("BEH-IFACE-DEDUP", "Interface Deduplication", "Deduplicate interface edges from multiple import sources", "BEH-MANIFEST", "COMP-MANIFEST-INTERFACES"),
    # S5 Manifest — Recursive
    ("BEH-RECURSIVE-SCAN", "Per-Block Deep Scan", "Perform deep AST scan within a single F-block", "BEH-MANIFEST", "COMP-MANIFEST-GENERATOR"),
    ("BEH-RECURSIVE-DEPS", "Cross-Block Dependencies", "Compute dependency graph between F-blocks", "BEH-MANIFEST", "COMP-MANIFEST-GENERATOR"),
    # S6 Orchestration — Enrich
    ("BEH-ENRICH-SIGS", "Signature Enrichment", "Extract function signatures from AST and add to components", "BEH-ENRICH", "COMP-ENRICH"),
    ("BEH-ENRICH-CONSTS", "Constant Enrichment", "Extract module-level constants and add to components", "BEH-ENRICH", "COMP-ENRICH"),
    ("BEH-ENRICH-TESTS", "Test Contract Enrichment", "Discover test files via 7 naming conventions and extract contracts", "BEH-ENRICH", "COMP-ENRICH"),
    # S6 Orchestration — Decompose
    ("BEH-ORCH-FIND-COMPS", "Find Block Components", "Find all components belonging to an F-block", "BEH-DECOMPOSE", "COMP-DECOMPOSE"),
    ("BEH-ORCH-FIND-PARENT", "Find Parent Component", "Locate parent component for a block's component hierarchy", "BEH-DECOMPOSE", "COMP-DECOMPOSE"),
    ("BEH-ORCH-TRACE", "Trace Entities", "Trace relationships to find connected capabilities, interfaces, behaviors, constraints", "BEH-DECOMPOSE", "COMP-DECOMPOSE"),
    ("BEH-ORCH-COLLECT-RELS", "Collect Relationships", "Collect internal and boundary relationships for sub-model", "BEH-DECOMPOSE", "COMP-DECOMPOSE"),
    ("BEH-ORCH-BUILD", "Build Sub-Model", "Assemble final sub-model YAML from traced entities", "BEH-DECOMPOSE", "COMP-DECOMPOSE"),
    # S4 Extract
    ("BEH-EXTRACT-CAPS", "Extract Capabilities", "Derive capabilities from source code analysis", "BEH-EXTRACT", "COMP-EXTRACT"),
    ("BEH-EXTRACT-ACTORS", "Extract Actors", "Identify external actors from code patterns", "BEH-EXTRACT", "COMP-EXTRACT"),
    ("BEH-EXTRACT-COMPS", "Extract Components", "Map source modules to architecture components", "BEH-EXTRACT", "COMP-EXTRACT"),
    ("BEH-EXTRACT-IFACES", "Extract Interfaces", "Derive interfaces from import/export analysis", "BEH-EXTRACT", "COMP-EXTRACT"),
    ("BEH-EXTRACT-RELS", "Extract Relationships", "Infer relationships between extracted entities", "BEH-EXTRACT", "COMP-EXTRACT"),
    # S1 CLI
    ("BEH-CLI-SLICE", "CLI Slice Command", "Execute model slicing from command line", "BEH-INIT", "COMP-CLI"),
    ("BEH-CLI-DIFF", "CLI Diff Command", "Execute model diff from command line", "BEH-INIT", "COMP-CLI"),
    ("BEH-CLI-STATS", "CLI Stats Command", "Display model statistics from command line", "BEH-INIT", "COMP-CLI"),
    ("BEH-CLI-IMPACT", "CLI Impact Command", "Trace change impact from command line", "BEH-INIT", "COMP-CLI"),
    ("BEH-CLI-DECOMPOSE", "CLI Decompose Command", "Generate per-F-block sub-models from command line", "BEH-INIT", "COMP-CLI"),
    ("BEH-CLI-COVERAGE", "CLI Coverage Command", "Display regen coverage metrics from command line", "BEH-INIT", "COMP-CLI"),
    # S7 Profiles
    ("BEH-PROFILE-LOAD", "Load Profile", "Resolve profile path, load YAML, parse into dataclass", "BEH-VALIDATE", "COMP-PROFILES"),
    ("BEH-PROFILE-APPLY", "Apply Profile Rules", "Apply domain-specific validation rules from profile", "BEH-VALIDATE", "COMP-PROFILES"),
    # S9 Utils
    ("BEH-UTILS-DISCOVER", "File Discovery", "Discover Python source files with exclusion patterns", "BEH-MANIFEST", "COMP-UTILS"),
    ("BEH-UTILS-TESTS", "Test File Discovery", "Discover test files matching source modules", "BEH-MANIFEST", "COMP-UTILS"),
]


def main():
    model = load_model(MODEL_PATH)
    existing_ids = {b.id for b in model.entities.behaviors}
    comp_ids = {c.id for c in model.entities.components}
    beh_ids = {b.id for b in model.entities.behaviors}

    # Verify all component IDs
    for (_, _, _, comp_id) in NEW_PARENTS:
        assert comp_id in comp_ids, f"Component {comp_id} not found"
    for (_, _, _, _, comp_id) in SUB_BEHAVIORS:
        assert comp_id in comp_ids, f"Component {comp_id} not found"

    existing_rels = {
        (r.type if isinstance(r.type, str) else r.type.value, r.from_id, r.to_id)
        for r in model.relationships
    }
    added_behs = 0
    added_rels = 0

    # Add parents
    for (bid, name, desc, comp_id) in NEW_PARENTS:
        if bid not in existing_ids:
            model.entities.behaviors.append(Behavior(
                id=bid, name=name, status=Status.ACTIVE, description=desc,
                pattern=BehaviorPattern.SEQUENTIAL, priority=Priority.MEDIUM,
            ))
            existing_ids.add(bid)
            added_behs += 1
        # traces-to
        key = (RelationType.TRACES_TO.value, comp_id, bid)
        if key not in existing_rels:
            model.relationships.append(Relationship(type=RelationType.TRACES_TO, from_id=comp_id, to_id=bid))
            existing_rels.add(key)
            added_rels += 1

    # Add sub-behaviors
    for (bid, name, desc, parent_id, comp_id) in SUB_BEHAVIORS:
        if bid not in existing_ids:
            model.entities.behaviors.append(Behavior(
                id=bid, name=name, status=Status.ACTIVE, description=desc,
                pattern=BehaviorPattern.SEQUENTIAL, priority=Priority.MEDIUM,
            ))
            existing_ids.add(bid)
            added_behs += 1
        # contains: parent -> sub
        key = (RelationType.CONTAINS.value, parent_id, bid)
        if key not in existing_rels:
            model.relationships.append(Relationship(type=RelationType.CONTAINS, from_id=parent_id, to_id=bid))
            existing_rels.add(key)
            added_rels += 1
        # traces-to: component -> sub
        key = (RelationType.TRACES_TO.value, comp_id, bid)
        if key not in existing_rels:
            model.relationships.append(Relationship(type=RelationType.TRACES_TO, from_id=comp_id, to_id=bid))
            existing_rels.add(key)
            added_rels += 1

    save_model(model, MODEL_PATH)
    print(f"Added {added_behs} behaviors, {added_rels} relationships")
    print(f"Total behaviors: {len(model.entities.behaviors)}")
    print(f"Total relationships: {len(model.relationships)}")


if __name__ == "__main__":
    main()
