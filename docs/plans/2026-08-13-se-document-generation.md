# SE Document Generation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Auto-generate standard systems engineering documents (ConOps, Functional Analysis, Logical Architecture, Requirements Analysis, V&V, Operations Manual, Maintenance Manual, Use Cases, Risk Assessment, Interface Specification) plus project-specific docs from architecture model data, for every system in the extraction pipeline.

**Architecture:** New `docs/se/` package with one generator per document type, an orchestrator, changelog tracker for edition management, and frontmatter injection. Generators follow the existing pattern: `(model, manifest?) -> str`. The SE orchestrator is called from the pipeline emit stage (auto) and from `architect_docs` MCP tool (standalone). Each doc set gets a `changelog.yaml` tracking generations, user edits, and conflicts.

**Tech Stack:** Python dataclasses, ArchitectureModel API, YAML (changelog), Mermaid diagrams, existing `docs/` module patterns.

---

## Reference: Entity Access Patterns

All generators use these patterns:

```python
from architecture_model.core.parser import load_model, ArchitectureModel

# Entity access
model.entities.actors        # list[Actor] — id, name, type, goals
model.entities.capabilities  # list[Capability] — id, name, priority, requirements
model.entities.behaviors     # list[Behavior] — id, name, trigger, actor, steps, preconditions, postconditions, pattern
model.entities.interfaces    # list[Interface] — id, name, type, protocol, provider, consumer, endpoints
model.entities.constraints   # list[Constraint] — id, name, type, metric, threshold, rationale
model.entities.layers        # list[Layer] — id, name, order, technology, directories
model.entities.components    # list[Component] — id, name, layer, files, responsibilities, kind, signatures, test_contracts

# Relationships
model.relationships  # list[Relationship] — type, from_id, to_id, description, strength

# Safe enum to string
def _rel_type_str(rt) -> str:
    return rt.value if hasattr(rt, 'value') else str(rt)

def _constraint_type_str(ct) -> str:
    return ct.value if hasattr(ct, 'value') else str(ct)
```

## Reference: Generator Contract

Every SE doc generator follows this signature:

```python
def generate_<doctype>(model: ArchitectureModel, manifest: Any | None = None) -> str:
    """Return markdown string for the document."""
    lines: list[str] = []
    # ... build markdown
    return "\n".join(lines)
```

The orchestrator handles: file I/O, frontmatter injection, changelog updates, conflict detection.

---

### Task 1: Changelog + Frontmatter Infrastructure

**Files:**
- Create: `src/architecture_model/docs/se/__init__.py`
- Create: `src/architecture_model/docs/se/changelog.py`
- Create: `src/architecture_model/docs/se/frontmatter.py`
- Test: `tests/test_se_docs.py`

**Step 1: Write failing tests for changelog**

```python
# tests/test_se_docs.py
"""Tests for SE document generation system."""
from __future__ import annotations
import pytest
from pathlib import Path
import hashlib


class TestChangelog:
    """Tests for changelog tracking."""

    def test_new_changelog_created(self, tmp_path: Path) -> None:
        from architecture_model.docs.se.changelog import Changelog
        cl = Changelog(tmp_path / "changelog.yaml")
        cl.record_generation("conops.md", author="architect_pipeline", model_hash="abc123")
        data = cl.load()
        assert "conops.md" in data["documents"]
        entry = data["documents"]["conops.md"]
        assert entry["created_by"] == "architect_pipeline"
        assert len(entry["editions"]) == 1
        assert entry["editions"][0]["type"] == "generated"

    def test_detect_user_edit(self, tmp_path: Path) -> None:
        from architecture_model.docs.se.changelog import Changelog
        cl = Changelog(tmp_path / "changelog.yaml")
        # Record initial generation with section hashes
        cl.record_generation("conops.md", author="architect_pipeline", model_hash="abc123",
                             section_hashes={"Overview": "hash1", "Actors": "hash2"})
        # Simulate user editing by providing different hashes on check
        edits = cl.detect_edits("conops.md",
                                current_hashes={"Overview": "hash1", "Actors": "CHANGED"})
        assert edits == ["Actors"]

    def test_record_regeneration_preserves_user_edits(self, tmp_path: Path) -> None:
        from architecture_model.docs.se.changelog import Changelog
        cl = Changelog(tmp_path / "changelog.yaml")
        cl.record_generation("conops.md", author="architect_pipeline", model_hash="abc123",
                             section_hashes={"Overview": "h1"})
        cl.record_regeneration("conops.md", author="architect_pipeline", model_hash="def456",
                               preserved_sections=["Overview"], summary="Model updated")
        data = cl.load()
        editions = data["documents"]["conops.md"]["editions"]
        assert len(editions) == 2
        assert editions[1]["type"] == "regenerated"
        assert "Overview" in editions[1]["preserved_sections"]


class TestFrontmatter:
    """Tests for document frontmatter."""

    def test_generate_frontmatter(self) -> None:
        from architecture_model.docs.se.frontmatter import generate_frontmatter
        fm = generate_frontmatter(document="ConOps", system="Django", system_id="SYS-1",
                                  model_hash="abc123", edition=1)
        assert "---" in fm
        assert "document: ConOps" in fm
        assert "system: Django" in fm
        assert "edition: 1" in fm

    def test_parse_frontmatter(self) -> None:
        from architecture_model.docs.se.frontmatter import parse_frontmatter
        doc = "---\ndocument: ConOps\nedition: 2\n---\n# ConOps\nContent here"
        meta, body = parse_frontmatter(doc)
        assert meta["document"] == "ConOps"
        assert meta["edition"] == 2
        assert body.startswith("# ConOps")

    def test_extract_section_hashes(self) -> None:
        from architecture_model.docs.se.frontmatter import extract_section_hashes
        doc = "# Doc\n## Overview\nSome text\n## Actors\nMore text\n## Scenarios\nFinal"
        hashes = extract_section_hashes(doc)
        assert "Overview" in hashes
        assert "Actors" in hashes
        assert "Scenarios" in hashes
        # Each hash is a hex string
        assert all(len(h) == 32 for h in hashes.values())  # md5 hex length
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_se_docs.py -v`
Expected: FAIL — modules don't exist

**Step 3: Implement changelog.py**

```python
# src/architecture_model/docs/se/changelog.py
"""Edition changelog tracking for SE documents."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Changelog:
    """Tracks document generation, user edits, and regeneration history."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict[str, Any]:
        if self._path.exists():
            import yaml  # lazy import
            return yaml.safe_load(self._path.read_text()) or {"documents": {}}
        return {"documents": {}}

    def _save(self, data: dict[str, Any]) -> None:
        import yaml
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    def record_generation(self, doc_name: str, *, author: str, model_hash: str,
                          section_hashes: dict[str, str] | None = None,
                          summary: str = "Initial generation from model") -> None:
        data = self.load()
        now = _now_iso()
        data["documents"][doc_name] = {
            "created": now,
            "created_by": author,
            "model_version": model_hash,
            "section_hashes": section_hashes or {},
            "editions": [{
                "timestamp": now,
                "author": author,
                "type": "generated",
                "summary": summary,
            }],
        }
        self._save(data)

    def detect_edits(self, doc_name: str, *, current_hashes: dict[str, str]) -> list[str]:
        """Return list of section names that were modified since last generation."""
        data = self.load()
        doc = data.get("documents", {}).get(doc_name)
        if not doc:
            return []
        stored = doc.get("section_hashes", {})
        return [name for name, h in current_hashes.items()
                if name in stored and stored[name] != h]

    def record_regeneration(self, doc_name: str, *, author: str, model_hash: str,
                            preserved_sections: list[str] | None = None,
                            conflicts: list[str] | None = None,
                            section_hashes: dict[str, str] | None = None,
                            summary: str = "Model updated") -> None:
        data = self.load()
        doc = data["documents"].get(doc_name)
        if not doc:
            self.record_generation(doc_name, author=author, model_hash=model_hash,
                                   section_hashes=section_hashes, summary=summary)
            return
        doc["model_version"] = model_hash
        if section_hashes:
            doc["section_hashes"] = section_hashes
        doc["editions"].append({
            "timestamp": _now_iso(),
            "author": author,
            "type": "regenerated",
            "summary": summary,
            "preserved_sections": preserved_sections or [],
            "conflicts": conflicts or [],
        })
        self._save(data)
```

**Step 4: Implement frontmatter.py**

```python
# src/architecture_model/docs/se/frontmatter.py
"""Document frontmatter generation and parsing."""
from __future__ import annotations
import hashlib
import re
from typing import Any


def generate_frontmatter(*, document: str, system: str, system_id: str,
                         model_hash: str, edition: int = 1,
                         generator_version: str = "0.3.0") -> str:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "---",
        f"document: {document}",
        f"system: {system}",
        f"system_id: {system_id}",
        f"generated_at: {now}",
        f"generator_version: {generator_version}",
        f"model_hash: {model_hash}",
        f"edition: {edition}",
        "---",
    ]
    return "\n".join(lines)


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from a document. Returns (metadata, body)."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    import yaml
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2].lstrip("\n")
    return meta, body


def extract_section_hashes(text: str) -> dict[str, str]:
    """Extract md5 hashes for each ## section in a markdown document."""
    sections: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        if line.startswith("## "):
            if current_name is not None:
                content = "\n".join(current_lines).strip()
                sections[current_name] = hashlib.md5(content.encode()).hexdigest()
            current_name = line[3:].strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        content = "\n".join(current_lines).strip()
        sections[current_name] = hashlib.md5(content.encode()).hexdigest()

    return sections
```

**Step 5: Create `__init__.py`**

```python
# src/architecture_model/docs/se/__init__.py
"""SE document generation package."""
```

**Step 6: Run tests to verify they pass**

Run: `pytest tests/test_se_docs.py -v`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/architecture_model/docs/se/ tests/test_se_docs.py
git commit -m "feat: add changelog and frontmatter infrastructure for SE docs"
```

---

### Task 2: SE Doc Orchestrator + ConOps Generator

**Files:**
- Create: `src/architecture_model/docs/se/generator.py`
- Create: `src/architecture_model/docs/se/conops.py`
- Create: `src/architecture_model/docs/se/detect.py`
- Modify: `tests/test_se_docs.py`

**Step 1: Write failing tests**

```python
# Append to tests/test_se_docs.py

