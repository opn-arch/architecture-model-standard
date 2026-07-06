# Phase 1: Three-Repo Split Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split architecture-model-standard into three focused repositories, delivering a working MCP server (opencode-arch) and a standalone training package (arch-agent) that communicate via the shared schema.

**Architecture:** Create `arch-agent` first (mechanical move of training/), then `opencode-arch` (new MCP server), finally clean up `architecture-model-standard`. Each repo is independently testable. The MCP server wraps existing functionality from architecture-model-standard with oracle scoring from copilot-relay.

**Tech Stack:** Python 3.11+, FastMCP (mcp library), aiohttp (SSE client), pytest, hatchling (build), architecture-model-standard (shared dependency)

---

## Task 1: Create arch-agent Repository Structure

**Files:**
- Create: `~/Documents/Projects/arch-agent/pyproject.toml`
- Create: `~/Documents/Projects/arch-agent/src/arch_agent/__init__.py`
- Create: `~/Documents/Projects/arch-agent/README.md`

**Step 1: Initialize the repository**

```bash
cd ~/Documents/Projects
mkdir arch-agent && cd arch-agent
git init
mkdir -p src/arch_agent tests
```

**Step 2: Write pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "arch-agent"
version = "0.1.0"
description = "Self-improving architecture extraction and code generation model with DPO training"
requires-python = ">=3.11"
dependencies = [
    "architecture-model-standard>=0.3.0",
    "torch>=2.0",
    "transformers>=4.40",
    "peft>=0.10",
    "datasets>=2.19",
    "trl>=0.8",
    "litellm>=1.40",
    "aiohttp>=3.9",
    "numpy>=1.26",
]
license = "MIT"

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21"]

[project.scripts]
arch-agent = "arch_agent.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/arch_agent"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 3: Write `src/arch_agent/__init__.py`**

```python
"""arch-agent: Self-improving architecture extraction and code generation."""

__version__ = "0.1.0"
```

**Step 4: Commit scaffold**

```bash
git add . && git commit -m "chore: initial arch-agent repository scaffold"
```

---

## Task 2: Move Training Modules to arch-agent

**Files:**
- Copy: `architecture-model-standard/src/architecture_model/training/*.py` → `arch-agent/src/arch_agent/training/`
- Copy: `architecture-model-standard/tests/test_training/` → `arch-agent/tests/test_training/`

**Step 1: Copy source files**

```bash
cp -r ~/Documents/Projects/architecture-model-standard/src/architecture_model/training \
      ~/Documents/Projects/arch-agent/src/arch_agent/training
```

**Step 2: Copy test files**

```bash
cp -r ~/Documents/Projects/architecture-model-standard/tests/test_training \
      ~/Documents/Projects/arch-agent/tests/test_training
```

**Step 3: Fix import paths**

All imports in the copied files reference `architecture_model.training.*`. These need to become `arch_agent.training.*`.

Run:
```bash
cd ~/Documents/Projects/arch-agent
find src tests -name "*.py" -exec sed -i '' 's/architecture_model\.training/arch_agent.training/g' {} +
find src tests -name "*.py" -exec sed -i '' 's/from architecture_model import/from architecture_model import/g' {} +
```

Note: Keep `from architecture_model import` and `from architecture_model.core` etc. as-is — those reference the schema package which remains a dependency.

**Step 4: Install in dev mode and verify imports**

```bash
cd ~/Documents/Projects/arch-agent
pip install -e ~/Documents/Projects/architecture-model-standard
pip install -e ".[dev]"
python -c "from arch_agent.training.surrogate import Surrogate; print('OK')"
```

**Step 5: Run tests**

```bash
pytest tests/ --ignore=tests/test_training/test_config_loader.py -x -q
```

Expected: 619 tests pass (same as before, since we only changed the namespace).

**Step 6: Commit**

```bash
git add . && git commit -m "feat: move training pipeline from architecture-model-standard (39 modules, 619 tests)"
```

---

## Task 3: Add arch-agent CLI Entry Point

**Files:**
- Create: `~/Documents/Projects/arch-agent/src/arch_agent/cli.py`
- Test: `~/Documents/Projects/arch-agent/tests/test_cli.py`

**Step 1: Write failing test**

