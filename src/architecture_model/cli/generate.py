"""
CLI command for test-guided code generation.

Usage:
    architecture-model generate --test-guided /path/to/repo --max-retries 10 --model qwen2.5:7b
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def register_generate_command(subparsers: argparse._SubParsersAction) -> None:
    """Register the 'generate' subcommand."""
    p_generate = subparsers.add_parser(
        "generate",
        help="Generate code from architecture model",
        description="Generate implementation code using the architecture model. "
        "Currently supports --test-guided mode which iteratively generates "
        "code that passes the project's test suite.",
    )
    p_generate.add_argument(
        "repo_path",
        help="Path to the target repository",
    )
    p_generate.add_argument(
        "--test-guided",
        action="store_true",
        help="Enable test-guided generation mode (iterative generate/test/retry)",
    )
    p_generate.add_argument(
        "--max-retries",
        type=int,
        default=10,
        help="Maximum retry iterations (default: 10)",
    )
    p_generate.add_argument(
        "--model",
        default="qwen2.5:7b",
        help="Ollama model name (default: qwen2.5:7b)",
    )
    p_generate.add_argument(
        "--output",
        "-o",
        help="Output directory for generated code (default: stdout)",
    )
    p_generate.add_argument(
        "--convergence-threshold",
        type=int,
        default=3,
        help="Number of non-improving iterations before stopping (default: 3)",
    )


def _cmd_generate(args: argparse.Namespace) -> int:
    """Handle the 'generate' command."""
    if not args.test_guided:
        print("ERROR: Only --test-guided mode is currently supported.")
        print("Usage: architecture-model generate --test-guided /path/to/repo")
        return 1

    return asyncio.run(_run_test_guided(args))


def _check_training_deps() -> bool:
    """Check whether training dependencies are importable."""
    try:
        from architecture_model.training import test_guided_generator  # noqa: F401
        return True
    except ImportError:
        return False


async def _run_test_guided(args: argparse.Namespace) -> int:
    """Run the test-guided generation pipeline."""
    if not _check_training_deps():
        print(
            "ERROR: Training dependencies required. "
            "Install with: pip install architecture-model-standard[training]"
        )
        return 1

    from architecture_model.training.test_guided_generator import TestGuidedGenerator
    from architecture_model.training.surrogate import Surrogate
    from architecture_model.training.test_runner import TestRunner
    from architecture_model.training.test_contract_miner import TestContractMiner
    from architecture_model.training.prompt_builder import PromptBuilder
    from architecture_model.training.code_writer import CodeWriter
    from architecture_model.training.failure_parser import FailureParser
    from architecture_model.manifest.generator import generate_manifest
    from architecture_model.extract.from_code import extract_from_code

    repo_path = Path(args.repo_path).resolve()
    if not repo_path.is_dir():
        print(f"ERROR: {repo_path} is not a directory")
        return 1

    # Detect package name from repo path or pyproject.toml
    package_name = _detect_package_name(repo_path)

    print(f"Repository: {repo_path}")
    print(f"Package: {package_name}")
    print(f"Model: {args.model}")
    print(f"Max retries: {args.max_retries}")
    print(f"Convergence threshold: {args.convergence_threshold}")
    print()

    # 1. Generate manifest
    print("Generating manifest...")
    manifest = generate_manifest(repo_path)

    # 2. Extract architecture model
    print("Extracting architecture model...")
    model = extract_from_code(repo_path)

    # 3. Create dependencies
    surrogate = Surrogate(model_name=args.model)
    test_runner = TestRunner()
    contract_miner = TestContractMiner()
    prompt_builder = PromptBuilder()
    code_writer = CodeWriter()
    failure_parser = FailureParser()

    # 4. Create generator
    generator = TestGuidedGenerator(
        surrogate=surrogate,
        test_runner=test_runner,
        contract_miner=contract_miner,
        prompt_builder=prompt_builder,
        code_writer=code_writer,
        failure_parser=failure_parser,
        max_retries=args.max_retries,
        convergence_threshold=args.convergence_threshold,
    )

    # 5. Run generation
    print("Starting test-guided generation...")
    print()
    result = await generator.generate(model, manifest, repo_path, package_name)

    # 6. Print results
    print()
    print("=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"  Pass rate:   {result.final_pass_rate:.1%}")
    print(f"  Iterations:  {result.iterations}")
    print(f"  Converged:   {result.converged}")
    if result.structural_score is not None:
        print(f"  Structural:  {result.structural_score:.2f}")
    print()

    # 7. Write output
    if args.output:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{package_name}_generated.py"
        output_file.write_text(result.final_code, encoding="utf-8")
        print(f"Written to: {output_file}")
    else:
        print("--- Generated Code ---")
        print(result.final_code)

    return 0


def _detect_package_name(repo_path: Path) -> str:
    """Detect the package name from pyproject.toml or directory name."""
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8")
            # Simple TOML parsing for name field
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("name") and "=" in stripped:
                    # name = "package-name"
                    value = stripped.split("=", 1)[1].strip().strip("\"'")
                    if value:
                        # Normalize: dashes to underscores
                        return value.replace("-", "_")
        except (OSError, ValueError):
            pass

    # Fallback to directory name
    return repo_path.name.replace("-", "_")
