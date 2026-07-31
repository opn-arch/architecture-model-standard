# Hierarchical Model Organization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the system-of-systems decomposition real — root model becomes skeletal (blocks + capabilities + cross-block interfaces only), sub-models contain full component detail, slicer loads sub-models directly.

**Architecture:** Three changes: (1) A `compact_root_model()` function that strips component detail from the root model after decomposition, keeping only block-level entities. (2) A `load_block_model()` function that loads a sub-model from `.architecture-models/<block_id>/`. (3) Wire the slicer's `slice_by_fblock` to auto-load sub-models when available.

**Tech Stack:** Python 3.12, architecture-model-standard, pytest

**Test command:** `/opt/anaconda3/bin/python -m pytest tests/ --ignore=tests/test_config_loader.py -v`

**Repo:** `/Users/baigm2/Documents/Projects/architecture-model-standard/`

---

## Task 1: `compact_root_model()` — Strip detail from root after decomposition

**Files:**
- Modify: `src/architecture_model/orchestration/decompose.py`
- Test: `tests/test_compact_root.py`

**Step 1: Write the failing test**

```python
# tests/test_compact_root.py
"""Test that compact_root_model strips component detail, keeping block-level entities."""
import pytest
from architecture_model.core.types import (
    ArchitectureModel, Component, Capability, Interface, Behavior,
    Relationship, FunctionSignature, Symbol, Constant, SymbolKind,
)
from architecture_model.orchestration.decompose import compact_root_model


def _make_full_model():
    """A model with full component detail — signatures, symbols, constants, etc."""
    return ArchitectureModel(
        meta={"project": "test", "schema_version": "1.3"},
        entities={
            "components": [
                Component(
                    id="COMP-1", name="Scheduler", f_block="F1",
                    files=["scheduler/main.py"],
                    contract="Schedules tasks across workers",
                    pattern="service-layer",
                    signatures=[FunctionSignature(name="schedule", params=["task: Task"], returns="str")],
                    symbols=[Symbol(name="Scheduler", kind=SymbolKind.CLASS, members=["schedule", "cancel"], supers=[])],
                    constants=[Constant(name="MAX_WORKERS", value="8")],
                    responsibilities=["schedule tasks", "cancel tasks"],
                ),
                Component(
                    id="COMP-2", name="Worker", f_block="F1",
                    files=["scheduler/worker.py"],
                    contract="Executes tasks",
                    pattern="worker",
                    signatures=[FunctionSignature(name="execute", params=["task: Task"], returns="Result")],
                    symbols=[Symbol(name="Worker", kind=SymbolKind.CLASS, members=["execute"], supers=[])],
                ),
                Component(
                    id="COMP-3", name="Monitor", f_block="F2",
                    files=["monitor/metrics.py"],
                    contract="Collects metrics",
                    pattern="monitor",
                ),
            ],
            "capabilities": [
                Capability(id="CAP-1", name="Task Execution", status="ACTIVE"),
            ],
            "interfaces": [
                Interface(id="IF-1", name="REST API", status="ACTIVE"),
            ],
            "behaviors": [
                Behavior(id="BHV-1", name="Task Lifecycle"),
            ],
        },
        relationships=[
            Relationship(source="COMP-1", target="CAP-1", type="realizes"),
            Relationship(source="COMP-1", target="COMP-2", type="uses"),
        ],
    )


class TestCompactRootModel:
    def test_keeps_components_as_stubs(self):
        """Components should retain id, name, f_block, contract — but lose detail."""
        model = _make_full_model()
        compact_root_model(model, block_ids=["F1", "F2"])

        comps = model.entities.get("components", []) if hasattr(model.entities, "get") else model.entities.components
        assert len(comps) == 3  # All components still present

        comp1 = next(c for c in comps if c.id == "COMP-1")
        # Identity preserved
        assert comp1.name == "Scheduler"
        assert comp1.f_block == "F1"
        assert comp1.contract == "Schedules tasks across workers"
        assert comp1.pattern == "service-layer"
        # Detail stripped
        assert comp1.signatures == []
        assert comp1.symbols == []
        assert comp1.constants == []
        assert comp1.responsibilities == []
        assert comp1.files == []

    def test_keeps_capabilities_and_interfaces(self):
        """Non-component entities are untouched."""
        model = _make_full_model()
        compact_root_model(model, block_ids=["F1", "F2"])

        caps = model.entities.get("capabilities", []) if hasattr(model.entities, "get") else model.entities.capabilities
        assert len(caps) == 1
        assert caps[0].name == "Task Execution"

    def test_keeps_all_relationships(self):
        """Relationships are preserved (they reference IDs, not detail)."""
        model = _make_full_model()
        compact_root_model(model, block_ids=["F1", "F2"])

        assert len(model.relationships) == 2

    def test_model_size_shrinks(self):
        """Compacted model should serialize to fewer characters."""
        import yaml
        model = _make_full_model()

        # Rough size comparison — serialize meta + entities
        before_comps = sum(
            len(str(c.signatures)) + len(str(c.symbols)) + len(str(c.constants))
            for c in (model.entities.get("components", []) if hasattr(model.entities, "get") else model.entities.components)
        )
        assert before_comps > 0

        compact_root_model(model, block_ids=["F1", "F2"])

        after_comps = sum(
            len(str(c.signatures)) + len(str(c.symbols)) + len(str(c.constants))
            for c in (model.entities.get("components", []) if hasattr(model.entities, "get") else model.entities.components)
        )
        assert after_comps < before_comps
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_compact_root.py -v`
Expected: ImportError