```python
# tests/test_cli.py
"""Tests for the arch-agent CLI."""
import subprocess
import sys


def test_cli_version():
    result = subprocess.run(
        [sys.executable, "-m", "arch_agent.cli", "--version"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "arch_agent.cli", "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "arch-agent" in result.stdout.lower() or "usage" in result.stdout.lower()
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_cli.py -v
```

Expected: FAIL (module not found or no --version flag)

**Step 3: Write minimal implementation**

```python
# src/arch_agent/cli.py
"""arch-agent CLI entry point."""
import argparse
import sys

from arch_agent import __version__


def main():
    parser = argparse.ArgumentParser(
        prog="arch-agent",
        description="Self-improving architecture extraction and code generation model"
    )
    parser.add_argument("--version", action="version", version=f"arch-agent {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    # train subcommand
    train_parser = subparsers.add_parser("train", help="Run training pipeline")
    train_parser.add_argument("--pairs-dir", help="Directory containing DPO pairs")
    train_parser.add_argument("--base-model", default="qwen2.5:7b", help="Base model ID")

    # infer subcommand
    infer_parser = subparsers.add_parser("infer", help="Run inference (extraction or generation)")
    infer_parser.add_argument("--task", choices=["extract", "generate"], required=True)
    infer_parser.add_argument("--input", required=True, help="Input file path")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/test_cli.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add . && git commit -m "feat: add arch-agent CLI with train and infer subcommands"
```

---

## Task 4: Create opencode-arch Repository Structure

**Files:**
- Create: `~/Documents/Projects/opencode-arch/pyproject.toml`
- Create: `~/Documents/Projects/opencode-arch/src/opencode_arch/__init__.py`
- Create: `~/Documents/Projects/opencode-arch/src/opencode_arch/mcp/__init__.py`
- Create: `~/Documents/Projects/opencode-arch/src/opencode_arch/mcp/server.py`

**Step 1: Initialize the repository**

```bash
cd ~/Documents/Projects
mkdir opencode-arch && cd opencode-arch
git init
mkdir -p src/opencode_arch/mcp/tools src/opencode_arch/oracle src/opencode_arch/context tests
```

**Step 2: Write pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "opencode-arch"
version = "0.1.0"
description = "OpenCode architecture extension - MCP server for extraction, generation, and validation"
requires-python = ">=3.11"
dependencies = [
    "architecture-model-standard>=0.3.0",
    "mcp>=1.0",
    "aiohttp>=3.9",
    "pyyaml>=6.0",
]
license = "MIT"

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21"]
training = ["arch-agent>=0.1.0"]

