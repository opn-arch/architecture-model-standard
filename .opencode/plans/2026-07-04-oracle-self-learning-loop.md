# Oracle Self-Learning Loop Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a self-improving oracle extraction system using manifest coverage as the objective signal, self-critique for per-extraction refinement, and meta-reflection for prompt evolution across batches.

**Architecture:** The oracle receives optimized context (manifest summary + code slices + few-shot examples), extracts with an evolving prompt, self-critiques against manifest coverage gaps, and periodically reflects on failures to evolve its own instructions. Learning happens at two time scales: per-extraction (self-critique) and per-batch (prompt evolution).

**Tech Stack:** Python, Ollama (nomic-embed-text for retrieval), litellm (oracle calls), SQLite (performance tracking), pytest, aiohttp

---

### Task 1: ManifestCoverageComputer

**Files:**
- Create: `src/architecture_model/training/oracle_coverage.py`
- Test: `tests/test_training/test_oracle_coverage.py`

**Step 1: Write the failing test**

```python
# tests/test_training/test_oracle_coverage.py
"""Tests for manifest coverage computation."""

import pytest
from architecture_model.training.oracle_coverage import (
    ManifestCoverageComputer,
    CoverageResult,
)
from architecture_model.core.types import (
    ArchitectureModel, Entities, Component, Capability, Layer,
    Relationship, RelationType, Status, ModelMeta,
)


def _make_manifest():
    """Create a minimal test manifest."""
    return {
        "modules": [
            {"file": "src/client.py", "name": "HTTP Client", "line_count": 200,
             "functions": ["get", "post", "connect"], "imports": ["src/pool.py"], "status": "active"},
            {"file": "src/pool.py", "name": "Connection Pool", "line_count": 150,
             "functions": ["acquire", "release"], "imports": [], "status": "active"},
            {"file": "src/utils.py", "name": "Utilities", "line_count": 30,
             "functions": ["format_url"], "imports": [], "status": "active"},
        ],
        "interfaces": [
            {"source": "src/client.py", "target": "src/pool.py", "import_path": "pool"},
        ],
        "functional_blocks": {
            "F1": {"name": "networking", "status": "active",
                   "sub_functions": [{"file": "src/client.py"}, {"file": "src/pool.py"}]},
        },
    }


def _make_model_covering_all():
    meta = ModelMeta(schema_version="1.0", project="test")
    return ArchitectureModel(
        meta=meta,
        entities=Entities(
            actors=[], behaviors=[], interfaces=[], constraints=[],
            capabilities=[Capability(id="CAP1", name="networking", status=Status.ACTIVE)],
            layers=[Layer(id="L1", name="core", status=Status.ACTIVE)],
            components=[
                Component(id="C1", name="HTTP Client", layer="L1", status=Status.ACTIVE),
                Component(id="C2", name="Connection Pool", layer="L1", status=Status.ACTIVE),
            ],
        ),
        relationships=[
            Relationship(type=RelationType.DEPENDS_ON, from_id="C1", to_id="C2"),
        ],
    )


class TestManifestCoverage:
    def test_full_coverage(self):
        manifest = _make_manifest()
        model = _make_model_covering_all()
        computer = ManifestCoverageComputer()
        result = computer.compute(manifest, model)
        # All significant modules covered, interface covered, block covered
        assert result.module_coverage > 0.8
        assert result.interface_coverage == 1.0
        assert result.block_coverage == 1.0
        assert result.overall > 0.8

    def test_partial_coverage(self):
        manifest = _make_manifest()
        meta = ModelMeta(schema_version="1.0", project="test")
        model = ArchitectureModel(
            meta=meta,
            entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[],
                layers=[Layer(id="L1", name="core", status=Status.ACTIVE)],
                components=[
                    Component(id="C1", name="HTTP Client", layer="L1", status=Status.ACTIVE),
                ],
            ),
            relationships=[],
        )
        computer = ManifestCoverageComputer()
        result = computer.compute(manifest, model)
        # Only 1 of 2 significant modules covered, no interface, no block
        assert result.module_coverage < 0.8
        assert result.interface_coverage == 0.0
        assert len(result.uncovered_modules) >= 1
        assert len(result.uncovered_interfaces) >= 1

    def test_significance_weighting(self):
        """Large modules (by LOC) matter more than small ones."""
        manifest = _make_manifest()
        meta = ModelMeta(schema_version="1.0", project="test")
        # Cover only the 30-LOC utility, miss the 200-LOC client
        model = ArchitectureModel(
            meta=meta,
            entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[], layers=[Layer(id="L1", name="core", status=Status.ACTIVE)],
                components=[
                    Component(id="C1", name="Utilities", layer="L1", status=Status.ACTIVE),
                ],
            ),
            relationships=[],
        )
        computer = ManifestCoverageComputer()
        result = computer.compute(manifest, model)
        # Covering 30 LOC out of 380 total → very low weighted coverage
        assert result.module_coverage < 0.2

    def test_empty_manifest(self):
        manifest = {"modules": [], "interfaces": [], "functional_blocks": {}}
        meta = ModelMeta(schema_version="1.0", project="test")
        model = ArchitectureModel(
            meta=meta, entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[], layers=[], components=[]),
            relationships=[],
        )
        computer = ManifestCoverageComputer()
        result = computer.compute(manifest, model)
        assert result.overall == 1.0  # nothing to cover

    def test_uncovered_lists(self):
        manifest = _make_manifest()
        meta = ModelMeta(schema_version="1.0", project="test")
        model = ArchitectureModel(
            meta=meta, entities=Entities(
                actors=[], behaviors=[], interfaces=[], constraints=[],
                capabilities=[], layers=[], components=[]),
            relationships=[],
        )
        computer = ManifestCoverageComputer()
        result = computer.compute(manifest, model)
        assert "src/client.py" in result.uncovered_modules
        assert ("src/client.py", "src/pool.py") in result.uncovered_interfaces
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_training/test_oracle_coverage.py -v`
Expected: FAIL (module not found)