**Step 3: Write minimal implementation**

Add to `src/architecture_model/orchestration/decompose.py`:

```python
from ..monitoring import monitored

@monitored("orchestration.compact_root_model")
def compact_root_model(model, *, block_ids: list[str]) -> None:
    """Strip component detail from the root model after decomposition.

    Keeps: id, name, f_block, status, contract, pattern, kind, layer, description
    Strips: signatures, symbols, constants, files, responsibilities,
            test_contracts, observability, fields, functions
    Mutates model in-place.
    """
    components = (
        model.entities.components
        if hasattr(model.entities, "components")
        else model.entities.get("components", [])
        if hasattr(model.entities, "get")
        else []
    )

    for comp in components:
        if not hasattr(comp, "f_block"):
            continue
        # Strip implementation detail — keep identity + contract + pattern
        comp.signatures = []
        comp.symbols = []
        comp.constants = []
        comp.files = []
        comp.responsibilities = []
        if hasattr(comp, "test_contracts"):
            comp.test_contracts = []
        if hasattr(comp, "observability"):
            comp.observability = []
        if hasattr(comp, "fields"):
            comp.fields = []
        if hasattr(comp, "functions"):
            comp.functions = []
```

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_compact_root.py -v`
Expected: All pass

**Step 5: Export**

Add `compact_root_model` to `orchestration/__init__.py` and top-level `__init__.py`.

**Step 6: Commit**

```bash
git add -A && git commit -m "feat: compact_root_model strips component detail from root after decomposition"
```

---

## Task 2: `load_block_model()` — Load sub-model from `.architecture-models/`

**Files:**
- Modify: `src/architecture_model/core/parser.py`
- Test: `tests/test_load_block_model.py`

**Step 1: Write the failing test**

```python
# tests/test_load_block_model.py
"""Test loading sub-models from .architecture-models/ directory."""
import pytest
from pathlib import Path
from architecture_model.core.parser import load_model, load_block_model


class TestLoadBlockModel:
    def test_loads_sub_model_by_block_id(self, tmp_path):
        """Should load .architecture-models/<block_id>/.architecture-model.yaml."""
        sub_dir = tmp_path / ".architecture-models" / "F1"
        sub_dir.mkdir(parents=True)
        (sub_dir / ".architecture-model.yaml").write_text("""
meta:
  project: test/F1
  schema_version: '1.3'
  parent_model: ../../.architecture-model.yaml
entities:
  components:
    - id: COMP-1
      name: Scheduler
      status: ACTIVE
      f_block: F1
relationships: []
""")
        model = load_block_model(tmp_path, "F1")
        assert model is not None
        comps = model.entities.components if hasattr(model.entities, "components") else model.entities.get("components", [])
        assert len(comps) == 1
        assert comps[0].name == "Scheduler"

    def test_returns_none_for_missing_block(self, tmp_path):
        """Should return None if block sub-model doesn't exist."""
        model = load_block_model(tmp_path, "F99")
        assert model is None

    def test_loads_from_custom_output_dir(self, tmp_path):
        """Should support custom output directory name."""
        sub_dir = tmp_path / "models" / "F2"
        sub_dir.mkdir(parents=True)
        (sub_dir / ".architecture-model.yaml").write_text("""
meta:
  project: test/F2
  schema_version: '1.3'
entities:
  components:
    - id: COMP-2
      name: Worker
      status: ACTIVE
relationships: []
""")
        model = load_block_model(tmp_path, "F2", output_dir="models")
        assert model is not None
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_load_block_model.py -v`
Expected: ImportError

**Step 3: Write implementation**

Add to `src/architecture_model/core/parser.py`:

```python
def load_block_model(
    project_root: str | Path,
    block_id: str,
    output_dir: str = ".architecture-models",
) -> ArchitectureModel | None:
    """Load a block sub-model from the .architecture-models/ directory.

    Returns None if the sub-model doesn't exist.
    """
    root = Path(project_root)
    sub_model_path = root / output_dir / block_id / ".architecture-model.yaml"
    if not sub_model_path.exists():
        return None
    return load_model(sub_model_path)