def _make_model():
    """Build a minimal ArchitectureModel with all 7 entity types for testing."""
    from architecture_model.core.parser import _parse_raw
    raw = {
        "meta": {"schema_version": "2.0", "project": "TestProject"},
        "entities": {
            "actors": [{"id": "ACT-1", "name": "Developer", "type": "human", "goals": ["Build features"]}],
            "capabilities": [
                {"id": "CAP-1", "name": "Data Processing", "status": "ACTIVE"},
                {"id": "CAP-2", "name": "User Management", "status": "ACTIVE"},
            ],
            "behaviors": [
                {"id": "BEH-1", "name": "Submit Form", "trigger": "user action",
                 "actor": "ACT-1", "steps": ["Validate input", "Save data", "Return response"],
                 "preconditions": ["User authenticated"], "postconditions": ["Data saved"]},
                {"id": "BEH-2", "name": "Middleware Pipeline", "trigger": "HTTP request",
                 "steps": ["Process request", "Call view", "Process response"]},
            ],
            "interfaces": [
                {"id": "INT-1", "name": "REST API", "type": "REST", "provider": "COMP-1",
                 "consumer": "ACT-1", "endpoints": [{"path": "/api/data", "method": "GET"}]},
            ],
            "constraints": [
                {"id": "CON-1", "name": "Python 3.10+", "type": "technology", "rationale": "Type hints"},
                {"id": "CON-2", "name": "Response < 200ms", "type": "performance",
                 "metric": "latency", "threshold": "200ms"},
            ],
            "layers": [
                {"id": "LYR-1", "name": "web", "order": 1},
                {"id": "LYR-2", "name": "data", "order": 2},
            ],
            "components": [
                {"id": "COMP-1", "name": "APIServer", "layer": "web",
                 "files": ["src/api.py"], "kind": "service",
                 "responsibilities": ["Handle HTTP requests"]},
                {"id": "COMP-2", "name": "DataStore", "layer": "data",
                 "files": ["src/db.py"], "kind": "data-store",
                 "responsibilities": ["Persist data"]},
            ],
        },
        "relationships": [
            {"from": "COMP-1", "to": "CAP-1", "type": "realizes"},
            {"from": "COMP-1", "to": "COMP-2", "type": "depends-on"},
            {"from": "COMP-1", "to": "CON-2", "type": "constrained-by"},
            {"from": "BEH-1", "to": "BEH-2", "type": "triggers"},
            {"from": "ACT-1", "to": "INT-1", "type": "consumes"},
        ],
    }
    return _parse_raw(raw)


class TestConOps:
    def test_generates_conops(self) -> None:
        from architecture_model.docs.se.conops import generate_conops
        model = _make_model()
        md = generate_conops(model)
        assert "# Concept of Operations" in md
        assert "Developer" in md  # actor name
        assert "Submit Form" in md  # use case behavior
        assert "REST API" in md  # interface

    def test_conops_has_required_sections(self) -> None:
        from architecture_model.docs.se.conops import generate_conops
        model = _make_model()
        md = generate_conops(model)
        for section in ["System Overview", "Stakeholders", "Operational Scenarios",
                        "System Context", "Operational Constraints"]:
            assert f"## {section}" in md, f"Missing section: {section}"


class TestOrchestrator:
    def test_generate_se_docs_creates_files(self, tmp_path: Path) -> None:
        from architecture_model.docs.se.generator import generate_se_docs
        model = _make_model()
        result = generate_se_docs(model, tmp_path)
        assert (tmp_path / "conops.md").exists()
        assert (tmp_path / "changelog.yaml").exists()
        assert len(result["generated"]) >= 1

    def test_regeneration_preserves_user_edits(self, tmp_path: Path) -> None:
        from architecture_model.docs.se.generator import generate_se_docs
        model = _make_model()
        # First generation
        generate_se_docs(model, tmp_path)
        # Simulate user edit
        conops = tmp_path / "conops.md"
        original = conops.read_text()
        conops.write_text(original.replace("## System Overview", "## System Overview\nUser added this line."))
        # Regenerate — user-edited section should be preserved
        result = generate_se_docs(model, tmp_path)
        new_content = conops.read_text()
        assert "User added this line." in new_content
```

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_se_docs.py::TestConOps -v`
Expected: FAIL

**Step 3: Implement conops.py**

```python
# src/architecture_model/docs/se/conops.py
"""ConOps (Concept of Operations) document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def _constraint_type_str(ct: object) -> str:
    return ct.value if hasattr(ct, "value") else str(ct)


def generate_conops(model: ArchitectureModel, manifest: object | None = None) -> str:
    """Generate Concept of Operations document from model data."""
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"

    lines.append(f"# Concept of Operations: {project}")
    lines.append("")

    # --- System Overview ---
    lines.append("## System Overview")
    lines.append("")
    cap_count = len(model.entities.capabilities)
    comp_count = len(model.entities.components)
    lines.append(f"{project} provides {cap_count} capabilities implemented across {comp_count} components.")
    lines.append("")
    if model.entities.capabilities:
        lines.append("**Core Capabilities:**")
        lines.append("")
        for cap in model.entities.capabilities:
            desc = f" - {cap.description}" if cap.description else ""
            lines.append(f"- **{cap.name}**{desc}")
        lines.append("")

    # --- Stakeholders / Actors ---
    lines.append("## Stakeholders")
    lines.append("")
    if model.entities.actors:
        lines.append("| Actor | Type | Goals |")
        lines.append("|-------|------|-------|")
        for actor in model.entities.actors:
            atype = actor.type.value if hasattr(actor.type, "value") else str(actor.type)
            goals = "; ".join(actor.goals) if actor.goals else "—"
            lines.append(f"| {actor.name} | {atype} | {goals} |")
    else:
        lines.append("*No actors defined in the model.*")
    lines.append("")

    # --- Operational Scenarios (from behaviors) ---
    lines.append("## Operational Scenarios")
    lines.append("")
    use_cases = [b for b in model.entities.behaviors
                 if getattr(b, "actor", None) or "use_case" in str(getattr(b, "extensions", {}))]
    workflows = [b for b in model.entities.behaviors if b not in use_cases]

    if use_cases:
        lines.append("### User-Initiated Scenarios")
        lines.append("")
        for beh in use_cases:
            lines.append(f"#### {beh.name}")
            if beh.trigger:
                lines.append(f"**Trigger:** {beh.trigger}")
            if beh.actor:
                lines.append(f"**Actor:** {beh.actor}")
            if beh.preconditions:
                lines.append(f"**Preconditions:** {', '.join(beh.preconditions)}")
            if beh.steps:
                lines.append("**Flow:**")
                for i, step in enumerate(beh.steps, 1):
                    lines.append(f"  {i}. {step}")
            if beh.postconditions:
                lines.append(f"**Postconditions:** {', '.join(beh.postconditions)}")
            lines.append("")

    if workflows:
        lines.append("### System Workflows")
        lines.append("")
        for beh in workflows[:20]:  # cap to avoid huge docs
            trigger = f" (trigger: {beh.trigger})" if beh.trigger else ""
            steps = " -> ".join(beh.steps[:5]) if beh.steps else "—"
            lines.append(f"- **{beh.name}**{trigger}: {steps}")
        if len(workflows) > 20:
            lines.append(f"- *...and {len(workflows) - 20} more workflows*")
        lines.append("")

    if not use_cases and not workflows:
        lines.append("*No behaviors defined in the model.*")
        lines.append("")

    # --- System Context ---
    lines.append("## System Context")
    lines.append("")
    if model.entities.interfaces:
        lines.append("### External Interfaces")
        lines.append("")
        lines.append("| Interface | Type | Provider | Consumer |")
        lines.append("|-----------|------|----------|----------|")
        for iface in model.entities.interfaces:
            itype = iface.type.value if hasattr(iface.type, "value") else str(iface.type)
            lines.append(f"| {iface.name} | {itype} | {iface.provider or '—'} | {iface.consumer or '—'} |")
        lines.append("")

        # Mermaid context diagram
        lines.append("```mermaid")
        lines.append("graph LR")
        for actor in model.entities.actors:
            lines.append(f'    {actor.id}["{actor.name}"]')
        lines.append(f'    SYS["{project}"]')
        for iface in model.entities.interfaces:
            if iface.consumer:
                lines.append(f'    {iface.consumer} -->|"{iface.name}"| SYS')
            if iface.provider:
                lines.append(f'    SYS -->|"{iface.name}"| {iface.provider}')
        lines.append("```")
        lines.append("")
    else:
        lines.append("*No interfaces defined in the model.*")
        lines.append("")

    # --- Operational Constraints ---
    lines.append("## Operational Constraints")
    lines.append("")
    op_constraints = [c for c in model.entities.constraints
                      if _constraint_type_str(c.type) in ("operational", "performance", "reliability")]
    tech_constraints = [c for c in model.entities.constraints
                        if _constraint_type_str(c.type) in ("technology", "regulatory")]
    other_constraints = [c for c in model.entities.constraints
                         if c not in op_constraints and c not in tech_constraints]

    for label, items in [("Operational & Performance", op_constraints),
                         ("Technology & Regulatory", tech_constraints),
                         ("Other", other_constraints)]:
        if items:
            lines.append(f"### {label}")
            lines.append("")
            for con in items:
                ctype = _constraint_type_str(con.type)
                detail = ""
                if con.metric and con.threshold:
                    detail = f" ({con.metric}: {con.threshold})"
                rationale = f" — {con.rationale}" if con.rationale else ""
                lines.append(f"- **{con.name}** [{ctype}]{detail}{rationale}")
            lines.append("")

    if not model.entities.constraints:
        lines.append("*No constraints defined in the model.*")
        lines.append("")

    return "\n".join(lines)
