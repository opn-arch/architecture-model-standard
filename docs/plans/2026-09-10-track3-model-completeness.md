# Track 3 Implementation Plan: Model Completeness for Phase B + User-Facing Use Cases

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add missing Phase B entities (SI&L, LLM Provider, Pipeline Dashboard, Comment, Feedback) and 4 user-facing use-case behaviors to the canonical `.architecture-model.yaml`, then reconcile `viewer-curation.yaml` so all 7 phantom-ID diagnostics are eliminated and the 4 SE panels (ConOps / Functional / Logical / Use Cases) can pass Sitting C review.

**Architecture:** The canonical model uses numeric IDs (`COMP-N`, `CAP-N`, `IF-N`, `LAY-N`, `BEH-N`) constrained by schema regex `^[A-Z]+-[A-Z]?-?\d+$|^[a-z][a-z0-9-]+$`. The 7 curation-referenced IDs (e.g. `CAP-COMMENT-COLLABORATION`) don't match this pattern — they were aspirational names. Track 3 introduces the entities with **conforming numeric IDs** and **updates `viewer-curation.yaml`** to reference them. Next-free IDs: `CAP-16`, `COMP-13`, `IF-17`, `LAY-6`, `BEH-26`, `REQ-31`, `SYS-5`, `ACT-4`.

**Tech Stack:** YAML editing (`.architecture-model.yaml`, `.architecture/viewer-curation.yaml`), `architecture_model.core.parser` / `validator` for verification, pytest for regression, `architecture-model docs` + `architecture-model viewer` for panel regen.

**Baseline before Track 3 starts:** 3638 passed / 104 skipped; model at `.architecture-model.yaml` HEAD; branch `feat/phase-5-fanout-provenance-family5` at `5f88282`.

**Sitting B evidence:** `docs/plans/2026-09-10-track2-sitting-b-review.md`
**Audit checklist source:** `.architecture/reviews/track3-audit-checklist.md`

---

## Task 0: Investigate the `SYS-src-(core)` duplicate

**Rationale:** Sitting B diagnostics include `Duplicate entity ID rejected in .architecture-model: SYS-src-(core)`. This wasn't in the Sitting A summary — it's a new symptom that must be diagnosed before adding new systems (Task 5 might collide).

**Files:**
- Read: `.architecture-model.yaml` (entities.systems)
- Grep: source for `SYS-src-` synthesis code

**Step 1: Find the duplicate source**

Run:
```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -c "
import yaml
m = yaml.safe_load(open('.architecture-model.yaml'))
seen = {}
for kind in m['entities']:
    for e in m['entities'][kind] or []:
        eid = e['id']
        if eid in seen:
            print(f'DUP {eid}: {seen[eid]} vs {kind}')
        seen[eid] = kind
print('done, checked', len(seen), 'entities')
"
```

Expected: identify whether the dup is in `.architecture-model.yaml` itself (canonical bug) or is being injected by a projector/loader.

**Step 2: If canonical model has no dup, grep the projector chain**

Run:
```
grep -rn "SYS-src-" src/architecture_model/ tests/ 2>&1 | head -30
```

Look for a synthesizer that emits `SYS-src-(core)` — likely in `docs/se/` or `core/view_curation.py`.

**Step 3: Record findings**

Append findings to `docs/plans/2026-09-10-track2-sitting-b-review.md` under a new `## Task 0 Investigation` section. If it's a legitimate bug, spin it out as its own commit **before** the entity-addition tasks. If it's a downstream artifact of Task 5 onward (system emission), note that and continue.

**Step 4: Commit findings**

```
git add docs/plans/2026-09-10-track2-sitting-b-review.md
git commit -m "docs(track3): investigate SYS-src-(core) duplicate diagnostic"
```

---

## Task 1: Author Phase B design record

**Rationale:** Before touching YAML we need a single authoritative list of every new entity, its ID, name, layer allocation, capability parent, and semantic content. This becomes the reference for Tasks 2-9 and future regressions.

**Files:**
- Create: `docs/plans/2026-09-10-track3-phase-b-entities.md`

**Step 1: Write the entity table**

Write a plan document listing:

**Layers (2 new: LAY-6, LAY-7):**
- `LAY-6` "Observability" — SI&L instrumentation + telemetry
- `LAY-7` "AI Integration" — LLM provider routing + policy