**Step 3: Write implementation**

```python
# src/architecture_model/training/oracle_coverage.py
"""Manifest coverage computation for oracle self-learning.

Measures how well an ArchitectureModel explains a Reality Manifest.
Uses significance-weighted scoring: large modules matter more.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from architecture_model.core.types import ArchitectureModel


@dataclass
class CoverageResult:
    """Result of manifest coverage computation."""
    module_coverage: float          # LOC-weighted fraction of modules covered
    interface_coverage: float       # fraction of inter-block edges covered
    block_coverage: float           # fraction of F-blocks with matching capability
    overall: float                  # weighted combination
    uncovered_modules: list[str] = field(default_factory=list)
    uncovered_interfaces: list[tuple[str, str]] = field(default_factory=list)


class ManifestCoverageComputer:
    """Computes how well an ArchitectureModel covers a Reality Manifest."""

    def compute(self, manifest: dict, model: ArchitectureModel) -> CoverageResult:
        """Compute significance-weighted coverage.

        Args:
            manifest: Reality Manifest dict (modules, interfaces, functional_blocks).
            model: Architecture model to evaluate.

        Returns:
            CoverageResult with per-dimension and overall scores.
        """
        module_cov, uncovered_mods = self._compute_module_coverage(manifest, model)
        iface_cov, uncovered_ifaces = self._compute_interface_coverage(manifest, model)
        block_cov = self._compute_block_coverage(manifest, model)

        # Weighted combination: modules most important
        overall = 0.5 * module_cov + 0.3 * iface_cov + 0.2 * block_cov

        return CoverageResult(
            module_coverage=module_cov,
            interface_coverage=iface_cov,
            block_coverage=block_cov,
            overall=overall,
            uncovered_modules=uncovered_mods,
            uncovered_interfaces=uncovered_ifaces,
        )

    def _compute_module_coverage(
        self, manifest: dict, model: ArchitectureModel
    ) -> tuple[float, list[str]]:
        """LOC-weighted module coverage. Each manifest module should map to a component."""
        modules = manifest.get("modules", [])
        if not modules:
            return 1.0, []

        # Collect component names (lowercase) for matching
        component_names = {c.name.lower() for c in model.entities.components}

        total_loc = 0
        covered_loc = 0
        uncovered: list[str] = []

        for mod in modules:
            loc = mod.get("line_count", 0)
            if loc < 10:  # skip trivial files
                continue
            total_loc += loc

            mod_name = mod.get("name", "").lower()
            mod_file = mod.get("file", "")

            # Check if any component name matches (fuzzy: word overlap)
            matched = self._name_matches(mod_name, component_names)
            if matched:
                covered_loc += loc
            else:
                uncovered.append(mod_file)

        if total_loc == 0:
            return 1.0, []

        return covered_loc / total_loc, uncovered

    def _compute_interface_coverage(
        self, manifest: dict, model: ArchitectureModel
    ) -> tuple[float, list[tuple[str, str]]]:
        """Fraction of manifest import edges represented as relationships."""
        interfaces = manifest.get("interfaces", [])
        if not interfaces:
            return 1.0, []

        # Build set of relationship endpoints (using component name matching)
        component_names = {c.name.lower(): c.id for c in model.entities.components}
        rel_pairs: set[tuple[str, str]] = set()
        for r in model.relationships:
            rel_pairs.add((r.from_id, r.to_id))

        covered = 0
        uncovered: list[tuple[str, str]] = []

        for iface in interfaces:
            source = iface.get("source", "")
            target = iface.get("target", "")
            # Check if there's a relationship between components matching source/target
            if self._interface_covered(source, target, manifest, model):
                covered += 1
            else:
                uncovered.append((source, target))

        return covered / len(interfaces), uncovered

    def _compute_block_coverage(self, manifest: dict, model: ArchitectureModel) -> float:
        """Fraction of F-blocks with a matching capability."""
        blocks = manifest.get("functional_blocks", {})
        if not blocks:
            return 1.0

        cap_names = {c.name.lower() for c in model.entities.capabilities}
        covered = 0

        for block_id, block_data in blocks.items():
            block_name = block_data.get("name", block_id).lower()
            if self._name_matches(block_name, cap_names):
                covered += 1

        return covered / len(blocks)

    def _name_matches(self, name: str, candidates: set[str]) -> bool:
        """Check if name matches any candidate (exact or word overlap >= 0.4)."""
        name_lower = name.lower()
        if name_lower in candidates:
            return True

        name_words = set(name_lower.replace("-", " ").replace("_", " ").split())
        for candidate in candidates:
            cand_words = set(candidate.replace("-", " ").replace("_", " ").split())
            if not name_words or not cand_words:
                continue
            jaccard = len(name_words & cand_words) / len(name_words | cand_words)
            if jaccard >= 0.4:
                return True

        return False

    def _interface_covered(
        self, source_file: str, target_file: str,
        manifest: dict, model: ArchitectureModel
    ) -> bool:
        """Check if an import edge is covered by a relationship in the model."""
        modules = manifest.get("modules", [])

        # Find module names for source and target files
        source_name = None
        target_name = None
        for mod in modules:
            if mod.get("file") == source_file:
                source_name = mod.get("name", "").lower()
            if mod.get("file") == target_file:
                target_name = mod.get("name", "").lower()

        if not source_name or not target_name:
            return False

        # Find components matching these names
        source_comp = None
        target_comp = None
        for comp in model.entities.components:
            comp_lower = comp.name.lower()
            if self._name_matches(source_name, {comp_lower}):
                source_comp = comp.id
            if self._name_matches(target_name, {comp_lower}):
                target_comp = comp.id

        if not source_comp or not target_comp:
            return False

        # Check if a relationship exists between them
        for r in model.relationships:
            if r.from_id == source_comp and r.to_id == target_comp:
                return True

        return False
```

