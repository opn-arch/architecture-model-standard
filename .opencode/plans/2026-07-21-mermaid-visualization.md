# Mermaid Visualization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate 4 standard Mermaid diagrams from any ArchitectureModel, integrated into the standard modeling process.

**Architecture:** Refactor `src/architecture_model/cli/visualize.py` into a reusable module at `src/architecture_model/core/visualize.py` with 4 generators. Add an orchestration function that writes `.mmd` files. Wire into CLI as `architecture-model visualize`.

**Tech Stack:** Python dataclasses (existing types), Mermaid flowchart/C4 syntax, pathlib for file output.

---

## Task 1: Create core visualization module with context diagram

**Files:**
- Create: `src/architecture_model/core/visualize.py`
- Create: `tests/test_visualize.py`

**Step 1: Write failing test**

```python
"""Tests for Mermaid diagram generation."""
import pytest
from architecture_model.core.types import (
    ArchitectureModel, Entities, Actor, Capability, Component, Behavior,
    Interface, Constraint, Layer, Relationship, Meta,
    Status, ActorType, RelationType, ComponentKind, InterfaceType,
)
from architecture_model.core.visualize import generate_context_diagram


def _make_model():
    """Minimal model with actors, components, interfaces."""
    return ArchitectureModel(
        meta=Meta(project="test", schema_version="2.0"),
        entities=Entities(
            actors=[
                Actor(id="ACT-1", name="User", status=Status.ACTIVE, type=ActorType.PERSON),
                Actor(id="ACT-2", name="External API", status=Status.ACTIVE, type=ActorType.SYSTEM),
            ],
            capabilities=[
                Capability(id="CAP-1", name="Data Processing", status=Status.ACTIVE, f_block="F1"),
            ],
            components=[
                Component(id="COMP-1", name="Processor", status=Status.ACTIVE, kind=ComponentKind.SERVICE),
                Component(id="COMP-2", name="Gateway", status=Status.ACTIVE, kind=ComponentKind.SERVICE),
            ],
            behaviors=[
                Behavior(id="BEH-1", name="Process Data", status=Status.ACTIVE),
            ],
            interfaces=[
                Interface(id="IFC-1", name="REST API", status=Status.ACTIVE, type=InterfaceType.REST),
            ],
            constraints=[],
            layers=[
                Layer(id="L-svc", name="Services", status=Status.ACTIVE),
            ],
        ),
        relationships=[
            Relationship(from_id="ACT-1", to_id="IFC-1", type=RelationType.CONSUMES),
            Relationship(from_id="COMP-2", to_id="IFC-1", type=RelationType.EXPOSES),
            Relationship(from_id="COMP-1", to_id="CAP-1", type=RelationType.REALIZES),
            Relationship(from_id="COMP-1", to_id="COMP-2", type=RelationType.DEPENDS_ON),
        ],
    )


def test_context_diagram_structure():
    model = _make_model()
    diagram = generate_context_diagram(model)
    assert diagram.startswith("flowchart TB")
    assert "User" in diagram
    assert "External API" in diagram
    assert "consumes" in diagram or "IFC" in diagram
```

**Step 2:** Run: `pytest tests/test_visualize.py::test_context_diagram_structure -v` — Expected: FAIL

**Step 3: Implement context diagram generator**

Create `src/architecture_model/core/visualize.py`:

```python
"""Generate Mermaid diagrams from architecture models."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import ArchitectureModel


def _sid(node_id: str) -> str:
    """Sanitize ID for Mermaid (replace hyphens/dots with underscores)."""
    return node_id.replace("-", "_").replace(".", "_")


def _label(name: str) -> str:
    """Escape label for Mermaid."""
    return name.replace('"', "'")


def generate_context_diagram(model: "ArchitectureModel") -> str:
    """C4-style context: actors interacting with system via interfaces."""
    lines = ["flowchart TB"]

    # System boundary
    lines.append("    subgraph system[System]")
    for ifc in model.entities.interfaces:
        lines.append(f"        {_sid(ifc.id)}{{{{{_label(ifc.name)}}}}}")
    if not model.entities.interfaces:
        lines.append(f"        sys_core[{model.meta.project}]")
    lines.append("    end")

    # Actors
    for actor in model.entities.actors:
        aid = _sid(actor.id)
        atype = getattr(actor.type, 'value', actor.type) if actor.type else 'system'
        if atype == "person":
            lines.append(f"    {aid}[/{_label(actor.name)}\\]")
        else:
            lines.append(f"    {aid}[{_label(actor.name)}]")

    # Edges: consumes (actor->interface), exposes (component->interface)
    for rel in model.relationships:
        rtype = getattr(rel.type, 'value', rel.type)
        if rtype == "consumes":
            lines.append(f"    {_sid(rel.from_id)} -->|consumes| {_sid(rel.to_id)}")
        elif rtype == "exposes":
            lines.append(f"    {_sid(rel.from_id)} -.->|exposes| {_sid(rel.to_id)}")

    return "\n".join(lines)
```

