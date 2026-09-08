# Phase 2: Schema + Semantic Content — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the AMS schema to carry entity-level semantic content (intent, failure modes, trade-offs, requirements, verification, SLOs, maturity, …), add slice/materializer support for supplementary data (manifest, gates, drift, test results, SI&L, learning) and temporal windows, seed the append-only feedback journals, and introduce overlay slots in ViewSpec — all additive, backward-compatible with `schema_version: 2.0` models.

**Architecture:** Bump `schema_version` to `2.1` (additive). Every entity kind grows a fixed set of optional semantic fields (see §5 of the design doc). `ModelSlice` gains `supplementary_refs`, `revision_range`, and `time_window`. `MaterializedSlice` gains `manifest_fragment` and typed `supplementary_fragments`. Feedback data (gates outcomes, drift snapshots, ingested test results) is captured to three append-only JSONL journals. Every ViewSpec gains an optional `overlays: list[str]` slot; projectors read declared overlays and apply them where recognized. A migration CLI upgrades `.architecture-model.yaml` files in-place with a dry-run mode.

**Tech Stack:** Python 3.11+, pytest, PyYAML, jsonschema, existing lifecycle primitives (`ModelSlice`, `MaterializedSlice`, `ViewSpec`, materializer, projector registry from Phase 1), existing `architecture_model.ai.apply_model_patch`.

**Repos affected:**
- `architecture-model-standard` (ams) — schema changes, migration CLI, materializer extensions, journal writers, overlay contract
- `opencode-arch` (oca) — hook wiring to append to journals, updated `architect_docs` behavior to honor overlays via the Phase-1 registry

**Depends on:**
- Phase 1 landed and merged. Requires Phase 1's projector registry naming (`familyN.<name>[.llm]`), the invalidation module, `rebuild_artifacts` sugar in `architect_docs`, per-subsystem loop, and freshness metadata.

**Related skills:**
- @superpowers:test-driven-development for every task
- @superpowers:verification-before-completion before each commit
- @superpowers:subagent-driven-development for execution mode
- @superpowers:using-git-worktrees to isolate the branch before starting

**Baselines to preserve (post-Phase-1):**
- ams — full suite green + all Phase-1-added tests. Command: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/test_config_loader.py`
- oca — full suite green + all Phase-1-added tests. Command: `PYTHONPATH="$PWD/src:$AMS/src" /opt/anaconda3/bin/python -m pytest tests/ -q --ignore=tests/e2e`

**Branching:**
- ams: `feat/model-view-mapping-phase-2` off `main` (after Phase 1 merge)
- oca: `feat/model-view-mapping-phase-2` off `main` (after Phase 1 merge)

**Guardrails (rigid):**
- Never `git add -A`; stage each file explicitly.
- Never touch `.architecture*` telemetry directories.
- Never `pip install -e`; use PYTHONPATH pattern above.
- One commit per task; Conventional Commit format.
- Verify test baseline before AND after each commit.
- **Backward-compat invariant:** every existing `schema_version: 2.0` fixture MUST continue to parse and validate unchanged after schema bump. Add a regression test that loads all pre-Phase-2 test fixtures.

---

## Task Sequence Overview

| # | Task | Repo | Behavior change? |
|---|---|:-:|:-:|
| 1 | Nested type definitions: `FailureMode`, `TradeOff`, `SLO`, `RequirementRef`, `VerificationRef` | ams | Additive |
| 2 | Semantic fields on `Component` (14 fields, all optional) | ams | Additive |
| 3 | Semantic fields on `Capability`, `Behavior`, `Interface`, `Actor`, `Constraint`, `Layer` | ams | Additive |
| 4 | `schema_version` bump to `2.1` + JSON Schema update | ams | Additive |
| 5 | Backward-compat regression: all 2.0 fixtures still parse+validate | ams | Test-only |
| 6 | Migration CLI: `architecture-model migrate --to 2.1` with `--dry-run` | ams | Additive |
| 7 | Semantic-field rendering in `component_spec` + `functional_analysis` projectors | ams | Additive (renders when present) |
| 8 | `ModelSlice.supplementary_refs` field + `SupplementaryRef` type | ams | Additive |
| 9 | `MaterializedSlice.manifest_fragment` + materializer wiring for manifest scope | ams | Additive |
| 10 | Materializer wiring for `sil`, `gates`, `drift`, `test_results`, `learning` supplementary kinds | ams | Additive |
| 11 | Temporal slicing: `ModelSlice.revision_range` + `time_window` fields | ams | Additive |
| 12 | Materializer wiring for temporal fields (resolves generations, filters journals) | ams | Additive |
| 13 | Overlay slots: `ViewSpec.curation.overlays: list[str]` | ams | Additive |
| 14 | Overlay-aware projector base helper (`apply_overlays`) | ams | Additive |
| 15 | Gates journal writer: `architecture_model.feedback.gates.append` | ams | Additive |
| 16 | Drift journal writer: `architecture_model.feedback.drift.append` | ams | Additive |
| 17 | Test-results journal writer + JUnit/pytest ingest helper | ams | Additive |
| 18 | Wire gates journal from `architect_gate` MCP tool | oca | Additive |
| 19 | Wire drift journal from post-extract hook | oca | Additive |
| 20 | Wire test-results ingest CLI: `opencode-arch feedback ingest-junit <path>` | oca | Additive |
| 21 | Semantic-field pipeline seeding: docstring → `intent` in `specify` stage | ams | Additive |
| 22 | Invalidation rules for semantic-field diffs (surgical: only per-entity views) | ams | Additive |
| 23 | Overlay determinism guard: overlays applied in declared order, byte-identical | ams | Test-only |
| 24 | CONTEXT.md refresh — ams (schema 2.1, semantic fields, journals) | ams | Docs |
| 25 | CONTEXT.md refresh — oca (feedback wiring, ingest CLI) | oca | Docs |
| 26 | Full-suite verification pass — both repos | both | Verification |

---

## Task 1 — Nested type definitions

**Rationale:** The semantic-field additions in Tasks 2 and 3 depend on `FailureMode`, `TradeOff`, and `SLO` types. Define them first, standalone, with round-trip YAML tests.

**Files:**
- Create: `src/architecture_model/core/semantic_types.py`
- Test: `tests/core/test_semantic_types.py`

**Step 1: Write the failing tests**

```python
"""Semantic type round-trip and validation tests."""

from __future__ import annotations

import pytest

from architecture_model.core.semantic_types import (
    FailureMode, TradeOff, SLO, RequirementRef, VerificationRef,
    Likelihood, Severity, TradeOffStatus,
)