**Step 4: Run tests**

Run: `pytest tests/test_training/test_oracle_coverage.py -v`
Expected: PASS

Run: `pytest tests/ -x -q`
Expected: 370+ passed

**Step 5: Commit**

```bash
git add -A && git commit -m "feat(training): add ManifestCoverageComputer for oracle self-learning signal"
```

---

### Task 2: OraclePerformanceStore

**Files:**
- Create: `src/architecture_model/training/oracle_performance.py`
- Test: `tests/test_training/test_oracle_performance.py`

**Step 1: Write the failing test**

```python
# tests/test_training/test_oracle_performance.py
"""Tests for oracle performance tracking store."""

import pytest
from architecture_model.training.oracle_performance import (
    OraclePerformanceStore,
    OracleResult,
)


class TestOraclePerformanceStore:
    def test_record_and_count(self, tmp_path):
        store = OraclePerformanceStore(str(tmp_path / "oracle.db"))
        assert store.count() == 0
        store.record(OracleResult(
            repo_url="https://github.com/test/a",
            prompt_variant="v1",
            coverage_score=0.85,
            validator_score=92.0,
            iteration=1,
        ))
        assert store.count() == 1

    def test_get_poor_extractions(self, tmp_path):
        store = OraclePerformanceStore(str(tmp_path / "oracle.db"))
        store.record(OracleResult("repo-a", "v1", 0.9, 95.0, 1))
        store.record(OracleResult("repo-b", "v1", 0.4, 70.0, 1))  # poor
        store.record(OracleResult("repo-c", "v1", 0.3, 60.0, 1))  # poor
        store.record(OracleResult("repo-d", "v1", 0.8, 90.0, 1))

        poor = store.get_poor_extractions(threshold=0.7, limit=3)
        assert len(poor) == 2
        assert poor[0].coverage_score <= 0.4

    def test_get_average_coverage(self, tmp_path):
        store = OraclePerformanceStore(str(tmp_path / "oracle.db"))
        store.record(OracleResult("a", "v1", 0.8, 90.0, 1))
        store.record(OracleResult("b", "v1", 0.6, 80.0, 1))
        avg = store.get_average_coverage()
        assert avg == pytest.approx(0.7, abs=0.01)

    def test_get_recent_count(self, tmp_path):
        store = OraclePerformanceStore(str(tmp_path / "oracle.db"))
        store.record(OracleResult("a", "v1", 0.8, 90.0, 1))
        store.record(OracleResult("b", "v1", 0.6, 80.0, 2))
        store.record(OracleResult("c", "v1", 0.7, 85.0, 2))
        assert store.count_since_iteration(2) == 2

    def test_empty_store(self, tmp_path):
        store = OraclePerformanceStore(str(tmp_path / "oracle.db"))
        assert store.get_poor_extractions() == []
        assert store.get_average_coverage() == 0.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_training/test_oracle_performance.py -v`
Expected: FAIL (module not found)

**Step 3: Write implementation**

```python
# src/architecture_model/training/oracle_performance.py
"""SQLite store tracking oracle extraction performance over time."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class OracleResult:
    """A single oracle extraction result."""
    repo_url: str
    prompt_variant: str
    coverage_score: float
    validator_score: float
    iteration: int
    uncovered_modules: Optional[str] = None  # JSON list
    uncovered_interfaces: Optional[str] = None  # JSON list
    created_at: Optional[str] = None


class OraclePerformanceStore:
    """SQLite store for oracle performance tracking."""

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS oracle_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_url TEXT NOT NULL,
                prompt_variant TEXT NOT NULL,
                coverage_score REAL NOT NULL,
                validator_score REAL NOT NULL,
                iteration INTEGER NOT NULL,
                uncovered_modules TEXT,
                uncovered_interfaces TEXT,
                created_at TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def record(self, result: OracleResult) -> None:
        """Record an oracle extraction result."""
        created_at = result.created_at or datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """INSERT INTO oracle_results
               (repo_url, prompt_variant, coverage_score, validator_score,
                iteration, uncovered_modules, uncovered_interfaces, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (result.repo_url, result.prompt_variant, result.coverage_score,
             result.validator_score, result.iteration,
             result.uncovered_modules, result.uncovered_interfaces, created_at),
        )
        self._conn.commit()

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM oracle_results").fetchone()
        return row[0]

    def count_since_iteration(self, iteration: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM oracle_results WHERE iteration >= ?", (iteration,)
        ).fetchone()
        return row[0]

    def get_poor_extractions(
        self, threshold: float = 0.7, limit: int = 5
    ) -> list[OracleResult]:
        """Get extractions with coverage below threshold, worst first."""
        rows = self._conn.execute(
            """SELECT * FROM oracle_results
               WHERE coverage_score < ?
               ORDER BY coverage_score ASC LIMIT ?""",
            (threshold, limit),
        ).fetchall()
        return [self._row_to_result(r) for r in rows]

    def get_average_coverage(self) -> float:
        """Get average coverage across all results."""
        row = self._conn.execute(
            "SELECT AVG(coverage_score) FROM oracle_results"
        ).fetchone()
        return row[0] or 0.0

    def _row_to_result(self, row) -> OracleResult:
        return OracleResult(
            repo_url=row["repo_url"],
            prompt_variant=row["prompt_variant"],
            coverage_score=row["coverage_score"],
            validator_score=row["validator_score"],
            iteration=row["iteration"],
            uncovered_modules=row["uncovered_modules"],
            uncovered_interfaces=row["uncovered_interfaces"],
            created_at=row["created_at"],
        )
```

