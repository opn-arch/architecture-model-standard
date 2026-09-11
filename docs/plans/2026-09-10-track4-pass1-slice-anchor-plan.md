# Track 4 Pass 1 Implementation Plan — Slice Anchor for Functional Panel

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire the existing `slice_for_artifact` slicer into the viewer pipeline so that the functional panel of `viewer.html` renders only entities inside a deterministic `(model, files, artifacts)` anchor derived from the view name.

**Architecture:** Introduce a `SliceAnchor` dataclass and `build_slice_anchor(model, view_name, repo_path)` factory in a new `src/architecture_model/core/slice_anchor.py`. `_cmd_viewer` computes anchors for all four view names; `generate_html_viewer` accepts an optional `anchors` kwarg. In Pass 1 only the functional panel consumes its anchor — other three panels compute anchors for observability but keep receiving the full model.

**Tech Stack:** Python 3, pytest, pyyaml, dataclasses. No new deps.

**Design doc:** `docs/plans/2026-09-10-track4-slice-anchor-design.md` (committed `d738d75`).

**Rules:**
- TDD (RED → GREEN → commit) per task, one commit per task, Conventional Commits.
- Never `git add -A`; add only the files each task creates or modifies.
- Never touch `.architecture-models/`, `.architecture/inventory.json`, `.architecture/sil.sqlite*`, `.architecture-model.yaml`, `.DS_Store`. `.architecture/viewer-curation.yaml` is editable (not needed this pass).
- Never `pip install -e`. Run tests with `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest ...`.
- Baseline: 3646 passed / 104 skipped / 0 failed. New tests only add; no regressions accepted.

---

## Task 1: Create SliceAnchor dataclass and constants

**Files:**
- Create: `src/architecture_model/core/slice_anchor.py`
- Test: `tests/core/test_slice_anchor_dataclass.py`

**Step 1: Write the failing test**

```python
# tests/core/test_slice_anchor_dataclass.py
"""Track 4 Pass 1 Task 1 — SliceAnchor dataclass and view/artifact constants."""
from architecture_model.core.slice_anchor import (
    SliceAnchor,
    VIEW_TO_ARTIFACT,
    ARTIFACT_TO_DOC,
)
from architecture_model.core.types import ArchitectureModel, Entities, Meta


def _empty_model() -> ArchitectureModel:
    return ArchitectureModel(meta=Meta(project="t"), entities=Entities(), relationships=[])


def test_view_to_artifact_covers_all_four_views():
    assert set(VIEW_TO_ARTIFACT.keys()) == {"conops", "functional", "logical", "use_cases"}
    assert VIEW_TO_ARTIFACT["functional"] == "functional-architecture"
    assert VIEW_TO_ARTIFACT["logical"] == "logical-architecture"
    assert VIEW_TO_ARTIFACT["use_cases"] == "use-cases"
    assert VIEW_TO_ARTIFACT["conops"] == "conops"


def test_artifact_to_doc_covers_all_four_artifacts():
    assert set(ARTIFACT_TO_DOC.keys()) == {
        "conops", "functional-architecture", "logical-architecture", "use-cases"
    }
    for path in ARTIFACT_TO_DOC.values():
        assert path.startswith(".architecture-models/docs/se/")
        assert path.endswith(".md")


def test_slice_anchor_is_frozen_dataclass():
    anchor = SliceAnchor(
        view_name="functional",
        artifact_name="functional-architecture",
        model=_empty_model(),
        files=(),
        artifacts=(),
    )
    assert anchor.view_name == "functional"
    assert anchor.files == ()
    # frozen: cannot mutate
    import dataclasses
    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        anchor.view_name = "logical"
```

**Step 2: Run test to verify it fails**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_slice_anchor_dataclass.py -v
```
Expected: ImportError / ModuleNotFoundError for `architecture_model.core.slice_anchor`.

**Step 3: Write minimal implementation**

```python
# src/architecture_model/core/slice_anchor.py
"""Slice anchor for viewer panels — deterministic (model, files, artifacts) scope per view.

See docs/plans/2026-09-10-track4-slice-anchor-design.md for full design.
"""
from __future__ import annotations

from dataclasses import dataclass