**Step 4:** Run: `pytest tests/test_visualize.py::test_context_diagram_structure -v` — Expected: PASS

**Step 5:** Commit: `git add src/architecture_model/core/visualize.py tests/test_visualize.py && git commit -m "feat: add context diagram generator for Mermaid visualization"`

---

## Task 2: Add components diagram

**Files:**
- Modify: `src/architecture_model/core/visualize.py`
- Modify: `tests/test_visualize.py`

**Step 1: Write failing test**

```python
from architecture_model.core.visualize import generate_components_diagram

def test_components_diagram_layers():
    model = _make_model()
    diagram = generate_components_diagram(model)
    assert diagram.startswith("flowchart TB")
    assert "Processor" in diagram
    assert "Gateway" in diagram
    assert "realizes" in diagram
```

**Step 2: Implement**

```python
def generate_components_diagram(model: "ArchitectureModel") -> str:
    """Components grouped by layer, with realizes edges to capabilities."""
    lines = ["flowchart TB"]

    # Build layer membership from relationships
    layer_members: dict[str, list[str]] = defaultdict(list)
    comp_ids = {c.id for c in model.entities.components}
    for rel in model.relationships:
        rtype = getattr(rel.type, 'value', rel.type)
        if rtype == "contains" and rel.from_id in {l.id for l in model.entities.layers}:
            if rel.to_id in comp_ids:
                layer_members[rel.from_id].append(rel.to_id)

    assigned = {cid for members in layer_members.values() for cid in members}
    unassigned = [c for c in model.entities.components if c.id not in assigned]

    layer_map = {l.id: l for l in model.entities.layers}
    for lid, members in sorted(layer_members.items()):
        layer = layer_map[lid]
        lines.append(f"    subgraph {_sid(lid)}[{_label(layer.name)}]")
        for cid in members:
            comp = next(c for c in model.entities.components if c.id == cid)
            lines.append(f"        {_sid(cid)}[{_label(comp.name)}]")
        lines.append("    end")

    if unassigned:
        lines.append("    subgraph ungrouped[Components]")
        for comp in unassigned:
            lines.append(f"        {_sid(comp.id)}[{_label(comp.name)}]")
        lines.append("    end")

    for cap in model.entities.capabilities:
        lines.append(f"    {_sid(cap.id)}({{{_label(cap.name)}}})")

    for rel in model.relationships:
        rtype = getattr(rel.type, 'value', rel.type)
        if rtype == "realizes":
            lines.append(f"    {_sid(rel.from_id)} ==>|realizes| {_sid(rel.to_id)}")

    return "\n".join(lines)
```

**Step 3:** Run: `pytest tests/test_visualize.py -v` — Expected: PASS

**Step 4:** Commit: `git add -u && git commit -m "feat: add components diagram generator"`

---

## Task 3: Add behaviors diagram

**Files:**
- Modify: `src/architecture_model/core/visualize.py`
- Modify: `tests/test_visualize.py`

**Step 1: Write failing test**

```python
from architecture_model.core.visualize import generate_behaviors_diagram

def test_behaviors_diagram():
    model = _make_model()
    diagram = generate_behaviors_diagram(model)
    assert diagram.startswith("flowchart LR")
    assert "Process Data" in diagram
```

**Step 2: Implement**

```python
def generate_behaviors_diagram(model: "ArchitectureModel") -> str:
    """Behavior flow: triggers/contains relationships between behaviors."""
    lines = ["flowchart LR"]

    for beh in model.entities.behaviors:
        lines.append(f"    {_sid(beh.id)}([{_label(beh.name)}])")

    beh_ids = {b.id for b in model.entities.behaviors}
    for rel in model.relationships:
        rtype = getattr(rel.type, 'value', rel.type)
        if rtype == "triggers" and rel.from_id in beh_ids and rel.to_id in beh_ids:
            lines.append(f"    {_sid(rel.from_id)} -->|triggers| {_sid(rel.to_id)}")
        elif rtype == "contains" and rel.from_id in beh_ids and rel.to_id in beh_ids:
            lines.append(f"    {_sid(rel.from_id)} -.->|contains| {_sid(rel.to_id)}")

    for rel in model.relationships:
        rtype = getattr(rel.type, 'value', rel.type)
        if rtype == "traces-to" and rel.to_id in beh_ids:
            comp = next((c for c in model.entities.components if c.id == rel.from_id), None)
            if comp:
                lines.append(f"    {_sid(comp.id)}[{_label(comp.name)}] -.->|traces-to| {_sid(rel.to_id)}")

    return "\n".join(lines)
```

**Step 3:** Run tests, commit: `git add -u && git commit -m "feat: add behaviors diagram generator"`

---

## Task 4: Add dependencies diagram

**Files:**
- Modify: `src/architecture_model/core/visualize.py`
- Modify: `tests/test_visualize.py`

**Step 1: Write failing test**

```python
from architecture_model.core.visualize import generate_dependencies_diagram

def test_dependencies_diagram():
    model = _make_model()
    diagram = generate_dependencies_diagram(model)
    assert diagram.startswith("flowchart LR")
    assert "depends-on" in diagram or "depends_on" in diagram
    assert "Processor" in diagram
    assert "Gateway" in diagram
```

