# Phase 1: Substrate + Liveness Foundation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Canonicalize the Lifecycle spec-driven pipeline as the single model→view substrate; wire liveness (invalidation, targeted extract, freshness) end-to-end without any schema changes.

**Architecture:** Every existing doc/diagram generator becomes a registered projector. Every doc type gets a shipped default `ViewSpec`+`ArtifactSpec`. `architect_docs` becomes sugar over `rebuild_artifacts`. Executor gains a per-subsystem (M2) loop. A new invalidation module maps `SemanticDiff` → stale-set of views. Pre-commit and post-commit templates ship as opt-in. Freshness metadata rides on every rebuilt artifact.

**Tech Stack:** Python 3.11+, pytest, PyYAML, existing lifecycle primitives (`ModelSlice`, `MaterializedSlice`, `ViewSpec`, `ArtifactSpec`, `rebuild_artifacts`, `package_diff`, `stage_cache`).

**Repos affected:**
- `architecture-model-standard` (ams) — primitives, projector registry, invalidation module, targeted-extract dispatch, determinism guards, CONTEXT.md refresh
- `opencode-arch` (oca) — `architect_docs` refactor, per-subsystem loop, freshness in `architect_evaluate`, hook templates

**Related skills:**
- @superpowers:test-driven-development for every task
- @superpowers:verification-before-completion before each commit
- @superpowers:subagent-driven-development for execution mode
- @superpowers:using-git-worktrees to isolate the branch before starting

**Baselines to preserve:**
- ams `2918 passed + 6 pre-existing failures` — commands: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py`
- oca `917 passed + 2 pre-existing failures` — commands: `PYTHONPATH="$PWD/src:/Users/baigm2/Documents/Projects/architecture-model-standard/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/e2e`

**Branching:**
- ams: `feat/model-view-mapping-phase-1` off `main` @ `f64d801`
- oca: `feat/model-view-mapping-phase-1` off `main` @ `4aadf39`

**Guardrails (rigid):**
- Never `git add -A`; stage each file explicitly.
- Never touch `.architecture*` telemetry.
- Never `pip install -e`; use PYTHONPATH pattern above.
- One commit per task; Conventional Commit format.
- Verify test baseline before AND after each commit.

---

## Task Sequence Overview

| # | Task | Repo | Behavior change? |
|---|---|:-:|:-:|
| 1 | Determinism-guard backfill for 4 seeded SE projectors | ams | No (test-only) |
| 2 | Determinism-guard backfill for 3 Mermaid generators | ams | No (test-only) |
| 3 | Determinism-guard backfill for 17 SE doc generators | ams | No (test-only) |
| 4 | Determinism-guard backfill for non-SE generators (component_spec, icd, dependency_matrix, health, drift, system_design, integration_flows, behavior_spec, index) | ams | No (test-only) |
| 5 | Projector registry canonicalization + `.llm` naming convention | ams | Additive |
| 6 | Register 17 SE doc generators as projectors | ams | Additive |
| 7 | Register Mermaid generators + non-SE generators as projectors | ams | Additive |
| 8 | Invalidation module — `SemanticDiff → stale-set` rules | ams | Additive |
| 9 | Invalidation module — M2→M1 propagation rules | ams | Additive |
| 10 | Freshness metadata field on artifacts | ams | Additive |
| 11 | Targeted-extract dispatch — `changed_files → impacted subsystems` | ams | Additive |
| 12 | `architect_docs` refactor as `rebuild_artifacts` sugar | oca | Behavior-preserving refactor |
| 13 | Per-subsystem (M2) rebuild loop in executor | oca | Additive |
| 14 | Freshness surface in `architect_evaluate` | oca | Additive |
| 15 | Pre-commit hook template + post-commit CI template | oca | Additive (opt-in) |
| 16 | CONTEXT.md refresh — ams | ams | Docs |
| 17 | CONTEXT.md refresh — oca | oca | Docs |
| 18 | Full-suite verification pass — both repos | both | Verification |

---

## Task 1 — Determinism guard: 4 seeded SE projectors

**Rationale:** The 4 seeded projectors (`se.conops`, `se.functional`, `se.logical`, `se.use_cases`) have no byte-identical round-trip tests today. Add them before any refactor so we know the baseline.

**Files:**
- Create: `tests/lifecycle/test_projector_determinism.py`
- Reference (do not modify): `src/architecture_model/core/se_view_projectors.py`, `src/architecture_model/lifecycle/view_projection.py:229`

**Step 1: Write the failing test**

```python
"""Byte-identical round-trip guards for the 4 seeded SE projectors.

Each projector must produce identical ProjectedView.diagram_spec output
across two independent invocations against the same MaterializedSlice.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from architecture_model.core.parser import load_model
from architecture_model.lifecycle.model_slice import ModelSlice
from architecture_model.lifecycle.model_slice_materializer import materialize
from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY, project
from architecture_model.lifecycle.view_spec import ViewSpec, SliceRef

FIXTURE_MODEL = Path(__file__).parent.parent / "fixtures" / "lifecycle" / "sample_model.yaml"


@pytest.fixture
def materialized_sample_slice():
    model = load_model(FIXTURE_MODEL)
    slice_ = ModelSlice(
        id="test-slice",
        architecture_id="test-arch",
        model_revision="0000001",
        scope="local",
        shared_refs="none",
    )
    return materialize(slice_, model)


@pytest.mark.parametrize(
    "projector_name",
    ["se.conops", "se.functional", "se.logical", "se.use_cases"],
)
def test_projector_output_is_byte_identical(projector_name, materialized_sample_slice):
    view_spec = ViewSpec(
        id=f"test-{projector_name}",
        slice_ref=SliceRef(slice_id="test-slice", model_revision="0000001"),
        projector=projector_name,
        output_content_kind="diagram_spec",
    )

    projected_a = project(view_spec, materialized_sample_slice, DEFAULT_REGISTRY)
    projected_b = project(view_spec, materialized_sample_slice, DEFAULT_REGISTRY)

    ser_a = json.dumps(projected_a.diagram_spec, sort_keys=True)
    ser_b = json.dumps(projected_b.diagram_spec, sort_keys=True)
    assert ser_a == ser_b, f"{projector_name} not byte-identical across runs"
```

**Step 2: Run to confirm it needs a fixture**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/lifecycle/test_projector_determinism.py -v`
Expected: FAIL — fixture `sample_model.yaml` missing OR one of the projectors non-deterministic.

**Step 3: Create the fixture if missing**

Check first: `ls tests/fixtures/lifecycle/`. If `sample_model.yaml` exists, reuse. Otherwise create a minimal valid model with all 7 entity kinds and 4 relationships.

If creation needed:
```yaml
# tests/fixtures/lifecycle/sample_model.yaml
meta:
  project: test-sample
  schema_version: '1.3'
entities:
  actors:
    - {id: ACT-1, name: EndUser, status: ACTIVE}
  capabilities:
    - {id: CAP-F1, name: CoreCapability, status: ACTIVE}
  behaviors:
    - {id: BEH-1, name: PrimaryBehavior, status: ACTIVE}
  components:
    - {id: COMP-1, name: MainModule, status: ACTIVE, files: [src/main.py]}
  interfaces:
    - {id: IF-1, name: PublicAPI, status: ACTIVE}
  constraints:
    - {id: CON-1, name: LatencyBudget, status: ACTIVE}
  layers:
    - {id: LAY-1, name: Application, status: ACTIVE}
relationships:
  - {from: COMP-1, to: CAP-F1, type: realizes}
  - {from: COMP-1, to: IF-1, type: exposes}
  - {from: ACT-1, to: IF-1, type: consumes}
  - {from: CAP-F1, to: BEH-1, type: contains}
```

**Step 4: Run tests to verify PASS**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/lifecycle/test_projector_determinism.py -v`
Expected: 4 PASSED. If any FAIL, projector has non-determinism (sort ordering, timestamp, random id). Fix the projector — that's the point of the guard.