```

**Step 4: Implement detect.py (project-specific doc detection)**

```python
# src/architecture_model/docs/se/detect.py
"""Auto-detect which project-specific documents should be generated."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def _constraint_type_str(ct: object) -> str:
    return ct.value if hasattr(ct, "value") else str(ct)


def detect_project_docs(model: ArchitectureModel) -> list[str]:
    """Return list of project-specific doc types to generate based on model content.

    Returns doc type keys like 'api_reference', 'data_model', etc.
    """
    docs: list[str] = []

    # API Reference — if REST/HTTP interfaces exist
    rest_interfaces = [i for i in model.entities.interfaces
                       if str(getattr(i.type, "value", i.type)).upper() in ("REST", "WEBSOCKET")]
    if rest_interfaces:
        docs.append("api_reference")

    # Data Model — if DB/ORM components or "data" layer exists
    data_comps = [c for c in model.entities.components
                  if getattr(c, "kind", None) and
                  str(getattr(c.kind, "value", c.kind)) in ("data-store", "data-model")]
    data_layers = [la for la in model.entities.layers
                   if "data" in la.name.lower() or "db" in la.name.lower()]
    if data_comps or data_layers:
        docs.append("data_model")

    # Deployment Guide — if OPERATIONAL or TECHNOLOGY constraints exist
    deploy_constraints = [c for c in model.entities.constraints
                          if _constraint_type_str(c.type) in ("operational", "technology")]
    infra_comps = [c for c in model.entities.components
                   if getattr(c, "kind", None) and
                   str(getattr(c.kind, "value", c.kind)) == "infrastructure"]
    if deploy_constraints or infra_comps:
        docs.append("deployment_guide")

    # Security Analysis — if security constraints or auth/security components exist
    sec_constraints = [c for c in model.entities.constraints
                       if _constraint_type_str(c.type) == "security"]
    sec_comps = [c for c in model.entities.components
                 if any(kw in c.name.lower() for kw in ("auth", "security", "csrf", "permission"))]
    if sec_constraints or sec_comps:
        docs.append("security_analysis")

    # CLI Reference — if CLI interfaces exist
    cli_interfaces = [i for i in model.entities.interfaces
                      if str(getattr(i.type, "value", i.type)).upper() == "CLI"]
    cli_comps = [c for c in model.entities.components
                 if getattr(c, "kind", None) and
                 str(getattr(c.kind, "value", c.kind)) == "cli"]
    if cli_interfaces or cli_comps:
        docs.append("cli_reference")

    # Plugin/Extension Guide — if abstract classes or plugin patterns detected
    abstract_comps = [c for c in model.entities.components
                      if any(kw in c.name.lower() for kw in ("plugin", "extension", "backend", "adapter"))]
    if abstract_comps:
        docs.append("plugin_guide")

    return docs
```

**Step 5: Implement generator.py (orchestrator)**

```python
# src/architecture_model/docs/se/generator.py
"""SE document generation orchestrator."""
from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any, TYPE_CHECKING

from .changelog import Changelog
from .frontmatter import generate_frontmatter, parse_frontmatter, extract_section_hashes
from .detect import detect_project_docs

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel

# Registry: doc_key -> (module_name, function_name, display_name, filename)
STANDARD_DOCS: list[tuple[str, str, str, str]] = [
    ("conops", "conops", "ConOps", "conops.md"),
    ("functional_analysis", "functional_analysis", "Functional Analysis", "functional-analysis.md"),
    ("logical_architecture", "logical_architecture", "Logical Architecture", "logical-architecture.md"),
    ("requirements_analysis", "requirements_analysis", "Requirements Analysis", "requirements-analysis.md"),
    ("verification_validation", "verification_validation", "Verification & Validation", "verification-validation.md"),
    ("operations_manual", "operations_manual", "Operations Manual", "operations-manual.md"),
    ("maintenance_manual", "maintenance_manual", "Maintenance Manual", "maintenance-manual.md"),
    ("use_cases", "use_cases", "Use Cases", "use-cases.md"),
    ("risk_assessment", "risk_assessment", "Risk Assessment", "risk-assessment.md"),
    ("interface_spec", "interface_spec", "Interface Specification", "interface-specification.md"),
]

PROJECT_DOCS: dict[str, tuple[str, str, str]] = {
    "api_reference": ("api_reference", "API Reference", "api-reference.md"),
    "data_model": ("data_model", "Data Model", "data-model.md"),
    "deployment_guide": ("deployment_guide", "Deployment Guide", "deployment-guide.md"),
    "security_analysis": ("security_analysis", "Security Analysis", "security-analysis.md"),
    "cli_reference": ("cli_reference", "CLI Reference", "cli-reference.md"),
    "plugin_guide": ("plugin_guide", "Plugin / Extension Guide", "plugin-guide.md"),
}


def _model_hash(model: ArchitectureModel) -> str:
    """Compute a hash representing the model's current state."""
    content = f"{model.entity_count}-{model.relationship_count}"
    for c in model.entities.components:
        content += c.id
    return hashlib.md5(content.encode()).hexdigest()[:12]


def _import_generator(module_name: str):
    """Dynamically import a generator function."""
    import importlib
    mod = importlib.import_module(f"architecture_model.docs.se.{module_name}")
    # Convention: generate_<module_name>
    func_name = f"generate_{module_name}"
    return getattr(mod, func_name)