def test_failure_mode_round_trip():
    fm = FailureMode(
        id="FM-1",
        cause="Network partition",
        effect="Split brain",
        likelihood=Likelihood.UNLIKELY,
        severity=Severity.MAJOR,
        detection="Health check",
        mitigation="Quorum reads",
        mitigated_by=["COMP-3"],
    )
    d = fm.to_dict()
    assert FailureMode.from_dict(d) == fm


def test_failure_mode_rejects_unknown_likelihood():
    with pytest.raises(ValueError):
        FailureMode.from_dict({
            "id": "FM-1", "cause": "x", "effect": "y",
            "likelihood": "impossible", "severity": "minor",
            "detection": "z", "mitigation": "w",
        })


def test_trade_off_round_trip():
    to = TradeOff(
        id="TO-1",
        decision="Use SQLite",
        alternatives=["PostgreSQL", "DuckDB"],
        rationale="Zero-config for MVP",
        consequences=["Single-writer bottleneck"],
        revisit_when="10k concurrent writers",
        status=TradeOffStatus.ACTIVE,
    )
    assert TradeOff.from_dict(to.to_dict()) == to


def test_slo_round_trip_without_current():
    slo = SLO(metric="p99 latency", target="200ms", window="30d")
    d = slo.to_dict()
    assert "current" not in d  # optional field, omitted when None
    assert SLO.from_dict(d) == slo


def test_slo_round_trip_with_current():
    slo = SLO(metric="availability", target="99.9%", window="30d", current="99.94%")
    assert SLO.from_dict(slo.to_dict()) == slo


def test_requirement_ref_minimal():
    r = RequirementRef(id="REQ-42")
    assert RequirementRef.from_dict(r.to_dict()) == r