**Step 4: Run tests, commit**

Run: `pytest tests/test_training/test_oracle_performance.py -v`
Run: `pytest tests/ -x -q`

```bash
git add -A && git commit -m "feat(training): add OraclePerformanceStore for tracking extraction quality"
```

---

### Task 3: OracleContextBuilder

**Files:**
- Create: `src/architecture_model/training/oracle_context.py`
- Test: `tests/test_training/test_oracle_context.py`

**Step 1: Write the failing test**

```python
# tests/test_training/test_oracle_context.py
"""Tests for oracle context building."""

import pytest
from architecture_model.training.oracle_context import OracleContextBuilder


class TestOracleContextBuilder:
    def test_build_includes_manifest_summary(self, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "client.py").write_text("class Client:\n    def get(self): pass\n" * 20)
        (tmp_path / "pool.py").write_text("class Pool:\n    def acquire(self): pass\n" * 10)

        builder = OracleContextBuilder(tmp_path)
        context = builder.build()
        assert "Reality Manifest Summary" in context
        assert "client" in context.lower()

    def test_build_includes_code_context(self, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "main.py").write_text("def main():\n    print('hello')\n")

        builder = OracleContextBuilder(tmp_path)
        context = builder.build()
        assert "Source Code Context" in context or "main" in context

    def test_manifest_summary_shows_key_modules(self, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "big_module.py").write_text("# big\n" * 100)
        (tmp_path / "tiny.py").write_text("# tiny\n")

        builder = OracleContextBuilder(tmp_path)
        context = builder.build()
        assert "big_module" in context

    def test_max_chars_respected(self, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "huge.py").write_text("x = 1\n" * 10000)

        builder = OracleContextBuilder(tmp_path, max_chars=5000)
        context = builder.build()
        assert len(context) <= 6000  # some tolerance for headers
```

**Step 2: Implement**

The OracleContextBuilder combines:
1. A manifest summary (top modules by LOC, interface count, F-block names)
2. The existing ContextBuilder combined slice

```python
# src/architecture_model/training/oracle_context.py
"""Oracle-optimized context builder combining manifest summary + code slices."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from architecture_model.training.context_builder import ContextBuilder


class OracleContextBuilder:
    """Builds optimized context for oracle extraction.

    Combines a manifest summary (structure, key modules, interfaces)
    with ContextBuilder code slices for maximum extraction quality.
    """

    def __init__(self, repo_path: Path, max_chars: int = 48000) -> None:
        self._repo_path = Path(repo_path)
        self._max_chars = max_chars

    def build(self, manifest: Optional[dict] = None) -> str:
        """Build oracle context string.

        Args:
            manifest: Pre-generated manifest dict. If None, generates a lightweight one.

        Returns:
            Combined context string for oracle extraction.
        """
        if manifest is None:
            manifest = self._generate_lightweight_manifest()

        parts: list[str] = []

        # Part 1: Manifest summary
        summary = self._format_manifest_summary(manifest)
        parts.append(summary)

        # Part 2: Code context from ContextBuilder
        remaining = self._max_chars - len(summary) - 200  # header overhead
        cb = ContextBuilder(self._repo_path, max_chars=max(remaining, 5000))
        slices = cb.build()
        parts.append("\n## Source Code Context\n")
        parts.append(slices.combined())

        return "\n".join(parts)[:self._max_chars]

    def _generate_lightweight_manifest(self) -> dict:
        """Generate a minimal manifest via AST scan (no config required)."""
        modules: list[dict] = []
        interfaces: list[dict] = []

        for py_file in sorted(self._repo_path.rglob("*.py")):
            if "__pycache__" in str(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                loc = len(content.splitlines())
                rel = str(py_file.relative_to(self._repo_path))
                name = py_file.stem.replace("_", " ").title()
                modules.append({"file": rel, "name": name, "line_count": loc, "status": "active"})
            except OSError:
                continue

        return {"modules": modules, "interfaces": interfaces, "functional_blocks": {}}

    def _format_manifest_summary(self, manifest: dict) -> str:
        """Format manifest into a concise summary for the oracle."""
        modules = manifest.get("modules", [])
        interfaces = manifest.get("interfaces", [])
        blocks = manifest.get("functional_blocks", {})

        # Sort modules by LOC
        sorted_mods = sorted(modules, key=lambda m: m.get("line_count", 0), reverse=True)
        total_loc = sum(m.get("line_count", 0) for m in modules)
        active_mods = [m for m in modules if m.get("status") == "active"]

        lines = [
            "## Reality Manifest Summary",
            f"- **{len(active_mods)} active modules**, {total_loc} total LOC",
            f"- **{len(interfaces)} import interfaces** (dependency edges)",
            f"- **{len(blocks)} functional blocks**",
            "",
            "### Key Modules (by size):",
        ]

        for mod in sorted_mods[:10]:
            lines.append(
                f"- `{mod.get('file', '?')}` — {mod.get('name', '?')} "
                f"({mod.get('line_count', 0)} LOC)"
            )

        if blocks:
            lines.append("\n### Functional Blocks:")
            for bid, bdata in list(blocks.items())[:8]:
                bname = bdata.get("name", bid)
                n_files = len(bdata.get("sub_functions", []))
                lines.append(f"- **{bname}** ({n_files} files)")

        if interfaces:
            lines.append(f"\n### Cross-Module Dependencies ({len(interfaces)} edges):")
            for iface in interfaces[:10]:
                lines.append(f"- `{iface.get('source', '?')}` → `{iface.get('target', '?')}`")

        return "\n".join(lines)
```

