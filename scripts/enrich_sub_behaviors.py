#!/usr/bin/env python3
"""Enrich sub-behavior entities with AST-derived implementation detail."""

import ast
from pathlib import Path

from architecture_model.core.parser import load_model, save_model

MODEL_PATH = Path(".architecture-model.yaml")

# Behavior ID -> (source_file, function_name)
# Verified against actual source files.
BEHAVIOR_MAP = {
    # F3 Core - Validator
    "BEH-VALIDATE-IDS": ("src/architecture_model/core/validator.py", "_check_id_uniqueness"),
    "BEH-VALIDATE-REFS": ("src/architecture_model/core/validator.py", "_check_referential_integrity"),
    "BEH-VALIDATE-ORPHANS": ("src/architecture_model/core/validator.py", "_check_orphan_entities"),
    "BEH-VALIDATE-STATUS": ("src/architecture_model/core/validator.py", "_check_status_consistency"),
    "BEH-VALIDATE-CAPS": ("src/architecture_model/core/validator.py", "_check_capability_realization"),
    "BEH-VALIDATE-META": ("src/architecture_model/core/validator.py", "_check_meta_completeness"),
    "BEH-VALIDATE-V11": ("src/architecture_model/core/validator.py", "_check_v11_semantics"),
    "BEH-VALIDATE-REGEN": ("src/architecture_model/core/validator.py", "_check_regen_readiness"),
    "BEH-VALIDATE-PROFILE": ("src/architecture_model/core/validator.py", "_check_domain_profile"),
    "BEH-VALIDATE-IMPROVE": ("src/architecture_model/core/validator.py", "_check_improvement_opportunities"),

    # F3 Core - Parser
    "BEH-PARSE-LOAD": ("src/architecture_model/core/parser.py", "load_model"),
    "BEH-PARSE-SAVE": ("src/architecture_model/core/parser.py", "save_model"),
    "BEH-PARSE-DUMP": ("src/architecture_model/core/parser.py", "dump_model"),

    # F3 Core - Slicer
    "BEH-SLICE-FBLOCK": ("src/architecture_model/core/slicer.py", "slice_by_fblock"),
    "BEH-SLICE-LAYER": ("src/architecture_model/core/slicer.py", "slice_by_layer"),
    "BEH-SLICE-STATUS": ("src/architecture_model/core/slicer.py", "slice_by_status"),
    "BEH-SLICE-ARTIFACT": ("src/architecture_model/core/slicer.py", "slice_for_artifact"),
    "BEH-SLICE-COMPONENT": ("src/architecture_model/core/slicer.py", "slice_by_fblock"),  # no slice_by_component

    # F3 Core - Differ
    "BEH-DIFF-ENTITIES": ("src/architecture_model/core/differ.py", "_diff_entity_list"),
    "BEH-DIFF-RELS": ("src/architecture_model/core/differ.py", "_diff_relationships"),

    # F3 Core - Merger
    "BEH-MERGE-MANIFEST": ("src/architecture_model/core/merger.py", "merge_manifest"),
    "BEH-MERGE-ENRICH": ("src/architecture_model/core/merger.py", "enrich_from_manifest"),
    "BEH-MERGE-COMPACT": ("src/architecture_model/core/merger.py", "compact_for_generation"),
    "BEH-MERGE-COMPOSE": ("src/architecture_model/core/merger.py", "compose_enriched_model"),

    # F3 Core - Decomposer
    "BEH-DECOMPOSE-IDENTIFY": ("src/architecture_model/core/decomposer.py", "identify_systems"),
    "BEH-DECOMPOSE-COMPLEXITY": ("src/architecture_model/core/decomposer.py", "compute_complexity"),
    "BEH-DECOMPOSE-PARTITION": ("src/architecture_model/core/decomposer.py", "test_affinity_decompose"),

    # F5 Manifest - Scanner
    "BEH-SCAN-PARSE": ("src/architecture_model/manifest/scanner.py", "scan_file"),
    "BEH-SCAN-FUNCTIONS": ("src/architecture_model/manifest/scanner.py", "_extract_public_functions"),
    "BEH-SCAN-CLASSES": ("src/architecture_model/manifest/scanner.py", "_extract_classes"),
    "BEH-SCAN-IMPORTS": ("src/architecture_model/manifest/scanner.py", "_extract_imports"),
    "BEH-SCAN-CONSTANTS": ("src/architecture_model/manifest/scanner.py", "_extract_module_constants"),
    "BEH-SCAN-METRICS": ("src/architecture_model/manifest/scanner.py", "_file_line_count"),

    # F5 Manifest - Generator
    "BEH-MANIFEST-CONFIG": ("src/architecture_model/manifest/generator.py", "load_or_generate_manifest"),
    "BEH-MANIFEST-ASSEMBLE": ("src/architecture_model/manifest/generator.py", "generate_manifest"),

    # F5 Manifest - Body Hints
    "BEH-BODYHINT-CLASSIFY": ("src/architecture_model/manifest/body_hints.py", "classify_function"),
    "BEH-BODYHINT-SUMMARIZE": ("src/architecture_model/manifest/body_hints.py", "extract_body_hint"),

    # F5 Manifest - Test Analyzer
    "BEH-TEST-DISCOVER": ("src/architecture_model/manifest/test_analyzer.py", "_find_test_methods"),
    "BEH-TEST-ASSERTIONS": ("src/architecture_model/manifest/test_analyzer.py", "_extract_contracts_from_method"),

    # F5 Manifest - Interfaces
    "BEH-IFACE-RESOLVE": ("src/architecture_model/manifest/interfaces.py", "derive_interfaces"),
    "BEH-IFACE-DEDUP": ("src/architecture_model/manifest/interfaces.py", "_derive_interfaces"),

    # F5 Manifest - Recursive
    "BEH-RECURSIVE-SCAN": ("src/architecture_model/manifest/recursive.py", "generate_recursive_manifests"),
    "BEH-RECURSIVE-DEPS": ("src/architecture_model/manifest/recursive.py", "compute_block_dependencies"),

    # F6 Orchestration - Enrich
    "BEH-ENRICH-SIGS": ("src/architecture_model/orchestration/enrich.py", "_enrich_signatures"),
    "BEH-ENRICH-CONSTS": ("src/architecture_model/orchestration/enrich.py", "_enrich_constants"),
    "BEH-ENRICH-TESTS": ("src/architecture_model/orchestration/enrich.py", "_enrich_test_contracts"),

    # F6 Orchestration - Decompose
    "BEH-ORCH-FIND-COMPS": ("src/architecture_model/orchestration/decompose.py", "_find_block_components"),
    "BEH-ORCH-FIND-PARENT": ("src/architecture_model/orchestration/decompose.py", "_find_parent_component"),
    "BEH-ORCH-TRACE": ("src/architecture_model/orchestration/decompose.py", "_trace_entities"),
    "BEH-ORCH-COLLECT-RELS": ("src/architecture_model/orchestration/decompose.py", "_collect_relationships"),
    "BEH-ORCH-BUILD": ("src/architecture_model/orchestration/decompose.py", "decompose_model"),

    # F4 Extract (actual file: from_code.py)
    "BEH-EXTRACT-CAPS": ("src/architecture_model/extract/from_code.py", "_derive_capabilities"),
    "BEH-EXTRACT-ACTORS": ("src/architecture_model/extract/from_code.py", "_derive_actors"),
    "BEH-EXTRACT-COMPS": ("src/architecture_model/extract/from_code.py", "_derive_components"),
    "BEH-EXTRACT-IFACES": ("src/architecture_model/extract/from_code.py", "_derive_interfaces"),
    "BEH-EXTRACT-RELS": ("src/architecture_model/extract/from_code.py", "_derive_relationships"),

    # F1 CLI
    "BEH-CLI-SLICE": ("src/architecture_model/cli/main.py", "_cmd_slice"),
    "BEH-CLI-DIFF": ("src/architecture_model/cli/main.py", "_cmd_diff"),
    "BEH-CLI-STATS": ("src/architecture_model/cli/main.py", "_cmd_stats"),
    "BEH-CLI-IMPACT": ("src/architecture_model/cli/main.py", "_cmd_impact"),
    "BEH-CLI-DECOMPOSE": ("src/architecture_model/cli/main.py", "_cmd_decompose"),
    "BEH-CLI-COVERAGE": ("src/architecture_model/cli/main.py", "_cmd_coverage"),

    # F7 Profiles (actual file: schema.py)
    "BEH-PROFILE-LOAD": ("src/architecture_model/profiles/schema.py", "load_profile"),

    # F9 Utils (actual file: discovery.py)
    "BEH-UTILS-DISCOVER": ("src/architecture_model/utils/discovery.py", "collect_py_files"),
    "BEH-UTILS-TESTS": ("src/architecture_model/utils/discovery.py", "discover_test_files"),
}


