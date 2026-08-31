# Model Quality Improvement — 16 Work Packages Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Execute all 16 work packages to evolve the architecture model standard from structurally valid but semantically hollow to fully specified, enriched, and LLM-reviewable.

**Architecture:** 4 phases with strict dependency ordering. Phase 1 (Foundation) adds schema fields and fixes contamination. Phase 2 (Intelligence) adds pipeline narratives and LLM hooks. Phase 3 (Quality Loop) upgrades validation and review. Phase 4 (Delivery) adds budget-aware slicing, MCP updates, and PDF output.

**Tech Stack:** Python 3.12, dataclasses, JSON Schema Draft 2020-12, YAML, pytest

**Test command:** `/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py`

**Pre-existing failures (7):** test_includes_confidence, test_includes_components, test_has_f1_through_f6, test_has_functional_blocks, test_real_logs_db, test_name_version_requires, test_schema_json_has_all_relationship_types — DO NOT fix these; they are known.

---

## Phase 1: Foundation

### Task 1: WP-6 — Type System Update (`types.py`)

**Files:**
- Modify: `src/architecture_model/core/types.py:288-298` (BaseEntity), `:312-317` (Capability), `:478-501` (Component), `:606-613` (Requirement), `:372-379` (Interface)
- Test: `tests/test_wp6_se_fields.py` (new)

**Step 1: Write failing tests for new SE fields**

Create `tests/test_wp6_se_fields.py`:

```python
"""Tests for WP-6 SE fields on entity dataclasses."""
from architecture_model.core.types import (
    Actor, Behavior, Capability, Component, Constraint,
    Interface, Requirement, Status,
)


class TestBaseEntitySEFields:
    def test_intent_default_empty(self):
        """All entities should have intent field defaulting to empty string."""
        c = Component(id="C-1", name="Test", status=Status.ACTIVE)
        assert c.intent == ""

    def test_intent_settable(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE,
                      intent="Provide validation for architecture models")
        assert c.intent == "Provide validation for architecture models"


class TestComponentSEFields:
    def test_goals_default_empty(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE)
        assert c.goals == []

    def test_moes_default_empty(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE)
        assert c.moes == []

    def test_trade_offs_default_empty(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE)
        assert c.trade_offs == []

    def test_failure_modes_default_empty(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE)
        assert c.failure_modes == []

    def test_all_se_fields_populated(self):
        c = Component(
            id="C-1", name="Test", status=Status.ACTIVE,
            intent="Enable structural validation",
            goals=["Catch 95% of model errors", "Sub-second validation"],
            moes=["error detection rate", "p99 latency"],
            trade_offs=["Strictness vs usability"],
            failure_modes=["Silent pass on malformed YAML"],
        )
        assert len(c.goals) == 2
        assert len(c.moes) == 2
        assert c.trade_offs[0] == "Strictness vs usability"


class TestCapabilitySEFields:
    def test_moes_default_empty(self):
        c = Capability(id="CAP-1", name="Test", status=Status.ACTIVE)
        assert c.moes == []

    def test_intent_default_empty(self):
        c = Capability(id="CAP-1", name="Test", status=Status.ACTIVE)
        assert c.intent == ""


class TestRequirementSEFields:
    def test_rationale_default_empty(self):
        r = Requirement(id="REQ-1", name="Test", status=Status.ACTIVE)
        assert r.rationale == ""

    def test_priority_default_empty(self):
        r = Requirement(id="REQ-1", name="Test", status=Status.ACTIVE)
        assert r.priority == ""

    def test_moe_default_empty(self):
        r = Requirement(id="REQ-1", name="Test", status=Status.ACTIVE)
        assert r.moe == ""


class TestBehaviorSEFields:
    def test_intent_default_empty(self):
        b = Behavior(id="BEH-1", name="Test", status=Status.ACTIVE)
        assert b.intent == ""


class TestInterfaceSEFields:
    def test_contract_default_empty(self):
        i = Interface(id="IF-1", name="Test", status=Status.ACTIVE)
        assert i.contract == ""


class TestConstraintSEFields:
    def test_rationale_already_exists(self):
        """Constraint already has rationale — verify it still works."""
        c = Constraint(id="CON-1", name="Test", status=Status.ACTIVE,
                       rationale="Required by ISO 25010")
        assert c.rationale == "Required by ISO 25010"

    def test_intent_default_empty(self):
        c = Constraint(id="CON-1", name="Test", status=Status.ACTIVE)
        assert c.intent == ""
```

**Step 2: Run tests — expect failures**

```bash
/opt/anaconda3/bin/python -m pytest tests/test_wp6_se_fields.py -v
```

Expected: FAIL on `intent`, `goals`, `moes`, `trade_offs`, `failure_modes`, `contract` (on Interface), `rationale`/`priority`/`moe` (on Requirement).

**Step 3: Add SE fields to dataclasses in `types.py`**

Add to `BaseEntity` (line 298, after `confidence`):
```python
    intent: str = ""
```

Add to `Component` (after `external_dependencies` field, ~line 500):
```python
    goals: list[str] = field(default_factory=list)
    moes: list[str] = field(default_factory=list)
    trade_offs: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
```

Add to `Capability` (after `requirements` field, line 316):
```python
    moes: list[str] = field(default_factory=list)
```

Add to `Requirement` (after `content_hash` field, line 612):
```python
    rationale: str = ""
    priority: str = ""
    moe: str = ""
```

Add to `Interface` (after `schema` field, line 379):
```python
    contract: str = ""
```

Note: `Behavior` and `Constraint` already inherit `intent` from BaseEntity. `Constraint` already has `rationale`.

**Step 4: Run tests — expect pass**

```bash
/opt/anaconda3/bin/python -m pytest tests/test_wp6_se_fields.py -v
```

**Step 5: Run full test suite to check for regressions**

```bash
/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py 2>&1 | tail -30
```