**Step 3: Run tests, commit**

```bash
pytest tests/test_training/test_oracle_context.py -v
pytest tests/ -x -q
git add -A && git commit -m "feat(training): add OracleContextBuilder with manifest summary + code slices"
```

---

### Task 4: FewShotRetriever

**Files:**
- Create: `src/architecture_model/training/oracle_few_shot.py`
- Test: `tests/test_training/test_oracle_few_shot.py`

**Step 1: Write the failing test**

```python
# tests/test_training/test_oracle_few_shot.py
"""Tests for few-shot example retrieval."""

import pytest
from unittest.mock import MagicMock
from architecture_model.training.oracle_few_shot import FewShotRetriever


class TestFewShotRetriever:
    def test_retrieve_returns_empty_when_no_examples(self, tmp_path):
        store = MagicMock()
        store.get_high_scoring = MagicMock(return_value=[])
        retriever = FewShotRetriever(store)
        examples = retriever.retrieve(manifest={}, k=3)
        assert examples == []

    def test_retrieve_returns_k_examples(self, tmp_path):
        store = MagicMock()
        store.get_high_scoring = MagicMock(return_value=[
            {"repo_url": "a", "code_context": "# a", "oracle_output": "model: a",
             "coverage_score": 0.9, "modules": 5},
            {"repo_url": "b", "code_context": "# b", "oracle_output": "model: b",
             "coverage_score": 0.85, "modules": 10},
            {"repo_url": "c", "code_context": "# c", "oracle_output": "model: c",
             "coverage_score": 0.95, "modules": 3},
        ])
        retriever = FewShotRetriever(store)
        examples = retriever.retrieve(manifest={"modules": [{}] * 5}, k=2)
        assert len(examples) <= 2

    def test_format_few_shot_section(self):
        store = MagicMock()
        store.get_high_scoring = MagicMock(return_value=[
            {"repo_url": "https://github.com/test/repo", "code_context": "class Foo: pass",
             "oracle_output": "entities:\n  components: []", "coverage_score": 0.9, "modules": 5},
        ])
        retriever = FewShotRetriever(store)
        section = retriever.format_section(manifest={"modules": [{}] * 5}, k=1)
        assert "Few-Shot" in section
        assert "entities:" in section
```

**Step 2: Implement**

```python
# src/architecture_model/training/oracle_few_shot.py
"""Few-shot retrieval for oracle prompts.

Retrieves high-scoring past extractions as examples, ranked by
manifest similarity (module count, LOC distribution).
"""

from __future__ import annotations

from typing import Any


class FewShotRetriever:
    """Retrieves similar high-quality past extractions as few-shot examples."""

    def __init__(self, performance_store: Any) -> None:
        self._store = performance_store

    def retrieve(self, manifest: dict, k: int = 3) -> list[dict]:
        """Retrieve top-k similar high-scoring examples.

        Similarity is based on manifest characteristics (module count).
        Returns list of dicts with keys: code_context, oracle_output, coverage_score.
        """
        candidates = self._store.get_high_scoring(threshold=0.8, limit=20)
        if not candidates:
            return []

        # Score by similarity to current manifest
        target_modules = len(manifest.get("modules", []))
        scored = []
        for c in candidates:
            c_modules = c.get("modules", 0)
            # Prefer similar-sized projects
            size_diff = abs(target_modules - c_modules)
            similarity = 1.0 / (1.0 + size_diff * 0.1)
            scored.append((similarity, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:k]]

    def format_section(self, manifest: dict, k: int = 3) -> str:
        """Format few-shot examples as a prompt section."""
        examples = self.retrieve(manifest, k=k)
        if not examples:
            return ""

        lines = ["\n## Few-Shot Examples (high-scoring past extractions)\n"]
        for i, ex in enumerate(examples, 1):
            context_preview = ex.get("code_context", "")[:500]
            output = ex.get("oracle_output", "")[:1000]
            lines.append(f"### Example {i} (coverage: {ex.get('coverage_score', '?')})")
            lines.append(f"Input (abbreviated):\n```\n{context_preview}\n```")
            lines.append(f"Output:\n```yaml\n{output}\n```\n")

        return "\n".join(lines)
```

**Step 3: Run tests, commit**

```bash
pytest tests/test_training/test_oracle_few_shot.py -v
pytest tests/ -x -q
git add -A && git commit -m "feat(training): add FewShotRetriever for oracle prompt examples"
```

---

### Task 5: SelfCritiqueRefiner

**Files:**
- Create: `src/architecture_model/training/oracle_critique.py`
- Test: `tests/test_training/test_oracle_critique.py`

**Step 1: Write the failing test**

