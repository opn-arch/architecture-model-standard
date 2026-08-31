# SE Document Generator v2.1 Field Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update 5 SE document generators to surface v2.1 schema fields (intent, goals, moes, trade_offs, failure_modes, contract) so regenerated docs reflect the full semantic model.

**Architecture:** Each generator is a standalone module in `src/architecture_model/docs/se/`. Each reads the model and returns a markdown string. We add new sections/columns to each generator, write tests against known model fixtures, and regenerate all docs.

**Tech Stack:** Python dataclasses, pytest, architecture_model.core.types

**Worktree:** `/Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/model-quality-16wp`
**Branch:** `feature/model-quality-16wp`
**Test command:** `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`

---

## Shared Test Fixture

All tasks share this fixture. Create it in Task 1 and import in subsequent tasks.

```python
# tests/fixtures/se_doc_model.py
"""Shared model fixture for SE doc generator tests."""
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Capability,
    Actor, ActorType, Behavior, Interface, InterfaceType, Constraint,
    ConstraintType, Layer, Relationship, Status, Priority,
)


def make_model() -> ArchitectureModel:
    """Create a model with v2.1 fields populated for doc generation tests."""
    return ArchitectureModel(
        meta=ModelMeta(schema_version="2.1", project="test-project",
                       system="Test System", generated_at="2026-08-26"),
        entities=Entities(
            actors=[
                Actor(id="ACT-1", name="Developer", status=Status.ACTIVE,
                      type=ActorType.HUMAN, intent="Primary user of the system",
                      goals=["Ship features fast", "Maintain code quality"]),
            ],
            capabilities=[
                Capability(id="CAP-1", name="Model Validation", status=Status.ACTIVE,
                           description="Validates architecture models against schema",
                           intent="Ensure models are structurally correct before use",
                           priority=Priority.HIGH,
                           moes=["Validation score >= 80/100",
                                 "Zero critical issues on valid models"]),
                Capability(id="CAP-2", name="Context Formatting", status=Status.ACTIVE,
                           description="Compresses models for LLM consumption",
                           intent="Minimize token usage while preserving semantic content",
                           moes=["Compression ratio > 5x for repos > 50K tokens"]),
            ],
            components=[
                Component(id="COMP-1", name="Validator", status=Status.ACTIVE,
                          kind="library", layer="core",
                          description="Core validation engine",
                          intent="Single source of truth for model correctness",
                          responsibilities=["Schema validation", "Relationship integrity"],
                          goals=["100% coverage of schema rules"],
                          moes=["All 17 relationship types validated"],
                          trade_offs=["Strict validation vs permissive parsing",
                                      "Performance vs thoroughness"],
                          failure_modes=["Silent acceptance of invalid models",
                                         "False positives blocking valid models"],
                          files=["src/architecture_model/core/validator.py"]),
                Component(id="COMP-2", name="Slicer", status=Status.ACTIVE,
                          kind="library", layer="core",
                          description="Model slicing and filtering",
                          intent="Enable focused views of large models",
                          responsibilities=["F-block slicing", "Layer slicing"],
                          goals=["Sub-second slice operations"],
                          trade_offs=["Completeness vs token budget"],
                          files=["src/architecture_model/core/slicer.py"]),
            ],
            behaviors=[
                Behavior(id="BEH-1", name="Validate Model", status=Status.ACTIVE,
                         actor="ACT-1", trigger="User runs validate command",
                         preconditions=["Model file exists"],
                         steps=["Load model from YAML", "Run structural checks",
                                "Run semantic checks", "Return score"],
                         postconditions=["Validation result returned"]),
            ],
            interfaces=[
                Interface(id="IF-1", name="Validation API", status=Status.ACTIVE,
                          type=InterfaceType.FUNCTION_CALL,
                          description="validate_model(model) -> ValidationResult",
                          provider="COMP-1", consumer="COMP-2",
                          contract="Pre: model is parsed ArchitectureModel. Post: result.score in 0..100. Invariant: idempotent."),
            ],
            constraints=[
                Constraint(id="CON-1", name="Schema Compatibility", status=Status.ACTIVE,
                           type=ConstraintType.COMPATIBILITY,
                           description="Must support schema versions 1.0-2.1",
                           rationale="Backward compatibility with existing models"),
            ],
            layers=[
                Layer(id="L-1", name="Core", status=Status.ACTIVE, order=1,
                      technology="Python", directories=["src/architecture_model/core"]),
            ],
        ),
        relationships=[
            Relationship(from_id="COMP-1", to_id="CAP-1", type="realizes"),
            Relationship(from_id="COMP-2", to_id="CAP-2", type="realizes"),
            Relationship(from_id="COMP-2", to_id="COMP-1", type="depends-on"),
            Relationship(from_id="COMP-1", to_id="IF-1", type="exposes"),
            Relationship(from_id="BEH-1", to_id="COMP-1", type="traces-to"),
        ],
    )
```

