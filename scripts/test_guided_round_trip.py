#!/usr/bin/env python3
"""Test-Guided Round-Trip: real execution script for proof-of-concept runs.

Runs the full test-guided generation pipeline against repos in /tmp/test-repos/.
Supports Ollama (local models) or copilot-relay (frontier model via GitHub Copilot).

Usage:
    python scripts/test_guided_round_trip.py --repo python-dotenv --max-retries 10
    python scripts/test_guided_round_trip.py --repo click --max-retries 15
    python scripts/test_guided_round_trip.py --repo click --model qwen2.5:7b --output-dir results/test-guided/
    python scripts/test_guided_round_trip.py --repo python-dotenv --backend copilot-relay --max-retries 5
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
# Copilot-Relay Surrogate (duck-type compatible with Surrogate)
# ---------------------------------------------------------------------------


class CopilotRelaySurrogate:
    """Adapter that calls copilot-relay's SSE endpoint instead of Ollama.

    copilot-relay is a local SSE server at http://localhost:8400 that proxies
    requests to a frontier model (e.g., Claude) via GitHub Copilot.

    API:
        POST /chat  {"content": "user msg", "system": "system prompt"}
        Response: SSE stream with data: {"type": "chunk", "content": "..."} lines
                  ending with data: {"type": "done"}
    """

    def __init__(self, host: str = "http://localhost:8400"):
        self._host = host

    async def generate_with_prompt(self, system: str, user: str) -> str:
        """Generate code using copilot-relay (frontier model).

        Matches the Surrogate.generate_with_prompt(system, user) -> str interface.
        """
        import aiohttp

        url = f"{self._host}/chat"
        payload = {"content": user, "system": system}

        chunks: list[str] = []
        timeout = aiohttp.ClientTimeout(total=180)  # 3 minutes per request
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        print(f"[copilot-relay] HTTP {resp.status}")
                        return ""
                    # Parse SSE stream
                    async for line in resp.content:
                        text = line.decode("utf-8").strip()
                        if not text.startswith("data: "):
                            continue
                        data_str = text[6:]  # strip "data: " prefix
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        if data.get("type") == "chunk":
                            chunks.append(data.get("content", ""))
                        elif data.get("type") == "done":
                            break
                        elif data.get("type") == "error":
                            print(f"[copilot-relay] Error: {data.get('content', 'unknown')}")
                            break
        except asyncio.TimeoutError:
            print(f"[copilot-relay] TIMEOUT after 180s (got {len(chunks)} chunks so far)")
            # Return whatever we have so far
        except Exception as e:
            print(f"[copilot-relay] Exception: {e}")
            return ""

        content = "".join(chunks)
        if not content:
            return ""

        # Strip markdown fences (same logic as Surrogate)
        if "```python" in content:
            content = content.split("```python", 1)[1].split("```", 1)[0]
        elif "```" in content:
            content = content.split("```", 1)[1].split("```", 1)[0]

        # Strip non-Python preamble (frontier models often output diagrams/explanations)
        content = self._strip_preamble(content)
        return content.strip()

    @staticmethod
    def _strip_preamble(content: str) -> str:
        """Strip non-Python content before actual code.

        Frontier models often output mermaid diagrams, explanations, or planning
        text before the actual code, despite system prompt instructions.
        """
        import re

        lines = content.split("\n")

        # Find first line that looks like Python code or module header
        code_start_patterns = [
            re.compile(r"^#\s*[\w._/\-]+\.py\s*$"),  # Module header: # module.py
            re.compile(r"^(from|import)\s"),           # Import statement
            re.compile(r"^(class|def)\s"),             # Class/function definition
            re.compile(r'^"""'),                       # Docstring
            re.compile(r"^'"),                         # String/docstring
        ]

        for i, line in enumerate(lines):
            for pattern in code_start_patterns:
                if pattern.match(line.strip()):
                    return "\n".join(lines[i:])

        # No Python code found — return as-is (let downstream handle it)
        return content

    async def generate_code(self, model_slice: str) -> str:
        """Forward pass: architecture YAML → code (for compatibility)."""
        system = (
            "You are a code generation assistant. Given an architecture model in YAML, "
            "produce a complete Python implementation. Output ONLY valid Python code."
        )
        return await self.generate_with_prompt(system, model_slice)