def generate_se_docs(
    model: ArchitectureModel,
    output_dir: Path,
    manifest: Any | None = None,
    *,
    doc_filter: list[str] | None = None,
    author: str = "architect_pipeline",
) -> dict[str, Any]:
    """Generate SE documents for a model.

    Args:
        model: The architecture model to generate docs from.
        output_dir: Directory to write docs to.
        manifest: Optional manifest for enrichment.
        doc_filter: If set, only generate these doc keys. None = all.
        author: Author name for changelog entries.

    Returns:
        Dict with 'generated' (list of paths), 'skipped', 'preserved_edits', 'errors'.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    changelog = Changelog(output_dir / "changelog.yaml")
    mhash = _model_hash(model)

    system_name = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    system_id = getattr(model.meta, "system_id", "") or "SYS-unknown"

    result: dict[str, Any] = {"generated": [], "skipped": [], "preserved_edits": [], "errors": []}

    # Determine which docs to generate
    to_generate: list[tuple[str, str, str, str]] = []  # (key, module, display, filename)

    for key, mod, display, fname in STANDARD_DOCS:
        if doc_filter and key not in doc_filter:
            continue
        to_generate.append((key, mod, display, fname))

    # Auto-detect project-specific docs
    detected = detect_project_docs(model)
    for pkey in detected:
        if doc_filter and pkey not in doc_filter:
            continue
        if pkey in PROJECT_DOCS:
            mod, display, fname = PROJECT_DOCS[pkey]
            to_generate.append((pkey, mod, display, fname))

    # Generate each document
    for key, mod_name, display_name, filename in to_generate:
        try:
            gen_func = _import_generator(mod_name)
        except (ImportError, AttributeError):
            result["skipped"].append(f"{key}: generator not implemented")
            continue

        try:
            md_content = gen_func(model, manifest)
        except Exception as e:
            result["errors"].append(f"{key}: {e}")
            continue

        out_path = output_dir / filename

        # Check for existing file with user edits
        preserved: list[str] = []
        if out_path.exists():
            existing = out_path.read_text()
            _, existing_body = parse_frontmatter(existing)
            current_hashes = extract_section_hashes(existing_body)
            edited_sections = changelog.detect_edits(filename, current_hashes=current_hashes)

            if edited_sections:
                # Merge: keep user-edited sections, replace rest
                new_hashes = extract_section_hashes(md_content)
                merged = _merge_sections(existing_body, md_content, edited_sections)
                md_content = merged
                preserved = edited_sections
                result["preserved_edits"].extend(
                    [f"{filename}:{s}" for s in edited_sections])

        # Determine edition number
        cl_data = changelog.load()
        doc_entry = cl_data.get("documents", {}).get(filename)
        edition = len(doc_entry["editions"]) + 1 if doc_entry else 1

        # Add frontmatter
        fm = generate_frontmatter(
            document=display_name, system=system_name, system_id=system_id,
            model_hash=mhash, edition=edition,
        )
        full_doc = fm + "\n\n" + md_content

        out_path.write_text(full_doc)
        result["generated"].append(str(out_path))

        # Update changelog
        section_hashes = extract_section_hashes(md_content)
        if doc_entry:
            changelog.record_regeneration(filename, author=author, model_hash=mhash,
                                          preserved_sections=preserved,
                                          section_hashes=section_hashes)
        else:
            changelog.record_generation(filename, author=author, model_hash=mhash,
                                        section_hashes=section_hashes)

    # Generate index
    _write_index(output_dir, to_generate, detected, result)

    return result


def _merge_sections(existing_body: str, new_body: str, preserve: list[str]) -> str:
    """Merge new content with existing, preserving user-edited sections."""
    existing_sections = _split_sections(existing_body)
    new_sections = _split_sections(new_body)

    merged_lines: list[str] = []
    # Start with content before first ##
    if new_sections.get("__preamble__"):
        merged_lines.append(new_sections["__preamble__"])

    for section_name in new_sections:
        if section_name == "__preamble__":
            continue
        if section_name in preserve and section_name in existing_sections:
            merged_lines.append(f"## {section_name}")
            merged_lines.append(existing_sections[section_name])
        else:
            merged_lines.append(f"## {section_name}")
            merged_lines.append(new_sections[section_name])

    return "\n".join(merged_lines)


def _split_sections(text: str) -> dict[str, str]:
    """Split markdown into {section_name: content} dict."""
    sections: dict[str, str] = {}
    current: str | None = "__preamble__"
    lines: list[str] = []

    for line in text.split("\n"):
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(lines).strip()
            current = line[3:].strip()
            lines = []
        else:
            lines.append(line)

    if current is not None:
        sections[current] = "\n".join(lines).strip()

    return sections


def _write_index(output_dir: Path, generated: list[tuple], detected: list[str],
                 result: dict) -> None:
    """Write SE docs index file."""
    lines = ["# Systems Engineering Documents", ""]
    lines.append("## Standard SE Documents")
    lines.append("")
    for key, _, display, fname in generated:
        if key not in [d for d, *_ in [("api_reference",), ("data_model",),
                                        ("deployment_guide",), ("security_analysis",),
                                        ("cli_reference",), ("plugin_guide",)]]:
            status = "generated" if str(output_dir / fname) in result["generated"] else "skipped"
            icon = "+" if status == "generated" else "-"
            lines.append(f"- [{icon}] [{display}]({fname})")
    lines.append("")

    if detected:
        lines.append("## Project-Specific Documents")
        lines.append("")
        for pkey in detected:
            if pkey in PROJECT_DOCS:
                _, display, fname = PROJECT_DOCS[pkey]
                lines.append(f"- [{display}]({fname})")
        lines.append("")

    (output_dir / "index.md").write_text("\n".join(lines))
    result["generated"].append(str(output_dir / "index.md"))
```

**Step 6: Run tests**

Run: `pytest tests/test_se_docs.py -v`
Expected: PASS (conops + orchestrator tests)

**Step 7: Commit**

```bash
git add src/architecture_model/docs/se/ tests/test_se_docs.py
git commit -m "feat: add SE doc orchestrator, ConOps generator, and project-specific detection"
```

---

### Task 3: Functional Analysis + Logical Architecture Generators

**Files:**
- Create: `src/architecture_model/docs/se/functional_analysis.py`
- Create: `src/architecture_model/docs/se/logical_architecture.py`
- Modify: `tests/test_se_docs.py`

**Step 1: Write failing tests**

```python
# Append to tests/test_se_docs.py

class TestFunctionalAnalysis:
    def test_generates_functional_analysis(self) -> None:
        from architecture_model.docs.se.functional_analysis import generate_functional_analysis
        model = _make_model()
        md = generate_functional_analysis(model)
        assert "# Functional Analysis" in md
        assert "Data Processing" in md  # capability
        assert "COMP-1" in md or "APIServer" in md  # component realizing capability

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.functional_analysis import generate_functional_analysis
        model = _make_model()
        md = generate_functional_analysis(model)
        for section in ["Capability Inventory", "Functional Decomposition",
                        "Capability-Component Mapping"]:
            assert f"## {section}" in md, f"Missing: {section}"


class TestLogicalArchitecture:
    def test_generates_logical_architecture(self) -> None:
        from architecture_model.docs.se.logical_architecture import generate_logical_architecture
        model = _make_model()
        md = generate_logical_architecture(model)
        assert "# Logical Architecture" in md
        assert "web" in md  # layer
        assert "APIServer" in md  # component

    def test_has_mermaid_diagram(self) -> None:
        from architecture_model.docs.se.logical_architecture import generate_logical_architecture
        model = _make_model()
        md = generate_logical_architecture(model)
        assert "```mermaid" in md

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.logical_architecture import generate_logical_architecture
        model = _make_model()
        md = generate_logical_architecture(model)
        for section in ["Layer Structure", "Component Allocation", "Inter-Component Interfaces",
                        "Dependency Graph"]:
            assert f"## {section}" in md, f"Missing: {section}"
```

**Step 2: Run to verify failure**

Run: `pytest tests/test_se_docs.py::TestFunctionalAnalysis tests/test_se_docs.py::TestLogicalArchitecture -v`

**Step 3: Implement functional_analysis.py**

```python
# src/architecture_model/docs/se/functional_analysis.py
"""Functional (Capability) Analysis document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def generate_functional_analysis(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Functional Analysis: {project}")
    lines.append("")

    # --- Capability Inventory ---
    lines.append("## Capability Inventory")
    lines.append("")
    if model.entities.capabilities:
        lines.append("| ID | Capability | Priority | Status | Description |")
        lines.append("|----|-----------|----------|--------|-------------|")
        for cap in model.entities.capabilities:
            prio = cap.priority.value if hasattr(cap.priority, "value") else str(cap.priority) if cap.priority else "—"
            desc = cap.description or "—"
            status = cap.status.value if hasattr(cap.status, "value") else str(cap.status)
            lines.append(f"| {cap.id} | {cap.name} | {prio} | {status} | {desc} |")
    else:
        lines.append("*No capabilities defined.*")
    lines.append("")

    # --- Functional Decomposition ---
    lines.append("## Functional Decomposition")
    lines.append("")
    # Build hierarchy from contains relationships
    contains = [r for r in model.relationships if _rel_type_str(r.type) == "contains"]
    cap_map = {c.id: c for c in model.entities.capabilities}
    children: dict[str, list[str]] = {}
    for rel in contains:
        if rel.from_id in cap_map and rel.to_id in cap_map:
            children.setdefault(rel.from_id, []).append(rel.to_id)

    top_level = [c for c in model.entities.capabilities
                 if c.id not in {rel.to_id for rel in contains if rel.from_id in cap_map}]

    if top_level:
        lines.append("```mermaid")
        lines.append("graph TD")
        for cap in top_level:
            safe_name = cap.name.replace('"', "'")
            lines.append(f'    {cap.id}["{safe_name}"]')
            for child_id in children.get(cap.id, []):
                if child_id in cap_map:
                    child_name = cap_map[child_id].name.replace('"', "'")
                    lines.append(f'    {cap.id} --> {child_id}["{child_name}"]')
        lines.append("```")
    lines.append("")

    # --- Capability-Component Mapping ---
    lines.append("## Capability-Component Mapping")
    lines.append("")
    realizes = [r for r in model.relationships if _rel_type_str(r.type) == "realizes"]
    comp_map = {c.id: c for c in model.entities.components}

    if realizes:
        lines.append("| Capability | Realized By | Component Kind |")
        lines.append("|-----------|------------|----------------|")
        for cap in model.entities.capabilities:
            realizers = [r.from_id for r in realizes if r.to_id == cap.id]
            for comp_id in realizers:
                comp = comp_map.get(comp_id)
                if comp:
                    kind = comp.kind.value if hasattr(comp.kind, "value") else str(comp.kind) if comp.kind else "—"
                    lines.append(f"| {cap.name} | {comp.name} ({comp.id}) | {kind} |")
            if not realizers:
                lines.append(f"| {cap.name} | *unrealized* | — |")
    else:
        lines.append("*No realizes relationships defined.*")
    lines.append("")

    # --- Behavioral Coverage ---
    lines.append("## Behavioral Coverage")
    lines.append("")
    traces = [r for r in model.relationships if _rel_type_str(r.type) == "traces-to"]
    beh_map = {b.id: b for b in model.entities.behaviors}
    if model.entities.behaviors:
        lines.append(f"Total behaviors: {len(model.entities.behaviors)}")
        lines.append("")
        traced = {r.to_id for r in traces if r.to_id in beh_map}
        untraced = [b for b in model.entities.behaviors if b.id not in traced]
        if untraced:
            lines.append(f"**Untraced behaviors:** {len(untraced)}")
            for b in untraced[:10]:
                lines.append(f"- {b.name} ({b.id})")
            if len(untraced) > 10:
                lines.append(f"- *...and {len(untraced) - 10} more*")
    else:
        lines.append("*No behaviors defined.*")
    lines.append("")

    return "\n".join(lines)
```

**Step 4: Implement logical_architecture.py**

```python
# src/architecture_model/docs/se/logical_architecture.py
"""Logical Architecture document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def generate_logical_architecture(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Logical Architecture: {project}")
    lines.append("")

    # --- Layer Structure ---
    lines.append("## Layer Structure")
    lines.append("")
    if model.entities.layers:
        sorted_layers = sorted(model.entities.layers, key=lambda la: getattr(la, "order", 0))
        lines.append("| Order | Layer | Technologies | Directories |")
        lines.append("|-------|-------|-------------|-------------|")
        for layer in sorted_layers:
            tech = ", ".join(layer.technology) if layer.technology else "—"
            dirs = ", ".join(layer.directories) if layer.directories else "—"
            lines.append(f"| {getattr(layer, 'order', '—')} | {layer.name} | {tech} | {dirs} |")
    else:
        lines.append("*No layers defined.*")
    lines.append("")

    # --- Component Allocation ---
    lines.append("## Component Allocation")
    lines.append("")
    # Group components by layer
    by_layer: dict[str, list] = {}
    for comp in model.entities.components:
        layer = getattr(comp, "layer", "") or "unassigned"
        by_layer.setdefault(layer, []).append(comp)

    for layer_name, comps in sorted(by_layer.items()):
        lines.append(f"### {layer_name}")
        lines.append("")
        lines.append("| Component | Kind | Files | Responsibilities |")
        lines.append("|-----------|------|-------|------------------|")
        for comp in comps:
            kind = comp.kind.value if hasattr(comp.kind, "value") else str(comp.kind) if comp.kind else "—"
            files = len(comp.files) if comp.files else 0
            resps = "; ".join(comp.responsibilities[:3]) if comp.responsibilities else "—"
            lines.append(f"| {comp.name} ({comp.id}) | {kind} | {files} files | {resps} |")
        lines.append("")

    # --- Inter-Component Interfaces ---
    lines.append("## Inter-Component Interfaces")
    lines.append("")
    if model.entities.interfaces:
        lines.append("| Interface | Type | Protocol | Provider | Consumer |")
        lines.append("|-----------|------|----------|----------|----------|")
        for iface in model.entities.interfaces:
            itype = iface.type.value if hasattr(iface.type, "value") else str(iface.type)
            lines.append(f"| {iface.name} | {itype} | {iface.protocol or '—'} | {iface.provider or '—'} | {iface.consumer or '—'} |")
    else:
        lines.append("*No interfaces defined.*")
    lines.append("")

    # --- Dependency Graph ---
    lines.append("## Dependency Graph")
    lines.append("")
    deps = [r for r in model.relationships if _rel_type_str(r.type) == "depends-on"]
    comp_map = {c.id: c for c in model.entities.components}

    if deps:
        lines.append("```mermaid")
        lines.append("graph TD")
        seen_comps: set[str] = set()
        for rel in deps:
            if rel.from_id in comp_map and rel.to_id in comp_map:
                from_name = comp_map[rel.from_id].name.replace('"', "'")
                to_name = comp_map[rel.to_id].name.replace('"', "'")
                if rel.from_id not in seen_comps:
                    lines.append(f'    {rel.from_id}["{from_name}"]')
                    seen_comps.add(rel.from_id)
                if rel.to_id not in seen_comps:
                    lines.append(f'    {rel.to_id}["{to_name}"]')
                    seen_comps.add(rel.to_id)
                lines.append(f"    {rel.from_id} --> {rel.to_id}")
        lines.append("```")
    else:
        lines.append("*No dependency relationships defined.*")
    lines.append("")

    return "\n".join(lines)
```

**Step 5: Run tests**

Run: `pytest tests/test_se_docs.py -v`

**Step 6: Commit**

```bash
git add src/architecture_model/docs/se/functional_analysis.py src/architecture_model/docs/se/logical_architecture.py tests/test_se_docs.py
git commit -m "feat: add functional analysis and logical architecture SE doc generators"
```

---

### Task 4: Requirements Analysis + V&V Generators

**Files:**
- Create: `src/architecture_model/docs/se/requirements_analysis.py`
- Create: `src/architecture_model/docs/se/verification_validation.py`
- Modify: `tests/test_se_docs.py`

**Step 1: Write failing tests**

```python
class TestRequirementsAnalysis:
    def test_generates_requirements_analysis(self) -> None:
        from architecture_model.docs.se.requirements_analysis import generate_requirements_analysis
        model = _make_model()
        md = generate_requirements_analysis(model)
        assert "# Requirements Analysis" in md
        assert "Python 3.10+" in md  # constraint
        assert "constrained-by" in md or "Traceability" in md

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.requirements_analysis import generate_requirements_analysis
        model = _make_model()
        md = generate_requirements_analysis(model)
        for section in ["Constraint Inventory", "Requirements Traceability",
                        "Constraint Allocation", "Coverage Gaps"]:
            assert f"## {section}" in md, f"Missing: {section}"


class TestVerificationValidation:
    def test_generates_vv(self) -> None:
        from architecture_model.docs.se.verification_validation import generate_verification_validation
        model = _make_model()
        md = generate_verification_validation(model)
        assert "# Verification & Validation" in md

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.verification_validation import generate_verification_validation
        model = _make_model()
        md = generate_verification_validation(model)
        for section in ["Verification Matrix", "Validation Coverage", "Unverified Items"]:
            assert f"## {section}" in md, f"Missing: {section}"
```

**Step 2: Implement requirements_analysis.py**

```python
# src/architecture_model/docs/se/requirements_analysis.py
"""Requirements Analysis document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)

def _constraint_type_str(ct: object) -> str:
    return ct.value if hasattr(ct, "value") else str(ct)