---

### Task 1: Create shared test fixture and verify baseline

**Files:**
- Create: `tests/fixtures/__init__.py`
- Create: `tests/fixtures/se_doc_model.py`
- Test: `tests/test_se_doc_v21.py` (new — baseline verification)

**Step 1: Create fixture directory**

```bash
mkdir -p tests/fixtures
touch tests/fixtures/__init__.py
```

**Step 2: Write fixture file**

Write `tests/fixtures/se_doc_model.py` with the `make_model()` function from the Shared Test Fixture section above.

**Step 3: Write baseline test**

```python
# tests/test_se_doc_v21.py
"""Tests for v2.1 SE field rendering in doc generators."""
from tests.fixtures.se_doc_model import make_model


class TestBaselineGeneration:
    """Verify existing generators don't crash with v2.1 fields."""

    def test_conops_generates(self):
        from architecture_model.docs.se.conops import generate_conops
        model = make_model()
        result = generate_conops(model, manifest=None)
        assert "Test System" in result or "test-project" in result
        assert "Model Validation" in result

    def test_functional_analysis_generates(self):
        from architecture_model.docs.se.functional_analysis import generate_functional_analysis
        model = make_model()
        result = generate_functional_analysis(model, manifest=None)
        assert "CAP-1" in result

    def test_logical_architecture_generates(self):
        from architecture_model.docs.se.logical_architecture import generate_logical_architecture
        model = make_model()
        result = generate_logical_architecture(model, manifest=None)
        assert "Validator" in result

    def test_use_cases_generates(self):
        from architecture_model.docs.se.use_cases import generate_use_cases
        model = make_model()
        result = generate_use_cases(model, manifest=None)
        assert "Validate Model" in result

    def test_artifact_traceability_generates(self):
        from architecture_model.docs.se.artifact_traceability import generate_artifact_traceability
        model = make_model()
        result = generate_artifact_traceability(model, manifest=None)
        assert "COMP-1" in result or "components" in result.lower()
```

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_se_doc_v21.py -v`
Expected: All 5 PASS (v2.1 fields are ignored, no crash)

**Step 5: Commit**

```bash
git add tests/fixtures/ tests/test_se_doc_v21.py
git commit -m "test: add shared fixture and baseline tests for SE doc v2.1 integration"
```

---

### Task 2: Update ConOps generator — intent, goals, MOEs, failure modes

**Files:**
- Modify: `src/architecture_model/docs/se/conops.py`
- Test: `tests/test_se_doc_v21.py` (append)

**Step 1: Write failing tests**

Append to `tests/test_se_doc_v21.py`:

```python
class TestConopsV21:
    def test_capability_intent_rendered(self):
        from architecture_model.docs.se.conops import generate_conops
        model = make_model()
        result = generate_conops(model, manifest=None)
        assert "Ensure models are structurally correct" in result

    def test_capability_moes_rendered(self):
        from architecture_model.docs.se.conops import generate_conops
        model = make_model()
        result = generate_conops(model, manifest=None)
        assert "Validation score >= 80/100" in result

    def test_actor_intent_rendered(self):
        from architecture_model.docs.se.conops import generate_conops
        model = make_model()
        result = generate_conops(model, manifest=None)
        assert "Primary user of the system" in result
```

**Step 2: Run tests to verify they fail**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_se_doc_v21.py::TestConopsV21 -v`
Expected: FAIL — these strings don't appear in current output

**Step 3: Update `conops.py`**

In `src/architecture_model/docs/se/conops.py`, in the `generate_conops` function:

1. In the capability rendering section (around line 30-40), after each capability's description line, add intent and MOEs:

```python
# Replace the simple capability line with:
lines.append(f"- **{cap.name}**: {cap.description}")
if cap.intent:
    lines.append(f"  - *Intent:* {cap.intent}")
if cap.moes:
    lines.append(f"  - *Measures of Effectiveness:*")
    for moe in cap.moes:
        lines.append(f"    - {moe}")
```

2. In the actor rendering section (around line 50-65), after actor type/goals, add intent:

```python
if hasattr(actor, 'intent') and actor.intent:
    lines.append(f"  - *Intent:* {actor.intent}")
```