Expected: No new failures beyond the 7 pre-existing ones.

**Step 6: Commit**

```bash
git add src/architecture_model/core/types.py tests/test_wp6_se_fields.py
git commit -m "feat(schema): add SE fields — intent, goals, moes, trade_offs, failure_modes, contract, rationale"
```

---

### Task 2: WP-1 — JSON Schema Evolution (`schema.json`)

**Files:**
- Modify: `src/architecture_model/spec/schema.json`
- Test: `tests/test_wp1_schema_evolution.py` (new)

**Step 1: Write failing test**

Create `tests/test_wp1_schema_evolution.py`:

```python
"""Tests for WP-1 schema evolution — new SE fields in JSON Schema."""
import json
from pathlib import Path

import jsonschema


SCHEMA_PATH = Path(__file__).parent.parent / "src" / "architecture_model" / "spec" / "schema.json"


def _load_schema():
    return json.loads(SCHEMA_PATH.read_text())


class TestSchemaNewFields:
    def test_base_entity_has_intent(self):
        schema = _load_schema()
        base = schema["$defs"]["base_entity"]["properties"]
        assert "intent" in base

    def test_component_has_goals(self):
        schema = _load_schema()
        comp = schema["$defs"]["component"]["properties"]
        assert "goals" in comp

    def test_component_has_moes(self):
        schema = _load_schema()
        comp = schema["$defs"]["component"]["properties"]
        assert "moes" in comp

    def test_component_has_trade_offs(self):
        schema = _load_schema()
        comp = schema["$defs"]["component"]["properties"]
        assert "trade_offs" in comp

    def test_component_has_failure_modes(self):
        schema = _load_schema()
        comp = schema["$defs"]["component"]["properties"]
        assert "failure_modes" in comp

    def test_capability_has_moes(self):
        schema = _load_schema()
        cap = schema["$defs"]["capability"]["properties"]
        assert "moes" in cap

    def test_requirement_has_rationale(self):
        schema = _load_schema()
        req = schema["$defs"]["requirement"]["properties"]
        assert "rationale" in req

    def test_requirement_has_priority(self):
        schema = _load_schema()
        req = schema["$defs"]["requirement"]["properties"]
        assert "priority" in req

    def test_interface_has_contract(self):
        schema = _load_schema()
        iface = schema["$defs"]["interface"]["properties"]
        assert "contract" in iface

    def test_schema_version_bumped(self):
        schema = _load_schema()
        assert "2.1" in schema["$id"], f"Schema $id should reference v2.1: {schema['$id']}"


class TestSchemaValidation:
    """Ensure a model with new fields validates against updated schema."""

    def test_model_with_se_fields_validates(self):
        schema = _load_schema()
        model = {
            "meta": {
                "schema_version": "2.1.0",
                "project": "test",
                "generated_at": "2026-01-01T00:00:00Z",
            },
            "entities": {
                "components": [{
                    "id": "COMP-1",
                    "name": "Test",
                    "status": "ACTIVE",
                    "intent": "Provide core functionality",
                    "goals": ["High reliability"],
                    "moes": ["99.9% uptime"],
                    "trade_offs": ["Speed vs accuracy"],
                    "failure_modes": ["Timeout on large models"],
                }],
                "capabilities": [{
                    "id": "CAP-1",
                    "name": "Validation",
                    "status": "ACTIVE",
                    "moes": ["Catch 95% of errors"],
                }],
                "requirements": [{
                    "id": "REQ-1",
                    "name": "Must validate",
                    "status": "ACTIVE",
                    "rationale": "Ensures model correctness",
                    "priority": "must",
                    "moe": "Zero false negatives on structural checks",
                }],
                "interfaces": [{
                    "id": "IF-1",
                    "name": "Validate API",
                    "status": "ACTIVE",
                    "contract": "Input: ArchitectureModel, Output: ValidationResult",
                }],
            },
            "relationships": [],
        }
        jsonschema.validate(model, schema)  # Should not raise
```

**Step 2: Run tests — expect failures**

```bash
/opt/anaconda3/bin/python -m pytest tests/test_wp1_schema_evolution.py -v
```

**Step 3: Update `schema.json`**

Changes:
1. Bump `$id` to `v2.1.0`
2. Add `"intent": { "type": "string" }` to `base_entity.properties` (line 121)
3. Add `"intent": true` to every entity's property allowlist (actor, capability, behavior, interface, constraint, layer, component, system, data, event, resource, environment, quality_attribute, decision, lifecycle)
4. Add to `component.properties`:
   - `"goals": { "type": "array", "items": { "type": "string" } }`
   - `"moes": { "type": "array", "items": { "type": "string" } }`
   - `"trade_offs": { "type": "array", "items": { "type": "string" } }`
   - `"failure_modes": { "type": "array", "items": { "type": "string" } }`
5. Add to `capability.properties`: `"moes": { "type": "array", "items": { "type": "string" } }`
6. Add `requirements` array to entities properties block (currently missing from schema)
7. Add `$defs/requirement` definition with fields: `text`, `source_doc`, `source_anchor`, `content_hash`, `rationale`, `priority`, `moe`
8. Add to `interface.properties`: `"contract": { "type": "string" }`

**Step 4: Run tests — expect pass**

```bash
/opt/anaconda3/bin/python -m pytest tests/test_wp1_schema_evolution.py -v
```

**Step 5: Run full test suite**

```bash
/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py 2>&1 | tail -30
```

**Step 6: Commit**

```bash
git add src/architecture_model/spec/schema.json tests/test_wp1_schema_evolution.py
git commit -m "feat(schema): evolve JSON Schema to v2.1 with SE fields"
```

---

### Task 3: WP-16 — Parser Round-Trip Tests for New Fields

**Files:**
- Test: `tests/test_wp16_roundtrip.py` (new)
- Modify: `src/architecture_model/core/parser.py` (only if round-trip fails)