**Step 2: Implement**

```python
def generate_dependencies_diagram(model: "ArchitectureModel") -> str:
    """Inter-component dependency graph grouped by f_block."""
    lines = ["flowchart LR"]

    fblock_groups: dict[str, list] = defaultdict(list)
    for comp in model.entities.components:
        fb = getattr(comp, 'f_block', None) or "ungrouped"
        fblock_groups[fb].append(comp)

    fblock_names: dict[str, str] = {}
    for cap in model.entities.capabilities:
        if hasattr(cap, 'f_block') and cap.f_block:
            fblock_names[cap.f_block] = cap.name

    for fb in sorted(fblock_groups):
        comps = fblock_groups[fb]
        label = fblock_names.get(fb, fb)
        lines.append(f"    subgraph {_sid(fb)}[{_label(label)}]")
        for comp in comps:
            lines.append(f"        {_sid(comp.id)}[{_label(comp.name)}]")
        lines.append("    end")

    for rel in model.relationships:
        rtype = getattr(rel.type, 'value', rel.type)
        if rtype == "depends-on":
            lines.append(f"    {_sid(rel.from_id)} -->|depends-on| {_sid(rel.to_id)}")

    return "\n".join(lines)
```

**Step 3:** Run tests, commit: `git add -u && git commit -m "feat: add dependencies diagram generator"`

---

## Task 5: Add orchestration function + generate all diagrams

**Files:**
- Modify: `src/architecture_model/core/visualize.py`
- Modify: `tests/test_visualize.py`

**Step 1: Write failing test**

```python
from architecture_model.core.visualize import generate_all_diagrams

def test_generate_all_diagrams(tmp_path):
    model = _make_model()
    generate_all_diagrams(model, tmp_path)
    assert (tmp_path / "context.mmd").exists()
    assert (tmp_path / "components.mmd").exists()
    assert (tmp_path / "behaviors.mmd").exists()
    assert (tmp_path / "dependencies.mmd").exists()
```

**Step 2: Implement**

```python
def generate_all_diagrams(model: "ArchitectureModel", output_dir: Path) -> dict[str, Path]:
    """Generate all 4 standard diagrams and write to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generators = {
        "context": generate_context_diagram,
        "components": generate_components_diagram,
        "behaviors": generate_behaviors_diagram,
        "dependencies": generate_dependencies_diagram,
    }
    paths = {}
    for name, gen_fn in generators.items():
        content = gen_fn(model)
        path = output_dir / f"{name}.mmd"
        path.write_text(content + "\n")
        paths[name] = path
    return paths
```

**Step 3:** Run tests, commit: `git add -u && git commit -m "feat: add generate_all_diagrams orchestration"`

---

## Task 6: Wire CLI + generate diagrams for all 7 models

**Files:**
- Modify: `src/architecture_model/cli/visualize.py` — replace with re-exports from core

**Step 1:** Replace `cli/visualize.py` with thin wrapper:

```python
"""CLI visualization — delegates to core.visualize."""
from ..core.visualize import (
    generate_context_diagram,
    generate_components_diagram,
    generate_behaviors_diagram,
    generate_dependencies_diagram,
    generate_all_diagrams,
)

__all__ = [
    "generate_context_diagram",
    "generate_components_diagram",
    "generate_behaviors_diagram",
    "generate_dependencies_diagram",
    "generate_all_diagrams",
]
```

**Step 2:** Generate diagrams for all 7 models:

```bash
python -c "
from pathlib import Path
from architecture_model.core.parser import load_model
from architecture_model.core.visualize import generate_all_diagrams

models_dir = Path('.architecture-models')
model = load_model(Path('.architecture-model.yaml'))
generate_all_diagrams(model, models_dir / 'diagrams')
print('top-level: 4 diagrams')

for system in ['core', 'manifest', 'config', 'cli', 'orchestration', 'extract']:
    model = load_model(models_dir / system / '.architecture-model.yaml')
    generate_all_diagrams(model, models_dir / system / 'diagrams')
    print(f'  {system}: 4 diagrams')
"
```

**Step 3:** Run full test suite: `pytest tests/ -v --ignore=tests/test_config_loader.py`

**Step 4:** Commit: `git add . && git commit -m "feat: generate Mermaid diagrams for all architecture models"`

---

## Task 7: Update CONTEXT.md

Add visualization step to "Standard Modeling Process" section after step 4 (Enrich):

```
5. **Visualize** — `generate_all_diagrams()` produces 4 Mermaid diagrams per model:
   - `context.mmd` — C4-style: actors → interfaces → system boundary
   - `components.mmd` — Components grouped by layer, realizes edges to capabilities
   - `behaviors.mmd` — Behavior flow with triggers/contains relationships
   - `dependencies.mmd` — Inter-component dependency graph
```

Commit: `git add CONTEXT.md && git commit -m "docs: document visualization step in standard process"`
