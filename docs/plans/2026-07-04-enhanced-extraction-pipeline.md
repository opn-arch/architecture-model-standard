# Enhanced Extraction Pipeline — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a multi-pass, AST-guided extraction pipeline that produces near-perfect architecture models from large codebases by combining smart context selection, hierarchical extraction, and iterative refinement.

**Architecture:** Three new modules in `src/architecture_model/training/`: `context_builder.py` (AST-guided code context), `multi_pass.py` (5-pass hierarchical extraction), `refiner.py` (validator-feedback refinement loop). Integrated into the existing pipeline via an `EnhancedExtractor` facade.

**Tech Stack:** Python 3.11+, ast module, existing manifest scanner, existing validator, aiohttp (Ollama) / litellm (oracle)

**Test command:** `pytest tests/test_training/ --tb=short -q`

**Design doc:** Approved in conversation (2026-07-04 session)

---

## Prerequisites

These modules depend on the training package (Tasks 1-10, already committed). No new external dependencies needed — just `ast` stdlib + existing package internals.

---

### Task 1: ContextBuilder (`context_builder.py`)

AST-guided smart context selection that produces structured slices for each extraction pass.

**Files:**
- Create: `src/architecture_model/training/context_builder.py`
- Create: `tests/test_training/test_context_builder.py`

**Step 1: Write failing tests**

```python
"""Tests for AST-guided context builder."""
import pytest
from pathlib import Path
from architecture_model.training.context_builder import ContextBuilder, ContextSlices


@pytest.fixture
def sample_repo(tmp_path):
    """Create a minimal repo structure for testing."""
    # Create package structure
    (tmp_path / "src" / "myapp").mkdir(parents=True)
    (tmp_path / "src" / "myapp" / "__init__.py").write_text("")
    (tmp_path / "src" / "myapp" / "api").mkdir()
    (tmp_path / "src" / "myapp" / "api" / "__init__.py").write_text(
        "from django.urls import path\n"
    )
    (tmp_path / "src" / "myapp" / "api" / "views.py").write_text(
        "from rest_framework.views import APIView\n\n"
        "class UserEndpoint(APIView):\n"
        "    def get(self, request): pass\n"
    )
    (tmp_path / "src" / "myapp" / "models").mkdir()
    (tmp_path / "src" / "myapp" / "models" / "__init__.py").write_text("")
    (tmp_path / "src" / "myapp" / "models" / "user.py").write_text(
        "from django.db import models\n\n"
        "class User(models.Model):\n"
        "    name = models.CharField(max_length=100)\n"
    )
    (tmp_path / "src" / "myapp" / "tasks.py").write_text(
        "from celery import shared_task\n\n"
        "@shared_task\n"
        "def send_email(user_id: int): pass\n"
    )
    (tmp_path / "src" / "myapp" / "services").mkdir()
    (tmp_path / "src" / "myapp" / "services" / "__init__.py").write_text("")
    (tmp_path / "src" / "myapp" / "services" / "email.py").write_text(
        "class EmailService:\n"
        "    def send(self, to: str, body: str): pass\n"
    )
    (tmp_path / "src" / "myapp" / "wsgi.py").write_text(
        "from django.core.wsgi import get_wsgi_application\n"
        "application = get_wsgi_application()\n"
    )
    (tmp_path / "src" / "myapp" / "settings.py").write_text(
        "DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql'}}\n"
        "CACHES = {'default': {'BACKEND': 'django_redis.cache.RedisCache'}}\n"
        "CELERY_BROKER_URL = 'redis://localhost:6379'\n"
    )
    return tmp_path / "src" / "myapp"


class TestContextSlices:
    def test_slices_has_required_fields(self):
        """ContextSlices has all 5 pass-specific slices."""
        slices = ContextSlices(
            structure="dir tree",
            boundaries="api endpoints",
            behavior="tasks and workflows",
            relationships="import graph",
            constraints="configs",
        )
        assert slices.structure
        assert slices.boundaries
        assert slices.behavior
        assert slices.relationships
        assert slices.constraints

    def test_slices_combined(self):
        """combined() returns all slices joined."""
        slices = ContextSlices(
            structure="A", boundaries="B", behavior="C",
            relationships="D", constraints="E",
        )
        combined = slices.combined()
        assert "A" in combined and "E" in combined


class TestContextBuilder:
    def test_init(self, sample_repo):
        """ContextBuilder accepts repo path and max_chars."""
        cb = ContextBuilder(sample_repo, max_chars=10000)
        assert cb.repo_path == sample_repo

    def test_build_returns_slices(self, sample_repo):
        """build() returns a ContextSlices object."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()
        assert isinstance(slices, ContextSlices)

    def test_structure_slice_contains_dir_tree(self, sample_repo):
        """Structure slice includes directory listing."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()
        assert "api" in slices.structure
        assert "models" in slices.structure
        assert "services" in slices.structure

    def test_boundaries_slice_finds_api_classes(self, sample_repo):
        """Boundaries slice identifies API endpoint classes."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()
        assert "UserEndpoint" in slices.boundaries or "APIView" in slices.boundaries

    def test_behavior_slice_finds_tasks(self, sample_repo):
        """Behavior slice identifies async tasks."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()
        assert "send_email" in slices.behavior or "shared_task" in slices.behavior

    def test_constraints_slice_finds_config(self, sample_repo):
        """Constraints slice identifies infrastructure from config."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()
        assert "postgresql" in slices.constraints.lower() or "DATABASES" in slices.constraints

    def test_relationships_slice_has_imports(self, sample_repo):
        """Relationships slice includes import graph info."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()
        assert "import" in slices.relationships.lower() or "depends" in slices.relationships.lower()

    def test_respects_max_chars(self, sample_repo):
        """Total context respects max_chars limit."""
        cb = ContextBuilder(sample_repo, max_chars=500)
        slices = cb.build()
        total = len(slices.combined())
        # Allow some overflow for headers but should be reasonable
        assert total < 2000  # 4x max_chars as upper bound
```