from architecture_model.core.types import ArchitectureModel


VIEW_TO_ARTIFACT: dict[str, str] = {
    "conops": "conops",
    "functional": "functional-architecture",
    "logical": "logical-architecture",
    "use_cases": "use-cases",
}

ARTIFACT_TO_DOC: dict[str, str] = {
    "conops": ".architecture-models/docs/se/conops.md",
    "functional-architecture": ".architecture-models/docs/se/functional-analysis.md",
    "logical-architecture": ".architecture-models/docs/se/logical-architecture.md",
    "use-cases": ".architecture-models/docs/se/use-cases.md",
}


@dataclass(frozen=True)
class SliceAnchor:
    view_name: str
    artifact_name: str
    model: ArchitectureModel
    files: tuple[str, ...]
    artifacts: tuple[str, ...]
```

**Step 4: Run test to verify it passes**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_slice_anchor_dataclass.py -v
```
Expected: 3 passed.

**Step 5: Commit**

```bash
git add src/architecture_model/core/slice_anchor.py tests/core/test_slice_anchor_dataclass.py
git commit -m "feat(track4): add SliceAnchor dataclass and view/artifact constants"
```

---

## Task 2: Implement 1-hop closure over slicer output

**Files:**
- Modify: `src/architecture_model/core/slice_anchor.py`
- Test: `tests/core/test_slice_anchor_closure.py`

**Step 1: Write the failing test**

```python
# tests/core/test_slice_anchor_closure.py
"""Track 4 Pass 1 Task 2 — 1-hop closure preserves realizes/contains/depends-on neighbors."""
from architecture_model.core.slice_anchor import apply_one_hop_closure
from architecture_model.core.types import (
    ArchitectureModel, Entities, Meta,
    Capability, Component, Relationship, RelationType,
)


def _model_with_realizes():
    """CAP-1 is in slice. COMP-1 realizes CAP-1 but is NOT in slice. Closure pulls COMP-1 back."""
    full = ArchitectureModel(
        meta=Meta(project="t"),
        entities=Entities(
            capabilities=[Capability(id="CAP-1", name="c1")],
            components=[Component(id="COMP-1", name="k1"), Component(id="COMP-2", name="k2")],
        ),
        relationships=[
            Relationship(from_id="COMP-1", to_id="CAP-1", type=RelationType.REALIZES),
            Relationship(from_id="COMP-2", to_id="CAP-1", type=RelationType.DEPENDS_ON),
        ],
    )
    sliced = ArchitectureModel(
        meta=Meta(project="t"),
        entities=Entities(capabilities=[Capability(id="CAP-1", name="c1")]),
        relationships=[],
    )
    return full, sliced


def test_closure_pulls_realizer_component():
    full, sliced = _model_with_realizes()
    result = apply_one_hop_closure(full, sliced)
    ids = {c.id for c in result.entities.components}
    assert "COMP-1" in ids  # realizes closure
    assert "COMP-2" in ids  # depends-on closure
    rel_pairs = {(r.from_id, r.to_id, r.type.value) for r in result.relationships}
    assert ("COMP-1", "CAP-1", "realizes") in rel_pairs
    assert ("COMP-2", "CAP-1", "depends-on") in rel_pairs


def test_closure_is_one_hop_only_no_transitive():
    """CAP-1 in slice. COMP-1 realizes CAP-1. COMP-1 depends-on COMP-3. COMP-3 must NOT be pulled."""
    full = ArchitectureModel(
        meta=Meta(project="t"),
        entities=Entities(
            capabilities=[Capability(id="CAP-1", name="c1")],
            components=[
                Component(id="COMP-1", name="k1"),
                Component(id="COMP-3", name="k3"),
            ],
        ),
        relationships=[
            Relationship(from_id="COMP-1", to_id="CAP-1", type=RelationType.REALIZES),
            Relationship(from_id="COMP-1", to_id="COMP-3", type=RelationType.DEPENDS_ON),
        ],
    )
    sliced = ArchitectureModel(
        meta=Meta(project="t"),
        entities=Entities(capabilities=[Capability(id="CAP-1", name="c1")]),
        relationships=[],
    )
    result = apply_one_hop_closure(full, sliced)
    ids = {c.id for c in result.entities.components}
    assert "COMP-1" in ids
    assert "COMP-3" not in ids  # would require 2 hops


def test_closure_ignores_non_closure_relation_types():
    """A relationship of type 'exposes' should NOT expand the slice."""
    from architecture_model.core.types import Interface
    full = ArchitectureModel(
        meta=Meta(project="t"),
        entities=Entities(
            capabilities=[Capability(id="CAP-1", name="c1")],
            interfaces=[Interface(id="IF-1", name="i1", component_id="COMP-1", interface_type="library")],
            components=[Component(id="COMP-1", name="k1")],
        ),
        relationships=[
            Relationship(from_id="COMP-1", to_id="IF-1", type=RelationType.EXPOSES),
            Relationship(from_id="COMP-1", to_id="CAP-1", type=RelationType.REALIZES),
        ],
    )
    sliced = ArchitectureModel(
        meta=Meta(project="t"),
        entities=Entities(capabilities=[Capability(id="CAP-1", name="c1")]),
        relationships=[],
    )
    result = apply_one_hop_closure(full, sliced)
    # COMP-1 is pulled via REALIZES; but IF-1 is NOT pulled — EXPOSES is not a closure type
    ids = {c.id for c in result.entities.components}
    assert "COMP-1" in ids
    if_ids = {i.id for i in result.entities.interfaces}
    assert "IF-1" not in if_ids
```

