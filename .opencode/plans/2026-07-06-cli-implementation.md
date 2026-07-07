# CLI + MCP Server Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the MCP server for OpenCode integration and build a CLI (`opencode-arch`) with extract/generate/bench/metrics commands that use `opencode run` as the agent backend.

**Architecture:** CLI orchestrates scan/validate/test/store locally, delegates the "thinking" step (YAML extraction, code generation) to OpenCode via subprocess. Metrics read from existing SQLite telemetry store. Runner protocol allows swapping OpenCode subprocess for a custom model later.

**Tech Stack:** Python 3.11+, argparse (stdlib), subprocess (stdlib), existing telemetry store, `opencode run` subprocess

**Working directory:** `/Users/baigm2/Documents/Projects/opencode-arch/`

---

### Task 1: Fix MCP Server (FastMCP API change)

**Files:**
- Modify: `src/opencode_arch/mcp/server.py:11`

**Step 1: Fix the FastMCP constructor**

```python
# Change line 11 from:
    mcp = FastMCP(
        "opencode-arch",
        description="Architecture context compression, validation, and code quality tools",
    )
# To:
    mcp = FastMCP(
        "opencode-arch",
        instructions="Architecture context compression, validation, and code quality tools",
    )
```

**Step 2: Verify MCP server loads**

Run: `python -c "from opencode_arch.mcp.server import mcp; print(mcp.name)"`
Expected: `opencode-arch`

**Step 3: Run all tests**

Run: `pytest tests/ -v`
Expected: 28 passed

**Step 4: Commit**

```bash
git add src/opencode_arch/mcp/server.py
git commit -m "fix: update FastMCP constructor for mcp v1.28 API (description->instructions)"
```

---

### Task 2: Runner Protocol + OpenCode Backend

**Files:**
- Create: `src/opencode_arch/runner/__init__.py`
- Create: `src/opencode_arch/runner/base.py`
- Create: `src/opencode_arch/runner/opencode.py`
- Test: `tests/test_runner.py`

**Step 1: Write failing test**

```python
# tests/test_runner.py
"""Tests for the runner backends."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from opencode_arch.runner.base import RunResult
from opencode_arch.runner.opencode import OpencodeRunner


class TestRunResult:
    def test_run_result_fields(self):
        r = RunResult(output="hello", exit_code=0, success=True)
        assert r.output == "hello"
        assert r.exit_code == 0
        assert r.success is True

    def test_run_result_failure(self):
        r = RunResult(output="error", exit_code=1, success=False)
        assert r.success is False


class TestOpencodeRunner:
    @pytest.mark.asyncio
    async def test_run_calls_subprocess(self):
        """Should call opencode run with the prompt."""
        runner = OpencodeRunner()
        mock_result = MagicMock()
        mock_result.stdout = "extraction complete"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = await runner.run(
                prompt="Extract architecture",
                repo_path="/tmp/test-repo",
            )
            assert result.success is True
            assert "extraction complete" in result.output
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert "opencode" in call_args[0][0][0]
            assert "run" in call_args[0][0][1]

    @pytest.mark.asyncio
    async def test_run_handles_timeout(self):
        """Should handle subprocess timeout gracefully."""
        import subprocess
        runner = OpencodeRunner(timeout=1)

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="opencode", timeout=1)):
            result = await runner.run(prompt="test", repo_path="/tmp/x")
            assert result.success is False
            assert "timeout" in result.output.lower()

    @pytest.mark.asyncio
    async def test_run_handles_not_found(self):
        """Should handle missing opencode binary."""
        runner = OpencodeRunner()

        with patch("subprocess.run", side_effect=FileNotFoundError("opencode not found")):
            result = await runner.run(prompt="test", repo_path="/tmp/x")
            assert result.success is False
            assert "not found" in result.output.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_runner.py -v`
Expected: ImportError

**Step 3: Write implementation**

```python
# src/opencode_arch/runner/__init__.py
"""Runner backends for agent invocation."""
from opencode_arch.runner.base import RunResult, RunnerBackend
from opencode_arch.runner.opencode import OpencodeRunner

__all__ = ["RunResult", "RunnerBackend", "OpencodeRunner"]
```

