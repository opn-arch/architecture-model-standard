# Phase 3: Recursion + Entity Views — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the eight-family view taxonomy fractally recursive: every entity in the model is projectable as a "system-of-interest" at its own scale. Add entity-scoped slicing, scope chains on projected views, per-family per-entity-kind projectors, and depth control — so drill-downs become first-class re-projections rather than ad-hoc navigation.

**Architecture:** Introduce `slice_by_entity(model, entity_id)` returning the transitive-closure sub-model rooted at an entity. Extend `ModelSlice.scope` to include `entity(<id>)` scoping. Every `ProjectedView` gains a `scope_chain`, `parent`, `peers`, and `roll_up` field so renderers can emit breadcrumbs and drill-up links. Add ~40 entity-page projectors keyed as `familyN.entity_page` and dispatch by entity kind. Every ViewSpec gains `depth: int` and `expand_kinds: list[EntityKind]` to control recursion.

**Tech Stack:** Python 3.11+, pytest, existing Phase 1 registry + Phase 2 semantic fields, existing slicer (`slice_by_fblock`, `slice_by_layer`).

**Repos affected:**
- `architecture-model-standard` (ams) — slicer extension, projected-view metadata, entity-page projectors, ViewSpec extensions
- `opencode-arch` (oca) — expose entity-scoped `architect_slice`, extend `architect_docs` DEFAULT_SPECS for entity pages, drill-down navigation in evaluate output

**Depends on:**
- Phase 1 merged: projector registry, invalidation module, per-subsystem loop
- Phase 2 merged: semantic fields (entity F1/F7 views depend on them), supplementary_refs, overlays

**Related skills:**
- @superpowers:test-driven-development for every task
- @superpowers:verification-before-completion before each commit
- @superpowers:subagent-driven-development for execution mode

**Baselines to preserve (post-Phase-2):**
- ams — baseline + Phase 1 + Phase 2 tests, all green
- oca — baseline + Phase 1 + Phase 2 tests, all green

**Branching:**
- ams: `feat/model-view-mapping-phase-3` off `main` (after Phase 2 merge)
- oca: `feat/model-view-mapping-phase-3` off `main` (after Phase 2 merge)

**Guardrails (rigid):**
- Never `git add -A`; stage each file explicitly.
- Never touch `.architecture*` telemetry directories.
- Never `pip install -e`; use PYTHONPATH pattern.
- One commit per task; Conventional Commit format.
- Verify test baseline before AND after each commit.

---

## Task Sequence Overview

| # | Task | Repo | Behavior change? |
|---|---|:-:|:-:|
| 1 | `slice_by_entity(model, entity_id)` — transitive closure | ams | Additive |
| 2 | `ModelSlice.scope` extension: `entity(<id>)` scoping | ams | Additive |
| 3 | Materializer wiring for entity-scoped slices | ams | Additive |
| 4 | `ProjectedView.scope_chain`, `parent`, `peers`, `roll_up` | ams | Additive |
| 5 | `ViewSpec.depth` + `expand_kinds` fields | ams | Additive |
| 6 | Depth-limit enforcement in materializer | ams | Additive |
| 7 | Entity-page projector registry convention (`familyN.entity_page`) + kind dispatch | ams | Additive |
| 8 | Family 1 entity_page projector (per-entity mission/purpose) | ams | Additive |
| 9 | Family 2 entity_page projector (per-entity functional decomposition) | ams | Additive |
| 10 | Family 3 entity_page projector (per-entity structural — parts + depends-on) | ams | Additive |
| 11 | Family 4 entity_page projector (per-entity scenarios) | ams | Additive |
| 12 | Family 6 entity_page projector (per-entity interfaces + ICD) | ams | Additive |
| 13 | Family 7 entity_page projector (per-entity quality + verification + FMEA) | ams | Additive |
| 14 | Family 8 entity_page projector (per-entity health + revision history) | ams | Additive |
| 15 | Entity-page determinism guard (parametrized over 7 families × 3 sample entity kinds) | ams | Test-only |
| 16 | Drill-down link emission: each root-family view emits `{drill_to: entity_id}` in diagram_spec | ams | Additive |
| 17 | Renderer support for scope_chain breadcrumb + drill-up link | ams | Additive |
| 18 | Invalidation rules for entity-scoped views (parent + peers rebuild when child changes) | ams | Additive |
| 19 | MCP: `architect_slice` accepts `entity=<id>` focus | oca | Additive |
| 20 | MCP: `architect_docs` DEFAULT_SPECS gains entity-page variants (opt-in per-entity spec generator) | oca | Additive |
| 21 | MCP: `architect_evaluate` output includes drill-down link map | oca | Additive |
| 22 | CONTEXT.md refresh — ams (recursion, entity views, depth) | ams | Docs |
| 23 | CONTEXT.md refresh — oca (entity-scoped slice + docs) | oca | Docs |
| 24 | Full-suite verification pass — both repos | both | Verification |