[tool.hatch.build.targets.wheel]
packages = ["src/opencode_arch"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

**Step 3: Write `src/opencode_arch/__init__.py`**

```python
"""opencode-arch: Architecture extraction, generation, and validation for OpenCode."""

__version__ = "0.1.0"
```

**Step 4: Commit scaffold**

```bash
git add . && git commit -m "chore: initial opencode-arch repository scaffold"
```

---

## Task 5: Implement Oracle (copilot-relay) Adapter

**Files:**
- Create: `~/Documents/Projects/opencode-arch/src/opencode_arch/oracle/__init__.py`
- Create: `~/Documents/Projects/opencode-arch/src/opencode_arch/oracle/copilot_relay.py`
- Test: `~/Documents/Projects/opencode-arch/tests/test_oracle.py`

**Step 1: Write failing test**

```python
# tests/test_oracle.py
"""Tests for the copilot-relay oracle adapter."""
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from opencode_arch.oracle.copilot_relay import CopilotRelayOracle


@pytest.fixture
def oracle():
    return CopilotRelayOracle(host="http://localhost:8400")


class TestCopilotRelayOracle:
    def test_init_default_host(self):
        oracle = CopilotRelayOracle()
        assert oracle._host == "http://localhost:8400"

    def test_init_custom_host(self):
        oracle = CopilotRelayOracle(host="http://custom:9000")
        assert oracle._host == "http://custom:9000"

    @pytest.mark.asyncio
    async def test_generate_parses_sse_stream(self, oracle):
        """Oracle should parse SSE stream and concatenate chunk contents."""
        mock_lines = [
            b'data: {"type": "chunk", "content": "Hello"}',
            b'data: {"type": "chunk", "content": " world"}',
            b'data: {"type": "done"}',
        ]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content.__aiter__ = lambda self: self
        mock_response.content.__anext__ = AsyncMock(side_effect=mock_lines + [StopAsyncIteration()])

        with patch("aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.post.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await oracle.generate("system prompt", "user message")
            assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_score_extraction(self, oracle):
        """Score method should return a dict with score and feedback."""
        with patch.object(oracle, "generate", return_value='{"score": 85, "feedback": "Good coverage"}'):
            result = await oracle.score_extraction(
                model_yaml="entities: []",
                source_code="def foo(): pass"
            )
            assert result["score"] == 85
            assert "Good" in result["feedback"]
```

**Step 2: Run test to verify it fails**

```bash
cd ~/Documents/Projects/opencode-arch
pytest tests/test_oracle.py -v
```

Expected: FAIL (module not found)

**Step 3: Write implementation**

```python
# src/opencode_arch/oracle/__init__.py
"""Oracle scoring via frontier models."""

from opencode_arch.oracle.copilot_relay import CopilotRelayOracle

__all__ = ["CopilotRelayOracle"]
```

```python
# src/opencode_arch/oracle/copilot_relay.py
"""Copilot-relay SSE adapter for oracle scoring.

copilot-relay is a local SSE server at http://localhost:8400 that proxies
requests to a frontier model (e.g., Claude) via GitHub Copilot.

API:
    POST /chat  {"content": "user msg", "system": "system prompt"}
    Response: SSE stream with data: {"type": "chunk", "content": "..."} lines
              ending with data: {"type": "done"}
"""
from __future__ import annotations

import json
import asyncio
from typing import Any

import aiohttp


class CopilotRelayOracle:
    """Oracle that scores architecture extractions via copilot-relay."""

    def __init__(self, host: str = "http://localhost:8400", timeout: float = 180.0):
        self._host = host
        self._timeout = timeout

    async def generate(self, system: str, user: str) -> str:
        """Send a prompt to copilot-relay and return the full response.

        Compatible with Surrogate.generate_with_prompt(system, user) -> str.
        """
        timeout = aiohttp.ClientTimeout(total=self._timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            payload = {"content": user, "system": system}
            async with session.post(f"{self._host}/chat", json=payload) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"copilot-relay returned {resp.status}")

                chunks: list[str] = []
                async for line in resp.content:
                    decoded = line.decode("utf-8").strip()
                    if not decoded.startswith("data: "):
                        continue
                    data = json.loads(decoded[6:])
                    if data.get("type") == "chunk":
                        chunks.append(data.get("content", ""))
                    elif data.get("type") == "done":
                        break
                    elif data.get("type") == "error":
                        raise RuntimeError(f"copilot-relay error: {data}")

                return "".join(chunks)

    async def score_extraction(
        self,
        model_yaml: str,
        source_code: str,
        scoring_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Score an architecture extraction against source code.

        Returns: {"score": int (0-100), "feedback": str}
        """
        system = scoring_prompt or (
            "You are an architecture extraction quality scorer. "
            "Score the given YAML architecture model against the source code on a scale of 0-100. "
            "Return ONLY a JSON object: {\"score\": <int>, \"feedback\": \"<brief explanation>\"}"
        )
        user = (
            f"## Architecture Model (YAML)\n```yaml\n{model_yaml}\n```\n\n"
            f"## Source Code\n```python\n{source_code[:8000]}\n```\n\n"
            "Score this extraction for completeness, accuracy, and structural correctness."
        )

        raw = await self.generate(system, user)

        # Parse JSON from response (may have markdown fences)
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"score": 0, "feedback": f"Failed to parse oracle response: {text[:200]}"}
```

**Step 4: Run tests**

```bash
pytest tests/test_oracle.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add . && git commit -m "feat: add copilot-relay oracle adapter with SSE parsing and scoring"
```

---

## Task 6: Implement MCP Server with architect_extract Tool

**Files:**
- Create: `~/Documents/Projects/opencode-arch/src/opencode_arch/mcp/server.py`
- Create: `~/Documents/Projects/opencode-arch/src/opencode_arch/mcp/tools/extract.py`
- Test: `~/Documents/Projects/opencode-arch/tests/test_mcp_extract.py`

**Step 1: Write failing test**

```python
# tests/test_mcp_extract.py
"""Tests for the architect_extract MCP tool."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from opencode_arch.mcp.tools.extract import extract_architecture


class TestExtractTool:
    @pytest.mark.asyncio
    async def test_extract_returns_yaml(self):
        """Extract should return a YAML architecture model string."""
        mock_surrogate = AsyncMock()
        mock_surrogate.generate.return_value = (
            "entities:\n"
            "  - id: CAP-F1\n"
            "    type: capability\n"
            "    name: Core\n"
        )

        with patch("opencode_arch.mcp.tools.extract._get_surrogate", return_value=mock_surrogate):
            result = await extract_architecture(
                repo_path="/tmp/test-repo",
                focus="all"
            )
            assert "entities:" in result
            assert "CAP-F1" in result

    @pytest.mark.asyncio
    async def test_extract_with_focus_layer(self):
        """Extract with focus should limit scope."""
        mock_surrogate = AsyncMock()
        mock_surrogate.generate.return_value = "entities:\n  - id: COMP-1\n    type: component\n"

        with patch("opencode_arch.mcp.tools.extract._get_surrogate", return_value=mock_surrogate):
            result = await extract_architecture(
                repo_path="/tmp/test-repo",
                focus="data-layer"
            )
            assert "entities:" in result

    @pytest.mark.asyncio
    async def test_extract_error_handling(self):
        """Extract should return error message on failure."""
        mock_surrogate = AsyncMock()
        mock_surrogate.generate.side_effect = RuntimeError("Model unavailable")

        with patch("opencode_arch.mcp.tools.extract._get_surrogate", return_value=mock_surrogate):
            result = await extract_architecture(repo_path="/tmp/nonexistent")
            assert "error" in result.lower() or "Error" in result
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_mcp_extract.py -v
```

**Step 3: Write implementation**

```python
# src/opencode_arch/mcp/__init__.py
"""MCP server for architecture tools."""
```

```python
# src/opencode_arch/mcp/tools/__init__.py
"""MCP tool implementations."""
```

```python
# src/opencode_arch/mcp/tools/extract.py
"""architect_extract MCP tool — extract architecture from source code."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from architecture_model.manifest.generator import generate_manifest


async def _get_surrogate():
    """Get the configured surrogate model for extraction.

    Tries Ollama first (local), falls back to returning None (uses manifest-only).
    """
    try:
        from arch_agent.training.surrogate import Surrogate
        return Surrogate(model="qwen2.5:7b")
    except ImportError:
        return None


async def extract_architecture(
    repo_path: str,
    focus: str = "all",
) -> str:
    """Extract architecture model from a repository.

    Args:
        repo_path: Path to the repository root.
        focus: Focus scope - "all", a layer name, or a component pattern.

    Returns:
        YAML string of the extracted architecture model.
    """
    path = Path(repo_path)
    if not path.exists():
        return f"Error: Repository path does not exist: {repo_path}"

    try:
        # Step 1: Generate reality manifest (AST scan)
        manifest = generate_manifest(str(path))

        # Step 2: Use surrogate model to synthesize architecture from manifest
        surrogate = await _get_surrogate()
        if surrogate is None:
            # Fallback: return manifest as basic YAML structure
            import yaml
            return yaml.dump(manifest, default_flow_style=False)

        # Build prompt from manifest
        system = (
            "You are an architecture extraction engine. Given a code manifest, "
            "produce a YAML architecture model following the 7-entity, 8-relationship schema. "
            "Entities: actors, capabilities, behaviors, interfaces, constraints, layers, components. "
            "Output ONLY valid YAML."
        )

        import yaml
        manifest_text = yaml.dump(manifest, default_flow_style=False)
        user = f"Extract architecture from this manifest:\n\n```yaml\n{manifest_text[:12000]}\n```"

        if focus != "all":
            user += f"\n\nFocus specifically on: {focus}"

        result = await surrogate.generate(system, user)

        # Strip markdown fences if present
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0]

        return result.strip()

    except Exception as e:
        return f"Error during extraction: {e}"
```

```python
# src/opencode_arch/mcp/server.py
"""FastMCP server entry point for opencode-arch."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from opencode_arch.mcp.tools.extract import extract_architecture

# Create the MCP server
mcp = FastMCP("opencode-arch", description="Architecture extraction, generation, and validation tools")


@mcp.tool()
async def architect_extract(repo_path: str, focus: str = "all") -> str:
    """Extract architecture model from a repository.

    Scans source code via AST analysis, generates a reality manifest,
    then synthesizes a YAML architecture model using the surrogate model.

    Args:
        repo_path: Absolute path to the repository root.
        focus: Scope - "all" for full extraction, or a layer/component name to focus on.
    """
    return await extract_architecture(repo_path=repo_path, focus=focus)
```

**Step 4: Run tests**

```bash
pip install -e ".[dev]"
pytest tests/test_mcp_extract.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add . && git commit -m "feat: add architect_extract MCP tool with surrogate integration"
```

---

## Task 7: Implement architect_validate MCP Tool

**Files:**
- Create: `~/Documents/Projects/opencode-arch/src/opencode_arch/mcp/tools/validate.py`
- Test: `~/Documents/Projects/opencode-arch/tests/test_mcp_validate.py`

**Step 1: Write failing test**

```python
# tests/test_mcp_validate.py
"""Tests for the architect_validate MCP tool."""
import pytest
from unittest.mock import patch, AsyncMock

from opencode_arch.mcp.tools.validate import validate_architecture


VALID_YAML = """
schema_version: "1.3"
entities:
  - id: CAP-F1
    type: capability
    name: Core Processing
    status: ACTIVE
  - id: COMP-1
    type: component
    name: Processor
    status: ACTIVE
relationships:
  - source: COMP-1
    target: CAP-F1
    type: realizes
"""

INVALID_YAML = """
schema_version: "1.3"
entities:
  - id: CAP-F1
    type: capability
    name: Core Processing
relationships:
  - source: COMP-MISSING
    target: CAP-F1
    type: realizes
"""


class TestValidateTool:
    @pytest.mark.asyncio
    async def test_validate_valid_model(self):
        result = await validate_architecture(model_yaml=VALID_YAML)
        assert "score" in result
        assert result["score"] >= 80

    @pytest.mark.asyncio
    async def test_validate_orphaned_reference(self):
        result = await validate_architecture(model_yaml=INVALID_YAML)
        assert result["score"] < 100
        assert len(result.get("issues", [])) > 0

    @pytest.mark.asyncio
    async def test_validate_with_oracle_scoring(self):
        mock_oracle = AsyncMock()
        mock_oracle.score_extraction.return_value = {"score": 92, "feedback": "Excellent"}

        with patch("opencode_arch.mcp.tools.validate._get_oracle", return_value=mock_oracle):
            result = await validate_architecture(
                model_yaml=VALID_YAML,
                source_code="def process(): pass",
                use_oracle=True,
            )
            assert "oracle_score" in result
            assert result["oracle_score"] == 92
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_mcp_validate.py -v
```

**Step 3: Write implementation**

```python
# src/opencode_arch/mcp/tools/validate.py
"""architect_validate MCP tool — validate architecture model quality."""
from __future__ import annotations

from typing import Any

import yaml

from architecture_model.core.validator import validate_model
from architecture_model.core.parser import parse_model


async def _get_oracle():
    """Get the oracle for quality scoring (optional)."""
    try:
        from opencode_arch.oracle.copilot_relay import CopilotRelayOracle
        return CopilotRelayOracle()
    except Exception:
        return None


async def validate_architecture(
    model_yaml: str,
    source_code: str | None = None,
    use_oracle: bool = False,
) -> dict[str, Any]:
    """Validate an architecture model for structural correctness.

    Args:
        model_yaml: The YAML architecture model string to validate.
        source_code: Optional source code to validate against (enables oracle scoring).
        use_oracle: Whether to use frontier model for quality scoring.

    Returns:
        Dict with score (0-100), issues list, and optionally oracle_score.
    """
    try:
        model = parse_model(model_yaml)
        validation_result = validate_model(model)

        result: dict[str, Any] = {
            "score": validation_result.score,
            "issues": [str(issue) for issue in validation_result.issues],
            "entity_count": len(model.get("entities", [])),
            "relationship_count": len(model.get("relationships", [])),
        }

        # Optional oracle scoring against source code
        if use_oracle and source_code:
            oracle = await _get_oracle()
            if oracle:
                oracle_result = await oracle.score_extraction(
                    model_yaml=model_yaml,
                    source_code=source_code,
                )
                result["oracle_score"] = oracle_result.get("score", 0)
                result["oracle_feedback"] = oracle_result.get("feedback", "")

        return result

    except Exception as e:
        return {"score": 0, "issues": [f"Parse/validation error: {e}"], "entity_count": 0, "relationship_count": 0}
```

**Step 4: Register in MCP server**

Add to `src/opencode_arch/mcp/server.py`:

```python
from opencode_arch.mcp.tools.validate import validate_architecture


@mcp.tool()
async def architect_validate(model_yaml: str, source_code: str = "", use_oracle: bool = False) -> dict:
    """Validate an architecture model for structural correctness.

    Checks entity/relationship integrity, orphaned references, and optionally
    scores quality against source code using the frontier model oracle.

    Args:
        model_yaml: YAML architecture model string.
        source_code: Optional source code to validate extraction against.
        use_oracle: Whether to use copilot-relay for quality scoring.
    """
    return await validate_architecture(
        model_yaml=model_yaml,
        source_code=source_code or None,
        use_oracle=use_oracle,
    )
```

**Step 5: Run tests**

```bash
pytest tests/test_mcp_validate.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add . && git commit -m "feat: add architect_validate MCP tool with optional oracle scoring"
```

---

## Task 8: Create Extraction Skill

**Files:**
- Create: `~/Documents/Projects/opencode-arch/skills/extraction/SKILL.md`

**Step 1: Write the skill definition**

```markdown
# Skill: Architecture Extraction

## When to Use
Use when the user asks to extract, document, or analyze the architecture of a codebase.

## Workflow

1. **Identify target**: Determine the repo path and any focus area (layer, component, feature).

2. **Run extraction**: Call the `architect_extract` tool:
   - `repo_path`: The absolute path to the repository
   - `focus`: "all" for full extraction, or specify a layer/component name

3. **Validate result**: Call `architect_validate` with the extracted YAML:
   - Check structural score (target: 80+)
   - Review any issues flagged

4. **Present to user**: Show the extracted model with:
   - Entity summary (count by type)
   - Key relationships
   - Any validation issues to address

5. **Offer refinement**: Ask if the user wants to:
   - Focus on a specific layer or component
   - Add missing entities or relationships
   - Save as `.architecture-model.yaml`

## Notes
- Extraction quality improves over time (self-learning loop)
- For large repos, focus on one layer at a time
- The oracle scorer provides quality feedback when available
```

**Step 2: Commit**

```bash
git add . && git commit -m "feat: add extraction workflow skill"
```

---

## Task 9: Clean Up architecture-model-standard

**Files:**
- Remove: `src/architecture_model/training/` (39 files)
- Remove: `tests/test_training/` (42 files)
- Modify: `pyproject.toml` — remove training extras, bump version
- Modify: `src/architecture_model/cli/train.py` — remove or stub
- Modify: `src/architecture_model/cli/generate.py` — remove training imports

**Step 1: Remove training directory**

```bash
cd ~/Documents/Projects/architecture-model-standard
rm -rf src/architecture_model/training
rm -rf tests/test_training
```

**Step 2: Update pyproject.toml**

Remove the `[project.optional-dependencies] training = [...]` section. Bump version to 0.4.0.

```toml
[project]
name = "architecture-model-standard"
version = "0.4.0"
description = "Universal machine-readable YAML architecture model for LLM-driven system engineering"
requires-python = ">=3.11"
dependencies = ["pyyaml>=6.0"]
license = "MIT"

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21"]
```

**Step 3: Stub CLI train command**

Replace `src/architecture_model/cli/train.py` with:

```python
"""Training CLI commands — moved to arch-agent package."""


def register_train_commands(subparsers):
    """Register training subcommands (stub — see arch-agent package)."""
    parser = subparsers.add_parser(
        "train",
        help="Training commands (moved to arch-agent package)"
    )
    parser.set_defaults(func=_train_stub)


def _train_stub(args):
    print("Training commands have moved to the arch-agent package.")
    print("Install: pip install arch-agent")
    print("Run: arch-agent train --help")
```

**Step 4: Update CLI generate command**

Remove any imports from `architecture_model.training` in `src/architecture_model/cli/generate.py`. Replace with a stub that points to opencode-arch.

**Step 5: Run remaining tests**

```bash
pytest tests/ -x -q
```

Expected: All non-training tests pass (the core schema/validator/manifest tests).

**Step 6: Commit**

```bash
git add -A && git commit -m "refactor: remove training/ (moved to arch-agent), bump to v0.4.0"
```

---

## Task 10: Integration Test — Full Loop

**Files:**
- Create: `~/Documents/Projects/opencode-arch/tests/test_integration.py`

**Step 1: Write integration test**

```python
# tests/test_integration.py
"""Integration test: extract → validate → score loop."""
import pytest
from unittest.mock import patch, AsyncMock

from opencode_arch.mcp.tools.extract import extract_architecture
from opencode_arch.mcp.tools.validate import validate_architecture


@pytest.mark.asyncio
async def test_extract_then_validate_loop():
    """Full loop: extract architecture from a repo, then validate it."""
    mock_surrogate = AsyncMock()
    mock_surrogate.generate.return_value = (
        "schema_version: '1.3'\n"
        "entities:\n"
        "  - id: CAP-F1\n"
        "    type: capability\n"
        "    name: Configuration\n"
        "    status: ACTIVE\n"
        "  - id: COMP-1\n"
        "    type: component\n"
        "    name: ConfigLoader\n"
        "    status: ACTIVE\n"
        "relationships:\n"
        "  - source: COMP-1\n"
        "    target: CAP-F1\n"
        "    type: realizes\n"
    )

    with patch("opencode_arch.mcp.tools.extract._get_surrogate", return_value=mock_surrogate):
        # Step 1: Extract
        yaml_result = await extract_architecture(repo_path="/tmp/test-repo")
        assert "entities:" in yaml_result

        # Step 2: Validate
        validation = await validate_architecture(model_yaml=yaml_result)
        assert validation["score"] >= 80
        assert validation["entity_count"] == 2
        assert validation["relationship_count"] == 1


@pytest.mark.asyncio
async def test_extract_validate_with_oracle():
    """Full loop with oracle scoring."""
    mock_surrogate = AsyncMock()
    mock_surrogate.generate.return_value = (
        "schema_version: '1.3'\n"
        "entities:\n"
        "  - id: COMP-1\n"
        "    type: component\n"
        "    name: App\n"
        "    status: ACTIVE\n"
        "relationships: []\n"
    )
    mock_oracle = AsyncMock()
    mock_oracle.score_extraction.return_value = {"score": 75, "feedback": "Missing capabilities"}

    with patch("opencode_arch.mcp.tools.extract._get_surrogate", return_value=mock_surrogate):
        yaml_result = await extract_architecture(repo_path="/tmp/test-repo")

    with patch("opencode_arch.mcp.tools.validate._get_oracle", return_value=mock_oracle):
        validation = await validate_architecture(
            model_yaml=yaml_result,
            source_code="class App: pass",
            use_oracle=True,
        )
        assert "oracle_score" in validation
        assert validation["oracle_score"] == 75
```

**Step 2: Run integration tests**

```bash
cd ~/Documents/Projects/opencode-arch
pytest tests/test_integration.py -v
```

Expected: PASS

**Step 3: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass.

**Step 4: Commit**

```bash
git add . && git commit -m "test: add integration tests for extract → validate → score loop"
```

---

## Task 11: Create GitHub Repos and Push

**Step 1: Push arch-agent**

```bash
cd ~/Documents/Projects/arch-agent
git -c http.proxy="" -c https.proxy="" remote add origin git@github.com:anomalyco/arch-agent.git
git -c http.proxy="" -c https.proxy="" push -u origin main
```

**Step 2: Push opencode-arch**

```bash
cd ~/Documents/Projects/opencode-arch
git -c http.proxy="" -c https.proxy="" remote add origin git@github.com:anomalyco/opencode-arch.git
git -c http.proxy="" -c https.proxy="" push -u origin main
```

**Step 3: Push architecture-model-standard update**

```bash
cd ~/Documents/Projects/architecture-model-standard
git -c http.proxy="" -c https.proxy="" push origin main
```

---

## Summary

| Task | Repo | Deliverable |
|------|------|-------------|
| 1-3 | arch-agent | Scaffold + 39 training modules + CLI |
| 4-8 | opencode-arch | MCP server + oracle + extract + validate + skill |
| 9 | architecture-model-standard | Remove training/, bump v0.4.0 |
| 10 | opencode-arch | Integration tests proving the loop works |
| 11 | All | Push to GitHub |

**Phase 1 proves:** User extracts architecture via OpenCode → quality is scored → model improves over time.