```python
# tests/test_training/test_oracle_critique.py
"""Tests for oracle self-critique refinement loop."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from architecture_model.training.oracle_critique import SelfCritiqueRefiner
from architecture_model.training.oracle_coverage import CoverageResult
from architecture_model.core.types import (
    ArchitectureModel, Entities, Component, Layer, Status, ModelMeta,
)


def _make_model(n_components=1):
    meta = ModelMeta(schema_version="1.0", project="test")
    return ArchitectureModel(
        meta=meta,
        entities=Entities(
            actors=[], behaviors=[], interfaces=[], constraints=[],
            capabilities=[], layers=[Layer(id="L1", name="core", status=Status.ACTIVE)],
            components=[
                Component(id=f"C{i}", name=f"Component {i}", layer="L1", status=Status.ACTIVE)
                for i in range(n_components)
            ],
        ),
        relationships=[],
    )


class TestSelfCritiqueRefiner:
    @pytest.mark.asyncio
    async def test_returns_immediately_if_coverage_high(self):
        oracle = MagicMock()
        coverage_computer = MagicMock()
        coverage_computer.compute = MagicMock(return_value=CoverageResult(
            module_coverage=0.9, interface_coverage=0.9, block_coverage=1.0,
            overall=0.9, uncovered_modules=[], uncovered_interfaces=[],
        ))

        refiner = SelfCritiqueRefiner(oracle, coverage_computer, threshold=0.85)
        model = _make_model(3)
        result = await refiner.refine(model, manifest={}, context="# code")
        # Should not call oracle again (already good)
        assert result is model
        oracle.extract_model.assert_not_called()

    @pytest.mark.asyncio
    async def test_retries_on_low_coverage(self):
        improved_model = _make_model(5)

        oracle = MagicMock()
        oracle.extract_model = AsyncMock(return_value=improved_model)

        coverage_computer = MagicMock()
        # First call: low coverage, second: high
        coverage_computer.compute = MagicMock(side_effect=[
            CoverageResult(0.5, 0.3, 0.5, 0.45,
                          uncovered_modules=["src/missed.py"],
                          uncovered_interfaces=[("a.py", "b.py")]),
            CoverageResult(0.9, 0.9, 1.0, 0.92,
                          uncovered_modules=[], uncovered_interfaces=[]),
        ])

        refiner = SelfCritiqueRefiner(oracle, coverage_computer, threshold=0.85, max_rounds=3)
        model = _make_model(1)
        result = await refiner.refine(model, manifest={}, context="# code")

        assert result is improved_model
        oracle.extract_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_rounds_respected(self):
        oracle = MagicMock()
        oracle.extract_model = AsyncMock(return_value=_make_model(2))

        coverage_computer = MagicMock()
        # Always low coverage
        coverage_computer.compute = MagicMock(return_value=CoverageResult(
            0.3, 0.2, 0.0, 0.25,
            uncovered_modules=["x.py"], uncovered_interfaces=[],
        ))

        refiner = SelfCritiqueRefiner(oracle, coverage_computer, threshold=0.85, max_rounds=2)
        model = _make_model(1)
        result = await refiner.refine(model, manifest={}, context="# code")

        # Should have called extract_model exactly max_rounds times
        assert oracle.extract_model.call_count == 2
```

**Step 2: Implement**

```python
# src/architecture_model/training/oracle_critique.py
"""Self-critique refinement loop for oracle extractions.

After initial extraction, checks manifest coverage. If gaps exist,
builds a targeted critique and asks oracle to re-extract with gap awareness.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from architecture_model.core.types import ArchitectureModel
from architecture_model.training.oracle_coverage import ManifestCoverageComputer, CoverageResult

if TYPE_CHECKING:
    from architecture_model.training.oracle import Oracle


class SelfCritiqueRefiner:
    """Iterative self-critique loop for oracle extraction quality."""

    def __init__(
        self,
        oracle: "Oracle",
        coverage_computer: ManifestCoverageComputer,
        threshold: float = 0.85,
        max_rounds: int = 3,
    ) -> None:
        self._oracle = oracle
        self._coverage = coverage_computer
        self._threshold = threshold
        self._max_rounds = max_rounds

    async def refine(
        self,
        model: ArchitectureModel,
        manifest: dict,
        context: str,
    ) -> ArchitectureModel:
        """Refine oracle extraction via self-critique.

        If coverage is already above threshold, returns immediately.
        Otherwise, builds critique from gaps and re-extracts.

        Args:
            model: Initial oracle extraction.
            manifest: Reality Manifest for the repo.
            context: Code context string.

        Returns:
            Best model achieved (original or improved).
        """
        best_model = model

        for round_num in range(self._max_rounds):
            coverage = self._coverage.compute(manifest, best_model)

            if coverage.overall >= self._threshold:
                return best_model

            # Build critique from gaps
            critique = self._build_critique(coverage)

            # Re-extract with critique appended to context
            augmented_context = f"{context}\n\n{critique}"
            new_model = await self._oracle.extract_model(augmented_context)

            if new_model is not None:
                best_model = new_model

        return best_model

    def _build_critique(self, coverage: CoverageResult) -> str:
        """Build a critique prompt from coverage gaps."""
        lines = ["## Self-Critique — Gaps Identified\n"]
        lines.append(f"Coverage score: {coverage.overall:.2f} (target: {self._threshold})\n")

        if coverage.uncovered_modules:
            lines.append("### Uncovered Modules (must add components for these):")
            for mod in coverage.uncovered_modules[:10]:
                lines.append(f"- `{mod}`")

        if coverage.uncovered_interfaces:
            lines.append("\n### Uncovered Import Edges (must add relationships):")
            for src, tgt in coverage.uncovered_interfaces[:10]:
                lines.append(f"- `{src}` → `{tgt}`")

        lines.append("\n**Re-extract the architecture model, ensuring these modules and")
        lines.append("interfaces are represented as components and relationships.**")

        return "\n".join(lines)
```

**Step 3: Run tests, commit**

```bash
pytest tests/test_training/test_oracle_critique.py -v
pytest tests/ -x -q
git add -A && git commit -m "feat(training): add SelfCritiqueRefiner for oracle gap-targeted re-extraction"
```

---

### Task 6: PromptEvolver

**Files:**
- Create: `src/architecture_model/training/oracle_evolution.py`
- Test: `tests/test_training/test_oracle_evolution.py`

**Step 1: Write the failing test**