**Step 1: Write round-trip test**

Create `tests/test_wp16_roundtrip.py`:

```python
"""WP-16: Round-trip tests ensuring new SE fields survive parse->serialize->parse."""
import yaml

from architecture_model.core.parser import _parse_raw
from architecture_model.core.types import Status


def _make_model_dict():
    return {
        "meta": {
            "schema_version": "2.1",
            "project": "test",
            "generated_at": "2026-01-01",
        },
        "entities": {
            "components": [{
                "id": "COMP-1",
                "name": "Core",
                "status": "ACTIVE",
                "intent": "Provide validation",
                "goals": ["High accuracy"],
                "moes": ["99% detection"],
                "trade_offs": ["Speed vs depth"],
                "failure_modes": ["OOM on large models"],
            }],
            "capabilities": [{
                "id": "CAP-1",
                "name": "Validate",
                "status": "ACTIVE",
                "intent": "Ensure correctness",
                "moes": ["Catch all structural errors"],
            }],
            "requirements": [{
                "id": "REQ-1",
                "name": "Must validate",
                "status": "ACTIVE",
                "intent": "Correctness assurance",
                "rationale": "Models used for code gen",
                "priority": "must",
                "moe": "Zero false negatives",
            }],
            "interfaces": [{
                "id": "IF-1",
                "name": "Validate API",
                "status": "ACTIVE",
                "intent": "Entry point for validation",
                "contract": "ArchitectureModel -> ValidationResult",
            }],
            "behaviors": [{
                "id": "BEH-1",
                "name": "Run Validation",
                "status": "ACTIVE",
                "intent": "User triggers validation of a model file",
            }],
            "constraints": [{
                "id": "CON-1",
                "name": "Performance",
                "status": "ACTIVE",
                "intent": "Keep validation fast",
                "rationale": "Used in CI pipelines",
            }],
        },
        "relationships": [],
    }


class TestRoundTrip:
    def test_component_se_fields_survive_parse(self):
        model = _parse_raw(_make_model_dict())
        c = model.entities.components[0]
        assert c.intent == "Provide validation"
        assert c.goals == ["High accuracy"]
        assert c.moes == ["99% detection"]
        assert c.trade_offs == ["Speed vs depth"]
        assert c.failure_modes == ["OOM on large models"]

    def test_capability_se_fields_survive_parse(self):
        model = _parse_raw(_make_model_dict())
        cap = model.entities.capabilities[0]
        assert cap.intent == "Ensure correctness"
        assert cap.moes == ["Catch all structural errors"]

    def test_requirement_se_fields_survive_parse(self):
        model = _parse_raw(_make_model_dict())
        r = model.entities.requirements[0]
        assert r.rationale == "Models used for code gen"
        assert r.priority == "must"
        assert r.moe == "Zero false negatives"

    def test_interface_contract_survives_parse(self):
        model = _parse_raw(_make_model_dict())
        i = model.entities.interfaces[0]
        assert i.contract == "ArchitectureModel -> ValidationResult"

    def test_to_dict_preserves_se_fields(self):
        model = _parse_raw(_make_model_dict())
        d = model.to_dict()
        comp = d["entities"]["components"][0]
        assert comp["intent"] == "Provide validation"
        assert comp["goals"] == ["High accuracy"]
        assert comp["moes"] == ["99% detection"]

    def test_yaml_roundtrip(self):
        model = _parse_raw(_make_model_dict())
        yaml_str = model.to_yaml()
        reparsed = yaml.safe_load(yaml_str)
        comp = reparsed["entities"]["components"][0]
        assert comp["intent"] == "Provide validation"
        assert comp["goals"] == ["High accuracy"]
```

**Step 2: Run tests — may pass immediately if parser uses generic approach**

```bash
/opt/anaconda3/bin/python -m pytest tests/test_wp16_roundtrip.py -v
```

If failures: fix `_parse_raw()` in `parser.py` to handle new fields.

**Step 3: Run full suite, commit**

```bash
git add tests/test_wp16_roundtrip.py
git commit -m "test: add round-trip tests for SE fields (WP-16)"
```

---

### Task 4: WP-8 — Fix Contamination + Enrich Root Model

**Files:**
- Modify: `.architecture-model.yaml` (delete BEH-1 through BEH-18 Django routes, populate empty fields)

**Step 1: Identify contaminated behaviors**

Read `.architecture-model.yaml` behaviors section. BEH-1 through BEH-18 are Django admin routes from logs_db (wrong project). Names like "GET ''", "GET bookmarklets/", "GET tags/", "GET filters/".

**Step 2: Delete contaminated behaviors and their relationships**

Remove all BEH-* entries that reference Django routes. Remove all relationships referencing deleted BEH IDs.

**Step 3: Populate empty fields on actors**

For each actor (ACT-1 AI Agent, ACT-2 Developer, ACT-3 CI/CD), add meaningful `goals` and `intent`.

**Step 4: Run validation**

```bash
/opt/anaconda3/bin/python -m architecture_model validate .architecture-model.yaml
```

**Step 5: Commit**

```bash
git add .architecture-model.yaml
git commit -m "fix(model): remove contaminated Django behaviors, populate actor goals (WP-8)"
```

---

## Phase 2: Intelligence

### Task 5: WP-5 — Stage Summaries

**Files:**
- Modify: `src/architecture_model/pipeline/protocol.py:103-113` (add `summary` to StageResult)
- Modify: `src/architecture_model/pipeline/report.py:93+` (add synthesize/emit to _extract_findings, use summary)
- Modify: Pipeline stage files to write summaries: `observe.py`, `infer.py`, `allocate.py`, `relate.py`, `specify.py`, `contract.py`, `decompose.py`, `synthesize.py`
- Test: `tests/test_wp5_stage_summaries.py` (new)