**Step 2: Run tests — expect FAIL**

```bash
pytest tests/test_training/test_context_builder.py -v
```

**Step 3: Implement `context_builder.py`**

```python
"""
ContextBuilder: AST-guided smart context selection for architecture extraction.

Scans a repository using AST analysis to identify architecturally significant
code and produces structured context slices for multi-pass extraction.
"""

from __future__ import annotations

import ast
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ContextSlices:
    """Structured code context for multi-pass extraction.
    
    Each slice is optimized for a specific extraction pass:
    - structure: directory tree, package structure, entry points
    - boundaries: API endpoints, external interfaces, actor touchpoints
    - behavior: tasks, event handlers, workflows, processing pipelines
    - relationships: import graph, dependency hotspots, cross-module calls
    - constraints: configs, decorators enforcing rules, settings
    """
    structure: str
    boundaries: str
    behavior: str
    relationships: str
    constraints: str

    def combined(self) -> str:
        """Return all slices combined into a single context string."""
        return "\n\n".join([
            self.structure, self.boundaries, self.behavior,
            self.relationships, self.constraints,
        ])


# Decorator patterns that signal architectural significance
_ARCH_DECORATORS = {
    # Task/worker patterns
    "shared_task", "task", "instrumented_task", "periodic_task",
    # API patterns
    "api_view", "action", "route", "endpoint",
    # Silo/deployment patterns
    "control_silo_endpoint", "region_silo_endpoint", "cell_silo_endpoint",
    # Django patterns
    "receiver", "csrf_exempt",
}

# Base classes that signal architectural boundaries
_ARCH_BASE_CLASSES = {
    # DRF
    "APIView", "ViewSet", "ModelViewSet", "GenericAPIView",
    # Django
    "Model", "View", "TemplateView",
    # Celery
    "Task",
    # Kafka/Stream
    "ProcessingStrategy", "ProcessingStrategyFactory", "StreamProcessor",
    # Custom service patterns
    "Service", "BaseService", "IntegrationInstallation",
}

# Config keys that reveal infrastructure
_INFRA_PATTERNS = [
    "DATABASES", "CACHES", "BROKER_URL", "CELERY_",
    "KAFKA_", "REDIS_", "ELASTICSEARCH_", "CLICKHOUSE_",
    "SENTRY_", "SECRET_KEY", "ALLOWED_HOSTS",
]


class ContextBuilder:
    """Builds architecturally-rich code context from a repository."""

    def __init__(self, repo_path: Path, max_chars: int = 15000) -> None:
        self.repo_path = Path(repo_path)
        self._max_chars = max_chars
        self._per_slice = max_chars // 5  # Budget per slice

    def build(self) -> ContextSlices:
        """Scan the repo and return structured context slices."""
        return ContextSlices(
            structure=self._build_structure_slice(),
            boundaries=self._build_boundaries_slice(),
            behavior=self._build_behavior_slice(),
            relationships=self._build_relationships_slice(),
            constraints=self._build_constraints_slice(),
        )

    def _build_structure_slice(self) -> str:
        """Directory tree + package structure + entry points."""
        parts = []

        # Directory tree (top-level packages with file counts)
        parts.append("# PACKAGE STRUCTURE")
        for item in sorted(self.repo_path.iterdir()):
            if item.name.startswith((".", "__pycache__")):
                continue
            if item.is_dir():
                py_count = len(list(item.rglob("*.py")))
                parts.append(f"  {item.name}/ ({py_count} .py files)")
            elif item.suffix == ".py":
                parts.append(f"  {item.name}")

        # Entry points
        for name in ["wsgi.py", "asgi.py", "app.py", "main.py", "__main__.py"]:
            path = self.repo_path / name
            if path.exists():
                parts.append(f"\n# ENTRY POINT: {name}")
                parts.append(path.read_text()[:self._per_slice // 4])

        # Top-level __init__.py (often reveals architecture)
        init_path = self.repo_path / "__init__.py"
        if init_path.exists():
            content = init_path.read_text()
            if len(content) > 50:  # Skip empty inits
                parts.append(f"\n# __init__.py (package API)")
                parts.append(content[:self._per_slice // 4])

        return self._truncate("\n".join(parts))

    def _build_boundaries_slice(self) -> str:
        """API endpoints, external interfaces, actor touchpoints."""
        parts = ["# EXTERNAL BOUNDARIES (APIs, interfaces, integration points)"]

        # Find API/endpoint files
        api_files = self._find_files_matching(
            patterns=["api", "endpoint", "views", "urls", "routes"],
            extensions=[".py"],
        )

        for f in api_files[:10]:
            tree = self._parse_ast(f)
            if tree is None:
                continue
            classes = self._extract_classes_with_bases(tree, _ARCH_BASE_CLASSES)
            if classes:
                rel = f.relative_to(self.repo_path)
                parts.append(f"\n# {rel}")
                for cls_name, bases, methods in classes:
                    parts.append(f"class {cls_name}({', '.join(bases)}):")
                    for m in methods[:5]:
                        parts.append(f"    def {m}")

        # Integration/webhook files
        integ_files = self._find_files_matching(
            patterns=["integration", "webhook", "client"],
            extensions=[".py"],
        )
        for f in integ_files[:5]:
            rel = f.relative_to(self.repo_path)
            content = f.read_text()[:400]
            if "class " in content or "def " in content:
                parts.append(f"\n# {rel}")
                parts.append(content)

        return self._truncate("\n".join(parts))

    def _build_behavior_slice(self) -> str:
        """Tasks, event handlers, workflows, processing pipelines."""
        parts = ["# BEHAVIORS (tasks, event handlers, workflows)"]

        # Find decorated functions (tasks, signals, etc.)
        for py_file in self._iter_py_files(max_files=100):
            tree = self._parse_ast(py_file)
            if tree is None:
                continue
            decorated = self._extract_decorated_functions(tree, _ARCH_DECORATORS)
            if decorated:
                rel = py_file.relative_to(self.repo_path)
                parts.append(f"\n# {rel}")
                for name, decorators, args in decorated:
                    dec_str = ", ".join(f"@{d}" for d in decorators)
                    parts.append(f"  {dec_str}")
                    parts.append(f"  def {name}({args})")

        # Task/consumer __init__.py files
        for dirname in ["tasks", "consumers", "workers", "handlers", "processors"]:
            init = self.repo_path / dirname / "__init__.py"
            if init.exists():
                content = init.read_text()[:600]
                if content.strip():
                    parts.append(f"\n# {dirname}/__init__.py")
                    parts.append(content)

        return self._truncate("\n".join(parts))

    def _build_relationships_slice(self) -> str:
        """Import graph hotspots and cross-module dependencies."""
        parts = ["# RELATIONSHIPS (import graph, dependencies)"]

        # Build import frequency map
        import_counts: Counter = Counter()
        all_imports: dict[str, list[str]] = {}  # file -> imports

        for py_file in self._iter_py_files(max_files=200):
            tree = self._parse_ast(py_file)
            if tree is None:
                continue
            imports = self._extract_imports(tree)
            rel = str(py_file.relative_to(self.repo_path))
            all_imports[rel] = imports
            for imp in imports:
                import_counts[imp] += 1

        # Most-imported modules (architectural hotspots)
        parts.append("\n# MOST-IMPORTED MODULES (dependency hotspots)")
        for module, count in import_counts.most_common(20):
            parts.append(f"  {module}: imported by {count} files")

        # Key file dependencies
        parts.append("\n# KEY FILE IMPORTS")
        important_files = sorted(all_imports.keys())[:30]
        for f in important_files:
            if all_imports[f]:
                parts.append(f"  {f} → {', '.join(all_imports[f][:5])}")

        return self._truncate("\n".join(parts))

    def _build_constraints_slice(self) -> str:
        """Configs, decorator patterns enforcing rules, settings."""
        parts = ["# CONSTRAINTS (configs, settings, architectural rules)"]

        # Settings/config files
        config_files = self._find_files_matching(
            patterns=["settings", "config", "conf"],
            extensions=[".py"],
        )
        for f in config_files[:5]:
            content = f.read_text()
            # Extract lines matching infrastructure patterns
            infra_lines = []
            for line in content.splitlines():
                if any(pat in line for pat in _INFRA_PATTERNS):
                    infra_lines.append(line.strip())
            if infra_lines:
                rel = f.relative_to(self.repo_path)
                parts.append(f"\n# {rel}")
                parts.append("\n".join(infra_lines[:20]))

        # Decorator usage summary (constraints/rules)
        constraint_decorators = {"login_required", "permission_required",
                                 "rate_limit", "silo_mode", "csrf_exempt",
                                 "transaction", "atomic"}
        for py_file in self._iter_py_files(max_files=100):
            tree = self._parse_ast(py_file)
            if tree is None:
                continue
            decorated = self._extract_decorated_functions(tree, constraint_decorators)
            if decorated:
                rel = py_file.relative_to(self.repo_path)
                parts.append(f"\n# {rel}")
                for name, decs, _ in decorated[:3]:
                    parts.append(f"  @{', @'.join(decs)} → {name}")

        return self._truncate("\n".join(parts))

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _iter_py_files(self, max_files: int = 100) -> list[Path]:
        """Iterate Python files in repo, prioritizing shallow files."""
        files = []
        for py in sorted(self.repo_path.rglob("*.py")):
            if "__pycache__" in str(py):
                continue
            files.append(py)
            if len(files) >= max_files:
                break
        return files

    def _find_files_matching(self, patterns: list[str], extensions: list[str]) -> list[Path]:
        """Find files whose path contains any of the patterns."""
        results = []
        for py in self.repo_path.rglob("*"):
            if py.suffix not in extensions:
                continue
            if "__pycache__" in str(py):
                continue
            name_lower = py.name.lower()
            path_lower = str(py.relative_to(self.repo_path)).lower()
            if any(p in name_lower or p in path_lower for p in patterns):
                results.append(py)
        return sorted(results)[:20]

    def _parse_ast(self, filepath: Path) -> ast.Module | None:
        """Parse a Python file's AST, returning None on failure."""
        try:
            source = filepath.read_text(encoding="utf-8")
            return ast.parse(source, filename=str(filepath))
        except (SyntaxError, UnicodeDecodeError, OSError):
            return None

    def _extract_classes_with_bases(
        self, tree: ast.Module, target_bases: set[str]
    ) -> list[tuple[str, list[str], list[str]]]:
        """Extract classes inheriting from target base classes."""
        results = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(base.attr)
            if any(b in target_bases for b in bases):
                methods = [
                    n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not n.name.startswith("_")
                ]
                results.append((node.name, bases, methods))
        return results

    def _extract_decorated_functions(
        self, tree: ast.Module, target_decorators: set[str]
    ) -> list[tuple[str, list[str], str]]:
        """Extract functions with specific decorators."""
        results = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            matched_decorators = []
            for dec in node.decorator_list:
                dec_name = None
                if isinstance(dec, ast.Name):
                    dec_name = dec.id
                elif isinstance(dec, ast.Attribute):
                    dec_name = dec.attr
                elif isinstance(dec, ast.Call):
                    if isinstance(dec.func, ast.Name):
                        dec_name = dec.func.id
                    elif isinstance(dec.func, ast.Attribute):
                        dec_name = dec.func.attr
                if dec_name and dec_name in target_decorators:
                    matched_decorators.append(dec_name)
            if matched_decorators:
                args = ", ".join(a.arg for a in node.args.args[:4])
                results.append((node.name, matched_decorators, args))
        return results

    def _extract_imports(self, tree: ast.Module) -> list[str]:
        """Extract top-level module imports."""
        imports = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    imports.append(top)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    imports.append(top)
        return list(set(imports))

    def _truncate(self, text: str) -> str:
        """Truncate text to per-slice budget."""
        if len(text) <= self._per_slice:
            return text
        return text[:self._per_slice] + "\n# ... (truncated)"
```