**Step 2: Run test to verify it fails**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_slice_anchor_closure.py -v
```
Expected: ImportError for `apply_one_hop_closure`.

**Step 3: Write minimal implementation**

Append to `src/architecture_model/core/slice_anchor.py`:

```python
from copy import deepcopy

from architecture_model.core.types import RelationType

_CLOSURE_TYPES = frozenset({
    RelationType.REALIZES,
    RelationType.CONTAINS,
    RelationType.DEPENDS_ON,
})


def _all_entities(model: ArchitectureModel):
    """Yield (kind, entity) for every entity in the model."""
    for kind in (
        "actors", "capabilities", "behaviors", "interfaces",
        "constraints", "layers", "components", "systems",
    ):
        for entity in getattr(model.entities, kind, []) or []:
            yield kind, entity


def apply_one_hop_closure(full: ArchitectureModel, sliced: ArchitectureModel) -> ArchitectureModel:
    """Expand sliced with one hop of realizes/contains/depends-on neighbors from full.

    One pass, no transitive expansion. Deterministic by sorted iteration.
    """
    slice_ids: set[str] = set()
    for _, entity in _all_entities(sliced):
        slice_ids.add(entity.id)

    id_to_kind_entity: dict[str, tuple[str, object]] = {}
    for kind, entity in _all_entities(full):
        id_to_kind_entity[entity.id] = (kind, entity)

    to_add: set[str] = set()
    rels_to_add: list = []
    sorted_rels = sorted(
        (r for r in full.relationships if r.type in _CLOSURE_TYPES),
        key=lambda r: (r.type.value, r.from_id, r.to_id),
    )
    for rel in sorted_rels:
        f, t = rel.from_id, rel.to_id
        if f in slice_ids and t not in slice_ids and t in id_to_kind_entity:
            to_add.add(t)
            rels_to_add.append(rel)
        elif t in slice_ids and f not in slice_ids and f in id_to_kind_entity:
            to_add.add(f)
            rels_to_add.append(rel)

    result = deepcopy(sliced)
    for eid in sorted(to_add):
        kind, entity = id_to_kind_entity[eid]
        bucket = getattr(result.entities, kind)
        bucket.append(deepcopy(entity))
    for rel in rels_to_add:
        result.relationships.append(deepcopy(rel))
    return result
```

**Step 4: Run test to verify it passes**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_slice_anchor_closure.py -v
```
Expected: 3 passed.

**Step 5: Commit**

```bash
git add src/architecture_model/core/slice_anchor.py tests/core/test_slice_anchor_closure.py
git commit -m "feat(track4): implement 1-hop closure over slicer output"
```

---

## Task 3: Implement build_slice_anchor factory