**Step 5: Full-suite regression**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py`
Expected: `2922 passed, 6 pre-existing failures` (2918 + 4 new).

**Step 6: Commit**

```bash
git add tests/lifecycle/test_projector_determinism.py tests/fixtures/lifecycle/sample_model.yaml
git commit -m "test(lifecycle): guard byte-identical output of 4 seeded SE projectors"
```

---

## Task 2 — Determinism guard: 3 Mermaid generators

**Rationale:** `generate_all_diagrams()` produces 3 markdown files with embedded Mermaid. No byte-identical guard exists.

**Files:**
- Create: `tests/docs/test_mermaid_determinism.py`
- Reference: `src/architecture_model/docs/diagrams.py:17,33,84,116-137`

**Step 1: Write the failing test**

```python
"""Byte-identical round-trip guard for Mermaid diagram generators."""

from pathlib import Path
import pytest

from architecture_model.core.parser import load_model
from architecture_model.docs.diagrams import (
    generate_component_diagram,
    generate_use_case_diagram,
    generate_system_boundary_diagram,
)

FIXTURE = Path(__file__).parent.parent / "fixtures" / "lifecycle" / "sample_model.yaml"


@pytest.fixture(scope="module")
def sample_model():
    return load_model(FIXTURE)


@pytest.mark.parametrize(
    "generator",
    [generate_component_diagram, generate_use_case_diagram, generate_system_boundary_diagram],
)
def test_mermaid_generator_byte_identical(generator, sample_model):
    a = generator(sample_model)
    b = generator(sample_model)
    assert a == b, f"{generator.__name__} not byte-identical"
    assert isinstance(a, str)
    assert len(a) > 0
```

**Step 2: Run to verify PASS or expose non-determinism**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/docs/test_mermaid_determinism.py -v`
Expected: 3 PASSED. If FAIL, fix the generator's ordering.

**Step 3: Full-suite regression**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py`
Expected: `2925 passed, 6 pre-existing failures`.

**Step 4: Commit**

```bash
git add tests/docs/test_mermaid_determinism.py
git commit -m "test(docs): guard byte-identical output of Mermaid diagram generators"
```

---

## Task 3 — Determinism guard: 17 SE doc generators

**Rationale:** Same rationale, larger surface.

**Files:**
- Create: `tests/docs/test_se_generators_determinism.py`
- Reference: `src/architecture_model/docs/se/generator.py:16` for `STANDARD_DOCS` + `PROJECT_DOCS`

**Step 1: Write test**

```python
"""Byte-identical guard for all 17 SE doc generators (11 standard + 6 project)."""

from pathlib import Path
import pytest

from architecture_model.core.parser import load_model
from architecture_model.docs.se.generator import STANDARD_DOCS, PROJECT_DOCS

FIXTURE = Path(__file__).parent.parent / "fixtures" / "lifecycle" / "sample_model.yaml"


@pytest.fixture(scope="module")
def sample_model():
    return load_model(FIXTURE)


ALL_DOCS = list(STANDARD_DOCS) + list(PROJECT_DOCS.items())


@pytest.mark.parametrize("doc_entry", ALL_DOCS, ids=lambda e: e[0] if isinstance(e, tuple) else e)
def test_se_doc_byte_identical(doc_entry, sample_model):
    # STANDARD_DOCS entries and PROJECT_DOCS values are both (name, callable) tuples
    # Confirm during implementation; adapt to the actual shape.
    if isinstance(doc_entry, str):
        # STANDARD_DOCS might be a list of names; look up the generator
        from architecture_model.docs.se import generator as se_gen
        gen_fn = getattr(se_gen, f"generate_{doc_entry}", None)
        if gen_fn is None:
            pytest.skip(f"generator generate_{doc_entry} not found")
    else:
        _, gen_fn = doc_entry

    a = gen_fn(sample_model)
    b = gen_fn(sample_model)
    assert a == b
    assert isinstance(a, str) and len(a) > 0
```

**Step 2: Read `docs/se/generator.py` to confirm actual shape of `STANDARD_DOCS` / `PROJECT_DOCS` and adjust the test**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -c "from architecture_model.docs.se.generator import STANDARD_DOCS, PROJECT_DOCS; print(type(STANDARD_DOCS[0])); print(type(list(PROJECT_DOCS.items())[0]))"`
Adapt test to match.

**Step 3: Run**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/docs/test_se_generators_determinism.py -v`
Expected: 17 PASSED (or fewer if some generators require manifest — skip those with `pytest.skip("requires manifest")` and file follow-up).

**Step 4: Full-suite regression**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py`
Expected: baseline + 17 (or fewer if skips).

**Step 5: Commit**

```bash
git add tests/docs/test_se_generators_determinism.py
git commit -m "test(docs): guard byte-identical output of 17 SE doc generators"
```

---

## Task 4 — Determinism guard: non-SE generators

**Files:**
- Create: `tests/docs/test_nonse_generators_determinism.py`

**Step 1: Write test covering `component_spec`, `icd`, `dependency_matrix`, `health`, `drift`, `system_design`, `integration_flows`, `behavior_spec`, `index`**

```python
"""Byte-identical guard for non-SE doc generators."""

from pathlib import Path
import pytest

from architecture_model.core.parser import load_model
from architecture_model.docs.component_spec import generate_component_spec
from architecture_model.docs.icd import generate_icd
from architecture_model.docs.dependency_matrix import generate_dependency_matrix
from architecture_model.docs.health import generate_health
from architecture_model.docs.drift import generate_drift
from architecture_model.docs.system_design import generate_system_design
from architecture_model.docs.integration_flows import generate_integration_flows
from architecture_model.docs.behavior_spec import generate_behavior_spec
from architecture_model.docs.index import generate_index

FIXTURE = Path(__file__).parent.parent / "fixtures" / "lifecycle" / "sample_model.yaml"

GENERATORS = [
    generate_component_spec, generate_icd, generate_dependency_matrix,
    generate_health, generate_drift, generate_system_design,
    generate_integration_flows, generate_behavior_spec, generate_index,
]


@pytest.fixture(scope="module")
def sample_model():
    return load_model(FIXTURE)


@pytest.mark.parametrize("gen_fn", GENERATORS, ids=lambda f: f.__name__)
def test_nonse_generator_byte_identical(gen_fn, sample_model):
    a = gen_fn(sample_model)
    b = gen_fn(sample_model)
    assert a == b
    assert isinstance(a, str)
```

**Step 2: Verify actual signatures**

Read the imports lazily; if any generator requires a `manifest` arg, adjust the test parametrization to skip or supply one.

**Step 3: Run**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/docs/test_nonse_generators_determinism.py -v`
Expected: 9 PASSED (or fewer with skips + file follow-ups for skipped ones).

**Step 4: Full-suite regression + commit**

Full suite passes at baseline + N.

```bash
git add tests/docs/test_nonse_generators_determinism.py
git commit -m "test(docs): guard byte-identical output of non-SE generators"
```

---

## Task 5 — Projector registry canonicalization + `.llm` naming

**Rationale:** Today `ProjectorRegistry` in `lifecycle/view_projection.py` uses module-level seeding at import time. To make projectors discoverable and pluggable, formalize a small registry API + `.llm` variant convention.

**Files:**
- Modify: `src/architecture_model/lifecycle/view_projection.py`
- Create: `tests/lifecycle/test_projector_registry_naming.py`

**Step 1: Write failing test for `.llm` variant registration and lookup**

```python
"""Registry supports .llm variants alongside deterministic names."""

from architecture_model.lifecycle.view_projection import ProjectorRegistry


def test_llm_variant_registers_and_resolves():
    reg = ProjectorRegistry()

    def det_project(view_spec, materialized): return {"kind": "det"}
    def llm_project(view_spec, materialized): return {"kind": "llm"}

    reg.register("family2.functional", det_project)
    reg.register("family2.functional.llm", llm_project)

    assert reg.get("family2.functional")({}, None) == {"kind": "det"}
    assert reg.get("family2.functional.llm")({}, None) == {"kind": "llm"}