**Step 4: Run tests — all pass**

```bash
pytest tests/test_training/test_context_builder.py -v
```

**Step 5: Commit**

```bash
git add src/architecture_model/training/context_builder.py tests/test_training/test_context_builder.py
git commit -m "feat(training): add AST-guided context builder for smart code sampling"
```

---

### Task 2: MultiPassExtractor (`multi_pass.py`)

5-pass hierarchical extraction that builds the model incrementally.

**Files:**
- Create: `src/architecture_model/training/multi_pass.py`
- Create: `tests/test_training/test_multi_pass.py`

**Step 1: Write failing tests**

Tests mock the LLM client (surrogate or oracle) and verify:
- Each pass sends the correct context slice
- Each pass includes the partial model from previous passes
- Results are merged correctly into a complete model
- Pass-specific system prompts are used

```python
"""Tests for multi-pass hierarchical extraction."""
import pytest
from unittest.mock import AsyncMock, MagicMock
import yaml

from architecture_model.training.multi_pass import MultiPassExtractor, PassResult
from architecture_model.training.context_builder import ContextSlices
from architecture_model.core.types import ArchitectureModel, Entities, ModelMeta


@pytest.fixture
def context():
    return ContextSlices(
        structure="pkg: api/, models/, tasks/",
        boundaries="class UserAPI(APIView): ...",
        behavior="@task def send_email(): ...",
        relationships="api imports models, tasks imports services",
        constraints="DATABASES = {'default': ...}",
    )


@pytest.fixture
def mock_client():
    """Mock LLM client with _chat or _completion method."""
    client = MagicMock()
    client._chat = AsyncMock()
    return client


def _yaml_response(entities_yaml: str) -> dict:
    """Build mock Ollama response."""
    return {"message": {"content": entities_yaml}}


class TestMultiPassExtractor:
    def test_init(self, mock_client, context):
        """Accepts client and context slices."""
        mpe = MultiPassExtractor(mock_client, context, project_name="test")
        assert mpe._client is mock_client

    @pytest.mark.asyncio
    async def test_pass_structure_uses_structure_slice(self, mock_client, context):
        """Pass 1 sends structure slice with structure-specific prompt."""
        mock_client._chat.return_value = _yaml_response(
            "layers:\n  - id: L1\n    name: API\n    status: ACTIVE\n"
            "components:\n  - id: C1\n    name: api\n    status: ACTIVE\n    layer: L1"
        )
        mpe = MultiPassExtractor(mock_client, context, project_name="test")
        result = await mpe._pass_structure()
        # Verify structure slice was sent
        call_args = mock_client._chat.call_args[0][0]
        assert "PACKAGE STRUCTURE" in call_args[1]["content"] or "pkg:" in call_args[1]["content"]

    @pytest.mark.asyncio
    async def test_extract_produces_model(self, mock_client, context):
        """Full extract() returns an ArchitectureModel."""
        # Each pass returns a valid YAML fragment
        responses = [
            _yaml_response("layers:\n  - id: L1\n    name: Web\n    status: ACTIVE\ncomponents:\n  - id: C1\n    name: api\n    status: ACTIVE\n    layer: L1"),
            _yaml_response("actors:\n  - id: A1\n    name: User\n    status: ACTIVE\n    type: human\ninterfaces:\n  - id: I1\n    name: REST API\n    status: ACTIVE\n    type: rest"),
            _yaml_response("capabilities:\n  - id: CAP1\n    name: Auth\n    status: ACTIVE\nbehaviors:\n  - id: B1\n    name: Login\n    status: ACTIVE"),
            _yaml_response("relationships:\n  - type: depends-on\n    from: C1\n    to: A1"),
            _yaml_response("constraints:\n  - id: CON1\n    name: Rate Limit\n    status: ACTIVE"),
        ]
        mock_client._chat.side_effect = responses
        mpe = MultiPassExtractor(mock_client, context, project_name="test")
        model = await mpe.extract()
        assert isinstance(model, ArchitectureModel)
        assert len(model.entities.layers) >= 1
        assert len(model.entities.actors) >= 1
        assert len(model.entities.components) >= 1

    @pytest.mark.asyncio
    async def test_later_passes_include_prior_results(self, mock_client, context):
        """Pass 4 (relationships) receives entities from passes 1-3."""
        responses = [
            _yaml_response("layers:\n  - id: L1\n    name: Web\n    status: ACTIVE\ncomponents:\n  - id: C1\n    name: api\n    status: ACTIVE\n    layer: L1"),
            _yaml_response("actors:\n  - id: A1\n    name: User\n    status: ACTIVE\n    type: human\ninterfaces: []"),
            _yaml_response("capabilities: []\nbehaviors: []"),
            _yaml_response("relationships:\n  - type: depends-on\n    from: C1\n    to: A1"),
            _yaml_response("constraints: []"),
        ]
        mock_client._chat.side_effect = responses
        mpe = MultiPassExtractor(mock_client, context, project_name="test")
        await mpe.extract()
        # Pass 4 (relationships) should reference prior entities
        fourth_call = mock_client._chat.call_args_list[3][0][0]
        user_msg = fourth_call[1]["content"]
        assert "L1" in user_msg or "C1" in user_msg or "A1" in user_msg

    @pytest.mark.asyncio
    async def test_handles_parse_failure_gracefully(self, mock_client, context):
        """If a pass returns garbage, extraction still produces a partial model."""
        responses = [
            _yaml_response("layers:\n  - id: L1\n    name: Web\n    status: ACTIVE\ncomponents: []"),
            _yaml_response("NOT VALID YAML {{{"),  # Pass 2 fails
            _yaml_response("capabilities: []\nbehaviors: []"),
            _yaml_response("relationships: []"),
            _yaml_response("constraints: []"),
        ]
        mock_client._chat.side_effect = responses
        mpe = MultiPassExtractor(mock_client, context, project_name="test")
        model = await mpe.extract()
        # Should still return a model with pass 1 results
        assert model is not None
        assert len(model.entities.layers) >= 1
```