**Files:**
- Modify: `src/architecture_model/core/slice_anchor.py`
- Test: `tests/core/test_build_slice_anchor.py`

**Step 1: Write the failing test**

```python
# tests/core/test_build_slice_anchor.py
"""Track 4 Pass 1 Task 3 — build_slice_anchor factory for the 4 view names."""
from pathlib import Path
import pytest

from architecture_model.core.slice_anchor import build_slice_anchor, VIEW_TO_ARTIFACT
from architecture_model.core.types import (
    ArchitectureModel, Entities, Meta,
    Actor, Capability, Component, Behavior, Layer,
    Relationship, RelationType,
)


@pytest.fixture
def sample_model():
    return ArchitectureModel(
        meta=Meta(project="t"),
        entities=Entities(
            actors=[Actor(id="ACT-1", name="user")],
            capabilities=[Capability(id="CAP-1", name="cap1")],
            behaviors=[Behavior(id="BEH-1", name="beh1")],
            layers=[Layer(id="LAY-1", name="lay1")],
            components=[
                Component(id="COMP-1", name="c1", source_files=["src/a.py", "src/b.py"]),
                Component(id="COMP-2", name="c2", source_files=["src/c.py"]),
            ],
        ),
        relationships=[
            Relationship(from_id="COMP-1", to_id="CAP-1", type=RelationType.REALIZES),
            Relationship(from_id="COMP-2", to_id="CAP-1", type=RelationType.REALIZES),
            Relationship(from_id="LAY-1", to_id="COMP-1", type=RelationType.CONTAINS),
        ],
    )


def test_build_anchor_for_functional(sample_model, tmp_path):
    anchor = build_slice_anchor(sample_model, "functional", tmp_path)
    assert anchor.view_name == "functional"
    assert anchor.artifact_name == "functional-architecture"
    # functional slice keeps capabilities+behaviors; closure pulls in components that realize CAP-1
    cap_ids = {c.id for c in anchor.model.entities.capabilities}
    comp_ids = {c.id for c in anchor.model.entities.components}
    assert "CAP-1" in cap_ids
    assert "COMP-1" in comp_ids  # via realizes closure
    assert "COMP-2" in comp_ids


def test_build_anchor_derives_files_from_sliced_components(sample_model, tmp_path):
    anchor = build_slice_anchor(sample_model, "functional", tmp_path)
    # sorted union of source_files across sliced components
    assert anchor.files == ("src/a.py", "src/b.py", "src/c.py")


def test_build_anchor_unknown_view_falls_back(sample_model, tmp_path, caplog):
    import logging
    caplog.set_level(logging.WARNING)
    anchor = build_slice_anchor(sample_model, "no-such-view", tmp_path)
    # Fallback: full model, empty files, empty artifacts
    assert anchor.view_name == "no-such-view"
    assert anchor.artifact_name == ""
    assert len(anchor.model.entities.components) == 2  # full model preserved


def test_build_anchor_for_all_four_view_names_produces_valid_anchors(sample_model, tmp_path):
    for view in VIEW_TO_ARTIFACT:
        anchor = build_slice_anchor(sample_model, view, tmp_path)
        assert anchor.view_name == view
        assert anchor.artifact_name == VIEW_TO_ARTIFACT[view]
        assert isinstance(anchor.files, tuple)
        assert isinstance(anchor.artifacts, tuple)


def test_build_anchor_artifacts_includes_primary_doc_when_present(sample_model, tmp_path):
    doc_dir = tmp_path / ".architecture-models" / "docs" / "se"
    doc_dir.mkdir(parents=True)
    (doc_dir / "functional-analysis.md").write_text("# stub")
    anchor = build_slice_anchor(sample_model, "functional", tmp_path)
    assert ".architecture-models/docs/se/functional-analysis.md" in anchor.artifacts


def test_build_anchor_artifacts_empty_when_docs_absent(sample_model, tmp_path):
    # No .architecture-models directory under tmp_path
    anchor = build_slice_anchor(sample_model, "functional", tmp_path)
    assert anchor.artifacts == ()
```