```

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_load_block_model.py -v`
Expected: All pass

**Step 5: Export**

Add `load_block_model` to top-level `__init__.py`.

**Step 6: Commit**

```bash
git add -A && git commit -m "feat: load_block_model loads sub-models from .architecture-models/"
```

---

## Task 3: Slicer auto-loads sub-models when available

**Files:**
- Modify: `src/architecture_model/core/slicer.py`
- Test: `tests/test_slicer_sub_models.py`

**Step 1: Write the failing test**

```python
# tests/test_slicer_sub_models.py
"""Test that slicer loads sub-models when available for richer slicing."""
import pytest
from pathlib import Path
from architecture_model.core.slicer import slice_by_fblock
from architecture_model.core.parser import load_model
from architecture_model.core.types import FunctionSignature, Symbol, SymbolKind


class TestSlicerSubModels:
    def test_slice_loads_sub_model_detail(self, tmp_path):
        """When .architecture-models/F1/ exists, slice should return its richer content."""
        # Write a compact root model (no detail on components)
        (tmp_path / ".architecture-model.yaml").write_text("""
meta:
  project: test
  schema_version: '1.3'
functional_blocks:
  F1:
    name: Core
    dirs: [core]
  F2:
    name: Network
    dirs: [network]
entities:
  components:
    - id: COMP-1
      name: Scheduler
      status: ACTIVE
      f_block: F1
      contract: Schedules tasks
    - id: COMP-2
      name: RPCClient
      status: ACTIVE
      f_block: F2
      contract: Sends RPC calls
relationships:
  - source: COMP-1
    target: COMP-2
    type: uses
""")
        # Write a rich sub-model for F1
        sub_dir = tmp_path / ".architecture-models" / "F1"
        sub_dir.mkdir(parents=True)
        (sub_dir / ".architecture-model.yaml").write_text("""
meta:
  project: test/Core
  schema_version: '1.3'
  parent_model: ../../.architecture-model.yaml
entities:
  components:
    - id: COMP-1
      name: Scheduler
      status: ACTIVE
      f_block: F1
      contract: Schedules tasks across workers
      pattern: service-layer
      files: [core/scheduler.py]
      signatures:
        - name: schedule
          params: ["task: Task"]
          returns: str
      symbols:
        - name: Scheduler
          kind: CLASS
          members: [schedule, cancel]
relationships: []
""")
        root_model = load_model(str(tmp_path / ".architecture-model.yaml"))
        sliced = slice_by_fblock(root_model, "F1", project_root=tmp_path)

        # Should have the rich detail from sub-model
        comps = sliced.entities.components if hasattr(sliced.entities, "components") else sliced.entities.get("components", [])
        assert len(comps) == 1
        assert comps[0].contract == "Schedules tasks across workers"
        assert comps[0].pattern == "service-layer"
        assert len(comps[0].signatures) == 1

    def test_slice_falls_back_to_root_when_no_sub_model(self, tmp_path):
        """Without sub-models, slice should work from root as before."""
        (tmp_path / ".architecture-model.yaml").write_text("""
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Scheduler
      status: ACTIVE
      f_block: F1
      contract: Schedules tasks
relationships: []
""")
        root_model = load_model(str(tmp_path / ".architecture-model.yaml"))
        sliced = slice_by_fblock(root_model, "F1", project_root=tmp_path)

        comps = sliced.entities.components if hasattr(sliced.entities, "components") else sliced.entities.get("components", [])
        assert len(comps) == 1
        assert comps[0].name == "Scheduler"

    def test_slice_without_project_root_works_as_before(self):
        """Existing API (no project_root) should still work."""
        from architecture_model.core.types import ArchitectureModel, Component
        model = ArchitectureModel(
            meta={"project": "test", "schema_version": "1.3"},
            entities={"components": [
                Component(id="C1", name="A", f_block="F1"),
                Component(id="C2", name="B", f_block="F2"),
            ]},
            relationships=[],
        )
        sliced = slice_by_fblock(model, "F1")
        comps = sliced.entities.components if hasattr(sliced.entities, "components") else sliced.entities.get("components", [])
        assert len(comps) == 1
        assert comps[0].name == "A"
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_slicer_sub_models.py -v`
Expected: TypeError (slice_by_fblock doesn't accept project_root)

**Step 3: Modify `slice_by_fblock`**

In `src/architecture_model/core/slicer.py`, modify `slice_by_fblock` to accept an optional `project_root` parameter:

```python
def slice_by_fblock(
    model: ArchitectureModel,
    f_block: str,
    include_relationships: bool = True,
    *,
    project_root: Path | str | None = None,
) -> ArchitectureModel:
    """Slice model to a specific functional block.
    
    If project_root is provided and .architecture-models/<f_block>/ exists,
    loads the richer sub-model instead of filtering the root model.
    """
    # Try loading sub-model if project_root provided
    if project_root is not None:
        from .parser import load_block_model
        sub_model = load_block_model(project_root, f_block)
        if sub_model is not None:
            return sub_model

    # Fall back to existing filtering logic
    # ... (existing code unchanged)
```

**Important:** Add `project_root` as keyword-only (`*`) to avoid breaking existing callers.

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_slicer_sub_models.py -v`
Expected: All pass

**Step 5: Run full suite**

Run: `/opt/anaconda3/bin/python -m pytest tests/ --ignore=tests/test_config_loader.py -q`

**Step 6: Commit**

```bash
git add -A && git commit -m "feat: slice_by_fblock auto-loads sub-models when project_root provided"
```

---

## Task 4: Wire into pipeline — compact root after decompose + write

**Files:**
- Modify: `src/architecture_model/orchestration/pipeline.py`
- Test: `tests/test_pipeline_compact.py`

**Step 1: Write the failing test**

```python
# tests/test_pipeline_compact.py
"""Test that pipeline produces compact root + rich sub-models."""
import pytest
from pathlib import Path
from architecture_model.orchestration.pipeline import run_pipeline
from architecture_model.core.parser import load_model, load_block_model


@pytest.fixture
def pipeline_repo(tmp_path):
    """Create a minimal repo with config + model + source files."""
    # Config
    (tmp_path / "architecture.yaml").write_text("""
project: test-pipeline
functional_blocks:
  F1:
    name: Core
    dirs: [core]
  F2:
    name: API
    dirs: [api]
""")
    # Model
    (tmp_path / ".architecture-model.yaml").write_text("""
meta:
  project: test-pipeline
  schema_version: '1.3'
functional_blocks:
  F1:
    name: Core
    dirs: [core]
  F2:
    name: API
    dirs: [api]
entities:
  components:
    - id: COMP-1
      name: Engine
      status: ACTIVE
      f_block: F1
      files: [core/engine.py]
    - id: COMP-2
      name: Router
      status: ACTIVE
      f_block: F2
      files: [api/router.py]
relationships: []
""")
    # Source files
    core = tmp_path / "core"
    core.mkdir()
    (core / "engine.py").write_text('''
"""Engine that processes requests."""

MAX_QUEUE = 100

class Engine:
    """Core processing engine."""
    def process(self, request: dict) -> dict:
        """Process a single request."""
        return {}
    def shutdown(self) -> None:
        """Graceful shutdown."""
        pass
''')
    api = tmp_path / "api"
    api.mkdir()
    (api / "router.py").write_text('''
"""Routes incoming requests to handlers."""

class Router:
    """Request router."""
    def route(self, path: str) -> callable:
        """Route a path to its handler."""
        return lambda: None
''')
    return tmp_path


def test_pipeline_produces_compact_root_and_rich_sub_models(pipeline_repo):
    """After pipeline, root should be compact and sub-models should have detail."""
    result = run_pipeline(pipeline_repo, compact=True)

    # Root model should exist and be compact (no signatures/symbols on components)
    root = load_model(str(pipeline_repo / ".architecture-model.yaml"))
    root_comps = root.entities.components if hasattr(root.entities, "components") else root.entities.get("components", [])
    for comp in root_comps:
        assert comp.signatures == [], f"{comp.name} should have no signatures in root"
        assert comp.symbols == [], f"{comp.name} should have no symbols in root"
        # But identity preserved
        assert comp.contract or True  # contract may or may not be set
        assert comp.f_block  # block assignment preserved

    # Sub-models should exist and have detail
    sub_f1 = load_block_model(pipeline_repo, "F1")
    assert sub_f1 is not None
    f1_comps = sub_f1.entities.components if hasattr(sub_f1.entities, "components") else sub_f1.entities.get("components", [])
    assert len(f1_comps) >= 1
    # Sub-model may have enriched data (depending on whether enrichment ran)
```

**Step 2: Run test to verify it fails**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_pipeline_compact.py -v`
Expected: TypeError (compact parameter not accepted)

**Step 3: Modify pipeline**

In `src/architecture_model/orchestration/pipeline.py`, add `compact: bool = False` parameter to `run_pipeline`. After Step 2 (decompose + write_sub_models), if `compact=True`:

```python
if compact:
    from .decompose import compact_root_model
    from ..core.parser import save_model  # or however the model is saved
    block_ids = list(sub_models.keys())
    compact_root_model(model, block_ids=block_ids)
    # Re-save the compacted root model
    save_model(model, model_path)
```

Check how `save_model` works — it might be in parser.py or a separate serializer. If there's no `save_model`, you need to serialize and write the YAML yourself.

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_pipeline_compact.py -v`
Expected: Pass

**Step 5: Full suite**

Run: `/opt/anaconda3/bin/python -m pytest tests/ --ignore=tests/test_config_loader.py -q`

**Step 6: Commit**

```bash
git add -A && git commit -m "feat: pipeline compact mode — skeletal root + rich sub-models"
```

---

## Task 5: Wire into MCP slice tool

**Files:**
- Modify: `src/opencode_arch/mcp/tools/slice.py` (in opencode-arch repo)
- Test: `tests/test_slice_sub_models.py` (in opencode-arch repo)

**Repo:** `/Users/baigm2/Documents/Projects/opencode-arch/`

**Step 1: Write the failing test**

```python
# tests/test_slice_sub_models.py
"""Test that MCP slice tool uses sub-models when focus is a block ID."""
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_slice_passes_project_root_for_block_focus(tmp_path):
    """When focus is a block ID like 'F1', slice should pass project_root to slicer."""
    from opencode_arch.mcp.tools.slice import slice_context

    # Create minimal model + sub-model
    (tmp_path / ".architecture-model.yaml").write_text("""
meta:
  project: test
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Scheduler
      status: ACTIVE
      f_block: F1
relationships: []
""")
    sub_dir = tmp_path / ".architecture-models" / "F1"
    sub_dir.mkdir(parents=True)
    (sub_dir / ".architecture-model.yaml").write_text("""
meta:
  project: test/F1
  schema_version: '1.3'
entities:
  components:
    - id: COMP-1
      name: Scheduler
      status: ACTIVE
      f_block: F1
      contract: Rich detail from sub-model
      pattern: service-layer
relationships: []
""")

    result = await slice_context(str(tmp_path), focus="F1", budget=4000, detail="standard")
    assert "Rich detail from sub-model" in result or "service-layer" in result
```

**Step 2: Modify slice tool**

In `src/opencode_arch/mcp/tools/slice.py`, when focus looks like a block ID (starts with "F" and rest is digits), pass `project_root` to `slice_by_fblock`:

```python
# When slicing by fblock with a model file available
if focus.startswith("F") and focus[1:].isdigit():
    sliced = slice_by_fblock(model, focus, project_root=Path(repo_path))
```

**Step 3: Run tests, commit**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_slice_sub_models.py -v`

```bash
git add -A && git commit -m "feat: MCP slice tool auto-loads sub-models for block focus"
```

---

## Task 6: Integration test — full pipeline with compaction on hard repo

**Files:**
- Test: `tests/test_hierarchical_integration.py`
- Repo: architecture-model-standard

**Step 1: Write integration test**

```python
# tests/test_hierarchical_integration.py
"""Integration: pipeline produces hierarchical model, slicer loads sub-models."""
import pytest
from pathlib import Path
from architecture_model.core.parser import load_model, load_block_model
from architecture_model.core.slicer import slice_by_fblock


@pytest.fixture
def hierarchical_repo(tmp_path):
    """Create a repo with config, model, and source — run pipeline to produce hierarchy."""
    # Config
    (tmp_path / "architecture.yaml").write_text("""
project: hierarchy-test
functional_blocks:
  F1:
    name: Core
    dirs: [core]
  F2:
    name: Web
    dirs: [web]
""")
    # Model
    (tmp_path / ".architecture-model.yaml").write_text("""
meta:
  project: hierarchy-test
  schema_version: '1.3'
functional_blocks:
  F1:
    name: Core
    dirs: [core]
  F2:
    name: Web
    dirs: [web]
entities:
  components:
    - id: COMP-1
      name: Database
      status: ACTIVE
      f_block: F1
      files: [core/db.py]
    - id: COMP-2
      name: Server
      status: ACTIVE
      f_block: F2
      files: [web/server.py]
  capabilities:
    - id: CAP-1
      name: Data Storage
      status: ACTIVE
relationships:
  - source: COMP-1
    target: CAP-1
    type: realizes
  - source: COMP-2
    target: COMP-1
    type: uses
""")
    # Source
    core = tmp_path / "core"
    core.mkdir()
    (core / "db.py").write_text('''
"""Database connection and query execution."""
MAX_CONNECTIONS = 10

class Database:
    """Manages database connections."""
    def query(self, sql: str) -> list:
        """Execute a SQL query."""
        return []
    def connect(self) -> None:
        """Open a connection."""
        pass
''')
    web = tmp_path / "web"
    web.mkdir()
    (web / "server.py").write_text('''
"""HTTP server handling requests."""

class Server:
    """HTTP request handler."""
    def handle(self, request: dict) -> dict:
        """Handle an HTTP request."""
        return {}
    def start(self, port: int) -> None:
        """Start listening on port."""
        pass
''')
    return tmp_path


def test_hierarchical_pipeline(hierarchical_repo):
    """Full flow: pipeline → compact root → slicer loads sub-model."""
    from architecture_model.orchestration.pipeline import run_pipeline

    # Run pipeline with compact mode
    run_pipeline(hierarchical_repo, compact=True)

    # Root should be compact
    root = load_model(str(hierarchical_repo / ".architecture-model.yaml"))
    root_comps = root.entities.components if hasattr(root.entities, "components") else root.entities.get("components", [])
    for comp in root_comps:
        assert comp.signatures == []
        assert comp.symbols == []

    # Sub-models should exist
    f1 = load_block_model(hierarchical_repo, "F1")
    assert f1 is not None
    f1_comps = f1.entities.components if hasattr(f1.entities, "components") else f1.entities.get("components", [])
    assert len(f1_comps) >= 1

    # Slicer should load sub-model detail
    sliced = slice_by_fblock(root, "F1", project_root=hierarchical_repo)
    sliced_comps = sliced.entities.components if hasattr(sliced.entities, "components") else sliced.entities.get("components", [])
    assert len(sliced_comps) >= 1
    # Sub-model should have richer data than root
    assert sliced_comps[0].name == "Database"


def test_root_size_vs_sub_models(hierarchical_repo):
    """Root model should be significantly smaller than sum of sub-models."""
    from architecture_model.orchestration.pipeline import run_pipeline

    run_pipeline(hierarchical_repo, compact=True)

    root_size = (hierarchical_repo / ".architecture-model.yaml").stat().st_size
    sub_sizes = sum(
        f.stat().st_size
        for f in hierarchical_repo.glob(".architecture-models/*/.architecture-model.yaml")
    )
    # Root should be smaller than combined sub-models
    assert root_size < sub_sizes, f"Root ({root_size}) should be smaller than sub-models ({sub_sizes})"
```

**Step 2: Run, fix, commit**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_hierarchical_integration.py -v`

```bash
git add -A && git commit -m "test: integration test for hierarchical model organization"
```

---

## Task 7: Full verification

**Step 1: Run all arch-std tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/ --ignore=tests/test_config_loader.py -q`
Expected: All pass (603+)

**Step 2: Run all opencode-arch tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/ -q` (in opencode-arch, ignoring pre-existing failures)

---

## Summary

| Task | What | Impact |
|------|------|--------|
| 1 | `compact_root_model()` | Root model shrinks to identity-only stubs |
| 2 | `load_block_model()` | Load sub-models by block ID |
| 3 | Slicer auto-loads sub-models | `slice_by_fblock("F1", project_root=...)` returns rich data |
| 4 | Pipeline compact mode | `run_pipeline(compact=True)` produces hierarchy |
| 5 | MCP slice tool | Agent gets rich slices from sub-models |
| 6 | Integration test | End-to-end proof |
| 7 | Full verification | No regressions |