---

## Task 1 — `slice_by_entity(model, entity_id)`

**Rationale:** Root primitive for recursion. Given an entity ID, return a sub-model containing that entity, all entities reachable via `contains` (down), and all entities related via `realizes`/`exposes`/`consumes`/`depends-on` at one hop (so the sub-view has context). Higher-hop context comes from parent/peer metadata (Task 4), not from the slice itself.

**Files:**
- Modify: `src/architecture_model/core/slicer.py`
- Test: `tests/core/test_slice_by_entity.py`

**Contract:**

```python
def slice_by_entity(
    model: ArchitectureModel,
    entity_id: str,
    *,
    include_hops: int = 1,
) -> ArchitectureModel:
    """Return the sub-model rooted at `entity_id`.

    Includes:
      - The entity itself
      - Transitive `contains` descendants (unbounded)
      - Direct related entities via realizes/exposes/consumes/depends-on
        up to `include_hops` (default 1, deterministic BFS by (kind, id))
      - All relationships whose both endpoints are included
    """
```

**Test:**

```python
def test_slice_by_entity_includes_entity_and_contains_descendants(model_with_hierarchy):
    # model has COMP-1 contains COMP-1.1 contains COMP-1.1.1
    sub = slice_by_entity(model_with_hierarchy, "COMP-1")
    ids = {c.id for c in sub.components}
    assert ids == {"COMP-1", "COMP-1.1", "COMP-1.1.1"}


def test_slice_by_entity_includes_realized_capabilities(model_with_realizes):
    # COMP-3 realizes CAP-F2
    sub = slice_by_entity(model_with_realizes, "COMP-3")
    assert "CAP-F2" in {c.id for c in sub.capabilities}


def test_slice_by_entity_excludes_unrelated_entities(broad_model):
    sub = slice_by_entity(broad_model, "COMP-3")
    assert "COMP-99" not in {c.id for c in sub.components}


def test_slice_by_entity_respects_include_hops(chained_deps_model):
    # COMP-A depends-on COMP-B depends-on COMP-C depends-on COMP-D
    hop1 = slice_by_entity(chained_deps_model, "COMP-A", include_hops=1)
    assert {c.id for c in hop1.components} == {"COMP-A", "COMP-B"}
    hop2 = slice_by_entity(chained_deps_model, "COMP-A", include_hops=2)
    assert {c.id for c in hop2.components} == {"COMP-A", "COMP-B", "COMP-C"}


def test_slice_by_entity_relationships_have_both_endpoints_in_sub(model_with_hierarchy):
    sub = slice_by_entity(model_with_hierarchy, "COMP-1")
    ids = {e.id for e in sub.all_entities()}
    for r in sub.relationships:
        assert r.from_ in ids and r.to in ids


def test_slice_by_entity_missing_id_raises(broad_model):
    with pytest.raises(KeyError):
        slice_by_entity(broad_model, "COMP-DOES-NOT-EXIST")
```

**Commit:**

```bash
git add tests/core/test_slice_by_entity.py src/architecture_model/core/slicer.py
git commit -m "feat(slicer): add slice_by_entity for entity-scoped sub-models"
```

---

## Task 2 — `ModelSlice.scope` extension: `entity(<id>)`

**Files:**
- Modify: `src/architecture_model/lifecycle/model_slice.py`
- Test: `tests/lifecycle/test_slice_entity_scope.py`