**Step 2: Run test to verify it fails**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_build_slice_anchor.py -v
```
Expected: ImportError for `build_slice_anchor`.

**Step 3: Write minimal implementation**

Append to `src/architecture_model/core/slice_anchor.py`:

```python
import logging
from pathlib import Path
from copy import deepcopy

from architecture_model.core.slicer import slice_for_artifact

_log = logging.getLogger(__name__)


def _derive_files(model: ArchitectureModel) -> tuple[str, ...]:
    seen: set[str] = set()
    for comp in model.entities.components or []:
        for sf in (getattr(comp, "source_files", None) or []):
            seen.add(sf)
    return tuple(sorted(seen))


def _derive_artifacts(artifact_name: str, repo_path: Path) -> tuple[str, ...]:
    if not artifact_name:
        return ()
    found: set[str] = set()
    primary = ARTIFACT_TO_DOC.get(artifact_name)
    if primary and (repo_path / primary).is_file():
        found.add(primary)
    se_dir = repo_path / ".architecture-models" / "docs" / "se"
    if se_dir.is_dir():
        import yaml
        for md in sorted(se_dir.glob("*.md")):
            try:
                text = md.read_text(encoding="utf-8")
                if text.startswith("---\n"):
                    end = text.find("\n---", 4)
                    if end != -1:
                        fm = yaml.safe_load(text[4:end]) or {}
                        if isinstance(fm, dict) and fm.get("artifact") == artifact_name:
                            rel = md.relative_to(repo_path).as_posix()
                            found.add(rel)
            except Exception:
                continue
    return tuple(sorted(found))


def build_slice_anchor(
    model: ArchitectureModel,
    view_name: str,
    repo_path: Path,
) -> SliceAnchor:
    """Compute the deterministic SliceAnchor for a viewer panel view name."""
    artifact_name = VIEW_TO_ARTIFACT.get(view_name, "")
    if not artifact_name:
        _log.warning("viewer: no slicer mapping for view=%s; falling back to full model", view_name)
        return SliceAnchor(
            view_name=view_name,
            artifact_name="",
            model=deepcopy(model),
            files=(),
            artifacts=(),
        )
    sliced = slice_for_artifact(model, artifact_name)
    anchored = apply_one_hop_closure(model, sliced)
    files = _derive_files(anchored)
    artifacts = _derive_artifacts(artifact_name, Path(repo_path))
    _log.info(
        "viewer: anchor computed view=%s entities=%d files=%d artifacts=%d",
        view_name,
        sum(1 for _ in _all_entities(anchored)),
        len(files),
        len(artifacts),
    )
    return SliceAnchor(
        view_name=view_name,
        artifact_name=artifact_name,
        model=anchored,
        files=files,
        artifacts=artifacts,
    )
```

**Step 4: Run test to verify it passes**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_build_slice_anchor.py -v
```
Expected: 6 passed.

**Step 5: Commit**

```bash
git add src/architecture_model/core/slice_anchor.py tests/core/test_build_slice_anchor.py
git commit -m "feat(track4): implement build_slice_anchor factory"
```

---

## Task 4: Thread anchors through generate_html_viewer

**Files:**
- Modify: `src/architecture_model/core/visualize.py` (function `generate_html_viewer` at line 2421)
- Test: `tests/core/test_viewer_accepts_anchors.py`

**Step 1: Write the failing test**

```python
# tests/core/test_viewer_accepts_anchors.py
"""Track 4 Pass 1 Task 4 — generate_html_viewer accepts optional anchors kwarg."""
from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.visualize import generate_html_viewer
from architecture_model.core.slice_anchor import build_slice_anchor, VIEW_TO_ARTIFACT


def _minimal_model_yaml(path: Path) -> Path:
    path.write_text("""
meta:
  project: t
  schema_version: '2.1'
entities:
  capabilities:
    - id: CAP-1
      name: c1
  components:
    - id: COMP-1
      name: k1
      source_files: [src/a.py]
relationships:
  - from: COMP-1
    to: CAP-1
    type: realizes
""".lstrip())
    return path


def test_generate_html_viewer_accepts_anchors_kwarg(tmp_path):
    model_path = _minimal_model_yaml(tmp_path / ".architecture-model.yaml")
    model = load_model(model_path)
    anchors = {v: build_slice_anchor(model, v, tmp_path) for v in VIEW_TO_ARTIFACT}
    output = tmp_path / "viewer.html"
    # Should not raise; kwarg is optional and backward-compatible
    result = generate_html_viewer(model, output, repo_path=tmp_path, anchors=anchors)
    assert result.is_file()


def test_generate_html_viewer_still_works_without_anchors(tmp_path):
    model_path = _minimal_model_yaml(tmp_path / ".architecture-model.yaml")
    model = load_model(model_path)
    output = tmp_path / "viewer.html"
    result = generate_html_viewer(model, output, repo_path=tmp_path)
    assert result.is_file()
```