def test_verification_ref_with_method():
    v = VerificationRef(id="VER-7", method="pytest", target="test_foo")
    assert VerificationRef.from_dict(v.to_dict()) == v
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="$PWD/src" /opt/anaconda3/bin/python -m pytest tests/core/test_semantic_types.py -v`
Expected: `ModuleNotFoundError: architecture_model.core.semantic_types`

**Step 3: Write implementation**

```python
"""Nested semantic types used across entities.

All types are frozen dataclasses with explicit ``to_dict`` / ``from_dict``
so YAML round-trip is deterministic. Optional fields are omitted from
serialization when ``None`` (never emitted as ``null``) so byte-identical
guards pass across writes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Likelihood(str, Enum):
    RARE = "rare"
    UNLIKELY = "unlikely"
    POSSIBLE = "possible"
    LIKELY = "likely"
    CERTAIN = "certain"


class Severity(str, Enum):
    NEGLIGIBLE = "negligible"
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CATASTROPHIC = "catastrophic"


class TradeOffStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVISITED = "revisited"


@dataclass(frozen=True)
class FailureMode:
    id: str
    cause: str
    effect: str
    likelihood: Likelihood
    severity: Severity
    detection: str
    mitigation: str
    mitigated_by: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "cause": self.cause,
            "effect": self.effect,
            "likelihood": self.likelihood.value,
            "severity": self.severity.value,
            "detection": self.detection,
            "mitigation": self.mitigation,
            **({"mitigated_by": list(self.mitigated_by)} if self.mitigated_by else {}),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FailureMode":
        return cls(
            id=d["id"],
            cause=d["cause"],
            effect=d["effect"],
            likelihood=Likelihood(d["likelihood"]),
            severity=Severity(d["severity"]),
            detection=d["detection"],
            mitigation=d["mitigation"],
            mitigated_by=tuple(d.get("mitigated_by", [])),
        )


@dataclass(frozen=True)
class TradeOff:
    id: str
    decision: str
    alternatives: tuple[str, ...]
    rationale: str
    consequences: tuple[str, ...]
    revisit_when: str
    status: TradeOffStatus = TradeOffStatus.ACTIVE

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "decision": self.decision,
            "alternatives": list(self.alternatives),
            "rationale": self.rationale,
            "consequences": list(self.consequences),
            "revisit_when": self.revisit_when,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TradeOff":
        return cls(
            id=d["id"],
            decision=d["decision"],
            alternatives=tuple(d["alternatives"]),
            rationale=d["rationale"],
            consequences=tuple(d["consequences"]),
            revisit_when=d["revisit_when"],
            status=TradeOffStatus(d.get("status", "active")),
        )


@dataclass(frozen=True)
class SLO:
    metric: str
    target: str
    window: str
    current: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"metric": self.metric, "target": self.target, "window": self.window}
        if self.current is not None:
            d["current"] = self.current
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SLO":
        return cls(metric=d["metric"], target=d["target"], window=d["window"], current=d.get("current"))


@dataclass(frozen=True)
class RequirementRef:
    id: str
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id}
        if self.note is not None:
            d["note"] = self.note
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RequirementRef":
        return cls(id=d["id"], note=d.get("note"))


@dataclass(frozen=True)
class VerificationRef:
    id: str
    method: str | None = None
    target: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id}
        if self.method is not None:
            d["method"] = self.method
        if self.target is not None:
            d["target"] = self.target
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "VerificationRef":
        return cls(id=d["id"], method=d.get("method"), target=d.get("target"))
```

**Step 4: Run test to verify it passes**

Expected: 7 tests pass.

**Step 5: Commit**

```bash
git add tests/core/test_semantic_types.py src/architecture_model/core/semantic_types.py
git commit -m "feat(schema): add nested semantic types (FailureMode, TradeOff, SLO, refs)"
```

---

## Task 2 — Semantic fields on `Component`

**Rationale:** Component is the most-touched entity type and exercises every semantic field except a couple actor/constraint-only ones. Land Component first, then generalize to the other kinds in Task 3.

**Files:**
- Modify: `src/architecture_model/core/types.py` (locate `Component` dataclass — currently defines id/name/kind/status/files/…; add semantic fields with defaults)
- Modify: `src/architecture_model/core/parser.py` (component parser branch — read new fields)
- Test: `tests/core/test_component_semantic_fields.py`

**Step 1: Write the failing tests**

```python
"""Component gains 14 optional semantic fields (see design §5)."""

from __future__ import annotations

from architecture_model.core.types import Component, Maturity
from architecture_model.core.semantic_types import (
    FailureMode, TradeOff, SLO, RequirementRef, VerificationRef,
    Likelihood, Severity, TradeOffStatus,
)


def test_component_defaults_are_empty():
    c = Component(id="COMP-1", name="X", kind="module", status="ACTIVE")
    assert c.intent is None
    assert c.goals == ()
    assert c.stakeholders == ()
    assert c.success_criteria == ()
    assert c.failure_modes == ()
    assert c.trade_offs == ()
    assert c.assumptions == ()
    assert c.open_questions == ()
    assert c.requirements == ()
    assert c.verification == ()
    assert c.slos == ()
    assert c.owner is None
    assert c.maturity is None
    assert c.dependencies_rationale == {}


def test_component_semantic_round_trip():
    c = Component(
        id="COMP-1", name="Parser", kind="module", status="ACTIVE",
        intent="Parse YAML into typed model.",
        goals=("Accept schema_version 2.0 and 2.1",),
        assumptions=("YAML input is UTF-8",),
        open_questions=("Do we support anchors?",),
        failure_modes=(FailureMode(
            id="FM-1", cause="Malformed YAML", effect="ParseError raised",
            likelihood=Likelihood.POSSIBLE, severity=Severity.MINOR,
            detection="Schema validation", mitigation="Wrap with try/except",
        ),),
        trade_offs=(TradeOff(
            id="TO-1", decision="PyYAML over ruamel",
            alternatives=("ruamel.yaml",), rationale="Fewer deps",
            consequences=("No round-trip preservation",),
            revisit_when="Round-trip needed", status=TradeOffStatus.ACTIVE,
        ),),
        slos=(SLO(metric="parse latency", target="50ms", window="p99"),),
        requirements=(RequirementRef(id="REQ-1"),),
        verification=(VerificationRef(id="VER-1", method="pytest"),),
        owner="core-team",
        maturity=Maturity.STABLE,
        dependencies_rationale={"COMP-2": "Uses type system for validation"},
    )
    d = c.to_dict()
    c2 = Component.from_dict(d)
    assert c2 == c


def test_component_omits_none_defaults_from_serialization():
    c = Component(id="COMP-1", name="X", kind="module", status="ACTIVE")
    d = c.to_dict()
    assert "intent" not in d
    assert "failure_modes" not in d
    assert "owner" not in d
    assert "maturity" not in d
    assert "dependencies_rationale" not in d
```

**Step 2: Run to verify failure**

Expected: `AttributeError: Component has no attribute 'intent'` (or similar).

**Step 3: Implementation sketch (add to `types.py`)**

- Add `Maturity` enum: `PROPOSAL`, `DRAFT`, `ACTIVE`, `STABLE`, `DEPRECATED`.
- Add 14 optional fields to `Component` dataclass, all with defaults `None` / `()` / `{}`.
- Extend `to_dict` to omit empty/None fields.
- Extend `from_dict` (or parser branch) to accept them.

**Step 4: Verify tests pass.**

**Step 5: Commit**

```bash
git add tests/core/test_component_semantic_fields.py src/architecture_model/core/types.py src/architecture_model/core/parser.py
git commit -m "feat(schema): add 14 optional semantic fields on Component (2.1 additive)"
```

---

## Task 3 — Semantic fields on other entity kinds

**Rationale:** Extend the pattern from Task 2 to `Capability`, `Behavior`, `Interface`, `Actor`, `Constraint`, `Layer`. Applicability matrix from design §5:

| Field | Actor | Cap | Beh | Int | Con | Lay |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| intent | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| goals |  | ✓ | ✓ |  |  | ✓ |
| stakeholders |  | ✓ | ✓ | ✓ |  |  |
| success_criteria |  | ✓ | ✓ | ✓ | ✓ |  |
| failure_modes |  |  | ✓ | ✓ |  |  |
| trade_offs |  | ✓ |  | ✓ |  | ✓ |
| assumptions | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| open_questions | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| requirements |  | ✓ | ✓ | ✓ |  |  |
| verification |  | ✓ | ✓ | ✓ | ✓ |  |
| slos |  |  |  | ✓ |  |  |
| owner |  | ✓ |  |  |  | ✓ |
| maturity |  | ✓ | ✓ | ✓ | ✓ | ✓ |

**Files:**
- Modify: `src/architecture_model/core/types.py` for each kind
- Modify: `src/architecture_model/core/parser.py` for each parser branch
- Test: `tests/core/test_entity_semantic_fields.py` — parametrized over (kind, field_set) pairs

**Steps:** One test per (kind, non-trivial round-trip) — 6 dataclasses × ~3 assertions each; then implementation; then commit per kind (6 commits) to keep diffs bite-sized.

**Commits (one per kind):**

```
feat(schema): add semantic fields on Capability (2.1 additive)
feat(schema): add semantic fields on Behavior (2.1 additive)
feat(schema): add semantic fields on Interface (2.1 additive)
feat(schema): add semantic fields on Actor (2.1 additive)
feat(schema): add semantic fields on Constraint (2.1 additive)
feat(schema): add semantic fields on Layer (2.1 additive)
```

---

## Task 4 — `schema_version` bump to 2.1 + JSON Schema update

**Files:**
- Modify: `src/architecture_model/spec/architecture-model.schema.json` — bump `$id`, add new field definitions, mark all as `optional`, add semantic-type sub-schemas
- Modify: `src/architecture_model/spec/__init__.py` if it exposes `SCHEMA_VERSION`
- Test: `tests/spec/test_schema_version_bump.py`

**Test:**

```python
"""schema_version 2.1 accepts both 2.0 and 2.1 models; JSON Schema validates."""

from pathlib import Path
import json

from architecture_model.core.parser import load_model
from architecture_model.core.validator import validate_model

SCHEMA = Path("src/architecture_model/spec/architecture-model.schema.json")
FIXTURES_20 = Path("tests/fixtures").glob("**/*.yaml")  # existing 2.0 fixtures


def test_schema_advertises_2_1():
    schema = json.loads(SCHEMA.read_text())
    assert "2.1" in schema["properties"]["meta"]["properties"]["schema_version"]["enum"]
    assert "2.0" in schema["properties"]["meta"]["properties"]["schema_version"]["enum"]


def test_semantic_type_definitions_present():
    schema = json.loads(SCHEMA.read_text())
    defs = schema["$defs"]
    assert "FailureMode" in defs
    assert "TradeOff" in defs
    assert "SLO" in defs
```

**Commit:**

```bash
git add src/architecture_model/spec/architecture-model.schema.json tests/spec/test_schema_version_bump.py
git commit -m "feat(schema): bump schema_version to 2.1 (additive; 2.0 still accepted)"
```

---

## Task 5 — Backward-compat regression: all 2.0 fixtures still parse and validate

**Rationale:** Invariant guard. Every pre-Phase-2 fixture must load + validate unchanged.

**Files:**
- Test: `tests/regression/test_schema_2_0_backcompat.py`

**Test:**

```python
"""Every 2.0 fixture in the repo continues to parse and validate unchanged."""

from pathlib import Path
import pytest

from architecture_model.core.parser import load_model
from architecture_model.core.validator import validate_model

FIXTURE_ROOTS = [
    Path("tests/fixtures"),
    Path("tests/lifecycle/fixtures"),
]


def _iter_20_yamls():
    for root in FIXTURE_ROOTS:
        if not root.exists():
            continue
        for yaml_path in root.rglob("*.yaml"):
            text = yaml_path.read_text()
            if "schema_version: '2.0'" in text or 'schema_version: "2.0"' in text:
                yield yaml_path


@pytest.mark.parametrize("yaml_path", list(_iter_20_yamls()), ids=str)
def test_2_0_fixture_still_parses_and_validates(yaml_path):
    model = load_model(yaml_path)
    result = validate_model(model)
    assert result.is_valid, f"{yaml_path}: {result.issues}"
```

**Commit:**

```bash
git add tests/regression/test_schema_2_0_backcompat.py
git commit -m "test(schema): guard 2.0 fixture backward compatibility under 2.1"
```

---

## Task 6 — Migration CLI

**Rationale:** Downstream projects need a one-shot upgrade. Behavior: read `.architecture-model.yaml`, set `schema_version: '2.1'`, preserve everything else byte-identically (no field reordering, no re-quoting). Report skeleton-field candidates without writing them.

**Files:**
- Create: `src/architecture_model/cli/migrate.py`
- Modify: `src/architecture_model/cli/__init__.py` — register subcommand
- Test: `tests/cli/test_migrate.py`

**Test:**

```python
"""architecture-model migrate --to 2.1 upgrades schema_version and only that."""

from pathlib import Path
from click.testing import CliRunner

from architecture_model.cli import cli


def test_dry_run_reports_planned_changes(tmp_path):
    src = tmp_path / ".architecture-model.yaml"
    src.write_text("meta:\n  schema_version: '2.0'\n  project: demo\nentities: {}\n")
    result = CliRunner().invoke(cli, ["migrate", str(src), "--to", "2.1", "--dry-run"])
    assert result.exit_code == 0
    assert "would set schema_version to 2.1" in result.output
    assert src.read_text() == "meta:\n  schema_version: '2.0'\n  project: demo\nentities: {}\n"


def test_apply_writes_2_1_version(tmp_path):
    src = tmp_path / ".architecture-model.yaml"
    src.write_text("meta:\n  schema_version: '2.0'\n  project: demo\nentities: {}\n")
    result = CliRunner().invoke(cli, ["migrate", str(src), "--to", "2.1"])
    assert result.exit_code == 0
    assert "schema_version: '2.1'" in src.read_text()
    assert "schema_version: '2.0'" not in src.read_text()


def test_refuses_when_already_at_target(tmp_path):
    src = tmp_path / ".architecture-model.yaml"
    src.write_text("meta:\n  schema_version: '2.1'\n  project: demo\nentities: {}\n")
    result = CliRunner().invoke(cli, ["migrate", str(src), "--to", "2.1"])
    assert result.exit_code != 0
    assert "already at 2.1" in result.output
```

**Implementation notes:** Use PyYAML with `default_flow_style=False`, `sort_keys=False`, and preserve trailing newlines. For byte-preservation of unchanged parts, use string replacement on the meta block rather than a full round-trip parse. Guard against models that never had a `schema_version` line (error, tell user to run pipeline first).

**Commit:**

```bash
git add tests/cli/test_migrate.py src/architecture_model/cli/migrate.py src/architecture_model/cli/__init__.py
git commit -m "feat(cli): add architecture-model migrate --to 2.1 (with --dry-run)"
```

---

## Task 7 — Render semantic fields in projectors

**Rationale:** Fields aren't valuable until they render. Wire two projectors first (`component_spec` from Phase 1, `functional_analysis` SE doc from Phase 1) so end-to-end value is provable. Remaining projectors follow the pattern; deferred to per-need basis.

**Files:**
- Modify: `src/architecture_model/lifecycle/projectors/nonse.py` (`component_spec` projector added in Phase 1)
- Modify: `src/architecture_model/lifecycle/projectors/se_docs.py` (`functional_analysis`)
- Test: `tests/lifecycle/projectors/test_semantic_field_rendering.py`

**Behavior:** When `intent`/`failure_modes`/`trade_offs`/`slos`/`maturity`/`owner`/`dependencies_rationale` are present on a rendered entity, emit a `## Intent`, `## Failure Modes`, `## Trade-Offs`, `## SLOs`, `## Ownership`, `## Dependency Rationale` section respectively. Absent fields: no section, no placeholder. Byte-identical when all fields absent (no regression on existing outputs).

**Test skeleton:**

```python
def test_component_spec_omits_semantic_sections_when_all_fields_absent(minimal_model):
    view = project(materialize(...), ViewSpec(projector="family3.component_spec", ...))
    md = render_markdown(view)
    assert "## Intent" not in md
    assert "## Failure Modes" not in md


def test_component_spec_renders_intent_when_present(model_with_intent):
    view = project(materialize(...), ViewSpec(projector="family3.component_spec", ...))
    md = render_markdown(view)
    assert "## Intent" in md
    assert "Parse YAML into typed model." in md


def test_component_spec_backward_compat_byte_identical(model_2_0_fixture):
    """A 2.0 model rendered post-Phase-2 == same model rendered pre-Phase-2 (via captured fixture)."""
    view = project(...)
    md = render_markdown(view)
    expected = (FIXTURES / "component_spec_pre_phase2.md").read_text()
    assert md == expected
```

**Capture pre-Phase-2 fixture:** before starting this task, run Phase-1 `component_spec` projector on a canonical 2.0 model and commit the output to `tests/fixtures/pre_phase2/component_spec_pre_phase2.md`.

**Commit:**

```bash
git add tests/fixtures/pre_phase2/component_spec_pre_phase2.md \
        tests/lifecycle/projectors/test_semantic_field_rendering.py \
        src/architecture_model/lifecycle/projectors/nonse.py \
        src/architecture_model/lifecycle/projectors/se_docs.py
git commit -m "feat(projectors): render semantic fields in component_spec + functional_analysis"
```

---

## Task 8 — `ModelSlice.supplementary_refs`

**Rationale:** Family-6 (Interfaces reference docs), Family-7 (Quality/Verification), and Family-8 (Evolution/Health) views need data outside the model YAML (manifest, gates, drift, SI&L, test results, learning). One typed field on `ModelSlice` unifies them.

**Files:**
- Modify: `src/architecture_model/lifecycle/model_slice.py`
- Test: `tests/lifecycle/test_supplementary_refs.py`

**Contract:**

```python
@dataclass(frozen=True)
class SupplementaryRef:
    kind: Literal["manifest", "sil", "gates", "drift", "test_results", "learning"]
    path: str | None = None      # optional override; default resolves via well-known path
    filter: dict[str, Any] | None = None   # kind-specific filter (e.g., {"component_id": "COMP-3"})

    def to_dict(self) -> dict[str, Any]: ...

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SupplementaryRef": ...
```

`ModelSlice` gains `supplementary_refs: tuple[SupplementaryRef, ...] = ()`, serialized as list, omitted when empty. Digest input includes serialized refs in canonical order.

**Test:**

```python
def test_slice_with_supplementary_refs_round_trip():
    s = ModelSlice(
        id="s1", architecture_id="a1", model_revision="0000001",
        scope="local", shared_refs="none",
        supplementary_refs=(
            SupplementaryRef(kind="manifest"),
            SupplementaryRef(kind="sil", filter={"component_id": "COMP-3"}),
        ),
    )
    d = s.to_dict()
    assert d["supplementary_refs"][0]["kind"] == "manifest"
    assert ModelSlice.from_dict(d) == s


def test_slice_without_supplementary_omits_field():
    s = ModelSlice(id="s1", architecture_id="a1", model_revision="0000001",
                   scope="local", shared_refs="none")
    assert "supplementary_refs" not in s.to_dict()


def test_supplementary_ref_kind_is_validated():
    with pytest.raises(ValueError):
        SupplementaryRef(kind="unknown_kind")
```

**Commit:**

```bash
git add tests/lifecycle/test_supplementary_refs.py src/architecture_model/lifecycle/model_slice.py
git commit -m "feat(slice): add SupplementaryRef and ModelSlice.supplementary_refs"
```

---

## Task 9 — `MaterializedSlice.manifest_fragment`

**Rationale:** Family-6 reference docs (CLI, API, plugin guide) need signatures/routes/decorators from the manifest.

**Files:**
- Modify: `src/architecture_model/lifecycle/model_slice_materializer.py`
- Test: `tests/lifecycle/test_manifest_fragment.py`

**Contract:** When `SupplementaryRef(kind="manifest")` is present, materializer loads the manifest (from repo path via `generate_manifest` or a persisted JSON on disk if available), filters modules/functions/classes to those belonging to entities in scope, and attaches as `MaterializedSlice.manifest_fragment: ManifestFragment`. Fragment is a lightweight dataclass mirroring the subset of `Manifest` fields used by projectors (`modules`, `functions`, `classes`, `imports`).

**Test:**

```python
def test_materialize_with_manifest_ref_populates_fragment(tmp_repo_with_manifest):
    slice_ = ModelSlice(..., supplementary_refs=(SupplementaryRef(kind="manifest"),))
    mslice = materialize(slice_, model, repo_path=tmp_repo_with_manifest)
    assert mslice.manifest_fragment is not None
    assert len(mslice.manifest_fragment.functions) > 0


def test_materialize_without_manifest_ref_leaves_fragment_none(minimal_model):
    slice_ = ModelSlice(..., supplementary_refs=())
    mslice = materialize(slice_, minimal_model)
    assert mslice.manifest_fragment is None


def test_manifest_fragment_filtered_to_scope(model_with_two_components, tmp_repo):
    slice_ = ModelSlice(..., scope="local",
                        selectors={"entity_ids": ["COMP-1"]},
                        supplementary_refs=(SupplementaryRef(kind="manifest"),))
    mslice = materialize(slice_, model_with_two_components, repo_path=tmp_repo)
    fns = mslice.manifest_fragment.functions
    assert all(fn.file in COMP_1_FILES for fn in fns)
```

**Commit:**

```bash
git add tests/lifecycle/test_manifest_fragment.py src/architecture_model/lifecycle/model_slice_materializer.py
git commit -m "feat(materializer): populate MaterializedSlice.manifest_fragment from SupplementaryRef"
```

---

## Task 10 — Materializer wiring for `sil`, `gates`, `drift`, `test_results`, `learning`

**Rationale:** Uniform pattern: each kind resolves to a typed fragment on `MaterializedSlice.supplementary_fragments[kind]`.

**Files:**
- Modify: `src/architecture_model/lifecycle/model_slice_materializer.py`
- Create: `src/architecture_model/lifecycle/supplementary_loaders.py` — one loader per kind
- Test: `tests/lifecycle/test_supplementary_fragments.py`

**Well-known paths:**
- `manifest` → repo-provided (Task 9 done)
- `sil` → `.architecture/sil.sqlite` (read-only query)
- `gates` → `.architecture/gates.jsonl`
- `drift` → `.architecture/drift.jsonl`
- `test_results` → `.architecture/test_results.jsonl`
- `learning` → `.architecture/learning.jsonl` (may not exist — return empty)

**Filter contract:** each loader accepts kind-specific `filter` dict (e.g., `{"component_id": ...}`, `{"since": "2026-08-01T00:00:00Z"}`) and applies before returning.

**Commit:**

```bash
git add tests/lifecycle/test_supplementary_fragments.py \
        src/architecture_model/lifecycle/supplementary_loaders.py \
        src/architecture_model/lifecycle/model_slice_materializer.py
git commit -m "feat(materializer): wire sil/gates/drift/test_results/learning fragments"
```

---

## Task 11 — Temporal slicing fields

**Files:**
- Modify: `src/architecture_model/lifecycle/model_slice.py`
- Test: `tests/lifecycle/test_temporal_slicing.py`

**Contract:**

```python
@dataclass(frozen=True)
class RevisionRange:
    from_: str    # 7-digit generation id
    to: str       # 7-digit generation id

@dataclass(frozen=True)
class TimeWindow:
    from_: str    # ISO-8601 UTC
    to: str       # ISO-8601 UTC
```

Both fields optional on `ModelSlice`. Serialization: `from` (not `from_`) to avoid Python keyword. Slice digest includes them in canonical order.

**Tests:** round-trip; digest changes when temporal field present; missing field omitted from serialization.

**Commit:**

```bash
git add tests/lifecycle/test_temporal_slicing.py src/architecture_model/lifecycle/model_slice.py
git commit -m "feat(slice): add revision_range and time_window fields for temporal views"
```

---

## Task 12 — Materializer wiring for temporal fields

**Rationale:** When `revision_range` present, materializer loads each generation in range via `package_load` and attaches `MaterializedSlice.revision_series: tuple[ModelRevisionFragment, ...]`. When `time_window` present on supplementary journals, loaders filter by ISO timestamp.

**Files:**
- Modify: `src/architecture_model/lifecycle/model_slice_materializer.py`
- Test: `tests/lifecycle/test_temporal_materialization.py`

**Commit:**

```bash
git add tests/lifecycle/test_temporal_materialization.py src/architecture_model/lifecycle/model_slice_materializer.py
git commit -m "feat(materializer): resolve revision_range and time_window filters"
```

---

## Task 13 — Overlay slots in `ViewSpec.curation`

**Files:**
- Modify: `src/architecture_model/lifecycle/view_spec.py`
- Test: `tests/lifecycle/test_view_spec_overlays.py`

**Contract:**

```python
@dataclass(frozen=True)
class Curation:
    ...existing fields...
    overlays: tuple[str, ...] = ()   # e.g., ("sil", "drift", "gates")
```

Order preserved; deterministic; unknown values allowed (projector may not recognize an overlay, silently skips).

**Test:**

```python
def test_view_spec_serializes_overlays_in_declared_order():
    spec = ViewSpec(..., curation=Curation(overlays=("sil", "drift")))
    d = spec.to_dict()
    assert d["curation"]["overlays"] == ["sil", "drift"]


def test_view_spec_omits_overlays_when_empty():
    spec = ViewSpec(..., curation=Curation())
    d = spec.to_dict()
    assert "overlays" not in d["curation"]
```

**Commit:**

```bash
git add tests/lifecycle/test_view_spec_overlays.py src/architecture_model/lifecycle/view_spec.py
git commit -m "feat(view-spec): add overlay slots in curation (deterministic order)"
```

---

## Task 14 — Overlay-aware projector helper

**Files:**
- Create: `src/architecture_model/lifecycle/overlays.py`
- Test: `tests/lifecycle/test_overlays.py`

**Contract:**

```python
def apply_overlays(base_view: ProjectedView, mslice: MaterializedSlice,
                   declared: Sequence[str]) -> ProjectedView:
    """Fold recognized overlays into base_view.diagram_spec in declared order.

    Recognized: 'sil', 'drift', 'gates'. Unknown overlays are ignored (deterministic).
    Each overlay adds a section/decoration keyed by overlay name.
    """
```

Provide three built-in overlays that mutate the diagram_spec dict:
- `sil`: adds `sil_summary` key per entity when supplementary_fragments["sil"] present
- `drift`: adds `drift_flags` key per entity from supplementary_fragments["drift"]
- `gates`: adds `gate_status` block at top from supplementary_fragments["gates"] last outcome

**Commit:**

```bash
git add tests/lifecycle/test_overlays.py src/architecture_model/lifecycle/overlays.py
git commit -m "feat(overlays): add apply_overlays helper (sil/drift/gates)"
```

---

## Task 15 — Gates journal writer

**Files:**
- Create: `src/architecture_model/feedback/__init__.py`
- Create: `src/architecture_model/feedback/gates.py`
- Test: `tests/feedback/test_gates_journal.py`

**Contract:**

```python
def append(repo_path: Path, event: GateEvent) -> None:
    """Append a single line to .architecture/gates.jsonl.

    Atomic: writes tmp + rename. Never truncates.
    """


@dataclass(frozen=True)
class GateEvent:
    timestamp: str          # ISO-8601 UTC (may be pinned via AMS_DETERMINISTIC_NOW)
    gate_id: str
    outcome: Literal["pass", "fail", "warn"]
    findings: tuple[str, ...] = ()
    model_revision: str | None = None
```

**Test:** append twice, read file, assert two lines, both parseable JSON, order preserved.

**Commit:**

```bash
git add tests/feedback/test_gates_journal.py src/architecture_model/feedback/gates.py src/architecture_model/feedback/__init__.py
git commit -m "feat(feedback): add append-only gates.jsonl writer"
```

---

## Task 16 — Drift journal writer

**Files:**
- Create: `src/architecture_model/feedback/drift.py`
- Test: `tests/feedback/test_drift_journal.py`

**Contract:**

```python
@dataclass(frozen=True)
class DriftSnapshot:
    timestamp: str
    model_revision: str
    flags: tuple[DriftFlag, ...]

@dataclass(frozen=True)
class DriftFlag:
    entity_id: str
    kind: Literal["orphan", "missing_impl", "unrealized_capability", "broken_ref"]
    detail: str
```

Same append-only pattern as Task 15.

**Commit:**

```bash
git add tests/feedback/test_drift_journal.py src/architecture_model/feedback/drift.py
git commit -m "feat(feedback): add append-only drift.jsonl writer"
```

---

## Task 17 — Test-results journal + JUnit ingest

**Files:**
- Create: `src/architecture_model/feedback/test_results.py`
- Create: `src/architecture_model/feedback/junit_ingest.py`
- Test: `tests/feedback/test_test_results_journal.py`
- Test: `tests/feedback/test_junit_ingest.py`

**Contract:**

```python
@dataclass(frozen=True)
class TestResultBatch:
    timestamp: str
    suite: str
    total: int
    passed: int
    failed: int
    skipped: int
    duration_s: float
    failures: tuple[TestFailure, ...] = ()


def ingest_junit(junit_xml_path: Path) -> TestResultBatch:
    """Parse a JUnit XML file into a TestResultBatch (stdlib xml.etree, no external deps)."""
```

**Commit:**

```bash
git add tests/feedback/test_test_results_journal.py tests/feedback/test_junit_ingest.py \
        src/architecture_model/feedback/test_results.py src/architecture_model/feedback/junit_ingest.py
git commit -m "feat(feedback): add test_results.jsonl writer and JUnit ingest"
```

---

## Task 18 — Wire gates journal from `architect_gate` (oca)

**Rationale:** Every `architect_gate` invocation appends to `.architecture/gates.jsonl`.

**Files:**
- Modify: `src/opencode_arch/mcp/tools/gate.py` (or wherever the tool is defined)
- Test: `tests/mcp/tools/test_gate_journal_writes.py`

**Contract:** After computing gate outcome, call `architecture_model.feedback.gates.append(repo_path, event)`. On failure to write journal, do NOT fail the gate — log a warning and continue (journal is diagnostic, not authoritative).

**Test:** invoke gate tool on a fixture repo, assert `.architecture/gates.jsonl` gained one line matching the outcome.

**Guardrail:** the fixture repo lives in `tmp_path`, never the real `.architecture/` in the working tree.

**Commit:**

```bash
git add tests/mcp/tools/test_gate_journal_writes.py src/opencode_arch/mcp/tools/gate.py
git commit -m "feat(feedback): append to gates.jsonl from architect_gate"
```

---

## Task 19 — Wire drift journal from post-extract hook (oca)

**Rationale:** After each successful pipeline run, compute drift flags via `architecture_model.core.drift` (extracted per design §3 as shared helper) and append a `DriftSnapshot`.

**Files:**
- Modify: `src/opencode_arch/mcp/tools/pipeline.py` (or wherever `architect_pipeline` finalizes)
- Test: `tests/mcp/tools/test_drift_journal_writes.py`

**Commit:**

```bash
git add tests/mcp/tools/test_drift_journal_writes.py src/opencode_arch/mcp/tools/pipeline.py
git commit -m "feat(feedback): append to drift.jsonl after each pipeline run"
```

---

## Task 20 — Test-results ingest CLI (oca)

**Files:**
- Create: `src/opencode_arch/cli/feedback.py` — click subcommand group
- Modify: `src/opencode_arch/cli/__init__.py`
- Test: `tests/cli/test_feedback_ingest_junit.py`

**Command:** `opencode-arch feedback ingest-junit <junit.xml> [--repo-path .]`

**Commit:**

```bash
git add tests/cli/test_feedback_ingest_junit.py src/opencode_arch/cli/feedback.py src/opencode_arch/cli/__init__.py
git commit -m "feat(cli): add opencode-arch feedback ingest-junit"
```

---

## Task 21 — Pipeline seeds `intent` from docstrings

**Rationale:** First automatic population path (per design §5). `specify` stage extracts first-line docstring from primary file into `Component.intent` (only when field is empty). Purely additive; models where components already have `intent` are untouched.

**Files:**
- Modify: `src/architecture_model/pipeline/specify.py`
- Test: `tests/pipeline/test_intent_seeding.py`

**Behavior:**
- For each Component with `intent is None` and at least one primary Python file:
  - Read the file's module-level docstring
  - Take the first line, strip whitespace
  - Assign to `component.intent` if non-empty and ≤ 200 chars
- Deterministic: if docstring changes, `intent` changes; captured in package_diff as a semantic-field change.

**Commit:**

```bash
git add tests/pipeline/test_intent_seeding.py src/architecture_model/pipeline/specify.py
git commit -m "feat(pipeline): seed Component.intent from module docstrings in specify stage"
```

---

## Task 22 — Invalidation rules for semantic-field diffs

**Rationale:** Semantic-field diffs should trigger only per-entity F1/F7 view rebuilds (surgical), not the entire family. Extends the Phase-1 invalidation module.

**Files:**
- Modify: `src/architecture_model/lifecycle/invalidation.py`
- Test: `tests/lifecycle/test_invalidation_semantic_fields.py`

**Rule additions:**

```python
# In the rule table added by Phase 1, extend `changed_field_rules`:
SEMANTIC_FIELD_RULES = {
    "intent":        ["family1.entity_page", "family1.mission"],
    "failure_modes": ["family7.entity_page", "family7.risk"],
    "trade_offs":    ["family1.entity_page", "family3.entity_page"],
    "slos":          ["family5.entity_page", "family7.entity_page", "family8.entity_page"],
    "owner":         ["family1.entity_page"],
    "maturity":      ["family1.entity_page", "family8.health"],
    "requirements":  ["family7.req_matrix", "family7.entity_page"],
    "verification":  ["family7.req_matrix", "family7.entity_page"],
    "dependencies_rationale": ["family3.entity_page", "family3.dependency_matrix"],
    "assumptions":   ["family7.entity_page"],
    "open_questions": ["family7.entity_page", "family8.health"],
    "goals":         ["family1.entity_page", "family2.entity_page"],
    "stakeholders":  ["family1.entity_page"],
    "success_criteria": ["family1.entity_page", "family7.entity_page"],
}
```

**Test:** create a diff mutating only `intent` on `COMP-3` and assert stale-set == entity-scoped F1/mission views for `COMP-3`.

**Commit:**

```bash
git add tests/lifecycle/test_invalidation_semantic_fields.py src/architecture_model/lifecycle/invalidation.py
git commit -m "feat(invalidation): map semantic-field diffs to surgical per-entity rebuilds"
```

---

## Task 23 — Overlay determinism guard

**Files:**
- Test: `tests/lifecycle/test_overlay_determinism.py`

**Test:** for each overlay combination `(sil,)`, `(drift,)`, `(gates,)`, `(sil, drift)`, `(sil, drift, gates)`, project + render twice; assert byte-identical. Also assert `(sil, drift)` != `(drift, sil)` in output only if projector is order-sensitive (it should be — overlays declared in order are applied in order).

**Commit:**

```bash
git add tests/lifecycle/test_overlay_determinism.py
git commit -m "test(overlays): guard byte-identical output under fixed overlay order"
```

---

## Task 24 — CONTEXT.md refresh (ams)

- Note `schema_version: 2.1` (additive, 2.0 still accepted).
- List new semantic fields on entities.
- Document `SupplementaryRef` kinds and journal file paths.
- Document overlay slots.
- Note migration CLI usage.

**Commit:** `docs(context): refresh AMS CONTEXT.md for Phase 2 schema + feedback`

---

## Task 25 — CONTEXT.md refresh (oca)

- Note gates + drift journal auto-population.
- Document `opencode-arch feedback ingest-junit`.
- Reference AMS Phase 2 for schema changes.

**Commit:** `docs(context): refresh OCA CONTEXT.md for Phase 2 feedback wiring`

---

## Task 26 — Full-suite verification

Run both repos' full suites; expect baseline preserved plus new tests added by Phase 2 all passing. Then invoke @superpowers:verification-before-completion.

**Expected output:**
- ams: baseline + ~50 new Phase-2 tests, all passing.
- oca: baseline + ~10 new Phase-2 tests, all passing.

**Commit:** none (verification only).

---

## Task 27 — Executor per-subsystem fan-out for `scope='descendants'`

**Origin:** Deferred from Phase 1 Task 13. During Phase 1 execution we discovered that plan Task 13 conflated two distinct features:

- **Merged-fragment** (shipped in Phase 1 via ``materialize()`` at ``model_slice_materializer.py:184``): one artifact per ``ArtifactSpec``, fragment = root ∪ all descendants merged.
- **Per-subsystem fan-out** (deferred here): N artifacts per ``ArtifactSpec`` with ``scope='descendants'``, one per descendant + root, each with a single-package fragment, output paths namespaced by subsystem slug.

Merged-fragment answers "give me one architectural document that spans the whole tree." Fan-out answers "give me one document per M2 subsystem, addressable by slug (``conops-a.md``, ``conops-b.md``)." Plan Task 13's example (``docs/architecture/conops.md``) and ``>= 2`` built-count assertion imply fan-out. Phase 1 shipping tests (``tests/lifecycle_exec/test_rebuild_descendants.py``) cover merged-fragment; this task adds fan-out on top without removing merged-fragment.

**Files (oca):**
- Modify: ``src/opencode_arch/lifecycle_exec/rebuild.py`` (executor loop over descendants; ``spec_id`` namespacing)
- Modify: ``src/architecture_model/lifecycle/model_slice.py`` (optional: add a ``fan_out: bool`` field or a new scope value ``descendants:each`` — decide in design step)
- Create: ``tests/lifecycle_exec/test_rebuild_fanout.py``

**Step 1: Design decision — signal fan-out vs. merge**

Two options, decide before coding:

1. Add ``ModelSlice.fan_out: bool = False`` (Phase-2 additive schema change). ``scope='descendants' + fan_out=False`` → merged (Phase 1 default). ``fan_out=True`` → one materialize per descendant.
2. Introduce a new scope literal ``descendants:each`` alongside existing ``descendants``. Same semantics, no new field. Requires touching ``Scope = Literal[...]`` in ``model_slice.py:54``.

**Recommendation:** option 2 — keeps the "scope tells you the fan-out shape" invariant. Option 1 gives scope + fan_out two knobs, which is confusing.

**Step 2: Write failing test**

```python
def test_fanout_produces_one_artifact_per_descendant(tmp_path):
    # Publish root with 2 children a, b
    # Rebuild with scope='descendants:each' (or fan_out=True)
    # Assert len(report.built) == 3  # root + a + b
    # Assert each output_path contains the subsystem slug
    # Assert each fragment contains only that subsystem's entities
```

**Step 3: Implement executor loop**

In ``rebuild_artifacts``, when the resolved slice has fan-out semantics:
- Enumerate ``iter_descendants(pkg, include_self=True)``.
- For each descendant, materialize a slice narrowed to that package's entities only (build a per-descendant ``ModelSlice`` internally, or subset the fragment after materialize).
- Namespace ``spec_id`` in the output as ``<spec_id>.<slug>`` so ``<lifecycle>/artifacts/<id>.<ext>`` does not collide across descendants.
- Append one entry per descendant to ``report.built``.

**Step 4: Verify Phase 1 merged-fragment tests still pass**

``tests/lifecycle_exec/test_rebuild_descendants.py`` must remain green — this task adds fan-out, does not modify merge.

**Step 5: Commit**

```bash
git add src/opencode_arch/lifecycle_exec/rebuild.py tests/lifecycle_exec/test_rebuild_fanout.py
# (+ src/architecture_model/lifecycle/model_slice.py if schema change)
git commit -m "feat(lifecycle_exec): per-subsystem fan-out for scope='descendants:each'"
```

---

## Task 28 — Persist `ProjectedView.provenance` per artifact

**Origin:** Deferred from Phase 1 Task 14. Task 10 stamps `ProjectedView.provenance["freshness"] = "fresh"` and `["revision"]` in-memory at ``src/architecture_model/lifecycle/view_projection.py:189-194``, but the OCA rebuild path (``lifecycle_exec/rebuild.py:575``) writes only raw renderer bytes to ``<lifecycle>/artifacts/<id>.<ext>``. Provenance is discarded after the render step.

**Consequence:** Task 14's ``architect_evaluate.freshness_summary`` cannot classify anything as fresh/stale/pending — every present artifact falls into the ``unknown`` bucket by design (see docstring at ``opencode_arch/mcp/tools/evaluate.py:116``). The shape contract is honored; the semantic contract is not.

**Files (oca):**
- Modify: ``src/opencode_arch/lifecycle_exec/rebuild.py`` (write provenance sidecar next to each atomic body write)
- Modify: ``src/opencode_arch/mcp/tools/evaluate.py`` (read sidecar; bucket by ``provenance["freshness"]``)
- Extend: ``tests/mcp/tools/test_evaluate_freshness.py`` (assert non-zero ``fresh`` after a real rebuild round-trip)

**Step 1: Design decision — sidecar shape**

Two options:

1. **Per-artifact JSON sidecar**: alongside ``<id>.<ext>`` write ``<id>.provenance.json`` containing the ``ProjectedView.provenance`` dict verbatim. Read cost is trivial; per-file operation matches rebuild's atomic-write pattern.
2. **Single index file**: ``.architecture/lifecycle/artifacts/_index.yaml`` mapping ``spec_id → provenance``. Fewer files but requires read-modify-write on every rebuild (contention risk in Phase 2's parallel rebuild story).

**Recommendation:** option 1 — matches the file-per-artifact model already established by ``rebuild.py``, and evaluate's directory scan naturally skips ``*.provenance.json`` if we exclude the ``.provenance.json`` suffix (or, cleaner, count only files whose basename does NOT end in ``.provenance.json``).

**Step 2: Write failing test**

```python
def test_evaluate_reports_fresh_after_rebuild(tmp_path):
    # publish root, register a projector, run rebuild_artifacts
    # then call evaluate_workspace(force_refresh=True)
    # assert freshness_summary["fresh"] >= 1
```

**Step 3: Implement sidecar write in rebuild + reader in evaluate**

Rebuild:
- After atomic body write at ``rebuild.py:575``, also write ``<id>.provenance.json`` containing ``{"freshness": provenance["freshness"], "revision": provenance["revision"], "produced_at": provenance["produced_at"], "projector": provenance["projector"]}`` (no need to persist the full dict).

Evaluate:
- In ``_collect_freshness_summary``, for each non-sidecar file, check if ``<name>.provenance.json`` exists; if so read ``freshness`` and increment the matching bucket; otherwise fall back to ``unknown``.
- Skip ``*.provenance.json`` from the top-level file count.

**Step 4: Update docstring in evaluate.py**

Remove the "Phase 1 pragmatic" note; state that freshness now reflects actual provenance and that missing sidecars are treated as unknown (for artifacts produced before Task 28 shipped).

**Step 5: Commit**

```bash
git add src/opencode_arch/lifecycle_exec/rebuild.py src/opencode_arch/mcp/tools/evaluate.py tests/mcp/tools/test_evaluate_freshness.py
git commit -m "feat(lifecycle_exec): persist ProjectedView.provenance per artifact; wire freshness_summary"
```

---

## Rollback Strategy

Each task is a single commit on the feature branch. If a task's design proves flawed under review, revert the commit; no other task depends on internal implementation details (only public contracts, which are covered by tests). Schema bump (Task 4) is the only irreversible task — it's additive and 2.0 remains valid indefinitely.

## Deferred (to Phase 3+)

- Rendering semantic fields in more projectors beyond `component_spec` and `functional_analysis` (Phase 3 landed entity views).
- LLM authoring of semantic fields (Phase 4, write-back projectors).
- Migration CLI batch mode across many downstream repos (Phase 4 tooling).