3. Add a new section before constraints (~line 120) for failure modes:

```python
failure_comps = [(c.name, c.failure_modes) for c in model.entities.components if c.failure_modes]
if failure_comps:
    lines.append("")
    lines.append("## Degraded Operations & Failure Modes")
    lines.append("")
    for comp_name, modes in failure_comps:
        lines.append(f"### {comp_name}")
        for mode in modes:
            lines.append(f"- {mode}")
        lines.append("")
```

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_se_doc_v21.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/architecture_model/docs/se/conops.py tests/test_se_doc_v21.py
git commit -m "feat(docs): surface intent, MOEs, failure modes in ConOps generator"
```

---

### Task 3: Update Functional Analysis generator — intent, MOEs, trade-offs

**Files:**
- Modify: `src/architecture_model/docs/se/functional_analysis.py`
- Test: `tests/test_se_doc_v21.py` (append)

**Step 1: Write failing tests**

Append to `tests/test_se_doc_v21.py`:

```python
class TestFunctionalAnalysisV21:
    def test_capability_intent_in_table(self):
        from architecture_model.docs.se.functional_analysis import generate_functional_analysis
        model = make_model()
        result = generate_functional_analysis(model, manifest=None)
        assert "Ensure models are structurally correct" in result

    def test_moes_section(self):
        from architecture_model.docs.se.functional_analysis import generate_functional_analysis
        model = make_model()
        result = generate_functional_analysis(model, manifest=None)
        assert "Measures of Effectiveness" in result
        assert "Validation score >= 80/100" in result

    def test_trade_offs_in_mapping(self):
        from architecture_model.docs.se.functional_analysis import generate_functional_analysis
        model = make_model()
        result = generate_functional_analysis(model, manifest=None)
        assert "Strict validation vs permissive parsing" in result
```

**Step 2: Run tests to verify they fail**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_se_doc_v21.py::TestFunctionalAnalysisV21 -v`
Expected: FAIL

**Step 3: Update `functional_analysis.py`**

In `src/architecture_model/docs/se/functional_analysis.py`:

1. Add `Intent` column to the capability inventory table (around line 35-45):

```python
lines.append("| ID | Name | Priority | Status | Description | Intent |")
lines.append("|---|---|---|---|---|---|")
for cap in model.entities.capabilities:
    p = cap.priority.value if hasattr(cap.priority, 'value') else str(cap.priority)
    s = cap.status.value if hasattr(cap.status, 'value') else str(cap.status)
    intent_col = cap.intent or "—"
    lines.append(f"| {cap.id} | {cap.name} | {p} | {s} | {cap.description} | {intent_col} |")
```

2. After the capability inventory table, add MOE section:

```python
caps_with_moes = [(c.id, c.name, c.moes) for c in model.entities.capabilities if c.moes]
if caps_with_moes:
    lines.append("")
    lines.append("## Measures of Effectiveness")
    lines.append("")
    lines.append("| Capability | MOE |")
    lines.append("|---|---|")
    for cid, cname, moes in caps_with_moes:
        for moe in moes:
            lines.append(f"| {cname} ({cid}) | {moe} |")
```

3. After the realizes mapping section, add trade-offs:

```python
comps_with_tradeoffs = [(c.id, c.name, c.trade_offs) for c in model.entities.components if c.trade_offs]
if comps_with_tradeoffs:
    lines.append("")
    lines.append("### Design Trade-offs")
    lines.append("")
    for cid, cname, toffs in comps_with_tradeoffs:
        lines.append(f"**{cname}** ({cid}):")
        for t in toffs:
            lines.append(f"- {t}")
        lines.append("")
```

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_se_doc_v21.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/architecture_model/docs/se/functional_analysis.py tests/test_se_doc_v21.py
git commit -m "feat(docs): add intent column, MOE table, trade-offs to Functional Analysis"
```

---

### Task 4: Update Logical Architecture generator — contract, trade-offs, intent

**Files:**
- Modify: `src/architecture_model/docs/se/logical_architecture.py`
- Test: `tests/test_se_doc_v21.py` (append)

**Step 1: Write failing tests**

Append to `tests/test_se_doc_v21.py`:

```python
class TestLogicalArchitectureV21:
    def test_component_intent_rendered(self):
        from architecture_model.docs.se.logical_architecture import generate_logical_architecture
        model = make_model()
        result = generate_logical_architecture(model, manifest=None)
        assert "Single source of truth" in result

    def test_interface_contract_rendered(self):
        from architecture_model.docs.se.logical_architecture import generate_logical_architecture
        model = make_model()
        result = generate_logical_architecture(model, manifest=None)
        assert "Pre: model is parsed" in result or "idempotent" in result

    def test_trade_offs_rendered(self):
        from architecture_model.docs.se.logical_architecture import generate_logical_architecture
        model = make_model()
        result = generate_logical_architecture(model, manifest=None)
        assert "Strict validation vs permissive parsing" in result