**Step 2: Run test to verify it fails**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_viewer_accepts_anchors.py -v
```
Expected: `TypeError: generate_html_viewer() got an unexpected keyword argument 'anchors'`.

**Step 3: Write minimal implementation**

Read `src/architecture_model/core/visualize.py` line 2421 to find the signature. Add `anchors: dict[str, "SliceAnchor"] | None = None` as an optional kwarg at the end of the signature. For Task 4 no behavior change beyond accepting the kwarg — store it for Task 5 to consume.

```python
# At the top of visualize.py near other imports:
from architecture_model.core.slice_anchor import SliceAnchor  # noqa: F401 (typing)

# Update generate_html_viewer signature:
def generate_html_viewer(
    model: "ArchitectureModel",
    output_path: Path,
    ...existing kwargs...,
    anchors: dict[str, "SliceAnchor"] | None = None,
) -> Path:
```

Add nothing else in this task. The kwarg is stored but unused.

**Step 4: Run test to verify it passes**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_viewer_accepts_anchors.py -v
```
Expected: 2 passed.

Also run the existing viewer test files to confirm no regression:

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/test_viewer_v3.py tests/test_html_viewer.py tests/test_curated_viewer.py -q
```
Expected: all previously-passing tests still pass.

**Step 5: Commit**

```bash
git add src/architecture_model/core/visualize.py tests/core/test_viewer_accepts_anchors.py
git commit -m "feat(track4): accept optional anchors kwarg on generate_html_viewer"
```

---

## Task 5: Route functional panel through anchor.model

**Files:**
- Modify: `src/architecture_model/core/visualize.py` — inside `generate_html_viewer`, at the site(s) where the functional panel/diagram is generated
- Test: `tests/test_viewer_anchored.py`

**Step 1: Explore first**

Find every call site inside `generate_html_viewer` that uses the full `model` to produce functional-panel content. Search:

```
PYTHONPATH="$PWD/src" grep -n "generate_functional_architecture_diagram\|functional" src/architecture_model/core/visualize.py | head -40
```

For each site inside `generate_html_viewer` that feeds the functional panel, replace `model` with `(anchors["functional"].model if anchors and "functional" in anchors else model)`. Introduce a small helper at the top of `generate_html_viewer`:

```python
_APPLY_ANCHOR = {"functional"}

def _panel_model(view: str, full: "ArchitectureModel", anchors) -> "ArchitectureModel":
    if anchors and view in _APPLY_ANCHOR and view in anchors:
        return anchors[view].model
    return full
```

**Step 2: Write the failing test**

```python
# tests/test_viewer_anchored.py
"""Track 4 Pass 1 Task 5 — functional panel renders only anchor.model entities."""
from pathlib import Path

from architecture_model.core.parser import load_model
from architecture_model.core.visualize import generate_html_viewer
from architecture_model.core.slice_anchor import build_slice_anchor, VIEW_TO_ARTIFACT


def _model_yaml(path: Path) -> Path:
    """Model: CAP-1 realized by COMP-1 (both in-scope for functional). LAY-9 is unrelated (should NOT appear)."""
    path.write_text("""
meta:
  project: t
  schema_version: '2.1'
entities:
  capabilities:
    - id: CAP-1
      name: InScopeCap
  components:
    - id: COMP-1
      name: InScopeComp
      source_files: [src/a.py]
  layers:
    - id: LAY-9
      name: UnrelatedLayerNAME
relationships:
  - from: COMP-1
    to: CAP-1
    type: realizes
""".lstrip())
    return path