class PerComponentGenerator(TestGuidedGenerator):
    """Subclass that generates code per-component in iteration 1.

    Frontier models (copilot-relay) are better at focused generation of one
    module at a time rather than generating all modules in a single response,
    which often leads to truncation or off-topic output (diagrams, explanations).

    Uses focused natural-language prompts (not heavy YAML system prompts)
    to stay within copilot-relay's output token budget.

    Includes regression guard: if a retry worsens pass rate, reverts to best code.
    """

    _FOCUSED_SYSTEM = (
        "You are a Python code generator. Generate the COMPLETE implementation "
        "of the requested module. Output ONLY valid Python code. "
        "No markdown fences. No explanations. No commentary. Just code."
    )

    async def _initial_generation(self, model_yaml: str, contracts) -> str:
        """Generate each component individually with focused prompts.

        Uses a lightweight prompt per component (describing what to generate
        in natural language rather than dumping full YAML) to stay within
        copilot-relay's response budget.
        """
        import re
        import yaml as _yaml

        # Parse component details from model YAML
        try:
            model_dict = _yaml.safe_load(model_yaml)
            components = model_dict.get("entities", {}).get("components", [])
        except Exception:
            return await super()._initial_generation(model_yaml, contracts)

        if not components:
            return await super()._initial_generation(model_yaml, contracts)

        print(f"    Generating {len(components)} components individually...")
        parts = []

        for comp in components:
            comp_name = comp.get("name", comp.get("id", ""))
            if not comp_name:
                continue

            # Build focused prompt from component metadata
            user_prompt = self._build_focused_prompt(comp, contracts)
            print(f"      -> {comp_name}...", end=" ", flush=True)

            code = await self._surrogate.generate_with_prompt(
                self._FOCUSED_SYSTEM, user_prompt
            )

            if code:
                parts.append(f"# {comp_name}.py\n{code}")
                print(f"OK ({len(code)} chars)")
            else:
                # Retry once with an even simpler prompt
                print("EMPTY, retrying...", end=" ", flush=True)
                await asyncio.sleep(2)  # Brief pause before retry
                simple_prompt = (
                    f"Generate the complete Python module '{comp_name}.py'. "
                    f"It should contain working implementations (not stubs)."
                )
                if comp.get("symbols"):
                    classes = [s.get("name", "") for s in comp["symbols"] if s.get("name")]
                    simple_prompt += f" Classes: {', '.join(classes)}."
                if comp.get("functions"):
                    funcs = comp["functions"][:10]
                    simple_prompt += f" Functions: {', '.join(funcs)}."

                code = await self._surrogate.generate_with_prompt(
                    self._FOCUSED_SYSTEM, simple_prompt
                )
                if code:
                    parts.append(f"# {comp_name}.py\n{code}")
                    print(f"OK ({len(code)} chars)")
                else:
                    print("FAILED")

            # Small delay between components to avoid rate limiting
            await asyncio.sleep(1)

        return "\n\n".join(parts)

    def _build_focused_prompt(self, comp: dict, contracts) -> str:
        """Build a focused natural-language prompt for a single component."""
        comp_name = comp.get("name", comp.get("id", ""))
        lines = [f"Generate the complete Python module '{comp_name}.py'."]

        # Add class/symbol info
        symbols = comp.get("symbols", [])
        if symbols:
            for sym in symbols:
                name = sym.get("name", "")
                members = sym.get("members", [])
                supers = sym.get("supers", [])
                if name:
                    desc = f"class {name}"
                    if supers:
                        desc += f"({', '.join(supers)})"
                    if members:
                        desc += f" with methods: {', '.join(members[:15])}"
                    lines.append(desc)

        # Add functions
        functions = comp.get("functions", [])
        if functions:
            lines.append(f"Top-level functions: {', '.join(functions[:15])}")

        # Add contracts
        contract_text = contracts.summary_for_prompt(comp_name)
        if contract_text:
            lines.append(f"\nBehavioral contracts from tests:\n{contract_text}")

        lines.append(
            "\nIMPORTANT: Implement ALL method/function bodies with real logic. "
            "Do NOT use 'pass' or '...' stubs. Use relative imports for sibling modules."
        )

        return "\n".join(lines)

    async def _targeted_retry(
        self,
        failures,
        model_yaml: str,
        contracts,
        current_code: str,
    ) -> tuple[str, list[str]]:
        """Override retry to use focused prompts and only retry known components.

        Prevents retrying phantom module names extracted from test failure paths.
        Uses the same focused prompt style as initial generation.
        """
        import re
        import yaml as _yaml

        # Only retry components that are actually in the generated code (have headers)
        generated_components = set()
        for match in re.finditer(r"^#\s*([\w._/\-]+)\.py\s*$", current_code, re.MULTILINE):
            generated_components.add(Path(match.group(1)).stem)

        # Get failing components from the failure parser
        if failures.by_component:
            failing = sorted(
                failures.by_component.items(),
                key=lambda x: len(x[1]),
                reverse=True,
            )
            # Only retry components we actually generated
            to_fix = [c for c, _ in failing if c in generated_components][:3]
        else:
            to_fix = list(generated_components)[:3]

        if not to_fix:
            return current_code, []

        # Parse component metadata from YAML for focused prompts
        try:
            model_dict = _yaml.safe_load(model_yaml)
            components = model_dict.get("entities", {}).get("components", [])
            comp_map = {c.get("name", c.get("id", "")): c for c in components}
        except Exception:
            comp_map = {}

        regenerated = []
        code = current_code

        for comp_name in to_fix:
            comp_meta = comp_map.get(comp_name, {"name": comp_name})

            # Build retry prompt with failure context
            failure_text = failures.format_for_retry_prompt(comp_name)
            existing_code = self._extract_component_code(code, comp_name)

            user_prompt = (
                f"Fix the Python module '{comp_name}.py'. "
                f"The current implementation has test failures.\n\n"
                f"CURRENT CODE:\n{existing_code[:3000]}\n\n"
                f"TEST FAILURES:\n{failure_text[:2000]}\n\n"
                f"Generate the FIXED complete module. Fix ONLY the bugs described above. "
                f"Maintain the same structure. Output ONLY Python code."
            )

            print(f"      retry {comp_name}...", end=" ", flush=True)
            fixed = await self._surrogate.generate_with_prompt(
                self._FOCUSED_SYSTEM, user_prompt
            )

            if fixed and len(fixed) > 20:
                code = self._splice_component(code, comp_name, fixed)
                regenerated.append(comp_name)
                print(f"OK ({len(fixed)} chars)")
            else:
                print("SKIPPED (empty response)")

            await asyncio.sleep(1)

        return code, regenerated


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

    backend = getattr(args, "backend", "ollama")
    model_label = f"copilot-relay (frontier)" if backend == "copilot-relay" else args.model

    print(f"\n{'='*70}")
    print(f"  TEST-GUIDED GENERATION: {repo_name}")
    print(f"{'='*70}")
    print(f"  Repo:      {repo_root}")
    print(f"  Package:   {package_name}")
    print(f"  Backend:   {backend}")
    print(f"  Model:     {model_label}")
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
        if backend == "copilot-relay":
            surrogate = CopilotRelaySurrogate()
        else:
            surrogate = Surrogate(model_name=args.model)
        test_runner = TestRunner()
        prompt_builder = PromptBuilder()
        code_writer = CodeWriter()
        failure_parser = FailureParser()

        # Use per-component generator for copilot-relay (avoids response truncation)
        generator_cls = PerComponentGenerator if backend == "copilot-relay" else TestGuidedGenerator
        generator = generator_cls(
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
    if backend == "copilot-relay":
        print("    Using copilot-relay frontier model at http://localhost:8400\n")
    else:
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
            if backend == "copilot-relay":
                print("\n    Is copilot-relay running? Check: curl http://localhost:8400/health")
            else:
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
        "backend": backend,
        "model": model_label,
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
    python scripts/test_guided_round_trip.py --repo python-dotenv --backend copilot-relay
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
        help="Ollama model name (default: qwen2.5:7b). Ignored if --backend=copilot-relay",
    )
    parser.add_argument(
        "--backend",
        choices=["ollama", "copilot-relay"],
        default="ollama",
        help="LLM backend to use (default: ollama)",
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