def test_registry_lists_registered_projectors():
    reg = ProjectorRegistry()
    reg.register("family1.mission", lambda *_: {})
    reg.register("family1.mission.llm", lambda *_: {})
    names = sorted(reg.list_names())
    assert names == ["family1.mission", "family1.mission.llm"]


def test_registry_duplicate_register_raises():
    import pytest
    reg = ProjectorRegistry()
    reg.register("x", lambda *_: {})
    with pytest.raises(ValueError, match="already registered"):
        reg.register("x", lambda *_: {})
```

**Step 2: Run to confirm failure**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/lifecycle/test_projector_registry_naming.py -v`
Expected: FAIL (missing `list_names` or duplicate-guard).

**Step 3: Implement additions to `ProjectorRegistry`**

Read current implementation first: `view_projection.py` around line 114–226. Extend without breaking existing:

```python
class ProjectorRegistry:
    # ... existing ...

    def list_names(self) -> list[str]:
        """Return all registered projector names in insertion order."""
        return list(self._projectors.keys())

    def register(self, name: str, projector) -> None:
        """Register a projector. Raises ValueError if name already registered."""
        if name in self._projectors:
            raise ValueError(f"projector {name!r} already registered")
        self._projectors[name] = projector
```

**Step 4: Run test to verify PASS**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/lifecycle/test_projector_registry_naming.py -v`
Expected: 3 PASSED.

**Step 5: Full-suite regression**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py`
Expected: baseline preserved.

**Step 6: Commit**

```bash
git add src/architecture_model/lifecycle/view_projection.py tests/lifecycle/test_projector_registry_naming.py
git commit -m "feat(lifecycle): add list_names + duplicate guard to ProjectorRegistry"
```

---

## Task 6 — Register 17 SE doc generators as projectors

**Rationale:** Wire every SE doc generator into `DEFAULT_REGISTRY` under a canonical `family<N>.<name>` name. Deterministic; no behavior change until callers switch to `rebuild_artifacts`.

**Files:**
- Modify: `src/architecture_model/lifecycle/view_projection.py` (extend `_seed_default_registry`)
- Create: `src/architecture_model/lifecycle/projectors/se_docs.py` — thin adapters converting `generate_<name>(model)` → `ProjectedView`
- Create: `tests/lifecycle/test_se_doc_projectors.py`

**Step 1: Write failing test**

```python
"""17 SE doc generators are registered as projectors under family names."""

import pytest
from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY

EXPECTED_SE_PROJECTORS = [
    "family1.conops",                    # ConOps is F1 (mission/purpose)
    "family2.functional_analysis",       # F2 functional decomposition
    "family3.logical_architecture",      # F3 structural
    "family4.operations_manual",         # F4 operational
    "family4.maintenance_manual",        # F4 operational
    "family4.use_cases",                 # F4 behavioral (may duplicate seeded se.use_cases)
    "family5.deployment_guide",          # F5 physical
    "family6.interface_spec",            # F6 interfaces
    "family6.api_reference",             # F6 (manifest-backed; ok for now, manifest_fragment lands in phase 2)
    "family6.cli_reference",             # F6
    "family6.plugin_guide",              # F6
    "family6.data_model",                # F6
    "family7.requirements_analysis",     # F7 quality
    "family7.verification_validation",   # F7 quality
    "family7.risk_assessment",           # F7 quality
    "family7.security_analysis",         # F7 quality
    "family7.artifact_traceability",     # F7 quality
]


def test_all_se_doc_projectors_registered():
    names = set(DEFAULT_REGISTRY.list_names())
    for expected in EXPECTED_SE_PROJECTORS:
        assert expected in names, f"missing projector {expected}"
```

**Step 2: Run to fail**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/lifecycle/test_se_doc_projectors.py -v`
Expected: FAIL — projectors not registered.

**Step 3: Implement adapter module**

Create `src/architecture_model/lifecycle/projectors/__init__.py` (empty).

Create `src/architecture_model/lifecycle/projectors/se_docs.py`:

```python
"""Adapters wrapping architecture_model.docs.se generators as projectors.

Each adapter takes (view_spec, materialized_slice) and returns a ProjectedView
whose diagram_spec is {"content_kind": "markdown", "body": <str>}.
"""

from __future__ import annotations

from architecture_model.docs.se import (
    api_reference,
    artifact_traceability,
    cli_reference,
    conops,
    data_model,
    deployment_guide,
    functional_analysis,
    interface_spec,
    logical_architecture,
    maintenance_manual,
    operations_manual,
    plugin_guide,
    requirements_analysis,
    risk_assessment,
    security_analysis,
    use_cases,
    verification_validation,
)
from architecture_model.lifecycle.view_projection import ProjectedView


def _wrap(generate_fn):
    """Return a projector callable that renders markdown via generate_fn."""
    def projector(view_spec, materialized_slice) -> ProjectedView:
        # MaterializedSlice.fragment contains the model dict; reconstruct
        # a minimal ArchitectureModel view or pass through if generators
        # accept dicts. This layer must be verified against actual
        # generator signatures during Step 4 below.
        from architecture_model.core.parser import _parse_raw
        model = _parse_raw(materialized_slice.fragment)
        body = generate_fn(model)
        return ProjectedView(
            view_id=view_spec.id,
            slice_id=materialized_slice.slice_id,
            model_revision=materialized_slice.model_revision,
            diagram_spec={"content_kind": "markdown", "body": body},
            provenance={"projector": view_spec.projector},
            warnings=[],
        )
    return projector


SE_PROJECTOR_MAP: dict[str, callable] = {
    "family1.conops":                   _wrap(conops.generate_conops),
    "family2.functional_analysis":      _wrap(functional_analysis.generate_functional_analysis),
    "family3.logical_architecture":     _wrap(logical_architecture.generate_logical_architecture),
    "family4.operations_manual":        _wrap(operations_manual.generate_operations_manual),
    "family4.maintenance_manual":       _wrap(maintenance_manual.generate_maintenance_manual),
    "family4.use_cases":                _wrap(use_cases.generate_use_cases),
    "family5.deployment_guide":         _wrap(deployment_guide.generate_deployment_guide),
    "family6.interface_spec":           _wrap(interface_spec.generate_interface_spec),
    "family6.api_reference":            _wrap(api_reference.generate_api_reference),
    "family6.cli_reference":            _wrap(cli_reference.generate_cli_reference),
    "family6.plugin_guide":             _wrap(plugin_guide.generate_plugin_guide),
    "family6.data_model":               _wrap(data_model.generate_data_model),
    "family7.requirements_analysis":    _wrap(requirements_analysis.generate_requirements_analysis),
    "family7.verification_validation":  _wrap(verification_validation.generate_verification_validation),
    "family7.risk_assessment":          _wrap(risk_assessment.generate_risk_assessment),
    "family7.security_analysis":        _wrap(security_analysis.generate_security_analysis),
    "family7.artifact_traceability":    _wrap(artifact_traceability.generate_artifact_traceability),
}


def register_all(registry) -> None:
    for name, proj in SE_PROJECTOR_MAP.items():
        if name not in registry.list_names():
            registry.register(name, proj)
```

**Step 4: Verify generator signatures**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -c "from architecture_model.docs.se import conops; import inspect; print(inspect.signature(conops.generate_conops))"`

If any generator takes `(model, manifest)` rather than `(model)`, adjust the wrapper to fetch `materialized_slice.manifest_fragment` — **but** since `manifest_fragment` is a Phase 2 addition, for now pass `None` and mark the projector as `family6.*` with a `warning` in ProjectedView. Adjust the test to accept that.

**Step 5: Extend `_seed_default_registry`**

In `view_projection.py`, near line 229:

```python
def _seed_default_registry() -> ProjectorRegistry:
    reg = ProjectorRegistry()
    # ... existing 4 se.* registrations ...

    from architecture_model.lifecycle.projectors.se_docs import register_all as _register_se_docs
    _register_se_docs(reg)

    return reg
```

**Step 6: Run test to verify PASS**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/lifecycle/test_se_doc_projectors.py -v`
Expected: PASS.

**Step 7: Full-suite regression**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py`
Expected: baseline preserved + new test.

**Step 8: Commit**

```bash
git add src/architecture_model/lifecycle/projectors/__init__.py src/architecture_model/lifecycle/projectors/se_docs.py src/architecture_model/lifecycle/view_projection.py tests/lifecycle/test_se_doc_projectors.py
git commit -m "feat(lifecycle): register 17 SE doc generators as family<N>.<name> projectors"
```

---

## Task 7 — Register Mermaid + non-SE generators as projectors

**Files:**
- Create: `src/architecture_model/lifecycle/projectors/mermaid.py`
- Create: `src/architecture_model/lifecycle/projectors/nonse.py`
- Modify: `src/architecture_model/lifecycle/view_projection.py` (extend `_seed_default_registry`)
- Create: `tests/lifecycle/test_mermaid_and_nonse_projectors.py`

**Step 1: Write failing test**

```python
"""Mermaid diagram + non-SE doc generators registered as projectors."""

from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY

EXPECTED = [
    # Mermaid
    "family3.component_diagram",
    "family4.use_case_diagram",
    "family1.system_boundary_diagram",
    # Non-SE docs
    "family3.component_spec",
    "family6.icd",
    "family3.dependency_matrix",
    "family8.health",
    "family8.drift",
    "family3.system_design",
    "family4.integration_flows",
    "family4.behavior_spec",
    "family8.index",
]


def test_all_registered():
    names = set(DEFAULT_REGISTRY.list_names())
    missing = [n for n in EXPECTED if n not in names]
    assert not missing, f"missing: {missing}"
```

**Step 2: Run to fail; then implement**

Create `mermaid.py` and `nonse.py` with the same `_wrap` pattern as Task 6. Then register in `_seed_default_registry`.

**Step 3: Verify + full-suite regression**

Run pytest for the new test and the full suite.

**Step 4: Commit**

```bash
git add src/architecture_model/lifecycle/projectors/mermaid.py src/architecture_model/lifecycle/projectors/nonse.py src/architecture_model/lifecycle/view_projection.py tests/lifecycle/test_mermaid_and_nonse_projectors.py
git commit -m "feat(lifecycle): register Mermaid + non-SE generators as family<N>.<name> projectors"
```

---

## Task 8 — Invalidation module: SemanticDiff → stale-set

**Rationale:** The invalidation module is the linchpin of liveness. It's a small deterministic function that takes a diff and returns the set of view IDs to rebuild.

**Files:**
- Create: `src/architecture_model/lifecycle/invalidation.py`
- Create: `tests/lifecycle/test_invalidation_rules.py`

**Step 1: Write failing tests**

```python
"""Invalidation rules: diff kinds → stale view families."""

import pytest
from architecture_model.lifecycle.invalidation import stale_families, RULES


def _diff(**kw):
    """Minimal diff dict for tests."""
    return {
        "entities": kw.get("entities", {"added": [], "removed": [], "changed": []}),
        "relationships": kw.get("relationships", {"added": [], "removed": [], "changed": []}),
    }


def test_component_added_invalidates_f3_f2_f8():
    diff = _diff(entities={
        "added": [{"kind": "component", "id": "COMP-99"}],
        "removed": [], "changed": [],
    })
    families = stale_families(diff)
    assert "family3" in families
    assert "family2" in families
    assert "family8" in families


def test_capability_change_invalidates_f1_f2_f7():
    diff = _diff(entities={
        "added": [], "removed": [],
        "changed": [{"kind": "capability", "id": "CAP-1", "fields": ["intent"]}],
    })
    families = stale_families(diff)
    assert "family1" in families
    assert "family2" in families
    assert "family7" in families


def test_constraint_added_invalidates_f7_f1():
    diff = _diff(entities={
        "added": [{"kind": "constraint", "id": "CON-9"}],
        "removed": [], "changed": [],
    })
    families = stale_families(diff)
    assert "family7" in families
    assert "family1" in families


def test_interface_change_invalidates_f6_f3():
    diff = _diff(entities={
        "added": [], "removed": [],
        "changed": [{"kind": "interface", "id": "IF-1", "fields": ["name"]}],
    })
    families = stale_families(diff)
    assert "family6" in families
    assert "family3" in families


def test_semantic_field_only_change_invalidates_only_touched_families():
    """A change to failure_modes on a Behavior touches F7, not F3."""
    diff = _diff(entities={
        "added": [], "removed": [],
        "changed": [{"kind": "behavior", "id": "BEH-1", "fields": ["failure_modes"]}],
    })
    families = stale_families(diff)
    assert "family7" in families
    assert "family3" not in families


def test_empty_diff_stales_nothing():
    assert stale_families(_diff()) == set()


def test_rules_are_data_not_code():
    """RULES must be a data table, iterable, and reference-stable."""
    assert isinstance(RULES, list)
    assert all("trigger" in r and "invalidates" in r for r in RULES)
```