def generate_requirements_analysis(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Requirements Analysis: {project}")
    lines.append("")

    # --- Constraint Inventory ---
    lines.append("## Constraint Inventory")
    lines.append("")
    if model.entities.constraints:
        lines.append("| ID | Constraint | Type | Metric | Threshold | Rationale |")
        lines.append("|----|-----------|------|--------|-----------|-----------|")
        for con in model.entities.constraints:
            ctype = _constraint_type_str(con.type)
            lines.append(f"| {con.id} | {con.name} | {ctype} | {con.metric or '—'} | {con.threshold or '—'} | {con.rationale or '—'} |")
    else:
        lines.append("*No constraints defined.*")
    lines.append("")

    # --- Capability-Derived Requirements ---
    lines.append("## Capability-Derived Requirements")
    lines.append("")
    if model.entities.capabilities:
        for cap in model.entities.capabilities:
            if cap.requirements:
                lines.append(f"### {cap.name} ({cap.id})")
                for req in cap.requirements:
                    lines.append(f"- {req}")
                lines.append("")
        if not any(c.requirements for c in model.entities.capabilities):
            lines.append("*No explicit requirements on capabilities.*")
            lines.append("")
    else:
        lines.append("*No capabilities defined.*")
        lines.append("")

    # --- Requirements Traceability ---
    lines.append("## Requirements Traceability")
    lines.append("")
    constrained_by = [r for r in model.relationships if _rel_type_str(r.type) == "constrained-by"]
    traces_to = [r for r in model.relationships if _rel_type_str(r.type) == "traces-to"]
    satisfies = [r for r in model.relationships if _rel_type_str(r.type) == "satisfies"]

    all_trace_rels = constrained_by + traces_to + satisfies
    if all_trace_rels:
        lines.append("| From | Relationship | To | Description |")
        lines.append("|------|-------------|-----|-------------|")
        entity_map = {e.id: e.name for e in (list(model.entities.components) +
                      list(model.entities.capabilities) + list(model.entities.constraints) +
                      list(model.entities.behaviors))}
        for rel in all_trace_rels:
            from_name = entity_map.get(rel.from_id, rel.from_id)
            to_name = entity_map.get(rel.to_id, rel.to_id)
            rtype = _rel_type_str(rel.type)
            lines.append(f"| {from_name} | {rtype} | {to_name} | {rel.description or '—'} |")
    else:
        lines.append("*No traceability relationships defined.*")
    lines.append("")

    # --- Constraint Allocation ---
    lines.append("## Constraint Allocation")
    lines.append("")
    con_map = {c.id: c for c in model.entities.constraints}
    allocated = {r.to_id for r in constrained_by}
    unallocated = [c for c in model.entities.constraints if c.id not in allocated]

    if constrained_by:
        comp_map = {c.id: c for c in model.entities.components}
        lines.append("| Constraint | Allocated To |")
        lines.append("|-----------|-------------|")
        for con in model.entities.constraints:
            targets = [r.from_id for r in constrained_by if r.to_id == con.id]
            target_names = [comp_map[t].name if t in comp_map else t for t in targets]
            lines.append(f"| {con.name} | {', '.join(target_names) or '*unallocated*'} |")
    lines.append("")

    # --- Coverage Gaps ---
    lines.append("## Coverage Gaps")
    lines.append("")
    gaps: list[str] = []
    if unallocated:
        for c in unallocated:
            gaps.append(f"Constraint **{c.name}** ({c.id}) is not allocated to any component")
    unrealized_caps = []
    realizes = [r for r in model.relationships if _rel_type_str(r.type) == "realizes"]
    realized_ids = {r.to_id for r in realizes}
    for cap in model.entities.capabilities:
        if cap.id not in realized_ids:
            gaps.append(f"Capability **{cap.name}** ({cap.id}) has no realizing component")

    if gaps:
        for g in gaps:
            lines.append(f"- {g}")
    else:
        lines.append("*No coverage gaps detected.*")
    lines.append("")

    return "\n".join(lines)
```

**Step 3: Implement verification_validation.py**

```python
# src/architecture_model/docs/se/verification_validation.py
"""Verification & Validation document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def generate_verification_validation(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Verification & Validation: {project}")
    lines.append("")

    # --- Verification Matrix ---
    lines.append("## Verification Matrix")
    lines.append("")
    # Map components to their test contracts
    comps_with_tests = [(c, c.test_contracts) for c in model.entities.components
                        if hasattr(c, "test_contracts") and c.test_contracts]

    if comps_with_tests:
        lines.append("| Component | Test File | Test Method | Assertion | Contract Type |")
        lines.append("|-----------|----------|-------------|-----------|---------------|")
        for comp, contracts in comps_with_tests:
            for tc in contracts[:10]:  # cap per component
                tf = getattr(tc, "test_file", "—")
                tm = getattr(tc, "test_method", "—")
                assertion = getattr(tc, "assertion", "—")
                ct = getattr(tc, "contract_type", "—")
                lines.append(f"| {comp.name} | {tf} | {tm} | {assertion} | {ct} |")
            if len(contracts) > 10:
                lines.append(f"| {comp.name} | ... | *{len(contracts) - 10} more contracts* | | |")
    else:
        lines.append("*No test contracts found on components.*")
    lines.append("")

    # --- Validation Coverage ---
    lines.append("## Validation Coverage")
    lines.append("")
    total_comps = len(model.entities.components)
    tested_comps = len(comps_with_tests)
    total_contracts = sum(len(c.test_contracts) for c, _ in comps_with_tests)
    lines.append(f"- **Components with tests:** {tested_comps}/{total_comps} ({100*tested_comps//max(total_comps,1)}%)")
    lines.append(f"- **Total test contracts:** {total_contracts}")
    lines.append("")

    # Constraint verification
    lines.append("### Constraint Verification Status")
    lines.append("")
    verifies = [r for r in model.relationships if _rel_type_str(r.type) == "verifies"]
    con_map = {c.id: c for c in model.entities.constraints}
    verified_ids = {r.to_id for r in verifies}

    if model.entities.constraints:
        lines.append("| Constraint | Type | Verified? |")
        lines.append("|-----------|------|-----------|")
        for con in model.entities.constraints:
            from architecture_model.docs.se.requirements_analysis import _constraint_type_str
            ctype = _constraint_type_str(con.type)
            verified = "Yes" if con.id in verified_ids else "No"
            lines.append(f"| {con.name} | {ctype} | {verified} |")
    else:
        lines.append("*No constraints to verify.*")
    lines.append("")

    # --- Behavior Validation ---
    lines.append("## Behavior Validation")
    lines.append("")
    if model.entities.behaviors:
        behaviors_with_steps = [b for b in model.entities.behaviors if b.steps]
        lines.append(f"- **Total behaviors:** {len(model.entities.behaviors)}")
        lines.append(f"- **Behaviors with defined steps:** {len(behaviors_with_steps)}")
        lines.append(f"- **Behaviors with preconditions:** {sum(1 for b in model.entities.behaviors if b.preconditions)}")
        lines.append(f"- **Behaviors with postconditions:** {sum(1 for b in model.entities.behaviors if b.postconditions)}")
    else:
        lines.append("*No behaviors defined.*")
    lines.append("")

    # --- Unverified Items ---
    lines.append("## Unverified Items")
    lines.append("")
    unverified: list[str] = []
    untested_comps = [c for c in model.entities.components
                      if not (hasattr(c, "test_contracts") and c.test_contracts)]
    for c in untested_comps:
        unverified.append(f"Component **{c.name}** ({c.id}) has no test contracts")
    unverified_cons = [c for c in model.entities.constraints if c.id not in verified_ids]
    for c in unverified_cons:
        unverified.append(f"Constraint **{c.name}** ({c.id}) has no verification")

    if unverified:
        for item in unverified:
            lines.append(f"- {item}")
    else:
        lines.append("*All items have verification coverage.*")
    lines.append("")

    return "\n".join(lines)
```

**Step 4: Run tests, commit**

Run: `pytest tests/test_se_docs.py -v`

```bash
git add src/architecture_model/docs/se/requirements_analysis.py src/architecture_model/docs/se/verification_validation.py tests/test_se_docs.py
git commit -m "feat: add requirements analysis and V&V SE doc generators"
```

---

### Task 5: Operations Manual + Maintenance Manual Generators

**Files:**
- Create: `src/architecture_model/docs/se/operations_manual.py`
- Create: `src/architecture_model/docs/se/maintenance_manual.py`
- Modify: `tests/test_se_docs.py`

**Step 1: Write failing tests**

```python
class TestOperationsManual:
    def test_generates_operations_manual(self) -> None:
        from architecture_model.docs.se.operations_manual import generate_operations_manual
        model = _make_model()
        md = generate_operations_manual(model)
        assert "# Operations Manual" in md
        assert "REST API" in md

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.operations_manual import generate_operations_manual
        model = _make_model()
        md = generate_operations_manual(model)
        for section in ["Interface Catalog", "Operational Workflows",
                        "Configuration & Constraints", "Error Handling"]:
            assert f"## {section}" in md, f"Missing: {section}"


class TestMaintenanceManual:
    def test_generates_maintenance_manual(self) -> None:
        from architecture_model.docs.se.maintenance_manual import generate_maintenance_manual
        model = _make_model()
        md = generate_maintenance_manual(model)
        assert "# Maintenance Manual" in md
        assert "APIServer" in md

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.maintenance_manual import generate_maintenance_manual
        model = _make_model()
        md = generate_maintenance_manual(model)
        for section in ["Component Inventory", "Dependency Impact Analysis",
                        "Modification Procedures", "Known Constraints"]:
            assert f"## {section}" in md, f"Missing: {section}"
```

**Step 2: Implement operations_manual.py**

```python
# src/architecture_model/docs/se/operations_manual.py
"""Operations Manual document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)

def _constraint_type_str(ct: object) -> str:
    return ct.value if hasattr(ct, "value") else str(ct)