def summarize_statement(stmt) -> str | None:
    """Summarize a top-level statement into a step description."""
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        return f"Call {ast.unparse(stmt.value.func)}()"
    if isinstance(stmt, ast.Assign):
        targets = ast.unparse(stmt.targets[0]) if stmt.targets else "?"
        if isinstance(stmt.value, ast.Call):
            return f"{targets} = {ast.unparse(stmt.value.func)}()"
        return f"Compute {targets}"
    if isinstance(stmt, ast.AugAssign):
        return f"Update {ast.unparse(stmt.target)}"
    if isinstance(stmt, ast.For):
        return f"Iterate over {ast.unparse(stmt.iter)}"
    if isinstance(stmt, ast.If):
        test = ast.unparse(stmt.test)
        return f"Check {test[:60]}"
    if isinstance(stmt, ast.Return):
        if stmt.value:
            val = ast.unparse(stmt.value)
            return f"Return {val[:60]}"
        return "Return"
    if isinstance(stmt, ast.With):
        return f"With {ast.unparse(stmt.items[0].context_expr)}"
    if isinstance(stmt, ast.Assert):
        return f"Assert {ast.unparse(stmt.test)[:60]}"
    return None


def find_caller(tree, function_name: str) -> str:
    """Find which function in the same file calls function_name."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == function_name:
                continue
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name) and child.func.id == function_name:
                        return node.name
                    if isinstance(child.func, ast.Attribute) and child.func.attr == function_name:
                        return node.name
    return ""


def find_function(tree, function_name: str):
    """Find a function/method node by name in the AST."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == function_name:
                return node
    return None