**Step 1: Write failing test**

```python
"""WP-5: Stage summaries — qualitative narrative on StageResult."""
from architecture_model.pipeline.protocol import StageResult, QualityMetrics


class TestStageSummary:
    def test_summary_field_exists(self):
        result = StageResult(
            output={},
            quality=QualityMetrics(score=85.0),
            summary="Discovered 14 capabilities across 6 functional blocks",
        )
        assert result.summary == "Discovered 14 capabilities across 6 functional blocks"

    def test_summary_defaults_empty(self):
        result = StageResult(output={}, quality=QualityMetrics(score=85.0))
        assert result.summary == ""
```

**Step 2: Add `summary: str = ""` to StageResult** (after `version` field, line 113)

**Step 3: Update `_extract_findings()` in `report.py`**
- Add cases for `synthesize` and `emit` stages
- Include `result.summary` in the findings output when non-empty

**Step 4: Update each stage's `run()` method** to set `summary` on the returned StageResult. Each stage should write 1-2 sentence narrative:
- observe: "Scanned {n} files, found {m} modules with {k} import edges"
- infer: "Inferred {n} capabilities, {m} actors, {k} behaviors from code patterns"
- allocate: "Allocated {n} files to {m} components ({p}% coverage)"
- relate: "Derived {n} relationships ({types breakdown})"
- specify: "Specified {n} interfaces"
- contract: "Extracted {n} contracts"
- decompose: "Identified {n} systems, {m} inline components"
- synthesize: "Ran {n} sub-pipelines, all converged"

**Step 5: Run full test suite, commit**

```bash
git commit -m "feat(pipeline): add qualitative summaries to StageResult (WP-5)"
```

---

### Task 6: WP-2 — Detail Level Indicator

**Files:**
- Create: `src/architecture_model/core/detail_level.py`
- Test: `tests/test_wp2_detail_level.py` (new)

**Step 1: Write failing test**

```python
"""WP-2: Detail level scoring — L0 through L4."""
from architecture_model.core.detail_level import compute_detail_level, DetailLevel
from architecture_model.core.types import Component, Capability, Behavior, Interface, Status


class TestDetailLevel:
    def test_skeleton_component(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE)
        assert compute_detail_level(c) == DetailLevel.L0_SKELETON

    def test_described_component(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE,
                      description="A test component")
        assert compute_detail_level(c) == DetailLevel.L1_DESCRIBED

    def test_specified_component(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE,
                      description="A test component",
                      intent="Provide testing",
                      responsibilities=["Parse", "Validate"])
        assert compute_detail_level(c) == DetailLevel.L2_SPECIFIED

    def test_enriched_component(self):
        from architecture_model.core.types import FunctionSignature, TestContract
        c = Component(id="C-1", name="Test", status=Status.ACTIVE,
                      description="A test component",
                      intent="Provide testing",
                      responsibilities=["Parse"],
                      signatures=[FunctionSignature(name="parse", params=["path"])],
                      test_contracts=[TestContract(assertion="returns dict",
                                                   contract_type="output",
                                                   test_method="test_parse")])
        assert compute_detail_level(c) == DetailLevel.L3_ENRICHED

    def test_reviewed_component(self):
        c = Component(id="C-1", name="Test", status=Status.ACTIVE,
                      extensions={"_llm_review": {"timestamp": "2026-01-01"}})
        assert compute_detail_level(c) == DetailLevel.L4_REVIEWED
```

**Step 2: Implement `detail_level.py`**

```python
"""Detail level scoring for architecture entities.

Levels:
  L0 (Skeleton)  — id, name, status only
  L1 (Described) — has description
  L2 (Specified) — has intent + responsibilities/steps/protocol
  L3 (Enriched)  — has signatures + test_contracts
  L4 (Reviewed)  — has been LLM-reviewed (extensions['_llm_review'] present)
"""
from enum import IntEnum
from architecture_model.core.types import BaseEntity, Component, Capability, Behavior, Interface


class DetailLevel(IntEnum):
    L0_SKELETON = 0
    L1_DESCRIBED = 1
    L2_SPECIFIED = 2
    L3_ENRICHED = 3
    L4_REVIEWED = 4


def compute_detail_level(entity: BaseEntity) -> DetailLevel:
    """Compute detail level from field population. Not stored — always derived."""
    if entity.extensions.get("_llm_review"):
        return DetailLevel.L4_REVIEWED

    if isinstance(entity, Component):
        if entity.signatures and entity.test_contracts:
            return DetailLevel.L3_ENRICHED

    has_intent = bool(entity.intent)
    has_detail = False
    if isinstance(entity, Component):
        has_detail = bool(entity.responsibilities)
    elif isinstance(entity, Behavior):
        has_detail = bool(entity.steps)
    elif isinstance(entity, Interface):
        has_detail = bool(entity.protocol)
    elif isinstance(entity, Capability):
        has_detail = bool(getattr(entity, 'moes', None))
    else:
        has_detail = has_intent

    if has_intent and has_detail:
        return DetailLevel.L2_SPECIFIED

    if entity.description:
        return DetailLevel.L1_DESCRIBED

    return DetailLevel.L0_SKELETON
```

**Step 3: Run tests, commit**

```bash
git commit -m "feat(core): add detail level scoring L0-L4 (WP-2)"
```

---

### Task 7: WP-4 — LLM Enrichment Hooks in Pipeline

**Files:**
- Modify: `src/architecture_model/pipeline/protocol.py` (verify `llm_enrich` callback)
- Modify: `src/architecture_model/pipeline/infer.py` (add enrichment hook)
- Modify: `src/architecture_model/pipeline/specify.py` (add enrichment hook)
- Test: `tests/test_wp4_llm_hooks.py` (new)

**Step 1: Write test**