**Step 2: Run tests — expect FAIL**

**Step 3: Implement `multi_pass.py`**

Core logic:
- 5 passes, each with a focused system prompt
- Each pass receives: its context slice + partial model from prior passes
- YAML response parsed into entity lists, merged into final model
- Parse failures for individual passes don't crash the whole extraction

**Step 4: Run tests — all pass**

**Step 5: Commit**

```bash
git add src/architecture_model/training/multi_pass.py tests/test_training/test_multi_pass.py
git commit -m "feat(training): add multi-pass hierarchical extraction"
```

---

### Task 3: ModelRefiner (`refiner.py`)

Iterative refinement using validator feedback.

**Files:**
- Create: `src/architecture_model/training/refiner.py`
- Create: `tests/test_training/test_refiner.py`

**Step 1: Write failing tests**

```python
"""Tests for iterative model refinement."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import yaml

from architecture_model.training.refiner import ModelRefiner
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Actor, Status,
    Component, Layer, Relationship, RelationType,
)


def _make_model(actors=None, components=None, layers=None, relationships=None):
    """Build a minimal model."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="1.0", project="test"),
        entities=Entities(
            actors=actors or [],
            components=components or [],
            layers=layers or [],
        ),
        relationships=relationships or [],
    )


@pytest.fixture
def mock_client():
    client = MagicMock()
    client._chat = AsyncMock()
    return client


class TestModelRefiner:
    def test_init(self, mock_client):
        """Accepts client and max_rounds."""
        refiner = ModelRefiner(mock_client, max_rounds=3)
        assert refiner._max_rounds == 3

    @pytest.mark.asyncio
    async def test_no_refinement_needed_for_high_score(self, mock_client):
        """Model with score >= 95 is returned immediately without LLM calls."""
        model = _make_model(
            actors=[Actor(id="A1", name="User", status=Status.ACTIVE)],
            components=[Component(id="C1", name="API", status=Status.ACTIVE, layer="L1")],
            layers=[Layer(id="L1", name="Web", status=Status.ACTIVE)],
            relationships=[
                Relationship(type=RelationType.CONTAINS, source="L1", target="C1"),
            ],
        )
        refiner = ModelRefiner(mock_client, max_rounds=3)
        result = await refiner.refine(model, "some code context")
        # Should not call client since score is already high
        mock_client._chat.assert_not_called()
        assert result is model or result.entity_count >= model.entity_count

    @pytest.mark.asyncio
    async def test_refines_model_with_low_score(self, mock_client):
        """Model with orphaned entities gets refined."""
        # Orphaned component (no relationship to layer) → low score
        model = _make_model(
            components=[
                Component(id="C1", name="API", status=Status.ACTIVE, layer="L1"),
                Component(id="C2", name="DB", status=Status.ACTIVE, layer="L2"),
            ],
        )
        # Mock the refinement response
        mock_client._chat.return_value = {"message": {"content": (
            "layers:\n"
            "  - id: L1\n    name: Web\n    status: ACTIVE\n"
            "  - id: L2\n    name: Data\n    status: ACTIVE\n"
            "relationships:\n"
            "  - type: contains\n    from: L1\n    to: C1\n"
            "  - type: contains\n    from: L2\n    to: C2"
        )}}
        refiner = ModelRefiner(mock_client, max_rounds=3)
        result = await refiner.refine(model, "some code")
        # Should have called client at least once
        assert mock_client._chat.called
        # Result should have more relationships or entities
        assert result.relationship_count >= model.relationship_count or result.entity_count > model.entity_count

    @pytest.mark.asyncio
    async def test_respects_max_rounds(self, mock_client):
        """Stops after max_rounds even if score hasn't improved."""
        model = _make_model(
            components=[Component(id="C1", name="API", status=Status.ACTIVE, layer="L1")],
        )
        # Always return empty (won't improve score)
        mock_client._chat.return_value = {"message": {"content": "relationships: []"}}
        refiner = ModelRefiner(mock_client, max_rounds=2)
        await refiner.refine(model, "code")
        # Should have called at most max_rounds times
        assert mock_client._chat.call_count <= 2

    @pytest.mark.asyncio
    async def test_feedback_includes_validator_issues(self, mock_client):
        """The refinement prompt includes specific validator issues."""
        model = _make_model(
            components=[Component(id="C1", name="Orphan", status=Status.ACTIVE, layer="X")],
        )
        mock_client._chat.return_value = {"message": {"content": "relationships: []"}}
        refiner = ModelRefiner(mock_client, max_rounds=1)
        await refiner.refine(model, "code")
        # Check the prompt sent includes issue information
        call_args = mock_client._chat.call_args[0][0]
        user_msg = call_args[1]["content"]
        assert "orphan" in user_msg.lower() or "issue" in user_msg.lower() or "C1" in user_msg
```