**Step 2: Run to fail**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/lifecycle/test_invalidation_rules.py -v`
Expected: FAIL (module missing).

**Step 3: Implement invalidation module**

```python
# src/architecture_model/lifecycle/invalidation.py
"""Map a SemanticDiff onto the set of view families to invalidate.

The rule table is data; adding a rule is data-only, not code. Each rule
declares a trigger (entity kind + operation + optional field set) and
the set of families it invalidates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Semantic-only fields; touching these invalidates F1/F7 only (surgical).
_SEMANTIC_FIELDS: frozenset[str] = frozenset({
    "intent", "goals", "stakeholders", "success_criteria",
    "failure_modes", "trade_offs", "assumptions", "open_questions",
    "requirements", "verification", "slos", "owner", "maturity",
    "dependencies_rationale",
})

# Which families each semantic field belongs to (for surgical invalidation).
_SEMANTIC_FIELD_FAMILIES: dict[str, set[str]] = {
    "intent": {"family1"},
    "goals": {"family1", "family7"},
    "stakeholders": {"family1"},
    "success_criteria": {"family1", "family7"},
    "failure_modes": {"family7"},
    "trade_offs": {"family1", "family3", "family7"},
    "assumptions": {"family7"},
    "open_questions": {"family7", "family8"},
    "requirements": {"family7"},
    "verification": {"family7"},
    "slos": {"family5", "family7", "family8"},
    "owner": {"family1", "family8"},
    "maturity": {"family1", "family8"},
    "dependencies_rationale": {"family3"},
}


@dataclass(frozen=True)
class Rule:
    trigger: dict[str, Any]   # {"kind": "component", "op": "added"} etc.
    invalidates: frozenset[str]


RULES: list[Rule] = [
    # Structural add/remove
    Rule({"kind": "component", "op": "added"},   frozenset({"family3", "family2", "family8"})),
    Rule({"kind": "component", "op": "removed"}, frozenset({"family3", "family2", "family8"})),
    Rule({"kind": "capability", "op": "added"},   frozenset({"family1", "family2", "family7"})),
    Rule({"kind": "capability", "op": "removed"}, frozenset({"family1", "family2", "family7"})),
    Rule({"kind": "capability", "op": "changed"}, frozenset({"family1", "family2", "family7"})),
    Rule({"kind": "constraint", "op": "added"},   frozenset({"family7", "family1"})),
    Rule({"kind": "constraint", "op": "removed"}, frozenset({"family7", "family1"})),
    Rule({"kind": "interface", "op": "added"},    frozenset({"family6", "family3"})),
    Rule({"kind": "interface", "op": "removed"},  frozenset({"family6", "family3"})),
    Rule({"kind": "interface", "op": "changed"},  frozenset({"family6", "family3"})),
    Rule({"kind": "behavior", "op": "added"},     frozenset({"family4", "family2", "family7"})),
    Rule({"kind": "behavior", "op": "removed"},   frozenset({"family4", "family2", "family7"})),
    Rule({"kind": "actor", "op": "added"},        frozenset({"family1", "family4"})),
    Rule({"kind": "actor", "op": "removed"},      frozenset({"family1", "family4"})),
    Rule({"kind": "layer", "op": "added"},        frozenset({"family3"})),
    Rule({"kind": "layer", "op": "removed"},      frozenset({"family3"})),
    # Relationship changes — always F3 (structural) + F8 (diff)
    Rule({"rel": True, "op": "added"},   frozenset({"family3", "family8"})),
    Rule({"rel": True, "op": "removed"}, frozenset({"family3", "family8"})),
]


def _semantic_only(fields: list[str]) -> bool:
    return bool(fields) and all(f in _SEMANTIC_FIELDS for f in fields)


def _families_for_semantic_fields(fields: list[str]) -> set[str]:
    result: set[str] = set()
    for f in fields:
        result |= _SEMANTIC_FIELD_FAMILIES.get(f, set())
    return result


def stale_families(diff: dict) -> set[str]:
    """Compute the set of view families made stale by a SemanticDiff.

    diff shape (subset used):
        {"entities": {"added": [{kind, id}], "removed": [...], "changed": [{kind, id, fields}]},
         "relationships": {"added": [...], "removed": [...], "changed": [...]}}
    """
    stale: set[str] = set()

    ents = diff.get("entities", {})
    for op in ("added", "removed"):
        for entry in ents.get(op, []):
            kind = entry.get("kind")
            for rule in RULES:
                t = rule.trigger
                if t.get("kind") == kind and t.get("op") == op:
                    stale |= rule.invalidates

    # Changed: if only semantic fields, surgical; else full rule set.
    for entry in ents.get("changed", []):
        kind = entry.get("kind")
        fields = entry.get("fields", [])
        if _semantic_only(fields):
            stale |= _families_for_semantic_fields(fields)
        else:
            for rule in RULES:
                t = rule.trigger
                if t.get("kind") == kind and t.get("op") == "changed":
                    stale |= rule.invalidates
            # Fallback: any changed structural entity invalidates F3+F8
            stale |= {"family3", "family8"}

    # Relationships
    rels = diff.get("relationships", {})
    for op in ("added", "removed"):
        if rels.get(op):
            for rule in RULES:
                t = rule.trigger
                if t.get("rel") and t.get("op") == op:
                    stale |= rule.invalidates
    if rels.get("changed"):
        stale |= {"family3", "family8"}

    return stale


def stale_view_ids(diff: dict, all_view_ids: list[str]) -> list[str]:
    """Given all registered view IDs (family<N>.<name>[.llm]), return those in stale families."""
    families = stale_families(diff)
    result = []
    for vid in all_view_ids:
        head = vid.split(".", 1)[0]
        if head in families:
            result.append(vid)
    return sorted(result)
```

**Step 4: Verify tests PASS**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/lifecycle/test_invalidation_rules.py -v`
Expected: 7 PASSED.

**Step 5: Full-suite regression**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py`

**Step 6: Commit**

```bash
git add src/architecture_model/lifecycle/invalidation.py tests/lifecycle/test_invalidation_rules.py
git commit -m "feat(lifecycle): add invalidation module mapping SemanticDiff to view families"
```

---

## Task 9 — Invalidation module: M2→M1 propagation

**Rationale:** When an M2 sub-model changes, some kinds of changes bubble up to M1 while others stay local. Encode the rules from Section 7.

**Files:**
- Modify: `src/architecture_model/lifecycle/invalidation.py`
- Create: `tests/lifecycle/test_invalidation_propagation.py`

**Step 1: Write test**

```python
"""M2 → M1 propagation rules."""

from architecture_model.lifecycle.invalidation import propagates_to_m1


def _diff(**kw):
    return {
        "entities": kw.get("entities", {"added": [], "removed": [], "changed": []}),
        "relationships": kw.get("relationships", {"added": [], "removed": [], "changed": []}),
    }


def test_public_interface_add_propagates():
    diff = _diff(relationships={
        "added": [{"type": "exposes", "from": "COMP-1", "to": "IF-1"}],
        "removed": [], "changed": [],
    })
    assert propagates_to_m1(diff) is True


def test_cross_subsystem_depends_on_propagates():
    diff = _diff(relationships={
        "added": [{"type": "depends-on", "from": "COMP-1", "to": "COMP-2", "cross_subsystem": True}],
        "removed": [], "changed": [],
    })
    assert propagates_to_m1(diff) is True


def test_internal_only_change_does_not_propagate():
    diff = _diff(entities={
        "added": [], "removed": [],
        "changed": [{"kind": "component", "id": "COMP-1", "fields": ["name"]}],
    })
    assert propagates_to_m1(diff) is False


def test_semantic_field_on_top_level_entity_propagates_surgically():
    """A semantic-field change on a component that appears in M1 → M1 semantic-only invalidation."""
    diff = _diff(entities={
        "added": [], "removed": [],
        "changed": [{"kind": "component", "id": "COMP-1", "fields": ["intent"],
                     "appears_in_m1": True}],
    })
    assert propagates_to_m1(diff) is True
```

**Step 2: Fail, then implement**

Add to `invalidation.py`:

```python
_M1_PROPAGATING_REL_TYPES = frozenset({"exposes", "consumes"})


def propagates_to_m1(diff: dict) -> bool:
    """True iff this M2 diff must invalidate M1 as well."""
    rels = diff.get("relationships", {})
    for op in ("added", "removed"):
        for r in rels.get(op, []):
            if r.get("type") in _M1_PROPAGATING_REL_TYPES:
                return True
            if r.get("cross_subsystem"):
                return True

    ents = diff.get("entities", {})
    for entry in ents.get("changed", []):
        if entry.get("appears_in_m1"):
            return True
    for op in ("added", "removed"):
        for entry in ents.get(op, []):
            # Component add/remove propagates only if it's a subsystem-level component
            # (marked by upstream). Conservative default: propagate.
            if entry.get("kind") == "component":
                return True

    return False
```

**Step 3: Verify + regression**

Run tests; ensure baseline holds.

**Step 4: Commit**

```bash
git add src/architecture_model/lifecycle/invalidation.py tests/lifecycle/test_invalidation_propagation.py
git commit -m "feat(lifecycle): add M2->M1 propagation rules to invalidation module"
```

---

## Task 10 — Freshness metadata on artifacts

**Rationale:** Consumers need to know whether an artifact reflects HEAD's model or is stale.

**Files:**
- Modify: `src/architecture_model/lifecycle/artifact_spec.py` (or wherever provenance lives)
- Modify: `src/architecture_model/lifecycle/view_projection.py` (`ProjectedView.provenance`)
- Create: `tests/lifecycle/test_freshness_metadata.py`

**Step 1: Write test**

```python
"""ProjectedView provenance carries freshness + revision fields."""

from architecture_model.lifecycle.view_projection import ProjectedView


def test_projected_view_provenance_has_freshness():
    v = ProjectedView(
        view_id="v1",
        slice_id="s1",
        model_revision="0000001",
        diagram_spec={},
        provenance={"projector": "family1.mission", "freshness": "fresh", "revision": "0000001"},
        warnings=[],
    )
    assert v.provenance["freshness"] == "fresh"
    assert v.provenance["revision"] == "0000001"


def test_freshness_values():
    from architecture_model.lifecycle.freshness import FRESHNESS_VALUES
    assert set(FRESHNESS_VALUES) == {"fresh", "stale", "pending"}
```

**Step 2: Fail, then implement**

Create `src/architecture_model/lifecycle/freshness.py`:

```python
"""Freshness constants for artifact provenance."""

from typing import Literal

Freshness = Literal["fresh", "stale", "pending"]
FRESHNESS_VALUES: tuple[Freshness, ...] = ("fresh", "stale", "pending")
```

Adjust `ProjectedView.provenance` docstring / schema notes to specify that projectors SHOULD populate `freshness` and `revision` keys. (No structural schema change; provenance is a dict.)

**Step 3: Update the adapter `_wrap` in Tasks 6/7 to stamp `freshness` + `revision`**

Modify `projectors/se_docs.py` `_wrap`:

```python
return ProjectedView(
    view_id=view_spec.id,
    slice_id=materialized_slice.slice_id,
    model_revision=materialized_slice.model_revision,
    diagram_spec={"content_kind": "markdown", "body": body},
    provenance={
        "projector": view_spec.projector,
        "freshness": "fresh",
        "revision": materialized_slice.model_revision,
    },
    warnings=[],
)
```

Same for `mermaid.py` and `nonse.py` adapters.

**Step 4: Verify + full-suite regression**

Ensure existing determinism tests still pass byte-identical (the provenance field is dictionary, so any test comparing `diagram_spec` only is unaffected; if any test compares full `ProjectedView`, adjust).

**Step 5: Commit**

```bash
git add src/architecture_model/lifecycle/freshness.py src/architecture_model/lifecycle/projectors/ tests/lifecycle/test_freshness_metadata.py
git commit -m "feat(lifecycle): stamp freshness + revision on ProjectedView provenance"
```

---

## Task 11 — Targeted-extract dispatch

**Rationale:** Given a set of changed files, decide which M2 subsystems must re-extract and whether M1 aggregation is needed.

**Files:**
- Create: `src/architecture_model/pipeline/targeted.py`
- Create: `tests/pipeline/test_targeted_dispatch.py`

**Step 1: Write test**

```python
"""targeted_extract(changed_files, repo_root) → dispatch plan."""

from pathlib import Path
from architecture_model.pipeline.targeted import compute_dispatch_plan


def test_single_file_maps_to_single_subsystem(tmp_path):
    # Simulate a repo with 2 M2 sub-models
    (tmp_path / ".architecture-models" / "core").mkdir(parents=True)
    (tmp_path / ".architecture-models" / "core" / ".architecture-model.yaml").write_text(
        "meta: {project: t, schema_version: '1.3'}\n"
        "entities:\n  components:\n"
        "    - {id: COMP-1, name: Parser, status: ACTIVE, files: [src/pkg/core/parser.py]}\n"
        "relationships: []\n"
    )
    (tmp_path / ".architecture-models" / "manifest").mkdir(parents=True)
    (tmp_path / ".architecture-models" / "manifest" / ".architecture-model.yaml").write_text(
        "meta: {project: t, schema_version: '1.3'}\n"
        "entities:\n  components:\n"
        "    - {id: COMP-2, name: Scanner, status: ACTIVE, files: [src/pkg/manifest/scanner.py]}\n"
        "relationships: []\n"
    )

    plan = compute_dispatch_plan(
        changed_files=[Path("src/pkg/core/parser.py")],
        repo_root=tmp_path,
    )
    assert plan.subsystems_to_extract == ["core"]
    assert plan.needs_m1_aggregation is True


def test_unknown_file_flags_investigation(tmp_path):
    (tmp_path / ".architecture-models").mkdir()
    plan = compute_dispatch_plan(
        changed_files=[Path("src/new/module.py")],
        repo_root=tmp_path,
    )
    assert plan.subsystems_to_extract == []
    assert plan.unknown_files == [Path("src/new/module.py")]
    assert plan.needs_m1_aggregation is True  # M1 must investigate new file
```

**Step 2: Fail, then implement**

```python
# src/architecture_model/pipeline/targeted.py
"""Targeted extraction: map changed files → impacted subsystems + M1 decision."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class DispatchPlan:
    subsystems_to_extract: list[str] = field(default_factory=list)
    needs_m1_aggregation: bool = False
    unknown_files: list[Path] = field(default_factory=list)