**Components (5 new: COMP-13..COMP-17):**
- `COMP-13` "SI&L Instrumentation" — src/architecture_model/sil/{__init__,decorators,record,rollup}.py — layer `LAY-6`
- `COMP-14` "LLM Provider Layer" — src/architecture_model/llm/provider.py — layer `LAY-7`
- `COMP-15` "Pipeline Dashboard" — src/architecture_model/lifecycle/pipeline_html_data.py + assets/pipeline_dashboard/ — layer `LAY-4` (Interface)
- `COMP-16` "Comment System" — src/architecture_model/comments/{models,store}.py — layer `LAY-3` (Application)
- `COMP-17` "Feedback Journals" — src/architecture_model/feedback/{drift,gates,junit_ingest}.py — layer `LAY-6` (Observability)

**Capabilities (3 new: CAP-16..CAP-18):**
- `CAP-16` "Comment-Driven Collaboration" — realized by `COMP-16` — user captures free-text feedback on any lifecycle artifact
- `CAP-17` "SI&L Instrumentation" — realized by `COMP-13` — every architecturally significant call site emits telemetry
- `CAP-18` "LLM Provider Routing" — realized by `COMP-14` — policy-driven provider selection with cost caps and fallback

**Interfaces (6 new: IF-44..IF-49):**
- `IF-44` "SI&L Store API" — exposed by `COMP-13`, consumed by pipeline stages + MCP tools
- `IF-45` "LLM Provider Protocol" — exposed by `COMP-14`, consumed by orchestration
- `IF-46` "Pipeline Dashboard Data" — exposed by `COMP-15`, consumed by viewer.html
- `IF-47` "Comment Store API" — exposed by `COMP-16`, consumed by CLI + MCP tools
- `IF-48` "Gate Event Journal" — exposed by `COMP-17`, consumed by `architect_gate` MCP tool
- `IF-49` "Drift Snapshot Journal" — exposed by `COMP-17`, consumed by pipeline observe stage

**Behaviors (4 new user-facing UCs: BEH-26..BEH-29):**
- `BEH-26` "Slice-Scoped Context" — actor `ACT-1` (AI Agent) invokes `architect_slice` to load a focused view; realizes `CAP-3.2` (Model Operations)
- `BEH-27` "Learning Loop" — actor `ACT-2` (Developer) runs pipeline; system records lessons; next run uses accumulated lessons
- `BEH-28` "Development Loop" — actor `ACT-2` edits code → runs `architect_pipeline` → reviews viewer → captures comment → files issue via `logs-db`
- `BEH-29` "Comment-Driven Collaboration" — actor `ACT-2` captures a comment on a rendered artifact via `architecture-model comment`; comment persists in `.architecture/comments/`

**Relationships to add (partial list — see Task 8):**
- `contains`: LAY-6 → COMP-13, LAY-6 → COMP-17, LAY-7 → COMP-14, LAY-4 → COMP-15, LAY-3 → COMP-16
- `realizes`: COMP-16 → CAP-16, COMP-13 → CAP-17, COMP-14 → CAP-18
- `exposes`: COMP-13 → IF-44, COMP-14 → IF-45, COMP-15 → IF-46, COMP-16 → IF-47, COMP-17 → IF-48, COMP-17 → IF-49
- `traces-to`: BEH-26..BEH-29 → their respective capabilities
- `allocated-to`: BEH-26 → COMP-1 (Core; slicer.py lives there)
- ...

**Step 2: Commit the design record**

```
git add docs/plans/2026-09-10-track3-phase-b-entities.md
git commit -m "docs(track3): author Phase B entity design record"
```

---

## Task 2: RED — write regression test asserting the new entities exist

**Files:**
- Create: `tests/test_track3_phase_b_entities.py`

**Step 1: Write the failing test**