```python
"""WP-4: LLM enrichment hooks in pipeline stages."""
import asyncio
from unittest.mock import AsyncMock
from architecture_model.pipeline.protocol import PipelineContext
from pathlib import Path


class TestLLMEnrichmentHook:
    def test_context_has_llm_callback(self):
        ctx = PipelineContext(repo_path=Path("/tmp"), output_dir=Path("/tmp"))
        assert ctx.llm_callback is None

    def test_context_llm_enrich_skips_when_no_callback(self):
        ctx = PipelineContext(repo_path=Path("/tmp"), output_dir=Path("/tmp"))
        result = asyncio.run(ctx.llm_enrich("infer", "describe this", {}))
        assert result is None

    def test_context_llm_enrich_calls_callback(self):
        mock = AsyncMock(return_value="A validation engine")
        ctx = PipelineContext(
            repo_path=Path("/tmp"), output_dir=Path("/tmp"),
            llm_callback=mock,
        )
        result = asyncio.run(ctx.llm_enrich("infer", "describe this", {"code": "..."}))
        mock.assert_called_once()
        assert result == "A validation engine"
```

**Step 2: Verify `llm_enrich` in protocol.py** already supports this pattern (line 144). Fix if it doesn't gracefully return None when no callback.

**Step 3: Add opt-in enrichment calls in `infer.py`** — after capabilities identified, if `ctx.llm_callback` set, call to generate descriptions/intents. Guard with `if ctx.llm_callback:`.

**Step 4: Same for `specify.py`** — after interfaces identified, use LLM to describe protocol/contract.

**Step 5: Run tests, commit**

```bash
git commit -m "feat(pipeline): add LLM enrichment hooks in infer and specify stages (WP-4)"
```

---

### Task 8: WP-14 — Behavior Reconstruction

**Files:**
- Create: `src/architecture_model/pipeline/reconstruct_behaviors.py`
- Test: `tests/test_wp14_behavior_reconstruction.py` (new)

**Step 1: Write test**

```python
"""WP-14: Behavior reconstruction from call graph and capability mapping."""
from architecture_model.pipeline.reconstruct_behaviors import reconstruct_behaviors
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Capability, Component,
    Relationship, RelationType, Status,
)


class TestBehaviorReconstruction:
    def test_generates_behavior_per_capability(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(
                capabilities=[
                    Capability(id="CAP-1", name="Validate Model", status=Status.ACTIVE,
                               description="Validates architecture models"),
                ],
                components=[
                    Component(id="COMP-1", name="Validator", status=Status.ACTIVE),
                ],
            ),
            relationships=[
                Relationship(type=RelationType.REALIZES, from_id="COMP-1", to_id="CAP-1"),
            ],
        )
        behaviors, rels = reconstruct_behaviors(model)
        assert len(behaviors) >= 1
        assert any("Validate" in b.name for b in behaviors)
        assert all(b.intent for b in behaviors), "All behaviors should have intent"
        assert all(b.steps for b in behaviors), "All behaviors should have steps"
        assert len(rels) >= 1  # traces-to relationships
```

**Step 2: Implement `reconstruct_behaviors.py`**

```python
"""Reconstruct behaviors from capabilities and component relationships.

For each capability, generates a behavior with:
- Name derived from capability name
- Intent from capability description
- Steps derived from realizing components
- trigger, actor set to reasonable defaults
"""
from architecture_model.core.types import (
    ArchitectureModel, Behavior, Relationship, RelationType, Status,
)


def reconstruct_behaviors(model: ArchitectureModel) -> tuple[list[Behavior], list[Relationship]]:
    """Generate behaviors for capabilities that lack them."""
    existing_cap_ids = set()
    for r in model.relationships:
        if r.type == RelationType.TRACES_TO:
            existing_cap_ids.add(r.to_id)

    behaviors = []
    rels = []
    cap_to_components = {}
    for r in model.relationships:
        if r.type == RelationType.REALIZES:
            cap_to_components.setdefault(r.to_id, []).append(r.from_id)

    comp_map = {c.id: c for c in model.entities.components}

    for i, cap in enumerate(model.entities.capabilities, 1):
        if cap.id in existing_cap_ids:
            continue
        comp_ids = cap_to_components.get(cap.id, [])
        comp_names = [comp_map[cid].name for cid in comp_ids if cid in comp_map]
        steps = [f"Invoke {name}" for name in comp_names] or [f"Execute {cap.name}"]

        beh = Behavior(
            id=f"BEH-R{i}",
            name=f"Perform {cap.name}",
            status=Status.ACTIVE,
            intent=cap.description or f"Behavior for {cap.name}",
            trigger=f"User or system requests {cap.name.lower()}",
            steps=steps,
        )
        behaviors.append(beh)
        rels.append(Relationship(
            type=RelationType.TRACES_TO,
            from_id=beh.id, to_id=cap.id,
            description=f"{beh.name} traces to {cap.name}",
        ))

    return behaviors, rels
```

**Step 3: Run tests, commit**

```bash
git commit -m "feat(pipeline): add behavior reconstruction from capabilities (WP-14)"
```

---

## Phase 3: Quality Loop

### Task 9: WP-11 — Validator Scoring Update

**Files:**
- Modify: `src/architecture_model/core/validator.py`
- Test: `tests/test_wp11_semantic_scoring.py` (new)

**Step 1: Write test**

```python
"""WP-11: Two-tier validation scoring — structural + semantic."""
from architecture_model.core.validator import validate_model
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Status,
)


class TestSemanticScoring:
    def test_validation_result_has_semantic_sub_scores(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(components=[
                Component(id="COMP-1", name="C", status=Status.ACTIVE,
                          description="Core", intent="Provide validation",
                          responsibilities=["Parse", "Check"]),
            ]),
            relationships=[],
        )
        result = validate_model(model)
        assert hasattr(result, 'semantic_issues') or any(
            'SEMANTIC' in str(i) for i in result.issues
        )
```