**Step 2: Run tests — expect FAIL**

**Step 3: Implement `refiner.py`**

Core logic:
- Validate model → check score
- If score >= 95, return as-is
- Otherwise: identify issues, build refinement prompt with issues + code context
- LLM returns corrections (new entities/relationships)
- Merge corrections into model
- Repeat up to max_rounds

**Step 4: Run tests — all pass**

**Step 5: Commit**

```bash
git add src/architecture_model/training/refiner.py tests/test_training/test_refiner.py
git commit -m "feat(training): add iterative model refiner with validator feedback"
```

---

### Task 4: Pipeline Integration + `__init__.py` Update

Wire the enhanced extraction into the pipeline and expose via public API.

**Files:**
- Modify: `src/architecture_model/training/pipeline.py` (add enhanced extraction path)
- Modify: `src/architecture_model/training/__init__.py` (export new classes)
- Create: `tests/test_training/test_enhanced_extraction.py` (integration test)

**Step 1: Write integration test**

```python
"""Integration test for enhanced extraction pipeline."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from architecture_model.training.context_builder import ContextBuilder, ContextSlices
from architecture_model.training.multi_pass import MultiPassExtractor
from architecture_model.training.refiner import ModelRefiner


@pytest.fixture
def sample_repo(tmp_path):
    """Minimal repo for integration testing."""
    pkg = tmp_path / "myapp"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "api.py").write_text(
        "from rest_framework.views import APIView\n"
        "class UserView(APIView):\n"
        "    def get(self, request): pass\n"
    )
    (pkg / "models.py").write_text(
        "from django.db import models\n"
        "class User(models.Model):\n"
        "    name = models.CharField(max_length=100)\n"
    )
    (pkg / "tasks.py").write_text(
        "from celery import shared_task\n"
        "@shared_task\n"
        "def notify(user_id): pass\n"
    )
    return pkg


class TestEnhancedExtraction:
    def test_context_builder_produces_slices(self, sample_repo):
        """ContextBuilder produces non-empty slices for a real repo."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()
        assert len(slices.structure) > 0
        assert len(slices.combined()) > 100

    @pytest.mark.asyncio
    async def test_full_pipeline_context_to_model(self, sample_repo):
        """End-to-end: context → multi-pass → model."""
        cb = ContextBuilder(sample_repo)
        slices = cb.build()

        mock_client = MagicMock()
        mock_client._chat = AsyncMock(side_effect=[
            {"message": {"content": "layers:\n  - id: L1\n    name: Web\n    status: ACTIVE\ncomponents:\n  - id: C1\n    name: api\n    status: ACTIVE\n    layer: L1"}},
            {"message": {"content": "actors:\n  - id: A1\n    name: User\n    status: ACTIVE\n    type: human\ninterfaces: []"}},
            {"message": {"content": "capabilities:\n  - id: CAP1\n    name: CRUD\n    status: ACTIVE\nbehaviors: []"}},
            {"message": {"content": "relationships:\n  - type: contains\n    from: L1\n    to: C1"}},
            {"message": {"content": "constraints: []"}},
        ])

        extractor = MultiPassExtractor(mock_client, slices, project_name="test")
        model = await extractor.extract()
        assert model is not None
        assert model.entity_count >= 3  # At least layer + component + actor
```