```python
"""Regression test: canonical model contains Phase B + user-facing UC entities.

Track 3 introduces 2 layers, 5 components, 3 capabilities, 6 interfaces, and
4 user-facing behaviors that cover SI&L, LLM Provider Layer, Pipeline
Dashboard, Comment System, Feedback Journals, plus the four user-facing use
cases (Slice-scoped context, Learning loop, Development loop, Comment-driven
collaboration).

If this test fails, `.architecture-model.yaml` is missing entities the Track 2
Sitting B review flagged as required.
"""
from __future__ import annotations

from pathlib import Path
import yaml

MODEL_PATH = Path(__file__).resolve().parents[1] / ".architecture-model.yaml"


def _load():
    return yaml.safe_load(MODEL_PATH.read_text())


def _ids(model: dict, kind: str) -> set[str]:
    return {e["id"] for e in (model["entities"].get(kind) or [])}


def test_track3_layers_present() -> None:
    ids = _ids(_load(), "layers")
    assert {"LAY-6", "LAY-7"}.issubset(ids), sorted(ids)


def test_track3_components_present() -> None:
    ids = _ids(_load(), "components")
    assert {"COMP-13", "COMP-14", "COMP-15", "COMP-16", "COMP-17"}.issubset(ids), sorted(ids)


def test_track3_capabilities_present() -> None:
    ids = _ids(_load(), "capabilities")
    assert {"CAP-16", "CAP-17", "CAP-18"}.issubset(ids), sorted(ids)


def test_track3_interfaces_present() -> None:
    ids = _ids(_load(), "interfaces")
    assert {f"IF-{n}" for n in range(44, 50)}.issubset(ids), sorted(ids)


def test_track3_user_facing_behaviors_present() -> None:
    ids = _ids(_load(), "behaviors")
    assert {"BEH-26", "BEH-27", "BEH-28", "BEH-29"}.issubset(ids), sorted(ids)


def test_track3_component_layer_containment() -> None:
    """Each new component must be contained by its declared layer."""
    m = _load()
    rels = m["relationships"]
    expected = {
        ("LAY-6", "COMP-13"),  # SI&L in Observability
        ("LAY-6", "COMP-17"),  # Feedback in Observability
        ("LAY-7", "COMP-14"),  # LLM Provider in AI Integration
        ("LAY-4", "COMP-15"),  # Dashboard in Interface layer
        ("LAY-3", "COMP-16"),  # Comment System in Application
    }
    actual = {(r["from"], r["to"]) for r in rels if r.get("type") == "contains"}
    missing = expected - actual
    assert not missing, f"missing contains edges: {missing}"


def test_track3_component_realizes_capability() -> None:
    m = _load()
    rels = m["relationships"]
    expected = {
        ("COMP-16", "CAP-16"),
        ("COMP-13", "CAP-17"),
        ("COMP-14", "CAP-18"),
    }
    actual = {(r["from"], r["to"]) for r in rels if r.get("type") == "realizes"}
    missing = expected - actual
    assert not missing, f"missing realizes edges: {missing}"


def test_track3_model_validates() -> None:
    """After Track 3 edits the model must still be schema-valid."""
    from architecture_model.core.parser import load_model
    from architecture_model.core.validator import validate_model

    model = load_model(MODEL_PATH)
    result = validate_model(model)
    assert result.is_valid, f"score={result.score} issues={[str(i) for i in result.issues[:10]]}"
```

**Step 2: Run test to verify RED**

Run:
```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/test_track3_phase_b_entities.py -v
```

Expected: 8 tests FAIL (LAY-6 missing, COMP-13 missing, etc.).

**Step 3: Commit the red tests**

```
git add tests/test_track3_phase_b_entities.py
git commit -m "test(track3): RED tests for Phase B entities in canonical model"
```

---

## Task 3: Add LAY-6 and LAY-7 layers

**Files:**
- Modify: `.architecture-model.yaml` (entities.layers section)

**Step 1: Locate the layers block**

Run:
```
grep -n "^  layers:" .architecture-model.yaml
```

Expected: one match. Read the file 20 lines from that line to see the existing layer entries and their YAML shape (fields: `id`, `name`, `status`, plus optional `description`, `owner`).

**Step 2: Append the new layers**

Using `edit`, insert after `LAY-5` (the last existing layer):

```yaml
  - id: LAY-6
    name: Observability
    status: ACTIVE
    description: |
      Cross-cutting instrumentation and evidence journals: SI&L telemetry
      records for every architecturally significant call site, plus append-only
      journals (gates.jsonl, drift.jsonl, test_results.jsonl) that back
      lifecycle overlays and viewer badges.
  - id: LAY-7
    name: AI Integration
    status: ACTIVE
    description: |
      LLM provider abstraction and routing policy. Sits above orchestration
      so any component can request a completion by task-class, and the layer
      resolves the concrete provider (MCP subprocess, direct HTTPS, or relay)
      with per-call cost caps.
```

Preserve existing indentation exactly (two-space nested under `layers:`).

**Step 3: Run the layer test**