**Step 2: Add semantic checks** to validator — INFO-level diagnostics for missing intent, responsibilities, moes. These inform but don't penalize the structural score.

**Step 3: Run tests, commit**

```bash
git commit -m "feat(validator): add semantic scoring dimension (WP-11)"
```

---

### Task 10: WP-3 — LLM Entity Review Loop

**Files:**
- Create: `src/architecture_model/core/review.py`
- Test: `tests/test_wp3_entity_review.py` (new)

**Step 1: Write test**

```python
"""WP-3: LLM entity review loop."""
from architecture_model.core.review import prepare_review_prompt, apply_review
from architecture_model.core.types import Component, Status


class TestEntityReview:
    def test_prepare_review_prompt_for_component(self):
        c = Component(id="COMP-1", name="Validator", status=Status.ACTIVE,
                      description="Validates models")
        prompt = prepare_review_prompt(c)
        assert "COMP-1" in prompt
        assert "Validator" in prompt
        assert "intent" in prompt.lower()  # should ask about missing fields

    def test_apply_review_sets_extension(self):
        c = Component(id="COMP-1", name="Validator", status=Status.ACTIVE)
        reviewed = apply_review(c, {"intent": "Ensure model correctness",
                                     "review_notes": "Good coverage"})
        assert reviewed.intent == "Ensure model correctness"
        assert reviewed.extensions.get("_llm_review") is not None

    def test_apply_review_preserves_existing_fields(self):
        c = Component(id="COMP-1", name="Validator", status=Status.ACTIVE,
                      description="Original description")
        reviewed = apply_review(c, {"intent": "New intent"})
        assert reviewed.description == "Original description"
```

**Step 2: Implement `review.py`**

```python
"""LLM entity review loop — prepare prompts and apply review results."""
import copy
from datetime import datetime, timezone
from architecture_model.core.types import BaseEntity, Component, Capability
from architecture_model.core.detail_level import compute_detail_level


def prepare_review_prompt(entity: BaseEntity) -> str:
    """Generate a prompt asking LLM to review and fill missing fields."""
    level = compute_detail_level(entity)
    missing = []
    if not entity.intent:
        missing.append("intent")
    if not entity.description:
        missing.append("description")
    if isinstance(entity, Component):
        if not entity.responsibilities:
            missing.append("responsibilities")
        if not entity.goals:
            missing.append("goals")
        if not entity.moes:
            missing.append("moes")

    prompt = f"Review entity {entity.id} ({entity.name}).\n"
    prompt += f"Current detail level: L{level}\n"
    prompt += f"Description: {entity.description or '(none)'}\n"
    if missing:
        prompt += f"Missing fields to fill: {', '.join(missing)}\n"
    prompt += "Provide values for missing fields as JSON."
    return prompt


def apply_review(entity: BaseEntity, review_data: dict) -> BaseEntity:
    """Apply LLM review results back to entity."""
    updated = copy.deepcopy(entity)
    for field_name, value in review_data.items():
        if field_name == "review_notes":
            continue
        if hasattr(updated, field_name) and not getattr(updated, field_name):
            setattr(updated, field_name, value)
    updated.extensions["_llm_review"] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "notes": review_data.get("review_notes", ""),
    }
    return updated
```

**Step 3: Run tests, commit**

```bash
git commit -m "feat(core): add LLM entity review loop (WP-3)"
```

---

### Task 11: WP-15 — View Enrichment Propagation

**Files:**
- Modify: `src/architecture_model/pipeline/derive_views.py` or create `src/architecture_model/core/propagation.py`
- Test: `tests/test_wp15_view_propagation.py` (new)

**Step 1: Write test**

```python
"""WP-15: Propagate sub-model enrichment to root model."""
from architecture_model.core.propagation import propagate_enrichment
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Status,
    FunctionSignature, TestContract,
)


class TestEnrichmentPropagation:
    def test_signatures_propagate_to_root(self):
        root = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(components=[
                Component(id="COMP-1", name="Core", status=Status.ACTIVE),
            ]),
            relationships=[],
        )
        sub = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01",
                           refines_component="COMP-1"),
            entities=Entities(components=[
                Component(id="COMP-1.1", name="Parser", status=Status.ACTIVE,
                          signatures=[FunctionSignature(name="parse", params=["path"])],
                          test_contracts=[TestContract(assertion="returns model",
                                                       contract_type="output",
                                                       test_method="test_parse")]),
            ]),
            relationships=[],
        )
        updated = propagate_enrichment(root, [sub])
        root_comp = updated.entities.components[0]
        assert len(root_comp.signatures) >= 1
        assert len(root_comp.test_contracts) >= 1
```

**Step 2: Implement `propagation.py`**

```python
"""Propagate enrichment data from sub-models to root model."""
import copy
from architecture_model.core.types import ArchitectureModel


def propagate_enrichment(root: ArchitectureModel, sub_models: list[ArchitectureModel]) -> ArchitectureModel:
    """Copy signatures, constants, test_contracts from sub-model components to root."""
    updated = copy.deepcopy(root)
    comp_map = {c.id: c for c in updated.entities.components}

    for sub in sub_models:
        parent_id = sub.meta.refines_component
        if not parent_id or parent_id not in comp_map:
            continue
        parent = comp_map[parent_id]
        for sub_comp in sub.entities.components:
            parent.signatures.extend(sub_comp.signatures)
            parent.test_contracts.extend(sub_comp.test_contracts)
            parent.constants.extend(sub_comp.constants)

    return updated
```

**Step 3: Run tests, commit**

```bash
git commit -m "feat(core): propagate sub-model enrichment to root model (WP-15)"
```

---

## Phase 4: Delivery

### Task 12: WP-7 — Slicer Budget Handling

**Files:**
- Create: `src/architecture_model/core/budget.py`
- Modify: `src/architecture_model/core/slicer.py` (add `max_tokens` parameter)
- Test: `tests/test_wp7_budget_slicer.py` (new)