```python
# src/opencode_arch/runner/base.py
"""Runner protocol and result types."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class RunResult:
    """Result of an agent run."""
    output: str
    exit_code: int
    success: bool


class RunnerBackend(Protocol):
    """Protocol for agent invocation backends."""

    async def run(self, prompt: str, repo_path: str) -> RunResult:
        """Run the agent with a prompt in a repo context."""
        ...
```

```python
# src/opencode_arch/runner/opencode.py
"""OpenCode subprocess runner backend."""
from __future__ import annotations

import subprocess
from pathlib import Path

from opencode_arch.runner.base import RunResult, RunnerBackend


class OpencodeRunner:
    """Invokes `opencode run` as a subprocess."""

    def __init__(self, timeout: int = 300, model: str | None = None):
        self.timeout = timeout
        self.model = model

    async def run(self, prompt: str, repo_path: str) -> RunResult:
        """Run OpenCode with a prompt in the given repo directory."""
        cmd = ["opencode", "run", prompt, "--dir", repo_path]
        if self.model:
            cmd.extend(["--model", self.model])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return RunResult(
                output=result.stdout + result.stderr,
                exit_code=result.returncode,
                success=result.returncode == 0,
            )
        except subprocess.TimeoutExpired:
            return RunResult(
                output=f"Timeout: opencode run exceeded {self.timeout}s",
                exit_code=-1,
                success=False,
            )
        except FileNotFoundError:
            return RunResult(
                output="Error: opencode not found. Install with: npm i -g opencode",
                exit_code=-1,
                success=False,
            )
        except Exception as e:
            return RunResult(
                output=f"Error: {e}",
                exit_code=-1,
                success=False,
            )
```

**Step 4: Run tests**

Run: `pytest tests/test_runner.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
git add src/opencode_arch/runner/ tests/test_runner.py
git commit -m "feat: add runner protocol + OpenCode subprocess backend"
```

---

### Task 3: CLI Entry Point + Extract Command

**Files:**
- Create: `src/opencode_arch/cli/__init__.py`
- Create: `src/opencode_arch/cli/main.py`
- Create: `src/opencode_arch/cli/extract.py`
- Create: `src/opencode_arch/cli/prompts.py`
- Modify: `pyproject.toml` (add entry point)
- Test: `tests/test_cli_extract.py`

**Step 1: Write failing test**

```python
# tests/test_cli_extract.py
"""Tests for the extract CLI command."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

from opencode_arch.cli.extract import run_extract
from opencode_arch.runner.base import RunResult


MOCK_AGENT_YAML = """\
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: App
      status: ACTIVE
  capabilities:
    - id: CAP-F1
      name: Core
      status: ACTIVE
relationships:
  - from: COMP-1
    to: CAP-F1
    type: realizes
"""


class TestExtractCommand:
    @pytest.mark.asyncio
    async def test_extract_success(self):
        """Should run full extraction loop and return metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "app.py").write_text("class App: pass\n")

            mock_runner = AsyncMock()
            mock_runner.run.return_value = RunResult(
                output=f"```yaml\n{MOCK_AGENT_YAML}```",
                exit_code=0,
                success=True,
            )

            result = await run_extract(
                repo_path=tmpdir,
                runner=mock_runner,
                budget=2000,
                focus="all",
                target_score=80,
            )
            assert result["success"] is True
            assert result["score"] >= 80
            assert result["tokens_used"] > 0
            assert Path(tmpdir, ".architecture-model.yaml").exists()

    @pytest.mark.asyncio
    async def test_extract_runner_failure(self):
        """Should handle runner failure gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "app.py").write_text("x = 1\n")

            mock_runner = AsyncMock()
            mock_runner.run.return_value = RunResult(
                output="Error: model unavailable",
                exit_code=1,
                success=False,
            )

            result = await run_extract(
                repo_path=tmpdir,
                runner=mock_runner,
            )
            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_extract_nonexistent_path(self):
        """Should fail for nonexistent repo."""
        mock_runner = AsyncMock()
        result = await run_extract(
            repo_path="/tmp/nonexistent_xyz_abc",
            runner=mock_runner,
        )
        assert result["success"] is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_extract.py -v`