Run:
```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/test_track3_phase_b_entities.py::test_track3_layers_present -v
```

Expected: PASS.

**Step 4: Validate model still parses**

Run:
```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -c "
from pathlib import Path
from architecture_model.core.parser import load_model
m = load_model(Path('.architecture-model.yaml'))
print('layers:', len(m.entities.layers))
"
```

Expected: `layers: 7`.

**Step 5: Commit**

```
git add .architecture-model.yaml
git commit -m "feat(model): add LAY-6 Observability and LAY-7 AI Integration layers"
```

---

## Task 4: Add COMP-13..COMP-17 components

**Files:**
- Modify: `.architecture-model.yaml` (entities.components section)

**Step 1: Find the end of the components block**

Run:
```
grep -n "^  [a-z_]*:$" .architecture-model.yaml
```

This lists all top-level entity kinds. The components section ends right before `actors:` (or whichever kind is next). Insert new components before that boundary.

**Step 2: Append COMP-13..COMP-17**

For each of the five components add a block. Example (COMP-13):

```yaml
  - id: COMP-13
    name: SI&L Instrumentation
    status: ACTIVE
    files:
      - src/architecture_model/sil/__init__.py
      - src/architecture_model/sil/decorators.py
      - src/architecture_model/sil/record.py
      - src/architecture_model/sil/rollup.py
    description: |
      Structural Interface Layer: SQLite-backed ring buffer at
      .architecture/sil.sqlite retaining the 50 most recent events per
      component_id, plus YAML rollup snapshots under .architecture/sil/. The
      @sil_instrument decorator is applied to 10 pipeline stages, 5 lifecycle
      renderers, 3 validators, and all 19 MCP *_tool handlers.
```

Repeat for COMP-14 (LLM Provider Layer — `src/architecture_model/llm/provider.py`), COMP-15 (Pipeline Dashboard — `src/architecture_model/lifecycle/pipeline_html_data.py` + `assets/pipeline_dashboard/`), COMP-16 (Comment System — `src/architecture_model/comments/models.py`, `src/architecture_model/comments/store.py`), COMP-17 (Feedback Journals — `src/architecture_model/feedback/drift.py`, `src/architecture_model/feedback/gates.py`, `src/architecture_model/feedback/junit_ingest.py`).

Use file-path lists that match the actual source tree. Verify with:
```
ls src/architecture_model/{sil,llm,comments,feedback}/ src/architecture_model/lifecycle/pipeline_html_data.py assets/pipeline_dashboard/ 2>&1
```

**Step 3: Run the component test**

Run:
```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/test_track3_phase_b_entities.py::test_track3_components_present -v
```

Expected: PASS.

**Step 4: Validate**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -c "
from architecture_model.core.parser import load_model
from architecture_model.core.validator import validate_model
from pathlib import Path
m = load_model(Path('.architecture-model.yaml'))
r = validate_model(m)
print(f'score={r.score} valid={r.is_valid}')
for i in r.issues[:5]: print(' -', i)
"
```

Expected: `valid=True` (or same score as pre-Task 4; no new issues about the added components).

**Step 5: Commit**

```
git add .architecture-model.yaml
git commit -m "feat(model): add COMP-13..COMP-17 for SI&L, LLM, Dashboard, Comment, Feedback"
```

---

## Task 5: Add CAP-16..CAP-18 capabilities

**Files:**
- Modify: `.architecture-model.yaml` (entities.capabilities section)

**Step 1: Append capabilities**

Add after the last existing capability:

```yaml
  - id: CAP-16
    name: Comment-Driven Collaboration
    status: ACTIVE
    description: |
      Users capture free-text comments on any rendered lifecycle artifact via
      `architecture-model comment`. Comments persist in .architecture/comments/
      as YAML records referencing artifact digest + timestamp; downstream
      workflows can promote comments to logs-db issues.
  - id: CAP-17
    name: SI&L Instrumentation
    status: ACTIVE
    description: |
      Every architecturally significant call site emits a telemetry event to
      the SI&L SQLite store, giving component-scoped invocation counts,
      failure rates, and latency for live badge overlays and the pipeline
      dashboard.
  - id: CAP-18
    name: LLM Provider Routing
    status: ACTIVE
    description: |
      Task-class-keyed routing policy (.architecture/llm/policy.yaml) picks a
      provider + model per call, enforces per-call cost caps, and falls back
      on error. Model outputs record their generator via meta.provider so
      reproducibility can be audited.