def extract_behavior_detail(source_file: str, function_name: str) -> dict:
    """Extract steps, preconditions, postconditions from function AST."""
    tree = ast.parse(Path(source_file).read_text())

    func = find_function(tree, function_name)
    if func is None:
        return {}

    result = {}

    # STEPS: top-level statements, max 10
    steps = []
    for stmt in func.body:
        # Skip docstrings
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            continue
        step = summarize_statement(stmt)
        if step:
            steps.append(step)
    result["steps"] = steps[:10]

    # PRECONDITIONS: type annotations + early guards
    preconditions = []
    for arg in func.args.args:
        if arg.annotation:
            preconditions.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
    for stmt in func.body[:3]:
        if isinstance(stmt, ast.If):
            if any(isinstance(s, (ast.Return, ast.Raise)) for s in stmt.body):
                preconditions.append(f"Guard: {ast.unparse(stmt.test)[:70]}")
    result["preconditions"] = preconditions

    # POSTCONDITIONS: return type + return statements
    postconditions = []
    if func.returns:
        postconditions.append(f"Returns: {ast.unparse(func.returns)}")
    for node in ast.walk(func):
        if isinstance(node, ast.Return) and node.value:
            val = ast.unparse(node.value)
            if len(val) < 80:
                entry = f"return {val}"
                if entry not in postconditions:
                    postconditions.append(entry)
    result["postconditions"] = postconditions[:5]

    # TRIGGER
    trigger = find_caller(tree, function_name)
    if trigger:
        result["trigger"] = trigger

    return result


def main():
    model = load_model(MODEL_PATH)
    beh_map = {b.id: b for b in model.entities.behaviors}

    enriched = 0
    skipped = 0

    for beh_id, (source_file, func_name) in BEHAVIOR_MAP.items():
        if beh_id not in beh_map:
            print(f"WARNING: {beh_id} not in model, skipping")
            skipped += 1
            continue

        source_path = Path(source_file)
        if not source_path.exists():
            print(f"WARNING: {source_file} not found, skipping {beh_id}")
            skipped += 1
            continue

        detail = extract_behavior_detail(source_file, func_name)
        if not detail:
            print(f"WARNING: {func_name} not found in {source_file}, skipping {beh_id}")
            skipped += 1
            continue

        beh = beh_map[beh_id]
        if detail.get("steps"):
            beh.steps = detail["steps"]
        if detail.get("preconditions"):
            beh.preconditions = detail["preconditions"]
        if detail.get("postconditions"):
            beh.postconditions = detail["postconditions"]
        if detail.get("trigger"):
            beh.trigger = detail["trigger"]

        enriched += 1
        print(
            f"  {beh_id}: {len(detail.get('steps', []))} steps, "
            f"{len(detail.get('preconditions', []))} pre, "
            f"{len(detail.get('postconditions', []))} post"
        )

    save_model(model, MODEL_PATH)
    print(f"\nEnriched {enriched} behaviors, skipped {skipped}")


if __name__ == "__main__":
    main()