```

**Step 2: Run tests to verify they fail**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_se_doc_v21.py::TestLogicalArchitectureV21 -v`
Expected: FAIL

**Step 3: Update `logical_architecture.py`**

In `src/architecture_model/docs/se/logical_architecture.py`:

1. In the component detail section (around line 45-60), after responsibilities, add intent and trade-offs:

```python
if comp.intent:
    lines.append(f"  - *Intent:* {comp.intent}")
if comp.trade_offs:
    lines.append(f"  - *Trade-offs:*")
    for t in comp.trade_offs:
        lines.append(f"    - {t}")
```

2. In the interface section (around line 70-85), after each interface row, add contract:

```python
if iface.contract:
    lines.append(f"  - *Contract:* {iface.contract}")
```

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_se_doc_v21.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/architecture_model/docs/se/logical_architecture.py tests/test_se_doc_v21.py
git commit -m "feat(docs): add intent, contracts, trade-offs to Logical Architecture"
```

---

### Task 5: Update Use Cases generator — MOEs as success criteria, failure modes

**Files:**
- Modify: `src/architecture_model/docs/se/use_cases.py`
- Test: `tests/test_se_doc_v21.py` (append)

**Step 1: Write failing tests**

Append to `tests/test_se_doc_v21.py`:

```python
class TestUseCasesV21:
    def test_success_criteria_from_moes(self):
        from architecture_model.docs.se.use_cases import generate_use_cases
        model = make_model()
        result = generate_use_cases(model, manifest=None)
        # BEH-1 traces-to COMP-1, COMP-1 realizes CAP-1, CAP-1 has MOEs
        assert "Success Criteria" in result or "Validation score >= 80/100" in result

    def test_failure_modes_rendered(self):
        from architecture_model.docs.se.use_cases import generate_use_cases
        model = make_model()
        result = generate_use_cases(model, manifest=None)
        # COMP-1 has failure_modes, linked via traces-to from BEH-1
        assert "Failure Modes" in result or "Silent acceptance" in result
```

**Step 2: Run tests to verify they fail**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_se_doc_v21.py::TestUseCasesV21 -v`
Expected: FAIL

**Step 3: Update `use_cases.py`**

In `src/architecture_model/docs/se/use_cases.py`:

1. At the top of `generate_use_cases`, build relationship lookup maps:

```python
# Map: behavior_id -> [component_ids] via traces-to
beh_to_comps = {}
for r in model.relationships:
    rt = r.type.value if hasattr(r.type, 'value') else str(r.type)
    if rt == "traces-to":
        beh_to_comps.setdefault(r.from_id, []).append(r.to_id)

# Map: component_id -> [capability_ids] via realizes
comp_to_caps = {}
for r in model.relationships:
    rt = r.type.value if hasattr(r.type, 'value') else str(r.type)
    if rt == "realizes":
        comp_to_caps.setdefault(r.from_id, []).append(r.to_id)

comp_map = {c.id: c for c in model.entities.components}
cap_map = {c.id: c for c in model.entities.capabilities}
```

2. After each behavior's postconditions rendering, add success criteria and failure modes:

```python
# Collect MOEs and failure modes via relationship chain
linked_comps = beh_to_comps.get(beh.id, [])
linked_caps = set()
for comp_id in linked_comps:
    for cap_id in comp_to_caps.get(comp_id, []):
        linked_caps.add(cap_id)

moes = []
for cap_id in linked_caps:
    cap = cap_map.get(cap_id)
    if cap and cap.moes:
        moes.extend(cap.moes)

failure_modes = []
for comp_id in linked_comps:
    comp = comp_map.get(comp_id)
    if comp and comp.failure_modes:
        failure_modes.extend(comp.failure_modes)

if moes:
    lines.append("")
    lines.append("**Success Criteria:**")
    for moe in moes:
        lines.append(f"- {moe}")

if failure_modes:
    lines.append("")
    lines.append("**Failure Modes:**")
    for fm in failure_modes:
        lines.append(f"- {fm}")
```

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_se_doc_v21.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/architecture_model/docs/se/use_cases.py tests/test_se_doc_v21.py
git commit -m "feat(docs): add success criteria and failure modes to Use Cases via relationship chain"
```

---

### Task 6: Update Artifact Traceability generator — gap detection for MOEs and contracts

**Files:**
- Modify: `src/architecture_model/docs/se/artifact_traceability.py`
- Test: `tests/test_se_doc_v21.py` (append)

**Step 1: Write failing tests**

Append to `tests/test_se_doc_v21.py`:

```python
class TestArtifactTraceabilityV21:
    def test_moe_gap_detection(self):
        from architecture_model.docs.se.artifact_traceability import generate_artifact_traceability
        from tests.fixtures.se_doc_model import make_model
        model = make_model()
        # Remove MOEs from CAP-2 to create a gap
        model.entities.capabilities[1].moes = []
        result = generate_artifact_traceability(model, manifest=None)
        assert "without MOE" in result.lower() or "missing moe" in result.lower()

    def test_contract_gap_detection(self):
        from architecture_model.docs.se.artifact_traceability import generate_artifact_traceability
        from tests.fixtures.se_doc_model import make_model
        model = make_model()
        # Clear contract to create a gap
        model.entities.interfaces[0].contract = ""
        result = generate_artifact_traceability(model, manifest=None)
        assert "without contract" in result.lower() or "missing contract" in result.lower()
```

**Step 2: Run tests to verify they fail**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_se_doc_v21.py::TestArtifactTraceabilityV21 -v`
Expected: FAIL

**Step 3: Update `artifact_traceability.py`**

In `src/architecture_model/docs/se/artifact_traceability.py`, find the gap analysis section (Section 5, around line 350-380). Add new gap checks:

```python
lines.append("")
lines.append("### Semantic Completeness Gaps")
lines.append("")

# MOE gaps
caps_without_moes = [c for c in model.entities.capabilities if not c.moes]
if caps_without_moes:
    lines.append(f"**Capabilities without MOEs:** {len(caps_without_moes)}")
    for c in caps_without_moes:
        lines.append(f"- {c.id}: {c.name} — missing MOE definition")
    lines.append("")

# Contract gaps
ifaces_without_contract = [i for i in model.entities.interfaces if not i.contract]
if ifaces_without_contract:
    lines.append(f"**Interfaces without contract:** {len(ifaces_without_contract)}")
    for i in ifaces_without_contract:
        lines.append(f"- {i.id}: {i.name} — missing contract (pre/post/invariant)")
    lines.append("")

# Intent gaps
entities_without_intent = []
for c in model.entities.components:
    if not c.intent:
        entities_without_intent.append(f"{c.id}: {c.name} (component)")
for c in model.entities.capabilities:
    if not c.intent:
        entities_without_intent.append(f"{c.id}: {c.name} (capability)")
if entities_without_intent:
    lines.append(f"**Entities without intent:** {len(entities_without_intent)}")
    for e in entities_without_intent:
        lines.append(f"- {e}")
    lines.append("")
```

**Step 4: Run tests**

Run: `/opt/anaconda3/bin/python -m pytest tests/test_se_doc_v21.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/architecture_model/docs/se/artifact_traceability.py tests/test_se_doc_v21.py
git commit -m "feat(docs): add semantic completeness gap detection to Artifact Traceability"
```

---

### Task 7: Full suite verification and doc regeneration

**Step 1: Run full test suite**

Run: `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`
Expected: Same 5 pre-existing failures, 0 new failures

**Step 2: Regenerate top-level docs (optional, verify manually)**

```bash
cd /Users/baigm2/Documents/Projects/architecture-model-standard/.worktrees/model-quality-16wp
architecture-model docs . --se
```

Verify the generated docs contain the new sections.

**Step 3: Commit any generated doc changes if desired**

```bash
git add .architecture-models/docs/se/
git commit -m "docs: regenerate SE documents with v2.1 field content"
```

---

## Execution Order Summary

| Task | What | Complexity | Est. Effort |
|------|------|-----------|-------------|
| 1 | Shared fixture + baseline tests | Low | 10 min |
| 2 | ConOps: intent, MOEs, failure modes | Medium | 20 min |
| 3 | Functional Analysis: intent column, MOE table, trade-offs | Medium | 20 min |
| 4 | Logical Architecture: contract, trade-offs, intent | Low | 15 min |
| 5 | Use Cases: success criteria, failure modes (relationship joins) | High | 25 min |
| 6 | Artifact Traceability: gap detection | Low | 15 min |
| 7 | Full verification + doc regen | Low | 10 min |

**Total estimated: ~2 hours**

All tasks are sequential (shared test file). No parallelization opportunities.