**Contract:** `scope` is a str Literal today (`"local" | "descendants" | "federated"`). Change to accept either a Literal or a string of form `"entity(<id>)"`. Add parser: `parse_entity_scope(s: str) -> str | None` returning the ID or `None` if not entity-scoped. Validation: entity ID must match `[A-Z][A-Z0-9-]*(\.\d+)*` (matches existing entity ID pattern).

**Digest input:** the raw scope string is fed into the slice digest as-is; entity IDs are preserved verbatim.

**Test:**

```python
def test_slice_entity_scope_round_trip():
    s = ModelSlice(id="s1", architecture_id="a1", model_revision="0000001",
                   scope="entity(COMP-3)", shared_refs="none")
    d = s.to_dict()
    assert d["scope"] == "entity(COMP-3)"
    assert ModelSlice.from_dict(d) == s


def test_parse_entity_scope():
    from architecture_model.lifecycle.model_slice import parse_entity_scope
    assert parse_entity_scope("entity(COMP-3)") == "COMP-3"
    assert parse_entity_scope("entity(CAP-F1.2)") == "CAP-F1.2"
    assert parse_entity_scope("local") is None
    assert parse_entity_scope("entity()") is None
    assert parse_entity_scope("entity(bad id)") is None


def test_entity_scope_digest_stable():
    s1 = ModelSlice(..., scope="entity(COMP-3)")
    s2 = ModelSlice(..., scope="entity(COMP-3)")
    assert s1.digest() == s2.digest()
    s3 = ModelSlice(..., scope="entity(COMP-4)")
    assert s1.digest() != s3.digest()
```

**Commit:**

```bash
git add tests/lifecycle/test_slice_entity_scope.py src/architecture_model/lifecycle/model_slice.py
git commit -m "feat(slice): accept 'entity(<id>)' scope form"
```

---

## Task 3 — Materializer wiring for entity-scoped slices

**Files:**
- Modify: `src/architecture_model/lifecycle/model_slice_materializer.py`
- Test: `tests/lifecycle/test_materialize_entity_scope.py`

**Behavior:** When `slice.scope` matches `entity(<id>)`, materializer invokes `slice_by_entity(model, id, include_hops=slice.selectors.get("hops", 1))` and continues as normal.

**Commit:**

```bash
git add tests/lifecycle/test_materialize_entity_scope.py src/architecture_model/lifecycle/model_slice_materializer.py
git commit -m "feat(materializer): resolve entity-scoped slices via slice_by_entity"
```

---

## Task 4 — `ProjectedView.scope_chain`, `parent`, `peers`, `roll_up`

**Files:**
- Modify: `src/architecture_model/lifecycle/projected_view.py` (or wherever `ProjectedView` is defined)
- Test: `tests/lifecycle/test_projected_view_scope_metadata.py`

**Contract:**

```python
@dataclass(frozen=True)
class ProjectedView:
    ...existing fields...
    scope_chain: tuple[str, ...] = ()   # e.g., ("ROOT", "COMP-1", "COMP-1.2")
    parent: str | None = None           # entity id of parent by `contains`
    peers: tuple[str, ...] = ()         # sibling entity ids at same scope
    roll_up: bool = False               # True if data aggregated from children
```

Computed by the projector during projection. `parent` and `peers` derived from the model's `contains` graph. `scope_chain` unfolded from the top of the containment tree down.

**Test:**

```python
def test_entity_scoped_view_has_scope_chain(model_with_hierarchy):
    # COMP-1 contains COMP-1.2 contains COMP-1.2.3
    view = project(materialize(slice_(scope="entity(COMP-1.2.3)"), model), ViewSpec(...))
    assert view.scope_chain == ("ROOT", "COMP-1", "COMP-1.2", "COMP-1.2.3")
    assert view.parent == "COMP-1.2"
    assert "COMP-1.2.4" in view.peers  # sibling of COMP-1.2.3


def test_root_scoped_view_has_empty_scope_chain(model):
    view = project(materialize(slice_(scope="local"), model), ViewSpec(...))
    assert view.scope_chain == ()
    assert view.parent is None
    assert view.peers == ()
    assert view.roll_up is False
```

**Commit:**

