#!/usr/bin/env python3
"""Test-Guided Round-Trip: real execution script for proof-of-concept runs.

Runs the full test-guided generation pipeline against repos in /tmp/test-repos/.
Requires Ollama running locally with the specified model.

Usage:
    python scripts/test_guided_round_trip.py --repo python-dotenv --max-retries 10
    python scripts/test_guided_round_trip.py --repo click --max-retries 15
    python scripts/test_guided_round_trip.py --repo click --model qwen2.5:7b --output-dir results/test-guided/
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from architecture_model.core.merger import compact_for_generation, enrich_from_manifest
from architecture_model.core.parser import dump_model
from architecture_model.core.types import (
    ArchitectureModel,
    Component,
    ComponentKind,
    Entities,
    ModelMeta,
    Relationship,
    RelationType,
    Status,
    Symbol,
    SymbolKind,
)
from architecture_model.manifest.scanner import _scan_file
from architecture_model.training.code_writer import CodeWriter
from architecture_model.training.failure_parser import FailureParser
from architecture_model.training.prompt_builder import PromptBuilder
from architecture_model.training.surrogate import Surrogate
from architecture_model.training.test_contract_miner import TestContractMiner
from architecture_model.training.test_guided_generator import TestGuidedGenerator
from architecture_model.training.test_runner import TestRunner

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CLONE_DIR = Path("/tmp/test-repos")

REPO_SUBDIRS = {
    "click": "src/click",
    "typer": "typer",
    "httpcore": "httpcore",
    "anyio": "src/anyio",
    "python-dotenv": "src/dotenv",
    "colorama": "colorama",
    "tqdm": "tqdm",
    "attrs": "src",
    "structlog": "src/structlog",
    "pydantic": "pydantic",
    "fastapi": "fastapi",
    "rich": "rich",
    "httpx": "httpx",
    "black": "src/black",
    "marshmallow": "src/marshmallow",
    "flask": "src/flask",
    "jinja": "src/jinja2",
    "starlette": "starlette",
    "arrow": "arrow",
}


# ---------------------------------------------------------------------------
# Manifest and model builders
# ---------------------------------------------------------------------------


def build_manifest_for_repo(repo_root: Path) -> dict:
    """Build a manifest by AST-scanning source files."""
    modules = []
    py_files = sorted(repo_root.rglob("*.py"))

    # Exclude common non-source directories
    exclude = {".venv", "venv", "__pycache__", ".git", "node_modules", ".tox", ".eggs"}
    py_files = [
        f for f in py_files
        if not any(part in exclude for part in f.parts)
    ]

    # Limit to prevent excessive scanning
    py_files = py_files[:150]

    for f in py_files:
        try:
            meta = _scan_file(repo_root, f)
            modules.append(meta)
        except Exception:
            continue

    return {"modules": modules, "interfaces": []}


def build_model_from_manifest(manifest: dict, project_name: str) -> ArchitectureModel:
    """Build an ArchitectureModel from manifest data.

    Maps each source module to a Component with symbols derived from classes/functions.
    Excludes test files and conftest to produce a clean generation model.
    """
    components: list[Component] = []
    seen_modules: set[str] = set()

    for mod_info in manifest.get("modules", []):
        file_path = mod_info.get("file", "")
        if not file_path or file_path in seen_modules:
            continue
        seen_modules.add(file_path)

        # Derive component name from file path
        stem = Path(file_path).stem
        if stem == "__init__" or stem == "__main__":
            continue

        # Skip test files and conftest
        if stem.startswith("test_") or stem == "conftest":
            continue
        if "/tests/" in file_path or "/test/" in file_path:
            continue

        comp_id = stem  # Use plain name as ID (LLMs confuse id/name otherwise)

        # Build symbols from classes
        symbols: list[Symbol] = []
        for cls_info in mod_info.get("classes", []):
            cls_name = cls_info if isinstance(cls_info, str) else cls_info.get("name", "")
            members = []
            if isinstance(cls_info, dict):
                members = cls_info.get("methods", [])
            if cls_name:
                symbols.append(Symbol(
                    name=cls_name,
                    kind=SymbolKind.CLASS,
                    members=members,
                ))

        # Build functions list
        functions: list[str] = []
        for func in mod_info.get("functions", []):
            func_name = func if isinstance(func, str) else func.get("name", "")
            if func_name and not func_name.startswith("_"):
                functions.append(func_name)

        components.append(Component(
            id=comp_id,
            name=stem,
            status=Status.ACTIVE,
            kind=ComponentKind.LIBRARY,
            files=[file_path],
            symbols=symbols,
            functions=functions,
        ))

    # Limit components to prevent overly large models
    components = components[:50]

    # Build simple dependency relationships from imports
    relationships: list[Relationship] = []
    comp_names = {c.name for c in components}
    comp_id_map = {c.name: c.id for c in components}

    for mod_info in manifest.get("modules", []):
        file_path = mod_info.get("file", "")
        stem = Path(file_path).stem
        if stem not in comp_id_map:
            continue
        for imp in mod_info.get("imports", []):
            imp_module = imp if isinstance(imp, str) else imp.get("module", "")
            if not imp_module:
                continue
            # Check if import references a known component
            imp_parts = imp_module.split(".")
            for part in imp_parts:
                if part in comp_names and part != stem:
                    relationships.append(Relationship(
                        type=RelationType.DEPENDS_ON,
                        from_id=comp_id_map[stem],
                        to_id=comp_id_map[part],
                    ))
                    break

    return ArchitectureModel(
        meta=ModelMeta(
            schema_version="1.2",
            project=project_name,
            source_language="python",
        ),
        entities=Entities(components=components),
        relationships=relationships,
    )


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------


async def run_test_guided(args: argparse.Namespace) -> dict:
    """Run the test-guided generation pipeline on a repo."""
    repo_name = args.repo
    repo_root = CLONE_DIR / repo_name

    if not repo_root.exists():
        print(f"ERROR: Repo not found at {repo_root}")
        print(f"  Clone it first: git clone <url> {repo_root}")
        return {"error": f"Repo not found: {repo_root}"}

    # Detect source directory
    subdir = REPO_SUBDIRS.get(repo_name, repo_name)
    src_dir = repo_root / subdir
    if not src_dir.exists():
        src_dir = repo_root

    # Detect package name
    package_name = _detect_package_name(repo_root, repo_name)

    print(f"\n{'='*70}")
    print(f"  TEST-GUIDED GENERATION: {repo_name}")
    print(f"{'='*70}")
    print(f"  Repo:      {repo_root}")
    print(f"  Package:   {package_name}")
    print(f"  Model:     {args.model}")
    print(f"  Retries:   {args.max_retries}")
    print()

    # 1. Build manifest
    print("[1] Building manifest (AST scan)...", end=" ", flush=True)
    t0 = time.time()
    try:
        manifest = build_manifest_for_repo(repo_root)
        n_mods = len(manifest["modules"])
        print(f"OK ({n_mods} modules, {time.time()-t0:.1f}s)")
    except Exception as e:
        print(f"FAILED: {e}")
        return {"error": f"Manifest generation failed: {e}"}

    # 2. Build model from manifest
    print("[2] Building architecture model from manifest...", end=" ", flush=True)
    try:
        model = build_model_from_manifest(manifest, repo_name)
        n_comp = len(model.entities.components)
        n_rel = len(model.relationships)
        print(f"OK ({n_comp} components, {n_rel} relationships)")
    except Exception as e:
        print(f"FAILED: {e}")
        return {"error": f"Model build failed: {e}"}

    # 3. Mine contracts from tests
    print("[3] Mining behavioral contracts from tests...", end=" ", flush=True)
    try:
        contract_miner = TestContractMiner()
        contracts = contract_miner.mine(repo_root, package_name)
        print(
            f"OK ({contracts.total_tests} tests, {contracts.total_assertions} assertions, "
            f"{len(contracts.contracts)} contracts)"
        )
    except Exception as e:
        print(f"FAILED: {e}")
        return {"error": f"Contract mining failed: {e}"}

    # 4. Initialize components
    print("[4] Initializing generation pipeline...", end=" ", flush=True)
    try:
        surrogate = Surrogate(model_name=args.model)
        test_runner = TestRunner()
        prompt_builder = PromptBuilder()
        code_writer = CodeWriter()
        failure_parser = FailureParser()

        generator = TestGuidedGenerator(
            surrogate=surrogate,
            test_runner=test_runner,
            contract_miner=contract_miner,
            prompt_builder=prompt_builder,
            code_writer=code_writer,
            failure_parser=failure_parser,
            max_retries=args.max_retries,
            convergence_threshold=3,
        )
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        return {"error": f"Pipeline initialization failed: {e}"}

    # 5. Run generation
    print(f"\n[5] Starting test-guided generation (max {args.max_retries} retries)...")
    print("    This requires Ollama running with the specified model.\n")
    t0 = time.time()
    try:
        result = await generator.generate(
            model=model,
            manifest=manifest,
            repo_path=repo_root,
            package_name=package_name,
        )
        total_time = time.time() - t0
    except Exception as e:
        total_time = time.time() - t0
        print(f"\n    FAILED after {total_time:.1f}s: {e}")
        if "Cannot connect" in str(e) or "Connection refused" in str(e):
            print("\n    Is Ollama running? Start it with: ollama serve")
            print(f"    Then pull the model: ollama pull {args.model}")
        return {"error": str(e), "time_seconds": total_time}

    # 6. Print results
    print(f"\n{'='*70}")
    print("  RESULTS")
    print(f"{'='*70}")
    print(f"  Pass rate:      {result.final_pass_rate:.1%}")
    print(f"  Iterations:     {result.iterations}")
    print(f"  Converged:      {result.converged}")
    print(f"  Total time:     {total_time:.1f}s")
    if result.structural_score is not None:
        print(f"  Structural:     {result.structural_score:.2f}")
    print()

    # Iteration details
    if result.attempts:
        print(f"  {'Iter':>4} {'Pass Rate':>10} {'Time(s)':>8} {'Regenerated':>20}")
        print(f"  {'─'*50}")
        for attempt in result.attempts:
            regen = ", ".join(attempt.components_regenerated) if attempt.components_regenerated else "-"
            print(
                f"  {attempt.iteration:>4} "
                f"{attempt.pass_rate:>10.1%} "
                f"{attempt.time_seconds:>8.1f} "
                f"{regen:>20}"
            )
    print()

    # 7. Save results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    result_data = {
        "test": "test_guided_round_trip",
        "timestamp": ts,
        "repo": repo_name,
        "package": package_name,
        "model": args.model,
        "max_retries": args.max_retries,
        "results": {
            "pass_rate": result.final_pass_rate,
            "iterations": result.iterations,
            "converged": result.converged,
            "total_time_seconds": total_time,
            "structural_score": result.structural_score,
        },
        "attempts": [
            {
                "iteration": a.iteration,
                "pass_rate": a.pass_rate,
                "time_seconds": a.time_seconds,
                "components_regenerated": a.components_regenerated,
                "n_failures": len(a.failures.failures) if a.failures else 0,
            }
            for a in result.attempts
        ],
        "contracts": {
            "total_tests": contracts.total_tests,
            "total_assertions": contracts.total_assertions,
            "n_contracts": len(contracts.contracts),
            "public_api": contracts.public_api[:20],
        },
        "model_info": {
            "n_components": n_comp,
            "n_relationships": n_rel,
            "n_manifest_modules": n_mods,
        },
    }

    result_path = output_dir / f"test_guided_{repo_name}_{ts}.json"
    result_path.write_text(json.dumps(result_data, indent=2, default=str))
    print(f"  Results saved: {result_path}")

    # Save generated code
    code_path = output_dir / f"test_guided_{repo_name}_{ts}_code.py"
    code_path.write_text(result.final_code)
    print(f"  Code saved:    {code_path}")

    return result_data


def _detect_package_name(repo_root: Path, fallback: str) -> str:
    """Detect the importable package name.
    
    Priority: REPO_SUBDIRS (known mappings) > source directory detection > pyproject.toml.
    The pyproject.toml 'name' is the DISTRIBUTION name (e.g., "python-dotenv")
    which differs from the importable name (e.g., "dotenv").
    """
    # 1. Use known source subdirectory (most reliable — gives importable name)
    subdir = REPO_SUBDIRS.get(fallback)
    if subdir:
        parts = subdir.split("/")
        return parts[-1].replace("-", "_")

    # 2. Look for a src/X/ directory
    src_dir = repo_root / "src"
    if src_dir.exists():
        for child in sorted(src_dir.iterdir()):
            if child.is_dir() and (child / "__init__.py").exists():
                return child.name.replace("-", "_")

    # 3. Look for a top-level package directory matching repo name
    candidate = repo_root / fallback.replace("-", "_")
    if candidate.is_dir() and (candidate / "__init__.py").exists():
        return fallback.replace("-", "_")

    return fallback.replace("-", "_")


def main():
    parser = argparse.ArgumentParser(
        description="Test-Guided Generation Round-Trip Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
    python scripts/test_guided_round_trip.py --repo python-dotenv --max-retries 10
    python scripts/test_guided_round_trip.py --repo click --max-retries 15
    python scripts/test_guided_round_trip.py --repo click --model qwen2.5:7b
""",
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Repository name (looks for /tmp/test-repos/NAME)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=10,
        help="Maximum retry iterations (default: 10)",
    )
    parser.add_argument(
        "--model",
        default="qwen2.5:7b",
        help="Ollama model name (default: qwen2.5:7b)",
    )
    parser.add_argument(
        "--output-dir",
        default="results/test-guided/",
        help="Output directory for results (default: results/test-guided/)",
    )
    args = parser.parse_args()

    try:
        result = asyncio.run(run_test_guided(args))
        if "error" in result:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