```

**Step 2: Run the capability test**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/test_track3_phase_b_entities.py::test_track3_capabilities_present -v
```

Expected: PASS.

**Step 3: Commit**

```
git add .architecture-model.yaml
git commit -m "feat(model): add CAP-16 (Comments), CAP-17 (SI&L), CAP-18 (LLM Routing)"
```

---

## Task 6: Add IF-44..IF-49 interfaces

**Files:**
- Modify: `.architecture-model.yaml` (entities.interfaces section)

**Step 1: Append the 6 interfaces**

For each, use fields matching existing interfaces (check with `grep -A5 "IF-1:" .architecture-model.yaml`). Typical shape:

```yaml
  - id: IF-44
    name: SI&L Store API
    kind: LIBRARY
    status: ACTIVE
    description: |
      Public API for reading and writing structural-interface-layer events:
      SILStore.record(event), SILStore.query(component_id), rollup helpers.
```

Then IF-45 (LLM Provider Protocol — `kind: LIBRARY`), IF-46 (Pipeline Dashboard Data — `kind: LIBRARY`), IF-47 (Comment Store API — `kind: LIBRARY`), IF-48 (Gate Event Journal — `kind: DATA`), IF-49 (Drift Snapshot Journal — `kind: DATA`).

If the schema doesn't accept a `kind` value, `grep -B1 -A5 "kind:" .architecture-model.yaml | head -30` reveals accepted values.

**Step 2: Run interface test**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/test_track3_phase_b_entities.py::test_track3_interfaces_present -v
```

Expected: PASS.

**Step 3: Commit**

```
git add .architecture-model.yaml
git commit -m "feat(model): add IF-44..IF-49 for Track 3 component interfaces"
```

---

## Task 7: Add BEH-26..BEH-29 user-facing use cases

**Files:**
- Modify: `.architecture-model.yaml` (entities.behaviors section)

**Step 1: Append the 4 behaviors**

Match the shape of existing rich behaviors like `BEH-P1` (grep for `id: BEH-P1` and read 20 lines). Fields to populate for each new use case: `id`, `name`, `status`, `goal`, `trigger`, `preconditions`, `postconditions`, `success_outcome`, plus `source_file` if applicable.

```yaml
  - id: BEH-26
    name: Slice-Scoped Context
    status: ACTIVE
    goal: |
      Load a focused architectural context (single F-block, layer, or entity)
      within an AI agent's token budget.
    trigger: AI agent invokes `architect_slice` with a focus target
    preconditions: A published architecture model exists at .architecture-model.yaml
    postconditions: Agent receives compressed context under budget
    success_outcome: Agent produces informed edits without loading full model
  - id: BEH-27
    name: Learning Loop
    status: ACTIVE
    goal: |
      Pipeline accumulates lessons from prior runs and applies them to
      subsequent extractions, monotonically improving quality.
    trigger: Developer runs `architecture-model pipeline .`
    preconditions: .architecture/learning/history.json is readable
    postconditions: New lessons appended; drift flags updated
    success_outcome: Successive runs show reduced novel-pattern rate
  - id: BEH-28
    name: Development Loop
    status: ACTIVE
    goal: |
      Developer edits code, regenerates architecture artifacts, reviews the
      viewer, captures a comment, and files an issue \u2014 all without leaving
      the tool suite.
    trigger: Developer modifies source files
    preconditions: Architecture model exists; MCP tools available
    postconditions: Comment persisted; issue optionally filed via logs-db
    success_outcome: Feedback loop closes within one review session
  - id: BEH-29
    name: Comment-Driven Collaboration
    status: ACTIVE
    goal: |
      Users leave free-text feedback on any rendered artifact and downstream
      workflows (logs-db issue triage) consume it.
    trigger: User invokes `architecture-model comment <artifact>`
    preconditions: The artifact exists under .architecture/lifecycle/artifacts/
    postconditions: Comment record persisted with artifact digest reference
    success_outcome: Reviewers can trace decisions back to artifact versions
```

Populate whichever additional fields the existing rich behaviors carry (e.g. `moe`, `failure_modes`) using the same shapes.

**Step 2: Run behavior test**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/test_track3_phase_b_entities.py::test_track3_user_facing_behaviors_present -v
```

Expected: PASS.

**Step 3: Commit**

```
git add .architecture-model.yaml
git commit -m "feat(model): add BEH-26..BEH-29 user-facing use cases"
```