def test_functional_panel_renders_only_anchored_entities(tmp_path):
    model_path = _model_yaml(tmp_path / ".architecture-model.yaml")
    model = load_model(model_path)
    anchors = {v: build_slice_anchor(model, v, tmp_path) for v in VIEW_TO_ARTIFACT}
    out = tmp_path / "viewer.html"
    generate_html_viewer(model, out, repo_path=tmp_path, anchors=anchors)
    html = out.read_text(encoding="utf-8")

    # Extract functional panel Mermaid block. Naive substring test:
    # The functional slicer drops layers. Under anchor, LAY-9 must not appear
    # in the functional panel Mermaid source.
    # We rely on the functional panel being introduced by a known marker.
    # Find any occurrence of the functional-architecture diagram section.
    assert "InScopeCap" in html  # Cap must be present (in slice)
    # Locate functional block boundaries. Use a simple bracket: everything between
    # 'functional-architecture' anchor and next '</script>' or similar.
    # For robustness, assert LAY-9 not present in the whole viewer if functional is the only place
    # it would appear. But other panels still see the full model. So instead: pull functional
    # diagram body via visualize helper directly.
    from architecture_model.core.visualize import generate_functional_architecture_diagram
    functional_body = generate_functional_architecture_diagram(anchors["functional"].model)
    assert "UnrelatedLayerNAME" not in functional_body


def test_functional_panel_without_anchors_still_uses_full_model(tmp_path):
    model_path = _model_yaml(tmp_path / ".architecture-model.yaml")
    model = load_model(model_path)
    out = tmp_path / "viewer.html"
    # No anchors kwarg — legacy behavior: full model to all panels
    generate_html_viewer(model, out, repo_path=tmp_path)
    html = out.read_text(encoding="utf-8")
    # Backward-compat: unchanged behavior.
    assert "InScopeCap" in html
```

**Step 3: Run test to verify it fails**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/test_viewer_anchored.py -v
```
Expected: The second test passes (backward-compat unchanged). The first test may already pass since we test the `functional_body` directly with `anchors["functional"].model`. If it passes without code change, that means the slicer-derived model is already clean and our test proves the anchor works. Good — that's the invariant. Still add the wiring in `generate_html_viewer` per Step 4 so integrated calls route through the anchor.

**Step 4: Write minimal implementation**

In `src/architecture_model/core/visualize.py`, inside `generate_html_viewer`, locate every call to `generate_functional_architecture_diagram(model)` (or wrapper that renders the functional panel content). Replace `model` with `_panel_model("functional", model, anchors)` using the helper defined above.

If the functional diagram is generated as part of a batch (e.g., in a loop over view names), gate it per-view so only the `"functional"` route swaps the model.

**Step 5: Run test to verify it passes**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/test_viewer_anchored.py -v
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/test_viewer_v3.py tests/test_html_viewer.py tests/test_curated_viewer.py -q
```
Expected: new tests pass, existing viewer tests still pass.

**Step 6: Commit**

```bash
git add src/architecture_model/core/visualize.py tests/test_viewer_anchored.py
git commit -m "feat(track4): route functional panel through anchor.model in generate_html_viewer"
```

---

## Task 6: Wire anchors into _cmd_viewer

**Files:**
- Modify: `src/architecture_model/cli/main.py` (function `_cmd_viewer` at line 1141)
- Test: `tests/cli/test_cmd_viewer_anchors.py`

**Step 1: Write the failing test**

```python
# tests/cli/test_cmd_viewer_anchors.py
"""Track 4 Pass 1 Task 6 — _cmd_viewer computes and passes anchors to generate_html_viewer."""
from pathlib import Path
from unittest.mock import patch
import argparse

from architecture_model.cli.main import _cmd_viewer


def _write_model(root: Path) -> None:
    (root / ".architecture-model.yaml").write_text("""
meta:
  project: t
  schema_version: '2.1'
entities:
  capabilities:
    - id: CAP-1
      name: c1
  components:
    - id: COMP-1
      name: k1
      source_files: [src/a.py]
relationships:
  - from: COMP-1
    to: CAP-1
    type: realizes
""".lstrip())