```bash
git add tests/lifecycle/test_projected_view_scope_metadata.py src/architecture_model/lifecycle/projected_view.py
git commit -m "feat(projected-view): add scope_chain, parent, peers, roll_up metadata"
```

---

## Task 5 — `ViewSpec.depth` + `expand_kinds`

**Files:**
- Modify: `src/architecture_model/lifecycle/view_spec.py`
- Test: `tests/lifecycle/test_view_spec_depth.py`

**Contract:**

```python
@dataclass(frozen=True)
class ViewSpec:
    ...existing fields...
    depth: int = 1                              # how many contains levels to descend
    expand_kinds: tuple[str, ...] = ()          # which entity kinds recurse (empty = all)
```

Validation: `depth >= 0`; `depth == 0` means only the scope root, no children rendered.

**Commit:**

```bash
git add tests/lifecycle/test_view_spec_depth.py src/architecture_model/lifecycle/view_spec.py
git commit -m "feat(view-spec): add depth and expand_kinds recursion controls"
```

---

## Task 6 — Depth-limit enforcement in materializer

**Rationale:** Materializer already computes transitive closure for entity scope; add depth pruning after closure. Children beyond `depth` are represented as opaque stub entities (id + name + kind) with no relationships or nested content.

**Files:**
- Modify: `src/architecture_model/lifecycle/model_slice_materializer.py`
- Test: `tests/lifecycle/test_depth_enforcement.py`

**Test:**

```python
def test_depth_zero_returns_only_scope_root(model_with_hierarchy):
    view_spec = ViewSpec(..., depth=0)
    mslice = materialize(slice_(scope="entity(COMP-1)"), model, view_spec=view_spec)
    ids = {e.id for e in mslice.fragment.components}
    assert ids == {"COMP-1"}


def test_depth_one_includes_direct_children(model_with_hierarchy):
    view_spec = ViewSpec(..., depth=1)
    mslice = materialize(slice_(scope="entity(COMP-1)"), model, view_spec=view_spec)
    ids = {e.id for e in mslice.fragment.components}
    assert "COMP-1" in ids and "COMP-1.1" in ids
    # But not grandchildren:
    assert "COMP-1.1.1" not in ids


def test_expand_kinds_restricts_recursion(mixed_model):
    view_spec = ViewSpec(..., depth=3, expand_kinds=("Component",))
    mslice = materialize(slice_(scope="entity(COMP-1)"), mixed_model, view_spec=view_spec)
    # Capabilities contained by COMP-1 are NOT recursed (not in expand_kinds)
    caps = {c.id for c in mslice.fragment.capabilities}
    assert "CAP-F1" in caps  # direct child appears
    # ... but its sub-capabilities do NOT
```

**Commit:**

```bash
git add tests/lifecycle/test_depth_enforcement.py src/architecture_model/lifecycle/model_slice_materializer.py
git commit -m "feat(materializer): enforce depth and expand_kinds on entity-scoped slices"
```

---

## Task 7 — Entity-page projector registry convention + kind dispatch

**Rationale:** Rather than register `family3.entity_page.component`, `family3.entity_page.capability`, … as separate projectors (14 kinds × 7 families = 98 names), register one projector per family named `familyN.entity_page` that dispatches internally by `mslice.fragment.scope_entity.kind`.

**Files:**
- Modify: `src/architecture_model/lifecycle/view_projection.py` (or wherever projector base helpers live)
- Create: `src/architecture_model/lifecycle/projectors/entity_pages.py`
- Test: `tests/lifecycle/test_entity_page_dispatch.py`

**Contract:**

```python
class EntityPageProjector(Projector):
    """Base class: dispatches project() to _project_<kind>() by scope-entity kind."""

    family: int   # 1..8

    def project(self, mslice: MaterializedSlice, spec: ViewSpec) -> ProjectedView:
        kind = mslice.fragment.scope_entity.kind.lower()
        method = getattr(self, f"_project_{kind}", None)
        if method is None:
            raise NotImplementedError(
                f"family{self.family}.entity_page has no rendering for kind={kind}"
            )
        return method(mslice, spec)
```

Subclasses in Tasks 8–14 implement `_project_component`, `_project_capability`, `_project_behavior`, etc.