---

## Task 8: Add relationships wiring Track 3 entities into the graph

**Files:**
- Modify: `.architecture-model.yaml` (relationships list)

**Step 1: Append relationships block**

The relationships list is at the top level of the YAML document, after `entities:`. Find its end and append:

```yaml
# Track 3 wiring: containment
- {from: LAY-6, to: COMP-13, type: contains}
- {from: LAY-6, to: COMP-17, type: contains}
- {from: LAY-7, to: COMP-14, type: contains}
- {from: LAY-4, to: COMP-15, type: contains}
- {from: LAY-3, to: COMP-16, type: contains}
# Track 3 wiring: realization
- {from: COMP-16, to: CAP-16, type: realizes}
- {from: COMP-13, to: CAP-17, type: realizes}
- {from: COMP-14, to: CAP-18, type: realizes}
# Track 3 wiring: interface exposure
- {from: COMP-13, to: IF-44, type: exposes}
- {from: COMP-14, to: IF-45, type: exposes}
- {from: COMP-15, to: IF-46, type: exposes}
- {from: COMP-16, to: IF-47, type: exposes}
- {from: COMP-17, to: IF-48, type: exposes}
- {from: COMP-17, to: IF-49, type: exposes}
# Track 3 wiring: capability trace
- {from: BEH-26, to: CAP-3, type: traces-to}   # Model Ops capability
- {from: BEH-27, to: CAP-4, type: traces-to}   # Adjust to actual "Scripts"/"Learning" cap id
- {from: BEH-28, to: CAP-16, type: traces-to}
- {from: BEH-29, to: CAP-16, type: traces-to}
# Track 3 wiring: allocation to code
- {from: BEH-26, to: COMP-1, type: allocated-to}
- {from: BEH-27, to: COMP-2, type: allocated-to}
- {from: BEH-28, to: COMP-8, type: allocated-to}   # CLI drives the loop
- {from: BEH-29, to: COMP-16, type: allocated-to}
```

Verify the `CAP-3` / `CAP-4` targets in `traces-to` are the intended capabilities — read the capability list and pick the closest existing parent. Adjust to actual IDs.

**Step 2: Run wiring tests**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/test_track3_phase_b_entities.py::test_track3_component_layer_containment tests/test_track3_phase_b_entities.py::test_track3_component_realizes_capability -v
```

Expected: PASS.

**Step 3: Validate model**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -c "
from pathlib import Path
from architecture_model.core.parser import load_model
from architecture_model.core.validator import validate_model
m = load_model(Path('.architecture-model.yaml'))
r = validate_model(m)
print(f'score={r.score} valid={r.is_valid} issues={len(r.issues)}')
for i in r.issues[:10]: print(' -', i)
"
```

Expected: `valid=True`, score >= previous baseline (86).

**Step 4: Commit**

```
git add .architecture-model.yaml
git commit -m "feat(model): wire Track 3 entities with contains/realizes/exposes/traces-to/allocated-to"
```

---

## Task 9: Update `viewer-curation.yaml` to reference canonical IDs

**Files:**
- Modify: `.architecture/viewer-curation.yaml`

**Step 1: Replace phantom IDs with canonical IDs**

Mapping:
- `CAP-COMMENT-COLLABORATION` → `CAP-16`
- `CAP-SIL-INSTRUMENTATION` → `CAP-17`
- `CAP-LLM-ROUTING` → `CAP-18`
- `COMP-COMMENT-SYS` → `COMP-16`
- `COMP-SIL` → `COMP-13`
- `COMP-LLM` → `COMP-14`
- `COMP-DASHBOARD` → `COMP-15`

Use `Edit` with `replaceAll: true` for each mapping.

**Step 2: Verify no phantom IDs remain**

```
grep -E "CAP-COMMENT-COLLABORATION|CAP-SIL-INSTRUMENTATION|CAP-LLM-ROUTING|COMP-COMMENT-SYS|COMP-SIL|COMP-LLM|COMP-DASHBOARD" .architecture/viewer-curation.yaml
```

Expected: no output.