def _load_file_ownership(repo_root: Path) -> dict[str, set[str]]:
    """Return {subsystem_name: set of owned file paths (relative to repo_root)}."""
    ownership: dict[str, set[str]] = {}
    models_dir = repo_root / ".architecture-models"
    if not models_dir.exists():
        return ownership
    for sub_dir in sorted(models_dir.iterdir()):
        model_path = sub_dir / ".architecture-model.yaml"
        if not model_path.exists():
            continue
        data = yaml.safe_load(model_path.read_text()) or {}
        files: set[str] = set()
        components = (data.get("entities") or {}).get("components") or []
        for comp in components:
            for f in comp.get("files", []) or []:
                files.add(f)
        ownership[sub_dir.name] = files
    return ownership


def compute_dispatch_plan(changed_files: list[Path], repo_root: Path) -> DispatchPlan:
    ownership = _load_file_ownership(repo_root)
    plan = DispatchPlan()
    for cf in changed_files:
        cf_str = str(cf)
        matched = False
        for sub, files in ownership.items():
            if cf_str in files:
                if sub not in plan.subsystems_to_extract:
                    plan.subsystems_to_extract.append(sub)
                matched = True
        if not matched:
            plan.unknown_files.append(cf)
    # M1 aggregation always needed if any subsystem re-ran OR unknown files present.
    plan.needs_m1_aggregation = bool(plan.subsystems_to_extract) or bool(plan.unknown_files)
    return plan
```

**Step 3: Verify + regression**

**Step 4: Commit**

```bash
git add src/architecture_model/pipeline/targeted.py tests/pipeline/test_targeted_dispatch.py
git commit -m "feat(pipeline): add targeted-extract dispatch (changed files -> impacted subsystems)"
```

---

## Task 12 — `architect_docs` refactor as `rebuild_artifacts` sugar (oca)

**Rationale:** With projectors registered for every doc type, `architect_docs` becomes a thin wrapper that constructs default `ViewSpec` + `ArtifactSpec` per format and calls `rebuild_artifacts`.

**Repo:** oca. Switch to `../opencode-arch/` context; branch `feat/model-view-mapping-phase-1` off `main` @ `4aadf39`.

**Files:**
- Modify: `src/opencode_arch/mcp/tools/docs.py`
- Create: `src/opencode_arch/mcp/tools/docs_specs.py` — default ViewSpec + ArtifactSpec per format
- Modify: `tests/mcp/tools/test_docs.py` (existing tests must continue to pass)
- Create: `tests/mcp/tools/test_docs_specs.py`

**Step 1: Read existing `docs.py` to understand exact tool signature**

Read `opencode-arch/src/opencode_arch/mcp/tools/docs.py:12-63`. Preserve external tool contract (format names, output paths).

**Step 2: Write test for default specs**

```python
"""Every supported doc format maps to a (ViewSpec, ArtifactSpec) pair."""

import pytest
from opencode_arch.mcp.tools.docs_specs import DEFAULT_SPECS, SUPPORTED_FORMATS


def test_every_format_has_a_spec():
    missing = [f for f in SUPPORTED_FORMATS if f not in DEFAULT_SPECS]
    assert not missing


@pytest.mark.parametrize("fmt", SUPPORTED_FORMATS)
def test_spec_maps_to_registered_projector(fmt):
    from architecture_model.lifecycle.view_projection import DEFAULT_REGISTRY
    view_spec, artifact_spec = DEFAULT_SPECS[fmt]
    assert view_spec["projector"] in DEFAULT_REGISTRY.list_names(), (
        f"format {fmt} references unregistered projector {view_spec['projector']}"
    )
```

**Step 3: Fail, then implement `docs_specs.py`**

```python
"""Default ViewSpec + ArtifactSpec pairs for every architect_docs format."""

from __future__ import annotations