```python
# tests/test_training/test_oracle_evolution.py
"""Tests for self-reflective prompt evolution."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from architecture_model.training.oracle_evolution import PromptEvolver
from architecture_model.training.oracle_performance import OracleResult


class TestPromptEvolver:
    def test_should_evolve_after_batch_size(self):
        store = MagicMock()
        store.count_since_iteration = MagicMock(return_value=10)
        store.get_average_coverage = MagicMock(return_value=0.8)
        evolver = PromptEvolver(store, batch_size=10)
        assert evolver.should_evolve(current_iteration=5) is True

    def test_should_evolve_on_quality_drop(self):
        store = MagicMock()
        store.count_since_iteration = MagicMock(return_value=3)  # under batch size
        store.get_average_coverage = MagicMock(return_value=0.5)  # but quality dropped
        evolver = PromptEvolver(store, batch_size=10, quality_threshold=0.7)
        assert evolver.should_evolve(current_iteration=5) is True

    def test_should_not_evolve_when_fine(self):
        store = MagicMock()
        store.count_since_iteration = MagicMock(return_value=3)
        store.get_average_coverage = MagicMock(return_value=0.85)
        evolver = PromptEvolver(store, batch_size=10, quality_threshold=0.7)
        assert evolver.should_evolve(current_iteration=5) is False

    def test_get_current_prompt_returns_base(self):
        store = MagicMock()
        evolver = PromptEvolver(store)
        prompt = evolver.get_current_prompt()
        assert "architecture extraction engine" in prompt.lower() or "UAM" in prompt

    @pytest.mark.asyncio
    async def test_evolve_updates_prompt(self):
        store = MagicMock()
        store.get_poor_extractions = MagicMock(return_value=[
            OracleResult("repo-a", "v1", 0.3, 60.0, 1,
                        uncovered_modules='["x.py"]', uncovered_interfaces='[]'),
        ])

        oracle = MagicMock()
        oracle._completion = AsyncMock(return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content="""
analysis:
  - pattern: "missed utility modules"
    reason: "prompt does not emphasize small helper modules"
prompt_additions:
  - "Include ALL modules with >10 LOC as components, even utilities"
prompt_removals: []
"""))],
            usage=MagicMock(total_tokens=100),
        ))

        evolver = PromptEvolver(store)
        old_prompt = evolver.get_current_prompt()
        await evolver.evolve(oracle)
        new_prompt = evolver.get_current_prompt()

        # New prompt should contain the addition
        assert "utility" in new_prompt.lower() or "modules" in new_prompt.lower()
        assert new_prompt != old_prompt
```

**Step 2: Implement**

```python
# src/architecture_model/training/oracle_evolution.py
"""Self-reflective prompt evolution for oracle extraction.

Periodically reflects on poor extractions, asks oracle to analyze
failures and suggest prompt improvements. Maintains prompt lineage.
"""

from __future__ import annotations

import yaml
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.training.oracle import Oracle
    from architecture_model.training.oracle_performance import OraclePerformanceStore

# The base prompt that gets evolved
_BASE_EXTRACTION_PROMPT = """\
You are an architecture extraction engine. Given source code, extract a \
UAM (Universal Architecture Model) in YAML format.

The model has 7 entity types:
- actors: external agents (human, system, external-service)
- capabilities: functional blocks the system provides
- behaviors: use cases, workflows, operational sequences
- interfaces: APIs, protocols, data exchanges
- constraints: non-functional requirements, design rules
- layers: architectural tiers
- components: deployable units, modules, packages

And 8 relationship types:
- realizes, contains, depends-on, exposes, consumes, traces-to, allocated-to, constrained-by

Output ONLY valid YAML matching this structure:
meta:
  schema_version: "1.0"
  project: "<project name>"
entities:
  actors: [...]
  capabilities: [...]
  behaviors: [...]
  interfaces: [...]
  constraints: [...]
  layers: [...]
  components: [...]
relationships: [...]

Each entity must have: id, name, status (ACTIVE/PLANNED/DORMANT/DEPRECATED).
Each relationship must have: type, from, to.

Output raw YAML only — no markdown fences, no explanation."""


_REFLECTION_PROMPT = """\
You are improving your own architecture extraction instructions.

Here are recent extractions that scored poorly on manifest coverage:

{failures}

For each, the manifest shows these modules/interfaces were missed:
{gaps}

Analyze WHY these patterns were missed. Then suggest specific improvements \
to the extraction system prompt.

Return YAML:
analysis:
  - pattern: "what was missed"
    reason: "why it was missed"
prompt_additions:
  - "new instruction to add"
prompt_removals:
  - "instruction to remove (if misleading)"
"""


class PromptEvolver:
    """Self-reflective prompt evolution for oracle."""

    def __init__(
        self,
        performance_store: "OraclePerformanceStore",
        batch_size: int = 10,
        quality_threshold: float = 0.7,
    ) -> None:
        self._store = performance_store
        self._batch_size = batch_size
        self._quality_threshold = quality_threshold
        self._current_prompt = _BASE_EXTRACTION_PROMPT
        self._version = 1
        self._last_evolved_iteration = 0

    def get_current_prompt(self) -> str:
        """Return the current evolved prompt."""
        return self._current_prompt

    @property
    def version(self) -> int:
        return self._version

    def should_evolve(self, current_iteration: int) -> bool:
        """Check if prompt should evolve (batch trigger or quality drop)."""
        # Quality drop trigger
        avg_coverage = self._store.get_average_coverage()
        if avg_coverage > 0 and avg_coverage < self._quality_threshold:
            return True

        # Batch size trigger
        count = self._store.count_since_iteration(self._last_evolved_iteration)
        return count >= self._batch_size

    async def evolve(self, oracle: "Oracle") -> str:
        """Reflect on failures and evolve the prompt.

        Asks oracle to analyze its own poor extractions and suggest
        prompt improvements. Applies suggestions to create new variant.

        Returns:
            The new evolved prompt.
        """
        poor = self._store.get_poor_extractions(threshold=self._quality_threshold, limit=5)
        if not poor:
            return self._current_prompt

        # Format failures for reflection
        failures = self._format_failures(poor)
        gaps = self._format_gaps(poor)

        reflection = _REFLECTION_PROMPT.format(failures=failures, gaps=gaps)

        # Ask oracle to reflect
        messages = [
            {"role": "system", "content": "You are a prompt engineering expert."},
            {"role": "user", "content": reflection},
        ]
        response = await oracle._completion(messages)
        content = response.choices[0].message.content

        # Parse YAML response
        try:
            suggestions = yaml.safe_load(content)
        except yaml.YAMLError:
            return self._current_prompt

        if not isinstance(suggestions, dict):
            return self._current_prompt

        # Apply suggestions
        new_prompt = self._apply_suggestions(suggestions)
        self._current_prompt = new_prompt
        self._version += 1
        self._last_evolved_iteration = self._store.count()

        return new_prompt

    def _apply_suggestions(self, suggestions: dict) -> str:
        """Apply prompt additions/removals to create new variant."""
        prompt = self._current_prompt

        additions = suggestions.get("prompt_additions", [])
        removals = suggestions.get("prompt_removals", [])

        # Remove lines matching removals
        for removal in removals:
            if isinstance(removal, str) and removal in prompt:
                prompt = prompt.replace(removal, "")

        # Add new instructions before the "Output raw YAML" line
        if additions:
            insertion = "\n\nAdditional instructions:\n"
            for add in additions:
                if isinstance(add, str):
                    insertion += f"- {add}\n"

            # Insert before final instruction
            if "Output raw YAML" in prompt:
                prompt = prompt.replace(
                    "Output raw YAML only",
                    f"{insertion}\nOutput raw YAML only",
                )
            else:
                prompt += insertion

        return prompt

    def _format_failures(self, poor: list) -> str:
        lines = []
        for p in poor:
            lines.append(f"- Repo: {p.repo_url} (coverage: {p.coverage_score:.2f})")
        return "\n".join(lines)

    def _format_gaps(self, poor: list) -> str:
        lines = []
        for p in poor:
            mods = p.uncovered_modules or "[]"
            ifaces = p.uncovered_interfaces or "[]"
            lines.append(f"- {p.repo_url}: missed modules={mods}, missed interfaces={ifaces}")
        return "\n".join(lines)
```