**Step 2: Add to pipeline.py**

Add an `enhanced_extract` method to `TrainingPipeline` that uses the new modules:

```python
async def _enhanced_extract(self, repo_path: Path) -> tuple[ArchitectureModel | None, float]:
    """Enhanced extraction: context_builder → multi_pass → refiner."""
    from .context_builder import ContextBuilder
    from .multi_pass import MultiPassExtractor
    from .refiner import ModelRefiner

    # Build smart context
    cb = ContextBuilder(repo_path)
    slices = cb.build()

    # Multi-pass extraction
    extractor = MultiPassExtractor(self._surrogate, slices, project_name=repo_path.name)
    model = await extractor.extract()
    if model is None:
        return None, 0.0

    # Refine with validator feedback
    refiner = ModelRefiner(self._surrogate, max_rounds=2)
    model = await refiner.refine(model, slices.combined())

    confidence = self._surrogate.confidence(model)
    return model, confidence
```

**Step 3: Update `__init__.py`**

Add exports:
```python
from architecture_model.training.context_builder import ContextBuilder, ContextSlices
from architecture_model.training.multi_pass import MultiPassExtractor
from architecture_model.training.refiner import ModelRefiner
```

**Step 4: Run full test suite**

```bash
pytest tests/test_training/ --tb=short -q
```

**Step 5: Commit**

```bash
git add src/architecture_model/training/ tests/test_training/
git commit -m "feat(training): integrate enhanced extraction into pipeline"
```

---

### Task 5: Sentry Integration Test Script

Update the test script to use the enhanced pipeline and compare results.

**Files:**
- Modify: `scripts/test_sentry.py` (add enhanced extraction path)

**Step 1: Add enhanced extraction to test script**

Run both the old (single-pass) and new (multi-pass + refine) approaches on Sentry, compare results side by side.

**Step 2: Run and capture results**

**Step 3: Commit**

```bash
git add scripts/test_sentry.py
git commit -m "test: update Sentry integration test with enhanced extraction"
```

---

## Implementation Order Rationale

```
Task 1: ContextBuilder    ← foundation, smart code sampling
Task 2: MultiPassExtractor ← uses ContextSlices from Task 1
Task 3: ModelRefiner       ← uses validator, independent of Task 2
Task 4: Integration        ← wires 1+2+3 into pipeline
Task 5: Test on Sentry     ← validates improvement
```

Tasks 1-3 are independently testable. Task 4 integrates. Task 5 validates on real data.