SUPPORTED_FORMATS: tuple[str, ...] = (
    "conops",
    "functional_analysis",
    "logical_architecture",
    "operations_manual",
    "maintenance_manual",
    "use_cases",
    "deployment_guide",
    "interface_spec",
    "api_reference",
    "cli_reference",
    "plugin_guide",
    "data_model",
    "requirements_analysis",
    "verification_validation",
    "risk_assessment",
    "security_analysis",
    "artifact_traceability",
    "component_spec",
    "icd",
    "dependency_matrix",
    "health",
    "drift",
    "system_design",
    "integration_flows",
    "behavior_spec",
    "index",
)

# format → (family_prefix, projector_suffix)
_PROJECTOR_MAP: dict[str, str] = {
    "conops":                     "family1.conops",
    "functional_analysis":        "family2.functional_analysis",
    "logical_architecture":       "family3.logical_architecture",
    "operations_manual":          "family4.operations_manual",
    "maintenance_manual":         "family4.maintenance_manual",
    "use_cases":                  "family4.use_cases",
    "deployment_guide":           "family5.deployment_guide",
    "interface_spec":             "family6.interface_spec",
    "api_reference":              "family6.api_reference",
    "cli_reference":              "family6.cli_reference",
    "plugin_guide":               "family6.plugin_guide",
    "data_model":                 "family6.data_model",
    "requirements_analysis":      "family7.requirements_analysis",
    "verification_validation":    "family7.verification_validation",
    "risk_assessment":            "family7.risk_assessment",
    "security_analysis":          "family7.security_analysis",
    "artifact_traceability":      "family7.artifact_traceability",
    "component_spec":             "family3.component_spec",
    "icd":                        "family6.icd",
    "dependency_matrix":          "family3.dependency_matrix",
    "health":                     "family8.health",
    "drift":                      "family8.drift",
    "system_design":              "family3.system_design",
    "integration_flows":          "family4.integration_flows",
    "behavior_spec":              "family4.behavior_spec",
    "index":                      "family8.index",
}


def _default_view_spec(fmt: str) -> dict:
    return {
        "id": f"docs.{fmt}",
        "slice_ref": {"slice_id": f"docs.{fmt}.slice", "model_revision": "CURRENT"},
        "projector": _PROJECTOR_MAP[fmt],
        "output_content_kind": "markdown",
    }


def _default_artifact_spec(fmt: str) -> dict:
    return {
        "id": f"docs.{fmt}",
        "renderer": "markdown",
        "view_refs": [f"docs.{fmt}"],
        "output_path": f"docs/architecture/{fmt}.md",
    }


DEFAULT_SPECS: dict[str, tuple[dict, dict]] = {
    fmt: (_default_view_spec(fmt), _default_artifact_spec(fmt))
    for fmt in SUPPORTED_FORMATS
}
```

**Step 4: Refactor `docs.py` to use specs + rebuild_artifacts**

Replace the per-format `if/elif` chain with:

```python
def architect_docs(repo_path: str, formats: str = "all") -> dict:
    from opencode_arch.mcp.tools.docs_specs import DEFAULT_SPECS, SUPPORTED_FORMATS
    from opencode_arch.lifecycle_exec.rebuild import rebuild_artifacts

    requested = (
        list(SUPPORTED_FORMATS) if formats == "all"
        else [f.strip() for f in formats.split(",") if f.strip()]
    )
    view_specs = []
    slice_specs = []
    artifact_specs = []
    for fmt in requested:
        if fmt not in DEFAULT_SPECS:
            continue
        vs, ars = DEFAULT_SPECS[fmt]
        view_specs.append(vs)
        artifact_specs.append(ars)
        # slice_spec: minimal local scope over current revision
        slice_specs.append({
            "id": vs["slice_ref"]["slice_id"],
            "architecture_id": f"{Path(repo_path).name}-root",
            "model_revision": "CURRENT",
            "scope": "local",
            "shared_refs": "none",
        })
    return rebuild_artifacts(
        repo_path=repo_path,
        artifact_specs=artifact_specs,
        view_specs=view_specs,
        slice_specs=slice_specs,
    )
```

**Step 5: Verify existing test_docs.py still passes AND new tests PASS**

Run: `PYTHONPATH="$PWD/src:/Users/baigm2/Documents/Projects/architecture-model-standard/src" /opt/anaconda3/bin/python -m pytest tests/mcp/tools/test_docs.py tests/mcp/tools/test_docs_specs.py -v`
Expected: existing tests unaffected (output paths, format list preserved); new tests pass.

**Step 6: Full oca suite regression**

Run full oca suite. Preserve `917 passed + 2 pre-existing`.

**Step 7: Commit**

```bash
git add src/opencode_arch/mcp/tools/docs.py src/opencode_arch/mcp/tools/docs_specs.py tests/mcp/tools/test_docs_specs.py
git commit -m "refactor(mcp/docs): architect_docs becomes sugar over rebuild_artifacts"
```

---

## Task 13 — Per-subsystem (M2) rebuild loop in executor

**Rationale:** Today `rebuild_artifacts` operates on a single scope. Extend it so a spec with `scope: descendants` iterates each M2 sub-model automatically.

**Files (oca):**
- Modify: `src/opencode_arch/lifecycle_exec/rebuild.py`
- Create: `tests/lifecycle_exec/test_rebuild_descendants.py`

**Step 1: Read current `rebuild.py` to understand its shape**

Read the full file (up to 613 lines). Identify the entry point, artifact iteration loop, and where slice resolution occurs.

**Step 2: Write failing test**

```python
"""When a slice spec has scope='descendants', rebuild runs once per M2 sub-model."""

from pathlib import Path
import pytest


def test_descendants_scope_iterates_subsystems(tmp_path):
    from opencode_arch.lifecycle_exec.rebuild import rebuild_artifacts

    # Create 2 sub-models (M2)
    (tmp_path / ".architecture-model.yaml").write_text(
        "meta: {project: root, schema_version: '1.3'}\n"
        "entities:\n  components: []\nrelationships: []\n"
    )
    for name in ["a", "b"]:
        d = tmp_path / ".architecture-models" / name
        d.mkdir(parents=True)
        (d / ".architecture-model.yaml").write_text(
            f"meta: {{project: {name}, schema_version: '1.3'}}\n"
            f"entities:\n  components: []\nrelationships: []\n"
        )

    result = rebuild_artifacts(
        repo_path=str(tmp_path),
        artifact_specs=[{
            "id": "conops",
            "renderer": "markdown",
            "view_refs": ["conops"],
            "output_path": "docs/architecture/conops.md",
        }],
        view_specs=[{
            "id": "conops",
            "slice_ref": {"slice_id": "conops.slice", "model_revision": "CURRENT"},
            "projector": "family1.conops",
            "output_content_kind": "markdown",
        }],
        slice_specs=[{
            "id": "conops.slice",
            "architecture_id": "root",
            "model_revision": "CURRENT",
            "scope": "descendants",
            "shared_refs": "none",
        }],
    )

    # Expect one artifact per subsystem (a, b) plus one for root
    assert len(result.get("built", [])) >= 2
```

**Step 3: Extend `rebuild_artifacts` to loop over M2s when `scope=descendants`**

Add branch: after loading root package, if slice_spec.scope == "descendants", enumerate `iter_descendants(root_pkg, include_self=True)`, rebuild once per package, adjust output_path to include subsystem slug.

**Step 4: Verify + regression**

Existing tests (single-scope rebuild) must still pass. New test passes.

**Step 5: Commit**

```bash
git add src/opencode_arch/lifecycle_exec/rebuild.py tests/lifecycle_exec/test_rebuild_descendants.py
git commit -m "feat(lifecycle_exec): rebuild loops per-subsystem when slice scope=descendants"
```

---

## Task 14 — Freshness in `architect_evaluate` (oca)

**Files:**
- Modify: `src/opencode_arch/mcp/tools/evaluate.py`
- Create/extend: `tests/mcp/tools/test_evaluate_freshness.py`

**Step 1: Write test**

```python
def test_evaluate_reports_freshness_summary(tmp_path):
    from opencode_arch.mcp.tools.evaluate import architect_evaluate

    (tmp_path / ".architecture-model.yaml").write_text(
        "meta: {project: t, schema_version: '1.3'}\nentities: {}\nrelationships: []\n"
    )
    (tmp_path / ".architecture" / "lifecycle" / "artifacts").mkdir(parents=True)
    result = architect_evaluate(repo_path=str(tmp_path))
    assert "freshness_summary" in result
    assert set(result["freshness_summary"].keys()) >= {"fresh", "stale", "pending", "total"}