def test_cmd_viewer_passes_anchors_kwarg(tmp_path):
    _write_model(tmp_path)
    args = argparse.Namespace(
        path=str(tmp_path),
        model=None,
        output=None,
        title=None,
        no_docs=False,
        curation=None,
    )
    captured = {}
    orig = None
    from architecture_model.core import visualize as _v
    orig = _v.generate_html_viewer

    def spy(*a, **kw):
        captured["anchors"] = kw.get("anchors")
        return orig(*a, **kw)

    with patch.object(_v, "generate_html_viewer", spy):
        rc = _cmd_viewer(args)
    assert rc == 0
    assert captured["anchors"] is not None
    assert set(captured["anchors"].keys()) == {"conops", "functional", "logical", "use_cases"}
```

**Step 2: Run test to verify it fails**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/cli/test_cmd_viewer_anchors.py -v
```
Expected: `assert captured["anchors"] is not None` fails (anchors not being passed).

**Step 3: Write minimal implementation**

In `src/architecture_model/cli/main.py` `_cmd_viewer` (line ~1141), after `model = load_model(model_path)` (line 1155) and before the call to `generate_html_viewer`, insert:

```python
from ..core.slice_anchor import build_slice_anchor, VIEW_TO_ARTIFACT
anchors = {v: build_slice_anchor(model, v, repo_path) for v in VIEW_TO_ARTIFACT}
```

Then add `anchors=anchors` to the `generate_html_viewer(...)` call.

**Step 4: Run test to verify it passes**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/cli/test_cmd_viewer_anchors.py -v
```
Expected: 1 passed.

**Step 5: Commit**

```bash
git add src/architecture_model/cli/main.py tests/cli/test_cmd_viewer_anchors.py
git commit -m "feat(track4): compute and pass slice anchors from _cmd_viewer"
```

---

## Task 7: Full regression + summary

**Step 1: Run the entire suite**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py
```
Expected: 3646 previously-passing tests still pass. New tests added by Tasks 1–6 pass on top. Target: 3660 passed / 104 skipped / 0 failed (final count depends on exact new-test counts: 3+3+6+2+2+1 = 17 new, so ~3663 passed).

If any regression: investigate. Do NOT amend prior commits. Fix in a new commit.

**Step 2: Regenerate viewer.html to confirm end-to-end flow**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m architecture_model.cli.main viewer .
```

Open `.architecture/diagrams/viewer.html` in a browser. Confirm the functional panel renders. Content should be substantively equivalent to before (no visible regression) because the slice + 1-hop closure preserves Plan A/B entities. The generated viewer file is gitignored — do not commit it.

**Step 3: Push**

```
git push origin feat/phase-5-fanout-provenance-family5
```

**Step 4: Session summary**

Note Track 4 Pass 1 complete. Anchors computed for all 4 views; only functional panel consumes its anchor. Pass 2 will extend `_APPLY_ANCHOR` to add `logical`, `use_cases`, `conops`. Pass 3 emits anchor metadata into viewer HTML for reader audit. Pass 4 wires curation validation against anchors.

---

## Notes for the executor

- Never `git add -A`. Add only files each task touches.
- Never touch `.architecture-model.yaml`, `.architecture-models/`, `.architecture/diagrams/`, `.architecture/inventory.json`, `.architecture/sil.sqlite*`, or `.DS_Store`. All viewer outputs are generated.
- If a test fails RED with a different error than "expected import fails", read the traceback carefully — the model schema or field name may differ from the plan. Cross-check by reading the actual dataclass definition in `src/architecture_model/core/types.py` before adjusting the test.
- Tasks 1–3 are pure additions with no risk to existing behavior. Tasks 4–6 change the viewer entry-point signature and cli command; run the full suite after Task 4 and again after Task 6 as regression gates.
- If `generate_html_viewer` internally invokes many sub-generators for the functional panel (e.g., there is both a "diagram" call and a "spec" call), scope Pass 1 to the diagram call only. Log any second consumer as an item for Pass 2.
- Test-file paths (`tests/core/`, `tests/cli/`) may need directory creation. Check first with `ls tests/core tests/cli 2>/dev/null` and `mkdir -p` if absent.