**Test:**

```python
def test_entity_page_dispatches_by_kind(component_slice):
    class F3Test(EntityPageProjector):
        family = 3
        def _project_component(self, m, s): return _stub_view("component-rendered")
    p = F3Test()
    view = p.project(component_slice, ViewSpec(...))
    assert view.diagram_spec["tag"] == "component-rendered"


def test_entity_page_raises_on_unsupported_kind(constraint_slice):
    class F3Test(EntityPageProjector):
        family = 3
        # No _project_constraint defined
    with pytest.raises(NotImplementedError, match="kind=constraint"):
        F3Test().project(constraint_slice, ViewSpec(...))
```

**Commit:**

```bash
git add tests/lifecycle/test_entity_page_dispatch.py \
        src/architecture_model/lifecycle/projectors/entity_pages.py \
        src/architecture_model/lifecycle/view_projection.py
git commit -m "feat(projectors): add EntityPageProjector base with kind dispatch"
```

---

## Tasks 8-14 — Family entity_page projectors

Each task: subclass `EntityPageProjector`, set `family = N`, implement `_project_<kind>` methods per the applicability matrix in the design (§4 + §5). Register in `DEFAULT_REGISTRY` under `familyN.entity_page`.

Follow the pattern from Phase-1 SE-doc projectors: build a `diagram_spec` dict, populate deterministic keys sorted, integrate scope_chain/parent/peers/roll_up from Task 4, apply overlays helper from Phase-2 Task 14.

### Task 8 — Family 1 entity_page

Kinds: Component, Capability, Behavior, Interface, Actor, Constraint, Layer.
Content: intent, goals, stakeholders (via reverse-lookup of who depends on this entity), success_criteria, ownership, maturity.

**Commit:** `feat(projectors): add family1.entity_page (mission/purpose per entity)`

### Task 9 — Family 2 entity_page

Kinds: Capability primary; also Component (which capabilities it realizes), Behavior (which capability it belongs to).
Content: sub-`contains` tree, cross-block `triggers`, realizing components.

**Commit:** `feat(projectors): add family2.entity_page (functional decomp per entity)`

### Task 10 — Family 3 entity_page

Kinds: Component, Layer.
Content: internal parts (`contains` tree), `depends-on` graph, exposed/consumed interfaces, `dependencies_rationale` from Phase 2.

**Commit:** `feat(projectors): add family3.entity_page (structural per entity)`

### Task 11 — Family 4 entity_page

Kinds: Behavior, Actor.
Content: scenarios participated in, interfaces exchanged, actors involved.

**Commit:** `feat(projectors): add family4.entity_page (scenarios per entity)`

### Task 12 — Family 6 entity_page

Kinds: Interface primary; also Component (its exposed + consumed).
Content: ICD (schema, direction, producer/consumer), signatures/routes from `manifest_fragment` when present.

**Commit:** `feat(projectors): add family6.entity_page (interfaces + ICD per entity)`

### Task 13 — Family 7 entity_page

Kinds: Component, Capability, Behavior, Interface, Constraint.
Content: allocated requirements, verification refs, FMEA table (failure_modes), assumptions, open_questions, SLOs.

**Commit:** `feat(projectors): add family7.entity_page (quality + verification per entity)`

### Task 14 — Family 8 entity_page

Kinds: Component, Capability, Interface (any entity that has SI&L data).
Content: SI&L rollup from supplementary_fragments["sil"], recent drift flags, revision history if temporal fields set.

**Commit:** `feat(projectors): add family8.entity_page (health + evolution per entity)`

---

## Task 15 — Entity-page determinism guard

**Files:**
- Test: `tests/lifecycle/projectors/test_entity_page_determinism.py`

**Test:**