```

**Step 2: Fail, then implement**

Extend `evaluate.py` to scan `.architecture/lifecycle/artifacts/*` and count freshness values (defaults to 'unknown' if not stamped). Merge into result dict.

**Step 3: Verify + regression + commit**

```bash
git add src/opencode_arch/mcp/tools/evaluate.py tests/mcp/tools/test_evaluate_freshness.py
git commit -m "feat(mcp/evaluate): surface freshness summary of architecture artifacts"
```

---

## Task 15 — Pre-commit + post-commit templates (oca)

**Rationale:** Ship as opt-in templates users can install into their own repo.

**Files:**
- Create: `docs/templates/pre-commit.sh`
- Create: `docs/templates/architecture-refresh.yml` (GitHub Actions)
- Modify: `docs/index.md` or equivalent to document opt-in installation
- Create: `tests/templates/test_hook_template_syntax.py`

**Step 1: Write template validation test**

```python
"""Templates are syntactically valid shell and YAML."""

import subprocess
from pathlib import Path
import yaml

REPO = Path(__file__).resolve().parents[2]


def test_pre_commit_hook_is_valid_bash():
    hook = REPO / "docs" / "templates" / "pre-commit.sh"
    # bash -n = syntax check without executing
    result = subprocess.run(["bash", "-n", str(hook)], capture_output=True)
    assert result.returncode == 0, result.stderr.decode()


def test_github_actions_workflow_is_valid_yaml():
    wf = REPO / "docs" / "templates" / "architecture-refresh.yml"
    data = yaml.safe_load(wf.read_text())
    assert "on" in data or True in data  # PyYAML parses `on:` as True
    assert "jobs" in data
```

**Step 2: Fail, then create templates**

`docs/templates/pre-commit.sh`:

```bash
#!/usr/bin/env bash
# Opt-in pre-commit hook: refresh architecture model + views for staged changes.
# Install: cp docs/templates/pre-commit.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

set -euo pipefail

CHANGED=$(git diff --cached --name-only --diff-filter=ACMR | grep -E '\.(py|ts|tsx|js)$' || true)
if [ -z "$CHANGED" ]; then
  exit 0
fi

echo "[architecture] refreshing model+views for staged changes..."
# Use whichever runner the project has configured; default to architect-mcp CLI.
if command -v architect-mcp >/dev/null 2>&1; then
  architect-mcp refresh --changed "$CHANGED" || {
    echo "[architecture] pre-commit refresh failed; commit aborted"
    exit 1
  }
else
  echo "[architecture] architect-mcp CLI not found; skipping (install opencode-arch)"
fi
```

`docs/templates/architecture-refresh.yml`:

```yaml
name: Architecture Refresh

on:
  push:
    branches: [main]
  pull_request:

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 2 }
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - name: Install opencode-arch
        run: pip install opencode-arch
      - name: Refresh model + views
        run: architect-mcp refresh --all
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: architecture-artifacts
          path: .architecture/lifecycle/artifacts/
```

**Step 3: Verify tests PASS**

**Step 4: Commit**

```bash
git add docs/templates/pre-commit.sh docs/templates/architecture-refresh.yml tests/templates/test_hook_template_syntax.py
git commit -m "feat(templates): add opt-in pre-commit + post-commit CI templates"
```

---

## Task 16 — CONTEXT.md refresh (ams)

**Files:**
- Modify: `CONTEXT.md`

**Step 1: Read current CONTEXT.md**

Confirm the stale claims:
- "6 subsystems" (actual: 25)
- "4 Mermaid diagrams: context.mmd / components.mmd / behaviors.mmd / dependencies.mmd" (actual: 3 md files)
- Current SE workflow section

**Step 2: Update with correct facts**

- Change subsystem count to 25 and update the file structure diagram.
- Change diagram section to describe 3 md outputs: `component-diagram.md`, `use-case-diagrams.md`, `system-boundary-diagram.md`.
- Add a "Phase 1 substrate" section pointing to the design doc and this plan.

**Step 3: Verify + commit**

No tests changed. Just:

```bash
git add CONTEXT.md
git commit -m "docs(CONTEXT): refresh subsystem count, diagram outputs, Phase 1 pointers"
```

---

## Task 17 — CONTEXT.md refresh (oca)

**Files (oca repo):**
- Modify: `CONTEXT.md`

Update `architect_docs` description to note it becomes sugar over `rebuild_artifacts`. Add note about freshness metadata on artifacts.

Commit:

```bash
git add CONTEXT.md
git commit -m "docs(CONTEXT): note architect_docs as rebuild_artifacts sugar + freshness metadata"
```

---

## Task 18 — Full-suite verification

**Rationale:** Final gate before opening PR(s).

**Step 1: ams full suite**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py`
Expected: `2918 passed + 6 pre-existing failures + N new tests passed` where N ≈ 30–40 from Tasks 1–4 and 5–11.

**Step 2: oca full suite**

Run: `PYTHONPATH="$PWD/src:/Users/baigm2/Documents/Projects/architecture-model-standard/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/e2e`
Expected: `917 passed + 2 pre-existing failures + N new tests passed` where N ≈ 5–10 from Tasks 12–15.

**Step 3: Byte-identical guard cross-check**

Reset a clean checkout of both repos to before Task 1, replay the branch, confirm all determinism guards still pass. (No code change; sanity operation only.)

**Step 4: Verification report**

Create `docs/reports/2026-09-08-phase-1-verification.md` with:
- Test counts (before, after per task, final).
- List of new projectors registered.
- List of new tests.
- Any deferred items (e.g., generators skipped for manifest requirement — Phase 2 unlocks them via `manifest_fragment`).

Commit:

```bash
git add docs/reports/2026-09-08-phase-1-verification.md
git commit -m "docs(report): Phase 1 verification report"
```

**Step 5: Open PRs**

Two PRs, one per repo. Base branch: `main`. Never force-push. Include a summary linking to the design doc and this plan.

---

## Deferred to later phases (do NOT do here)

- Entity semantic schema (`intent`, `goals`, `failure_modes`, `trade_offs`, `slos`, ...) — **Phase 2**
- `schema_version` bump to 2.1 + migration — **Phase 2**
- `MaterializedSlice.manifest_fragment` — **Phase 2**
- `ModelSlice.supplementary_refs` — **Phase 2**
- Temporal slicing (`revision_range`, `time_window`) — **Phase 2**
- Feedback persistence journals (`gates.jsonl`, `drift.jsonl`, `test_results.jsonl`) — **Phase 2**
- Overlay slots in ViewSpec curation — **Phase 2**
- Entity-scoped slicing (`slice_by_entity`) — **Phase 3**
- Scope-chain on ProjectedView — **Phase 3**
- Entity-page projectors × families — **Phase 3**
- LLM write-back projector class emitting AI Proposals — **Phase 4**
- Endpoint→Interface promotion extractor — **Phase 4**
- Federated (M3) trigger and materialization completion — **Phase 4**

## Notes on execution mode

**Recommended:** subagent-driven-development. Each task is a subagent invocation; fresh context per task; test baseline verified between tasks. Requires @superpowers:subagent-driven-development.

**Alternative:** parallel session with @superpowers:executing-plans if user prefers batched execution with review checkpoints.