**Step 1: Write test**

```python
"""WP-7: Budget-aware slicing."""
from architecture_model.core.budget import estimate_tokens, reduce_to_budget
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Status,
    FunctionSignature,
)


class TestTokenEstimation:
    def test_empty_model_small(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(),
            relationships=[],
        )
        tokens = estimate_tokens(model)
        assert tokens < 500

    def test_model_with_signatures_larger(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(components=[
                Component(id="COMP-1", name="Big", status=Status.ACTIVE,
                          signatures=[FunctionSignature(name=f"fn_{i}", params=["a", "b"])
                                      for i in range(100)]),
            ]),
            relationships=[],
        )
        tokens = estimate_tokens(model)
        assert tokens > 1000


class TestBudgetReduction:
    def test_reduce_drops_signatures_first(self):
        model = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(components=[
                Component(id="COMP-1", name="Big", status=Status.ACTIVE,
                          signatures=[FunctionSignature(name=f"fn_{i}", params=["a", "b"])
                                      for i in range(100)]),
            ]),
            relationships=[],
        )
        reduced = reduce_to_budget(model, max_tokens=500)
        assert estimate_tokens(reduced) <= 500
        assert len(reduced.entities.components[0].signatures) < 100
```

**Step 2: Implement `budget.py`**

```python
"""Token estimation and budget-aware model reduction."""
import copy
from architecture_model.core.types import ArchitectureModel


def estimate_tokens(model: ArchitectureModel) -> int:
    """Estimate token count from YAML serialization. ~4 chars per token."""
    yaml_str = model.to_yaml()
    return len(yaml_str) // 4


def reduce_to_budget(model: ArchitectureModel, max_tokens: int) -> ArchitectureModel:
    """Progressively reduce model detail to fit within token budget.

    Reduction order (least valuable first):
    1. Drop body_hint from signatures
    2. Drop test_contracts
    3. Truncate signatures to top-N
    4. Truncate descriptions to 100 chars
    5. Drop constants
    """
    reduced = copy.deepcopy(model)
    if estimate_tokens(reduced) <= max_tokens:
        return reduced

    # Phase 1: Drop body_hints
    for comp in reduced.entities.components:
        for sig in comp.signatures:
            sig.body_hint = ""
    if estimate_tokens(reduced) <= max_tokens:
        return reduced

    # Phase 2: Drop test_contracts
    for comp in reduced.entities.components:
        comp.test_contracts = []
    if estimate_tokens(reduced) <= max_tokens:
        return reduced

    # Phase 3: Truncate signatures to top 10
    for comp in reduced.entities.components:
        comp.signatures = comp.signatures[:10]
    if estimate_tokens(reduced) <= max_tokens:
        return reduced

    # Phase 4: Truncate descriptions
    for comp in reduced.entities.components:
        if len(comp.description) > 100:
            comp.description = comp.description[:100] + "..."
    if estimate_tokens(reduced) <= max_tokens:
        return reduced

    # Phase 5: Drop constants
    for comp in reduced.entities.components:
        comp.constants = []

    return reduced
```

**Step 3: Add `max_tokens` to `slice_by_source_block()` in `slicer.py`**

Add optional parameter `max_tokens: int | None = None` to `slice_by_source_block()`. After structural slicing, if `max_tokens` is set, call `reduce_to_budget()`.

**Step 4: Run tests, commit**

```bash
git commit -m "feat(core): add budget-aware slicing with progressive reduction (WP-7)"
```

---

### Task 13: WP-13 — MCP Tool Update Spec

**Files:**
- Create: `docs/plans/wp13-mcp-tool-spec.md` (spec only — changes are in opencode-arch repo)

**Step 1: Write spec document** describing API changes needed in opencode-arch:
- `architect_slice` accepts `max_tokens`, surfaces `intent`/`goals`/`moes`/`detail_level`
- New `architect_review` tool wrapping `review.py`
- Budget-aware slicing parameter

**Step 2: Commit**

```bash
git commit -m "docs: add MCP tool update spec for opencode-arch (WP-13)"
```

---

### Task 14: WP-12 — PDF as Standard Output

**Files:**
- Modify: CLI entry point (find via `grep -r "def docs" src/architecture_model/cli/`)
- Reuse: `scripts/build_arch_pdf.py` logic
- Test: `tests/test_wp12_pdf_output.py` (new)

**Step 1: Write test**

```python
"""WP-12: PDF as standard CLI output."""
from click.testing import CliRunner


class TestPDFCommand:
    def test_docs_command_has_pdf_option(self):
        from architecture_model.cli import cli  # adjust import
        runner = CliRunner()
        result = runner.invoke(cli, ["docs", "--help"])
        assert result.exit_code == 0
        assert "--pdf" in result.output or "pdf" in result.output.lower()
```

**Step 2: Add `--pdf` flag** to existing `docs` CLI command. When set, invoke the PDF builder after generating markdown docs.

**Step 3: Run tests, commit**

```bash
git commit -m "feat(cli): add --pdf flag to docs command (WP-12)"
```

---

### Task 15: WP-9 — Cross-Repo Consistency

**Files:**
- Create: `src/architecture_model/core/cross_repo.py`
- Test: `tests/test_wp9_cross_repo.py` (new)

**Step 1: Write test**