def generate_operations_manual(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Operations Manual: {project}")
    lines.append("")

    # --- Interface Catalog ---
    lines.append("## Interface Catalog")
    lines.append("")
    if model.entities.interfaces:
        for iface in model.entities.interfaces:
            itype = iface.type.value if hasattr(iface.type, "value") else str(iface.type)
            lines.append(f"### {iface.name} ({itype})")
            lines.append("")
            if iface.protocol:
                lines.append(f"**Protocol:** {iface.protocol}")
            if iface.provider:
                lines.append(f"**Provider:** {iface.provider}")
            if iface.consumer:
                lines.append(f"**Consumer:** {iface.consumer}")
            if iface.endpoints:
                lines.append("")
                lines.append("| Method | Path |")
                lines.append("|--------|------|")
                for ep in iface.endpoints:
                    method = ep.get("method", "—")
                    path = ep.get("path", "—")
                    lines.append(f"| {method} | {path} |")
            lines.append("")
    else:
        lines.append("*No interfaces defined.*")
        lines.append("")

    # --- Operational Workflows ---
    lines.append("## Operational Workflows")
    lines.append("")
    workflows = [b for b in model.entities.behaviors if b.steps]
    if workflows:
        for beh in workflows[:20]:
            lines.append(f"### {beh.name}")
            if beh.trigger:
                lines.append(f"**Trigger:** {beh.trigger}")
            lines.append("")
            for i, step in enumerate(beh.steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")
        if len(workflows) > 20:
            lines.append(f"*...and {len(workflows) - 20} more workflows.*")
            lines.append("")
    else:
        lines.append("*No workflows with defined steps.*")
        lines.append("")

    # --- Configuration & Constraints ---
    lines.append("## Configuration & Constraints")
    lines.append("")
    op_constraints = [c for c in model.entities.constraints
                      if _constraint_type_str(c.type) in ("operational", "technology")]
    if op_constraints:
        for con in op_constraints:
            ctype = _constraint_type_str(con.type)
            lines.append(f"- **{con.name}** [{ctype}]")
            if con.rationale:
                lines.append(f"  - Rationale: {con.rationale}")
            if con.metric and con.threshold:
                lines.append(f"  - Metric: {con.metric} (threshold: {con.threshold})")
    else:
        lines.append("*No operational constraints defined.*")
    lines.append("")

    # --- Error Handling ---
    lines.append("## Error Handling")
    lines.append("")
    # Derive from behaviors with compensations or error steps
    error_behaviors = [b for b in model.entities.behaviors
                       if b.compensations or any("error" in s.lower() for s in b.steps)]
    if error_behaviors:
        for beh in error_behaviors[:10]:
            lines.append(f"### {beh.name}")
            if beh.compensations:
                lines.append("**Compensations:**")
                for comp in beh.compensations:
                    lines.append(f"- Step: {comp.step} -> Compensate: {comp.compensate}")
            lines.append("")
    else:
        lines.append("*No explicit error handling behaviors defined.*")
    lines.append("")

    return "\n".join(lines)
```

**Step 3: Implement maintenance_manual.py**

```python
# src/architecture_model/docs/se/maintenance_manual.py
"""Maintenance Manual document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def generate_maintenance_manual(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Maintenance Manual: {project}")
    lines.append("")

    comp_map = {c.id: c for c in model.entities.components}
    deps = [r for r in model.relationships if _rel_type_str(r.type) == "depends-on"]

    # --- Component Inventory ---
    lines.append("## Component Inventory")
    lines.append("")
    if model.entities.components:
        lines.append("| Component | Kind | Layer | Files | Signatures | Test Contracts |")
        lines.append("|-----------|------|-------|-------|-----------|----------------|")
        for comp in model.entities.components:
            kind = comp.kind.value if hasattr(comp.kind, "value") else str(comp.kind) if comp.kind else "—"
            layer = getattr(comp, "layer", "—") or "—"
            files = len(comp.files) if comp.files else 0
            sigs = len(comp.signatures) if hasattr(comp, "signatures") and comp.signatures else 0
            tests = len(comp.test_contracts) if hasattr(comp, "test_contracts") and comp.test_contracts else 0
            lines.append(f"| {comp.name} ({comp.id}) | {kind} | {layer} | {files} | {sigs} | {tests} |")
    else:
        lines.append("*No components defined.*")
    lines.append("")

    # --- Dependency Impact Analysis ---
    lines.append("## Dependency Impact Analysis")
    lines.append("")
    # For each component, show what depends on it (fan-in) and what it depends on (fan-out)
    if deps:
        lines.append("| Component | Depends On (fan-out) | Depended By (fan-in) | Impact Risk |")
        lines.append("|-----------|---------------------|---------------------|-------------|")
        for comp in model.entities.components:
            fan_out = [r.to_id for r in deps if r.from_id == comp.id]
            fan_in = [r.from_id for r in deps if r.to_id == comp.id]
            risk = "HIGH" if len(fan_in) >= 5 else "MEDIUM" if len(fan_in) >= 2 else "LOW"
            out_names = ", ".join(comp_map[x].name for x in fan_out if x in comp_map) or "—"
            in_names = ", ".join(comp_map[x].name for x in fan_in if x in comp_map) or "—"
            lines.append(f"| {comp.name} | {out_names} | {in_names} | {risk} |")
    else:
        lines.append("*No dependency relationships defined.*")
    lines.append("")

    # --- Modification Procedures ---
    lines.append("## Modification Procedures")
    lines.append("")
    lines.append("For each component, the following files and dependencies must be considered:")
    lines.append("")
    for comp in model.entities.components:
        lines.append(f"### {comp.name} ({comp.id})")
        lines.append("")
        if comp.files:
            lines.append("**Files:**")
            for f in comp.files[:20]:
                lines.append(f"- `{f}`")
            if len(comp.files) > 20:
                lines.append(f"- *...and {len(comp.files) - 20} more files*")
        downstream = [comp_map[r.from_id].name for r in deps
                      if r.to_id == comp.id and r.from_id in comp_map]
        if downstream:
            lines.append(f"**Downstream dependents (must re-test):** {', '.join(downstream)}")
        if comp.responsibilities:
            lines.append(f"**Responsibilities:** {'; '.join(comp.responsibilities)}")
        lines.append("")

    # --- Known Constraints ---
    lines.append("## Known Constraints")
    lines.append("")
    constrained = [r for r in model.relationships if _rel_type_str(r.type) == "constrained-by"]
    con_map = {c.id: c for c in model.entities.constraints}
    if constrained:
        lines.append("| Component | Constraint | Type | Detail |")
        lines.append("|-----------|-----------|------|--------|")
        for rel in constrained:
            comp_name = comp_map[rel.from_id].name if rel.from_id in comp_map else rel.from_id
            con = con_map.get(rel.to_id)
            if con:
                from architecture_model.docs.se.requirements_analysis import _constraint_type_str
                ctype = _constraint_type_str(con.type)
                detail = f"{con.metric}: {con.threshold}" if con.metric else con.rationale or "—"
                lines.append(f"| {comp_name} | {con.name} | {ctype} | {detail} |")
    else:
        lines.append("*No constraint allocations defined.*")
    lines.append("")

    return "\n".join(lines)
```

**Step 4: Run tests, commit**

Run: `pytest tests/test_se_docs.py -v`

```bash
git add src/architecture_model/docs/se/operations_manual.py src/architecture_model/docs/se/maintenance_manual.py tests/test_se_docs.py
git commit -m "feat: add operations manual and maintenance manual SE doc generators"
```

---

### Task 6: Use Cases + Risk Assessment + Interface Specification Generators

**Files:**
- Create: `src/architecture_model/docs/se/use_cases.py`
- Create: `src/architecture_model/docs/se/risk_assessment.py`
- Create: `src/architecture_model/docs/se/interface_spec.py`
- Modify: `tests/test_se_docs.py`

**Step 1: Write failing tests**

```python
class TestUseCases:
    def test_generates_use_cases(self) -> None:
        from architecture_model.docs.se.use_cases import generate_use_cases
        model = _make_model()
        md = generate_use_cases(model)
        assert "# Use Cases" in md
        assert "Submit Form" in md
        assert "Developer" in md

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.use_cases import generate_use_cases
        model = _make_model()
        md = generate_use_cases(model)
        for section in ["Actor-Goal Matrix", "Use Case Specifications", "Use Case Diagram"]:
            assert f"## {section}" in md, f"Missing: {section}"


class TestRiskAssessment:
    def test_generates_risk_assessment(self) -> None:
        from architecture_model.docs.se.risk_assessment import generate_risk_assessment
        model = _make_model()
        md = generate_risk_assessment(model)
        assert "# Risk Assessment" in md

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.risk_assessment import generate_risk_assessment
        model = _make_model()
        md = generate_risk_assessment(model)
        for section in ["Risk Register", "Dependency Risks", "Constraint Risks"]:
            assert f"## {section}" in md, f"Missing: {section}"


class TestInterfaceSpec:
    def test_generates_interface_spec(self) -> None:
        from architecture_model.docs.se.interface_spec import generate_interface_spec
        model = _make_model()
        md = generate_interface_spec(model)
        assert "# Interface Specification" in md
        assert "REST API" in md

    def test_has_required_sections(self) -> None:
        from architecture_model.docs.se.interface_spec import generate_interface_spec
        model = _make_model()
        md = generate_interface_spec(model)
        for section in ["Interface Inventory", "Interface Details"]:
            assert f"## {section}" in md, f"Missing: {section}"
```

**Step 2: Implement use_cases.py**

```python
# src/architecture_model/docs/se/use_cases.py
"""Use Cases document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def generate_use_cases(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Use Cases: {project}")
    lines.append("")

    actor_map = {a.id: a for a in model.entities.actors}
    use_case_behaviors = [b for b in model.entities.behaviors if getattr(b, "actor", None)]
    other_behaviors = [b for b in model.entities.behaviors if not getattr(b, "actor", None)]

    # --- Actor-Goal Matrix ---
    lines.append("## Actor-Goal Matrix")
    lines.append("")
    if model.entities.actors and use_case_behaviors:
        actors = model.entities.actors
        lines.append("| Actor | Use Cases |")
        lines.append("|-------|----------|")
        for actor in actors:
            actor_ucs = [b.name for b in use_case_behaviors if b.actor == actor.id or b.actor == actor.name]
            if not actor_ucs:
                # Fallback: any behavior mentioning actor
                actor_ucs = [b.name for b in use_case_behaviors]
            lines.append(f"| {actor.name} | {'; '.join(actor_ucs[:10])} |")
    elif model.entities.actors:
        lines.append("| Actor | Goals |")
        lines.append("|-------|-------|")
        for actor in model.entities.actors:
            goals = "; ".join(actor.goals) if actor.goals else "—"
            lines.append(f"| {actor.name} | {goals} |")
    else:
        lines.append("*No actors defined.*")
    lines.append("")

    # --- Use Case Specifications ---
    lines.append("## Use Case Specifications")
    lines.append("")
    all_ucs = use_case_behaviors or other_behaviors[:20]
    for beh in all_ucs:
        lines.append(f"### UC: {beh.name}")
        lines.append("")
        lines.append(f"**ID:** {beh.id}")
        if beh.actor:
            actor = actor_map.get(beh.actor)
            lines.append(f"**Actor:** {actor.name if actor else beh.actor}")
        if beh.trigger:
            lines.append(f"**Trigger:** {beh.trigger}")
        if beh.preconditions:
            lines.append(f"**Preconditions:**")
            for pc in beh.preconditions:
                lines.append(f"- {pc}")
        if beh.steps:
            lines.append("**Main Flow:**")
            for i, step in enumerate(beh.steps, 1):
                lines.append(f"  {i}. {step}")
        if beh.postconditions:
            lines.append("**Postconditions:**")
            for pc in beh.postconditions:
                lines.append(f"- {pc}")
        # Show triggered behaviors
        triggers = [r for r in model.relationships
                    if r.from_id == beh.id and _rel_type_str(r.type) == "triggers"]
        if triggers:
            beh_map = {b.id: b for b in model.entities.behaviors}
            lines.append("**Triggers:**")
            for t in triggers:
                target = beh_map.get(t.to_id)
                lines.append(f"- {target.name if target else t.to_id}")
        lines.append("")

    if not all_ucs:
        lines.append("*No use case behaviors defined.*")
        lines.append("")

    # --- Use Case Diagram ---
    lines.append("## Use Case Diagram")
    lines.append("")
    if model.entities.actors and (use_case_behaviors or other_behaviors):
        lines.append("```mermaid")
        lines.append("graph LR")
        for actor in model.entities.actors:
            lines.append(f'    {actor.id}(("{actor.name}"))')
        for beh in (use_case_behaviors or other_behaviors)[:15]:
            safe_name = beh.name.replace('"', "'")
            lines.append(f'    {beh.id}["{safe_name}"]')
            if beh.actor:
                actor_id = beh.actor if beh.actor.startswith("ACT-") else None
                if not actor_id:
                    for a in model.entities.actors:
                        if a.name == beh.actor:
                            actor_id = a.id
                            break
                if actor_id:
                    lines.append(f"    {actor_id} --> {beh.id}")
        lines.append("```")
    else:
        lines.append("*Insufficient data for use case diagram.*")
    lines.append("")

    return "\n".join(lines)
```

**Step 3: Implement risk_assessment.py**

```python
# src/architecture_model/docs/se/risk_assessment.py
"""Risk Assessment document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)

def _constraint_type_str(ct: object) -> str:
    return ct.value if hasattr(ct, "value") else str(ct)


def generate_risk_assessment(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Risk Assessment: {project}")
    lines.append("")

    comp_map = {c.id: c for c in model.entities.components}
    deps = [r for r in model.relationships if _rel_type_str(r.type) == "depends-on"]

    # --- Risk Register ---
    lines.append("## Risk Register")
    lines.append("")
    risks: list[dict] = []

    # High fan-in components (single point of failure)
    for comp in model.entities.components:
        fan_in = sum(1 for r in deps if r.to_id == comp.id)
        if fan_in >= 5:
            risks.append({
                "id": f"RISK-DEP-{comp.id}",
                "category": "Dependency",
                "description": f"{comp.name} has {fan_in} dependents — single point of failure",
                "severity": "HIGH",
                "mitigation": f"Ensure thorough testing of {comp.name}; consider interface abstraction",
            })
        elif fan_in >= 3:
            risks.append({
                "id": f"RISK-DEP-{comp.id}",
                "category": "Dependency",
                "description": f"{comp.name} has {fan_in} dependents",
                "severity": "MEDIUM",
                "mitigation": "Monitor for breaking changes",
            })

    # Unverified constraints
    constrained = [r for r in model.relationships if _rel_type_str(r.type) == "constrained-by"]
    verified = {r.to_id for r in model.relationships if _rel_type_str(r.type) == "verifies"}
    for con in model.entities.constraints:
        if con.id not in verified:
            ctype = _constraint_type_str(con.type)
            severity = "HIGH" if ctype in ("security", "reliability", "performance") else "MEDIUM"
            risks.append({
                "id": f"RISK-CON-{con.id}",
                "category": "Constraint",
                "description": f"Constraint '{con.name}' ({ctype}) has no verification",
                "severity": severity,
                "mitigation": "Add verification tests or monitoring",
            })

    # Unrealized capabilities
    realizes = [r for r in model.relationships if _rel_type_str(r.type) == "realizes"]
    realized_ids = {r.to_id for r in realizes}
    for cap in model.entities.capabilities:
        if cap.id not in realized_ids:
            risks.append({
                "id": f"RISK-CAP-{cap.id}",
                "category": "Capability",
                "description": f"Capability '{cap.name}' has no realizing component",
                "severity": "HIGH",
                "mitigation": "Allocate to component or remove if not needed",
            })

    if risks:
        lines.append("| Risk ID | Category | Severity | Description | Mitigation |")
        lines.append("|---------|----------|----------|-------------|------------|")
        for risk in sorted(risks, key=lambda r: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(r["severity"], 3)):
            lines.append(f"| {risk['id']} | {risk['category']} | {risk['severity']} | {risk['description']} | {risk['mitigation']} |")
    else:
        lines.append("*No risks identified.*")
    lines.append("")

    # --- Dependency Risks ---
    lines.append("## Dependency Risks")
    lines.append("")
    # Components with high fan-out (fragile, many dependencies)
    high_fanout = [(c, sum(1 for r in deps if r.from_id == c.id))
                   for c in model.entities.components]
    high_fanout = [(c, n) for c, n in high_fanout if n >= 3]
    high_fanout.sort(key=lambda x: -x[1])

    if high_fanout:
        lines.append("Components with high dependency count (fragile to upstream changes):")
        lines.append("")
        lines.append("| Component | Dependencies (fan-out) |")
        lines.append("|-----------|----------------------|")
        for comp, count in high_fanout:
            lines.append(f"| {comp.name} | {count} |")
    else:
        lines.append("*No high fan-out components.*")
    lines.append("")

    # --- Constraint Risks ---
    lines.append("## Constraint Risks")
    lines.append("")
    if model.entities.constraints:
        unallocated = [c for c in model.entities.constraints
                       if c.id not in {r.to_id for r in constrained}]
        if unallocated:
            lines.append("**Unallocated constraints (no component owns them):**")
            lines.append("")
            for con in unallocated:
                lines.append(f"- {con.name} ({_constraint_type_str(con.type)})")
        else:
            lines.append("*All constraints allocated.*")
    else:
        lines.append("*No constraints defined.*")
    lines.append("")

    return "\n".join(lines)
```

**Step 4: Implement interface_spec.py**

```python
# src/architecture_model/docs/se/interface_spec.py
"""Interface Specification document generator."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _rel_type_str(rt: object) -> str:
    return rt.value if hasattr(rt, "value") else str(rt)


def generate_interface_spec(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Interface Specification: {project}")
    lines.append("")

    comp_map = {c.id: c for c in model.entities.components}

    # --- Interface Inventory ---
    lines.append("## Interface Inventory")
    lines.append("")
    if model.entities.interfaces:
        lines.append("| ID | Interface | Type | Protocol | Provider | Consumer |")
        lines.append("|----|-----------|------|----------|----------|----------|")
        for iface in model.entities.interfaces:
            itype = iface.type.value if hasattr(iface.type, "value") else str(iface.type)
            lines.append(f"| {iface.id} | {iface.name} | {itype} | {iface.protocol or '—'} | {iface.provider or '—'} | {iface.consumer or '—'} |")
    else:
        lines.append("*No interfaces defined in the model.*")
    lines.append("")

    # --- Interface Details ---
    lines.append("## Interface Details")
    lines.append("")
    if model.entities.interfaces:
        for iface in model.entities.interfaces:
            itype = iface.type.value if hasattr(iface.type, "value") else str(iface.type)
            lines.append(f"### {iface.name}")
            lines.append("")
            lines.append(f"- **ID:** {iface.id}")
            lines.append(f"- **Type:** {itype}")
            if iface.protocol:
                lines.append(f"- **Protocol:** {iface.protocol}")
            if iface.data_format:
                lines.append(f"- **Data Format:** {iface.data_format}")
            if iface.provider:
                prov = comp_map.get(iface.provider)
                lines.append(f"- **Provider:** {prov.name if prov else iface.provider}")
            if iface.consumer:
                cons = comp_map.get(iface.consumer)
                lines.append(f"- **Consumer:** {cons.name if cons else iface.consumer}")
            lines.append("")

            if iface.endpoints:
                lines.append("**Endpoints:**")
                lines.append("")
                lines.append("| Method | Path | Description |")
                lines.append("|--------|------|-------------|")
                for ep in iface.endpoints:
                    method = ep.get("method", "—")
                    path = ep.get("path", "—")
                    desc = ep.get("description", "—")
                    lines.append(f"| {method} | `{path}` | {desc} |")
                lines.append("")

            if iface.schema:
                lines.append(f"**Schema:** `{iface.schema}`")
                lines.append("")
    else:
        lines.append("*No interfaces to detail.*")
        lines.append("")

    # --- Component-Level Interfaces ---
    lines.append("## Component-Level Interfaces")
    lines.append("")
    comps_with_ifaces = [(c, c.interfaces) for c in model.entities.components
                         if hasattr(c, "interfaces") and c.interfaces]
    if comps_with_ifaces:
        for comp, ifaces in comps_with_ifaces:
            lines.append(f"### {comp.name} ({comp.id})")
            lines.append("")
            lines.append("| Name | Kind | Target | Signature |")
            lines.append("|------|------|--------|-----------|")
            for ci in ifaces[:20]:
                kind = getattr(ci, "kind", "—")
                target = getattr(ci, "target_component", "—")
                sig = getattr(ci, "signature", "—")
                lines.append(f"| {ci.name} | {kind} | {target} | `{sig}` |")
            if len(ifaces) > 20:
                lines.append(f"| ... | | | *{len(ifaces) - 20} more* |")
            lines.append("")
    else:
        lines.append("*No component-level interfaces defined.*")
    lines.append("")

    return "\n".join(lines)
```

**Step 5: Run tests, commit**

Run: `pytest tests/test_se_docs.py -v`

```bash
git add src/architecture_model/docs/se/use_cases.py src/architecture_model/docs/se/risk_assessment.py src/architecture_model/docs/se/interface_spec.py tests/test_se_docs.py
git commit -m "feat: add use cases, risk assessment, and interface specification SE doc generators"
```

---

### Task 7: Project-Specific Document Generators

**Files:**
- Create: `src/architecture_model/docs/se/api_reference.py`
- Create: `src/architecture_model/docs/se/data_model.py`
- Create: `src/architecture_model/docs/se/deployment_guide.py`
- Create: `src/architecture_model/docs/se/security_analysis.py`
- Create: `src/architecture_model/docs/se/cli_reference.py`
- Create: `src/architecture_model/docs/se/plugin_guide.py`
- Modify: `tests/test_se_docs.py`

**Step 1: Write failing tests**

```python
class TestProjectSpecificDetection:
    def test_detects_api_reference(self) -> None:
        from architecture_model.docs.se.detect import detect_project_docs
        model = _make_model()  # has REST interface
        docs = detect_project_docs(model)
        assert "api_reference" in docs

    def test_detects_deployment_guide(self) -> None:
        from architecture_model.docs.se.detect import detect_project_docs
        model = _make_model()  # has technology constraint
        docs = detect_project_docs(model)
        assert "deployment_guide" in docs

    def test_no_false_positives(self) -> None:
        from architecture_model.docs.se.detect import detect_project_docs
        from architecture_model.core.parser import _parse_raw
        minimal = _parse_raw({"meta": {"schema_version": "2.0"}, "entities": {}, "relationships": []})
        docs = detect_project_docs(minimal)
        assert docs == []


class TestApiReference:
    def test_generates_api_reference(self) -> None:
        from architecture_model.docs.se.api_reference import generate_api_reference
        model = _make_model()
        md = generate_api_reference(model)
        assert "# API Reference" in md
        assert "/api/data" in md


class TestDataModel:
    def test_generates_data_model(self) -> None:
        from architecture_model.docs.se.data_model import generate_data_model
        model = _make_model()
        md = generate_data_model(model)
        assert "# Data Model" in md
        assert "DataStore" in md
```

**Step 2: Implement all 6 project-specific generators** (each follows same pattern — concise, extract relevant data from model)

Each file: `generate_<name>(model, manifest=None) -> str` with sections appropriate to the doc type.

I'll provide the API reference as the exemplar; the others follow the same pattern with appropriate sections:

```python
# src/architecture_model/docs/se/api_reference.py
"""API Reference document generator (project-specific)."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def generate_api_reference(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# API Reference: {project}")
    lines.append("")

    # Collect REST/HTTP interfaces
    rest_interfaces = [i for i in model.entities.interfaces
                       if str(getattr(i.type, "value", i.type)).upper() in ("REST", "WEBSOCKET")]

    lines.append("## Endpoints")
    lines.append("")
    if rest_interfaces:
        for iface in rest_interfaces:
            lines.append(f"### {iface.name}")
            lines.append("")
            if iface.endpoints:
                lines.append("| Method | Path | Description |")
                lines.append("|--------|------|-------------|")
                for ep in iface.endpoints:
                    lines.append(f"| {ep.get('method', '—')} | `{ep.get('path', '—')}` | {ep.get('description', '—')} |")
            lines.append("")
    else:
        lines.append("*No REST/HTTP interfaces defined.*")
    lines.append("")

    # Component signatures that look like API handlers
    lines.append("## Handler Signatures")
    lines.append("")
    for comp in model.entities.components:
        if hasattr(comp, "signatures") and comp.signatures:
            api_sigs = [s for s in comp.signatures
                        if any(d in str(getattr(s, "decorators", []))
                               for d in ("route", "api_view", "get", "post", "put", "delete"))]
            if api_sigs:
                lines.append(f"### {comp.name}")
                for sig in api_sigs:
                    lines.append(f"- `{sig.name}({', '.join(getattr(sig, 'params', []))})`")
                    if getattr(sig, "returns", None):
                        lines.append(f"  Returns: `{sig.returns}`")
                lines.append("")

    return "\n".join(lines)
```

```python
# src/architecture_model/docs/se/data_model.py
"""Data Model document generator (project-specific)."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def generate_data_model(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Data Model: {project}")
    lines.append("")

    # Data-layer components
    data_comps = [c for c in model.entities.components
                  if (getattr(c, "layer", "") or "").lower() in ("data", "db", "database")
                  or (getattr(c, "kind", None) and
                      str(getattr(c.kind, "value", c.kind)) in ("data-store", "data-model"))]

    lines.append("## Data Components")
    lines.append("")
    if data_comps:
        for comp in data_comps:
            lines.append(f"### {comp.name} ({comp.id})")
            if comp.files:
                lines.append(f"**Files:** {', '.join(f'`{f}`' for f in comp.files[:5])}")
            if hasattr(comp, "symbols") and comp.symbols:
                lines.append("**Models/Classes:**")
                for sym in comp.symbols[:20]:
                    lines.append(f"- `{sym.name}`")
            if hasattr(comp, "fields") and comp.fields:
                lines.append("**Fields:**")
                lines.append("| Name | Type |")
                lines.append("|------|------|")
                for field in comp.fields:
                    lines.append(f"| {field.name} | {getattr(field, 'type', '—')} |")
            lines.append("")
    else:
        lines.append("*No data-layer components identified.*")
    lines.append("")

    return "\n".join(lines)
```

```python
# src/architecture_model/docs/se/deployment_guide.py
"""Deployment Guide document generator (project-specific)."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _constraint_type_str(ct: object) -> str:
    return ct.value if hasattr(ct, "value") else str(ct)


def generate_deployment_guide(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Deployment Guide: {project}")
    lines.append("")

    lines.append("## Technology Constraints")
    lines.append("")
    tech = [c for c in model.entities.constraints if _constraint_type_str(c.type) == "technology"]
    ops = [c for c in model.entities.constraints if _constraint_type_str(c.type) == "operational"]
    for con in tech + ops:
        lines.append(f"- **{con.name}** ({_constraint_type_str(con.type)}): {con.rationale or '—'}")
    if not tech and not ops:
        lines.append("*No deployment constraints defined.*")
    lines.append("")

    lines.append("## Component Deployment")
    lines.append("")
    lines.append("| Component | Kind | Layer |")
    lines.append("|-----------|------|-------|")
    for comp in model.entities.components:
        kind = comp.kind.value if hasattr(comp.kind, "value") else str(comp.kind) if comp.kind else "—"
        lines.append(f"| {comp.name} | {kind} | {getattr(comp, 'layer', '—') or '—'} |")
    lines.append("")

    return "\n".join(lines)
```

```python
# src/architecture_model/docs/se/security_analysis.py
"""Security Analysis document generator (project-specific)."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def _constraint_type_str(ct: object) -> str:
    return ct.value if hasattr(ct, "value") else str(ct)


def generate_security_analysis(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Security Analysis: {project}")
    lines.append("")

    sec_constraints = [c for c in model.entities.constraints if _constraint_type_str(c.type) == "security"]
    sec_comps = [c for c in model.entities.components
                 if any(kw in c.name.lower() for kw in ("auth", "security", "csrf", "permission", "token"))]

    lines.append("## Security Constraints")
    lines.append("")
    if sec_constraints:
        for con in sec_constraints:
            lines.append(f"- **{con.name}**: {con.rationale or '—'}")
    else:
        lines.append("*No explicit security constraints defined.*")
    lines.append("")

    lines.append("## Security-Related Components")
    lines.append("")
    if sec_comps:
        for comp in sec_comps:
            lines.append(f"### {comp.name} ({comp.id})")
            if comp.responsibilities:
                lines.append(f"Responsibilities: {'; '.join(comp.responsibilities)}")
            if comp.files:
                lines.append(f"Files: {', '.join(f'`{f}`' for f in comp.files[:5])}")
            lines.append("")
    else:
        lines.append("*No security-related components identified.*")
    lines.append("")

    return "\n".join(lines)
```

```python
# src/architecture_model/docs/se/cli_reference.py
"""CLI Reference document generator (project-specific)."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def generate_cli_reference(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# CLI Reference: {project}")
    lines.append("")

    cli_interfaces = [i for i in model.entities.interfaces
                      if str(getattr(i.type, "value", i.type)).upper() == "CLI"]
    cli_comps = [c for c in model.entities.components
                 if getattr(c, "kind", None) and str(getattr(c.kind, "value", c.kind)) == "cli"]

    lines.append("## CLI Interfaces")
    lines.append("")
    if cli_interfaces:
        for iface in cli_interfaces:
            lines.append(f"### {iface.name}")
            if iface.endpoints:
                for ep in iface.endpoints:
                    lines.append(f"- `{ep.get('path', ep.get('command', '—'))}`")
            lines.append("")
    lines.append("")

    lines.append("## CLI Components")
    lines.append("")
    if cli_comps:
        for comp in cli_comps:
            lines.append(f"### {comp.name}")
            if comp.files:
                lines.append(f"Files: {', '.join(f'`{f}`' for f in comp.files[:10])}")
            if hasattr(comp, "signatures") and comp.signatures:
                lines.append("Commands/Functions:")
                for sig in comp.signatures[:20]:
                    lines.append(f"- `{sig.name}`")
            lines.append("")
    else:
        lines.append("*No CLI components identified.*")
    lines.append("")

    return "\n".join(lines)
```

```python
# src/architecture_model/docs/se/plugin_guide.py
"""Plugin / Extension Guide document generator (project-specific)."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from architecture_model.core.parser import ArchitectureModel


def generate_plugin_guide(model: ArchitectureModel, manifest: object | None = None) -> str:
    lines: list[str] = []
    project = getattr(model.meta, "project", "") or getattr(model.meta, "system", "") or "System"
    lines.append(f"# Plugin / Extension Guide: {project}")
    lines.append("")

    ext_comps = [c for c in model.entities.components
                 if any(kw in c.name.lower() for kw in ("plugin", "extension", "backend", "adapter"))]

    lines.append("## Extension Points")
    lines.append("")
    if ext_comps:
        for comp in ext_comps:
            lines.append(f"### {comp.name} ({comp.id})")
            if comp.responsibilities:
                lines.append(f"**Purpose:** {'; '.join(comp.responsibilities)}")
            if comp.files:
                lines.append(f"**Files:** {', '.join(f'`{f}`' for f in comp.files[:5])}")
            if hasattr(comp, "interfaces") and comp.interfaces:
                lines.append("**Interfaces:**")
                for ci in comp.interfaces[:10]:
                    lines.append(f"- {ci.name} ({getattr(ci, 'kind', '—')})")
            lines.append("")
    else:
        lines.append("*No plugin/extension components identified.*")
    lines.append("")

    return "\n".join(lines)
```

**Step 3: Run tests, commit**

Run: `pytest tests/test_se_docs.py -v`

```bash
git add src/architecture_model/docs/se/ tests/test_se_docs.py
git commit -m "feat: add project-specific SE doc generators (API, data model, deployment, security, CLI, plugin)"
```

---

### Task 8: Pipeline Emit Integration

**Files:**
- Modify: `src/architecture_model/pipeline/emit.py`
- Modify: `tests/test_se_docs.py`

**Step 1: Write failing test**

```python
class TestEmitIntegration:
    def test_emit_generates_se_docs(self, tmp_path: Path) -> None:
        """SE docs are generated during emit stage."""
        from architecture_model.docs.se.generator import generate_se_docs
        model = _make_model()
        se_dir = tmp_path / "se"
        result = generate_se_docs(model, se_dir)
        # All 10 standard docs generated (or skipped if not implemented)
        assert len(result["generated"]) >= 5
        assert (se_dir / "conops.md").exists()
        assert (se_dir / "changelog.yaml").exists()
        # Check frontmatter
        content = (se_dir / "conops.md").read_text()
        assert "---" in content
        assert "document: ConOps" in content
```

**Step 2: Add SE doc generation hook to emit stage**

In `src/architecture_model/pipeline/emit.py`, after the existing artifact writing, add a call to `generate_se_docs` for:
1. The top-level SoS model
2. Each subsystem model

```python
# In emit.py, after writing per-system model YAML files:

# Generate SE docs for top-level
from architecture_model.docs.se.generator import generate_se_docs as gen_se
from architecture_model.core.parser import load_model

top_model_path = output_dir / ".architecture-model.yaml"
if top_model_path.exists():
    try:
        top_model = load_model(top_model_path)
        se_dir = output_dir / "docs" / "se"
        gen_se(top_model, se_dir)
    except Exception:
        pass  # Non-fatal: docs are supplementary

# Generate SE docs for each subsystem
for sys_dir in output_dir.iterdir():
    sys_model_path = sys_dir / ".architecture-model.yaml"
    if sys_dir.is_dir() and sys_model_path.exists():
        try:
            sys_model = load_model(sys_model_path)
            sys_se_dir = sys_dir / "docs" / "se"
            gen_se(sys_model, sys_se_dir)
        except Exception:
            pass
```

**Step 3: Run tests, commit**

Run: `pytest tests/test_se_docs.py tests/test_pipeline_stages.py -v`

```bash
git add src/architecture_model/pipeline/emit.py tests/test_se_docs.py
git commit -m "feat: integrate SE doc generation into pipeline emit stage"
```

---

### Task 9: MCP Tool + CLI Updates

**Files:**
- Modify: `src/architecture_model/docs/se/__init__.py` (export generate_se_docs)
- Modify: MCP docs tool at `/Users/baigm2/Documents/Projects/opencode-arch/src/opencode_arch/mcp/tools/docs.py`
- Modify: `src/architecture_model/cli/main.py` (add --se flag)

**Step 1: Update MCP tool to support SE doc formats**

Add `se_all` format option and individual SE doc keys to `architect_docs`. When `formats` includes `se_all` or specific SE doc keys, call `generate_se_docs()`.

**Step 2: Update CLI to add `--se` flag**

Add `--se` / `--formats se_all` support to `architecture-model docs` command.

**Step 3: Test, commit**

Run: `pytest tests/test_se_docs.py -v`

```bash
git add -A
git commit -m "feat: add SE doc support to MCP tool and CLI"
```

---

### Task 10: End-to-End Verification on Django

**No code changes — operational task.**

1. Clear Django pipeline cache
2. Run full pipeline (observe → emit) — emit now auto-generates SE docs
3. Verify SE docs exist at `.architecture-models/.architecture-models/docs/se/` (top-level) and per subsystem
4. Check that Django model produces rich ConOps (211 behaviors, 1 actor, constraints), Use Cases, V&V (test contracts), etc.
5. Verify changelog.yaml is created for each doc set
6. Verify project-specific docs are auto-detected (Django should get: api_reference, data_model, deployment_guide, cli_reference)

---

## Summary

| Task | Type | Description |
|------|------|-------------|
| 1 | Infra | Changelog + frontmatter infrastructure |
| 2 | Feature | SE orchestrator + ConOps generator + detect |
| 3 | Feature | Functional Analysis + Logical Architecture |
| 4 | Feature | Requirements Analysis + V&V |
| 5 | Feature | Operations Manual + Maintenance Manual |
| 6 | Feature | Use Cases + Risk Assessment + Interface Spec |
| 7 | Feature | 6 project-specific doc generators |
| 8 | Integration | Pipeline emit hook for SE docs |
| 9 | Integration | MCP tool + CLI updates |
| 10 | Ops | End-to-end verification on Django |

Total: 10 tasks. Tasks 1-7 are pure generators (independent, parallelizable). Task 8-9 are integration. Task 10 is verification.