```python
@pytest.mark.parametrize("family,entity_id", [
    (1, "COMP-3"), (1, "CAP-F1"), (1, "BEH-2"),
    (2, "CAP-F1"), (2, "COMP-3"),
    (3, "COMP-3"), (3, "LAY-1"),
    (4, "BEH-2"), (4, "ACT-1"),
    (6, "IF-1"), (6, "COMP-3"),
    (7, "COMP-3"), (7, "CAP-F1"), (7, "CON-1"),
    (8, "COMP-3"),
])
def test_entity_page_byte_identical_across_runs(family, entity_id, sample_model):
    spec = ViewSpec(
        id=f"test-f{family}-{entity_id}",
        projector=f"family{family}.entity_page",
        slice_ref=SliceRef(slice_id="s", model_revision="0000001"),
        output_content_kind="diagram_spec",
    )
    slice_ = ModelSlice(id="s", architecture_id="a", model_revision="0000001",
                       scope=f"entity({entity_id})", shared_refs="none")
    a = project(materialize(slice_, sample_model), spec)
    b = project(materialize(slice_, sample_model), spec)
    assert json.dumps(a.to_dict(), sort_keys=True) == json.dumps(b.to_dict(), sort_keys=True)
```

**Commit:**

```bash
git add tests/lifecycle/projectors/test_entity_page_determinism.py
git commit -m "test(projectors): guard byte-identical entity_page output across 8 families"
```

---

## Task 16 — Drill-down link emission

**Rationale:** Every root-family view (e.g., `family3.component_map`) already lists entities; add a `drill_to: entity_id` metadata key next to each rendered entity so renderers can emit hyperlinks or hover targets.

**Files:**
- Modify: 7 root-family projectors (from Phase 1) to inject `drill_to`
- Test: `tests/lifecycle/test_drill_to_metadata.py`

**Behavior:** each entity node in a root view's `diagram_spec` gets `"drill_to": f"family{same_family}.entity_page:{entity_id}"`. No visual change; renderer-side later interprets.

**Commit:**

```bash
git add tests/lifecycle/test_drill_to_metadata.py <7 projector files>
git commit -m "feat(projectors): emit drill_to entity-page metadata on root-family entities"
```

---

## Task 17 — Renderer support for scope_chain breadcrumb + drill-up link

**Files:**
- Modify: `src/architecture_model/lifecycle/renderers/markdown.py`
- Modify: `src/architecture_model/lifecycle/renderers/html.py`
- Test: `tests/lifecycle/renderers/test_scope_chain_rendering.py`

**Behavior:**
- Markdown renderer emits at the top: `> **Path:** ROOT / COMP-1 / COMP-1.2 / **COMP-1.2.3**` when `scope_chain` non-empty.
- HTML renderer emits nav `<a>` links to parent + peer entity pages.
- Root views (empty scope_chain) render unchanged (backward compat with Phase 1).

**Commit:**

```bash
git add tests/lifecycle/renderers/test_scope_chain_rendering.py \
        src/architecture_model/lifecycle/renderers/markdown.py \
        src/architecture_model/lifecycle/renderers/html.py
git commit -m "feat(renderers): emit scope_chain breadcrumb + drill-up links"
```

---

## Task 18 — Invalidation rules for entity-scoped views

**Rationale:** When entity `E` changes, invalidate:
- `familyN.entity_page` for `E`
- `familyN.entity_page` for each direct parent (roll-up may change)
- `familyN.entity_page` for each peer if the change affects `contains` or `depends-on` at that scope
- `familyN.<root-view>` for the family that the change primarily affects

**Files:**
- Modify: `src/architecture_model/lifecycle/invalidation.py`
- Test: `tests/lifecycle/test_invalidation_entity_scoped.py`

**Rule additions:**

```python
def entity_change_stale_set(entity_id: str, family: int, model_context) -> set[str]:
    """Return view IDs affected by a change to entity_id in family scope."""
    stale = {f"family{family}.entity_page:{entity_id}"}
    parent = find_parent(entity_id, model_context)
    if parent:
        stale.add(f"family{family}.entity_page:{parent}")
    for peer in find_peers(entity_id, model_context):
        stale.add(f"family{family}.entity_page:{peer}")
    stale.add(f"family{family}.root")
    return stale
```

**Commit:**

```bash
git add tests/lifecycle/test_invalidation_entity_scoped.py src/architecture_model/lifecycle/invalidation.py
git commit -m "feat(invalidation): rebuild parent+peers when child entity changes"
```

---

## Task 19 — MCP `architect_slice` accepts entity focus