**Step 3: Run tests, commit**

```bash
pytest tests/test_training/test_oracle_evolution.py -v
pytest tests/ -x -q
git add -A && git commit -m "feat(training): add PromptEvolver with self-reflective meta-learning"
```

---

### Task 7: Wire Into Oracle + Pipeline

**Files:**
- Modify: `src/architecture_model/training/oracle.py`
- Modify: `src/architecture_model/training/pipeline.py`
- Modify: `src/architecture_model/training/__init__.py`
- Test: `tests/test_training/test_pipeline.py` (add oracle learning tests)

**Step 1: Write failing tests**

```python
# Add to tests/test_training/test_pipeline.py
class TestOracleSelfLearning:
    @pytest.mark.asyncio
    async def test_oracle_uses_enhanced_context(self):
        """Oracle should receive manifest-enriched context."""
        # Verify that when _process_repo queries oracle, it passes
        # OracleContextBuilder output (not raw _read_code_context)
        pass  # Full mock test

    @pytest.mark.asyncio
    async def test_oracle_records_performance(self):
        """After oracle extraction, result is recorded in OraclePerformanceStore."""
        pass  # Verify store.record() called

    @pytest.mark.asyncio
    async def test_prompt_evolves_after_batch(self):
        """Prompt evolution triggers after batch_size repos."""
        pass  # Verify evolver.evolve() called
```

**Step 2: Implement pipeline integration**

Add to `_process_repo`:
1. Build oracle context with OracleContextBuilder (not raw code)
2. After oracle extraction, compute manifest coverage
3. Run self-critique refinement
4. Record result in OraclePerformanceStore
5. Check if prompt should evolve

Add `oracle_learning` subsystem to TrainingPipeline.__init__:
```python
from .oracle_coverage import ManifestCoverageComputer
from .oracle_performance import OraclePerformanceStore
from .oracle_context import OracleContextBuilder
from .oracle_critique import SelfCritiqueRefiner
from .oracle_evolution import PromptEvolver
```

**Step 3: Update Oracle class to use evolved prompt**

Modify `oracle.py` to accept a `system_prompt` parameter (defaulting to the built-in one) so the pipeline can pass the evolved prompt.

**Step 4: Run tests, commit**

```bash
pytest tests/ -x -q
git add -A && git commit -m "feat(training): wire oracle self-learning into MPC pipeline"
```

---

### Task 8: Integration Verification

**Step 1:** Run full test suite: `pytest tests/ -v` — all should pass

**Step 2:** Run a quick functional test:
```python
# Verify oracle learning components work together
from architecture_model.training.oracle_coverage import ManifestCoverageComputer
from architecture_model.training.oracle_context import OracleContextBuilder
# Build context for httpx repo, compute coverage on a mock model
```

**Step 3:** Commit any remaining fixes

---

## Execution Order

```
1 (coverage) + 2 (perf store)  [parallel]
→ 3 (oracle context) + 4 (few-shot)  [parallel]
→ 5 (self-critique)
→ 6 (prompt evolution)
→ 7 (pipeline wiring)
→ 8 (verify)
```