Expected: ImportError

**Step 3: Write implementation**

```python
# src/opencode_arch/cli/__init__.py
"""CLI for opencode-arch."""
```

```python
# src/opencode_arch/cli/prompts.py
"""Prompt templates for agent invocation."""

EXTRACT_PROMPT = """\
Extract the architecture of the repository at: {repo_path}

Focus: {focus}
Token budget: {budget}
Target validation score: {target_score}+

Use the architect_scan, architect_slice, architect_validate, and architect_extract tools to complete the extraction. Output the final YAML model between ```yaml fences.
"""

GENERATE_PROMPT = """\
Generate code for the repository at: {repo_path}

Use architect_scan and architect_slice to understand the architecture.
Then generate code that passes the test suite.
Use architect_generate to run tests and verify.
Iterate on failures (max {max_iter} attempts).
"""
```

```python
# src/opencode_arch/cli/extract.py
"""Extract command - full architecture extraction loop."""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

from opencode_arch.runner.base import RunResult, RunnerBackend
from opencode_arch.cli.prompts import EXTRACT_PROMPT


async def run_extract(
    repo_path: str,
    runner: RunnerBackend,
    budget: int = 4000,
    focus: str = "all",
    target_score: int = 80,
) -> dict[str, Any]:
    """Run the full extraction loop.

    1. Validates repo exists
    2. Calls runner with extraction prompt
    3. Parses YAML from output
    4. Validates and stores via tool APIs
    5. Records telemetry
    6. Returns metrics
    """
    path = Path(repo_path)
    if not path.exists():
        return {"success": False, "error": f"Path does not exist: {repo_path}"}

    start_time = time.time()

    prompt = EXTRACT_PROMPT.format(
        repo_path=str(path.resolve()),
        focus=focus,
        budget=budget,
        target_score=target_score,
    )

    result = await runner.run(prompt=prompt, repo_path=str(path))
    elapsed = time.time() - start_time

    if not result.success:
        return {
            "success": False,
            "error": f"Runner failed: {result.output[:500]}",
            "time_seconds": elapsed,
        }

    yaml_content = _extract_yaml_from_output(result.output)
    if not yaml_content:
        return {
            "success": False,
            "error": "No YAML model found in agent output",
            "time_seconds": elapsed,
        }

    from opencode_arch.mcp.tools.extract import store_extraction
    store_result = await store_extraction(
        repo_path=str(path),
        model_yaml=yaml_content,
        context_tokens=budget,
    )

    return {
        "success": store_result.get("stored", False),
        "score": store_result.get("score", 0),
        "tokens_used": budget,
        "time_seconds": elapsed,
        "iterations": 1,
        "issues": store_result.get("issues", []),
        "path": store_result.get("path", ""),
    }


def _extract_yaml_from_output(output: str) -> str | None:
    """Extract YAML content from agent output (between ```yaml fences)."""
    match = re.search(r"```ya?ml\s*\n(.*?)```", output, re.DOTALL)
    if match:
        return match.group(1).strip()

    match = re.search(r"```\s*\n(.*?)```", output, re.DOTALL)
    if match:
        content = match.group(1).strip()
        if "meta:" in content or "entities:" in content:
            return content

    match = re.search(r"(meta:\s*\n.*?)(?:\n\n|\Z)", output, re.DOTALL)
    if match:
        return match.group(1).strip()

    return None
```

```python
# src/opencode_arch/cli/main.py
"""CLI entry point for opencode-arch."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="opencode-arch",
        description="Architecture extraction, generation, and benchmarking CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # extract
    extract_p = subparsers.add_parser("extract", help="Extract architecture from a repository")
    extract_p.add_argument("repo_path", help="Path to the target repository")
    extract_p.add_argument("--budget", type=int, default=4000, help="Token budget (default: 4000)")
    extract_p.add_argument("--focus", default="all", help="Focus: all, F-block ID, layer name")
    extract_p.add_argument("--target-score", type=int, default=80, help="Min validation score (default: 80)")
    extract_p.add_argument("--model", default=None, help="Model override (provider/model)")
    extract_p.add_argument("--timeout", type=int, default=300, help="Timeout seconds (default: 300)")

    # generate
    gen_p = subparsers.add_parser("generate", help="Generate code and run tests")
    gen_p.add_argument("repo_path", help="Path to the target repository")
    gen_p.add_argument("--max-iter", type=int, default=3, help="Max retries (default: 3)")
    gen_p.add_argument("--test-command", default=None, help="Custom test command")
    gen_p.add_argument("--model", default=None, help="Model override (provider/model)")
    gen_p.add_argument("--timeout", type=int, default=300, help="Timeout seconds (default: 300)")

    # bench
    bench_p = subparsers.add_parser("bench", help="Benchmark extraction on multiple repos")
    bench_p.add_argument("repos", nargs="+", help="Paths to target repositories")
    bench_p.add_argument("--output", default=None, help="Output file (JSON)")
    bench_p.add_argument("--model", default=None, help="Model override (provider/model)")

    # metrics
    metrics_p = subparsers.add_parser("metrics", help="Display recorded metrics")
    metrics_p.add_argument("--tool", default=None, help="Filter by tool name")
    metrics_p.add_argument("--last", type=int, default=10, help="Number of records (default: 10)")

    args = parser.parse_args()

    if args.command == "extract":
        from opencode_arch.cli.extract import run_extract
        from opencode_arch.runner.opencode import OpencodeRunner
        runner = OpencodeRunner(timeout=args.timeout, model=args.model)
        result = asyncio.run(run_extract(
            repo_path=args.repo_path, runner=runner,
            budget=args.budget, focus=args.focus, target_score=args.target_score,
        ))
        _print_extract_result(result)

    elif args.command == "generate":
        from opencode_arch.cli.generate import run_generate
        from opencode_arch.runner.opencode import OpencodeRunner
        runner = OpencodeRunner(timeout=args.timeout, model=args.model)
        result = asyncio.run(run_generate(
            repo_path=args.repo_path, runner=runner,
            max_iter=args.max_iter, test_command=args.test_command,
        ))
        _print_generate_result(result)

    elif args.command == "bench":
        from opencode_arch.cli.bench import run_bench
        from opencode_arch.runner.opencode import OpencodeRunner
        runner = OpencodeRunner(model=args.model)
        results = asyncio.run(run_bench(repos=args.repos, runner=runner))
        _print_bench_results(results, output_file=args.output)

    elif args.command == "metrics":
        from opencode_arch.cli.metrics import show_metrics
        show_metrics(tool=args.tool, last=args.last)


def _print_extract_result(result: dict):
    if result["success"]:
        print(f"Extraction successful!")
        print(f"  Score:   {result['score']}/100")
        print(f"  Tokens:  {result['tokens_used']}")
        print(f"  Time:    {result['time_seconds']:.1f}s")
        print(f"  Path:    {result.get('path', 'N/A')}")
        if result.get("issues"):
            print(f"  Issues:  {len(result['issues'])}")
    else:
        print(f"Extraction failed: {result.get('error', 'unknown')}")
        sys.exit(1)


def _print_generate_result(result: dict):
    if result.get("passed"):
        print(f"Code generation successful!")
        print(f"  Pass rate:   {result['pass_rate']:.0%}")
        print(f"  Tests:       {result['total_tests']}")
        print(f"  Iterations:  {result['iterations']}")
        print(f"  Time:        {result['time_seconds']:.1f}s")
    else:
        print(f"Code generation incomplete")
        print(f"  Pass rate:   {result.get('pass_rate', 0):.0%}")
        if result.get("error"):
            print(f"  Error:       {result['error']}")
        sys.exit(1)


def _print_bench_results(results: list[dict], output_file: str | None):
    import json
    print(f"\nBenchmark Results ({len(results)} repos)")
    print("-" * 60)
    for r in results:
        status = "PASS" if r.get("success") else "FAIL"
        print(f"  [{status}] {r.get('repo', '?'):30} score={r.get('score', 0):3} time={r.get('time_seconds', 0):.1f}s")
    scores = [r["score"] for r in results if r.get("success")]
    if scores:
        print(f"\n  Average score: {sum(scores)/len(scores):.0f}/100")
        print(f"  Success rate:  {len(scores)}/{len(results)}")
    if output_file:
        Path(output_file).write_text(json.dumps(results, indent=2))
        print(f"\n  Saved to: {output_file}")


if __name__ == "__main__":
    main()
```

**Step 4: Add entry point to pyproject.toml**

Add after `[tool.hatch.build.targets.wheel]` section:
```toml
[project.scripts]
opencode-arch = "opencode_arch.cli.main:main"
```

**Step 5: Run tests**

Run: `pytest tests/test_cli_extract.py -v`
Expected: 3 passed

Run: `pytest tests/ -v`
Expected: 36 passed (28 + 5 + 3)

**Step 6: Commit**

```bash
git add src/opencode_arch/cli/ tests/test_cli_extract.py pyproject.toml
git commit -m "feat: add CLI entry point with extract command"
```

---

### Task 4: Generate Command

**Files:**
- Create: `src/opencode_arch/cli/generate.py`
- Test: `tests/test_cli_generate.py`

**Step 1: Write failing test**

```python
# tests/test_cli_generate.py
"""Tests for the generate CLI command."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

from opencode_arch.cli.generate import run_generate
from opencode_arch.runner.base import RunResult


class TestGenerateCommand:
    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Should run generate loop and report passing tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "calc.py").write_text("def add(a, b):\n    return a + b\n")
            Path(tmpdir, "test_calc.py").write_text(
                "from calc import add\ndef test_add():\n    assert add(1, 2) == 3\n"
            )
            mock_runner = AsyncMock()
            mock_runner.run.return_value = RunResult(output="done", exit_code=0, success=True)

            result = await run_generate(repo_path=tmpdir, runner=mock_runner, max_iter=3)
            assert result["passed"] is True
            assert result["pass_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_generate_nonexistent_path(self):
        """Should fail for nonexistent repo."""
        mock_runner = AsyncMock()
        result = await run_generate(repo_path="/tmp/nonexistent_xyz_abc", runner=mock_runner)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_generate_runner_failure(self):
        """Should still run tests even if runner fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "app.py").write_text("x = 1\n")
            mock_runner = AsyncMock()
            mock_runner.run.return_value = RunResult(output="Error", exit_code=1, success=False)

            result = await run_generate(repo_path=tmpdir, runner=mock_runner)
            assert "time_seconds" in result
```

**Step 2: Write implementation**

```python
# src/opencode_arch/cli/generate.py
"""Generate command - test-guided code generation loop."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from opencode_arch.runner.base import RunnerBackend
from opencode_arch.cli.prompts import GENERATE_PROMPT


async def run_generate(
    repo_path: str,
    runner: RunnerBackend,
    max_iter: int = 3,
    test_command: str | None = None,
) -> dict[str, Any]:
    """Run the test-guided code generation loop."""
    path = Path(repo_path)
    if not path.exists():
        return {"error": f"Path does not exist: {repo_path}", "passed": False}

    start_time = time.time()
    iterations = 0
    last_test_result = {}

    from opencode_arch.mcp.tools.generate import run_tests_on_generated_code

    for i in range(max_iter):
        iterations = i + 1

        prompt = GENERATE_PROMPT.format(repo_path=str(path.resolve()), max_iter=max_iter)
        if i > 0 and last_test_result.get("failures"):
            failures_str = "\n".join(last_test_result["failures"][:10])
            prompt += f"\n\nPrevious failures (iteration {i}):\n{failures_str}\nFix these issues."

        await runner.run(prompt=prompt, repo_path=str(path))

        test_result = await run_tests_on_generated_code(repo_path=str(path), test_command=test_command)
        last_test_result = test_result

        if test_result.get("passed") or test_result.get("pass_rate", 0) == 1.0:
            break
        if test_result.get("total_tests", 0) == 0:
            break

    elapsed = time.time() - start_time

    try:
        from opencode_arch.telemetry.store import TelemetryStore
        store = TelemetryStore()
        store.record(
            tool="architect_generate", repo=path.name,
            context_tokens=0, output_quality=int(last_test_result.get("pass_rate", 0) * 100),
            iterations=iterations,
        )
    except Exception:
        pass

    return {
        "passed": last_test_result.get("passed", False),
        "pass_rate": last_test_result.get("pass_rate", 0.0),
        "total_tests": last_test_result.get("total_tests", 0),
        "passed_tests": last_test_result.get("passed_tests", 0),
        "failures": last_test_result.get("failures", []),
        "iterations": iterations,
        "time_seconds": elapsed,
    }
```

**Step 3: Run tests**

Run: `pytest tests/test_cli_generate.py -v`
Expected: 3 passed

**Step 4: Commit**

```bash
git add src/opencode_arch/cli/generate.py tests/test_cli_generate.py
git commit -m "feat: add generate CLI command (test-guided code generation loop)"
```

---

### Task 5: Bench + Metrics Commands

**Files:**
- Create: `src/opencode_arch/cli/bench.py`
- Create: `src/opencode_arch/cli/metrics.py`
- Test: `tests/test_cli_bench.py`
- Test: `tests/test_cli_metrics.py`

**Step 1: Write tests**

```python
# tests/test_cli_bench.py
"""Tests for the bench CLI command."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

from opencode_arch.cli.bench import run_bench
from opencode_arch.runner.base import RunResult

MOCK_YAML = "meta:\n  project: t\n  schema_version: '1.3'\nentities:\n  components:\n    - id: COMP-1\n      name: X\n      status: ACTIVE\n"

class TestBenchCommand:
    @pytest.mark.asyncio
    async def test_bench_multiple_repos(self):
        repos = []
        for i in range(3):
            d = tempfile.mkdtemp()
            Path(d, "app.py").write_text(f"x = {i}\n")
            repos.append(d)
        mock_runner = AsyncMock()
        mock_runner.run.return_value = RunResult(output=f"```yaml\n{MOCK_YAML}```", exit_code=0, success=True)
        results = await run_bench(repos=repos, runner=mock_runner)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_bench_handles_failures(self):
        d = tempfile.mkdtemp()
        mock_runner = AsyncMock()
        mock_runner.run.return_value = RunResult(output=f"```yaml\n{MOCK_YAML}```", exit_code=0, success=True)
        results = await run_bench(repos=[d, "/tmp/nonexistent_xyz_bench"], runner=mock_runner)
        assert len(results) == 2
        assert results[1]["success"] is False
```

```python
# tests/test_cli_metrics.py
"""Tests for the metrics CLI command."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from opencode_arch.cli.metrics import show_metrics, format_metrics_table
from opencode_arch.telemetry.store import TelemetryStore


class TestMetricsCommand:
    def test_format_metrics_table_with_data(self):
        records = [
            {"tool": "extract", "repo": "my-repo", "context_tokens": 430, "output_quality": 94, "iterations": 1, "timestamp": 1720300000},
        ]
        output = format_metrics_table(records)
        assert "my-repo" in output
        assert "94" in output

    def test_format_metrics_table_empty(self):
        output = format_metrics_table([])
        assert "No records" in output

    def test_show_metrics_queries_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store = TelemetryStore(db_path=db_path)
            store.record(tool="extract", repo="test", context_tokens=500, output_quality=90, iterations=1)
            with patch("opencode_arch.cli.metrics.TelemetryStore", return_value=store):
                show_metrics(tool="extract", last=5)
```

**Step 2: Write implementations**

```python
# src/opencode_arch/cli/bench.py
"""Bench command - benchmark extraction on multiple repos."""
from __future__ import annotations
from typing import Any
from opencode_arch.runner.base import RunnerBackend
from opencode_arch.cli.extract import run_extract


async def run_bench(
    repos: list[str],
    runner: RunnerBackend,
    budget: int = 4000,
    target_score: int = 80,
) -> list[dict[str, Any]]:
    """Run extraction benchmark on multiple repositories."""
    results = []
    for repo_path in repos:
        result = await run_extract(
            repo_path=repo_path, runner=runner,
            budget=budget, target_score=target_score,
        )
        result["repo"] = repo_path
        results.append(result)
    return results
```

```python
# src/opencode_arch/cli/metrics.py
"""Metrics command - display recorded telemetry."""
from __future__ import annotations
import time
from opencode_arch.telemetry.store import TelemetryStore


def show_metrics(tool: str | None = None, last: int = 10):
    """Query and display metrics from the telemetry store."""
    store = TelemetryStore()
    records = store.query(tool=tool, limit=last)
    print(format_metrics_table(records))
    if tool and records:
        avgs = store.averages(tool=tool)
        print(f"\n  Averages for '{tool}':")
        print(f"    Tokens:     {avgs['avg_context_tokens']:.0f}")
        print(f"    Quality:    {avgs['avg_output_quality']:.0f}/100")
        print(f"    Iterations: {avgs['avg_iterations']:.1f}")


def format_metrics_table(records: list[dict]) -> str:
    """Format records as a readable table."""
    if not records:
        return "  No records found."
    lines = []
    lines.append(f"  {'Tool':<18} {'Repo':<25} {'Score':>5} {'Tokens':>6} {'Iter':>4} {'Time'}")
    lines.append("  " + "-" * 75)
    for r in records:
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(r.get("timestamp", 0)))
        lines.append(
            f"  {r.get('tool', '?'):<18} {r.get('repo', '?'):<25} "
            f"{r.get('output_quality', 0):>5} {r.get('context_tokens', 0):>6} "
            f"{r.get('iterations', 0):>4} {ts}"
        )
    return "\n".join(lines)
```

**Step 3: Run tests**

Run: `pytest tests/test_cli_bench.py tests/test_cli_metrics.py -v`
Expected: 5 passed

**Step 4: Run full suite**

Run: `pytest tests/ -v`
Expected: ~44 passed

**Step 5: Commit**

```bash
git add src/opencode_arch/cli/bench.py src/opencode_arch/cli/metrics.py tests/test_cli_bench.py tests/test_cli_metrics.py
git commit -m "feat: add bench and metrics CLI commands"
```

---

### Task 6: Final Verification + Docs

**Files:**
- Modify: `CONTEXT.md` (add CLI section)
- Modify: `pyproject.toml` (bump to v0.3.0)

**Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All pass (~44 tests)

**Step 2: Verify CLI entry point works**

Run: `pip install -e . && opencode-arch --help`
Expected: Shows help with extract/generate/bench/metrics

**Step 3: Verify MCP server loads**

Run: `python -c "from opencode_arch.mcp.server import mcp; print(mcp.name)"`
Expected: `opencode-arch`

**Step 4: Update CONTEXT.md with CLI section and bump version**

**Step 5: Commit**

```bash
git add -A
git commit -m "docs: add CLI docs to CONTEXT.md, bump to v0.3.0"
```

---

## Summary

| Task | Component | New Tests |
|------|-----------|-----------|
| 1 | Fix MCP server | 0 (verify existing 28) |
| 2 | Runner protocol + OpenCode backend | 5 |
| 3 | CLI entry point + extract command | 3 |
| 4 | Generate command | 3 |
| 5 | Bench + metrics commands | 5 |
| 6 | Final verification + docs | 0 |

**Total new tests: 16** (bringing total to ~44)

**Usage after implementation:**
```bash
# One-time: register MCP server with OpenCode
opencode mcp add

# Extract architecture:
opencode-arch extract /path/to/repo --budget=4000

# Generate code with test verification:
opencode-arch generate /path/to/repo --max-iter=3

# Benchmark:
opencode-arch bench /path/to/repo1 /path/to/repo2

# View metrics:
opencode-arch metrics --tool=extract --last=10
```