**Files:**
- Modify: `src/opencode_arch/mcp/tools/slice.py` (or wherever `architect_slice` lives)
- Test: `tests/mcp/tools/test_slice_entity_focus.py`

**Behavior:** `architect_slice(repo_path=..., focus="entity(COMP-3)")` returns the compressed context for the entity-scoped sub-model.

**Test:**

```python
def test_architect_slice_entity_focus_returns_scoped_content(fixture_repo):
    result = architect_slice(fixture_repo, focus="entity(COMP-3)", budget=4000)
    assert "COMP-3" in result["content"]
    assert "COMP-99" not in result["content"]  # unrelated component excluded
```

**Commit:**

```bash
git add tests/mcp/tools/test_slice_entity_focus.py src/opencode_arch/mcp/tools/slice.py
git commit -m "feat(mcp): architect_slice accepts entity(<id>) focus"
```

---

## Task 20 — MCP `architect_docs` DEFAULT_SPECS gains entity-page variants

**Rationale:** Add a special format `entity_pages` that expands into per-entity ArtifactSpecs at rebuild time. Opt-in (not part of `all`).

**Files:**
- Modify: `src/opencode_arch/mcp/tools/docs_specs.py`
- Modify: `src/opencode_arch/mcp/tools/docs.py`
- Test: `tests/mcp/tools/test_docs_entity_pages.py`

**Behavior:** `architect_docs(repo_path, formats="entity_pages")` walks the model, generates one ArtifactSpec per (family, entity_id) intersection where applicability matrix permits, and rebuilds them under `.architecture/lifecycle/artifacts/entity_pages/family{N}/{entity_id}.md`.

**Commit:**

```bash
git add tests/mcp/tools/test_docs_entity_pages.py \
        src/opencode_arch/mcp/tools/docs_specs.py \
        src/opencode_arch/mcp/tools/docs.py
git commit -m "feat(mcp): architect_docs formats='entity_pages' expands per-entity variants"
```

---

## Task 21 — `architect_evaluate` output includes drill-down link map

**Files:**
- Modify: `src/opencode_arch/mcp/tools/evaluate.py`
- Test: `tests/mcp/tools/test_evaluate_drilldown_map.py`

**Behavior:** result envelope grows a `drilldowns: {entity_id: [family1_url, family3_url, ...]}` block. URLs are file paths relative to `.architecture/lifecycle/artifacts/entity_pages/`. Only entities with generated pages appear.

**Commit:**

```bash
git add tests/mcp/tools/test_evaluate_drilldown_map.py src/opencode_arch/mcp/tools/evaluate.py
git commit -m "feat(mcp): architect_evaluate emits drill-down link map"
```

---

## Task 22 — CONTEXT.md refresh (ams)

- Document `slice_by_entity` and `entity(<id>)` scope
- Document EntityPageProjector convention
- Document `depth` + `expand_kinds` on ViewSpec
- Document scope_chain/parent/peers/roll_up on ProjectedView

**Commit:** `docs(context): refresh AMS CONTEXT.md for Phase 3 recursion + entity views`

---

## Task 23 — CONTEXT.md refresh (oca)

- Document `architect_slice focus="entity(<id>)"`
- Document `architect_docs formats="entity_pages"`
- Document evaluate drill-down map

**Commit:** `docs(context): refresh OCA CONTEXT.md for Phase 3 entity-scoped tools`

---

## Task 24 — Full-suite verification

Both repos green + all Phase-3 tests passing. @superpowers:verification-before-completion.

**Expected:**
- ams: baseline + Phase 1 + Phase 2 + ~60 Phase-3 tests, all passing.
- oca: baseline + Phase 1 + Phase 2 + ~8 Phase-3 tests, all passing.

---

## Rollback Strategy

Same as Phase 2 — one commit per task; independent contracts. If a specific family's entity_page design proves poor, revert that family's Task 8-14 commit; other families continue working.

## Deferred (to Phase 4)

- Family 5 entity_page (deployment) — depends on populated deployment metadata, which most models lack; ship in Phase 4 when endpoint promotion also improves physical modeling.
- LLM `.llm` variants of entity_page projectors — Phase 4 write-back class.
- Cross-repo entity references (federated navigation) — Phase 4 M3 completion.