```python
"""WP-9: Cross-repo consistency checking."""
from architecture_model.core.cross_repo import check_consistency
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Actor, ActorType, Status,
)


class TestCrossRepoConsistency:
    def test_schema_version_mismatch(self):
        m1 = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="a", generated_at="2026-01-01"),
            entities=Entities(), relationships=[],
        )
        m2 = ArchitectureModel(
            meta=ModelMeta(schema_version="2.0", project="b", generated_at="2026-01-01"),
            entities=Entities(), relationships=[],
        )
        issues = check_consistency([m1, m2])
        assert any("schema_version" in str(i).lower() for i in issues)

    def test_matching_actors_consistent(self):
        actor = Actor(id="ACT-1", name="Developer", status=Status.ACTIVE,
                      type=ActorType.HUMAN)
        m1 = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="a", generated_at="2026-01-01"),
            entities=Entities(actors=[actor]), relationships=[],
        )
        m2 = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="b", generated_at="2026-01-01"),
            entities=Entities(actors=[actor]), relationships=[],
        )
        issues = check_consistency([m1, m2])
        assert len(issues) == 0
```

**Step 2: Implement `cross_repo.py`**

Check: schema version alignment, shared entity ID consistency (same ID → same type/name), interface compatibility.

**Step 3: Run tests, commit**

```bash
git commit -m "feat(core): add cross-repo consistency checker (WP-9)"
```

---

### Task 16: WP-10 — Model Changelog / Drift Detection

**Files:**
- Create: `src/architecture_model/core/changelog.py`
- Test: `tests/test_wp10_changelog.py` (new)

**Step 1: Write test**

```python
"""WP-10: Model changelog generation."""
from architecture_model.core.changelog import generate_changelog
from architecture_model.core.types import (
    ArchitectureModel, Entities, ModelMeta, Component, Status,
)


class TestChangelog:
    def test_detects_added_component(self):
        old = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(), relationships=[],
        )
        new = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-02"),
            entities=Entities(components=[
                Component(id="COMP-1", name="New", status=Status.ACTIVE),
            ]),
            relationships=[],
        )
        log = generate_changelog(old, new)
        assert "Added" in log
        assert "COMP-1" in log

    def test_detects_removed_component(self):
        old = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-01"),
            entities=Entities(components=[
                Component(id="COMP-1", name="Old", status=Status.ACTIVE),
            ]),
            relationships=[],
        )
        new = ArchitectureModel(
            meta=ModelMeta(schema_version="2.1", project="test", generated_at="2026-01-02"),
            entities=Entities(), relationships=[],
        )
        log = generate_changelog(old, new)
        assert "Removed" in log
        assert "COMP-1" in log
```

**Step 2: Implement `changelog.py`**

```python
"""Model changelog — human-readable diff between model versions."""
from architecture_model.core.types import ArchitectureModel


def generate_changelog(old: ArchitectureModel, new: ArchitectureModel) -> str:
    """Generate human-readable changelog between two model versions."""
    sections = []

    for entity_type in ["components", "capabilities", "behaviors", "interfaces",
                         "constraints", "requirements", "actors"]:
        old_entities = {e.id: e for e in getattr(old.entities, entity_type, [])}
        new_entities = {e.id: e for e in getattr(new.entities, entity_type, [])}

        added = set(new_entities) - set(old_entities)
        removed = set(old_entities) - set(new_entities)
        common = set(old_entities) & set(new_entities)

        if added:
            sections.append(f"### Added {entity_type}")
            for eid in sorted(added):
                sections.append(f"- {eid}: {new_entities[eid].name}")

        if removed:
            sections.append(f"### Removed {entity_type}")
            for eid in sorted(removed):
                sections.append(f"- {eid}: {old_entities[eid].name}")

        changed = []
        for eid in sorted(common):
            if old_entities[eid].description != new_entities[eid].description:
                changed.append(eid)
            elif old_entities[eid].intent != new_entities[eid].intent:
                changed.append(eid)
        if changed:
            sections.append(f"### Changed {entity_type}")
            for eid in changed:
                sections.append(f"- {eid}: {new_entities[eid].name}")

    if not sections:
        return "No changes detected."

    header = f"# Changelog\n\n**From:** {old.meta.generated_at} **To:** {new.meta.generated_at}\n\n"
    return header + "\n".join(sections)
```

**Step 3: Run tests, commit**

```bash
git commit -m "feat(core): add model changelog and drift detection (WP-10)"
```

---

## Execution Order Summary

| Task | WP | Phase | Depends On | Est. Effort |
|------|----|-------|------------|-------------|
| 1 | WP-6 | 1 | — | 20 min |
| 2 | WP-1 | 1 | WP-6 | 25 min |
| 3 | WP-16 | 1 | WP-6, WP-1 | 15 min |
| 4 | WP-8 | 1 | WP-6 | 30 min |
| 5 | WP-5 | 2 | — | 30 min |
| 6 | WP-2 | 2 | WP-6 | 20 min |
| 7 | WP-4 | 2 | WP-5 | 25 min |
| 8 | WP-14 | 2 | WP-6 | 30 min |
| 9 | WP-11 | 3 | WP-6, WP-2 | 25 min |
| 10 | WP-3 | 3 | WP-6, WP-2 | 25 min |
| 11 | WP-15 | 3 | WP-8 | 20 min |
| 12 | WP-7 | 4 | — | 30 min |
| 13 | WP-13 | 4 | WP-7, WP-2, WP-3 | 15 min |
| 14 | WP-12 | 4 | — | 25 min |
| 15 | WP-9 | 4 | WP-1 | 20 min |
| 16 | WP-10 | 4 | — | 20 min |

**Total estimated: ~6 hours**

## Parallelization Opportunities

- **Phase 1:** Tasks 1→2→3 sequential; Task 4 parallel with Task 3
- **Phase 2:** Tasks 5+6+8 parallel; Task 7 after Task 5
- **Phase 3:** Tasks 9+10 parallel; Task 11 after Task 4
- **Phase 4:** Tasks 12+14+15+16 all parallel; Task 13 after 12

## Verification Gate

After each phase:
```bash
/opt/anaconda3/bin/python -m pytest tests/ -v --ignore=tests/test_config_loader.py 2>&1 | tail -5
```

No new failures beyond the 7 pre-existing ones = phase complete.