**Step 3: Regenerate viewer + SE docs**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m architecture_model.cli.main docs .
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m architecture_model.cli.main viewer .
```

**Step 4: Verify diagnostics no longer report phantom IDs**

```
grep "Entity not found" .architecture-models/docs/se/conops.md
```

Expected: 0 matches for the 7 phantom IDs. The `Duplicate entity ID rejected` diagnostic may remain (Task 0 covers it).

**Step 5: Commit curation update**

```
git add .architecture/viewer-curation.yaml
git commit -m "fix(curation): repoint 7 phantom IDs to canonical Track 3 IDs"
```

Note: this commit intentionally includes only `viewer-curation.yaml`. The regenerated `.architecture-models/docs/se/*.md` and `.architecture/diagrams/viewer.html` are outputs — do not commit them (per guardrails).

---

## Task 10: Full test suite + Sitting C review

**Files:**
- Create: `docs/plans/2026-09-10-track3-sitting-c-review.md`

**Step 1: Full test suite**

```
PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py
```

Expected: **3646 passed** (3638 baseline + 8 new Track 3 tests) / 104 skipped, no regressions.

If any pre-existing tests fail because of the new entities (e.g. `test_capability_hierarchy.py` counts capabilities), inspect the failures. If they need to know about the new entities, update them in the same task with `git add tests/... && git commit --amend --no-edit` **only if** the earlier commit was mine and unpushed. Otherwise create a follow-up `test(track3): update <test> for new entities` commit.

**Step 2: Regenerate viewer and SE docs (if not done in Task 9)**

Already done — skip.

**Step 3: Re-review the 4 SE panels**

Read each panel:
- `.architecture-models/docs/se/conops.md`
- `.architecture-models/docs/se/functional-analysis.md`
- `.architecture-models/docs/se/logical-architecture.md`
- `.architecture-models/docs/se/use-cases.md`

Grade each panel PASS/WARN/FAIL against these criteria:

| Panel | PASS criterion |
|-------|----------------|
| ConOps | Featured scenarios include BEH-26..BEH-29; phantom-ID diagnostics gone; no raw Django-auth GETs in top 15 |
| Functional | F-blocks `view-comment-pipeline` and `sil-llm-dashboard` show ≥1 member each; capability inventory non-empty |
| Logical | LAY-6, LAY-7 tiers render with their components; layer→component containment tables populated |
| Use Cases | Actor-Goal Matrix links ACT-1/ACT-2 to BEH-26..BEH-29; those UCs appear in the featured catalog with non-empty goal/trigger |

**Step 4: Write Sitting C review**

Author `docs/plans/2026-09-10-track3-sitting-c-review.md` mirroring the structure of `2026-09-10-track2-sitting-b-review.md`. If any panel is still FAIL/WARN, list remaining defects and route them to Track 4 (slice anchoring) or Track 5 (projector filter) as appropriate.

**Step 5: Commit review**

```
git add docs/plans/2026-09-10-track3-sitting-c-review.md
git commit -m "docs(track3): sitting C review after Phase B entity additions"
```

---

## Task 11: Push and prepare handoff to Track 4

**Step 1: Push branch**

```
git push origin feat/phase-5-fanout-provenance-family5
```

**Step 2: Update session summary**

Note in your next turn that Track 3 is complete and describe which panels reached PASS. Route remaining WARN/FAIL items to Track 4/5.

---

## Notes for the executor

- Never `git add -A`. Never touch `.architecture-model.yaml` outside Tasks 3-8, and never touch `.architecture-models/`, `.architecture/diagrams/`, `.architecture/inventory.json`, `.architecture/sil.sqlite*` — those are pipeline outputs.
- Use `Edit` with a large enough context window in `oldString` to unambiguously match. When adding YAML blocks, prefer inserting after a known unique anchor line.
- If YAML parse fails after an edit, restore from HEAD and try smaller edits: `git checkout HEAD -- .architecture-model.yaml`.
- Every YAML edit should be followed by `PYTHONPATH="$PWD/src" python -c "import yaml; yaml.safe_load(open('.architecture-model.yaml'))"` as a smoke test before running pytest.
- If any of the 29 known model-dependent tests (`test_capability_hierarchy.py`, `test_entity_explorer.py`, `test_layer_entities.py`, `test_pipeline_behaviors.py`, `test_se_diagrams.py`) fail after Task 4 or 5, inspect whether they hardcode entity counts. Update the count expectations in the same commit and note it in the commit message.
- Do not attempt to re-fix the `SYS-src-(core)` duplicate as part of Tasks 3-9 — Task 0 owns that diagnosis. If Task 0 concludes the duplicate is caused by a synthesize/emit bug outside canonical, spin it off to its own plan.
